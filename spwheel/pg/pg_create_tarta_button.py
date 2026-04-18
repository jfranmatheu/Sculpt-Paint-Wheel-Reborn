from bpy.props import StringProperty, EnumProperty
from bpy.types import Context, UILayout

from ..core.bl_types import PropertyGroupRoot
from ..wheels.presets import preset_type_per_mode


def enum_preset_menus(self, context):
    if presets := preset_type_per_mode.get(context.mode, None):
        return [(a, b, c or "") for a, b, c in presets[0]]
    return [()]

def enum_preset_panels(self, context):
    if presets := preset_type_per_mode.get(context.mode, None):
        return [(a, b, c or "") for a, b, c in presets[1]]
    return [()]

def enum_preset_operators(self, context):
    if presets := preset_type_per_mode.get(context.mode, None):
        return [(a, b, c or "") for a, b, c in presets[2]]
    return [()]


class CreateTartaButton(PropertyGroupRoot.WINDOW_MANAGER):

    name: StringProperty(name="Name", default="Button")
    image_path: StringProperty(name="Icon Image", default="", subtype="FILE_PATH")

    type: EnumProperty(
        name="Type",
        items=(
            ("OPERATOR", "Operator", ""),
            ("POPUP", "Popup", ""),
        ),
    )
    operator_type: EnumProperty(
        name="Operator",
        items=(
            ("PRESET", "Preset", ""),
            ("CUSTOM", "Custom", ""),
        ),
        default="PRESET",
    )
    preset_operator: EnumProperty(name="Preset Operator", items=enum_preset_operators)
    custom_operator: StringProperty(
        name="Custom Code",
        default="bpy.ops.sculpt.brush_stroke()",
        maxlen=2048,
    )

    popup_type: EnumProperty(
        name="Popup",
        items=(
            ("MENU", "Menu", ""),
            ("PANEL", "Panel", ""),
        ),
        default="MENU",
    )
    menu_source: EnumProperty(
        name="Menu Source",
        items=(
            ("PRESET", "Preset", ""),
            ("CUSTOM", "Custom", ""),
        ),
        default="PRESET",
    )
    preset_menu: EnumProperty(name="Preset Menu", items=enum_preset_menus)
    custom_menu: StringProperty(name="Menu ID", default="VIEW3D_MT_sculpt", maxlen=256)

    panel_source: EnumProperty(
        name="Panel Source",
        items=(
            ("PRESET", "Preset", ""),
            ("CUSTOM", "Custom", ""),
        ),
        default="PRESET",
    )
    preset_panel: EnumProperty(name="Preset Panel", items=enum_preset_panels)
    custom_panel: StringProperty(
        name="Panel ID",
        default="VIEW3D_PT_tools_brush_settings_advanced",
        maxlen=256,
    )

    def draw_ui(self, context: Context, layout: UILayout) -> None:
        return super().draw_ui(context, layout)
