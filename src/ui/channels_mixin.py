#!/usr/bin/env python3
"""Channel selection, filtering & duplicate utilities extracted from main_app."""
from __future__ import annotations

from .async_utils import run_background  # (kept for parity if needed later)


class ChannelsMixin:
    def refresh_channels_display(self):
        self.channel_list_component.refresh(self.filtered_channels, group_visible_fn=lambda g: self.group_visible.get(g, True))
        self.update_channel_count()
        self.page.update()

    def _current_display_channels(self):
        return [ch for ch in self.filtered_channels if self.group_visible.get(ch.get('group','') or 'Uncategorized', True)]

    def update_channel_count(self):
        total = len(self.channels)
        selected = sum(1 for c in self.channels if c.get('selected'))
        visible = len(self._current_display_channels())
        parts = [f"{selected} / {total}"]
        if visible < total:
            parts.append(f"visible:{visible}")
        if self.show_only_selected:
            parts.append("showing-selected")
        self.channel_count_text.value = "  |  ".join(parts)
        self.page.update()

    def update_quality_info(self):
        self.quality_info_text.value = f"{self.merged_count} duplicates merged (quality)" if self.merged_count else ""
        self.quality_info_text.update()

    def on_channel_checkbox_change(self, channel, value: bool):
        channel['selected'] = value
        self.refresh_channels_display(); self.save_current_session()

    def on_search_changed(self, e):
        term = e.control.value.lower()
        base = self.channels if not self.show_only_selected else [c for c in self.channels if c.get('selected')]
        if term:
            self.filtered_channels = [c for c in base if term in c['name'].lower() or term in (c.get('group','') or 'Uncategorized').lower()]
        else:
            self.filtered_channels = base.copy()
        self.refresh_channels_display()

    def select_all_clicked(self, _):
        for ch in self._current_display_channels():
            ch['selected'] = True
        self.refresh_channels_display(); self.save_current_session()

    def select_none_clicked(self, _):
        for ch in self._current_display_channels():
            ch['selected'] = False
        self.refresh_channels_display(); self.save_current_session()

    def toggle_show_selected(self, _):
        self.show_only_selected = not self.show_only_selected
        self.toggle_selected_button.text = "Show All" if self.show_only_selected else "Show Selected"
        dummy = type('x', (), {'control': type('y', (), {'value': self.search_field.value})})()
        self.on_search_changed(dummy)

    def toggle_channel_click(self, channel):
        channel['selected'] = not channel.get('selected', False)
        self.refresh_channels_display(); self.save_current_session()

    # --- duplicate merge utilities (unchanged) ----------------------------
    def normalize_channel_name(self, name):  # noqa: D401
        if not name:
            return ""
        normalized = name.lower().strip()
        prefixes_to_remove = ['hd ', 'sd ', 'fhd ', '4k ', 'uhd ']
        suffixes_to_remove = [' hd', ' sd', ' fhd', ' 4k', ' uhd']
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        normalized = normalized.replace('  ', ' ').replace(' - ', ' ').replace(' | ', ' ')
        return normalized.strip()

    def merge_duplicate_channels(self, verbose: bool = False):
        stats = {
            'original_count': len(self.channels),
            'new_count': len(self.channels),
            'duplicates_removed': 0,
            'groups_total': 0,
            'groups_merged': 0,
        }
        if not self.channels:
            return stats
        channel_groups = {}
        for channel in self.channels:
            name = channel.get("name", "").strip()
            if name:
                normalized_name = self.normalize_channel_name(name)
                channel_groups.setdefault(normalized_name, []).append(channel)
        stats['groups_total'] = len(channel_groups)
        merged_channels = []
        for _, channels in channel_groups.items():
            if len(channels) == 1:
                merged_channels.append(channels[0])
            else:
                best_channel = self.select_best_channel_from_group(channels)
                merged_channels.append(best_channel)
                stats['groups_merged'] += 1
        self.channels = merged_channels; self.filtered_channels = merged_channels.copy()
        stats['new_count'] = len(self.channels)
        stats['duplicates_removed'] = stats['original_count'] - stats['new_count']
        if verbose:
            if stats['duplicates_removed'] > 0:
                self.update_status(f"Duplicate merge: {stats['duplicates_removed']} removed across {stats['groups_merged']} groups")
            else:
                self.update_status("Duplicate merge: no duplicates found")
        return stats

    def select_best_channel_from_group(self, channels):
        if not channels:
            return None
        if len(channels) == 1:
            return channels[0]
        def score_channel(ch):
            score = 0
            url = ch.get("url", "").lower()
            if "fhd" in url or "1080p" in url:
                score += 100
            elif "hd" in url or "720p" in url:
                score += 50
            elif "4k" in url or "2160p" in url:
                score += 150
            score -= len(url) // 100
            if ch.get("selected", False):
                score += 10
            return score
        best_channel = max(channels, key=score_channel)
        if any(ch.get("selected", False) for ch in channels):
            best_channel["selected"] = True
        return best_channel
