"""Small cached wrapper around Blender previews for image-path icon ids."""

from __future__ import annotations

import hashlib
import os

import bpy
from bpy.utils import previews

_preview_collection: previews.ImagePreviewCollection | None = None
_path_to_key: dict[str, str] = {}


def _normalized_image_path(image_path: str) -> str:
    # Resolve Blender relative paths (e.g. //foo/bar.png) then normalize for cache lookups.
    return os.path.normcase(os.path.abspath(bpy.path.abspath(image_path)))


def _get_collection() -> previews.ImagePreviewCollection:
    global _preview_collection
    if _preview_collection is None:
        _preview_collection = previews.new()
    return _preview_collection


def get_image_icon_id(image_path: str, *, force_reload: bool = False) -> int:
    """Return cached icon_id for *image_path* (0 when path is invalid/unavailable)."""
    if not image_path:
        return 0
    abs_path = _normalized_image_path(image_path)
    if not os.path.isfile(abs_path):
        return 0

    collection = _get_collection()
    key = _path_to_key.get(abs_path)
    if key is None:
        key = f"img_{hashlib.sha1(abs_path.encode('utf-8')).hexdigest()}"
        _path_to_key[abs_path] = key

    try:
        if force_reload or key not in collection:
            return collection.load(key, abs_path, "IMAGE", force_reload=force_reload).icon_id
        return collection[key].icon_id
    except Exception:
        return 0


def unregister():
    global _preview_collection
    if _preview_collection is not None:
        previews.remove(_preview_collection)
        _preview_collection = None
    _path_to_key.clear()
