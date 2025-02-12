"""
These three files form the core registration system, with each having a distinct responsibility:
- addon_loader.py → Module loading and initialization
- auto_load.py → Legacy module loading (deprecated in favour of AddonLoader)
- btypes.py → Blender class management

You shall not use both AddonLoader and AutoLoad at the same time.
"""

from .addon_loader import AddonLoader
from .auto_load import AutoLoad
from .btypes import BTypes


__all__ = [
    'AddonLoader',
    'AutoLoad'
]
