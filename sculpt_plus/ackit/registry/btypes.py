""" Module used to register new custom wrapper classes based on Blender types. """

from bpy.utils import register_class, unregister_class, register_classes_factory

from enum import Enum, auto
from typing import Dict, List, Type, Callable
from collections import defaultdict
from dataclasses import dataclass

from ..debug.output import print_debug
from .utils import get_ordered_pg_classes_to_register

__all__ = [
    'BTypes',
]

# Register/Unregister classes with classes_factory functions.
FACTORY_REGISTER = False

classes_per_type: Dict['BTypes', List[Type]] = defaultdict(list)
register_factory: Dict['BTypes', 'RegisterFactory'] = {}


@dataclass
class RegisterFactory:
    register: Callable
    unregister: Callable


class BTypes(Enum):
    """ Supported types. """
    Operator = auto()
    Macro = auto()
    UIList = auto()
    Menu = auto()
    Panel = auto()
    PropertyGroup = auto()
    AddonPreferences = auto()
    NodeTree = auto()
    NodeSocket = auto()
    Node = auto()
    Gizmo = auto()
    GizmoGroup = auto()

    def get_classes(self) -> List[Type]:
        return classes_per_type[self]

    def sort_classes(self, filter: Callable) -> None:
        classes_per_type[self] = filter(self.get_classes())

    def add_class(self, cls) -> None:
        print_debug(f"New {self.name} class : {cls.__name__}")
        classes_per_type[self].append(cls)

    def register_classes(self) -> None:
        if reg_factory := register_factory.get(self, None):
            print_debug(f"Register {self.name} classes")
            reg_factory.register()
        else:
            for cls in classes_per_type[self]:
                print_debug(f"Register {self.name} class: {cls.__name__}")
                register_class(cls)

    def unregister_classes(self) -> None:
        if reg_factory := register_factory.get(self, None):
            reg_factory.unregister()
        else:
            for cls in classes_per_type[self]:
                if "bl_rna" in cls.__dict__:
                    print_debug(f"UNRegister {self.name} class: {cls.__name__}")
                    unregister_class(cls)

    def create_classes_factory(self):
        register_factory[self] = RegisterFactory(*register_classes_factory(classes_per_type[self]))
        
    @staticmethod
    def clear_cache():
        classes_per_type.clear()
        register_factory.clear()


# ----------------------------------------------------------------

def late_init():
    # Sort property group classes to avoid any dependency issues.
    BTypes.PropertyGroup.sort_classes(get_ordered_pg_classes_to_register)

    if FACTORY_REGISTER:
        for btype in BTypes:
            btype.create_classes_factory()


def register():
    for btype in BTypes:
        btype.register_classes()


def unregister():
    for btype in BTypes:
        btype.unregister_classes()

    BTypes.clear_cache()
