from os.path import dirname, join

icons_dir = join(dirname(dirname(dirname(__file__))), 'images', "custom_buttons")

_SCULPT_ASSET_BASE = "brushes/essentials_brushes-mesh_sculpt.blend/Brush"

def_sculpt_tools = (
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Draw",
        "display_name": "Sculpt Draw",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Draw Sharp",
        "display_name": "Draw Sharp",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Clay Strips",
        "display_name": "Clay Strips",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Inflate/Deflate",
        "display_name": "Inflate",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Crease",
        "display_name": "Crease",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Scrape/Peaks",
        "display_name": "Scrape",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Scrape Multiplane",
        "display_name": "MultiPlane Scrape",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Pinch/Magnify",
        "display_name": "Pinch",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Grab",
        "display_name": "Grab",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Elastic Grab",
        "display_name": "Elastic Deform",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Pose",
        "display_name": "Pose",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Cloth",
        "display_name": "Cloth",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Mask",
        "display_name": "Mask",
    },
    {
        "asset_library_type": "ESSENTIALS",
        "asset_library_identifier": "",
        "relative_asset_identifier": f"{_SCULPT_ASSET_BASE}/Draw Face Sets",
        "display_name": "Draw Face Sets",
    },
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
        'image_path' : join(icons_dir, 'stroke_icon.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_tools_brush_stroke'
    },
    {
        'id': 'FALLOFF_SETTINGS',
        'name' : "Falloff Settings",
        'image_path' : join(icons_dir, 'fallOff_icon.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_tools_brush_falloff'
    },
    {
        'id': 'TEXTURE_SETTINGS',
        'name' : "Texture Settings",
        'image_path' : join(icons_dir, 'texture_icon.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_tools_brush_texture'
    },
    {
        'id': 'REMESH_SETTINGS',
        'name' : "Remesh Settings",
        'image_path' : join(icons_dir, 'grid_icon.png'),
        'type' : 'POPUP',
        'popup_type' : 'PANEL',
        'as_attribute' : 'PRESET',
        'preset_panel' : 'VIEW3D_PT_sculpt_voxel_remesh'
    },
    {
        'id': 'MASK_CLEAR',
        'name' : "Mask Clear",
        'image_path' : join(icons_dir, 'maskClear_icon.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MASK_CLEAR',
        'custom_identifier' : "paint.mask_flood_fill#mode='VALUE', value=0"
    },
    {
        'id': 'MASK_INVERT',
        'name' : "Mask Invert",
        'image_path' : join(icons_dir, 'maskInvert_icon.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MASK_INVERT',
        'custom_identifier' : "paint.mask_flood_fill#mode='INVERT'"
    },
    {
        'id': 'MASK_SHARP',
        'name' : "Mask Sharp",
        'image_path' : join(icons_dir, 'maskSharp_icon.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MF_SHARPEN',
        'custom_identifier' : "sculpt.mask_filter#filter_type='SHARPEN', auto_iteration_count=True"
    },
    {
        'id': 'MASK_SMOOTH',
        'name' : "Mask Smooth",
        'image_path' : join(icons_dir, 'maskSmooth2_icon.png'),
        'type' : 'OPERATOR',
        'as_attribute' : 'PRESET',
        'preset_operator' : '_MF_SMOOTH',
        'custom_identifier' : "sculpt.mask_filter#filter_type='SMOOTH', auto_iteration_count=True"
    }
)
