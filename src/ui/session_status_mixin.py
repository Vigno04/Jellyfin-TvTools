#!/usr/bin/env python3
"""Session & status/progress related methods extracted from main_app.

Responsible for:
  * UI status/progress updates
  * Session persistence (save/load)
  * Button state management
  * Backward compatibility helper (save_current_selection)
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

import flet as ft


class SessionStatusMixin:
    # --- status / progress -------------------------------------------------
    def update_status(self, message: str, is_error: bool = False):  # noqa: D401
        """Update status bar + progress bar heuristics (copied verbatim)."""
        low = message.lower()
        if low.startswith("quality probing"):
            import re as _re
            m = _re.search(r"quality probing (\d+)/(\d+)", low)
            if m:
                cur = int(m.group(1))
                total = int(m.group(2)) or 1
                self.progress_bar.visible = True
                self.progress_bar.value = cur / total
        elif "quality merge complete" in low:
            self.progress_bar.value = 1
        elif low.startswith("link check "):
            import re as _re
            m = _re.search(r"link check (\d+)/(\d+)", low)
            if m:
                cur = int(m.group(1))
                total = int(m.group(2)) or 1
                self.progress_bar.visible = True
                self.progress_bar.value = cur / total
        elif low.startswith("link check complete"):
            self.progress_bar.value = 1

        self.status_text.value = message
        self.status_text.color = ft.Colors.RED_300 if is_error else ft.Colors.GREY_400
        self.page.update()

    def show_progress(self, show: bool):
        self.progress_bar.visible = show
        self.load_button.disabled = show
        self.page.update()

    # --- session persistence ----------------------------------------------
    def restore_saved_selections(self):
        if not self.channels:
            return
        # SessionManager.load_session already applied in load_saved_session
        if self.session_manager.load_session():  # pragma: no cover - original logic
            return

    def load_saved_session(self):
        if not self.session_manager.has_saved_session():
            return
        session_data = self.session_manager.load_session()
        if not session_data:
            return
        try:
            self.channels = session_data.get("channels", [])
            self.playlist_sources = session_data.get("playlist_sources", [])
            self.stream_urls_seen = session_data.get("stream_urls_seen", set())
            url_value = session_data.get("url_field", "")
            if url_value:
                self.url_field.value = url_value
            if self.channels:
                self.filtered_channels = self.channels.copy()
                self.populate_groups()
                self.refresh_channels_display()
                self.update_sources_list_text()
                self.update_button_states()
                self.update_status(
                    f"Session restored: {len(self.channels)} channels from {len(self.playlist_sources)} playlists"
                )
            self.page.update()
        except Exception as e:  # noqa: BLE001
            self.update_status(f"Failed to restore session: {e}", is_error=True)

    def update_button_states(self):
        has_channels = bool(self.channels)
        has_sources = bool(self.playlist_sources)
        for button in (
            self.merge_quality_button,
            self.remove_dead_button,
            self.remove_unwanted_button,
            self.optimize_all_button,
            self.export_button,
        ):
            button.disabled = not has_channels
        self.clear_sources_btn.disabled = not (self.playlist_sources or has_channels)
        self.refresh_sources_btn.disabled = not has_sources
        if hasattr(self, 'update_saved_playlist_button_state'):
            self.update_saved_playlist_button_state()
        self.page.update()

    def save_current_session(self):  # persisted after user-facing ops
        try:
            self.session_manager.save_session(
                channels=self.channels,
                playlist_sources=self.playlist_sources,
                stream_urls_seen=self.stream_urls_seen,
                url_field=self.url_field.value if self.url_field else "",
            )
        except Exception as e:  # noqa: BLE001
            print(f"Failed to save session: {e}")

    # Backward compatibility helper used by GroupManagerMixin
    def save_current_selection(self):  # noqa: D401
        """Alias for legacy call in GroupManagerMixin."""
        self.save_current_session()
