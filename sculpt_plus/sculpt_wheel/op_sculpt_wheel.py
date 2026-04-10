"""Sculpt Wheel modal operator."""

from __future__ import annotations

import math
from math import dist
from math import pi as PI
from typing import Set


def layout_sector_from_pointer(mx: float, my: float, cx: float, cy: float, n: int) -> int:
    """Wedge index 0..n-1 matching rendered pie sectors (top = 0, then clockwise)."""
    if n <= 0:
        return 0
    th = math.atan2(my - cy, mx - cx)
    step = 2.0 * math.pi / n
    shifted = (PI / 2.0 - th + step * 0.5 + 2.0 * PI) % (2.0 * PI)
    i = int(math.floor(shifted / step))
    return i % n

from bpy.types import Context, Event

from ..core import bl_types
from ..core.utils.op_return import OpReturn
from ..core.utils.mouse_utils import ModalMouse

from .data import SculptWheelData, SculptWheelStorage, get_wheel_storage
from .brush_library_cache import flatten_brushes_for_set, list_cached_brush_set_keys
from .gpu_utils import (
    compute_slot_radius,
    compute_slot_positions,
    compute_custom_button_layout_count,
    map_custom_layout_indices,
)
from .brush_assets import (
    clear_preview_cache,
    get_active_sculpt_brush,
    activate_wheel_brush_entry,
    wheel_brush_index_for_active,
    get_wheel_brush_preview_texture,
)
from .draw import draw_wheel
from .custom_buttons import (
    invoke_wheel_custom_button,
    clear_custom_button_texture_cache,
)
from .sculpt_paint_compat import get_sculpt_unified_paint_settings


# ---------------------------------------------------------------------------
# Brush size / strength (unified paint settings aware)
# ---------------------------------------------------------------------------


def _brush_size_get(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_size:
        return float(ups.size)
    return float(brush.size)


def _brush_size_set(context: Context, value: float) -> None:
    v = int(max(1, min(500, round(value))))
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return
    if ups is not None and ups.use_unified_size:
        ups.size = v
    else:
        brush.size = v


def _brush_strength_get(context: Context) -> float:
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return 1.0
    if ups is not None and ups.use_unified_strength:
        return float(ups.strength)
    return float(brush.strength)


def _brush_strength_set(context: Context, value: float) -> None:
    v = float(max(0.01, min(2.0, value)))
    ups = get_sculpt_unified_paint_settings(context)
    brush = context.tool_settings.sculpt.brush
    if brush is None:
        return
    if ups is not None and ups.use_unified_strength:
        ups.strength = v
    else:
        brush.strength = v


class SculptWheelOperator(bl_types.OperatorModal):
    """Open a radial brush wheel for quick sculpt brush selection."""

    bl_label = "Sculpt Wheel"
    bl_context_mode = 'SCULPT'

    cancel_on = {"ESC"}
    confirm_on: Set[str] = set()

    # -- Runtime state (not saved) --
    wheel_center_x: float = 0
    wheel_center_y: float = 0
    wheel_radius: float = 180
    slot_radius: float = 0
    slot_positions: list[tuple[float, float]] = []
    hover_index: int = -1
    icon_scale: float = 0.92
    show_names: bool = False

    brushes: list[dict] = []
    brush_set_keys: list[str] = []
    active_brush_set_index: int = 0
    brush_set_count: int = 0
    active_brush_slot_index: int = -1

    # Inner ring (custom buttons) — “tarta” pie layout
    custom_positions: list[tuple[float, float]] = []
    custom_radius: float = 0.0
    custom_layout_map: list[int] = []
    custom_layout_n: int = 0
    tarta_ring_outer_radius: float = 0.0
    tarta_inner_ratio: float = 0.5
    icon_ring_radius: float = 0.0
    hover_custom_index: int = -1
    hover_custom_layout_slot: int = -1
    hover_gesture_pad: bool = False

    gesture_pad_radius: float = 36.0

    _trigger_key: str = 'SPACE'
    _keep_open: bool = False
    _on_release_select: bool = False
    _can_close: bool = False
    _wheel_data: SculptWheelData | None = None
    _wheel_storage: SculptWheelStorage | None = None
    _gesture_invert: bool = False
    _gesture_preview: str = 'SIMPLE'

    # Gesture pad drag
    _gesture_state: str | None = None  # None | 'pending' | 'drag'
    _gesture_axis: str | None = None  # 'X' | 'Y'
    _gesture_origin: tuple[float, float] = (0.0, 0.0)
    _gesture_prev: tuple[float, float] = (0.0, 0.0)
    _saved_size: float = 0.0
    _saved_strength: float = 0.0

    # Custom button click
    _custom_press_idx: int = -1

    # ------------------------------------------------------------------
    # Poll
    # ------------------------------------------------------------------

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.area is None or context.area.type != 'VIEW_3D':
            return "Requires a 3D Viewport"
        if context.mode != 'SCULPT':
            return "Must be in Sculpt mode"
        return True

    # ------------------------------------------------------------------
    # Invoke
    # ------------------------------------------------------------------

    def invoke(self, context: Context, event: Event) -> Set[str]:
        prefs = self._get_prefs(context)
        self.wheel_radius = prefs.wheel_radius if prefs else 180
        self.icon_scale = prefs.wheel_icon_scale if prefs else 0.92
        self.show_names = prefs.wheel_show_names if prefs else False
        self._keep_open = prefs.wheel_keep_open if prefs else False
        self._on_release_select = prefs.wheel_on_release_select if prefs else False
        self._can_close = not self._keep_open
        self.gesture_pad_radius = float(prefs.wheel_gesture_pad_radius if prefs else 36)
        self._gesture_invert = prefs.wheel_gesture_invert if prefs else False
        self._gesture_preview = getattr(prefs, "wheel_gesture_preview", "SIMPLE") if prefs else "SIMPLE"

        self._trigger_key = self._detect_trigger_key(context, event)
        self.wheel_center_x = float(event.mouse_region_x)
        self.wheel_center_y = float(event.mouse_region_y)

        self._wheel_storage = get_wheel_storage(context)
        self._wheel_data = SculptWheelData.get(context)

        self._reset_interaction_state()
        self._rebuild_layout(context)
        self._cache_previews()

        if not context.window_manager.modal_handler_add(self):
            return OpReturn.CANCEL
        self._modal_begin(context, event)
        context.tool_settings.sculpt.show_brush = False
        return OpReturn.RUN

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw_2d(self, context: Context) -> None:
        draw_wheel(context, self)

    # ------------------------------------------------------------------
    # Modal hooks
    # ------------------------------------------------------------------

    def modal_begin(self, context: Context, event: Event, modal_mouse: ModalMouse, **kw) -> None:
        pass

    def modal_step(self, context: Context, event: Event) -> Set[str]:
        mx, my = float(event.mouse_region_x), float(event.mouse_region_y)

        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            if self._gesture_state is not None:
                self._restore_gesture_values(context)
                self._gesture_state = None
                self._gesture_axis = None
                self._gesture_origin = (0.0, 0.0)
                context.region.tag_redraw()
                return OpReturn.RUN
            return OpReturn.FINISH

        if self._gesture_state == 'drag' and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._gesture_state = None
            self._gesture_axis = None
            self._gesture_origin = (0.0, 0.0)
            context.region.tag_redraw()
            return OpReturn.RUN

        if self._gesture_state == 'pending' and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._gesture_state = None
            self._gesture_axis = None
            self._gesture_origin = (0.0, 0.0)
            context.region.tag_redraw()
            return OpReturn.RUN

        if self._custom_press_idx >= 0 and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self.hover_custom_index == self._custom_press_idx:
                btn = self._wheel_storage.custom_buttons[self._custom_press_idx]
                invoke_wheel_custom_button(context, btn)
            self._custom_press_idx = -1
            context.region.tag_redraw()
            return OpReturn.RUN

        if event.type == self._trigger_key and event.value == 'RELEASE':
            if self._on_release_select and self.hover_index >= 0:
                self._select_hovered(context)
            if self._can_close:
                return OpReturn.FINISH
            self._can_close = True
            return OpReturn.RUN

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if not self._is_inside_wheel(event):
                return OpReturn.FINISH

            if self.hover_gesture_pad and get_active_sculpt_brush(context) is not None:
                self._saved_size = _brush_size_get(context)
                self._saved_strength = _brush_strength_get(context)
                self._gesture_state = 'pending'
                self._gesture_origin = (self.wheel_center_x, self.wheel_center_y)
                self._gesture_prev = (mx, my)
                return OpReturn.RUN

            if self.hover_custom_index >= 0:
                self._custom_press_idx = self.hover_custom_index
                return OpReturn.RUN

            if self.hover_index >= 0:
                self._select_hovered(context)
                if self._can_close:
                    return OpReturn.FINISH
                return OpReturn.RUN

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            self._cycle_brush_set(context, 1 if event.type == 'WHEELUPMOUSE' else -1)
            context.region.tag_redraw()
            return OpReturn.RUN

        return OpReturn.RUN

    def modal_step_move(self, context: Context, event: Event, mouse: ModalMouse, **kw) -> bool:
        mx, my = float(event.mouse_region_x), float(event.mouse_region_y)
        self._update_hover(mx, my)
        self.active_brush_slot_index = wheel_brush_index_for_active(context, self.brushes)

        if self._gesture_state == 'pending':
            px, py = self._gesture_prev
            if abs(my - py) > 6.0:
                self._gesture_axis = 'Y'
                self._gesture_state = 'drag'
                self._gesture_prev = (mx, my)
            elif abs(mx - px) > 6.0:
                self._gesture_axis = 'X'
                self._gesture_state = 'drag'
                self._gesture_prev = (mx, my)
        elif self._gesture_state == 'drag' and self._gesture_axis:
            self._gesture_apply(context, event, mx, my)

        context.region.tag_redraw()
        return True

    def modal_end(self, context: Context, cancel: bool, mouse: ModalMouse) -> None:
        context.tool_settings.sculpt.show_brush = True
        clear_preview_cache()
        clear_custom_button_texture_cache()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_interaction_state(self) -> None:
        self._gesture_state = None
        self._gesture_axis = None
        self._gesture_origin = (0.0, 0.0)
        self._custom_press_idx = -1
        self.hover_custom_index = -1
        self.hover_custom_layout_slot = -1
        self.hover_gesture_pad = False

    def _restore_gesture_values(self, context: Context) -> None:
        _brush_size_set(context, self._saved_size)
        _brush_strength_set(context, self._saved_strength)

    def _gesture_apply(self, context: Context, event: Event, mx: float, my: float) -> None:
        axis = self._gesture_axis
        if axis is None:
            return
        px, py = self._gesture_prev
        diff = (my - py) if axis == 'Y' else (mx - px)
        if abs(diff) < 5.0:
            return
        is_vert = axis == 'Y'
        rate = 1.0 if is_vert else 0.01
        if event.shift:
            rate *= 0.2
        elif event.ctrl:
            rate *= 2.0
        invert = self._gesture_invert
        adjust_size = (is_vert and not invert) or (not is_vert and invert)
        if adjust_size:
            _brush_size_set(context, _brush_size_get(context) + rate * diff)
        else:
            _brush_strength_set(context, _brush_strength_get(context) + rate * diff)
        self._gesture_prev = (mx, my)

    @staticmethod
    def _is_inside_disc(mx: float, my: float, cx: float, cy: float, r: float) -> bool:
        return dist((mx, my), (cx, cy)) <= r

    @staticmethod
    def _get_prefs(context: Context):
        from ..prefs import SculptPlusPreferences
        bl_id = getattr(SculptPlusPreferences, 'bl_idname', None)
        if bl_id is None:
            return None
        addon = context.preferences.addons.get(bl_id)
        if addon is None:
            return None
        return addon.preferences

    @staticmethod
    def _detect_trigger_key(context: Context, event: Event) -> str:
        try:
            kc = context.window_manager.keyconfigs.user
            km = kc.keymaps.get('Sculpt')
            if km is not None:
                for kmi in km.keymap_items:
                    if kmi.idname == SculptWheelOperator.bl_idname:
                        return kmi.type
        except Exception:
            pass
        return event.type if event.value == 'PRESS' else 'SPACE'

    def _rebuild_layout(self, context: Context) -> None:
        cx, cy = self.wheel_center_x, self.wheel_center_y
        st = self._wheel_storage
        wd = self._wheel_data

        self.brush_set_keys = list_cached_brush_set_keys()
        self.brush_set_count = len(self.brush_set_keys)
        cur_set = wd.wheel_brush_set if wd is not None else "NONE"

        if not self.brush_set_keys:
            if wd is not None:
                wd.wheel_brush_set = "NONE"
            self.active_brush_set_index = 0
            self.brushes = []
        else:
            if cur_set == "NONE" or cur_set not in self.brush_set_keys:
                cur_set = self.brush_set_keys[0]
                if wd is not None:
                    wd.wheel_brush_set = cur_set
            try:
                self.active_brush_set_index = self.brush_set_keys.index(cur_set)
            except ValueError:
                self.active_brush_set_index = 0
            self.brushes = flatten_brushes_for_set(cur_set)

        self.active_brush_slot_index = wheel_brush_index_for_active(context, self.brushes)

        n_br = len(self.brushes)
        if n_br == 0:
            self.slot_positions = []
            self.slot_radius = 0
        else:
            count = max(7, n_br)
            ring_radius = self.wheel_radius * 0.74
            self.slot_radius = compute_slot_radius(ring_radius, count)
            self.slot_positions = compute_slot_positions(cx, cy, ring_radius, count)

        n_cb = len(st.custom_buttons) if st is not None else 0
        if n_cb > 0:
            layout_n = compute_custom_button_layout_count(n_cb)
            self.custom_layout_n = layout_n
            self.tarta_ring_outer_radius = self.wheel_radius * 0.48
            self.tarta_inner_ratio = min(
                0.92,
                self.gesture_pad_radius / max(self.tarta_ring_outer_radius, 1.0),
            )
            self.icon_ring_radius = self.tarta_ring_outer_radius * 0.72
            self.custom_radius = (
                compute_slot_radius(self.icon_ring_radius, layout_n) * 0.88
            )
            self.custom_positions = compute_slot_positions(
                cx, cy, self.icon_ring_radius, layout_n,
            )
            self.custom_layout_map = map_custom_layout_indices(layout_n, n_cb)
        else:
            self.custom_positions = []
            self.custom_radius = 0.0
            self.custom_layout_map = []
            self.custom_layout_n = 0
            self.tarta_ring_outer_radius = 0.0
            self.tarta_inner_ratio = 0.5
            self.icon_ring_radius = 0.0

    def _cache_previews(self) -> None:
        for entry in self.brushes:
            get_wheel_brush_preview_texture(entry)

    def _update_hover(self, mx: float, my: float) -> None:
        self.hover_index = -1
        self.hover_custom_index = -1
        self.hover_custom_layout_slot = -1
        self.hover_gesture_pad = False

        cx, cy = self.wheel_center_x, self.wheel_center_y

        for i, (sx, sy) in enumerate(self.slot_positions):
            if i >= len(self.brushes):
                break
            if dist((mx, my), (sx, sy)) <= self.slot_radius:
                self.hover_index = i
                return

        if self.custom_layout_n > 0 and len(self.custom_layout_map) > 0:
            r_pt = math.hypot(mx - cx, my - cy)
            if r_pt >= self.gesture_pad_radius - 1.0 and r_pt <= self.tarta_ring_outer_radius + 3.0:
                si = layout_sector_from_pointer(mx, my, cx, cy, self.custom_layout_n)
                if 0 <= si < len(self.custom_layout_map):
                    bid = self.custom_layout_map[si]
                    if bid >= 0:
                        self.hover_custom_index = bid
                        self.hover_custom_layout_slot = si
                        return
            for i, (sx, sy) in enumerate(self.custom_positions):
                if i >= len(self.custom_layout_map):
                    break
                bid = self.custom_layout_map[i]
                if bid < 0:
                    continue
                if dist((mx, my), (sx, sy)) <= self.custom_radius:
                    self.hover_custom_index = bid
                    self.hover_custom_layout_slot = i
                    return

        if dist((mx, my), (cx, cy)) <= self.gesture_pad_radius:
            self.hover_gesture_pad = True

    def _is_inside_wheel(self, event: Event) -> bool:
        return dist(
            (float(event.mouse_region_x), float(event.mouse_region_y)),
            (self.wheel_center_x, self.wheel_center_y),
        ) <= self.wheel_radius

    def _select_hovered(self, context: Context) -> None:
        if self.hover_index < 0 or self.hover_index >= len(self.brushes):
            return
        entry = self.brushes[self.hover_index]
        if activate_wheel_brush_entry(context, entry):
            self.active_brush_slot_index = self.hover_index

    def _cycle_brush_set(self, context: Context, direction: int) -> None:
        if self.brush_set_count <= 1 or self._wheel_data is None:
            return
        keys = self.brush_set_keys
        if not keys:
            return
        i = (self.active_brush_set_index + direction) % len(keys)
        self._wheel_data.wheel_brush_set = keys[i]
        clear_preview_cache()
        self._rebuild_layout(context)
        self._cache_previews()
