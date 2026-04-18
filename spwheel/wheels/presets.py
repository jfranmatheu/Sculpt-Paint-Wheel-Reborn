from .sculpt.sculpt_presets import preset_menus_sculpt, preset_panels_sculpt, preset_operators_sculpt


preset_type_per_mode = {
    "SCULPT": (preset_menus_sculpt, preset_panels_sculpt, preset_operators_sculpt),
}


__all__ = [
    "preset_type_per_mode",
]
