"""Sculpt wheel sidebar operators (brush library load / rebuild)."""

from __future__ import annotations

from bpy.props import IntProperty, StringProperty
from bpy.types import Context

from ..core import bl_types

from .brush_lib_config import (
    bootstrap_all_windows,
    load_brush_lib_data,
    set_active_page,
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


class WheelSetBrushLibActivePage(bl_types.Operator):
    """Set the default wheel page for a brush library (prefs row)."""

    bl_label = "Set wheel page"
    bl_description = (
        "Choose which page is active for this library (shown first when you open the wheel)"
    )
    bl_options = {"REGISTER", "INTERNAL"}

    blend_key: StringProperty(name="Blend key", default="", maxlen=2048)
    page_index: IntProperty(name="Page", default=0, min=0, max=511)

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.mode != "SCULPT":
            return False
        wd = SculptWheelData.get(context)
        return bool(wd.brush_libs_loaded)

    def execute(self, context: Context) -> set[str]:
        key = (self.blend_key or "").strip()
        if not key:
            return {"CANCELLED"}
        wd = SculptWheelData.get(context)
        if not any(it.blend_key == key for it in wd.brush_lib_configs):
            return {"CANCELLED"}
        set_active_page(context, key, int(self.page_index))
        if getattr(context, "region", None):
            context.region.tag_redraw()
        return {"FINISHED"}
