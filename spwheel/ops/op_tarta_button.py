import bpy
"""Operators for tarta button CRUD actions."""

from bpy.props import EnumProperty, IntProperty, StringProperty

from ..core.bl_types import OperatorAction
from ..pg.pg_wheel_storage import WheelStorage, WheelTartaSetStorage
from ..pg.pg_tarta_set import MAX_TARTA_BUTTONS
from ..wheels.presets import preset_type_per_mode


class OpPollActiveSet:
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        wheel_storage = WheelStorage.get_by_mode(context)
        if wheel_storage is None or wheel_storage.active_tarta_set is None:
            return "No active Custom Buttons set"
        return True


class OpPollActiveButton(OpPollActiveSet):
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        is_valid = super().poll_operator(context)
        if is_valid is not True:
            return is_valid
        active_set = WheelStorage.get_by_mode(context).active_tarta_set
        idx = active_set.active_button_index
        if idx < 0 or idx >= len(active_set.buttons):
            return "No active button"
        return True


def _split_operator_expr(expr: str) -> tuple[str, str]:
    if not expr:
        return "", ""
    op_id, sep, payload = expr.partition("#")
    if not sep:
        return op_id.strip(), ""
    return op_id.strip(), payload.strip()


def _normalize_operator_expr(expr: str) -> str:
    expr = (expr or "").strip()
    if not expr:
        return ""
    if expr.startswith("bpy.ops."):
        expr = expr[len("bpy.ops."):]
    if "#" in expr:
        return expr
    if "(" in expr and expr.endswith(")"):
        op_id, _, args_part = expr.partition("(")
        args = args_part[:-1].strip()
        return f"{op_id.strip()}#{args}" if args else op_id.strip()
    return expr


def _resolve_preset_operator_expr(context, preset_key: str) -> str:
    presets = preset_type_per_mode.get(context.mode, None)
    if not presets:
        return preset_key
    preset_ops = presets[2]
    for op_id, _name, op_expr in preset_ops:
        if op_id != preset_key:
            continue
        if op_expr:
            return op_expr
        return op_id
    return preset_key


class OpTartaButtonAdd(OperatorAction, OpPollActiveSet):
    """Create a new button in the active custom-button set."""
    bl_label = "Add Button"

    @classmethod
    def poll_operator(cls, context) -> bool | str:
        is_valid = super().poll_operator(context)
        if is_valid is not True:
            return is_valid
        if len(WheelStorage.get_by_mode(context).active_tarta_set.buttons) >= MAX_TARTA_BUTTONS:
            return f"A set can have up to {MAX_TARTA_BUTTONS} buttons"
        return True

    def enum_preset_menus(self, context):
        if context is not None and (presets := preset_type_per_mode.get(context.mode, None)):
            # Skip UI types that don't exist in the running Blender version.
            return [(a, b, c or "") for a, b, c in presets[0] if hasattr(bpy.types, a)]
        return [("VIEW3D_MT_sculpt", "Sculpt Menu", "")]

    def enum_preset_panels(self, context):
        if context is not None and (presets := preset_type_per_mode.get(context.mode, None)):
            return [(a, b, c or "") for a, b, c in presets[1] if hasattr(bpy.types, a)]
        return [("VIEW3D_PT_tools_brush_settings_advanced", "Advanced Settings", "")]

    def enum_preset_operators(self, context):
        if context is not None and (presets := preset_type_per_mode.get(context.mode, None)):
            return [(a, b, c or "") for a, b, c in presets[2]]
        return [("_MASK_INVERT", "Invert Mask", "")]

    name: StringProperty(name="Name", default="Button")
    image_path: StringProperty(name="Icon Image", default="", subtype="FILE_PATH")

    type: EnumProperty(
        name="Type",
        items=(
            ("OPERATOR", "Operator", ""),
            ("POPUP", "Popup", ""),
        ),
        default="OPERATOR",
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
        name="Custom Operator",
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

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "image_path")
        layout.prop(self, "type")

        if self.type == "POPUP":
            layout.prop(self, "popup_type")
            if self.popup_type == "MENU":
                layout.prop(self, "menu_source", text="Use")
                if self.menu_source == "PRESET":
                    layout.prop(self, "preset_menu")
                else:
                    layout.prop(self, "custom_menu")
            else:
                layout.prop(self, "panel_source", text="Use")
                if self.panel_source == "PRESET":
                    layout.prop(self, "preset_panel")
                else:
                    layout.prop(self, "custom_panel")
        else:
            layout.prop(self, "operator_type", text="Use")
            if self.operator_type == "PRESET":
                layout.prop(self, "preset_operator")
            else:
                layout.prop(self, "custom_operator")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        wheel_storage: WheelTartaSetStorage = WheelStorage.get_by_mode(context)
        active_set = wheel_storage.active_tarta_set
        if active_set is None:
            self.report({"ERROR"}, "No active Custom Buttons set")
            return self.OpReturn.CANCEL

        button = active_set.buttons.add()
        button.name = self.name.strip() or "Button"
        button.image_path = self.image_path
        button.type = self.type

        if self.type == "OPERATOR":
            button.popup_type = "NONE"
            if self.operator_type == "PRESET":
                expr = _resolve_preset_operator_expr(context, self.preset_operator)
            else:
                expr = self.custom_operator
            expr = _normalize_operator_expr(expr)
            op_id, payload = _split_operator_expr(expr)
            if not op_id:
                active_set.buttons.remove(len(active_set.buttons) - 1)
                self.report({"ERROR"}, "Invalid operator id")
                return self.OpReturn.CANCEL
            button.operator_id = op_id
            button.attr = payload
        elif self.type == "POPUP":
            button.attr = ""
            button.popup_type = self.popup_type
            if self.popup_type == "MENU":
                button.operator_id = self.preset_menu if self.menu_source == "PRESET" else self.custom_menu
            else:
                button.operator_id = self.preset_panel if self.panel_source == "PRESET" else self.custom_panel
            if not button.operator_id:
                active_set.buttons.remove(len(active_set.buttons) - 1)
                self.report({"ERROR"}, "Popup target id cannot be empty")
                return self.OpReturn.CANCEL

        active_set.active_button_index = len(active_set.buttons) - 1
        return self.OpReturn.FINISH


class OpTartaButtonRemove(OperatorAction, OpPollActiveButton):
    """Remove active button from the active custom-button set."""
    bl_label = "Remove Button"

    def action(self, context, event):
        active_set = WheelStorage.get_by_mode(context).active_tarta_set
        idx = active_set.active_button_index
        active_set.buttons.remove(idx)
        if len(active_set.buttons) == 0:
            active_set.active_button_index = -1
        else:
            active_set.active_button_index = min(idx, len(active_set.buttons) - 1)


class OpTartaButtonMove(OperatorAction, OpPollActiveButton):
    """Move active button up/down in the active custom-button set."""
    bl_label = "Move Button"

    direction: IntProperty(
        name="Direction",
        description="The direction to move the active button",
        default=0,
        min=-1,
        max=1,
    )

    def action(self, context, event):
        active_set = WheelStorage.get_by_mode(context).active_tarta_set
        count = len(active_set.buttons)
        if count <= 1:
            return
        src = active_set.active_button_index
        if self.direction == 1:
            dst = (src - 1 + count) % count
        elif self.direction == -1:
            dst = (src + 1) % count
        else:
            return
        active_set.buttons.move(src, dst)
        active_set.active_button_index = dst
