#!/usr/bin/env python3
"""Configuration management utilities for Jellyfin TV Tools backend."""
from __future__ import annotations
import json
import os
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "download_url": "https://tivustream.website/urls/listm3u",
    "auto_select_enabled": True,  # If False, no filtering is applied; all channels start unselected
    "keep_groups": [],
    "exclude_groups": [],
    "force_keep_channels": [],
    "force_exclude_channels": [],
    "exclude_patterns": [
        ".*test.*",
        ".*backup.*", 
        ".*temp.*",
        ".*prova.*",
        ".*demo.*"
    ],
    "quality_management": {
        # Legacy name-based quality detection (HD, 4K suffixes) - less reliable than stream analysis
        "use_name_based_quality": False,
        "quality_suffixes": ["4K", "UHD", "HD", "HQ"],
        "priority_order": ["4K", "UHD", "HD", "HQ"],
        "exclude_lower_quality": True,
        "normalize_channel_names": True,
        # When True, prioritizes actual stream analysis over name-based quality suffixes
        "prioritize_stream_analysis": True,
        # Enable in-process caching of stream quality probe results (per URL)
        # Disable if you want always-fresh metrics at the cost of extra network requests.
        "use_stream_quality_cache": False,
        # Time-to-live (seconds) for cached stream quality metrics (only relevant if cache enabled)
        "stream_quality_cache_ttl": 3600,
        # Max number of parallel network probes when analyzing duplicate channel variants
        "max_parallel_stream_probes": 12,
        # Max bytes to download per stream when probing (lower -> faster, risk missing info)
        "max_stream_probe_bytes": 16384,
        # Attempt to use HTTP Range header when probing (some servers may ignore or reject)
        "use_range_header": False,
        # List of channel names that should NOT be normalized (exact match, case-insensitive)
        # Example: ["Rai 4K", "FOCUS"] - these channels will never have suffixes removed
        "normalization_exclusions": ["Rai 4K"],
        # Optional regex based alias normalization applied BEFORE suffix stripping.
        # Each rule: {"pattern": "^raiplay\\s+", "replace": "Rai "}
        # Default below ensures channels like "Raiplay 1 HD" merge with "Rai 1 HD".
        "alias_rules": [
            # Normalize variants like "Raiplay 1", "RaiPlay 2", "Rai Play 3" -> "Rai 1", etc.
            {"pattern": "^rai\\s*play\\s+", "replace": "Rai "},
        ],
    },
}

def get_default_config() -> Dict[str, Any]:
    """Return a fresh copy of the default configuration."""
    # Return a deep-ish copy to avoid accidental mutations
    return json.loads(json.dumps(DEFAULT_CONFIG))

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file; fall back to defaults on error."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.loads(f.read().strip())
    except Exception:
        return get_default_config()
