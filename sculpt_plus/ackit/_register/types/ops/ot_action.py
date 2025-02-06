from typing import Set

from bpy.types import Context, Event, UILayout

from ....utils.operator import OpsReturn
from .ot_generic import Generic


__all__ = ['Action']


class Action(Generic):
    def execute(self, context: Context) -> Set[str]:
        self.action(context)
        return OpsReturn.FINISH

    def action(self, context: 'Context') -> None:
        pass
