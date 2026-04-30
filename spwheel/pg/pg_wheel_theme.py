from typing import Tuple
from bpy.props import FloatProperty, FloatVectorProperty, PointerProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup



class ButtonTheme(PropertyGroup):
    label_color: FloatVectorProperty(
        subtype='COLOR', name="Label Color", min=0, max=1, size=4, default=(.92, .92, .92, .95))
    icon_opacity: FloatProperty(
        name="Icon Opacity", min=0, max=1, default=1.0)

    color: FloatVectorProperty(
        subtype='COLOR', name="Brush Color", min=0, max=1, size=4, default=(.01, .01, .01, .9))
    hovered_color: FloatVectorProperty(
        subtype='COLOR', name="Brush Hovered Color", min=0, max=1, size=4, default=(.02, .02, .02, .9))
    active_color: FloatVectorProperty(
        subtype='COLOR', name="Brush Active Color", min=0, max=1, size=4, default=(.01, .01, .01, .92))
    outline_color: FloatVectorProperty(
        subtype='COLOR', name="Brush Outline Color", min=0, max=1, size=4, default=(.164, .164, .164, .9))
    hovered_outline_color: FloatVectorProperty(
        subtype='COLOR', name="Brush Outline Hovered Color", min=0, max=1, size=4, default=(.02, .02, .02, .9))
    active_outline_color: FloatVectorProperty(
        subtype='COLOR', name="Brush Outline Active Color", min=0, max=1, size=4, default=(.92, .64, .11, .92))

    def get_color(self, hovered: bool, active: bool) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
        if active:
            return self.active_color, self.active_outline_color
        elif hovered:
            return self.hovered_color, self.hovered_outline_color
        else:
            return self.color, self.outline_color


class WheelTheme(PropertyGroup):
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(.92, .92, .92, .95))
    base_color: FloatVectorProperty(
        subtype='COLOR', name="Wheel Base Color", min=0, max=1, size=4, default=(.004, .004, .004, .95))
    base_outline_color: FloatVectorProperty(
        subtype='COLOR', name="Wheel Base Outline Color", min=0, max=1, size=4, default=(.164, .164, .164, .9))
    tarta_color: FloatVectorProperty(
        subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(.04, .04, .04, .6))
    tarta_outline_color: FloatVectorProperty(
        subtype='COLOR', name="Pie Outline Color", min=0, max=1, size=4, default=(.164, .164, .164, .9))
    # pad_color: FloatVectorProperty(
    #     subtype='COLOR', name="PAD Color", min=0, max=1, size=4, default=(.12, .12, .12, .4))

    button: PointerProperty(type=ButtonTheme)
    brush_picker_button: PointerProperty(type=ButtonTheme)


    def draw_ui(self, context: Context, layout: UILayout):
        layout.prop(self, 'text_color')

        layout.prop(self, 'base_color')
        layout.prop(self, 'base_outline_color')

        layout.prop(self, 'tarta_color')
        layout.prop(self, 'tarta_outline_color')

        h, content = self.draw_section(layout, "Brush Slot Colors", icon='BRUSH_DATA', align_content=True, content_layout_type='COLUMN')

        row = content.row(align=True)
        row.label(text="", icon='BLANK1')
        row.label(text="Idle")
        row.label(text="Hovered")
        row.label(text="Active")

        row = content.row(align=True)
        row.label(text="Base")
        row.box().prop(self, 'brush_color', text="")
        row.box().prop(self, 'brush_hovered_color', text="")
        row.box().prop(self, 'brush_active_color', text="")

        row = content.row(align=True)
        row.label(text="Outline")
        row.box().prop(self, 'brush_outline_color', text="")
        row.box().prop(self, 'brush_outline_hovered_color', text="")
        row.box().prop(self, 'brush_outline_active_color', text="")
