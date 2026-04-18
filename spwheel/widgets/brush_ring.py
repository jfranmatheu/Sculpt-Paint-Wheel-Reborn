"""Brush-set ring: ``PickerBrushButton`` instances on a radial layout."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, Sequence, runtime_checkable

from ..gpu.brush_preview import get_brush_preview_texture
from ..gpu.utils import compute_slot_positions, compute_slot_radius, draw_circle_fill, draw_ring, draw_textured_circle
from .button import ButtonBase
from .core import Widget

if TYPE_CHECKING:
    from bpy.types import Context


@runtime_checkable
class BrushItemView(Protocol):
    """Minimal brush slot data for drawing (host types can satisfy structurally)."""

    @property
    def name(self) -> str: ...

    @property
    def preview_path(self) -> str: ...


@runtime_checkable
class BrushSetSource(Protocol):
    """Ordered brush slots (structure TBD — replace with richer type later)."""

    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> BrushItemView: ...


class ListBrushSet:
    """Concrete adapter when you already have a sequence of brush-like objects."""

    def __init__(self, items: Sequence[object]) -> None:
        self._items = list(items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> object:
        return self._items[index]


class PickerBrushButton(ButtonBase):
    """One brush slot: preview disk + rings when hover/active."""

    __slots__ = ("slot_index", "active", "icon_scale", "show_name", "_item_ref")

    def __init__(
        self,
        slot_index: int,
        hit_radius: float,
        *,
        icon_scale: float = 0.92,
        show_name: bool = False,
    ) -> None:
        super().__init__(hit_radius=hit_radius)
        self.slot_index = int(slot_index)
        self.active: bool = False
        self.icon_scale = float(icon_scale)
        self.show_name: bool = show_name
        self._item_ref: Optional[BrushItemView] = None

    def bind_item(self, item: Optional[BrushItemView]) -> None:
        self._item_ref = item

    def draw_self(self, context: "Context") -> None:
        from ..core.gpu.imm_2d import draw_text

        item = self._item_ref
        sx, sy = self._region_x, self._region_y
        r = self.hit_radius
        col_bg = (0.10, 0.105, 0.12, 0.88)
        col_hov = (0.20, 0.22, 0.28, 0.42)
        col_ring = (0.16, 0.16, 0.2, 0.97)
        col_ring_act = (0.78, 0.62, 0.22, 0.92)
        col_ring_hov = (0.40, 0.44, 0.50, 0.62)
        col_text = (0.70, 0.72, 0.76, 0.98)

        draw_circle_fill(sx, sy, r, col_bg, softness=0.015)
        if self.hovered:
            draw_circle_fill(sx, sy, r, col_hov, softness=0.015)

        icon_r = r * self.icon_scale
        if item is not None and item.preview_path:
            tex = get_brush_preview_texture(item.preview_path, item.name)
            if tex is not None:
                draw_textured_circle(sx, sy, icon_r, tex, opacity=1.0, softness=0.025)

        if self.active:
            draw_ring(sx, sy, r, col_ring_act, thickness=2.0, softness=0.012)
        elif self.hovered:
            draw_ring(sx, sy, r, col_ring_hov, thickness=1.5, softness=0.012)
        else:
            draw_ring(sx, sy, r, col_ring, thickness=1.0, softness=0.012)

        if self.show_name and item is not None and item.name:
            draw_text(
                item.name,
                sx, sy - r - 10,
                size=11.0,
                color=col_text,
                align='CENTER',
                shadow=True,
            )


class BrushSetRing(Widget):
    """Places ``PickerBrushButton`` children on a ring using ``gpu.utils`` layout."""

    __slots__ = ("_source", "ring_scale", "icon_scale", "show_names", "_pickers")

    def __init__(
        self,
        source: Optional[BrushSetSource],
        *,
        ring_scale: float = 0.74,
        icon_scale: float = 0.92,
        show_names: bool = False,
    ) -> None:
        super().__init__()
        self.set_local(0.0, 0.0)
        self._source: Optional[BrushSetSource] = source
        self.ring_scale = float(ring_scale)
        self.icon_scale = float(icon_scale)
        self.show_names = bool(show_names)
        self._pickers: list[PickerBrushButton] = []
        self._rebuild_pickers()

    def set_source(self, source: Optional[BrushSetSource]) -> None:
        self._source = source
        self._rebuild_pickers()

    def _rebuild_pickers(self) -> None:
        for p in self._pickers:
            self.remove_child(p)
        self._pickers.clear()
        if self._source is None or len(self._source) == 0:
            return
        n = len(self._source)
        count = max(7, n)
        root = self.wheel_root()
        ring_r = root.radius * self.ring_scale if root else 100.0
        slot_r = compute_slot_radius(ring_r, count)
        for i in range(n):
            pb = PickerBrushButton(i, slot_r, icon_scale=self.icon_scale, show_name=self.show_names)
            self.add_child(pb)
            self._pickers.append(pb)
            try:
                pb.bind_item(self._source[i])
            except Exception:
                pb.bind_item(None)

    def layout(self) -> None:
        root = self.wheel_root()
        if root is None or self._source is None or len(self._source) == 0:
            super().layout()
            return
        n = len(self._source)
        count = max(7, n)
        ring_r = root.radius * self.ring_scale
        cx, cy = root.center_x, root.center_y
        positions = compute_slot_positions(cx, cy, ring_r, count)
        slot_r = compute_slot_radius(ring_r, count)
        for i, pb in enumerate(self._pickers):
            if i >= len(positions):
                break
            px, py = positions[i]
            pb.set_local(px - root.center_x, py - root.center_y)
            pb.hit_radius = slot_r
        super().layout()

    def sync_hover(self, mx: float, my: float, active_index: int = -1) -> None:
        for pb in self._pickers:
            pb.active = pb.slot_index == active_index
            pb.set_hover(mx, my)

    def hit_test(self, mx: float, my: float) -> Optional[Widget]:
        if not self.visible or not self.enabled:
            return None
        for child in reversed(self.children):
            hit = child.hit_test(mx, my)
            if hit is not None:
                return hit
        return None
