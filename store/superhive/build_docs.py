"""Build store/superhive/docs.html from DOCS.md.

Run from anywhere:  python store/superhive/build_docs.py
Requires:           pip install markdown

Superhive's editors don't accept <head>, <style> or styled markup, so the output is a plain HTML fragment,
ready to paste as a whole: headings, paragraphs, lists, links and images only.

What it does:
- Converts DOCS.md to HTML.
- Turns tables into lists (tables look broken without styles) and quotes into plain paragraphs.
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


def table_to_list(match):
    """<table> -> <ul>: each row becomes '<strong>first cell</strong>: other cells'."""
    headers = [h.strip().lower() for h in re.findall(r"<th[^>]*>(.*?)</th>", match.group(0), re.S)]
    items = []
    for row in re.findall(r"<tr>(.*?)</tr>", match.group(0), re.S):
        cells = [c.strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if not cells:
            continue  # header row
        first = cells[0] if cells[0].startswith(("<strong>", "<code>")) else f"<strong>{cells[0]}</strong>"
        rest = cells[1:]
        if len(headers) == 3 and headers[1] == "default":  # Setting | Default | Description
            text = f"{rest[1]} (default: {rest[0]})"
        else:
            text = " — ".join(rest)
        items.append(f"<li>{first}: {text}</li>")
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def image_url(match):
    name = match.group(1)
    path = f"store/superhive/images/{name}" if (HERE / "images" / name).exists() else f"docs/images/promo/{name}"
    return f'src="{RAW}/{path}" width="100%"'


html = re.sub(r"<table>.*?</table>", table_to_list, html, flags=re.S)
html = re.sub(r"<blockquote>\s*(.*?)\s*</blockquote>", r"\1", html, flags=re.S)
html = re.sub(r'src="docs/images/promo/([^"]+)"', image_url, html)
html = re.sub(r'href="(FAQ\.md|README\.md|DOCS\.md)(#[^"]*)?"',
              lambda m: f'href="{REPO}/blob/main/{m.group(1)}{m.group(2) or ""}"', html)

# Graphics: numbered chapter headings become banner images (anchors kept), plus a graphic per chapter.
CHAPTER_GRAPHICS = {
    1: ("14_requirements.png", "Requirements and install"),
    2: ("12_anatomy.png", "The wheel at a glance"),
    3: ("11_controls.png", "Controls"),
    4: ("13_modes_reference.png", "A wheel for every mode"),
    7: ("15_preferences.png", "Preferences"),
}


def chapter_banner(match):
    anchor, num, title = match.group(1), int(match.group(2)), match.group(3)
    out = f'<h2 id="{anchor}"><img src="{RAW}/store/superhive/images/ch{num:02d}.png" alt="{num}. {title}" width="100%"></h2>'
    if num in CHAPTER_GRAPHICS:
        name, alt = CHAPTER_GRAPHICS[num]
        out += f'\n<p><img src="{RAW}/store/superhive/images/{name}" alt="{alt}" width="100%"></p>'
    return out


html = re.sub(r'<h2 id="([^"]+)">(\d+)\. ([^<]+)</h2>', chapter_banner, html)

for forbidden in ("<table", "<style", "<!--", "<head", "<div", "style="):
    assert forbidden not in html, forbidden

(HERE / "docs.html").write_text(html.strip() + "\n", encoding="utf-8")
print("wrote", HERE / "docs.html")
