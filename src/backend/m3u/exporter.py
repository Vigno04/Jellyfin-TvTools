#!/usr/bin/env python3
"""M3U export utilities."""
from __future__ import annotations

from typing import List, Dict, Any, Tuple, Callable
import os

from ..config_manager import get_output_path, ensure_output_directory_exists

ProgressCb = Callable[[str], None] | None


def export_m3u(channels: List[Dict[str, Any]], config: Dict[str, Any], *, output_path: str | None = None, progress_callback: ProgressCb = None) -> Tuple[bool, str]:
    try:
        if progress_callback:
            progress_callback("Exporting M3U playlist...")
        selected = [c for c in channels if c.get('selected')]
        if not selected:
            return False, "No channels selected for export"
        if not output_path:
            output_path = get_output_path(config, 'm3u_output'); ensure_output_directory_exists(config, 'm3u_output')
        lines = ['#EXTM3U']
        for ch in selected:
            extinf = '#EXTINF:-1'
            if ch.get('channel_id'): extinf += f' channel-id="{ch["channel_id"]}"'
            if ch.get('tvg_id'): extinf += f' tvg-id="{ch["tvg_id"]}"'
            if ch.get('tvg_chno'): extinf += f' tvg-chno="{ch["tvg_chno"]}"'
            if ch.get('tvg_name'): extinf += f' tvg-name="{ch["tvg_name"]}"'
            if ch.get('tvg_logo'): extinf += f' tvg-logo="{ch["tvg_logo"]}"'
            if ch.get('group'): extinf += f' group-title="{ch["group"]}"'
            extinf += f',{ch["name"]}'
            lines.append(extinf)
            for l in ch['lines']:
                if l.startswith('#EXTVLCOPT:'): lines.append(l)
            for l in reversed(ch['lines']):
                if not l.startswith('#'): lines.append(l); break
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        msg = f"Successfully exported {len(selected)} channels to {os.path.basename(output_path)}"
        if progress_callback: progress_callback(msg)
        return True, msg
    except Exception as e:  # noqa: BLE001
        err = f"Export failed: {e}"; (progress_callback and progress_callback(err))
        return False, err
