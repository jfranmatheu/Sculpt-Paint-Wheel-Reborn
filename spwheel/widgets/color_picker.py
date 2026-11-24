"""HSV ring + arcs + handles; samples color via host ``HsvSampleProvider`` (mode-agnostic)."""
import math
from typing import TYPE_CHECKING

from mathutils import Vector
import bpy

from ..pg.pg_wheel_theme import WheelTheme
from ..utils.ups import get_ups_color_hsv, get_ups_color, get_ups_secondary_color, set_ups_color_hsv
from ..gpu.colpk import (
    draw_colpk_hue_ring,
    draw_colpk_sat_arc,
    draw_colpk_val_arc,
    draw_colpk_sv_swatches,
    get_colpk_sv_swatches_layout,
)
from ..gpu.colpk_helpers import (
    S_ANGLE_BOT,
    S_ANGLE_TOP,
    V_ANGLE_BOT,
    V_ANGLE_TOP,
    colpk_linked_preview_enabled,
)
from ..gpu.utils import draw_circle_fill, draw_ring
from .widget import WidgetRing

if TYPE_CHECKING:
    from bpy.types import Context, Event


def _handle_positions(
    cx: float,
    cy: float,
    hue_inner: float,
    hue_outer: float,
    sv_inner: float,
    sv_outer: float,
    h: float,
    s: float,
    v: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    r_mid_h = 0.5 * (hue_inner + hue_outer)
    r_mid_sv = 0.5 * (sv_inner + sv_outer)
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


class ColorPickerWidget(WidgetRing):
    use_modal = True

    def __init__(self) -> None:
        super().__init__()
        self.hue_inner_r = 0.0
        self.hue_outer_r = 0.0
        self.sv_inner_r = 0.0
        self.sv_outer_r = 0.0
        self._hover_handle: str | None = None
        self._active_handle: str | None = None
        self._hover_swap = False

    @staticmethod
    def _clamp01(v: float) -> float:
        return max(0.0001, min(1.0, v))

    @staticmethod
    def _normalized_hsv(context: "Context") -> tuple[float, float, float]:
        hsv_color = get_ups_color_hsv(context)
        if hsv_color is None:
            return (0.0, 0.0, 0.0)
        h, s, v = hsv_color
        return (
            ColorPickerWidget._clamp01(h),
            ColorPickerWidget._clamp01(s),
            ColorPickerWidget._clamp01(v),
        )

    def _handle_radius(self) -> float:
        return max(6.0, self.wheel.radius * 0.018)

    def _handle_positions_for_color(self, context: "Context") -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
        h, s, v = self._normalized_hsv(context)
        cx, cy = self.center
        return _handle_positions(
            cx,
            cy,
            self.hue_inner_r,
            self.hue_outer_r,
            self.sv_inner_r,
            self.sv_outer_r,
            h,
            s,
            v,
        )

    def _pick_hover_handle(self, context: "Context", p_local: Vector) -> str | None:
        hr = self._handle_radius()
        handles = self._handle_positions_for_color(context)
        labels = ("h", "s", "v")
        for i, (hx, hy) in enumerate(handles):
            if math.hypot(p_local.x - hx, p_local.y - hy) <= hr * 1.35:
                return labels[i]
        return None

    def _pick_control_from_area(self, p_local: Vector) -> str | None:
        cx, cy = self.center
        dx = p_local.x - cx
        dy = p_local.y - cy
        dist = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx))  # [-180, 180]
        angle_360 = (angle + 360.0) % 360.0

        margin = max(2.0, self._handle_radius() * 0.45)

        # Hue uses the full hue ring.
        if (self.hue_inner_r - margin) <= dist <= (self.hue_outer_r + margin):
            return "h"

        # S/V share the same radial band; choose by angular sectors.
        if not ((self.sv_inner_r - margin) <= dist <= (self.sv_outer_r + margin)):
            return None

        in_sat = S_ANGLE_TOP <= angle_360 <= S_ANGLE_BOT
        in_val = V_ANGLE_BOT <= angle <= V_ANGLE_TOP
        if in_sat and not in_val:
            return "s"
        if in_val and not in_sat:
            return "v"
        if in_sat:
            return "s"
        if in_val:
            return "v"
        return None

    def _event_local_to_wheel(self, event: "Event") -> tuple[float, float]:
        return self.wheel.to_local(event.mouse_region_x, event.mouse_region_y)

    def _swap_button_hit(self, p_local: Vector) -> bool:
        _left, center, _right, _swatch_r, swap_r = get_colpk_sv_swatches_layout(
            self.center.x,
            self.center.y,
            self.sv_outer_r - 16,
            self.sv_outer_r + 16,
        )
        return math.hypot(p_local.x - center[0], p_local.y - center[1]) <= swap_r * 1.15

    def _apply_handle_drag(self, context: "Context", event: "Event", handle: str) -> None:
        mx, my = self._event_local_to_wheel(event)
        cx, cy = self.center
        dx = mx - cx
        dy = my - cy

        h, s, v = self._normalized_hsv(context)
        angle_deg = math.degrees(math.atan2(dy, dx))

        if handle == "h":
            angle = math.atan2(dy, dx)
            h = (angle / (2.0 * math.pi)) % 1.0
        elif handle == "s":
            ang = (angle_deg + 360.0) % 360.0
            ang = max(S_ANGLE_TOP, min(S_ANGLE_BOT, ang))
            s = self._clamp01((ang - S_ANGLE_TOP) / max(1e-8, (S_ANGLE_BOT - S_ANGLE_TOP)))
        elif handle == "v":
            ang = angle_deg
            if ang > 180.0:
                ang -= 360.0
            ang = max(V_ANGLE_BOT, min(V_ANGLE_TOP, ang))
            v = self._clamp01((V_ANGLE_TOP - ang) / max(1e-8, (V_ANGLE_TOP - V_ANGLE_BOT)))

        set_ups_color_hsv(context, self._clamp01(h), self._clamp01(s), self._clamp01(v))
        context.region.tag_redraw()

    def on_wheel_activate(self, context: "Context", wheel_prefs, storage, wg_prefs=None) -> None:
        ring_inner = min(self.radius_inner, self.radius_outer)
        ring_outer = max(self.radius_inner, self.radius_outer)
        band = max(0.0, ring_outer - ring_inner)
        if band <= 0.0:
            self.hue_inner_r = 0.0
            self.hue_outer_r = 0.0
            self.sv_inner_r = 0.0
            self.sv_outer_r = 0.0
            self._hover_handle = None
            self._active_handle = None
            return

        # Build inside the provided annulus so it starts at ring_inner and grows outward.
        edge_pad = max(2.0, band * 0.02)
        usable = max(0.0, band - edge_pad * 2.0)
        if usable <= 0.0:
            self.hue_inner_r = ring_inner
            self.hue_outer_r = ring_inner
            self.sv_inner_r = ring_inner
            self.sv_outer_r = ring_inner
            self._hover_handle = None
            self._active_handle = None
            return

        gap = max(2.0, min(6.0, usable * 0.06))
        hue_thick = max(8.0, (usable - gap) * 0.42)
        sv_thick = max(8.0, usable - gap - hue_thick)

        self.hue_inner_r = ring_inner + edge_pad
        self.hue_outer_r = min(ring_outer - edge_pad, self.hue_inner_r + hue_thick)
        self.sv_inner_r = min(ring_outer - edge_pad, self.hue_outer_r + gap)
        self.sv_outer_r = min(ring_outer - edge_pad, self.sv_inner_r + sv_thick)
        self._hover_handle = None
        self._active_handle = None

    def draw(self, context: "Context", theme: WheelTheme) -> None:
        if self.hue_outer_r <= 0.0:
            return
        cx, cy = self.center
        h, s, v = self._normalized_hsv(context)
        ho = self.hue_outer_r
        hi = self.hue_inner_r
        so = self.sv_outer_r
        si = self.sv_inner_r
        if colpk_linked_preview_enabled(context):
            draw_colpk_hue_ring(cx, cy, ho, hi, s, v)
            draw_colpk_sat_arc(cx, cy, so, si, S_ANGLE_TOP, S_ANGLE_BOT, h, v)
            draw_colpk_val_arc(cx, cy, so, si, V_ANGLE_TOP, V_ANGLE_BOT, h, s)
        else:
            draw_colpk_hue_ring(cx, cy, ho, hi, 1.0, 1.0)
            draw_colpk_sat_arc(cx, cy, so, si, S_ANGLE_TOP, S_ANGLE_BOT, h, 1.0)
            draw_colpk_val_arc(cx, cy, so, si, V_ANGLE_TOP, V_ANGLE_BOT, h, 1.0)
        hr = self._handle_radius()
        col_outline = (0.82, 0.84, 0.88, 0.92)
        col_fill = (0.06, 0.062, 0.07, 0.96)
        for hp in _handle_positions(
            cx, cy, self.hue_inner_r, self.hue_outer_r, self.sv_inner_r, self.sv_outer_r, h, s, v,
        ):
            hx, hy = hp
            draw_circle_fill(hx, hy, hr, col_fill, softness=0.12)
            draw_ring(hx, hy, hr, col_outline, thickness=1.15, softness=0.05)

        primary = get_ups_color(context)
        secondary = get_ups_secondary_color(context)
        primary_rgb = (
            float(primary[0]) if primary else 0.0,
            float(primary[1]) if primary else 0.0,
            float(primary[2]) if primary else 0.0,
        )
        secondary_rgb = (
            float(secondary[0]) if secondary else 1.0,
            float(secondary[1]) if secondary else 1.0,
            float(secondary[2]) if secondary else 1.0,
        )
        draw_colpk_sv_swatches(
            cx,
            cy,
            self.sv_outer_r - 16,
            self.sv_outer_r + 16,
            primary_rgb,
            secondary_rgb,
            hover_swap=self._hover_swap,
        )

    def test_hit(self, context: "Context", p: Vector) -> bool:
        self._hover_swap = self._swap_button_hit(p)
        if self._hover_swap:
            self._hover_handle = None
            return True
        self._hover_handle = self._pick_hover_handle(context, p)
        if self._hover_handle is None:
            self._hover_handle = self._pick_control_from_area(p)
        return self._hover_handle is not None

    def on_left_press(self, context: "Context", event: "Event") -> bool:
        if self._hover_swap:
            try:
                bpy.ops.paint.brush_colors_flip()
            except RuntimeError as ex:  # (Its poll fails in some modes.)
                print(f"[SPWheel] Can't swap the brush colors here: {ex}")
                return False
            context.region.tag_redraw()
            return True
        if self._hover_handle is None:
            return False
        self._active_handle = self._hover_handle
        self._apply_handle_drag(context, event, self._active_handle)
        return True

    def modal(self, context: "Context", event: "Event") -> bool:
        if self._active_handle is None:
            return False
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self._apply_handle_drag(context, event, self._active_handle)
            return True
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._active_handle = None
            return False
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._active_handle = None
            return False
        return True
