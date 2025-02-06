import inspect
import typing
import importlib
import pkgutil
from collections import defaultdict

import bpy


# Get/Find subclasses
########################################################################

def get_subclasses_recursive(base_cls, only_outermost: bool = False):
    all_subclasses = []

    def iter_subclasses(cls):
        nonlocal all_subclasses
        subclasses = cls.__subclasses__()
        if only_outermost and len(subclasses) == 0:
            all_subclasses.append(cls)
        else:
            for subclass in subclasses:
                if not only_outermost:
                    all_subclasses.append(subclass)
                iter_subclasses(subclass)

    iter_subclasses(base_cls)
    return all_subclasses


# Get/Find nested classes
########################################################################

def get_inner_classes(cls):
    return [cls_attribute for cls_attribute in cls.__dict__.values()
            if inspect.isclass(cls_attribute)]

def get_inner_classes_by_type(cls, cls_type: type):
    return [cls_attribute for cls_attribute in cls.__dict__.values()
            if inspect.isclass(cls_attribute)
            and issubclass(cls_attribute, cls_type)]


# Filter classes
########################################################################

def pack_classes_by_modules(classes: list, one_per_module: bool = False) -> typing.Dict[str, typing.List[typing.Type]]:
    if one_per_module:
        return {cls.__module__.split('.')[-2]: cls for cls in classes}
    d = defaultdict(list)
    for cls in classes:
        d[cls.__module__.split('.')[-2]].append(cls)
    return d

def get_ordered_pg_classes_to_register(classes) -> list:
    my_classes = set(classes)
    my_classes_by_idname = {cls.bl_idname : cls for cls in classes if hasattr(cls, "bl_idname")}

    deps_dict = {}
    for cls in my_classes:
        deps_dict[cls] = set(iter_my_register_deps(cls, my_classes, my_classes_by_idname))

    return toposort(deps_dict)


# Find classes to register
#################################################


def get_ordered_classes_to_register(modules):
    return toposort(get_register_deps_dict(modules))


def get_register_deps_dict(modules):
    my_classes = set(iter_my_classes(modules))
    my_classes_by_idname = {cls.bl_idname: cls for cls in my_classes if hasattr(cls, "bl_idname")}

    deps_dict = {}
    for cls in my_classes:
        deps_dict[cls] = set(iter_my_register_deps(cls, my_classes, my_classes_by_idname))
    return deps_dict


def iter_my_register_deps(cls, my_classes, my_classes_by_idname):
    yield from iter_my_deps_from_annotations(cls, my_classes)
    yield from iter_my_deps_from_parent_id(cls, my_classes_by_idname)


def iter_my_deps_from_annotations(cls, my_classes):
    for value in typing.get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            if dependency in my_classes:
                yield dependency


def get_dependency_from_annotation(value):
    if isinstance(value, bpy.props._PropertyDeferred):
        return value.keywords.get("type")
    return None


def iter_my_deps_from_parent_id(cls, my_classes_by_idname):
    if issubclass(cls, bpy.types.Panel):
        parent_idname = getattr(cls, "bl_parent_id", None)
        if parent_idname is not None:
            parent_cls = my_classes_by_idname.get(parent_idname)
            if parent_cls is not None:
                yield parent_cls


def iter_my_classes(modules):
    base_types = get_register_base_types()
    for cls in get_classes_in_modules(modules):
        if any(issubclass(cls, base) for base in base_types):
            if not getattr(cls, "is_registered", False):
                yield cls


def get_classes_in_modules(modules):
    classes = set()
    for module in modules:
        for cls in iter_classes_in_module(module):
            classes.add(cls)
    return classes


def iter_classes_in_module(module):
    for value in module.__dict__.values():
        if inspect.isclass(value):
            yield value

def get_register_base_types():
    return set(
        getattr(bpy.types, name)
        for name in [
            "Panel",
            "Operator",
            "PropertyGroup",
            "AddonPreferences",
            "Header",
            "Menu",
            "Node",
            "NodeSocket",
            "NodeTree",
            "UIList",
            "RenderEngine",
            "Gizmo",
            "GizmoGroup",
        ]
    )


# Find order to register to solve dependencies
#################################################

def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    while len(deps_dict) > 0:
        unsorted = []
        sorted_list_sub = []  # helper for additional sorting by bl_order - in panels
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list_sub.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        deps_dict = {value: deps_dict[value] - sorted_values for value in unsorted}
        sorted_list_sub.sort(key=lambda cls: getattr(cls, "bl_order", 0))
        sorted_list.extend(sorted_list_sub)
    return sorted_list
