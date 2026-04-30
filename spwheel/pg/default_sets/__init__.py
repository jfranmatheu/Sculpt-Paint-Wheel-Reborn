from .sculpt_defaults import *
from .weight_defaults import *


_tarta_sets = {
    'SCULPT': def_sculpt_buttons,
    'WEIGHT': def_weight_buttons,
}

_brush_sets = {
    'SCULPT': def_sculpt_tools,
    'WEIGHT': None,
}


def get_tarta_set(mode: str):
    return _tarta_sets[mode]


def get_brush_set(mode: str):
    return _brush_sets[mode]
