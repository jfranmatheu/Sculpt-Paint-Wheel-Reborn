"""Preset menus, panels and operators for the Grease Pencil Weight Paint mode wheel."""

preset_menus_weight_grease_pencil = (
    ("VIEW3D_MT_weight_grease_pencil", "Weights Menu", ""),
)

preset_panels_weight_grease_pencil = (
    ("VIEW3D_PT_tools_grease_pencil_weight_paint_settings", "Brush Settings", ""),
    ("VIEW3D_PT_tools_grease_pencil_weight_options", "Options", ""),
    ("VIEW3D_PT_tools_grease_pencil_brush_weight_falloff", "Falloff", ""),
    ("VIEW3D_PT_grease_pencil_multi_frame", "Multi Frame", ""),
    ("VIEW3D_PT_tools_grease_pencil_weight_appearance", "Cursor", ""),
    ("TOPBAR_PT_grease_pencil_layers", "Layers", ""),
)

preset_operators_weight_grease_pencil = (
    ("grease_pencil.vertex_group_normalize_all", "Normalize All", ""),
    ("grease_pencil.vertex_group_normalize", "Normalize", ""),
    ("grease_pencil.weight_invert", "Invert Weight", ""),
    ("grease_pencil.vertex_group_smooth", "Smooth Weight", ""),
    ("grease_pencil.weight_toggle_direction", "Toggle Add/Subtract", ""),
)
