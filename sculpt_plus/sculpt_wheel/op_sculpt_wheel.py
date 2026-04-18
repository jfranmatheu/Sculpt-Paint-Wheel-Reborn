"""Sculpt Wheel modal operator."""

from __future__ import annotations

import math
from math import dist
from math import pi as PI
from typing import Set


def layout_sector_from_pointer(mx: float, my: float, cx: float, cy: float, n: int) -> int:
    """Wedge index 0..n-1 matching the pie shader (first slice starts at 180 deg, then CW)."""
    if n <= 0:
        return 0
    angle = math.atan2(my - cy, mx - cx)
    step = 2.0 * math.pi / n
    shifted = (PI - angle + 2.0 * PI) % (2.0 * PI)
    i = int(math.floor(shifted / step))
    return i % n

from bpy.types import Context, Event

from ..core import bl_types
from ..core.utils.op_return import OpReturn
from ..core.utils.mouse_utils import ModalMouse

from ..src.brush_management import (
    BrushData,
    activate_brush,
    active_brush_index_in_list,
    get_brush_preview_texture,
    get_brushes_for_blend,
    get_page_name,
    page_count_for_blend,
    clear_texture_cache,
)

from .data import (
    SculptWheelData,
    SculptWheelStorage,
    get_wheel_storage,
    resolve_custom_buttons_for_blend,
    parse_blend_key,
)
from .brush_lib_config import (
    ensure_brush_libs_loaded,
    get_wheel_base_color,
    get_active_page,
    set_active_page,
    list_ordered_blend_keys,
)
from .colpk_wheel import (
    active_sculpt_brush_has_color,
    colpk_pick_channel,
    colpk_update_from_mouse,
    get_sculpt_brush_rgb,
    set_sculpt_brush_rgb,
)
from .gpu_utils import (
    compute_slot_radius,
    compute_slot_positions,
    compute_custom_button_layout_count,
    map_custom_layout_indices,
)
from .custom_buttons import (
    invoke_wheel_custom_button,
    clear_custom_button_texture_cache,
)
from .draw import COL_BASE, draw_wheel


class SculptWheelOperator(bl_types.OperatorModal):
    """Open a radial brush wheel for quick sculpt brush selection."""

    bl_label = "Sculpt Wheel"
    bl_context_mode = 'SCULPT'

    cancel_on = {"ESC"}
    confirm_on: Set[str] = set()

    wheel_center_x: float = 0
    wheel_center_y: float = 0
    wheel_radius: float = 180
    slot_radius: float = 0
    slot_positions: list[tuple[float, float]] = []
    hover_index: int = -1
    icon_scale: float = 0.92
    show_names: bool = False

    brushes: list[BrushData] = []
    blend_keys: list[str] = []
    active_blend_index: int = 0
    blend_count: int = 0
    active_brush_slot_index: int = -1
    active_page: int = 0
    total_pages: int = 1
    active_page_title: str = ""

    custom_positions: list[tuple[float, float]] = []
    custom_radius: float = 0.0
    custom_layout_map: list[int] = []
    custom_layout_n: int = 0
    tarta_ring_outer_radius: float = 0.0
    tarta_inner_ratio: float = 0.5
    icon_ring_radius: float = 0.0
    hover_custom_index: int = -1
    hover_custom_layout_slot: int = -1

    wheel_base_color: tuple[float, float, float, float] = (
        COL_BASE[0], COL_BASE[1], COL_BASE[2], COL_BASE[3],
    )

    _trigger_key: str = 'SPACE'
    _keep_open: bool = False
    _on_release_select: bool = False
    _can_close: bool = False
    _wheel_data: SculptWheelData | None = None
    _wheel_storage: SculptWheelStorage | None = None
    _custom_press_idx: int = -1

    show_color_picker: bool = False
    colpk_hue_inner_r: float = 0.0
    colpk_hue_outer_r: float = 0.0
    colpk_sv_inner_r: float = 0.0
    colpk_sv_outer_r: float = 0.0
    _colpk_channel: str | None = None
    _colpk_prev_rgb: tuple[float, float, float] | None = None

    # Current blend identification for brush_management queries.
    _cur_library_id: str = ""
    _cur_blend_id: str = ""

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
        if not ensure_brush_libs_loaded(context):
            self.report(
                {"WARNING"},
                "Could not load brush libraries (Sidebar → Sculpt Wheel → reload libraries)",
            )
            return OpReturn.CANCEL

        prefs = self._get_prefs(context)
        self.wheel_radius = prefs.wheel_radius if prefs else 180
        self.icon_scale = prefs.wheel_icon_scale if prefs else 0.92
        self.show_names = prefs.wheel_show_names if prefs else False
        self._keep_open = prefs.wheel_keep_open if prefs else False
        self._on_release_select = prefs.wheel_on_release_select if prefs else False
        self._can_close = not self._keep_open

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
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            return OpReturn.FINISH

        if self._custom_press_idx >= 0 and event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            coll = getattr(self, "_active_custom_buttons", None)
            if (
                coll is not None
                and self.hover_custom_index == self._custom_press_idx
                and 0 <= self._custom_press_idx < len(coll)
            ):
                btn = coll[self._custom_press_idx]
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

            mx, my = float(event.mouse_region_x), float(event.mouse_region_y)
            cx, cy = self.wheel_center_x, self.wheel_center_y

            for i, (sx, sy) in enumerate(self.slot_positions):
                if i >= len(self.brushes):
                    break
                if dist((mx, my), (sx, sy)) <= self.slot_radius:
                    self._select_brush_at_index(context, i)
                    if self._can_close:
                        return OpReturn.FINISH
                    return OpReturn.RUN

            ch = colpk_pick_channel(mx, my, cx, cy, self)
            if ch is not None:
                self._colpk_prev_rgb = get_sculpt_brush_rgb(context)
                self._colpk_channel = ch
                colpk_update_from_mouse(context, self, ch, mx, my)
                return self._colpk_submodal

            if self.hover_custom_index >= 0:
                self._custom_press_idx = self.hover_custom_index
                return OpReturn.RUN

            if self.hover_index >= 0:
                self._select_hovered(context)
                if self._can_close:
                    return OpReturn.FINISH
                return OpReturn.RUN

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            direction = 1 if event.type == 'WHEELUPMOUSE' else -1
            # Shift+wheel: switch brush library blend; otherwise wheel changes page when multi-page.
            if event.shift and self.blend_count > 1:
                self._cycle_blend(context, direction)
            elif self.total_pages > 1:
                self._cycle_page(context, direction)
            elif self.blend_count > 1:
                self._cycle_blend(context, direction)
            context.region.tag_redraw()
            return OpReturn.RUN

        return OpReturn.RUN

    def modal_step_move(self, context: Context, event: Event, mouse: ModalMouse, **kw) -> bool:
        mx, my = float(event.mouse_region_x), float(event.mouse_region_y)
        self._update_hover(mx, my)
        self.active_brush_slot_index = active_brush_index_in_list(context, self.brushes)

        context.region.tag_redraw()
        return True

    def modal_end(self, context: Context, cancel: bool, mouse: ModalMouse) -> None:
        context.tool_settings.sculpt.show_brush = True
        clear_texture_cache()
        clear_custom_button_texture_cache()

    def _colpk_submodal(self, context: Context, event: Event) -> bool:
        ch = self._colpk_channel
        if ch is None:
            return False

        if event.type in ('MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'):
            mx, my = float(event.mouse_region_x), float(event.mouse_region_y)
            colpk_update_from_mouse(context, self, ch, mx, my)
            context.region.tag_redraw()
            return True

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._colpk_channel = None
            self._colpk_prev_rgb = None
            context.region.tag_redraw()
            return False

        if event.type in ('RIGHTMOUSE', 'ESC') and event.value == 'PRESS':
            if self._colpk_prev_rgb is not None:
                set_sculpt_brush_rgb(context, self._colpk_prev_rgb)
            self._colpk_channel = None
            self._colpk_prev_rgb = None
            context.region.tag_redraw()
            return False
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_interaction_state(self) -> None:
        self._custom_press_idx = -1
        self.hover_custom_index = -1
        self.hover_custom_layout_slot = -1
        self._colpk_channel = None
        self._colpk_prev_rgb = None

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

        self.blend_keys = list_ordered_blend_keys(context)
        self.blend_count = len(self.blend_keys)
        cur_blend = wd.wheel_active_blend if wd is not None else "NONE"

        if not self.blend_keys:
            if wd is not None:
                wd.wheel_active_blend = "NONE"
            self.active_blend_index = 0
            self.brushes = []
            self._cur_library_id = ""
            self._cur_blend_id = ""
            self.active_page = 0
            self.total_pages = 1
            self.active_page_title = ""
            self.wheel_base_color = (COL_BASE[0], COL_BASE[1], COL_BASE[2], COL_BASE[3])
            self._active_custom_buttons = None
        else:
            if cur_blend == "NONE" or cur_blend not in self.blend_keys:
                cur_blend = self.blend_keys[0]
                if wd is not None:
                    wd.wheel_active_blend = cur_blend
            try:
                self.active_blend_index = self.blend_keys.index(cur_blend)
            except ValueError:
                self.active_blend_index = 0

            lid, bid = parse_blend_key(cur_blend)
            self._cur_library_id = lid
            self._cur_blend_id = bid
            self.active_page = get_active_page(context, cur_blend)
            self.total_pages = max(1, page_count_for_blend(lid, bid))
            if self.active_page >= self.total_pages:
                self.active_page = 0
                set_active_page(context, cur_blend, 0)

            self.brushes = get_brushes_for_blend(lid, bid, self.active_page)
            self.active_page_title = get_page_name(lid, bid, self.active_page)
            self.wheel_base_color = get_wheel_base_color(context, cur_blend)
            self._active_custom_buttons = resolve_custom_buttons_for_blend(context, cur_blend)

        self.active_brush_slot_index = active_brush_index_in_list(context, self.brushes)

        n_br = len(self.brushes)
        if n_br == 0:
            self.slot_positions = []
            self.slot_radius = 0
        else:
            count = max(7, n_br)
            ring_radius = self.wheel_radius * 0.74
            self.slot_radius = compute_slot_radius(ring_radius, count)
            self.slot_positions = compute_slot_positions(cx, cy, ring_radius, count)

        cb_coll = getattr(self, "_active_custom_buttons", None)
        n_cb = len(cb_coll) if cb_coll is not None else 0
        if n_cb > 0:
            layout_n = compute_custom_button_layout_count(n_cb)
            self.custom_layout_n = layout_n
            self.tarta_ring_outer_radius = self.wheel_radius * 0.48
            self.tarta_inner_ratio = min(
                0.92,
                42.0 / max(self.tarta_ring_outer_radius, 1.0),
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

        self._refresh_show_color_picker(context)

    def _cache_previews(self) -> None:
        for brush in self.brushes:
            if brush.preview.path:
                get_brush_preview_texture(brush.preview.path, brush.name)

    def _update_hover(self, mx: float, my: float) -> None:
        self.hover_index = -1
        self.hover_custom_index = -1
        self.hover_custom_layout_slot = -1

        cx, cy = self.wheel_center_x, self.wheel_center_y
        inner_r = (
            self.tarta_ring_outer_radius
            if self.custom_layout_n > 0 and self.tarta_ring_outer_radius > 1.0
            else min(42.0, self.wheel_radius * 0.24)
        )

        for i, (sx, sy) in enumerate(self.slot_positions):
            if i >= len(self.brushes):
                break
            if dist((mx, my), (sx, sy)) <= self.slot_radius:
                self.hover_index = i
                return

        if self.custom_layout_n > 0 and len(self.custom_layout_map) > 0:
            r_pt = math.hypot(mx - cx, my - cy)
            if r_pt >= inner_r - 1.0 and r_pt <= self.tarta_ring_outer_radius + 3.0:
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

    def _is_inside_wheel(self, event: Event) -> bool:
        return dist(
            (float(event.mouse_region_x), float(event.mouse_region_y)),
            (self.wheel_center_x, self.wheel_center_y),
        ) <= self.wheel_radius

    def _refresh_show_color_picker(self, context: Context) -> None:
        """Show HSV rings only when the active sculpt brush supports color (RNA)."""
        self.show_color_picker = bool(active_sculpt_brush_has_color(context))
        if self.show_color_picker:
            base_outer = (
                self.tarta_ring_outer_radius
                if self.tarta_ring_outer_radius > 1.0
                else max(28.0, self.wheel_radius * 0.30)
            )
            gap = max(5.0, self.wheel_radius * 0.028)
            hue_thick = max(14.0, self.wheel_radius * 0.062)
            self.colpk_hue_inner_r = base_outer + gap
            self.colpk_hue_outer_r = self.colpk_hue_inner_r + hue_thick
            gap2 = max(4.0, self.wheel_radius * 0.022)
            sv_thick = max(16.0, self.wheel_radius * 0.07)
            self.colpk_sv_inner_r = self.colpk_hue_outer_r + gap2
            self.colpk_sv_outer_r = self.colpk_sv_inner_r + sv_thick
        else:
            self.colpk_hue_inner_r = 0.0
            self.colpk_hue_outer_r = 0.0
            self.colpk_sv_inner_r = 0.0
            self.colpk_sv_outer_r = 0.0

    def _select_hovered(self, context: Context) -> None:
        if self.hover_index < 0 or self.hover_index >= len(self.brushes):
            return
        brush = self.brushes[self.hover_index]
        if activate_brush(context, brush):
            self.active_brush_slot_index = self.hover_index
            self._refresh_show_color_picker(context)

    def _select_brush_at_index(self, context: Context, index: int) -> None:
        if index < 0 or index >= len(self.brushes):
            return
        brush = self.brushes[index]
        if activate_brush(context, brush):
            self.active_brush_slot_index = index
            self._refresh_show_color_picker(context)

    def _cycle_blend(self, context: Context, direction: int) -> None:
        if self.blend_count <= 1 or self._wheel_data is None:
            return
        keys = self.blend_keys
        if not keys:
            return
        i = (self.active_blend_index + direction) % len(keys)
        self._wheel_data.wheel_active_blend = keys[i]
        clear_texture_cache()
        self._rebuild_layout(context)
        self._cache_previews()

    def _cycle_page(self, context: Context, direction: int) -> None:
        if self.total_pages <= 1 or self._wheel_data is None:
            return
        cur = (self._wheel_data.wheel_active_blend or "").strip()
        if not cur or cur == "NONE":
            return
        new_page = (self.active_page + direction) % self.total_pages
        set_active_page(context, cur, new_page)
        clear_texture_cache()
        self._rebuild_layout(context)
        self._cache_previews()
