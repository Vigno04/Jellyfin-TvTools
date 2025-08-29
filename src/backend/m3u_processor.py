#!/usr/bin/env python3
"""
M3U Processing Backend for Jellyfin TV Tools
Handles downloading, filtering, and quality management of M3U playlists
"""

import re
import os
from typing import List, Dict, Any, Tuple

try:
    import requests
except ImportError:
    print("Installing requests library...")
    os.system("pip install requests")
    import requests


try:  # Support package import (backend.m3u_processor) and legacy direct import
    from .config_manager import load_config, get_default_config  # type: ignore
    from .quality_manager import QualityManager  # type: ignore
    from .stream_quality_checker import StreamQualityChecker  # type: ignore
except ImportError:  # Fallback if imported with backend path directly on sys.path
    from config_manager import load_config, get_default_config  # type: ignore
    from quality_manager import QualityManager  # type: ignore
    from stream_quality_checker import StreamQualityChecker  # type: ignore


class M3UProcessor:
    """Main class for processing M3U playlists with filtering and quality management."""

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "..", "config.json")
        self.config = load_config(self.config_path)

    # --- quality management (delegated) ---------------------------------
    def apply_quality_management(self, channels: List[Dict], quality_config: Dict) -> List[Dict]:
        manager = QualityManager(quality_config)
        merged, _removed = manager.merge(channels)
        return merged

    # --- post-download quality merging (enhanced) -----------------------
    def merge_quality(self, channels: List[Dict], progress_callback=None) -> Tuple[List[Dict], int]:
        """Merge duplicate channels based on name + probed stream metrics.

        Strategy:
          1. Group channels by base name (using QualityManager logic with current config)
          2. For groups with >1 channel: probe each URL (HLS master parsing) – network light
          3. Compute score = (bitrate_kbps * codec_weight - latency_penalty)
          4. Sort by (quality suffix priority, -score) and keep top; carry over selected if ANY was selected
        """
        quality_cfg = dict(self.config.get("quality_management", {}))
        quality_cfg.setdefault("use_name_based_quality", True)
        qm = QualityManager(quality_cfg)
        checker = StreamQualityChecker(
            use_cache=quality_cfg.get("use_stream_quality_cache", False),
            cache_ttl=quality_cfg.get("stream_quality_cache_ttl", 3600),
            max_probe_bytes=quality_cfg.get("max_stream_probe_bytes", 16384),
            use_range=quality_cfg.get("use_range_header", False),
        )

        # Build groups (case-insensitive grouping)
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for ch in channels:
            base = qm.base_channel_name(ch["name"])
            ch["_base_name"] = base
            # Group by lowercase base name for case-insensitive merging
            group_key = base.lower()
            groups.setdefault(group_key, []).append(ch)

        total_groups = sum(1 for g in groups.values() if len(g) > 1)
        done_groups = 0
        merged: List[Dict] = []
        removed_count = 0

        # Pre-collect work items for groups >1 for parallel probing
        multi_groups = {b: g for b, g in groups.items() if len(g) > 1}
        single_groups = {b: g for b, g in groups.items() if len(g) == 1}

        # Handle singles quickly
        for base, group in single_groups.items():
            ch = group[0]
            if quality_cfg.get("normalize_channel_names", True) and ch["name"] != base:
                ch["name"] = base
                ch["lines"][0] = re.sub(r",([^,]+)$", f",{base}", ch["lines"][0])
            merged.append(ch)

        # Parallel probe duplicates
        from concurrent.futures import ThreadPoolExecutor, as_completed
        work = []
        max_workers = int(quality_cfg.get("max_parallel_stream_probes", 12) or 1)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            # Intra-run dedup: if multiple variants share identical URL, probe once
            url_future: dict[str, Any] = {}
            for base, group in multi_groups.items():
                for ch in group:
                    url = ch["lines"][-1]
                    fut = url_future.get(url)
                    if fut is None:
                        fut = ex.submit(checker.analyze, url, None)
                        url_future[url] = fut
                    work.append((base, ch, fut))
            completed = 0
            total_futs = len(work)
            for base, ch, fut in work:
                metrics = fut.result().as_dict()
                ch["quality_metrics"] = metrics
                ch["_quality_score"] = metrics.get("score") or 0
                ch["_priority_index"] = qm.quality_priority(ch["name"])
                completed += 1
                if progress_callback and completed % 3 == 0:
                    progress_callback(f"Quality probing {completed}/{total_futs} variants")

        # Now choose best per multi group
        for group_key, group in multi_groups.items():
            # Choose sorting strategy based on configuration
            if quality_cfg.get("prioritize_stream_analysis", True):
                # Prioritize actual stream quality score over name-based suffixes
                # Only fall back to name priority if stream analysis fails (score is 0)
                group.sort(key=lambda c: (-c["_quality_score"], c["_priority_index"]))
            else:
                # Traditional approach: name-based quality suffixes first, then stream analysis
                group.sort(key=lambda c: (c["_priority_index"], -c["_quality_score"]))
            best = group[0]
            try:
                # Use the original base name (with original casing) of the best channel for logging
                best_base = best["_base_name"]
                print(f"[QUALITY] Group '{best_base}' ({len(group)} variants)")
                for cand in group:
                    m = cand.get("quality_metrics", {})
                    latency = m.get('response_ms')
                    latency_str = f"{latency:.1f}" if latency is not None else 'n/a'
                    print(
                        f"  - name='{cand['name']}' pri={cand['_priority_index']} "
                        f"score={cand.get('_quality_score'):.2f} bitrate={m.get('bitrate_kbps')}kbps "
                        f"codec={m.get('codec')} latency_ms={latency_str}"
                    )
                print(f"  => chosen: {best['name']}")
            except Exception:
                pass
            if any(c.get("selected") for c in group):
                best["selected"] = True
            
            # Merge attributes from all variants - if best channel is missing an attribute,
            # take it from the next best variant that has it
            self._merge_channel_attributes(best, group)
            
            # Preserve the original name of the best channel (don't normalize to base)
            # This way "Focus" and "FOCUS" will merge, but keep whichever one was chosen as best
            merged.append(best)
            removed_count += len(group) - 1

        if progress_callback:
            progress_callback(f"Quality merge complete – removed {removed_count} duplicates")

        for ch in merged:
            for k in ["_base_name", "_quality_score", "_priority_index"]:
                if k in ch:
                    del ch[k]
        return merged, removed_count

    def _merge_channel_attributes(self, best_channel: Dict, all_variants: List[Dict]):
        """Merge attributes from all channel variants into the best channel.
        
        If the best channel is missing an attribute (empty or None), 
        it will be filled from the next best variant that has that attribute.
        """
        # List of attributes that can be merged from other variants
        mergeable_attributes = [
            "tvg_logo", "tvg_id", "tvg_name", "tvg_chno", "channel_id"
        ]
        
        for attr in mergeable_attributes:
            # If best channel doesn't have this attribute or it's empty
            if not best_channel.get(attr):
                # Try to find it in other variants (they're already sorted by quality)
                for variant in all_variants[1:]:  # Skip first one (that's the best)
                    if variant.get(attr):
                        best_channel[attr] = variant[attr]
                        break
    
    def download_m3u(self, url: str = None, progress_callback=None) -> Tuple[bool, List[str], str]:
        """
        Download M3U playlist from URL
        Returns: (success, lines, error_message)
        """
        url = url or self.config["download_url"]
        
        try:
            if progress_callback:
                progress_callback("Downloading M3U playlist...")
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            
            if progress_callback:
                progress_callback("Download completed successfully!")
            
            return True, lines, ""
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            if progress_callback:
                progress_callback(error_msg)
            return False, [], error_msg
    
    def parse_channels(self, lines: List[str], progress_callback=None) -> List[Dict]:
        """
        Parse M3U lines into channel objects
        Returns list of channel dictionaries
        """
        if progress_callback:
            progress_callback("Parsing channels...")
        
        channels = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Process channels
            if line.startswith('#EXTINF:'):
                # Extract channel info
                group_match = re.search(r'group-title="([^"]*)"', line)
                group_title = group_match.group(1) if group_match else ""
                
                name_match = re.search(r',([^,]+)$', line)
                channel_name = name_match.group(1).strip() if name_match else ""
                
                # Skip section headers and placeholders
                if ('=== ' in channel_name or 
                    'LAST UPDATE' in channel_name or 
                    channel_name.startswith('---')):
                    # Skip this section header and its URL
                    i += 2
                    continue
                
                # Extract all available attributes from EXTINF line
                tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
                tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
                tvg_chno_match = re.search(r'tvg-chno="([^"]*)"', line)
                channel_id_match = re.search(r'channel-id="([^"]*)"', line)
                
                # Collect all lines for this channel (EXTINF + options + URL)
                channel_lines = [lines[i]]  # Start with EXTINF line
                j = i + 1
                
                # Add any EXTVLCOPT lines
                while j < len(lines) and lines[j].strip().startswith('#EXTVLCOPT:'):
                    channel_lines.append(lines[j])
                    j += 1
                
                # Add the URL line
                if j < len(lines) and not lines[j].strip().startswith('#'):
                    channel_lines.append(lines[j])
                    j += 1
                
                # Create channel object with all attributes
                channel = {
                    "name": channel_name,
                    "group": group_title,
                    "lines": channel_lines,
                    "selected": False,  # Default selection state for UI
                    # Additional M3U attributes
                    "tvg_logo": tvg_logo_match.group(1) if tvg_logo_match else "",
                    "tvg_id": tvg_id_match.group(1) if tvg_id_match else "",
                    "tvg_name": tvg_name_match.group(1) if tvg_name_match else "",
                    "tvg_chno": tvg_chno_match.group(1) if tvg_chno_match else "",
                    "channel_id": channel_id_match.group(1) if channel_id_match else "",
                }
                
                channels.append(channel)
                
                i = j
            else:
                i += 1
        
        if progress_callback:
            progress_callback(f"Parsed {len(channels)} channels")
        
        return channels
    
    def filter_channels(self, channels: List[Dict], progress_callback=None, quality_config_override: Dict = None) -> List[Dict]:
        """
        Apply filtering rules to channels based on config
        Returns filtered list of channels
        """
        if progress_callback:
            progress_callback("Applying filters...")
        
        # Short-circuit: if auto selection disabled, return empty (no preselected)
        if not self.config.get("auto_select_enabled", True):
            if progress_callback:
                progress_callback("Auto selection disabled: 0 preselected")
            return []

        # Get settings from config
        keep_groups = set(self.config["keep_groups"])
        exclude_groups = set(self.config["exclude_groups"])
        force_keep = set(self.config["force_keep_channels"])
        force_exclude = set(self.config["force_exclude_channels"])
        exclude_patterns = self.config["exclude_patterns"]
        
        filtered_channels = []
        
        for channel in channels:
            channel_name = channel["name"]
            group_title = channel["group"]
            
            # Decide if we keep this channel
            keep = False
            
            # Force exclude takes precedence
            if channel_name in force_exclude:
                keep = False
            # Force keep takes precedence over other rules
            elif channel_name in force_keep:
                keep = True
            # Check if group is excluded
            elif group_title in exclude_groups:
                keep = False
            # Check if group is allowed
            elif group_title in keep_groups:
                keep = True
                # But exclude if matches exclude patterns
                for pattern in exclude_patterns:
                    if re.search(pattern, channel_name, re.IGNORECASE):
                        keep = False
                        break
            
            if keep:
                filtered_channels.append(channel)
        
        # Apply quality management
        quality_config = quality_config_override or self.config.get("quality_management", {})
        if quality_config.get("use_name_based_quality", False):
            filtered_channels = self.apply_quality_management(filtered_channels, quality_config)
        
        if progress_callback:
            progress_callback(f"Filtering complete: {len(filtered_channels)} channels kept")
        
        return filtered_channels
    
    def export_m3u(self, channels: List[Dict], output_path: str = None, progress_callback=None) -> Tuple[bool, str]:
        """
        Export selected channels to M3U file
        Returns: (success, message)
        """
        try:
            if progress_callback:
                progress_callback("Exporting M3U playlist...")
            
            # Filter only selected channels
            selected_channels = [ch for ch in channels if ch.get("selected", False)]
            
            if not selected_channels:
                return False, "No channels selected for export"
            
            # Prepare output path
            if not output_path:
                output_path = os.path.join(os.path.dirname(self.config_path), "..", "data", "tivustream_list.m3u")
            
            # Prepare final output
            filtered_lines = ['#EXTM3U']
            for channel in selected_channels:
                # Reconstruct EXTINF line with all attributes
                extinf_line = "#EXTINF:-1"
                
                # Add attributes if they exist
                if channel.get("channel_id"):
                    extinf_line += f' channel-id="{channel["channel_id"]}"'
                if channel.get("tvg_id"):
                    extinf_line += f' tvg-id="{channel["tvg_id"]}"'
                if channel.get("tvg_chno"):
                    extinf_line += f' tvg-chno="{channel["tvg_chno"]}"'
                if channel.get("tvg_name"):
                    extinf_line += f' tvg-name="{channel["tvg_name"]}"'
                if channel.get("tvg_logo"):
                    extinf_line += f' tvg-logo="{channel["tvg_logo"]}"'
                if channel.get("group"):
                    extinf_line += f' group-title="{channel["group"]}"'
                
                # Add channel name at the end
                extinf_line += f',{channel["name"]}'
                
                # Add the reconstructed EXTINF line
                filtered_lines.append(extinf_line)
                
                # Add EXTVLCOPT lines if they exist in the original lines
                for line in channel["lines"]:
                    if line.startswith('#EXTVLCOPT:'):
                        filtered_lines.append(line)
                
                # Add the URL (last line that doesn't start with #)
                for line in reversed(channel["lines"]):
                    if not line.startswith('#'):
                        filtered_lines.append(line)
                        break
            
            # Save filtered playlist
            with open(output_path, 'w', encoding='utf-8') as f:
                for line in filtered_lines:
                    f.write(line + '\n')
            
            success_msg = f"Successfully exported {len(selected_channels)} channels to {os.path.basename(output_path)}"
            if progress_callback:
                progress_callback(success_msg)
            
            return True, success_msg
            
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            if progress_callback:
                progress_callback(error_msg)
            return False, error_msg
    
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

    # --- dead link checking -------------------------------------------------
    def _is_stream_alive(self, url: str, timeout: float = 4.0) -> bool:
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
            resp.close()
            return read > 0
        except Exception:
            return False

    def remove_dead_streams(self, channels: List[Dict], progress_callback=None) -> Tuple[List[Dict], int, List[Dict]]:
        total = len(channels)
        alive: List[Dict] = []
        dead: List[Dict] = []
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def task(ch):
            url = ch.get('lines', [None])[-1]
            if isinstance(url, str) and url and not url.startswith('#'):
                return ch, self._is_stream_alive(url)
            return ch, False
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(task, ch) for ch in channels]
            for idx, fut in enumerate(as_completed(futures), start=1):
                ch, ok = fut.result()
                if ok:
                    alive.append(ch)
                else:
                    dead.append(ch)
                if progress_callback and idx % 2 == 0:
                    progress_callback(f"Link check {idx}/{total} dead:{len(dead)}")
        if progress_callback:
            progress_callback(f"Link check complete – removed {len(dead)} dead streams")
        try:
            if dead:
                print("[DEAD] Removed dead streams:\n" + "\n".join(f"  - {c['name']}" for c in dead))
        except Exception:
            pass
        return alive, len(dead), dead

    def remove_unwanted_channels(self, channels: List[Dict], progress_callback=None) -> Tuple[List[Dict], int, List[Dict]]:
        """Remove channels matching unwanted patterns like test, backup, etc."""
        if progress_callback:
            progress_callback("Removing unwanted channels...")
        
        exclude_patterns = self.config.get("exclude_patterns", [])
        force_exclude = set(self.config.get("force_exclude_channels", []))
        
        if not exclude_patterns and not force_exclude:
            return channels, 0, []
        
        import re
        wanted: List[Dict] = []
        unwanted: List[Dict] = []
        
        for ch in channels:
            channel_name = ch["name"]
            should_exclude = False
            
            # Check force exclude list
            if channel_name in force_exclude:
                should_exclude = True
            else:
                # Check exclude patterns
                for pattern in exclude_patterns:
                    try:
                        if re.search(pattern, channel_name, re.IGNORECASE):
                            should_exclude = True
                            break
                    except re.error:
                        continue  # Skip invalid regex patterns
            
            if should_exclude:
                unwanted.append(ch)
            else:
                wanted.append(ch)
        
        removed_count = len(unwanted)
        
        if progress_callback:
            progress_callback(f"Unwanted channels removed: {removed_count} filtered out")
        
        # Debug output
        try:
            if unwanted:
                print(f"[UNWANTED] Removed {removed_count} unwanted channels:\n" + 
                      "\n".join(f"  - {c['name']}" for c in unwanted[:10]))  # Show first 10
                if len(unwanted) > 10:
                    print(f"  ... and {len(unwanted) - 10} more")
        except Exception:
            pass
            
        return wanted, removed_count, unwanted
