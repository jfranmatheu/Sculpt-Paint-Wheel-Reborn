from bpy.props import BoolProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup


class ColorPickerPreferences(PropertyGroup):
    lock_ring_sv: BoolProperty(
        name="[Ring] Lock Saturation/Lightness",
        default=False,
        description="Lock Saturation and Lightness (Value) in the color picker ring for the Hue"
    )

    def draw_ui(self, context: Context, layout: UILayout):
        layout.prop(self, 'lock_ring_sv')
