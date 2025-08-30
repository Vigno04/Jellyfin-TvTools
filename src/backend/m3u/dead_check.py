#!/usr/bin/env python3
"""Dead stream / unwanted channel operations extracted."""
from __future__ import annotations

from typing import List, Dict, Any, Tuple, Callable
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

ProgressCb = Callable[[str], None] | None


def is_stream_alive(url: str, *, timeout: float = 4.0) -> bool:
    try:
        resp = requests.get(url, headers={'User-Agent': 'JellyfinTvTools/link-check'}, timeout=timeout, stream=True)
        if resp.status_code >= 400:
            return False
        read = 0
        for _ in range(4):
            try:
                chunk = next(resp.iter_content(chunk_size=4096))
            except StopIteration:
                break
            if not chunk:
                break
            read += len(chunk)
            if read >= 1024:
                break
        resp.close(); return read > 0
    except Exception:  # noqa: BLE001
        return False


def remove_dead_streams(channels: List[Dict[str, Any]], *, progress_callback: ProgressCb = None, max_workers: int = 20) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
    total = len(channels); alive: List[Dict[str, Any]] = []; dead: List[Dict[str, Any]] = []
    def task(ch):
        url = ch.get('lines', [None])[-1]
        if isinstance(url, str) and url and not url.startswith('#'):
            return ch, is_stream_alive(url)
        return ch, False
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(task, ch) for ch in channels]
        for idx, fut in enumerate(as_completed(futures), start=1):
            ch, ok = fut.result()
            (alive if ok else dead).append(ch)
            if progress_callback and idx % 2 == 0:
                progress_callback(f"Link check {idx}/{total} dead:{len(dead)}")
    if progress_callback:
        progress_callback(f"Link check complete – removed {len(dead)} dead streams")
    return alive, len(dead), dead


def remove_unwanted_channels(channels: List[Dict[str, Any]], config: Dict[str, Any], *, progress_callback: ProgressCb = None) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
    if progress_callback:
        progress_callback("Removing unwanted channels...")
    exclude_patterns = config.get('exclude_patterns', [])
    force_exclude = set(config.get('force_exclude_channels', []))
    if not exclude_patterns and not force_exclude:
        return channels, 0, []
    wanted: List[Dict[str, Any]] = []; unwanted: List[Dict[str, Any]] = []
    for ch in channels:
        name = ch['name']; should_exclude = False
        if name in force_exclude:
            should_exclude = True
        else:
            for pattern in exclude_patterns:
                try:
                    if re.search(pattern, name, re.IGNORECASE):
                        should_exclude = True; break
                except re.error:
                    continue
        (unwanted if should_exclude else wanted).append(ch)
    removed = len(unwanted)
    if progress_callback:
        progress_callback(f"Unwanted channels removed: {removed} filtered out")
    return wanted, removed, unwanted
