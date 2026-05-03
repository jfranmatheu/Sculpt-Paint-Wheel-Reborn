from os.path import dirname, join

icons_dir = join(dirname(dirname(dirname(__file__))), "assets", 'images', "custom_buttons")

def_sculpt_tools = (
    "Draw",
    "Draw Sharp",
    "Clay Strips",
    "Inflate/Deflate",
    "Crease Polish",
    "Crease Sharp",
    "Blob",
    "Layer",
    "Fill/Deepen",
    "Flatten/Contrast",
    "Plateau",
    "Scrape Multiplane",
    "Scrape/Fill",
    "Pinch/Magnify",
    "Grab",
    "Grab 2D",
    "Elastic Grab",
    "Pose",
    # "Mask",
    # "Face Set Paint",
)

def_sculpt_buttons = (
    #{
    #    'name' : "Advanced Brush Settings",
    #    'image_path' : join(icons_dir, 'brush_icon.png'),
    #    'type' : 'POPUP',
    #    'popup_type' : 'PANEL',
    #    'as_attribute' : 'PRESET',
    #    'preset_panel' : 'VIEW3D_PT_tools_brush_stroke'
    #},
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
    {
        'id': 'REMESH_SETTINGS',
        'name' : "Remesh Settings",
        'image_path' : join(icons_dir, 'grid.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_sculpt_voxel_remesh'
    },
    {
        'id': 'MASK_CLEAR',
        'name' : "Mask Clear",
        'image_path' : join(icons_dir, 'mask_clear.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MASK_CLEAR',
        'custom_identifier' : "paint.mask_flood_fill#mode='VALUE', value=0"
    },
    {
        'id': 'MASK_INVERT',
        'name' : "Mask Invert",
        'image_path' : join(icons_dir, 'mask_invert.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MASK_INVERT',
        'custom_identifier' : "paint.mask_flood_fill#mode='INVERT'"
    },
    {
        'id': 'MASK_SHARP',
        'name' : "Mask Sharp",
        'image_path' : join(icons_dir, 'mask_sharp.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MF_SHARPEN',
        'custom_identifier' : "sculpt.mask_filter#filter_type='SHARPEN', auto_iteration_count=True"
    },
    {
        'id': 'MASK_SMOOTH',
        'name' : "Mask Smooth",
        'image_path' : join(icons_dir, 'mask_smooth.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MF_SMOOTH',
        'custom_identifier' : "sculpt.mask_filter#filter_type='SMOOTH', auto_iteration_count=True"
    }
)
