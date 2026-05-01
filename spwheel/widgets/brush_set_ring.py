"""Brush-set ring: ``PickerBrushButton`` instances on a radial layout."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Sequence, Tuple

from ..pg.pg_wheel_storage import SculptPaintWheelStorage

from ..gpu.utils import compute_slot_positions_in_double_ring, compute_slot_radius_in_double_ring

from .buttons.pk_brush import PickerBrushButton
from .widget import WidgetRing
from ..gpu.draw import draw_circle_fill, draw_ring, draw_text


USE_DEBUG=True


if TYPE_CHECKING:
    from bpy.types import Context, Event
    from ..pg.pg_wheel_prefs import WheelPrefs, BrushSet, WheelTheme
    from ..pg.pg_wheel_storage import SculptPaintWheelStorage
    from ..pg.pg_brush_metadata import BrushMetadata


COL_TOOLSET_DOT_ACTIVE = (0.72, 0.60, 0.26, 0.88)
COL_TOOLSET_DOT = (0.32, 0.34, 0.38, 0.55)

class BrushSetRing(WidgetRing):
    """Places ``PickerBrushButton`` children on a ring using ``gpu.utils`` layout."""
    _storage: SculptPaintWheelStorage
    _pickers: list[PickerBrushButton] = []
    _last_active_index: int = -1

    interactable = False

    def init(self) -> None:
        super().init()
        self._pickers = []
        self.slot_count = 0
        self._last_active_index = -1

    @property
    def active_brush_set(self) -> Optional[BrushSet]:
        return self._storage.active_brush_set

    @property
    def brush_sets(self) -> Sequence[BrushSet]:
        return self._storage.brush_sets
    
    @property
    def active_brush_set_index(self) -> int:
        return self._storage.active_brush_set_index

    def setup_event_subs(self) -> Tuple[Tuple[str, Callable[[Context, Event], None]]] | None:
        return (
            ('scroll_up', self.on_scroll_up),
            ('scroll_down', self.on_scroll_down)
        )

    def on_scroll_up(self, context: Context, event: Event) -> None:
        if event.shift:
            # Shift + scroll up: change to next brush set
            self._storage.active_brush_set_index += 1
            if self._storage.active_brush_set_index >= len(self.brush_sets):
                self._storage.active_brush_set_index = 0
            if self._last_active_index != self.active_brush_set_index:
                self._rebuild_pickers()
        else:
            # Scroll up: change to next page.
            active_brush_set: BrushSet = self.active_brush_set
            slot_count: int = self.slot_count
            max_page_index = (len(active_brush_set.items) + slot_count - 1) // slot_count - 1
            last_page_index = active_brush_set.page_index
            active_brush_set.page_index += 1
            if active_brush_set.page_index > max_page_index:
                active_brush_set.page_index = max_page_index
            if last_page_index != active_brush_set.page_index:
                self._rebuild_pickers(context)

    def on_scroll_down(self, context: Context, event: Event) -> None:
        if event.shift:
            # Shift + scroll down: change to previous brush set
            self._storage.active_brush_set_index -= 1
            if self._storage.active_brush_set_index < 0:
                self._storage.active_brush_set_index = len(self.brush_sets) - 1
            if self._last_active_index != self.active_brush_set_index:
                self._rebuild_pickers(context)
        else:
            # Scroll down: change to previous page.
            active_brush_set: BrushSet = self.active_brush_set
            last_page_index = active_brush_set.page_index
            active_brush_set.page_index -= 1
            if active_brush_set.page_index < 0:
                active_brush_set.page_index = 0
            if last_page_index != active_brush_set.page_index:
                self._rebuild_pickers(context)

    def activate(self, context: Context, prefs: WheelPrefs, storage: SculptPaintWheelStorage) -> None:
        self._storage = storage
        self.ring_padding = prefs.brush_set_ring.ring_padding
        slot_count = prefs.brush_set_ring.slot_count
        if slot_count != self.slot_count:
            self.slot_count = slot_count
            self._sync_picker_slots()
        self._rebuild_pickers(context)

    def deactivate_all_pickers(self) -> None:
        for pb in self._pickers:
            pb.active = False

    def get_page_brushes_metadata(self) -> list[BrushMetadata]:
        active_brush_set: BrushSet = self.active_brush_set
        slot_count: int = self.slot_count
        start_index = active_brush_set.page_index * slot_count
        end_index = start_index + slot_count
        if end_index > len(active_brush_set.items):
            end_index = len(active_brush_set.items)
        return active_brush_set.items[start_index:end_index]

    def _sync_picker_slots(self) -> None:
        if USE_DEBUG:
            print(f"Syncing picker slots: {self.slot_count}")
        # Remove all pickers first.
        for p in self._pickers:
            self.remove_child(p, free=True)
        self._pickers.clear()

        count = self.slot_count
        if count == 0:
            if USE_DEBUG:
                print("No pickers to sync")
            return

        # Compute slot positions and radius.
        cx, cy = self.center
        slot_r = compute_slot_radius_in_double_ring(self.radius_inner, self.radius_outer, count, ring_padding=self.ring_padding)
        positions = compute_slot_positions_in_double_ring(cx, cy, self.radius_inner, self.radius_outer, count)

        # Create and position pickers.
        for i in range(count):
            pb = PickerBrushButton()
            px, py = positions[i]
            # position is relative to the center of the ring (local coordinates)
            pb.set_transform(px - cx, py - cy, slot_r)
            self.add_child(pb)
            self._pickers.append(pb)
            if USE_DEBUG:
                print(f"Added picker {i}: {pb.label}")

    def _rebuild_pickers(self, context: Context) -> None:
        if USE_DEBUG:
            print(f"Rebuilding pickers: {self.active_brush_set_index}")
        self._last_active_index = self.active_brush_set_index
        if not self._pickers:
            if USE_DEBUG:
                print("No pickers to rebuild")
            return

        # If no active brush set, clear all pickers.
        if self.active_brush_set_index == -1:
            for pb in self._pickers:
                pb.clear_brush_metadata()
            return

        # Get brushes metadata for the current page.
        brushes_metadata = self.get_page_brushes_metadata()
        # Set brush metadata for each picker.
        for i, pb in enumerate(self._pickers):
            if i < len(brushes_metadata):
                if USE_DEBUG:
                    print(f"Setting brush metadata for picker {i}: {brushes_metadata[i].name}")
                pb.set_brush_metadata(brushes_metadata[i], show_label=False)
            else:
                # If no brush metadata, clear the picker data.
                if USE_DEBUG:
                    print(f"Clearing brush metadata for picker {i}")
                pb.clear_brush_metadata()

        if USE_DEBUG:
            print(f"Rebuilt {len(self._pickers)} pickers")
            
        context.region.tag_redraw()

    def draw(self, context: Context, theme: WheelTheme) -> None:
        draw_ring(*self.offset, self.radius_outer, theme.base_outline_color, thickness=1.25)
        draw_ring(*self.offset, self.radius_inner, theme.base_outline_color, thickness=1.25)
        self.draw_active_brush_set_title(context, theme)
        self.draw_page_indicator(context, theme)


    def draw_active_brush_set_title(self, context: Context, theme: WheelTheme) -> None:
        active_brush_set: BrushSet = self.active_brush_set
        if not active_brush_set:
            return
        title = active_brush_set.name
        # Draw over the wheel.
        wheel = self.wheel
        draw_text(
            title,
            0,
            0 + wheel.radius + 14.0,
            size=14.0,
            color=theme.text_color,
            align="CENTER",
            shadow=True,
            valign='BOTTOM'
        )

    def draw_page_indicator(self, context: Context, theme: WheelTheme) -> None:
        active_brush_set: BrushSet = self.active_brush_set
        if not active_brush_set:
            return
        if self.slot_count <= 0:
            return
        page_index = active_brush_set.page_index
        page_count = (len(active_brush_set.items) + self.slot_count - 1) // self.slot_count
        if page_count <= 1:
            return
        wheel = self.wheel
        dot_radius = 3.0
        spacing = min(10.0, max(5.0, 180.0 / max(page_count, 1)))
        total_w = (page_count - 1) * spacing
        start_x = -total_w * 0.5
        dot_y = -wheel.radius - 14.0
        for i in range(page_count):
            dx = start_x + i * spacing
            col = COL_TOOLSET_DOT_ACTIVE if i == page_index else COL_TOOLSET_DOT
            draw_circle_fill(dx, dot_y, dot_radius, col, softness=0.04)

        # draw page number
        draw_text(
            f"{page_index + 1} / {page_count}",
            0,
            dot_y - dot_radius - 5.0,
            size=9.0,
            color=theme.text_color,
            align="CENTER",
            shadow=True,
            valign='TOP'
        )
