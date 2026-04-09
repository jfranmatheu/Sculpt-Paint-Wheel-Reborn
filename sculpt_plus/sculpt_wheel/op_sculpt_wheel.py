"""Sculpt Wheel modal operator."""

from __future__ import annotations

from math import cos, dist, sin
from math import pi as PI
from typing import Set

from bpy.types import Context, Event

from ..core import bl_types
from ..core.utils.op_return import OpReturn
from ..core.utils.mouse_utils import ModalMouse

from .data import SculptWheelData, WheelToolset
from .gpu_utils import (
    compute_slot_radius,
    compute_slot_positions,
    compute_custom_button_layout_count,
    map_custom_layout_indices,
)
from .brush_assets import (
    clear_preview_cache,
    get_active_sculpt_brush,
    get_brush_asset_ref,
    find_brush_for_slot,
    get_brush_preview_texture,
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

    active_toolset: WheelToolset | None = None
    active_toolset_idx: int = 0
    toolset_count: int = 0

    # Inner ring (custom buttons)
    custom_positions: list[tuple[float, float]] = []
    custom_radius: float = 0.0
    custom_layout_map: list[int] = []
    hover_custom_index: int = -1
    hover_gesture_pad: bool = False

    gesture_pad_radius: float = 36.0
    wheel_ui_mode: str = 'PICKER'  # 'PICKER' | 'EDIT'

    edit_toggle_x: float = 0.0
    edit_toggle_y: float = 0.0
    edit_toggle_radius: float = 16.0

    _trigger_key: str = 'SPACE'
    _keep_open: bool = False
    _on_release_select: bool = False
    _can_close: bool = False
    _wheel_data: SculptWheelData | None = None
    _gesture_invert: bool = False
    _gesture_preview: str = 'SIMPLE'

    # Gesture pad drag
    _gesture_state: str | None = None  # None | 'pending' | 'drag'
    _gesture_axis: str | None = None  # 'X' | 'Y'
    _gesture_prev: tuple[float, float] = (0.0, 0.0)
    _saved_size: float = 0.0
    _saved_strength: float = 0.0

    # Custom button click
    _custom_press_idx: int = -1

    # Edit mode slot drag
    _slot_drag_from: int = -1

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

        self._wheel_data = SculptWheelData.get(context)
        self._wheel_data.ensure_default_toolset(context)

        self._sync_active_brush(context)
        self.wheel_ui_mode = 'PICKER'
        self._reset_interaction_state()
        self._rebuild_layout()

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
                context.region.tag_redraw()
                return OpReturn.RUN
            return OpReturn.FINISH

        if self._gesture_state == 'drag' and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._gesture_state = None
            self._gesture_axis = None
            context.region.tag_redraw()
            return OpReturn.RUN

        if self._gesture_state == 'pending' and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._gesture_state = None
            self._gesture_axis = None
            context.region.tag_redraw()
            return OpReturn.RUN

        if self._slot_drag_from >= 0 and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._finish_slot_drag(context, mx, my)
            context.region.tag_redraw()
            return OpReturn.RUN

        if self._custom_press_idx >= 0 and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self.hover_custom_index == self._custom_press_idx:
                btn = self._wheel_data.custom_buttons[self._custom_press_idx]
                invoke_wheel_custom_button(context, btn)
            self._custom_press_idx = -1
            context.region.tag_redraw()
            return OpReturn.RUN

        if event.type == self._trigger_key and event.value == 'RELEASE':
            if self._on_release_select and self.hover_index >= 0 and self.wheel_ui_mode == 'PICKER':
                self._select_hovered(context)
            if self._can_close:
                return OpReturn.FINISH
            self._can_close = True
            return OpReturn.RUN

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._hit_edit_toggle(mx, my):
                self.wheel_ui_mode = 'EDIT' if self.wheel_ui_mode == 'PICKER' else 'PICKER'
                context.region.tag_redraw()
                return OpReturn.RUN

            if not self._is_inside_wheel(event):
                return OpReturn.FINISH

            if self.wheel_ui_mode == 'EDIT':
                if self.hover_index >= 0:
                    self._slot_drag_from = self.hover_index
                    return OpReturn.RUN
                return OpReturn.RUN

            # PICKER
            if self.hover_gesture_pad and get_active_sculpt_brush(context) is not None:
                self._saved_size = _brush_size_get(context)
                self._saved_strength = _brush_strength_get(context)
                self._gesture_state = 'pending'
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
            self._cycle_toolset(context, 1 if event.type == 'WHEELUPMOUSE' else -1)
            context.region.tag_redraw()
            return OpReturn.RUN

        return OpReturn.RUN

    def modal_step_move(self, context: Context, event: Event, mouse: ModalMouse, **kw) -> bool:
        mx, my = float(event.mouse_region_x), float(event.mouse_region_y)
        self._update_hover(mx, my)

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
        self._custom_press_idx = -1
        self._slot_drag_from = -1
        self.hover_custom_index = -1
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

    def _finish_slot_drag(self, context: Context, mx: float, my: float) -> None:
        a = self._slot_drag_from
        self._slot_drag_from = -1
        if self.active_toolset is None or a < 0:
            return
        if not self._is_inside_disc(mx, my, self.wheel_center_x, self.wheel_center_y, self.wheel_radius):
            self.active_toolset.remove_slot(a)
            self._rebuild_layout()
            return
        b = self.hover_index
        if b >= 0 and b != a:
            self.active_toolset.swap_slots(a, b)
            self._rebuild_layout()

    def _hit_edit_toggle(self, mx: float, my: float) -> bool:
        return dist((mx, my), (self.edit_toggle_x, self.edit_toggle_y)) <= self.edit_toggle_radius

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

    def _rebuild_layout(self) -> None:
        cx, cy = self.wheel_center_x, self.wheel_center_y
        ts = self._wheel_data.active_toolset
        self.active_toolset = ts
        self.active_toolset_idx = self._wheel_data.active_toolset_index
        self.toolset_count = len(self._wheel_data.toolsets)

        rad = 16.0 * self.wheel_radius / 180.0
        self.edit_toggle_radius = rad
        left_x = cx - self.wheel_radius - rad * 2.0 - 10.0
        left_y = cy
        ang = PI / 4.0
        dx, dy = left_x - cx, left_y - cy
        self.edit_toggle_x = cx + dx * cos(ang) - dy * sin(ang)
        self.edit_toggle_y = cy + dx * sin(ang) + dy * cos(ang)

        if ts is None or len(ts.slots) == 0:
            self.slot_positions = []
            self.slot_radius = 0
        else:
            count = max(7, len(ts.slots))
            ring_radius = self.wheel_radius * 0.6
            self.slot_radius = compute_slot_radius(ring_radius, count)
            self.slot_positions = compute_slot_positions(cx, cy, ring_radius, count)

        n_cb = len(self._wheel_data.custom_buttons)
        if n_cb > 0:
            layout_n = compute_custom_button_layout_count(n_cb)
            inner_r = self.wheel_radius * 0.38
            self.custom_radius = compute_slot_radius(inner_r, layout_n) * 0.88
            self.custom_positions = compute_slot_positions(cx, cy, inner_r, layout_n)
            self.custom_layout_map = map_custom_layout_indices(layout_n, n_cb)
        else:
            self.custom_positions = []
            self.custom_radius = 0.0
            self.custom_layout_map = []

    def _cache_previews(self) -> None:
        if self.active_toolset is None:
            return
        for slot in self.active_toolset.slots:
            brush = find_brush_for_slot(slot)
            if brush is not None:
                get_brush_preview_texture(brush)

    def _sync_active_brush(self, context: Context) -> None:
        brush = get_active_sculpt_brush(context)
        if brush is None or self.active_toolset is None:
            return
        asset_ref = get_brush_asset_ref(context)
        for i, slot in enumerate(self.active_toolset.slots):
            if slot.display_name == brush.name:
                self.active_toolset.active_slot_index = i
                if asset_ref is not None and slot.asset_library_type == 'LOCAL':
                    slot.set_from_brush(brush, asset_ref)
                return

    def _update_hover(self, mx: float, my: float) -> None:
        self.hover_index = -1
        self.hover_custom_index = -1
        self.hover_gesture_pad = False

        cx, cy = self.wheel_center_x, self.wheel_center_y

        for i, (sx, sy) in enumerate(self.slot_positions):
            if self.active_toolset is not None and i >= len(self.active_toolset.slots):
                break
            if dist((mx, my), (sx, sy)) <= self.slot_radius:
                self.hover_index = i
                return

        for i, (sx, sy) in enumerate(self.custom_positions):
            if i >= len(self.custom_layout_map):
                break
            bid = self.custom_layout_map[i]
            if bid < 0:
                continue
            if dist((mx, my), (sx, sy)) <= self.custom_radius:
                self.hover_custom_index = bid
                return

        if dist((mx, my), (cx, cy)) <= self.gesture_pad_radius:
            self.hover_gesture_pad = True

    def _is_inside_wheel(self, event: Event) -> bool:
        return dist(
            (float(event.mouse_region_x), float(event.mouse_region_y)),
            (self.wheel_center_x, self.wheel_center_y),
        ) <= self.wheel_radius

    def _select_hovered(self, context: Context) -> None:
        if self.active_toolset is None or self.hover_index < 0:
            return
        self.active_toolset.select_slot(context, self.hover_index)

    def _cycle_toolset(self, context: Context, direction: int) -> None:
        if self.toolset_count <= 1:
            return
        idx = (self._wheel_data.active_toolset_index + direction) % self.toolset_count
        self._wheel_data.active_toolset_index = idx
        self._sync_active_brush(context)
        self._rebuild_layout()
        self._cache_previews()
