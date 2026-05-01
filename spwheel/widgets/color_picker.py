"""HSV ring + arcs + handles; samples color via host ``HsvSampleProvider`` (mode-agnostic)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Protocol

from ..gpu.colpk import draw_colpk_hue_ring, draw_colpk_sat_arc, draw_colpk_val_arc
from ..gpu.colpk_helpers import (
    S_ANGLE_BOT,
    S_ANGLE_TOP,
    V_ANGLE_BOT,
    V_ANGLE_TOP,
    colpk_linked_preview_enabled,
)
from ..gpu.utils import draw_circle_fill, draw_ring
from .widget import Widget

if TYPE_CHECKING:
    from bpy.types import Context


class HsvSampleProvider(Protocol):
    """Host supplies HSV in 0..1 (e.g. sculpt brush or a weight paint override)."""

    def sample_hsv(self, context: "Context") -> tuple[float, float, float]:
        ...


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


class ColorPickerWidget(Widget):
    """Draws GPU colpk rings when ``hsv_provider`` is set and ``show`` is True."""

    __slots__ = (
        "hsv_provider",
        "show",
        "hue_inner_r",
        "hue_outer_r",
        "sv_inner_r",
        "sv_outer_r",
    )

    def __init__(self, hsv_provider: Optional[HsvSampleProvider] = None) -> None:
        super().__init__()
        self.set_local(0.0, 0.0)
        self.hsv_provider = hsv_provider
        self.show: bool = True
        self.hue_inner_r = 0.0
        self.hue_outer_r = 0.0
        self.sv_inner_r = 0.0
        self.sv_outer_r = 0.0

    def layout(self) -> None:
        root = self.wheel_root()
        if root is None:
            super().layout()
            return
        wr = root.radius
        base_outer = max(28.0, wr * 0.30)
        gap = max(5.0, wr * 0.028)
        hue_thick = max(14.0, wr * 0.062)
        self.hue_inner_r = base_outer + gap
        self.hue_outer_r = self.hue_inner_r + hue_thick
        gap2 = max(4.0, wr * 0.022)
        sv_thick = max(16.0, wr * 0.07)
        self.sv_inner_r = self.hue_outer_r + gap2
        self.sv_outer_r = self.sv_inner_r + sv_thick
        super().layout()

    def draw(self, context: "Context") -> None:
        if not self.visible:
            return
        self.draw_self(context)
        for child in self.children:
            child.draw(context)

    def draw_self(self, context: "Context") -> None:
        if not self.show or self.hsv_provider is None or self.hue_outer_r <= 0.0:
            return
        root = self.wheel_root()
        if root is None:
            return
        cx, cy = root.center_x, root.center_y
        h, s, v = self.hsv_provider.sample_hsv(context)
        h = max(0.0, min(1.0, h))
        s = max(0.0, min(1.0, s))
        v = max(0.0, min(1.0, v))
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
        hr = max(3.0, root.radius * 0.018)
        col_outline = (0.82, 0.84, 0.88, 0.92)
        col_fill = (0.06, 0.062, 0.07, 0.96)
        for hp in _handle_positions(
            cx, cy, self.hue_inner_r, self.hue_outer_r, self.sv_inner_r, self.sv_outer_r, h, s, v,
        ):
            hx, hy = hp
            draw_circle_fill(hx, hy, hr, col_fill, softness=0.12)
            draw_ring(hx, hy, hr, col_outline, thickness=1.15, softness=0.05)

    def hit_self(self, mx: float, my: float) -> Optional[Widget]:
        return None
