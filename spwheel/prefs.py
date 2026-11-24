from bpy.props import (
    PointerProperty
)
from bpy.types import Context, UILayout

from .core import bl_types
from .pg.pg_wheel_prefs import WheelPrefs
# from .pg.pg_wheel_storage import WheelStorage


SUPPORT_URL = "https://superhivemarket.com/products/sculpt-paint-wheel"


class BlendWheelPrefs(bl_types.AddonPreferences):

    wheel: PointerProperty(type=WheelPrefs)

    def draw_ui(self, context: Context, layout: UILayout):
        self.draw_support_ui(layout)
        layout.separator()
        layout.operator(
            "spwheel.opsavebackupaddonpreferences",
            text="Save/Backup Addon Preferences",
            icon='EXPORT'
        )
        layout.separator()
        # header, content = self.draw_section(layout, "Wheel Preferences", '', align_content=False, content_layout_type='GRID_FLOW')
        self.wheel.draw_preferences_ui(context, layout.column())

    @staticmethod
    def draw_support_ui(layout: UILayout):
        box = layout.box()
        row = box.row()
        row.label(text="Support Development", icon='FUND')
        col = box.column(align=True)
        col.label(text="Sculpt-Paint Wheel is made by an independent developer.")
        col.label(text="If it speeds up your workflow, buying it on Superhive funds new features and fixes.")
        row = box.row()
        row.scale_y = 1.6
        op = row.operator("wm.url_open", text="Support on Superhive ♥", icon='FUND')
        op.url = SUPPORT_URL
