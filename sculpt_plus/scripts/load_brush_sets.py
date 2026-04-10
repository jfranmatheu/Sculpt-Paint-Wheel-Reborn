"""Run inside Blender (--background --python) to build brush_assets shelve DB.

Scans preferences asset libraries, loads sculpt brushes from each .blend,
stores preview pixels + metadata for the sculpt wheel.
"""
from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path

import bpy
import shelve


def _essentials_relative_id(brush_name: str) -> str:
    blend = "essentials_brushes-mesh_sculpt.blend"
    return f"brushes/{blend}/Brush/{brush_name}".replace("\\", "/")


def _user_relative_id(library_path: Path, blend_file: Path, brush_name: str) -> str:
    lib = library_path.resolve()
    bf = blend_file.resolve()
    try:
        rel_blend = bf.relative_to(lib).as_posix()
    except ValueError:
        rel_blend = bf.name
    return f"{rel_blend}/Brush/{brush_name}"


@dataclass
class FakeLibrary:
    name: str
    path: str


essential_sculpt_brush_names_by_group = {
    "ADD": {'Blob', 'Clay', 'Clay Strips', 'Clay Thumb', 'Crease Polish', 'Crease Sharp', 'Draw', 'Draw Sharp', 'Inflate/Deflate', 'Layer'},
    "TRIM_SCRAPE": {'Fill/Deepen', 'Flatten/Contrast', 'Plateau', 'Scrape Multiplane', 'Scrape/Fill', 'Smooth', 'Trim'},
    "GRAB_ROTATE": {'Boundary', 'Elastic Grab', 'Elastic Snake Hook', 'Grab', 'Grab 2D', 'Grab Shilouette', 'Nudge', 'Pinch/Magnify', 'Pose', 'Pull', 'Relax Pinch', 'Relax Slide', 'Snake Hook', 'Thumb', 'Twist'},
    "MASK_AND_MULTIRES": {'Density', 'Eraser Multires Displacement', 'Face Set Paint', 'Mask', 'Smear Multires Displacement'},
    "PAINT": {'Airbrush', 'Blend Hard', 'Blend Soft', 'Blend Square', 'Paint Blend', 'Paint Hard', 'Paint Hard Pressure', 'Paint Soft', 'Paint Soft Pressure', 'Paint Square', 'Sharpen', 'Smear'},
    "CLOTH": {'Bend Boundary Cloth', 'Bend/Twist Cloth', 'Drag Cloth', 'Expand/Contract Cloth', 'Grab Cloth', 'Grab Planar Cloth', 'Grab Random Cloth', 'Inflate Cloth', 'Pinch Folds Cloth', 'Pinch Point Cloth', 'Push Cloth', 'Stretch/Move Cloth', 'Twist Boundary Cloth'},
}


def main() -> None:
    for brush in reversed(bpy.data.brushes):
        bpy.data.brushes.remove(brush)

    prefs = bpy.context.preferences
    filepaths = prefs.filepaths
    asset_libraries = list(filepaths.asset_libraries)
    blender_local_data = Path(bpy.utils.resource_path("LOCAL"))
    data_root = Path(bpy.utils.resource_path("USER")) / "sculpt_plus_data"
    data_root.mkdir(parents=True, exist_ok=True)
    db_path = str(data_root / "brush_assets")

    # Append essentials blend file.
    asset_libraries.append(
        FakeLibrary(
            name="Essentials Brushes",
            path="" # str(blender_local_data / "brushes" / "essentials_brushes-mesh_sculpt.blend")
        )
    )

    with shelve.open(db_path, flag="n") as db:
        for asset_library in asset_libraries:
            library_name = asset_library.name
            is_essential = asset_library.path == ""

            print(f"Loading asset library: {library_name} ({'essential' if is_essential else 'user'})")

            if is_essential:
                library_path = blender_local_data / "datafiles" / "assets"
                essentials_lib = library_path / "brushes" / "essentials_brushes-mesh_sculpt.blend"
                blend_files = [
                    (essentials_lib, "Essentials: Add", essential_sculpt_brush_names_by_group["ADD"]),
                    (essentials_lib, "Essentials: Trim/Scrape", essential_sculpt_brush_names_by_group["TRIM_SCRAPE"]),
                    (essentials_lib, "Essentials: Grab/Rotate", essential_sculpt_brush_names_by_group["GRAB_ROTATE"]),
                    (essentials_lib, "Essentials: Mask/Multi-res", essential_sculpt_brush_names_by_group["MASK_AND_MULTIRES"]),
                    (essentials_lib, "Essentials: Paint", essential_sculpt_brush_names_by_group["PAINT"]),
                    (essentials_lib, "Essentials: Cloth", essential_sculpt_brush_names_by_group["CLOTH"])
                ]
                asset_library_path = ""
            else:
                library_path = Path(bpy.path.abspath(asset_library.path))
                if not library_path.is_dir():
                    print(f"!Asset library path {asset_library.path} is not a directory")
                    continue
                blend_files = [(fp, None, None) for fp in library_path.rglob("*.blend") if fp.is_file()]
                asset_library_path = asset_library.path

            for (blend_file, custom_name, filter) in blend_files:
                print(f"\t- Loading blend file: {blend_file}")

                with bpy.data.libraries.load(
                    str(blend_file), link=False, assets_only=True
                ) as (data_from, data_to):
                    data_to.brushes = data_from.brushes

                brush_data: dict = {}

                try:
                    for brush in data_to.brushes:
                        if not brush.use_paint_sculpt:
                            continue
                        if filter is not None and brush.name not in filter:
                            continue
                        preview = brush.preview_ensure()
                        if preview is None:
                            print(f"\t\t!Brush {brush.name} has no preview")
                            continue
                        w, h = preview.image_size
                        if w <= 0 or h <= 0:
                            print(f"\t\t!Brush {brush.name} has invalid preview size: {w}x{h}")
                            continue
                        try:
                            pixels = list(preview.image_pixels_float[:])
                        except Exception:
                            print(f"\t\t!Brush {brush.name} has invalid preview pixels")
                            continue
                        if len(pixels) != w * h * 4:
                            print(f"\t\t!Brush {brush.name} has invalid preview pixel count: {len(pixels)}")
                            continue

                        if is_essential:
                            rel_id = _essentials_relative_id(brush.name)
                            lib_type = "ESSENTIALS"
                            lib_id = ""
                        else:
                            rel_id = _user_relative_id(library_path, blend_file, brush.name)
                            lib_type = "LOCAL"
                            lib_id = library_name

                        brush_data[brush.name] = {
                            "preview_pixels": pixels,
                            "preview_width": int(w),
                            "preview_height": int(h),
                            "blend_path": str(blend_file.resolve()),
                            "relative_asset_identifier": rel_id,
                            "asset_library_type": lib_type,
                            "asset_library_identifier": lib_id,
                        }
                        
                        print(f"\t\t> {brush.name}")

                finally:
                    for brush in reversed(bpy.data.brushes):
                        try:
                            bpy.data.brushes.remove(brush)
                        except Exception:
                            pass

                if brush_data:
                    db[custom_name if custom_name else blend_file.stem] = {
                        "name": custom_name if custom_name else blend_file.stem,
                        "library_name": library_name,
                        "library_path": asset_library_path,
                        "blend_file_path": str(blend_file.resolve()),
                        "brushes": brush_data,
                        "type": "ESSENTIAL" if is_essential else "USER",
                    }

    sys.exit(0)

print("Done")

if __name__ == "__main__":
    main()
