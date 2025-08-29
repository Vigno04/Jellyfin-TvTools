#!/usr/bin/env python3
"""Group management mixin extracted from main_app to reduce file size."""
from __future__ import annotations
import flet as ft

class GroupManagerMixin:
    def init_group_state(self):
        self.groups_list = None               # ListView showing all groups with controls
        self.group_included = {}              # group -> bool (included)
        self.group_visible = {}               # group -> bool (visible)
        self.all_groups_visible = True        # track state for toggle button

    # -------------- groups logic --------------
    def populate_groups(self):  # expects self.channels
        groups = set()
        for c in self.channels:
            group_name = c.get('group', '') or 'Uncategorized'
            groups.add(group_name)
        self.build_groups_list(sorted(groups))
        self.page.update()

    def build_groups_list(self, groups):
        if not self.groups_list:
            return
        self.groups_list.controls.clear()
        for g in groups:
            included = self.group_included.get(g, False)
            visible = self.group_visible.get(g, True)  # default visible

            include_cb = ft.Checkbox(
                label="Include",
                value=included,
                on_change=lambda e, gr=g: self.on_group_include_toggle(gr, e.control.value),
                width=80,
            )
            visibility_cb = ft.Checkbox(
                label="Visible",
                value=visible,
                on_change=lambda e, gr=g: self.on_group_visibility_toggle(gr, e.control.value),
                width=80,
            )

            group_name = ft.Text(
                g,
                size=13,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.CYAN_ACCENT_200 if included else ft.Colors.GREY_300,
            )

            row = ft.Container(
                ft.Row([
                    group_name,
                    ft.Row([include_cb, visibility_cb], spacing=8),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                bgcolor=ft.Colors.with_opacity(0.12 if included else 0.06, ft.Colors.WHITE),
                border_radius=8,
                opacity=1.0 if visible else 0.5,
            )
            self.groups_list.controls.append(row)
        self.groups_list.update()

    def on_group_include_toggle(self, group: str, included: bool):
        self.group_included[group] = included
        for ch in self.channels:  # bulk update
            ch_group = ch.get('group') or 'Uncategorized'
            if ch_group == group:
                ch['selected'] = included
        groups = { (c.get('group','') or 'Uncategorized') for c in self.channels }
        self.build_groups_list(sorted(groups))
        self.refresh_channels_display()
        self.save_current_selection()

    def on_group_visibility_toggle(self, group: str, visible: bool):
        self.group_visible[group] = visible
        self.update_all_groups_visible_state()
        groups = { (c.get('group','') or 'Uncategorized') for c in self.channels }
        self.build_groups_list(sorted(groups))
        self.refresh_channels_display()

    def update_all_groups_visible_state(self):
        groups = { (c.get('group','') or 'Uncategorized') for c in self.channels }
        if not groups:
            return
        all_visible = all(self.group_visible.get(g, True) for g in groups)
        self.all_groups_visible = all_visible
        self.update_visibility_button()

    def update_visibility_button(self):
        if self.all_groups_visible:
            self.visibility_toggle_btn.text = "Hide All"
            self.visibility_toggle_btn.icon = ft.Icons.VISIBILITY_OFF
        else:
            self.visibility_toggle_btn.text = "Show All"
            self.visibility_toggle_btn.icon = ft.Icons.VISIBILITY
        if hasattr(self.visibility_toggle_btn, 'update'):
            self.visibility_toggle_btn.update()

    def toggle_all_visibility(self, _):
        groups = { (c.get('group','') or 'Uncategorized') for c in self.channels }
        new_state = not self.all_groups_visible
        for g in groups:
            self.group_visible[g] = new_state
        self.all_groups_visible = new_state
        self.update_visibility_button()
        self.build_groups_list(sorted(groups))
        self.refresh_channels_display()

    def show_all_groups(self, _):
        groups = { (c.get('group','') or 'Uncategorized') for c in self.channels if c.get('group') }
        for g in groups:
            self.group_visible[g] = True
        self.build_groups_list(sorted(groups))
        self.refresh_channels_display()

    def hide_all_groups(self, _):
        groups = { (c.get('group','') or 'Uncategorized') for c in self.channels if c.get('group') }
        for g in groups:
            self.group_visible[g] = False
        self.build_groups_list(sorted(groups))
        self.refresh_channels_display()
