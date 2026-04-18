"""Sculpt wheel sidebar operators (brush library load / rebuild)."""

from __future__ import annotations

from bpy.props import EnumProperty, StringProperty
from bpy.types import Context

from ..core import bl_types

from .brush_lib_config import (
    bootstrap_all_windows,
    brush_lib_config_move,
    load_brush_lib_data,
)
from .data import SculptWheelData


class WheelLoadBrushData(bl_types.Operator):
    """First-time or refresh: read libraries.json and sync configs."""

    bl_label = "Load brush libraries"
    bl_description = (
        "Load or refresh brush library data and sync the wheel configuration"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return True

    def execute(self, context: Context) -> set[str]:
        ok, err = load_brush_lib_data(context, force_rebuild=False)
        if ok:
            self.report({"INFO"}, "Brush libraries loaded")
            return {"FINISHED"}
        self.report({"ERROR"}, f"Brush load failed: {err[:500]}")
        return {"CANCELLED"}


class WheelReloadBrushLibraries(bl_types.Operator):
    """Full rescan of asset libraries, rebuild cache, sync all windows."""

    bl_label = "Reload brush libraries"
    bl_description = (
        "Rescan asset libraries and rebuild brush cache (runs background Blender)"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return True

    def execute(self, context: Context) -> set[str]:
        ok, err = bootstrap_all_windows(force_rebuild=True)
        if ok:
            self.report({"INFO"}, "Brush libraries reloaded")
            return {"FINISHED"}
        self.report({"ERROR"}, f"Brush reload failed: {err[:500]}")
        return {"CANCELLED"}


class WheelSetActiveBrushLib(bl_types.Operator):
    """Set the wheel's active brush library (from UIList radio)."""

    bl_label = "Use brush library"
    bl_description = "Make this brush library active on the sculpt wheel"
    bl_options = {"REGISTER", "INTERNAL"}

    blend_key: StringProperty(name="Blend key", default="", maxlen=2048)

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == "SCULPT"

    def execute(self, context: Context) -> set[str]:
        key = (self.blend_key or "").strip()
        if not key:
            return {"CANCELLED"}
        wd = SculptWheelData.get(context)
        if not any(it.blend_key == key for it in wd.brush_lib_configs):
            return {"CANCELLED"}
        wd.wheel_active_blend = key
        if getattr(context, "region", None):
            context.region.tag_redraw()
        return {"FINISHED"}


class WheelBrushLibMove(bl_types.Operator):
    """Reorder brush library config rows."""

    bl_label = "Move brush library"
    bl_description = "Change sort order of the selected brush library in the list"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    direction: EnumProperty(
        name="Direction",
        items=(
            ("UP", "Up", "Move earlier in the list"),
            ("DOWN", "Down", "Move later in the list"),
        ),
        default="UP",
    )

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != "SCULPT":
            return False
        wd = SculptWheelData.get(context)
        return wd.brush_libs_loaded and len(wd.brush_lib_configs) > 1

    def execute(self, context: Context) -> set[str]:
        d = -1 if self.direction == "UP" else 1
        if brush_lib_config_move(context, d):
            if getattr(context, "region", None):
                context.region.tag_redraw()
            return {"FINISHED"}
        return {"CANCELLED"}
