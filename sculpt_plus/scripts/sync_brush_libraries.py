"""Run inside Blender (--background --python) to build/update libraries.json + preview .bin files.

Scans preferences asset libraries, loads sculpt brushes from each .blend,
compresses preview pixels as RGBA8 .bin, writes the global index.

Usage:
    blender --background --python sync_brush_libraries.py [--force]
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import zlib
from pathlib import Path
from typing import Any

import bpy


# ──────────────────────────────────────────────────────────────────────
# ID helpers (mirror of src/brush_management/ids.py, standalone here)
# ──────────────────────────────────────────────────────────────────────

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _library_id(library_path: str) -> str:
    return _sha1(str(Path(library_path).resolve()))


def _blend_id(blend_path: str, mtime: float, size: int) -> str:
    return _sha1(f"{Path(blend_path).resolve()}|{mtime}|{size}")


def _brush_id(blend_path: str, brush_name: str) -> str:
    return _sha1(f"{Path(blend_path).resolve()}|{brush_name}")


def _preview_hash(library_name: str, blend_stem: str, brush_name: str) -> str:
    return _sha1(f"{library_name}|{blend_stem}|{brush_name}")


def _preview_rel(hash_id: str) -> str:
    return f"previews/{hash_id[:2]}/{hash_id[2:4]}/{hash_id}.bin"


def _display_title_from_blend_stem(stem: str) -> str:
    """Match ``brush_management.runtime.blend_file_display_title`` for console labels."""
    s = (stem or "").strip()
    if not s:
        return ""
    return s.replace("_", " ").replace("-", " ").title()


# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────

def _cache_dir() -> Path:
    return Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data" / "cache"


def _libraries_json_path() -> Path:
    return _cache_dir() / "libraries.json"


# ──────────────────────────────────────────────────────────────────────
# Essentials (builtin)
# ──────────────────────────────────────────────────────────────────────

ESSENTIAL_GROUPS: dict[str, set[str]] = {
    "Add": {
        "Blob", "Clay", "Clay Strips", "Clay Thumb", "Crease Polish",
        "Crease Sharp", "Draw", "Draw Sharp", "Inflate/Deflate", "Layer",
    },
    "Trim/Scrape": {
        "Fill/Deepen", "Flatten/Contrast", "Plateau", "Scrape Multiplane",
        "Scrape/Fill", "Smooth", "Trim",
    },
    "Grab/Rotate": {
        "Boundary", "Elastic Grab", "Elastic Snake Hook", "Grab", "Grab 2D",
        "Grab Shilouette", "Nudge", "Pinch/Magnify", "Pose", "Pull",
        "Relax Pinch", "Relax Slide", "Snake Hook", "Thumb", "Twist",
    },
    "Mask/Multi-res": {
        "Density", "Eraser Multires Displacement", "Face Set Paint",
        "Mask", "Smear Multires Displacement",
    },
    "Paint": {
        "Airbrush", "Blend Hard", "Blend Soft", "Blend Square", "Paint Blend",
        "Paint Hard", "Paint Hard Pressure", "Paint Soft", "Paint Soft Pressure",
        "Paint Square", "Sharpen", "Smear",
    },
    "Cloth": {
        "Bend Boundary Cloth", "Bend/Twist Cloth", "Drag Cloth",
        "Expand/Contract Cloth", "Grab Cloth", "Grab Planar Cloth",
        "Grab Random Cloth", "Inflate Cloth", "Pinch Folds Cloth",
        "Pinch Point Cloth", "Push Cloth", "Stretch/Move Cloth",
        "Twist Boundary Cloth",
    },
}
ESSENTIAL_BRUSH_NAMES: set[str] = set().union(*ESSENTIAL_GROUPS.values())


def _essentials_relative_id(brush_name: str) -> str:
    blend = "essentials_brushes-mesh_sculpt.blend"
    return f"brushes/{blend}/Brush/{brush_name}".replace("\\", "/")


def _user_relative_id(library_path: Path, blend_file: Path, brush_name: str) -> str:
    import os
    lib = library_path.resolve()
    bf = blend_file.resolve()
    try:
        rel_blend = os.path.relpath(bf, lib).replace(os.sep, "/")
        if rel_blend.startswith(".."):
            rel_blend = bf.name
    except Exception:
        rel_blend = bf.name
    return f"{rel_blend}/Brush/{brush_name}"


def _user_relative_id_from_brush(brush, library_path: Path, blend_file: Path, brush_name: str) -> str:
    """Build identifier from current library root + blend path.

    Some migrated assets keep stale ``asset_weak_reference.relative_asset_identifier``
    values from old locations (e.g. user Documents library). Building from the
    current library path avoids activation against outdated paths.
    """
    return _user_relative_id(library_path, blend_file, brush_name)


# ──────────────────────────────────────────────────────────────────────
# Preview writing
# ──────────────────────────────────────────────────────────────────────

def _write_preview(cache_root: Path, hash_id: str, w: int, h: int, pixels_float) -> str:
    """Compress float pixels to uint8, write .bin, return relative path."""
    data = bytes(int(max(0.0, min(1.0, p)) * 255) for p in pixels_float)
    compressed = zlib.compress(data, 6)
    rel = _preview_rel(hash_id)
    full = cache_root / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    with full.open("wb") as f:
        f.write(w.to_bytes(4, "little"))
        f.write(h.to_bytes(4, "little"))
        f.write(compressed)
    return rel


# ──────────────────────────────────────────────────────────────────────
# Load existing index
# ──────────────────────────────────────────────────────────────────────

def _load_existing_index() -> dict[str, Any]:
    path = _libraries_json_path()
    if not path.is_file():
        return {"version": 1, "generated_at": 0, "libraries": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("libraries"), dict):
            return data
    except Exception:
        pass
    return {"version": 1, "generated_at": 0, "libraries": {}}


# ──────────────────────────────────────────────────────────────────────
# Main sync
# ──────────────────────────────────────────────────────────────────────

MAX_BRUSHES_PER_PAGE = 20
INDEX_VERSION = 2


def _load_brushes_from_blend(blend_file: Path, *, assets_only: bool) -> list[Any]:
    """Load brushes from *blend_file* and return loaded Brush datablocks."""
    with bpy.data.libraries.load(str(blend_file), link=False, assets_only=assets_only) as (data_from, data_to):
        data_to.brushes = data_from.brushes
    return [b for b in (data_to.brushes or []) if b is not None]


def _default_user_prefs() -> dict[str, Any]:
    return {"active_page": 0, "custom_order": [], "favorites": []}


def _chunk_pages_ordered(ordered_brush_ids: list[str]) -> list[dict[str, Any]]:
    """Split ordered brush ids into pages of max size; names ``Page 1``, ``Page 2``, …."""
    if not ordered_brush_ids:
        return []
    pages: list[dict[str, Any]] = []
    for i in range(0, len(ordered_brush_ids), MAX_BRUSHES_PER_PAGE):
        chunk = ordered_brush_ids[i : i + MAX_BRUSHES_PER_PAGE]
        pages.append({"name": f"Page {len(pages) + 1}", "brushes": chunk})
    return pages


def _user_prefs_for_path(old_lib: dict | None, blend_path: str, blend_key: str) -> dict[str, Any]:
    """Prefer prefs from an old blend with same *blend_path*; else ``blend_key``; else defaults."""
    if old_lib is None:
        return _default_user_prefs()
    blends = old_lib.get("blends") or {}
    for ob in blends.values():
        if isinstance(ob, dict) and ob.get("path") == blend_path:
            return dict(ob.get("user_prefs") or _default_user_prefs())
    old_blend = blends.get(blend_key)
    if isinstance(old_blend, dict):
        return dict(old_blend.get("user_prefs") or _default_user_prefs())
    return _default_user_prefs()


def main() -> None:
    force = "--force" in sys.argv

    for brush in reversed(bpy.data.brushes):
        bpy.data.brushes.remove(brush)

    cache_root = _cache_dir()
    cache_root.mkdir(parents=True, exist_ok=True)
    (cache_root / "previews").mkdir(parents=True, exist_ok=True)

    existing_index = _load_existing_index()
    existing_libs: dict[str, Any] = existing_index.get("libraries", {})

    prefs = bpy.context.preferences
    blender_local = Path(bpy.utils.resource_path("LOCAL"))
    essentials_blend = blender_local / "datafiles" / "assets" / "brushes" / "essentials_brushes-mesh_sculpt.blend"

    new_libraries: dict[str, Any] = {}

    # ── Essentials (builtin) ──────────────────────────────────────────
    essentials_lib_id = _library_id("BUILTIN_ESSENTIALS")
    old_essentials = existing_libs.get(essentials_lib_id)

    if not force and old_essentials and old_essentials.get("builtin"):
        print(f"[Sync] Essentials: unchanged (builtin), skipping.")
        new_libraries[essentials_lib_id] = old_essentials
    else:
        print(f"[Sync] Essentials: scanning...")
        essentials_lib: dict[str, Any] = {
            "name": "Essentials",
            "path": "",
            "last_scan": time.time(),
            "builtin": True,
            "blends": {},
        }

        if not essentials_blend.is_file():
            print(f"  ! Essentials blend not found: {essentials_blend}")
        else:
            stat = essentials_blend.stat()
            bid = _blend_id(str(essentials_blend), stat.st_mtime, stat.st_size)
            essentials_path = str(essentials_blend.resolve())
            allowed_names: set[str] = set()
            for names in ESSENTIAL_GROUPS.values():
                allowed_names |= names

            with bpy.data.libraries.load(str(essentials_blend), link=False, assets_only=True) as (data_from, data_to):
                data_to.brushes = data_from.brushes

            brushes_out: dict[str, Any] = {}
            try:
                for brush in data_to.brushes:
                    if not brush.use_paint_sculpt:
                        continue
                    if brush.name not in allowed_names:
                        continue

                    preview = brush.preview_ensure()
                    if preview is None:
                        continue
                    w, h = preview.image_size
                    if w <= 0 or h <= 0:
                        continue
                    try:
                        pixels = preview.image_pixels_float[:]
                    except Exception:
                        continue
                    if len(pixels) != w * h * 4:
                        continue

                    stem = essentials_blend.stem
                    phash = _preview_hash("Essentials", stem, brush.name)
                    prev_rel = _write_preview(cache_root, phash, w, h, pixels)
                    brid = _brush_id(str(essentials_blend), brush.name)

                    brushes_out[brid] = {
                        "name": brush.name,
                        "type": "SCULPT",
                        "preview": {
                            "path": prev_rel,
                            "width": w,
                            "height": h,
                            "format": "RGBA8",
                            "compression": "zlib",
                        },
                        "asset_library_type": "ESSENTIALS",
                        "asset_library_identifier": "",
                        "relative_asset_identifier": _essentials_relative_id(brush.name),
                    }
                    print(f"    > {brush.name}")
            finally:
                for brush in reversed(bpy.data.brushes):
                    try:
                        bpy.data.brushes.remove(brush)
                    except Exception:
                        pass

            pages_out: list[dict[str, Any]] = []
            for group_name, brush_filter in ESSENTIAL_GROUPS.items():
                page_ids = sorted(
                    (
                        brid
                        for brid, bd in brushes_out.items()
                        if isinstance(bd, dict) and bd.get("name") in brush_filter
                    ),
                    key=lambda x: brushes_out[x]["name"],
                )
                if page_ids:
                    pages_out.append({"name": group_name, "brushes": page_ids})

            if brushes_out:
                essentials_lib["blends"][bid] = {
                    "file_name": essentials_blend.stem,
                    "path": essentials_path,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                    "brush_count": len(brushes_out),
                    "brushes": brushes_out,
                    "pages": pages_out,
                    "user_prefs": _user_prefs_for_path(old_essentials, essentials_path, bid),
                }

        new_libraries[essentials_lib_id] = essentials_lib

    # ── User asset libraries ──────────────────────────────────────────
    libraries_to_scan = []
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        for arg in sys.argv[idx + 1:]:
            if "|" in arg:
                name, path_str = arg.split("|", 1)
                libraries_to_scan.append({"name": name, "path": path_str})

    if not libraries_to_scan:
        for asset_library in prefs.filepaths.asset_libraries:
            libraries_to_scan.append({
                "name": asset_library.name,
                "path": bpy.path.abspath(asset_library.path)
            })

    for lib_info in libraries_to_scan:
        library_name = lib_info["name"]
        library_path = Path(lib_info["path"])
        if not library_path.is_dir():
            print(f"[Sync] {library_name}: path not a directory, skipping.")
            continue

        lid = _library_id(str(library_path))
        old_lib = existing_libs.get(lid)

        blend_files = sorted(
            [fp for fp in library_path.rglob("*.blend") if fp.is_file()],
            key=lambda p: p.name.lower(),
        )

        if not blend_files:
            print(f"[Sync] {library_name}: no .blend files found.")
            continue

        lib_changed = force
        if not lib_changed and old_lib:
            old_blends = old_lib.get("blends", {})
            old_paths = {b.get("path"): b for b in old_blends.values() if isinstance(b, dict)}
            for bf in blend_files:
                stat = bf.stat()
                old_blend = old_paths.get(str(bf.resolve()))
                if old_blend is None:
                    lib_changed = True
                    break
                if abs(old_blend.get("mtime", 0) - stat.st_mtime) > 0.01 or old_blend.get("size", 0) != stat.st_size:
                    lib_changed = True
                    break
        elif not old_lib:
            lib_changed = True

        if not lib_changed:
            print(f"[Sync] {library_name}: unchanged, keeping cached data.")
            new_libraries[lid] = old_lib
            continue

        print(f"[Sync] {library_name}: changes detected, rebuilding...")

        # Clean old previews for this library
        lib_preview_dir = cache_root / "previews" / lid[:2] / lid[2:4]
        if lib_preview_dir.is_dir():
            shutil.rmtree(lib_preview_dir, ignore_errors=True)

        lib_data: dict[str, Any] = {
            "name": library_name,
            "path": str(library_path.resolve()),
            "last_scan": time.time(),
            "builtin": False,
            "blends": {},
        }

        for blend_file in blend_files:
            print(f"  - {_display_title_from_blend_stem(blend_file.stem)} ({blend_file.name})")
            stat = blend_file.stat()
            bid = _blend_id(str(blend_file), stat.st_mtime, stat.st_size)
            loaded_brushes = _load_brushes_from_blend(blend_file, assets_only=True)
            used_fallback_load = False
            if not loaded_brushes:
                print("    · No asset-marked brushes found; retrying with assets_only=False")
                loaded_brushes = _load_brushes_from_blend(blend_file, assets_only=False)
                used_fallback_load = True

            brushes_out: dict[str, Any] = {}
            non_sculpt_count = 0
            skipped_builtin_like_count = 0
            preview_missing_count = 0
            fallback_drop_builtin_like = False
            if used_fallback_load:
                sculpt_names = [b.name for b in loaded_brushes if b and b.use_paint_sculpt]
                # If file contains custom names besides Blender essentials, drop essentials-like entries.
                fallback_drop_builtin_like = any(n not in ESSENTIAL_BRUSH_NAMES for n in sculpt_names)
            try:
                for brush in loaded_brushes:
                    if not brush.use_paint_sculpt:
                        non_sculpt_count += 1
                        continue
                    if fallback_drop_builtin_like and brush.name in ESSENTIAL_BRUSH_NAMES:
                        skipped_builtin_like_count += 1
                        continue

                    prev_rel = ""
                    w = 0
                    h = 0
                    preview = brush.preview_ensure()
                    if preview is None:
                        preview_missing_count += 1
                        print(f"    ! {brush.name}: no preview (indexed anyway)")
                    else:
                        w, h = preview.image_size
                        if w <= 0 or h <= 0:
                            preview_missing_count += 1
                            print(f"    ! {brush.name}: invalid preview size {w}x{h} (indexed anyway)")
                            w = 0
                            h = 0
                        else:
                            try:
                                pixels = preview.image_pixels_float[:]
                            except Exception:
                                preview_missing_count += 1
                                print(f"    ! {brush.name}: failed reading preview pixels (indexed anyway)")
                                pixels = None
                            if pixels is not None:
                                if len(pixels) != w * h * 4:
                                    preview_missing_count += 1
                                    print(f"    ! {brush.name}: pixel count mismatch (indexed anyway)")
                                    w = 0
                                    h = 0
                                else:
                                    phash = _preview_hash(library_name, blend_file.stem, brush.name)
                                    prev_rel = _write_preview(cache_root, phash, w, h, pixels)
                    brid = _brush_id(str(blend_file), brush.name)

                    brushes_out[brid] = {
                        "name": brush.name,
                        "type": "SCULPT",
                        "preview": {
                            "path": prev_rel,
                            "width": w,
                            "height": h,
                            "format": "RGBA8",
                            "compression": "zlib",
                        },
                        "asset_library_type": "CUSTOM",
                        "asset_library_identifier": library_name,
                        "relative_asset_identifier": _user_relative_id_from_brush(
                            brush, library_path, blend_file, brush.name,
                        ),
                    }
                    print(f"    > {brush.name}")
                if not brushes_out:
                    print(
                        f"    ! No sculpt brushes indexed (loaded={len(loaded_brushes)}, "
                        f"non_sculpt={non_sculpt_count}, skipped_builtin_like={skipped_builtin_like_count})"
                    )
                elif preview_missing_count:
                    print(f"    · Indexed {len(brushes_out)} brushes ({preview_missing_count} without preview image)")
            finally:
                for brush in reversed(bpy.data.brushes):
                    try:
                        bpy.data.brushes.remove(brush)
                    except Exception:
                        pass

            if brushes_out:
                ordered_ids = sorted(
                    brushes_out.keys(),
                    key=lambda x: str(brushes_out[x].get("name", "")).lower(),
                )
                pages_out = _chunk_pages_ordered(ordered_ids)
                lib_data["blends"][bid] = {
                    "file_name": blend_file.stem,
                    "path": str(blend_file.resolve()),
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                    "brush_count": len(brushes_out),
                    "brushes": brushes_out,
                    "pages": pages_out,
                    "user_prefs": _user_prefs_for_path(
                        old_lib, str(blend_file.resolve()), bid,
                    ),
                }

        new_libraries[lid] = lib_data

    # ── Write final index ─────────────────────────────────────────────
    output = {
        "version": INDEX_VERSION,
        "generated_at": time.time(),
        "libraries": new_libraries,
    }

    json_path = _libraries_json_path()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    total_brushes = sum(
        b.get("brush_count", 0)
        for lib in new_libraries.values()
        for b in (lib.get("blends") or {}).values()
        if isinstance(b, dict)
    )
    print(f"\n[Sync] Done: {len(new_libraries)} libraries, {total_brushes} brushes total.")
    sys.exit(0)


if __name__ == "__main__":
    main()
