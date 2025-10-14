#!/usr/bin/env python3
"""Manual channel merge dialog and operations."""
from __future__ import annotations

import flet as ft
from typing import TYPE_CHECKING, Any, List, Dict

if TYPE_CHECKING:  # pragma: no cover - hinting support only
    pass

Channel = Dict[str, Any]


class ManualMergeMixin:
    page: Any
    channels: List[Channel]
    filtered_channels: List[Channel]
    refresh_channels_display: Any
    save_current_session: Any
    update_status: Any

    def __init__(self):
        self.merge_dialog = None
        self.merge_source_channel = None
        self.merge_target_dropdown = None
        self.merge_confirm_button = None
        self.merge_search_field = None
        self.merge_all_targets = []  # Cache of all target options
        self.merge_max_initial_options = 100  # Limit initial dropdown size for performance

    def open_manual_merge_dialog(self, source_channel: Channel):
        """Open the manual merge dialog with the selected source channel."""
        self.merge_source_channel = source_channel
        
        # Build list of potential target channels (exclude source)
        self.merge_all_targets = [
            (i, ch)
            for i, ch in enumerate(self.channels)
            if ch is not source_channel
        ]
        
        # Only load first N options initially for performance
        initial_targets = self.merge_all_targets[:self.merge_max_initial_options]
        target_options = [
            ft.dropdown.Option(key=str(i), text=ch['name'])
            for i, ch in initial_targets
        ]
        
        # Add hint if there are more channels
        if len(self.merge_all_targets) > self.merge_max_initial_options:
            target_options.append(
                ft.dropdown.Option(
                    key="__hint__",
                    text=f"--- Use search to find from {len(self.merge_all_targets)} channels ---",
                    disabled=True
                )
            )
        
        self.merge_search_field = ft.TextField(
            label="Search channels...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_merge_search_changed,
            width=500,
        )
        
        self.merge_target_dropdown = ft.Dropdown(
            label="Select target channel to merge into",
            options=target_options,
            width=500,
            on_change=self._on_target_selected,
        )
        
        self.merge_confirm_button = ft.ElevatedButton(
            "Merge Channels",
            icon=ft.Icons.MERGE,
            on_click=self._confirm_merge,
            disabled=True,
        )
        
        self.merge_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Manual Channel Merge"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Source channel:", weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(
                                source_channel['name'],
                                size=16,
                                color=ft.Colors.CYAN_ACCENT_400,
                            ),
                            padding=ft.padding.symmetric(horizontal=10, vertical=8),
                            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                            border_radius=8,
                        ),
                        ft.Container(height=10),
                        ft.Text("will be merged into:", size=12, color=ft.Colors.GREY_400),
                        ft.Container(height=5),
                        self.merge_search_field,
                        ft.Container(height=5),
                        self.merge_target_dropdown,
                        ft.Container(height=10),
                        ft.Text(
                            "⚠️ The source channel will be removed and its URL/metadata "
                            "will be transferred to the target channel if better quality.",
                            size=11,
                            color=ft.Colors.ORANGE_300,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                width=500,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_merge_dialog),
                self.merge_confirm_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(self.merge_dialog)
        self.merge_dialog.open = True
        self.page.update()

    def _on_merge_search_changed(self, e):
        """Filter dropdown options based on search term."""
        search_term = e.control.value.lower().strip()
        
        if search_term:
            # Filter targets by search term - limit results for performance
            filtered_targets = [
                (i, ch)
                for i, ch in self.merge_all_targets
                if search_term in ch['name'].lower()
            ][:200]  # Limit to 200 results max
        else:
            # Show initial limited set when no search
            filtered_targets = self.merge_all_targets[:self.merge_max_initial_options]
        
        # Update dropdown options
        self.merge_target_dropdown.options = [
            ft.dropdown.Option(key=str(i), text=ch['name'])
            for i, ch in filtered_targets
        ]
        
        # Add hint if results were limited
        if search_term and len(filtered_targets) == 200:
            self.merge_target_dropdown.options.append(
                ft.dropdown.Option(
                    key="__hint__",
                    text="--- More results available, refine search ---",
                    disabled=True
                )
            )
        elif not search_term and len(self.merge_all_targets) > self.merge_max_initial_options:
            self.merge_target_dropdown.options.append(
                ft.dropdown.Option(
                    key="__hint__",
                    text=f"--- Use search to find from {len(self.merge_all_targets)} channels ---",
                    disabled=True
                )
            )
        
        # Reset selection if current selection is filtered out
        if self.merge_target_dropdown.value and self.merge_target_dropdown.value != "__hint__":
            current_key = self.merge_target_dropdown.value
            if not any(str(i) == current_key for i, _ in filtered_targets):
                self.merge_target_dropdown.value = None
                self.merge_confirm_button.disabled = True
        
        self.page.update()

    def _on_target_selected(self, e):
        """Enable confirm button when target is selected."""
        selected_value = self.merge_target_dropdown.value
        # Don't allow confirming on the hint option
        self.merge_confirm_button.disabled = (
            not selected_value or selected_value == "__hint__"
        )
        self.page.update()

    def _confirm_merge(self, e):
        """Execute the manual merge operation."""
        if not self.merge_target_dropdown.value or self.merge_target_dropdown.value == "__hint__":
            return
        
        target_index = int(self.merge_target_dropdown.value)
        target_channel = self.channels[target_index]
        
        # Perform merge: keep target, remove source, transfer selection state
        source_selected = self.merge_source_channel.get('selected', False)
        target_selected = target_channel.get('selected', False)
        
        # If either was selected, target becomes selected
        if source_selected or target_selected:
            target_channel['selected'] = True
        
        # Remove source from both lists
        if self.merge_source_channel in self.channels:
            self.channels.remove(self.merge_source_channel)
        if self.merge_source_channel in self.filtered_channels:
            self.filtered_channels.remove(self.merge_source_channel)
        
        # Refresh UI
        self.refresh_channels_display()
        self.save_current_session()
        
        # Show confirmation
        source_name = self.merge_source_channel['name']
        target_name = target_channel['name']
        self.update_status(f"Merged '{source_name}' into '{target_name}'")
        
        # Close dialog
        self._close_merge_dialog(e)

    def _close_merge_dialog(self, e):
        """Close the merge dialog."""
        if self.merge_dialog:
            self.merge_dialog.open = False
            self.page.update()
            if self.merge_dialog in self.page.overlay:
                self.page.overlay.remove(self.merge_dialog)
            self.merge_dialog = None
        self.merge_source_channel = None
