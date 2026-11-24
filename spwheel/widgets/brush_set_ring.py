"""Brush-set ring: ``PickerBrushButton`` instances on a radial layout."""

from __future__ import annotations

from math import asin, pi
from typing import TYPE_CHECKING, Callable, Optional, Sequence, Tuple

from ..pg.pg_brush_set import BrushSetPreferences
from ..pg.pg_wheel_storage import SculptPaintWheelStorage

from ..gpu.utils import compute_slot_positions_in_double_ring

from .buttons.pk_brush import PickerBrushButton
from .widget import WidgetRing
from ..gpu.draw import draw_circle_fill, draw_ring, draw_text
from ..core.gpu.imm_2d import draw_lines


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
    _wg_prefs = BrushSetPreferences

    _storage: SculptPaintWheelStorage
    _pickers: list[PickerBrushButton] = []
    _last_active_index: int = -1

    interactable = True
    use_modal = True

    @staticmethod
    def _compute_layout_count_from_slot_radius(
        center_radius: float,
        slot_radius: float,
        slot_padding: float = 0.0,
    ) -> int:
        """Compute how many slots can fit around *center_radius* with tangential padding."""
        if center_radius <= 0.0 or slot_radius <= 0.0:
            return 0
        effective_radius = slot_radius + max(0.0, slot_padding) * 0.5
        if effective_radius >= center_radius:
            return 1
        ratio = max(0.0, min(1.0, effective_radius / center_radius))
        angle = asin(ratio)
        if angle <= 0.0:
            return 0
        return max(1, int(pi / angle))

    def init(self) -> None:
        super().init()
        self._pickers = []
        self.slot_count = 0
        self._slot_radius = 0.0
        self._last_active_index = -1
        self._is_page_dragging = False
        self._page_drag_start_x = 0.0
        self._page_drag_steps_applied = 0
        self._page_drag_step_px = 14.0
        self._is_set_dragging = False
        self._set_drag_start_x = 0.0
        self._set_drag_steps_applied = 0
        self._set_drag_step_px = 20.0
        self._hover_page_area = False
        self._hover_set_area = False

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
            self._step_set(context, 1)
        elif self.active_brush_set is None:
            return  # (No brush set in this mode: no pages.)
        else:
            # Scroll up: change to next page.
            active_brush_set: BrushSet = self.active_brush_set
            slot_count: int = self.slot_count
            if slot_count <= 0:
                return
            max_page_index = (len(active_brush_set.items) + slot_count - 1) // slot_count - 1
            last_page_index = active_brush_set.page_index
            active_brush_set.page_index += 1
            if active_brush_set.page_index > max_page_index:
                active_brush_set.page_index = max_page_index
            if last_page_index != active_brush_set.page_index:
                self._rebuild_pickers(context)

    def on_scroll_down(self, context: Context, event: Event) -> None:
        if event.shift:
            self._step_set(context, -1)
        elif self.active_brush_set is None:
            return  # (No brush set in this mode: no pages.)
        else:
            # Scroll down: change to previous page.
            active_brush_set: BrushSet = self.active_brush_set
            if self.slot_count <= 0:
                return
            last_page_index = active_brush_set.page_index
            active_brush_set.page_index -= 1
            if active_brush_set.page_index < 0:
                active_brush_set.page_index = 0
            if last_page_index != active_brush_set.page_index:
                self._rebuild_pickers(context)

    def on_wheel_activate(self, context: Context, wheel_prefs: WheelPrefs, storage: SculptPaintWheelStorage, wg_prefs: BrushSetPreferences) -> None:
        self._storage = storage
        self.wg_prefs = wg_prefs
        self.ring_padding = wg_prefs.ring_padding
        self._sync_picker_slots()
        self._rebuild_pickers(context)

    def _on_wheel_activate(self, context: Context, wheel_prefs: WheelPrefs, storage: SculptPaintWheelStorage) -> None:
        # Widget._on_wheel_activate enables children before/while activating them.
        # Re-apply picker visibility afterwards so unused slots remain disabled.
        super()._on_wheel_activate(context, wheel_prefs, storage)
        self._rebuild_pickers(context)

    def deactivate_all_pickers(self) -> None:
        for pb in self._pickers:
            pb.active = False

    def get_page_brushes_metadata(self) -> list[BrushMetadata]:
        active_brush_set: BrushSet = self.active_brush_set
        slot_count: int = self.slot_count
        if slot_count <= 0:
            return []
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

        inner = min(self.radius_inner, self.radius_outer) + self.ring_padding
        outer = max(self.radius_inner, self.radius_outer) - self.ring_padding
        radial_space = max(0.0, outer - inner)
        center_radius = 0.5 * (inner + outer)
        preferred_slot_radius = max(0.0, self.wg_prefs.slot_size * 0.5)
        slot_r = min(preferred_slot_radius, radial_space * 0.5)
        slot_padding = max(0.0, self.wg_prefs.slot_padding)
        count = self._compute_layout_count_from_slot_radius(center_radius, slot_r, slot_padding)
        self._slot_radius = slot_r
        self.slot_count = count
        if count == 0:
            if USE_DEBUG:
                print("No pickers to sync")
            return

        # Compute slot positions and radius.
        cx, cy = self.center
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

    def _layout_visible_pickers(self, visible_count: int) -> None:
        visible_count = max(0, min(visible_count, len(self._pickers)))
        cx, cy = self.center
        positions = []
        if visible_count > 0:
            positions = compute_slot_positions_in_double_ring(
                cx,
                cy,
                self.radius_inner,
                self.radius_outer,
                visible_count,
            )
        for i, pb in enumerate(self._pickers):
            if i < visible_count:
                px, py = positions[i]
                pb.enabled = True
                pb.set_transform(px - cx, py - cy, self._slot_radius)
            else:
                pb.enabled = False

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
                pb.enabled = False
            return

        # Get brushes metadata for the current page.
        slot_count = self.slot_count
        if slot_count <= 0:
            return
        max_page_index = max(0, (len(self.active_brush_set.items) + slot_count - 1) // slot_count - 1)
        if self.active_brush_set.page_index > max_page_index:
            self.active_brush_set.page_index = max_page_index
        brushes_metadata = self.get_page_brushes_metadata()
        self._layout_visible_pickers(len(brushes_metadata))
        # Set brush metadata for each picker.
        for i, pb in enumerate(self._pickers):
            if i < len(brushes_metadata):
                if USE_DEBUG:
                    print(f"Setting brush metadata for picker {i}: {brushes_metadata[i].name}")
                pb.enabled = True
                pb.set_brush_metadata(brushes_metadata[i], show_label=False)
            else:
                # If no brush metadata, clear the picker data.
                if USE_DEBUG:
                    print(f"Clearing brush metadata for picker {i}")
                pb.clear_brush_metadata()
                pb.enabled = False

        if USE_DEBUG:
            print(f"Rebuilt {len(self._pickers)} pickers")
            
        context.region.tag_redraw()

    def _get_page_indicator_layout(self) -> tuple[int, int, float, float, float, float, float] | None:
        active_brush_set: BrushSet = self.active_brush_set
        if not active_brush_set:
            return None
        if self.slot_count <= 0:
            return None
        page_count = (len(active_brush_set.items) + self.slot_count - 1) // self.slot_count
        if page_count <= 1:
            return None
        page_index = max(0, min(active_brush_set.page_index, page_count - 1))
        wheel = self.wheel
        dot_radius = 3.0
        spacing = min(10.0, max(5.0, 180.0 / max(page_count, 1)))
        total_w = (page_count - 1) * spacing
        start_x = -total_w * 0.5
        dot_y = -wheel.radius - 14.0
        return (page_index, page_count, dot_radius, spacing, start_x, dot_y, total_w)

    def _get_title_layout(self) -> tuple[str, float, float] | None:
        active_brush_set: BrushSet = self.active_brush_set
        if not active_brush_set:
            return None
        title = (active_brush_set.name or "").strip()
        if not title:
            return None
        wheel = self.wheel
        title_y = wheel.radius + 14.0
        # Rough width estimate for hit/arrow placement (no font metrics dependency).
        title_half_w = max(26.0, len(title) * 4.2)
        return (title, title_y, title_half_w)

    def _step_page(self, context: Context, delta: int) -> bool:
        if delta == 0:
            return False
        active_brush_set: BrushSet = self.active_brush_set
        if not active_brush_set:
            return False
        slot_count = self.slot_count
        if slot_count <= 0:
            return False
        max_page_index = max(0, (len(active_brush_set.items) + slot_count - 1) // slot_count - 1)
        last_page_index = active_brush_set.page_index
        active_brush_set.page_index = max(0, min(max_page_index, active_brush_set.page_index + delta))
        if active_brush_set.page_index != last_page_index:
            self._rebuild_pickers(context)
            return True
        return False

    def _step_set(self, context: Context, delta: int) -> bool:
        if delta == 0:
            return False
        set_count = len(self.brush_sets)
        if set_count <= 0:
            return False
        last_index = self.active_brush_set_index
        self._storage.active_brush_set_index = (self._storage.active_brush_set_index + delta) % set_count
        if self._storage.active_brush_set_index != last_index:
            wheel = self.wheel
            if hasattr(wheel, "on_brush_set_change"):
                wheel.on_brush_set_change(context)
            self._rebuild_pickers(context)
            return True
        return False

    def test_hit(self, context: Context, p) -> bool:
        self._hover_page_area = False
        self._hover_set_area = False

        title_layout = self._get_title_layout()
        if title_layout is not None:
            _title, title_y, title_half_w = title_layout
            if abs(p.y - title_y) <= 14.0 and abs(p.x) <= title_half_w + 28.0:
                self._hover_set_area = True
                return True

        layout = self._get_page_indicator_layout()
        if layout is None:
            return False
        _page_index, _page_count, dot_radius, _spacing, _start_x, dot_y, total_w = layout
        # Thin horizontal target around page dots; low-risk and tablet friendly.
        half_w = total_w * 0.5 + 16.0
        if abs(p.y - dot_y) > max(14.0, dot_radius * 4.0):
            return False
        self._hover_page_area = -half_w <= p.x <= half_w
        return self._hover_page_area

    def on_left_press(self, context: Context, event: Event) -> bool:
        mx, _my = self.wheel.to_local(event.mouse_region_x, event.mouse_region_y)
        if self._hover_set_area:
            self._is_set_dragging = True
            self._set_drag_start_x = mx
            self._set_drag_steps_applied = 0
            title_layout = self._get_title_layout()
            if title_layout is not None:
                _title, _title_y, title_half_w = title_layout
                self._set_drag_step_px = max(16.0, min(42.0, (title_half_w * 2.0) / 4.0))
            return True
        if self._hover_page_area:
            self._is_page_dragging = True
            self._page_drag_start_x = mx
            self._page_drag_steps_applied = 0
            layout = self._get_page_indicator_layout()
            if layout is not None:
                _page_index, _page_count, dot_radius, spacing, _start_x, _dot_y, _total_w = layout
                self._page_drag_step_px = max(12.0, spacing + dot_radius * 1.2)
            return True
        return False

    def modal(self, context: Context, event: Event) -> bool:
        if not self._is_page_dragging and not self._is_set_dragging:
            return False
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            mx, _my = self.wheel.to_local(event.mouse_region_x, event.mouse_region_y)
            if self._is_set_dragging:
                dx = mx - self._set_drag_start_x
                target_steps = int(dx / max(1.0, self._set_drag_step_px))
                delta_steps = target_steps - self._set_drag_steps_applied
                if delta_steps != 0:
                    self._set_drag_steps_applied = target_steps
                    self._step_set(context, delta_steps)
                return True
            dx = mx - self._page_drag_start_x
            target_steps = int(dx / max(1.0, self._page_drag_step_px))
            delta_steps = target_steps - self._page_drag_steps_applied
            if delta_steps != 0:
                self._page_drag_steps_applied = target_steps
                self._step_page(context, delta_steps)
            return True
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._is_page_dragging = False
            self._is_set_dragging = False
            return False
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self._is_page_dragging = False
            self._is_set_dragging = False
            return False
        return True

    def draw(self, context: Context, theme: WheelTheme) -> None:
        # draw_ring(*self.offset, self.radius_outer, theme.base_outline_color, thickness=1.25)
        color_picker = getattr(self.wheel, 'color_picker', None)
        if color_picker is not None and color_picker.enabled:
            draw_ring(*self.offset, self.radius_inner, theme.base_outline_color, thickness=1.25)
        self.draw_active_brush_set_title(context, theme)
        self.draw_page_indicator(context, theme)


    def draw_active_brush_set_title(self, context: Context, theme: WheelTheme) -> None:
        title_layout = self._get_title_layout()
        if title_layout is None:
            return
        title, title_y, title_half_w = title_layout
        # Draw over the wheel.
        draw_text(
            title,
            0,
            title_y,
            size=14.0,
            color=theme.text_color,
            align="CENTER",
            shadow=True,
            valign='BOTTOM'
        )

        if self._hover_set_area or self._is_set_dragging:
            col = (*theme.text_color[:3], min(1.0, theme.text_color[3] + 0.1))
            y = title_y + 6.0
            gap = 12.0
            tip = 6.0
            lx = -title_half_w - gap
            rx = title_half_w + gap
            lines = [
                # Left tip "<"
                (lx + tip, y + tip), (lx, y),
                (lx + tip, y - tip), (lx, y),
                # Right tip ">"
                (rx - tip, y + tip), (rx, y),
                (rx - tip, y - tip), (rx, y),
            ]
            draw_lines(lines, col, line_width=1.8, strip=False)

    def draw_page_indicator(self, context: Context, theme: WheelTheme) -> None:
        layout = self._get_page_indicator_layout()
        if layout is None:
            return
        page_index, page_count, dot_radius, spacing, start_x, dot_y, _total_w = layout
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
