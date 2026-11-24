import traceback
from typing import Callable, Set
from bpy.types import Context, Event

from ..core import bl_types
from ..core.utils.op_return import OpReturn
from ..core.utils.mouse_utils import ModalMouse
from ..utils.ups import get_tool_settings

from ..wheels.wheel import Wheel, WheelPrefs


supported_modes = {'SCULPT', 'SCULPT_CURVES', 'PAINT_WEIGHT', 'PAINT_VERTEX', 'PAINT_TEXTURE', 'PAINT_GREASE_PENCIL', 'SCULPT_GREASE_PENCIL', 'WEIGHT_GREASE_PENCIL', 'VERTEX_GREASE_PENCIL' }


class WheelModal(bl_types.OperatorModal):
    """Wrapper operator for the Wheel modal loop (mode-agnostic)."""

    bl_label = "Sculpt-Paint Wheel Modal"

    wheel: Wheel
    prefs: WheelPrefs

    @classmethod
    def poll_operator(cls, context: Context) -> bool | str:
        if context.area.type != 'VIEW_3D':
            return '3D Viewport required for this operator'
        if context.active_object is None:
            return 'Active object required for this operator'
        if context.mode in supported_modes:
            return True
        return f'Current mode not in the supported modes: {supported_modes}'

    def modal_begin(self, context: Context, event: Event, modal_mouse: ModalMouse, **kw) -> None:
        if ts := get_tool_settings(context):
            if ts.brush:
                ts.show_brush = False
        # The draw handler runs for every 3D viewport region: draw only in the one the wheel was opened in.
        self._region_ptr = context.region.as_pointer() if context.region is not None else 0
        self.wheel = Wheel.get(context)
        self.prefs = WheelPrefs.get(context)
        self.wheel._activate(context, modal_mouse.init)
        self.wheel_is_hovered = True
        self.trigger_key = event.type
        self.trigger_key_released = False

    def modal_end(self, context: Context, cancel: bool, mouse: ModalMouse) -> None:
        if ts := get_tool_settings(context):
            if ts.brush:
                ts.show_brush = True

    def modal(self, context: Context, event: Event) -> Set[str]:
        try:
            return super().modal(context, event)
        except Exception as ex:
            # Without this, the error escapes the modal and the wheel is never closed: its drawing stays and the
            # brush cursor stays hidden.
            traceback.print_exc()
            self.report({'ERROR'}, f"Sculpt-Paint Wheel: {ex}")
            try:
                return self._modal_end(context, cancel=True)
            except Exception:
                traceback.print_exc()
                return OpReturn.CANCEL

    def modal_step_move(self, context: Context, event: Event, mouse: ModalMouse, **kw) -> bool:
        self.wheel_is_hovered = self.wheel.update_hover(context, mouse.current)
        return True

    def modal_step(self, context: Context, event: Event) -> Set[str] | Callable[[Context, Event], bool]:
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return OpReturn.CANCEL

        if event.type == self.trigger_key:
            if event.value == 'RELEASE':
                if not self.trigger_key_released:
                    self.trigger_key_released = True
                    
                    if self.prefs.select_on_release:
                        if self.wheel_is_hovered:
                            ret = self.wheel.on_left_press(context, event)
                            if ret and callable(ret):
                                # A widget that drags (pickers, brush set title / pages): no mouse button is held
                                # here, so take the press as a click and end its drag instead of entering it.
                                widget = getattr(ret, "__self__", None)
                                if widget is not None and hasattr(widget, "end_drag"):
                                    widget.end_drag(context)
                            else:
                                self.wheel.on_left_release(context, event)
                        
                        if not self.prefs.keep_open:
                            return OpReturn.FINISH
                        return OpReturn.RUN
                        
                    if not self.prefs.keep_open:
                        return OpReturn.FINISH
                return OpReturn.RUN
            elif event.value == 'PRESS':
                if self.trigger_key_released and self.prefs.keep_open:
                    return OpReturn.FINISH

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if not self.wheel_is_hovered:
                # We clicked outside the wheel, finish the modal loop.
                return OpReturn.FINISH
            ret = self.wheel.on_left_press(context, event)
            if ret and callable(ret):
                # Enter submodal state, where a widget takes temporal control of the modal loop.
                return ret
            else:
                return OpReturn.RUN

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.wheel.on_left_release(context, event)
            return OpReturn.RUN

        if event.type == 'WHEELUPMOUSE':
            self.wheel.on_scroll_up(context, event)
            return OpReturn.RUN

        if event.type == 'WHEELDOWNMOUSE':
            self.wheel.on_scroll_down(context, event)
            return OpReturn.RUN

        return OpReturn.RUN

    def draw_2d(self, context: Context) -> None:
        if not hasattr(self, 'wheel'):
            return
        region = context.region
        if region is None or region.as_pointer() != getattr(self, "_region_ptr", 0):
            return  # (Another viewport, or another view of a quad view.)
        try:
            self.wheel._draw(context, self.prefs)
        except Exception:
            if not getattr(self, "_draw_error_reported", False):  # (Once: it would repeat on every redraw.)
                self._draw_error_reported = True
                traceback.print_exc()
