# Store pages

Marketing material for the store listings of Sculpt-Paint Wheel. This folder isn't part of the add-on.

| Store | Product page | Contents |
|---|---|---|
| [Superhive](superhive/) | https://superhivemarket.com/products/sculpt-paint-wheel | `description.html` (product description), `docs.html` (documentation tab, generated from `DOCS.md` by `build_docs.py`) |
| [Payhip](payhip/) | | `description.html` (product description; the user guide ships as a PDF with the product) |
| [media](media/) | | Shared by both: `images/` (page graphics), `gallery/` (16:9 gallery images), `videos/` (mp4 + animated webp) |

## Publishing

```
python store/tools/build_release.py --store
python store/superhive/build_docs.py
python store/tools/build_guide_pdf.py
python store/tools/package_stores.py
```

`build/store/upload/<store>/` (ignored by git) then holds everything for that store: the add-on zip and the PDF user guide (`product/`), the gallery images in upload order (`gallery/`, 01 is the cover), the videos, and the pages.

- **Superhive:** paste `description.html` into the description and `docs.html` into the documentation tab, as plain HTML. Upload the zip as the product file; the gallery images and videos go to the product gallery.
- **Payhip:** its description editor is a rich-text editor: open `description.html` in a browser, select all, copy, and paste into the editor (headings, lists and images come along). Upload the zip and the PDF guide as the product files, and the gallery images as product images.

The page images and animations load from `store/media/` on the repository's **`V2`** branch. Keep that branch until the pages are republished with `main` URLs (the branch is set in one place per page: the URLs in each `description.html` and `BRANCH` in `superhive/build_docs.py`).

Superhive's editors don't accept `<head>`, `<style>` or styled markup, so the pages are plain HTML fragments: headings, paragraphs, lists and images; the images carry the visual design. `docs.html` is generated: edit `DOCS.md`, then run `build_docs.py` (needs `pip install markdown`). It swaps the repository-oriented parts of `DOCS.md` for store ones: graphics, chapter banners, help through the store, no repository links, and no "Support Development" box (the store build doesn't have it).

## Version 2 graphics and videos

Everything is made from the real add-on running in Blender 5.3:

1. **Capture** with `store/tools/capture_v2.py`, once per part (`modes`, `centre`, `themes`, `double`, `prefs`, `themes_live`, `tints_live`). Use an isolated Blender profile (`BLENDER_USER_RESOURCES`) with the extension installed as `user_default/spwheel` and no saved preferences, so the defaults are captured:
   ```
   blender --factory-startup --enable-event-simulate --window-geometry 0 0 1920 1200 --python store/tools/capture_v2.py -- <captures dir> <part>
   ```
2. **Graphics**: `python store/tools/v2_graphics.py <captures dir> <output dir>` renders the page images `v2_01_hero.png` ... `v2_14_anatomy.png`, the chapter banners `v2_ch01.png` ... `v2_ch10.png` (1600 px wide, rounded transparent corners) and the gallery slides `g01_cover.png` ... `g08_yours.png` (1920x1080). Copy them to `media/images/` and `media/gallery/`.
3. **Videos**: `python store/tools/live_montage.py <captures dir>/themes_live <output dir> themes` and `... /tints_live <output dir> tints` (needs ffmpeg) edit the live recordings into `v2_themes` / `v2_tints`: an animated cursor working the real Preferences, the wheel updating beside it, captions and title cards. `.mp4` (1920x1080) for the galleries, animated `.webp` for the pages. Copy them to `media/videos/`.

## Builds

`python store/tools/build_release.py [--store]` builds the add-on zip with Blender's own extension builder, from the git-tracked files only, and validates it. `--store` is the copy sold in the stores (`build/store/superhive/`): the same add-on without the "Support Development" box in the preferences.

## Wording

- Store pages sell the add-on: what it does for the artist, what's new, and that purchases fund an independent developer. No "free" or repository messaging, and no links to GitHub: help and questions go through the store.
- No pricing talk in images, so they can be reused anywhere.
