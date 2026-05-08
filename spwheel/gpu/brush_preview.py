"""Lazy GPU textures from cached brush preview .bin files (Sculpt+ / Blend-Wheel cache layout)."""

from __future__ import annotations

import traceback
import zlib
from array import array
from pathlib import Path
from typing import Any

import bpy
import gpu
from gpu.types import GPUTexture

_texture_cache: dict[str, Any] = {}
_fallback_texture: Any = None


def _cache_root() -> Path:
    return Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data" / "cache"


def read_preview_bin(rel_path: str) -> tuple[int, int, bytes] | None:
    full = _cache_root() / rel_path
    if not full.is_file():
        return None
    try:
        with full.open("rb") as f:
            w = int.from_bytes(f.read(4), "little")
            h = int.from_bytes(f.read(4), "little")
            compressed = f.read()
        data = zlib.decompress(compressed)
        if len(data) != w * h * 4:
            return None
        return w, h, data
    except Exception:
        return None


def clear_texture_cache() -> None:
    _texture_cache.clear()


def _get_fallback_texture() -> Any:
    global _fallback_texture
    if _fallback_texture is not None:
        return _fallback_texture
    try:
        from ..core.globals import PATHS

        p = PATHS.ASSETS / "images" / "brush.png"
        if not p.is_file():
            return None
        from .button_texture import get_custom_button_texture

        _fallback_texture = get_custom_button_texture(str(p.resolve()))
        return _fallback_texture
    except Exception:
        return None


def get_brush_preview_texture(preview_path: str, brush_id_key: str = "") -> Any:
    """Lazy-load a GPUTexture from a cached .bin preview under the user cache."""
    cache_key = brush_id_key or preview_path
    cached = _texture_cache.get(cache_key)
    if cached is not None:
        return cached

    result = read_preview_bin(preview_path)
    if result is None:
        fb = _get_fallback_texture()
        if fb is not None:
            _texture_cache[cache_key] = fb
        return fb

    w, h, data = result
    try:
        float_data = array("f", (ch / 255.0 for ch in data))
        buf = gpu.types.Buffer("FLOAT", len(float_data), float_data)
        tex = GPUTexture((w, h), format="RGBA16F", data=buf)
        _texture_cache[cache_key] = tex
        return tex
    except Exception:
        print(f"[Wheel] GPU texture creation failed: {traceback.format_exc()}")
        fb = _get_fallback_texture()
        if fb is not None:
            _texture_cache[cache_key] = fb
        return fb
