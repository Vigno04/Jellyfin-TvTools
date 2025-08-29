#!/usr/bin/env python3
"""Light‑weight stream quality probing utilities.

We intentionally avoid heavy dependencies (ffprobe/ffmpeg) and derive an
approximate quality score using:
  * Name based priority (handled in QualityManager / caller)
  * For HLS master playlists: BANDWIDTH + CODECS attributes
  * Simple codec efficiency weighting (AV1 > HEVC > VP9 > H264 > MPEG2)
  * Response latency (ms) as a negative factor

If probing fails we still return a metrics dict (with None values) so the
caller can fall back to name priority only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
import re

import requests
import threading
import time as _time

# (Legacy) module-level defaults retained for backward compatibility
_DEFAULT_CACHE_TTL = 3600

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) JellyfinTvTools/quality-probe'


@dataclass
class StreamMetrics:
    url: str
    response_ms: float | None = None
    bitrate_kbps: float | None = None
    codec: str | None = None
    codec_weight: float = 1.0
    score: float | None = None  # final computed score (excluding name priority)
    error: str | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'response_ms': self.response_ms,
            'bitrate_kbps': self.bitrate_kbps,
            'codec': self.codec,
            'codec_weight': self.codec_weight,
            'score': self.score,
            'error': self.error,
        }


CODEC_WEIGHTS = [
    (re.compile(r'av01', re.I), 1.18, 'AV1'),
    (re.compile(r'vp09|vp9', re.I), 1.12, 'VP9'),
    (re.compile(r'hevc|h265|hev1|hvc1', re.I), 1.12, 'HEVC'),
    (re.compile(r'avc|h264', re.I), 1.0, 'H264'),
    (re.compile(r'mpeg2', re.I), 0.85, 'MPEG2'),
]


class StreamQualityChecker:
    """Fetch limited data to estimate stream quality.

    Design choices:
      * Short timeouts (default 5s) so UI remains responsive.
      * Never raises – returns metrics with error field set.
    """

    def __init__(self, timeout: float = 5.0, *, use_cache: bool = True, cache_ttl: int | float = _DEFAULT_CACHE_TTL,
                 max_probe_bytes: int = 32768, use_range: bool = False, session: requests.Session | None = None):
        self.timeout = timeout
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.max_probe_bytes = max_probe_bytes
        self.use_range = use_range
        self._session = session or requests.Session()
        # Lazy-create per-instance cache to avoid cross-run contamination when disabled
        self._cache: dict[str, tuple[float, dict]] = {}
        self._cache_lock = threading.Lock()

    def analyse(self, url: str) -> StreamMetrics:  # British spelling alias acceptable
        return self.analyze(url)

    def analyze(self, url: str, use_cache: bool | None = None) -> StreamMetrics:
        if use_cache is None:
            use_cache = self.use_cache
        # Cache lookup
        if use_cache:
            with self._cache_lock:
                cached = self._cache.get(url)
                if cached and (_time.time() - cached[0]) < self.cache_ttl:
                    data = cached[1]
                    m = StreamMetrics(url=url)
                    for k, v in data.items():
                        setattr(m, k, v)
                    return m
        metrics = StreamMetrics(url=url)
        start = time.perf_counter()
        try:
            # We GET a small portion because some IPTV servers mis-handle HEAD
            headers = {'User-Agent': UA}
            if self.use_range:
                headers['Range'] = f'bytes=0-{self.max_probe_bytes - 1}'
            resp = self._session.get(url, headers=headers, timeout=self.timeout, stream=True)
            metrics.response_ms = (time.perf_counter() - start) * 1000
            content_type = resp.headers.get('Content-Type', '')

            # Read only a small chunk / first 32KB
            first_bytes = b''
            # Read up to max_probe_bytes in chunks
            remaining = self.max_probe_bytes
            while remaining > 0:
                try:
                    chunk = next(resp.iter_content(chunk_size=min(8192, remaining)))
                except StopIteration:
                    break
                if not chunk:
                    break
                first_bytes += chunk
                remaining -= len(chunk)
                if len(first_bytes) >= self.max_probe_bytes:
                    break
            resp.close()

            text_sample = None
            if b'EXTM3U' in first_bytes[:20] or url.lower().endswith('.m3u8') or 'mpegurl' in content_type.lower():
                # Treat as (part of) an HLS playlist – attempt to parse values
                try:
                    # If we only got partial file we still parse what we have
                    text_sample = first_bytes.decode('utf-8', errors='ignore')
                except Exception:  # noqa: BLE001
                    text_sample = ''

            if text_sample:
                bitrate, codec = self._parse_hls_master(text_sample)
                metrics.bitrate_kbps = bitrate
                metrics.codec = codec
            # Determine codec weight
            if metrics.codec:
                for pattern, weight, canonical in CODEC_WEIGHTS:
                    if pattern.search(metrics.codec):
                        metrics.codec_weight = weight
                        metrics.codec = canonical
                        break
            # Compute score – prefer higher bitrate * codec weight, penalise latency a bit
            if metrics.bitrate_kbps:
                latency_penalty = (metrics.response_ms or 0) * 0.5  # 0.5 points per ms
                metrics.score = metrics.bitrate_kbps * metrics.codec_weight - latency_penalty
            else:
                # Fallback: inverse latency only
                if metrics.response_ms is not None:
                    metrics.score = 100000 / (metrics.response_ms + 50)  # diminishing returns
        except Exception as e:  # noqa: BLE001
            metrics.error = str(e)
        # Store cache
        if use_cache:
            with self._cache_lock:
                self._cache[url] = (_time.time(), metrics.as_dict())
        return metrics

    def _parse_hls_master(self, playlist_text: str) -> tuple[Optional[float], Optional[str]]:
        """Return (best_bitrate_kbps, codec) from HLS #EXT-X-STREAM-INF lines."""
        best_bitrate = None
        best_codec = None
        for line in playlist_text.splitlines():
            if line.startswith('#EXT-X-STREAM-INF:'):
                attrs = line.split(':', 1)[1]
                bw_match = re.search(r'BANDWIDTH=(\d+)', attrs)
                codecs_match = re.search(r'CODECS="([^"]+)"', attrs)
                if bw_match:
                    bw = int(bw_match.group(1)) / 1000.0  # to kbps
                    if best_bitrate is None or bw > best_bitrate:
                        best_bitrate = bw
                        if codecs_match:
                            best_codec = codecs_match.group(1)
        return best_bitrate, best_codec


__all__ = ["StreamQualityChecker", "StreamMetrics"]
