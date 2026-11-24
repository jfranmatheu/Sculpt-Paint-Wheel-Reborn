from typing import Tuple
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, PointerProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup
from ..utils.tint_palette import PALETTE_RGB



class ButtonTheme(PropertyGroup):
    label_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Label Color", min=0, max=1, size=4, default=(.92, .92, .92, .95))
    icon_opacity: FloatProperty(
        name="Icon Opacity", min=0, max=1, default=1.0)

    color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Brush Color", min=0, max=1, size=4, default=(.153, .153, .165, 1.0))
    hovered_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Brush Hovered Color", min=0, max=1, size=4, default=(.188, .188, .204, 1.0))
    active_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Brush Active Color", min=0, max=1, size=4, default=(.178, .267, .421, 1.0))
    outline_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Brush Outline Color", min=0, max=1, size=4, default=(.247, .247, .275, 1.0))
    highlight_outline_width: FloatProperty(
        name="Hovered / Active Outline Width",
        description="Width of the outline of a hovered or active brush, in pixels",
        min=0.25, max=6.0, default=2.0, subtype='PIXEL')
    active_outline_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Brush Outline Active Color", min=0, max=1, size=4, default=(.231, .510, .965, 1.0))

    def get_color(self, hovered: bool, active: bool) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
        if active:
            return self.active_color, self.active_outline_color
        elif hovered:
            return self.hovered_color, self.outline_color  # Hover outline: the wheel's accent color.
        else:
            return self.color, self.outline_color


class WheelTheme(PropertyGroup):
    text_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Text Color", min=0, max=1, size=4, default=(.98, .98, .98, 1.0))
    base_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Wheel Base Color", min=0, max=1, size=4, default=(.084, .084, .091, 1.0))
    base_outline_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Wheel Base Outline Color", min=0, max=1, size=4, default=(.247, .247, .275, 1.0))
    tarta_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Pie Color", min=0, max=1, size=4, default=(.115, .115, .124, 1.0))
    tarta_outline_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Pie Outline Color", min=0, max=1, size=4, default=(.247, .247, .275, 1.0))
    tarta_accent_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Accent Color", min=0, max=1, size=4, default=(.98, .98, .98, .75),
        description="Ring around a hovered brush slot")
    tarta_pressed_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Pressed Color", min=0, max=1, size=4, default=(.231, .510, .965, 1.0),
        description="Pressed pie buttons (toggles that are on, operators whose state is on): their fill blends towards it and their outline takes it")
    core_color: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Core Color", min=0, max=1, size=4, default=(.061, .061, .066, 1.0),
        description="Disc in the middle of the wheel, behind the name")
    tarta_icon_size: FloatProperty(
        name="Icon Size", description="Size of the pie buttons' icons, as a fraction of the segment thickness",
        min=0.2, max=1.0, default=0.72, subtype='FACTOR')
    shadow_opacity: FloatProperty(
        name="Shadow Opacity", description="Opacity of the soft shadow around the wheel (0: no shadow)",
        min=0.0, max=1.0, default=0.45, subtype='FACTOR')
    shadow_size: FloatProperty(
        name="Shadow Size", description="Blur of the shadow's edge, as a fraction of the wheel radius",
        min=0.0, max=0.5, default=0.06, subtype='FACTOR')
    tarta_tint_mode: EnumProperty(
        name="Tint Mode",
        description="How the pie segments of the custom buttons are tinted",
        items=(
            ("DISABLED", "Disabled", "No tint: every segment uses the pie color"),
            ("PER_TYPE", "Per Type", "Tint by button type (operator / script, popup, toggle)"),
            ("CUSTOM", "Custom", "Each button's own color, picked from the swatch in the button list"),
        ),
        default="CUSTOM")
    tarta_tint_target: EnumProperty(
        name="Tint Target",
        description="What part of a custom button shows its tint",
        items=(
            ("FILL", "Fill", "The segment's fill"),
            ("OUTLINE", "Outline", "The segment's outline"),
            ("ICON", "Icon", "The button's icon"),
            ("COLOR_STRIP", "Color Strip", "A thin strip along the inner edge of the segment"),
        ),
        default="FILL")
    tarta_tint_opacity: FloatProperty(
        name="Tint Opacity",
        description="Opacity of the tint on the outline, the icon or the color strip",
        min=0.0, max=1.0, default=0.9, subtype='FACTOR')
    tarta_custom_tint_strength: FloatProperty(
        name="Custom Tint Strength",
        description="How strongly a button's custom color tints its segment (0: none, 1: the full color)",
        min=0.0, max=1.0, default=0.12, subtype='FACTOR')
    tarta_operator_tint: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Operator / Script Tint", min=0, max=1, size=4, default=(.2, .35, .7, .25),
        description="Tint of operator and script buttons, mixed over the pie color (alpha: tint strength)")
    tarta_popup_tint: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Popup Tint", min=0, max=1, size=4, default=(.6, .4, .8, .15),
        description="Tint of popup (menu / panel) buttons, mixed over the pie color (alpha: tint strength)")
    tarta_toggle_tint: FloatVectorProperty(
        subtype='COLOR_GAMMA', name="Toggle Tint", min=0, max=1, size=4, default=(.25, .6, .45, .2),
        description="Tint of toggle buttons while off, mixed over the pie color (alpha: tint strength). "
                    "When on, they are filled with the accent color")

    def get_tarta_tint(self, button) -> Tuple[float, float, float, float] | None:
        """A custom button's tint: (r, g, b, fill strength), or None (tint disabled, or no tint for it)."""
        mode = self.tarta_tint_mode
        if mode == "DISABLED" or button is None:
            return None
        if mode == "CUSTOM":
            rgb = PALETTE_RGB.get(button.tint)
            return None if rgb is None else (*rgb, self.tarta_custom_tint_strength)
        if button.is_operator or button.is_script:
            return tuple(self.tarta_operator_tint)
        if button.is_popup:
            return tuple(self.tarta_popup_tint)
        if button.is_toggle:
            return tuple(self.tarta_toggle_tint)
        return None

    def get_tarta_fill(self, button) -> Tuple[float, float, float, float]:
        """Segment fill for a custom button: the pie color, tinted when the tint targets the fill."""
        base = self.tarta_color
        tint = self.get_tarta_tint(button) if self.tarta_tint_target == "FILL" else None
        if tint is None:
            return tuple(base)
        k = tint[3]
        return (base[0] + (tint[0] - base[0]) * k,
                base[1] + (tint[1] - base[1]) * k,
                base[2] + (tint[2] - base[2]) * k,
                base[3])
    # pad_color: FloatVectorProperty(
    #     subtype='COLOR_GAMMA', name="PAD Color", min=0, max=1, size=4, default=(.12, .12, .12, .4))

    button: PointerProperty(type=ButtonTheme)
    brush_picker_button: PointerProperty(type=ButtonTheme)


    def draw_ui(self, context: Context, layout: UILayout):
        from .pg_wheel_prefs import prefs_panel

        row = layout.row()
        row.alignment = 'RIGHT'
        row.operator("spwheel.opresetwheeltheme", text="Reset Theme", icon='LOOP_BACK')

        if body := prefs_panel(layout, "spwheel_theme_general", "General", 'COLOR'):
            body.prop(self, 'tarta_accent_color')
            body.prop(self, 'text_color')

        if body := prefs_panel(layout, "spwheel_theme_wheel", "Wheel", 'MESH_CIRCLE'):
            body.prop(self, 'base_color', text="Background")
            body.prop(self, 'base_outline_color', text="Outline")
            body.prop(self, 'core_color', text="Core")
            col = body.column(heading="Shadow")
            col.prop(self, 'shadow_opacity', text="Opacity")
            sub = col.column()
            sub.active = self.shadow_opacity > 0.0
            sub.prop(self, 'shadow_size', text="Size")

        if body := prefs_panel(layout, "spwheel_theme_pie", "Pie Menu", 'ANTIALIASED'):
            body.prop(self, 'tarta_color', text="Segment")
            body.prop(self, 'tarta_outline_color', text="Outline")
            body.prop(self, 'tarta_pressed_color', text="Pressed")
            body.prop(self, 'tarta_icon_size')
            body.separator()
            body.row().prop(self, 'tarta_tint_mode', text="Tint", expand=True)
            if self.tarta_tint_mode != "DISABLED":
                body.row().prop(self, 'tarta_tint_target', text="Target", expand=True)
                if self.tarta_tint_target != "FILL":
                    body.prop(self, 'tarta_tint_opacity', text="Opacity")
            if self.tarta_tint_mode == "PER_TYPE":
                body.prop(self, 'tarta_operator_tint', text="Operator / Script")
                body.prop(self, 'tarta_popup_tint', text="Popup")
                body.prop(self, 'tarta_toggle_tint', text="Toggle")
            elif self.tarta_tint_mode == "CUSTOM":
                if self.tarta_tint_target == "FILL":
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
