from bpy.props import (
    PointerProperty
)
from bpy.types import Context, UILayout

from .core import bl_types
from .pg.pg_wheel_prefs import WheelPrefs
# from .pg.pg_wheel_storage import WheelStorage


class BlendWheelPrefs(bl_types.AddonPreferences):

    wheel: PointerProperty(type=WheelPrefs)

    def draw_ui(self, context: Context, layout: UILayout):
        # header, content = self.draw_section(layout, "Wheel Preferences", '', align_content=False, content_layout_type='GRID_FLOW')
        self.wheel.draw_preferences_ui(context, layout.grid_flow())
