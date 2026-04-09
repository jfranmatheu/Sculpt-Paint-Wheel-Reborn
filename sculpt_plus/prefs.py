from bpy.props import BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty
from bpy.types import Context, UILayout

from .core import bl_types
from .sculpt_wheel.data import SculptWheelStorage


class SculptPlusPreferences(bl_types.AddonPreferences):

    sculpt_wheel_storage: PointerProperty(type=SculptWheelStorage)

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
    wheel_gesture_pad_radius: IntProperty(
        name="Gesture Pad Radius",
        description="Center circle size for size/strength drag (picker mode)",
        min=20, max=80, default=36,
    )
    wheel_gesture_invert: BoolProperty(
        name="Invert Gesture Axes",
        description="Swap which axis controls brush size vs strength",
        default=False,
    )
    wheel_gesture_preview: EnumProperty(
        name="Gesture Overlay",
        description="Show extra rings while adjusting size or strength",
        items=(
            ('SIMPLE', "Simple", "Minimal center pad"),
            ('PREVIEW', "Preview", "Show value rings like the legacy wheel"),
        ),
        default='SIMPLE',
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
        col.separator()
        col.prop(self, "wheel_gesture_pad_radius")
        col.prop(self, "wheel_gesture_invert")
        col.prop(self, "wheel_gesture_preview")
