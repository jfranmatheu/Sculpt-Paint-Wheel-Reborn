from bpy.types import Context

from ..wheel import Wheel
from ...widgets.tarta_ring import TartaRing
from ...widgets.weight_picker import WeightPickerWidget
from ...widgets.weight_toolbar import WeightToolbarWidget


class _WeightWheelBase(Wheel):
    tarta_ring: TartaRing
    weight_picker: WeightPickerWidget
    weight_toolbar: WeightToolbarWidget
    
    default_radius = 170

    def setup(self, context: Context) -> None:
        tarta_ring = TartaRing()
        tarta_ring.set_parent(self)
        tarta_ring.set_transform(0, 0, 0.08, 0.48)
        self.tarta_ring = tarta_ring

        weight_picker = WeightPickerWidget()
        weight_picker.set_parent(self)
        self.weight_picker = weight_picker

        weight_toolbar = WeightToolbarWidget()
        weight_toolbar.set_parent(self)
        self.weight_toolbar = weight_toolbar

    def activate(self, context: Context, prefs, storage) -> None:
        self.prefs = prefs
        self.weight_picker.set_transform(0, 0, 0.4, 0.81)


class WeightWheel(_WeightWheelBase):
    bl_context_mode = 'PAINT_WEIGHT'


class WeightGreasePencilWheel(_WeightWheelBase):
    bl_context_mode = 'WEIGHT_GREASE_PENCIL'
