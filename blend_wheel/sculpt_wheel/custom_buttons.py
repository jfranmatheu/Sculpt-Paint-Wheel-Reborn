"""Custom wheel buttons: build action strings, invoke, GPU image cache."""

from __future__ import annotations

import os
from typing import Optional

import bpy
import gpu

from ..core.debug import print_debug
from .presets import preset_menus, preset_operators, preset_panels


def _preset_operator_to_bpy_line(preset_id: str) -> str:
    for rid, _title, expr in preset_operators:
        if rid != preset_id:
            continue
        cmd = expr if expr else rid
        if "#" in cmd:
            base, args = cmd.split("#", 1)
            base = base.strip()
            args = args.strip()
            return f"bpy.ops.{base}({args})"
        if "(" in cmd:
            return f"bpy.ops.{cmd}"
        return f"bpy.ops.{cmd}()"
    return ""


def _preset_menu_idname(preset_id: str) -> str:
    for rid, _title, _desc in preset_menus:
        if rid == preset_id:
            return rid
    return ""


def _preset_panel_idname(preset_id: str) -> str:
    for rid, _title, _desc in preset_panels:
        if rid == preset_id:
            return rid
    return ""


def preset_operator_attr_for_storage(preset_id: str) -> str:
    """Full ``WheelCustomButton.attr`` for a ``preset_operators`` identifier (executable Python)."""
    line = _preset_operator_to_bpy_line(preset_id)
    if not line:
        return ""
    return "import bpy\n" + line


def build_custom_button_attr(create) -> str:
    """Build executable / idname string from CreateWheelCustomButton (RNA group)."""
    if create.type == "OPERATOR":
        if create.operator_type == "PRESET":
            line = _preset_operator_to_bpy_line(create.preset_operator)
            if not line:
                return ""
            return "import bpy\n" + line
        if create.operator_type == "CUSTOM":
            s = create.custom_operator.strip()
            if not s:
                return ""
            if not s.startswith("import "):
                s = "import bpy\n" + s
            return s
        return ""
    if create.type == "POPUP":
        if create.popup_type == "MENU":
            if create.menu_source == "PRESET":
                return _preset_menu_idname(create.preset_menu)
            return create.custom_menu.strip()
        if create.popup_type == "PANEL":
            if create.panel_source == "PRESET":
                return _preset_panel_idname(create.preset_panel)
            return create.custom_panel.strip()
        return ""
    return ""


def invoke_wheel_custom_button(context: bpy.types.Context, button) -> None:
    """Run a WheelCustomButton (type POPUP_MENU / POPUP_PANEL / OPERATOR)."""
    if button.type == "POPUP":
        if button.popup_type == "MENU":
            bpy.ops.wm.call_menu(name=button.attr)
        elif button.popup_type == "PANEL":
            bpy.ops.wm.call_panel(name=button.attr, keep_open=True)
    elif button.type == "OPERATOR":
        try:
            exec(button.attr, {"bpy": bpy})
        except Exception as ex:
            print("Sculpt+ wheel custom button:", ex)


# --- GPU image cache (path -> gpu.types.GPUTexture) ---

_texture_cache: dict[str, gpu.types.GPUTexture] = {}


def get_custom_button_texture(path: str) -> Optional[gpu.types.GPUTexture]:
    if not path or not os.path.isfile(path):
        if path:
            print_debug(f"[Sculpt+] custom button icon missing (reload add-on or pick a new image): {path}")
        return None
    norm = os.path.normpath(path)
    tex = _texture_cache.get(norm)
    if tex is not None:
        return tex
    try:
        img = bpy.data.images.load(norm, check_existing=True)
    except Exception:
        print(f"Custom button texture load failed: {norm}")
        return None
    try:
        tex = gpu.texture.from_image(img)
    except Exception:
        print(f"Custom button texture GPU conversion failed: {norm}")
        return None
    _texture_cache[norm] = tex
    return tex


def clear_custom_button_texture_cache() -> None:
    _texture_cache.clear()
