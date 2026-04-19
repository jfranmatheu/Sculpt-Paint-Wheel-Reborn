"""Brush-set ring: ``PickerBrushButton`` instances on a radial layout."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Sequence, Tuple

from ..gpu.utils import compute_slot_positions, compute_slot_radius

from .buttons.pk_brush import PickerBrushButton
from .widget import WidgetRing
from ..gpu.draw import draw_circle_fill, draw_ring


if TYPE_CHECKING:
    from bpy.types import Context
    from ..pg.pg_wheel_prefs import WheelPrefs, BrushSet, WheelTheme


class BrushSetRing(WidgetRing):
    """Places ``PickerBrushButton`` children on a ring using ``gpu.utils`` layout."""
    _data: WheelPrefs
    _pickers: list[PickerBrushButton] = []
    _last_active_index: int = -1

    @property
    def active_brush_set(self) -> Optional[BrushSet]:
        return self._data.active_brush_set

    @property
    def brush_sets(self) -> Sequence[BrushSet]:
        return self._data.brush_sets
    
    @property
    def active_brush_set_index(self) -> int:
        return self._data.active_brush_set_index

    def setup_event_subs(self) -> Tuple[Tuple[str, Callable[[Context], None]]] | None:
        return (
            ('scroll_up', self.on_scroll_up),
            ('scroll_down', self.on_scroll_down)
        )

    def on_scroll_up(self, context: Context) -> None:
        self._data.active_brush_set_index += 1
        if self._data.active_brush_set_index >= len(self.brush_sets):
            self._data.active_brush_set_index = 0
        if self._last_active_index != self.active_brush_set_index:
            self._rebuild_pickers()

    def on_scroll_down(self, context: Context) -> None:
        self._data.active_brush_set_index -= 1
        if self._data.active_brush_set_index < 0:
            self._data.active_brush_set_index = len(self.brush_sets) - 1
        if self._last_active_index != self.active_brush_set_index:
            self._rebuild_pickers()

    def activate(self, context: Context, prefs: WheelPrefs) -> None:
        self._data = prefs
        if not hasattr(self, '_pickers'):
            self._pickers = []
        self._rebuild_pickers()

    def _rebuild_pickers(self) -> None:
        self._last_active_index = self.active_brush_set_index
        for p in self._pickers:
            self.remove_child(p, free=True)
        self._pickers.clear()
        if self.active_brush_set_index == -1:
            return
        brushes_metadata = self.active_brush_set.get_brushes_metadata()
        if len(brushes_metadata) == 0:
            return
        n = len(brushes_metadata)
        count = max(12, n)
        ring_r = self.radius_outer
        cx, cy = self.center, self.center
        positions = compute_slot_positions(cx, cy, ring_r, count)
        slot_r = compute_slot_radius(ring_r, count)
        for i in range(n):
            pb = PickerBrushButton()
            px, py = positions[i]
            pb.set_transform(px - cx, py - cy, slot_r)
            self.add_child(pb)
            self._pickers.append(pb)
            pb.set_brush_metadata(brushes_metadata[i], show_label=False)


    def draw(self, context: Context, theme: WheelTheme) -> None:
        draw_ring(*self.offset, self.radius_outer, theme.base_outline_color)
        draw_ring(*self.offset, self.radius_inner, theme.base_outline_color)
