"""The promo video's music: an original, synthesized 46 s track (120 BPM, A minor), cut to the edit.

Usage:
    python store/video/make_promo_music.py <out dir>

Uses the instruments, effects and mastering of the FlexSpace marketing kit (make_music.py), found through the
MUSIC_KIT environment variable or at its usual place in the B3D-MySpace repository. Writes <out dir>/promo_music.wav
(48 kHz, 24-bit, -14 LUFS, <= -1 dBTP) and promo_cue.json (bars, sections, hits in seconds and frames).

Timeline (1 beat = 0.5 s = 15 frames, 1 bar = 2 s = 60 frames):
    bars  1-2   COLD     0-4 s    the problem: hunting for brushes. Filtered pad, ticking hats, riser.
    bars  3-4   TITLE    4-8 s    impact + crash: the wheel pops open, the title. Kick on every beat, stab.
    bars  5-9   SCULPT   8-18 s   groove A: kick, claps, offbeat hats, bass pluck, filtered arp.
    bars 10-12  PAINT    18-24 s  crash, groove B: octave bass, ghost hats, the filter opens.
    bars 13-15  DRAW     24-30 s  crash, chord plucks over the groove.
    bars 16-17  WEIGHT   30-34 s  riser + snare roll; a one-beat break at 33.5 s.
    bars 18-20  DROP     34-40 s  impact + crash: sidechained sub, supersaw stabs, lead motif (themes, double ring).
    bar  21     FILL     40-42 s  stab stutter, tom fill, reverse swell.
    bars 22-23  END      42-46 s  end-card impact + crash + Am stab, pad and arp tail; fade 45-46 s.
"""
import importlib.util
import json
import os
import sys

import numpy as np

KIT = os.environ.get("MUSIC_KIT", r"X:\B3D\@jfranmatheu\B3D-MySpace\marketing\flexspace\superhive\src\make_music.py")
spec = importlib.util.spec_from_file_location("make_music", KIT)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

DUR = 46.0
BARS = 23
SECTIONS = [("COLD", 1, 2), ("TITLE", 3, 4), ("SCULPT", 5, 9), ("PAINT", 10, 12), ("DRAW", 13, 15),
            ("WEIGHT", 16, 17), ("DROP", 18, 20), ("FILL", 21, 21), ("END", 22, 23)]
BAR_CHORD = {1: "Am", 2: "F", 3: "Am", 4: "Am", 5: "Am", 6: "F", 7: "C", 8: "G", 9: "Am",
             10: "F", 11: "C", 12: "G", 13: "Am", 14: "F", 15: "C", 16: "G", 17: "G",
             18: "Am", 19: "F", 20: "C", 21: "G", 22: "Am", 23: "Am"}
TITLE_T, PAINT_T, DRAW_T, DROP_T, END_T = 4.0, 18.0, 24.0, 34.0, 42.0
BREAK = (33.5, 34.0)
FADE = (44.8, 46.0)


def section_of(bar):
    for name, a, b in SECTIONS:
        if a <= bar <= b:
            return name
    return None


def build():
    T, BEAT, hz, CH = M.T, M.BEAT, M.hz, M.CHORDS
    drums, bass, pads, arp, stabs, lead, fx = (M.Bus() for _ in range(7))
    rev_send, rev_fx_send = M.Bus(), M.Bus()
    kicks = []

    def K(t, vel=1.0):
        kicks.append(t)
        drums.add(t, M.kick(vel), 0.95)

    def CL(t, vel=1.0):
        c = M.clap(vel)
        drums.add(t, c, 0.42)
        rev_send.add(t, c, 0.16)

    def HH(t, vel=1.0, open_=False, pan=0.15):
        drums.add(t, M.hat(open_, vel), 0.11 if not open_ else 0.085, pan)

    def SN(t, vel=1.0, gain=0.36):
        s = M.snare(vel)
        drums.add(t, s, gain)
        rev_send.add(t, s, 0.12)

    def TM(t, f0, vel=1.0, pan=0.0):
        s = M.tom(f0, vel)
        drums.add(t, s, 0.42, pan)
        rev_send.add(t, s, 0.12, pan)

    def CR(t, vel=1.0, gain=0.22):
        c = M.crash(vel=vel)
        drums.add(t, c, gain)
        rev_send.add(t, c, 0.05)

    def IMP(t, size=1.0, gain=None):
        x = M.impact(size)
        fx.add(t, x, gain if gain is not None else (0.85 if size >= 1 else 0.5))
        rev_fx_send.add(t, x, 0.18)

    def SWELL(t_end, dur=2.0, gain=0.32):
        x = M.reverse_swell(dur)
        fx.add(t_end - dur, x, gain)
        rev_fx_send.add(t_end - dur, x, 0.08)

    def RISER(t0, dur, gain=0.24):
        x = M.noise_riser(dur)
        fx.add(t0, x, gain)
        rev_fx_send.add(t0, x, 0.1)

    # ---- drums
    for bar in range(1, BARS + 1):
        sec = section_of(bar)
        t0 = T(bar)
        for b in range(4):
            tb = t0 + b * BEAT
            if BREAK[0] <= tb < BREAK[1]:
                continue
            if sec == "COLD":
                HH(tb + 0.25, 0.5 + 0.1 * bar, pan=0.25)               # ticking: the clock is running
            elif sec == "TITLE":
                K(tb, 0.95)
                if bar == 4:
                    HH(tb + 0.25, 0.7)
            elif sec in ("SCULPT", "PAINT", "DRAW", "WEIGHT"):
                K(tb, 0.95 if sec == "SCULPT" else 1.0)
                if b in (1, 3) and (sec != "SCULPT" or bar >= 6):
                    CL(tb, 0.9 if sec == "SCULPT" else 1.0)
                HH(tb + 0.25, 0.8 if sec == "SCULPT" else 0.9)
                if sec in ("PAINT", "DRAW", "WEIGHT"):
                    HH(tb + 0.125, 0.4, pan=-0.2)
                    HH(tb + 0.375, 0.4, pan=-0.2)
            elif sec == "DROP":
                K(tb)
                if b in (1, 3):
                    CL(tb)
                for s16 in range(4):
                    if s16 == 2:
                        HH(tb + 0.25, 0.8, open_=True)
                    else:
                        HH(tb + s16 * 0.125, 0.55 if s16 else 0.35, pan=-0.15 if s16 % 2 else 0.2)
            elif sec == "FILL" and b < 2:
                K(tb)
                CL(tb + 0.5) if b == 1 else None
    # snare roll through the weight section into the break: 8ths -> 16ths
    roll = list(np.arange(32.0, 33.0, 0.25)) + list(np.arange(33.0, 33.5, 0.125))
    for tb in roll:
        SN(tb, 0.35 + 0.6 * ((tb - 32.0) / 1.5) ** 1.3, 0.5)
    # tom fill into the end card
    for i, tb in enumerate(np.arange(41.0, 42.0, 0.125)):
        TM(tb, 210 * (0.9 ** i), 0.75 + 0.03 * i, pan=0.5 - i * 0.14)
    for t in (TITLE_T, 8.0, PAINT_T, DRAW_T, DROP_T, END_T):
        CR(t, 1.0, 0.3 if t in (DROP_T, END_T) else 0.22)

    # ---- FX
    IMP(TITLE_T, 1.0)
    IMP(PAINT_T, 0.5)
    IMP(DRAW_T, 0.5)
    IMP(DROP_T, 1.0)
    IMP(END_T, 1.0, 1.0)
    RISER(0.6, 3.4, 0.22)                                           # the cold open builds into the title hit
    SWELL(TITLE_T, 1.5, 0.3)
    RISER(30.0, 4.0, 0.34)
    pr = M.pitch_riser(2.0, hz("A3"), hz("A4"))
    fx.add(32.0, pr, 0.2)
    rev_fx_send.add(32.0, pr, 0.08)
    SWELL(DROP_T, 2.0, 0.34)
    SWELL(END_T, 1.0, 0.22)
    RISER(16.0, 2.0, 0.12)
    RISER(22.0, 2.0, 0.12)

    # ---- bass
    for bar in range(1, BARS + 1):
        sec = section_of(bar)
        f = hz(CH[BAR_CHORD[bar]]["root"])
        t0 = T(bar)
        if sec in ("SCULPT", "PAINT", "DRAW", "WEIGHT"):
            for b in range(4):
                tb = t0 + b * BEAT
                if BREAK[0] <= tb < BREAK[1]:
                    continue
                bass.add(tb + 0.25, M.bass_pluck(f), 0.5)
                if sec != "SCULPT":
                    bass.add(tb + 0.375, M.bass_pluck(f * 2), 0.22)
        elif sec == "DROP":
            bass.add(t0, M.drop_bass(f, M.BAR), 0.62)
        elif sec == "FILL":
            bass.add(t0, M.drop_bass(f, M.BAR - 1.0), 0.55)
    n = int(3.9 * M.SR)                                             # sub under the title
    bass.add(TITLE_T, np.sin(2 * np.pi * hz("A1") * M.tt(n)) * np.exp(-M.tt(n) / 1.4) * M.gate_env(n, 0.02, 0.3), 0.3)
    n = int(4.2 * M.SR)                                             # sub tail under the end card
    bass.add(END_T, np.sin(2 * np.pi * hz("A1") * M.tt(n)) * np.exp(-M.tt(n) / 2.0) * M.gate_env(n, 0.3, 0.5), 0.3)

    # ---- pads
    for bar in range(1, BARS + 1):
        sec = section_of(bar)
        ch = CH[BAR_CHORD[bar]]
        t0 = T(bar)
        if sec == "END":
            if bar == 22:
                for m in ch["pad"] + ["A2", "E3"]:
                    p = M.pad_note(hz(m), 4.2, a=0.05, r=2.0)
                    pads.add(t0, p, 0.3)
                    rev_send.add(t0, p, 0.14)
            continue
        if sec == "DROP":
            for m in ch["pad"]:
                p = M.pad_note(hz(m), M.BAR + 0.35, a=1.1, r=0.35)
                pads.add(t0, p, 0.34)
                rev_send.add(t0, p, 0.14)
            continue
        g = {"COLD": 0.3, "TITLE": 0.34}.get(sec, 0.3)
        for m in ch["pad"]:
            p = M.pad_note(hz(m), M.BAR + 0.3, a=0.6 if sec == "COLD" else 0.06, r=0.3)
            pads.add(t0, p, g)
            rev_send.add(t0, p, g * 0.35)

    # ---- arp (16ths), from the sculpt section
    pat = [0, 1, 2, 3, 1, 2, 3, 2, 0, 1, 2, 3, 2, 3, 1, 2]
    for bar in range(5, BARS + 1):
        sec = section_of(bar)
        ch = CH[BAR_CHORD[bar]]["arp"]
        g = {"SCULPT": 0.14, "PAINT": 0.15, "DRAW": 0.15, "WEIGHT": 0.15, "DROP": 0.09, "FILL": 0.09, "END": 0.13}[sec]
        for i in range(16):
            tb = T(bar) + i * 0.125
            if BREAK[0] <= tb < BREAK[1]:
                continue
            g_i = g * max(0.0, 1 - (tb - END_T) / 4.0) if sec == "END" else g * (1.0 if i % 4 == 0 else 0.75)
            arp.add(tb, M.pluck(hz(ch[pat[i]]), 0.2, 3200.0), g_i, pan=0.3 if i % 2 else -0.3)

    # ---- chord plucks in the drawing section, stabs and lead in the drop
    for bar in range(13, 16):
        ch = CH[BAR_CHORD[bar]]["stab"]
        for off in (0.0, 0.75, 1.5):
            s = M.stab(ch, 0.18, 3800.0)
            stabs.add(T(bar) + off, s, 0.35)
            rev_send.add(T(bar) + off, s, 0.1)
    s = M.stab(CH["Am"]["stab"], 0.6, 6000.0)                        # title stab
    stabs.add(TITLE_T, s, 0.8)
    rev_send.add(TITLE_T, s, 0.3)
    for bar in range(18, 21):
        ch = CH[BAR_CHORD[bar]]["stab"]
        t0 = T(bar)
        s = M.stab(ch, 0.72)
        stabs.add(t0, s, 0.95)
        rev_send.add(t0, s, 0.25)
        s2 = M.stab(ch, 0.2, 4000.0)
        stabs.add(t0 + 0.75, s2, 0.5)
        stabs.add(t0 + 1.25, s2, 0.4)
    for i, tb in enumerate(np.arange(T(21), T(21) + 1.0, 0.25)):      # stab stutter in the fill
        stabs.add(tb, M.stab(CH["G"]["stab"], 0.12, 3000 + 600 * i), 0.4)
    s = M.stab(CH["Am"]["stab"], 1.4, 6000.0)                        # end-card chord
    stabs.add(END_T, s, 0.9)
    rev_send.add(END_T, s, 0.35)
    motif_pos = [0, 3, 6, 8, 10, 12, 14]
    motif = {"Am": ["E5", "E5", "A5", "G5", "E5", "D5", "C5"], "F": ["C5", "C5", "F5", "E5", "C5", "A4", "C5"],
             "C": ["E5", "E5", "G5", "E5", "D5", "C5", "D5"]}
    for bar in range(18, 21):
        for pos, m in zip(motif_pos, motif[BAR_CHORD[bar]]):
            tb = T(bar) + pos * 0.125
            x = M.lead_note(hz(m), 0.3)
            lead.add(tb, x, 0.3)
            rev_send.add(tb, x, 0.08)

    return dict(drums=drums.x, bass=bass.x, pads=pads.x, arp=arp.x, stabs=stabs.x, lead=lead.x, fx=fx.x,
                rev=rev_send.x, rev_fx=rev_fx_send.x, kicks=kicks)


def process(parts):
    auto, sweep, S = M.auto, M.sweep, M.S
    nt = M.NT
    sc = M.sidechain_curve(parts["kicks"], -8.0, 0.12)

    def sc_amt(k):
        return (1 - (1 - sc) * k)[:, None]

    in_drop = auto([(0, 0), (DROP_T - 0.01, 0), (DROP_T, 1), (END_T - 0.01, 1), (END_T, 0), (60, 0)], n=nt, log=False)
    in_groove = auto([(0, 0), (7.99, 0), (8.0, 1), (DROP_T - 0.01, 1), (DROP_T, 0), (60, 0)], n=nt, log=False)
    bass = parts["bass"] * (1 - (1 - sc_amt(1.0)) * in_drop[:, None])
    pads_pump = 1 - (1 - sc_amt(0.75)) * (in_drop + 0.5 * in_groove)[:, None]
    pad_fc = auto([(0, 380), (3.9, 1400), (4.0, 900), (8.0, 900), (PAINT_T, 2200), (DRAW_T, 3600), (BREAK[0], 6500),
                   (DROP_T, 7500), (END_T - 0.01, 7500), (END_T, 3500), (FADE[1], 350), (60, 350)], n=nt)
    pads = sweep(parts["pads"], "lp", pad_fc, q=0.9) * pads_pump
    arp_fc = auto([(0, 700), (8, 900), (PAINT_T, 2000), (DRAW_T, 3000), (BREAK[0], 6000), (DROP_T, 4500),
                   (END_T - 0.01, 4500), (END_T, 3000), (FADE[1], 400), (60, 400)], n=nt)
    arp = sweep(parts["arp"], "lp", arp_fc, q=1.0)
    arp = arp + M.pingpong(arp)
    arp = arp * (1 - (1 - sc_amt(0.4)) * in_drop[:, None])
    stabs = parts["stabs"] * (1 - (1 - sc_amt(0.6)) * in_drop[:, None])
    music = pads + arp + stabs + parts["lead"]
    hp_fc = auto([(0, 20), (32.0, 20), (BREAK[0], 1200), (DROP_T - 0.001, 1500), (DROP_T, 20), (60, 20)], n=nt)
    music = sweep(music, "hp", hp_fc, q=0.707)

    energy = 10 ** (auto([(0, -6.0), (3.99, -4.0), (4.0, -3.5), (8.0, -3.0), (PAINT_T, -2.5), (DRAW_T, -2.0),
                          (BREAK[0], -1.0), (DROP_T, 0.0), (60, 0.0)], n=nt, log=False) / 20)[:, None]
    bass = bass * energy
    drums = np.tanh(1.25 * parts["drums"] * energy) / 1.25 * 1.15
    rev = M.reverb(parts["rev"], M.make_ir()) * 0.55
    rev_fx = M.reverb(parts["rev_fx"], M.make_ir(2.4)) * 0.55
    rev = sweep(rev, "hp", hp_fc, q=0.707)

    brk = np.ones(nt)
    i0, i1, i2 = S(BREAK[0] - 0.012), S(BREAK[0]), S(BREAK[1])
    brk[i0:i1] = np.linspace(1, 0, i1 - i0)
    brk[i1:i2] = 0.0
    brk = brk[:, None]
    groups = dict(drums=drums * brk, bass=bass * brk, music=music * brk, fx=parts["fx"], reverb=rev * brk + rev_fx)
    full = sum(groups.values())
    fade = np.ones(nt)
    f0, f1 = S(FADE[0]), S(FADE[1])
    fade[f0:f1] = np.cos(np.linspace(0, np.pi / 2, f1 - f0)) ** 2
    fade[f1:] = 0
    return (M.filt(full, "hp", 24, 0.6) * fade[:, None])[:M.N]


def cue():
    fr = lambda t: int(round(t * M.FPS))  # noqa: E731
    return dict(
        title="Sculpt-Paint Wheel 2 promo music (original, synthesized)", bpm=M.BPM, key="A minor", fps=M.FPS,
        duration_s=DUR, duration_frames=fr(DUR), beat_frames=15, bar_frames=60,
        sections=[dict(name=n, bars=[a, b], t=[M.T(a), M.T(b + 1)], frames=[fr(M.T(a)), fr(M.T(b + 1))])
                  for n, a, b in SECTIONS],
        hits=dict(title=fr(TITLE_T), paint=fr(PAINT_T), draw=fr(DRAW_T), drop=fr(DROP_T), end=fr(END_T),
                  break_=[fr(BREAK[0]), fr(BREAK[1])], fade=[fr(FADE[0]), fr(FADE[1])]),
    )


def main():
    M.rng = np.random.default_rng(20261125)
    M._set_length(DUR)
    print("rendering ...", flush=True)
    full = process(build())
    print("  pre-master: %.2f LUFS, TP %.2f dBTP" % (M.lufs(full), M.true_peak_db(full)), flush=True)
    path = os.path.join(OUT, "promo_music.wav")
    M.master_file(full, "promo", path)
    m = M.ffmpeg_measure(path)
    c = cue()
    c["loudness"] = m
    json.dump(c, open(os.path.join(OUT, "promo_cue.json"), "w"), indent=1)
    print(json.dumps(m, indent=1))
    print("wrote", path)


main()
