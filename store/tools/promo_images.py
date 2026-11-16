"""Render the promo images for Sculpt-Paint Wheel (README and stores).

Usage: python promo_images.py <docs/images dir> <output dir> [<dir with texture/weight paint captures>]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

W = 1200
S = 2  # supersampling factor
F = "C:/Windows/Fonts/"
LANCZOS = Image.Resampling.LANCZOS

ORANGE = (255, 140, 40)
ORANGE_TXT = (255, 176, 80)
WHITE = (255, 255, 255)
SOFT = (220, 214, 235)
DIM = (170, 160, 195)
CARD = (38, 30, 58)
CARD_EDGE = (70, 58, 100)


def font(name, size):
    return ImageFont.truetype(F + name, size * S)


F_KICK = font("segoeuib.ttf", 22)
F_H1 = font("seguibl.ttf", 54)
F_H2 = font("seguibl.ttf", 40)
F_BODY = font("segoeui.ttf", 25)
F_BODY_B = font("segoeuib.ttf", 25)
F_SMALL = font("segoeui.ttf", 20)
F_BTN = font("segoeuib.ttf", 26)
F_CARD_T = font("segoeuib.ttf", 26)
F_CARD_B = font("segoeui.ttf", 20)
F_ICON = font("seguisym.ttf", 34)


def canvas(h, glow_at=None):
    """Dark violet->charcoal gradient with an optional orange glow (x, y, r) in px."""
    w, hh = W * S, h * S
    img = Image.new("RGB", (w, hh))
    d = ImageDraw.Draw(img)
    for x in range(w):
        t = x / w
        d.line([(x, 0), (x, hh)], fill=(int(46 * (1 - t) + 22 * t), int(20 * (1 - t) + 24 * t), int(78 * (1 - t) + 36 * t)))
    if glow_at:
        gx, gy, gr = (v * S for v in glow_at)
        glow = Image.new("L", (w, hh), 0)
        ImageDraw.Draw(glow).ellipse((gx - gr, gy - gr, gx + gr, gy + gr), fill=95)
        glow = glow.filter(ImageFilter.GaussianBlur(80 * S))
        img.paste(Image.new("RGB", (w, hh), ORANGE), (0, 0), glow)
    return img


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if d.textlength(test, font=f) <= max_w * S:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def paragraph(d, x, y, text, f=F_BODY, fill=SOFT, max_w=1000, gap=10):
    """Draw wrapped text; x/y in px; returns the y (px) after the block."""
    lh = f.size / S + gap
    for line in wrap(d, text, f, max_w):
        d.text((x * S, y * S), line, font=f, fill=fill)
        y += lh
    return y


def heading(d, x, y, kicker, title, f_title=F_H2):
    d.text((x * S, y * S), kicker, font=F_KICK, fill=ORANGE_TXT)
    d.text((x * S, (y + 30) * S), title, font=f_title, fill=WHITE)
    return y + 30 + f_title.size / S + 22


def screenshot(img, path, box, crop=None, radius=18):
    """Paste a rounded screenshot into box=(x, y, w) px, keeping aspect ratio; returns bottom y px."""
    shot = Image.open(path).convert("RGB")
    if crop:
        shot = shot.crop(crop)
    x, y, w = (int(v) for v in box)
    h = int(shot.height * w / shot.width)
    shot = shot.resize((w * S, h * S), LANCZOS)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, shot.size[0] - 1, shot.size[1] - 1), radius=radius * S, fill=255)
    shadow = Image.new("L", (img.width, img.height), 0)
    ImageDraw.Draw(shadow).rounded_rectangle(((x + 6) * S, (y + 10) * S, (x + w + 6) * S, (y + h + 10) * S), radius=radius * S, fill=170)
    shadow = shadow.filter(ImageFilter.GaussianBlur(14 * S))
    img.paste(Image.new("RGB", img.size, (8, 4, 14)), (0, 0), shadow)
    img.paste(shot, (x * S, y * S), mask)
    ImageDraw.Draw(img).rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), radius=radius * S, outline=CARD_EDGE, width=2 * S)
    return y + h


def pill(d, x, y, label, fill=ORANGE, f=F_BTN, h=60):
    bw = d.textlength(label, font=f) / S + 56
    d.rounded_rectangle(((x + 3) * S, (y + 5) * S, (x + bw + 3) * S, (y + h + 5) * S), radius=h * S // 2, fill=(20, 10, 30))
    d.rounded_rectangle((x * S, y * S, (x + bw) * S, (y + h) * S), radius=h * S // 2, fill=fill)
    d.text(((x + 28) * S, (y + h / 2) * S), label, font=f, fill=WHITE, anchor="lm")
    return x + bw


def card(d, x, y, w, h, icon, title, body):
    d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), radius=16 * S, fill=CARD, outline=CARD_EDGE, width=2 * S)
    d.text(((x + 24) * S, (y + 22) * S), icon, font=F_ICON, fill=ORANGE)
    d.text(((x + 78) * S, (y + 26) * S), title, font=F_CARD_T, fill=WHITE)
    paragraph(d, x + 24, y + 74, body, f=F_CARD_B, fill=SOFT, max_w=w - 48, gap=7)


def save(img, h, name):
    img.resize((W, h), LANCZOS).save(os.path.join(OUT, name), optimize=True)
    print("saved", name)


# 1. Hero ---------------------------------------------------------------------
H = 900
img = canvas(H, glow_at=(600, 560, 420))
d = ImageDraw.Draw(img)
d.text((W * S // 2, 64 * S), "BLENDER ADD-ON  •  FREE & OPEN SOURCE", font=F_KICK, fill=ORANGE_TXT, anchor="mm")
d.text((W * S // 2, 128 * S), "Sculpt-Paint Wheel", font=font("seguibl.ttf", 70), fill=WHITE, anchor="mm")
d.text((W * S // 2, 196 * S), "Your brushes, one keypress away.", font=font("segoeui.ttf", 32), fill=SOFT, anchor="mm")
screenshot(img, os.path.join(SRC, "spwheel_sculpt.png"), (170, 250, 860), crop=(150, 120, 1160, 760))
save(img, H, "01_hero.png")

# 2. How it works -----------------------------------------------------------
H = 680
img = canvas(H)
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "HOW IT WORKS", "Stay in the flow")
steps = [
    ("1", "Hold Space", "The wheel pops up right under your cursor, in the 3D Viewport."),
    ("2", "Flick & click", "Pick a brush on the outer ring, or run a custom button in the center."),
    ("3", "Keep working", "Release Space and you're back to sculpting or painting. No toolbar hunting."),
]
cw, gap = 330, 30
for i, (num, title, body) in enumerate(steps):
    x = 70 + i * (cw + gap)
    d.rounded_rectangle((x * S, y * S, (x + cw) * S, (y + 330) * S), radius=18 * S, fill=CARD, outline=CARD_EDGE, width=2 * S)
    d.ellipse(((x + 26) * S, (y + 28) * S, (x + 92) * S, (y + 94) * S), fill=ORANGE)
    d.text(((x + 59) * S, (y + 61) * S), num, font=font("seguibl.ttf", 34), fill=WHITE, anchor="mm")
    d.text(((x + 26) * S, (y + 120) * S), title, font=font("seguibl.ttf", 30), fill=WHITE)
    paragraph(d, x + 26, y + 172, body, f=F_BODY, fill=SOFT, max_w=cw - 52, gap=8)
paragraph(d, 70, y + 370, "Each mode has its own wheel, brush sets and custom buttons — set up exactly the workflow you want.",
          f=F_BODY, fill=DIM, max_w=1060)
save(img, H, "02_how_it_works.png")

# 3. Supported modes -----------------------------------------------------------
H = 1370
img = canvas(H, glow_at=(1150, 60, 220))
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "EVERY PAINT MODE", "Works where you work")
modes = ["Sculpt", "Vertex Paint", "Weight Paint", "Texture Paint", "Sculpt Curves (hair)",
         "Grease Pencil Draw", "Grease Pencil Sculpt", "Grease Pencil Weight", "Grease Pencil Vertex"]
x, row_y = 70, y
for m in modes:
    tw = d.textlength(m, font=F_SMALL) / S + 40
    if x + tw > W - 70:
        x, row_y = 70, row_y + 56
    d.rounded_rectangle((x * S, row_y * S, (x + tw) * S, (row_y + 42) * S), radius=21 * S, fill=CARD, outline=ORANGE, width=2 * S)
    d.text(((x + 20) * S, (row_y + 21) * S), m, font=F_SMALL, fill=WHITE, anchor="lm")
    x += tw + 12
top = row_y + 80
half = (W - 70 * 2 - 30) // 2
EXTRA = sys.argv[3] if len(sys.argv) > 3 else SRC  # folder with texture/weight paint captures
grid = [
    (os.path.join(SRC, "spwheel_sculpt.png"), "Sculpt"),
    (os.path.join(EXTRA, "spwheel_texture_paint.png"), "Texture Paint"),
    (os.path.join(SRC, "spwheel_grease_pencil.png"), "Grease Pencil Draw"),
    (os.path.join(EXTRA, "spwheel_weight_paint.png"), "Weight Paint"),
]
row_top = top
for row in range(2):
    bottoms = []
    for col in range(2):
        path, label = grid[row * 2 + col]
        x = 70 + col * (half + 30)
        bottoms.append(screenshot(img, path, (x, row_top, half), crop=(300, 150, 1010, 760)))
        d.text(((x + half / 2) * S, (max(bottoms) + 16) * S), label, font=F_BODY_B, fill=WHITE, anchor="ma")
    row_top = max(bottoms) + 70
save(img, H, "03_modes.png")

# 4. Customize -------------------------------------------------------------------
H = 1020
img = canvas(H)
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "MAKE IT YOURS", "Your brushes, your buttons")
bottom = screenshot(img, os.path.join(SRC, "spwheel_sidebar_sculpt.png"), (700, y + 10, 400), crop=(1040, 55, 1290, 560))
ty = y + 20
for title, body in [
    ("Brush Sets", "Build sets of your favorite brushes for the outer ring. Add the active brush with one click and reorder freely."),
    ("Custom Buttons", "Put panels, menus or operators in the center: stroke settings, masks, layers, remesh and more."),
    ("Ready-made presets", "Each mode comes with sensible defaults and a list of presets based on what Blender offers there."),
]:
    d.text((70 * S, ty * S), "\u25CF  " + title, font=F_BODY_B, fill=WHITE)
    ty = paragraph(d, 100, ty + 40, body, f=F_BODY, fill=SOFT, max_w=500, gap=8) + 26
save(img, H, "04_customize.png")

# 5. Download -------------------------------------------------------------------
H = 520
img = canvas(H, glow_at=(120, 260, 260))
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "FREE & OPEN SOURCE", "Download it on GitHub", f_title=F_H1)
y = paragraph(d, 70, y, "The add-on is free. Always grab the latest version from the GitHub releases page — the documentation lives there too.",
              max_w=1060)
end = pill(d, 70, y + 26, "Get the latest release  \u2192")
pill(d, end + 20, y + 26, "Read the docs", fill=(90, 70, 140))
d.text((70 * S, (y + 120) * S), "github.com/jfran3d/Sculpt-Paint-Wheel-Reborn  •  Blender 5.1+  •  Tested on Blender 5.3",
       font=F_SMALL, fill=DIM)
save(img, H, "05_download.png")

# 6. Support (one variant per channel) -----------------------------------------
def support_image(name, kicker, title, cta, footer, pills=()):
    H = 1000 if pills else 940
    img = canvas(H, glow_at=(600, 90, 260))
    d = ImageDraw.Draw(img)
    d.text((W * S // 2, 70 * S), "♥", font=font("seguisym.ttf", 70), fill=ORANGE, anchor="mm")
    d.text((W * S // 2, 140 * S), kicker, font=F_KICK, fill=ORANGE_TXT, anchor="mm")
    d.text((W * S // 2, 196 * S), title, font=F_H1, fill=WHITE, anchor="mm")
    y = 260
    for line in wrap(d, "Sculpt-Paint Wheel is built and maintained by one independent developer, with no company behind it. "
                        "Every Blender release changes something under the hood, and keeping the wheel working takes real hours.", F_BODY, 960):
        d.text((W * S // 2, y * S), line, font=F_BODY, fill=SOFT, anchor="ma")
        y += 36
    y += 10
    d.text((W * S // 2, y * S), cta, font=F_BODY_B, fill=WHITE, anchor="ma")
    y += 60
    if pills:
        widths = [d.textlength(p, font=F_BTN) / S + 56 for p, _ in pills]
        x = (W - sum(widths) - 20 * (len(pills) - 1)) / 2
        for (label, fill), w in zip(pills, widths):
            pill(d, x, y, label, fill=fill)
            x += w + 20
        y += 100
    else:
        y += 10
    cw, ch, gap = 525, 150, 30
    items = [
        ("↻", "New Blender versions", "Ports and testing for every new Blender release."),
        ("⚒", "Fixes & polish", "Bug fixes and quality-of-life improvements."),
        ("✦", "New features", "New wheels, new modes and new ideas."),
        ("♡", "Open source", "The code stays open on GitHub for everyone."),
    ]
    for i, (icon, ctitle, body) in enumerate(items):
        cx = 60 + (i % 2) * (cw + gap) + 15
        cy = y + (i // 2) * (ch + 24)
        card(d, cx, cy, cw, ch, icon, ctitle, body)
    y += 2 * (ch + 24) + 20
    d.text((W * S // 2, y * S), footer, font=F_SMALL, fill=DIM, anchor="ma")
    save(img, H, name)


# GitHub: points to the store.
support_image(
    "06_support_github.png", "LIKE THE WHEEL?", "Support the developer",
    "Buying it on Superhive funds what comes next:",
    "The add-on stays free and open source here on GitHub. Buying it is how you say thanks.",
    pills=(("Buy on Superhive  →", ORANGE),),
)
# Stores: thanks the buyer, no pricing talk.
support_image(
    "06_support_store.png", "THANK YOU", "Your purchase supports the developer",
    "Every purchase goes straight into keeping the wheel alive:",
    "New versions are always published on GitHub, so you'll never miss an update.",
)

# 7. Other ways to help -------------------------------------------------------
H = 430
img = canvas(H)
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "COMMUNITY", "More ways to help")
cw, gap = 340, 20
for i, (icon, title, body) in enumerate([
    ("\u2605", "Star on GitHub", "It helps other artists find the project."),
    ("\u2691", "Report bugs", "Open an issue with steps to reproduce it."),
    ("\u27A6", "Share it", "Tell your fellow Blender artists about it."),
]):
    card(d, 70 + i * (cw + gap), y, cw, 170, icon, title, body)
d.text((W * S // 2, (H - 40) * S), "Thank you for supporting independent Blender development! \u2665", font=F_BODY_B, fill=ORANGE_TXT, anchor="mm")
save(img, H, "07_help.png")
