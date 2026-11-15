from os.path import dirname, join

import bpy

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


# Essentials: brushes/essentials_brushes-curve_sculpt.blend
def_sculpt_curves_tools = (
    "Add",
    "Delete",
    "Density",
    "Comb",
    "Slide",
    "Pinch",
    "Puff",
    "Smooth",
    "Grow/Shrink",
    "Pull Tips",
    "Select",
)
if bpy.app.version >= (5, 3, 0):
    def_sculpt_curves_tools += ("Cut",)  # New essentials brush in 5.3.

# Brush "Advanced" and "Texture" panels don't poll in Sculpt Curves mode.
def_sculpt_curves_buttons = (
    _panel("BRUSH_SETTINGS", "Brush Settings", "brush.png", "VIEW3D_PT_tools_brush_settings"),
    _panel("STROKE_SETTINGS", "Stroke", "stroke.png", "VIEW3D_PT_tools_brush_stroke"),
    _panel("FALLOFF_SETTINGS", "Falloff", "falloff.png", "VIEW3D_PT_tools_brush_falloff"),
    _panel("MIRROR", "Symmetry", "mirror.png", "VIEW3D_PT_curves_sculpt_symmetry"),
    _menu("CURVES_MENU", "Curves", "grid.png", "VIEW3D_MT_sculpt_curves"),
)
