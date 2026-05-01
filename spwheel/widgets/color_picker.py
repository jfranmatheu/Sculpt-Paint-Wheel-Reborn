"""HSV ring + arcs + handles; samples color via host ``HsvSampleProvider`` (mode-agnostic)."""
from colorsys import hsv_to_rgb, rgb_to_hsv
import math
from typing import TYPE_CHECKING

from mathutils import Vector

from ..pg.pg_wheel_theme import WheelTheme
from ..utils.ups import get_ups_color, set_ups_color
from ..gpu.colpk import draw_colpk_hue_ring, draw_colpk_sat_arc, draw_colpk_val_arc
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

    @staticmethod
    def _clamp01(v: float) -> float:
        return max(0.0, min(1.0, v))

    @staticmethod
    def _normalized_hsv(context: "Context") -> tuple[float, float, float]:
        rgba_color = get_ups_color(context)
        if rgba_color is None:
            return (0.0, 0.0, 0.0)
        h, s, v = rgb_to_hsv(*rgba_color[:3])
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

    def _event_local_to_wheel(self, event: "Event") -> tuple[float, float]:
        return self.wheel.to_local(event.mouse_region_x, event.mouse_region_y)

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

        r, g, b = hsv_to_rgb(self._clamp01(h), self._clamp01(s), self._clamp01(v))
        set_ups_color(context, (r, g, b))
        context.region.tag_redraw()

    def on_wheel_activate(self, context: "Context", wheel_prefs, storage, wg_prefs=None) -> None:
        wr = self.radius_outer
        base_outer = max(28.0, wr * 0.30)
        gap = max(5.0, wr * 0.028)
        hue_thick = max(14.0, wr * 0.062)
        self.hue_inner_r = base_outer + gap
        self.hue_outer_r = self.hue_inner_r + hue_thick
        gap2 = max(4.0, wr * 0.022)
        sv_thick = max(16.0, wr * 0.07)
        self.sv_inner_r = self.hue_outer_r + gap2
        self.sv_outer_r = self.sv_inner_r + sv_thick
        self._hover_handle = None
        self._active_handle = None

    def draw(self, context: "Context", theme: WheelTheme) -> None:
        if self.hue_outer_r <= 0.0:
            return
        rgba_color = get_ups_color(context)
        if rgba_color is None:
            return
        cx, cy = self.center
        h, s, v = self._normalized_hsv(context)
        ho = self.hue_outer_r
        so = self.sv_outer_r
        if colpk_linked_preview_enabled(context):
            draw_colpk_hue_ring(cx, cy, ho, s, v)
            draw_colpk_sat_arc(cx, cy, so, S_ANGLE_TOP, S_ANGLE_BOT, h, v)
            draw_colpk_val_arc(cx, cy, so, V_ANGLE_TOP, V_ANGLE_BOT, h, s)
        else:
            draw_colpk_hue_ring(cx, cy, ho, 1.0, 1.0)
            draw_colpk_sat_arc(cx, cy, so, S_ANGLE_TOP, S_ANGLE_BOT, h, 1.0)
            draw_colpk_val_arc(cx, cy, so, V_ANGLE_TOP, V_ANGLE_BOT, h, 1.0)
        hr = self._handle_radius()
        col_outline = (0.82, 0.84, 0.88, 0.92)
        col_fill = (0.06, 0.062, 0.07, 0.96)
        for hp in _handle_positions(
            cx, cy, self.hue_inner_r, self.hue_outer_r, self.sv_inner_r, self.sv_outer_r, h, s, v,
        ):
            hx, hy = hp
            draw_circle_fill(hx, hy, hr, col_fill, softness=0.12)
            draw_ring(hx, hy, hr, col_outline, thickness=1.15, softness=0.05)

    def test_hit(self, context: "Context", p: Vector) -> bool:
        self._hover_handle = self._pick_hover_handle(context, p)
        return self._hover_handle is not None

    def on_left_press(self, context: "Context", event: "Event") -> bool:
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
