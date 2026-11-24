"""Record the promo video's footage: the real Sculpt-Paint Wheel used in Blender, one screenshot per frame.

    blender --factory-startup --enable-event-simulate --window-geometry 0 0 2560 1440 \
            --python store/video/rec_promo.py -- <out dir> <sequence>

Sequences: pain, sculpt, texture, gpencil, weight, themes, double. Each one runs in its own Blender, in an isolated
profile (BLENDER_USER_RESOURCES) with the extension installed as ``user_default/spwheel`` and no saved preferences.

Input is simulated (``window.event_simulate``): the wheel opens with Space, picks are real clicks on the real slots
(their positions come from the wheel's own widgets), strokes are real sculpt / paint / draw strokes. Every frame is a
window screenshot taken after the events of that frame; Blender's screenshots have no OS cursor, so the pointer is
logged per frame (window px, top-left origin, plus button / key state) and drawn by the editor (make_promo.py).

Writes <out dir>/<sequence>/NNNN.png and meta.json: fps, window size, frames[{x, y, down, keys}], marks{name: frame}.
"""
import json
import math
import os
import shutil
import sys
import traceback

import addon_utils
import bpy
from bpy_extras import view3d_utils

ARGS = sys.argv[sys.argv.index("--") + 1:]
SEQ = ARGS[1]
OUT = os.path.join(ARGS[0], SEQ)
P = "bl_ext.user_default.spwheel"
FPS = 30
UI = 1.3333            # 1920x1080's layout with 1.33x the pixels: room for the editor's punch-ins.
TICK = 0.02            # Seconds between steps (lets Blender handle the simulated events and redraw).

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)


def log(*a):
    print("REC:", *a, flush=True)


def mod(name):
    import importlib
    return importlib.import_module(f"{P}.{name}")


def wprefs():
    return bpy.context.preferences.addons[P].preferences.wheel


# ----- Window, areas, coordinates --------------------------------------------------------------------------------

def win():
    return bpy.context.window_manager.windows[0]


def v3d():
    w = win()
    a = max((a for a in w.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width * a.height)
    return w, a, [r for r in a.regions if r.type == 'WINDOW'][0]


def region_to_win(rx, ry):
    """Region px (bottom-left origin) -> window px (top-left origin)."""
    w, a, r = v3d()
    return r.x + rx, w.height - (r.y + ry)


def project(co):
    w, a, r = v3d()
    p = view3d_utils.location_3d_to_region_2d(r, a.spaces.active.region_3d, co)
    return region_to_win(p.x, p.y)


def head_frame(ob):
    """Screen centre and radius (window px) of an object's bounding box."""
    from mathutils import Vector
    pts = [project(ob.matrix_world @ Vector(c)) for c in ob.bound_box]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2), max(max(xs) - min(xs), max(ys) - min(ys)) / 2


# ----- Wheel geometry (window px) ---------------------------------------------------------------------------------

def wheel():
    return mod("wheels.wheel").Wheel.instances.get(bpy.context.mode)


def wheel_to_win(lx, ly):
    w = wheel()
    rx, ry = w.to_region(lx, ly)
    return region_to_win(rx, ry)


def slot(name):
    ring = wheel().brush_set_ring
    for pb in ring._pickers:
        md = getattr(pb, "_brush_metadata", None)
        if pb.enabled and md is not None and md.name == name:
            return wheel_to_win(pb.offset.x, pb.offset.y)
    names = [p._brush_metadata.name for p in ring._pickers if p.enabled and p._brush_metadata is not None]
    raise RuntimeError(f"no slot {name!r} on the wheel: {names}")


def hue_point(h):
    cp = wheel().color_picker
    r = (cp.hue_inner_r + cp.hue_outer_r) / 2
    a = h * 2 * math.pi
    return wheel_to_win(cp.center.x + r * math.cos(a), cp.center.y + r * math.sin(a))


def weight_point(v):
    wp = wheel().weight_picker
    a = math.radians(mod("gpu.weight").weight_value_to_angle_deg(v))
    r = (wp.radius_inner + wp.radius_outer) / 2
    return wheel_to_win(wp.center.x + r * math.cos(a), wp.center.y + r * math.sin(a))


def centre():
    return wheel_to_win(0, 0)


# ----- Recorder -------------------------------------------------------------------------------------------------

class Rec:
    def __init__(self):
        self.n = 0
        self.frames = []
        self.marks = {}
        self.ptr = [0.0, 0.0]
        self.down = False
        self.keys = []

    def ev(self, type, value, **kw):
        w = win()
        w.event_simulate(type=type, value=value, x=int(round(self.ptr[0])), y=int(round(w.height - self.ptr[1])), **kw)

    def grab(self, hold=1):
        """Draw the window and save it as the next frame (``hold`` frames: copies of it)."""
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        path = os.path.join(OUT, f"{self.n:04d}.png")
        bpy.ops.screen.screenshot(filepath=path)
        for i in range(hold):
            if i:
                shutil.copyfile(path, os.path.join(OUT, f"{self.n:04d}.png"))
            self.frames.append({"x": round(self.ptr[0], 1), "y": round(self.ptr[1], 1), "down": self.down,
                                "keys": list(self.keys)})
            self.n += 1

    def mark(self, name):
        self.marks[name] = self.n
        log("mark", name, self.n)

    def save(self, **extra):
        w = win()
        json.dump({"fps": FPS, "window": [w.width, w.height], "ui_scale": UI, "frames": self.frames,
                   "marks": self.marks, **extra}, open(os.path.join(OUT, "meta.json"), "w"), indent=0)


R = Rec()


def ease(t):
    return t * t * (3 - 2 * t)


def step():
    """Let Blender process the simulated events, then take the frame."""
    yield TICK
    R.grab()


def hold(n):
    yield TICK
    R.grab(n)


def move(x, y, frames=12):
    x0, y0 = R.ptr
    for i in range(1, frames + 1):
        k = ease(i / frames)
        R.ptr = [x0 + (x - x0) * k, y0 + (y - y0) * k]
        R.ev('MOUSEMOVE', 'NOTHING')
        yield from step()


def key(type, value):
    if value == 'PRESS':
        R.keys.append(type)
    elif type in R.keys:
        R.keys.remove(type)
    R.ev(type, value)
    yield from step()


def click(x, y, frames=12, hold_after=6):
    yield from move(x, y, frames)
    R.down = True
    R.ev('LEFTMOUSE', 'PRESS')
    yield from step()
    R.down = False
    R.ev('LEFTMOUSE', 'RELEASE')
    yield from step()
    if hold_after:
        yield from hold(hold_after)


def pick_hue(h, frames=12):
    """Pick a hue on the wheel's color ring: press just before it and drag onto it (the ring sets the hue on drag)."""
    yield from move(*hue_point(h - 0.04), frames)
    R.down = True
    R.ev('LEFTMOUSE', 'PRESS')
    yield from step()
    for i in range(1, 6):
        R.ptr = list(hue_point(h - 0.04 + 0.04 * i / 5))
        R.ev('MOUSEMOVE', 'NOTHING')
        yield from step()
    R.down = False
    R.ev('LEFTMOUSE', 'RELEASE')
    yield from step()
    yield from hold(6)


def drag(path, approach=10):
    """A stroke along ``path`` (window px), one point per frame."""
    yield from move(*path[0], approach)
    R.down = True
    R.ev('LEFTMOUSE', 'PRESS')
    yield from step()
    for x, y in path[1:]:
        R.ptr = [x, y]
        R.ev('MOUSEMOVE', 'NOTHING')
        yield from step()
    R.down = False
    R.ev('LEFTMOUSE', 'RELEASE')
    yield from step()


def path_pts(fn, n):
    return [fn(i / (n - 1)) for i in range(n)]


def open_wheel():
    yield from key('SPACE', 'PRESS')
    yield from hold(8)


def close_wheel():
    yield from key('SPACE', 'RELEASE')
    yield from hold(4)


# ----- Scene setup ------------------------------------------------------------------------------------------------

def close_splash():
    w = win()
    w.event_simulate(type='MOUSEMOVE', value='NOTHING', x=60, y=60)
    w.event_simulate(type='ESC', value='PRESS', x=60, y=60)


def prefs_setup(double_ring=False):
    p = bpy.context.preferences
    p.view.ui_scale = UI
    p.view.show_tooltips = False
    wp = wprefs()
    wp.scale = UI
    wp.brush_set_ring.allow_double_ring = double_ring
    p.view.show_splash = False


def scene(kind, mode, fullscreen=True, matcap=None, texture=False, color_tex=None):
    w, a, r = v3d()
    with bpy.context.temp_override(window=w, area=a, region=r):
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        if kind == "MESH":
            bpy.ops.mesh.primitive_monkey_add(size=2.0)
            ob = bpy.context.object
            m = ob.modifiers.new("s", 'SUBSURF')
            m.levels = 3
            bpy.ops.object.modifier_apply(modifier="s")
            bpy.ops.object.shade_smooth()
            if mode == "WEIGHT_PAINT":
                ob.vertex_groups.new(name="Weights")
        else:
            bpy.ops.object.grease_pencil_add(type='EMPTY')
            ob = bpy.context.object
        bpy.ops.view3d.view_axis(type='FRONT')
        if kind == "MESH":  # A 3/4 view in perspective: depth for the sculpt / paint shots.
            bpy.ops.view3d.view_orbit(angle=math.radians(24), type='ORBITLEFT')
            bpy.ops.view3d.view_orbit(angle=math.radians(8), type='ORBITUP')
            a.spaces.active.region_3d.view_perspective = 'PERSP'
        bpy.ops.object.mode_set(mode=mode)
        if texture:
            ob.data.materials.append(bpy.data.materials.new("Paint"))
            bpy.ops.paint.add_texture_paint_slot(type='BASE_COLOR', color=color_tex or (0.82, 0.8, 0.78, 1.0),
                                                 width=2048, height=2048)
        if fullscreen:
            bpy.ops.screen.screen_full_area(use_hide_panels=False)
    w, a, r = v3d()
    sp = a.spaces.active
    sp.overlay.show_floor = False
    sp.overlay.show_ortho_grid = False
    sp.overlay.show_axis_x = sp.overlay.show_axis_y = False
    sp.overlay.show_text = False
    sp.overlay.show_stats = False
    sp.show_gizmo_navigate = False
    sp.show_region_toolbar = not fullscreen
    sp.show_region_ui = False
    if matcap:
        sp.shading.type = 'SOLID'
        sp.shading.light = 'MATCAP'
        sp.shading.studio_light = matcap
    if texture:
        sp.shading.type = 'SOLID'
        sp.shading.light = 'STUDIO'
        sp.shading.color_type = 'TEXTURE'
    if kind != "MESH":
        sp.shading.type = 'SOLID'
        sp.shading.background_type = 'VIEWPORT'
        sp.shading.background_color = (0.075, 0.075, 0.085)
    return ob


def frame_object(ob, fill=0.62):
    """View the object so it fills ``fill`` of the viewport height."""
    w, a, r = v3d()
    with bpy.context.temp_override(window=w, area=a, region=r):
        bpy.ops.view3d.view_selected()
    rv = a.spaces.active.region_3d
    (_cx, _cy), rad = head_frame(ob)
    rv.view_distance *= (2 * rad) / (fill * r.height)


def paint_struct():
    ts = bpy.context.scene.tool_settings
    return {"SCULPT": ts.sculpt, "PAINT_TEXTURE": ts.image_paint, "PAINT_WEIGHT": ts.weight_paint,
            "PAINT_VERTEX": ts.vertex_paint, "PAINT_GREASE_PENCIL": getattr(ts, "gpencil_paint", None)}.get(bpy.context.mode)


def ups():
    """The mode's unified paint settings (Blender 5: on each Paint struct)."""
    p = paint_struct()
    return getattr(p, "unified_paint_settings", None) if p is not None else None


def brushes():
    ts = bpy.context.tool_settings
    out = []
    for paint in (ts.sculpt, ts.image_paint, ts.vertex_paint, ts.weight_paint, getattr(ts, "gpencil_paint", None)):
        br = getattr(paint, "brush", None) if paint is not None else None
        if br is not None:
            out.append(br)
    return out


def set_brush_size(px):
    """The brush size, on the unified settings and on the brushes (whichever the mode uses)."""
    u = ups()
    if u is not None:
        u.size = int(px * UI)
    for br in brushes():
        if hasattr(br, "size"):
            br.size = int(px * UI)


def set_strength(v):
    u = ups()
    if u is not None and hasattr(u, "strength"):
        u.strength = v
    for br in brushes():
        if hasattr(br, "strength"):
            br.strength = v


def set_color(rgb):
    u = ups()
    if u is not None and hasattr(u, "color"):
        u.color = rgb
    for br in brushes():
        if hasattr(br, "color"):
            br.color = rgb


def active_brush_name():
    ts = bpy.context.tool_settings
    paint = {"SCULPT": ts.sculpt, "PAINT_TEXTURE": ts.image_paint, "PAINT_WEIGHT": ts.weight_paint,
             "PAINT_GREASE_PENCIL": getattr(ts, "gpencil_paint", None)}.get(bpy.context.mode)
    return paint.brush.name if paint is not None and paint.brush is not None else None


# ----- Sequences --------------------------------------------------------------------------------------------------

def seq_pain():
    """Hunting for brushes: the default layout, the cursor wandering over the toolbar and the asset shelf."""
    prefs_setup()
    ob = scene("MESH", "SCULPT", fullscreen=False, matcap='clay_brown.exr')
    frame_object(ob, 0.55)
    yield 0.5
    w, a, r = v3d()
    (cx, cy), rad = head_frame(ob)
    R.ptr = [cx, cy]
    yield from hold(6)
    R.mark("start")
    tool_x = r.x + 26 * UI
    shelf_y = w.height - (a.y + 60 * UI)
    for (x, y, f) in [(tool_x, cy - 180, 14), (tool_x, cy - 60, 10), (tool_x, cy + 80, 10),
                      (cx - 500, shelf_y, 16), (cx - 200, shelf_y, 12), (cx + 100, shelf_y, 12),
                      (cx + 420, shelf_y, 12), (cx + 150, shelf_y - 8, 12), (cx - 350, shelf_y, 14)]:
        yield from move(x, y, f)
        yield from hold(3)
    R.mark("end")
    R.save()


def seq_sculpt():
    prefs_setup()
    ob = scene("MESH", "SCULPT", matcap='clay_brown.exr')
    frame_object(ob, 0.66)
    ob.use_mesh_mirror_x = True
    set_brush_size(46)
    yield 0.8
    (cx, cy), rad = head_frame(ob)
    log("head", cx, cy, rad)
    R.ptr = [cx + rad * 0.15, cy - rad * 0.1]
    yield from hold(10)

    # 1. Pick Clay Strips from the wheel.
    R.mark("open1")
    yield from open_wheel()
    yield from click(*slot("Clay Strips"), frames=14, hold_after=8)
    log("picked", active_brush_name())
    yield from close_wheel()
    R.mark("strokes1")
    # Brow ridge, then cheeks (mirrored by symmetry).
    yield from drag(path_pts(lambda t: (cx - rad * 0.55 + rad * 0.5 * t, cy - rad * 0.38 - math.sin(t * math.pi) * rad * 0.08), 26))
    yield from drag(path_pts(lambda t: (cx - rad * 0.52 + rad * 0.18 * t, cy + rad * 0.05 + rad * 0.28 * t), 22))
    yield from drag(path_pts(lambda t: (cx - rad * 0.22 + rad * 0.2 * math.sin(t * math.pi), cy - rad * 0.62 + rad * 0.2 * t), 20))
    yield from hold(6)

    # 2. Smart centre: drag up for a bigger brush.
    R.mark("open2")
    yield from move(cx + rad * 0.32, cy - rad * 0.05, 8)
    yield from open_wheel()
    c = centre()
    yield from move(c[0], c[1], 3)
    R.down = True
    R.ev('LEFTMOUSE', 'PRESS')
    yield from step()
    R.mark("radius")
    for i in range(1, 19):
        R.ptr = [c[0], c[1] - i * 5 * UI]
        R.ev('MOUSEMOVE', 'NOTHING')
        yield from step()
    yield from hold(8)
    R.down = False
    R.ev('LEFTMOUSE', 'RELEASE')
    yield from step()
    log("size", ups().size if ups() else None)

    # 3. Crease Polish.
    yield from click(*slot("Crease Polish"), frames=14, hold_after=8)
    log("picked", active_brush_name())
    yield from close_wheel()
    set_brush_size(30)
    R.mark("strokes2")
    yield from drag(path_pts(lambda t: (cx - rad * 0.12 - rad * 0.06 * t, cy + rad * 0.15 + rad * 0.36 * t), 22))
    yield from drag(path_pts(lambda t: (cx - rad * 0.45 + rad * 0.3 * t, cy - rad * 0.22 + rad * 0.03 * math.sin(t * 6)), 22))
    yield from hold(8)
    R.mark("end")
    R.save(head=[cx, cy, rad])


def seq_texture():
    prefs_setup()
    ob = scene("MESH", "TEXTURE_PAINT", texture=True)
    frame_object(ob, 0.66)
    set_brush_size(22)
    set_strength(1.0)
    ups().use_unified_color = True   # The wheel's picks and the strokes then use the same color.
    set_color((0.2, 0.55, 0.95))
    yield 0.8
    (cx, cy), rad = head_frame(ob)
    rad *= 0.6
    cx += rad * 0.12
    R.ptr = [cx + rad * 0.1, cy]
    yield from hold(8)

    R.mark("open1")
    yield from open_wheel()
    yield from pick_hue(0.035, 14)    # Warm orange.
    yield from close_wheel()
    R.mark("strokes1")
    yield from drag(path_pts(lambda t: (cx - rad * 0.6 + rad * 1.2 * t, cy - rad * 0.4 + math.sin(t * math.pi * 2) * rad * 0.06), 34))
    yield from drag(path_pts(lambda t: (cx - rad * 0.5 + rad * 1.0 * t, cy - rad * 0.28 + math.sin(t * math.pi * 2 + 1) * rad * 0.05), 30))

    R.mark("open2")
    yield from open_wheel()
    yield from pick_hue(0.53, 14)     # Teal.
    yield from close_wheel()
    R.mark("strokes2")
    yield from drag(path_pts(lambda t: (cx - rad * 0.45 + rad * 0.9 * t, cy + rad * 0.35 + math.sin(t * math.pi) * rad * 0.1), 30))
    yield from drag(path_pts(lambda t: (cx - rad * 0.3 + rad * 0.6 * t, cy + rad * 0.48 + math.sin(t * math.pi) * rad * 0.08), 26))

    R.mark("open3")
    yield from open_wheel()
    yield from pick_hue(0.78, 14)     # Violet.
    yield from close_wheel()
    yield from drag(path_pts(lambda t: (cx - rad * 0.2 + rad * 0.12 * math.cos(t * 6.28), cy + rad * 0.02 + rad * 0.12 * math.sin(t * 6.28)), 30))
    yield from hold(8)
    R.mark("end")
    R.save(head=[cx, cy, rad])


def seq_gpencil():
    prefs_setup()
    ob = scene("GP", "PAINT_GREASE_PENCIL")
    ts = bpy.context.tool_settings
    gp = getattr(ts, "gpencil_paint", None)
    if gp is not None and hasattr(gp, "color_mode"):
        gp.color_mode = 'VERTEXCOLOR'
    set_brush_size(16)
    set_strength(1.0)
    set_color((0.95, 0.95, 0.97))
    yield 0.8
    w, a, r = v3d()
    cx, cy = r.x + r.width / 2, w.height - (r.y + r.height / 2)
    s = r.height * 0.32
    R.ptr = [cx, cy]
    yield from hold(8)

    R.mark("open1")
    yield from open_wheel()
    yield from click(*slot("Ink Pen"), frames=14, hold_after=6)
    log("picked", active_brush_name())
    yield from pick_hue(0.58, 10)     # Blue.
    yield from close_wheel()
    R.mark("strokes1")
    # A wave and a loop.
    yield from drag(path_pts(lambda t: (cx - s * 1.4 + s * 2.8 * t, cy + s * 0.15 + math.sin(t * math.pi * 3) * s * 0.35), 40))
    yield from drag(path_pts(lambda t: (cx - s * 0.4 + s * 0.5 * math.cos(t * 6.6), cy - s * 0.25 + s * 0.5 * math.sin(t * 6.6)), 36))

    R.mark("open2")
    yield from open_wheel()
    yield from click(*slot("Marker Bold"), frames=14, hold_after=6)
    log("picked", active_brush_name())
    yield from pick_hue(0.03, 10)     # Orange.
    yield from close_wheel()
    R.mark("strokes2")
    yield from drag(path_pts(lambda t: (cx + s * 0.35 + s * 0.9 * t, cy - s * 0.7 + s * 1.2 * t * t), 30))
    yield from drag(path_pts(lambda t: (cx - s * 1.2 + s * 2.4 * t, cy + s * 0.75 + math.sin(t * math.pi) * -s * 0.2), 34))
    yield from hold(8)
    R.mark("end")
    R.save()


def seq_weight():
    prefs_setup()
    ob = scene("MESH", "WEIGHT_PAINT")
    frame_object(ob, 0.66)
    bpy.context.scene.tool_settings.vertex_group_user = 'NONE'
    set_brush_size(36)
    set_strength(1.0)
    yield 0.8
    (cx, cy), rad = head_frame(ob)
    rad *= 0.6
    cx += rad * 0.12
    R.ptr = [cx + rad * 0.1, cy]
    yield from hold(8)

    R.mark("open1")
    yield from open_wheel()
    yield from click(*weight_point(1.0), frames=14, hold_after=6)
    yield from close_wheel()
    R.mark("strokes1")
    yield from drag(path_pts(lambda t: (cx - rad * 0.55 + rad * 1.1 * t, cy - rad * 0.45), 30))
    yield from drag(path_pts(lambda t: (cx - rad * 0.5 + rad * 1.0 * t, cy - rad * 0.3), 28))

    R.mark("open2")
    yield from open_wheel()
    yield from click(*weight_point(0.5), frames=14, hold_after=6)
    yield from close_wheel()
    R.mark("strokes2")
    yield from drag(path_pts(lambda t: (cx - rad * 0.5 + rad * 1.0 * t, cy + rad * 0.2), 28))
    yield from hold(8)
    R.mark("end")
    R.save(head=[cx, cy, rad])


def seq_themes():
    prefs_setup()
    ob = scene("MESH", "SCULPT", matcap='clay_brown.exr')
    frame_object(ob, 0.66)
    yield 0.8
    (cx, cy), rad = head_frame(ob)
    R.ptr = [cx, cy]
    yield from hold(4)
    yield from open_wheel()
    R.mark("themes")
    for name in ["Dark", "Light", "Midnight", "Ember", "Forest", "Rose", "Graphite", "High Contrast", "Paper", "Frost", "Dark"]:
        bpy.ops.spwheel.opapplythemepreset('EXEC_DEFAULT', preset=name)
        yield from hold(8)
    yield from close_wheel()
    R.mark("end")
    R.save(head=[cx, cy, rad])


SCULPT_PRO = ("Draw", "Draw Sharp", "Clay", "Clay Strips", "Clay Thumb", "Layer", "Inflate/Deflate", "Blob",
              "Crease Polish", "Crease Sharp", "Smooth", "Flatten/Contrast", "Fill/Deepen", "Scrape/Fill",
              "Scrape Multiplane", "Plateau", "Trim", "Pinch/Magnify", "Relax Pinch", "Relax Slide", "Grab", "Grab 2D",
              "Grab Silhouette", "Elastic Grab", "Snake Hook", "Elastic Snake Hook", "Thumb", "Pose", "Nudge", "Twist",
              "Pull", "Boundary", "Sharpen", "Density")


def seq_double():
    prefs_setup(double_ring=True)
    ob = scene("MESH", "SCULPT", matcap='clay_brown.exr')
    frame_object(ob, 0.5)
    storage = mod("pg.pg_wheel_storage").WheelStorage.get_by_mode(bpy.context.mode)
    first = storage.active_brush_set_index
    bs = storage.add_brush_set("SCULPT")
    bs.name = "Sculpt Pro"
    for n in SCULPT_PRO:
        bs.add_brush_from_essential("SCULPT", n)
    storage.active_brush_set_index = first
    yield 0.8
    (cx, cy), rad = head_frame(ob)
    R.ptr = [cx, cy]
    yield from hold(4)
    yield from open_wheel()
    R.mark("switch")
    R.keys.append('SHIFT')
    R.ev('WHEELUPMOUSE', 'PRESS', shift=True)
    yield from step()
    R.keys.remove('SHIFT')
    yield from hold(12)
    R.mark("grown")
    for ang in range(0, 200, 25):
        a = math.radians(160 - ang)
        rr = wheel().radius * wheel().scale * 0.82
        yield from move(cx + math.cos(a) * rr, cy - math.sin(a) * rr, 5)
    yield from hold(6)
    yield from close_wheel()
    R.mark("end")
    R.save()


SEQS = {"pain": seq_pain, "sculpt": seq_sculpt, "texture": seq_texture, "gpencil": seq_gpencil,
        "weight": seq_weight, "themes": seq_themes, "double": seq_double}


# ----- Driver -----------------------------------------------------------------------------------------------------

def main():
    yield 0.6
    close_splash()
    yield 0.6
    yield from SEQS[SEQ]()
    log("done", R.n, "frames")


GEN = None


def tick():
    global GEN
    try:
        if GEN is None:
            GEN = main()
        delay = next(GEN)
        return max(0.0, float(delay if delay is not None else TICK))
    except StopIteration:
        bpy.ops.wm.quit_blender()
        return None
    except Exception:
        traceback.print_exc()
        try:
            R.save(error=traceback.format_exc())
        except Exception:
            pass
        bpy.ops.wm.quit_blender()
        return None


addon_utils.enable(P, default_set=True)
bpy.app.timers.register(tick, first_interval=3)
