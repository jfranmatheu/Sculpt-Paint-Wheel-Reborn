"""Edit the promo video: the real recordings (rec_promo.py), cut to the music (make_promo_music.py).

Usage:
    python store/video/make_promo.py <recordings dir> <audio dir> <out dir> [--fmt 16x9|1x1|9x16|all] [--stills 1.0,5.5]

16:9 (1920x1080) and 1:1 (1080x1080) are full-bleed; 9:16 (1080x1920) puts the footage on a square stage between
title bands. Every format comes from the same timeline: shots map timeline frames to recording frames (speed ramps,
frame blending for slow motion) and to a camera (focus point + zoom on the 2560x1361 recordings, at most 1.1x
upscale); on top come the pointer (logged per frame by the recorder), click ripples, the Space keycap, kinetic
type, transitions (whips, flashes, RGB split, punch-ins), a 2x2 grid, a stutter montage and the end card.
Frames are piped to ffmpeg; the audio is the music plus click / whoosh sounds, loudness-normalised to -14 LUFS.
"""
import importlib.util
import json
import math
import os
import subprocess
import sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REC, AUDIO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
FMT = sys.argv[sys.argv.index("--fmt") + 1] if "--fmt" in sys.argv else "16x9"
STILLS = [float(s) for s in sys.argv[sys.argv.index("--stills") + 1].split(",")] if "--stills" in sys.argv else None
os.makedirs(OUT, exist_ok=True)
FFMPEG = "ffmpeg"

FPS = 30
TOTAL = 1380                       # 46 s = 23 bars at 120 BPM (1 beat = 15 frames, 1 bar = 60)
UI = 1.3333
ACCENT = (255, 138, 36)
TEXT = (244, 244, 247)
MUTED = (170, 172, 184)
BG_TOP, BG_BOTTOM = (17, 18, 23), (9, 10, 13)
FONTS = "C:/Windows/Fonts/"

SIZES = {"16x9": (1920, 1080), "1x1": (1080, 1080), "9x16": (1080, 1920)}


def vf(size, style="Regular"):
    f = ImageFont.truetype(FONTS + "SegUIVar.ttf", int(size))
    f.set_variation_by_name(style)
    return f


# ----- Recordings ----------------------------------------------------------------------------------------------------

class Seq:
    def __init__(self, name):
        self.name = name
        self.dir = os.path.join(REC, name)
        self.meta = json.load(open(os.path.join(self.dir, "meta.json")))
        self.frames = self.meta["frames"]
        self.n = len(self.frames)
        self.marks = self.meta["marks"]
        head = self.meta.get("head")
        self.head = (head[0], head[1]) if head else (1280, 680)
        self.opens = [i for i in range(1, self.n) if "SPACE" in self.frames[i]["keys"] and "SPACE" not in self.frames[i - 1]["keys"]]

    def ptr(self, s):
        i = int(max(0, min(self.n - 1, math.floor(s))))
        j = min(self.n - 1, i + 1)
        k = max(0.0, min(1.0, s - i))
        a, b = self.frames[i], self.frames[j]
        return a["x"] + (b["x"] - a["x"]) * k, a["y"] + (b["y"] - a["y"]) * k, a["down"], "SPACE" in a["keys"]

    def open_pos(self, k=0):
        f = self.frames[self.opens[k]]
        return f["x"], f["y"]


SEQ = {n: Seq(n) for n in ("pain", "sculpt", "texture", "gpencil", "weight", "themes", "double")}


@lru_cache(maxsize=24)
def raw(name, i):
    s = SEQ[name]
    i = int(max(0, min(s.n - 1, i)))
    im = cv2.imread(os.path.join(s.dir, f"{i:04d}.png"), cv2.IMREAD_COLOR)
    return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)


def src_frame(name, s):
    """Recording frame at a fractional index (blended for slow motion)."""
    i = math.floor(s)
    k = s - i
    a = raw(name, i)
    if k < 0.12 or i + 1 >= SEQ[name].n:
        return a
    if k > 0.88:
        return raw(name, i + 1)
    return cv2.addWeighted(a, 1 - k, raw(name, i + 1), k, 0)


# ----- Timing helpers ------------------------------------------------------------------------------------------------

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def pw(*pts):
    """Piecewise-linear map (timeline frame -> recording frame)."""
    def f(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, s0), (t1, s1) in zip(pts, pts[1:]):
            if t <= t1:
                return s0 + (s1 - s0) * (t - t0) / max(1e-6, t1 - t0)
        return pts[-1][1]
    return f


def cam(*keys):
    """Eased camera keys (frame, cx, cy, zoom) in recording px."""
    def f(t):
        if t <= keys[0][0]:
            return keys[0][1:]
        for a, b in zip(keys, keys[1:]):
            if t <= b[0]:
                k = ease((t - a[0]) / max(1e-6, b[0] - a[0]))
                return tuple(a[i] + (b[i] - a[i]) * k for i in (1, 2, 3))
        return keys[-1][1:]
    return f


# ----- Camera / footage ----------------------------------------------------------------------------------------------

VIEW_Y = (112, 1240)   # The 3D View's drawing area in the recordings (below the headers, above the asset shelf).


def footage(name, s, cx, cy, z, w, h, clamp_y=VIEW_Y):
    """A w x h view of recording ``name`` at frame ``s``: centred on (cx, cy), ``z`` x the 1:1 pixel scale."""
    img = src_frame(name, s)
    H, W = img.shape[:2]
    sw, sh = w / z, h / z
    sw, sh = min(sw, W), min(sh, H, clamp_y[1] - clamp_y[0]) if clamp_y != (0, H) else min(sh, H)
    sw = min(sw, sh * w / h)
    x0 = max(0.0, min(W - sw, cx - sw / 2))
    y0 = max(clamp_y[0], min(min(H, clamp_y[1]) - sh, cy - sh / 2))
    y0 = max(0.0, y0)
    M = np.float32([[w / sw, 0, -x0 * w / sw], [0, h / sh, -y0 * h / sh]])
    out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_AREA if w / sw < 1 else cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)
    return out, (x0, y0, w / sw)


def to_view(p, tr):
    x0, y0, k = tr
    return (p[0] - x0) * k, (p[1] - y0) * k


# ----- Overlays ------------------------------------------------------------------------------------------------------

def cursor_sprite(scale=1.0):
    k = 4
    pts = [(0, 0), (0, 17), (4.2, 13.2), (7, 19.6), (9.7, 18.5), (7, 12.3), (12.4, 12.3)]
    s = 2.0 * scale
    w, h = int(16 * s * k), int(23 * s * k)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(2 * k + x * s * k, 2 * k + y * s * k) for x, y in pts], fill=(255, 255, 255, 255),
              outline=(16, 16, 20, 255), width=int(1.5 * k))
    img = img.resize((w // k, h // k), Image.Resampling.LANCZOS)
    sh = img.getchannel("A").filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.55))
    out = Image.new("RGBA", (img.width + 10, img.height + 10), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", sh.size, (0, 0, 0, 255)), (3, 6), sh)
    out.alpha_composite(img, (0, 0))
    return out


CURSOR = {1.0: cursor_sprite(1.0), 0.85: cursor_sprite(0.85)}


@lru_cache(maxsize=256)
def text_img(text, size, style, color, tracking=0.0):
    f = vf(size, style)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    sp = size * tracking
    w = int(sum(d.textlength(c, font=f) for c in text) + sp * max(0, len(text) - 1)) + 12
    img = Image.new("RGBA", (w, int(size * 1.45)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    x = 0
    for c in (text if tracking else [text]):
        dd.text((x, 0), c, font=f, fill=color)
        x += dd.textlength(c, font=f) + sp
    sh = img.getchannel("A").filter(ImageFilter.GaussianBlur(max(2, size // 18))).point(lambda v: int(v * 0.6))
    out = Image.new("RGBA", (img.width + 16, img.height + 16), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", sh.size, (0, 0, 0, 255)), (4, 8), sh)
    out.alpha_composite(img, (2, 2))
    return out


def put_text(canvas, text, size, x, y, age, style="Semibold Display", color=TEXT, anim="pop", anchor="l", tracking=0.0, life=None,
             max_w=None):
    """Kinetic text: ``age`` = frames since it appeared (``life``: frames until it leaves). Shrinks to fit the frame."""
    if age < 0 or (life is not None and age > life + 8):
        return
    max_w = max_w or canvas.width - 120
    w0 = text_img(text, int(size), style, color, tracking).width
    if w0 > max_w:
        size = size * max_w / w0
    img = text_img(text, int(size), style, color, tracking)
    a = 1.0
    dy = 0.0
    sc = 1.0
    if anim == "slam":
        k = ease_out(age / 7)
        sc = 1.35 - 0.35 * k
        a = min(1.0, age / 4)
    elif anim == "pop":
        k = ease_out(age / 9)
        dy = (1 - k) * size * 0.45
        a = k
    elif anim == "wipe":
        k = ease_out(age / 12)
        img = img.copy()
        cut = int(img.width * k)
        m = Image.new("L", img.size, 0)
        ImageDraw.Draw(m).rectangle((0, 0, cut, img.height), fill=255)
        img.putalpha(Image.fromarray(np.minimum(np.asarray(img.getchannel("A")), np.asarray(m))))
    if life is not None and age > life:
        k = (age - life) / 8
        a *= 1 - k
        dy -= k * size * 0.3
    if sc != 1.0:
        img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.Resampling.BILINEAR)
    if a < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    px = x - (img.width / 2 if anchor == "c" else (img.width if anchor == "r" else 0))
    canvas.alpha_composite(img, (int(px), int(y + dy - (img.height - text_img(text, int(size), style, color, tracking).height) / 2)))


def chip(canvas, text, x, y, age, anchor="l"):
    if age < 0:
        return
    f = vf(26, "Bold Text")
    d = ImageDraw.Draw(canvas)
    w = d.textlength(text, font=f) + 44
    k = ease_out(age / 8)
    if anchor == "c":
        x -= w / 2
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((x, y, x + w * k, y + 48), radius=24, fill=ACCENT + (int(235 * k),))
    canvas.alpha_composite(layer)
    if k > 0.6:
        ImageDraw.Draw(canvas).text((x + 22, y + 24), text, font=f, fill=(24, 14, 4), anchor="lm")


def keycap(canvas, label, x, y, lit):
    f = vf(28, "Semibold Text")
    d = ImageDraw.Draw(canvas)
    w = d.textlength(label, font=f) + 56
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    off = 4 if lit else 0
    ld.rounded_rectangle((x, y + 8, x + w, y + 64), radius=14, fill=(0, 0, 0, 150))
    ld.rounded_rectangle((x, y + off, x + w, y + 56 + off), radius=14,
                         fill=(ACCENT + (240,)) if lit else (40, 42, 50, 220), outline=(255, 255, 255, 60), width=2)
    canvas.alpha_composite(layer)
    ImageDraw.Draw(canvas).text((x + w / 2, y + 28 + off), label, font=f, fill=(24, 14, 4) if lit else TEXT, anchor="mm")


def scrim(canvas, box, a=150):
    x0, y0, x1, y1 = box
    m = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(m).rectangle(box, fill=a)
    m = m.filter(ImageFilter.GaussianBlur(60))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", canvas.size, (6, 6, 9)).split(), m)))


# ----- Shots ---------------------------------------------------------------------------------------------------------
# Each shot: (start, end, seq, time map, camera, extra) -- frames in the timeline, recording px for the camera.

S = SEQ
sc_open = S["sculpt"].open_pos(0)
sc_open2 = S["sculpt"].open_pos(1)
HEAD = S["sculpt"].head

SHOTS = [
    # COLD 0-120: hunting through the shelf (full Blender UI).
    dict(a=0, b=120, seq="pain", t=pw((0, 6), (120, 140)), cam=cam((0, 1280, 700, 0.74), (120, 1280, 820, 0.8)), grade="cold"),
    # TITLE 120-240: the wheel pops open (slow motion), title.
    dict(a=120, b=240, seq="sculpt", t=pw((120, 10), (150, 18), (240, 40)), cam=cam((120, sc_open[0], sc_open[1], 1.0), (240, sc_open[0], sc_open[1], 1.08)), comp="right"),
    # SCULPT 240-540.
    dict(a=240, b=355, seq="sculpt", t=pw((240, 40), (355, 155)), cam=cam((240, HEAD[0], HEAD[1], 0.98), (300, HEAD[0] - 120, HEAD[1] - 140, 1.08), (355, HEAD[0] - 60, HEAD[1] - 60, 1.04))),
    dict(a=355, b=430, seq="sculpt", t=pw((355, 155), (430, 230)), cam=cam((355, sc_open2[0], sc_open2[1], 1.0), (430, sc_open2[0], sc_open2[1], 1.08)), comp="right"),
    dict(a=430, b=540, seq="sculpt", t=pw((430, 230), (540, 306)), cam=cam((430, HEAD[0], HEAD[1], 1.0), (540, HEAD[0] - 80, HEAD[1], 1.08))),
    # PAINT 540-720 (speed ramps: real time on the picks, fast through the strokes).
    dict(a=540, b=720, seq="texture", t=pw((540, 8), (572, 44), (612, 135), (644, 176), (684, 254), (720, 330)),
         cam=cam((540, 1350, 640, 1.0), (620, 1380, 650, 1.06), (720, 1360, 680, 1.02))),
    # DRAW 720-900.
    dict(a=720, b=900, seq="gpencil", t=pw((720, 8), (752, 62), (800, 160), (836, 224), (900, 318)),
         cam=cam((720, 1290, 690, 0.99), (900, 1290, 690, 1.05))),
    # WEIGHT 900-1005, then the break (a frozen, dimmed frame) to 1020.
    dict(a=900, b=1005, seq="weight", t=pw((900, 8), (930, 44), (965, 124), (1005, 207)),
         cam=cam((900, 1360, 650, 1.0), (1005, 1360, 650, 1.07))),
    dict(a=1005, b=1020, seq="weight", t=pw((1005, 206), (1020, 206)), cam=cam((1005, 1360, 650, 1.07), (1020, 1360, 650, 1.1)), grade="break"),
    # DROP 1020-1200: themes, double ring, the 2x2 grid.
    dict(a=1020, b=1080, seq="themes", t=pw((1020, 12), (1080, 100)), cam=cam((1020, 1298, 654, 1.08), (1080, 1298, 654, 1.0)), comp="right"),
    dict(a=1080, b=1140, seq="double", t=pw((1080, 4), (1140, 64)), cam=cam((1080, 1290, 671, 1.0), (1140, 1290, 671, 0.96)), comp="right"),
    dict(a=1140, b=1200, kind="grid"),
    # FILL 1200-1260: stutter montage.
    dict(a=1200, b=1260, kind="montage"),
    # END 1260-1380.
    dict(a=1260, b=1380, kind="end"),
]

CAPTIONS = [  # (start, end, kicker, line) -- the lower-third of a scene
    (246, 540, "SCULPT", "Pick a brush. Keep sculpting."),
    (546, 720, "TEXTURE PAINT", "Colors right on the wheel"),
    (726, 900, "GREASE PENCIL", "Swap pens and colors mid-stroke"),
    (906, 1004, "WEIGHT PAINT", "Any weight, one gesture"),
]
STATEMENTS = [  # (start, end, text, style)
    (8, 52, "Hunting for brushes?", "pop"),
    (56, 92, "Again?", "slam"),
    (94, 120, "There's a faster way.", "wipe"),
    (362, 425, "Drag the centre: size & strength", "pop"),
    (1024, 1078, "10 themes", "slam"),
    (1084, 1138, "Double ring: 34 brushes", "slam"),
    (1144, 1198, "Every mode", "slam"),
]
CUTS = [540, 720, 900]                       # whip pans between scenes
HITS = [120, 1020, 1260]                     # flash + punch-in
PUNCH = [120, 240, 540, 720, 900, 1020, 1080, 1140, 1260]


def shot_at(f):
    for s in SHOTS:
        if s["a"] <= f < s["b"]:
            return s
    return SHOTS[-1]


def render_shot(s, f, w, h, ctx):
    kind = s.get("kind")
    if kind == "grid":
        return grid(f, w, h, ctx)
    if kind == "montage":
        return montage(f, w, h, ctx)
    if kind == "end":
        return end_card(f, w, h)
    src = s["t"](f)
    cx, cy, z = s["cam"](f)
    for hf in PUNCH:
        if 0 <= f - hf < 12:
            z *= 1 + 0.05 * (1 - (f - hf) / 12) ** 2
    comp = s.get("comp")
    if comp == "right":          # Text on the left (16:9) / on top (square): the subject goes to the other side.
        if w > h * 1.3:
            cx -= w * 0.21 / z
        elif w == h:
            cy -= h * 0.1 / z
    img, tr = footage(s["seq"], src, cx, cy, z, w, h, (0, 1361) if s["seq"] == "pain" else VIEW_Y)
    if s.get("grade") == "cold":
        g = img.mean(axis=2, keepdims=True)
        img = (img * 0.55 + g * 0.45) * 0.82
        img = np.clip(img, 0, 255).astype(np.uint8)
    elif s.get("grade") == "break":
        img = (img * 0.45).astype(np.uint8)
    ctx["pointer"] = (s["seq"], src, tr)
    return img


def grid(f, w, h, ctx):
    t = f - 1140
    cells = [("sculpt", 48 + t * 1.6, HEAD), ("texture", 49 + t * 1.5, S["texture"].head), ("gpencil", 67 + t * 1.6, (1290, 690)),
             ("weight", 44 + t * 1.8, S["weight"].head)]
    gap = 8
    cw, ch = (w - gap) // 2, (h - gap) // 2
    out = np.full((h, w, 3), 12, np.uint8)
    for i, (name, src, (cx, cy)) in enumerate(cells):
        k = ease_out((t - i * 2) / 10)
        img, _ = footage(name, src, cx, cy, 0.62 * min(cw / 960, ch / 540) * 1.6, cw, ch)
        x, y = (i % 2) * (cw + gap), (i // 2) * (ch + gap)
        out[y:y + ch, x:x + cw] = (img * max(0.0, k)).astype(np.uint8)
    ctx["pointer"] = None
    return out


MONTAGE = [("sculpt", 30, sc_open, 1.1), ("texture", 25, S["texture"].open_pos(0), 1.08), ("gpencil", 30, S["gpencil"].open_pos(0), 1.1),
           ("weight", 26, S["weight"].open_pos(0), 1.1), ("themes", 60, (1298, 654), 1.1), ("sculpt", 190, sc_open2, 1.1),
           ("texture", 150, S["texture"].open_pos(1), 1.1), ("double", 40, (1290, 671), 1.0)]


def montage(f, w, h, ctx):
    t = f - 1200
    i = min(len(MONTAGE) - 1, int(t / 7.5))
    name, src, (cx, cy), z = MONTAGE[i]
    k = (t - i * 7.5) / 7.5
    img, tr = footage(name, src + k * 4, cx, cy, z * (1.0 + 0.04 * k), w, h)
    ctx["pointer"] = (name, src + k * 4, tr)
    return img


# ----- End card -------------------------------------------------------------------------------------------------------

def background(w, h, spot=None):
    y = np.linspace(0, 1, h)[:, None, None]
    img = (np.array(BG_TOP) * (1 - y) + np.array(BG_BOTTOM) * y) * np.ones((h, w, 3))
    if spot:
        sx, sy, r = spot
        yy, xx = np.mgrid[0:h, 0:w]
        g = np.exp(-(((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * (r * 0.55) ** 2)))[..., None]
        img = img + g * np.array(ACCENT) * 0.22
    return np.clip(img, 0, 255).astype(np.uint8)


@lru_cache(maxsize=8)
def wheel_cut(name, frame, cx, cy, r):
    img = raw(name, frame)
    half = int(r + 30)
    crop = Image.fromarray(img[int(cy) - half:int(cy) + half, int(cx) - half:int(cx) + half]).convert("RGBA")
    k = 4
    m = Image.new("L", (crop.width * k, crop.height * k), 0)
    ImageDraw.Draw(m).ellipse(((half - r) * k, (half - r) * k, (half + r) * k, (half + r) * k), fill=255)
    crop.putalpha(m.resize(crop.size, Image.Resampling.LANCZOS))
    return crop


def place(canvas, sprite, cx, cy, d, r):
    s = d / (2 * r)
    sp = sprite.resize((int(sprite.width * s), int(sprite.height * s)), Image.Resampling.LANCZOS)
    sh = sp.getchannel("A").filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.7))
    canvas.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", sp.size, (0, 0, 0)).split(), sh)),
                           (int(cx - sp.width / 2), int(cy - sp.height / 2 + 14)))
    canvas.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))


R_SC, R_TEX, R_W = 195 * UI, 210 * UI, 170 * UI


def end_card(f, w, h):
    t = f - 1260
    vertical = h > w
    square = w == h
    if vertical:
        wc = (w * 0.5, h * 0.36)
    elif square:
        wc = (w * 0.5, h * 0.34)
    else:
        wc = (w * 0.68, h * 0.48)
    canvas = Image.fromarray(background(w, h, (wc[0], wc[1], w * 0.5))).convert("RGBA")
    drift = math.sin(t / 30) * 6
    k = ease_out(t / 14)
    base = (h * 0.44 if not vertical else w * 0.6) * (0.9 + 0.1 * k)
    tex = wheel_cut("texture", 30, *S["texture"].open_pos(0), R_TEX)
    wgt = wheel_cut("weight", 30, *S["weight"].open_pos(0), R_W)
    scu = wheel_cut("sculpt", 32, *sc_open, R_SC)
    place(canvas, tex, wc[0] + base * 0.62, wc[1] - base * 0.42 + drift, base * 0.66, R_TEX)
    place(canvas, wgt, wc[0] + base * 0.66, wc[1] + base * 0.5 - drift, base * 0.56, R_W)
    place(canvas, scu, wc[0], wc[1] + drift * 0.5, base, R_SC)
    if vertical:
        tx, ty, anchor = w / 2, h * 0.66, "c"
    elif square:
        tx, ty, anchor = w / 2, h * 0.68, "c"
    else:
        tx, ty, anchor = w * 0.07, h * 0.3, "l"
    size = 92 if not square else 78
    put_text(canvas, "Sculpt-Paint", size, tx, ty, t - 4, "Bold Display", TEXT, "slam", anchor)
    put_text(canvas, "Wheel 2", size, tx, ty + size * 1.05, t - 7, "Bold Display", ACCENT, "slam", anchor)
    put_text(canvas, "Your brushes, one keypress away.", 34 if not square else 30, tx, ty + size * 2.3, t - 14, "Regular", MUTED, "pop", anchor)
    chip(canvas, "AVAILABLE ON SUPERHIVE", tx, ty + size * 2.3 + 70, t - 22, anchor)
    return np.asarray(canvas.convert("RGB"))


# ----- Frame composition ---------------------------------------------------------------------------------------------

def whip(f):
    for c in CUTS:
        if c - 6 <= f < c + 6:
            return c, (f - (c - 6)) / 12
    return None


def compose(f, fmt, ctx):
    W, H = SIZES[fmt]
    stage = (0, 360, 1080, 1200) if fmt == "9x16" else (0, 0, W, H)
    sx, sy, sw, sh = stage
    wp = whip(f)
    if wp:
        c, k = wp
        a = render_shot(shot_at(c - 1), f, sw, sh, ctx)
        ptr_a = ctx.get("pointer")
        b = render_shot(shot_at(c), f, sw, sh, ctx)
        off = int(ease(k) * sw)
        img = np.zeros_like(a)
        img[:, :sw - off] = a[:, off:]
        img[:, sw - off:] = b[:, :off]
        blur = int(4 + 90 * math.sin(math.pi * k))
        img = cv2.blur(img, (blur, 1))
        ctx["pointer"] = None
        ctx["whoosh"].add(c - 6)
    else:
        img = render_shot(shot_at(f), f, sw, sh, ctx)
    s = shot_at(f)
    # RGB split on the big hits.
    for hf in (1020, 1260):
        if 0 <= f - hf < 8:
            d = int(14 * (1 - (f - hf) / 8))
            img = img.copy()
            img[:, :, 0] = np.roll(img[:, :, 0], d, axis=1)
            img[:, :, 2] = np.roll(img[:, :, 2], -d, axis=1)

    if fmt == "9x16":
        canvas = Image.fromarray(background(W, H, (W / 2, 1000, 900))).convert("RGBA")
        canvas.paste(Image.fromarray(img), (sx, sy))
    else:
        canvas = Image.fromarray(img).convert("RGBA")

    # Pointer, ripples, keycap.
    p = ctx.get("pointer")
    if p and s.get("kind") != "end":
        name, src, tr = p
        x, y, down, space = SEQ[name].ptr(src)
        vx, vy = to_view((x, y), tr)
        vx, vy = vx + sx, vy + sy
        sq = SEQ[name]
        i = int(src)
        if down and i > 0 and not sq.frames[i - 1]["down"]:
            ctx["clicks"].append((f, vx, vy))
        for cf, rx, ry in ctx["clicks"]:
            age = f - cf
            if 0 <= age < 14:
                layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
                rr = 10 + 40 * ease_out(age / 14)
                ImageDraw.Draw(layer).ellipse((rx - rr, ry - rr, rx + rr, ry + rr), outline=ACCENT + (int(230 * (1 - age / 14)),), width=5)
                canvas.alpha_composite(layer)
        if sx <= vx < sx + sw and sy <= vy < sy + sh:
            cur = CURSOR[0.85 if down else 1.0]
            canvas.alpha_composite(cur, (int(vx) - 3, int(vy) - 3))
        if s.get("grade") != "cold" and 120 <= f < 1140:
            if fmt == "16x9":
                keycap(canvas, "Space", W - 210, H - 120, space)
            elif fmt == "1x1":
                keycap(canvas, "Space", W - 190, H - 110, space)
            else:
                keycap(canvas, "Space", W / 2 - 75, 1770, space)

    # Type.
    if fmt == "16x9":
        big, big_x, big_y, big_anchor = 84, 110, 420, "l"
        cap_x, cap_y, cap_anchor = 110, H - 210, "l"
    elif fmt == "1x1":
        big, big_x, big_y, big_anchor = 66, W / 2, 110, "c"
        cap_x, cap_y, cap_anchor = W / 2, 60, "c"
    else:
        big, big_x, big_y, big_anchor = 80, W / 2, 190, "c"
        cap_x, cap_y, cap_anchor = W / 2, 150, "c"
    for a, b, text, style in STATEMENTS:
        if a <= f < b + 8:
            if fmt == "16x9":
                scrim(canvas, (0, big_y - 40, 1100, big_y + big + 60), 120)
            put_text(canvas, text, big, big_x, big_y, f - a, "Bold Display", TEXT, style, big_anchor, life=b - a,
                     max_w=860 if fmt == "16x9" else None)
    if 120 <= f < 240:
        t = f - 126
        if fmt == "16x9":
            scrim(canvas, (0, 300, 1000, 760), 140)
            put_text(canvas, "Sculpt-Paint Wheel 2", 96, 110, 360, t, "Bold Display", TEXT, "slam")
            put_text(canvas, "Your brushes, one keypress away.", 38, 112, 480, t - 18, "Regular", MUTED, "pop")
            chip(canvas, "HOLD SPACE", 112, 560, t - 28)
        else:
            ty = 120 if fmt == "1x1" else 150
            put_text(canvas, "Sculpt-Paint Wheel 2", 74 if fmt == "1x1" else 84, W / 2, ty, t, "Bold Display", TEXT, "slam", "c")
            put_text(canvas, "Your brushes, one keypress away.", 32, W / 2, ty + 100, t - 18, "Regular", MUTED, "pop", "c")
            if fmt == "9x16":
                chip(canvas, "HOLD SPACE", W / 2, 1620, t - 28, "c")
    stating = any(a <= f < b + 8 for a, b, _t, _s in STATEMENTS)
    for a, b, kicker, line in CAPTIONS:
        if a <= f < b and not (stating and fmt == "1x1"):
            t = f - a
            if fmt == "16x9":
                scrim(canvas, (0, cap_y - 30, 900, cap_y + 140), 130)
                chip(canvas, kicker, cap_x, cap_y, t)
                put_text(canvas, line, 44, cap_x, cap_y + 64, t - 6, "Semibold Display", TEXT, "pop", life=b - a - 10)
            elif fmt == "1x1":
                chip(canvas, kicker, cap_x, cap_y, t, "c")
                put_text(canvas, line, 40, cap_x, cap_y + 60, t - 6, "Semibold Display", TEXT, "pop", "c", life=b - a - 10)
            else:
                if not stating:
                    chip(canvas, kicker, cap_x, 170, t, "c")
                put_text(canvas, line, 50, cap_x, 1600, t - 6, "Semibold Display", TEXT, "pop", "c", life=b - a - 10)

    out = np.asarray(canvas.convert("RGB")).astype(np.float32)
    # Flashes on the hits, vignette, the fade at the end.
    for hf in HITS:
        if 0 <= f - hf < 10:
            a = 0.85 * (1 - (f - hf) / 10) ** 2
            out = out * (1 - a) + 255 * a
    if f >= 1344:
        out *= max(0.0, 1 - (f - 1344) / 36)
    yy, xx = np.ogrid[0:H, 0:W]
    return np.clip(out, 0, 255).astype(np.uint8)


_VIG = {}


def vignette(img):
    H, W = img.shape[:2]
    if (W, H) not in _VIG:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _VIG[(W, H)] = (1 - 0.16 * np.clip(d - 0.55, 0, 1) ** 1.5)[..., None].astype(np.float32)
    return np.clip(img * _VIG[(W, H)], 0, 255).astype(np.uint8)


# ----- Audio ---------------------------------------------------------------------------------------------------------

def make_audio(clicks, whooshes, path):
    kit = os.environ.get("MUSIC_KIT", r"X:\B3D\@jfranmatheu\B3D-MySpace\marketing\flexspace\superhive\src\make_music.py")
    spec = importlib.util.spec_from_file_location("make_music", kit)
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    import soundfile as sf
    music, sr = sf.read(os.path.join(AUDIO, "promo_music.wav"), dtype="float32")
    mix = music.copy()

    def add(t, sig, gain):
        i = int(t * sr)
        s2 = sig if sig.ndim == 2 else np.stack([sig, sig], axis=1)
        e = min(len(mix), i + len(s2))
        if e > i >= 0:
            mix[i:e] += s2[:e - i] * gain

    for f in sorted(set(clicks)):
        add(f / FPS, M.click(2400.0, 0.01), 10 ** (-17 / 20))
    for f in sorted(set(whooshes)):
        add(f / FPS, M.whoosh(0.4), 10 ** (-9 / 20))
    tmp = os.path.join(OUT, "_mix.wav")
    sf.write(tmp, mix, sr, subtype="PCM_24")
    # Two-pass loudness normalisation (a single pass overshoots once the clicks are in): measure, then apply.
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={input_i}:measured_TP={input_tp}:"
          "measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}").format(**m)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", tmp, "-af", af, "-ar", "48000", "-t", str(TOTAL / FPS), path],
                   check=True)
    os.remove(tmp)


# ----- Render ----------------------------------------------------------------------------------------------------------

def render(fmt):
    W, H = SIZES[fmt]
    ctx = {"clicks": [], "whoosh": set()}
    if STILLS:
        for s in STILLS:
            f = int(s * FPS)
            ctx2 = {"clicks": [], "whoosh": set()}
            Image.fromarray(vignette(compose(f, fmt, ctx2))).save(os.path.join(OUT, f"still_{fmt}_{s:05.2f}.png"))
        print("stills", fmt)
        return
    video = os.path.join(OUT, f"_video_{fmt}.mp4")
    p = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                          "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                          "-movflags", "+faststart", video], stdin=subprocess.PIPE)
    clicks_seen = []
    for f in range(TOTAL):
        before = len(ctx["clicks"])
        frame = vignette(compose(f, fmt, ctx))
        clicks_seen += [c[0] for c in ctx["clicks"][before:]]
        ctx["clicks"] = [c for c in ctx["clicks"] if f - c[0] < 14]
        p.stdin.write(frame.tobytes())
        if f % 150 == 0:
            print(f"  {fmt} frame {f}/{TOTAL}", flush=True)
    p.stdin.close()
    p.wait()
    audio = os.path.join(OUT, "_audio.wav")
    if fmt == "16x9" or not os.path.exists(audio):
        make_audio(clicks_seen, sorted(ctx["whoosh"]), audio)
    final = os.path.join(OUT, f"sculpt-paint-wheel-2_{fmt}.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", video, "-i", audio, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "320k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(video)
    print("wrote", final, f"{os.path.getsize(final) / 1e6:.1f} MB")


for fmt in (("16x9", "1x1", "9x16") if FMT == "all" else (FMT,)):
    render(fmt)
