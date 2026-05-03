"""Operators for tarta button CRUD actions."""

from bpy.props import IntProperty

from ..core.bl_types import OperatorAction
from ..pg.pg_create_tarta_button import CreateTartaButton
from ..pg.pg_wheel_storage import WheelStorage, WheelTartaSetStorage
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

    def action(self, context, event):
        wheel_storage: WheelTartaSetStorage = WheelStorage.get_by_mode(context)
        active_set = wheel_storage.active_tarta_set
        create = CreateTartaButton.get(context)

        button = active_set.buttons.add()
        button.name = create.name
        button.image_path = create.image_path
        button.type = create.type

        if create.type == "OPERATOR":
            button.popup_type = "NONE"
            if create.operator_type == "PRESET":
                expr = _resolve_preset_operator_expr(context, create.preset_operator)
            else:
                expr = create.custom_operator
            expr = _normalize_operator_expr(expr)
            op_id, payload = _split_operator_expr(expr)
            button.operator_id = op_id
            button.attr = payload
        elif create.type == "POPUP":
            button.attr = ""
            button.popup_type = create.popup_type
            if create.popup_type == "MENU":
                button.operator_id = create.preset_menu if create.menu_source == "PRESET" else create.custom_menu
            else:
                button.operator_id = create.preset_panel if create.panel_source == "PRESET" else create.custom_panel

        active_set.active_button_index = len(active_set.buttons) - 1


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
