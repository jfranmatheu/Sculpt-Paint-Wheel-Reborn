"""Build store/superhive/docs.html (the Superhive "Documentation" tab) from DOCS.md.

Run from anywhere:  python store/superhive/build_docs.py
Requires:           pip install markdown

Superhive's editors don't accept <head>, <style> or styled markup, so the output is a plain HTML fragment,
ready to paste as a whole: headings, paragraphs, lists, links and images only.

What it does:
- Converts DOCS.md to HTML.
- Turns tables into lists (tables look broken without styles) and quotes into plain paragraphs.
- Store page: the V2 store graphics instead of the README images, a banner per chapter and a graphic or two per
  chapter; no links to the repository, the FAQ or the issue tracker (help goes through Superhive), and a sales
  "Supporting the project" section.
- Images and animations load from store/media/ in the repository's ``BRANCH``.
"""
import pathlib
import re

import markdown

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRANCH = "V2"
RAW = f"https://raw.githubusercontent.com/jfranmatheu/Sculpt-Paint-Wheel-Reborn/{BRANCH}/store/media"
MEDIA = ROOT / "store" / "media"

md = (ROOT / "DOCS.md").read_text(encoding="utf-8")

# ----- Store-only wording -------------------------------------------------------------------------------------------
md = re.sub(r" ?For quick answers, see the \[FAQ\]\(FAQ\.md\)\.", "", md)
md = re.sub(r"See the \[FAQ\]\(FAQ\.md\) or \[open an issue\]\([^)]*\) with",
            "Message the developer from this product page on Superhive with", md)
md = re.sub(r"\[([^\]]+)\]\((?:FAQ|README|DOCS)\.md[^)]*\)", r"\1", md)  # Any other link to the repository's files.
# The store build has no "Support Development" box in the preferences (STORE_PATCHES in build_release.py).
md = re.sub(r"### Support Development\r?\n\r?\n[^\n]*\r?\n\r?\n", "", md)
support_start = md.index("## Supporting the project")
md = md[:support_start] + """## Supporting the project

![Made by an independent developer](docs/images/promo/06_support_store.png)

Sculpt-Paint Wheel is made by one independent developer, and it has kept growing for about six years thanks to the artists who support it. Every new Blender version needs porting, testing and fixing.

Your purchase goes straight into that work: updates for new Blender releases, fixes driven by your feedback, and new features like everything in 2.0. **Thank you!** ♥
"""

# Images of the README / GitHub docs -> store graphics (None: left out of the store page).
STORE_IMAGES = {
    "01_hero.png": "v2_01_hero.png",
    "02_how_it_works.png": None,
    "03_modes.png": None,
    "04_customize.png": None,
    "06_support_github.png": "v2_13_support.png",
    "06_support_store.png": "v2_13_support.png",
}

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


def image(match):
    name = match.group(2)
    store = STORE_IMAGES.get(name, name)
    if store is None:
        return ""
    return f'<p><img alt="{match.group(1)}" src="{RAW}/images/{store}" width="100%" /></p>'


html = re.sub(r"<table>.*?</table>", table_to_list, html, flags=re.S)
html = re.sub(r"<blockquote>\s*(.*?)\s*</blockquote>", r"\1", html, flags=re.S)
html = re.sub(r'<p><img alt="([^"]*)" src="docs/images/promo/([^"]+)" ?/?></p>', image, html)

# Graphics: numbered chapter headings become banner images (anchors kept), plus graphics per chapter.
CHAPTER_GRAPHICS = {
    1: [("images/v2_12_install.png", "Requirements and install")],
    2: [("images/v2_14_anatomy.png", "The wheel at a glance")],
    3: [("images/v2_11_controls.png", "Controls"), ("images/v2_03_centre.png", "Smart centre: brush radius and strength")],
    4: [("images/v2_04_modes.png", "A wheel for every mode"), ("images/v2_05_color.png", "Color picker")],
    5: [("images/v2_07_double_ring.png", "Double ring")],
    6: [("images/v2_10_yours.png", "Make it yours")],
    7: [("images/v2_08_settings.png", "Settings"), ("images/v2_09_theme_tab.png", "Theme tab"),
        ("images/v2_06_themes.png", "Built-in themes"), ("videos/v2_tints.webp", "Button tints, changed live")],
}


def chapter_banner(match):
    anchor, num, title = match.group(1), int(match.group(2)), match.group(3)
    out = f'<h2 id="{anchor}"><img src="{RAW}/images/v2_ch{num:02d}.png" alt="{num}. {title}" width="100%"></h2>'
    for path, alt in CHAPTER_GRAPHICS.get(num, ()):
        out += f'\n<p><img src="{RAW}/{path}" alt="{alt}" width="100%"></p>'
    return out


html = re.sub(r'<h2 id="([^"]+)">(\d+)\. ([^<]+)</h2>', chapter_banner, html)
html = re.sub(r"\n{3,}", "\n\n", html)

for forbidden in ("<table", "<style", "<!--", "<head", "<div", "style=", "github.com/", "FAQ.md", "free and open"):
    assert forbidden not in html, forbidden
for path in re.findall(rf'{re.escape(RAW)}/([^"]+)"', html):
    assert (MEDIA / path).exists(), f"missing {path}"

(HERE / "docs.html").write_text(html.strip() + "\n", encoding="utf-8")
print("wrote", HERE / "docs.html")


# ----- FAQ (the store's FAQ section: one question / answer pair per entry) --------------------------------------------
# From FAQ.md, without the repository-oriented questions; store answers where FAQ.md points to the repository.
import json  # noqa: E402

FAQ_SKIP = {"Is it really free?", "If it's free, why is it for sale?", "Do buyers get a different version?",
            "Where can I buy it?", "Can I help without buying it?"}
FAQ_STORE_ANSWERS = {
    "Does it work with Blender 4.x?":
        "Not this version. It's built as a Blender 5.x extension and relies on the brush assets and Grease Pencil "
        "system that Blender 5 uses.",
    "How do I install it?":
        "1. Download the add-on zip from your Superhive library. Don't unzip it.\n"  # (No <...>: Superhive strips it.)
        "2. In Blender, go to **Edit › Preferences › Get Extensions**, open the **v** menu at the top right and choose "
        "**Install from Disk...**. You can also drag and drop the zip into Blender.\n"
        "3. Make sure **Sculpt-Paint Wheel** is enabled under **Edit › Preferences › Add-ons**.",
    "Does it work on Windows, macOS and Linux?":
        "It's built only on Blender's own Python and drawing APIs, with no platform-specific code, so it's available "
        "on every platform Blender supports. If something looks wrong on your system, message me here on Superhive.",
    "I found a bug.":
        "Message me here on Superhive. Include your Blender version, the mode you were in, the steps to reproduce it, "
        "and any error from **Window › Toggle System Console** (Windows) or the terminal (macOS/Linux).",
}

faq_md = (ROOT / "FAQ.md").read_text(encoding="utf-8").replace("\r\n", "\n")
faq = []
for block in re.split(r"\n### ", faq_md)[1:]:
    question, _, answer = block.partition("\n")
    question = question.strip()
    if question in FAQ_SKIP:
        continue
    answer = FAQ_STORE_ANSWERS.get(question, answer.split("\n---")[0].split("\n## ")[0].strip())
    answer = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", answer)  # Links: their text only.
    answer = re.sub(r"\s*See Supported modes for what's on each one\.", "", answer)
    answer_html = markdown.markdown(answer, extensions=["sane_lists"]).replace("\n", "")
    for forbidden in ("github", "free", "open source", "README", "DOCS.md", "FAQ.md"):
        assert forbidden.lower() not in (question + answer_html).lower(), (question, forbidden)
    faq.append({"question": question, "answer": answer_html})

(HERE / "faq.json").write_text(json.dumps(faq, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote", HERE / "faq.json", f"({len(faq)} questions)")
