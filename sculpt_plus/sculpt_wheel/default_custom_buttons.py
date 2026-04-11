"""First-run default custom button set (presets + bundled icons under ``assets/images/custom_buttons``)."""

from __future__ import annotations

from ..core.globals import PATHS
from .custom_buttons import preset_operator_attr_for_storage

# Packaged PNGs (same order as user-facing labels).
_ICON_DIR = PATHS.ASSETS / "images" / "custom_buttons"

_DEFAULT_SET_NAME = "Default"

# Popover panels (bl_idname must exist in ``presets.preset_panels``).
_DEFAULT_PANELS: tuple[tuple[str, str, str], ...] = (
    ("Advanced", "VIEW3D_PT_tools_brush_settings_advanced", "brush.png"),
    ("Stroke", "VIEW3D_PT_tools_brush_stroke", "stroke.png"),
    ("Falloff", "VIEW3D_PT_tools_brush_falloff", "falloff.png"),
    # ("Texture", "VIEW3D_PT_tools_brush_texture", "texture.png"),
    ("Voxel Remesh", "VIEW3D_PT_sculpt_voxel_remesh", "grid.png"),
)

# Preset operator ids from ``presets.preset_operators``.
_DEFAULT_OPERATORS: tuple[tuple[str, str, str], ...] = (
    ("Clear mask", "_MASK_CLEAR", "mask_clear.png"),
    ("Invert mask", "_MASK_INVERT", "mask_invert.png"),
    ("Sharpen mask", "_MF_SHARPEN", "mask_sharp.png"),
    ("Smooth mask", "_MF_SMOOTH", "mask_smooth.png"),
)


def _icon_abs(filename: str) -> str:
    p = _ICON_DIR / filename
    if p.is_file():
        return str(p.resolve())
    return ""


def _bundled_icon_filenames_in_order() -> list[str]:
    return [x[2] for x in _DEFAULT_PANELS] + [x[2] for x in _DEFAULT_OPERATORS]


def resolve_addon_icon_for_default_slot(button_index: int) -> str:
    """Absolute path to the stock icon for *button_index* in the first default set, or ``\"\"``."""
    names = _bundled_icon_filenames_in_order()
    if 0 <= button_index < len(names):
        return _icon_abs(names[button_index])
    return ""


def repair_missing_icon_paths(st) -> None:
    """Fix RNA paths that point to missing user-data copies (``setXX_btnYY``) or stale files."""
    import os

    for si, bset in enumerate(st.custom_button_sets):
        for bi, btn in enumerate(bset.custom_buttons):
            path = (btn.image_path or "").strip()
            if path and os.path.isfile(path):
                continue
            if si == 0:
                fixed = resolve_addon_icon_for_default_slot(bi)
                if fixed:
                    btn.image_path = fixed


def apply_default_custom_button_set(bset) -> None:
    """Fill *bset* with the stock layout; clears existing buttons."""
    while len(bset.custom_buttons) > 0:
        bset.custom_buttons.remove(0)

    for title, panel_id, icon_fn in _DEFAULT_PANELS:
        b = bset.custom_buttons.add()
        b.name = title
        b.type = "POPUP"
        b.popup_type = "PANEL"
        b.attr = panel_id
        ip = _icon_abs(icon_fn)
        if ip:
            b.image_path = ip

    for title, preset_id, icon_fn in _DEFAULT_OPERATORS:
        attr = preset_operator_attr_for_storage(preset_id)
        if not attr:
            continue
        b = bset.custom_buttons.add()
        b.name = title
        b.type = "OPERATOR"
        b.popup_type = "NONE"
        b.attr = attr
        ip = _icon_abs(icon_fn)
        if ip:
            b.image_path = ip

    bset.name = _DEFAULT_SET_NAME
