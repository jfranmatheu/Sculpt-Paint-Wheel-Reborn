"""Radial pie (tarta) + per-slot icons from custom data (mode-agnostic protocols)."""

from __future__ import annotations

import math
from math import pi as PI
from typing import TYPE_CHECKING, Optional, Protocol, Sequence, runtime_checkable

from ..gpu.button_texture import get_custom_button_texture
from ..gpu.draw import COL_PIE_TARTA, COL_PIE_TARTA_OP, draw_pie_split_ring, draw_textured_quad
from ..gpu.utils import compute_custom_button_layout_count, compute_slot_positions, compute_slot_radius, map_custom_layout_indices
from .core import Widget

if TYPE_CHECKING:
    from bpy.types import Context


def layout_sector_from_pointer(mx: float, my: float, cx: float, cy: float, n: int) -> int:
    """Wedge index 0..n-1 matching ``draw_pie_split_ring`` (first slice at 180 deg, CW)."""
    if n <= 0:
        return 0
    angle = math.atan2(my - cy, mx - cx)
    step = 2.0 * math.pi / n
    shifted = (PI - angle + 2.0 * PI) % (2.0 * PI)
    i = int(math.floor(shifted / step))
    return i % n


@runtime_checkable
class RadialCustomItem(Protocol):
    """One slot on the pie (host-defined payload TBD)."""

    @property
    def name(self) -> str: ...

    @property
    def image_path(self) -> str: ...

    @property
    def is_operator_slot(self) -> bool: ...


class RadialPieWidget(Widget):
    """GPU pie ring + icons; hit-test prefers icon discs then sector wedge."""

    __slots__ = (
        "_items",
        "layout_n",
        "custom_layout_map",
        "tarta_outer_radius",
        "tarta_inner_ratio",
        "icon_ring_radius",
        "custom_radius",
        "custom_positions",
        "hover_layout_slot",
        "hover_custom_bid",
    )

    def __init__(self, items: Sequence[RadialCustomItem]) -> None:
        super().__init__()
        self.set_local(0.0, 0.0)
        self._items: list[RadialCustomItem] = list(items)
        self.layout_n = 0
        self.custom_layout_map: list[int] = []
        self.tarta_outer_radius = 0.0
        self.tarta_inner_ratio = 0.5
        self.icon_ring_radius = 0.0
        self.custom_radius = 0.0
        self.custom_positions: list[tuple[float, float]] = []
        self.hover_layout_slot: int = -1
        self.hover_custom_bid: int = -1

    def set_items(self, items: Sequence[RadialCustomItem]) -> None:
        self._items = list(items)

    def layout(self) -> None:
        root = self.wheel_root()
        n = len(self._items)
        if root is None or n == 0:
            self.layout_n = 0
            self.custom_layout_map = []
            self.custom_positions = []
            self.tarta_outer_radius = 0.0
            super().layout()
            return
        cx, cy = root.center_x, root.center_y
        self.layout_n = compute_custom_button_layout_count(n)
        self.custom_layout_map = map_custom_layout_indices(self.layout_n, n)
        self.tarta_outer_radius = root.radius * 0.48
        self.tarta_inner_ratio = min(0.92, 42.0 / max(self.tarta_outer_radius, 1.0))
        self.icon_ring_radius = self.tarta_outer_radius * 0.72
        self.custom_radius = compute_slot_radius(self.icon_ring_radius, self.layout_n) * 0.88
        self.custom_positions = compute_slot_positions(cx, cy, self.icon_ring_radius, self.layout_n)
        super().layout()

    def draw(self, context: "Context") -> None:
        if not self.visible:
            return
        self.draw_self(context)

    def draw_self(self, context: "Context") -> None:
        from ..core.gpu.imm_2d import draw_text

        if self.layout_n <= 0 or self.tarta_outer_radius <= 0.0:
            return
        root = self.wheel_root()
        if root is None:
            return
        cx, cy = root.center_x, root.center_y
        kinds2: list[int] = []
        for si in range(self.layout_n):
            bid = self.custom_layout_map[si]
            if bid < 0:
                kinds2.append(0)
            else:
                kinds2.append(1 if self._items[bid].is_operator_slot else 0)
        draw_pie_split_ring(
            cx,
            cy,
            self.tarta_outer_radius,
            self.tarta_inner_ratio,
            self.layout_n,
            self.hover_layout_slot,
            COL_PIE_TARTA,
            COL_PIE_TARTA_OP,
            kinds2,
            inner_soft=0.025,
            outer_soft=0.025,
        )
        col_text = (0.70, 0.72, 0.76, 0.98)
        half = self.custom_radius * 0.85
        for i, (sx, sy) in enumerate(self.custom_positions):
            if i >= len(self.custom_layout_map):
                break
            bid = self.custom_layout_map[i]
            if bid < 0:
                continue
            btn = self._items[bid]
            is_hov = bid == self.hover_custom_bid
            tex = get_custom_button_texture(btn.image_path)
            if tex is not None:
                h = half * (1.08 if is_hov else 1.0)
                draw_textured_quad(sx, sy, h, tex, opacity=1.0 if is_hov else 0.94)
            elif btn.name:
                draw_text(btn.name[:10], sx, sy, size=9.0, color=col_text, align="CENTER", shadow=True)

    def sync_hover(self, mx: float, my: float) -> None:
        self.hover_layout_slot = -1
        self.hover_custom_bid = -1
        root = self.wheel_root()
        if root is None or self.layout_n <= 0:
            return
        cx, cy = root.center_x, root.center_y
        inner_r = self.tarta_outer_radius * self.tarta_inner_ratio

        for i, (sx, sy) in enumerate(self.custom_positions):
            if i >= len(self.custom_layout_map):
                break
            bid = self.custom_layout_map[i]
            if bid < 0:
                continue
            if math.hypot(mx - sx, my - sy) <= self.custom_radius:
                self.hover_custom_bid = bid
                self.hover_layout_slot = i
                return

        r_pt = math.hypot(mx - cx, my - cy)
        if r_pt >= inner_r - 1.0 and r_pt <= self.tarta_outer_radius + 3.0:
            si = layout_sector_from_pointer(mx, my, cx, cy, self.layout_n)
            if 0 <= si < len(self.custom_layout_map):
                bid = self.custom_layout_map[si]
                if bid >= 0:
                    self.hover_custom_bid = bid
                    self.hover_layout_slot = si

    def hit_test(self, mx: float, my: float) -> Optional[Widget]:
        if not self.visible or not self.enabled:
            return None
        self.sync_hover(mx, my)
        if self.hover_custom_bid >= 0:
            return self
        return None
