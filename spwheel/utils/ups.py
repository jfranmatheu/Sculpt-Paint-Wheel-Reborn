from mathutils import Color
from typing import Optional

from bl_ui.properties_paint_common import UnifiedPaintPanel, BrushAssetShelf
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
import bpy
from bpy.types import AssetWeakReference, Brush, Context, Sculpt, Paint, UnifiedPaintSettings


# Blender 5.3 renamed UnifiedPaintPanel.paint_settings() to paint_settings_from_active_tool().
_paint_settings = getattr(UnifiedPaintPanel, "paint_settings_from_active_tool", None) or UnifiedPaintPanel.paint_settings


def get_tool_settings(context: Optional[Context] = None) -> Sculpt | Paint | None:
    return _paint_settings(context or bpy.context)

def get_active_brush(context: Optional[Context] = None) -> Brush | None:
    if context is None:
        tool = ToolSelectPanelHelper.tool_active_from_context(bpy.context)
        if not tool or not tool.use_brushes:
            return None
        paint_settings = _paint_settings(bpy.context)
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

def has_brush_color_capabilities(context: Context | Brush | None) -> bool:
    act_brush = context if isinstance(context, Brush) else get_active_brush(context)
    if act_brush is None:
        return False
    if act_brush.use_paint_image or act_brush.use_paint_grease_pencil:
        return act_brush.image_paint_capabilities.has_color
    elif act_brush.use_paint_sculpt:
        return act_brush.sculpt_capabilities.has_color
    elif act_brush.use_paint_vertex:
        return act_brush.vertex_paint_capabilities.has_color
        # we could also act_brush.image_paint_capabilities.has_color
    else:
        return False

def get_ups(context: Optional[Context] = None) -> UnifiedPaintSettings | None:
    ups = _paint_settings(context or bpy.context)
    return ups.unified_paint_settings if ups else None

def _get_ups_attr(context: Context, attr: str, unif_attr: Optional[str] = None) -> float | None:
    ups = get_ups(context)
    if not ups:
        return None
    return getattr(ups, attr) if getattr(ups, f"use_unified_{unif_attr or attr}") else getattr(get_active_brush(context), attr)

def _set_ups_attr(context: Context, attr: str, value: float):
    ups = get_ups(context)
    if not ups:
        return
    if hasattr(ups, f"use_unified_{attr}") and getattr(ups, f"use_unified_{attr}"):
        setattr(ups, attr, value)
    else:
        setattr(get_active_brush(context), attr, value)

def get_ups_size(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "size")
def set_ups_size(context: Context, size: float = 10.0): _set_ups_attr(context, "size", size)

def get_ups_strength(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "strength")
def set_ups_strength(context: Context, strength: float = 0.5): _set_ups_attr(context, "strength", strength)

def get_ups_color(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "color")
def get_ups_secondary_color(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "secondary_color", unif_attr='color')
def get_ups_color_hsv(context: Optional[Context] = None) -> tuple[float, float, float] | None:
    """HSV of the brush color as displayed (sRGB), as Blender's own color wheel: the color itself is stored
    scene-linear."""
    color = _get_ups_attr(context, "color")
    if color is None:
        return None
    return tuple(Color(color[:3]).from_scene_linear_to_srgb().hsv)
def set_ups_color(context: Context, color: tuple[float, float, float, float] = (0.0, 0.0, 0.0)): _set_ups_attr(context, "color", color)
def set_ups_color_hsv(context: Context, h: float, s: float, v: float):
    """Set the brush color from a displayed (sRGB) HSV."""
    color_attr = _get_ups_attr(context, "color")
    srgb = Color()
    srgb.hsv = (h, s, v)
    color_attr[:3] = srgb.from_srgb_to_scene_linear()

def get_ups_weight(context: Optional[Context] = None) -> float | None: return _get_ups_attr(context, "weight")
def set_ups_weight(context: Context, weight: float = 0.5): _set_ups_attr(context, "weight", weight)
