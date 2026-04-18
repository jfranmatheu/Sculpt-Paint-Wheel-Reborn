from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty
from bpy.types import Context, PointerProperty, UILayout

from ..core.bl_types import PropertyGroup
from .pg_brush_set import BrushSet
from .pg_colpk import ColorPicker
from .pg_wheel_theme import WheelTheme
from .pg_tarta_set import WheelTartaSet
from ..ui.lists.ul_brush_sets_list import BrushSetsList
from ..ui.lists.ul_tarta_set_list import TartaSetList



class WheelPrefs(PropertyGroup):

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

    color_picker: PointerProperty(type=ColorPicker)


    # Tarta Sets.
    # -----------------------------------------------------------------------

    tarta_sets: CollectionProperty(type=WheelTartaSet)
    active_tarta_set_index: IntProperty(
        name="Active Custom Buttons Set Index",
        description="Index of the active custom buttons set",
        default=-1,
    )

    @property
    def active_tarta_set(self) -> WheelTartaSet:
        if not self.tarta_sets:
            return None
        if self.active_tarta_set_index < 0:
            return None
        if self.active_tarta_set_index >= len(self.tarta_sets):
            return None
        return self.tarta_sets[self.active_tarta_set_index]


    # Wheel Data: Brush Sets.
    # -----------------------------------------------------------------------

    brush_sets: CollectionProperty(type=BrushSet)
    active_brush_set_index: IntProperty(
        name="Active Brush Set Index",
        description="Index of the active brush set",
        default=-1,
    )

    @property
    def active_brush_set(self) -> BrushSet:
        if not self.brush_sets:
            return None
        if self.active_brush_set_index < 0:
            return None
        if self.active_brush_set_index >= len(self.brush_sets):
            return None
        return self.brush_sets[self.active_brush_set_index]


    # -----------------------------------------------------------------------
    # UI.
    # -----------------------------------------------------------------------

    def draw_ui(self, context: Context, layout: UILayout, in_preferences: bool = False):
        if in_preferences:
            self.draw_preferences_ui(context, layout)
        else:
            self.draw_panel_ui(context, layout)

    def draw_preferences_ui(self, context: Context, layout: UILayout):
        _, content = self.draw_section(layout, "Settings", icon='SETTINGS')
        content.prop(self, 'scale')
        content.prop(self, 'keep_open')
        content.prop(self, 'select_on_release')

        _, content = self.draw_section(layout, "Theme", icon='COLOR')
        self.theme.draw_ui(context, content)
        
        _, content = self.draw_section(layout, "Color Picker", icon='COLORSET_02_VEC')
        self.color_picker.draw_ui(context, content)

    def draw_panel_ui(self, context: Context, layout: UILayout):
        # Only the brush sets.
        self.draw_brush_set_list(layout)

    def draw_brush_set_list(self, layout: UILayout):
        BrushSetsList.draw_list(layout, self, 'brush_sets', 'active_brush_set_index')

    def draw_tarta_set_list(self, layout: UILayout):
        TartaSetList.draw_list(layout, self, 'tarta_sets', 'active_tarta_set_index')
