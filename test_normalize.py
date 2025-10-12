#!/usr/bin/env python3
"""Test script to verify channel name normalization."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from backend.quality_manager import QualityManager

# Configurazione di test
config = {
    "quality_suffixes": ["4K", "UHD", "HD", "HQ", "FHD"],
    "priority_order": ["4K", "UHD", "HD", "HQ"],
    "normalize_channel_names": True,
    "normalization_exclusions": [],
    "alias_rules": []
}

qm = QualityManager(config)

# Test cases
test_cases = [
    "Tv8",
    "Tv8©",
    "TV8 (720p)",
    "TV8 (1080p)",
    "Pluto TV Reality",
    "Pluto TV Reality Italy",
    "Pluto TV Reality Italian",
    "Pluto TV Reality ITA",
    "Discovery Channel [24/7]",
    "Discovery Channel (HD)",
    "Rai 1 HD",
    "Rai 1 FHD",
    "Rai 1 4K",
    "National Geographic (1080p) [24/7]",
    "Sky Sport® HD",
]

print("=" * 70)
print("CHANNEL NORMALIZATION TEST")
print("=" * 70)
print()

for original in test_cases:
    normalized = qm.base_channel_name(original)
    print(f"'{original}'")
    print(f"  → '{normalized}'")
    print()

print("=" * 70)
print("\nGrouping Test (channels that should merge):")
print("=" * 70)
print()

# Group by normalized name
groups = {}
for name in test_cases:
    base = qm.base_channel_name(name)
    if base not in groups:
        groups[base] = []
    groups[base].append(name)

for base, variants in groups.items():
    if len(variants) > 1:
        print(f"Group: '{base}'")
        for v in variants:
            print(f"  - {v}")
        print()
