#!/usr/bin/env python3
"""Facade retaining original public API while delegating to modular helpers.

This keeps backward compatibility for existing imports (M3UProcessor class)
but internally uses smaller focused modules in backend.m3u.*
"""

import os
from typing import List, Dict, Any, Tuple

try:  # local imports
    from .config_manager import load_config
except ImportError:  # pragma: no cover
    from config_manager import load_config  # type: ignore

from .m3u.downloader import download_m3u as _download
from .m3u.parser import parse_channels as _parse
from .m3u.filters import filter_channels as _filter
from .m3u.quality_merge import merge_quality as _merge_quality
from .m3u.dead_check import remove_dead_streams as _remove_dead, remove_unwanted_channels as _remove_unwanted
from .m3u.exporter import export_m3u as _export


class M3UProcessor:
    """Main class for processing M3U playlists with filtering and quality management."""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "..", "config.json")
        self.config = load_config(self.config_path)

    # --- quality management facade --------------------------------------
    def merge_quality(self, channels: List[Dict], progress_callback=None) -> Tuple[List[Dict], int]:
        return _merge_quality(channels, self.config.get('quality_management', {}), progress_callback=progress_callback)
    
    def download_m3u(self, url: str = None, progress_callback=None) -> Tuple[bool, List[str], str]:
        return _download(url or self.config['download_url'], progress_callback=progress_callback)
    
    def parse_channels(self, lines: List[str], progress_callback=None) -> List[Dict]:
        return _parse(lines, progress_callback=progress_callback)
    
    def filter_channels(self, channels: List[Dict], progress_callback=None, quality_config_override: Dict = None) -> List[Dict]:
        return _filter(channels, self.config, progress_callback=progress_callback, quality_config_override=quality_config_override)
    
    def export_m3u(self, channels: List[Dict], output_path: str = None, progress_callback=None) -> Tuple[bool, str]:
        return _export(channels, self.config, output_path=output_path, progress_callback=progress_callback)
    
    def process_full_pipeline(self, url: str = None, progress_callback=None, enable_quality_priority: bool | None = None) -> Tuple[bool, List[Dict], str, int]:
        """
        Run the complete pipeline: download -> parse -> filter
        Returns: (success, channels, message, merged_count)
        """
        # Download
        success, lines, error = self.download_m3u(url, progress_callback)
        if not success:
            return False, [], error, 0
        
        # Parse
        all_channels = self.parse_channels(lines, progress_callback)
        original_count = len(all_channels)
        merged_count = 0
        
        # Check if quality merging is requested
        # Always load full channel list first (no pre-merge). Filtering still marks selections.
        # Disable automatic quality merging (manual button triggers later)
        filtered_channels = self.filter_channels(
            all_channels,
            progress_callback,
            quality_config_override={"use_name_based_quality": False},
        )
        filtered_names = {ch["name"] for ch in filtered_channels}
        for channel in all_channels:
            channel["selected"] = channel["name"] in filtered_names
        return True, all_channels, f"Successfully processed {len(all_channels)} channels (showing all)", merged_count

    def remove_dead_streams(self, channels: List[Dict], progress_callback=None) -> Tuple[List[Dict], int, List[Dict]]:
        return _remove_dead(channels, progress_callback=progress_callback)

    def remove_unwanted_channels(self, channels: List[Dict], progress_callback=None) -> Tuple[List[Dict], int, List[Dict]]:
        return _remove_unwanted(channels, self.config, progress_callback=progress_callback)
