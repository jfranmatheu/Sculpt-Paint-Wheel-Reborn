from array import array
from pathlib import Path
import traceback
import zlib
import hashlib

import gpu
from gpu.types import GPUTexture

from ..gpu.button_texture import get_custom_button_texture
from .common import get_cache_path



_texture_cache: dict[str, GPUTexture] = {}
_fallback_texture: GPUTexture | None = None


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def generate_preview_hash(library_name: str, blend_stem: str, brush_name: str, is_essential: bool = False) -> str:
    return _sha1(f"{'E' if is_essential else 'C'}|{library_name}|{blend_stem}|{brush_name}")


def _preview_rel(hash_id: str) -> str:
    return f"previews/{hash_id}.bin"

def get_preview_path(hash_id: str) -> Path:
    return get_cache_path(_preview_rel(hash_id))


def write_preview(hash_id: str, w: int, h: int, pixels_float) -> str:
    """Compress float pixels to uint8, write .bin, return full path."""
    data = bytes(int(max(0.0, min(1.0, p)) * 255) for p in pixels_float)
    compressed = zlib.compress(data, 6)
    full = get_preview_path(hash_id)
    full.parent.mkdir(parents=True, exist_ok=True)
    with full.open("wb") as f:
        f.write(w.to_bytes(4, "little"))
        f.write(h.to_bytes(4, "little"))
        f.write(compressed)
    return full.as_posix()


def _get_fallback_texture() -> GPUTexture | None:
    if _fallback_texture is not None:
        return _fallback_texture
    from ..core.globals import PATHS
    p = PATHS.ASSETS / "images" / "brush.png"
    return get_custom_button_texture(str(p.resolve()))


def read_preview(hash_id: str) -> tuple[int, int, bytes] | None:
    """Read and decompress preview from disk. Returns (w, h, rgba_uint8) or None."""
    full = get_preview_path(hash_id)
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


def get_brush_gputex(brush_id_key: str) -> GPUTexture | None:
    """Lazy-load a GPU texture from a cached .bin preview.

    Returns a GPUTexture or None. The result is cached in-memory by *brush_id_key*
    (falls back to *preview_path* as key).
    """
    cache_key = brush_id_key
    if cache_key in _texture_cache:
        return _texture_cache[cache_key]

    preview_data = read_preview(brush_id_key)
    if preview_data is None:
        return None
    w, h, data = preview_data
    if w is None:
        return None

    try:
        # Blender requires FLOAT buffers.
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
