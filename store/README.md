# Store pages

Marketing material for the store listing of Sculpt-Paint Wheel. This folder isn't part of the add-on.

| Store | Product page | Contents |
|---|---|---|
| [Superhive](superhive/) | https://superhivemarket.com/products/sculpt-paint-wheel | `description.html` (product description), `docs.html` (documentation tab, generated from `DOCS.md` by `build_docs.py`), `images/` and `videos/` |

## Superhive HTML

Superhive's description and documentation editors don't accept `<head>`, `<style>` or styled markup. `description.html` and `docs.html` are therefore plain HTML fragments: **paste each file as a whole**. They only use headings, paragraphs, lists, links and images; the images carry the visual design.

Images and animations load from `store/superhive/` on the repository's **`main`** branch, so merge the branch that adds them before pasting the pages into Superhive.

`docs.html` is generated: edit `DOCS.md`, then run `python store/superhive/build_docs.py` (needs `pip install markdown`). It swaps the GitHub-oriented parts of `DOCS.md` for store ones (graphics, chapter banners, help through Superhive, no repository links).

## Version 2 graphics and videos

Everything is made from the real add-on running in Blender 5.3:

1. **Capture** with `store/tools/capture_v2.py`, once per part (`modes`, `centre`, `themes`, `double`, `prefs`, `tints`, `presets`). Use an isolated Blender profile (`BLENDER_USER_RESOURCES`) with the extension installed as `user_default/spwheel` and no saved preferences, so the defaults are captured:
   ```
   blender --factory-startup --enable-event-simulate --window-geometry 0 0 1920 1200 --python store/tools/capture_v2.py -- <captures dir> <part>
   ```
2. **Graphics**: `python store/tools/v2_graphics.py <captures dir> <output dir>` renders `v2_01_hero.png` ... `v2_14_anatomy.png` and the chapter banners `v2_ch01.png` ... `v2_ch10.png` (1600 px wide, rounded transparent corners). Copy them to `superhive/images/`.
3. **Videos**: `python store/tools/theme_montage.py <captures dir>/tints <output dir> tints` and `... /presets <output dir> presets` (needs ffmpeg) make the theme videos (`.mp4` for the gallery, animated `.webp` for the pages). Copy them to `superhive/videos/`.

## Build for the stores

```
python store/tools/build_release.py
```

Creates `build/store/spwheel-<version>.zip` (ignored by git) with Blender's own extension builder, from the git-tracked files only, and validates it. Upload that zip as the product file on Superhive. Blender is found automatically; pass `--blender PATH` to choose one.

## Wording

- Store pages sell the add-on: what it does for the artist, what's new, and that purchases fund an independent developer. No "free" or repository messaging, and no links to GitHub: help and questions go through Superhive.
- No pricing talk in images, so they can be reused anywhere.
