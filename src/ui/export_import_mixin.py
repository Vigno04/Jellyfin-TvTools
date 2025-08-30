#!/usr/bin/env python3
"""Export / Import operations for playlists, sessions & channel lists."""
from __future__ import annotations

import json
import os
import time
import glob

from .async_utils import run_background
try:  # Support both package and flat execution contexts
    from backend.config_manager import get_output_path, ensure_output_directory_exists  # type: ignore
except ImportError:  # pragma: no cover - fallback for unusual path setups
    import sys
    import os as _os
    root = _os.path.join(_os.path.dirname(__file__), '..', 'backend')
    if root not in sys.path:
        sys.path.append(root)
    from config_manager import get_output_path, ensure_output_directory_exists  # type: ignore


class ExportImportMixin:
    def export_clicked(self, _):
        def task():
            self.update_status("Exporting selected channels...")
            override = self.processor.config.get('export_override_path') or None
            # ensure parent directory exists if override provided
            if override:
                import os
                try:
                    os.makedirs(os.path.dirname(override) or '.', exist_ok=True)
                except Exception:  # noqa: BLE001
                    pass
            success, msg = self.processor.export_m3u(self.channels, output_path=override, progress_callback=self.update_status)
            self.update_status(msg, is_error=not success)
            if success:
                self.page.snack_bar = self._snack(msg)
                self.page.update()
        run_background(task, before=lambda: self.show_progress(True), after=lambda: self.show_progress(False), name="export-m3u")

    def export_selection_clicked(self, _):
        def task():
            try:
                self.update_status("Exporting session...")
                timestamp = int(time.time())
                backup_file = get_output_path(self.processor.config, "session_backups", str(timestamp))
                ensure_output_directory_exists(self.processor.config, "session_backups")
                session_data = {"channels": self.channels, "playlist_sources": self.playlist_sources, "stream_urls_seen": list(self.stream_urls_seen), "url_field": self.url_field.value}
                with open(backup_file, "w", encoding="utf-8") as f: json.dump(session_data, f, indent=2, ensure_ascii=False)
                msg = f"Session exported to {os.path.basename(backup_file)}"; self.update_status(msg); self.page.snack_bar = self._snack(msg); self.page.update()
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Export failed: {e}", is_error=True)
        run_background(task, before=lambda: self.show_progress(True), after=lambda: self.show_progress(False), name="export-session")

    def import_selection_clicked(self, _):
        def task():
            try:
                self.update_status("Looking for session backup...")
                backup_dir = get_output_path(self.processor.config, "session_backups", "").rsplit(os.sep, 1)[0]
                backups = glob.glob(os.path.join(backup_dir, "session_backup_*.json")) or glob.glob("data/session_backup_*.json")
                if not backups:
                    self.update_status("No session backups found", is_error=True); return
                latest = max(backups, key=os.path.getmtime)
                with open(latest, "r", encoding="utf-8") as f: data = json.load(f)
                self.channels = data.get("channels", []); self.playlist_sources = data.get("playlist_sources", []); self.stream_urls_seen = set(data.get("stream_urls_seen", []))
                if self.channels:
                    self.filtered_channels = self.channels.copy(); self.populate_groups(); self.refresh_channels_display(); self.update_sources_list_text(); self.update_button_states(); self.save_current_session()
                msg = f"Session imported from {os.path.basename(latest)}: {len(self.channels)} channels"; self.update_status(msg); self.page.snack_bar = self._snack(msg); self.page.update()
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Import failed: {e}", is_error=True)
        run_background(task, before=lambda: self.show_progress(True), after=lambda: self.show_progress(False), name="import-session")

    def export_channel_list_clicked(self, _):
        def task():
            try:
                if not self.channels:
                    self.update_status("No channels to export", is_error=True); return
                self.update_status("Exporting channel list...")
                channel_list = [{"name": ch.get("name", ""), "selected": ch.get("selected", False)} for ch in self.channels if ch.get("name")]
                timestamp = int(time.time())
                export_file = get_output_path(self.processor.config, "channel_lists", str(timestamp))
                ensure_output_directory_exists(self.processor.config, "channel_lists")
                export_data = {"exported_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total_channels": len(channel_list), "channels": channel_list}
                with open(export_file, "w", encoding="utf-8") as f: json.dump(export_data, f, indent=2, ensure_ascii=False)
                msg = f"Channel list exported to {os.path.basename(export_file)} ({len(channel_list)} channels)"; self.update_status(msg); self.page.snack_bar = self._snack(msg); self.page.update()
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Channel list export failed: {e}", is_error=True)
        run_background(task, before=lambda: self.show_progress(True), after=lambda: self.show_progress(False), name="export-channel-list")

    def import_channel_list_clicked(self, _):
        if not self.channels:
            self.update_status("Load a playlist before importing channel list", is_error=True); return
        self.update_status("Select a channel list JSON file to import (will auto-optimize first)...")
        try:
            if not hasattr(self, 'channel_list_picker'):
                import flet as ft
                self.channel_list_picker = ft.FilePicker(on_result=self.on_channel_list_file_picked); self.page.overlay.append(self.channel_list_picker)
            self.channel_list_picker.pick_files(allow_multiple=False, allowed_extensions=['json'])
        except Exception as ex:  # noqa: BLE001
            self.update_status(f"File picker failed: {ex}", is_error=True)

    def _close_dialog(self):  # unchanged
        if getattr(self.page, 'dialog', None):
            self.page.dialog.open = False; self.page.update()

    def on_channel_list_file_picked(self, e):  # e: ft.FilePickerResultEvent
        if not e.files:
            self.update_status("Import cancelled", is_error=True); return
        fobj = e.files[0]; path = getattr(fobj, 'path', None)
        if (not path or not os.path.isfile(path)):
            content_bytes = None
            for attr in ('bytes', 'content', 'data'):
                if hasattr(fobj, attr) and getattr(fobj, attr): content_bytes = getattr(fobj, attr); break
            if content_bytes is None and hasattr(fobj, 'read_bytes'):
                try: content_bytes = fobj.read_bytes()
                except Exception: pass  # noqa: BLE001
            if content_bytes:
                os.makedirs('data', exist_ok=True); temp_path = os.path.join('data', '_picked_channel_list.json')
                try:
                    with open(temp_path, 'wb') as tf: tf.write(content_bytes); path = temp_path
                except Exception as ex:  # noqa: BLE001
                    self.update_status(f"Failed saving picked file: {ex}", is_error=True); return
            else:
                self.update_status("Picked file has no accessible path/content", is_error=True); return
        self.update_status(f"Selected channel list file: {os.path.basename(path)}"); self._start_channel_list_import(using_file=path)

    def _start_channel_list_import(self, using_file: str):
        def import_task():
            try:
                if not os.path.isfile(using_file): self.update_status("File not found", is_error=True); return
                if not self.channels: self.update_status("Load a playlist before importing channel list", is_error=True); return
                with open(using_file, 'r', encoding='utf-8') as f: data = json.load(f)
                imported_channels = data.get('channels', [])
                if not imported_channels: self.update_status("No channels in file", is_error=True); return
                imported_map = {}
                for ch in imported_channels:
                    name = ch.get('name', '').strip()
                    if name: imported_map[self.normalize_channel_name(name)] = ch.get('selected', False)
                self.update_status("Optimizing playlist before applying selections (merge+clean+dead)...")
                try:
                    q_removed, u_removed, d_removed = self._optimize_all_core_internal()
                    self.update_status(f"Optimization done: {q_removed} quality + {u_removed} unwanted + {d_removed} dead removed; applying selections...")
                except Exception as op_ex:  # noqa: BLE001
                    self.update_status(f"Optimization failed (continuing import): {op_ex}", is_error=True)
                matches = 0
                for ch in self.channels:
                    n = self.normalize_channel_name(ch.get('name', ''))
                    if n in imported_map:
                        ch['selected'] = imported_map[n]; matches += 1
                self.filtered_channels = self.channels.copy(); self.refresh_channels_display(); self.update_channel_count(); self.save_current_session()
                msg = f"Import complete: applied selections from '{os.path.basename(using_file)}' to {matches} channels"; self.update_status(msg); self.page.snack_bar = self._snack(msg); self.page.update()
            except Exception as ex:  # noqa: BLE001
                self.update_status(f"Import failed: {ex}", is_error=True)
        run_background(import_task, before=lambda: self.show_progress(True), after=lambda: self.show_progress(False), name="import-channel-list")

    # small helper for consistent snackbar styling
    def _snack(self, msg: str):
        import flet as ft
        return ft.SnackBar(ft.Text(msg), open=True, bgcolor=ft.Colors.GREEN_800)
