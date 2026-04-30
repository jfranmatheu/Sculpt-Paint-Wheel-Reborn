from pathlib import Path
import sys
import zlib

import bpy


_ESSENTIALS_BLEND_IDS = (
    "mesh_sculpt",
    "mesh_weight",
    "mesh_texture",
    "mesh_vertex",
    "gp_weight",
    "gp_vertex",
    "gp_draw",
    "gp_sculpt",
    "curve_sculpt",
)


def _log(message: str) -> None:
    print(f"[Sculpt+][essentials-bg] {message}", flush=True)


def _safe_essential_brush_name(brush_name: str) -> str:
    return brush_name.replace("/", "_").replace("\\", "_")


def _get_essential_preview_key(mode_id: str, brush_name: str) -> str:
    return f"{mode_id}__{_safe_essential_brush_name(brush_name)}"


def _write_preview(path: Path, w: int, h: int, pixels_float) -> None:
    data = bytes(int(max(0.0, min(1.0, p)) * 255) for p in pixels_float)
    compressed = zlib.compress(data, 6)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(w.to_bytes(4, "little"))
        f.write(h.to_bytes(4, "little"))
        f.write(compressed)


def _iter_loaded_brushes(blend_path: Path):
    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        names = [name for name in data_from.brushes if name]
        data_to.brushes = names
    for brush in data_to.brushes:
        if brush is not None:
            yield brush


def generate_all(asset_root: Path, output_dir: Path) -> int:
    _log(f"Asset root: {asset_root}")
    _log(f"Output dir: {output_dir}")
    written = 0
    for blend_id in _ESSENTIALS_BLEND_IDS:
        blend_path = asset_root / f"essentials_brushes-{blend_id}.blend"
        if not blend_path.is_file():
            _log(f"SKIP missing blend file: {blend_path.name}")
            continue
        _log(f"Loading blend file: {blend_path.name}")

        loaded_count = 0
        for brush in _iter_loaded_brushes(blend_path):
            loaded_count += 1
            preview = brush.preview or brush.preview_ensure()
            brush_name = brush.name
            if '.' in brush_name:
                brush_name = brush_name.split('.')[0]
            if not preview:
                _log(f"SKIP no preview: {brush_name}")
                continue

            # image_pixels_float contains the full preview buffer.
            # Use image_size so header and payload lengths match.
            w, h = preview.image_size
            if w <= 0 or h <= 0:
                _log(f"SKIP zero icon size: {brush_name} ({w}x{h})")
                continue

            pixels = preview.image_pixels_float
            if not pixels:
                _log(f"SKIP empty pixels: {brush_name}")
                continue

            file_name = f"{_get_essential_preview_key(blend_id, brush_name)}.bin"
            _write_preview(output_dir / file_name, w, h, pixels)
            written += 1
            _log(f"WROTE {file_name} ({w}x{h})")

            bpy.data.brushes.remove(brush)

        _log(f"Finished {blend_path.name}, loaded brushes: {loaded_count}")

    return written


def _parse_args() -> tuple[Path, Path]:
    if "--" not in sys.argv:
        raise RuntimeError("Missing '--' separator for script arguments")
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) < 2:
        raise RuntimeError("Expected: <asset_root_dir> <output_dir>")
    return Path(argv[0]), Path(argv[1])


def main() -> int:
    asset_root, output_dir = _parse_args()
    _log("Starting essentials preview generation")
    generated = generate_all(asset_root, output_dir)
    _log(f"Generated {generated} essentials previews at: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
