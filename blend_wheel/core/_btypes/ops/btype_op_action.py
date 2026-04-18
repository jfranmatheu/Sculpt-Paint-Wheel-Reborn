from typing import Set
from bpy.types import Context, Event

from .btype_op_base import BType_Operator
from ...utils.op_return import OpReturn


class BType_OpAction(BType_Operator):

    def action(self, context: Context, event: Event) -> bool | str:
        return False

    def invoke(self, context: Context, event: Event) -> Set[str]:
        msg = self.action(context, event)
        if isinstance(msg, str):
            self.report({"ERROR"}, msg)
            return OpReturn.CANCEL
        elif msg:
            return OpReturn.FINISH
        else:
            return OpReturn.CANCEL
