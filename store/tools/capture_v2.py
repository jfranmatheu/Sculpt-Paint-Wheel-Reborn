"""Capture the real Sculpt-Paint Wheel 2 in Blender for the store graphics and videos.

    blender --factory-startup --enable-event-simulate --window-geometry 0 0 1920 1200 \
            --python store/tools/capture_v2.py -- <out dir> <part>

Use an isolated user profile (BLENDER_USER_RESOURCES) with the extension installed (or linked) as
``user_default/spwheel``, and a fresh ``spwheel/preferences.json`` so the defaults are what's captured.

Parts (each writes into <out dir>/<part>/):
    modes     the wheel in the 9 modes: <mode>.png (3D View area) + <mode>.json (wheel centre, image pixels)
    centre    hover a pie button, drag the centre up (radius) and sideways (strength)
    themes    the Sculpt wheel in every built-in theme, Texture Paint in Dark and Light
    double    one ring vs two rings (a 34-brush set from the Essentials library), Texture Paint with two rings
    prefs     Preferences filling the window at 1.4x UI scale: Settings and Theme tabs
    tints     frames/ + frames.json: theme tint settings changed live (Preferences left, wheel right)
    presets   frames/ + frames.json: theme presets applied live (Preferences left, wheel right)
"""
import bpy, addon_utils, importlib, json, os, sys, traceback

ARGS = sys.argv[sys.argv.index("--") + 1:]
PART = ARGS[1]
OUT = os.path.join(ARGS[0], PART)
os.makedirs(OUT, exist_ok=True)
P = "bl_ext.user_default.spwheel"
log = {}

MODES = [  # (file id, object kind, mode_set mode)
    ("sculpt", "MESH", "SCULPT"),
    ("texture", "MESH", "TEXTURE_PAINT"),
    ("vertex", "MESH", "VERTEX_PAINT"),
    ("weight", "MESH", "WEIGHT_PAINT"),
    ("curves", "CURVES", "SCULPT_CURVES"),
    ("gp-draw", "GP", "PAINT_GREASE_PENCIL"),
    ("gp-sculpt", "GP", "SCULPT_GREASE_PENCIL"),
    ("gp-weight", "GP", "WEIGHT_GREASE_PENCIL"),
    ("gp-vertex", "GP", "VERTEX_GREASE_PENCIL"),
]


# ----- Helpers ------------------------------------------------------------------------------------------------

def note(k, v):
    log[k] = v
    print("TEST:", k, v, flush=True)


def mod(name):
    return importlib.import_module(f"{P}.{name}")


def wheel_prefs():
    return bpy.context.preferences.addons[P].preferences.wheel


def redraw():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            a.tag_redraw()


def main_area(kind):
    win = bpy.context.window
    areas = [a for a in win.screen.areas if a.type == kind]
    return win, (max(areas, key=lambda a: a.width * a.height) if areas else None)


def region(area, kind='WINDOW'):
    return [r for r in area.regions if r.type == kind][0]


def monkey():
    bpy.ops.mesh.primitive_monkey_add(size=2.2)
    ob = bpy.context.object
    m = ob.modifiers.new("s", 'SUBSURF'); m.levels = 2
    bpy.ops.object.modifier_apply(modifier="s")
    bpy.ops.object.shade_smooth()
    return ob


def setup(kind, mode):
    win, a = main_area('VIEW_3D')
    with bpy.context.temp_override(window=win, area=a, region=region(a)):
        ob = bpy.context.object
        if ob and ob.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        if kind == "MESH":
            ob = monkey()
            if mode == "WEIGHT_PAINT":
                ob.vertex_groups.new(name="Group")
        elif kind == "CURVES":
            monkey()
            bpy.ops.view3d.view_axis(type='FRONT')
            bpy.ops.view3d.view_selected()
            bpy.ops.object.curves_empty_hair_add()
        else:
            bpy.ops.object.grease_pencil_add(type='MONKEY')
        if kind != "CURVES":
            bpy.ops.view3d.view_axis(type='FRONT')
            bpy.ops.view3d.view_selected()
        bpy.ops.object.mode_set(mode=mode)
        if mode == "TEXTURE_PAINT":
            ob = bpy.context.object
            ob.data.materials.append(bpy.data.materials.new("Paint"))
            bpy.ops.paint.add_texture_paint_slot(type='BASE_COLOR', color=(0.55, 0.62, 0.8, 1.0), width=1024, height=1024)
    if PART not in ("themes_live", "tints_live"):
        # Cut-out shots: the object far away behind the wheel and no floor grid, so the translucent page pill
        # only shows the plain viewport background.
        space = a.spaces.active
        space.region_3d.view_distance *= 10
        space.overlay.show_floor = False
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False


def ev(type, value, dx=0, dy=0):
    win, a = main_area('VIEW_3D')
    r = region(a)
    win.event_simulate(type=type, value=value, x=r.x + r.width // 2 + dx, y=r.y + r.height // 2 + dy)


def shoot(name):
    """The 3D View area, plus the wheel centre in image pixels."""
    win, a = main_area('VIEW_3D')
    r = region(a)
    with bpy.context.temp_override(window=win, area=a):
        bpy.ops.screen.screenshot_area(filepath=os.path.join(OUT, f"{name}.png"))
    cx = (r.x - a.x) + r.width // 2
    cy = a.height - ((r.y - a.y) + r.height // 2)
    info = {"cx": cx, "cy": cy, "area": [a.width, a.height]}
    w = mod("wheels.wheel").Wheel.instances.get(bpy.context.mode)
    if w is not None and w.radius:  # The wheel's radius in pixels and its page pill (cut-outs for the graphics).
        info["radius"] = w.radius * w.scale
        ring = getattr(w, "brush_set_ring", None)
        pill = ring._get_page_indicator_layout() if ring is not None else None
        if pill:
            _i, _n, px, py, pw, ph = pill
            info["pill"] = [px * w.scale, -(py + ph) * w.scale, pw * w.scale, ph * w.scale]  # x, y (down), w, h
    json.dump(info, open(os.path.join(OUT, f"{name}.json"), "w"))
    print("TEST: saved", name, flush=True)


def open_wheel():
    return [(lambda: ev('MOUSEMOVE', 'NOTHING'), 0.3), (lambda: ev('ESC', 'PRESS'), 0.4), (lambda: ev('SPACE', 'PRESS'), 1.0)]


def close_wheel():
    return [(lambda: ev('SPACE', 'RELEASE'), 0.3), (lambda: ev('ESC', 'PRESS'), 0.5)]


def apply_theme(name):
    bpy.ops.spwheel.opapplythemepreset('EXEC_DEFAULT', preset=name)
    redraw()


def close_splash():
    win = bpy.context.window
    win.event_simulate(type="MOUSEMOVE", value="NOTHING", x=40, y=40)
    win.event_simulate(type="ESC", value="PRESS", x=40, y=40)


def essentials_brushes(asset_id):
    path = os.path.join(bpy.utils.resource_path('LOCAL'), "datafiles", "assets", "brushes",
                        f"essentials_brushes-{asset_id}.blend")
    with bpy.data.libraries.load(path, assets_only=True) as (src, _dst):
        return list(src.brushes)


SCULPT_PRO = (  # 34 sculpting brushes of Blender's Essentials library (no paint / cloth ones).
    "Draw", "Draw Sharp", "Clay", "Clay Strips", "Clay Thumb", "Layer", "Inflate/Deflate", "Blob", "Crease Polish",
    "Crease Sharp", "Smooth", "Flatten/Contrast", "Fill/Deepen", "Scrape/Fill", "Scrape Multiplane", "Plateau", "Trim",
    "Pinch/Magnify", "Relax Pinch", "Relax Slide", "Grab", "Grab 2D", "Grab Silhouette", "Elastic Grab", "Snake Hook",
    "Elastic Snake Hook", "Thumb", "Pose", "Nudge", "Twist", "Pull", "Boundary", "Sharpen", "Density",
)


def big_sculpt_set():
    """A 'Sculpt Pro' brush set with 34 Essentials brushes, made active."""
    storage = mod("pg.pg_wheel_storage").WheelStorage.get_by_mode(bpy.context.mode)
    available = set(essentials_brushes("mesh_sculpt"))
    names = [n for n in SCULPT_PRO if n in available]
    note("missing from essentials", [n for n in SCULPT_PRO if n not in available])
    bs = storage.add_brush_set("SCULPT")
    bs.name = "Sculpt Pro"
    for n in names:
        bs.add_brush_from_essential("SCULPT", n)
    note("big set", len(bs.items))


def prefs_fill(tab):
    """Preferences in the main area, the add-on expanded on ``tab``."""
    win, a = main_area('VIEW_3D')
    a.type = 'PREFERENCES'
    wheel_prefs().prefs_tab = tab
    bpy.context.preferences.active_section = 'ADDONS'
    bpy.context.window_manager.addon_search = "Sculpt-Paint"


def prefs_tab(tab):
    wheel_prefs().prefs_tab = tab
    redraw()


def scroll_prefs(n):
    win, a = main_area('PREFERENCES')
    with bpy.context.temp_override(window=win, area=a, region=region(a)):
        bpy.ops.view2d.scroll_up(deltax=0, deltay=8000)
        for _ in range(n):
            bpy.ops.view2d.scroll_down(deltax=0, deltay=60)
    redraw()


def shot_prefs(name):
    win, a = main_area('PREFERENCES')
    with bpy.context.temp_override(window=win, area=a):
        bpy.ops.screen.screenshot_area(filepath=os.path.join(OUT, f"{name}.png"))
    print("TEST: saved", name, flush=True)


# ----- Live recordings: Preferences (left) and the open wheel (right) -----------------------------------------

FR = os.path.join(OUT, "frames")


def split():
    win, a = main_area('VIEW_3D')
    with bpy.context.temp_override(window=win, area=a, region=region(a)):
        bpy.ops.screen.area_split(direction='VERTICAL', factor=0.45)
    v3d = sorted([x for x in win.screen.areas if x.type == 'VIEW_3D'], key=lambda x: x.x)
    v3d[0].type = 'PREFERENCES'
    wheel_prefs().prefs_tab = 'THEME'
    bpy.context.preferences.active_section = 'ADDONS'
    bpy.context.window_manager.addon_search = "Sculpt-Paint"


def fit_view():
    win, a = main_area('VIEW_3D')
    with bpy.context.temp_override(window=win, area=a, region=region(a)):
        bpy.ops.view3d.view_selected()








# ----- Parts ----------------------------------------------------------------------------------------------------

steps = [(close_splash, 0.6)]

if PART == "modes":
    for fid, kind, mode in MODES:
        steps += [(lambda kind=kind, mode=mode: setup(kind, mode), 1.6)] + open_wheel()
        steps += [(lambda fid=fid: shoot(fid), 0.3)] + close_wheel()

elif PART == "centre":
    steps += [(lambda: setup("MESH", "SCULPT"), 1.6)] + open_wheel() + [
        (lambda: shoot("sculpt"), 0.3),
        (lambda: ev('MOUSEMOVE', 'NOTHING', 56, 56), 0.6), (lambda: shoot("sculpt_hover"), 0.3),
        (lambda: ev('MOUSEMOVE', 'NOTHING'), 0.4), (lambda: ev('LEFTMOUSE', 'PRESS'), 0.3),
        (lambda: ev('MOUSEMOVE', 'NOTHING', 0, 12), 0.15), (lambda: ev('MOUSEMOVE', 'NOTHING', 0, 40), 0.15),
        (lambda: ev('MOUSEMOVE', 'NOTHING', 0, 70), 0.5), (lambda: shoot("sculpt_drag_radius"), 0.3),
        (lambda: ev('LEFTMOUSE', 'RELEASE', 0, 70), 0.4),
        (lambda: ev('MOUSEMOVE', 'NOTHING'), 0.4), (lambda: ev('LEFTMOUSE', 'PRESS'), 0.3),
        (lambda: ev('MOUSEMOVE', 'NOTHING', 12, 0), 0.15), (lambda: ev('MOUSEMOVE', 'NOTHING', 50, 0), 0.15),
        (lambda: ev('MOUSEMOVE', 'NOTHING', 80, 0), 0.5), (lambda: shoot("sculpt_drag_strength"), 0.3),
        (lambda: ev('LEFTMOUSE', 'RELEASE', 80, 0), 0.4),
    ] + close_wheel()

elif PART == "themes":
    names = ["Dark", "Light", "Midnight", "Ember", "Forest", "Rose", "Graphite", "High Contrast", "Paper", "Frost"]
    steps += [(lambda: setup("MESH", "SCULPT"), 1.6)] + open_wheel()
    for n in names:
        steps += [(lambda n=n: apply_theme(n), 0.5), (lambda n=n: shoot("sculpt_" + n.lower().replace(" ", "_")), 0.2)]
    steps += close_wheel() + [(lambda: setup("MESH", "TEXTURE_PAINT"), 1.6)] + open_wheel()
    for n in ("Dark", "Light"):
        steps += [(lambda n=n: apply_theme(n), 0.5), (lambda n=n: shoot("texture_" + n.lower()), 0.2)]
    steps += close_wheel() + [(lambda: apply_theme("Dark"), 0.2)]

elif PART == "double":
    steps += [(lambda: setup("MESH", "SCULPT"), 1.6)] + open_wheel() + [(lambda: shoot("sculpt_one_ring"), 0.3)]
    steps += close_wheel() + [(big_sculpt_set, 0.3), (lambda: setattr(wheel_prefs().brush_set_ring, "allow_double_ring", False), 0.2)]
    steps += open_wheel() + [(lambda: shoot("big_one_ring"), 0.3)] + close_wheel()
    steps += [(lambda: setattr(wheel_prefs().brush_set_ring, "allow_double_ring", True), 0.2)]
    steps += open_wheel() + [(lambda: shoot("big_two_rings"), 0.3),
                             (lambda: ev('MOUSEMOVE', 'NOTHING', -205, 120), 0.6), (lambda: shoot("big_two_rings_hover"), 0.3)]
    steps += close_wheel()

elif PART == "prefs":
    steps += [(lambda: setattr(bpy.context.preferences.view, "ui_scale", 1.4), 0.6), (lambda: prefs_fill('SETTINGS'), 1.0),
              (lambda: bpy.ops.preferences.addon_expand(module=P), 0.8),
              (lambda: setattr(wheel_prefs().brush_set_ring, "allow_double_ring", True), 0.2),
              (lambda: scroll_prefs(6), 0.8), (lambda: shot_prefs("prefs_settings"), 0.4),
              (lambda: prefs_tab('THEME'), 0.6), (lambda: scroll_prefs(6), 0.8), (lambda: shot_prefs("prefs_theme"), 0.4),
              (lambda: apply_theme("Midnight"), 0.3), (lambda: setattr(wheel_prefs().theme, "tarta_pressed_color", (0.9, 0.45, 0.2, 1)), 0.6),
              (lambda: shot_prefs("prefs_theme_modified"), 0.4),
              (lambda: scroll_prefs(16), 0.8), (lambda: shot_prefs("prefs_theme_pie"), 0.4),
              (lambda: apply_theme("Dark"), 0.3)]

elif PART in ("themes_live", "tints_live"):
    # Beats for live_montage.py: each beat is a real UI state (full-window screenshot) plus where the cursor goes
    # and what it does there (window pixels, top-left origin). Positions are calibrated for a 1920x1200 window
    # with the Preferences split on the left, scrolled to the top.
    DROPDOWN = (300, 536)
    MENU_ORDER = ["Dark", "Light", "Ember", "Forest", "Frost", "Graphite", "High Contrast", "Midnight", "Paper", "Rose"]
    TINT_Y, TARGET_Y, SLIDER_Y, SLIDER_X0, SLIDER_W = 960, 985, 1010, 390, 300
    TINT_X = {"DISABLED": 439, "PER_TYPE": 539, "CUSTOM": 640}
    TARGET_X = {"FILL": 426, "OUTLINE": 501, "ICON": 576, "COLOR_STRIP": 652}
    live = {"beats": [], "wheels": {}}
    cur = {"wheel": None}

    def win_ev(type, value, x, y):
        win = bpy.context.window
        win.event_simulate(type=type, value=value, x=x, y=win.height - y)

    def grab(name):
        os.makedirs(FR, exist_ok=True)
        bpy.ops.screen.screenshot(filepath=os.path.join(FR, f"{name}.png"))
        return f"{name}.png"

    def wheel_geom():
        _, v = main_area('VIEW_3D')
        rv = region(v)
        w = mod("wheels.wheel").Wheel.instances.get(bpy.context.mode)
        return {"cx": rv.x + rv.width // 2, "cy": bpy.context.window.height - (rv.y + rv.height // 2),
                "radius": w.radius * w.scale}

    def beat(action, cursor, caption, sub="", hold=0.5):
        n = len(live["beats"])
        live["beats"].append({"file": grab(f"b{n:03d}"), "action": action, "cursor": list(cursor),
                              "caption": caption, "sub": sub, "hold": hold, "wheel": cur["wheel"],
                              "geom": wheel_geom()})  # (The wheel in this very screenshot, when it is open.)

    def wheel_shot(apply_beat=None):
        """The open wheel (whole window), cut out later around its centre."""
        _, v = main_area('VIEW_3D')
        rv = region(v)
        win = bpy.context.window
        w = mod("wheels.wheel").Wheel.instances.get(bpy.context.mode)
        name = f"w{len(live['wheels']):03d}"
        live["wheels"][name] = {"file": grab(name), "cx": rv.x + rv.width // 2,
                                "cy": win.height - (rv.y + rv.height // 2), "radius": w.radius * w.scale}
        cur["wheel"] = name
        if apply_beat is not None:
            live["beats"][apply_beat]["wheel"] = name

    def set_theme(**kw):
        for k, v in kw.items():
            setattr(wheel_prefs().theme, k, v)
        redraw()

    steps += [(lambda: setup("MESH", "SCULPT"), 1.5), (split, 1.2), (fit_view, 0.6),
              (lambda: bpy.ops.preferences.addon_expand(module=P), 0.8), (lambda: scroll_prefs(0), 0.8),
              (lambda: ev('MOUSEMOVE', 'NOTHING'), 0.3), (lambda: ev('ESC', 'PRESS'), 0.4)]

    if PART == "themes_live":
        steps += [(lambda: ev('SPACE', 'PRESS'), 1.0), (wheel_shot, 0.2)] + close_wheel()
        steps += [(lambda: win_ev('MOUSEMOVE', 'NOTHING', 560, 760), 0.4),
                  (lambda: beat("idle", (560, 760), "Theme presets", "Ten built-in themes, one click away", 0.8), 0.2)]
        for name in ["Light", "Midnight", "Ember", "Forest", "Paper", "Frost", "High Contrast", "Rose", "Graphite", "Dark"]:
            item = (232, 561 + 22 * MENU_ORDER.index(name))
            steps += [
                (lambda: win_ev('MOUSEMOVE', 'NOTHING', *DROPDOWN), 0.35),
                (lambda name=name: beat("move", DROPDOWN, name, "", 0.15), 0.1),
                (lambda: win_ev('LEFTMOUSE', 'PRESS', *DROPDOWN), 0.05),
                (lambda: win_ev('LEFTMOUSE', 'RELEASE', *DROPDOWN), 0.5),
                (lambda name=name: beat("click", DROPDOWN, name, "", 0.25), 0.1),
                (lambda item=item: win_ev('MOUSEMOVE', 'NOTHING', *item), 0.4),
                (lambda item=item, name=name: beat("move", item, name, "", 0.2), 0.1),
                (lambda item=item: win_ev('LEFTMOUSE', 'PRESS', *item), 0.05),
                (lambda item=item: win_ev('LEFTMOUSE', 'RELEASE', *item), 0.5),
                (lambda item=item, name=name: beat("click", item, name, "", 1.3), 0.1),
                (lambda name=name: note(f"applied {name}", wheel_prefs().theme.active_preset), 0.1),
                (lambda: ev('MOUSEMOVE', 'NOTHING'), 0.2), (lambda: ev('SPACE', 'PRESS'), 0.9),
                (lambda: wheel_shot(len(live["beats"]) - 1), 0.2),
            ] + close_wheel()
    else:
        def slider(v):
            return (int(SLIDER_X0 + SLIDER_W * v), SLIDER_Y)

        def drag(prop, values, caption, sub):
            out = []
            for i, v in enumerate(values):
                out += [(lambda v=v: set_theme(**{prop: v}), 0.25),
                        (lambda v=v, i=i: beat("press" if i == 0 else "drag", slider(v), caption, sub.format(v=v),
                                               0.5 if i in (0, len(values) - 1) else 0.07), 0.1)]
            out.append((lambda: beat("release", slider(values[-1]), caption, sub.format(v=values[-1]), 0.5), 0.1))
            return out

        def click(xy, caption, sub, hold=1.2, **kw):
            return [(lambda: set_theme(**kw), 0.4), (lambda: beat("click", xy, caption, sub, hold), 0.1)]

        T = "tarta_"
        down = [round(0.9 - 0.1 * i, 2) for i in range(8)]          # 0.9 .. 0.2
        up = [round(0.3 + 0.1 * i, 2) for i in range(8)]            # 0.3 .. 1.0
        steps += [(lambda: set_theme(shadow_size=0.061), 0.2), (lambda: ev('SPACE', 'PRESS'), 1.0),
                  (lambda: beat("idle", (560, 900), "Button tints", "Color the pie buttons your way", 0.8), 0.1)]
        steps += click((TINT_X["DISABLED"], TINT_Y), "Tint: Disabled", "Every segment uses the pie color",
                       **{T + "tint_mode": "DISABLED"})
        steps += click((TINT_X["PER_TYPE"], TINT_Y), "Tint: Per Type", "Operators, popups and toggles get their own tint",
                       **{T + "tint_mode": "PER_TYPE"})
        steps += click((TINT_X["CUSTOM"], TINT_Y), "Tint: Custom", "Every button keeps its own color",
                       **{T + "tint_mode": "CUSTOM"})
        steps += click((TARGET_X["OUTLINE"], TARGET_Y), "Target: Outline", "The outline takes the color", 0.6,
                       **{T + "tint_target": "OUTLINE"})
        steps += drag(T + "tint_opacity", down + up, "Target: Outline", "Opacity {v:.1f}")
        steps += click((TARGET_X["ICON"], TARGET_Y), "Target: Icon", "The icon takes the color", 0.6,
                       **{T + "tint_target": "ICON"})
        steps += drag(T + "tint_opacity", [1.0] + down[1:-1] + up[2:], "Target: Icon", "Opacity {v:.1f}")
        steps += click((TARGET_X["FILL"], TARGET_Y), "Target: Fill", "The whole segment is tinted", 0.6,
                       **{T + "tint_target": "FILL"})
        steps += drag(T + "custom_tint_strength", [0.12, 0.2, 0.3, 0.4, 0.5, 0.6, 0.5, 0.4, 0.3, 0.2, 0.12],
                      "Target: Fill", "Strength {v:.2f}")
        steps += click((TARGET_X["COLOR_STRIP"], TARGET_Y), "Target: Color Strip", "The default: a thin strip of color",
                       1.6, **{T + "tint_target": "COLOR_STRIP", T + "tint_opacity": 0.9})
        steps += close_wheel()

    steps += [(lambda: json.dump(live, open(os.path.join(OUT, "live.json"), "w"), indent=1), 0.1)]

else:
    raise SystemExit(f"unknown part {PART!r}")

steps += [(lambda: json.dump(log, open(os.path.join(OUT, "log.json"), "w"), indent=1), 0.1)]
i = [0]


def tick():
    try:
        if i[0] >= len(steps):
            bpy.ops.wm.quit_blender()
            return None
        fn, delay = steps[i[0]]
        i[0] += 1
        fn()
        return delay
    except Exception:
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None


addon_utils.enable(P, default_set=True)
bpy.app.timers.register(tick, first_interval=4)
