from pathlib import Path
import traceback
import zlib
import hashlib
import subprocess

import gpu
import numpy as np
from gpu.types import GPUTexture

from ..gpu.button_texture import get_custom_button_texture
from .common import get_cache_path



# Texture per preview key; None: no preview for it (looked up once, not on every redraw). Writing a preview
# drops its entry, so the new image is loaded.
_texture_cache: dict[str, GPUTexture | None] = {}
_fallback_texture: GPUTexture | None = None


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def generate_preview_hash(library_name: str, blend_stem: str, brush_name: str, is_essential: bool = False,
                          library_id: str = "") -> str:
    """Cache key of a brush preview. ``library_id`` tells apart libraries (or files) holding a brush at the same
    path: without it two custom libraries with the same ``brushes.blend/Brush/X`` shared one preview."""
    key = f"{'E' if is_essential else 'C'}|{library_name}|{blend_stem}|{brush_name}"
    if library_id:
        key += f"|{library_id}"
    return _sha1(key)


def _preview_rel(hash_id: str) -> str:
    return f"previews/{hash_id}.bin"

def get_preview_path(hash_id: str) -> Path:
    return get_cache_path(_preview_rel(hash_id))


def _safe_essential_brush_name(brush_name: str) -> str:
    return brush_name.replace("/", "_").replace("\\", "_")


def _safe_essential_mode_id(mode_id: str) -> str:
    return mode_id.replace("/", "_").replace("\\", "_")


def get_essential_preview_key(mode_id: str, brush_name: str) -> str:
    return f"{_safe_essential_mode_id(mode_id)}__{_safe_essential_brush_name(brush_name)}"


def _essential_brush_name_variants(brush_name: str) -> list[str]:
    """Match generator: optional strip of Blender-style '.001' suffix in blend data names."""
    names: list[str] = [brush_name]
    if "." in brush_name:
        stem = brush_name.split(".", 1)[0]
        if stem and stem not in names:
            names.append(stem)
    return names


def get_essential_preview_path(mode_id: str, brush_name: str) -> Path:
    from ..core.globals import PATHS
    return PATHS.ASSETS / "previews_essentials" / f"{get_essential_preview_key(mode_id, brush_name)}.bin"


def write_preview(hash_id: str, w: int, h: int, pixels_float) -> str:
    """Compress float pixels to uint8, write .bin, return full path."""
    data = bytes(int(max(0.0, min(1.0, p)) * 255) for p in pixels_float)
    compressed = zlib.compress(data, 6)
    full = get_preview_path(hash_id)
    full.parent.mkdir(parents=True, exist_ok=True)
    _texture_cache.pop(hash_id, None)  # (A new image: reload it.)
    with full.open("wb") as f:
        f.write(w.to_bytes(4, "little"))
        f.write(h.to_bytes(4, "little"))
        f.write(compressed)
    return full.as_posix()


def write_essential_preview(mode_id: str, brush_name: str, w: int, h: int, pixels_float) -> str:
    data = bytes(int(max(0.0, min(1.0, p)) * 255) for p in pixels_float)
    compressed = zlib.compress(data, 6)
    full = get_essential_preview_path(mode_id, brush_name)
    full.parent.mkdir(parents=True, exist_ok=True)
    _texture_cache.pop(f"ESSENTIALS|{mode_id}|{brush_name}", None)
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


def _log_essential_preview_miss(mode_id: str, brush_name: str, tried_paths: list[Path]) -> None:
    try:
        from ..core.globals import GLOBALS
        if not GLOBALS.IN_DEVELOPMENT:
            return
    except Exception:
        return
    print(
        f"[Sculpt+] essentials preview not found: mode_id={mode_id!r} brush={brush_name!r} "
        f"tried: {[p.as_posix() for p in tried_paths]}"
    )


def _log_essential_preview_size_mismatch(mode_id: str, brush_name: str, path: Path, w: int, h: int, size: int) -> None:
    try:
        from ..core.globals import GLOBALS
        if not GLOBALS.IN_DEVELOPMENT:
            return
    except Exception:
        return
    print(
        f"[Sculpt+] essentials preview size mismatch: mode_id={mode_id!r} brush={brush_name!r} "
        f"path={path.as_posix()} header={w}x{h} expected={w*h*4} got={size}"
    )


def read_essential_preview(mode_id: str, brush_name: str) -> tuple[int, int, bytes] | None:
    tried: list[Path] = []
    for variant in _essential_brush_name_variants(brush_name):
        full = get_essential_preview_path(mode_id, variant)
        tried.append(full)
        if not full.is_file():
            continue
        try:
            with full.open("rb") as f:
                w = int.from_bytes(f.read(4), "little")
                h = int.from_bytes(f.read(4), "little")
                compressed = f.read()
            data = zlib.decompress(compressed)
            if len(data) != w * h * 4:
                _log_essential_preview_size_mismatch(mode_id, brush_name, full, w, h, len(data))
                continue
            return w, h, data
        except Exception:
            continue
    _log_essential_preview_miss(mode_id, brush_name, tried)
    return None


# sRGB byte -> linear float. The texture shaders take linear colors (as gpu.texture.from_image gives them).
_SRGB_TO_LINEAR = np.array(
    [(c / 255.0) / 12.92 if c / 255.0 <= 0.04045 else ((c / 255.0 + 0.055) / 1.055) ** 2.4 for c in range(256)],
    dtype=np.float32,
)


def _rgba8_srgb_to_linear_floats(data: bytes) -> np.ndarray:
    """RGBA8 sRGB bytes -> flat float32 RGBA with linear rgb (alpha kept)."""
    px = np.frombuffer(data, dtype=np.uint8).reshape(-1, 4)
    out = np.empty(px.shape, dtype=np.float32)
    out[:, :3] = _SRGB_TO_LINEAR[px[:, :3]]
    out[:, 3] = px[:, 3] / np.float32(255.0)
    return out.ravel()


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
        _texture_cache[cache_key] = None
        return None
    w, h, data = preview_data
    if w is None:
        return None

    try:
        # Blender requires FLOAT buffers: the cached RGBA8 sRGB bytes as float32, rgb made linear.
        float_data = _rgba8_srgb_to_linear_floats(data)
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


def get_essential_brush_gputex(mode_id: str, brush_name: str) -> GPUTexture | None:
    # Cache by metadata keys (not file stem) so name variants hit the same texture.
    cache_key = f"ESSENTIALS|{mode_id}|{brush_name}"
    if cache_key in _texture_cache:
        return _texture_cache[cache_key]

    preview_data = read_essential_preview(mode_id, brush_name)
    if preview_data is None:
        _texture_cache[cache_key] = None
        return None
    w, h, data = preview_data
    if w is None:
        return None

    try:
        float_data = _rgba8_srgb_to_linear_floats(data)
        buf = gpu.types.Buffer("FLOAT", len(float_data), float_data)
        tex = GPUTexture((w, h), format="RGBA16F", data=buf)
        _texture_cache[cache_key] = tex
        return tex
    except Exception:
        print(f"[Sculpt+] Essentials GPU texture creation failed: {traceback.format_exc()}")
        fb = _get_fallback_texture()
        if fb is not None:
            _texture_cache[cache_key] = fb
        return fb


def get_brush_texture(brush_id_key: str, is_essential: bool = False, mode_id: str = "") -> GPUTexture | None:
    if is_essential:
        if mode_id == "":
            return None
        return get_essential_brush_gputex(mode_id, brush_id_key)
    return get_brush_gputex(brush_id_key)


def generate_essentials_previews_background() -> bool:
    """
    Spawn a background Blender process that generates essentials previews.
    """
    print("[Sculpt+] generate_essentials_previews_background(): starting")
    try:
        import bpy
        from ..core.globals import PATHS
    except Exception:
        print("[Sculpt+] generate_essentials_previews_background(): failed importing bpy/PATHS")
        print(traceback.format_exc())
        return False

    asset_root = Path(bpy.utils.system_resource('DATAFILES')) / "assets" / "brushes"
    print(f"[Sculpt+] Essentials asset root: {asset_root}")

    script_path = Path(__file__).parent / "generate_essentials_previews_bg.py"
    output_dir = PATHS.ASSETS / "previews_essentials"
    print(f"[Sculpt+] Essentials preview script: {script_path}")
    print(f"[Sculpt+] Essentials output dir: {output_dir}")

    cmd = [
        bpy.app.binary_path,
        "--background",
        "--factory-startup",
        "--python",
        str(script_path),
        "--",
        str(asset_root),
        str(output_dir),
    ]
    print("[Sculpt+] Launching background preview generation:")
    print("[Sculpt+] " + " ".join(f'"{c}"' if " " in c else c for c in cmd))

    try:
        proc = subprocess.Popen(cmd)
    except Exception:
        print("[Sculpt+] Failed to launch background Blender process")
        print(traceback.format_exc())
        return False

    print(f"[Sculpt+] Background Blender PID: {proc.pid}")
    return True


# TO GENERATE ESSENTIALS PREVIEWS:
'''def register():
    generate_essentials_previews_background()
'''
