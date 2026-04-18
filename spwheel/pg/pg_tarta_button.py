from bpy.props import EnumProperty, StringProperty

from ..core.bl_types import PropertyGroup


class WheelTartaButton(PropertyGroup):
    pg_parent = None

    name: StringProperty(name="Name", default="Custom")
    type: EnumProperty(
        name="Action Type",
        items=(
            ("OPERATOR", "Operator", "Run Python / preset operator"),
            ("POPUP", "Popup", "Open a menu or panel"),
        ),
    )
    popup_type: EnumProperty(
        name="Popup Kind",
        items=(
            ("NONE", "—", "Not used for operators"),
            ("MENU", "Menu", ""),
            ("PANEL", "Panel", ""),
        ),
        default="NONE",
    )
    attr: StringProperty(name="Payload", default="", maxlen=4096)
    image_path: StringProperty(name="Icon Path", default="", subtype="FILE_PATH")
