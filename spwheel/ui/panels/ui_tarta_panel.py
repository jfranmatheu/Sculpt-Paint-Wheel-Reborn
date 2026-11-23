from bpy.types import Context, UILayout

from ...core.bl_types import PanelTypes
from ...pg.pg_wheel_storage import WheelStorage, WheelTartaSetStorage
from ...pg.pg_tarta_set import WheelTartaSet
from ...pg.pg_wm import PG_WM
from ...ui.lists.ul_tarta_button_list import TartaButtonList
from ...ops.op_tarta_set_list import OpTartaSetListAdd, OpTartaSetListRemove
from ...ops.op_tarta_button import OpTartaButtonAdd, OpTartaButtonMove, OpTartaButtonRemove, OpTartaButtonScriptEdit


class WheelTartaSetOptionsPopover(PanelTypes.POPOVER):
    bl_label = "Tarta Set Options"

    def draw_ui(self, context: Context, layout: UILayout):
        wheel_storage: WheelTartaSetStorage = WheelStorage.get_by_mode(context)
        active_tarta_set = wheel_storage.active_tarta_set
        if active_tarta_set is None:
            layout.label(text="No active set", icon="INFO")
            return
        layout.prop(active_tarta_set, "name", text="Name")
        layout.separator()
        layout.alert = True
        layout.operator(OpTartaSetListRemove.bl_idname, text="Remove Set", icon="TRASH")


class WheelTartaButtonsPanel(PanelTypes.VIEW_3D_SIDEBAR):
    bl_context = ".paint_common"

    bl_label = 'Custom Button Sets'
    bl_order = 2
    
    def draw_set_selector_row(self, wheel_storage: WheelTartaSetStorage, layout: UILayout):
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.prop(wheel_storage, "tarta_sets_enum", text="")
        _row = row.row(align=True)
        _row.scale_x = 1.25
        _row.popover(WheelTartaSetOptionsPopover.bl_idname, text="", icon='PROPERTIES')
        row.separator()
        _row = row.row(align=True)
        _row.scale_x = 1.25
        _row.operator(OpTartaSetListAdd.bl_idname, text="", icon='COLLECTION_NEW')

    def draw_button_list(self, active_tarta_set: WheelTartaSet, layout: UILayout):
        row = layout.row(align=True)
        TartaButtonList.draw_list(row, active_tarta_set, 'buttons', 'active_button_index')
        col = row.column(align=True)
        col.ui_units_x = 1
        sep_box = col.box()
        sep_box.scale_y = 0.5
        sep_box.label(text='', icon='BLANK1')
        col.operator(OpTartaButtonAdd.bl_idname, text="", icon='ADD')
        col.operator(OpTartaButtonRemove.bl_idname, text="", icon='REMOVE')
        col.separator()
        col.operator(OpTartaButtonMove.bl_idname, text="", icon='TRIA_UP').direction = 1
        col.operator(OpTartaButtonMove.bl_idname, text="", icon='TRIA_DOWN').direction = -1

        idx = active_tarta_set.active_button_index
        if 0 <= idx < len(active_tarta_set.buttons) and active_tarta_set.buttons[idx].is_script:
            layout.operator(OpTartaButtonScriptEdit.bl_idname, text="Edit Script", icon='TEXT')

    def draw_ui(self, context: Context, layout: UILayout):
        wheel_storage: WheelTartaSetStorage = WheelStorage.get_by_mode(context)

        main = layout.column()
        lists_col = main.column(align=True)
        self.draw_set_selector_row(wheel_storage, lists_col)
        
        wm_props = PG_WM.get(context)
        sep_row = lists_col.row(align=True)
        sep_row.scale_y = 0.15
        sep_row.prop(wm_props, "sep_color_custom_buttons_set", text="")

        if active_tarta_set := wheel_storage.active_tarta_set:
            self.draw_button_list(active_tarta_set, lists_col)
        else:
            main.box().label(text="No set selected", icon="INFO")
