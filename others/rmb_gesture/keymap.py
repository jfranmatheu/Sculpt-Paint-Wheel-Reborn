"""Keymap: Sculpt mode, right mouse click-drag."""

import bpy

_addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


def register() -> None:
    from .op_rmb_sculpt_gesture import RmbSculptGestureOperator

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return

    km = kc.keymaps.new(name="Sculpt", space_type="EMPTY")
    kmi = km.keymap_items.new(
        RmbSculptGestureOperator.bl_idname,
        type="RIGHTMOUSE",
        value="CLICK_DRAG",
    )
    _addon_keymaps.append((km, kmi))

    kms = bpy.context.window_manager.keyconfigs.user.keymaps
    km = kms.get('Sculpt', None)
    if km is not None:
        for kmi in km.keymap_items:
            if kmi.idname == 'wm.call_panel' and kmi.properties['name'] == 'VIEW3D_PT_sculpt_context_menu':
                if kmi.value != 'CLICK':
                    kmi.value = 'CLICK'


def unregister() -> None:
    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)
    _addon_keymaps.clear()
    
    kms = bpy.context.window_manager.keyconfigs.user.keymaps
    km = kms.get('Sculpt', None)
    if km is not None:
        for kmi in km.keymap_items:
            if kmi.idname == 'wm.call_panel' and kmi.properties['name'] == 'VIEW3D_PT_sculpt_context_menu':
                if kmi.value != 'PRESS':
                    kmi.value = 'PRESS'
