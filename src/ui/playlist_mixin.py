#!/usr/bin/env python3
"""Playlist source management extracted from main_app."""
from __future__ import annotations

import os
from typing import Dict, List, TYPE_CHECKING, Any

from .async_utils import run_background

if TYPE_CHECKING:  # pragma: no cover - hints only
    from backend.m3u_processor import M3UProcessor


class PlaylistMixin:
    url_field: Any
    update_status: Any
    playlist_sources: List[Dict]
    stream_urls_seen: set
    channels: List[Dict]
    filtered_channels: List[Dict]
    processor: "M3UProcessor"
    sources_list_text: Any
    group_included: Dict[str, bool]
    group_visible: Dict[str, bool]
    page: Any
    quality_info_text: Any
    summary_playlists_text: Any
    load_saved_button: Any
    restore_saved_selections: Any
    populate_groups: Any
    refresh_channels_display: Any
    save_current_session: Any
    update_button_states: Any
    update_quality_info: Any
    show_progress: Any
    update_visibility_button: Any

    def update_saved_playlist_button_state(self) -> None:
        """Enable or disable the saved playlists quick action based on config."""
        button = getattr(self, 'load_saved_button', None)
        if not button:
            return
        saved = [u.strip() for u in self.processor.config.get('saved_playlists', []) if u.strip()]
        button.disabled = not bool(saved)
        button.tooltip = "Configure saved playlist links in Settings" if button.disabled else "Load every saved playlist in one go"
        # Only update if button is already attached to page (avoids assertion during build)
        try:
            button.update()
        except (AssertionError, AttributeError):
            pass  # Button not yet added to page; state will be applied on initial render

    def _process_playlist_url(self, url: str, existing_selections: set[str]) -> tuple[bool, str, int, int]:
        """Download, parse, and append playlist channels.

        Returns (success, message, added_count, skipped_count).
        """
        success, lines, error = self.processor.download_m3u(url, progress_callback=self.update_status)
        if not success:
            return False, error, 0, 0

        added = skipped = 0
        for ch in self.processor.parse_channels(lines):
            stream_url = ch['lines'][-1] if ch['lines'] else None
            if not stream_url or stream_url in self.stream_urls_seen:
                skipped += 1
                continue
            self.stream_urls_seen.add(stream_url)
            ch['source_url'] = url
            ch['selected'] = ch['name'] in existing_selections
            self.channels.append(ch)
            added += 1

        self.playlist_sources.append({'url': url, 'channels_added': added, 'skipped': skipped})
        return True, "", added, skipped

    def _finalize_playlist_changes(self) -> None:
        self.filtered_channels = self.channels.copy()
        self.update_sources_list_text()
        self.apply_filters_to_channels()
        self.restore_saved_selections()
        self.populate_groups()
        self.refresh_channels_display()
        self.save_current_session()
        self.update_button_states()
        self.update_quality_info()

    def add_playlist_clicked(self, _):
        """Handle the 'Add Playlist' button click event."""
        url = (self.url_field.value or '').strip()
        
        if not url:
            self.update_status("Enter a playlist URL first", is_error=True)
            return
        
        if any(s['url'] == url for s in self.playlist_sources):
            self.update_status("Playlist already added")
            return

        def task():
            """Background task to download and process playlist."""
            existing_selections = {ch['name'] for ch in self.channels if ch.get('selected')}
            success, message, added, skipped = self._process_playlist_url(url, existing_selections)
            if not success:
                self.update_status(message or "Failed to add playlist", is_error=True)
                return

            self._finalize_playlist_changes()

            self.update_status(
                f"Added playlist: {added} new, {skipped} duplicates (total {len(self.channels)})"
            )

        run_background(
            task, 
            before=lambda: self.show_progress(True), 
            after=lambda: self.show_progress(False), 
            name="add-playlist"
        )

    def load_saved_playlists_clicked(self, _):
        """Load every playlist URL saved in settings in one action."""
        saved_urls = [u.strip() for u in self.processor.config.get('saved_playlists', []) if u.strip()]
        if not saved_urls:
            self.update_status("Add saved playlist links in Settings first", is_error=True)
            return

        urls_to_add: list[str] = []
        seen: set[str] = set()
        for url in saved_urls:
            if url in seen:
                continue
            seen.add(url)
            if any(s['url'] == url for s in self.playlist_sources):
                continue
            urls_to_add.append(url)
        if not urls_to_add:
            self.update_status("All saved playlists are already loaded")
            return

        def task():
            existing_selections = {ch['name'] for ch in self.channels if ch.get('selected')}
            total_added = total_skipped = 0
            failures: list[tuple[str, str]] = []

            for idx, url in enumerate(urls_to_add, start=1):
                self.update_status(f"Loading saved playlist {idx}/{len(urls_to_add)}...")
                success, message, added, skipped = self._process_playlist_url(url, existing_selections)
                if success:
                    total_added += added
                    total_skipped += skipped
                else:
                    failures.append((url, message))

            if total_added or total_skipped:
                self._finalize_playlist_changes()

            if failures and not (total_added or total_skipped):
                first_error = failures[0][1] or "Unknown error"
                self.update_status(f"Saved playlists failed: {first_error}", is_error=True)
                return

            summary_bits = []
            if total_added:
                summary_bits.append(f"{total_added} new")
            summary_bits.append(f"{total_skipped} duplicates")
            if failures:
                summary_bits.append(f"{len(failures)} failed")
            detail = ", ".join(summary_bits)
            self.update_status(f"Loaded saved playlists: {detail} (total {len(self.channels)})")

        run_background(
            task,
            before=lambda: self.show_progress(True),
            after=lambda: self.show_progress(False),
            name="load-saved-playlists",
        )

    def update_sources_list_text(self):
        """Update the sources list display text with current playlist information."""
        if not self.playlist_sources:
            self.sources_list_text.value = "No playlists added"
        else:
            parts = []
            for i, source in enumerate(self.playlist_sources):
                basename = os.path.basename(source['url']) or source['url']
                stats = f"+{source['channels_added']}/~{source['skipped']}"
                parts.append(f"{i+1}. {basename} ({stats})")
            self.sources_list_text.value = " | ".join(parts)
        
        self.sources_list_text.update()

        summary_sources = getattr(self, 'summary_playlists_text', None)
        if summary_sources:
            summary_sources.value = str(len(self.playlist_sources))
            summary_sources.update()

    def apply_filters_to_channels(self):
        """Apply configured filters to channels and update selection state."""
        filtered = self.processor.filter_channels(
            self.channels, 
            quality_config_override={"use_name_based_quality": False}
        )
        selected_names = {c['name'] for c in filtered}
        
        for ch in self.channels:
            ch['selected'] = ch['name'] in selected_names
        
        # Reset group visibility state
        self.group_included.clear()
        self.group_visible.clear()
        self.all_groups_visible = True
        self.update_visibility_button()

    def clear_all_sources_clicked(self, _):
        """Clear all loaded playlists and reset state."""
        if not self.playlist_sources:
            return
        
        self.playlist_sources.clear()
        self.stream_urls_seen.clear()
        self.channels.clear()
        self.filtered_channels.clear()
        self.update_sources_list_text()
        
        self.update_button_states()
        self.refresh_channels_display()
        self.save_current_session()
        self.update_status("Cleared all playlists")

    def refresh_all_sources_clicked(self, _):
        """Refresh all loaded playlists by re-downloading them."""
        if not self.playlist_sources:
            self.update_status("No playlists to refresh", is_error=True)
            return
        
        urls_to_refresh = [s['url'] for s in self.playlist_sources]

        def task():
            """Background task to refresh all playlists."""
            self.update_status("Refreshing all playlists...")

            preserved_selections = {ch['name'] for ch in self.channels if ch.get('selected')}

            # Reset state
            self.playlist_sources.clear()
            self.stream_urls_seen.clear()
            self.channels.clear()
            self.filtered_channels.clear()

            total_sources = len(urls_to_refresh)
            total_added = total_skipped = 0
            failures: list[tuple[str, str]] = []

            for index, url in enumerate(urls_to_refresh, start=1):
                self.update_status(f"Refreshing playlist {index}/{total_sources}: {url[:50]}...")
                success, message, added, skipped = self._process_playlist_url(url, preserved_selections)
                if success:
                    total_added += added
                    total_skipped += skipped
                else:
                    failures.append((url, message))

            self._finalize_playlist_changes()

            if failures and not self.playlist_sources:
                first_error = failures[0][1] or "Unknown error"
                self.update_status(f"Refresh failed: {first_error}", is_error=True)
                return

            detail = []
            if total_added:
                detail.append(f"{total_added} new")
            detail.append(f"{total_skipped} duplicates")
            if failures:
                detail.append(f"{len(failures)} failed")
            summary = ", ".join(detail)
            self.update_status(
                f"Refreshed {len(self.playlist_sources)} playlists – {summary}, {len(self.channels)} channels total"
            )

        run_background(
            task,
            before=lambda: self.show_progress(True),
            after=lambda: self.show_progress(False),
            name="refresh-all",
        )
