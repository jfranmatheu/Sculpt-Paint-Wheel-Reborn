"""Preset menus, panels and operators for the mesh Vertex Paint mode wheel."""

preset_menus_paint_vertex = (
    ("VIEW3D_MT_paint_vertex", "Paint Menu", ""),
)

preset_panels_paint_vertex = (
    ("VIEW3D_PT_tools_brush_settings_advanced", "Advanced Settings", ""),
    ("VIEW3D_PT_tools_brush_stroke", "Stroke", ""),
    ("VIEW3D_PT_tools_brush_falloff", "Falloff", ""),
    ("VIEW3D_PT_tools_brush_texture", "Texture", ""),
    ("VIEW3D_PT_tools_brush_color", "Color", ""),
    ("VIEW3D_PT_tools_vertexpaint_symmetry_for_topbar", "Symmetry", ""),
    ("VIEW3D_PT_mesh_paint_automasking", "Auto-Masking", ""),
)

preset_operators_paint_vertex = (
    ("paint.vertex_color_set", "Set Vertex Colors", ""),
    ("paint.vertex_color_smooth", "Smooth Vertex Colors", ""),
    ("paint.vertex_color_dirt", "Dirty Vertex Colors", ""),
    ("paint.vertex_color_from_weight", "Vertex Color from Weight", ""),
    ("paint.vertex_color_invert", "Invert", ""),
    ("paint.vertex_color_levels", "Levels", ""),
    ("paint.vertex_color_hsv", "Hue/Saturation/Value", ""),
    ("paint.vertex_color_brightness_contrast", "Brightness/Contrast", ""),
)
