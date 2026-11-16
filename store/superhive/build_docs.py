"""Build store/superhive/docs.html from DOCS.md.

Run from anywhere:  python store/superhive/build_docs.py
Requires:           pip install markdown

What it does:
- Converts DOCS.md to HTML (tables and heading anchors included).
- Points images at the rounded store images on GitHub (store/superhive/images/), falling back to docs/images/promo/.
- Makes relative links (FAQ.md, README.md, ...) absolute GitHub links.
- Rewrites the "Supporting the project" section for the Superhive page: buy it here, no link to other stores.
"""
import pathlib
import re

import markdown

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPO = "https://github.com/jfran3d/Sculpt-Paint-Wheel-Reborn"
RAW = "https://raw.githubusercontent.com/jfran3d/Sculpt-Paint-Wheel-Reborn/main"

md = (ROOT / "DOCS.md").read_text(encoding="utf-8")

# Superhive-specific support section.
support_start = md.index("## Supporting the project")
md = md[:support_start] + """## Supporting the project

![Your purchase supports the developer](docs/images/promo/06_support_store.png)

Sculpt-Paint Wheel is **free and open source**, just like Blender. It's maintained by one independent developer, and every new Blender version needs porting, testing and fixing.

By buying it here on Superhive, you fund that work, so the add-on keeps improving and stays available to everyone, including students and artists who can't afford to buy it. **Thank you!** ♥
"""

html = markdown.markdown(md, extensions=["tables", "toc", "sane_lists"])


def image_url(match):
    name = match.group(1)
    store_img = HERE / "images" / name
    path = f"store/superhive/images/{name}" if store_img.exists() else f"docs/images/promo/{name}"
    return f'src="{RAW}/{path}" width="100%"'


html = re.sub(r'src="docs/images/promo/([^"]+)"', image_url, html)
html = re.sub(r'href="(FAQ\.md|README\.md|DOCS\.md)(#[^"]*)?"', lambda m: f'href="{REPO}/blob/main/{m.group(1)}{m.group(2) or ""}"', html)

page = f"""<!--
  Superhive documentation for Sculpt-Paint Wheel. GENERATED from DOCS.md by build_docs.py; edit DOCS.md instead.

  Paste everything between "PASTE START" and "PASTE END" into the Superhive documentation editor (HTML / source mode).
  Open this file in a browser to preview it on a white page, like Superhive.
-->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sculpt-Paint Wheel – Superhive documentation preview</title>
<style>
  /* Preview only: approximates Superhive's white page. Superhive applies its own styles. */
  body {{ margin: 0; background: #fff; color: #333; font: 16px/1.6 "Segoe UI", system-ui, sans-serif; }}
  .preview {{ max-width: 900px; margin: 0 auto; padding: 32px 16px 64px; }}
  h1, h2, h3 {{ color: #111; line-height: 1.25; }}
  h2 {{ margin-top: 2.2em; }}
  a {{ color: #d9630a; }}
  img {{ max-width: 100%; height: auto; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e3e3e3; vertical-align: top; }}
  code {{ background: #f3f3f3; padding: 1px 5px; border-radius: 4px; }}
  blockquote {{ margin: 1.5em 0; padding: 0.6em 1.2em; border-left: 4px solid #ff8c28; background: #fff6ee; }}
  hr {{ border: 0; border-top: 1px solid #e3e3e3; margin: 2.5em 0; }}
</style>
</head>
<body>
<div class="preview">
<!-- ======================= PASTE START ======================= -->

{html}

<!-- ======================== PASTE END ======================== -->
</div>
</body>
</html>
"""
(HERE / "docs.html").write_text(page, encoding="utf-8")
print("wrote", HERE / "docs.html")
