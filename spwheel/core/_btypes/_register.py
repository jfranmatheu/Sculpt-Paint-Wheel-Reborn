"""Register/Unregister bpy types defined in this extension"""

from collections import defaultdict
from pprint import pprint
from typing import get_type_hints

from _bpy_types import PropertyGroup
import bpy
from bpy.types import WorkSpaceTool
from bpy.utils import register_class, unregister_class, register_tool, unregister_tool

from ..debug import print_debug, CM_PrintDebugDeferred
from ...core import GLOBALS
from ._base import BType
from ..utils.class_utils import get_subclasses_recursive
from .data.btype_pg import BType_PropertyGroup, BType_PGRoot


classes_per_btype = defaultdict(list)
registered_classes_per_btype = defaultdict(list)
pg_root_groups = defaultdict(list)
registered_pg_pointers = []
registered_master_pg_classes = []

def get_classes_per_btype():
    global classes_per_btype
    return classes_per_btype

def add_class(cls):
    global classes_per_btype
    classes_per_btype[cls.bpy_type].append(cls)


def init():
    """ Initialize the bpy types defined in this extension. """
    print_debug("🅱️  BTYPE INITIALIZATION PROCESS ++++++++++++++++++++++++++++++++++++++++++++++++++++++")

    if classes_per_btype:
        # Valid data was previously loaded and its persistence is unknown.
        # Clear it to avoid confusion and potential errors.
        classes_per_btype.clear()
        pg_root_groups.clear()
        registered_pg_pointers.clear()
        registered_master_pg_classes.clear()
        registered_classes_per_btype.clear()

    # Tag-Register all classes that inherit from BType
    print_debug("1. Tag-Registering all classes that inherit from BType...", indent=1)
    for cls in get_subclasses_recursive(BType, only_last=True, exclude_from_module=GLOBALS.ADDON.CORE_PACKAGE_NAME):
        # NOTE: tag_register might return the class itself or a Runtime-created (dynamic type) one!
        if cls._skip_register:
            continue
        '''if hasattr(cls, 'bl_idname') and cls.bl_idname:
            (f"Warning: class '{cls.__name__}' has a bl_idname. It will be skipped.")
            continue'''
        with CM_PrintDebugDeferred() as print_bypass:
            if new_cls := cls.tag_register():
                print_bypass(f"🟢 '{new_cls.__name__}({new_cls.bpy_type})'", indent=2)
                add_class(new_cls)
            else:
                print_bypass(f"🔴 '{cls.__name__}({new_cls.bpy_type})'", indent=2)

    print_debug("1.1. Classes per BType:")
    pprint(classes_per_btype)

    # Sort PropertyGroup classes hierarchically!
    if pg_classes := classes_per_btype.get(PropertyGroup):
        print_debug(f"2. Sorting PropertyGroup classes hierarchically... ({len(pg_classes)})", indent=1)
        pg_classes = sort_property_group_classes(pg_classes)
        classes_per_btype[PropertyGroup] = pg_classes

        # Link children PropertyGroups recursively
        for cls in classes_per_btype.get(bpy.types.AddonPreferences, []):
            set_pg_parent_recursively(cls)
        for cls in pg_classes:
            set_pg_parent_recursively(cls)

        # Group ROOT PropertyGroups by their pg_root_type
        print_debug(f"3. Grouping PropertyGroup classes by their pg_root_type...", indent=1)
        pg_root_groups.clear()
        for cls in pg_classes:
            if getattr(cls, 'pg_role', None) != 'ROOT':
                continue
            if pg_root_type := getattr(cls, 'pg_root_type', None):
                pg_root_groups[pg_root_type].append(cls)
                print_debug(f"* Grouped '{cls.__name__}' under 'bpy.types.{pg_root_type.__name__}'", indent=2)

    print_debug(f"++++++++++++++++++++++++++++++++++++++++++++++++++++++", indent=1)


def _bpy_register_phase(bpy_type) -> int:
    """Lower phase registers first. PropertyGroups must precede AddonPreferences (PointerProperty)."""
    if bpy_type is None:
        return 1
    name = getattr(bpy_type, "__name__", "")
    # Compare by name: dict keys may be bpy.types.* while PropertyGroup is from _bpy_types.
    if name == "PropertyGroup":
        return 0
    if name == "AddonPreferences":
        return 2
    return 1


def _iter_classes_per_btype_register_order():
    items = list(get_classes_per_btype().items())
    items.sort(key=lambda it: (_bpy_register_phase(it[0]), getattr(it[0], "__name__", "")))
    return items


def _iter_registered_per_btype_unregister_order():
    """Unregister AddonPreferences before PropertyGroups that they reference."""
    items = list(registered_classes_per_btype.items())
    items.sort(key=lambda it: (-_bpy_register_phase(it[0]), getattr(it[0], "__name__", "")))
    return items


def register():
    print_debug("🅱️  BTYPE REGISTERING PROCESS ++++++++++++++++++++++++++++++++++++++++++++++++++++++")

    print_debug(f"1. Registering all classes that inherit from BType...", indent=1)
    # Register all classes that inherit from BType
    for bpy_type, cls_list in _iter_classes_per_btype_register_order():
        if bpy_type is None:
            continue
        if bpy_type == WorkSpaceTool:
            reg_fn = lambda _cls: register_tool(_cls, **_cls.register_kwargs)
            # Sort classes by their order in the group.
            groups = {tool_cls.group for tool_cls in cls_list if tool_cls.group}
            ungrouped_tools = [tool_cls for tool_cls in cls_list if tool_cls.group is None]
            cls_list = ungrouped_tools
            for group in groups:
                cls_list.extend(group.ordered_tools)
        else:
            reg_fn = register_class
        for cls in cls_list:
            try:
                if cls._skip_register:
                    continue
                cls.on_register()
                reg_fn(cls)
                registered_classes_per_btype[bpy_type].append(cls)
                print_debug(f"🟢 '{cls.__name__}({bpy_type})' - Idname: '{cls.bl_idname}'", indent=2)
            except Exception as e:
                print_debug(f"🔴 '{cls.__name__}({bpy_type})' - Error: {e}", indent=2)

    print_debug(f"2. Registering MASTER PropertyGroup classes...", indent=1)
    # Define a MASTER PropertyGroup per pg_root_type and attach it under the root datapath.
    root_prop_name = GLOBALS.ADDON.DEFAULT_ROOT_PROP_GROUP_DATAPATH
    for root_type, root_pg_list in pg_root_groups.items():
        if not root_pg_list:
            continue
        print_debug(f"* {root_type}: {[cls.__name__ for cls in root_pg_list]}", indent=2)
        annotations = {}
        for cls in root_pg_list:
            prop_name = getattr(cls, 'get_name', lambda: cls.__name__.lower())()
            annotations[prop_name] = bpy.props.PointerProperty(type=cls)
        MasterPG = type(
            f"{GLOBALS.ADDON.ID_UPPER}_PG_MASTER_{root_type.__name__.lower()}",
            (bpy.types.PropertyGroup,),
            {
                "__annotations__": annotations,
                "_skip_register": True,
                'pg_role': 'MASTER'
            }
        )
        register_class(MasterPG)
        registered_master_pg_classes.append(MasterPG)
        setattr(root_type, root_prop_name, bpy.props.PointerProperty(type=MasterPG))
        registered_pg_pointers.append((root_type, root_prop_name))
        
    print_debug(f"++++++++++++++++++++++++++++++++++++++++++++++++++++++", indent=1)

def unregister():
    print_debug("🅱️  BTYPE UNREGISTERING PROCESS ++++++++++++++++++++++++++++++++++++++++++++++++++++++")

    print_debug(f"1. Unregistering all classes that inherit from BType...", indent=1)
    # Unregister all classes that inherit from BType
    for bpy_type, cls_list in _iter_registered_per_btype_unregister_order():
        if bpy_type is None:
            continue
        if bpy_type == WorkSpaceTool:
            unreg_fn = unregister_tool
        else:
            unreg_fn = unregister_class
        for cls in cls_list:
            try:
                if cls._skip_register:
                    continue
                cls.on_unregister()
                unreg_fn(cls)
                print_debug(f"🟢 '{cls.__name__}({bpy_type})", indent=2)
            except Exception as e:
                print_debug(f"🔴 '{cls.__name__}({bpy_type})' - Error: {e}", indent=2)

    print_debug(f"2. Removing MASTER PropertyGroup attributes...", indent=1)
    # Remove the pointer properties to the MASTER PropertyGroup classes.
    for root_type, prop_name in registered_pg_pointers:
        delattr(root_type, prop_name)

    registered_classes_per_btype.clear()
    registered_pg_pointers.clear()

    print_debug(f"3. Unregistering MASTER PropertyGroup classes...", indent=1)
    # Unregister MASTER PropertyGroup classes.
    while registered_master_pg_classes:
        cls = registered_master_pg_classes.pop()
        try:
            unregister_class(cls)
        except Exception as e:
            print_debug(f"🔴 Failed to unregister master PropertyGroup {cls.__name__}: {e}", indent=2)

    print_debug(f"++++++++++++++++++++++++++++++++++++++++++++++++++++++", indent=1)


# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------

def sort_property_group_classes(pg_classes) -> list:
    my_classes = set(pg_classes)
    my_classes_by_idname = {cls.bl_idname : cls for cls in pg_classes if hasattr(cls, "bl_idname")}

    deps_dict = {}
    for cls in my_classes:
        deps_dict[cls] = set(iter_my_register_deps(cls, my_classes, my_classes_by_idname))

    return toposort(deps_dict)

def iter_my_register_deps(cls, my_classes, my_classes_by_idname):
    yield from iter_my_deps_from_annotations(cls, my_classes)
    yield from iter_my_deps_from_parent_id(cls, my_classes_by_idname)

def iter_my_deps_from_annotations(cls, my_classes):
    for value in get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            if dependency in my_classes:
                yield dependency

def get_dependency_from_annotation(value):
    if isinstance(value, bpy.props._PropertyDeferred):
        return value.keywords.get("type")
    return None

def set_pg_parent_recursively(cls):
    """ Assign the `pg_parent` class attribute recursively for PropertyGroups inside annotations. """
    for key, value in get_type_hints(cls, {}, {}).items():
        if hasattr(value, "keywords"):
            child_cls = value.keywords.get("type")
            if child_cls and issubclass(child_cls, BType_PropertyGroup):
                child_cls.pg_prop_name = key
                child_cls.pg_parent = cls
                set_pg_parent_recursively(child_cls)

def iter_my_deps_from_parent_id(cls, my_classes_by_idname):
    if bpy.types.Panel in cls.__bases__:
        parent_idname = getattr(cls, "bl_parent_id", None)
        if parent_idname is not None:
            parent_cls = my_classes_by_idname.get(parent_idname)
            if parent_cls is not None:
                yield parent_cls

def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    while len(deps_dict) > 0:
        unsorted = []
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        deps_dict = {value : deps_dict[value] - sorted_values for value in unsorted}
    return sorted_list
