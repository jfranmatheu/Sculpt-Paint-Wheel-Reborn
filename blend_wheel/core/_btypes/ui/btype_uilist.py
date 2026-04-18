from bpy.types import UIList, UILayout, Context

from .btype_ui_base import BType_UICommon


class BType_UIList(BType_UICommon, UIList):
    bl_idname: str

    @classmethod
    def draw_list(cls, layout: UILayout, data: Context, attr_name: str, active_attr_name: str):
        layout.template_list(
            cls.bl_idname,
            "",
            data,
            attr_name,
            data,
            active_attr_name,
            rows=min(8, max(4, len(getattr(data, attr_name)))),
        )
