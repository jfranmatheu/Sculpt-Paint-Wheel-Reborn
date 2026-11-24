"""Brush-set ring: ``PickerBrushButton`` instances on a radial layout."""

from __future__ import annotations

from math import asin, pi
from typing import TYPE_CHECKING, Callable, Optional, Sequence, Tuple

from ..pg.pg_brush_set import BrushSetPreferences
from ..pg.pg_wheel_storage import SculptPaintWheelStorage

from ..gpu.utils import compute_slot_positions_in_single_ring

from .buttons.pk_brush import PickerBrushButton
from .widget import WidgetRing
from ..gpu.draw import draw_circle_fill, draw_ring, draw_text
from ..core.gpu.imm_2d import draw_lines
from ..gpu.ring_prims import capsule
from ..core.globals import GLOBALS
from ..utils.ups import get_tool_settings


USE_DEBUG = GLOBALS.IN_DEVELOPMENT  # (Rebuild logs: development builds only.)


if TYPE_CHECKING:
    from bpy.types import Context, Event
    from ..pg.pg_wheel_prefs import WheelPrefs, BrushSet, WheelTheme
    from ..pg.pg_wheel_storage import SculptPaintWheelStorage
    from ..pg.pg_brush_metadata import BrushMetadata


PAGE_PILL_HOVER = 0.07   # How much a hovered page pill lightens (dark palette) / darkens (light palette).
PAGE_PILL_ALPHA = 0.5    # Idle pill: a translucent, secondary chip...
PAGE_PILL_ALPHA_HOVER = 0.95  # ...solid while the mouse is over it.


def _layout_count(center_radius: float, slot_radius: float, slot_padding: float = 0.0) -> int:
    """How many slots fit around *center_radius* with tangential padding."""
    if center_radius <= 0.0 or slot_radius <= 0.0:
        return 0
    effective_radius = slot_radius + max(0.0, slot_padding) * 0.5
    if effective_radius >= center_radius:
        return 1
    angle = asin(max(0.0, min(1.0, effective_radius / center_radius)))
    if angle <= 0.0:
        return 0
    return max(1, int(pi / angle))


def ring_rows(radius_inner: float, radius_outer: float, prefs: BrushSetPreferences,
              rows: int = 1) -> list[tuple[float, float, int]]:
    """The rings of brush slots: (centre radius, slot radius, slot count) each, the outer one first.

    Two rings are laid out as radial pairs: every outer slot has an inner slot right under it, so both rings
    hold as many slots as the inner (shorter) one fits."""
    inner = min(radius_inner, radius_outer) + prefs.ring_padding
    outer = max(radius_inner, radius_outer) - prefs.ring_padding
    gap = prefs.row_gap if rows > 1 else 0.0
    row_h = max(0.0, (outer - inner - gap * (rows - 1)) / rows)
    slot_r = min(max(0.0, prefs.slot_size * 0.5), row_h * 0.5)
    centers = [outer - row_h * 0.5 - k * (row_h + gap) for k in range(rows)]
    n = _layout_count(centers[-1], slot_r, prefs.slot_padding)
    return [(c, slot_r, n) for c in centers]


def slots_per_page(prefs: BrushSetPreferences, wheel_radius: float, rows: int = 1) -> int:
    """Brush slots per page of a wheel of that (base) radius with that many rings, as the wheel lays them out."""
    outer = (wheel_radius + prefs.extra_radius(rows)) * 0.97
    return sum(n for _c, _r, n in ring_rows(outer - prefs.ring_thickness(rows), outer, prefs, rows))


def ring_count_for(prefs: BrushSetPreferences, wheel_radius: float, brush_count: int) -> int:
    """Rings of slots to show a set of ``brush_count`` brushes: two only when allowed and one isn't enough."""
    if prefs.allow_double_ring and brush_count > slots_per_page(prefs, wheel_radius, 1):
        return 2
    return 1


def _toward(c, target, k: float):
    return (c[0] + (target[0] - c[0]) * k, c[1] + (target[1] - c[1]) * k, c[2] + (target[2] - c[2]) * k, c[3])

class BrushSetRing(WidgetRing):
    """Places ``PickerBrushButton`` children on a ring using ``gpu.utils`` layout."""
    _wg_prefs = BrushSetPreferences

    _storage: SculptPaintWheelStorage
    _pickers: list[PickerBrushButton] = []
    _last_active_index: int = -1

    interactable = True
    use_modal = True

    def _row_positions(self, count: int) -> list[tuple[float, float]]:
        """Centres of the first *count* slots, spread evenly around the ring. On two rings the slots go in radial
        pairs (outer, then the inner one under it), the pairs spread evenly: a page that isn't full keeps the
        rings aligned and symmetric (an odd count leaves the last pair without its inner slot)."""
        cx, cy = self.center
        rows = self._rows
        if count <= 0 or not rows:
            return []
        if len(rows) == 1:
            return compute_slot_positions_in_single_ring(cx, cy, rows[0][0], min(count, rows[0][2]), 0.0)
        count = min(count, sum(n for _c, _r, n in rows))
        pairs = (count + len(rows) - 1) // len(rows)
        per_row = [compute_slot_positions_in_single_ring(cx, cy, c, pairs, 0.0) for c, _r, _n in rows]
        positions = []
        for j in range(pairs):
            for row in per_row:
                if len(positions) < count:
                    positions.append(row[j])
        return positions

    def init(self) -> None:
        super().init()
        self._pickers = []
        self.slot_count = 0
        self._slot_radius = 0.0
        self._rows = []
        self.row_count = 1  # Rings of slots: set by the wheel when it lays itself out (see ring_count_for).
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
        self._hover_page_part = None  # Page pill part under the mouse: -1 back arrow, 0 middle, 1 forward arrow.
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

        self._rows = ring_rows(self.radius_inner, self.radius_outer, self.wg_prefs, self.row_count)
        count = sum(n for _c, _r, n in self._rows)
        slot_r = self._rows[0][1] if self._rows else 0.0
        self._slot_radius = slot_r
        self.slot_count = count
        if count == 0:
            if USE_DEBUG:
                print("No pickers to sync")
            return

        # Compute slot positions and radius.
        cx, cy = self.center
        positions = self._row_positions(count)

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
        positions = self._row_positions(visible_count)
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
        # The slots are new: the active brush's slot is highlighted again (it would otherwise be only after a click,
        # and lost when the wheel re-lays out, e.g. showing the color picker for a painting brush).
        ts = get_tool_settings(context)
        ref = getattr(ts, "brush_asset_reference", None) if ts is not None else None
        active_key = (ref.asset_library_type, ref.asset_library_identifier, ref.relative_asset_identifier) if ref else None
        # Set brush metadata for each picker.
        for i, pb in enumerate(self._pickers):
            if i < len(brushes_metadata):
                if USE_DEBUG:
                    print(f"Setting brush metadata for picker {i}: {brushes_metadata[i].name}")
                pb.enabled = True
                meta = brushes_metadata[i]
                pb.set_brush_metadata(meta, show_label=False)
                pb.active = active_key == (meta.asset_library_type, meta.asset_library_identifier,
                                           meta.relative_asset_identifier)
            else:
                # If no brush metadata, clear the picker data.
                if USE_DEBUG:
                    print(f"Clearing brush metadata for picker {i}")
                pb.clear_brush_metadata()
                pb.enabled = False

        if USE_DEBUG:
            print(f"Rebuilt {len(self._pickers)} pickers")
            
        context.region.tag_redraw()

    def _get_page_indicator_layout(self) -> tuple[int, int, float, float, float, float] | None:
        """Page pill under the ring (only with more than one page): (page_index, page_count, x, y, w, h),
        (x, y) its bottom-left corner in wheel-local units. A small gap separates it from the wheel's edge."""
        active_brush_set: BrushSet = self.active_brush_set
        if not active_brush_set:
            return None
        if self.slot_count <= 0:
            return None
        page_count = (len(active_brush_set.items) + self.slot_count - 1) // self.slot_count
        if page_count <= 1:
            return None
        page_index = max(0, min(active_brush_set.page_index, page_count - 1))
        r = self.wheel.radius
        h = max(26.0, r * 0.14)
        w = max(120.0, r * 0.64)
        top = -r - h * 0.3
        return (page_index, page_count, -w * 0.5, top - h, w, h)

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

    def _step_page(self, context: Context, delta: int, wrap: bool = False) -> bool:
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
        if wrap:  # (Back from the first page is the last one, forward from the last is the first.)
            active_brush_set.page_index = (active_brush_set.page_index + delta) % (max_page_index + 1)
        else:
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
        _page_index, _page_count, x, y, w, h = layout
        if not (x <= p.x <= x + w and y <= p.y <= y + h):
            self._hover_page_part = None
            return False
        u = (p.x - x) / max(w, 1e-6)
        self._hover_page_part = -1 if u < 0.32 else 1 if u > 0.68 else 0
        self._hover_page_area = True
        return True

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
        if self._hover_page_area and self._hover_page_part is not None:
            self._step_page(context, self._hover_page_part or 1, wrap=True)
            return True
        return False

    def end_drag(self, context: Context) -> None:
        self._is_page_dragging = False
        self._is_set_dragging = False

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
        """A pill in the wheel's colors: back arrow, "n / N", forward arrow; the part under the mouse lit."""
        layout = self._get_page_indicator_layout()
        if layout is None:
            return
        page_index, page_count, x, y, w, h = layout
        light = getattr(theme, 'is_light', False)
        part = self._hover_page_part if self._hover_page_area else None
        base = tuple(theme.base_color)
        hovered = part is not None
        fill = _toward(base, (0.0, 0.0, 0.0, 1.0) if light else (1.0, 1.0, 1.0, 1.0), PAGE_PILL_HOVER) if hovered else base
        border = tuple(theme.base_outline_color)
        a = PAGE_PILL_ALPHA_HOVER if hovered else PAGE_PILL_ALPHA
        # Secondary until hovered: translucent fill and outline, muted text and arrows.
        capsule(x, y, w, h, fill=(fill[0], fill[1], fill[2], a),
                border=(border[0], border[1], border[2], a if hovered else a * 0.8), border_w=1.0)

        text_col = tuple(theme.text_color)
        muted = (text_col[0], text_col[1], text_col[2], text_col[3] * (0.75 if hovered else 0.6))
        accent = tuple(theme.tarta_pressed_color)
        draw_text(f"{page_index + 1} / {page_count}", 0.0, y + h * 0.5, size=max(10.0, h * 0.48),
                  color=text_col if part == 0 else muted, align="CENTER", valign='MIDDLE', shadow=False)

        k = h * 0.2                      # Caret half-height.
        inset = h * 0.55                 # Carets at the pill's ends, clear of the numbers.
        cy = y + h * 0.5
        for step, cx, sign in ((-1, x + inset, -1.0), (1, x + w - inset, 1.0)):
            lit = part == step
            col = (accent[0], accent[1], accent[2], 1.0) if lit else muted
            tip = cx + sign * k * 0.5
            back = cx - sign * k * 0.5
            draw_lines([(back, cy + k), (tip, cy), (tip, cy), (back, cy - k)], col,
                       line_width=2.2 if lit else 1.8, strip=False)
