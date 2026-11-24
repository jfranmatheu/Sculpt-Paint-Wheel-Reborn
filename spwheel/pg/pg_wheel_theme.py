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
    highlight_outline_width: FloatProperty(
        name="Hovered / Active Outline Width",
        description="Width of the outline of a hovered or active brush, in pixels",
        min=0.25, max=6.0, default=2.0, subtype='PIXEL')
    active_outline_color: FloatVectorProperty(
        subtype='COLOR', name="Brush Outline Active Color", min=0, max=1, size=4, default=(.92, .64, .11, .92))

    def get_color(self, hovered: bool, active: bool) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
        if active:
            return self.active_color, self.active_outline_color
        elif hovered:
            return self.hovered_color, self.outline_color  # Hover outline: the wheel's accent color.
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
        subtype='COLOR', name="Accent Color", min=0, max=1, size=4, default=(.82, .84, .88, .85),
        description="Hover outline of the pie buttons and the brush buttons; pressed (toggled on) pie buttons are "
                    "filled with a blend of it")
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
        from .pg_wheel_prefs import prefs_panel

        if body := prefs_panel(layout, "spwheel_theme_general", "General", 'COLOR'):
            body.prop(self, 'tarta_accent_color')
            body.prop(self, 'text_color')

        if body := prefs_panel(layout, "spwheel_theme_wheel", "Wheel", 'MESH_CIRCLE'):
            body.prop(self, 'base_color', text="Background")
            body.prop(self, 'base_outline_color', text="Outline")

        if body := prefs_panel(layout, "spwheel_theme_pie", "Pie Menu", 'ANTIALIASED'):
            body.prop(self, 'tarta_color', text="Segment")
            body.prop(self, 'tarta_outline_color', text="Outline")
            body.separator()
            body.row().prop(self, 'tarta_tint_mode', text="Tint", expand=True)
            if self.tarta_tint_mode == "PER_TYPE":
                body.prop(self, 'tarta_operator_tint', text="Operator / Script")
                body.prop(self, 'tarta_popup_tint', text="Popup")
                body.prop(self, 'tarta_toggle_tint', text="Toggle")
            elif self.tarta_tint_mode == "CUSTOM":
                body.prop(self, 'tarta_custom_tint_strength', text="Strength")
                hint = body.row()
                hint.active = False
                hint.label(text="Pick each button's color in the Custom Buttons list", icon='INFO')

        if body := prefs_panel(layout, "spwheel_theme_brush_ring", "Brush Ring", 'BRUSH_DATA'):
            self._draw_brush_slots(body)

    def _draw_brush_slots(self, layout: UILayout) -> None:
        bt = self.brush_picker_button  # What the brush slots draw with.
        grid = layout.grid_flow(row_major=True, columns=4, even_columns=False, align=True)
        grid.use_property_split = False
        for text in ("", "Idle", "Hovered", "Active"):
            grid.label(text=text)
        grid.label(text="Fill")
        grid.prop(bt, 'color', text="")
        grid.prop(bt, 'hovered_color', text="")
        grid.prop(bt, 'active_color', text="")
        grid.label(text="Outline")
        grid.prop(bt, 'outline_color', text="")
        grid.prop(self, 'tarta_accent_color', text="")  # Shared with the pie menu hover.
        grid.prop(bt, 'active_outline_color', text="")
        layout.separator()
        layout.prop(bt, 'highlight_outline_width', text="Hovered / Active Width")
        layout.prop(bt, 'icon_opacity')
