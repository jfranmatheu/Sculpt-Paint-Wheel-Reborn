from bpy.types import Context

from ..wheel import Wheel
from ...widgets.tarta_ring import TartaRing
from ...widgets.weight_picker import WeightPickerWidget


class _WeightWheelBase(Wheel):
    tarta_ring: TartaRing
    weight_picker: WeightPickerWidget
    
    default_radius = 165

    def setup(self, context: Context) -> None:
        tarta_ring = TartaRing()
        tarta_ring.set_parent(self)
        tarta_ring.set_transform(0, 0, 0.12, 0.54)
        self.tarta_ring = tarta_ring

        weight_picker = WeightPickerWidget()
        weight_picker.set_parent(self)
        self.weight_picker = weight_picker

    def activate(self, context: Context, prefs, storage) -> None:
        self.weight_picker.set_transform(0, 0, 0.5, 0.80)


class WeightWheel(_WeightWheelBase):
    bl_context_mode = 'PAINT_WEIGHT'


class WeightGpencilWheel(_WeightWheelBase):
    bl_context_mode = 'WEIGHT_GPENCIL'
