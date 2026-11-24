"""Print the store user guide (store/superhive/docs.html) as an illustrated PDF, for stores without a documentation
tab (Payhip) and as a download next to the add-on.

Usage:
    python store/superhive/build_docs.py         (first, so docs.html is current)
    python store/tools/build_guide_pdf.py

Output (ignored by git): build/store/Sculpt-Paint Wheel 2 - User Guide.pdf
Needs Playwright with Chromium (pip install playwright, then: python -m playwright install chromium).
Images are read from store/media/ on disk, so nothing has to be pushed first.
"""
import pathlib
import re
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
MEDIA = ROOT / "store" / "media"
OUT = ROOT / "build" / "store" / "Sculpt-Paint Wheel 2 - User Guide.pdf"

html = (ROOT / "store" / "superhive" / "docs.html").read_text(encoding="utf-8")
html = re.sub(r"https://raw\.githubusercontent\.com/[^\"]+?/store/media/", MEDIA.as_uri() + "/", html)
# Not tied to one store.
html = html.replace("Message the developer from this product page on Superhive with",
                    "Message the developer from the store where you bought it with")
html = html.replace(MEDIA.as_uri() + "/videos/v2_tints.webp", MEDIA.as_uri() + "/images/v2_09_theme_tab.png")  # (No animation in a PDF.)

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
body { font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; font-size: 10.5pt; line-height: 1.5; color: #23242b; }
h1 { font-size: 24pt; margin: 0 0 8pt; letter-spacing: -0.3pt; }
h2 { margin: 18pt 0 8pt; break-before: page; }
h2 img { border-radius: 10px; }
h3 { font-size: 13pt; margin: 16pt 0 4pt; color: #111; }
p img, h2 img { display: block; width: 100%; break-inside: avoid; margin: 6pt 0; }
code { font-family: 'Cascadia Code', Consolas, monospace; font-size: 9pt; background: #f1f1f4; padding: 1px 4px; border-radius: 4px; }
ul, ol { padding-left: 18pt; }
li { margin: 2pt 0; }
hr { display: none; }
a { color: #c25e08; text-decoration: none; }
"""

doc = f"<!doctype html><html><head><meta charset='utf-8'><title>Sculpt-Paint Wheel 2: User Guide</title><style>{CSS}</style></head><body>{html}</body></html>"
OUT.parent.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(doc)
    tmp = pathlib.Path(f.name)
try:
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:  # (Playwright's own build missing: use the newest Chromium already installed.)
            builds = sorted(pathlib.Path.home().glob("AppData/Local/ms-playwright/chromium-*/chrome-win*/chrome.exe"))
            if not builds:
                raise
            browser = p.chromium.launch(executable_path=str(builds[-1]))
        page = browser.new_page()
        page.goto(tmp.as_uri(), wait_until="networkidle")
        page.pdf(path=str(OUT), format="A4", print_background=True, display_header_footer=True,
                 header_template="<span></span>",
                 footer_template="<div style='font-size:8px;color:#888;width:100%;text-align:center'>"
                                 "Sculpt-Paint Wheel 2 · User Guide · <span class='pageNumber'></span></div>",
                 margin={"top": "16mm", "bottom": "18mm", "left": "15mm", "right": "15mm"})
        browser.close()
finally:
    tmp.unlink(missing_ok=True)
print("wrote", OUT, f"({OUT.stat().st_size / 1e6:.1f} MB)")
