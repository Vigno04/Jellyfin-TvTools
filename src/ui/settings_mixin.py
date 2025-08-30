#!/usr/bin/env python3
"""Settings panel (slide-out) extracted from main_app for clarity."""
from __future__ import annotations

import flet as ft

try:  # attempt absolute import via backend path already injected in main_app
    from backend.config_manager import save_config  # type: ignore
except ImportError:  # pragma: no cover
    import sys, os as _os
    root = _os.path.join(_os.path.dirname(__file__), '..', 'backend')
    if root not in sys.path:
        sys.path.append(root)
    from config_manager import save_config  # type: ignore


class SettingsMixin:
    def _ensure_settings_overlay(self):
        if hasattr(self, 'settings_overlay'):
            return
        self._settings_controls = {}
        self._settings_backdrop = ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
            on_click=lambda e: self.close_settings(),
        )
        self._settings_panel_column = ft.Column([], spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)
        panel_content = ft.Container(
            width=470,
            bgcolor=ft.Colors.with_opacity(0.97, ft.Colors.BLUE_GREY_900),
            padding=20,
            content=self._settings_panel_column,
        )
        # Add export path picker (shared overlay element)
        if not hasattr(self, 'export_path_picker'):
            self.export_path_picker = ft.FilePicker(on_result=self._on_export_path_picked)
            # ensure single instance in overlay
            if not any(isinstance(o, ft.FilePicker) and o is self.export_path_picker for o in self.page.overlay):
                self.page.overlay.append(self.export_path_picker)

        self.settings_overlay = ft.Container(
            content=ft.Row([self._settings_backdrop, panel_content], spacing=0),
            visible=False,
            expand=True,
        )
        self.page.overlay.append(self.settings_overlay); self.page.update()
        def on_keyboard(e: ft.KeyboardEvent):
            if e.key == "Escape" and self.settings_overlay.visible:
                self.close_settings()
        self.page.on_keyboard_event = on_keyboard

    def _build_settings_form(self):  # called fresh each open
        cfg = self.processor.config; qm = cfg.get('quality_management', {})
        def label(text): return ft.Text(text, size=12, weight=ft.FontWeight.BOLD)
        def help_text(text): return ft.Text(text, size=11, color=ft.Colors.GREY_500)
        self.setting_download_url = ft.TextField(label="Download URL", value=cfg.get('download_url',''), dense=True, tooltip="Primary M3U playlist URL to download channels from")
        self.setting_auto_select = ft.Switch(label="Auto-select filtering enabled", value=cfg.get('auto_select_enabled', True), tooltip="Apply filters automatically on load (when enabled)")
        self.setting_keep_groups = ft.TextField(
            label="Keep Groups (comma separated)",
            value=",".join(cfg.get('keep_groups', [])),
            dense=True,
            tooltip="Only keep channels from these groups. Leave empty to keep all groups."
        )
        self.setting_exclude_groups = ft.TextField(
            label="Exclude Groups (comma separated)",
            value=",".join(cfg.get('exclude_groups', [])),
            dense=True,
            tooltip="Always exclude channels from these groups, even if they match other criteria."
        )
        self.setting_force_keep_channels = ft.TextField(
            label="Force Keep Channels",
            value=",".join(cfg.get('force_keep_channels', [])),
            dense=True,
            tooltip="Always keep these specific channel names, regardless of other filters."
        )
        self.setting_force_exclude_channels = ft.TextField(
            label="Force Exclude Channels",
            value=",".join(cfg.get('force_exclude_channels', [])),
            dense=True,
            tooltip="Always exclude these specific channel names, regardless of other filters."
        )
        self.setting_exclude_patterns = ft.TextField(
            label="Exclude Patterns (regex, one per line)",
            value="\n".join(cfg.get('exclude_patterns', [])),
            multiline=True,
            min_lines=3,
            max_lines=6,
            dense=True,
            tooltip="Regex patterns to exclude channels. Common patterns: .*test.*, .*backup.*, .*temp.*"
        )
        base_dir = cfg.get('output_directories', {}).get('base_output_dir', 'data')
        self.setting_base_output_dir = ft.TextField(
            label="Base Output Directory",
            value=base_dir,
            dense=True,
            tooltip="Base directory for all exports, backups, and session files. Can be relative or absolute path."
        )
        self.setting_prioritize_stream_analysis = ft.Switch(
            label="Prioritize Stream Analysis",
            value=qm.get('prioritize_stream_analysis', True),
            tooltip="Use actual stream probing over name-based quality detection for better accuracy."
        )
        self.setting_use_name_quality = ft.Switch(
            label="Use Name-based Quality",
            value=qm.get('use_name_based_quality', False),
            tooltip="Detect quality from channel names (HD, 4K suffixes). Less reliable than stream analysis."
        )
        self.setting_exclude_lower_quality = ft.Switch(
            label="Exclude Lower Quality Duplicates",
            value=qm.get('exclude_lower_quality', True),
            tooltip="When merging duplicates, keep only the highest quality version of each channel."
        )
        self.setting_normalize_names = ft.Switch(
            label="Normalize Channel Names",
            value=qm.get('normalize_channel_names', True),
            tooltip="Remove quality suffixes and standardize names for better duplicate detection."
        )
        self.setting_use_quality_cache = ft.Switch(
            label="Use Stream Quality Cache",
            value=qm.get('use_stream_quality_cache', False),
            tooltip="Cache stream quality results to speed up repeated operations. May use stale data."
        )
        self.setting_use_range_header = ft.Switch(
            label="Use HTTP Range Header",
            value=qm.get('use_range_header', False),
            tooltip="Use HTTP Range requests for partial downloads. Some servers may not support this."
        )
        self.setting_max_parallel = ft.TextField(
            label="Max Parallel Stream Probes",
            value=str(qm.get('max_parallel_stream_probes', 12)),
            dense=True,
            tooltip="Number of streams to probe simultaneously. Higher = faster but more network load."
        )
        self.setting_probe_bytes = ft.TextField(
            label="Max Probe Bytes",
            value=str(qm.get('max_stream_probe_bytes', 16384)),
            dense=True,
            tooltip="Maximum bytes to download when checking stream quality. Lower = faster but less accurate."
        )
        # --- Export override section ------------------------------------
        self.setting_export_override_switch = ft.Switch(
            label="Use Custom Export Path",
            value=bool(cfg.get('export_override_path')),
            tooltip="When enabled, exported M3U will be written to the custom file instead of default timestamped path."
        )
        self.setting_export_override_path = ft.TextField(
            label="Custom Export File (.m3u)",
            value=cfg.get('export_override_path', ''),
            dense=True,
            read_only=True,
            tooltip="Full path to export file. Click 'Choose File' to set."
        )
        choose_export_btn = ft.OutlinedButton(
            "Choose File...",
            icon=ft.Icons.FOLDER_OPEN,
            tooltip="Pick / name the export .m3u file (existing file will be overwritten).",
            on_click=lambda e: self.export_path_picker.save_file(file_name='channels.m3u') if hasattr(self.export_path_picker, 'save_file') else self.export_path_picker.pick_files(allow_multiple=False)
        )
        clear_export_btn = ft.TextButton(
            "Clear",
            icon=ft.Icons.CLEAR,
            tooltip="Clear custom export path and revert to default behavior.",
            on_click=lambda e: self._clear_export_override()
        )
        self._export_buttons_row = ft.Row([choose_export_btn, clear_export_btn], spacing=8)
        save_btn = ft.FilledButton("Save & Apply", icon=ft.Icons.SAVE, on_click=self.save_settings); close_btn = ft.OutlinedButton("Close", icon=ft.Icons.CLOSE, on_click=lambda e: self.close_settings())
        sections = [
            ft.Row([ft.Text("Settings", size=22, weight=ft.FontWeight.BOLD), ft.IconButton(icon=ft.Icons.CLOSE, tooltip="Close", on_click=lambda e: self.close_settings())], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), margin=ft.margin.symmetric(vertical=8)),
            label("General"), self.setting_download_url, self.setting_auto_select, self.setting_keep_groups, self.setting_exclude_groups, self.setting_force_keep_channels, self.setting_force_exclude_channels, self.setting_exclude_patterns,
            ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE), margin=ft.margin.symmetric(vertical=8)),
            label("Output"), self.setting_base_output_dir, help_text("Affects future exports & backups."),
            ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE), margin=ft.margin.symmetric(vertical=8)),
            label("Export Options"),
            self.setting_export_override_switch,
            self.setting_export_override_path,
            self._export_buttons_row,
            ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE), margin=ft.margin.symmetric(vertical=8)),
            label("Quality Management"), self.setting_prioritize_stream_analysis, self.setting_use_name_quality, self.setting_exclude_lower_quality, self.setting_normalize_names, self.setting_use_quality_cache, self.setting_use_range_header,
            ft.Row([self.setting_max_parallel, self.setting_probe_bytes], spacing=12), help_text("Quality options affect merging & optimization."),
            ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE), margin=ft.margin.symmetric(vertical=12)),
            ft.Row([save_btn, close_btn], spacing=14), help_text("Some changes need re-download to apply."),
        ]
        self._settings_panel_column.controls = sections; self._settings_panel_column.update()
        # wire enable/disable behavior
        self.setting_export_override_switch.on_change = lambda e: self._update_export_override_enabled()
        self._update_export_override_enabled()

    def _update_export_override_enabled(self):
        enabled = self.setting_export_override_switch.value
        self.setting_export_override_path.disabled = not enabled
        for b in self._export_buttons_row.controls:
            b.disabled = not enabled
        self.setting_export_override_path.update(); self._export_buttons_row.update()

    def _clear_export_override(self):
        self.setting_export_override_path.value = ''
        self.setting_export_override_switch.value = False
        self._update_export_override_enabled()
        self._settings_panel_column.update()

    def _on_export_path_picked(self, e: ft.FilePickerResultEvent):
        # For save_file result, path is e.path; for pick_files we use first file path
        path = getattr(e, 'path', None)
        if not path and getattr(e, 'files', None):
            f0 = e.files[0]
            path = getattr(f0, 'path', None)
        if path:
            if not path.lower().endswith('.m3u'):
                path += '.m3u'
            self.setting_export_override_path.value = path
            self.setting_export_override_switch.value = True
            self._update_export_override_enabled()
            self.update_status(f"Custom export path set: {path}")
            self._settings_panel_column.update()
        else:
            self.update_status("Export path selection cancelled", is_error=True)

    def save_settings(self, _):
        cfg = self.processor.config; qm = cfg.setdefault('quality_management', {})
        def csv_list(v): return [x.strip() for x in v.split(',') if x.strip()] if v.strip() else []
        def lines_list(v): return [l.strip() for l in v.splitlines() if l.strip()]
        cfg['download_url'] = self.setting_download_url.value.strip() or cfg.get('download_url')
        cfg['auto_select_enabled'] = self.setting_auto_select.value
        cfg['keep_groups'] = csv_list(self.setting_keep_groups.value)
        cfg['exclude_groups'] = csv_list(self.setting_exclude_groups.value)
        cfg['force_keep_channels'] = csv_list(self.setting_force_keep_channels.value)
        cfg['force_exclude_channels'] = csv_list(self.setting_force_exclude_channels.value)
        cfg['exclude_patterns'] = lines_list(self.setting_exclude_patterns.value)
        cfg.setdefault('output_directories', {})['base_output_dir'] = self.setting_base_output_dir.value.strip() or 'data'
        # Export override
        if self.setting_export_override_switch.value and self.setting_export_override_path.value.strip():
            cfg['export_override_path'] = self.setting_export_override_path.value.strip()
        else:
            cfg.pop('export_override_path', None)
        qm['prioritize_stream_analysis'] = self.setting_prioritize_stream_analysis.value
        qm['use_name_based_quality'] = self.setting_use_name_quality.value
        qm['exclude_lower_quality'] = self.setting_exclude_lower_quality.value
        qm['normalize_channel_names'] = self.setting_normalize_names.value
        qm['use_stream_quality_cache'] = self.setting_use_quality_cache.value
        qm['use_range_header'] = self.setting_use_range_header.value
        try: qm['max_parallel_stream_probes'] = int(self.setting_max_parallel.value.strip())
        except Exception: pass  # noqa: BLE001
        try: qm['max_stream_probe_bytes'] = int(self.setting_probe_bytes.value.strip())
        except Exception: pass  # noqa: BLE001
        ok = save_config(self.processor.config_path, cfg); msg = "Settings saved" if ok else "Failed to save settings"
        self.update_status(msg, is_error=not ok)
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), open=True, bgcolor=ft.Colors.GREEN_800 if ok else ft.Colors.RED_800); self.page.update()

    def open_settings(self, _):
        self._ensure_settings_overlay(); self._build_settings_form()
        if self.settings_overlay.visible: return
        self.settings_overlay.visible = True; self.page.update()

    def close_settings(self):
        if hasattr(self, 'settings_overlay') and self.settings_overlay.visible:
            self.settings_overlay.visible = False; self.page.update()
