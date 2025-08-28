#!/usr/bin/env python3
"""
Simple M3U Downloader and Filter - Fixed Version
"""

import re
import os
import json

try:
    import requests
except ImportError:
    print("Installing requests library...")
    os.system("pip install requests")
    import requests

def load_config():
    """Load configuration from JSON file"""
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.loads(f.read().strip())
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def get_base_channel_name(channel_name, quality_suffixes):
    """Extract base channel name by removing quality suffixes"""
    name = channel_name.strip()
    for suffix in quality_suffixes:
        # Remove suffix with space or at end
        if name.endswith(f" {suffix}"):
            name = name[:-len(f" {suffix}")].strip()
        elif name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    return name

def get_quality_priority(channel_name, priority_order):
    """Get priority level for a channel based on quality suffix"""
    name = channel_name.strip()
    for i, quality in enumerate(priority_order):
        if name.endswith(f" {quality}") or name.endswith(quality):
            return i  # Lower number = higher priority
    return len(priority_order)  # Standard quality has lowest priority

def apply_quality_management(channels, quality_config):
    """Apply quality management to filter and rename channels"""
    if not quality_config.get("enable_quality_priority", False):
        return channels
    
    quality_suffixes = quality_config.get("quality_suffixes", [])
    priority_order = quality_config.get("priority_order", [])
    exclude_lower = quality_config.get("exclude_lower_quality", True)
    normalize_names = quality_config.get("normalize_channel_names", True)
    
    # Group channels by base name
    channel_groups = {}
    for channel_data in channels:
        channel_name = channel_data["name"]
        base_name = get_base_channel_name(channel_name, quality_suffixes)
        
        if base_name not in channel_groups:
            channel_groups[base_name] = []
        
        priority = get_quality_priority(channel_name, priority_order)
        channel_groups[base_name].append((priority, channel_data))
    
    # Process each group
    result_channels = []
    for base_name, group in channel_groups.items():
        # Sort by priority (lower number = higher priority)
        group.sort(key=lambda x: x[0])
        
        if exclude_lower and len(group) > 1:
            # Keep only the highest quality version
            best_channel = group[0][1]
            if normalize_names:
                # Rename to base name for EPG compatibility
                best_channel["name"] = base_name
                # Update the EXTINF line
                extinf_line = best_channel["lines"][0]
                extinf_line = re.sub(r',([^,]+)$', f',{base_name}', extinf_line)
                best_channel["lines"][0] = extinf_line
            result_channels.append(best_channel)
        else:
            # Keep all versions
            for _, channel_data in group:
                result_channels.append(channel_data)
    
    return result_channels

def download_and_filter_m3u():
    """Download and filter M3U playlist"""
    
    config = load_config()
    if not config:
        print("Failed to load configuration")
        return
    
    print("=" * 50)
    print("M3U DOWNLOADER AND FILTER - WITH QUALITY MANAGEMENT")
    print("=" * 50)
    
    # Get settings from config
    download_url = config["download_url"]
    keep_groups = set(config["keep_groups"])
    exclude_groups = set(config["exclude_groups"])
    force_keep = set(config["force_keep_channels"])
    force_exclude = set(config["force_exclude_channels"])
    exclude_patterns = config["exclude_patterns"]
    quality_config = config.get("quality_management", {})
    
    try:
        # Download
        print("\n1. Downloading latest M3U...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(download_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        print("✓ Downloaded successfully")
        
        # Filter
        print("\n2. Filtering channels...")
        kept_channels = []
        i = 0
        excluded_count = 0
        
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
                    kept_channels.append({
                        "name": channel_name,
                        "group": group_title,
                        "lines": channel_lines
                    })
                else:
                    excluded_count += 1
                
                i = j
            else:
                i += 1
        
        # Apply quality management
        print("\n3. Applying quality management...")
        if quality_config.get("enable_quality_priority", False):
            original_count = len(kept_channels)
            kept_channels = apply_quality_management(kept_channels, quality_config)
            quality_optimized = original_count - len(kept_channels)
            print(f"✓ Quality optimization removed {quality_optimized} duplicate/lower quality channels")
        
        # Prepare final output
        print("\n4. Preparing final output...")
        filtered_lines = ['#EXTM3U']
        
        for channel in kept_channels:
            filtered_lines.extend(channel["lines"])
        
        # Clean folder and save
        print("\n5. Cleaning folder and saving...")
        tv_folder = os.path.dirname(os.path.abspath(__file__))
        
        # Remove old files
        for filename in ['tivustream_list.m3u', 'source_check.m3u', 'debug_m3u.py']:
            filepath = os.path.join(tv_folder, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"  ✓ Removed: {filename}")
                except:
                    pass
        
        # Save filtered playlist
        final_path = os.path.join(tv_folder, "tivustream_list.m3u")
        with open(final_path, 'w', encoding='utf-8') as f:
            for line in filtered_lines:
                f.write(line + '\n')
        
        print(f"\n{'='*50}")
        print("SUCCESS!")
        print(f"{'='*50}")
        print(f"Channels kept: {len(kept_channels)}")
        print(f"Channels excluded: {excluded_count}")
        if quality_config.get("enable_quality_priority", False):
            print("✓ Quality management enabled")
        print(f"Final file: tivustream_list.m3u")
        print("Ready for Jellyfin!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_and_filter_m3u()
