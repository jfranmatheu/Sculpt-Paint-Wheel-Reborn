"""Brush library configuration: merges libraries.json data with wheel UI state.

Replaces the old brush_sets_config.py (shelve-based). Now powered by
``src.brush_management`` and the ``libraries.json`` index.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

import bpy
from bpy.types import Context

from ..core.debug import print_debug

DEFAULT_WHEEL_COLOR = (0.075, 0.078, 0.085, 0.97)
JSON_NAME = "brush_lib_config.json"
JSON_VERSION = 1
_CFG_LOADING = False


def _config_json_path() -> Path:
    return Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data" / JSON_NAME


def load_config_json() -> dict[str, Any]:
    path = _config_json_path()
    if not path.is_file():
        return {"version": JSON_VERSION, "blends": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"version": JSON_VERSION, "blends": {}}
        data.setdefault("blends", {})
        return data
    except Exception:
        print_debug(f"[Sculpt+] brush_lib_config read failed: {traceback.format_exc()}")
        return {"version": JSON_VERSION, "blends": {}}


def save_config_json(data: dict[str, Any]) -> None:
    path = _config_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["version"] = JSON_VERSION
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        print_debug(f"[Sculpt+] brush_lib_config write failed: {traceback.format_exc()}")


def _default_entry(order: int, lib_name: str, blend_name: str) -> dict[str, Any]:
    dn = blend_name if blend_name else "Brush Library"
    if lib_name:
        dn = f"{lib_name} — {blend_name}" if blend_name else lib_name
    return {
        "order": order,
        "display_name": dn,
        "library_name": lib_name,
        "blend_name": blend_name,
        "wheel_color": list(DEFAULT_WHEEL_COLOR),
        "show_color_picker": False,
        "custom_button_set": "ACTIVE",
        "active_page": 0,
    }


def _coerce_custom_button_set(v: Any) -> str:
    if v == "ACTIVE" or (isinstance(v, str) and v.strip().upper() == "ACTIVE"):
        return "ACTIVE"
    if v is not None:
        try:
            return str(max(0, min(9, int(v))))
        except (TypeError, ValueError):
            pass
    return "ACTIVE"


def sync_brush_lib_configs(context: Context) -> None:
    """Merge libraries.json data with config JSON, repopulate WM collection."""
    global _CFG_LOADING
    from .data import SculptWheelData, WheelBrushLibConfigItem, make_blend_key
    from ..src.brush_management import is_loaded, get_index, list_library_blend_keys

    if not is_loaded():
        return

    wd = SculptWheelData.get(context)
    idx = get_index()
    blend_keys = list_library_blend_keys()

    config = load_config_json()
    blends_cfg: dict[str, Any] = config.get("blends", {})

    valid_keys = set()
    for lid, bid, label in blend_keys:
        bk = make_blend_key(lid, bid)
        valid_keys.add(bk)

    for k in list(blends_cfg.keys()):
        if k not in valid_keys:
            del blends_cfg[k]

    max_order = 0
    for v in blends_cfg.values():
        if isinstance(v, dict):
            try:
                max_order = max(max_order, int(v.get("order", 0)))
            except (TypeError, ValueError):
                pass

    next_order = max_order + 1
    for lid, bid, label in blend_keys:
        bk = make_blend_key(lid, bid)
        lib_data = idx.libraries.get(lid)
        blend_data = lib_data.blends.get(bid) if lib_data else None
        lib_name = lib_data.name if lib_data else ""
        blend_name = blend_data.file_name if blend_data else bid

        if bk not in blends_cfg:
            blends_cfg[bk] = _default_entry(next_order, lib_name, blend_name)
            next_order += 1
            continue

        ent = blends_cfg[bk]
        if not isinstance(ent, dict):
            blends_cfg[bk] = _default_entry(next_order, lib_name, blend_name)
            next_order += 1
            continue

        ent.setdefault("library_name", lib_name)
        ent.setdefault("blend_name", blend_name)
        if "order" not in ent:
            ent["order"] = next_order
            next_order += 1
        if not str(ent.get("display_name", "")).strip():
            dn = blend_name
            if lib_name:
                dn = f"{lib_name} — {blend_name}"
            ent["display_name"] = dn
        wc = ent.get("wheel_color")
        if not (isinstance(wc, list) and len(wc) == 4):
            ent["wheel_color"] = list(DEFAULT_WHEEL_COLOR)
        ent.setdefault("show_color_picker", False)
        ent.setdefault("custom_button_set", "ACTIVE")
        ent.setdefault("active_page", 0)

    config["blends"] = blends_cfg
    save_config_json(config)

    _CFG_LOADING = True
    try:
        wd.brush_lib_configs.clear()

        def _sort_key(bk: str) -> tuple[int, str]:
            ent = blends_cfg.get(bk, {})
            if not isinstance(ent, dict):
                return (0, bk.lower())
            try:
                o = int(ent.get("order", 0))
            except (TypeError, ValueError):
                o = 0
            return (o, bk.lower())

        all_keys = [make_blend_key(lid, bid) for lid, bid, _ in blend_keys]
        ordered = sorted(all_keys, key=_sort_key)

        for bk in ordered:
            ent = blends_cfg.get(bk, {})
            if not isinstance(ent, dict):
                continue
            from .data import parse_blend_key
            lid, bid = parse_blend_key(bk)

            it: WheelBrushLibConfigItem = wd.brush_lib_configs.add()
            it.blend_key = bk
            it.library_id = lid
            it.blend_id = bid
            it.library_name = str(ent.get("library_name", ""))
            it.blend_name = str(ent.get("blend_name", ""))
            it.order = int(ent.get("order", 0))
            dn = str(ent.get("display_name", "")).strip()
            if not dn:
                dn = it.blend_name or bk
            it.display_name = dn
            wc = ent.get("wheel_color")
            if isinstance(wc, list) and len(wc) == 4:
                it.wheel_color = tuple(float(x) for x in wc)
            else:
                it.wheel_color = DEFAULT_WHEEL_COLOR
            it.show_color_picker = bool(ent.get("show_color_picker"))
            it.custom_button_set = _coerce_custom_button_set(ent.get("custom_button_set"))
            it.active_page = int(ent.get("active_page", 0))
        for it in wd.brush_lib_configs:
            clamp_brush_lib_item_pages(context, it)
    finally:
        _CFG_LOADING = False

    wd.brush_libs_loaded = True
    _fix_active_blend_enum(wd, ordered)
    sync_brush_lib_list_index(context)


def sync_brush_lib_list_index(context: Context) -> None:
    from .data import sync_brush_lib_list_index as _sync
    _sync(context)


def save_brush_lib_configs_to_json(context: Context) -> None:
    if _CFG_LOADING:
        return
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    blends: dict[str, Any] = {}
    for it in wd.brush_lib_configs:
        blends[it.blend_key] = {
            "order": int(it.order),
            "display_name": (it.display_name or it.blend_name or it.blend_key).strip(),
            "library_name": it.library_name,
            "blend_name": it.blend_name,
            "wheel_color": list(it.wheel_color),
            "show_color_picker": bool(it.show_color_picker),
            "custom_button_set": _coerce_custom_button_set(
                getattr(it, "custom_button_set", "ACTIVE")
            ),
            "active_page": int(it.active_page),
        }
    save_config_json({"version": JSON_VERSION, "blends": blends})


def _fix_active_blend_enum(wd: Any, ordered_keys: list[str]) -> None:
    if not ordered_keys:
        wd.wheel_active_blend = "NONE"
        return
    cur = wd.wheel_active_blend
    if cur == "NONE" or cur not in ordered_keys:
        wd.wheel_active_blend = ordered_keys[0]


def list_ordered_blend_keys(context: Context) -> list[str]:
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    if len(wd.brush_lib_configs) == 0:
        from ..src.brush_management import list_library_blend_keys
        from .data import make_blend_key
        return [make_blend_key(lid, bid) for lid, bid, _ in list_library_blend_keys()]

    def _o(it) -> int:
        try:
            return int(it.order)
        except (TypeError, ValueError):
            return 0

    items = [(it.blend_key, _o(it)) for it in wd.brush_lib_configs]
    items.sort(key=lambda t: (t[1], t[0].lower()))
    return [k for k, _ in items]


def blend_display_label(context: Context, blend_key: str) -> str:
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    for it in wd.brush_lib_configs:
        if it.blend_key == blend_key:
            return (it.display_name or it.blend_name or blend_key).strip()
    return blend_key


def get_active_blend_show_color_picker(context: Context) -> bool:
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    key = (wd.wheel_active_blend or "").strip()
    if not key or key == "NONE":
        return False
    for it in wd.brush_lib_configs:
        if it.blend_key == key:
            return bool(it.show_color_picker)
    return False


def get_wheel_base_color(context: Context, blend_key: str) -> tuple[float, float, float, float]:
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    for it in wd.brush_lib_configs:
        if it.blend_key == blend_key:
            c = it.wheel_color
            return (float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    return DEFAULT_WHEEL_COLOR


def clamp_brush_lib_item_pages(context: Context, item: Any) -> None:
    """Keep ``item.active_page`` within ``[0, page_count - 1]`` for its blend."""
    from ..src.brush_management import is_loaded, page_count_for_blend
    if not is_loaded():
        return
    lid = (getattr(item, "library_id", None) or "").strip()
    bid = (getattr(item, "blend_id", None) or "").strip()
    if not lid or not bid:
        return
    n = max(1, page_count_for_blend(lid, bid))
    v = max(0, min(n - 1, int(getattr(item, "active_page", 0))))
    if int(item.active_page) != v:
        item.active_page = v


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
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    for it in wd.brush_lib_configs:
        if it.blend_key == blend_key:
            return int(it.active_page)
    return 0


def set_active_page(context: Context, blend_key: str, page: int) -> None:
    from .data import SculptWheelData, parse_blend_key
    from ..src.brush_management import page_count_for_blend
    wd = SculptWheelData.get(context)
    lid, bid = parse_blend_key(blend_key)
    n = max(1, page_count_for_blend(lid, bid))
    page = max(0, min(n - 1, int(page)))
    for it in wd.brush_lib_configs:
        if it.blend_key == blend_key:
            it.active_page = page
            break


def brush_lib_config_move(context: Context, direction: int) -> bool:
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    n = len(wd.brush_lib_configs)
    if n < 2:
        return False
    active = int(wd.brush_lib_config_active_index)
    if active < 0 or active >= n:
        return False
    active_key = wd.brush_lib_configs[active].blend_key
    order_idx = sorted(
        range(n),
        key=lambda i: (int(wd.brush_lib_configs[i].order), wd.brush_lib_configs[i].blend_key.lower()),
    )
    try:
        pos = order_idx.index(active)
    except ValueError:
        return False
    new_pos = pos + direction
    if new_pos < 0 or new_pos >= n:
        return False
    i_a = order_idx[pos]
    i_b = order_idx[new_pos]
    a = wd.brush_lib_configs[i_a]
    b = wd.brush_lib_configs[i_b]
    a.order, b.order = b.order, a.order
    _resort_configs(context)
    for j in range(len(wd.brush_lib_configs)):
        if wd.brush_lib_configs[j].blend_key == active_key:
            wd.brush_lib_config_active_index = j
            break
    return True


def _resort_configs(context: Context) -> None:
    global _CFG_LOADING
    from .data import SculptWheelData
    wd = SculptWheelData.get(context)
    n = len(wd.brush_lib_configs)
    if n == 0:
        return
    rows = []
    for i in range(n):
        it = wd.brush_lib_configs[i]
        rows.append({
            "blend_key": it.blend_key,
            "library_id": it.library_id,
            "blend_id": it.blend_id,
            "library_name": it.library_name,
            "blend_name": it.blend_name,
            "order": int(it.order),
            "display_name": (it.display_name or it.blend_name or it.blend_key).strip(),
            "wheel_color": tuple(float(x) for x in it.wheel_color),
            "show_color_picker": bool(it.show_color_picker),
            "custom_button_set": _coerce_custom_button_set(getattr(it, "custom_button_set", "ACTIVE")),
            "active_page": int(it.active_page),
        })
    rows.sort(key=lambda r: (r["order"], r["blend_key"].lower()))
    _CFG_LOADING = True
    try:
        wd.brush_lib_configs.clear()
        for r in rows:
            it = wd.brush_lib_configs.add()
            it.blend_key = r["blend_key"]
            it.library_id = r["library_id"]
            it.blend_id = r["blend_id"]
            it.library_name = r["library_name"]
            it.blend_name = r["blend_name"]
            it.order = r["order"]
            it.display_name = r["display_name"]
            it.wheel_color = r["wheel_color"]
            it.show_color_picker = r["show_color_picker"]
            it.custom_button_set = r["custom_button_set"]
            it.active_page = r["active_page"]
        for it in wd.brush_lib_configs:
            clamp_brush_lib_item_pages(context, it)
    finally:
        _CFG_LOADING = False
    save_brush_lib_configs_to_json(context)


def ensure_brush_libs_loaded(context: Context) -> bool:
    from .data import SculptWheelData
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
