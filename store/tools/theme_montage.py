"""Edit a theme recording (frames from a Blender session) into store videos.

Usage:
    python store/tools/theme_montage.py <recording dir> <output dir> tints|presets

<recording dir> holds frames/NNN.png + frames.json, written by ``capture_v2.py`` (parts ``tints`` and ``presets``):
the wheel theme changed live, Preferences on the left, the open wheel on the right. Each frame is composed into
1920x1080: caption on top, a part of the Theme tab (the changing rows highlighted) on the left, the wheel on the
right. Consecutive frames crossfade. Needs ffmpeg on PATH.

Outputs:
    tints    v2_theme_tints.mp4 (everything), v2_tint_modes.mp4 / .webp (Disabled / Per Type / Custom),
             v2_tint_targets.mp4 / .webp (Custom: Color Strip, Outline, Icon, Fill), v2_tints_still.png
    presets  v2_theme_presets.mp4 / .webp (the built-in themes one after another), v2_presets_still.png
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REC, OUT, KIND = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
meta = json.load(open(os.path.join(REC, "frames.json"), encoding="utf-8"))["frames"]

W, H, FPS = 1920, 1080, 30
F = "C:/Windows/Fonts/"
ORANGE = (255, 140, 40)
F_KICK = ImageFont.truetype(F + "segoeuib.ttf", 26)
F_TITLE = ImageFont.truetype(F + "seguibl.ttf", 56)
F_SUB = ImageFont.truetype(F + "segoeui.ttf", 30)


def background():
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for x in range(W):
        t = x / W
        d.line([(x, 0), (x, H)], fill=(int(46 * (1 - t) + 22 * t), int(20 * (1 - t) + 24 * t), int(78 * (1 - t) + 36 * t)))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((1180, 260, 1820, 900), fill=90)
    bg.paste(Image.new("RGB", (W, H), ORANGE), (0, 0), glow.filter(ImageFilter.GaussianBlur(120)))
    return bg


BG = background()

# Per recording: (panel top, panel bottom, highlight top, highlight bottom), in pixels from the top of the
# Preferences area of a capture_v2.py recording (1920x1200 window, Preferences on the left 45%).
LAYOUT = {
    "tints": (785, 1062, 920, 996),     # Pie Menu section; highlight: Tint, Target, Opacity / Strength.
    "presets": (497, 790, 497, 524),    # Theme selector, General and Wheel sections; highlight: the selector.
}


def rounded(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=r, fill=255)
    return m


def paste_card(canvas, im, xy, r=22):
    x, y = xy
    shadow = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle((x + 8, y + 14, x + im.width + 8, y + im.height + 14), radius=r, fill=170)
    canvas.paste(Image.new("RGB", canvas.size, (8, 4, 14)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(18)))
    canvas.paste(im, (x, y), rounded(im, r))
    ImageDraw.Draw(canvas).rounded_rectangle((x, y, x + im.width, y + im.height), radius=r, outline=(80, 66, 112), width=2)


def compose(fr):
    shot = Image.open(os.path.join(REC, "frames", fr["file"])).convert("RGB")
    win_h = fr["window"][1]
    # Part of the Theme tab (offsets from the top of the Preferences area, see LAYOUT).
    px, py, pw, ph = fr["prefs"]
    top = win_h - (py + ph)
    PANEL_Y0, PANEL_Y1, HL0, HL1 = LAYOUT[KIND]
    panel = shot.crop((px + 172, top + PANEL_Y0, px + pw - 8, top + PANEL_Y1))
    # Wheel: square around the wheel centre.
    cx, cy = fr["wheel"][0], win_h - fr["wheel"][1]
    wheel = shot.crop((cx - 300, cy - 300, cx + 300, cy + 300))

    canvas = BG.copy()
    d = ImageDraw.Draw(canvas)
    kicker = "SCULPT-PAINT WHEEL 2  \u2022  " + ("THEMES" if KIND == "presets" else "THEME")
    d.text((80, 58), kicker, font=F_KICK, fill=(255, 176, 80))
    label = fr["label"].replace("\u00b7", "\u2022")
    d.text((80, 92), label, font=F_TITLE, fill=(255, 255, 255))
    d.text((80 + d.textlength(label, font=F_TITLE) + 28, 112), fr["sub"], font=F_SUB, fill=(215, 208, 232))

    pw2 = 800
    sy = pw2 / panel.width
    panel = panel.resize((pw2, int(panel.height * sy)), Image.Resampling.LANCZOS)
    py0 = 205 + (820 - panel.height) // 2
    paste_card(canvas, panel, (80, py0), r=16)
    # Highlight the rows that change.
    hl_top, hl_bottom = py0 + int((HL0 - PANEL_Y0) * sy), py0 + int((HL1 - PANEL_Y0) * sy)
    d.rounded_rectangle((66, hl_top, 80 + pw2 + 14, hl_bottom), radius=14, outline=ORANGE, width=4)

    ws = 820
    wheel = wheel.resize((ws, ws), Image.Resampling.LANCZOS)
    paste_card(canvas, wheel, (W - ws - 90, 205), r=28)
    return canvas


def durations():
    """Seconds each recorded frame stays on screen (repeated frames = a held state)."""
    out = []
    for i, fr in enumerate(meta):
        same_next = i + 1 < len(meta) and meta[i + 1]["sub"] == fr["sub"] and meta[i + 1]["label"] == fr["label"]
        out.append(0.55 if same_next else 0.8)
    return out


def render(indices, name, webp=False):
    tmp = tempfile.mkdtemp(prefix="spw_montage_")
    try:
        frames = [compose(meta[i]) for i in indices]
        secs = [durations()[i] for i in indices]
        fade = int(0.25 * FPS)
        n = 0
        for k, im in enumerate(frames):
            hold = max(1, int(secs[k] * FPS) - (fade if k + 1 < len(frames) else 0))
            for _ in range(hold):
                im.save(os.path.join(tmp, f"{n:05d}.png")); n += 1
            if k + 1 < len(frames):
                for f in range(fade):
                    Image.blend(im, frames[k + 1], (f + 1) / (fade + 1)).save(os.path.join(tmp, f"{n:05d}.png")); n += 1
        mp4 = os.path.join(OUT, f"{name}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "slow", "-movflags", "+faststart", mp4],
                       check=True)
        print(f"wrote {mp4} ({n / FPS:.1f}s, {os.path.getsize(mp4) / 1e6:.1f} MB)")
        if webp:
            out = os.path.join(OUT, f"{name}.webp")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf", "fps=12,scale=960:-1:flags=lanczos",
                            "-c:v", "libwebp", "-lossless", "0", "-q:v", "60", "-loop", "0", "-an", out], check=True)
            print(f"wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def idx(pred):
    return [i for i, f in enumerate(meta) if pred(f)]


if KIND == "tints":
    render(list(range(len(meta))), "v2_theme_tints")
    render(idx(lambda f: f["label"].startswith("Tint:")), "v2_tint_modes", webp=True)
    render(idx(lambda f: f["label"].startswith("Custom")), "v2_tint_targets", webp=True)
    compose(meta[-1]).save(os.path.join(OUT, "v2_tints_still.png"))
else:
    render(list(range(len(meta))), "v2_theme_presets", webp=True)
    compose(meta[0]).save(os.path.join(OUT, "v2_presets_still.png"))
