"""Palette for the per-button custom tint of the pie menu ("CUSTOM" tint mode).

Each color gets a round swatch icon (drawn into a preview icon at register time) so the button list can show a
dropdown of swatches. Default sets get a color per button by function, guessed from their bundled icon.
"""

from __future__ import annotations


import bpy
import bpy.utils.previews

# (identifier, name, sRGB color). Order is stored (enum numbers), so only append new colors.
PALETTE: tuple[tuple[str, str, tuple[float, float, float]], ...] = (
    ("RED", "Red", (0.86, 0.30, 0.30)),
    ("ORANGE", "Orange", (0.93, 0.55, 0.22)),
    ("YELLOW", "Yellow", (0.92, 0.78, 0.25)),
    ("GREEN", "Green", (0.40, 0.75, 0.35)),
    ("TEAL", "Teal", (0.22, 0.70, 0.62)),
    ("BLUE", "Blue", (0.25, 0.55, 0.90)),
    ("INDIGO", "Indigo", (0.42, 0.44, 0.90)),
    ("PURPLE", "Purple", (0.62, 0.40, 0.85)),
    ("PINK", "Pink", (0.90, 0.42, 0.68)),
    ("GRAY", "Gray", (0.60, 0.62, 0.66)),
)
PALETTE_RGB: dict[str, tuple[float, float, float]] = {key: rgb for key, _name, rgb in PALETTE}

_SWATCH_SIZE = 32
_previews = None
_enum_items: list[tuple] = [("NONE", "None", "No tint", 'RADIOBUT_OFF', 0)]


def _swatch_pixels(rgb, size: int = _SWATCH_SIZE) -> list[int]:
    """Antialiased round swatch as packed RGBA ints (little-endian byte order R, G, B, A)."""
    r, g, b = (int(max(0.0, min(1.0, c)) * 255 + 0.5) for c in rgb)
    c = (size - 1) / 2.0
    radius = size * 0.42
    out = []
    for y in range(size):
        for x in range(size):
            d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
            a = int(max(0.0, min(1.0, radius - d + 0.5)) * 255 + 0.5)
            v = r | (g << 8) | (b << 16) | (a << 24)
            out.append(v - (1 << 32) if v >= (1 << 31) else v)  # Blender stores them as signed int32.
    return out


def tint_enum_items(_self=None, _context=None) -> list[tuple]:
    """Items for the button ``tint`` EnumProperty (kept referenced: Blender needs the strings to stay alive)."""
    return _enum_items


def _build_enum_items() -> None:
    global _enum_items
    items = [("NONE", "None", "No tint", 'RADIOBUT_OFF', 0)]
    for i, (key, name, _rgb) in enumerate(PALETTE, start=1):
        icon = _previews[key].icon_id if _previews is not None and key in _previews else 'BLANK1'
        items.append((key, name, f"{name} tint", icon, i))
    _enum_items = items


# ---------------------------------------------------------------------------
# Default colors for the bundled buttons, by function (guessed from their icon).
# ---------------------------------------------------------------------------

_TINT_BY_ICON = {
    # Brush settings.
    "brush": "BLUE", "stroke": "BLUE", "falloff": "BLUE", "falloff_2": "BLUE", "texture": "BLUE",
    # Menus, layers, options.
    "options": "GRAY", "grid": "GRAY", "weights": "GRAY",
    # Symmetry.
    "mirror": "GREEN", "symmetrize": "GREEN",
    # Masking (sculpt mask, auto-masking, selection masking).
    "mask": "PURPLE", "mask_clear": "PURPLE", "mask_invert": "PURPLE", "mask_sharp": "PURPLE",
    "mask_smooth": "PURPLE", "mask_smooth_2": "PURPLE", "mask_grow": "PURPLE", "mask_shrink": "PURPLE",
    "face_mask": "PURPLE", "vertex_mask": "PURPLE",
    # Visibility.
    "hide": "TEAL", "show": "TEAL", "wireframe": "TEAL",
    # Face sets.
    "face_sets": "ORANGE",
    # Topology / mesh data.
    "voxels": "YELLOW", "dyntopo": "YELLOW", "save": "YELLOW", "uv": "YELLOW", "snap": "YELLOW",
    # Colors.
    "smooth": "PINK", "dirt": "PINK", "invert": "PINK",
    # Grease pencil frames.
    "frames": "INDIGO", "onion": "INDIGO", "draw_back": "INDIGO", "frame_add": "INDIGO",
}
_WEIGHT_ICONS = {"smooth", "invert", "normalize", "clean", "weights"}


def default_tint(image_path: str, mode: str = "") -> str:
    """Palette key for a bundled button icon (by function), or "NONE" for other images."""
    from .icon_paths import builtin_name
    name = builtin_name(image_path or "")
    if name is None:
        return "NONE"
    if "WEIGHT" in mode and name in _WEIGHT_ICONS:
        return "ORANGE"
    if mode == "SCULPT" and name == "invert":
        return "TEAL"  # Invert Visible.
    return _TINT_BY_ICON.get(name, "NONE")


def register():
    global _previews
    _previews = bpy.utils.previews.new()
    for key, _name, rgb in PALETTE:
        preview = _previews.new(key)
        preview.icon_size = (_SWATCH_SIZE, _SWATCH_SIZE)
        preview.icon_pixels = _swatch_pixels(rgb)
        preview.image_size = (_SWATCH_SIZE, _SWATCH_SIZE)
        preview.image_pixels = _swatch_pixels(rgb)
    _build_enum_items()


def unregister():
    global _previews
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
    _build_enum_items()
