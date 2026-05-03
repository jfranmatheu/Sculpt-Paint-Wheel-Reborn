from bpy.types import Context, UILayout

from ...core.bl_types import PanelTypes
from ...pg.pg_wheel_storage import WheelStorage, WheelTartaSetStorage
from ...pg.pg_tarta_set import WheelTartaSet
from ...pg.pg_create_tarta_button import CreateTartaButton
from ...pg.pg_wm import PG_WM
from ...ui.lists.ul_tarta_button_list import TartaButtonList
from ...ops.op_tarta_set_list import OpTartaSetListAdd, OpTartaSetListRemove
from ...ops.op_tarta_button import OpTartaButtonAdd, OpTartaButtonMove, OpTartaButtonRemove


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
        row.prop(wheel_storage, "tarta_sets_enum", text="")
        row.popover(WheelTartaSetOptionsPopover.bl_idname, text="", icon='PROPERTIES')
        row.separator()
        row.operator(OpTartaSetListAdd.bl_idname, text="", icon='COLLECTION_NEW')

    def draw_button_list(self, active_tarta_set: WheelTartaSet, layout: UILayout):
        row = layout.row(align=True)
        TartaButtonList.draw_list(row, active_tarta_set, 'buttons', 'active_button_index')
        col = row.column(align=True)
        col.ui_units_x = 1
        sep_box = col.box()
        sep_box.scale_y = 0.5
        sep_box.label(text='', icon='BLANK1')
        col.operator(OpTartaButtonMove.bl_idname, text="", icon='TRIA_UP').direction = 1
        col.operator(OpTartaButtonMove.bl_idname, text="", icon='TRIA_DOWN').direction = -1
        col.separator()
        col.operator(OpTartaButtonRemove.bl_idname, text="", icon='REMOVE')

    def draw_create_button_section(self, create: CreateTartaButton, layout: UILayout):
        header, content = layout.panel('TEMP_PT_create_custom_button')
        header.label(text="Create Button (active set)", icon="PLUS")
        if not content:
            return

        box = content.column(align=True)
        box.use_property_split = True
        box.use_property_decorate = False
        box.label(text="Create :", icon="PROPERTIES")
        box.separator()

        sett = box.box()
        sett.prop(create, 'name', text="Name")
        sett.prop(create, 'image_path', text="Image Path")
        sett.prop(create, 'type', text="Type")

        if create.type == 'POPUP':
            sett.prop(create, 'popup_type', text="Pop-up Type")
            if create.popup_type == 'MENU':
                sett.prop(create, 'menu_source', text="Use")
                if create.menu_source == 'PRESET':
                    sett.prop(create, 'preset_menu', text="Preset Menu")
                else:
                    sett.prop(create, 'custom_menu', text="Menu ID")
            else:
                sett.prop(create, 'panel_source', text="Use")
                if create.panel_source == 'PRESET':
                    sett.prop(create, 'preset_panel', text="Preset Panel")
                else:
                    sett.prop(create, 'custom_panel', text="Panel ID")
        elif create.type == 'OPERATOR':
            sett.prop(create, 'operator_type', text="Use")
            if create.operator_type == 'PRESET':
                sett.prop(create, 'preset_operator', text="Preset Operator")
            else:
                sett.prop(create, 'custom_operator', text="Operator")
                sett.label(text="Example: paint.mask_flood_fill#mode='INVERT'")

        box.operator(OpTartaButtonAdd.bl_idname, text="Create Button")

    def draw_ui(self, context: Context, layout: UILayout):
        wheel_storage: WheelTartaSetStorage = WheelStorage.get_by_mode(context)
        create: CreateTartaButton = CreateTartaButton.get(context)

        main = layout.column()
        lists_col = main.column(align=True)
        self.draw_set_selector_row(wheel_storage, lists_col)
        
        wm_props = PG_WM.get(context)
        print("wm_props:", wm_props)
        sep_row = lists_col.row(align=True)
        sep_row.scale_y = 0.1
        sep_row.prop(wm_props, "sep_color_custom_buttons_set", text="")

        if active_tarta_set := wheel_storage.active_tarta_set:
            self.draw_button_list(active_tarta_set, lists_col)
            self.draw_create_button_section(create, main)
        else:
            main.box().label(text="No set selected", icon="INFO")
            self.draw_create_button_section(create, main)
