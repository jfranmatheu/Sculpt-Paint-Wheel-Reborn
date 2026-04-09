"""Disk persistence for sculpt wheel toolsets and custom buttons (user config dir)."""

from __future__ import annotations

import hashlib
import json
import shutil
import traceback
from pathlib import Path

import bpy
from bpy.path import abspath as bpy_abspath
from bpy.types import Context

from ..core.debug import print_debug
from ..core.globals import GLOBALS

JSON_VERSION = 1

# Debounced save after UIList reorder / RNA edits (coalesce)
_save_timer_pending = False
_last_saved_fingerprint: str | None = None


def data_root() -> Path:
    return Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data"


def toolsets_json_path() -> Path:
    return data_root() / "toolsets.json"


def custom_buttons_json_path() -> Path:
    return data_root() / "custom_buttons.json"


def brush_icons_dir() -> Path:
    return data_root() / "icons" / "brush_slots"


def custom_button_icons_dir() -> Path:
    return data_root() / "icons" / "custom_buttons"


def ensure_data_dirs() -> None:
    data_root().mkdir(parents=True, exist_ok=True)
    brush_icons_dir().mkdir(parents=True, exist_ok=True)
    custom_button_icons_dir().mkdir(parents=True, exist_ok=True)


def _norm_abs(path_str: str) -> Path:
    s = (path_str or "").strip()
    if not s:
        return Path()
    if s.startswith("//"):
        s = bpy_abspath(s)
    return Path(s).resolve()


def _rel_under_root(abs_path: Path) -> str | None:
    try:
        rel = abs_path.relative_to(data_root())
        return rel.as_posix()
    except ValueError:
        return None


def _copy_icon_to_brush_slot(ti: int, si: int, src: Path) -> str | None:
    if not src.is_file():
        return None
    ext = src.suffix if src.suffix else ".png"
    dest = brush_icons_dir() / f"ts{ti}_slot{si}{ext}"
    try:
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return str(dest.resolve())
    except OSError:
        print_debug(f"[Sculpt+] brush slot icon copy failed: {traceback.format_exc()}")
        return None


def _copy_icon_to_custom_button(i: int, src: Path) -> str | None:
    if not src.is_file():
        return None
    ext = src.suffix if src.suffix else ".png"
    dest = custom_button_icons_dir() / f"btn_{i:02d}{ext}"
    try:
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return str(dest.resolve())
    except OSError:
        print_debug(f"[Sculpt+] custom button icon copy failed: {traceback.format_exc()}")
        return None


def _storage_fingerprint(context: Context) -> str:
    from .data import get_wheel_storage, SculptWheelData

    st = get_wheel_storage(context)
    wm = SculptWheelData.get(context)
    payload = {
        "a": wm.active_toolset_index,
        "t": [],
        "c": [],
    }
    for ts in st.toolsets:
        slots = []
        for sl in ts.slots:
            slots.append(
                (
                    sl.asset_library_type,
                    sl.asset_library_identifier,
                    sl.relative_asset_identifier,
                    sl.display_name,
                    tuple(sl.slot_color),
                    (sl.custom_icon_path or "").strip(),
                )
            )
        payload["t"].append(
            (ts.name, int(ts.active_slot_index), int(len(ts.slots)), tuple(slots))
        )
    for cb in st.custom_buttons:
        payload["c"].append(
            (cb.name, cb.type, cb.popup_type, cb.attr, (cb.image_path or "").strip())
        )
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def save_wheel_storage(context: Context) -> None:
    """Write toolsets + custom buttons JSON and normalize icon files under data_root."""
    from .data import get_wheel_storage, SculptWheelData

    global _last_saved_fingerprint

    ensure_data_dirs()
    st = get_wheel_storage(context)
    wm = SculptWheelData.get(context)

    toolsets_obj = {
        "version": JSON_VERSION,
        "active_toolset_index": int(wm.active_toolset_index),
        "toolsets": [],
    }
    for ti, ts in enumerate(st.toolsets):
        slots_out = []
        for si, sl in enumerate(ts.slots):
            icon_abs = (sl.custom_icon_path or "").strip()
            custom_rel = None
            if icon_abs:
                src = _norm_abs(icon_abs)
                if src.is_file():
                    new_abs = _copy_icon_to_brush_slot(ti, si, src)
                    if new_abs:
                        sl.custom_icon_path = new_abs
                        custom_rel = _rel_under_root(Path(new_abs))
            entry = {
                "asset_library_type": sl.asset_library_type,
                "asset_library_identifier": sl.asset_library_identifier,
                "relative_asset_identifier": sl.relative_asset_identifier,
                "display_name": sl.display_name,
                "slot_color": [float(x) for x in sl.slot_color],
            }
            if custom_rel:
                entry["custom_icon"] = custom_rel
            slots_out.append(entry)
        toolsets_obj["toolsets"].append(
            {
                "name": ts.name,
                "active_slot_index": int(ts.active_slot_index),
                "slots": slots_out,
            }
        )

    buttons_out = []
    for i, btn in enumerate(st.custom_buttons):
        src = _norm_abs(btn.image_path)
        icon_rel = None
        if src.is_file():
            new_abs = _copy_icon_to_custom_button(i, src)
            if new_abs:
                btn.image_path = new_abs
                ir = _rel_under_root(Path(new_abs))
                if ir:
                    icon_rel = ir
        buttons_out.append(
            {
                "name": btn.name,
                "type": btn.type,
                "popup_type": btn.popup_type,
                "attr": btn.attr,
                "icon": icon_rel or "",
            }
        )

    try:
        toolsets_json_path().write_text(
            json.dumps(toolsets_obj, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        custom_buttons_json_path().write_text(
            json.dumps(
                {"version": JSON_VERSION, "custom_buttons": buttons_out},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        _last_saved_fingerprint = _storage_fingerprint(context)
    except OSError:
        print_debug(f"[Sculpt+] wheel persistence save failed: {traceback.format_exc()}")


def touch_wheel_storage_save_debounced(context: Context, delay: float = 0.4) -> None:
    """Coalesce saves after UIList reorder / RNA edits without operators."""
    global _save_timer_pending

    fp = _storage_fingerprint(context)
    if fp == _last_saved_fingerprint:
        return

    if _save_timer_pending:
        return
    _save_timer_pending = True

    def _flush():
        global _save_timer_pending
        _save_timer_pending = False
        try:
            c = bpy.context
            if c is not None:
                save_wheel_storage(c)
        except Exception:
            print_debug(f"[Sculpt+] debounced wheel save: {traceback.format_exc()}")
        return None

    bpy.app.timers.register(_flush, first_interval=delay)


def load_wheel_storage_if_empty(context: Context) -> None:
    """If collections are empty, hydrate from JSON when files exist."""
    from .data import get_wheel_storage, SculptWheelData
    print_debug(f"[Sculpt+] loading wheel storage if empty")

    ensure_data_dirs()
    st = get_wheel_storage(context)
    wm = SculptWheelData.get(context)

    if len(st.toolsets) == 0 and toolsets_json_path().is_file():
        try:
            raw = json.loads(toolsets_json_path().read_text(encoding="utf-8"))
            if raw.get("version") == JSON_VERSION and isinstance(raw.get("toolsets"), list):
                n_ts = len(raw["toolsets"])
                if n_ts > 0:
                    wm.active_toolset_index = max(
                        0,
                        min(int(raw.get("active_toolset_index", 0)), n_ts - 1),
                    )
                for td in raw["toolsets"]:
                    if not isinstance(td, dict):
                        continue
                    ts = st.toolsets.add()
                    print_debug(f"[Sculpt+] adding toolset: {td.get('name', 'Toolset')}")
                    ts.name = str(td.get("name", "Toolset"))
                    ts.active_slot_index = int(td.get("active_slot_index", -1))
                    for sd in td.get("slots") or []:
                        if not isinstance(sd, dict):
                            continue
                        sl = ts.slots.add()
                        print_debug(f"[Sculpt+] adding slot: {sd.get('display_name', '')}")
                        sl.asset_library_type = str(sd.get("asset_library_type", "LOCAL"))
                        sl.asset_library_identifier = str(
                            sd.get("asset_library_identifier", "")
                        )
                        sl.relative_asset_identifier = str(
                            sd.get("relative_asset_identifier", "")
                        )
                        sl.display_name = str(sd.get("display_name", ""))
                        col = sd.get("slot_color") or [0.4, 0.4, 0.4, 1.0]
                        if len(col) >= 4:
                            sl.slot_color = (
                                float(col[0]),
                                float(col[1]),
                                float(col[2]),
                                float(col[3]),
                            )
                        rel = sd.get("custom_icon")
                        if rel:
                            p = data_root() / str(rel)
                            if p.is_file():
                                sl.custom_icon_path = str(p.resolve())
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            print_debug(f"[Sculpt+] toolsets load failed: {traceback.format_exc()}")

    if len(st.custom_buttons) == 0 and custom_buttons_json_path().is_file():
        try:
            print_debug(f"[Sculpt+] loading custom buttons if empty")
            raw = json.loads(custom_buttons_json_path().read_text(encoding="utf-8"))
            arr = raw.get("custom_buttons")
            if raw.get("version") == JSON_VERSION and isinstance(arr, list):
                for bd in arr:
                    if not isinstance(bd, dict):
                        continue
                    b = st.custom_buttons.add()
                    print_debug(f"[Sculpt+] adding custom button: {bd.get('name', 'Custom')}")
                    b.name = str(bd.get("name", "Custom"))
                    b.type = str(bd.get("type", "OPERATOR"))
                    b.popup_type = str(bd.get("popup_type", "NONE"))
                    b.attr = str(bd.get("attr", ""))
                    rel = bd.get("icon") or ""
                    if rel:
                        p = data_root() / str(rel)
                        if p.is_file():
                            b.image_path = str(p.resolve())
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            print_debug(f"[Sculpt+] custom buttons load failed: {traceback.format_exc()}")

    global _last_saved_fingerprint
    try:
        _last_saved_fingerprint = _storage_fingerprint(context)
    except Exception:
        _last_saved_fingerprint = None


def schedule_load_if_empty() -> None:
    """Run after preferences exist (deferred from addon register)."""

    def _timer():
        try:
            c = bpy.context
            if c is None:
                return 0.1
            addon = c.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME)
            if addon is None:
                return 0.1
            load_wheel_storage_if_empty(c)
        except Exception:
            print_debug(f"[Sculpt+] wheel persistence load: {traceback.format_exc()}")
        return None

    bpy.app.timers.register(_timer, first_interval=0.05)
