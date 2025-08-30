#!/usr/bin/env python3
"""Playlist download utilities (extracted from monolithic m3u_processor)."""
from __future__ import annotations

from typing import List, Tuple, Callable
import requests

ProgressCb = Callable[[str], None] | None


def download_m3u(url: str, *, progress_callback: ProgressCb = None, timeout: int = 30) -> Tuple[bool, List[str], str]:
    """Download M3U playlist returning (success, lines, error)."""
    try:
        if progress_callback:
            progress_callback("Downloading M3U playlist...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) JellyfinTvTools/downloader'}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        if progress_callback:
            progress_callback("Download completed successfully!")
        return True, lines, ""
    except Exception as e:  # noqa: BLE001
        msg = f"Download failed: {e}"
        if progress_callback:
            progress_callback(msg)
        return False, [], msg
