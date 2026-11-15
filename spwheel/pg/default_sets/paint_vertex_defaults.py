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


# Essentials: brushes/essentials_brushes-mesh_vertex.blend
def_paint_vertex_tools = (
    "Paint Soft",
    "Paint Soft Pressure",
    "Paint Hard",
    "Paint Hard Pressure",
    "Airbrush",
    "Blur",
    "Average",
    "Smear",
)

def_paint_vertex_buttons = (
    _panel("STROKE_SETTINGS", "Stroke", "stroke.png", "VIEW3D_PT_tools_brush_stroke"),
    _panel("FALLOFF_SETTINGS", "Falloff", "falloff.png", "VIEW3D_PT_tools_brush_falloff"),
    _panel("TEXTURE_SETTINGS", "Texture", "texture.png", "VIEW3D_PT_tools_brush_texture"),
    _panel("MIRROR", "Symmetry", "mirror.png", "VIEW3D_PT_tools_vertexpaint_symmetry_for_topbar"),
    _menu("PAINT_MENU", "Paint", "brush.png", "VIEW3D_MT_paint_vertex"),
    _operator("VC_SMOOTH", "Smooth Colors", "mask_smooth.png", "paint.vertex_color_smooth"),
)
