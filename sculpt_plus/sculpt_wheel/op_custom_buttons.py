"""Operators to add/remove sculpt wheel custom button sets and buttons."""

from __future__ import annotations

import os

from bpy.path import abspath as bpy_abspath
from bpy.props import EnumProperty, IntProperty
from bpy.types import Context

from ..core import bl_types

from .data import (
    MAX_CUSTOM_BUTTON_SETS,
    MAX_CUSTOM_BUTTONS_PER_SET,
    SculptWheelData,
    get_active_custom_button_buttons,
    get_wheel_storage,
    wheel_add_custom_button_from_create,
    wheel_move_custom_button,
    wheel_remove_custom_button,
)
from .persistence import save_wheel_storage


class WheelAddCustomButtonSet(bl_types.Operator):
    """Add a new empty custom button set (max 10)."""

    bl_label = "Add Custom Button Set"
    bl_description = "Create another named set of wheel inner-ring buttons"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != "SCULPT":
            return False
        st = get_wheel_storage(context)
        return len(st.custom_button_sets) < MAX_CUSTOM_BUTTON_SETS

    def execute(self, context: Context) -> set[str]:
        st = get_wheel_storage(context)
        s = st.custom_button_sets.add()
        n = len(st.custom_button_sets)
        s.name = f"Set {n}"
        st.custom_button_set_active_index = n - 1
        save_wheel_storage(context)
        self.report({"INFO"}, f"Added custom button set {s.name!r}")
        return {"FINISHED"}


class WheelRemoveCustomButtonSet(bl_types.Operator):
    """Remove the active custom button set (always keeps at least one)."""

    bl_label = "Remove Custom Button Set"
    bl_description = "Delete the selected custom button set"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != "SCULPT":
            return False
        st = get_wheel_storage(context)
        return len(st.custom_button_sets) > 1

    def execute(self, context: Context) -> set[str]:
        st = get_wheel_storage(context)
        si = int(st.custom_button_set_active_index)
        if len(st.custom_button_sets) <= 1:
            return {"CANCELLED"}
        si = max(0, min(len(st.custom_button_sets) - 1, si))
        st.custom_button_sets.remove(si)
        st.custom_button_set_active_index = max(0, len(st.custom_button_sets) - 1)
        save_wheel_storage(context)
        self.report({"INFO"}, "Removed custom button set")
        return {"FINISHED"}


class WheelAddCustomButton(bl_types.Operator):
    """Add a custom button from the sidebar “create” fields."""

    bl_label = "Add Custom Button"
    bl_description = "Add a custom action to the active set’s inner ring"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != "SCULPT":
            return False
        return get_active_custom_button_buttons(context) is not None

    def execute(self, context: Context) -> set[str]:
        data = SculptWheelData.get(context)
        create = data.create_custom_button
        buttons = get_active_custom_button_buttons(context)
        if buttons is None:
            self.report({"WARNING"}, "No custom button set is available")
            return {"CANCELLED"}
        if not create.name or create.name.isspace():
            self.report({"WARNING"}, "Button name is not valid")
            return {"CANCELLED"}
        path = create.image_path
        if path.startswith("//"):
            path = bpy_abspath(path)
        if not path or not os.path.isfile(path):
            self.report({"WARNING"}, "Image path is not valid")
            return {"CANCELLED"}
        if len(buttons) >= MAX_CUSTOM_BUTTONS_PER_SET:
            self.report({"WARNING"}, f"Maximum {MAX_CUSTOM_BUTTONS_PER_SET} buttons per set")
            return {"CANCELLED"}
        if create.type == "POPUP":
            if create.popup_type == "MENU" and create.menu_source == "CUSTOM":
                mid = create.custom_menu.strip()
                if "_MT_" not in mid:
                    self.report({"WARNING"}, "Menu id should look like VIEW3D_MT_…")
                    return {"CANCELLED"}
            if create.popup_type == "PANEL" and create.panel_source == "CUSTOM":
                pid = create.custom_panel.strip()
                if "_PT_" not in pid:
                    self.report({"WARNING"}, "Panel id should look like VIEW3D_PT_…")
                    return {"CANCELLED"}
        if create.type == "OPERATOR" and create.operator_type == "CUSTOM":
            raw = create.custom_operator.strip()
            if "bpy.ops." not in raw:
                self.report({"WARNING"}, "Custom operator code should call bpy.ops.…")
                return {"CANCELLED"}

        if not wheel_add_custom_button_from_create(context, create):
            self.report({"WARNING"}, "Could not build this button (check fields)")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Added custom button {create.name!r}")
        return {"FINISHED"}


class WheelMoveCustomButtonInSet(bl_types.Operator):
    """Move one custom wheel button earlier or later within its set."""

    bl_label = "Move custom wheel button"
    bl_description = "Reorder a custom action within its button set"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    set_index: IntProperty(name="Set", default=0, min=0, max=MAX_CUSTOM_BUTTON_SETS - 1)
    button_index: IntProperty(name="Button", default=0, min=0, max=MAX_CUSTOM_BUTTONS_PER_SET - 1)
    direction: EnumProperty(
        name="Direction",
        items=(
            ("UP", "Up", "Earlier in the set"),
            ("DOWN", "Down", "Later in the set"),
        ),
        default="UP",
    )

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == "SCULPT"

    def execute(self, context: Context) -> set[str]:
        d = -1 if self.direction == "UP" else 1
        if wheel_move_custom_button(context, int(self.set_index), int(self.button_index), d):
            if getattr(context, "region", None):
                context.region.tag_redraw()
            return {"FINISHED"}
        return {"CANCELLED"}


class WheelRemoveCustomButton(bl_types.Operator):
    """Remove one custom button by index (optionally specify which set)."""

    bl_label = "Remove Custom Button"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(name="Button index", default=-1, min=-1, max=MAX_CUSTOM_BUTTONS_PER_SET - 1)
    set_index: IntProperty(
        name="Set index",
        description="Which custom button set (-1 = active set)",
        default=-1,
        min=-1,
        max=MAX_CUSTOM_BUTTON_SETS - 1,
    )

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == "SCULPT"

    def execute(self, context: Context) -> set[str]:
        if self.index < 0:
            return {"CANCELLED"}
        si = int(self.set_index)
        if si < 0:
            wheel_remove_custom_button(context, int(self.index))
        else:
            wheel_remove_custom_button(context, int(self.index), set_index=si)
        if getattr(context, "region", None):
            context.region.tag_redraw()
        return {"FINISHED"}
