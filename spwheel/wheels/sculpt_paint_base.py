from bpy.types import Context
from ..pg.pg_wheel_prefs import WheelPrefs
from .wheel import Wheel
from ..widgets.brush_set_ring import BrushSetRing
from ..widgets.tarta_ring import TartaRing
from ..pg.pg_wheel_storage import SculptPaintWheelStorage, WheelStorage
from ..widgets.color_picker import ColorPickerWidget


class SculptPaintWheel(Wheel):
    brush_set_ring: BrushSetRing
    tarta_ring: TartaRing
    color_picker: ColorPickerWidget
    default_radius = 210 # radius without color picker: 160
    reduced_radius = 160

    def setup(self, context: Context) -> None:
        tarta_ring = TartaRing()
        tarta_ring.set_parent(self)
        self.tarta_ring = tarta_ring
        
        color_picker = ColorPickerWidget()
        color_picker.set_parent(self)
        self.color_picker = color_picker

        brush_set_ring = BrushSetRing()
        brush_set_ring.set_parent(self)
        self.brush_set_ring = brush_set_ring

    def on_brush_set_change(self, context: Context) -> None:
        self._activate(context)

    def activate(self, context: Context, prefs: WheelPrefs, storage: SculptPaintWheelStorage) -> None:
        active_brush_set = WheelStorage.get_by_mode(context).active_brush_set
        use_colorpk = active_brush_set.use_color_picker if active_brush_set else False
        self.radius = self.default_radius if use_colorpk else self.reduced_radius

        self.brush_set_ring.set_transform_thickness(0.97, -1 * (prefs.brush_set_ring.slot_size + prefs.brush_set_ring.ring_padding * 2.0))
        if use_colorpk:
            self.color_picker.enabled = True
            self.tarta_ring.set_transform(0, 0, .1, .4)
            self.color_picker.set_transform(0, 0, self.tarta_ring.radius_outer+4, self.brush_set_ring.radius_inner-4)
        else:
            self.color_picker.enabled = False
            self.tarta_ring.set_transform(0, 0, 0.1, self.brush_set_ring.radius_inner-4)
