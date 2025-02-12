import bpy
from bpy.types import UILayout, Context

from .menu import Menu


class PieMenu(Menu):

    @classmethod
    def popup(cls) -> None:
        bpy.ops.wm.call_menu_pie('INVOKE_DEFAULT', name=cls.bl_idname)

    @classmethod
    def draw_in_layout(cls, layout: UILayout, label: str = None, icon: str = 'NONE'):
        raise NotImplementedError
    
    def draw(self, context: Context):
        self.draw_ui(context, self.layout.menu_pie())
