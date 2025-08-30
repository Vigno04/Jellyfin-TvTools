#!/usr/bin/env python3
"""Filtering related helpers (keep/exclude groups, patterns, name-based quality)."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Callable

from ..quality_manager import QualityManager

ProgressCb = Callable[[str], None] | None


def filter_channels(channels: List[Dict[str, Any]], config: Dict[str, Any], *, progress_callback: ProgressCb = None, quality_config_override: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    if progress_callback:
        progress_callback("Applying filters...")
    if not config.get('auto_select_enabled', True):
        if progress_callback:
            progress_callback("Auto selection disabled: 0 preselected")
        return []
    keep_groups = set(config.get('keep_groups', []))
    exclude_groups = set(config.get('exclude_groups', []))
    force_keep = set(config.get('force_keep_channels', []))
    force_exclude = set(config.get('force_exclude_channels', []))
    exclude_patterns = config.get('exclude_patterns', [])
    filtered: List[Dict[str, Any]] = []
    for channel in channels:
        name = channel['name']; group = channel['group']; keep = False
        if name in force_exclude:
            keep = False
        elif name in force_keep:
            keep = True
        elif group in exclude_groups:
            keep = False
        elif group in keep_groups:
            keep = True
            for pattern in exclude_patterns:
                if re.search(pattern, name, re.IGNORECASE):
                    keep = False; break
        if keep:
            filtered.append(channel)
    quality_config = quality_config_override or config.get('quality_management', {})
    if quality_config.get('use_name_based_quality', False):
        manager = QualityManager(quality_config)
        filtered, _ = manager.merge(filtered)
    if progress_callback:
        progress_callback(f"Filtering complete: {len(filtered)} channels kept")
    return filtered
