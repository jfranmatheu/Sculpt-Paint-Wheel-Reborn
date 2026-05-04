from os.path import dirname, join

icons_dir = join(dirname(dirname(dirname(__file__))), "assets", "images", "custom_buttons")


def_weight_buttons = (
    {
        'id': 'BRUSH SETTINGS',
        'name' : "Brush Settings",
        'image_path' : join(icons_dir, 'brush.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'CUSTOM',
        'custom_identifier' : 'VIEW3D_PT_tools_brush_settings_advanced'
    },
    {
        'id': 'STROKE_SETTINGS',
        'name' : "Stroke Settings",
        'image_path' : join(icons_dir, 'stroke.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'CUSTOM',
        'custom_identifier' : 'VIEW3D_PT_tools_brush_stroke'
    },
    {
        'id': 'FALLOFF_SETTINGS',
        'name' : "Falloff Settings",
        'image_path' : join(icons_dir, 'falloff.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'CUSTOM',
        'custom_identifier' : 'VIEW3D_PT_tools_brush_falloff'
    },
    {
        'id': 'MIRROR',
        'name' : "Mirror",
        'image_path' : join(icons_dir, 'mirror.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'CUSTOM',
        'custom_identifier' : 'VIEW3D_PT_tools_weightpaint_symmetry_for_topbar'
    },
    {
        'id': 'WEIGHT_OPTIONS',
        'name' : "Weight Options",
        'image_path' : join(icons_dir, 'options.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'CUSTOM',
        'custom_identifier' : 'VIEW3D_PT_tools_weightpaint_options' #'WEIGHT_PT_options'
    },
    {
        'id': 'WEIGHTS',
        'name' : "Weights",
        'image_path' : join(icons_dir, 'weights.png'),
        'type' : 'POPUP',
        'popup_type' : 'MENU',
        'as_attribute' : 'CUSTOM',
        'custom_identifier' : 'VIEW3D_MT_paint_weight',
        'preset_menu' : 'VIEW3D_MT_paint_weight'
    },
)
