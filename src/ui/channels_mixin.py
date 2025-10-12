#!/usr/bin/env python3
"""Channel selection, filtering & duplicate utilities extracted from main_app."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .async_utils import run_background  # (kept for parity if needed later)

if TYPE_CHECKING:  # pragma: no cover - hinting support only
    from .channel_list import ChannelListView


class ChannelsMixin:
    page: Any
    channel_list_component: "ChannelListView"
    group_visible: dict[str, bool]
    channels: list[dict]
    filtered_channels: list[dict]
    show_only_selected: bool
    channel_count_text: Any
    summary_total_text: Any
    summary_selected_text: Any
    quality_info_text: Any
    merged_count: int
    save_current_session: Any
    toggle_selected_button: Any
    search_field: Any
    update_status: Any

    def refresh_channels_display(self):
        """Refresh the channel list display with current filtered channels."""
        try:
            self.channel_list_component.refresh(
                self.filtered_channels, 
                group_visible_fn=lambda g: self.group_visible.get(g, True)
            )
            self.update_channel_count()
            # Update only the list view, not the entire page to avoid assertion errors
            self.channel_list_component.list_view.update()
        except Exception as e:
            print(f"Error refreshing channel display: {e}")
            # Fallback: try full page update
            try:
                self.page.update()
            except:
                pass

    def _current_display_channels(self):
        """Get list of channels that are currently visible based on group visibility."""
        default_group = 'Uncategorized'
        return [
            ch for ch in self.filtered_channels 
            if self.group_visible.get(ch.get('group', '') or default_group, True)
        ]

    def update_channel_count(self):
        """Update the channel count display text with current statistics."""
        try:
            total = len(self.channels)
            selected = sum(1 for c in self.channels if c.get('selected'))
            visible = len(self._current_display_channels())
            
            parts = [f"{selected:,} selected", f"{total:,} total"]
            if visible < total:
                parts.append(f"{visible:,} visible")
            if self.show_only_selected:
                parts.append("showing only selected")

            if self.channel_count_text:
                self.channel_count_text.value = "  |  ".join(parts)
                self.channel_count_text.update()

            summary_total = getattr(self, 'summary_total_text', None)
            summary_selected = getattr(self, 'summary_selected_text', None)
            if summary_total:
                summary_total.value = f"{total:,}"
                summary_total.update()
            if summary_selected:
                summary_selected.value = f"{selected:,}"
                summary_selected.update()
        except Exception as e:
            print(f"Error updating channel count: {e}")

    def update_quality_info(self):
        self.quality_info_text.value = f"{self.merged_count} duplicates merged (quality)" if self.merged_count else ""
        self.quality_info_text.update()

    def on_channel_checkbox_change(self, channel, value: bool):
        """Handle channel checkbox state change."""
        try:
            channel['selected'] = value
            self.refresh_channels_display()
            self.save_current_session()
        except Exception as e:
            print(f"Error changing checkbox: {e}")

    def on_search_changed(self, e):
        """Filter channels based on search term in name or group."""
        term = e.control.value.lower().strip()
        
        # Determine base channel list (all or only selected)
        if self.show_only_selected:
            base = [c for c in self.channels if c.get('selected')]
        else:
            base = self.channels
        
        # Apply search filter
        if term:
            default_group = 'Uncategorized'
            self.filtered_channels = [
                c for c in base 
                if term in c['name'].lower() 
                or term in (c.get('group', '') or default_group).lower()
            ]
        else:
            self.filtered_channels = base.copy()
        
        # Schedule refresh in UI thread to avoid assertion errors
        try:
            self.refresh_channels_display()
        except Exception as e:
            print(f"Error in on_search_changed: {e}")
            # Silently ignore to prevent UI freeze

    def select_all_clicked(self, _):
        """Select all currently visible channels."""
        try:
            for ch in self._current_display_channels():
                ch['selected'] = True
            self.refresh_channels_display()
            self.save_current_session()
        except Exception as e:
            print(f"Error selecting all: {e}")

    def select_none_clicked(self, _):
        """Deselect all currently visible channels."""
        try:
            for ch in self._current_display_channels():
                ch['selected'] = False
            self.refresh_channels_display()
            self.save_current_session()
        except Exception as e:
            print(f"Error clearing selection: {e}")

    def toggle_show_selected(self, _):
        """Toggle between showing all channels and only selected channels."""
        self.show_only_selected = not self.show_only_selected
        self.toggle_selected_button.text = "Show All" if self.show_only_selected else "Show Selected"
        
        # Create a dummy event to trigger search filter refresh
        class DummyEvent:
            def __init__(self, value):
                self.control = type('Control', (), {'value': value})()
        
        dummy_event = DummyEvent(self.search_field.value)
        self.on_search_changed(dummy_event)

    def toggle_channel_click(self, channel):
        """Toggle selection state of a single channel."""
        try:
            channel['selected'] = not channel.get('selected', False)
            self.refresh_channels_display()
            self.save_current_session()
        except Exception as e:
            print(f"Error toggling channel: {e}")

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
        self.channels = merged_channels
        self.filtered_channels = merged_channels.copy()
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
