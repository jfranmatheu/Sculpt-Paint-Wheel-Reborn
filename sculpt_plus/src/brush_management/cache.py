"""Disk cache paths and libraries.json read/write."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

import bpy

from .models import LibrariesIndex


def cache_dir() -> Path:
    """``<USER>/sculpt_plus_data/cache``."""
    return Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data" / "cache"


def libraries_json_path() -> Path:
    return cache_dir() / "libraries.json"


def previews_dir() -> Path:
    return cache_dir() / "previews"


def ensure_cache_dirs() -> None:
    cache_dir().mkdir(parents=True, exist_ok=True)
    previews_dir().mkdir(parents=True, exist_ok=True)


def load_libraries_index() -> LibrariesIndex:
    path = libraries_json_path()
    if not path.is_file():
        return LibrariesIndex()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return LibrariesIndex()
        return LibrariesIndex.from_dict(data)
    except Exception:
        print(f"[Sculpt+] libraries.json read failed: {traceback.format_exc()}")
        return LibrariesIndex()


def save_libraries_index(index: LibrariesIndex) -> None:
    ensure_cache_dirs()
    path = libraries_json_path()
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(index.to_dict(), f, indent=2, ensure_ascii=False)
    except Exception:
        print(f"[Sculpt+] libraries.json write failed: {traceback.format_exc()}")


def save_user_prefs_only(index: LibrariesIndex) -> None:
    """Merge only user_prefs into existing JSON without overwriting library data."""
    existing = load_libraries_index()
    for lid, lib in index.libraries.items():
        existing_lib = existing.libraries.get(lid)
        if existing_lib is None:
            continue
        for bid, blend in lib.blends.items():
            existing_blend = existing_lib.blends.get(bid)
            if existing_blend is None:
                continue
            existing_blend.user_prefs = dict(blend.user_prefs)
    save_libraries_index(existing)


def clean_library_previews(lib_id: str) -> None:
    """Remove all preview .bin files for a given library."""
    lib_dir = previews_dir() / lib_id
    if lib_dir.is_dir():
        import shutil
        shutil.rmtree(lib_dir, ignore_errors=True)
