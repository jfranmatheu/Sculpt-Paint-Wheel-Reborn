from typing import Set
from bpy.types import Context, Event

from .btype_op_base import BType_Operator
from ...utils.op_return import OpReturn


class BType_OpAction(BType_Operator):

    def action(self, context: Context, event: Event) -> bool | str | None:
        """Do the operator's work. Return a message (str) to report an error, False to cancel; anything else
        (True, or nothing) means it finished."""
        return False

    def invoke(self, context: Context, event: Event) -> Set[str]:
        msg = self.action(context, event)
        if isinstance(msg, str):
            self.report({"ERROR"}, msg)
            return OpReturn.CANCEL
        if msg is False:
            return OpReturn.CANCEL
        # (None included: actions that just do their work don't return anything.)
        return OpReturn.FINISH
