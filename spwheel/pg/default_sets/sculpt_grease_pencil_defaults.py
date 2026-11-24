from os.path import dirname, join
from ._buttons import (
    AUTO_NORMALIZE, FACE_SELECTION_MASKING, GP_MULTI_FRAME, GP_ONION_SKIN, MIRROR_X, VERTEX_SELECTION_MASKING,
    operator, toggle,
)

icons_dir = join(dirname(dirname(dirname(__file__))), "assets", "images", "custom_buttons")


def _panel(id, name, icon, panel):
    return {
        "id": id,
        "name": name,
        "image_path": join(icons_dir, icon),
        "type": "POPUP",
        "popup_type": "PANEL",
        "as_attribute": "PRESET",
        "preset_panel": panel,
    }


def _menu(id, name, icon, menu):
    return {
        "id": id,
        "name": name,
        "image_path": join(icons_dir, icon),
        "type": "POPUP",
        "popup_type": "MENU",
        "as_attribute": "PRESET",
        "preset_menu": menu,
    }


def _operator(id, name, icon, operator):
    return {
        "id": id,
        "name": name,
        "image_path": join(icons_dir, icon),
        "type": "OPERATOR",
        "as_attribute": "PRESET",
        "preset_operator": operator,
        "custom_identifier": operator,
    }


# Essentials: brushes/essentials_brushes-gp_sculpt.blend
def_sculpt_grease_pencil_tools = (
    "Smooth",
    "Thickness",
    "Strength",
    "Randomize",
    "Grab",
    "Pull",
    "Twist",
    "Pinch",
    "Clone",
)

def_sculpt_grease_pencil_buttons = (
    _panel("FALLOFF_SETTINGS", "Falloff", "falloff.png", "VIEW3D_PT_tools_brush_falloff"),
    _panel("AUTO_MASKING", "Auto-Masking", "mask.png", "VIEW3D_PT_grease_pencil_sculpt_automasking"),
    _panel("MULTI_FRAME", "Multi Frame", "options.png", "VIEW3D_PT_grease_pencil_multi_frame"),
    _panel("LAYERS", "Layers", "grid.png", "TOPBAR_PT_grease_pencil_layers"),
    GP_MULTI_FRAME,
    GP_ONION_SKIN,
)
