#!/usr/bin/env python3
"""Playlist source management extracted from main_app."""
from __future__ import annotations

import os
from typing import Dict, List

from .async_utils import run_background


class PlaylistMixin:
    def add_playlist_clicked(self, _):
        url = (self.url_field.value or '').strip()
        if not url:
            self.update_status("Enter a playlist URL first", is_error=True)
            return
        if any(s['url'] == url for s in self.playlist_sources):
            self.update_status("Playlist already added")
            return

        def task():
            existing_selections = {ch['name'] for ch in self.channels if ch.get('selected')}
            success, lines, error = self.processor.download_m3u(url, progress_callback=self.update_status)
            if not success:
                self.update_status(error, is_error=True)
                return
            added = skipped = 0
            for ch in self.processor.parse_channels(lines):
                stream_url = ch['lines'][-1] if ch['lines'] else None
                if not stream_url or stream_url in self.stream_urls_seen:
                    skipped += 1
                    continue
                self.stream_urls_seen.add(stream_url)
                ch['source_url'] = url
                ch['selected'] = False if ch['name'] in existing_selections else False
                self.channels.append(ch)
                added += 1
            self.filtered_channels = self.channels.copy()
            self.playlist_sources.append({'url': url, 'channels_added': added, 'skipped': skipped})
            self.update_sources_list_text()
            self.apply_filters_to_channels()
            self.restore_saved_selections()
            self.populate_groups()
            self.refresh_channels_display()
            self.save_current_session()
            self.update_button_states()
            self.update_quality_info()
            self.update_status(f"Added playlist: {added} new, {skipped} duplicates (total {len(self.channels)})")

        run_background(task, before=lambda: self.show_progress(True), after=lambda: self.show_progress(False), name="add-playlist")

    def update_sources_list_text(self):
        if not self.playlist_sources:
            self.sources_list_text.value = "No playlists added"
        else:
            parts = [f"{i+1}. {os.path.basename(s['url']) or s['url']} (+{s['channels_added']}/~{s['skipped']})" for i, s in enumerate(self.playlist_sources)]
            self.sources_list_text.value = " | ".join(parts)
        self.sources_list_text.update()

    def apply_filters_to_channels(self):
        filtered = self.processor.filter_channels(self.channels, quality_config_override={"use_name_based_quality": False})
        selected_names = {c['name'] for c in filtered}
        for ch in self.channels:
            ch['selected'] = ch['name'] in selected_names
        self.group_included.clear()
        self.group_visible.clear()
        self.all_groups_visible = True
        self.update_visibility_button()

    def clear_all_sources_clicked(self, _):
        if not self.playlist_sources:
            return
        self.playlist_sources.clear()
        self.stream_urls_seen.clear()
        self.channels.clear()
        self.filtered_channels.clear()
        self.sources_list_text.value = "No playlists added"
        self.update_button_states()
        self.refresh_channels_display()
        self.save_current_session()
        self.update_status("Cleared all playlists")

    def refresh_all_sources_clicked(self, _):
        if not self.playlist_sources:
            self.update_status("No playlists to refresh", is_error=True)
            return
        urls_to_refresh = [s['url'] for s in self.playlist_sources]

        def task():
            self.update_status("Refreshing all playlists...")
            self.playlist_sources.clear(); self.stream_urls_seen.clear(); self.channels.clear(); self.filtered_channels.clear()
            total_sources = len(urls_to_refresh)
            for i, url in enumerate(urls_to_refresh, 1):
                self.update_status(f"Refreshing playlist {i}/{total_sources}: {url[:50]}...")
                success, lines, error = self.processor.download_m3u(url, progress_callback=self.update_status)
                if not success:
                    self.update_status(f"Failed to refresh {url}: {error}", is_error=True)
                    continue
                added = skipped = 0
                for ch in self.processor.parse_channels(lines):
                    stream_url = ch['lines'][-1] if ch['lines'] else None
                    if not stream_url or stream_url in self.stream_urls_seen:
                        skipped += 1
                        continue
                    self.stream_urls_seen.add(stream_url)
                    ch['source_url'] = url; ch['selected'] = False
                    self.channels.append(ch); added += 1
                self.playlist_sources.append({'url': url, 'channels_added': added, 'skipped': skipped})
            self.filtered_channels = self.channels.copy()
            self.update_sources_list_text(); self.apply_filters_to_channels(); self.restore_saved_selections(); self.populate_groups(); self.refresh_channels_display(); self.update_button_states(); self.save_current_session()
            self.update_status(f"Refreshed {len(self.playlist_sources)} playlists with {len(self.channels)} total channels")

        run_background(task, name="refresh-all")
