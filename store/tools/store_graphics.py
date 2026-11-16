"""Extra store graphics for Sculpt-Paint Wheel (Superhive pages are image-first).

Usage: python gfx.py <docs/images dir> <output dir> <prefs screenshot>
Reuses the style helpers from promo_images.py (everything before its first image).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC, OUT, PREFS = sys.argv[1], sys.argv[2], sys.argv[3]
helpers = open(os.path.join(HERE, "promo_images.py"), encoding="utf-8").read().split("# 1. Hero")[0]
sys.argv = [sys.argv[0], SRC, OUT]
exec(helpers)  # defines W, S, fonts, colors, canvas, heading, paragraph, card, pill, screenshot, save, wrap, font...

from PIL import Image, ImageDraw  # noqa: E402

GREEN = (120, 210, 140)


def grid_cards(d, y, items, cols, cw, ch, gap=24, x0=70):
    y += 14
    for i, (icon, title, body) in enumerate(items):
        card(d, x0 + (i % cols) * (cw + gap), y + (i // cols) * (ch + gap), cw, ch, icon, title, body)
    rows = (len(items) + cols - 1) // cols
    return y + rows * (ch + gap)


def keycap(d, x, y, label, h=54):
    f = F_BODY_B
    w = d.textlength(label, font=f) / S + 40
    d.rounded_rectangle(((x) * S, (y + 5) * S, (x + w) * S, (y + h + 5) * S), radius=10 * S, fill=(14, 10, 22))
    d.rounded_rectangle((x * S, y * S, (x + w) * S, (y + h) * S), radius=10 * S, fill=(62, 52, 88), outline=CARD_EDGE, width=2 * S)
    d.text(((x + w / 2) * S, (y + h / 2) * S), label, font=f, fill=WHITE, anchor="mm")
    return x + w


# --- Benefits -----------------------------------------------------------------
H = 650
img = canvas(H, glow_at=(1150, 40, 220))
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "WHY ARTISTS LOVE IT", "Built for flow")
grid_cards(d, y, [
    ("⚡", "Blazing fast", "One gesture instead of three clicks. Seconds saved, every stroke."),
    ("✋", "Muscle memory", "Brushes keep their place on the ring. Your hand learns where they are."),
    ("◎", "Every paint mode", "Sculpt, paint, hair curves and all Grease Pencil modes."),
    ("⚙", "Your setup", "Brush sets and custom buttons for any workflow."),
    ("✔", "Feels native", "Blender's own brushes, panels and operators. Nothing to relearn."),
    ("★", "Blender 5.x ready", "A modern extension, tested on Blender 5.3."),
], cols=3, cw=340, ch=210)
save(img, H, "10_benefits.png")

# --- Controls -----------------------------------------------------------------
H = 640
img = canvas(H)
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "CONTROLS", "Everything at your fingertips")
rows = [
    (["Hold  Space"], "Open the wheel under the cursor"),
    (["Left Click"], "Pick a brush or run a button"),
    (["Mouse Wheel"], "Switch brush pages"),
    (["Release  Space"], "Close the wheel"),
    (["Esc", "Right Click"], "Cancel"),
]
for keys, text in rows:
    x = 70
    for i, k in enumerate(keys):
        if i:
            d.text(((x + 14) * S, (y + 27) * S), "/", font=F_BODY_B, fill=DIM, anchor="lm")
            x += 40
        x = keycap(d, x, y, k)
    d.text((420 * S, (y + 27) * S), text, font=F_BODY, fill=SOFT, anchor="lm")
    y += 78
d.text((70 * S, (y + 10) * S), "Tip: turn on Select on Release to press, move and release in one motion.", font=F_SMALL, fill=ORANGE_TXT)
save(img, H, "11_controls.png")

# --- Wheel anatomy -------------------------------------------------------------
H = 820
img = canvas(H, glow_at=(600, 430, 300))
d = ImageDraw.Draw(img)
heading(d, 70, 60, "THE WHEEL AT A GLANCE", "Know your wheel")
# Crop the wheel from the Sculpt capture and place it in the middle.
crop = (430, 230, 880, 650)  # screenshot px
scale = 1.25
wx, wy = 600 - (crop[2] - crop[0]) * scale / 2, 200
bottom = screenshot(img, os.path.join(SRC, "spwheel_sculpt.png"), (int(wx), wy, int((crop[2] - crop[0]) * scale)), crop=crop, radius=24)


def to_canvas(px, py):
    return wx + (px - crop[0]) * scale, wy + (py - crop[1]) * scale


def callout(target, label, side, ly):
    tx, ty = to_canvas(*target)
    lx = 70 if side == "L" else W - 70
    d.ellipse(((tx - 7) * S, (ty - 7) * S, (tx + 7) * S, (ty + 7) * S), fill=ORANGE)
    elbow = (wx - 30) if side == "L" else (wx + (crop[2] - crop[0]) * scale + 30)
    d.line([(tx * S, ty * S), (elbow * S, ly * S), ((lx + (250 if side == "L" else -250)) * S, ly * S)], fill=ORANGE, width=3 * S)
    d.text((lx * S, ly * S), label, font=F_BODY_B, fill=WHITE, anchor="lm" if side == "L" else "rm")


callout((598, 263), "Set name", "L", 263)
callout((570, 345), "Brush ring", "L", 420)
callout((714, 452), "Custom buttons", "R", 452)
callout((672, 624), "Page indicator", "R", 700)
d.text((70 * S, (H - 50) * S), "Weight Paint shows a 0.0–1.0 weight dial instead of the brush ring.", font=F_SMALL, fill=DIM)
save(img, H, "12_anatomy.png")

# --- Modes reference --------------------------------------------------------------
H = 790
img = canvas(H, glow_at=(1150, 40, 220))
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "OUT OF THE BOX", "A wheel for every mode")
grid_cards(d, y, [
    ("●", "Sculpt", "18 brushes, masks, remesh, stroke & falloff"),
    ("●", "Texture Paint", "15 brushes incl. pixel art, clone, fill"),
    ("●", "Vertex Paint", "8 brushes, symmetry, color tools"),
    ("●", "Weight Paint", "Weight dial 0.0–1.0, weight tools"),
    ("●", "Sculpt Curves", "12 hair brushes, symmetry, snapping"),
    ("●", "GP Draw", "13 brushes, layers, materials, stabilizer"),
    ("●", "GP Sculpt", "9 brushes, auto-masking, multi-frame"),
    ("●", "GP Weight", "Weight dial, normalize, invert, smooth"),
    ("●", "GP Vertex", "5 brushes, color, palette, vertex color"),
], cols=3, cw=340, ch=170)
save(img, H, "13_modes_reference.png")

# --- Requirements & install --------------------------------------------------------
H = 510
img = canvas(H)
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "REQUIREMENTS", "Install in a minute")
x = 70
for label in ("Blender 5.1+", "Tested on 5.3", "Windows • macOS • Linux", "No internet needed"):
    tw = d.textlength(label, font=F_SMALL) / S + 40
    d.rounded_rectangle((x * S, y * S, (x + tw) * S, (y + 44) * S), radius=22 * S, fill=CARD, outline=ORANGE, width=2 * S)
    d.text(((x + 20) * S, (y + 22) * S), label, font=F_SMALL, fill=WHITE, anchor="lm")
    x += tw + 14
y += 90
grid_cards(d, y, [
    ("1", "Download", "Get spwheel-<version>.zip. Don't unzip it."),
    ("2", "Install", "Preferences › Get Extensions › Install from Disk, or drag & drop."),
    ("3", "Hold Space", "In any sculpt or paint mode. Done!"),
], cols=3, cw=340, ch=200)
save(img, H, "14_requirements.png")

# --- Preferences (real screenshot) --------------------------------------------------
H = 640
img = canvas(H)
d = ImageDraw.Draw(img)
y = heading(d, 70, 60, "PREFERENCES", "Tune it to your taste")
screenshot(img, PREFS, (70, int(y), 640), crop=(172, 240, 840, 534), radius=14)
ty = y + 10
for title, body in [
    ("Scale", "Make the wheel bigger or smaller."),
    ("Keep Open", "Pick several things before closing."),
    ("Select on Release", "Press, move, release: done."),
    ("Theme", "Colors for the wheel and buttons."),
    ("Weight Wheel", "Markers and direct selection weight."),
]:
    d.text((740 * S, ty * S), "●  " + title, font=F_BODY_B, fill=WHITE)
    ty = paragraph(d, 768, ty + 36, body, f=F_SMALL, fill=SOFT, max_w=400, gap=6) + 22
save(img, H, "15_preferences.png")

# --- Free and open -------------------------------------------------------------------
H = 560
img = canvas(H, glow_at=(600, 60, 260))
d = ImageDraw.Draw(img)
d.text((W * S // 2, 80 * S), "FREE & OPEN SOURCE", font=F_KICK, fill=ORANGE_TXT, anchor="mm")
d.text((W * S // 2, 140 * S), "Open, just like Blender", font=F_H1, fill=WHITE, anchor="mm")
y = 205
for line in wrap(d, "Blender exists because people chose to support something open that everyone can use. "
                    "Sculpt-Paint Wheel follows the same spirit: the code is open and free to download on GitHub.", F_BODY, 980):
    d.text((W * S // 2, y * S), line, font=F_BODY, fill=SOFT, anchor="ma")
    y += 36
y += 24
for line in wrap(d, "Buying it here keeps development going, so everyone benefits, including students and artists who can't afford it.",
                 F_BODY_B, 980):
    d.text((W * S // 2, y * S), line, font=F_BODY_B, fill=WHITE, anchor="ma")
    y += 36
label = "Thank you for your support ♥"
pill(d, (W - (d.textlength(label, font=F_BTN) / S + 56)) / 2, y + 40, label)
save(img, H, "16_free_open.png")

# --- Chapter banners (docs) ----------------------------------------------------------
CHAPTERS = ["Getting started", "The wheel at a glance", "Controls", "Modes reference", "Brush sets",
            "Custom buttons", "Preferences", "Your data and backups", "Hotkeys and keymap", "Troubleshooting"]
for i, title in enumerate(CHAPTERS, 1):
    H = 150
    img = canvas(H, glow_at=(90, 75, 140))
    d = ImageDraw.Draw(img)
    d.ellipse((50 * S, 33 * S, 134 * S, 117 * S), fill=ORANGE)
    d.text((92 * S, 75 * S), str(i), font=font("seguibl.ttf", 40), fill=WHITE, anchor="mm")
    d.text((165 * S, 52 * S), "SCULPT-PAINT WHEEL  •  USER GUIDE", font=F_KICK, fill=ORANGE_TXT, anchor="lm")
    d.text((165 * S, 95 * S), title, font=F_H2, fill=WHITE, anchor="lm")
    save(img, H, f"ch{i:02d}.png")
