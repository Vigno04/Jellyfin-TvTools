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
# Newly factored mixins
from .session_status_mixin import SessionStatusMixin  # noqa: E402
from .playlist_mixin import PlaylistMixin  # noqa: E402
from .channels_mixin import ChannelsMixin  # noqa: E402
from .optimization_mixin import OptimizationMixin  # noqa: E402
from .export_import_mixin import ExportImportMixin  # noqa: E402
from .settings_mixin import SettingsMixin  # noqa: E402
from .manual_merge_mixin import ManualMergeMixin  # noqa: E402


class JellyfinTVToolsApp(
    GroupManagerMixin,
    SessionStatusMixin,
    PlaylistMixin,
    ChannelsMixin,
    OptimizationMixin,
    ExportImportMixin,
    SettingsMixin,
    ManualMergeMixin,
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
        self.load_saved_button = None

        # Summary metrics (populated during build_ui)
        self.summary_total_text = None
        self.summary_selected_text = None
        self.summary_playlists_text = None

        # Multi-playlist aggregation
        self.playlist_sources = []  # list of {url, channels_added, skipped}
        self.stream_urls_seen = set()

        # Selection and display state
        self.show_only_selected = False
        self.quality_selected_count = 0
        self.merged_count = 0

        # Initialize group management state
        self.init_group_state()
        
        # Initialize manual merge state
        ManualMergeMixin.__init__(self)

        # Session persistence - pass config for output directory settings
        self.session_manager = SessionManager(config=self.processor.config)

        # Build the UI
        self.build_ui()
        
        # Load previous session if available
        self.load_saved_session()

    def build_ui(self):
        self._configure_page()

        header = self._build_header()
        summary_row = self._build_summary_row()
        left_column = self._build_left_column()
        right_column = self._build_right_column()

        body = ft.ResponsiveRow(
            controls=[
                ft.Container(left_column, col={"sm": 12, "md": 5, "lg": 4}),
                ft.Container(right_column, col={"sm": 12, "md": 7, "lg": 8}),
            ],
            run_spacing=18,
            alignment=ft.MainAxisAlignment.START,
        )

        layout = ft.Column(
            controls=[header, summary_row, body],
            spacing=18,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        wrapper = ft.Container(
            content=layout,
            expand=True,
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
        )

        self.page.add(wrapper)

        # Resize handler keeps channel list height responsive
        def on_resize(_):
            reserved = 440
            if self.channels_list:
                self.channels_list.height = max(240, self.page.window_height - reserved)
                if hasattr(self, 'channel_list_component'):
                    self.channel_list_component.list_view.update()
            self.page.update()

        self.page.on_resize = on_resize
        on_resize(None)

        # Attach file picker for channel list import (created lazily in mixin if needed)
        if not hasattr(self, 'channel_list_picker'):
            self.channel_list_picker = ft.FilePicker(on_result=self.on_channel_list_file_picked)
            if not any(isinstance(o, ft.FilePicker) for o in self.page.overlay):
                self.page.overlay.append(self.channel_list_picker)
            self.page.update()

        # Ensure settings overlay via mixin
        self._ensure_settings_overlay()

    # --- UI Builders -----------------------------------------------------
    def _configure_page(self):
        self.page.title = "Jellyfin TV Tools"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY, use_material3=True)
        self.page.window_width = 1320
        self.page.window_height = 860
        self.page.window_min_width = 1080
        self.page.window_min_height = 680

    def _build_header(self) -> ft.Container:
        title_block = ft.Row(
            controls=[
                ft.Icon(ft.Icons.TV, size=44, color=ft.Colors.CYAN_ACCENT_400),
                ft.Column(
                    controls=[
                        ft.Text("Jellyfin TV Tools", size=26, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Manage and curate IPTV playlists with confidence",
                            size=14,
                            color=ft.Colors.GREY_400,
                        ),
                    ],
                    spacing=2,
                ),
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.START,
        )

        actions = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.HELP_OUTLINE,
                    tooltip="Open documentation",
                    on_click=lambda _e: self.update_status("Documentation coming soon", is_error=False),
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    tooltip="Settings",
                    on_click=self.open_settings,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            ],
            spacing=6,
        )

        return ft.Container(
            content=ft.Row(
                controls=[title_block, actions],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=18, vertical=16),
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            border_radius=16,
        )

    def _build_summary_row(self) -> ft.Control:
        self.summary_total_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD)
        self.summary_selected_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_ACCENT_200)
        self.summary_playlists_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD)

        summary_cards = ft.ResponsiveRow(
            controls=[
                self._summary_card(ft.Icons.LAYERS, "Total channels", self.summary_total_text, "Loaded across all playlists"),
                self._summary_card(ft.Icons.CHECK_CIRCLE, "Selected", self.summary_selected_text, "Included in export"),
                self._summary_card(ft.Icons.CLOUD, "Playlists", self.summary_playlists_text, "Active sources"),
            ],
            run_spacing=12,
            alignment=ft.MainAxisAlignment.START,
        )
        return summary_cards

    def _summary_card(self, icon: str, title: str, value_control: ft.Text, subtitle: str) -> ft.Container:
        accent = ft.Colors.with_opacity(0.08, ft.Colors.CYAN_200)
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Icon(icon, size=26, color=ft.Colors.CYAN_ACCENT_400),
                                padding=ft.padding.all(10),
                                bgcolor=accent,
                                border_radius=12,
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(title.upper(), size=11, color=ft.Colors.GREY_400, weight=ft.FontWeight.W_500),
                                    value_control,
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=12,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Text(subtitle, size=12, color=ft.Colors.GREY_500),
                ],
                spacing=10,
            ),
            padding=ft.padding.symmetric(horizontal=18, vertical=16),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14,
            col={"sm": 12, "md": 4, "lg": 3},
        )

    def _build_left_column(self) -> ft.Column:
        sources_card = self._build_sources_card()
        status_card = self._build_status_card()
        export_card = self._build_export_card()
        return ft.Column(
            controls=[sources_card, status_card, export_card],
            spacing=16,
            expand=True,
        )

    def _build_right_column(self) -> ft.Column:
        channels_card = self._build_channels_card()
        return ft.Column(
            controls=[channels_card],
            spacing=16,
            expand=True,
        )

    def _build_sources_card(self) -> ft.Container:
        # Get first saved playlist as default or fallback to legacy download_url
        saved_playlists = self.processor.config.get("saved_playlists", [])
        default_url = saved_playlists[0] if saved_playlists else self.processor.config.get("download_url", "")
        
        self.url_field = ft.TextField(
            label="Playlist URL (or pick from saved list)",
            value=default_url,
            prefix_icon=ft.Icons.LINK,
            dense=True,
            border_radius=12,
            autofocus=False,
            expand=True,
        )

        self.load_button = ft.FilledButton(
            "Download playlist",
            icon=ft.Icons.CLOUD_DOWNLOAD,
            on_click=self.add_playlist_clicked,
        )
        self.load_saved_button = ft.OutlinedButton(
            "Load saved playlists",
            icon=ft.Icons.LIBRARY_ADD_CHECK,
            on_click=self.load_saved_playlists_clicked,
        )
        self.merge_quality_button = ft.OutlinedButton(
            "Merge quality duplicates",
            icon=ft.Icons.HIGH_QUALITY,
            on_click=self.merge_quality_clicked,
            disabled=True,
        )
        self.remove_dead_button = ft.OutlinedButton(
            "Remove dead streams",
            icon=ft.Icons.DELETE_SWEEP,
            on_click=self.remove_dead_clicked,
            disabled=True,
        )
        self.remove_unwanted_button = ft.OutlinedButton(
            "Remove unwanted",
            icon=ft.Icons.FILTER_ALT_OFF,
            on_click=self.remove_unwanted_clicked,
            disabled=True,
        )
        self.optimize_all_button = ft.FilledTonalButton(
            "Optimize everything",
            icon=ft.Icons.AUTO_FIX_HIGH,
            on_click=self.optimize_all_clicked,
            disabled=True,
        )
        self.quality_info_text = ft.Text("", size=11, color=ft.Colors.CYAN_ACCENT_200)
        self.sources_list_text = ft.Text("No playlists added", size=12, color=ft.Colors.GREY_400)
        self.clear_sources_btn = ft.TextButton(
            "Clear all",
            icon=ft.Icons.CLEAR_ALL,
            on_click=self.clear_all_sources_clicked,
            disabled=True,
        )
        self.refresh_sources_btn = ft.TextButton(
            "Refresh all",
            icon=ft.Icons.REFRESH,
            on_click=self.refresh_all_sources_clicked,
            disabled=True,
        )

        quick_actions = ft.ResponsiveRow(
            controls=[
                ft.Container(self.load_button, col={"sm": 12, "md": 12, "lg": 12}),
                ft.Container(self.load_saved_button, col={"sm": 12, "md": 12, "lg": 12}),
                ft.Container(self.merge_quality_button, col={"sm": 12, "md": 12, "lg": 6}),
                ft.Container(self.remove_dead_button, col={"sm": 12, "md": 12, "lg": 6}),
                ft.Container(self.remove_unwanted_button, col={"sm": 12, "md": 12, "lg": 6}),
                ft.Container(self.optimize_all_button, col={"sm": 12, "md": 12, "lg": 6}),
            ],
            run_spacing=10,
        )

        sources_header = ft.Row(
            controls=[
                ft.Text("Sources", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[self.refresh_sources_btn, self.clear_sources_btn],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        card = ft.Container(
            content=ft.Column(
                controls=[
                    sources_header,
                    ft.Row([self.sources_list_text], alignment=ft.MainAxisAlignment.START),
                    ft.Row([self.url_field], alignment=ft.MainAxisAlignment.START),
                    quick_actions,
                    self.quality_info_text,
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14,
        )

        # Set initial button state after controls are created (before adding to page)
        self.update_saved_playlist_button_state()
        return card

    def _build_status_card(self) -> ft.Container:
        self.progress_bar = ft.ProgressBar(visible=False, bar_height=8, color=ft.Colors.CYAN_ACCENT_400)
        self.status_text = ft.Text("Ready", size=12, color=ft.Colors.GREY_400)

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Text("Activity & status", size=18, weight=ft.FontWeight.BOLD),
                        ft.Icon(ft.Icons.PLAYLIST_PLAY, color=ft.Colors.CYAN_ACCENT_400),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(
                        "Keep an eye on long operations such as quality merges and link checks.",
                        size=11,
                        color=ft.Colors.GREY_500,
                    ),
                    self.progress_bar,
                    self.status_text,
                ],
                spacing=10,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14,
        )

    def _build_channels_card(self) -> ft.Container:
        self.search_field = ft.TextField(
            label="Search channels or groups",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self.on_search_changed,
            border_radius=30,
            dense=True,
            expand=True,
        )
        self.select_all_button = ft.OutlinedButton(
            "Select all",
            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            on_click=self.select_all_clicked,
        )
        self.select_none_button = ft.OutlinedButton(
            "Clear selection",
            icon=ft.Icons.CANCEL_OUTLINED,
            on_click=self.select_none_clicked,
        )
        self.toggle_selected_button = ft.OutlinedButton(
            "Show selected",
            icon=ft.Icons.FILTER_LIST,
            on_click=self.toggle_show_selected,
        )
        self.channel_count_text = ft.Text("0 selected | 0 total", size=12, color=ft.Colors.GREY_400)

        controls_row = ft.ResponsiveRow(
            controls=[
                ft.Container(self.search_field, col={"sm": 12, "md": 7, "lg": 6}),
                ft.Container(
                    ft.Row(
                        [self.select_all_button, self.select_none_button, self.toggle_selected_button],
                        spacing=8,
                        wrap=True,
                    ),
                    col={"sm": 12, "md": 5, "lg": 4},
                ),
                ft.Container(
                    self.channel_count_text,
                    alignment=ft.alignment.center_right,
                    col={"sm": 12, "md": 12, "lg": 2},
                ),
            ],
            run_spacing=10,
            alignment=ft.MainAxisAlignment.START,
        )

        self.channel_list_component = ChannelListView(
            on_toggle_channel=self.toggle_channel_click,
            on_checkbox_change=lambda ch, val: self.on_channel_checkbox_change(ch, val),
            on_request_merge=self.open_manual_merge_dialog,
        )
        self.channels_list = self.channel_list_component.control()

        self.groups_list = ft.ListView(
            height=220,
            spacing=4,
            padding=ft.padding.symmetric(horizontal=4, vertical=4),
        )
        self.visibility_toggle_btn = ft.OutlinedButton(
            "Hide all",
            icon=ft.Icons.VISIBILITY_OFF,
            on_click=self.toggle_all_visibility,
        )

        groups_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Groups", size=16, weight=ft.FontWeight.BOLD),
                            self.visibility_toggle_btn,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        "Toggle visibility or bulk include channels per group to sculpt your playlist.",
                        size=11,
                        color=ft.Colors.GREY_500,
                    ),
                    self.groups_list,
                ],
                spacing=8,
            ),
            padding=ft.padding.all(14),
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            border_radius=12,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Channels", size=18, weight=ft.FontWeight.BOLD),
                    controls_row,
                    groups_section,
                    ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
                    self.channels_list,
                ],
                spacing=14,
            ),
            padding=ft.padding.symmetric(horizontal=22, vertical=20),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14,
        )

    def _build_export_card(self) -> ft.Container:
        self.export_button = ft.FilledButton(
            "Export playlist",
            icon=ft.Icons.PLAYLIST_ADD_CHECK_CIRCLE,
            on_click=self.export_clicked,
            disabled=True,
        )
        self.export_selection_button = ft.OutlinedButton(
            "Export session",
            icon=ft.Icons.BACKUP,
            on_click=self.export_selection_clicked,
        )
        self.export_channel_list_button = ft.OutlinedButton(
            "Export channel list",
            icon=ft.Icons.LIST_ALT,
            on_click=self.export_channel_list_clicked,
        )
        self.import_selection_button = ft.OutlinedButton(
            "Restore session",
            icon=ft.Icons.RESTORE,
            on_click=self.import_selection_clicked,
        )
        self.import_channel_list_button = ft.OutlinedButton(
            "Import channel list",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self.import_channel_list_clicked,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Backups & exports", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Keep your curated selections safe or share them with other Jellyfin servers.",
                        size=11,
                        color=ft.Colors.GREY_500,
                    ),
                    ft.Row(
                        [self.export_button, self.export_selection_button, self.export_channel_list_button],
                        spacing=12,
                        wrap=True,
                    ),
                    ft.Row(
                        [self.import_selection_button, self.import_channel_list_button],
                        spacing=12,
                        wrap=True,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=18),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            border_radius=14,
        )

    # settings methods moved to SettingsMixin

    # (All operational methods moved to dedicated mixins for clarity.)

    # playlist management, channel selection, optimization, export/import moved

    # playlist methods moved to PlaylistMixin

    # NOTE: Channel management, optimization, and export/import methods live in mixins.
    # Duplicated implementations once present here were removed to avoid drift.


def main(page: ft.Page):
    """Initialize and run the Jellyfin TV Tools application.
    
    Args:
        page: The Flet page object provided by ft.app()
    """
    JellyfinTVToolsApp(page)

