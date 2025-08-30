#!/usr/bin/env python3
"""Channel list rendering and interactions split out from main_app."""
from __future__ import annotations
import flet as ft
from typing import List, Dict, Any, Callable

Channel = Dict[str, Any]

class ChannelListView:
    def __init__(self,
                 on_toggle_channel: Callable[[Channel], None],
                 on_checkbox_change: Callable[[Channel, bool], None]):
        self.on_toggle_channel = on_toggle_channel
        self.on_checkbox_change = on_checkbox_change
        self.list_view = ft.ListView(height=480, spacing=4, padding=ft.padding.symmetric(horizontal=4, vertical=6))

    def control(self) -> ft.ListView:
        return self.list_view

    def _build_row(self, channel: Channel, group_visible: bool) -> ft.Control | None:
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
        return ft.Container(
            ft.Row([checkbox, group_chip], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor=ft.Colors.with_opacity(0.18 if selected else 0.06, ft.Colors.WHITE),
            border_radius=12,
            ink=True,
            on_click=lambda _e, c=channel: self.on_toggle_channel(c),
        )

    def refresh(self, channels: List[Channel], group_visible_fn) -> None:
        self.list_view.controls.clear()
        for ch in channels:
            g = ch.get('group', '') or 'Uncategorized'
            row = self._build_row(ch, group_visible_fn(g))
            if row:
                self.list_view.controls.append(row)
        self.list_view.update()

    # --- helpers ---------------------------------------------------------
    def _pretty_channel_name(self, raw: str) -> str:
        if not raw:
            return raw
        acronyms = {"hd", "uhd", "fhd", "tv", "ip", "iptv", "4k"}
        # split by spaces only (avoid touching punctuation inside tokens)
        words = raw.split()
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
