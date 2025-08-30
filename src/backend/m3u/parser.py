#!/usr/bin/env python3
"""M3U playlist parsing utilities."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Callable

ProgressCb = Callable[[str], None] | None


def parse_channels(lines: List[str], *, progress_callback: ProgressCb = None) -> List[Dict[str, Any]]:
    if progress_callback:
        progress_callback("Parsing channels...")
    channels: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            group_match = re.search(r'group-title="([^"]*)"', line)
            group_title = group_match.group(1) if group_match else ""
            name_match = re.search(r',([^,]+)$', line)
            channel_name = name_match.group(1).strip() if name_match else ""
            if ('=== ' in channel_name or 'LAST UPDATE' in channel_name or channel_name.startswith('---')):
                i += 2
                continue
            tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
            tvg_chno_match = re.search(r'tvg-chno="([^"]*)"', line)
            channel_id_match = re.search(r'channel-id="([^"]*)"', line)
            channel_lines = [lines[i]]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('#EXTVLCOPT:'):
                channel_lines.append(lines[j]); j += 1
            if j < len(lines) and not lines[j].strip().startswith('#'):
                channel_lines.append(lines[j]); j += 1
            channels.append({
                'name': channel_name,
                'group': group_title,
                'lines': channel_lines,
                'selected': False,
                'tvg_logo': tvg_logo_match.group(1) if tvg_logo_match else '',
                'tvg_id': tvg_id_match.group(1) if tvg_id_match else '',
                'tvg_name': tvg_name_match.group(1) if tvg_name_match else '',
                'tvg_chno': tvg_chno_match.group(1) if tvg_chno_match else '',
                'channel_id': channel_id_match.group(1) if channel_id_match else '',
            })
            i = j
        else:
            i += 1
    if progress_callback:
        progress_callback(f"Parsed {len(channels)} channels")
    return channels
