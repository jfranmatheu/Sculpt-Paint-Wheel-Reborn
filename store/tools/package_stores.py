"""Gather everything to publish on each store into build/store/upload/<store>/ (ignored by git).

Usage (after build_release.py --store, superhive/build_docs.py and build_guide_pdf.py):
    python store/tools/package_stores.py

Each folder holds, ready to upload or paste:
    product/    the add-on zip (store build) and the illustrated user guide (PDF)
    gallery/    16:9 gallery images, in upload order (01 is the cover)
    videos/     the theme videos (mp4, 1920x1080)
    description.html (and docs.html for Superhive)
"""
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = ROOT / "store"
BUILD = ROOT / "build" / "store"
UPLOAD = BUILD / "upload"

version = re.search(r'^version\s*=\s*"([^"]+)"', (ROOT / "spwheel" / "blender_manifest.toml").read_text(encoding="utf-8"), re.M).group(1)
zip_path = BUILD / "superhive" / f"spwheel-{version}.zip"
guide = BUILD / "Sculpt-Paint Wheel 2 - User Guide.pdf"
for f in (zip_path, guide):
    if not f.exists():
        raise SystemExit(f"missing {f}: build it first (see the usage)")

PAGES = {"superhive": ["description.html", "docs.html"], "payhip": ["description.html"]}
if UPLOAD.exists():
    shutil.rmtree(UPLOAD)
for store, pages in PAGES.items():
    out = UPLOAD / store
    (out / "product").mkdir(parents=True)
    shutil.copy2(zip_path, out / "product")
    shutil.copy2(guide, out / "product")
    shutil.copytree(STORE / "media" / "gallery", out / "gallery")
    (out / "videos").mkdir()
    for mp4 in (STORE / "media" / "videos").glob("*.mp4"):
        shutil.copy2(mp4, out / "videos")
    for page in pages:
        shutil.copy2(STORE / store / page, out / page)
    print("ready:", out, sorted(p.name for p in out.rglob("*") if p.is_file()))
