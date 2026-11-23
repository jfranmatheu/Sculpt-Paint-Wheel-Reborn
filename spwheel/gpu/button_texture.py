"""GPU texture cache for wheel custom-button image paths."""

from __future__ import annotations

import os
from typing import Optional

import bpy
import gpu

_texture_cache: dict[str, gpu.types.GPUTexture] = {}


def get_custom_button_texture(path: str) -> Optional[gpu.types.GPUTexture]:
    if not path or not os.path.isfile(path):
        return None
    norm = os.path.normpath(path)
    tex = _texture_cache.get(norm)
    if tex is not None:
        return tex
    try:
        img = bpy.data.images.load(norm, check_existing=True)
    except Exception:
        print(f"WARN! Failed to load custom-button image: {norm}")
        return None
    try:
        tex = gpu.texture.from_image(img)
    except Exception:
        print(f"WARN! Failed to create custom-button texture: {norm}")
        return None
    _texture_cache[norm] = tex
    return tex


def clear_custom_button_texture_cache() -> None:
    _texture_cache.clear()


def forget_custom_button_texture(path: str) -> None:
    """Drop the cached texture for *path* and reload its image, so the next draw reads the file again."""
    norm = os.path.normpath(path)
    _texture_cache.pop(norm, None)
    for img in bpy.data.images:
        if img.filepath and os.path.normpath(bpy.path.abspath(img.filepath)) == norm:
            try:
                img.reload()
            except Exception:
                pass
