from .sculpt_defaults import def_sculpt_buttons, def_sculpt_tools
from .sculpt_curves_defaults import def_sculpt_curves_buttons, def_sculpt_curves_tools
from .sculpt_grease_pencil_defaults import def_sculpt_grease_pencil_buttons, def_sculpt_grease_pencil_tools

from .weight_defaults import def_weight_buttons
from .weight_grease_pencil_defaults import def_weight_grease_pencil_buttons, def_weight_grease_pencil_tools

from .paint_texture_defaults import def_paint_texture_buttons, def_paint_texture_tools
from .paint_vertex_defaults import def_paint_vertex_buttons, def_paint_vertex_tools
from .paint_grease_pencil_defaults import def_paint_grease_pencil_buttons, def_paint_grease_pencil_tools
from .vertex_grease_pencil_defaults import def_vertex_grease_pencil_buttons, def_vertex_grease_pencil_tools
from .masking_defaults import MASKING_SET_NAME, def_sculpt_masking_buttons

# Keys are `context.mode` values.
_tarta_sets = {
    'SCULPT': def_sculpt_buttons,
    'SCULPT_CURVES': def_sculpt_curves_buttons,
    'SCULPT_GREASE_PENCIL': def_sculpt_grease_pencil_buttons,
    'PAINT_WEIGHT': def_weight_buttons,
    'WEIGHT_GREASE_PENCIL': def_weight_grease_pencil_buttons,
    'PAINT_TEXTURE': def_paint_texture_buttons,
    'PAINT_VERTEX': def_paint_vertex_buttons,
    'PAINT_GREASE_PENCIL': def_paint_grease_pencil_buttons,
    'VERTEX_GREASE_PENCIL': def_vertex_grease_pencil_buttons,
}

# Second default set ("Masking"), Sculpt only.
_masking_sets = {
    'SCULPT': def_sculpt_masking_buttons,
}

_brush_sets = {
    'SCULPT': def_sculpt_tools,
    'SCULPT_CURVES': def_sculpt_curves_tools,
    'SCULPT_GREASE_PENCIL': def_sculpt_grease_pencil_tools,
    'PAINT_WEIGHT': None,
    'WEIGHT_GREASE_PENCIL': def_weight_grease_pencil_tools,
    'PAINT_TEXTURE': def_paint_texture_tools,
    'PAINT_VERTEX': def_paint_vertex_tools,
    'PAINT_GREASE_PENCIL': def_paint_grease_pencil_tools,
    'VERTEX_GREASE_PENCIL': def_vertex_grease_pencil_tools,
}


def get_tarta_set(mode: str):
    return _tarta_sets.get(mode)


def get_masking_set(mode: str):
    return _masking_sets.get(mode)


def get_brush_set(mode: str):
    return _brush_sets.get(mode)
