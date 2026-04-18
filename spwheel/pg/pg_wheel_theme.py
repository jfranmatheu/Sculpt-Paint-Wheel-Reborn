from bpy.props import FloatVectorProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup



class WheelTheme(PropertyGroup):
    base_color: FloatVectorProperty(
        subtype='COLOR', name="Wheel Base Color", min=0, max=1, size=4, default=(.004, .004, .004, .95))
    pie_color: FloatVectorProperty(
        subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(.04, .04, .04, .6))
    pad_color: FloatVectorProperty(
        subtype='COLOR', name="PAD Color", min=0, max=1, size=4, default=(.12, .12, .12, .4))
    tool_color: FloatVectorProperty(
        subtype='COLOR', name="PAD Color", min=0, max=1, size=4, default=(.01, .01, .01, .9))
    tool_color_hovered: FloatVectorProperty(
        subtype='COLOR', name="PAD Color", min=0, max=1, size=4, default=(.02, .02, .02, .9))
    tool_outline_color: FloatVectorProperty(
        subtype='COLOR', name="PAD Color", min=0, max=1, size=4, default=(.164, .164, .164, .9))


    def draw_ui(self, context: Context, layout: UILayout):
        layout.prop(self, 'base_color')
        layout.prop(self, 'pie_color')
        layout.prop(self, 'pad_color')
        layout.prop(self, 'tool_color')
        layout.prop(self, 'tool_color_hovered')
        layout.prop(self, 'tool_outline_color')
