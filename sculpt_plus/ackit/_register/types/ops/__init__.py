from typing import TypeVar

import bpy

from .ot_generic import Generic as Operator
from .ot_action import Action
from .ot_modal import Modal


__all__ = [
    'Operator', 'Action', 'Modal',
    'T'
]


# Create a virtual type that combines bpy and ackit Operator types for proper typing.
T = TypeVar('T', bound=bpy.types.Operator | Operator)
