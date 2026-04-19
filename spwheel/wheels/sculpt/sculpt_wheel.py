from bpy.types import Context
from ..wheel import Wheel

from ...widgets.brush_set_ring import BrushSetRing

class SculptWheel(Wheel):

    def setup(self, context: Context) -> None:
        brush_set_ring = BrushSetRing()
        brush_set_ring.set_parent(self)
        brush_set_ring.set_transform(0.0, 0.0, 0.74, 0.4)
