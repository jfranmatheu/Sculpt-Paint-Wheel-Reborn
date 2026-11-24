import ast
import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Context

from ..core.bl_types import PropertyGroup
from ..utils import button_scripts
from ..utils.tint_palette import tint_enum_items


# Blender 5.3 moved brush falloff into the "Shape" panel for mesh paint modes, and the old
# Falloff panel no longer polls there. Keep stored IDs version-agnostic and alias at call time.
_SHAPE_PANEL_MODES = {'SCULPT', 'PAINT_VERTEX', 'PAINT_WEIGHT', 'PAINT_TEXTURE'}


def _resolve_panel_id(context, panel_id: str) -> str:
    if (
        panel_id == "VIEW3D_PT_tools_brush_falloff"
        and context.mode in _SHAPE_PANEL_MODES
        and hasattr(bpy.types, "VIEW3D_PT_tools_brush_shape")
    ):
        return "VIEW3D_PT_tools_brush_shape"
    return panel_id


class WheelTartaButton(PropertyGroup):
    pg_parent = None

    name: StringProperty(name="Name", default="Custom")
    type: EnumProperty(
        name="Action Type",
        items=(
            ("OPERATOR", "Operator", "Run Python / preset operator"),
            ("POPUP", "Popup", "Open a menu or panel"),
            ("SCRIPT", "Script", "Run a Python script"),
            ("PROPERTY", "Toggle", "Toggle a boolean property; the button shows its state"),
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
    tint: EnumProperty(
        name="Tint",
        description="Color of the button's pie segment (when the theme's Tint Mode is Custom)",
        items=tint_enum_items,
    )
    # Toggle buttons: boolean property to flip, as a data path from the context.
    data_path: StringProperty(
        name="Property",
        description="Boolean property to toggle, as a data path from the context (e.g. object.data.use_mirror_x)",
        default="",
    )
    # Operator / script buttons: optional boolean shown as the button's pressed state.
    state_path: StringProperty(
        name="Pressed When",
        description="Optional boolean data path from the context; the button is drawn pressed while it is True "
                    "(e.g. object.use_dynamic_topology_sculpting)",
        default="",
    )
    # Script file in the add-on user data (see utils/button_scripts.py).
    script_id: StringProperty(name="Script ID", default="")
    # Fallback source stored in the button itself (bundled default sets); unused when script_id is set.
    script_inline: StringProperty(name="Inline Script", default="", maxlen=4096)

    @property
    def is_operator(self) -> bool:
        return self.type == "OPERATOR"

    @property
    def is_script(self) -> bool:
        return self.type == "SCRIPT"

    @property
    def is_toggle(self) -> bool:
        return self.type == "PROPERTY"

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

    def get_state(self, context: Context) -> bool | None:
        """Pressed state: the toggled property, or ``state_path`` for other buttons. None when the button has no
        state or the path doesn't resolve to a boolean in this context."""
        path = self.data_path if self.is_toggle else self.state_path
        if not path or self.is_popup:
            return None
        try:
            value = context.path_resolve(path)
        except (ValueError, TypeError, AttributeError):
            return None
        return value if isinstance(value, bool) else None

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
        try:
            self._run(context)
        except Exception as ex:
            # E.g. an operator whose poll fails here (no vertex groups...), a wrong operator / menu / panel id.
            message = str(ex).strip().removeprefix("Error: ") or type(ex).__name__
            button_scripts.report_script_error(context, f"Can't run '{self.name}'", message)

    def _run(self, context: Context) -> None:
        if self.is_operator:
            op_call = self._resolve_op_call(self.operator_id)
            if op_call is None:
                return
            kwargs = self._parse_operator_kwargs(self.attr)
            if kwargs:
                op_call(**kwargs)
            else:
                op_call()
        elif self.is_toggle:
            if self.data_path:
                try:
                    bpy.ops.wm.context_toggle(data_path=self.data_path)
                except RuntimeError as ex:
                    print(f"[SPWheel] Toggle '{self.name}' failed: {ex}")
        elif self.is_script:
            if error := button_scripts.run_button_script(self, context):
                button_scripts.report_script_error(context, f"Script '{self.name}' failed", error)
        elif self.is_popup_menu:
            if self.operator_id:
                bpy.ops.wm.call_menu(name=self.operator_id)
        elif self.is_popup_panel:
            if self.operator_id:
                bpy.ops.wm.call_panel(name=_resolve_panel_id(context, self.operator_id))
