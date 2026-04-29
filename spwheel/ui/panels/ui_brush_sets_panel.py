from bpy.types import Context, UILayout

from ...core.bl_types import PanelTypes
from ...prefs import BlendWheelPrefs, WheelPrefs
from ...pg.pg_wheel_storage import WheelStorage, SculptPaintWheelStorage
from ...ops.op_brush_set_list import OpBrushSetListAdd, OpBrushSetListRemove, OpBrushSetListMove
from ...ui.lists.ul_brush_sets_list import BrushSetsList



class WheelBrushSetsPanel(PanelTypes.VIEW_3D_SIDEBAR):
    bl_context = ".paint_common"

    bl_label = 'Brush Sets'
    bl_order = 1

    def draw_ui(self, context: Context, layout: UILayout):
        wheel_storage: SculptPaintWheelStorage = WheelStorage.get(context)

        row = layout.row()
        BrushSetsList.draw_list(row, wheel_storage, 'brush_sets', 'active_brush_set_index')
        col = row.column(align=True)
        col.operator(OpBrushSetListAdd.bl_idname, text="", icon='ADD')
        col.operator(OpBrushSetListRemove.bl_idname, text="", icon='REMOVE')
        col.separator()
        col.operator(OpBrushSetListMove.bl_idname, text="", icon='TRIA_UP').direction = 1
        col.operator(OpBrushSetListMove.bl_idname, text="", icon='TRIA_DOWN').direction = -1
        
        if active_brush_set := wheel_storage.active_brush_set:
            pass
