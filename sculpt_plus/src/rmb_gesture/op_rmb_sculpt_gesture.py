"""Modal: right-button click-drag to adjust sculpt brush size and strength."""

from __future__ import annotations

from typing import Set

from bpy.types import Context, Event

from ..core import bl_types
from ..core.utils.op_return import OpReturn
from ..core.utils.mouse_utils import ModalMouse
from ..prefs import SculptPlusPreferences
from ..sculpt_wheel.brush_assets import get_active_sculpt_brush
from .brush_adjust import (
    brush_size_get,
    brush_size_set,
    brush_strength_get,
    brush_strength_set,
)
from .draw import draw_rmb_gesture


class RmbSculptGestureOperator(bl_types.OperatorModal):
    """Adjust active sculpt brush size (vertical axis) and strength (horizontal) via RMB drag."""

    bl_label = "Sculpt RMB Brush Gesture"
    bl_context_mode = "SCULPT"

    cancel_on = {"ESC"}
    confirm_on: Set[str] = set()

    _state: str | None = None  # None | 'pending' | 'drag'
    _axis: str | None = None
    _origin: tuple[float, float] = (0.0, 0.0)
    _prev: tuple[float, float] = (0.0, 0.0)
    _saved_size: float = 0.0
    _saved_strength: float = 0.0
    _invert: bool = False
    _overlay_radius: float = 180.0
    _preview: str = "SIMPLE"

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.area is None or context.area.type != "VIEW_3D":
            return "Requires a 3D Viewport"
        if context.mode != "SCULPT":
            return "Must be in Sculpt mode"
        if get_active_sculpt_brush(context) is None:
            return "No active sculpt brush"
        return True

    @staticmethod
    def _prefs(context: Context) -> SculptPlusPreferences | None:
        bl_id = getattr(SculptPlusPreferences, "bl_idname", None)
        if bl_id is None:
            return None
        addon = context.preferences.addons.get(bl_id)
        return addon.preferences if addon else None

    def invoke(self, context: Context, event: Event) -> Set[str]:
        prefs = self._prefs(context)
        self._invert = bool(prefs.rmb_gesture_invert) if prefs else False
        self._overlay_radius = float(
            prefs.rmb_gesture_overlay_radius if prefs else 180
        )
        self._preview = (
            str(prefs.rmb_gesture_preview) if prefs else "SIMPLE"
        )
        self._origin = (float(event.mouse_region_x), float(event.mouse_region_y))
        self._prev = self._origin
        self._saved_size = brush_size_get(context)
        self._saved_strength = brush_strength_get(context)
        self._state = "pending"
        self._axis = None

        if not context.window_manager.modal_handler_add(self):
            return OpReturn.CANCEL
        self._modal_begin(context, event)
        context.window.cursor_modal_set("CROSSHAIR")
        return OpReturn.RUN

    def draw_2d(self, context: Context) -> None:
        draw_rmb_gesture(context, self)

    def modal_begin(
        self, context: Context, event: Event, modal_mouse: ModalMouse, **kw
    ) -> None:
        context.region.tag_redraw()

    def modal_step(self, context: Context, event: Event) -> Set[str]:
        if event.type == "RIGHTMOUSE" and event.value == "RELEASE":
            if self._state == "pending":
                brush_size_set(context, self._saved_size)
                brush_strength_set(context, self._saved_strength)
            return OpReturn.FINISH
        return OpReturn.RUN

    def modal_step_move(
        self, context: Context, event: Event, mouse: ModalMouse, **kw
    ) -> bool:
        mx, my = float(event.mouse_region_x), float(event.mouse_region_y)

        if self._state == "pending":
            px, py = self._prev
            if abs(my - py) > 6.0:
                self._axis = "Y"
                self._state = "drag"
                self._prev = (mx, my)
            elif abs(mx - px) > 6.0:
                self._axis = "X"
                self._state = "drag"
                self._prev = (mx, my)
        elif self._state == "drag" and self._axis:
            self._gesture_apply(context, event, mx, my)

        context.region.tag_redraw()
        return True

    def modal_end(self, context: Context, cancel: bool, mouse: ModalMouse) -> None:
        context.window.cursor_modal_restore()
        if cancel:
            brush_size_set(context, self._saved_size)
            brush_strength_set(context, self._saved_strength)

    def _gesture_apply(self, context: Context, event: Event, mx: float, my: float) -> None:
        axis = self._axis
        if axis is None:
            return
        px, py = self._prev
        diff = (my - py) if axis == "Y" else (mx - px)
        if abs(diff) < 5.0:
            return
        is_vert = axis == "Y"
        rate = 1.0 if is_vert else 0.01
        if event.shift:
            rate *= 0.2
        elif event.ctrl:
            rate *= 2.0
        invert = self._invert
        adjust_size = (is_vert and not invert) or (not is_vert and invert)
        if adjust_size:
            brush_size_set(context, brush_size_get(context) + rate * diff)
        else:
            brush_strength_set(
                context, brush_strength_get(context) + rate * diff
            )
        self._prev = (mx, my)
