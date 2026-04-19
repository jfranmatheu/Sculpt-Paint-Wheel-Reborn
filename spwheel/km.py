from .ops.op_wheel_modal import WheelModal


modes = {
    'Image Paint',
    'Vertex Paint',
    'Weight Paint',
    'Sculpt',
    'Grease Pencil Stroke Paint Mode',
    'Grease Pencil Stroke Vertex Mode',
    'Grease Pencil Stroke Weight Mode'
}

#addon_keymaps = []
def late_register():
    op_id = WheelModal.bl_idname
    from bpy import context as C
    cfg = C.window_manager.keyconfigs.addon
    for mode_km in modes:
        if not cfg.keymaps.__contains__(mode_km):
            km = cfg.keymaps.new(name=mode_km, space_type='EMPTY', region_type='WINDOW')
        else:
            km = cfg.keymaps[mode_km]
        kmi = km.keymap_items.new(op_id, type="SPACE", value = "PRESS", alt=int('alt' in mode_km))
        #addon_keymaps.append(km)

        #kmi.properties.name = "editor_switcher_pie_menu"
        #if not cfg.keymaps.__contains__(val['km']):
        #    cfg.keymaps.new(val['km']) #, space_type='EMPTY', region_type='WINDOW'
            #if 'Image' in val['km']:
            #    cfg.keymaps.new(val['km'], space_type='IMAGE_EDITOR', region_type='WINDOW')
        #kmi = cfg.keymaps[val['km']].keymap_items
        #kmi.new(val['op'], 'SPACE', 'PRESS')

def unregister():
    op_id = WheelModal.bl_idname
    import bpy
    #wm = bpy.context.window_manager
    #for km in addon_keymaps:
    #    for kmi in km.keymap_items:
    #        km.keymap_items.remove(kmi)
    #    wm.keyconfigs.addon.keymaps.remove(km)
    #addon_keymaps.clear()
    #return

    cfg = bpy.context.window_manager.keyconfigs.addon
    for mode_km in modes:
        if cfg.keymaps.__contains__(mode_km):
            for kmi in cfg.keymaps[mode_km].keymap_items:
                if kmi.idname == op_id:
                    cfg.keymaps[mode_km].keymap_items.remove(kmi)
                    break
