from bpy.types import Context
from .wheel import Wheel
from ..widgets.brush_set_ring import BrushSetRing
from ..widgets.tarta_ring import TartaRing


class SculptPaintWheel(Wheel):
    brush_set_ring: BrushSetRing

    def setup(self, context: Context) -> None:
        brush_set_ring = BrushSetRing()
        brush_set_ring.set_parent(self)
        brush_set_ring.set_transform(0.0, 0.0, 0.97, 0.4)
        self.brush_set_ring = brush_set_ring

        tarta_ring = TartaRing()
        tarta_ring.set_parent(self)
        tarta_ring.set_transform(0.0, 0.0, brush_set_ring.radius_inner, 0.75)
