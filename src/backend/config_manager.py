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
    "output_directories": {
        # Base directory for all outputs (relative to project root)
        "base_output_dir": "data",
        # M3U playlist output
        "m3u_output": {
            "directory": "data",
            "filename": "tivustream_list.m3u"
        },
        # Session backups
        "session_backups": {
            "directory": "data",
            "filename_prefix": "session_backup_"
        },
        # Channel list exports
        "channel_lists": {
            "directory": "data",
            "filename_prefix": "channel_list_"
        },
        # Current session file
        "current_session": {
            "directory": "data",
            "filename": "session.json"
        }
    },
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


def get_output_directory(config: Dict[str, Any], output_type: str) -> str:
    """
    Get output directory path for a specific output type.
    
    Args:
        config: Configuration dictionary
        output_type: One of 'm3u_output', 'session_backups', 'channel_lists', 'current_session'
    
    Returns:
        Directory path as string
    """
    output_dirs = config.get("output_directories", {})
    
    if output_type in output_dirs:
        return output_dirs[output_type].get("directory", "data")
    
    # Fallback to base directory
    return output_dirs.get("base_output_dir", "data")


def get_output_path(config: Dict[str, Any], output_type: str, filename_suffix: str = None) -> str:
    """
    Get full output file path for a specific output type.
    
    Args:
        config: Configuration dictionary
        output_type: One of 'm3u_output', 'session_backups', 'channel_lists', 'current_session'
        filename_suffix: Optional suffix for timestamped files (e.g., timestamp for backups)
    
    Returns:
        Full file path as string
    """
    output_dirs = config.get("output_directories", {})
    
    if output_type == "m3u_output":
        directory = output_dirs.get("m3u_output", {}).get("directory", "data")
        filename = output_dirs.get("m3u_output", {}).get("filename", "tivustream_list.m3u")
        return os.path.join(directory, filename)
    
    elif output_type == "session_backups":
        directory = output_dirs.get("session_backups", {}).get("directory", "data")
        prefix = output_dirs.get("session_backups", {}).get("filename_prefix", "session_backup_")
        suffix = filename_suffix or "backup"
        return os.path.join(directory, f"{prefix}{suffix}.json")
    
    elif output_type == "channel_lists":
        directory = output_dirs.get("channel_lists", {}).get("directory", "data")
        prefix = output_dirs.get("channel_lists", {}).get("filename_prefix", "channel_list_")
        suffix = filename_suffix or "export"
        return os.path.join(directory, f"{prefix}{suffix}.json")
    
    elif output_type == "current_session":
        directory = output_dirs.get("current_session", {}).get("directory", "data")
        filename = output_dirs.get("current_session", {}).get("filename", "session.json")
        return os.path.join(directory, filename)
    
    # Fallback
    base_dir = output_dirs.get("base_output_dir", "data")
    return os.path.join(base_dir, filename_suffix or "output.txt")


def ensure_output_directory_exists(config: Dict[str, Any], output_type: str) -> None:
    """
    Ensure the output directory for a specific output type exists.
    Creates the directory if it doesn't exist.
    
    Args:
        config: Configuration dictionary
        output_type: One of 'm3u_output', 'session_backups', 'channel_lists', 'current_session'
    """
    directory = get_output_directory(config, output_type)
    os.makedirs(directory, exist_ok=True)
