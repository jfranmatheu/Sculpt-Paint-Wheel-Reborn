from .sculpt.sculpt_presets import preset_menus_sculpt, preset_panels_sculpt, preset_operators_sculpt
from .sculpt.sculpt_curves_presets import preset_menus_sculpt_curves, preset_panels_sculpt_curves, preset_operators_sculpt_curves
from .sculpt.sculpt_grease_pencil_presets import preset_menus_sculpt_grease_pencil, preset_panels_sculpt_grease_pencil, preset_operators_sculpt_grease_pencil
from .paint_texture.paint_texture_presets import preset_menus_paint_texture, preset_panels_paint_texture, preset_operators_paint_texture
from .paint_texture.paint_vertex_presets import preset_menus_paint_vertex, preset_panels_paint_vertex, preset_operators_paint_vertex
from .paint_texture.paint_grease_pencil_presets import preset_menus_paint_grease_pencil, preset_panels_paint_grease_pencil, preset_operators_paint_grease_pencil
from .paint_texture.vertex_grease_pencil_presets import preset_menus_vertex_grease_pencil, preset_panels_vertex_grease_pencil, preset_operators_vertex_grease_pencil
from .weight.weight_presets import preset_menus_weight, preset_panels_weight, preset_operators_weight
from .weight.weight_grease_pencil_presets import preset_menus_weight_grease_pencil, preset_panels_weight_grease_pencil, preset_operators_weight_grease_pencil


# Keys are `context.mode` values.
preset_type_per_mode = {
    "SCULPT": (preset_menus_sculpt, preset_panels_sculpt, preset_operators_sculpt),
    "SCULPT_CURVES": (preset_menus_sculpt_curves, preset_panels_sculpt_curves, preset_operators_sculpt_curves),
    "SCULPT_GREASE_PENCIL": (preset_menus_sculpt_grease_pencil, preset_panels_sculpt_grease_pencil, preset_operators_sculpt_grease_pencil),
    "PAINT_TEXTURE": (preset_menus_paint_texture, preset_panels_paint_texture, preset_operators_paint_texture),
    "PAINT_VERTEX": (preset_menus_paint_vertex, preset_panels_paint_vertex, preset_operators_paint_vertex),
    "PAINT_GREASE_PENCIL": (preset_menus_paint_grease_pencil, preset_panels_paint_grease_pencil, preset_operators_paint_grease_pencil),
    "VERTEX_GREASE_PENCIL": (preset_menus_vertex_grease_pencil, preset_panels_vertex_grease_pencil, preset_operators_vertex_grease_pencil),
    "PAINT_WEIGHT": (preset_menus_weight, preset_panels_weight, preset_operators_weight),
    "WEIGHT_GREASE_PENCIL": (preset_menus_weight_grease_pencil, preset_panels_weight_grease_pencil, preset_operators_weight_grease_pencil),
}


# Toggle buttons: (data path from the context, name, description). Mesh / curves symmetry for the modes that use it.
_MIRROR_TOGGLES = (
    ("object.data.use_mirror_x", "Mirror X", "Symmetry along X"),
    ("object.data.use_mirror_y", "Mirror Y", "Symmetry along Y"),
    ("object.data.use_mirror_z", "Mirror Z", "Symmetry along Z"),
)
preset_toggles_per_mode = {
    "SCULPT": _MIRROR_TOGGLES,
    "SCULPT_CURVES": _MIRROR_TOGGLES,
    "PAINT_TEXTURE": _MIRROR_TOGGLES,
    "PAINT_VERTEX": _MIRROR_TOGGLES,
    "PAINT_WEIGHT": _MIRROR_TOGGLES,
}

# Pressed state for preset operators that switch something on/off: operator id -> boolean data path.
preset_operator_states = {
    "sculpt.dynamic_topology_toggle": "object.use_dynamic_topology_sculpting",
}


__all__ = [
    "preset_type_per_mode",
    "preset_toggles_per_mode",
    "preset_operator_states",
]
