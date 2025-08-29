#!/usr/bin/env python3
"""Modern dark UI for Jellyfin TV Tools (Flet)."""

import os
import sys
import threading
import time
import json
import flet as ft

from backend.m3u_processor import M3UProcessor  # noqa: E402
from .session_manager import SessionManager  # noqa: E402
from .group_manager import GroupManagerMixin  # noqa: E402
from .channel_list import ChannelListView  # noqa: E402
from .async_utils import run_background  # noqa: E402


class JellyfinTVToolsApp(GroupManagerMixin):
    def __init__(self, page: ft.Page):
        # Core state
        self.page = page
        self.processor = M3UProcessor()
        self.channels = []
        self.filtered_channels = []

        # UI element placeholders (assigned in build_ui)
        self.url_field = None
        self.load_button = None
        self.progress_bar = None
        self.status_text = None
        self.search_field = None
        self.channels_list = None  # replaced by ChannelListView.list_view after build
        self.export_button = None
        self.export_selection_button = None
        self.export_channel_list_button = None
        self.import_selection_button = None
        self.import_channel_list_button = None
        self.select_all_button = None
        self.select_none_button = None
        self.toggle_selected_button = None
        self.channel_count_text = None
        self.merge_quality_button = None
        self.remove_dead_button = None
        self.remove_unwanted_button = None
        self.optimize_all_button = None
        self.quality_info_text = None
        self.sources_list_text = None
        self.clear_sources_btn = None
        self.refresh_sources_btn = None

        # Multi-playlist aggregation
        self.playlist_sources = []  # list of {url, channels_added, skipped}
        self.stream_urls_seen = set()

        # Selection and display state
        self.show_only_selected = False
        self.quality_selected_count = 0
        self.merged_count = 0

        # Initialize group management state
        self.init_group_state()

        # Session persistence
        self.session_manager = SessionManager()

        # Build the UI
        self.build_ui()
        
        # Load previous session if available
        self.load_saved_session()

    def build_ui(self):
        self.page.title = "Jellyfin TV Tools"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY, use_material3=True)
        self.page.window_width = 1280
        self.page.window_height = 840
        self.page.window_min_width = 1000
        self.page.window_min_height = 640

        # Header section
        header = ft.Container(
            ft.Row([
                ft.Icon(ft.Icons.TV, size=44, color=ft.Colors.CYAN_ACCENT_400),
                ft.Column([
                    ft.Text("Jellyfin TV Tools", size=26, weight=ft.FontWeight.BOLD),
                    ft.Text("IPTV Playlist & Guide Manager", size=14, color=ft.Colors.GREY_400)
                ], spacing=2)
            ]),
            padding=18,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            border_radius=14,
            margin=ft.margin.only(bottom=18)
        )

        # Sources section
        self.url_field = ft.TextField(
            label="M3U Playlist URL",
            value=self.processor.config.get("download_url", ""),
            prefix_icon=ft.Icons.LINK,
            dense=True,
            border_radius=10
        )
        # Primary action: download/refresh the playlist (was "Add Playlist")
        self.load_button = ft.FilledButton(
            "Download List",
            icon=ft.Icons.CLOUD_DOWNLOAD,
            on_click=self.add_playlist_clicked
        )
        self.merge_quality_button = ft.OutlinedButton(
            "Merge Quality Duplicates",
            icon=ft.Icons.HIGH_QUALITY,
            on_click=self.merge_quality_clicked,
            disabled=True
        )
        self.remove_dead_button = ft.OutlinedButton(
            "Remove Dead Streams",
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self.remove_dead_clicked,
            disabled=True
        )
        self.remove_unwanted_button = ft.OutlinedButton(
            "Remove Test/Unwanted",
            icon=ft.Icons.FILTER_ALT_OFF,
            on_click=self.remove_unwanted_clicked,
            disabled=True
        )
        self.optimize_all_button = ft.FilledTonalButton(
            "Optimize (Merge + Clean + Dead)",
            icon=ft.Icons.AUTO_FIX_HIGH,
            on_click=self.optimize_all_clicked,
            disabled=True
        )
        self.quality_info_text = ft.Text("", size=11, color=ft.Colors.CYAN_ACCENT_200)
        self.sources_list_text = ft.Text("No playlists added", size=11, color=ft.Colors.GREY_400)
        self.clear_sources_btn = ft.TextButton(
            "Clear All",
            icon=ft.Icons.CLEAR_ALL,
            on_click=self.clear_all_sources_clicked,
            disabled=True
        )
        self.refresh_sources_btn = ft.TextButton(
            "Refresh All",
            icon=ft.Icons.REFRESH,
            on_click=self.refresh_all_sources_clicked,
            disabled=True
        )

        sources_card = ft.Container(
            ft.Column([
                ft.Text("Sources", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([self.sources_list_text, 
                       ft.Row([self.refresh_sources_btn, self.clear_sources_btn], spacing=8)], 
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.ResponsiveRow([
                    ft.Column([self.url_field], col={'sm':12}),
                ], run_spacing=10),
                ft.Row([
                    self.load_button,
                    self.merge_quality_button,
                    self.remove_dead_button,
                    self.remove_unwanted_button,
                    self.optimize_all_button,
                    self.quality_info_text
                ], spacing=16, wrap=True)
            ], spacing=14),
            padding=22,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14,
            margin=ft.margin.only(bottom=18)
        )

        # Progress section
        self.progress_bar = ft.ProgressBar(visible=False, bar_height=6, color=ft.Colors.CYAN_ACCENT_400)
        self.status_text = ft.Text("Ready", size=12, color=ft.Colors.GREY_400)
        progress_section = ft.Container(
            ft.Column([self.progress_bar, self.status_text], spacing=8),
            padding=10
        )

        # Channel controls
        self.search_field = ft.TextField(
            label="Search channels or groups",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self.on_search_changed,
            border_radius=30,
            dense=True,
            width=420
        )
        self.select_all_button = ft.OutlinedButton("Select All", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=self.select_all_clicked)
        self.select_none_button = ft.OutlinedButton("Clear", icon=ft.Icons.CANCEL_OUTLINED, on_click=self.select_none_clicked)
        self.toggle_selected_button = ft.OutlinedButton("Show Selected", icon=ft.Icons.FILTER_LIST, on_click=self.toggle_show_selected)
        self.channel_count_text = ft.Text("0 channels", size=12, color=ft.Colors.GREY_400)
        controls_row = ft.ResponsiveRow([
            ft.Container(self.search_field, col={'sm':12,'md':6,'lg':5}),
            ft.Container(ft.Row([self.select_all_button, self.select_none_button, self.toggle_selected_button], spacing=8), col={'sm':12,'md':4,'lg':4}),
            ft.Container(self.channel_count_text, alignment=ft.alignment.center_right, col={'sm':12,'md':2,'lg':3})
        ], run_spacing=8, alignment=ft.MainAxisAlignment.START)

        # Channel list component
        self.channel_list_component = ChannelListView(
            on_toggle_channel=self.toggle_channel_click,
            on_checkbox_change=lambda ch, val: self.on_channel_checkbox_change(ch, val)
        )
        self.channels_list = self.channel_list_component.control()

        # Group controls - list with individual visibility and include toggles
        self.groups_list = ft.ListView(height=200, spacing=2, padding=ft.padding.symmetric(horizontal=4, vertical=4))
        self.visibility_toggle_btn = ft.OutlinedButton("Hide All", icon=ft.Icons.VISIBILITY_OFF, on_click=self.toggle_all_visibility)
        groups_section = ft.Container(
            ft.Column([
                ft.Row([
                    ft.Text("Groups", size=18, weight=ft.FontWeight.BOLD),
                    self.visibility_toggle_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Each group can be included (select all channels) and made visible independently.", 
                       size=11, color=ft.Colors.GREY_500),
                self.groups_list
            ], spacing=8),
            padding=10,
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            border_radius=10
        )

        channels_card = ft.Container(
            ft.Column([
                ft.Text("Channels", size=18, weight=ft.FontWeight.BOLD),
                controls_row,
                groups_section,
                ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                self.channels_list
            ], spacing=12),
            padding=22,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14,
            margin=ft.margin.only(bottom=18)
        )

        # Export section
        self.export_button = ft.FilledButton("Export m3u list", icon=ft.Icons.PLAYLIST_ADD_CHECK_CIRCLE, on_click=self.export_clicked, disabled=True)
        self.export_selection_button = ft.OutlinedButton("Export Session", icon=ft.Icons.BACKUP, on_click=self.export_selection_clicked)
        self.export_channel_list_button = ft.OutlinedButton("Export Channel list", icon=ft.Icons.LIST_ALT, on_click=self.export_channel_list_clicked)
        self.import_selection_button = ft.OutlinedButton("Restore Session", icon=ft.Icons.RESTORE, on_click=self.import_selection_clicked)
        self.import_channel_list_button = ft.OutlinedButton("Import Channel list", icon=ft.Icons.UPLOAD_FILE, on_click=self.import_channel_list_clicked)
        
        export_card = ft.Container(
            ft.Column([
                ft.Text("Export & Backup", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([self.export_button, self.export_selection_button, self.export_channel_list_button], spacing=14),
                ft.Row([self.import_selection_button, self.import_channel_list_button], spacing=14),
                ft.Text("M3U -> .m3u  |  Session -> auto-saved + manual backup  |  Channel List -> .json", size=12, color=ft.Colors.GREY_500)
            ], spacing=12),
            padding=22,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14
        )

        # Main layout
        root = ft.ListView(
            controls=[header, sources_card, progress_section, channels_card, export_card],
            expand=1,
            spacing=0,
            padding=ft.padding.only(right=4)
        )
        
        self.page.add(root)
        
        # Resize handler
        def on_resize(_):
            reserved = 360
            self.channels_list.height = max(220, self.page.window_height - reserved)
            self.page.update()
        
        self.page.on_resize = on_resize
        on_resize(None)
        self.page.update()

        # Attach file picker for channel list import
        self.channel_list_picker = ft.FilePicker(on_result=self.on_channel_list_file_picked)
        if not any(isinstance(o, ft.FilePicker) for o in self.page.overlay):
            self.page.overlay.append(self.channel_list_picker)
        self.page.update()

    def update_status(self, message: str, is_error: bool = False):
        low = message.lower()
        if low.startswith("quality probing"):
            import re as _re
            m = _re.search(r"quality probing (\d+)/(\d+)", low)
            if m:
                cur = int(m.group(1))
                total = int(m.group(2)) or 1
                self.progress_bar.visible = True
                self.progress_bar.value = cur/total
        elif "quality merge complete" in low:
            self.progress_bar.value = 1
        elif low.startswith("link check "):
            import re as _re
            m = _re.search(r"link check (\d+)/(\d+)", low)
            if m:
                cur = int(m.group(1))
                total = int(m.group(2)) or 1
                self.progress_bar.visible = True
                self.progress_bar.value = cur/total
        elif low.startswith("link check complete"):
            self.progress_bar.value = 1
        
        self.status_text.value = message
        self.status_text.color = ft.Colors.RED_300 if is_error else ft.Colors.GREY_400
        self.page.update()

    def show_progress(self, show: bool):
        self.progress_bar.visible = show
        self.load_button.disabled = show
        self.page.update()

    def restore_saved_selections(self):
        """Restore previously saved channel selections, preserving existing selections"""
        if not self.channels:
            return
            
        # Try to load auto-saved selections first
        if self.session_manager.load_session():
            return
            
        # No manual fallback needed anymore - session manager handles everything

    def load_saved_session(self):
        """Load complete session from previous app run"""
        if not self.session_manager.has_saved_session():
            return
            
        session_data = self.session_manager.load_session()
        if not session_data:
            return
            
        try:
            # Restore complete state
            self.channels = session_data.get("channels", [])
            self.playlist_sources = session_data.get("playlist_sources", [])
            self.stream_urls_seen = session_data.get("stream_urls_seen", set())
            
            # Restore UI field values
            url_value = session_data.get("url_field", "")
            
            if url_value:
                self.url_field.value = url_value
            
            # Update UI state
            if self.channels:
                self.filtered_channels = self.channels.copy()
                self.populate_groups()
                self.refresh_channels_display()
                self.update_sources_list_text()
                
                # Update button states based on channels availability
                self.update_button_states()
                
                self.update_status(f"Session restored: {len(self.channels)} channels from {len(self.playlist_sources)} playlists")
            
            self.page.update()
        except Exception as e:
            self.update_status(f"Failed to restore session: {e}", is_error=True)

    def update_button_states(self):
        """Update button states based on current channel availability"""
        has_channels = bool(self.channels)
        has_sources = bool(self.playlist_sources)
        
        # These buttons require channels to be available
        for button in (self.merge_quality_button, self.remove_dead_button, 
                      self.remove_unwanted_button, self.optimize_all_button, 
                      self.export_button):
            button.disabled = not has_channels
        
        # Clear sources button is enabled when there are sources or channels
        self.clear_sources_btn.disabled = not (self.playlist_sources or has_channels)
        # Refresh sources button is enabled only when there are sources
        self.refresh_sources_btn.disabled = not has_sources
        
        self.page.update()

    def save_current_session(self):
        """Save complete current session state"""
        try:
            self.session_manager.save_session(
                channels=self.channels,
                playlist_sources=self.playlist_sources,
                stream_urls_seen=self.stream_urls_seen,
                url_field=self.url_field.value if self.url_field else ""
            )
        except Exception as e:
            print(f"Failed to save session: {e}")

    def add_playlist_clicked(self, _):
        url = (self.url_field.value or '').strip()
        if not url:
            self.update_status("Enter a playlist URL first", is_error=True)
            return
        
        if any(s['url'] == url for s in self.playlist_sources):
            self.update_status("Playlist already added")
            return
        
        def task():
            # Load existing selections before adding new channels
            existing_selections = set()
            for ch in self.channels:
                if ch.get('selected'):
                    existing_selections.add(ch['name'])
            
            success, lines, error = self.processor.download_m3u(url, progress_callback=self.update_status)
            if not success:
                self.update_status(error, is_error=True)
                return
            
            added = 0
            skipped = 0
            for ch in self.processor.parse_channels(lines):
                stream_url = ch['lines'][-1] if ch['lines'] else None
                if not stream_url or stream_url in self.stream_urls_seen:
                    skipped += 1
                    continue
                
                self.stream_urls_seen.add(stream_url)
                ch['source_url'] = url
                
                # Preserve existing selections - new duplicates start unselected
                if ch['name'] in existing_selections:
                    ch['selected'] = False  # New duplicate stays unselected
                else:
                    ch['selected'] = False  # Default state
                
                self.channels.append(ch)
                added += 1
            
            self.filtered_channels = self.channels.copy()
            self.playlist_sources.append({'url': url, 'channels_added': added, 'skipped': skipped})
            
            self.update_sources_list_text()
            self.apply_filters_to_channels()
            self.restore_saved_selections()  # Apply persistent selections
            self.populate_groups()
            self.refresh_channels_display()
            
            # Auto-save current session after initial load
            self.save_current_session()
            
            # Update button states based on channels availability
            self.update_button_states()
            
            self.update_quality_info()
            self.update_status(f"Added playlist: {added} new, {skipped} duplicates (total {len(self.channels)})")
        
        run_background(
            task,
            before=lambda: self.show_progress(True),
            after=lambda: self.show_progress(False),
            name="add-playlist"
        )

    def update_sources_list_text(self):
        if not self.playlist_sources:
            self.sources_list_text.value = "No playlists added"
        else:
            parts = [f"{i+1}. {os.path.basename(s['url']) or s['url']} (+{s['channels_added']}/~{s['skipped']})" 
                    for i, s in enumerate(self.playlist_sources)]
            self.sources_list_text.value = " | ".join(parts)
        self.sources_list_text.update()

    def apply_filters_to_channels(self):
        filtered = self.processor.filter_channels(
            self.channels,
            quality_config_override={"use_name_based_quality": False}
        )
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
        
        # Update button states (will disable all since no channels)
        self.update_button_states()
        
        self.refresh_channels_display()
        self.save_current_session()  # Save complete session after clear
        self.update_status("Cleared all playlists")

    def refresh_all_sources_clicked(self, _):
        if not self.playlist_sources:
            self.update_status("No playlists to refresh", is_error=True)
            return
        
        # Store URLs before clearing
        urls_to_refresh = [source['url'] for source in self.playlist_sources]
        
        def task():
            self.update_status("Refreshing all playlists...")
            
            # Clear current data
            self.playlist_sources.clear()
            self.stream_urls_seen.clear()
            self.channels.clear()
            self.filtered_channels.clear()
            
            # Store existing selections to preserve them
            existing_selections = set()
            
            # Re-download each playlist
            total_sources = len(urls_to_refresh)
            for i, url in enumerate(urls_to_refresh, 1):
                self.update_status(f"Refreshing playlist {i}/{total_sources}: {url[:50]}...")
                
                success, lines, error = self.processor.download_m3u(url, progress_callback=self.update_status)
                if not success:
                    self.update_status(f"Failed to refresh {url}: {error}", is_error=True)
                    continue
                
                added = 0
                skipped = 0
                for ch in self.processor.parse_channels(lines):
                    stream_url = ch['lines'][-1] if ch['lines'] else None
                    if not stream_url or stream_url in self.stream_urls_seen:
                        skipped += 1
                        continue
                    
                    self.stream_urls_seen.add(stream_url)
                    ch['source_url'] = url
                    ch['selected'] = False  # Default state
                    
                    self.channels.append(ch)
                    added += 1
                
                self.playlist_sources.append({'url': url, 'channels_added': added, 'skipped': skipped})
            
            # Update UI
            self.filtered_channels = self.channels.copy()
            self.update_sources_list_text()
            self.apply_filters_to_channels()
            self.restore_saved_selections()  # Apply persistent selections
            self.populate_groups()
            self.refresh_channels_display()
            self.update_button_states()
            self.save_current_session()
            
            total_channels = len(self.channels)
            total_sources_refreshed = len(self.playlist_sources)
            self.update_status(f"Refreshed {total_sources_refreshed} playlists with {total_channels} total channels")
        
        run_background(task)

    def refresh_channels_display(self):
        self.channel_list_component.refresh(
            self.filtered_channels,
            group_visible_fn=lambda g: self.group_visible.get(g, True)
        )
        self.update_channel_count()
        self.page.update()

    def _current_display_channels(self):
        return [ch for ch in self.filtered_channels 
                if self.group_visible.get(ch.get('group','') or 'Uncategorized', True)]

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
        if self.merged_count:
            self.quality_info_text.value = f"{self.merged_count} duplicates merged (quality)"
        else:
            self.quality_info_text.value = ""
        self.quality_info_text.update()

    def on_channel_checkbox_change(self, channel, value: bool):
        channel['selected'] = value
        self.refresh_channels_display()
        self.save_current_session()

    def on_search_changed(self, e):
        term = e.control.value.lower()
        base = self.channels if not self.show_only_selected else [c for c in self.channels if c.get('selected')]
        
        if term:
            self.filtered_channels = [c for c in base 
                                    if term in c['name'].lower() 
                                    or term in (c.get('group','') or 'Uncategorized').lower()]
        else:
            self.filtered_channels = base.copy()
        
        self.refresh_channels_display()

    def select_all_clicked(self, _):
        for ch in self._current_display_channels():
            ch['selected'] = True
        self.refresh_channels_display()
        self.save_current_session()

    def select_none_clicked(self, _):
        for ch in self._current_display_channels():
            ch['selected'] = False
        self.refresh_channels_display()
        self.save_current_session()

    def toggle_show_selected(self, _):
        self.show_only_selected = not self.show_only_selected
        self.toggle_selected_button.text = "Show All" if self.show_only_selected else "Show Selected"
        
        # Simulate search change to refresh display
        dummy = type('x', (), {'control': type('y', (), {'value': self.search_field.value})})()
        self.on_search_changed(dummy)

    def merge_quality_clicked(self, _):
        if not self.channels:
            return
        
        def task():
            self.update_status("Merging quality duplicates (probing streams)...")
            self.progress_bar.value = 0
            self.progress_bar.visible = True
            
            merged, removed = self.processor.merge_quality(self.channels, progress_callback=self.update_status)
            self.channels = merged
            self.filtered_channels = merged.copy()
            self.merged_count = removed
            
            self.refresh_channels_display()
            self.update_quality_info()
            self.save_current_session()  # Save after merge
            self.update_status(f"Quality merge complete: {removed} removed")
        
        def after():
            self.merge_quality_button.disabled = False
            self.remove_dead_button.disabled = False
            self.progress_bar.visible = False
            self.progress_bar.value = None
            self.page.update()
        
        run_background(
            task,
            before=lambda: setattr(self.merge_quality_button, 'disabled', True),
            after=after,
            name="merge-quality"
        )

    def remove_dead_clicked(self, _):
        if not self.channels:
            return
        
        def task():
            self.update_status("Checking streams for dead links...")
            self.progress_bar.value = 0
            self.progress_bar.visible = True
            
            alive, removed, _ = self.processor.remove_dead_streams(self.channels, progress_callback=self.update_status)
            self.channels = alive
            self.filtered_channels = alive.copy()
            
            self.refresh_channels_display()
            self.save_current_session()  # Save after removing dead streams
            self.update_status(f"Link check complete – {removed} removed")
        
        def after():
            self.remove_dead_button.disabled = False
            self.merge_quality_button.disabled = False
            self.progress_bar.visible = False
            self.progress_bar.value = None
            self.page.update()
        
        run_background(
            task,
            before=lambda: [
                setattr(self.remove_dead_button, 'disabled', True),
                setattr(self.merge_quality_button, 'disabled', True)
            ],
            after=after,
            name="remove-dead"
        )

    def remove_unwanted_clicked(self, _):
        if not self.channels:
            return
        
        def task():
            self.update_status("Removing test and unwanted channels...")
            self.progress_bar.value = 0
            self.progress_bar.visible = True
            
            clean, removed, _ = self.processor.remove_unwanted_channels(self.channels, progress_callback=self.update_status)
            self.channels = clean
            self.filtered_channels = clean.copy()
            
            self.refresh_channels_display()
            self.save_current_session()  # Save after removing unwanted channels
            self.update_status(f"Unwanted channels removed: {removed} filtered out")
        
        def after():
            self.remove_unwanted_button.disabled = False
            self.progress_bar.visible = False
            self.progress_bar.value = None
            self.page.update()
        
        run_background(
            task,
            before=lambda: setattr(self.remove_unwanted_button, 'disabled', True),
            after=after,
            name="remove-unwanted"
        )

    def toggle_channel_click(self, channel):
        channel['selected'] = not channel.get('selected', False)
        self.refresh_channels_display()
        self.save_current_session()

    def optimize_all_clicked(self, _):
        if not self.channels:
            return

        def task():
            try:
                self.progress_bar.value = 0
                self.progress_bar.visible = True
                removed_quality, removed_unwanted, removed_dead = self._optimize_all_core_internal()
                self.merged_count = removed_quality
                self.save_current_session()
                self.update_status(
                    f"Optimization complete: {removed_quality} quality + {removed_unwanted} unwanted + {removed_dead} dead removed"
                )
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Optimization failed: {e}", is_error=True)

        def before():
            for b in (self.merge_quality_button, self.remove_dead_button, self.remove_unwanted_button, self.optimize_all_button):
                b.disabled = True
            self.page.update()

        def after():
            for b in (self.merge_quality_button, self.remove_dead_button, self.remove_unwanted_button, self.optimize_all_button):
                b.disabled = False
            self.progress_bar.visible = False
            self.progress_bar.value = None
            self.page.update()

        run_background(task, before=before, after=after, name="optimize-all")

    def export_clicked(self, _):
        def task():
            self.update_status("Exporting selected channels...")
            success, msg = self.processor.export_m3u(self.channels, progress_callback=self.update_status)
            self.update_status(msg, is_error=not success)
            
            if success:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(msg),
                    open=True,
                    bgcolor=ft.Colors.GREEN_800
                )
                self.page.update()
        
        run_background(
            task,
            before=lambda: self.show_progress(True),
            after=lambda: self.show_progress(False),
            name="export-m3u"
        )

    def export_selection_clicked(self, _):
        """Export current session as a backup"""
        def task():
            try:
                self.update_status("Exporting session...")
                # Use session manager to create backup
                backup_file = os.path.join("data", f"session_backup_{int(time.time())}.json")
                session_data = {
                    "channels": self.channels,
                    "playlist_sources": self.playlist_sources,
                    "stream_urls_seen": list(self.stream_urls_seen),
                    "url_field": self.url_field.value
                }
                
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                msg = f"Session exported to {backup_file}"
                self.update_status(msg)
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(msg),
                    open=True,
                    bgcolor=ft.Colors.GREEN_800
                )
                self.page.update()
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Export failed: {e}", is_error=True)
        
        run_background(
            task,
            before=lambda: self.show_progress(True),
            after=lambda: self.show_progress(False),
            name="export-session"
        )

    def import_selection_clicked(self, _):
        """Import session from backup"""
        def task():
            try:
                self.update_status("Looking for session backup...")
                import glob
                backups = glob.glob("data/session_backup_*.json")
                if not backups:
                    self.update_status("No session backups found", is_error=True)
                    return
                
                # Load the most recent backup
                latest_backup = max(backups, key=os.path.getmtime)
                with open(latest_backup, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                
                # Restore from backup
                self.channels = session_data.get("channels", [])
                self.playlist_sources = session_data.get("playlist_sources", [])
                self.stream_urls_seen = set(session_data.get("stream_urls_seen", []))
                
                if self.channels:
                    self.filtered_channels = self.channels.copy()
                    self.populate_groups()
                    self.refresh_channels_display()
                    self.update_sources_list_text()
                    
                    # Update button states based on channels availability
                    self.update_button_states()
                    
                    self.save_current_session()  # Save as current session
                    
                msg = f"Session imported from {os.path.basename(latest_backup)}: {len(self.channels)} channels"
                self.update_status(msg)
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(msg),
                    open=True,
                    bgcolor=ft.Colors.GREEN_800
                )
                self.page.update()
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Import failed: {e}", is_error=True)
        
        run_background(
            task,
            before=lambda: self.show_progress(True),
            after=lambda: self.show_progress(False),
            name="import-session"
        )

    def export_channel_list_clicked(self, _):
        """Export only the channel names (without URLs) for reuse with other playlists"""
        def task():
            try:
                if not self.channels:
                    self.update_status("No channels to export", is_error=True)
                    return
                
                import json
                import time
                
                self.update_status("Exporting channel list...")
                
                # Create a list of channel names only
                channel_list = []
                for channel in self.channels:
                    channel_info = {
                        "name": channel.get("name", ""),
                        "selected": channel.get("selected", False)
                    }
                    if channel_info["name"]:  # Only add if name exists
                        channel_list.append(channel_info)
                
                # Create export file
                export_file = os.path.join("data", f"channel_list_{int(time.time())}.json")
                export_data = {
                    "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_channels": len(channel_list),
                    "channels": channel_list
                }
                
                with open(export_file, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                msg = f"Channel list exported to {os.path.basename(export_file)} ({len(channel_list)} channels)"
                self.update_status(msg)
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(msg),
                    open=True,
                    bgcolor=ft.Colors.GREEN_800
                )
                self.page.update()
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Channel list export failed: {e}", is_error=True)
        
        run_background(
            task,
            before=lambda: self.show_progress(True),
            after=lambda: self.show_progress(False),
            name="export-channel-list"
        )

    def import_channel_list_clicked(self, _):
        """Open OS file picker; after picking run full optimization then apply selections."""
        if not self.channels:
            self.update_status("Load a playlist before importing channel list", is_error=True)
            return
        self.update_status("Select a channel list JSON file to import (will auto-optimize first)...")
        try:
            if not hasattr(self, 'channel_list_picker'):
                self.channel_list_picker = ft.FilePicker(on_result=self.on_channel_list_file_picked)
                self.page.overlay.append(self.channel_list_picker)
            self.channel_list_picker.pick_files(allow_multiple=False, allowed_extensions=['json'])
        except Exception as ex:  # noqa: BLE001
            self.update_status(f"File picker failed: {ex}", is_error=True)

    def _close_dialog(self):
        if getattr(self.page, 'dialog', None):
            self.page.dialog.open = False
            self.page.update()

    def on_channel_list_file_picked(self, e: ft.FilePickerResultEvent):
        if not e.files:
            self.update_status("Import cancelled", is_error=True)
            return
        fobj = e.files[0]
        path = getattr(fobj, 'path', None)
        # Some environments (web) don't provide a path; we may have bytes/content
        if (not path or not os.path.isfile(path)):
            # Try to persist in-memory content
            content_bytes = None
            for attr in ('bytes', 'content', 'data'):
                if hasattr(fobj, attr) and getattr(fobj, attr):
                    content_bytes = getattr(fobj, attr)
                    break
            if content_bytes is None and hasattr(fobj, 'read_bytes'):
                try:
                    content_bytes = fobj.read_bytes()
                except Exception:  # noqa: BLE001
                    pass
            if content_bytes:
                os.makedirs('data', exist_ok=True)
                temp_path = os.path.join('data', '_picked_channel_list.json')
                try:
                    with open(temp_path, 'wb') as tf:
                        tf.write(content_bytes)
                    path = temp_path
                except Exception as ex:  # noqa: BLE001
                    self.update_status(f"Failed saving picked file: {ex}", is_error=True)
                    return
            else:
                self.update_status("Picked file has no accessible path/content", is_error=True)
                return
        self.update_status(f"Selected channel list file: {os.path.basename(path)}")
        self._start_channel_list_import(using_file=path)

    def _start_channel_list_import(self, using_file: str):
        def import_task():
            try:
                import json
                if not os.path.isfile(using_file):
                    self.update_status("File not found", is_error=True)
                    return
                if not self.channels:
                    self.update_status("Load a playlist before importing channel list", is_error=True)
                    return
                # Load import file first
                with open(using_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                imported_channels = data.get('channels', [])
                if not imported_channels:
                    self.update_status("No channels in file", is_error=True)
                    return
                imported_map = {}
                for ch in imported_channels:
                    name = ch.get('name', '').strip()
                    if name:
                        imported_map[self.normalize_channel_name(name)] = ch.get('selected', False)
                # Run full optimization BEFORE applying selections
                self.update_status("Optimizing playlist before applying selections (merge+clean+dead)...")
                try:
                    q_removed, u_removed, d_removed = self._optimize_all_core_internal()
                    self.update_status(
                        f"Optimization done: {q_removed} quality + {u_removed} unwanted + {d_removed} dead removed; applying selections..."
                    )
                except Exception as op_ex:  # noqa: BLE001
                    self.update_status(f"Optimization failed (continuing import): {op_ex}", is_error=True)
                # Apply imported selection states
                matches = 0
                for ch in self.channels:
                    n = self.normalize_channel_name(ch.get('name', ''))
                    if n in imported_map:
                        ch['selected'] = imported_map[n]
                        matches += 1
                self.filtered_channels = self.channels.copy()
                self.refresh_channels_display()
                self.update_channel_count()
                self.save_current_session()
                msg = (f"Import complete: applied selections from '{os.path.basename(using_file)}' to {matches} channels" )
                self.update_status(msg)
                self.page.snack_bar = ft.SnackBar(ft.Text(msg), open=True, bgcolor=ft.Colors.GREEN_800)
                self.page.update()
            except Exception as ex:  # noqa: BLE001
                self.update_status(f"Import failed: {ex}", is_error=True)
        run_background(import_task, before=lambda: self.show_progress(True), after=lambda: self.show_progress(False), name="import-channel-list")

    def normalize_channel_name(self, name):
        """Normalize channel name for better matching across different playlists"""
        if not name:
            return ""
        
        # Convert to lowercase and remove common variations
        normalized = name.lower().strip()
        
        # Remove common prefixes/suffixes that might vary between lists
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
        
        # Remove extra spaces and common symbols that might vary
        normalized = normalized.replace('  ', ' ')
        normalized = normalized.replace(' - ', ' ')
        normalized = normalized.replace(' | ', ' ')
        
        return normalized.strip()

    def merge_duplicate_channels(self, verbose: bool = False):
        """Merge channels with the same normalized name, keeping the best quality version.

        Returns stats dict: {
            'original_count': int,
            'new_count': int,
            'duplicates_removed': int,
            'groups_total': int,
            'groups_merged': int
        }
        """
        stats = {
            'original_count': len(self.channels),
            'new_count': len(self.channels),
            'duplicates_removed': 0,
            'groups_total': 0,
            'groups_merged': 0
        }
        if not self.channels:
            return stats

        # Group channels by normalized name
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
                self.update_status(
                    f"Duplicate merge: {stats['duplicates_removed']} removed across {stats['groups_merged']} groups"
                )
            else:
                self.update_status("Duplicate merge: no duplicates found")
        return stats

    # --- Internal core optimization used by optimize button and import ---
    def _optimize_all_core_internal(self):
        """Run merge_quality, remove_unwanted, remove_dead sequentially.
        Returns tuple: (removed_quality, removed_unwanted, removed_dead)
        """
        removed_quality = removed_unwanted = removed_dead = 0
        # Merge quality duplicates
        self.update_status("Optimizing: merging quality duplicates...")
        merged, removed_quality = self.processor.merge_quality(self.channels, progress_callback=self.update_status)
        self.channels = merged
        self.filtered_channels = merged.copy()
        self.refresh_channels_display()
        self.update_quality_info()
        # Unwanted
        self.update_status("Optimizing: removing unwanted/test channels...")
        clean, removed_unwanted, _uw = self.processor.remove_unwanted_channels(self.channels, progress_callback=self.update_status)
        self.channels = clean
        self.filtered_channels = clean.copy()
        self.refresh_channels_display()
        # Dead
        self.update_status("Optimizing: checking dead streams...")
        alive, removed_dead, _dead = self.processor.remove_dead_streams(self.channels, progress_callback=self.update_status)
        self.channels = alive
        self.filtered_channels = alive.copy()
        self.refresh_channels_display()
        return removed_quality, removed_unwanted, removed_dead

    def select_best_channel_from_group(self, channels):
        """Select the best channel from a group of channels with similar names"""
        if not channels:
            return None
        if len(channels) == 1:
            return channels[0]
        
        # Scoring criteria (higher is better)
        def score_channel(ch):
            score = 0
            url = ch.get("url", "").lower()
            
            # Prefer URLs with quality indicators
            if "fhd" in url or "1080p" in url:
                score += 100
            elif "hd" in url or "720p" in url:
                score += 50
            elif "4k" in url or "2160p" in url:
                score += 150
                
            # Prefer shorter URLs (often more reliable)
            score -= len(url) // 100
            
            # Prefer channels that are currently selected
            if ch.get("selected", False):
                score += 10
                
            return score
        
        # Sort by score and return the best one
        best_channel = max(channels, key=score_channel)
        
        # Preserve selection state - if any version was selected, keep it selected
        was_selected = any(ch.get("selected", False) for ch in channels)
        best_channel["selected"] = was_selected
        
        return best_channel


def main(page: ft.Page):
    JellyfinTVToolsApp(page)


if __name__ == '__main__':
    ft.app(target=main, view=ft.AppView.FLET_APP)
