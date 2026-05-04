"""Preset menus/panels/operators exposed to weight wheel button builders."""

preset_menus_weight = (
    ("VIEW3D_MT_paint_weight", "Weights Menu", ""),
)

preset_panels_weight = (
    ("VIEW3D_PT_tools_brush_settings_advanced", "Brush Settings", ""),
    ("VIEW3D_PT_tools_brush_stroke", "Stroke Settings", ""),
    ("VIEW3D_PT_tools_brush_falloff", "Falloff Settings", ""),
    ("VIEW3D_PT_tools_weightpaint_symmetry_for_topbar", "Mirror", ""),
    ("VIEW3D_PT_tools_weightpaint_options", "Weight Options", ""),
)

preset_operators_weight = (
    ("_BOX_SELECT_OPTIONS", "Box Select Options", "weightwheel.box_select_tool_options"),
    ("_WEIGHT_SET", "Apply Weight", "paint.weight_set"),
    ("_WEIGHT_SAMPLE", "Sample Weight", "paint.weight_sample"),
)

