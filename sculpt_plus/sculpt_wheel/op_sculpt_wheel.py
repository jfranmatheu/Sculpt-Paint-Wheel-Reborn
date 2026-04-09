"""Sculpt Wheel modal operator."""

from __future__ import annotations

from math import dist
from typing import Set

from bpy.types import Context, Event

from ..core import bl_types
from ..core.utils.op_return import OpReturn
from ..core.utils.mouse_utils import ModalMouse

from .data import SculptWheelData, WheelToolset
from .gpu_utils import compute_slot_radius, compute_slot_positions
from .brush_assets import (
    clear_preview_cache,
    get_active_sculpt_brush,
    get_brush_asset_ref,
    find_brush_for_slot,
    get_brush_preview_texture,
)
from .draw import draw_wheel


class SculptWheelOperator(bl_types.OperatorModal):
    """Open a radial brush wheel for quick sculpt brush selection."""

    bl_label = "Sculpt Wheel"
    bl_context_mode = 'SCULPT'

    cancel_on = {"ESC", "RIGHTMOUSE"}
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

    _trigger_key: str = 'SPACE'
    _keep_open: bool = False
    _on_release_select: bool = False
    _can_close: bool = False
    _wheel_data: SculptWheelData | None = None

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

        self._trigger_key = self._detect_trigger_key(context, event)
        self.wheel_center_x = event.mouse_region_x
        self.wheel_center_y = event.mouse_region_y

        self._wheel_data = SculptWheelData.get(context)
        self._wheel_data.ensure_default_toolset(context)

        self._sync_active_brush(context)
        self._rebuild_layout()

        # Pre-cache preview textures.
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
        draw_wheel(self)

    # ------------------------------------------------------------------
    # Modal hooks
    # ------------------------------------------------------------------

    def modal_begin(self, context: Context, event: Event, modal_mouse: ModalMouse, **kw) -> None:
        pass

    def modal_step(self, context: Context, event: Event) -> Set[str]:
        # Key release of the trigger key.
        if event.type == self._trigger_key and event.value == 'RELEASE':
            if self._on_release_select and self.hover_index >= 0:
                self._select_hovered(context)
            if self._can_close:
                return OpReturn.FINISH
            self._can_close = True
            return OpReturn.RUN

        # LMB click to select.
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self.hover_index >= 0:
                self._select_hovered(context)
                if self._can_close:
                    return OpReturn.FINISH
                return OpReturn.RUN
            if not self._is_inside_wheel(event):
                return OpReturn.FINISH

        # Scroll to switch toolsets.
        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            self._cycle_toolset(context, 1 if event.type == 'WHEELUPMOUSE' else -1)
            context.region.tag_redraw()
            return OpReturn.RUN

        return OpReturn.RUN

    def modal_step_move(self, context: Context, event: Event, mouse: ModalMouse, **kw) -> bool:
        self._update_hover(mouse.current.x, mouse.current.y)
        context.region.tag_redraw()
        return True

    def modal_end(self, context: Context, cancel: bool, mouse: ModalMouse) -> None:
        context.tool_settings.sculpt.show_brush = True
        clear_preview_cache()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        """Read the actual keymap item that triggered us so we can close on its release."""
        try:
            kc = context.window_manager.keyconfigs.user
            km = kc.keymaps.get('Sculpt')
            if km is None:
                km = kc.keymaps.get('Sculpt', None)
            if km is not None:
                for kmi in km.keymap_items:
                    if kmi.idname == SculptWheelOperator.bl_idname:
                        return kmi.type
        except Exception:
            pass
        return event.type if event.value == 'PRESS' else 'SPACE'

    def _rebuild_layout(self) -> None:
        ts = self._wheel_data.active_toolset
        self.active_toolset = ts
        self.active_toolset_idx = self._wheel_data.active_toolset_index
        self.toolset_count = len(self._wheel_data.toolsets)
        if ts is None or len(ts.slots) == 0:
            self.slot_positions = []
            self.slot_radius = 0
            return
        count = max(7, len(ts.slots))
        ring_radius = self.wheel_radius * 0.6
        self.slot_radius = compute_slot_radius(ring_radius, count)
        self.slot_positions = compute_slot_positions(
            self.wheel_center_x, self.wheel_center_y, ring_radius, count,
        )

    def _cache_previews(self) -> None:
        if self.active_toolset is None:
            return
        for slot in self.active_toolset.slots:
            brush = find_brush_for_slot(slot)
            if brush is not None:
                get_brush_preview_texture(brush)

    def _sync_active_brush(self, context: Context) -> None:
        """Set active_slot_index to match the currently active sculpt brush.

        Also updates the matching slot's asset reference from
        ``Paint.brush_asset_reference`` when available, so that future
        activations use the asset operator.
        """
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
        for i, (sx, sy) in enumerate(self.slot_positions):
            if self.active_toolset is not None and i >= len(self.active_toolset.slots):
                break
            if dist((mx, my), (sx, sy)) <= self.slot_radius:
                self.hover_index = i
                return

    def _is_inside_wheel(self, event: Event) -> bool:
        return dist(
            (event.mouse_region_x, event.mouse_region_y),
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
