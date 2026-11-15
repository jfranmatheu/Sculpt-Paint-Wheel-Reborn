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


# Essentials: brushes/essentials_brushes-gp_draw.blend
def_paint_grease_pencil_tools = (
    "Pencil",
    "Pencil Soft",
    "Pen",
    "Ink Pen",
    "Ink Pen Rough",
    "Marker Bold",
    "Marker Chisel",
    "Airbrush",
    "Tint",
    "Fill",
    "Eraser Soft",
    "Eraser Hard",
    "Eraser Stroke",
)

# Mirrors what Draw mode exposes in the tool header / Tool sidebar (Blender 4.3+).
def_paint_grease_pencil_buttons = (
    _panel("LAYERS", "Layers", "grid.png", "TOPBAR_PT_grease_pencil_layers"),
    _panel("MATERIALS", "Materials", "texture.png", "TOPBAR_PT_grease_pencil_materials"),
    _panel("STROKE_SETTINGS", "Stroke", "stroke.png", "VIEW3D_PT_tools_grease_pencil_v3_brush_stroke"),
    _panel("STABILIZER", "Stabilize Stroke", "falloff_2.png", "VIEW3D_PT_tools_grease_pencil_v3_brush_stabilizer"),
    _panel("ADVANCED", "Advanced", "brush.png", "VIEW3D_PT_tools_grease_pencil_v3_brush_advanced"),
    _operator("INSERT_BLANK_FRAME", "Insert Blank Keyframe", "options.png", "grease_pencil.insert_blank_frame"),
)
