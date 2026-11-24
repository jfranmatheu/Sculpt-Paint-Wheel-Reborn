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


# Essentials: brushes/essentials_brushes-gp_vertex.blend
def_vertex_grease_pencil_tools = (
    "Paint",
    "Blur",
    "Average",
    "Smear",
    "Replace",
)

def_vertex_grease_pencil_buttons = (
    _panel("COLOR", "Color", "texture.png", "VIEW3D_PT_tools_grease_pencil_brush_vertex_color"),
    _panel("FALLOFF_SETTINGS", "Falloff", "falloff.png", "VIEW3D_PT_tools_grease_pencil_brush_vertex_falloff"),
    _panel("MULTI_FRAME", "Multi Frame", "options.png", "VIEW3D_PT_grease_pencil_multi_frame"),
    _menu("PAINT_MENU", "Paint", "brush.png", "VIEW3D_MT_paint_vertex_grease_pencil"),
    _operator("RESET_VERTEX_COLOR", "Reset Vertex Color", "mask_clear.png", "grease_pencil.stroke_reset_vertex_color"),
    _operator("VC_INVERT", "Invert Colors", "invert.png", "grease_pencil.vertex_color_invert"),
    GP_MULTI_FRAME,
    GP_ONION_SKIN,
)
