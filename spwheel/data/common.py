from pathlib import Path

import bpy

from ..core import GLOBALS


def get_cache_root() -> Path:
    """Return absolute path to cache root."""
    return Path(bpy.utils.resource_path("USER")) / GLOBALS.ADDON.ID / "cache"

def get_cache_path(*rel_path: str) -> Path:
    """Return absolute path to cache file."""
    return get_cache_root().joinpath(*rel_path)
