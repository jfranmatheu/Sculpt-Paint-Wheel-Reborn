""" Operators that affect the Brush Set List items."""

from bpy.props import IntProperty
from ..core.bl_types import OperatorAction
from ..pg.pg_wheel_storage import WheelStorage, SculptPaintWheelStorage


class OpPollStorage:
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        storage = WheelStorage.get_by_mode(context)
        if storage is None or not hasattr(storage, "brush_sets"):
            return "Only in a sculpt / paint mode with brush sets"
        return True


class OpPollActive(OpPollStorage):
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        if (valid := super().poll_operator(context)) is not True:
            return valid
        if WheelStorage.get_by_mode(context).active_brush_set is None:
            return "No active brush set"
        return True


class OpBrushSetListAdd(OperatorAction, OpPollStorage):
    """ Add a new Brush Set to the Brush Set List."""
    def action(self, context, event):
        WheelStorage.get_by_mode(context).add_brush_set(context.mode)

class OpBrushSetListRemove(OperatorAction, OpPollActive):
    """ Add a new Brush Set to the Brush Set List."""
    def action(self, context, event):
        WheelStorage.get_by_mode(context).remove_active_brush_set()


class OpBrushSetListMove(OperatorAction, OpPollActive):
    """ Add a new Brush Set to the Brush Set List."""

    direction: IntProperty(
        name="Direction",
        description="The direction to move the Brush Set List items",
        default=0,
        min=-1,
        max=1,
    )

    def action(self, context, event):
        WheelStorage.get_by_mode(context).move_active_brush_set(self.direction)
