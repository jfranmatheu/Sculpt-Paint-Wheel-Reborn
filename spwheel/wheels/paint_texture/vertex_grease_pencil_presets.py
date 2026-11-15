"""Preset menus, panels and operators for the Grease Pencil Vertex Paint mode wheel."""

preset_menus_vertex_grease_pencil = (
    ("VIEW3D_MT_paint_vertex_grease_pencil", "Paint Menu", ""),
)

preset_panels_vertex_grease_pencil = (
    ("VIEW3D_PT_tools_grease_pencil_vertex_paint_settings", "Brush Settings", ""),
    ("VIEW3D_PT_tools_grease_pencil_brush_vertex_color", "Color", ""),
    ("VIEW3D_PT_tools_grease_pencil_brush_vertex_falloff", "Falloff", ""),
    ("VIEW3D_PT_grease_pencil_multi_frame", "Multi Frame", ""),
    ("VIEW3D_PT_tools_grease_pencil_vertex_appearance", "Cursor", ""),
    ("TOPBAR_PT_grease_pencil_layers", "Layers", ""),
)

preset_operators_vertex_grease_pencil = (
    ("grease_pencil.vertex_color_set", "Set Color Attribute", ""),
    ("grease_pencil.stroke_reset_vertex_color", "Reset Vertex Color", ""),
    ("grease_pencil.vertex_color_invert", "Invert", ""),
    ("grease_pencil.vertex_color_levels", "Levels", ""),
    ("grease_pencil.vertex_color_hsv", "Hue/Saturation/Value", ""),
    ("grease_pencil.vertex_color_brightness_contrast", "Brightness/Contrast", ""),
)
