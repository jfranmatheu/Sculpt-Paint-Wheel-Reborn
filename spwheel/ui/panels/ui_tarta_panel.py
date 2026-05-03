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
            self.draw_create_button_section(create, main)

        return

        '''if len(buttons) == 0:
            from ..spw_io import check_sculpt_custom_buttons
            if check_sculpt_custom_buttons():
                layout.operator('sculpt.wheel_load_custom_buttons', text="Load Buttons")
            else:
                layout.operator('sculpt.wheel_load_custom_buttons', text="Initialize Default Buttons")
            layout.scale_y = 2.5
            return

        if len(buttons) != 0:
            box = layout.box().column(align=True)
            box.use_property_split = True
            box.use_property_decorate = False
            box.label(text="List :", icon="OUTLINER")
            box.separator()
        for i, b in enumerate(buttons):
            row = box.row(align=True)
            # row.prop(b, 'show_settings', text="", icon='TRIA_RIGHT' if not b.show_settings else 'TRIA_DOWN')
            row.prop(b, 'name', text="")
            row.operator('sculpt.wheel_remove_custom_button', text="", icon="X").index = i
            if b.show_settings:
                sett = box.box()
                sett.prop(b, 'image_path', text="Image Path")
                #sett.template_icon_view(context.window_manager, "sculpt_wheel_icons")
                sett.prop(b, 'type', text="Type")
                if b.type == 'POPUP':
                    sett.prop(b, 'popup_type', text="Pop-up Type")
                    _row = sett.row()
                    _row.prop(b, 'as_attribute', text="Use...", expand=True)
                    if b.as_attribute == 'PRESET':
                        if b.popup_type == 'MENU':
                            sett.prop(b, 'preset_menu', text="Presets")
                        elif b.popup_type == 'PANEL':
                            sett.prop(b, 'preset_panel', text="Presets")
                        elif b.popup_type == 'PIE_MENU':
                            # sett.prop(b, 'popup_type', text="Identifier") # TODO: Some presets for pie menus?
                            sett.alert = True
                            sett.label(text="No presets for pie menus :(")
                    elif b.as_attribute == 'CUSTOM':
                        sett.prop(b, 'custom_identifier', text="Idname")
                elif b.type == 'OPERATOR':
                    _row = sett.row()
                    _row.prop(b, 'as_attribute', text="Use...", expand=True)
                    if b.as_attribute == 'PRESET':
                        sett.prop(b, 'preset_operator', text="Presets")
                    elif b.as_attribute == 'CUSTOM':
                        sett.prop(b, 'custom_identifier', text="Operator")
                        sett.label(text="Example: bpy.ops.object.voxel_remesh()")
                elif b.type == 'TOGGLE':
                    sett.alert = True
                    sett.label(text="Work in progress...")

                    #_row = sett.row()
                    #_row.prop(create, 'as_attribute', text="Use...", expand=True)
                    #if create.as_attribute == 'PRESET':
                    #    sett.label(text="No presets for toggles :(")
                    #elif create.as_attribute == 'CUSTOM':
                    #    sett.prop(create, 'custom_identifier', text="Property Name")

                box.separator()'''

        header, content = main.panel('TEMP_PT_create_custom_button')
        header.label(text="Create Button (active set)", icon="PLUS")

        box = content.column(align=True)
        box.use_property_split = True
        box.use_property_decorate = False
        box.label(text="Create :", icon="PROPERTIES")
        box.separator()
        sett = box.box()
        sett.prop(create, 'name', text="Name")
        sett.prop(create, 'image_path', text="Image Path")
        #sett.template_icon_view(context.window_manager, "sculpt_wheel_icons")
        sett.prop(create, 'type', text="Type")
        if create.type == 'POPUP':
            sett.prop(create, 'popup_type', text="Pop-up Type")
            _row = sett.row()
            _row.prop(create, 'as_attribute', text="Use...", expand=True)
            if create.as_attribute == 'PRESET':
                if create.popup_type == 'MENU':
                    sett.prop(create, 'preset_menu', text="Presets")
                elif create.popup_type == 'PANEL':
                    sett.prop(create, 'preset_panel', text="Presets")
                elif create.popup_type == 'PIE_MENU':
                    # sett.prop(b, 'popup_type', text="Identifier") # TODO: Some presets for pie menus?
                    sett.alert = True
                    sett.label(text="No presets for pie menus :(")
            elif create.as_attribute == 'CUSTOM':
                sett.prop(create, 'custom_identifier', text="Idname")
        elif create.type == 'OPERATOR':
            _row = sett.row()
            _row.prop(create, 'as_attribute', text="Use...", expand=True)
            if create.as_attribute == 'PRESET':
                sett.prop(create, 'preset_operator', text="Presets")
            elif create.as_attribute == 'CUSTOM':
                sett.prop(create, 'custom_identifier', text="Operator")
                sett.label(text="Example: bpy.ops.object.voxel_remesh()")
        # elif create.type == 'TOGGLE':
        #     sett.alert = True
        #     sett.label(text="Work in progress...")

        box.operator('sculpt.wheel_add_custom_button', text="Create Button")
