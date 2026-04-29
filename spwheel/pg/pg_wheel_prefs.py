from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroup
from .pg_brush_set import BrushSet, BrushSetPreferences
from .pg_colpk import ColorPickerPreferences
from .pg_wheel_theme import WheelTheme
from .wheels.weight_prefs import WeightWheelPrefs
from .pg_wheel_storage import WheelStorage


class WheelPrefs(PropertyGroup):

    # Wheel Storage.
    # -----------------------------------------------------------------------

    storage: PointerProperty(type=WheelStorage)


    # Per Mode Preferences.
    # -----------------------------------------------------------------------

    weight: PointerProperty(type=WeightWheelPrefs)


    # Wheel Style.
    # -----------------------------------------------------------------------

    scale: FloatProperty(
        name="Scale",
        description="Scale of the wheel",
        default=1.0,
        min=0.1,
        max=10.0,
        step=0.1,
        precision=2,
    )

    theme: PointerProperty(type=WheelTheme)

    # Wheel Behavior.
    # -----------------------------------------------------------------------

    keep_open: BoolProperty(
        name="Keep Open",
        description="First key release does not close the wheel; click to select then press key again to close",
        default=False,
    )

    select_on_release: BoolProperty(
        name="Select on Release",
        description="Select the hovered brush when the trigger key is released instead of clicking",
        default=False,
    )

    # Wheel Widgets Settings.
    # -----------------------------------------------------------------------

    color_picker: PointerProperty(type=ColorPickerPreferences)
    brush_set_ring: PointerProperty(type=BrushSetPreferences)


    # -----------------------------------------------------------------------
    # UI.
    # -----------------------------------------------------------------------

    def draw_preferences_ui(self, context: Context, layout: UILayout):
        _, content = self.draw_section(layout, "Settings", icon='SETTINGS')
        content.prop(self, 'scale')
        content.prop(self, 'keep_open')
        content.prop(self, 'select_on_release')

        _, content = self.draw_section(layout, "Theme", icon='COLOR')
        self.theme.draw_ui(context, content)
        
        _, content = self.draw_section(layout, "Color Picker", icon='COLORSET_02_VEC')
        self.color_picker.draw_ui(context, content)
