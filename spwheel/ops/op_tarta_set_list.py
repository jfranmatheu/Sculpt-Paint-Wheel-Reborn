""" Operators that affect the Brush Set List items."""

from bpy.props import IntProperty
from ..core.bl_types import OperatorAction
from ..pg.pg_wheel_prefs import WheelPrefs


class OpPollActive:
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        if WheelPrefs.get(context).active_tarta_set is None:
            return "No active Custom Buttons set"
        return True


class OpTartaSetListAdd(OperatorAction):
    """ Add a new Brush Set to the Brush Set List."""
    def action(self, context, event):
        WheelPrefs.get(context).add_tarta_set()

class OpTartaSetListRemove(OperatorAction, OpPollActive):
    """ Add a new Brush Set to the Brush Set List."""
    def action(self, context, event):
        WheelPrefs.get(context).remove_active_tarta_set()


class OpTartaSetListMove(OperatorAction, OpPollActive):
    """ Add a new Brush Set to the Brush Set List."""

    direction: IntProperty(
        name="Direction",
        description="The direction to move the Brush Set List items",
        default=0,
        min=-1,
        max=1,
    )

    def action(self, context, event):
        WheelPrefs.get(context).move_active_tarta_set(self.direction)
