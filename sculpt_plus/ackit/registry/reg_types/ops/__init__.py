from typing import TypeVar

import bpy

from .generic import Generic as Operator
from .action import Action
from .modal import Modal


__all__ = [
    'Operator', 'Action', 'Modal',
    'T'
]


# Create a virtual type that combines bpy and ackit Operator types for proper typing.
T = TypeVar('T', bound=bpy.types.Operator | Operator)
