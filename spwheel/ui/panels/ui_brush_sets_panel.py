from bpy.types import Context, UILayout

from ...core.bl_types import PanelTypes
from ...pg.pg_wheel_storage import WheelStorage, SculptPaintWheelStorage
from ...pg.pg_brush_set import BrushSet
from ...pg.pg_wm import PG_WM
from ...ops.op_brush_set_list import OpBrushSetListAdd, OpBrushSetListRemove
from ...ops.op_brush_list import OpBrushListAdd, OpBrushListRemove, OpBrushListMove
from ...ui.lists.ul_brush_metadata_list import BrushMetadataList



class WheelBrushSetOptionsPopover(PanelTypes.POPOVER):
    bl_label = "Brush Set Options"

    def draw_ui(self, context: Context, layout: UILayout):
        wheel_storage: SculptPaintWheelStorage = WheelStorage.get_by_mode(context)
        active_brush_set = wheel_storage.active_brush_set
        if active_brush_set is None:
            layout.label(text="No active set", icon="INFO")
            return
        layout.prop(active_brush_set, "name", text="Name")
        layout.separator()
        layout.alert = True
        layout.operator(OpBrushSetListRemove.bl_idname, text="Remove Set", icon="TRASH")


class WheelBrushSetsPanel(PanelTypes.VIEW_3D_SIDEBAR):
    bl_context = ".paint_common"

    bl_label = 'Brush Sets'
    bl_order = 1

    @classmethod
    def poll(cls, context: Context) -> bool:
        # Weight modes does not use brush sets (yet).
        return 'WEIGHT' not in context.mode

    def draw_set_selector_row(self, wheel_storage: SculptPaintWheelStorage, layout: UILayout):
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.prop(wheel_storage, "brush_sets_enum", text="")
        _row = row.row(align=True)
        _row.scale_x = 1.25
        _row.popover(WheelBrushSetOptionsPopover.bl_idname, text="", icon='PROPERTIES')
        row.separator()
        _row = row.row(align=True)
        _row.scale_x = 1.25
        _row.operator(OpBrushSetListAdd.bl_idname, text="", icon='COLLECTION_NEW')

    def draw_brush_items_list(self, active_brush_set: BrushSet, layout: UILayout):
        row = layout.row(align=True)
        BrushMetadataList.draw_list(row, active_brush_set, 'items', 'active_item_index')
        col = row.column(align=True)
        col.ui_units_x = 1
        sep_box = col.box()
        sep_box.scale_y = 0.5
        sep_box.label(text='', icon='BLANK1')
        col.operator(OpBrushListAdd.bl_idname, text="", icon='ADD')
        col.operator(OpBrushListRemove.bl_idname, text="", icon='REMOVE')
        col.separator()
        col.operator(OpBrushListMove.bl_idname, text="", icon='TRIA_UP').direction = 1
        col.operator(OpBrushListMove.bl_idname, text="", icon='TRIA_DOWN').direction = -1

    def draw_ui(self, context: Context, layout: UILayout):
        wheel_storage: SculptPaintWheelStorage = WheelStorage.get_by_mode(context)
        lists_col = layout.column(align=True)
        self.draw_set_selector_row(wheel_storage, lists_col)
        
        wm_props = PG_WM.get(context)
        sep_row = lists_col.row(align=True)
        sep_row.scale_y = 0.1
        sep_row.prop(wm_props, "sep_color_brush_set", text="")

        if active_brush_set := wheel_storage.active_brush_set:
            self.draw_brush_items_list(active_brush_set, lists_col)
