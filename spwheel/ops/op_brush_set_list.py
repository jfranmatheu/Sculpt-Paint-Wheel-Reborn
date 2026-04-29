""" Operators that affect the Brush Set List items."""

from bpy.props import IntProperty
from ..core.bl_types import OperatorAction
from ..pg.pg_wheel_storage import WheelStorage, SculptPaintWheelStorage


class OpPollActive:
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        if WheelStorage.get(context).active_brush_set is None:
            return "No active brush set"
        return True


class OpBrushSetListAdd(OperatorAction):
    """ Add a new Brush Set to the Brush Set List."""
    def action(self, context, event):
        WheelStorage.get(context).add_brush_set()

class OpBrushSetListRemove(OperatorAction, OpPollActive):
    """ Add a new Brush Set to the Brush Set List."""
    def action(self, context, event):
        WheelStorage.get(context).remove_active_brush_set()


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
        WheelStorage.get(context).move_active_brush_set(self.direction)
