"""In-memory cache of brush_assets shelve + background DB build."""

from __future__ import annotations

import shelve
import subprocess
import traceback
from pathlib import Path
from typing import Any

import bpy

from ..core.debug import print_debug
from ..core.globals import GLOBALS, PATHS
from subprocess import CompletedProcess

# Deep copy of shelve contents (serializable dicts only)
_cache: dict[str, Any] = {}


def sculpt_data_root() -> Path:
    return Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data"


def brush_shelve_base() -> Path:
    return sculpt_data_root() / "brush_assets"


def brush_database_exists() -> bool:
    base = brush_shelve_base()
    parent = base.parent
    stem = base.name
    return any(parent.glob(f"{stem}.*"))


def _read_shelve_into_dict() -> dict[str, Any]:
    base = brush_shelve_base()
    if not brush_database_exists():
        return {}
    out: dict[str, Any] = {}
    try:
        with shelve.open(str(base), flag="r") as db:
            for k in db.keys():
                out[str(k)] = db[k]
    except Exception:
        print_debug(f"[Sculpt+] brush shelve read failed: {traceback.format_exc()}")
        return {}
    return out


def refresh_brush_library_cache() -> None:
    """Reload _cache from disk (call after DB build or file change)."""
    global _cache
    _cache = _read_shelve_into_dict()


def get_brush_library_cache() -> dict[str, Any]:
    """Mutable view of cached shelve data (brush-set key -> record)."""
    return _cache


def brush_set_display_label(shelve_key: str) -> str:
    """Human-readable label for the wheel enum."""
    block = get_brush_library_cache().get(shelve_key)
    if isinstance(block, dict):
        # lib = (block.get("library_name") or "").strip()
        name = (block.get("name") or shelve_key).strip() or shelve_key
        # if lib:
        #     return f"{lib} — {name}"
        return name
    return shelve_key


def list_cached_brush_set_keys() -> list[str]:
    """Sorted shelve keys for the wheel; one entry per stored brush set."""
    cache = get_brush_library_cache()
    out: list[str] = []
    for k in sorted(cache.keys(), key=str.lower):
        block = cache.get(k)
        if not isinstance(block, dict):
            continue
        if isinstance(block.get("brushes"), dict):
            out.append(k)
    return out


def flatten_brushes_for_set(set_key: str) -> list[dict[str, Any]]:
    """Ordered flat list of brush dicts for one brush set (wheel order)."""
    block = get_brush_library_cache().get(set_key)
    if not isinstance(block, dict):
        return []
    brushes = block.get("brushes") or {}
    if not isinstance(brushes, dict):
        return []
    set_label = block.get("name") or block.get("set_label")
    if not isinstance(set_label, str) or not set_label.strip():
        set_label = str(set_key)
    entries: list[dict[str, Any]] = []
    for brush_name in sorted(brushes.keys(), key=str.lower):
        row = brushes[brush_name]
        if not isinstance(row, dict):
            continue
        e = dict(row)
        e["brush_name"] = brush_name
        e["blend_stem"] = set_label
        e["brush_set_key"] = set_key
        entries.append(e)
    return entries


def run_load_brush_sets_background() -> tuple[bool, str]:
    """Spawn Blender --background to rebuild brush_assets shelve."""
    script = PATHS.ROOT / "scripts" / "load_brush_sets.py"
    if not script.is_file():
        return False, f"Missing script: {script}"

    sculpt_data_root().mkdir(parents=True, exist_ok=True)
    exe = bpy.app.binary_path
    try:
        proc = subprocess.Popen(
            [exe, "--background", "--python", str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        # Stream the subprocess output to the terminal in real-time
        for line in proc.stdout:
            print(line, end='')
        proc.wait()
        proc.stdout.close()
        # Build a CompletedProcess-like object for downstream compatibility
        proc = CompletedProcess(proc.args, proc.returncode)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-2000:]
            print(tail)
            print_debug(f"[Sculpt+] brush DB build failed: {tail}")
            return False, tail or f"exit {proc.returncode}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "Timed out building brush database"
    except Exception as e:
        return False, str(e)


def ensure_brush_asset_database() -> None:
    """Create shelve via background Blender if missing."""
    if brush_database_exists():
        return
    ok, err = run_load_brush_sets_background()
    if not ok:
        print_debug(f"[Sculpt+] brush DB build failed: {err}")


def force_rebuild_brush_database() -> tuple[bool, str]:
    """Always run background script (for Reload operator)."""
    return run_load_brush_sets_background()
