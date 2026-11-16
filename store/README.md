# Store pages

Marketing material for the store listings of Sculpt-Paint Wheel. This folder isn't part of the add-on.

| Store | Product page | Contents |
|---|---|---|
| [Superhive](superhive/) | https://superhivemarket.com/products/sculpt-paint-wheel | `description.html` (product description), `docs.html` (documentation tab, generated from `DOCS.md` by `build_docs.py`) and `images/` for the gallery |
| [Payhip](payhip/) | https://payhip.com/b/zXfm2 | `README.md` (image order and text links) and `images/` |

The images are copies of `docs/images/promo/`. They're regenerated from real Blender 5.3 screenshots, so if the add-on's look changes, update `docs/images/promo/` first and copy the files here again.

## Superhive HTML

Superhive's description and documentation editors don't accept `<head>`, `<style>` or styled markup. `description.html` and `docs.html` are therefore plain HTML fragments: **paste each file as a whole**. They only use headings, paragraphs, lists, links and images; the images carry the visual design and load from this repository on GitHub.

`docs.html` is generated: edit `DOCS.md`, then run `python store/superhive/build_docs.py` (needs `pip install markdown`).

## Image tools

The graphics are rendered with Pillow from real Blender 5.3 screenshots:
- `tools/promo_images.py`: the shared promo images (`docs/images/promo/`).
- `tools/store_graphics.py`: extra store graphics (benefits, controls, wheel anatomy, modes reference, requirements, preferences, free & open) and the numbered chapter banners for `docs.html`.

Store copies get transparent rounded corners so they sit well on white store pages.

## Wording

All channels share the same wording rules:
- The add-on is **free and open source** on GitHub.
- Buying it in a store **funds development**, so everyone benefits, including people who can't afford it.
- No pricing talk in shared images. Store-specific calls to action stay in each store's own text.
