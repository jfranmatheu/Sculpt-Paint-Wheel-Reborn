"""Edit a live theme recording into a store video: an animated cursor working the real Blender UI, the wheel
updating beside it.

Usage:
    python store/tools/live_montage.py <recording dir> <output dir> themes|tints

<recording dir> is a ``capture_v2.py`` recording (parts ``themes_live`` / ``tints_live``): frames/*.png + live.json.
Each beat is a real UI state from Blender plus where the cursor goes and what it does (move, click, press, drag,
release). Blender's screenshots have no cursor, so the cursor, its moves (eased) and clicks (ripples) are drawn
here, together with a camera that follows the action on the Preferences, the wheel cut out of the viewport,
animated captions and intro / outro cards. Needs ffmpeg on PATH.

Outputs: v2_<kind>.mp4 (1920x1080, 30 fps) and v2_<kind>.webp (animated, 800 px wide, for web pages).
"""
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

REC, OUT, KIND = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
LIVE = json.load(open(os.path.join(REC, "live.json"), encoding="utf-8"))
BEATS = LIVE["beats"]
FR = os.path.join(REC, "frames")

W, H, FPS = 1920, 1080, 30
FONTS = "C:/Windows/Fonts/"
LANCZOS = Image.Resampling.LANCZOS
BG_TOP, BG_BOTTOM = (17, 18, 23), (10, 11, 14)
ACCENT = (255, 138, 36)
TEXT = (244, 244, 247)
MUTED = (152, 155, 168)
EDGE = (255, 255, 255, 26)

THEME_NOTES = {
    "Dark": "The default", "Light": "Bright and crisp", "Midnight": "Deep navy, blue accent",
    "Ember": "Warm charcoal, orange glow", "Forest": "Dark greens, mint accent", "Rose": "Plum, pink accent",
    "Graphite": "Close to Blender's own greys", "High Contrast": "Black and white, yellow highlights",
    "Paper": "Cream and ink, terracotta", "Frost": "Icy blues and slate",
}
TITLE = {"themes": ("THEMES", "Ten looks, one click"), "tints": ("BUTTON TINTS", "Color your buttons, live")}[KIND]

# Layout: the Preferences "camera" panel on the left, the wheel on the right.
PANEL = (96, 250, 900, 740)          # x, y, w, h on the video
SRC_X0, SRC_X1 = 172, 712            # Preferences content, window px
SRC_Y_MIN, SRC_Y_MAX = 470, 1091
WHEEL_C, WHEEL_D = (1452, 600), 640  # centre and circle diameter of the wheel on the video


def vf(size, style="Regular"):
    f = ImageFont.truetype(FONTS + "SegUIVar.ttf", size)
    f.set_variation_by_name(style)
    return f


F_KICK = vf(22, "Semibold Text")
F_TITLE = vf(66, "Semibold Display")
F_SUB = vf(30, "Regular")
F_BIG = vf(92, "Bold Display")


# ----- Easing / timing ----------------------------------------------------------------------------------------------

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


# ----- Static pieces ------------------------------------------------------------------------------------------------

def background():
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    g = Image.new("L", (W // 8, H // 8), 0)
    gd = ImageDraw.Draw(g)
    for x, y, r in ((WHEEL_C[0], WHEEL_C[1], 470), (300, 0, 300)):
        gd.ellipse(((x - r) / 8, (y - r) / 8, (x + r) / 8, (y + r) / 8), fill=44)
    g = g.filter(ImageFilter.GaussianBlur(9)).resize((W, H), LANCZOS)
    img.paste(Image.new("RGB", (W, H), ACCENT), (0, 0), g)
    dots = Image.new("L", (W, H), 0)
    dd = ImageDraw.Draw(dots)
    for yy in range(13, H, 26):
        for xx in range(13, W, 26):
            dd.ellipse((xx - 1, yy - 1, xx + 1, yy + 1), fill=255)
    dots = ImageChops.multiply(dots, g.point(lambda v: min(255, v * 4))).point(lambda v: v * 0.1)
    img.paste(Image.new("RGB", (W, H), (255, 255, 255)), (0, 0), dots)
    return img


def rounded_mask(w, h, r):
    m = Image.new("L", (w * 3, h * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 3 - 1, h * 3 - 1), radius=r * 3, fill=255)
    return m.resize((w, h), LANCZOS)


def shadow_layer(mask, blur=26, opacity=0.65):
    pad = blur * 3
    m = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0)
    m.paste(mask, (pad, pad))
    return m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * opacity)), pad


BG_PLAIN = background()
BG = BG_PLAIN.copy()
PX, PY, PW, PH = PANEL
PANEL_MASK = rounded_mask(PW, PH, 22)
_sh, _pad = shadow_layer(PANEL_MASK)
BG.paste(Image.new("RGB", _sh.size, (0, 0, 0)), (PX - _pad, PY - _pad + 18), _sh)


def cursor_sprite(scale=1.0):
    k = 4
    pts = [(0, 0), (0, 17), (4.2, 13.2), (7, 19.6), (9.7, 18.5), (7, 12.3), (12.4, 12.3)]
    s = 1.75 * scale
    w, h = int(16 * s * k), int(23 * s * k)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    poly = [(2 * k + x * s * k, 2 * k + y * s * k) for x, y in pts]
    d.polygon(poly, fill=(255, 255, 255, 255), outline=(20, 20, 24, 255), width=int(1.4 * k))
    img = img.resize((w // k, h // k), LANCZOS)
    sh = img.getchannel("A").filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.55))
    out = Image.new("RGBA", (img.width + 8, img.height + 8), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", sh.size, (0, 0, 0, 255)), (3, 5), sh)
    out.alpha_composite(img, (0, 0))
    return out


CURSOR = cursor_sprite()
CURSOR_PRESSED = cursor_sprite(0.86)

_frames = {}


def frame(name):
    if name not in _frames:
        _frames[name] = Image.open(os.path.join(FR, name)).convert("RGB")
    return _frames[name]


_wheels = {}


def wheel_cut(file, cx, cy, r):
    """The wheel cut out of a window screenshot (circle + its page pill), scaled to WHEEL_D; cached."""
    key = (file, cx, cy, round(r))
    if key in _wheels:
        return _wheels[key]
    shot = frame(file)
    half = int(r + 60)
    crop = shot.crop((cx - half, cy - half, cx + half, cy + half))
    k = 4
    m = Image.new("L", (crop.width * k, crop.height * k), 0)
    md = ImageDraw.Draw(m)
    c, rr = half * k, (r + 0.6) * k
    md.ellipse((c - rr, c - rr, c + rr, c + rr), fill=255)
    ph, pw = max(26.0, r * 0.14 / 1.0), max(120.0, r * 0.64)
    top = r + ph * 0.3
    md.rounded_rectangle((c - pw / 2 * k, c + top * k, c + pw / 2 * k, c + (top + ph) * k), radius=ph / 2 * k, fill=255)
    m = m.resize(crop.size, LANCZOS)
    out = crop.convert("RGBA")
    out.putalpha(m)
    size = int(out.width * WHEEL_D / (2 * r))
    out = out.resize((size, size), LANCZOS)
    sh, pad = shadow_layer(out.getchannel("A"), blur=24, opacity=0.75)
    full = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    full.paste(Image.new("RGBA", sh.size, (0, 0, 0, 255)), (0, 22), sh)
    full.alpha_composite(out, (pad, pad))
    _wheels[key] = full
    return full


def beat_wheel(b):
    if b.get("wheel"):
        w = LIVE["wheels"][b["wheel"]]
        return wheel_cut(w["file"], w["cx"], w["cy"], w["radius"])
    g = b["geom"]
    return wheel_cut(b["file"], g["cx"], g["cy"], g["radius"])


_texts = {}


def text_sprite(text, f, fill, tracking=0.0):
    key = (text, f.size, fill, tracking)
    if key not in _texts:
        d = ImageDraw.Draw(Image.new("L", (1, 1)))
        sp = f.size * tracking
        w = int(sum(d.textlength(c, font=f) for c in text) + sp * max(0, len(text) - 1)) + 8
        img = Image.new("RGBA", (w, int(f.size * 1.5)), (0, 0, 0, 0))
        dd = ImageDraw.Draw(img)
        x = 0
        for c in (text if tracking else [text]):
            dd.text((x, 0), c, font=f, fill=fill)
            x += dd.textlength(c, font=f) + sp
        _texts[key] = img
    return _texts[key]


def paste_alpha(dst, sprite, x, y, alpha):
    if alpha <= 0:
        return
    if alpha < 1:
        sprite = sprite.copy()
        sprite.putalpha(sprite.getchannel("A").point(lambda v: int(v * alpha)))
    dst.alpha_composite(sprite, (int(x), int(y)))


# ----- Timeline -----------------------------------------------------------------------------------------------------

def caption_of(b):
    if KIND == "themes" and b["caption"] in THEME_NOTES:
        return b["caption"], THEME_NOTES[b["caption"]]
    return b["caption"], b["sub"]


INTRO, OUTRO = 1.6, 2.2
events = []  # per beat: start, arrive, end, from, to
t = INTRO
prev = BEATS[0]["cursor"]
for b in BEATS:
    to = b["cursor"]
    dist = math.dist(prev, to)
    if b["action"] in ("drag", "release"):
        travel = 0.0 if b["action"] == "release" else 0.11
    elif b["action"] == "idle":
        travel = 0.0
    else:
        travel = 0.28 + min(0.5, dist / 1500)
    arrive = t + travel
    end = arrive + max(0.08, b["hold"]) + (0.12 if b["action"] in ("click", "press") else 0)
    events.append({"b": b, "start": t, "arrive": arrive, "end": end, "from": prev, "to": to})
    prev, t = to, end
TOTAL = t + OUTRO
N = int(TOTAL * FPS)


def state_at(tt):
    """Cursor position, current prefs frame, wheel, caption and click / press state at time tt (seconds)."""
    ev = events[0]
    for e in events:
        if tt >= e["start"]:
            ev = e
    i = events.index(ev)
    b = ev["b"]
    if ev["arrive"] > ev["start"]:
        k = (tt - ev["start"]) / (ev["arrive"] - ev["start"])
        k = k if b["action"] == "drag" else ease(k)
    else:
        k = 1.0
    cur = (lerp(ev["from"][0], ev["to"][0], min(1, k)), lerp(ev["from"][1], ev["to"][1], min(1, k)))
    arrived = tt >= ev["arrive"]
    shown = b if arrived or i == 0 else events[i - 1]["b"]  # The UI changes when the cursor gets there.
    pressed = (b["action"] in ("press", "drag") and arrived) or (b["action"] == "click" and 0 <= tt - ev["arrive"] < 0.12)
    clicks = [e["arrive"] for e in events if e["b"]["action"] in ("click", "press") and 0 <= tt - e["arrive"] < 0.5]
    dragging = b["action"] in ("press", "drag")
    return cur, shown, pressed, clicks, dragging, i


# Camera: follows the beat's focus (cursor), eased; zooms in a little while dragging.
def camera_at(tt):
    def target(e):
        b = e["b"]
        y = b["cursor"][1] if KIND == "tints" else 650
        drag = b["action"] in ("press", "drag", "release")
        x = 560 if drag else (SRC_X0 + SRC_X1) / 2  # (Drags: centred on the slider.)
        return y, (1.15 if drag else 1.0), x

    ev_i = 0
    for j, e in enumerate(events):
        if tt >= e["start"]:
            ev_i = j
    y1, z1, x1 = target(events[ev_i])
    y0, z0, x0 = target(events[ev_i - 1]) if ev_i > 0 else (y1, z1, x1)
    e = events[ev_i]
    k = ease((tt - e["start"]) / 0.55)
    return lerp(y0, y1, k), lerp(z0, z1, k), lerp(x0, x1, k)


def panel_view(img, shown, cam_y, zoom, cam_x):
    base = (SRC_X1 - SRC_X0) / PW  # source px per video px at zoom 1
    sw, sh = (SRC_X1 - SRC_X0) / zoom, PH * base / zoom
    cx = max(SRC_X0 + sw / 2, min(SRC_X1 - sw / 2, cam_x))
    cy = max(SRC_Y_MIN + sh / 2, min(SRC_Y_MAX - sh / 2, cam_y))
    box = (cx - sw / 2, cy - sh / 2, cx + sw / 2, cy + sh / 2)
    crop = frame(shown["file"]).resize((PW, PH), LANCZOS, box=box)
    img.paste(crop, (PX, PY), PANEL_MASK)
    return box


def to_panel(p, box):
    return (PX + (p[0] - box[0]) / (box[2] - box[0]) * PW, PY + (p[1] - box[1]) / (box[3] - box[1]) * PH)


# Wheel changes: crossfade + a small pop.
wheel_changes = []
last = None
for e in events:
    w = e["b"].get("wheel") or e["b"]["file"]
    if KIND == "themes":
        w = e["b"].get("wheel")
    if w != last:
        wheel_changes.append((e["arrive"], e["b"]))
        last = w


def wheel_at(tt):
    cur_i = 0
    for j, (ts, _b) in enumerate(wheel_changes):
        if tt >= ts:
            cur_i = j
    ts, b = wheel_changes[cur_i]
    prev_b = wheel_changes[cur_i - 1][1] if cur_i > 0 else None
    k = (tt - ts) / 0.32
    return beat_wheel(b), (beat_wheel(prev_b) if prev_b is not None and k < 1 else None), k


def draw_wheel(img, tt):
    w, w_prev, k = wheel_at(tt)
    pop = 1.0 + (0.025 * math.sin(math.pi * min(1, k / 1.4)) if KIND == "themes" and 0 <= k < 1.4 else 0)

    def put(sprite, alpha):
        s = sprite if pop == 1.0 else sprite.resize((int(sprite.width * pop), int(sprite.height * pop)), Image.Resampling.BILINEAR)
        paste_alpha(img, s, WHEEL_C[0] - s.width / 2, WHEEL_C[1] - s.height / 2, alpha)

    if w_prev is not None:
        put(w_prev, 1.0)
        put(w, ease(k))
    else:
        put(w, 1.0)


def draw_caption(img, tt, i, shown):
    kick = text_sprite(f"SCULPT-PAINT WHEEL 2  \u00b7  {TITLE[0]}", F_KICK, ACCENT, 0.18)
    img.alpha_composite(kick, (PX, 70))
    title, sub = caption_of(shown)  # (What the UI shows right now: the caption changes with it.)
    j = i
    while j > 0 and caption_of(events[j - 1]["b"])[0] == title:
        j -= 1
    start = events[j]["start"]
    k = ease_out((tt - start) / 0.4)
    ts = text_sprite(title, F_TITLE, TEXT)
    paste_alpha(img, ts, PX, 104 + (1 - k) * 18, k)
    if sub:
        ss = text_sprite(sub, F_SUB, MUTED)
        x = PX + ts.width + 24
        paste_alpha(img, ss, x, 136 + (1 - k) * 18, k)


def draw_cursor(img, pos, pressed, clicks, tt, box):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for ct in clicks:
        k = ease_out((tt - ct) / 0.5)
        e = [x for x in events if x["arrive"] == ct][0]
        cx, cy = to_panel(e["to"], box)
        r = 8 + 34 * k
        a = int(230 * (1 - k))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ACCENT + (a,), width=4)
        d.ellipse((cx - 10 * (1 - k), cy - 10 * (1 - k), cx + 10 * (1 - k), cy + 10 * (1 - k)), fill=ACCENT + (int(120 * (1 - k)),))
    img.alpha_composite(layer)
    x, y = to_panel(pos, box)
    img.alpha_composite(CURSOR_PRESSED if pressed else CURSOR, (int(x) - 3, int(y) - 3))


def compose(n):
    tt = n / FPS
    img = BG.copy().convert("RGBA")
    pos, shown, pressed, clicks, dragging, i = state_at(tt)
    cam_y, zoom, cam_x = camera_at(tt)
    box = panel_view(img, shown, cam_y, zoom, cam_x)
    ImageDraw.Draw(img).rounded_rectangle((PX, PY, PX + PW, PY + PH), radius=22, outline=EDGE, width=2)
    draw_wheel(img, tt)
    draw_caption(img, tt, i, shown)
    if INTRO - 0.2 < tt < TOTAL - OUTRO + 0.3:
        draw_cursor(img, pos, pressed, clicks, tt, box)
    # Intro and outro cards over the scene.
    if tt < INTRO + 0.5:
        a = 1.0 if tt < INTRO - 0.3 else 1 - ease((tt - (INTRO - 0.3)) / 0.8)
        card(img, a, TITLE[0], TITLE[1])
    if tt > TOTAL - OUTRO:
        a = ease((tt - (TOTAL - OUTRO)) / 0.6)
        card(img, a, "SCULPT-PAINT WHEEL 2", "Available on Superhive")
    return img.convert("RGB")


def card(img, a, kicker, title):
    if a <= 0:
        return
    over = BG_PLAIN.copy().convert("RGBA")
    k = text_sprite(kicker, F_KICK, ACCENT, 0.2)
    t = text_sprite(title, F_BIG, TEXT)
    over.alpha_composite(k, ((W - k.width) // 2, 430))
    over.alpha_composite(t, ((W - t.width) // 2, 474))
    over.putalpha(int(255 * a))
    img.alpha_composite(over)


def render():
    mp4 = os.path.join(OUT, f"v2_{KIND}.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                             "-preset", "slow", "-movflags", "+faststart", mp4], stdin=subprocess.PIPE)
    for n in range(N):
        proc.stdin.write(compose(n).tobytes())
        if n % 150 == 0:
            print(f"  frame {n}/{N}", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"wrote {mp4} ({TOTAL:.1f}s, {os.path.getsize(mp4) / 1e6:.1f} MB)")
    webp = os.path.join(OUT, f"v2_{KIND}.webp")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf", "fps=12,scale=800:-1:flags=lanczos",
                    "-c:v", "libwebp", "-lossless", "0", "-q:v", "55", "-loop", "0", "-an", webp], check=True)
    print(f"wrote {webp} ({os.path.getsize(webp) / 1e6:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[4] == "--still":  # A few frames to check the composition.
        for s in sys.argv[5:]:
            compose(int(float(s) * FPS)).save(os.path.join(OUT, f"still_{KIND}_{s}.png"))
    else:
        render()
