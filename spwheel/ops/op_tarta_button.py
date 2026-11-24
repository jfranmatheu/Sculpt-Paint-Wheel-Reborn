"""Operators for tarta button CRUD actions."""
from pathlib import Path

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty

from ..core.bl_types import OperatorAction
from ..pg.pg_wheel_storage import WheelStorage, WheelTartaSetStorage
from ..pg.pg_tarta_set import MAX_TARTA_BUTTONS
from ..utils import button_scripts
from ..wheels.presets import preset_operator_states, preset_toggles_per_mode, preset_type_per_mode


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


class OpPollActiveScriptButton(OpPollActiveButton):
    @classmethod
    def poll_operator(cls, context) -> bool | str:
        is_valid = super().poll_operator(context)
        if is_valid is not True:
            return is_valid
        if not _get_active_button(context).is_script:
            return "Active button is not a script button"
        return True


def _get_active_button(context):
    active_set = WheelStorage.get_by_mode(context).active_tarta_set
    return active_set.buttons[active_set.active_button_index]


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

    def enum_preset_toggles(self, context):
        if context is not None and (toggles := preset_toggles_per_mode.get(context.mode)):
            return [(a, b, c or "") for a, b, c in toggles]
        return [("NONE", "No presets for this mode", "")]

    name: StringProperty(name="Name", default="Button")
    image_path: StringProperty(name="Icon Image", default="", subtype="FILE_PATH")

    type: EnumProperty(
        name="Type",
        items=(
            ("OPERATOR", "Operator", ""),
            ("POPUP", "Popup", ""),
            ("SCRIPT", "Script", "Run a Python script, saved in the add-on user data"),
            ("PROPERTY", "Toggle", "Toggle a boolean property; the button shows its state"),
        ),
        default="OPERATOR",
    )

    toggle_source: EnumProperty(
        name="Toggle",
        items=(
            ("PRESET", "Preset", ""),
            ("CUSTOM", "Custom", ""),
        ),
        default="PRESET",
    )
    preset_toggle: EnumProperty(name="Preset Toggle", items=enum_preset_toggles)
    custom_toggle: StringProperty(
        name="Property",
        description="Boolean property as a data path from the context (e.g. object.data.use_mirror_x)",
        default="object.data.use_mirror_x",
        maxlen=1024,
    )
    state_path: StringProperty(
        name="Pressed When",
        description="Optional boolean data path from the context; the button is drawn pressed while it is True "
                    "(e.g. object.use_dynamic_topology_sculpting). Left empty for presets that know their state",
        default="",
        maxlen=1024,
    )

    script_source: EnumProperty(
        name="Script Source",
        items=(
            ("NEW", "New", "Start from a template and open it in the Text Editor"),
            ("TEXT", "Text", "Copy an existing Text datablock"),
            ("FILE", "File", "Copy a .py file from disk"),
        ),
        default="NEW",
    )
    script_text: StringProperty(name="Text", default="")
    script_file: StringProperty(name="File", default="", subtype="FILE_PATH")

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

        if self.type == "PROPERTY":
            layout.prop(self, "toggle_source", text="Use")
            if self.toggle_source == "PRESET":
                layout.prop(self, "preset_toggle")
            else:
                layout.prop(self, "custom_toggle")
            return
        if self.type == "SCRIPT":
            layout.prop(self, "script_source", text="Use")
            if self.script_source == "TEXT":
                layout.prop_search(self, "script_text", bpy.data, "texts")
            elif self.script_source == "FILE":
                layout.prop(self, "script_file")
            layout.prop(self, "state_path")
        elif self.type == "POPUP":
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
            layout.prop(self, "state_path")

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
        button.state_path = self.state_path.strip() if self.type in {"OPERATOR", "SCRIPT"} else ""

        if self.type == "PROPERTY":
            button.popup_type = "NONE"
            button.operator_id = ""
            button.attr = ""
            path = self.preset_toggle if self.toggle_source == "PRESET" else self.custom_toggle.strip()
            if path.startswith("bpy.context."):
                path = path[len("bpy.context."):]
            elif path.startswith("context."):
                path = path[len("context."):]
            if not path or path == "NONE":
                active_set.buttons.remove(len(active_set.buttons) - 1)
                self.report({"ERROR"}, "Pick a property to toggle")
                return self.OpReturn.CANCEL
            button.data_path = path
            if self.toggle_source == "PRESET" and self.name.strip() in {"", "Button"}:
                labels = {p: label for p, label, _d in preset_toggles_per_mode.get(context.mode, ())}
                button.name = labels.get(path, button.name)
            if button.get_state(context) is None:
                self.report({"WARNING"}, f"'{path}' is not a boolean in the current context; the button will "
                                         "do nothing until it is")
        elif self.type == "SCRIPT":
            button.popup_type = "NONE"
            button.operator_id = ""
            button.attr = ""
            source = self._get_script_source()
            if isinstance(source, Exception):
                active_set.buttons.remove(len(active_set.buttons) - 1)
                self.report({"ERROR"}, str(source))
                return self.OpReturn.CANCEL
            button.script_id = button_scripts.new_script_id()
            try:
                button_scripts.write_script(button.script_id, source)
            except OSError as ex:
                active_set.buttons.remove(len(active_set.buttons) - 1)
                self.report({"ERROR"}, f"Could not save the script: {ex}")
                return self.OpReturn.CANCEL
            if self.script_source == "NEW":
                text = button_scripts.open_text(button.script_id, button.name, source)
                button_scripts.show_text_in_editor(context, text)
        elif self.type == "OPERATOR":
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
            if not button.state_path:
                button.state_path = preset_operator_states.get(op_id, "")
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

    def _get_script_source(self) -> str | Exception:
        if self.script_source == "TEXT":
            text = bpy.data.texts.get(self.script_text)
            if text is None:
                return ValueError("Pick a Text datablock")
            return text.as_string()
        if self.script_source == "FILE":
            path = Path(bpy.path.abspath(self.script_file)) if self.script_file else None
            if path is None or not path.is_file():
                return ValueError("Pick a Python file")
            try:
                return path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as ex:
                return ex
        return button_scripts.SCRIPT_TEMPLATE


class OpTartaButtonRemove(OperatorAction, OpPollActiveButton):
    """Remove active button from the active custom-button set."""
    bl_label = "Remove Button"

    def action(self, context, event):
        active_set = WheelStorage.get_by_mode(context).active_tarta_set
        idx = active_set.active_button_index
        removed = active_set.buttons[idx]
        script_id = removed.script_id if removed.is_script else ""
        active_set.buttons.remove(idx)
        if script_id:
            button_scripts.delete_script_if_unused(context, script_id)
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


class OpTartaButtonScriptEdit(OperatorAction, OpPollActiveScriptButton):
    """Open the active button's script in the Text Editor"""
    bl_label = "Edit Script"

    def action(self, context, event):
        button = _get_active_button(context)
        if not button.script_id:
            # Bundled default with inline source: give it its own script file.
            button.script_id = button_scripts.new_script_id()
            button_scripts.write_script(button.script_id, button.script_inline)
        text = button_scripts.open_text(button.script_id, button.name, button.script_inline)
        if not button_scripts.show_text_in_editor(context, text):
            self.report({"WARNING"}, f"Open '{text.name}' in a Text Editor to edit it")
        return True


class OpTartaButtonScriptSave(OperatorAction):
    """Save this Text to its custom button script (shared by all projects)"""
    bl_label = "Save Button Script"

    @classmethod
    def poll_operator(cls, context) -> bool | str:
        if button_scripts.get_text_script_id(getattr(context, "edit_text", None)) is None:
            return "This Text is not linked to a custom button script"
        return True

    def action(self, context, event):
        try:
            path = button_scripts.save_text(context.edit_text)
        except OSError as ex:
            return f"Could not save the script: {ex}"
        self.report({"INFO"}, f"Button script saved: {path}")
        return True


def _draw_text_header(self, context):
    if button_scripts.get_text_script_id(getattr(context, "edit_text", None)) is None:
        return
    self.layout.operator(OpTartaButtonScriptSave.bl_idname, text="Save Button Script", icon="FILE_TICK")


def register():
    bpy.types.TEXT_HT_header.append(_draw_text_header)


def unregister():
    bpy.types.TEXT_HT_header.remove(_draw_text_header)
