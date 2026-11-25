"""Color-picker layout and brush RGB helpers for the wheel overlay (non-GPU)."""

from __future__ import annotations

import math
from typing import Any

from bpy.types import Context
from mathutils import Color

from ..core.globals import GLOBALS

ANG_THRESH = 25.0
S_ANGLE_TOP = 90.0 + ANG_THRESH
S_ANGLE_BOT = 270.0 - ANG_THRESH
V_ANGLE_TOP = 90.0 - ANG_THRESH
V_ANGLE_BOT = -90.0 + ANG_THRESH


def get_sculpt_unified_paint_settings(context: Context) -> Any | None:
    ts = context.tool_settings
    sculpt = getattr(ts, "sculpt", None)
    if sculpt is not None:
        ups = getattr(sculpt, "unified_paint_settings", None)
        if ups is not None:
            return ups
    return getattr(ts, "unified_paint_settings", None)


def get_sculpt_brush_rgb(context: Context) -> tuple[float, float, float]:
    ts = context.tool_settings
    sculpt = getattr(ts, "sculpt", None)
    if sculpt is None:
        return (1.0, 1.0, 1.0)
    brush = getattr(sculpt, "brush", None)
    if brush is None:
        return (1.0, 1.0, 1.0)
    ups = get_sculpt_unified_paint_settings(context)
    from ..utils.ups import uses_unified
    if ups is not None and uses_unified(ups, brush, "color"):
        return (float(ups.color[0]), float(ups.color[1]), float(ups.color[2]))
    return (float(brush.color[0]), float(brush.color[1]), float(brush.color[2]))


def colpk_linked_preview_enabled(context: Context) -> bool:
    addon = context.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME)
    if addon is None:
        return True
    return bool(getattr(addon.preferences, "wheel_colpk_linked_preview", True))


def _rgb_to_hsv(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    c = Color()
    c.r, c.g, c.b = rgb
    return (float(c.h), float(c.s), float(c.v))


def colpk_handle_positions(
    op: Any,
    context: Context,
) -> tuple[tuple[float, float] | None, tuple[float, float] | None, tuple[float, float] | None]:
    """Screen positions for handles on H / S / V rings (mid-radius)."""
    if not getattr(op, "show_color_picker", False):
        return (None, None, None)
    cx, cy = op.wheel_center_x, op.wheel_center_y
    rgb = get_sculpt_brush_rgb(context)
    h, s, v = _rgb_to_hsv(rgb)

    r_mid_h = 0.5 * (op.colpk_hue_inner_r + op.colpk_hue_outer_r)
    r_mid_sv = 0.5 * (op.colpk_sv_inner_r + op.colpk_sv_outer_r)

    ang_h = 2.0 * math.pi * h
    px_h = cx + r_mid_h * math.cos(ang_h)
    py_h = cy + r_mid_h * math.sin(ang_h)

    ang_s_deg = S_ANGLE_TOP + s * (S_ANGLE_BOT - S_ANGLE_TOP)
    ang_s = math.radians(ang_s_deg)
    px_s = cx + r_mid_sv * math.cos(ang_s)
    py_s = cy + r_mid_sv * math.sin(ang_s)

    ang_v_deg = V_ANGLE_TOP - v * (V_ANGLE_TOP - V_ANGLE_BOT)
    ang_v = math.radians(ang_v_deg)
    px_v = cx + r_mid_sv * math.cos(ang_v)
    py_v = cy + r_mid_sv * math.sin(ang_v)

    return ((px_h, py_h), (px_s, py_s), (px_v, py_v))
