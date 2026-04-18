"""Disk persistence for sculpt wheel custom button sets only."""

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
from ..core.globals import GLOBALS, PATHS

from .data import MAX_CUSTOM_BUTTON_SETS, MAX_CUSTOM_BUTTONS_PER_SET

JSON_VERSION = 2

_save_timer_pending = False
_last_saved_fingerprint: str | None = None


def data_root() -> Path:
    return Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data"


def custom_buttons_json_path() -> Path:
    return data_root() / "custom_buttons.json"


def custom_button_icons_dir() -> Path:
    return data_root() / "icons" / "custom_buttons"


def ensure_data_dirs() -> None:
    data_root().mkdir(parents=True, exist_ok=True)
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


def _rel_under_addon_root(abs_path: Path) -> str | None:
    """Relative path from add-on root (for bundled icons); ``None`` if outside."""
    try:
        return abs_path.resolve().relative_to(PATHS.ROOT.resolve()).as_posix()
    except ValueError:
        return None


def _copy_icon_to_custom_button(set_i: int, btn_i: int, src: Path) -> str | None:
    if not src.is_file():
        return None
    ext = src.suffix if src.suffix else ".png"
    dest = custom_button_icons_dir() / f"set{set_i:02d}_btn{btn_i:02d}{ext}"
    try:
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        return str(dest.resolve())
    except OSError:
        print_debug(f"[Sculpt+] custom button icon copy failed: {traceback.format_exc()}")
        return None


def _storage_fingerprint(context: Context) -> str:
    from .data import get_wheel_storage

    st = get_wheel_storage(context)
    payload: dict = {"sets": []}
    for s in st.custom_button_sets:
        row = {
            "n": s.name,
            "ex": bool(getattr(s, "custom_set_expanded", False)),
            "b": [],
        }
        for cb in s.custom_buttons:
            row["b"].append(
                (cb.name, cb.type, cb.popup_type, cb.attr, (cb.image_path or "").strip())
            )
        payload["sets"].append(row)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def save_wheel_storage(context: Context) -> None:
    """Write custom button sets JSON and normalize icon files under data_root."""
    from .data import get_wheel_storage

    global _last_saved_fingerprint

    ensure_data_dirs()
    st = get_wheel_storage(context)

    sets_out: list[dict] = []
    for si, bset in enumerate(st.custom_button_sets):
        buttons_out = []
        for bi, btn in enumerate(bset.custom_buttons):
            src = _norm_abs(btn.image_path)
            icon_rel = None
            icon_addon = ""
            if src.is_file():
                addon_rel = _rel_under_addon_root(src)
                if addon_rel is not None:
                    # Bundled add-on icons: keep RNA path as-is; persist relative path only.
                    icon_addon = addon_rel
                else:
                    new_abs = _copy_icon_to_custom_button(si, bi, src)
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
                    "icon_addon": icon_addon,
                }
            )
        sets_out.append(
            {
                "name": bset.name,
                "expanded": bool(getattr(bset, "custom_set_expanded", False)),
                "custom_buttons": buttons_out,
            }
        )

    try:
        custom_buttons_json_path().write_text(
            json.dumps(
                {"version": JSON_VERSION, "custom_button_sets": sets_out},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        _last_saved_fingerprint = _storage_fingerprint(context)
    except OSError:
        print_debug(f"[Sculpt+] custom buttons save failed: {traceback.format_exc()}")


def touch_wheel_storage_save_debounced(context: Context, delay: float = 0.4) -> None:
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
            print_debug(f"[Sculpt+] debounced save: {traceback.format_exc()}")
        return None

    bpy.app.timers.register(_flush, first_interval=delay)


def _load_button_dict_into_collection(bset, bd: dict) -> None:
    b = bset.custom_buttons.add()
    b.name = str(bd.get("name", "Custom"))
    b.type = str(bd.get("type", "OPERATOR"))
    b.popup_type = str(bd.get("popup_type", "NONE"))
    b.attr = str(bd.get("attr", ""))
    ia = (bd.get("icon_addon") or "").strip()
    if ia:
        p = PATHS.ROOT / ia.replace("\\", "/")
        if p.is_file():
            b.image_path = str(p.resolve())
            return
    rel = bd.get("icon") or ""
    if rel:
        p = data_root() / str(rel)
        if p.is_file():
            b.image_path = str(p.resolve())


def load_custom_buttons_if_empty(context: Context) -> None:
    global _last_saved_fingerprint

    from .data import get_wheel_storage

    ensure_data_dirs()
    st = get_wheel_storage(context)

    if len(st.custom_button_sets) > 0:
        from .default_custom_buttons import repair_missing_icon_paths

        repair_missing_icon_paths(st)
        try:
            _last_saved_fingerprint = _storage_fingerprint(context)
        except Exception:
            _last_saved_fingerprint = None
        return

    if not custom_buttons_json_path().is_file():
        from .default_custom_buttons import apply_default_custom_button_set

        s = st.custom_button_sets.add()
        apply_default_custom_button_set(s)
        save_wheel_storage(context)
        try:
            _last_saved_fingerprint = _storage_fingerprint(context)
        except Exception:
            _last_saved_fingerprint = None
        return

    try:
        raw = json.loads(custom_buttons_json_path().read_text(encoding="utf-8"))
        ver = raw.get("version", 1)

        if ver >= 2 and isinstance(raw.get("custom_button_sets"), list):
            for sd in raw["custom_button_sets"]:
                if not isinstance(sd, dict):
                    continue
                if len(st.custom_button_sets) >= MAX_CUSTOM_BUTTON_SETS:
                    break
                s = st.custom_button_sets.add()
                s.name = str(sd.get("name") or "Button set")
                s.custom_set_expanded = bool(sd.get("expanded", False))
                arr = sd.get("custom_buttons")
                if not isinstance(arr, list):
                    continue
                for bd in arr:
                    if not isinstance(bd, dict):
                        continue
                    if len(s.custom_buttons) >= MAX_CUSTOM_BUTTONS_PER_SET:
                        break
                    _load_button_dict_into_collection(s, bd)
        else:
            arr = raw.get("custom_buttons")
            if isinstance(arr, list):
                s = st.custom_button_sets.add()
                s.name = "Default"
                for bd in arr:
                    if not isinstance(bd, dict):
                        continue
                    if len(s.custom_buttons) >= MAX_CUSTOM_BUTTONS_PER_SET:
                        break
                    _load_button_dict_into_collection(s, bd)

        if len(st.custom_button_sets) == 0:
            from .default_custom_buttons import apply_default_custom_button_set

            s = st.custom_button_sets.add()
            apply_default_custom_button_set(s)

        st.custom_button_set_active_index = 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        print_debug(f"[Sculpt+] custom buttons load failed: {traceback.format_exc()}")
        if len(st.custom_button_sets) == 0:
            from .default_custom_buttons import apply_default_custom_button_set

            s = st.custom_button_sets.add()
            apply_default_custom_button_set(s)

    from .default_custom_buttons import repair_missing_icon_paths

    repair_missing_icon_paths(st)
    try:
        _last_saved_fingerprint = _storage_fingerprint(context)
    except Exception:
        _last_saved_fingerprint = None


def schedule_custom_buttons_load() -> None:
    def _timer():
        try:
            c = bpy.context
            if c is None:
                return 0.1
            addon = c.preferences.addons.get(GLOBALS.ADDON.PACKAGE_NAME)
            if addon is None:
                return 0.1
            load_custom_buttons_if_empty(c)
        except Exception:
            print_debug(f"[Sculpt+] custom buttons deferred load: {traceback.format_exc()}")
        return None

    bpy.app.timers.register(_timer, first_interval=0.05)
