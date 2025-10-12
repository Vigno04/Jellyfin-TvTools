#!/usr/bin/env python3
"""Quality management (merging / prioritization) utilities for M3U channels."""
from __future__ import annotations
import re
import unicodedata
from typing import Dict, List, Tuple, Any

Channel = Dict[str, Any]

class QualityManager:
    """Encapsulates logic related to channel quality merging & normalization."""

    def __init__(self, quality_config: Dict[str, Any]):
        self.config = quality_config or {}
        self.quality_suffixes: List[str] = self.config.get("quality_suffixes", [])
        self.priority_order: List[str] = self.config.get("priority_order", [])
        self.exclude_lower: bool = self.config.get("exclude_lower_quality", True)
        self.normalize_names: bool = self.config.get("normalize_channel_names", True)
        # alias_rules: list of {pattern: <regex>, replace: <string>} applied case-insensitively
        self.alias_rules = self.config.get("alias_rules", [])
        # normalization_exclusions: list of channel names that should not be normalized
        self.normalization_exclusions: List[str] = self.config.get("normalization_exclusions", [])

    # ---------------- basic helpers -----------------
    def base_channel_name(self, channel_name: str) -> str:
        name = channel_name.strip()

        # Check if this channel is in the normalization exclusion list (case-insensitive)
        for exclusion in self.normalization_exclusions:
            if name.lower() == exclusion.lower():
                return name  # Return original name without any normalization

        # Step 1: Normalize Unicode characters and drop special symbols (©, ®, accents)
        name = unicodedata.normalize('NFKD', name)
        name = ''.join(
            c for c in name
            if not unicodedata.combining(c) and (ord(c) < 128 or c.isspace())
        )

        # Step 2: Remove any metadata enclosed in parentheses or brackets
        # Examples: (1080p), [24/7], [Geo block], (Test)
        name = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', ' ', name)

        # Step 3: Apply custom alias normalization rules (case-insensitive)
        try:
            for rule in self.alias_rules:
                pat = rule.get("pattern")
                repl = rule.get("replace", "")
                if not pat:
                    continue
                if re.search(pat, name, re.IGNORECASE):
                    name = re.sub(pat, repl, name, flags=re.IGNORECASE)
        except Exception:
            # Fail safe – never break merging for bad regex
            pass

        # Step 4: Strip quality or technical markers at the beginning or end
        default_quality_tokens = {
            "4K", "8K", "HD", "FHD", "UHD", "SD", "HQ",
            "HDR", "HEVC", "H264", "H265", "H.264", "H.265",
            "1080P", "720P", "2160P", "4320P", "540P", "480P",
            "360P", "240P", "144P", "24/7", "DVR"
        }
        quality_tokens = {q.upper() for q in self.quality_suffixes}
        quality_tokens.update(default_quality_tokens)

        def is_quality_word(word: str) -> bool:
            stripped = re.sub(r'[^A-Za-z0-9/]+', '', word).upper()
            return stripped in quality_tokens

        tokens = [t for t in re.split(r'\s+', name) if t]

        while tokens and is_quality_word(tokens[0]):
            tokens.pop(0)
        while tokens and is_quality_word(tokens[-1]):
            tokens.pop()

        name = " ".join(tokens)

        # Step 5: Collapse stray separators and whitespace
        name = re.sub(r'[\|_/]+', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    def quality_priority(self, channel_name: str) -> int:
        name = channel_name.strip()
        for i, quality in enumerate(self.priority_order):
            if name.endswith(f" {quality}") or name.endswith(quality):
                return i
        return len(self.priority_order)

    # ---------------- public API -----------------
    def merge(self, channels: List[Channel]) -> Tuple[List[Channel], int]:
        """Return merged channels list + count of merged (removed) channels."""
        if not self.config.get("use_name_based_quality", False):
            return channels, 0
        groups: Dict[str, List[Tuple[int, Channel]]] = {}
        base_map: Dict[str, str] = {}  # Lowercase -> original case mapping
        for ch in channels:
            base = self.base_channel_name(ch["name"])
            base_lower = base.lower()
            # Use lowercase for grouping to handle case variations (Tv8 vs TV8)
            if base_lower not in base_map:
                base_map[base_lower] = base  # Remember first case variant
            groups.setdefault(base_lower, []).append((self.quality_priority(ch["name"]), ch))
        result: List[Channel] = []
        removed = 0
        for base_lower, group in groups.items():
            base = base_map[base_lower]  # Get the original case variant
            group.sort(key=lambda x: x[0])  # by priority
            if self.exclude_lower and len(group) > 1:
                best = group[0][1]
                if self.normalize_names:
                    best_name_original = best["name"]
                    best["name"] = base
                    extinf_line = best["lines"][0]
                    best["lines"][0] = re.sub(r",([^,]+)$", f",{base}", extinf_line)
                result.append(best)
                removed += len(group) - 1
            else:
                for _, ch in group:
                    result.append(ch)
        return result, removed
