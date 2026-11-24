"""Wheel theme presets: built-in ones shipped with the add-on, and the user's own in the user data folder.

A preset is a JSON dict of WheelTheme values (nested dicts for the button groups). Applying a preset resets the
theme to its property defaults and then applies the preset on top, so a preset only needs the values that differ
from the defaults (the built-in "Dark" is empty: it *is* the defaults). Adding a built-in theme is adding a file to
``assets/themes`` (its file name is its name); keys starting with "_" are notes and are ignored.

The theme being drawn is always the add-on's WheelTheme: editing a setting edits it live. ``is_modified`` tells
whether it still matches the active preset (for Save / Reset).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..core.globals import PATHS

BUILTIN_DIR = Path(__file__).resolve().parent.parent / "assets" / "themes"
BUILTIN_ORDER = ("Dark", "Light")    # Listed first, in this order; other built-ins follow alphabetically.
DEFAULT_PRESET = "Dark"
META_PROPS = frozenset({"active_preset"})  # Theme properties that aren't part of a preset.
FLOAT_TOL = 1e-3


def user_dir() -> Path:
    return Path(PATHS.USER_DATA) / "themes"


def _safe_file_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "Theme"


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def builtin_names() -> list[str]:
    names = sorted(p.stem for p in BUILTIN_DIR.glob("*.json"))
    first = [n for n in BUILTIN_ORDER if n in names]
    return first + [n for n in names if n not in first]


def user_names() -> list[str]:
    d = user_dir()
    if not d.is_dir():
        return []
    builtins = set(builtin_names())
    return sorted((p.stem for p in d.glob("*.json") if p.stem not in builtins), key=str.lower)


def is_builtin(name: str) -> bool:
    return (BUILTIN_DIR / f"{name}.json").is_file()


def exists(name: str) -> bool:
    return is_builtin(name) or (user_dir() / f"{_safe_file_name(name)}.json").is_file()


def load(name: str) -> dict | None:
    if is_builtin(name):
        return _read(BUILTIN_DIR / f"{name}.json")
    return _read(user_dir() / f"{_safe_file_name(name)}.json")


def is_light_preset(name: str) -> bool:
    """A light theme (its wheel background is bright; a preset without one is the dark default)."""
    base = (load(name) or {}).get("base_color")
    if not isinstance(base, (list, tuple)) or len(base) < 3:
        return False
    return 0.2126 * base[0] + 0.7152 * base[1] + 0.0722 * base[2] > 0.5


# ----- Theme <-> dict -----------------------------------------------------------------------------------------

def _props(data):
    for prop in data.bl_rna.properties:
        pid = prop.identifier
        if pid == "rna_type" or pid in META_PROPS or pid.startswith(("bl_", "_")):
            continue
        yield pid, prop


def snapshot(data) -> dict:
    """Every value of the theme (nested groups as dicts)."""
    out = {}
    for pid, prop in _props(data):
        if prop.type == 'POINTER':
            sub = getattr(data, pid, None)
            if sub is not None and hasattr(sub, "bl_rna"):
                out[pid] = snapshot(sub)
            continue
        if prop.is_readonly:
            continue
        val = getattr(data, pid)
        if getattr(prop, "is_array", False) or hasattr(val, "__len__") and not isinstance(val, str):
            val = [round(float(v), 5) if isinstance(v, float) else v for v in val]
        elif isinstance(val, float):
            val = round(val, 5)
        out[pid] = val
    return out


def defaults(data) -> dict:
    """The property defaults of the theme, in the same shape as ``snapshot``."""
    out = {}
    for pid, prop in _props(data):
        if prop.type == 'POINTER':
            sub = getattr(data, pid, None)
            if sub is not None and hasattr(sub, "bl_rna"):
                out[pid] = defaults(sub)
            continue
        if prop.is_readonly:
            continue
        if getattr(prop, "is_array", False):
            out[pid] = [round(float(v), 5) if isinstance(v, float) else v for v in prop.default_array]
        elif prop.type == 'ENUM':
            out[pid] = prop.default
        else:
            out[pid] = round(prop.default, 5) if isinstance(prop.default, float) else prop.default
    return out


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if k.startswith("_") or k not in out:
            continue
        out[k] = _merge(out[k], v) if isinstance(out[k], dict) and isinstance(v, dict) else v
    return out


def _apply(data, payload: dict) -> None:
    for pid, prop in _props(data):
        if pid not in payload:
            continue
        val = payload[pid]
        try:
            if prop.type == 'POINTER':
                if isinstance(val, dict):
                    _apply(getattr(data, pid), val)
            elif not prop.is_readonly:
                setattr(data, pid, val)
        except Exception:
            pass  # (A value from an older / newer version: skipped.)


def expected(data, name: str) -> dict | None:
    """What the theme holds right after applying preset ``name`` (None: no such preset)."""
    payload = load(name)
    if payload is None:
        return None
    return _merge(defaults(data), payload)


def apply(data, name: str) -> bool:
    """Reset the theme to its defaults, then apply preset ``name`` and make it the active one."""
    exp = expected(data, name)
    if exp is None:
        return False
    _apply(data, exp)
    data.active_preset = name
    return True


def _same(a, b) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return all(_same(a[k], b.get(k)) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= FLOAT_TOL
        except (TypeError, ValueError):
            return False
    return a == b


def is_modified(data) -> bool:
    exp = expected(data, data.active_preset)
    return exp is None or not _same(snapshot(data), exp)


def save(data, name: str) -> Path:
    """Write the theme as the user preset ``name`` (built-in names are refused)."""
    if is_builtin(name):
        raise ValueError(f'"{name}" is a built-in theme')
    d = user_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{_safe_file_name(name)}.json"
    payload = {"_name": name, **snapshot(data)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    data.active_preset = name
    return path


def delete(name: str) -> bool:
    if is_builtin(name):
        return False
    path = user_dir() / f"{_safe_file_name(name)}.json"
    if path.is_file():
        path.unlink()
        return True
    return False
