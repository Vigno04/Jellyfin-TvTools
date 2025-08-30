#!/usr/bin/env python3
"""Modern dark UI for Jellyfin TV Tools (Flet)."""

import os
import sys
# Removed unused threading/time/json imports after refactor into mixins
import flet as ft

# Add backend path to sys.path to ensure imports work
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.m3u_processor import M3UProcessor  # noqa: E402
# Removed unused backend config imports; handled within respective mixins
from .session_manager import SessionManager  # noqa: E402
from .group_manager import GroupManagerMixin  # noqa: E402
from .channel_list import ChannelListView  # noqa: E402
from .async_utils import run_background  # noqa: E402
# Newly factored mixins
from .session_status_mixin import SessionStatusMixin  # noqa: E402
from .playlist_mixin import PlaylistMixin  # noqa: E402
from .channels_mixin import ChannelsMixin  # noqa: E402
from .optimization_mixin import OptimizationMixin  # noqa: E402
from .export_import_mixin import ExportImportMixin  # noqa: E402
from .settings_mixin import SettingsMixin  # noqa: E402


class JellyfinTVToolsApp(
    GroupManagerMixin,
    SessionStatusMixin,
    PlaylistMixin,
    ChannelsMixin,
    OptimizationMixin,
    ExportImportMixin,
    SettingsMixin,
):
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

        # Session persistence - pass config for output directory settings
        self.session_manager = SessionManager(config=self.processor.config)

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

    # Header section with Settings button
        header = ft.Container(
            ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.TV, size=44, color=ft.Colors.CYAN_ACCENT_400),
                    ft.Column([
                        ft.Text("Jellyfin TV Tools", size=26, weight=ft.FontWeight.BOLD),
                        ft.Text("IPTV Playlist & Guide Manager", size=14, color=ft.Colors.GREY_400)
                    ], spacing=2)
                ], spacing=16),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    tooltip="Settings",
            on_click=self.open_settings,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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

        # Attach file picker for channel list import (created lazily in mixin if needed)
        if not hasattr(self, 'channel_list_picker'):
            self.channel_list_picker = ft.FilePicker(on_result=self.on_channel_list_file_picked)
            if not any(isinstance(o, ft.FilePicker) for o in self.page.overlay):
                self.page.overlay.append(self.channel_list_picker)
            self.page.update()
        # Ensure settings overlay via mixin
        self._ensure_settings_overlay()

    # settings methods moved to SettingsMixin

    # (All operational methods moved to dedicated mixins for clarity.)

    # playlist management, channel selection, optimization, export/import moved

    # playlist methods moved to PlaylistMixin

    # NOTE: Channel management, optimization, and export/import methods live in mixins.
    # Duplicated implementations once present here were removed to avoid drift.


def main(page: ft.Page):
    JellyfinTVToolsApp(page)


if __name__ == '__main__':
    ft.app(target=main, view=ft.AppView.FLET_APP)
