"""Generate the bundled custom-button icons (spwheel/assets/images/custom_buttons/*.png).

All icons share one style so they read as a set in the pie menu: a 128 px transparent canvas, the same
content box, one stroke weight with round caps/joins, and a single light colour (solid fills only where the
metaphor needs them, e.g. the filled half of "invert" or the hard disc of "sharpen").

Usage:  python store/tools/custom_button_icons.py [out_dir]
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SIZE = 128                # Output size.
SS = 4                    # Supersampling factor.
S = SIZE * SS             # Working canvas (512).
C = S / 2                 # Centre.
W = 9 * SS                # Stroke width (9 px at 128).
LO, HI = 18 * SS, 110 * SS  # Content box.
INK = (236, 238, 242, 255)

OUT_DIR = Path(__file__).resolve().parents[2] / "spwheel" / "assets" / "images" / "custom_buttons"


# ---------------------------------------------------------------------------
# Drawing helpers (all coordinates on the 512 px working canvas).
# ---------------------------------------------------------------------------

def new_layer() -> Image.Image:
    return Image.new("L", (S, S), 0)


def stroke(layer: Image.Image, pts, closed: bool = False, width: float = W) -> None:
    """Polyline with round caps and joins."""
    d = ImageDraw.Draw(layer)
    pts = [tuple(p) for p in pts]
    if closed:
        pts = pts + [pts[0]]
    d.line(pts, fill=255, width=int(width), joint="curve")
    r = width / 2
    for x, y in pts:
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)


def fill_poly(layer: Image.Image, pts) -> None:
    ImageDraw.Draw(layer).polygon([tuple(p) for p in pts], fill=255)


def circle(layer: Image.Image, cx, cy, r, fill: bool = False, width: float = W) -> None:
    d = ImageDraw.Draw(layer)
    if fill:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    else:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=255, width=int(width))


def rrect(layer: Image.Image, box, radius, fill: bool = False, width: float = W) -> None:
    d = ImageDraw.Draw(layer)
    if fill:
        d.rounded_rectangle(box, radius=radius, fill=255)
    else:
        d.rounded_rectangle(box, radius=radius, outline=255, width=int(width))


def bezier(p0, p1, p2, p3, n: int = 64):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((
            u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
        ))
    return out


def catmull_rom(points, n: int = 24):
    """Smooth curve through ``points``."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                       + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)
                for k in range(2)
            ))
    out.append(tuple(points[-1]))
    return out


def subtract(layer: Image.Image, cut: Image.Image) -> Image.Image:
    return ImageChops.subtract(layer, cut)


def intersect(a: Image.Image, b: Image.Image) -> Image.Image:
    return ImageChops.multiply(a, b)


def union(*layers: Image.Image) -> Image.Image:
    out = layers[0]
    for layer in layers[1:]:
        out = ImageChops.lighter(out, layer)
    return out


def finish(alpha: Image.Image) -> Image.Image:
    alpha = alpha.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    img = Image.new("RGBA", (SIZE, SIZE), INK)
    img.putalpha(alpha)
    return img


# ---------------------------------------------------------------------------
# Icons.
# ---------------------------------------------------------------------------

BOX = (LO + W / 2, LO + W / 2, HI - W / 2, HI - W / 2)  # Square frame inside the content box.
BOX_R = 22 * SS


def icon_brush():
    """Paintbrush: drawn upright (tip down) on its own layer, then tilted 45 deg so the tip points down-left."""
    a = new_layer()
    x = C
    u = SS  # 1 px at 128.
    # Handle: long, slightly tapered, rounded at the top.
    top, bottom = 10 * u, 56 * u
    fill_poly(a, [(x - 4.0 * u, top), (x + 4.0 * u, top), (x + 6.0 * u, bottom), (x - 6.0 * u, bottom)])
    circle(a, x, top, 4.0 * u, fill=True)
    # Ferrule: in line with the handle, a bit wider, with a crimp line.
    f0, f1 = 59 * u, 74 * u
    rrect(a, (x - 9 * u, f0, x + 9 * u, f1), 2 * u, fill=True)
    crimp = new_layer()
    ImageDraw.Draw(crimp).rectangle((x - 10 * u, 65.5 * u, x + 10 * u, 67.5 * u), fill=255)
    a = subtract(a, crimp)
    # Bristles: round belly ending in a tip flicked to one side.
    b0 = 76.5 * u
    tip = (x - 5 * u, 120 * u)
    right = bezier((x + 9 * u, b0), (x + 14 * u, b0 + 16 * u), (x + 12 * u, b0 + 34 * u), tip)
    left = bezier(tip, (x - 10 * u, b0 + 32 * u), (x - 14 * u, b0 + 14 * u), (x - 9 * u, b0))
    fill_poly(a, right + left)
    return a.rotate(-45, resample=Image.Resampling.BICUBIC, center=(C, C))


def icon_falloff():
    a = new_layer()
    x0, x1 = LO + 2 * SS, HI - 2 * SS
    top, bottom = LO + 10 * SS, HI - 12 * SS
    sigma = (x1 - x0) * 0.16
    pts = []
    for i in range(121):
        x = x0 + (x1 - x0) * i / 120
        y = bottom - (bottom - top) * math.exp(-((x - C) ** 2) / (2 * sigma * sigma))
        pts.append((x, y))
    stroke(a, pts)
    return a


def icon_falloff_2():
    a = new_layer()
    p0 = (LO + 8 * SS, HI - 12 * SS)
    p3 = (HI - 8 * SS, LO + 12 * SS)
    stroke(a, bezier(p0, (C + 4 * SS, p0[1]), (C - 4 * SS, p3[1]), p3))
    for x, y in (p0, p3):
        circle(a, x, y, W * 1.15, fill=True)
    return a


def icon_grid():
    """A 3x3 grid of lines, no outer frame."""
    a = new_layer()
    x0, y0, x1, y1 = BOX
    for k in (1, 3, 5):
        t = x0 + (x1 - x0) * k / 6
        stroke(a, [(t, y0), (t, y1)])
        t = y0 + (y1 - y0) * k / 6
        stroke(a, [(x0, t), (x1, t)])
    return a


def icon_mask():
    """Auto-masking: a domino mask."""
    a = new_layer()
    x0, x1 = LO, HI
    y0, y1 = C - 26 * SS, C + 26 * SS
    body = new_layer()
    rrect(body, (x0, y0, x1, y1), 26 * SS, fill=True)
    # Nose notch.
    notch = new_layer()
    circle(notch, C, y1 + 4 * SS, 16 * SS, fill=True)
    body = subtract(body, notch)
    # Eye holes.
    eyes = new_layer()
    for ex in (C - 22 * SS, C + 22 * SS):
        ImageDraw.Draw(eyes).ellipse((ex - 14 * SS, C - 10 * SS, ex + 14 * SS, C + 8 * SS), fill=255)
    return subtract(body, eyes)


def icon_mask_clear():
    a = new_layer()
    rrect(a, BOX, BOX_R)
    x0, y0, x1, y1 = BOX
    # Slash, with a transparent gap around it so it reads over the frame.
    gap = new_layer()
    stroke(gap, [(x0 - 6 * SS, y1 + 6 * SS), (x1 + 6 * SS, y0 - 6 * SS)], width=W * 2.6)
    a = subtract(a, gap)
    stroke(a, [(x0 + 4 * SS, y1 - 4 * SS), (x1 - 4 * SS, y0 + 4 * SS)])
    return a


def icon_mask_invert():
    a = new_layer()
    rrect(a, BOX, BOX_R)
    inside = new_layer()
    rrect(inside, BOX, BOX_R, fill=True)
    x0, y0, x1, y1 = BOX
    half = new_layer()
    fill_poly(half, [(x1, y0), (x1, y1), (x0, y1)])
    return union(a, intersect(inside, half))


def icon_mask_sharp():
    a = new_layer()
    circle(a, C, C, (HI - LO) / 2 - W / 2)
    circle(a, C, C, 20 * SS, fill=True)
    return a


def icon_mask_smooth():
    """Like the sharp one, but light: a thin ring and a soft, translucent fade from the centre out to it."""
    a = new_layer()
    thin = W * 0.5
    r_ring = (HI - LO) / 2 - thin / 2
    circle(a, C, C, r_ring, width=thin)
    soft = new_layer()
    px = soft.load()
    r_end = r_ring - thin / 2 - 2 * SS  # Fade out just inside the ring.
    peak = 0.8                           # Translucent even at the centre.
    for y in range(int(C - r_end) - 1, int(C + r_end) + 2):
        for x in range(int(C - r_end) - 1, int(C + r_end) + 2):
            t = min(math.hypot(x + 0.5 - C, y + 0.5 - C) / r_end, 1.0)
            px[x, y] = int(255 * peak * (1.0 - t) ** 2 + 0.5)  # Soft, gradual falloff.
    return union(a, soft)


def icon_mirror():
    a = new_layer()
    top, bottom = LO + 6 * SS, HI - 6 * SS
    gap = 9 * SS
    fill_poly(a, [(LO + 2 * SS, top), (C - gap, top), (C - gap, bottom)])
    stroke(a, [(LO + 2 * SS, top), (C - gap, top), (C - gap, bottom)], closed=True)
    stroke(a, [(HI - 2 * SS, top), (C + gap, top), (C + gap, bottom)], closed=True)
    return a


def icon_options():
    """Settings: three sliders."""
    a = new_layer()
    x0, x1 = LO + 4 * SS, HI - 4 * SS
    knob_r = 10 * SS
    for y, t in ((LO + 16 * SS, 0.68), (C, 0.3), (HI - 16 * SS, 0.56)):
        kx = x0 + (x1 - x0) * t
        stroke(a, [(x0, y), (x1, y)], width=W * 0.75)
        cut = new_layer()
        circle(cut, kx, y, knob_r + W * 0.9, fill=True)
        a = subtract(a, cut)
        circle(a, kx, y, knob_r + W / 2, width=W)
    return a


def icon_stroke():
    a = new_layer()
    pts = [
        (LO + 10 * SS, LO + 30 * SS),
        (LO + 34 * SS, LO + 8 * SS),
        (C + 6 * SS, LO + 22 * SS),
        (C - 18 * SS, C + 6 * SS),
        (C - 8 * SS, HI - 22 * SS),
        (C + 26 * SS, C + 4 * SS),
        (HI - 8 * SS, HI - 8 * SS),
    ]
    stroke(a, catmull_rom(pts), width=W * 1.15)
    return a


def icon_texture():
    a = new_layer()
    rrect(a, BOX, BOX_R)
    inside = new_layer()
    rrect(inside, BOX, BOX_R, fill=True)
    checker = new_layer()
    x0, y0, x1, y1 = BOX
    n = 4
    cw = (x1 - x0) / n
    d = ImageDraw.Draw(checker)
    for i in range(n):
        for j in range(n):
            if (i + j) % 2 == 0:
                d.rectangle((x0 + i * cw, y0 + j * cw, x0 + (i + 1) * cw, y0 + (j + 1) * cw), fill=255)
    return union(a, intersect(inside, checker))


def icon_voxels():
    """Remesh / voxels: an isometric cube."""
    a = new_layer()
    r = (HI - LO) / 2 - W / 2
    hexa = [(C + r * math.cos(math.radians(90 + 60 * k)), C - r * math.sin(math.radians(90 + 60 * k))) for k in range(6)]
    stroke(a, hexa, closed=True)
    # Inner Y edges: centre to the top-left, top-right... (vertices 0 = top).
    stroke(a, [(C, C), hexa[3]])   # Bottom.
    stroke(a, [(C, C), hexa[1]])   # Upper left.
    stroke(a, [(C, C), hexa[5]])   # Upper right.
    # Top face, filled.
    fill_poly(a, [hexa[0], hexa[1], (C, C), hexa[5]])
    return a


def icon_weights():
    """Weights: a dumbbell."""
    a = new_layer()
    stroke(a, [(LO + 14 * SS, C), (HI - 14 * SS, C)])
    for sx in (-1, 1):
        # Big inner plate, small outer plate.
        x_in = C + sx * 22 * SS
        rrect(a, (min(x_in, x_in + sx * 14 * SS), C - 30 * SS, max(x_in, x_in + sx * 14 * SS), C + 30 * SS), 6 * SS, fill=True)
        x_out = C + sx * 40 * SS
        rrect(a, (min(x_out, x_out + sx * 10 * SS), C - 19 * SS, max(x_out, x_out + sx * 10 * SS), C + 19 * SS), 5 * SS, fill=True)
    return a


ICONS = {
    "brush": icon_brush,
    "falloff": icon_falloff,
    "falloff_2": icon_falloff_2,
    "grid": icon_grid,
    "mask": icon_mask,
    "mask_clear": icon_mask_clear,
    "mask_invert": icon_mask_invert,
    "mask_sharp": icon_mask_sharp,
    "mask_smooth": icon_mask_smooth,
    "mask_smooth_2": icon_mask_smooth,
    "mirror": icon_mirror,
    "options": icon_options,
    "stroke": icon_stroke,
    "texture": icon_texture,
    "voxels": icon_voxels,
    "weights": icon_weights,
}


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fn in ICONS.items():
        finish(fn()).save(out_dir / f"{name}.png", optimize=True)
        print(f"{name}.png")


if __name__ == "__main__":
    main()
