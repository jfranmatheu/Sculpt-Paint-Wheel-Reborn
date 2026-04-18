"""Brush library list: sync from ``libraries.json`` into WM (no separate user JSON).

Per-blend ``active_page`` is stored in each blend's ``user_prefs`` inside the index
(see ``brush_management.runtime.set_user_pref``). Wheel overlay color is global add-on preference.
"""

from __future__ import annotations

import traceback
from typing import Any

import bpy
from bpy.types import Context

from ..core.debug import print_debug
from ..core.globals import GLOBALS

from .data import DEFAULT_WHEEL_COLOR, SculptWheelData, make_blend_key, parse_blend_key


def _addon_prefs(context: Context):
    addon = context.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME)
    return addon.preferences if addon else None


def sync_brush_lib_configs(context: Context) -> None:
    """Rebuild ``brush_lib_configs`` from the loaded brush index (order = index order)."""
    from ..src.brush_management import get_index, is_loaded, list_library_blend_keys

    if not is_loaded():
        return

    wd = SculptWheelData.get(context)
    idx = get_index()
    blend_rows = list_library_blend_keys()

    prev_pages_expanded: dict[str, bool] = {}
    for i in range(len(wd.brush_lib_configs)):
        it = wd.brush_lib_configs[i]
        bk0 = (it.blend_key or "").strip()
        if bk0:
            prev_pages_expanded[bk0] = bool(it.wheel_pages_expanded)
    wd.brush_lib_configs.clear()
    for lid, bid, _label in blend_rows:
        bk = make_blend_key(lid, bid)
        lib_data = idx.libraries.get(lid)
        blend_data = lib_data.blends.get(bid) if lib_data else None
        lib_name = lib_data.name if lib_data else ""
        blend_name = blend_data.file_name if blend_data else bid

        it = wd.brush_lib_configs.add()
        it.blend_key = bk
        it.library_id = lid
        it.blend_id = bid
        it.library_name = lib_name
        it.blend_name = blend_name
        if bk in prev_pages_expanded:
            it.wheel_pages_expanded = prev_pages_expanded[bk]

    _clamp_all_blend_active_pages()
    wd.brush_libs_loaded = True
    ordered = [make_blend_key(lid, bid) for lid, bid, _ in blend_rows]
    _fix_active_blend_enum(wd, ordered)
    sync_brush_lib_list_index(context)


def sync_brush_lib_list_index(context: Context) -> None:
    from .data import sync_brush_lib_list_index as _sync
    _sync(context)


def _fix_active_blend_enum(wd: Any, ordered_keys: list[str]) -> None:
    if not ordered_keys:
        wd.wheel_active_blend = "NONE"
        return
    cur = wd.wheel_active_blend
    if cur == "NONE" or cur not in ordered_keys:
        wd.wheel_active_blend = ordered_keys[0]


def list_ordered_blend_keys(context: Context) -> list[str]:
    from ..src.brush_management import list_library_blend_keys
    return [make_blend_key(lid, bid) for lid, bid, _ in list_library_blend_keys()]


def blend_display_label(context: Context, blend_key: str) -> str:
    from ..src.brush_management import list_library_blend_keys
    for lid, bid, label in list_library_blend_keys():
        if make_blend_key(lid, bid) == blend_key:
            return label
    return blend_key


def get_wheel_base_color(context: Context, blend_key: str) -> tuple[float, float, float, float]:
    """Global wheel overlay tint from add-on preferences (``blend_key`` ignored)."""
    p = _addon_prefs(context)
    if p is None:
        return DEFAULT_WHEEL_COLOR
    c = getattr(p, "wheel_overlay_base_color", None)
    if c is None or len(c) < 4:
        return DEFAULT_WHEEL_COLOR
    return (float(c[0]), float(c[1]), float(c[2]), float(c[3]))


def _clamp_all_blend_active_pages() -> None:
    from ..src.brush_management import get_index, is_loaded, page_count_for_blend, save_to_disk

    if not is_loaded():
        return
    idx = get_index()
    changed = False
    for lid, lib in idx.libraries.items():
        for bid, blend in lib.blends.items():
            n = max(1, page_count_for_blend(lid, bid))
            ap = int(blend.user_prefs.get("active_page", 0))
            v = max(0, min(n - 1, ap))
            if v != ap:
                blend.user_prefs["active_page"] = v
                changed = True
    if changed:
        save_to_disk()


def page_rows_for_blend_item(context: Context, item: Any) -> list[tuple[int, str, int]]:
    """``(page_index, page_name, brush_count)`` for the given config row (sidebar)."""
    from ..src.brush_management import (
        is_loaded,
        page_count_for_blend,
        get_brushes_for_blend,
        get_page_name,
    )
    if not is_loaded():
        return []
    lid = (getattr(item, "library_id", None) or "").strip()
    bid = (getattr(item, "blend_id", None) or "").strip()
    if not lid or not bid:
        return []
    np = page_count_for_blend(lid, bid)
    out: list[tuple[int, str, int]] = []
    for i in range(np):
        name = get_page_name(lid, bid, i)
        n_br = len(get_brushes_for_blend(lid, bid, i))
        out.append((i, name, n_br))
    return out


def get_active_page(context: Context, blend_key: str) -> int:
    from ..src.brush_management import get_user_prefs_for_blend, page_count_for_blend
    lid, bid = parse_blend_key(blend_key)
    n = max(1, page_count_for_blend(lid, bid))
    ap = int(get_user_prefs_for_blend(lid, bid).get("active_page", 0))
    return max(0, min(n - 1, ap))


def set_active_page(context: Context, blend_key: str, page: int) -> None:
    from ..src.brush_management import page_count_for_blend, set_user_pref
    lid, bid = parse_blend_key(blend_key)
    n = max(1, page_count_for_blend(lid, bid))
    page = max(0, min(n - 1, int(page)))
    set_user_pref(lid, bid, "active_page", page)


def ensure_brush_libs_loaded(context: Context) -> bool:
    wd = SculptWheelData.get(context)
    if wd.brush_libs_loaded:
        return True
    from ..src.brush_management import is_loaded, load_from_disk
    if not is_loaded():
        load_from_disk()
    sync_brush_lib_configs(context)
    return wd.brush_libs_loaded


def load_brush_lib_data(context: Context, *, force_rebuild: bool = False) -> tuple[bool, str]:
    from ..src.brush_management import sync_and_reload, clear_texture_cache
    ok, err = sync_and_reload(force=force_rebuild)
    if not ok:
        return False, err
    sync_brush_lib_configs(context)
    clear_texture_cache()
    return True, ""


def bootstrap_all_windows(*, force_rebuild: bool = False) -> tuple[bool, str]:
    from ..src.brush_management import sync_and_reload, is_loaded, load_from_disk, clear_texture_cache
    from ..src.brush_management.cache import libraries_json_path

    if force_rebuild or not libraries_json_path().is_file():
        ok, err = sync_and_reload(force=force_rebuild)
        if not ok:
            return False, err
    elif not is_loaded():
        load_from_disk()

    ctx = bpy.context
    if ctx is None:
        clear_texture_cache()
        return True, ""

    override = getattr(ctx, "temp_override", None)
    wms = list(bpy.data.window_managers)
    if override is None or not wms:
        try:
            sync_brush_lib_configs(ctx)
        except Exception:
            print_debug(f"[Sculpt+] brush lib bootstrap sync failed: {traceback.format_exc()}")
        clear_texture_cache()
        return True, ""

    for wm in wms:
        try:
            with ctx.temp_override(window_manager=wm):
                sync_brush_lib_configs(bpy.context)
        except Exception:
            print_debug(f"[Sculpt+] brush lib bootstrap sync (wm) failed: {traceback.format_exc()}")
    clear_texture_cache()
    return True, ""


def schedule_brush_lib_bootstrap() -> None:
    from ..core.globals import GLOBALS

    def _timer():
        try:
            c = bpy.context
            if c is None:
                return 0.1
            if c.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME) is None:
                return 0.1
            ok, err = bootstrap_all_windows(force_rebuild=False)
            if not ok:
                print_debug(f"[Sculpt+] brush library bootstrap failed: {err}")
        except Exception:
            print_debug(f"[Sculpt+] brush library bootstrap: {traceback.format_exc()}")
        return None

    bpy.app.timers.register(_timer, first_interval=0.15)
