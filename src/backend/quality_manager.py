#!/usr/bin/env python3
"""Quality management (merging / prioritization) utilities for M3U channels."""
from __future__ import annotations
import re
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
        self.normalization_exclusions: List[str] = self.config.get("normalization_exclusions", [])    # ---------------- basic helpers -----------------
    def base_channel_name(self, channel_name: str) -> str:
        name = channel_name.strip()
        
        # Check if this channel is in the normalization exclusion list (case-insensitive)
        for exclusion in self.normalization_exclusions:
            if name.lower() == exclusion.lower():
                return name  # Return original name without any normalization
        
        # Apply alias normalization first (case-insensitive)
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
        # Remove quality suffixes (case-insensitive matching, preserve original case)
        for suffix in self.quality_suffixes:
            for pattern in (f" {suffix}", suffix):
                # Case-insensitive check but preserve original casing
                if name.lower().endswith(pattern.lower()):
                    name = name[: -len(pattern)].strip()
                    break
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
        for ch in channels:
            base = self.base_channel_name(ch["name"])
            groups.setdefault(base, []).append((self.quality_priority(ch["name"]), ch))
        result: List[Channel] = []
        removed = 0
        for base, group in groups.items():
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
