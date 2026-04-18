"""HSV color-picker hit tests + brush color updates for the sculpt wheel."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Literal

from bpy.types import Context
from mathutils import Color

from ..core.globals import GLOBALS
from .sculpt_paint_compat import get_sculpt_unified_paint_settings

if TYPE_CHECKING:
    from .op_sculpt_wheel import SculptWheelOperator

ColpkChannel = Literal["H", "S", "V"]

ANG_THRESH = 25.0
# Blend-Wheel ColpkRngS (degrees, 0–360)
S_ANGLE_TOP = 90.0 + ANG_THRESH
S_ANGLE_BOT = 270.0 - ANG_THRESH
# ColpkRngV (degrees, atan2 range)
V_ANGLE_TOP = 90.0 - ANG_THRESH
V_ANGLE_BOT = -90.0 + ANG_THRESH


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 0.0
    t = (x - edge0) / (edge1 - edge0)
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _rgb_to_hsv(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    c = Color()
    c.r, c.g, c.b = rgb
    return (float(c.h), float(c.s), float(c.v))


def _hsv_to_rgb(hsv: tuple[float, float, float]) -> tuple[float, float, float]:
    c = Color()
    c.hsv = hsv
    return (float(c.r), float(c.g), float(c.b))


def colpk_linked_preview_enabled(context: Context) -> bool:
    """When True, rings tint by current H/S/V together; when False, use max for non-edited axes (prefs)."""
    addon = context.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME)
    if addon is None:
        return True
    return bool(getattr(addon.preferences, "wheel_colpk_linked_preview", True))


def active_sculpt_brush_has_color(context: Context) -> bool:
    """True when the active sculpt brush supports color (wheel may show the HSV rings)."""
    ts = getattr(context, "tool_settings", None)
    if ts is None:
        return False
    sculpt = getattr(ts, "sculpt", None)
    if sculpt is None:
        return False
    brush = getattr(sculpt, "brush", None)
    if brush is None:
        return False
    cap = getattr(brush, "sculpt_capabilities", None)
    if cap is None:
        return False
    return bool(getattr(cap, "has_color", False))


def get_sculpt_brush_rgb(context: Context) -> tuple[float, float, float]:
    ts = context.tool_settings
    brush = ts.sculpt.brush
    if brush is None:
        return (1.0, 1.0, 1.0)
    ups = get_sculpt_unified_paint_settings(context)
    if ups is not None and getattr(ups, "use_unified_color", False):
        return (float(ups.color[0]), float(ups.color[1]), float(ups.color[2]))
    return (float(brush.color[0]), float(brush.color[1]), float(brush.color[2]))


def set_sculpt_brush_rgb(context: Context, rgb: tuple[float, float, float]) -> bool:
    ts = context.tool_settings
    brush = ts.sculpt.brush
    if brush is None:
        return False
    ups = get_sculpt_unified_paint_settings(context)
    if ups is not None and getattr(ups, "use_unified_color", False):
        ups.color = rgb
    else:
        brush.color = rgb
    return True


def _in_annulus(mx: float, my: float, cx: float, cy: float, r_in: float, r_out: float) -> bool:
    r = math.hypot(mx - cx, my - cy)
    return (r_in - 1.0) <= r <= (r_out + 2.0)


def _deg360_from_center(mx: float, my: float, cx: float, cy: float) -> float:
    a = math.degrees(math.atan2(my - cy, mx - cx))
    if a < 0.0:
        a += 360.0
    return a


def colpk_pick_channel(mx: float, my: float, cx: float, cy: float, op: "SculptWheelOperator") -> ColpkChannel | None:
    """Return H/S/V if *mx,my* hits a picker ring (caller handles brush slots first)."""
    if not getattr(op, "show_color_picker", False):
        return None

    hi = float(op.colpk_hue_inner_r)
    ho = float(op.colpk_hue_outer_r)
    si = float(op.colpk_sv_inner_r)
    so = float(op.colpk_sv_outer_r)

    # Outer S/V arcs share one annulus; split by screen X and angle.
    if _in_annulus(mx, my, cx, cy, si, so):
        if mx < cx - 0.5:
            a = _deg360_from_center(mx, my, cx, cy)
            if S_ANGLE_TOP <= a <= S_ANGLE_BOT:
                return "S"
        elif mx > cx + 0.5:
            av = math.degrees(math.atan2(my - cy, mx - cx))
            if V_ANGLE_BOT <= av <= V_ANGLE_TOP:
                return "V"
        return None

    if _in_annulus(mx, my, cx, cy, hi, ho):
        return "H"

    return None


def colpk_update_from_mouse(
    context: Context,
    op: "SculptWheelOperator",
    channel: ColpkChannel,
    mx: float,
    my: float,
) -> None:
    cx, cy = op.wheel_center_x, op.wheel_center_y
    rgb = get_sculpt_brush_rgb(context)
    h, s, v = _rgb_to_hsv(rgb)
    s = max(1e-4, min(1.0, s))
    v = max(1e-4, min(1.0, v))

    if channel == "H":
        ang = math.atan2(-(my - cy), -(mx - cx))
        nh = (ang / (2.0 * math.pi)) + 0.5
        nh = nh % 1.0
        set_sculpt_brush_rgb(context, _hsv_to_rgb((nh, s, v)))
        return

    if channel == "S":
        # Match fragment shader: smoothstep(115°, 245°, angle) → sat 0→1 along the arc.
        a = _deg360_from_center(mx, my, cx, cy)
        if a <= S_ANGLE_TOP:
            ns = 0.0
        elif a >= S_ANGLE_BOT:
            ns = 1.0
        else:
            ns = _smoothstep(S_ANGLE_TOP, S_ANGLE_BOT, a)
        ns = max(1e-4, min(1.0, ns))
        set_sculpt_brush_rgb(context, _hsv_to_rgb((h, ns, v)))
        return

    if channel == "V":
        # Match fragment shader: smoothstep(65°, −65°, angle) → value 0 at top of arc, 1 at bottom.
        av = math.degrees(math.atan2(my - cy, mx - cx))
        if av > V_ANGLE_TOP:
            nv = 0.0
        elif av < V_ANGLE_BOT:
            nv = 1.0
        else:
            nv = _smoothstep(V_ANGLE_TOP, V_ANGLE_BOT, av)
        nv = max(1e-4, min(1.0, nv))
        set_sculpt_brush_rgb(context, _hsv_to_rgb((h, s, nv)))


def colpk_handle_positions(
    op: "SculptWheelOperator",
    context: Context,
) -> tuple[tuple[float, float] | None, tuple[float, float] | None, tuple[float, float] | None]:
    """Screen positions for handles on H / S / V rings (mid-radius)."""
    if not op.show_color_picker:
        return (None, None, None)
    cx, cy = op.wheel_center_x, op.wheel_center_y
    rgb = get_sculpt_brush_rgb(context)
    h, s, v = _rgb_to_hsv(rgb)

    r_mid_h = 0.5 * (op.colpk_hue_inner_r + op.colpk_hue_outer_r)
    r_mid_sv = 0.5 * (op.colpk_sv_inner_r + op.colpk_sv_outer_r)

    ang_h = 2.0 * math.pi * h
    px_h = cx + r_mid_h * math.cos(ang_h)
    py_h = cy + r_mid_h * math.sin(ang_h)

    # Saturation: same angle mapping as shader smoothstep(S_TOP, S_BOT, a) for s∈[0,1].
    ang_s_deg = S_ANGLE_TOP + s * (S_ANGLE_BOT - S_ANGLE_TOP)
    ang_s = math.radians(ang_s_deg)
    px_s = cx + r_mid_sv * math.cos(ang_s)
    py_s = cy + r_mid_sv * math.sin(ang_s)

    # Value: same as shader smoothstep(V_TOP, V_BOT, a) for v∈[0,1] on the right arc.
    ang_v_deg = V_ANGLE_TOP - v * (V_ANGLE_TOP - V_ANGLE_BOT)
    ang_v = math.radians(ang_v_deg)
    px_v = cx + r_mid_sv * math.cos(ang_v)
    py_v = cy + r_mid_sv * math.sin(ang_v)

    return ((px_h, py_h), (px_s, py_s), (px_v, py_v))
