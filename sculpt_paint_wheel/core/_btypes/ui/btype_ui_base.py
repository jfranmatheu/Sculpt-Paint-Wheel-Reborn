from typing import Tuple
from bpy.types import Context, UILayout

from .._base import BType


class BType_UICommon(BType):
    layout: UILayout

    def draw(self, context: Context) -> None:
        self.draw_ui(context, self.layout)

    @classmethod
    def draw_ui(cls, context: Context, layout: UILayout):
        pass


class BType_UIExtra(BType_UICommon):
    def draw_section(self, layout: UILayout, title: str, icon: str | int = 'NONE', align_content: bool = True) -> Tuple[UILayout, UILayout]:
        col = layout.column(align=True)
        title_box = col.box().row()
        title_box.label(text=title, icon=icon)
        content_box = col.box().column(align=align_content)
        return title_box, content_box
