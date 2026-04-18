"""Runtime state for the brush management system.

Provides the in-memory representation loaded from libraries.json,
brush activation helpers, and the bridge between the cache and the wheel UI.
"""

from __future__ import annotations

import traceback
from typing import Any

import bpy
from bpy.types import Context

from .cache import load_libraries_index, save_libraries_index, ensure_cache_dirs
from .models import (
    LibrariesIndex,
    LibraryData,
    BlendData,
    BrushData,
    MAX_BRUSHES_PER_PAGE,
)
from .previews import get_brush_preview_texture, clear_texture_cache

# Singleton runtime index.
_index: LibrariesIndex | None = None
_loaded: bool = False


def is_loaded() -> bool:
    return _loaded


def get_index() -> LibrariesIndex:
    global _index
    if _index is None:
        _index = LibrariesIndex()
    return _index


def load_from_disk() -> LibrariesIndex:
    """Read libraries.json into memory."""
    global _index, _loaded
    ensure_cache_dirs()
    _index = load_libraries_index()
    _loaded = True
    return _index


def save_to_disk() -> None:
    """Write current in-memory index to disk."""
    if _index is not None:
        save_libraries_index(_index)


def set_index(index: LibrariesIndex) -> None:
    global _index, _loaded
    _index = index
    _loaded = True


def reset() -> None:
    global _index, _loaded
    _index = None
    _loaded = False
    clear_texture_cache()


# ──────────────────────────────────────────────────────────────────────
# Wheel data helpers
# ──────────────────────────────────────────────────────────────────────

def list_library_blend_keys() -> list[tuple[str, str, str]]:
    """Return (library_id, blend_id, display_label) for every blend in the index,
    sorted by library name then blend name."""
    idx = get_index()
    results: list[tuple[str, str, str]] = []
    for lid, lib in idx.libraries.items():
        for bid, blend in lib.blends.items():
            label = blend.file_name or bid
            if lib.name:
                label = f"{lib.name} — {label}"
            results.append((lid, bid, label))
    results.sort(key=lambda t: t[2].lower())
    return results


def get_brushes_for_blend(
    library_id: str,
    blend_id: str,
    page: int = 0,
) -> list[BrushData]:
    """Return brushes for a specific blend file, optionally filtered by wheel page.

    If *page* is negative, returns ALL brushes for that blend.
    """
    idx = get_index()
    lib = idx.libraries.get(library_id)
    if lib is None:
        return []
    blend = lib.blends.get(blend_id)
    if blend is None:
        return []
    brushes = sorted(blend.brushes.values(), key=lambda b: (b.wheel_page, b.wheel_index))
    if page < 0:
        return brushes
    return [b for b in brushes if b.wheel_page == page]


def get_all_brushes_for_blend(library_id: str, blend_id: str) -> list[BrushData]:
    """All brushes regardless of page, sorted by (page, index)."""
    return get_brushes_for_blend(library_id, blend_id, page=-1)


def page_count_for_blend(library_id: str, blend_id: str) -> int:
    """Number of wheel pages for a blend file."""
    brushes = get_all_brushes_for_blend(library_id, blend_id)
    if not brushes:
        return 0
    max_page = max(b.wheel_page for b in brushes)
    return max_page + 1


def get_user_prefs_for_blend(library_id: str, blend_id: str) -> dict[str, Any]:
    idx = get_index()
    lib = idx.libraries.get(library_id)
    if lib is None:
        return {"active_page": 0, "custom_order": [], "favorites": []}
    blend = lib.blends.get(blend_id)
    if blend is None:
        return {"active_page": 0, "custom_order": [], "favorites": []}
    return dict(blend.user_prefs)


def set_user_pref(library_id: str, blend_id: str, key: str, value: Any) -> None:
    """Update a single user_prefs key for a blend, and persist to disk."""
    idx = get_index()
    lib = idx.libraries.get(library_id)
    if lib is None:
        return
    blend = lib.blends.get(blend_id)
    if blend is None:
        return
    blend.user_prefs[key] = value
    save_to_disk()


# ──────────────────────────────────────────────────────────────────────
# Brush activation
# ──────────────────────────────────────────────────────────────────────

def activate_brush(context: Context, brush: BrushData) -> bool:
    """Activate a brush via ``bpy.ops.brush.asset_activate``."""
    lt = brush.asset_library_type or "LOCAL"
    lid = brush.asset_library_identifier or ""
    rid = brush.relative_asset_identifier or ""
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
        print(f"[Sculpt+] brush activation failed: {traceback.format_exc()}")
        return False


def get_active_sculpt_brush(context: Context):
    """Return the active sculpt brush or None."""
    ts = context.tool_settings
    if ts and ts.sculpt:
        return ts.sculpt.brush
    return None


def active_brush_index_in_list(
    context: Context,
    brushes: list[BrushData],
) -> int:
    """Index into *brushes* matching the active sculpt brush name, or -1."""
    brush = get_active_sculpt_brush(context)
    if brush is None or not brushes:
        return -1
    for i, b in enumerate(brushes):
        if b.name == brush.name:
            return i
    return -1
