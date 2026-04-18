"""Synchronization logic: detect changes and spawn background Blender."""

from __future__ import annotations

import subprocess
import traceback
from pathlib import Path

import bpy

from ...core.globals import PATHS
from .cache import (
    cache_dir,
    clean_library_previews,
    ensure_cache_dirs,
    load_libraries_index,
    save_libraries_index,
)
from .models import LibrariesIndex
from .runtime import load_from_disk, set_index


def needs_sync() -> list[tuple[str, Path]]:
    """Check asset libraries for changed .blend files.

    Returns a list of ``(library_name, library_path)`` for libraries that need re-sync.
    """
    index = load_libraries_index()
    changed: list[tuple[str, Path]] = []

    try:
        asset_libraries = list(bpy.context.preferences.filepaths.asset_libraries)
    except Exception:
        return changed

    from .ids import library_id as make_lib_id

    for asset_lib in asset_libraries:
        lib_path = Path(bpy.path.abspath(asset_lib.path))
        if not lib_path.is_dir():
            continue
        lid = make_lib_id(str(lib_path))
        lib_data = index.libraries.get(lid)
        if lib_data is None:
            changed.append((asset_lib.name, lib_path))
            continue

        blend_files = [fp for fp in lib_path.rglob("*.blend") if fp.is_file()]
        existing_blends = {b.path: b for b in lib_data.blends.values()}
        for bf in blend_files:
            stat = bf.stat()
            existing = existing_blends.get(str(bf.resolve()))
            if existing is None:
                changed.append((asset_lib.name, lib_path))
                break
            if abs(existing.mtime - stat.st_mtime) > 0.01 or existing.size != stat.st_size:
                changed.append((asset_lib.name, lib_path))
                break

    return changed


def run_sync_background(*, force: bool = False) -> tuple[bool, str]:
    """Spawn ``blender --background --python sync_brush_libraries.py``.

    If *force* is True, rebuilds everything. Otherwise only changed libraries
    are rebuilt (the script handles incremental logic).
    """
    script = PATHS.ROOT / "scripts" / "sync_brush_libraries.py"
    if not script.is_file():
        return False, f"Missing script: {script}"

    ensure_cache_dirs()
    exe = bpy.app.binary_path
    cmd = [exe, "--background", "--python", str(script)]
    if force:
        cmd.append("--force")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            print(line, end="")
        proc.wait()
        proc.stdout.close()
        if proc.returncode != 0:
            return False, f"Sync script exited with code {proc.returncode}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "Timed out running sync script"
    except Exception as e:
        return False, str(e)


def sync_and_reload(*, force: bool = False) -> tuple[bool, str]:
    """Run sync in background, then reload libraries.json into memory.

    Preserves user_prefs across syncs.
    """
    old_index = load_libraries_index()

    ok, err = run_sync_background(force=force)
    if not ok:
        return False, err

    new_index = load_from_disk()

    _restore_user_prefs(old_index, new_index)
    save_libraries_index(new_index)
    set_index(new_index)
    return True, ""


def _restore_user_prefs(old: LibrariesIndex, new: LibrariesIndex) -> None:
    """Re-inject user_prefs from old index into the newly synced index."""
    for lid, old_lib in old.libraries.items():
        new_lib = new.libraries.get(lid)
        if new_lib is None:
            continue
        for old_bid, old_blend in old_lib.blends.items():
            # Try to match by path since blend_id changes with mtime
            for new_bid, new_blend in new_lib.blends.items():
                if new_blend.path == old_blend.path:
                    new_blend.user_prefs = dict(old_blend.user_prefs)
                    break
