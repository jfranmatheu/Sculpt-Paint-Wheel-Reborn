from bpy.types import Context, UILayout

from ...core.bl_types import PanelTypes
from ...prefs import BlendWheelPrefs, WheelPrefs


class WheelBrushSetsPanel(PanelTypes.VIEW_3D_SIDEBAR):
    bl_context = ".paint_common"

    bl_label = 'Brush Sets'
    bl_order = 1

    def draw_ui(self, context: Context, layout: UILayout):
        wheel_data: WheelPrefs = WheelPrefs.get(context)
        active_brush_set = wheel_data.active_brush_set

        if active_brush_set is None:
            layout.label(text="Initialize Default Toolset")
            return

        wheel_data.draw_brush_set_list(layout)
