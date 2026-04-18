"""Base type for this extension's bpy.types-based classes"""

from typing import Type, Tuple, Dict, Any
import re

import bpy

from ..globals import GLOBALS
from ..debug import print_debug


idname_pattern_per_bpy_type = {
    bpy.types.AddonPreferences: "{addon_package_name}",
    bpy.types.Panel: "{addon_id_upper}_PT_{class_name_lower}",
    bpy.types.Menu: "{addon_id_upper}_MT_{class_name_lower}",
    bpy.types.Gizmo: "{addon_id_upper}_GZ_{class_name_lower}",
    bpy.types.GizmoGroup: "{addon_id_upper}_GZG_{class_name_lower}",
    bpy.types.PropertyGroup: "{addon_id_upper}_PG_{class_name_lower}",
    bpy.types.WorkSpaceTool: "{addon_id}.{class_name_lower}",
    bpy.types.Operator: "{addon_id}.{class_name_lower}", # "{addon_id_upper}_OT_{class_name_lower}",
    bpy.types.NodeTree: "{addon_id_upper}_NT_{class_name_lower}",
    bpy.types.Node: "{addon_id_upper}_ND_{class_name_lower}",
    bpy.types.NodeSocket: "{addon_id_upper}_NS_{class_name_lower}",
    bpy.types.UIList: "{addon_id_upper}_UL_{class_name_lower}",
}


class BTypeMeta:
    bl_idname: str
    bl_label: str


class BType:
    bpy_type: Type[bpy.types.ID] | None = None
    _skip_register: bool = False

    @classmethod
    def tag_register(cls, **kwargs: Dict[str, Any]) -> Type[BTypeMeta]:
        """ Internal method to tag-register the class. """
        # Find the first base class that has a registered bl_rna.
        # print_debug(f"TAG-REGISTER '{cls.__name__}' with bases: {[base.__name__ for base in cls.__mro__]}")
        for base_cls in reversed(cls.__mro__):
            if base_cls.__name__ in {'object', 'bpy_struct', 'BType', cls.__name__}:
                continue
            if base_cls.__name__.startswith('BType'):
                continue
            if hasattr(base_cls, "bl_rna") and hasattr(bpy.types, base_cls.__name__):
                cls.bpy_type = base_cls
                # print_debug(f"Found bpy_type: {cls.bpy_type.__name__} for {cls.__name__}")
                break
        if cls.bpy_type is None:
            # print_debug(f"Warning: {cls.__name__} has no bpy_type set.")
            return
        if idname_pattern := idname_pattern_per_bpy_type.get(cls.bpy_type, None):
            idname = idname_pattern.format(
                addon_id_upper=GLOBALS.ADDON.ID_UPPER,
                addon_id=GLOBALS.ADDON.ID,
                class_name_lower=cls.__name__.lower(),
                addon_package_name=GLOBALS.ADDON.PACKAGE_NAME,
            )
            cls.bl_idname = idname
            if not hasattr(cls, "bl_label") or not cls.bl_label:
                cls.bl_label = label_from_class_name(cls.__name__)

        for key, value in kwargs.items():
            setattr(cls, key, value)

        # print(f"Tag-registering {cls.__name__} with idname: {cls.bl_idname}")
        return cls

    @classmethod
    def on_register(cls):
        pass

    @classmethod
    def on_unregister(cls):
        pass

    @classmethod
    def decorator(cls, *args, **kwargs) -> Type[BTypeMeta]:
        def decorator(decorated_cls: Type[BType]) -> Type[BTypeMeta]:
            if issubclass(decorated_cls, cls):
                if kwargs:
                    # Update the decorated class with the new kwargs.
                    for key, value in kwargs.items():
                        setattr(decorated_cls, key, value)
                # No need to create a new class if the decorated class is already a subclass of cls.
                return decorated_cls
            new_cls = type(
                cls.__name__,
                (decorated_cls, cls),
                kwargs,
            )
            new_cls.__module__ = decorated_cls.__module__
            return new_cls
        return decorator


'''def create_bpy_type(cls: Type[BType], base_classes: Tuple[Type] = (), **kwargs: Dict[str, Any]) -> Type[BTypeMeta]:
    """ Create the bpy.type class. """
    bases = (bpy_type, *base_classes, cls)
    new_cls = type(f"B_{cls.__name__}", bases, kwargs)
    new_cls.__module__ = cls.__module__  # Set the module to the same as the base class
    return new_cls'''


def label_from_class_name(name: str) -> str:
    parts = name.split("_")
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        words = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", part)
        merged: list[str] = []
        i = 0
        while i < len(words):
            w = words[i]
            if len(w) == 1 and w.isupper() and i + 1 < len(words) and words[i + 1][0].isupper():
                merged.append(w + words[i + 1])
                i += 2
            else:
                merged.append(w)
                i += 1
        out.extend(merged)
    return " ".join(out)
