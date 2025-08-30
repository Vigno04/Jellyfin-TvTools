#!/usr/bin/env python3
"""Optimization operations: quality merge, remove unwanted/dead, combined optimize."""
from __future__ import annotations

from .async_utils import run_background


class OptimizationMixin:
    def merge_quality_clicked(self, _):
        if not self.channels:
            return
        def task():
            self.update_status("Merging quality duplicates (probing streams)...")
            self.progress_bar.value = 0; self.progress_bar.visible = True
            merged, removed = self.processor.merge_quality(self.channels, progress_callback=self.update_status)
            self.channels = merged; self.filtered_channels = merged.copy(); self.merged_count = removed
            self.refresh_channels_display(); self.update_quality_info(); self.save_current_session(); self.update_status(f"Quality merge complete: {removed} removed")
        def after():
            self.merge_quality_button.disabled = False; self.remove_dead_button.disabled = False; self.progress_bar.visible = False; self.progress_bar.value = None; self.page.update()
        run_background(task, before=lambda: setattr(self.merge_quality_button, 'disabled', True), after=after, name="merge-quality")

    def remove_dead_clicked(self, _):
        if not self.channels:
            return
        def task():
            self.update_status("Checking streams for dead links...")
            self.progress_bar.value = 0; self.progress_bar.visible = True
            alive, removed, _ = self.processor.remove_dead_streams(self.channels, progress_callback=self.update_status)
            self.channels = alive; self.filtered_channels = alive.copy()
            self.refresh_channels_display(); self.save_current_session(); self.update_status(f"Link check complete – {removed} removed")
        def after():
            self.remove_dead_button.disabled = False; self.merge_quality_button.disabled = False; self.progress_bar.visible = False; self.progress_bar.value = None; self.page.update()
        run_background(task, before=lambda: [setattr(self.remove_dead_button,'disabled',True), setattr(self.merge_quality_button,'disabled',True)], after=after, name="remove-dead")

    def remove_unwanted_clicked(self, _):
        if not self.channels:
            return
        def task():
            self.update_status("Removing test and unwanted channels...")
            self.progress_bar.value = 0; self.progress_bar.visible = True
            clean, removed, _ = self.processor.remove_unwanted_channels(self.channels, progress_callback=self.update_status)
            self.channels = clean; self.filtered_channels = clean.copy()
            self.refresh_channels_display(); self.save_current_session(); self.update_status(f"Unwanted channels removed: {removed} filtered out")
        def after():
            self.remove_unwanted_button.disabled = False; self.progress_bar.visible = False; self.progress_bar.value = None; self.page.update()
        run_background(task, before=lambda: setattr(self.remove_unwanted_button, 'disabled', True), after=after, name="remove-unwanted")

    def optimize_all_clicked(self, _):
        if not self.channels:
            return
        def task():
            try:
                self.progress_bar.value = 0; self.progress_bar.visible = True
                rq, ru, rd = self._optimize_all_core_internal(); self.merged_count = rq; self.save_current_session(); self.update_status(f"Optimization complete: {rq} quality + {ru} unwanted + {rd} dead removed")
            except Exception as e:  # noqa: BLE001
                self.update_status(f"Optimization failed: {e}", is_error=True)
        def before():
            for b in (self.merge_quality_button, self.remove_dead_button, self.remove_unwanted_button, self.optimize_all_button):
                b.disabled = True
            self.page.update()
        def after():
            for b in (self.merge_quality_button, self.remove_dead_button, self.remove_unwanted_button, self.optimize_all_button):
                b.disabled = False
            self.progress_bar.visible = False; self.progress_bar.value = None; self.page.update()
        run_background(task, before=before, after=after, name="optimize-all")

    # Internal core sequence (unchanged behavior)
    def _optimize_all_core_internal(self):
        removed_quality = removed_unwanted = removed_dead = 0
        self.update_status("Optimizing: merging quality duplicates...")
        merged, removed_quality = self.processor.merge_quality(self.channels, progress_callback=self.update_status)
        self.channels = merged; self.filtered_channels = merged.copy(); self.refresh_channels_display(); self.update_quality_info()
        self.update_status("Optimizing: removing unwanted/test channels...")
        clean, removed_unwanted, _uw = self.processor.remove_unwanted_channels(self.channels, progress_callback=self.update_status)
        self.channels = clean; self.filtered_channels = clean.copy(); self.refresh_channels_display()
        self.update_status("Optimizing: checking dead streams...")
        alive, removed_dead, _dead = self.processor.remove_dead_streams(self.channels, progress_callback=self.update_status)
        self.channels = alive; self.filtered_channels = alive.copy(); self.refresh_channels_display()
        return removed_quality, removed_unwanted, removed_dead
