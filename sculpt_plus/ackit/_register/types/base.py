import re
from typing import Type, List

import bpy

from ..._globals import GLOBALS
from ...debug import print_debug
from ...utils.classes import get_subclasses_recursive
from ..register import BTypes


__all__ = [
    'BaseType'
]


class BaseType(object):
    original_name: str
    original_cls: Type
    registered: bool = False

    @classmethod
    def __subclasses_recursive__(cls) -> List['BaseType']:
        return get_subclasses_recursive(cls, only_outermost=True)

    @classmethod
    def tag_register(cls, bpy_type: type | str, type_key: str | None, *subtypes, **kwargs):
        if cls.registered:
            return cls

        if isinstance(bpy_type, str):
            bpy_type = getattr(bpy.types, bpy_type)

        print_debug(f"--> Tag-Register class '{cls.__name__}' of type '{bpy_type.__name__} --> Package: {cls.__module__}'")

        # Modify/Extend original class.
        if type_key is not None:
            # Identify the words at the original class name,
            # useful to create unique identifiers in the correct naming convention.
            pattern = r'[A-Z][a-z]*|[a-zA-Z]+'
            keywords = re.findall(pattern, cls.__name__)
            idname: str = '_'.join([word.lower() for word in keywords])

            # CLass name if a bpy-type key is specified. (eg. UL, PT, MT, OT, GZ, GZG, etc.)
            cls_name = f'{GLOBALS.ADDON_MODULE_UPPER}_{type_key}_{idname}'

            # Check if the original class has specified a label and description/tooltip attributes.
            if not hasattr(cls, 'bl_label') or not cls.bl_label:
                cls.bl_label = cls.label if hasattr(cls, 'label') else ' '.join(keywords)
            if not hasattr(cls, 'bl_description') or not cls.bl_label:
                cls.bl_description = cls.tooltip if hasattr(cls, 'tooltip') else cls.description if hasattr(cls, 'description') else ''

            # Some bpy types may require a bl_idname.
            if bpy_type == bpy.types.Operator:
                # Operator types idname should have an specific naming convention.
                cls.bl_idname = f"{GLOBALS.ADDON_MODULE_SHORT.lower()}.{idname}"

            elif bpy_type in {bpy.types.Menu, bpy.types.Panel, bpy.types.UIList}:
                # In the case of interface bpy.types, we can re-use the class name for the idname.
                cls.bl_idname = cls_name
        else:
            if bpy_type == bpy.types.AddonPreferences:
                # We override the original's class name for a name convention one.
                cls_name = f'{GLOBALS.ADDON_MODULE_UPPER}_AddonPreferences'
                cls.bl_idname = GLOBALS.ADDON_MODULE
            else:
                # This case is for unhandled bpy_types. We re-use the original's class name.
                cls_name = cls.__name__ # f'{GLOBALS.ADDON_MODULE_UPPER}_{idname}'

        # Preserve original class data.
        kwargs['original_name'] = cls.__name__
        kwargs['original_cls'] = cls

        # Mark as registered, same for newly created type (based on bpy_types).
        cls.registered = True
        kwargs['registered'] = True

        # Create new Blender type to be registered.
        new_cls = type(
            cls_name,
            (cls, *subtypes, bpy_type),
            kwargs
        )

        # Preserve original module to avoid issues excluding new classes due to being inside of '/types' directory!
        new_cls.__module__ = cls.__module__

        # Add this new class to be registered as a new BType (Blender type).
        btype: BTypes = getattr(BTypes, bpy_type.__name__)
        btype.add_class(new_cls)

        return new_cls


# ----------------------------------------------------------------

def init():
    for subcls in BaseType.__subclasses_recursive__():
        if 'types' in subcls.__module__:
           # SKIP: IF THE SUBCLASS IS INSIDE THE addon_utils module or inside any folder called 'types'.
           continue
        subcls.tag_register()
