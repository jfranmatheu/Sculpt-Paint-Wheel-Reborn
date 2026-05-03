""" Operators that affect the Brush Set List items."""

from bpy.props import IntProperty, StringProperty
from bpy.types import Context
from ..core.bl_types import OperatorAction
from ..pg.pg_wheel_storage import WheelStorage, WheelTartaSetStorage


class OpPollActive:
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        if WheelStorage.get_by_mode(context).active_tarta_set is None:
            return "No active Custom Buttons set"
        return True


class OpTartaSetListAdd(OperatorAction):
    """ Add a new Brush Set to the Brush Set List."""
    bl_label = "Add Custom Buttons Set"
    
    set_name: StringProperty(
        name="Custom Buttons Set Name",
        description="The name of the new Custom Buttons Set",
        default="New Custom Buttons Set",
    )

    def draw(self, context: Context) -> None:
        self.layout.prop(self, "set_name", text="Set Name")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, confirm_text="Create Set")

    def execute(self, context):
        WheelStorage.get_by_mode(context).add_tarta_set(self.set_name)
        return {"FINISHED"}

class OpTartaSetListRemove(OperatorAction, OpPollActive):
    """ Remove the active Custom Buttons Set from the Custom Buttons Set List."""
    bl_label = "Remove Custom Buttons Set"
    
    def action(self, context, event):
        WheelStorage.get_by_mode(context).remove_active_tarta_set()


class OpTartaSetListMove(OperatorAction, OpPollActive):
    """ Move the Custom Buttons Set List items."""
    bl_label = "Move Custom Buttons Set"

    direction: IntProperty(
        name="Direction",
        description="The direction to move the Custom Buttons Set List items",
        default=0,
        min=-1,
        max=1,
    )

    def action(self, context, event):
        WheelStorage.get_by_mode(context).move_active_tarta_set(self.direction)
