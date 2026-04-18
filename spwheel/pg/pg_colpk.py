from bpy.types import BoolProperty, Context, UILayout

from ..core.bl_types import PropertyGroup


class ColorPicker(PropertyGroup):
    lock_ring_sv: BoolProperty(
        name="[Ring] Lock Saturation/Lightness",
        default=False,
        description="Lock Saturation and Lightness (Value) in the color picker ring for the Hue"
    )

    def draw_ui(self, context: Context, layout: UILayout):
        layout.prop(self, 'lock_ring_sv')
