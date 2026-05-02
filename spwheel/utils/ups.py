from typing import Optional

from bl_ui.properties_paint_common import UnifiedPaintPanel, BrushAssetShelf
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
import bpy
from bpy.types import AssetWeakReference, Brush, Context, Sculpt, Paint, UnifiedPaintSettings


def get_tool_settings(context: Optional[Context] = None) -> Sculpt | Paint | None:
    return UnifiedPaintPanel.paint_settings(context or bpy.context)

def get_active_brush(context: Optional[Context] = None) -> Brush | None:
    if context is None:
        tool = ToolSelectPanelHelper.tool_active_from_context(bpy.context)
        if not tool or not tool.use_brushes:
            return None
        paint_settings = UnifiedPaintPanel.paint_settings(bpy.context)
        return paint_settings.brush_asset_reference if paint_settings else None
    else:
        ts = get_tool_settings(context)
        return ts.brush

def get_active_brush_asset_ref(context: Optional[Context] = None) -> AssetWeakReference | None:
    if context is None:
        return BrushAssetShelf.get_active_asset()
    else:
        return get_tool_settings(context).brush_asset_reference

def get_active_brush_mode(context: Optional[Context] = None) -> str | None:
    return UnifiedPaintPanel.get_brush_mode(context or bpy.context)

def get_ups(context: Optional[Context] = None) -> UnifiedPaintSettings | None:
    return UnifiedPaintPanel.paint_settings(context or bpy.context).unified_paint_settings

def _get_ups_attr(context: Context, attr: str) -> float | None:
    ups = get_ups(context)
    return getattr(ups, attr) if getattr(ups, f"use_unified_{attr}") else getattr(get_active_brush(context), attr)

def _set_ups_attr(context: Context, attr: str, value: float):
    ups = get_ups(context)
    if hasattr(ups, f"use_unified_{attr}") and getattr(ups, f"use_unified_{attr}"):
        setattr(ups, attr, value)
    else:
        setattr(get_active_brush(context), attr, value)

def get_ups_size(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "size")
def set_ups_size(context: Context, size: float = 10.0): _set_ups_attr(context, "size", size)

def get_ups_strength(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "strength")
def set_ups_strength(context: Context, strength: float = 0.5): _set_ups_attr(context, "strength", strength)

def get_ups_color(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "color")
def get_ups_color_hsv(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "color").hsv
def set_ups_color(context: Context, color: tuple[float, float, float, float] = (0.0, 0.0, 0.0)): _set_ups_attr(context, "color", color)
def set_ups_color_hsv(context: Context, h: float, s: float, v: float):
    color_attr = _get_ups_attr(context, "color")
    color_attr.hsv = (h, s, v)

def get_ups_weight(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "weight")
def set_ups_weight(context: Context, weight: float = 0.5): _set_ups_attr(context, "weight", weight)
