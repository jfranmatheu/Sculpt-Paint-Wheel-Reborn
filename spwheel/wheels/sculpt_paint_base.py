from bpy.types import Context
from ..pg.pg_wheel_prefs import WheelPrefs
from .wheel import Wheel
from ..widgets.brush_set_ring import BrushSetRing
from ..widgets.tarta_ring import TartaRing
from ..pg.pg_wheel_storage import SculptPaintWheelStorage
from ..widgets.color_picker import ColorPickerWidget



class SculptPaintWheel(Wheel):
    brush_set_ring: BrushSetRing
    tarta_ring: TartaRing
    color_picker: ColorPickerWidget

    def setup(self, context: Context) -> None:
        tarta_ring = TartaRing()
        tarta_ring.set_parent(self)
        tarta_ring.set_transform(0, 0, .1, .4)
        self.tarta_ring = tarta_ring
        
        color_picker = ColorPickerWidget()
        color_picker.set_parent(self)
        color_picker.set_transform(0, 0, .4, .64)
        self.color_picker = color_picker

        brush_set_ring = BrushSetRing()
        brush_set_ring.set_parent(self)
        # brush_set_ring.set_transform_thickness(0.97, -100)
        self.brush_set_ring = brush_set_ring

    def activate(self, context: Context, prefs: WheelPrefs, storage: SculptPaintWheelStorage) -> None:
        self.brush_set_ring.set_transform_thickness(0.97, -1 * (prefs.brush_set_ring.slot_size + prefs.brush_set_ring.ring_padding * 2.0))
        self.color_picker.set_transform(0, 0, self.tarta_ring.radius_outer+4, self.brush_set_ring.radius_inner-4)
