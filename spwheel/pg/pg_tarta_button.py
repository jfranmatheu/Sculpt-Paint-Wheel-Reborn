import datetime
import ast
import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Context

from ..gpu.brush_preview import _cache_root

from ..core.bl_types import PropertyGroup


class WheelTartaButton(PropertyGroup):
    pg_parent = None

    name: StringProperty(name="Name", default="Custom")
    type: EnumProperty(
        name="Action Type",
        items=(
            ("OPERATOR", "Operator", "Run Python / preset operator"),
            ("POPUP", "Popup", "Open a menu or panel"),
            ("SCRIPT", "Script", "Run a Python script"),
        ),
    )
    popup_type: EnumProperty(
        name="Popup Kind",
        items=(
            ("NONE", "—", "Not used for operators"),
            ("MENU", "Menu", ""),
            ("PANEL", "Panel", ""),
            ("CUSTOM_MENU", "Custom Menu", ""),
            ("CUSTOM_PANEL", "Custom Panel", ""),
        ),
        default="NONE",
    )
    operator_id: StringProperty(name="Operator ID", default="")
    attr: StringProperty(name="Payload", default="", maxlen=4096)
    image_path: StringProperty(name="Icon Path", default="", subtype="FILE_PATH")
    script_sorce: EnumProperty(
        name="Script Source",
        items=(
            ("INLINE", "Inline", ""),
            ("FILE", "File", ""),
        ),
        default="INLINE",
    )
    script_id: StringProperty(name="Script ID", default="")
    script_inline: StringProperty(name="Inline Script", default="", maxlen=4096)

    @property
    def is_operator(self) -> bool:
        return self.type == "OPERATOR"

    @property
    def is_script(self) -> bool:
        return self.type == "SCRIPT"

    @property
    def is_popup(self) -> bool:
        return self.type == "POPUP"

    @property
    def is_custom_popup(self) -> bool:
        return self.is_popup and self.popup_type in ("CUSTOM_MENU", "CUSTOM_PANEL")

    @property
    def is_popup_menu(self) -> bool:
        return self.is_popup and self.popup_type in ("MENU", "CUSTOM_MENU")

    @property
    def is_popup_panel(self) -> bool:
        return self.is_popup and self.popup_type in ("PANEL", "CUSTOM_PANEL")

    def load_script(self, text_datablock: bpy.types.Text):
        script_text = text_datablock.as_string()
        if len(script_text) < 4096:
            self.script_inline = script_text
            self.script_sorce = "INLINE"
        else:
            # Save to disk in addon data. Store the script_id to access the script contents.
            self.script_id = hash(f"{text_datablock.name}|{datetime.datetime.now().timestamp()}")
            self.script_sorce = "FILE"
            # Save the script to disk.
            with open(_cache_root, "w") as f:
                f.write(script_text)

    @staticmethod
    def _resolve_op_call(operator_id: str):
        if not operator_id:
            return None
        op_ref = bpy.ops
        for part in operator_id.split('.'):
            op_ref = getattr(op_ref, part, None)
            if op_ref is None:
                return None
        return op_ref

    @staticmethod
    def _parse_operator_kwargs(payload: str) -> dict:
        if not payload:
            return {}
        kwargs = {}
        for part in payload.split(','):
            chunk = part.strip()
            if not chunk or '=' not in chunk:
                continue
            key, value = chunk.split('=', 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            try:
                kwargs[key] = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                kwargs[key] = value
        return kwargs

    def __call__(self, context: Context) -> None:
        if self.is_operator:
            op_call = self._resolve_op_call(self.operator_id)
            if op_call is None:
                return
            kwargs = self._parse_operator_kwargs(self.attr)
            if kwargs:
                op_call(**kwargs)
            else:
                op_call()
        elif self.is_script:
            if self.script_sorce == "INLINE":
                exec(self.script_inline, {"bpy": bpy})
            elif self.script_sorce == "FILE":
                # Load the script from disk.
                with open(self.script_id, "r") as f:
                    script_text = f.read()
                exec(script_text, {"bpy": bpy})
        elif self.is_popup_menu:
            if self.operator_id:
                bpy.ops.wm.call_menu(name=self.operator_id)
        elif self.is_popup_panel:
            if self.operator_id:
                bpy.ops.wm.call_panel(name=self.operator_id)
