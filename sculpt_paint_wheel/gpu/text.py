"""Advanced 2D text drawing helpers (``blf``) for wheel / overlay UI."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Literal

import blf
import gpu
from bpy.types import Context
from mathutils import Color

from ..core.globals import GLOBALS
from ..core.gpu.imm_2d import draw_rect_fill, draw_text as imm_draw_text, text_dimensions as imm_text_dimensions


def ui_scale(context: Context) -> float:
    return float(getattr(context.preferences.view, "ui_scale", 1.0))


def blf_size_scaled(font_id: int, size_pt: float, context: Context) -> None:
    blf.size(font_id, int(round(size_pt * ui_scale(context))))


def text_dimensions(
    text: str,
    size: float = 14.0,
    font_id: int = 0,
    *,
    context: Context | None = None,
) -> tuple[float, float]:
    if context is not None:
        blf_size_scaled(font_id, size, context)
    else:
        blf.size(font_id, int(round(size)))
    return blf.dimensions(font_id, text)


def wrapped_lines(
    text: str,
    max_width_px: float,
    font_id: int = 0,
    size: float = 14.0,
    *,
    context: Context | None = None,
) -> list[str]:
    if context is not None:
        blf_size_scaled(font_id, size, context)
    else:
        blf.size(font_id, int(round(size)))
    split_fn = getattr(blf, "split", None)
    if split_fn is not None:
        lines = split_fn(font_id, text, max_width_px)
        return list(lines) if lines else ([text] if text else [])
    # Fallback: greedy wrap by words
    if max_width_px <= 4.0 or not text.strip():
        return [text] if text else []
    words = text.split(" ")
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        tw, _ = blf.dimensions(font_id, trial)
        if tw <= max_width_px:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def draw_text_multiline(
    lines: list[str],
    x: float,
    y_top: float,
    *,
    size: float = 14.0,
    line_step: float | None = None,
    font_id: int = 0,
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    align: Literal['LEFT', 'CENTER', 'RIGHT'] = 'LEFT',
    shadow: bool = False,
    context: Context | None = None,
) -> tuple[float, float]:
    """Draw stacked lines downward from *y_top* (first line at top). Returns total (width, height)."""
    if not lines:
        return (0.0, 0.0)
    eff_size = float(int(round(size * ui_scale(context)))) if context is not None else float(int(round(size)))
    blf.size(font_id, int(round(eff_size)))
    step = line_step if line_step is not None else blf.dimensions(font_id, "Mg")[1] * 1.15
    max_w = 0.0
    cy = y_top
    for line in lines:
        tw, th = blf.dimensions(font_id, line)
        max_w = max(max_w, tw)
        imm_draw_text(
            line, x, cy, size=eff_size, color=color, font_id=font_id, align=align,
            valign='TOP', shadow=shadow,
        )
        cy -= step
    return (max_w, step * len(lines))


def draw_text(
    text: str,
    x: float,
    y: float,
    *,
    size: float = 14.0,
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    font_id: int = 0,
    align: Literal['LEFT', 'CENTER', 'RIGHT'] = 'LEFT',
    valign: Literal['BOTTOM', 'MIDDLE', 'TOP'] = 'BOTTOM',
    shadow: bool = False,
    rotation: float = 0.0,
    context: Context | None = None,
) -> tuple[float, float]:
    """Delegates to ``core.gpu.imm_2d.draw_text``; pass *context* for UI-scaled font size."""
    eff_size = float(int(round(size * ui_scale(context)))) if context is not None else size
    return imm_draw_text(
        text, x, y, size=eff_size, color=color, font_id=font_id,
        align=align, valign=valign, shadow=shadow, rotation=rotation,
    )


@contextmanager
def gpu_scissor(x: int, y: int, width: int, height: int) -> Iterator[None]:
    """Temporarily restrict drawing to a screen-space rectangle (pixels)."""
    try:
        prev = gpu.state.scissor_get()
    except Exception:
        prev = None
    gpu.state.scissor_set(x, y, width, height)
    try:
        yield
    finally:
        if prev is not None and len(prev) >= 4:
            gpu.state.scissor_set(int(prev[0]), int(prev[1]), int(prev[2]), int(prev[3]))
        else:
            try:
                gpu.state.scissor_set(0, 0, 65535, 65535)
            except Exception:
                pass


def draw_text_clipped(
    text: str,
    x: float,
    y: float,
    clip_x: int,
    clip_y: int,
    clip_w: int,
    clip_h: int,
    *,
    size: float = 14.0,
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    font_id: int = 0,
    align: Literal['LEFT', 'CENTER', 'RIGHT'] = 'LEFT',
    valign: Literal['BOTTOM', 'MIDDLE', 'TOP'] = 'BOTTOM',
    shadow: bool = False,
    context: Context | None = None,
) -> tuple[float, float]:
    with gpu_scissor(clip_x, clip_y, clip_w, clip_h):
        return draw_text(
            text, x, y, size=size, color=color, font_id=font_id,
            align=align, valign=valign, shadow=shadow, context=context,
        )


def draw_text_with_background(
    text: str,
    x: float,
    y: float,
    *,
    size: float = 14.0,
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    bg_color: tuple[float, float, float, float] = (0.08, 0.08, 0.1, 0.92),
    pad: float = 4.0,
    font_id: int = 0,
    align: Literal['LEFT', 'CENTER', 'RIGHT'] = 'LEFT',
    valign: Literal['BOTTOM', 'MIDDLE', 'TOP'] = 'BOTTOM',
    shadow: bool = False,
    corner_radius: float = 0.0,
    context: Context | None = None,
) -> tuple[float, float]:
    """Draw a filled rectangle behind ``draw_text`` (requires non-background mode)."""
    if GLOBALS.IN_BACKGROUND:
        return imm_text_dimensions(text, size, font_id)
    tw, th = text_dimensions(text, size, font_id, context=context)
    draw_x = x
    draw_y = y
    if align == 'CENTER':
        draw_x -= tw * 0.5
    elif align == 'RIGHT':
        draw_x -= tw
    if valign == 'MIDDLE':
        draw_y -= th * 0.5
    elif valign == 'TOP':
        draw_y -= th
    rx = int(draw_x - pad)
    ry = int(draw_y - pad)
    rw = int(tw + 2 * pad)
    rh = int(th + 2 * pad)
    col = Color(bg_color)
    draw_rect_fill(rx, ry, rw, rh, col, corner_radius=corner_radius)
    eff_size = float(int(round(size * ui_scale(context)))) if context is not None else size
    imm_draw_text(
        text, x, y, size=eff_size, color=color, font_id=font_id,
        align=align, valign=valign, shadow=shadow,
    )
    return (tw, th)


_custom_font_ids: dict[str, int] = {}


def load_custom_font(path: str) -> int:
    """Load a TTF/OTF path; returns ``blf`` font id (cached per resolved path)."""
    from pathlib import Path

    key = str(Path(path).resolve())
    if key in _custom_font_ids:
        return _custom_font_ids[key]
    fid = blf.load(key)
    if fid == -1:
        raise OSError(f"blf.load failed for font: {key}")
    _custom_font_ids[key] = fid
    return fid


def ellipsis_middle(
    text: str,
    max_width_px: float,
    *,
    font_id: int = 0,
    size: float = 14.0,
    context: Context | None = None,
    middle: str = "…",
) -> str:
    """Shorten *text* to fit *max_width_px*, keeping start and end with *middle*."""
    if context is not None:
        blf_size_scaled(font_id, size, context)
    else:
        blf.size(font_id, int(round(size)))
    tw, _ = blf.dimensions(font_id, text)
    if tw <= max_width_px or len(text) < 4:
        return text
    mw, _ = blf.dimensions(font_id, middle)
    budget = max_width_px - mw
    if budget <= 0:
        return middle[:1]
    lo, hi = 1, len(text) // 2
    best = middle
    while lo <= hi:
        mid = (lo + hi) // 2
        left = text[:mid]
        right = text[-mid:]
        trial = left + middle + right
        w, _ = blf.dimensions(font_id, trial)
        if w <= max_width_px:
            best = trial
            lo = mid + 1
        else:
            hi = mid - 1
    return best
