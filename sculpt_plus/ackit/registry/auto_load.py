from bpy.utils import register_class, unregister_class

from ..globals import GLOBALS
from .utils import get_all_submodules
from .utils import get_ordered_classes_to_register

__all__ = [
    'AutoLoad',
]


class AutoLoad:
    """# Auto-Load

    Utility class for automatically fetching and registering Blender bpy classes.

    ## WARNING
    - Legacy method. Recommended to use `AddonLoader` instead!
    - In case of using, DO NOT use in combination with `AddonLoader` !!!

    ## HOW TO USE:
    - 1. Call `AutoLoad.init_modules()` in the root `__init__.py` file of your addon/extension.
    - 2. Call `AutoLoad.register_modules()` in a `register()` function inside your root `__init__.py`.
    - 3. Call `AutoLoad.unregister_modules()` in a `unregister()` function inside your root `__init__.py`.

    - In the modules of your addon you can add ``register()`` and ``unregister()`` methods
    that will be automatically called by the ``AutoLoad`` when addon registering and unregistering events occur.
    """

    modules = None
    ordered_classes = None

    @classmethod
    def init_autoload(cls):
        cls.modules = get_all_submodules(GLOBALS.ADDON_SOURCE_PATH)
        cls.ordered_classes = get_ordered_classes_to_register(cls.modules)

    @classmethod
    def register_autoload(cls):
        for cls in cls.ordered_classes:
            register_class(cls)

        for module in cls.modules:
            if hasattr(module, "register"):
                module.register()

    @classmethod
    def unregister_autoload(cls):
        for cls in reversed(cls.ordered_classes):
            unregister_class(cls)

        for module in cls.modules:
            if hasattr(module, "unregister"):
                module.unregister()
