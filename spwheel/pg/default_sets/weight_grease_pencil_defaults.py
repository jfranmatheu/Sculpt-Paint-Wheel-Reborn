from os.path import dirname, join

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


# The weight wheel draws its own weight markers instead of a brush list.
def_weight_grease_pencil_tools = None

def_weight_grease_pencil_buttons = (
    _panel("WEIGHT_OPTIONS", "Options", "options.png", "VIEW3D_PT_tools_grease_pencil_weight_options"),
    _panel("FALLOFF_SETTINGS", "Falloff", "falloff.png", "VIEW3D_PT_tools_grease_pencil_brush_weight_falloff"),
    _menu("WEIGHTS", "Weights", "weights.png", "VIEW3D_MT_weight_grease_pencil"),
    _operator("NORMALIZE_ALL", "Normalize All", "weights.png", "grease_pencil.vertex_group_normalize_all"),
    _operator("WEIGHT_INVERT", "Invert Weight", "mask_invert.png", "grease_pencil.weight_invert"),
    _operator("WEIGHT_SMOOTH", "Smooth Weight", "mask_smooth.png", "grease_pencil.vertex_group_smooth"),
)
