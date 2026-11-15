from typing import Optional
from bpy.types import Menu, UILayout, Context, Event

from .btype_ui_base import BType_UICommon


class BType_Menu(BType_UICommon, Menu):
    # Must be a valid icon enum name: None fails RNA class validation (Blender 5.2+).
    bl_icon: Optional[str | int] = 'NONE'

    @classmethod
    def draw_as_menu(cls, layout: UILayout, title: Optional[str] = None, icon: Optional[str | int] = None):
        icon = icon or cls.bl_icon
        layout.menu(cls.bl_idname, title=title or cls.bl_label, icon=icon if isinstance(icon, str) else 'NONE', icon_value=icon if isinstance(icon, int) else 0)

    @classmethod
    def draw_menu_contents(cls, layout: UILayout):
        layout.menu_contents(cls.bl_idname)

    @classmethod
    def invoke_popup_menu(cls, context: Context, title: Optional[str] = None, icon: Optional[str] = None):
        icon = icon or cls.bl_icon
        context.window_manager.popup_menu(lambda menu, context: cls.draw_ui(context, menu.layout), title=title or cls.bl_label, icon=icon if isinstance(icon, str) else 'NONE')


class BType_MenuPie(BType_Menu):

    def draw(self, context: Context, layout: UILayout):
        menu_pie = layout.menu_pie()
        self.draw_ui(context, menu_pie)

    @classmethod
    def popup_menu_pie(cls, context: Context, event: Event, *, title: Optional[str] = None, icon: Optional[str] = None):
        icon = icon or cls.bl_icon
        context.window_manager.popup_menu_pie(event, lambda menu, context: cls.draw_ui(context, menu.layout), title=title or cls.bl_label, icon=icon if isinstance(icon, str) else 'NONE')
