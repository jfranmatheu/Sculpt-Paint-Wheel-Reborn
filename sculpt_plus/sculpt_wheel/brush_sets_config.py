"""JSON-backed brush set metadata (order, labels, wheel color) + WM CollectionProperty sync."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

import bpy
from bpy.types import Context

from ..core.debug import print_debug
from .brush_library_cache import (
    brush_set_display_label,
    brush_shelve_base,
    get_brush_library_cache,
    list_cached_brush_set_keys,
)

JSON_NAME = "brush_sets_config.json"
JSON_VERSION = 1

# Matches default wheel annulus base in draw.py
DEFAULT_WHEEL_COLOR = (0.075, 0.078, 0.085, 0.97)

_CFG_LOADING = False


def ensure_brush_shelve_ready(*, force_rebuild: bool = False) -> tuple[bool, str]:
    """Ensure disk shelve exists (background Blender if missing) and refresh in-memory cache."""
    from .brush_library_cache import (
        brush_database_exists,
        force_rebuild_brush_database,
        refresh_brush_library_cache,
    )

    if force_rebuild or not brush_database_exists():
        ok, err = force_rebuild_brush_database()
        if not ok:
            return False, err
    refresh_brush_library_cache()
    return True, ""


def _item_custom_set_int(it: Any) -> int:
    try:
        return max(0, min(9, int(it.custom_button_set)))
    except (AttributeError, TypeError, ValueError):
        return 0


def _effective_display_name_for_item(it: Any) -> str:
    """Sidebar / JSON label: explicit display name, else blend/group, else shelve key."""
    dn = (getattr(it, "display_name", None) or "").strip()
    if dn:
        return dn
    bn = (getattr(it, "blend_name", None) or "").strip()
    if bn:
        return bn
    return (getattr(it, "set_key", None) or "").strip() or "Brush set"


def brush_sets_config_path() -> Path:
    return brush_shelve_base().parent / JSON_NAME


def _default_entry(order: int, shelve_key: str, block: dict[str, Any]) -> dict[str, Any]:
    name = (block.get("name") or shelve_key).strip() or shelve_key
    lib = (block.get("library_name") or "").strip()
    return {
        "order": order,
        "display_name": name,
        "library_name": lib,
        "blend_name": name,
        "wheel_color": list(DEFAULT_WHEEL_COLOR),
        "show_color_picker": False,
        "custom_button_set": 0,
    }


def _coerce_custom_button_set_from_ent(ent: dict[str, Any]) -> int:
    """Brush row custom-button set index ``0``..``9`` (JSON key ``custom_button_set``)."""
    v = ent.get("custom_button_set")
    if v is not None:
        try:
            return max(0, min(9, int(v)))
        except (TypeError, ValueError):
            pass
    old = ent.get("custom_buttons_set_id")
    if old is not None:
        try:
            if isinstance(old, str) and old.isdigit():
                return max(0, min(9, int(old)))
            if isinstance(old, int):
                return max(0, min(9, int(old)))
        except (TypeError, ValueError):
            pass
    return 0


def load_json_raw() -> dict[str, Any]:
    path = brush_sets_config_path()
    if not path.is_file():
        return {"version": JSON_VERSION, "sets": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"version": JSON_VERSION, "sets": {}}
        if "sets" not in data or not isinstance(data["sets"], dict):
            data["sets"] = {}
        data.setdefault("version", JSON_VERSION)
        return data
    except Exception:
        print_debug(f"[Sculpt+] brush_sets_config read failed: {traceback.format_exc()}")
        return {"version": JSON_VERSION, "sets": {}}


def save_json_raw(data: dict[str, Any]) -> None:
    path = brush_sets_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    data["version"] = JSON_VERSION
    sets = data.get("sets")
    if not isinstance(sets, dict):
        sets = {}
    # Only persist serializable brush-set entries
    out_sets: dict[str, Any] = {}
    for k, v in sets.items():
        if isinstance(v, dict):
            out_sets[str(k)] = dict(v)
    data["sets"] = out_sets
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        print_debug(f"[Sculpt+] brush_sets_config write failed: {traceback.format_exc()}")


def sync_brush_set_configs_from_shelve(context: Context) -> None:
    """Merge shelve keys with JSON defaults and repopulate ``brush_set_configs``."""
    global _CFG_LOADING
    from .data import SculptWheelData, WheelBrushSetConfigItem

    wd = SculptWheelData.get(context)
    cache = get_brush_library_cache()
    keys = list_cached_brush_set_keys()
    data = load_json_raw()
    sets: dict[str, Any] = data.get("sets", {})
    if not isinstance(sets, dict):
        sets = {}

    shelve_set = set(keys)
    for k in list(sets.keys()):
        if k not in shelve_set:
            del sets[k]

    max_order = 0
    for v in sets.values():
        if isinstance(v, dict):
            try:
                max_order = max(max_order, int(v.get("order", 0)))
            except (TypeError, ValueError):
                pass

    next_order = max_order + 1
    for k in keys:
        block = cache.get(k)
        blk = block if isinstance(block, dict) else {}
        if k not in sets:
            sets[k] = _default_entry(next_order, k, blk)
            next_order += 1
            continue
        ent = sets[k]
        if not isinstance(ent, dict):
            sets[k] = _default_entry(next_order, k, blk)
            next_order += 1
            continue
        ent.setdefault("library_name", str(blk.get("library_name") or ""))
        ent.setdefault("blend_name", str(blk.get("name") or k))
        if "order" not in ent:
            ent["order"] = next_order
            next_order += 1
        blend_nm = str(ent.get("blend_name") or blk.get("name") or k).strip() or k
        if not str(ent.get("display_name", "")).strip():
            ent["display_name"] = blend_nm
        wc = ent.get("wheel_color")
        if not (
            isinstance(wc, list)
            and len(wc) == 4
            and all(isinstance(x, (int, float)) for x in wc)
        ):
            ent["wheel_color"] = list(DEFAULT_WHEEL_COLOR)
        ent.setdefault("show_color_picker", False)
        if "custom_button_set" not in ent:
            ent["custom_button_set"] = _coerce_custom_button_set_from_ent(ent)

    data["sets"] = sets
    save_json_raw(data)

    _CFG_LOADING = True
    try:
        wd.brush_set_configs.clear()
        def _sort_key(sk: str) -> tuple[int, str]:
            ent = sets.get(sk, {})
            if not isinstance(ent, dict):
                return (0, str(sk).lower())
            try:
                o = int(ent.get("order", 0))
            except (TypeError, ValueError):
                o = 0
            return (o, str(sk).lower())

        ordered = sorted(keys, key=_sort_key)
        for sk in ordered:
            ent = sets.get(sk, {})
            if not isinstance(ent, dict):
                continue
            it: WheelBrushSetConfigItem = wd.brush_set_configs.add()
            it.set_key = sk
            it.library_name = str(ent.get("library_name") or "")
            it.blend_name = str(ent.get("blend_name") or sk)
            it.order = int(ent.get("order") or 0)
            dn = str(ent.get("display_name") or "").strip()
            if not dn:
                dn = str(ent.get("blend_name") or sk).strip() or sk
            it.display_name = dn
            wc = ent.get("wheel_color")
            if isinstance(wc, list) and len(wc) == 4:
                it.wheel_color = (
                    float(wc[0]),
                    float(wc[1]),
                    float(wc[2]),
                    float(wc[3]),
                )
            else:
                it.wheel_color = DEFAULT_WHEEL_COLOR
            it.show_color_picker = bool(ent.get("show_color_picker"))
            setattr(
                it,
                "custom_button_set",
                str(
                    _coerce_custom_button_set_from_ent(
                        ent if isinstance(ent, dict) else {}
                    )
                ),
            )
    finally:
        _CFG_LOADING = False

    # Must be True before assigning wheel_brush_set: enum items() still gated on this flag.
    wd.brush_sets_loaded = True
    _fix_wheel_brush_set_enum(wd, ordered)
    from .data import sync_brush_set_list_index_to_wheel

    sync_brush_set_list_index_to_wheel(context)


def save_brush_set_configs_to_json(context: Context) -> None:
    """Write WM collection back to JSON (call from property update callbacks)."""
    if _CFG_LOADING:
        return
    from .data import SculptWheelData

    wd = SculptWheelData.get(context)
    sets: dict[str, Any] = {}
    for it in wd.brush_set_configs:
        sets[it.set_key] = {
            "order": int(it.order),
            "display_name": _effective_display_name_for_item(it),
            "library_name": it.library_name,
            "blend_name": it.blend_name,
            "wheel_color": list(it.wheel_color),
            "show_color_picker": bool(it.show_color_picker),
            "custom_button_set": _item_custom_set_int(it),
        }
    save_json_raw({"version": JSON_VERSION, "sets": sets})


def resort_brush_set_configs_collection(context: Context) -> None:
    """Sort ``brush_set_configs`` items by (order, set_key); persist JSON."""
    global _CFG_LOADING
    from .data import SculptWheelData

    wd = SculptWheelData.get(context)
    n = len(wd.brush_set_configs)
    if n == 0:
        return
    rows: list[dict[str, Any]] = []
    for i in range(n):
        it = wd.brush_set_configs[i]
        rows.append(
            {
                "set_key": it.set_key,
                "library_name": it.library_name,
                "blend_name": it.blend_name,
                "order": int(it.order),
                "display_name": _effective_display_name_for_item(it),
                "wheel_color": tuple(float(x) for x in it.wheel_color),
                "show_color_picker": bool(it.show_color_picker),
                "custom_button_set": _item_custom_set_int(it),
            }
        )
    rows.sort(key=lambda r: (int(r["order"]), str(r["set_key"]).lower()))
    _CFG_LOADING = True
    try:
        wd.brush_set_configs.clear()
        for r in rows:
            it = wd.brush_set_configs.add()
            it.set_key = r["set_key"]
            it.library_name = r["library_name"]
            it.blend_name = r["blend_name"]
            it.order = int(r["order"])
            it.display_name = r["display_name"]
            it.wheel_color = r["wheel_color"]
            it.show_color_picker = r["show_color_picker"]
            it.custom_button_set = str(
                max(0, min(9, int(r["custom_button_set"])))
            )
    finally:
        _CFG_LOADING = False
    save_brush_set_configs_to_json(context)


def brush_set_config_move(context: Context, direction: int) -> bool:
    """Move active brush-set row up (*direction* ``-1``) or down (``+1``) in sort order."""
    from .data import SculptWheelData

    wd = SculptWheelData.get(context)
    n = len(wd.brush_set_configs)
    if n < 2:
        return False
    active = int(wd.brush_set_config_active_index)
    if active < 0 or active >= n:
        return False
    active_key = wd.brush_set_configs[active].set_key
    order_idx = sorted(
        range(n),
        key=lambda i: (
            int(wd.brush_set_configs[i].order),
            wd.brush_set_configs[i].set_key.lower(),
        ),
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
    a = wd.brush_set_configs[i_a]
    b = wd.brush_set_configs[i_b]
    a.order, b.order = b.order, a.order
    resort_brush_set_configs_collection(context)
    for j in range(len(wd.brush_set_configs)):
        if wd.brush_set_configs[j].set_key == active_key:
            wd.brush_set_config_active_index = j
            break
    return True


def _fix_wheel_brush_set_enum(wd: Any, ordered_keys: list[str]) -> None:
    if not ordered_keys:
        wd.wheel_brush_set = "NONE"
        return
    cur = wd.wheel_brush_set
    if cur == "NONE" or cur not in ordered_keys:
        wd.wheel_brush_set = ordered_keys[0]


def list_ordered_brush_set_keys(context: Context) -> list[str]:
    """Brush set keys in configured order (falls back to shelve sort if not loaded)."""
    from .data import SculptWheelData

    wd = SculptWheelData.get(context)
    if len(wd.brush_set_configs) == 0:
        return sorted(list_cached_brush_set_keys(), key=str.lower)

    def _o(it) -> int:
        try:
            return int(it.order)
        except (TypeError, ValueError):
            return 0

    items = [(it.set_key, _o(it)) for it in wd.brush_set_configs]
    items.sort(key=lambda t: (t[1], t[0].lower()))
    return [k for k, _ in items]


def brush_set_enum_label(context: Context, set_key: str) -> str:
    from .data import SculptWheelData

    wd = SculptWheelData.get(context)
    for it in wd.brush_set_configs:
        if it.set_key == set_key:
            return _effective_display_name_for_item(it)
    return brush_set_display_label(set_key)


def get_wheel_base_color_tuple(context: Context, set_key: str) -> tuple[float, float, float, float]:
    from .data import SculptWheelData

    wd = SculptWheelData.get(context)
    for it in wd.brush_set_configs:
        if it.set_key == set_key:
            c = it.wheel_color
            return (float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    return DEFAULT_WHEEL_COLOR


def load_wheel_brush_data(context: Context, *, force_rebuild: bool = False) -> tuple[bool, str]:
    """Refresh shelve (rebuild if missing or *force_rebuild*), sync WM + JSON, set loaded flag."""
    from .brush_assets import clear_preview_cache

    ok, err = ensure_brush_shelve_ready(force_rebuild=force_rebuild)
    if not ok:
        return False, err
    sync_brush_set_configs_from_shelve(context)
    clear_preview_cache()
    return True, ""


def bootstrap_wheel_brush_data_all_windows(*, force_rebuild: bool = False) -> tuple[bool, str]:
    """After add-on enable: ensure shelve, then sync ``brush_set_configs`` on every window manager."""
    from .brush_assets import clear_preview_cache

    ok, err = ensure_brush_shelve_ready(force_rebuild=force_rebuild)
    if not ok:
        return False, err
    ctx = bpy.context
    if ctx is None:
        clear_preview_cache()
        return True, ""
    override = getattr(ctx, "temp_override", None)
    wms = list(bpy.data.window_managers)
    if override is None or not wms:
        try:
            sync_brush_set_configs_from_shelve(ctx)
        except Exception:
            print_debug(
                f"[Sculpt+] brush bootstrap sync failed: {traceback.format_exc()}"
            )
        clear_preview_cache()
        return True, ""
    for wm in wms:
        try:
            with ctx.temp_override(window_manager=wm):
                sync_brush_set_configs_from_shelve(bpy.context)
        except Exception:
            print_debug(
                f"[Sculpt+] brush bootstrap sync (wm) failed: {traceback.format_exc()}"
            )
    clear_preview_cache()
    return True, ""


def ensure_brush_sets_loaded(context: Context) -> bool:
    from .data import SculptWheelData

    wd = SculptWheelData.get(context)
    if wd.brush_sets_loaded:
        return True
    ok, _err = load_wheel_brush_data(context, force_rebuild=False)
    return ok


def schedule_wheel_brush_bootstrap() -> None:
    """Deferred one-shot: build shelve if missing, then sync all window managers (after enable)."""
    from ..core.globals import GLOBALS

    def _timer():
        try:
            c = bpy.context
            if c is None:
                return 0.1
            if c.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME) is None:
                return 0.1
            ok, err = bootstrap_wheel_brush_data_all_windows(force_rebuild=False)
            if not ok:
                print_debug(f"[Sculpt+] brush library bootstrap failed: {err}")
        except Exception:
            print_debug(
                f"[Sculpt+] brush library bootstrap: {traceback.format_exc()}"
            )
        return None

    bpy.app.timers.register(_timer, first_interval=0.15)


