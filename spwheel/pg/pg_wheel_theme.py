from typing import Tuple
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, PointerProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup
from ..utils.tint_palette import PALETTE_RGB



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
        subtype='COLOR', name="Brush Outline Hovered Color", min=0, max=1, size=4, default=(.32, .32, .32, 1.0))
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
        subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(.075, .075, .08, .96))
    tarta_outline_color: FloatVectorProperty(
        subtype='COLOR', name="Pie Outline Color", min=0, max=1, size=4, default=(.164, .164, .164, .9))
    tarta_accent_color: FloatVectorProperty(
        subtype='COLOR', name="Pie Accent Color", min=0, max=1, size=4, default=(.17, .36, .72, 1.0),
        description="Outline of the hovered button and fill of pressed (toggled on) buttons")
    tarta_tint_mode: EnumProperty(
        name="Tint Mode",
        description="How the pie segments of the custom buttons are tinted",
        items=(
            ("DISABLED", "Disabled", "No tint: every segment uses the pie color"),
            ("PER_TYPE", "Per Type", "Tint by button type (operator / script, popup, toggle)"),
            ("CUSTOM", "Custom", "Each button's own color, picked from the swatch in the button list"),
        ),
        default="CUSTOM")
    tarta_custom_tint_strength: FloatProperty(
        name="Custom Tint Strength",
        description="How strongly a button's custom color tints its segment (0: none, 1: the full color)",
        min=0.0, max=1.0, default=0.3, subtype='FACTOR')
    tarta_operator_tint: FloatVectorProperty(
        subtype='COLOR', name="Operator / Script Tint", min=0, max=1, size=4, default=(.2, .35, .7, .25),
        description="Tint of operator and script buttons, mixed over the pie color (alpha: tint strength)")
    tarta_popup_tint: FloatVectorProperty(
        subtype='COLOR', name="Popup Tint", min=0, max=1, size=4, default=(.6, .4, .8, .15),
        description="Tint of popup (menu / panel) buttons, mixed over the pie color (alpha: tint strength)")
    tarta_toggle_tint: FloatVectorProperty(
        subtype='COLOR', name="Toggle Tint", min=0, max=1, size=4, default=(.25, .6, .45, .2),
        description="Tint of toggle buttons while off, mixed over the pie color (alpha: tint strength). "
                    "When on, they are filled with the accent color")

    def get_tarta_fill(self, button) -> Tuple[float, float, float, float]:
        """Segment fill for a custom button: the pie color, tinted by the button type when enabled."""
        base = self.tarta_color
        mode = self.tarta_tint_mode
        if mode == "DISABLED" or button is None:
            return tuple(base)
        if mode == "CUSTOM":
            rgb = PALETTE_RGB.get(button.tint)
            if rgb is None:
                return tuple(base)
            tint = (*rgb, self.tarta_custom_tint_strength)
        elif button.is_operator or button.is_script:
            tint = self.tarta_operator_tint
        elif button.is_popup:
            tint = self.tarta_popup_tint
        elif button.is_toggle:
            tint = self.tarta_toggle_tint
        else:
            return tuple(base)
        k = tint[3]
        return (base[0] + (tint[0] - base[0]) * k,
                base[1] + (tint[1] - base[1]) * k,
                base[2] + (tint[2] - base[2]) * k,
                base[3])
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
        layout.prop(self, 'tarta_accent_color')
        layout.prop(self, 'tarta_tint_mode')
        if self.tarta_tint_mode == "PER_TYPE":
            layout.prop(self, 'tarta_operator_tint')
            layout.prop(self, 'tarta_popup_tint')
            layout.prop(self, 'tarta_toggle_tint')
        elif self.tarta_tint_mode == "CUSTOM":
            layout.prop(self, 'tarta_custom_tint_strength')

        h, content = self.draw_section(layout, "Brush Slot Colors", icon='BRUSH_DATA', align_content=True, content_layout_type='COLUMN')

        split = content.row(align=True).split(factor=0.15, align=True)

        left_col = split.column(align=True)
        left_col.label(text=" ", icon='BLANK1')
        left_col.label(text="Base")
        left_col.label(text="Outline")

        right_row = split.row(align=True)

        idle_col = right_row.column(align=True)
        idle_col.label(text="Idle")
        idle_col.prop(self.button, 'color', text="")
        idle_col.prop(self.button, 'outline_color', text="")

        hovered_col = right_row.column(align=True)
        hovered_col.label(text="Hovered")
        hovered_col.prop(self.button, 'hovered_color', text="")
        hovered_col.prop(self.button, 'hovered_outline_color', text="")

        active_col = right_row.column(align=True)
        active_col.label(text="Active")
        active_col.prop(self.button, 'active_color', text="")
        active_col.prop(self.button, 'active_outline_color', text="")
