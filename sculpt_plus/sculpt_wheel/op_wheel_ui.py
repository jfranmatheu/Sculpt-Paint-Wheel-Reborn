"""Sculpt wheel sidebar operators (brush library reload)."""

from __future__ import annotations

from bpy.types import Context

from ..core import bl_types

from .brush_assets import clear_preview_cache
from .brush_library_cache import force_rebuild_brush_database, refresh_brush_library_cache


class WheelReloadBrushLibraries(bl_types.Operator):
    """Rebuild brush preview database from asset libraries and refresh cache."""

    bl_label = "Reload Brushes"
    bl_description = "Rescan asset libraries and rebuild brush preview data (runs background Blender)"
    bl_options = {"REGISTER"}

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        return True

    def execute(self, context: Context) -> set[str]:
        ok, err = force_rebuild_brush_database()
        refresh_brush_library_cache()
        clear_preview_cache()
        if ok:
            self.report({"INFO"}, "Brush library data rebuilt")
            return {"FINISHED"}
        self.report({"ERROR"}, f"Brush rebuild failed: {err[:500]}")
        return {"CANCELLED"}
