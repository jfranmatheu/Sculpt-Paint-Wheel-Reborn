from bpy.props import CollectionProperty, IntProperty, StringProperty

from ..core.bl_types import PropertyGroup
from .pg_tarta_button import WheelTartaButton
from ..ui.lists.ul_tarta_button_list import TartaButtonList


class WheelTartaSet(PropertyGroup):
    pg_parent = None

    name: StringProperty(
        name="Set name",
        default="Button set",
        maxlen=256
    )
    buttons: CollectionProperty(type=WheelTartaButton)
    active_button_index: IntProperty(
        name="Active Button Index",
        description="Index of the active button",
        default=-1,
    )

    def draw_list(self, layout: UILayout):
        TartaButtonList.draw_list(layout, self, 'buttons', 'active_button_index')
