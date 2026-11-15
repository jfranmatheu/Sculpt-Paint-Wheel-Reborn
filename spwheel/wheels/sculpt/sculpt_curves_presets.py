"""Preset menus, panels and operators for the Sculpt Curves mode wheel."""

preset_menus_sculpt_curves = (
    ("VIEW3D_MT_sculpt_curves", "Curves Menu", ""),
    ("VIEW3D_MT_select_sculpt_curves", "Select Menu", ""),
)

preset_panels_sculpt_curves = (
    ("VIEW3D_PT_tools_brush_settings", "Brush Settings", ""),
    ("VIEW3D_PT_tools_brush_stroke", "Stroke", ""),
    ("VIEW3D_PT_tools_brush_falloff", "Falloff", ""),
    ("VIEW3D_PT_curves_sculpt_symmetry", "Symmetry", ""),
)

preset_operators_sculpt_curves = (
    ("_SNAP_DEFORM", "Snap to Deformed Surface", "curves.snap_curves_to_surface#attach_mode='DEFORM'"),
    ("_SNAP_NEAREST", "Snap to Nearest Surface", "curves.snap_curves_to_surface#attach_mode='NEAREST'"),
    ("curves.select_all", "Select All", ""),
    ("sculpt_curves.select_random", "Select Random", ""),
)
