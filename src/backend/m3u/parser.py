#!/usr/bin/env python3
"""M3U playlist parsing utilities."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Callable

ProgressCb = Callable[[str], None] | None


def parse_channels(lines: List[str], *, progress_callback: ProgressCb = None) -> List[Dict[str, Any]]:
    """
    Parse M3U playlist lines into channel dictionaries.
    
    Args:
        lines: List of M3U file lines to parse
        progress_callback: Optional callback function for progress updates
    
    Returns:
        List of channel dictionaries with metadata and stream URLs
    """
    if progress_callback:
        progress_callback("Parsing channels...")
    
    channels: List[Dict[str, Any]] = []
    i = 0
    
    # Skip patterns for non-channel entries
    SKIP_PATTERNS = ['=== ', 'LAST UPDATE', '---']
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line.startswith('#EXTINF:'):
            i += 1
            continue
            
        # Extract channel metadata
        group_match = re.search(r'group-title="([^"]*)"', line)
        group_title = group_match.group(1) if group_match else ""
        
        name_match = re.search(r',([^,]+)$', line)
        channel_name = name_match.group(1).strip() if name_match else ""
        
        # Skip header/separator lines
        if any(pattern in channel_name for pattern in SKIP_PATTERNS):
            i += 2
            continue
        
        # Extract TVG metadata
        tvg_logo = _extract_attribute(line, 'tvg-logo')
        tvg_id = _extract_attribute(line, 'tvg-id')
        tvg_name = _extract_attribute(line, 'tvg-name')
        tvg_chno = _extract_attribute(line, 'tvg-chno')
        channel_id = _extract_attribute(line, 'channel-id')
        
        # Collect all lines for this channel (EXTINF + EXTVLCOPT + URL)
        channel_lines = [lines[i]]
        j = i + 1
        
        while j < len(lines) and lines[j].strip().startswith('#EXTVLCOPT:'):
            channel_lines.append(lines[j])
            j += 1
        
        if j < len(lines) and not lines[j].strip().startswith('#'):
            channel_lines.append(lines[j])
            j += 1
        
        channels.append({
            'name': channel_name,
            'group': group_title,
            'lines': channel_lines,
            'selected': False,
            'tvg_logo': tvg_logo,
            'tvg_id': tvg_id,
            'tvg_name': tvg_name,
            'tvg_chno': tvg_chno,
            'channel_id': channel_id,
        })
        
        i = j
    
    if progress_callback:
        progress_callback(f"Parsed {len(channels)} channels")
    
    return channels


def _extract_attribute(line: str, attribute: str) -> str:
    """
    Extract an attribute value from an EXTINF line.
    
    Args:
        line: The EXTINF line to parse
        attribute: The attribute name to extract (e.g., 'tvg-logo')
    
    Returns:
        The attribute value or empty string if not found
    """
    match = re.search(rf'{attribute}="([^"]*)"', line)
    return match.group(1) if match else ''
