"""Brush size / strength read/write (unified paint settings aware)."""

from __future__ import annotations

from bpy.types import Context

from ...sculpt_wheel.sculpt_paint_compat import get_sculpt_unified_paint_settings


def brush_size_get(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_size:
        return float(ups.size)
    return float(brush.size)


def brush_size_set(context: Context, value: float) -> None:
    v = int(max(1, min(500, round(value))))
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return
    if ups is not None and ups.use_unified_size:
        ups.size = v
    else:
        brush.size = v


def brush_strength_get(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_strength:
        return float(ups.strength)
    return float(brush.strength)


def brush_strength_set(context: Context, value: float) -> None:
    v = float(max(0.01, min(2.0, value)))
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return
    if ups is not None and ups.use_unified_strength:
        ups.strength = v
    else:
        brush.strength = v
