from bpy.types import Context, UILayout

from ...core.bl_types import PanelTypes
from ...pg.pg_wheel_storage import WheelStorage, WheelTartaSetStorage
from ...pg.pg_tarta_set import WheelTartaSet
from ...pg.pg_create_tarta_button import CreateTartaButton
from ...ui.lists.ul_tarta_set_list import TartaSetList
from ...ui.lists.ul_tarta_button_list import TartaButtonList
from ...ops.op_tarta_set_list import OpTartaSetListAdd, OpTartaSetListRemove, OpTartaSetListMove
from ...ops.op_tarta_button import OpTartaButtonAdd


class WheelTartaButtonsPanel(PanelTypes.VIEW_3D_SIDEBAR):
    bl_context = ".paint_common"

    bl_label = 'Custom Button Sets'
    bl_order = 2
    
    def draw_set_list(self, wheel_storage: WheelTartaSetStorage, layout: UILayout):
        row = layout.row()
        TartaSetList.draw_list(row, wheel_storage, 'tarta_sets', 'active_tarta_set_index')
        col = row.column(align=True)
        col.operator(OpTartaSetListAdd.bl_idname, text="", icon='ADD')
        col.operator(OpTartaSetListRemove.bl_idname, text="", icon='REMOVE')
        col.separator()
        col.operator(OpTartaSetListMove.bl_idname, text="", icon='TRIA_UP').direction = 1
        col.operator(OpTartaSetListMove.bl_idname, text="", icon='TRIA_DOWN').direction = -1

    def draw_button_list(self, active_tarta_set: WheelTartaSet, layout: UILayout):
        TartaButtonList.draw_list(layout, active_tarta_set, 'buttons', 'active_button_index')

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
        lists_row = main.row()

        self.draw_set_list(wheel_storage, lists_row)

        if active_tarta_set := wheel_storage.active_tarta_set:
            header, content = layout.panel('TEMP_PT_tarta_buttons')
            header.label(text=f'Buttons for {active_tarta_set.name}')
            if content:
                self.draw_button_list(active_tarta_set, content)
            self.draw_create_button_section(create, main)
        else:
            main.box().label(text="No set selected", icon="INFO")
