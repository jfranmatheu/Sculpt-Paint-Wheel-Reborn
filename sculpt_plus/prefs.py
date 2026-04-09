from bpy.props import BoolProperty, IntProperty, FloatProperty
from bpy.types import Context, UILayout

from .core import bl_types


class SculptPlusPreferences(bl_types.AddonPreferences):

    # -- Sculpt Wheel settings --
    wheel_radius: IntProperty(
        name="Wheel Radius",
        description="Pixel radius of the sculpt wheel",
        min=100, max=400, default=180,
    )
    wheel_show_names: BoolProperty(
        name="Show Brush Names",
        description="Display brush names below each slot",
        default=False,
    )
    wheel_icon_scale: FloatProperty(
        name="Icon Scale",
        description="Scale factor for brush preview icons inside slots",
        min=0.4, max=1.0, default=0.92,
    )
    wheel_keep_open: BoolProperty(
        name="Keep Open",
        description="First key release does not close the wheel; click to select then press key again to close",
        default=False,
    )
    wheel_on_release_select: BoolProperty(
        name="Select on Release",
        description="Select the hovered brush when the trigger key is released instead of clicking",
        default=False,
    )

    def draw_ui(self, context: Context, layout: UILayout):
        layout.label(text="Sculpt+ Preferences")

        box = layout.box()
        box.label(text="Sculpt Wheel", icon='BRUSH_DATA')
        col = box.column(align=True)
        col.prop(self, "wheel_radius")
        col.prop(self, "wheel_icon_scale")
        col.prop(self, "wheel_show_names")
        col.separator()
        col.prop(self, "wheel_keep_open")
        col.prop(self, "wheel_on_release_select")
