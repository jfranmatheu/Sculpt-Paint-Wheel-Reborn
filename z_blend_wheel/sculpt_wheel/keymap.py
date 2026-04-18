"""Keymap registration for the sculpt wheel."""

import bpy

_addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


def register() -> None:
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return

    km = kc.keymaps.new(name='Sculpt', space_type='EMPTY')
    kmi = km.keymap_items.new(
        'sculpt_plus.sculptwheeloperator',
        type='SPACE',
        value='PRESS',
    )
    _addon_keymaps.append((km, kmi))


def unregister() -> None:
    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)
    _addon_keymaps.clear()
