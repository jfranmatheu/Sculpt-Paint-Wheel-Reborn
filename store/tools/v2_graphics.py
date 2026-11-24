"""Store graphics announcing Sculpt-Paint Wheel 2.0 (sales-focused: no "free" / GitHub messaging).

Usage:
    python store/tools/v2_graphics.py <captures dir> <output dir>

<captures dir> is the output of ``capture_v2.py`` (parts modes, centre, themes, double, prefs): screenshots of the
real wheel in Blender 5.3, each with a .json holding the wheel centre, radius and page pill. Wheels are cut out of
the viewport here and float on a near-black canvas with one warm accent. Text uses Segoe UI Variable (Windows 11).
Images are 1600 px wide with transparent rounded corners, so they sit well on white store pages.
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

CAP, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

W = 1200            # Layout width (px); everything is drawn at S x and saved at OUT_W.
S = 2
OUT_W = 1600
FONTS = "C:/Windows/Fonts/"
LANCZOS = Image.Resampling.LANCZOS

BG_TOP, BG_BOTTOM = (17, 18, 23), (10, 11, 14)
ACCENT = (255, 138, 36)
ACCENT_SOFT = (255, 178, 104)
TEXT = (244, 244, 247)
MUTED = (152, 155, 168)
FAINT = (102, 105, 118)
CARD = (255, 255, 255, 9)
EDGE = (255, 255, 255, 24)


# ----- Type -------------------------------------------------------------------------------------------------------

def vf(size, style="Regular"):
    f = ImageFont.truetype(FONTS + "SegUIVar.ttf", int(size * S))
    f.set_variation_by_name(style)
    return f


F_HERO = vf(74, "Bold Display")
F_H1 = vf(46, "Semibold Display")
F_SUB = vf(20, "Regular")
F_EYEBROW = vf(14, "Semibold Text")
F_TITLE = vf(20, "Semibold Text")
F_BODY = vf(16, "Regular")
F_LABEL = vf(17, "Semibold Text")
F_SMALL = vf(14, "Regular")
F_NUM = vf(13, "Bold Text")
F_STAT = vf(64, "Bold Display")
F_KEY = vf(16, "Semibold Text")
F_SYM = ImageFont.truetype(FONTS + "seguisym.ttf", 30 * S)


def P(v):
    return int(round(v * S))


def tracked(d, x, y, text, f, fill, tracking=0.16, anchor_center=False):
    """Text with letter spacing (``tracking`` x the font size); x, y in layout px (top left, or top centre)."""
    sp = f.size * tracking
    total = sum(d.textlength(c, font=f) for c in text) + sp * (len(text) - 1)
    cx = P(x) - (total / 2 if anchor_center else 0)
    for c in text:
        d.text((cx, P(y)), c, font=f, fill=fill)
        cx += d.textlength(c, font=f) + sp
    return total / S


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if d.textlength(test, font=f) <= P(max_w):
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def para(d, x, y, text, f=F_BODY, fill=MUTED, max_w=600, lh=1.5, center=False):
    for line in wrap(d, text, f, max_w):
        d.text((P(x), P(y)), line, font=f, fill=fill, anchor="ma" if center else "la")
        y += f.size / S * lh
    return y


# ----- Canvas -----------------------------------------------------------------------------------------------------

def canvas(h, spots=((600, 0, 520),)):
    """Near-black vertical gradient, soft accent light spots (x, y, radius) and a faint dot grid near them."""
    w, hh = P(W), P(h)
    img = Image.new("RGBA", (w, hh))
    d = ImageDraw.Draw(img)
    for y in range(hh):
        t = y / hh
        d.line([(0, y), (w, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(BG_TOP, BG_BOTTOM)) + (255,))
    small = (w // 8, hh // 8)
    glow = Image.new("L", small, 0)
    gd = ImageDraw.Draw(glow)
    for x, y, r in spots:
        gd.ellipse(((x - r) * S / 8, (y - r) * S / 8, (x + r) * S / 8, (y + r) * S / 8), fill=46)
    glow = glow.filter(ImageFilter.GaussianBlur(P(70) / 8)).resize((w, hh), LANCZOS)
    img.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (w, hh), ACCENT).split(), glow)))
    # Dot grid, faded out away from the light.
    dots = Image.new("L", (w, hh), 0)
    dd = ImageDraw.Draw(dots)
    step = P(26)
    for yy in range(step // 2, hh, step):
        for xx in range(step // 2, w, step):
            dd.ellipse((xx - S, yy - S, xx + S, yy + S), fill=255)
    fade = glow.point(lambda v: min(255, v * 4))
    dots = ImageChops.multiply(dots, fade).point(lambda v: v * 0.10)
    img.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (w, hh), (255, 255, 255)).split(), dots)))
    # A hairline highlight along the top edge.
    ImageDraw.Draw(img).line([(0, 0), (w, 0)], fill=(255, 255, 255, 30), width=S)
    return img


def overlay(img):
    """A transparent layer to draw translucent shapes on, and the function that merges it back."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer), lambda: img.alpha_composite(layer)


def shadow(img, mask, x, y, blur=26, dy=18, opacity=0.6):
    """Drop shadow of an alpha ``mask`` placed at (x, y) (device px)."""
    pad = P(blur) * 3
    m = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0)
    m.paste(mask, (pad, pad))
    m = m.filter(ImageFilter.GaussianBlur(P(blur))).point(lambda v: int(v * opacity))
    sh = Image.merge("RGBA", (*Image.new("RGB", m.size, (0, 0, 0)).split(), m))
    img.alpha_composite(sh, (x - pad, y - pad + P(dy)))


def eyebrow(d, x, y, text, center=False):
    return tracked(d, x, y, text, F_EYEBROW, ACCENT, 0.2, anchor_center=center)


def header(img, x, y, kicker, title, sub=None, center=False, max_w=760):
    d = ImageDraw.Draw(img)
    eyebrow(d, x, y, kicker, center)
    d.text((P(x), P(y + 26)), title, font=F_H1, fill=TEXT, anchor="ma" if center else "la")
    y += 26 + F_H1.size / S + 14
    if sub:
        y = para(d, x, y, sub, F_SUB, MUTED, max_w, 1.45, center) + 6
    return y + 22


# ----- Wheels -----------------------------------------------------------------------------------------------------

def wheel_cut(part, name, with_pill=True):
    """The wheel of a capture cut out of the viewport: (RGBA image, wheel radius in its pixels).
    The image is a square centred on the wheel; with ``with_pill`` the page pill is kept below it."""
    info = json.load(open(os.path.join(CAP, part, f"{name}.json")))
    shot = Image.open(os.path.join(CAP, part, f"{name}.png")).convert("RGB")
    r = info["radius"]
    half = int(r + 60)
    cx, cy = info["cx"], info["cy"]
    crop = shot.crop((cx - half, cy - half, cx + half, cy + half))
    k = 4  # Supersampled mask for smooth edges.
    m = Image.new("L", (crop.width * k, crop.height * k), 0)
    md = ImageDraw.Draw(m)
    c = half * k
    rr = (r + 0.6) * k
    md.ellipse((c - rr, c - rr, c + rr, c + rr), fill=255)
    if with_pill and info.get("pill"):
        px, py, pw, ph = (v * k for v in info["pill"])
        md.rounded_rectangle((c + px, c + py, c + px + pw, c + py + ph), radius=ph / 2, fill=255)
    m = m.resize(crop.size, LANCZOS)
    out = crop.convert("RGBA")
    out.putalpha(m)
    return out, r


def place_wheel(img, part, name, cx, cy, diameter, with_pill=True, glow=False, opacity=1.0):
    """Put a cut-out wheel with its circle ``diameter`` px wide, centred at (cx, cy) layout px."""
    cut, r = wheel_cut(part, name, with_pill)
    scale = P(diameter) / (2 * r)
    size = int(cut.width * scale)
    cut = cut.resize((size, size), LANCZOS)
    if opacity < 1:
        cut.putalpha(cut.getchannel("A").point(lambda v: int(v * opacity)))
    x, y = P(cx) - size // 2, P(cy) - size // 2
    if glow:  # A soft accent light behind the wheel (on a canvas-wide layer: no clipped edges).
        q = 8
        g = Image.new("L", (img.width // q, img.height // q), 0)
        gr = P(diameter) * 0.62 / q
        ImageDraw.Draw(g).ellipse((P(cx) / q - gr, P(cy) / q - gr, P(cx) / q + gr, P(cy) / q + gr), fill=80)
        g = g.filter(ImageFilter.GaussianBlur(P(46) / q)).resize(img.size, LANCZOS)
        img.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", img.size, ACCENT).split(), g)))
    shadow(img, cut.getchannel("A"), x, y, blur=max(10, diameter * 0.05), dy=diameter * 0.035, opacity=0.75)
    img.alpha_composite(cut, (x, y))
    return P(cy) // S + diameter // 2  # bottom of the circle (layout px)


def zoom_circle(img, part, name, cx, cy, diameter, radius_px):
    """A round close-up of the wheel centre: ``radius_px`` capture pixels around it, shown ``diameter`` wide."""
    info = json.load(open(os.path.join(CAP, part, f"{name}.json")))
    shot = Image.open(os.path.join(CAP, part, f"{name}.png")).convert("RGB")
    x0, y0 = info["cx"] - radius_px, info["cy"] - radius_px
    crop = shot.crop((x0, y0, x0 + 2 * radius_px, y0 + 2 * radius_px)).resize((P(diameter), P(diameter)), LANCZOS)
    k = 4
    m = Image.new("L", (crop.width * k, crop.height * k), 0)
    ImageDraw.Draw(m).ellipse((0, 0, crop.width * k - 1, crop.height * k - 1), fill=255)
    m = m.resize(crop.size, LANCZOS)
    out = crop.convert("RGBA")
    out.putalpha(m)
    x, y = P(cx - diameter / 2), P(cy - diameter / 2)
    shadow(img, m, x, y, blur=18, dy=12, opacity=0.7)
    img.alpha_composite(out, (x, y))
    ImageDraw.Draw(img).ellipse((x, y, x + crop.width, y + crop.height), outline=(255, 255, 255, 40), width=S)


def framed(img, path, box, x, y, w, radius=14):
    """A screenshot crop in a thin rounded frame with a soft shadow; returns its bottom (layout px)."""
    shot = Image.open(path).convert("RGB").crop(box)
    h = int(shot.height * w / shot.width)
    shot = shot.resize((P(w), P(h)), LANCZOS).convert("RGBA")
    m = Image.new("L", shot.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, shot.width - 1, shot.height - 1), radius=P(radius), fill=255)
    shot.putalpha(m)
    shadow(img, m, P(x), P(y), blur=30, dy=20, opacity=0.7)
    img.alpha_composite(shot, (P(x), P(y)))
    layer, ld, merge = overlay(img)
    ld.rounded_rectangle((P(x), P(y), P(x + w), P(y + h)), radius=P(radius), outline=EDGE, width=S)
    merge()
    return y + h


# ----- Blocks -----------------------------------------------------------------------------------------------------

def card(img, x, y, w, h, num, title, body):
    layer, ld, merge = overlay(img)
    ld.rounded_rectangle((P(x), P(y), P(x + w), P(y + h)), radius=P(16), fill=CARD, outline=EDGE, width=S)
    ld.line([(P(x + 24), P(y)), (P(x + 64), P(y))], fill=ACCENT + (255,), width=P(2))  # accent tick on the top edge
    merge()
    d = ImageDraw.Draw(img)
    tracked(d, x + 24, y + 22, num, F_NUM, ACCENT, 0.12)
    d.text((P(x + 24), P(y + 46)), title, font=F_TITLE, fill=TEXT)
    para(d, x + 24, y + 80, body, F_BODY, MUTED, w - 48, 1.5)


def cards(img, y, items, cols, h, x0=72, gap=20):
    cw = (W - 2 * x0 - gap * (cols - 1)) / cols
    for i, (title, body) in enumerate(items):
        card(img, x0 + (i % cols) * (cw + gap), y + (i // cols) * (h + gap), cw, h, f"{i + 1:02d}", title, body)
    return y + ((len(items) + cols - 1) // cols) * (h + gap) - gap


def chip(img, x, y, text, accent=False, f=F_SMALL, h=32):
    d = ImageDraw.Draw(img)
    w = d.textlength(text, font=f) / S + 28
    layer, ld, merge = overlay(img)
    ld.rounded_rectangle((P(x), P(y), P(x + w), P(y + h)), radius=P(h / 2),
                         fill=(ACCENT + (40,)) if accent else (255, 255, 255, 12),
                         outline=(ACCENT + (150,)) if accent else EDGE, width=S)
    merge()
    ImageDraw.Draw(img).text((P(x + w / 2), P(y + h / 2)), text, font=f, fill=ACCENT_SOFT if accent else TEXT, anchor="mm")
    return x + w


def keycap(img, x, y, text, h=40):
    d = ImageDraw.Draw(img)
    w = d.textlength(text, font=F_KEY) / S + 30
    layer, ld, merge = overlay(img)
    ld.rounded_rectangle((P(x), P(y + 3), P(x + w), P(y + h + 3)), radius=P(9), fill=(0, 0, 0, 120))
    ld.rounded_rectangle((P(x), P(y), P(x + w), P(y + h)), radius=P(9), fill=(255, 255, 255, 16), outline=(255, 255, 255, 40), width=S)
    merge()
    ImageDraw.Draw(img).text((P(x + w / 2), P(y + h / 2)), text, font=F_KEY, fill=TEXT, anchor="mm")
    return x + w


def label(d, cx, y, title, sub=None):
    d.text((P(cx), P(y)), title, font=F_LABEL, fill=TEXT, anchor="ma")
    if sub:
        d.text((P(cx), P(y + 26)), sub, font=F_SMALL, fill=MUTED, anchor="ma")


def save(img, name):
    h = int(img.height * OUT_W / img.width)
    out = img.resize((OUT_W, h), LANCZOS)
    k = 3
    m = Image.new("L", (OUT_W * k, h * k), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, OUT_W * k - 1, h * k - 1), radius=30 * k, fill=255)
    out.putalpha(ImageChops.multiply(out.getchannel("A"), m.resize((OUT_W, h), LANCZOS)))
    out.save(os.path.join(OUT, name), optimize=True)
    print("saved", name, out.size)


# ===== 1. Hero =====================================================================================================
H = 760
img = canvas(H, spots=((840, 420, 430), (80, 0, 260)))
d = ImageDraw.Draw(img)
chip(img, 72, 150, "NEW  \u00b7  VERSION 2.0", accent=True, f=F_NUM)
d.text((P(72), P(198)), "Sculpt-Paint", font=F_HERO, fill=TEXT)
d.text((P(72), P(280)), "Wheel 2", font=F_HERO, fill=ACCENT)
y = para(d, 72, 392, "Your brushes, one keypress away. Hold Space, flick, keep working: now faster, smarter and fully yours.",
         F_SUB, MUTED, 430, 1.5)
for t in ("Every sculpt and paint mode", "10 themes, or make your own", "Up to 34 brushes on one page"):
    y += 14
    d.ellipse((P(74), P(y + 9), P(82), P(y + 17)), fill=ACCENT)
    d.text((P(96), P(y)), t, font=F_LABEL, fill=TEXT)
    y += 24
# Three wheels: Texture Paint and Weight Paint behind, Sculpt in front.
place_wheel(img, "modes", "texture", 1012, 228, 300)
place_wheel(img, "modes", "weight", 1030, 588, 252, with_pill=False)
place_wheel(img, "modes", "sculpt", 738, 432, 420, glow=True)
save(img, "v2_01_hero.png")

# ===== 2. What's new ===============================================================================================
H = 650
img = canvas(H, spots=((1100, 0, 360),))
y = header(img, 72, 68, "WHAT'S NEW IN 2.0", "A wheel reborn", "Rebuilt from the ground up, around how you actually work.")
cards(img, y, [
    ("New ring menu", "Up to 10 custom buttons, one clean segment each. No empty slots."),
    ("Smart centre", "Drag it up / down for radius, left / right for strength. In every wheel."),
    ("Toggles & scripts", "Buttons that show their on / off state, and buttons that run your own Python."),
    ("10 themes", "Dark, Light and eight more. Edit any color live and save your own."),
    ("Double ring", "Big brush sets get a second ring: up to 34 brushes on one page."),
    ("Crisp new icons", "A new super-sampled icon set, sharp at any size. Or use your own images."),
], cols=3, h=170)
d = ImageDraw.Draw(img)
para(d, 72, H - 64, "Plus a page pill under the ring, a Masking set for Sculpt, fuller default sets, a color picker in "
     "Grease Pencil vertex paint, and 40+ fixes.", F_SMALL, FAINT, 1056)
save(img, "v2_02_whats_new.png")

# ===== 3. Smart centre =============================================================================================
H = 640
img = canvas(H, spots=((600, 380, 420),))
y = header(img, 600, 64, "NEW  \u00b7  SMART CENTRE", "Tune your brush without leaving the wheel", center=True)
d = ImageDraw.Draw(img)
for i, (name, title, sub) in enumerate([
    ("sculpt_hover", "Hover", "The centre names the button under the cursor"),
    ("sculpt_drag_radius", "Drag up / down", "Brush radius"),
    ("sculpt_drag_strength", "Drag left / right", "Brush strength"),
]):
    cx = 240 + i * 360
    zoom_circle(img, "centre", name, cx, y + 140, 270, 118)
    label(d, cx, y + 300, title, sub)
d.text((P(600), P(H - 46)), "Shift for finer steps  \u00b7  Ctrl for faster  \u00b7  Esc or right click to cancel",
       font=F_SMALL, fill=FAINT, anchor="ma")
save(img, "v2_03_centre.png")

# ===== 4. Every mode ===============================================================================================
MODES = [("sculpt", "Sculpt"), ("texture", "Texture Paint"), ("vertex", "Vertex Paint"),
         ("weight", "Weight Paint"), ("curves", "Sculpt Curves"), ("gp-draw", "Grease Pencil Draw"),
         ("gp-sculpt", "Grease Pencil Sculpt"), ("gp-weight", "Grease Pencil Weight"), ("gp-vertex", "Grease Pencil Vertex")]
H = 1240
img = canvas(H, spots=((600, 160, 460), (600, 1000, 380)))
y = header(img, 600, 64, "EVERY PAINT MODE", "Nine wheels, ready out of the box",
           "Each mode gets its own brushes, buttons and sets, created the first time you use it.", center=True, max_w=900)
d = ImageDraw.Draw(img)
for i, (mid, name) in enumerate(MODES):
    cx = 220 + (i % 3) * 380
    cy = y + 150 + (i // 3) * 330
    info = json.load(open(os.path.join(CAP, "modes", f"{mid}.json")))
    place_wheel(img, "modes", mid, cx, cy, 260 * info["radius"] / 210, with_pill=False)
    label(d, cx, cy + 150, name)
save(img, "v2_04_modes.png")

# ===== 5. Color ====================================================================================================
H = 720
img = canvas(H, spots=((330, 420, 300), (870, 420, 300)))
y = header(img, 600, 64, "COLOR, BUILT IN", "Pick colors without leaving the wheel", center=True)
d = ImageDraw.Draw(img)
for i, (mid, name) in enumerate([("vertex", "Vertex Paint"), ("gp-draw", "Grease Pencil Draw")]):
    cx = 330 + i * 540
    bottom = place_wheel(img, "modes", mid, cx, y + 210, 400, with_pill=False)
    label(d, cx, y + 432, name)
d.text((P(600), P(H - 46)), "Hue ring, saturation and value arcs, primary / secondary swap. Colors match your brush exactly.",
       font=F_SMALL, fill=FAINT, anchor="ma")
save(img, "v2_05_color.png")

# ===== 6. Themes ===================================================================================================
THEMES = ["Dark", "Light", "Midnight", "Ember", "Forest", "Rose", "Graphite", "High Contrast", "Paper", "Frost"]
H = 780
img = canvas(H, spots=((600, 380, 520),))
y = header(img, 600, 64, "NEW  \u00b7  THEMES", "Ten looks built in. Or make your own.",
           "Pick a theme in one click, edit any color live, save your own and reset anytime.", center=True, max_w=720)
d = ImageDraw.Draw(img)
for i, n in enumerate(THEMES):
    cx = 156 + (i % 5) * 222
    cy = y + 110 + (i // 5) * 262
    place_wheel(img, "themes", "sculpt_" + n.lower().replace(" ", "_"), cx, cy, 190, with_pill=False)
    d.text((P(cx), P(cy + 108)), n, font=F_LABEL, fill=TEXT, anchor="ma")
save(img, "v2_06_themes.png")

# ===== 7. Double ring ==============================================================================================
H = 860
img = canvas(H, spots=((820, 480, 420),))
y = header(img, 600, 64, "NEW  \u00b7  DOUBLE RING", "Big brush sets, one glance",
           "Turn on Allow Double Ring: a set that doesn't fit on one ring gets a second, staggered ring.", center=True, max_w=980)
d = ImageDraw.Draw(img)
one = json.load(open(os.path.join(CAP, "double", "big_one_ring.json")))
two = json.load(open(os.path.join(CAP, "double", "big_two_rings.json")))
k = 470 / (2 * two["radius"])  # Same scale for both wheels.
cy = y + 260
place_wheel(img, "double", "big_one_ring", 300, cy, 2 * one["radius"] * k)
place_wheel(img, "double", "big_two_rings", 820, cy, 470, glow=True)
sy = cy + 262
d.text((P(300), P(sy)), "14", font=F_STAT, fill=TEXT, anchor="ma")
d.text((P(300), P(sy + 80)), "brushes per page, one ring", font=F_SMALL, fill=MUTED, anchor="ma")
d.text((P(820), P(sy)), "34", font=F_STAT, fill=ACCENT, anchor="ma")
d.text((P(820), P(sy + 80)), "brushes per page, two rings", font=F_SMALL, fill=MUTED, anchor="ma")
save(img, "v2_07_double_ring.png")

# ===== 8. Settings =================================================================================================
H = 680
img = canvas(H, spots=((600, 0, 420),))
y = header(img, 72, 64, "SETTINGS", "Size, behavior and the brush ring", "Every option at hand, in plain words.")
bottom = framed(img, os.path.join(CAP, "prefs", "prefs_settings.png"), (236, 640, 1574, 1047), 72, y, 1056)
save(img, "v2_08_settings.png")

# ===== 9. Theme tab ================================================================================================
H = 720
img = canvas(H, spots=((980, 500, 360),))
y = header(img, 72, 64, "THEME TAB", "Every color, edited live",
           "Pick a theme, tweak it while the wheel updates, then save it as your own.", max_w=900)
framed(img, os.path.join(CAP, "prefs", "prefs_theme_modified.png"), (236, 330, 1574, 1000), 72, y, 760)
place_wheel(img, "themes", "sculpt_midnight", 960, y + 250, 390, with_pill=False, glow=True)
save(img, "v2_09_theme_tab.png")

# ===== 10. Make it yours ============================================================================================
H = 640
img = canvas(H, spots=((100, 600, 380),))
y = header(img, 72, 64, "MAKE IT YOURS", "Your brushes, your buttons, your look")
cards(img, y, [
    ("Brush sets", "Any brush asset, your own included. Switch sets right from the wheel."),
    ("Custom buttons", "Panels, menus, operators, toggles or your own Python scripts."),
    ("Your icons", "Pick from the bundled icon set or load any image."),
    ("Tints", "Color buttons by type or one by one: fill, outline, icon or a strip."),
    ("Themes", "Ten built in, plus every theme you save."),
    ("Per mode", "Every mode keeps its own sets, ready when you switch."),
], cols=3, h=150)
save(img, "v2_10_yours.png")

# ===== 11. Controls ================================================================================================
ROWS = [(["Hold Space"], "Open the wheel under the cursor", False),
        (["Left Click"], "Pick a brush or run a button", False),
        (["Drag the centre"], "Brush radius and strength", True),
        (["Mouse Wheel", "Page pill"], "Switch brush pages", True),
        (["Shift", "Mouse Wheel"], "Switch brush sets", True),
        (["Release Space"], "Close the wheel", False),
        (["Esc", "Right Click"], "Cancel", False)]
H = 230 + len(ROWS) * 64 + 20
img = canvas(H, spots=((1100, 0, 360),))
y = header(img, 72, 64, "CONTROLS", "Everything at your fingertips")
d = ImageDraw.Draw(img)
for keys, text, new in ROWS:
    layer, ld, merge = overlay(img)
    ld.line([(P(72), P(y + 56)), (P(W - 72), P(y + 56))], fill=(255, 255, 255, 18), width=S)
    merge()
    x = 72
    for i, k_ in enumerate(keys):
        if i:
            sep = "+" if keys[0] == "Shift" else "or"
            d.text((P(x + 12), P(y + 20)), sep, font=F_SMALL, fill=FAINT, anchor="lm")
            x += 24 + d.textlength(sep, font=F_SMALL) / S
        x = keycap(img, x, y, k_)
    d.text((P(500), P(y + 20)), text, font=F_SUB, fill=TEXT, anchor="lm")
    if new:
        chip(img, 500 + d.textlength(text, font=F_SUB) / S + 16, y + 6, "NEW", accent=True, f=F_NUM, h=28)
    y += 64
save(img, "v2_11_controls.png")

# ===== 12. Install =================================================================================================
H = 460
img = canvas(H, spots=((600, 460, 420),))
y = header(img, 72, 64, "REQUIREMENTS", "Up and running in a minute")
x = 72
for t in ("Blender 5.1+", "Tested on 5.3", "Windows \u00b7 macOS \u00b7 Linux", "No internet needed"):
    x = chip(img, x, y - 8, t) + 10
y += 70
d = ImageDraw.Draw(img)
steps = [("Download", "Get spwheel-2.0.0.zip from your Superhive library."),
         ("Install", "Preferences \u203a Get Extensions \u203a Install from Disk, or drag and drop the zip."),
         ("Hold Space", "In any sculpt or paint mode. That's it.")]
sw = (W - 144) / 3
layer, ld, merge = overlay(img)
ld.line([(P(72 + 22), P(y + 22)), (P(72 + 2 * sw + 22), P(y + 22))], fill=(255, 255, 255, 40), width=S)
merge()
for i, (t, b) in enumerate(steps):
    x = 72 + i * sw
    d.ellipse((P(x), P(y), P(x + 44), P(y + 44)), fill=ACCENT)
    d.text((P(x + 22), P(y + 22)), str(i + 1), font=F_TITLE, fill=(20, 12, 4), anchor="mm")
    d.text((P(x), P(y + 64)), t, font=F_TITLE, fill=TEXT)
    para(d, x, y + 98, b, F_BODY, MUTED, sw - 40)
save(img, "v2_12_install.png")

# ===== 13. Support =================================================================================================
H = 590
img = canvas(H, spots=((600, 40, 360),))
d = ImageDraw.Draw(img)
d.text((P(600), P(78)), "\u2665", font=F_SYM, fill=ACCENT, anchor="mm")
eyebrow(d, 600, 118, "6 YEARS AND COUNTING", center=True)
d.text((P(600), P(146)), "Made by an independent developer", font=F_H1, fill=TEXT, anchor="ma")
y = para(d, 600, 222, "Sculpt-Paint Wheel has kept growing for about six years thanks to the artists who support it. "
         "Your purchase goes straight into the next version.", F_SUB, MUTED, 760, 1.5, center=True) + 26
cards(img, y, [("Blender updates", "Ported and tested for every new Blender release."),
               ("Fixes & polish", "Driven by real artists' feedback."),
               ("New features", "Like everything new in 2.0, and what comes next.")], cols=3, h=130)
t = "Thank you for your support  \u2665"
w = d.textlength(t, font=F_LABEL) / S + 56
layer, ld, merge = overlay(img)
ld.rounded_rectangle((P(600 - w / 2), P(H - 96), P(600 + w / 2), P(H - 44)), radius=P(26), fill=ACCENT + (255,))
merge()
ImageDraw.Draw(img).text((P(600), P(H - 70)), t, font=F_LABEL, fill=(24, 14, 4), anchor="mm")
save(img, "v2_13_support.png")

# ===== 14. The wheel at a glance (docs) ============================================================================
H = 760
img = canvas(H, spots=((400, 420, 420),))
y = header(img, 72, 64, "THE WHEEL AT A GLANCE", "Know your wheel")
info = json.load(open(os.path.join(CAP, "modes", "sculpt.json")))
D, CX, CY = 450, 390, y + 280
k = D / (2 * info["radius"])  # capture px -> layout px
place_wheel(img, "modes", "sculpt", CX, CY, D, glow=False)
d = ImageDraw.Draw(img)
d.text((P(CX), P(CY - D / 2 - 34)), "Default Set", font=F_LABEL, fill=TEXT, anchor="ma")
import math  # noqa: E402


def at(radius_px, deg):
    a = math.radians(deg)
    return CX + radius_px * k * math.cos(a), CY - radius_px * k * math.sin(a)


pill = info["pill"]
title_w = d.textlength("Default Set", font=F_LABEL) / S
CALLOUTS = [  # (point beside a part of the wheel, label, description), top to bottom so lines don't cross
    ((CX + title_w / 2 + 12, CY - D / 2 - 22), "Set name", "Drag it, or Shift + mouse wheel, to switch brush sets"),
    (at(153, 38), "Brush ring", "Your brushes, with Blender's previews. Click to pick"),
    (at(48, 12), "Smart centre", "Names what you hover. Drag it for radius and strength"),
    (at(88, -22), "Custom buttons", "Panels, menus, operators, toggles and scripts"),
    ((CX + (pill[0] + pill[2]) * k + 12, CY + (pill[1] + pill[3] / 2) * k), "Page pill",
     "Shown when a set has more brushes than fit"),
]
LX = 760
layer, ld, merge = overlay(img)
for i, ((px, py), title, body) in enumerate(CALLOUTS):
    ly = y + 30 + i * 102
    ld.line([(P(px), P(py)), (P(LX - 70), P(ly + 12)), (P(LX - 16), P(ly + 12))], fill=ACCENT + (200,), width=S, joint="curve")
merge()
for i, ((px, py), title, body) in enumerate(CALLOUTS):
    ly = y + 30 + i * 102
    d.ellipse((P(px - 5), P(py - 5), P(px + 5), P(py + 5)), fill=ACCENT, outline=(255, 255, 255), width=S)
    d.text((P(LX), P(ly)), title, font=F_TITLE, fill=TEXT)
    para(d, LX, ly + 32, body, F_BODY, MUTED, 360)
save(img, "v2_14_anatomy.png")

# ===== Chapter banners for the documentation tab ==================================================================
CHAPTERS = ["Getting started", "The wheel at a glance", "Controls", "Modes reference", "Brush sets", "Custom buttons",
            "Preferences", "Your data and backups", "Hotkeys and keymap", "Troubleshooting"]
for n, title in enumerate(CHAPTERS, 1):
    H = 150
    img = canvas(H, spots=((1100, 75, 260),))
    d = ImageDraw.Draw(img)
    d.text((P(72), P(75)), f"{n:02d}", font=F_STAT, fill=ACCENT, anchor="lm")
    layer, ld, merge = overlay(img)
    ld.line([(P(196), P(48)), (P(196), P(102))], fill=(255, 255, 255, 40), width=S)
    merge()
    tracked(d, 224, 44, f"CHAPTER {n}", F_EYEBROW, FAINT, 0.2)
    d.text((P(224), P(66)), title, font=F_H1, fill=TEXT)
    save(img, f"v2_ch{n:02d}.png")

# ===== Gallery: 16:9 slides (1920x1080, square corners) for the stores' image galleries ============================
GH = 675  # 1200 x 675 layout = 16:9
GALLERY_W = 1920


def save_slide(img, name):
    img.convert("RGB").resize((GALLERY_W, GALLERY_W * 9 // 16), LANCZOS).save(os.path.join(OUT, name), optimize=True)
    print("saved", name)


# 1. Cover
img = canvas(GH, spots=((850, 360, 420), (80, 0, 240)))
d = ImageDraw.Draw(img)
chip(img, 72, 150, "NEW  \u00b7  VERSION 2.0", accent=True, f=F_NUM)
d.text((P(72), P(196)), "Sculpt-Paint", font=F_HERO, fill=TEXT)
d.text((P(72), P(278)), "Wheel 2", font=F_HERO, fill=ACCENT)
para(d, 72, 388, "Your brushes, one keypress away. Hold Space, flick, keep working.", F_SUB, MUTED, 430, 1.5)
y = 470
for t_ in ("Every sculpt and paint mode", "10 themes, or make your own", "Up to 34 brushes on one page"):
    d.ellipse((P(74), P(y + 9), P(82), P(y + 17)), fill=ACCENT)
    d.text((P(96), P(y)), t_, font=F_LABEL, fill=TEXT)
    y += 36
place_wheel(img, "modes", "texture", 1022, 178, 276)
place_wheel(img, "modes", "weight", 1040, 506, 228, with_pill=False)
place_wheel(img, "modes", "sculpt", 752, 368, 388, glow=True)
save_slide(img, "g01_cover.png")

# 2. Modes
img = canvas(GH, spots=((600, 380, 480),))
y = header(img, 600, 44, "EVERY PAINT MODE", "Nine wheels, ready out of the box", center=True)
d = ImageDraw.Draw(img)
for i, (mid, name) in enumerate(MODES):
    row, col = divmod(i, 5)
    n_in_row = 5 if row == 0 else 4
    cx = 600 + (col - (n_in_row - 1) / 2) * 214
    cy = y + 92 + row * 238
    info = json.load(open(os.path.join(CAP, "modes", f"{mid}.json")))
    place_wheel(img, "modes", mid, cx, cy, 170 * info["radius"] / 210, with_pill=False)
    d.text((P(cx), P(cy + 98)), name, font=F_SMALL, fill=TEXT, anchor="ma")
save_slide(img, "g02_modes.png")

# 3. Smart centre
img = canvas(GH, spots=((600, 380, 420),))
y = header(img, 600, 56, "NEW  \u00b7  SMART CENTRE", "Tune your brush without leaving the wheel", center=True)
d = ImageDraw.Draw(img)
for i, (name, title, sub) in enumerate([("sculpt_hover", "Hover", "The centre names the button under the cursor"),
                                        ("sculpt_drag_radius", "Drag up / down", "Brush radius"),
                                        ("sculpt_drag_strength", "Drag left / right", "Brush strength")]):
    cx = 240 + i * 360
    zoom_circle(img, "centre", name, cx, y + 150, 290, 118)
    label(d, cx, y + 320, title, sub)
save_slide(img, "g03_centre.png")

# 4. Themes
img = canvas(GH, spots=((600, 380, 520),))
y = header(img, 600, 44, "NEW  \u00b7  THEMES", "Ten looks built in. Or make your own.", center=True)
d = ImageDraw.Draw(img)
for i, n in enumerate(THEMES):
    cx = 156 + (i % 5) * 222
    cy = y + 92 + (i // 5) * 238
    place_wheel(img, "themes", "sculpt_" + n.lower().replace(" ", "_"), cx, cy, 178, with_pill=False)
    d.text((P(cx), P(cy + 100)), n, font=F_SMALL, fill=TEXT, anchor="ma")
save_slide(img, "g04_themes.png")

# 5. Double ring
img = canvas(GH, spots=((820, 400, 400),))
y = header(img, 72, 56, "NEW  \u00b7  DOUBLE RING", "Big brush sets, one glance",
           "A set that doesn't fit on one ring gets a second, staggered ring.", max_w=420)
d = ImageDraw.Draw(img)
k = 500 / (2 * two["radius"])
d.text((P(72), P(y + 20)), "34", font=F_STAT, fill=ACCENT)
d.text((P(72), P(y + 100)), "brushes on one page", font=F_SUB, fill=TEXT)
d.text((P(72), P(y + 136)), "instead of 14 with one ring", font=F_SMALL, fill=MUTED)
place_wheel(img, "double", "big_two_rings", 840, 380, 500, glow=True)
save_slide(img, "g05_double_ring.png")

# 6. Color
img = canvas(GH, spots=((330, 400, 300), (870, 400, 300)))
y = header(img, 600, 56, "COLOR, BUILT IN", "Pick colors without leaving the wheel", center=True)
d = ImageDraw.Draw(img)
for i, (mid, name) in enumerate([("vertex", "Vertex Paint"), ("gp-draw", "Grease Pencil Draw")]):
    cx = 330 + i * 540
    place_wheel(img, "modes", mid, cx, y + 190, 360, with_pill=False)
    label(d, cx, y + 392, name)
save_slide(img, "g06_color.png")

# 7. Theme tab
img = canvas(GH, spots=((980, 420, 360),))
y = header(img, 72, 48, "THEME TAB", "Every color, edited live")
framed(img, os.path.join(CAP, "prefs", "prefs_theme_modified.png"), (236, 330, 1574, 1000), 72, y - 6, 700)
place_wheel(img, "themes", "sculpt_midnight", 960, 400, 400, with_pill=False, glow=True)
save_slide(img, "g07_theme_tab.png")

# 8. Make it yours
img = canvas(GH, spots=((100, 600, 380),))
y = header(img, 72, 64, "MAKE IT YOURS", "Your brushes, your buttons, your look")
cards(img, y + 24, [
    ("Brush sets", "Any brush asset, your own included. Switch sets right from the wheel."),
    ("Custom buttons", "Panels, menus, operators, toggles or your own Python scripts."),
    ("Your icons", "Pick from the bundled icon set or load any image."),
    ("Tints", "Color buttons by type or one by one: fill, outline, icon or a strip."),
    ("Themes", "Ten built in, plus every theme you save."),
    ("Per mode", "Every mode keeps its own sets, ready when you switch."),
], cols=3, h=205)
save_slide(img, "g08_yours.png")
