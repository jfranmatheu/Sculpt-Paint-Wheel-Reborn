"""Preview .bin read/write and lazy GPU texture loading."""

from __future__ import annotations

import zlib
import traceback
from array import array
from pathlib import Path
from typing import Any

from .cache import cache_dir
from .ids import preview_relative_path

# Lazy GPU texture cache: preview_hash -> GPUTexture
_texture_cache: dict[str, Any] = {}
_fallback_texture: Any = None


def write_preview_bin(hash_id: str, w: int, h: int, rgba_uint8: bytes) -> str:
    """Compress and write preview to disk. Returns the relative path."""
    rel = preview_relative_path(hash_id)
    full = cache_dir() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    compressed = zlib.compress(rgba_uint8, 6)
    with full.open("wb") as f:
        f.write(w.to_bytes(4, "little"))
        f.write(h.to_bytes(4, "little"))
        f.write(compressed)
    return rel


def read_preview_bin(rel_path: str) -> tuple[int, int, bytes] | None:
    """Read and decompress preview from disk. Returns (w, h, rgba_uint8) or None."""
    full = cache_dir() / rel_path
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
    """Generic brush icon from addon assets."""
    global _fallback_texture
    if _fallback_texture is not None:
        return _fallback_texture
    try:
        from ...core.globals import PATHS
        p = PATHS.ASSETS / "images" / "brush.png"
        if not p.is_file():
            return None
        from ..sculpt_wheel.custom_buttons import get_custom_button_texture
        _fallback_texture = get_custom_button_texture(str(p.resolve()))
        return _fallback_texture
    except Exception:
        return None


def get_brush_preview_texture(preview_path: str, brush_id_key: str = "") -> Any:
    """Lazy-load a GPU texture from a cached .bin preview.

    Returns a GPUTexture or None. The result is cached in-memory by *brush_id_key*
    (falls back to *preview_path* as key).
    """
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
        import gpu
        from gpu.types import GPUTexture
        # Blender 5.1 GPUTexture currently requires FLOAT buffers.
        # Convert cached RGBA8 bytes [0..255] to normalized float32 [0..1].
        float_data = array("f", (ch / 255.0 for ch in data))
        buf = gpu.types.Buffer("FLOAT", len(float_data), float_data)
        tex = GPUTexture((w, h), format="RGBA16F", data=buf)
        _texture_cache[cache_key] = tex
        return tex
    except Exception:
        print(f"[Sculpt+] GPU texture creation failed: {traceback.format_exc()}")
        fb = _get_fallback_texture()
        if fb is not None:
            _texture_cache[cache_key] = fb
        return fb
