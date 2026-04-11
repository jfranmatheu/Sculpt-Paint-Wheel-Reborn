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
    wheel_colpk_linked_preview: BoolProperty(
        name="Color pickers: live HSV preview",
        description=(
            "When on, each ring tints by the current hue/saturation/value together. "
            "When off, the hue ring uses full saturation and value, the saturation arc uses full value, "
            "and the value arc uses full saturation (easier to read each channel in isolation)"
        ),
        default=True,
    )

    # -- RMB sculpt gesture (click-drag right mouse in Sculpt) --
    rmb_gesture_overlay_radius: IntProperty(
        name="Overlay Ring Radius",
        description="Pixel radius of the on-screen rings while adjusting size or strength",
        min=80, max=400, default=180,
    )
    rmb_gesture_invert: BoolProperty(
        name="Invert Gesture Axes",
        description="Swap which drag axis controls brush size vs strength",
        default=False,
    )
    rmb_gesture_preview: EnumProperty(
        name="Gesture Overlay",
        description="Visual style while dragging (size / strength rings)",
        items=(
            ("SIMPLE", "Simple", "Minimal rings"),
            ("PREVIEW", "Preview", "Extra ring emphasis for strength display"),
        ),
        default="SIMPLE",
    )

    def draw_ui(self, context: Context, layout: UILayout):
        layout.label(text="Sculpt+ Preferences")

        box = layout.box()
        box.label(text="Sculpt Wheel", icon="BRUSH_DATA")
        box.label(
            text="Brush sets load automatically when the add-on enables (first run may build a cache)."
        )
        box.label(
            text="Pick the active set in the Sidebar (Sculpt mode) and use Reload there to rescan libraries."
        )
        col = box.column(align=True)
        col.prop(self, "wheel_radius")
        col.prop(self, "wheel_icon_scale")
        col.prop(self, "wheel_show_names")
        col.separator()
        col.prop(self, "wheel_keep_open")
        col.prop(self, "wheel_on_release_select")
        col.prop(self, "wheel_colpk_linked_preview")

        box = layout.box()
        box.label(text="RMB Brush Gesture", icon="MOUSE_RMB")
        box.label(
            text="In Sculpt mode: right-click and drag (add-on keymap) to tweak brush size and strength."
        )
        col = box.column(align=True)
        col.prop(self, "rmb_gesture_overlay_radius")
        col.prop(self, "rmb_gesture_invert")
        col.prop(self, "rmb_gesture_preview")
