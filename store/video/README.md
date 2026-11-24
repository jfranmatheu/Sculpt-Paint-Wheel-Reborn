# Promo video

A 46 s promo of Sculpt-Paint Wheel 2, built from the real add-on running in Blender 5.3, with original synthesized
music. Outputs `sculpt-paint-wheel-2_16x9.mp4` (1920x1080, YouTube / store), `_1x1.mp4` (1080x1080, feeds) and
`_9x16.mp4` (1080x1920, Shorts / Reels / TikTok), all from the same timeline.

## 1. Record (Blender)

`rec_promo.py` drives the wheel with simulated input and saves one window screenshot per frame (30 fps) plus
`meta.json` (pointer position, button and key state per frame, marks). One Blender per sequence:

| Sequence | What happens |
|---|---|
| `pain` | The default layout: the cursor hunting through the toolbar and the asset shelf |
| `sculpt` | Space, pick Clay Strips, strokes on the head; drag the centre for a bigger brush; pick Crease Polish, strokes |
| `texture` | Three colors picked on the wheel's hue ring (orange, teal, violet), a stroke after each |
| `gpencil` | Ink Pen + blue, a wave and a loop; Marker Bold + orange, two strokes |
| `weight` | Weight 1.0 then 0.5 from the dial, strokes after each |
| `themes` | The wheel open while the ten themes switch |
| `double` | Shift + mouse wheel to a 34-brush set: the wheel grows into the double ring |

```
BLENDER_USER_RESOURCES=<profile with the extension as user_default/spwheel, no saved preferences>
blender --factory-startup --enable-event-simulate --window-geometry 0 0 2560 1440 \
        --python store/video/rec_promo.py -- <recordings dir> <sequence>
```

The window is 2560x1440 at 1.33x UI scale (the 1920x1080 layout with more pixels), so the edit can reframe and push
in without upscaling past 1.1x. Clicks land on the wheel's real widgets: their positions come from the wheel itself.

## 2. Music

`make_promo_music.py <audio dir>` synthesizes the track (120 BPM, A minor, 23 bars) with the instruments, effects and
mastering of the FlexSpace marketing kit (`make_music.py`, found through `MUSIC_KIT`), and writes `promo_music.wav`
(-14 LUFS, -1.3 dBTP) and `promo_cue.json`. Its sections line up with the edit: cold open, title hit at 4 s, sculpt,
paint (18 s), draw (24 s), weight with a one-beat break, the drop at 34 s, fill, end card at 42 s.

## 3. Edit

```
py -3.10 store/video/make_promo.py <recordings dir> <audio dir> <out dir> --fmt all
py -3.10 store/video/make_promo.py ... --fmt 16x9 --stills 4.6,12.5,35.0     (stills to check a layout)
```

Shots map timeline frames to recording frames (speed ramps; blended frames for slow motion) and to an eased camera
over the recording. On top: the pointer and click ripples (from the logged pointer), a Space keycap that lights up
while held, kinetic type, whip pans between scenes, flashes, RGB split and punch-ins on the hits, a 2x2 "every mode"
grid, a stutter montage and the end card. Audio: the music plus click and whoosh sounds, loudness-normalised.

Needs Python 3.10 with numpy, opencv-python, Pillow and soundfile, ffmpeg on PATH, and Segoe UI Variable (Windows 11).
