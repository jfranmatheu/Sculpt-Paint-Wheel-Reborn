"""GPU overlay for RMB brush size / strength gesture."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bpy.types import Context

from ..core.gpu.state_control import CM_GPU_BLEND
from ..sculpt_wheel.gpu_utils import draw_ring
from ..sculpt_wheel.sculpt_paint_compat import get_sculpt_unified_paint_settings

if TYPE_CHECKING:
    from .op_rmb_sculpt_gesture import RmbSculptGestureOperator

COL_PENDING = (0.22, 0.24, 0.28, 0.55)
COL_OVR_SIZE = (0.42, 0.52, 0.62, 0.55)
COL_OVR_TRACK = (0.34, 0.36, 0.40, 0.38)
COL_OVR_VALUE = (0.62, 0.55, 0.28, 0.58)


def _overlay_brush_size(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_size:
        return float(ups.size)
    return float(brush.size)


def _overlay_brush_strength(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_strength:
        return float(ups.strength)
    return float(brush.strength)


def draw_rmb_gesture(context: Context, op: "RmbSculptGestureOperator") -> None:
    """Full-frame 2D draw: pending hint and/or drag value rings."""
    with CM_GPU_BLEND("ALPHA"):
        if op._state == "pending":
            ox, oy = op._origin
            draw_ring(ox, oy, 6.0, COL_PENDING, thickness=1.4, softness=0.06)
        if op._state == "drag" and op._axis is not None:
            _draw_drag_overlay(context, op)


def _draw_drag_overlay(context: Context, op: "RmbSculptGestureOperator") -> None:
    cx, cy = op._origin
    radius = op._overlay_radius
    is_vert = op._axis == "Y"
    invert = op._invert
    show_size = (is_vert and not invert) or (not is_vert and invert)
    preview = getattr(op, "_preview", "SIMPLE")

    if show_size:
        val = _overlay_brush_size(context)
        draw_ring(cx, cy, max(1.0, val * 0.5), COL_OVR_SIZE, thickness=1.8, softness=0.02)
    else:
        val = _overlay_brush_strength(context)
        if preview == "PREVIEW":
            draw_ring(cx, cy, radius * 1.06, COL_OVR_TRACK, thickness=1.0, softness=0.04)
        draw_ring(cx, cy, radius, COL_OVR_TRACK, thickness=1.4, softness=0.02)
        draw_ring(
            cx,
            cy,
            radius * min(1.0, max(0.0, val / 2.0)),
            COL_OVR_VALUE,
            thickness=1.8,
            softness=0.02,
        )
