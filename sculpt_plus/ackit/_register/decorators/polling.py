from typing import Type
from enum import Enum, auto

from ..types.ops import T  # Operator type.


__all__ = ['Polling']


class Polling:

    @staticmethod
    def _decorator(polling_function: callable):
        """ Add polling function to the decorated class. """

        def wrapper(cls: Type[T]) -> Type[T]:
            if not hasattr(cls, 'poll'):
                # Does not apply to the current class.
                return cls
            # NOTE: Operator.poll() should handle the execution of the '_polling_functions'.
            if not hasattr(cls, '_polling_functions') or cls._polling_functions is None:
                cls._polling_functions = set()
            cls._polling_functions.add(polling_function)
            return cls

        return wrapper

    class ACTIVE_OBJECT(Enum):
        """ Executes only if the active object is valid. """
        ANY = auto()
        # https://docs.blender.org/api/current/bpy_types_enum_items/object_type_items.html#object-type-items
        MESH = auto()
        CURVE = auto()
        SURFACE = auto()
        META = auto()
        FONT = auto()
        CURVES = auto()
        POINTCLOUD = auto()
        VOLUME = auto()
        GPENCIL = auto()
        GREASEPENCIL = auto()
        ARMATURE = auto()
        LATTICE = auto()
        EMPTY = auto()
        LIGHT = auto()
        LIGHT_PROBE = auto()
        CAMERA = auto()
        SPEAKER = auto()

        def __call__(self, cls: Type[T]) -> Type[T]:
            """ Applies the active object check for the current type. """
            if self.name == 'ANY':
                return Polling._decorator(lambda ctx: ctx.active_object is not None)(cls)
            else:
                return Polling._decorator(lambda ctx: ctx.active_object is not None and ctx.active_object.type == self.name)(cls)

    class MODE(Enum):
        """ Executes only if the mode in current context matches the selected mode.

            ### Example:
            ```
                @Polling.MODE.OBJECT
                @Register.OPS.GENERIC
                class MyOperator:
            ```
        """
        # https://docs.blender.org/api/current/bpy_types_enum_items/context_mode_items.html#rna-enum-context-mode-items
        EDIT_MESH = auto()
        EDIT_CURVE = auto()
        EDIT_CURVES = auto()
        EDIT_SURFACE = auto()
        EDIT_TEXT = auto()
        EDIT_ARMATURE = auto()
        EDIT_METABALL = auto()
        EDIT_LATTICE = auto()
        EDIT_GREASE_PENCIL = auto()
        EDIT_POINT_CLOUD = auto()
        POSE = auto()
        SCULPT = auto()
        PAINT_WEIGHT = auto()
        PAINT_VERTEX = auto()
        PAINT_TEXTURE = auto()
        PARTICLE = auto()
        OBJECT = auto()
        PAINT_GPENCIL = auto()
        EDIT_GPENCIL = auto()
        SCULPT_GPENCIL = auto()
        WEIGHT_GPENCIL = auto()
        VERTEX_GPENCIL = auto()
        SCULPT_CURVES = auto()
        PAINT_GREASE_PENCIL = auto()
        SCULPT_GREASE_PENCIL = auto()
        WEIGHT_GREASE_PENCIL = auto()
        VERTEX_GREASE_PENCIL = auto()

        def __call__(self, cls: Type[T]) -> Type[T]:
            """ Executes only if the mode in current context matches the specified mode. """
            return Polling._decorator(lambda ctx: ctx.mode == self.name)(cls)
