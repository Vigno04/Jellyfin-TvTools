#!/usr/bin/env python3
"""Dead stream / unwanted channel operations extracted."""
from __future__ import annotations

from typing import List, Dict, Any, Tuple, Callable
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

ProgressCb = Callable[[str], None] | None


def is_stream_alive(url: str, *, timeout: float = 8.0) -> bool:
    """Check if a stream URL is alive by attempting to fetch initial data.
    
    Args:
        url: The stream URL to check
        timeout: Request timeout in seconds (default: 8.0)
    
    Returns:
        True if stream appears to be alive, False otherwise
    """
    try:
        # Use a more compatible User-Agent (VLC is widely accepted by IPTV providers)
        headers = {
            'User-Agent': 'VLC/3.0.18 LibVLC/3.0.18',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        
        resp = requests.get(
            url, 
            headers=headers, 
            timeout=timeout, 
            stream=True,
            allow_redirects=True  # Explicitly allow redirects
        )
        
        # Accept 2xx and 3xx status codes (successful and redirect responses)
        if resp.status_code >= 400:
            return False
        
        # Try to read some data to verify the stream is actually working
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
        
        resp.close()
        
        # Stream is alive if we got a good status code and could read some data
        return read > 0
    except requests.exceptions.Timeout:
        # Timeout doesn't necessarily mean dead - could be slow network
        return False
    except requests.exceptions.ConnectionError:
        # Connection errors typically indicate dead stream
        return False
    except Exception:  # noqa: BLE001
        # For other exceptions, consider dead to be safe
        return False


def remove_dead_streams(channels: List[Dict[str, Any]], *, progress_callback: ProgressCb = None, max_workers: int = 20) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
    """Remove channels with dead/unreachable stream URLs.
    
    Args:
        channels: List of channel dictionaries
        progress_callback: Optional callback for progress updates
        max_workers: Maximum number of concurrent checks
    
    Returns:
        Tuple of (alive_channels, dead_count, dead_channels)
    """
    total = len(channels)
    alive: List[Dict[str, Any]] = []
    dead: List[Dict[str, Any]] = []
    
    def task(ch):
        """Check if a channel's stream is alive."""
        url = ch.get('lines', [None])[-1]
        
        # If no valid URL, keep the channel (don't mark as dead)
        if not isinstance(url, str) or not url or url.startswith('#'):
            return ch, True  # Changed from False to True - keep channels without valid URLs
        
        # Check if the stream URL is alive
        return ch, is_stream_alive(url)
    
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


def remove_unwanted_channels(
    channels: List[Dict[str, Any]], 
    config: Dict[str, Any], 
    *, 
    progress_callback: ProgressCb = None
) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
    """Remove channels matching unwanted patterns or in exclusion list.
    
    Args:
        channels: List of channel dictionaries
        config: Configuration dictionary with exclude_patterns and force_exclude_channels
        progress_callback: Optional callback for progress updates
    
    Returns:
        Tuple of (wanted_channels, removed_count, unwanted_channels)
    """
    if progress_callback:
        progress_callback("Removing unwanted channels...")
    
    exclude_patterns = config.get('exclude_patterns', [])
    force_exclude = set(config.get('force_exclude_channels', []))
    
    if not exclude_patterns and not force_exclude:
        return channels, 0, []
    
    wanted: List[Dict[str, Any]] = []
    unwanted: List[Dict[str, Any]] = []
    
    for ch in channels:
        name = ch['name']
        should_exclude = False
        
        # Check force exclusion list first
        if name in force_exclude:
            should_exclude = True
        else:
            # Check regex patterns
            for pattern in exclude_patterns:
                try:
                    if re.search(pattern, name, re.IGNORECASE):
                        should_exclude = True
                        break
                except re.error:
                    # Skip invalid regex patterns
                    continue
        
        if should_exclude:
            unwanted.append(ch)
        else:
            wanted.append(ch)
    
    removed = len(unwanted)
    
    if progress_callback:
        progress_callback(f"Unwanted channels removed: {removed} filtered out")
    
    return wanted, removed, unwanted
