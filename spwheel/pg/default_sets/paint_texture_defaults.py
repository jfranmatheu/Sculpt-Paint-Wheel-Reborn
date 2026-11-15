from os.path import dirname, join

icons_dir = join(dirname(dirname(dirname(__file__))), "assets", 'images', "custom_buttons")

def_paint_texture_tools = (
    'Paint Pixel Art',
    'Erase Pixel Art',
    'Airbrush',
    'Paint Hard',
    'Paint Hard Pressure',
    'Paint Soft',
    'Paint Soft Pressure',
    'Erase Hard',
    'Erase Hard Pressure',
    'Erase Soft',
    'Blur',
    'Smear',
    'Clone',
    'Fill',
    'Mask',
)

def_paint_texture_buttons = (
    {
        'name' : "Advanced Brush Settings",
        'image_path' : join(icons_dir, 'brush.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_tools_brush_settings_advanced'
    },
    {
        'id': 'STROKE_SETTINGS',
        'name' : "Stroke Settings",
        'image_path' : join(icons_dir, 'stroke.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_tools_brush_stroke'
    },
    {
        'id': 'FALLOFF_SETTINGS',
        'name' : "Falloff Settings",
        'image_path' : join(icons_dir, 'falloff.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_tools_brush_falloff'
    },
    {
        'id': 'TEXTURE_SETTINGS',
        'name' : "Texture Settings",
        'image_path' : join(icons_dir, 'texture.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_tools_brush_texture'
    },
)
