"""Sculpt wheel sidebar operators (brush library load / rebuild)."""

from __future__ import annotations

from bpy.props import EnumProperty, StringProperty
from bpy.types import Context

from ..core import bl_types

from .brush_sets_config import brush_set_config_move, load_wheel_brush_data
from .data import SculptWheelData


class WheelLoadBrushData(bl_types.Operator):
    """First-time or refresh: read shelve (build DB if missing) and sync configs."""

    bl_label = "Load brush sets"
    bl_description = (
        "Build or read the brush preview shelve from asset libraries and load set configuration"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return True

    def execute(self, context: Context) -> set[str]:
        ok, err = load_wheel_brush_data(context, force_rebuild=False)
        if ok:
            self.report({"INFO"}, "Brush sets loaded")
            return {"FINISHED"}
        self.report({"ERROR"}, f"Brush load failed: {err[:500]}")
        return {"CANCELLED"}


class WheelReloadBrushLibraries(bl_types.Operator):
    """Force full rebuild of brush shelve and refresh configs + JSON."""

    bl_label = "Rebuild brush cache"
    bl_description = (
        "Rescan asset libraries and rebuild brush preview data (runs background Blender)"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return True

    def execute(self, context: Context) -> set[str]:
        ok, err = load_wheel_brush_data(context, force_rebuild=True)
        if ok:
            self.report({"INFO"}, "Brush library data rebuilt")
            return {"FINISHED"}
        self.report({"ERROR"}, f"Brush rebuild failed: {err[:500]}")
        return {"CANCELLED"}


class WheelSetActiveBrushSet(bl_types.Operator):
    """Set the wheel’s active brush set (from UIList radio)."""

    bl_label = "Use brush set"
    bl_description = "Make this brush set active on the sculpt wheel"
    bl_options = {"REGISTER", "INTERNAL"}

    set_key: StringProperty(name="Set key", default="", maxlen=1024)

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return context.mode == "SCULPT"

    def execute(self, context: Context) -> set[str]:
        key = (self.set_key or "").strip()
        if not key:
            return {"CANCELLED"}
        wd = SculptWheelData.get(context)
        if not any(it.set_key == key for it in wd.brush_set_configs):
            return {"CANCELLED"}
        wd.wheel_brush_set = key
        if getattr(context, "region", None):
            context.region.tag_redraw()
        return {"FINISHED"}


class WheelBrushSetMove(bl_types.Operator):
    """Reorder brush set config rows (swap sort order with neighbor)."""

    bl_label = "Move brush set"
    bl_description = "Change sort order of the selected brush set in the list"
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
        return wd.brush_sets_loaded and len(wd.brush_set_configs) > 1

    def execute(self, context: Context) -> set[str]:
        d = -1 if self.direction == "UP" else 1
        if brush_set_config_move(context, d):
            if getattr(context, "region", None):
                context.region.tag_redraw()
            return {"FINISHED"}
        return {"CANCELLED"}
