#!/usr/bin/env python3
"""Channel list rendering and interactions split out from main_app."""
from __future__ import annotations
import re
import unicodedata
import flet as ft
from typing import List, Dict, Any, Callable

Channel = Dict[str, Any]


class ChannelListView:
    """Component for displaying and managing a scrollable list of channels."""
    
    def __init__(self,
                 on_toggle_channel: Callable[[Channel], None],
                 on_checkbox_change: Callable[[Channel, bool], None],
                 on_request_merge: Callable[[Channel], None]):
        self.on_toggle_channel = on_toggle_channel
        self.on_checkbox_change = on_checkbox_change
        self.on_request_merge = on_request_merge
        self.list_view = ft.ListView(
            height=480,
            spacing=4,
            padding=ft.padding.symmetric(horizontal=4, vertical=6)
        )
        self._current_channels = []  # Cache of currently displayed channels

    def control(self) -> ft.ListView:
        """Return the underlying ListView control."""
        return self.list_view

    def _build_row(self, channel: Channel, group_visible: bool) -> ft.Control | None:
        """Build a single channel row UI element."""
        if not group_visible:
            return None
            
        selected = channel.get('selected', False)
        # Pretty display name (UI only) – keep underlying 'name' unchanged for logic/search
        label_text = self._pretty_channel_name(channel.get('name', ''))
        
        checkbox = ft.Checkbox(
            label=label_text,
            value=selected,
            on_change=lambda e, c=channel: self.on_checkbox_change(c, e.control.value),
            fill_color=ft.Colors.CYAN_ACCENT_400,
        )
        
        group_name = channel.get('group', '') or 'Uncategorized'
        group_chip = ft.Container(
            ft.Text(group_name, size=10, color=ft.Colors.GREY_200),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
            border_radius=20,
        )
        
        container = ft.Container(
            ft.Row([checkbox, group_chip], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.18 if selected else 0.06, ft.Colors.WHITE),
            border_radius=12,
            ink=True,
        )

        return ft.GestureDetector(
            content=container,
            on_tap=lambda _e, c=channel: self.on_toggle_channel(c),
            on_secondary_tap=lambda _e, c=channel: self.on_request_merge(c),
            mouse_cursor=ft.MouseCursor.CLICK,
        )

    def refresh(self, channels: List[Channel], group_visible_fn) -> None:
        """Refresh the channel list with new data."""
        try:
            # Build new controls
            new_controls = []
            for ch in channels:
                g = ch.get('group', '') or 'Uncategorized'
                row = self._build_row(ch, group_visible_fn(g))
                if row:
                    new_controls.append(row)
            
            # Replace all controls at once instead of clearing and appending
            # This is safer and prevents assertion errors with control UIDs
            self.list_view.controls = new_controls
            self._current_channels = channels.copy()
            
        except Exception as e:
            print(f"Error refreshing channel list: {e}")
            # Keep old controls on error to prevent blank screen

    # --- helpers ---------------------------------------------------------
    def _pretty_channel_name(self, raw: str) -> str:
        """Format channel name with proper capitalization for acronyms and remove technical suffixes."""
        if not raw:
            return raw
        
        name = raw
        
        # Step 1: Normalize Unicode and remove special symbols
        name = unicodedata.normalize('NFKD', name)
        # Keep only ASCII-compatible characters
        name = ''.join(c for c in name if not unicodedata.combining(c) and ord(c) < 128 or c.isspace())
        
        # Step 2: Remove technical suffixes in parentheses/brackets: (720p), (1080p), [24/7], etc.
        name = re.sub(r'\s*[\(\[](?:\d+p|4K|HD|FHD|UHD|24/7|HEVC|H\.?264|H\.?265)[^\)\]]*[\)\]]', '', name, flags=re.IGNORECASE)
        
        # Step 3: Remove geographic variants
        name = re.sub(r'\s+(?:Italy|Italian|IT|ITA|Italia|Italiano)$', '', name, flags=re.IGNORECASE)
        
        # Step 4: Remove quality suffixes as standalone words
        quality_suffixes = ["HD", "FHD", "UHD", "4K", "8K", "SD", "720p", "1080p", "2160p"]
        for suffix in quality_suffixes:
            pattern = rf'\s+{re.escape(suffix)}$'
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Step 5: Clean multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Step 6: Apply capitalization for acronyms
        acronyms = {"hd", "uhd", "fhd", "tv", "ip", "iptv", "4k"}
        words = name.split()
        pretty_words: list[str] = []
        
        for w in words:
            lw = w.lower()
            if lw in acronyms:
                pretty_words.append(lw.upper())
            elif lw.isdigit():
                pretty_words.append(w)  # keep numbers as-is
            else:
                # Capitalize first letter, keep rest lowercase
                pretty_words.append(lw.capitalize())
                
        return " ".join(pretty_words)

