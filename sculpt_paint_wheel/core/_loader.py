import importlib
import pkgutil
import sys
from typing import Callable, Tuple

from .globals import PATHS, GLOBALS
from ._auto_code import AutoCode


__all__ = [
    "AddonLoader",
    "register",
    "unregister",
]

addon_root_package_name = GLOBALS.ADDON.PACKAGE_NAME


class AddonLoader:
    modules = None
    registered = False

    @classmethod
    def init(cls) -> Tuple[Callable, Callable]:
        """ Initialize the addon modules. """
        if GLOBALS.IN_BACKGROUND and not GLOBALS.ADDON.WORKS_IN_BACKGROUND:
            return lambda: print(f"[{GLOBALS.ADDON.NAME}] extension does not work in background."), lambda: None

        if 'ICONS' in GLOBALS.ADDON.AUTO_CODE_OPTIONS:
            AutoCode.ICONS()

        cls.modules = get_all_submodules(PATHS.ROOT)
        cls.registered = False

        for module in cls.modules:
            # When you need to initialize something specific in this module.
            if hasattr(module, "init"):
                module.init()

        for module in cls.modules:
            # When you need to initialize something that depends on another module initialization.
            if hasattr(module, "late_init"):
                module.late_init()

        return cls.register, cls.unregister

    @classmethod
    def cleanse_modules(cls):
        """search for your plugin modules in blender python sys.modules and remove them"""
        all_modules = sys.modules 
        all_modules = dict(sorted(all_modules.items(),key= lambda x:x[0])) #sort them
        for k, v in all_modules.items():
            if k.startswith(addon_root_package_name):
                del sys.modules[k]

    @classmethod
    def register(cls):
        """ Register the addon modules. """
        if cls.registered:
            return
        if cls.modules is None:
            cls.init()
        if cls.registered:
            return
        for module in cls.modules:
            if hasattr(module, "register"):
                module.register()
        for module in cls.modules:
            if hasattr(module, "late_register"):
                module.late_register()
        cls.registered = True

    @classmethod
    def unregister(cls):
        """ Unregister the addon modules. """
        if not cls.registered:
            return
        for module in cls.modules:
            if hasattr(module, "unregister"):
                module.unregister()
            if module.__name__ == __name__:
                continue
        for module in cls.modules:
            if hasattr(module, "late_unregister"):
                module.late_unregister()
        cls.registered = False
        cls.modules = None
        cls.cleanse_modules()


# Import modules
#################################################

def get_all_submodules(directory):
    return list(iter_submodules(directory, GLOBALS.ADDON.PACKAGE_NAME))

def iter_submodules(path, package_name):
    for name in sorted(iter_submodule_names(path)):
        yield importlib.import_module("." + name, package_name)

def iter_submodule_names(path, root=""):
    for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
        if is_package:
            sub_path = path / module_name
            sub_root = root + module_name + "."
            yield from iter_submodule_names(sub_path, sub_root)
        else:
            yield root + module_name
