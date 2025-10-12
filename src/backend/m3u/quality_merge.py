#!/usr/bin/env python3
"""Advanced quality merge logic extracted for readability."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Tuple

from ..quality_manager import QualityManager
from ..stream_quality_checker import StreamQualityChecker

ProgressCb = Callable[[str], None] | None


def merge_quality(
    channels: List[Dict[str, Any]],
    quality_cfg: Dict[str, Any],
    *,
    progress_callback: ProgressCb = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Merge duplicate channels by quality, keeping the best variant."""
    quality_cfg = dict(quality_cfg or {})
    quality_cfg.setdefault("use_name_based_quality", True)
    qm = QualityManager(quality_cfg)
    checker = StreamQualityChecker(
        use_cache=quality_cfg.get("use_stream_quality_cache", False),
        cache_ttl=quality_cfg.get("stream_quality_cache_ttl", 3600),
        max_probe_bytes=quality_cfg.get("max_stream_probe_bytes", 16384),
        use_range=quality_cfg.get("use_range_header", False),
    )
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for ch in channels:
        base = qm.base_channel_name(ch["name"])
        ch["_base_name"] = base
        groups.setdefault(base.lower(), []).append(ch)
    merged: List[Dict[str, Any]] = []
    removed_count = 0
    multi_groups = {k: g for k, g in groups.items() if len(g) > 1}
    single_groups = {k: g for k, g in groups.items() if len(g) == 1}
    for _, group in single_groups.items():
        ch = group[0]
        if (
            quality_cfg.get("normalize_channel_names", True)
            and ch["name"] != ch["_base_name"]
        ):
            ch["name"] = ch["_base_name"]
            ch["lines"][0] = re.sub(r",([^,]+)$", f',{ch["name"]}', ch["lines"][0])
        merged.append(ch)
    work = []
    max_workers = int(quality_cfg.get("max_parallel_stream_probes", 12) or 1)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
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
    for _, group in multi_groups.items():
        if quality_cfg.get("prioritize_stream_analysis", True):
            group.sort(key=lambda c: (-c["_quality_score"], c["_priority_index"]))
        else:
            group.sort(key=lambda c: (c["_priority_index"], -c["_quality_score"]))
        best = group[0]
        if any(c.get("selected") for c in group):
            best["selected"] = True
        _merge_channel_attributes(best, group)
        merged.append(best)
        removed_count += len(group) - 1
    if progress_callback:
        progress_callback(f"Quality merge complete – removed {removed_count} duplicates")
    for ch in merged:
        for k in ["_base_name", "_quality_score", "_priority_index"]:
            ch.pop(k, None)
    return merged, removed_count


def _merge_channel_attributes(
    best_channel: Dict[str, Any], all_variants: List[Dict[str, Any]]
):
    """Merge missing attributes from other variants into the best channel."""
    mergeable = ["tvg_logo", "tvg_id", "tvg_name", "tvg_chno", "channel_id"]
    for attr in mergeable:
        if not best_channel.get(attr):
            for variant in all_variants[1:]:
                if variant.get(attr):
                    best_channel[attr] = variant[attr]
                    break
