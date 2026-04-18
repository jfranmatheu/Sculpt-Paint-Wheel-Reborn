from bpy.types import Context, Gizmo as GZ

from .._base import BType
from ...gpu.globals import RuntimeDrawGlobals


class BType_GZ(BType, GZ):
    _instance = None

    @classmethod
    def get(cls):
        return cls._instance

    def setup(self):
        self.__class__._instance = self

    def exit(self, context, cancel):
        context.area.header_text_set(None)

    def modal(self, context, event, tweak):
        raise NotImplementedError("modal")

    def test_select(self, ctx, m):
        raise NotImplementedError("test_select")

    def invoke(self, ctx, evt):
        raise NotImplementedError("invoke")

    def draw(self, context: Context):
        pass
