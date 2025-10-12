#!/usr/bin/env python3
"""Debug test for channel merging to understand the 'G' issue"""

import sys
sys.path.insert(0, 'src')

from backend.quality_manager import QualityManager

# Simula la configurazione
config = {
    "use_name_based_quality": True,
    "normalize_channel_names": True,
    "exclude_lower_quality": True,
    "quality_suffixes": ["HD", "FHD", "UHD", "4K", "8K", "SD"],
    "priority_order": ["4K", "FHD", "1080p", "HD", "720p", "SD"],
    "alias_rules": [],
    "normalization_exclusions": []
}

qm = QualityManager(config)

# Test vari nomi che potrebbero causare problemi
test_channels = [
    {"name": "Tv8", "url": "http://test1.com", "lines": ["#EXTINF:-1,Tv8", "http://test1.com"]},
    {"name": "Tv8©", "url": "http://test2.com", "lines": ["#EXTINF:-1,Tv8©", "http://test2.com"]},
    {"name": "Tv8 (720p)", "url": "http://test3.com", "lines": ["#EXTINF:-1,Tv8 (720p)", "http://test3.com"]},
    {"name": "TV8 HD", "url": "http://test4.com", "lines": ["#EXTINF:-1,TV8 HD", "http://test4.com"]},
    {"name": "Tv8 G", "url": "http://test5.com", "lines": ["#EXTINF:-1,Tv8 G", "http://test5.com"]},
    {"name": "Rai 1", "url": "http://test6.com", "lines": ["#EXTINF:-1,Rai 1", "http://test6.com"]},
    {"name": "Rai 1 HD", "url": "http://test7.com", "lines": ["#EXTINF:-1,Rai 1 HD", "http://test7.com"]},
]

print("=" * 70)
print("BEFORE MERGE:")
print("=" * 70)
for i, ch in enumerate(test_channels, 1):
    base = qm.base_channel_name(ch["name"])
    print(f"{i}. '{ch['name']}' → base: '{base}'")
    # Check for hidden characters
    print(f"   Raw bytes: {ch['name'].encode('utf-8')}")
    print(f"   Base bytes: {base.encode('utf-8')}")
    print()

print("=" * 70)
print("AFTER MERGE:")
print("=" * 70)
merged, removed = qm.merge(test_channels)
print(f"Removed: {removed}")
print(f"Remaining: {len(merged)}")
print()
for i, ch in enumerate(merged, 1):
    print(f"{i}. Name: '{ch['name']}'")
    print(f"   Raw bytes: {ch['name'].encode('utf-8')}")
    print(f"   EXTINF: {ch['lines'][0]}")
    print()
