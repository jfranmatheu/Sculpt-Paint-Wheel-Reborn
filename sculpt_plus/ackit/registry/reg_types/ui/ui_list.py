from .base import BaseUI, UILayout
from ....globals import GLOBALS

import bpy
from bpy.types import UIList as BlUIList, Context, UILayout


class UIList(BaseUI):
    label: str

    @classmethod
    def tag_register(deco_cls) -> 'UIList':
        return super().tag_register(BlUIList, 'UL')

    @classmethod
    def draw_in_layout(cls, layout: UILayout, data, attr_coll: str, attr_index: str, rows: int = 5, list_id: str = ''):
        layout.template_list(
            cls.bl_idname, list_id,
            data, attr_coll,
            data, attr_index,
            rows=rows
        )

    def draw_item(self, context: Context, layout: UILayout, data, item, icon: str | int, active_data, active_propname: str, index: int, flt_flag):
        pass

    def draw_filter(self, context: Context, layout: UILayout):
        pass

    # def filter_items(self, context: Context, data, propname: str):
    #     pass
