from .sculpt.sculpt_presets import preset_menus_sculpt, preset_panels_sculpt, preset_operators_sculpt
from .weight.weight_presets import preset_menus_weight, preset_panels_weight, preset_operators_weight


preset_type_per_mode = {
    "SCULPT": (preset_menus_sculpt, preset_panels_sculpt, preset_operators_sculpt),
    "PAINT_WEIGHT": (preset_menus_weight, preset_panels_weight, preset_operators_weight),
    "WEIGHT_GPENCIL": (preset_menus_weight, preset_panels_weight, preset_operators_weight),
}


__all__ = [
    "preset_type_per_mode",
]
