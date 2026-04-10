"""Brush library wheel: GPU previews from shelve pixels, asset activation."""

from __future__ import annotations

from typing import Any

import bpy
import gpu
from gpu.types import GPUTexture

from ..core.globals import PATHS

# ---------------------------------------------------------------------------
# Wheel preview cache (entry key -> GPUTexture from shelve pixels)
# ---------------------------------------------------------------------------

_wheel_preview_cache: dict[str, GPUTexture] = {}
_fallback_brush_texture: GPUTexture | None = None


def clear_preview_cache() -> None:
    _wheel_preview_cache.clear()


def _entry_preview_key(entry: dict[str, Any]) -> str:
    return "|".join(
        (
            str(entry.get("asset_library_type", "")),
            str(entry.get("asset_library_identifier", "")),
            str(entry.get("relative_asset_identifier", "")),
            str(entry.get("brush_name", "")),
        )
    )


def get_fallback_brush_texture() -> GPUTexture | None:
    """Generic brush icon from addon assets when shelve preview is missing."""
    global _fallback_brush_texture
    if _fallback_brush_texture is not None:
        return _fallback_brush_texture
    p = PATHS.ASSETS / "images" / "brush.png"
    if not p.is_file():
        return None
    from .custom_buttons import get_custom_button_texture

    _fallback_brush_texture = get_custom_button_texture(str(p.resolve()))
    return _fallback_brush_texture


def get_wheel_brush_preview_texture(entry: dict[str, Any]) -> GPUTexture | None:
    """GPUTexture from shelve ``preview_pixels`` or fallback image."""
    key = _entry_preview_key(entry)
    cached = _wheel_preview_cache.get(key)
    if cached is not None:
        return cached

    pixels = entry.get("preview_pixels")
    w = int(entry.get("preview_width") or 0)
    h = int(entry.get("preview_height") or 0)
    if (
        isinstance(pixels, (list, tuple))
        and w > 0
        and h > 0
        and len(pixels) == w * h * 4
    ):
        try:
            buf = gpu.types.Buffer("FLOAT", len(pixels), pixels)
            tex = GPUTexture((w, h), format="RGBA32F", data=buf)
            _wheel_preview_cache[key] = tex
            return tex
        except Exception:
            pass

    fb = get_fallback_brush_texture()
    if fb is not None:
        _wheel_preview_cache[key] = fb
    return fb


def activate_wheel_brush_entry(context: bpy.types.Context, entry: dict[str, Any]) -> bool:
    """Activate brush via ``bpy.ops.brush.asset_activate`` using shelve metadata."""
    lt = str(entry.get("asset_library_type") or "LOCAL")
    lid = str(entry.get("asset_library_identifier") or "")
    rid = str(entry.get("relative_asset_identifier") or "")
    if not rid:
        return False
    try:
        ret = bpy.ops.brush.asset_activate(
            asset_library_type=lt,
            asset_library_identifier=lid,
            relative_asset_identifier=rid,
        )
        return ret == {"FINISHED"}
    except Exception:
        return False


def get_active_sculpt_brush(context: bpy.types.Context) -> bpy.types.Brush | None:
    ts = context.tool_settings
    if ts and ts.sculpt:
        return ts.sculpt.brush
    return None


def wheel_brush_index_for_active(
    context: bpy.types.Context, brushes: list[dict[str, Any]]
) -> int:
    """Index in *brushes* matching active sculpt brush name, or -1."""
    brush = get_active_sculpt_brush(context)
    if brush is None or not brushes:
        return -1
    for i, e in enumerate(brushes):
        if e.get("brush_name") == brush.name:
            return i
    return -1
