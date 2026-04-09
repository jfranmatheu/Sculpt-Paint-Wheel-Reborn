"""Sidebar UI operators for sculpt wheel brush sets."""

from __future__ import annotations

from bpy.props import IntProperty
from bpy.types import Context

from ..core import bl_types

from .data import SculptWheelData, get_wheel_storage, get_active_toolset
from .persistence import save_wheel_storage
from .brush_assets import (
    get_active_sculpt_brush,
    get_brush_asset_ref,
    slot_matches_brush,
)


class WheelAddActiveBrush(bl_types.Operator):
    """Append the current sculpt brush to the active toolset."""

    bl_label = "Add Active Brush"
    bl_description = "Add the current sculpt brush to the active brush set"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != 'SCULPT':
            return False
        if get_active_sculpt_brush(context) is None:
            return "No active sculpt brush"
        return True

    def execute(self, context: Context) -> set[str]:
        brush = get_active_sculpt_brush(context)
        if brush is None:
            self.report({'ERROR'}, "No active sculpt brush")
            return {'CANCELLED'}
        ts = get_active_toolset(context)
        if ts is None:
            self.report({'ERROR'}, "No brush set — use New Brush Set")
            return {'CANCELLED'}
        asset_ref = get_brush_asset_ref(context)
        for slot in ts.slots:
            if slot_matches_brush(slot, brush, asset_ref):
                self.report({'WARNING'}, "Brush already in this set")
                return {'CANCELLED'}
        ts.add_brush(brush, asset_ref)
        ts.active_slot_index = len(ts.slots) - 1
        save_wheel_storage(context)
        self.report({'INFO'}, f"Added {brush.name}")
        return {'FINISHED'}


class WheelAddToolset(bl_types.Operator):
    """Create a new empty brush set and make it active."""

    bl_label = "New Brush Set"
    bl_description = "Create a new brush set"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == 'SCULPT'

    def execute(self, context: Context) -> set[str]:
        st = get_wheel_storage(context)
        data = SculptWheelData.get(context)
        ts = st.toolsets.add()
        ts.name = f"Set {len(st.toolsets)}"
        data.active_toolset_index = len(st.toolsets) - 1
        save_wheel_storage(context)
        self.report({'INFO'}, f"Created {ts.name}")
        return {'FINISHED'}


class WheelSelectToolset(bl_types.Operator):
    """Select which brush set is active for the wheel and sidebar."""

    bl_label = "Select Brush Set"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", min=0)

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == 'SCULPT'

    def execute(self, context: Context) -> set[str]:
        st = get_wheel_storage(context)
        data = SculptWheelData.get(context)
        if self.index < 0 or self.index >= len(st.toolsets):
            return {'CANCELLED'}
        data.active_toolset_index = self.index
        save_wheel_storage(context)
        return {'FINISHED'}


class WheelRemoveBrushSlot(bl_types.Operator):
    """Remove a brush slot from the active toolset."""

    bl_label = "Remove Brush Slot"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name="Index", min=0)

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == 'SCULPT'

    def execute(self, context: Context) -> set[str]:
        ts = get_active_toolset(context)
        if ts is None:
            return {'CANCELLED'}
        if self.index < 0 or self.index >= len(ts.slots):
            return {'CANCELLED'}
        ts.remove_slot(self.index)
        save_wheel_storage(context)
        return {'FINISHED'}


class WheelRemoveToolset(bl_types.Operator):
    """Remove the active brush set."""

    bl_label = "Remove Brush Set"
    bl_description = "Delete the active brush set (cannot be undone if it was the last one)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != 'SCULPT':
            return False
        st = get_wheel_storage(context)
        if len(st.toolsets) <= 1:
            return "Keep at least one brush set"
        return True

    def execute(self, context: Context) -> set[str]:
        st = get_wheel_storage(context)
        data = SculptWheelData.get(context)
        if len(st.toolsets) <= 1:
            return {'CANCELLED'}
        idx = min(data.active_toolset_index, len(st.toolsets) - 1)
        st.toolsets.remove(idx)
        if data.active_toolset_index >= len(st.toolsets):
            data.active_toolset_index = len(st.toolsets) - 1
        save_wheel_storage(context)
        return {'FINISHED'}
