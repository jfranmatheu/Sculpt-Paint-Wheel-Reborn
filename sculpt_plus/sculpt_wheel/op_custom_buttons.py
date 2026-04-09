"""Operators to add/remove sculpt wheel custom buttons."""

from __future__ import annotations

import os

from bpy.path import abspath as bpy_abspath
from bpy.props import IntProperty
from bpy.types import Context

from ..core import bl_types

from .data import SculptWheelData


class WheelAddCustomButton(bl_types.Operator):
    """Add a custom button from the sidebar “create” fields."""

    bl_label = "Add Custom Button"
    bl_description = "Add a custom action to the wheel inner ring"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != 'SCULPT':
            return False
        return True

    def execute(self, context: Context) -> set[str]:
        data = SculptWheelData.get(context)
        create = data.create_custom_button
        if not create.name or create.name.isspace():
            self.report({'WARNING'}, "Button name is not valid")
            return {'CANCELLED'}
        path = create.image_path
        if path.startswith("//"):
            path = bpy_abspath(path)
        if not path or not os.path.isfile(path):
            self.report({'WARNING'}, "Image path is not valid")
            return {'CANCELLED'}
        if len(data.custom_buttons) >= 10:
            self.report({'WARNING'}, "Maximum 10 custom buttons")
            return {'CANCELLED'}
        if create.type == 'POPUP':
            if create.popup_type == 'MENU' and create.menu_source == 'CUSTOM':
                mid = create.custom_menu.strip()
                if '_MT_' not in mid:
                    self.report({'WARNING'}, "Menu id should look like VIEW3D_MT_…")
                    return {'CANCELLED'}
            if create.popup_type == 'PANEL' and create.panel_source == 'CUSTOM':
                pid = create.custom_panel.strip()
                if '_PT_' not in pid:
                    self.report({'WARNING'}, "Panel id should look like VIEW3D_PT_…")
                    return {'CANCELLED'}
        if create.type == 'OPERATOR' and create.operator_type == 'CUSTOM':
            raw = create.custom_operator.strip()
            if 'bpy.ops.' not in raw:
                self.report({'WARNING'}, "Custom operator code should call bpy.ops.…")
                return {'CANCELLED'}

        if not data.add_custom_button_from_create(create):
            self.report({'WARNING'}, "Could not build this button (check fields)")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Added custom button {create.name!r}")
        return {'FINISHED'}


class WheelRemoveCustomButton(bl_types.Operator):
    """Remove one custom button by index."""

    bl_label = "Remove Custom Button"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", default=-1, min=-1)

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == 'SCULPT'

    def execute(self, context: Context) -> set[str]:
        if self.index < 0:
            return {'CANCELLED'}
        data = SculptWheelData.get(context)
        data.remove_custom_button(self.index)
        return {'FINISHED'}
