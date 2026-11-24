from bpy.props import CollectionProperty, IntProperty, StringProperty
from bpy.types import UILayout
from typing import Any

from ..core.bl_types import PropertyGroup
from .pg_tarta_button import WheelTartaButton
from ..utils.tint_palette import default_tint
from ..utils import icon_paths


# Most buttons a set can hold (the pie menu has one segment per button).
MAX_TARTA_BUTTONS = 10



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

    @staticmethod
    def _split_operator_expr(expr: str) -> tuple[str, str]:
        if not expr:
            return "", ""
        op_id, sep, payload = expr.partition('#')
        if not sep:
            return op_id.strip(), ""
        return op_id.strip(), payload.strip()

    @classmethod
    def metadata_key(cls, metadata: dict[str, Any]) -> tuple[str, ...]:
        """What a default button's metadata creates, as ``button_key`` gives it for that button."""
        button_type = metadata.get("type", "OPERATOR")
        if button_type == "PROPERTY":
            return button_type, metadata.get("data_path", "")
        if button_type == "POPUP":
            if metadata.get("as_attribute", "CUSTOM") == "PRESET":
                target = metadata.get("preset_panel", "") or metadata.get("preset_menu", "")
            else:
                target = ""
            return button_type, target or metadata.get("custom_identifier", "")
        if button_type == "OPERATOR":
            op_id, payload = cls._split_operator_expr(metadata.get("custom_identifier", ""))
            return button_type, op_id or metadata.get("preset_operator", ""), cls._payload_key(payload)
        return button_type, metadata.get("name", "")

    @staticmethod
    def _payload_key(payload: str) -> str:
        """Operator arguments in a canonical form (``mode='VALUE', value=0`` == ``value=0,mode="VALUE"``)."""
        return repr(sorted(WheelTartaButton._parse_operator_kwargs(payload).items()))

    @classmethod
    def button_key(cls, button: WheelTartaButton) -> tuple[str, ...]:
        """What a button runs: its operator and arguments (two buttons of the same operator with other arguments,
        e.g. Clear / Invert Mask, are different), its popup id, or its property path."""
        if button.is_toggle:
            return button.type, button.data_path
        if button.is_script:
            return button.type, button.name
        if button.is_operator:
            return button.type, button.operator_id, cls._payload_key(button.attr)
        return button.type, button.operator_id

    @classmethod
    def key_string(cls, key: tuple[str, ...]) -> str:
        return "|".join(key)

    def add_tarta_button_from_metadata(self, metadata: dict[str, Any], mode: str = "") -> WheelTartaButton:
        button = self.buttons.add()
        button.name = metadata.get("name", "Button")
        button.image_path = icon_paths.to_portable(metadata.get("image_path", ""))
        button.tint = metadata.get("tint") or default_tint(button.image_path, mode)

        button_type = metadata.get("type", "OPERATOR")
        button.type = button_type if button_type in {"OPERATOR", "POPUP", "SCRIPT", "PROPERTY"} else "OPERATOR"
        button.state_path = metadata.get("state_path", "")

        if button.type == "POPUP":
            popup_type = metadata.get("popup_type", "PANEL")
            button.popup_type = popup_type if popup_type in {"MENU", "PANEL", "CUSTOM_MENU", "CUSTOM_PANEL"} else "PANEL"
            as_attribute = metadata.get("as_attribute", "CUSTOM")
            if as_attribute == "PRESET":
                if button.popup_type in {"PANEL", "CUSTOM_PANEL"}:
                    button.operator_id = metadata.get("preset_panel", "") or metadata.get("custom_identifier", "")
                else:
                    button.operator_id = metadata.get("preset_menu", "") or metadata.get("custom_identifier", "")
            else:
                button.operator_id = metadata.get("custom_identifier", "")
            button.attr = ""
            return button

        if button.type == "PROPERTY":
            button.popup_type = "NONE"
            button.data_path = metadata.get("data_path", "")
            return button

        if button.type == "OPERATOR":
            custom_identifier = metadata.get("custom_identifier", "")
            operator_id, payload = self._split_operator_expr(custom_identifier)
            button.operator_id = operator_id or metadata.get("preset_operator", "")
            button.attr = payload
            button.popup_type = "NONE"
            return button

        # SCRIPT: bundled defaults carry their source inline.
        button.popup_type = "NONE"
        button.operator_id = ""
        button.attr = ""
        button.script_inline = metadata.get("script", "")
        return button
