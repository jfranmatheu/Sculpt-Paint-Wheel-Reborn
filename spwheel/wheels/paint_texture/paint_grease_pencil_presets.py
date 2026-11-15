"""Preset menus, panels and operators for the Grease Pencil Draw mode wheel."""

preset_menus_paint_grease_pencil = (
    ("VIEW3D_MT_paint_grease_pencil", "Draw Menu", ""),
    ("GREASE_PENCIL_MT_layer_active", "Active Layer", ""),
)

preset_panels_paint_grease_pencil = (
    ("VIEW3D_PT_tools_grease_pencil_v3_brush_settings", "Brush Settings", ""),
    ("VIEW3D_PT_tools_grease_pencil_v3_brush_advanced", "Advanced", ""),
    ("VIEW3D_PT_tools_grease_pencil_v3_brush_stroke", "Stroke", ""),
    ("VIEW3D_PT_tools_grease_pencil_v3_brush_stabilizer", "Stabilize Stroke", ""),
    ("VIEW3D_PT_tools_grease_pencil_v3_brush_post_processing", "Post-Processing", ""),
    ("VIEW3D_PT_tools_grease_pencil_v3_brush_random", "Randomize", ""),
    ("VIEW3D_PT_tools_grease_pencil_v3_brush_mixcolor", "Color", ""),
    ("VIEW3D_PT_tools_grease_pencil_paint_appearance", "Cursor", ""),
    ("TOPBAR_PT_grease_pencil_layers", "Layers", ""),
    ("TOPBAR_PT_grease_pencil_materials", "Materials", ""),
    ("VIEW3D_PT_grease_pencil_guide", "Guides", ""),
)

preset_operators_paint_grease_pencil = (
    ("grease_pencil.insert_blank_frame", "Insert Blank Keyframe", ""),
    ("_INSERT_BLANK_FRAME_ALL", "Insert Blank Keyframe (All Layers)", "grease_pencil.insert_blank_frame#all_layers=True"),
    ("grease_pencil.frame_duplicate", "Duplicate Active Keyframe", ""),
    ("grease_pencil.layer_add", "Add Layer", ""),
)
