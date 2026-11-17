"""Builds assets/audio/ (task5): synthesizes original sounds with numpy (CC0, ours) and copies a few
CC0 Kenney sounds (kenney.nl: RPG Audio, Interface Sounds, Music Jingles) when their packs are given.

    python tools/make_audio.py [--kenney DIR]   DIR holds the unzipped Kenney packs (optional)

Everything is written as Ogg Vorbis (soundfile / libsndfile). Deterministic (seeded).
"""
import glob
import os
import shutil
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'assets', 'audio')
SR = 44100
rng = np.random.default_rng(20261117)
CREDITS = []


def t(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.01, r=0.2, shape=2.0):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** shape
    return e


def lp(x, cutoff):
    """One-pole low-pass (cutoff Hz, scalar or array)."""
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = np.exp(-2 * np.pi * c / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def bp(x, f, q=5.0):
    """Biquad band-pass at f (scalar)."""
    w = 2 * np.pi * f / SR
    al = np.sin(w) / (2 * q)
    b0, b1, b2 = al, 0, -al
    a0, a1, a2 = 1 + al, -2 * np.cos(w), 1 - al
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        yi = (b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x[i], y1, yi
        y[i] = yi
    return y


def noise(d):
    return rng.standard_normal(int(d * SR))


def norm(x, peak=0.7):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def write(sub, name, x, peak=0.7, credit='synthesized for Ghostopia (CC0)'):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    p = os.path.join(OUT, sub, name + '.ogg')
    x = norm(np.asarray(x, float), peak)
    data = np.ascontiguousarray((x.T if x.ndim == 2 else x).astype(np.float32))
    ch = 2 if x.ndim == 2 else 1
    # libsndfile's Vorbis encoder overflows the stack on large single writes: write in blocks.
    with sf.SoundFile(p, 'w', SR, ch, format='OGG', subtype='VORBIS') as fh:
        for i in range(0, len(data), 4096):
            fh.write(data[i:i + 4096])
    CREDITS.append((f'{sub}/{name}.ogg', credit))


def loopify(x, fade=1.0):
    """Crossfade the tail into the head so the file loops without a click."""
    n = int(fade * SR)
    head, tail = x[..., :n], x[..., -n:]
    w = np.linspace(0, 1, n)
    mixed = tail * (1 - w) + head * w
    out = x[..., n:].copy()
    out[..., -n:] = mixed
    return out


def formant_voice(f0, dur, formants, breath=0.15, vib=5.0, vib_amt=0.02):
    """Glottal pulse train through formant band-passes. f0 may be an array (glide)."""
    n = int(dur * SR)
    f0 = np.broadcast_to(np.asarray(f0, float), (n,)) * (1 + vib_amt * np.sin(2 * np.pi * vib * t(dur)))
    ph = np.cumsum(f0 / SR)
    src = (ph % 1.0) * 2 - 1           # saw
    src = src + breath * rng.standard_normal(n)
    out = np.zeros(n)
    for f, g, q in formants:
        out += g * bp(src, f, q)
    return out


VOWEL = {'a': [(800, 1.0, 6), (1200, 0.6, 8), (2500, 0.25, 10)],
         'e': [(500, 1.0, 6), (1800, 0.6, 9), (2600, 0.3, 10)],
         'o': [(450, 1.0, 6), (800, 0.6, 8), (2600, 0.15, 10)],
         'u': [(320, 1.0, 6), (700, 0.4, 8), (2400, 0.1, 10)],
         'i': [(300, 1.0, 6), (2300, 0.6, 10), (3000, 0.3, 10)]}


# ---------------------------------------------------------------- sfx

def creak(dur, f_lo, f_hi, rough, seed):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    tt = t(dur)
    f = f_lo + (f_hi - f_lo) * (0.5 + 0.5 * np.sin(2 * np.pi * r.uniform(0.3, 0.9) * tt + r.uniform(0, 6)))
    f *= 1 + 0.15 * np.cumsum(r.standard_normal(n)) / np.sqrt(n) * 3
    ph = np.cumsum(np.abs(f) / SR)
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)    # stick-slip clicks
    pulses *= 1 + rough * r.standard_normal(n)
    out = bp(pulses, 900, 3) + 0.6 * bp(pulses, 1900, 4) + 0.3 * bp(pulses, 3300, 6)
    return out * env(n, 0.05, 0.25)


def sfx():
    for i, (d, lo, hi) in enumerate([(1.1, 18, 60), (0.8, 25, 80), (1.4, 14, 45)], 1):
        write('sfx', f'creak_door_{i}', creak(d, lo, hi, 0.4, i))
    for i, (d, lo, hi) in enumerate([(0.45, 40, 120), (0.6, 30, 90)], 1):
        write('sfx', f'creak_floor_{i}', lp(creak(d, lo, hi, 0.6, 10 + i), 2200))
    # door slam: low thump + wood rattle
    d = 0.9
    x = lp(noise(d), 300) * np.exp(-t(d) * 9) * 3 + bp(noise(d), 180, 2) * np.exp(-t(d) * 6)
    x += 0.4 * bp(noise(d), 1400, 3) * np.exp(-t(d) * 20)
    write('sfx', 'door_slam', x, 0.85)
    # candle snuff: soft breathy puff
    d = 0.5
    write('sfx', 'candle_snuff', lp(noise(d), 1200) * env(int(d * SR), 0.02, 0.35) * np.exp(-t(d) * 4), 0.5)
    # match strike + flare
    d = 0.9
    strike = bp(noise(d), 3500, 2) * np.exp(-t(d) * 14)
    flare = lp(noise(d), 600) * np.clip(t(d) - 0.08, 0, None) * np.exp(-t(d) * 3) * 4
    write('sfx', 'candle_relight', strike + flare, 0.55)
    # whooshes
    for i, (d, f0, f1) in enumerate([(0.7, 400, 1600), (0.9, 1800, 500), (0.6, 600, 2200)], 1):
        n = int(d * SR)
        x = noise(d)
        cut = np.linspace(f0, f1, n)
        y = lp(x, cut) - lp(x, cut * 0.4)
        write('sfx', f'whoosh_{i}', y * np.sin(np.linspace(0, np.pi, n)) ** 2, 0.55)
    # the BOO: a breathy cute "boOOoo" rising then falling
    d = 1.3
    n = int(d * SR)
    f0 = 170 + 90 * np.sin(np.linspace(0, np.pi, n)) ** 1.5
    v = formant_voice(f0, d, VOWEL['u'], breath=0.5, vib=6, vib_amt=0.04)
    write('sfx', 'boo', v * env(n, 0.12, 0.4) + 0.2 * lp(noise(d), 800) * env(n, 0.1, 0.5), 0.8)
    # gasps (inhaled breath with a little voice)
    for i, (f, vw) in enumerate([(380, 'a'), (460, 'o')], 1):
        d = 0.45
        n = int(d * SR)
        x = bp(noise(d), 1500, 1.5) * env(n, 0.03, 0.2) + 0.5 * formant_voice(np.linspace(f, f * 1.3, n), d, VOWEL[vw], 0.6) * env(n, 0.05, 0.2)
        write('sfx', f'gasp_{i}', x, 0.6)
    # cartoony screams: wobbly gliding "aaaAAH" / "eeek" / "waah"
    for i, (fs, fe, vw, d) in enumerate([(420, 900, 'a', 1.0), (700, 1300, 'i', 0.8), (300, 650, 'a', 1.1)], 1):
        n = int(d * SR)
        glide = np.interp(np.arange(n), [0, n * 0.25, n], [fs, fe, fe * 0.85])
        x = formant_voice(glide, d, VOWEL[vw], breath=0.25, vib=11, vib_amt=0.06) * env(n, 0.03, 0.3)
        write('sfx', f'scream_{i}', x, 0.75)
    # laughs: "ha-ha-ha" pulses (nervous / hearty)
    for i, (f, k, rate) in enumerate([(260, 5, 6.5), (150, 6, 5.0)], 1):
        d = k / rate + 0.3
        n = int(d * SR)
        tt = t(d)
        gate = np.clip(np.sin(2 * np.pi * rate * tt), 0, None) ** 1.5 * (tt < k / rate)
        f0 = f * (1 + 0.15 * np.sin(2 * np.pi * rate * tt)) * np.linspace(1.1, 0.9, n)
        x = formant_voice(f0, d, VOWEL['a'], breath=0.5) * gate
        write('sfx', f'laugh_{i}', x, 0.65)
    # "hello?": two syllables, rising
    d1, d2 = 0.22, 0.42
    a = formant_voice(np.linspace(220, 240, int(d1 * SR)), d1, VOWEL['e'], 0.3) * env(int(d1 * SR), 0.03, 0.05)
    b = formant_voice(np.linspace(230, 340, int(d2 * SR)), d2, VOWEL['o'], 0.3) * env(int(d2 * SR), 0.02, 0.15)
    write('sfx', 'hello', np.concatenate([bp(noise(0.05), 2000, 1) * 0.3, a, b]), 0.6)
    # mining hits
    for i in (1, 2):
        d = 0.3
        n = int(d * SR)
        write('sfx', f'mine_dirt_{i}', lp(noise(d), 500 + 200 * i) * np.exp(-t(d) * 18) + 0.3 * bp(noise(d), 160, 2) * np.exp(-t(d) * 12), 0.7)
        stone = np.zeros(n)
        for f, dec in [(1800 + 300 * i, 30), (2900, 40), (4700, 55), (700, 25)]:
            stone += np.sin(2 * np.pi * f * t(d)) * np.exp(-t(d) * dec)
        write('sfx', f'mine_stone_{i}', stone + bp(noise(d), 3000, 2) * np.exp(-t(d) * 50), 0.7)
        wood = np.zeros(n)
        for f, dec in [(420 + 60 * i, 22), (980, 30), (1500, 40)]:
            wood += np.sin(2 * np.pi * f * t(d)) * np.exp(-t(d) * dec)
        write('sfx', f'mine_wood_{i}', wood + 0.5 * bp(noise(d), 900, 2) * np.exp(-t(d) * 35), 0.7)
        d = 0.35
        n = int(d * SR)
        x = noise(d)
        sw = lp(x, np.linspace(6000, 2500, n)) - lp(x, 1500)
        write('sfx', f'mine_plant_{i}', sw * np.sin(np.linspace(0, np.pi, n)) ** 2, 0.55)
    d = 0.6
    write('sfx', 'block_break', lp(noise(d), 900) * np.exp(-t(d) * 8) + 0.5 * bp(noise(d), 2400, 2) * np.exp(-t(d) * 14), 0.75)
    d = 0.25
    write('sfx', 'block_place', lp(noise(d), 400) * np.exp(-t(d) * 25) + np.sin(2 * np.pi * 140 * t(d)) * np.exp(-t(d) * 30), 0.7)
    # magical bits
    d = 1.4
    x = np.zeros(int(d * SR))
    for k, f in enumerate([1318.5, 1568.0, 1975.5, 2637.0]):
        s0 = int(k * 0.09 * SR)
        tt = t(d)[: len(x) - s0]
        x[s0:] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 4)
    write('sfx', 'fragment_chime', x, 0.6)
    d = 1.0
    stamp = lp(noise(d), 250) * np.exp(-t(d) * 14) * 3 + np.sin(2 * np.pi * 80 * t(d)) * np.exp(-t(d) * 10)
    sparkle = np.zeros(int(d * SR))
    for k in range(10):
        s0 = int((0.05 + k * 0.05) * SR)
        f = 2000 + 300 * k
        tt = t(d)[: len(sparkle) - s0]
        sparkle[s0:] += 0.25 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9)
    write('sfx', 'grade_stamp', stamp + sparkle, 0.85)
    d = 2.0
    n = int(d * SR)
    f = np.linspace(1800, 300, n)
    write('sfx', 'scatter', np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.02, 1.5) * 0.4 + (lp(noise(d), np.linspace(5000, 400, n)) - lp(noise(d), 200)) * env(n, 0.02, 1.2), 0.6)
    d = 0.5
    write('sfx', 'hurt', bp(noise(d), 4000, 1.2) * env(int(d * SR), 0.01, 0.3) * (1 + 0.5 * np.sin(2 * np.pi * 30 * t(d))), 0.4)
    d = 4.0
    bell = np.zeros(int(d * SR))
    for f, g, dec in [(220, 1, 0.8), (440 * 1.19, 0.5, 1.2), (220 * 2.0, 0.4, 1.0), (220 * 2.76, 0.3, 1.6), (220 * 5.4, 0.15, 2.5)]:
        bell += g * np.sin(2 * np.pi * f * t(d)) * np.exp(-t(d) * dec)
    write('sfx', 'dawn_warning', bell, 0.6)
    d = 1.2
    ting = np.zeros(int(d * SR))
    for f, dec in [(2093, 3), (2093 * 2.4, 5), (2093 * 3.9, 7)]:
        ting += np.sin(2 * np.pi * f * t(d)) * np.exp(-t(d) * dec)
    write('sfx', 'craft', ting + bp(noise(d), 3000, 3) * np.exp(-t(d) * 40), 0.6)
    d = 0.18
    write('sfx', 'pickup', np.sin(2 * np.pi * np.cumsum(np.linspace(800, 1400, int(d * SR))) / SR) * env(int(d * SR), 0.005, 0.1), 0.45)
    for i in (1, 2):
        d = 0.18
        write('sfx', f'footstep_{i}', lp(noise(d), 350 + 120 * i) * np.exp(-t(d) * 30), 0.5)
    # UI
    d = 0.06
    write('sfx', 'ui_click', np.sin(2 * np.pi * 1200 * t(d)) * np.exp(-t(d) * 70), 0.45)
    write('sfx', 'ui_hover', np.sin(2 * np.pi * 1800 * t(d)) * np.exp(-t(d) * 90), 0.2)
    d = 0.25
    write('sfx', 'ui_open', np.sin(2 * np.pi * np.cumsum(np.linspace(500, 900, int(d * SR))) / SR) * env(int(d * SR), 0.01, 0.15), 0.4)
    write('sfx', 'ui_close', np.sin(2 * np.pi * np.cumsum(np.linspace(900, 500, int(d * SR))) / SR) * env(int(d * SR), 0.01, 0.15), 0.4)
    # level up: little rising arpeggio (music box)
    write('sfx', 'level_up', music_box_notes([(0, 72), (0.12, 76), (0.24, 79), (0.36, 84), (0.48, 88)], 2.0), 0.7)


# ---------------------------------------------------------------- ambience

def stereo(l, r):
    return np.vstack([l, r])


def ambience():
    d = 40.0
    n = int(d * SR)
    tt = t(d)
    gust = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * tt) * np.sin(2 * np.pi * 0.013 * tt + 1)
    wl = (lp(noise(d), 300 + 500 * gust) - lp(noise(d), 80)) * (0.3 + 0.7 * gust)
    wr = (lp(noise(d), 320 + 480 * gust) - lp(noise(d), 80)) * (0.3 + 0.7 * gust)
    write('ambience', 'wind_loop', loopify(stereo(wl, wr), 2.0), 0.5)
    # crickets: chirp trains at a few pitches
    x = np.zeros((2, n))
    for k in range(9):
        f = rng.uniform(4200, 5200)
        period = rng.uniform(0.6, 1.4)
        pan = rng.uniform(0.15, 0.85)
        start = rng.uniform(0, period)
        while start < d - 0.3:
            for c in range(3):
                s0 = int((start + c * 0.045) * SR)
                ln = int(0.03 * SR)
                ch = np.sin(2 * np.pi * f * np.arange(ln) / SR) * np.hanning(ln) * rng.uniform(0.3, 0.6)
                x[0, s0:s0 + ln] += ch * (1 - pan)
                x[1, s0:s0 + ln] += ch * pan
            start += period * rng.uniform(0.9, 1.1)
    x += 0.05 * stereo(lp(noise(d), 400), lp(noise(d), 400))
    write('ambience', 'night_crickets_loop', loopify(x, 1.5), 0.45)
    # stream: bubbly band noise
    mod = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 0.7 * tt) * np.sin(2 * np.pi * 1.9 * tt))
    sl = (lp(noise(d), 2500) - lp(noise(d), 400)) * mod
    sr = (lp(noise(d), 2600) - lp(noise(d), 420)) * mod[::-1]
    write('ambience', 'stream_loop', loopify(stereo(sl, sr), 2.0), 0.5)
    # windmill: slow periodic wooden creaks over wind (3.5 rpm, 4 sails -> one creak every ~4.3 s)
    x = 0.25 * (lp(noise(d), 500) - lp(noise(d), 90))
    for k in range(int(d / 4.3)):
        c = creak(1.2, 10, 30, 0.5, 100 + k) * 0.8
        s0 = int((k * 4.3 + 0.5) * SR)
        x[s0:s0 + len(c)] += c[: max(0, min(len(c), n - s0))]
    write('ambience', 'windmill_loop', loopify(stereo(x, np.roll(x, 900)), 1.5), 0.5)
    # tavern murmur: many soft formant voices with syllable gates + clinks
    x = np.zeros(n)
    for k in range(10):
        f0 = rng.uniform(110, 260)
        vw = rng.choice(list(VOWEL))
        rate = rng.uniform(3, 5)
        g = np.clip(np.sin(2 * np.pi * rate * tt + rng.uniform(0, 6)), 0, None) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(0.05, 0.2) * tt + rng.uniform(0, 6))) ** 2
        x += lp(formant_voice(f0 * (1 + 0.1 * np.sin(2 * np.pi * 0.3 * tt)), d, VOWEL[vw], 0.4), 1800) * g * 0.3
    for k in range(int(d / 2.5)):
        s0 = int(rng.uniform(0, d - 0.5) * SR)
        ln = int(0.3 * SR)
        f = rng.uniform(2500, 3800)
        x[s0:s0 + ln] += 0.3 * np.sin(2 * np.pi * f * np.arange(ln) / SR) * np.exp(-np.arange(ln) / SR * 18)
    write('ambience', 'tavern_murmur_loop', loopify(stereo(x, np.roll(x, 2000)), 1.5), 0.45)
    # washed-out day: soft wind + sparse bird chirps
    x = 0.4 * (lp(noise(d), 700) - lp(noise(d), 150))
    for k in range(int(d / 1.8)):
        s0 = int(rng.uniform(0, d - 0.6) * SR)
        ln = int(rng.uniform(0.08, 0.2) * SR)
        f = np.linspace(rng.uniform(2500, 3500), rng.uniform(3500, 5000), ln)
        ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(ln) * 0.3
        x[s0:s0 + ln] += ch
    write('ambience', 'day_loop', loopify(stereo(x, np.roll(x, 3000)), 1.5), 0.4)


# ---------------------------------------------------------------- music

def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def music_box_notes(notes, dur, bright=1.0):
    x = np.zeros(int(dur * SR))
    for start, m in notes:
        s0 = int(start * SR)
        ln = min(int(2.2 * SR), len(x) - s0)
        if ln <= 0:
            continue
        tt = np.arange(ln) / SR
        f = midi(m)
        tone = (np.sin(2 * np.pi * f * tt) + 0.35 * bright * np.sin(2 * np.pi * f * 3.01 * tt) * np.exp(-tt * 6)
                + 0.15 * np.sin(2 * np.pi * f * 5.43 * tt) * np.exp(-tt * 10))
        x[s0:s0 + ln] += tone * np.exp(-tt * 2.2) * (1 - np.exp(-tt * 400))
    return x


def music():
    # Menu: cozy-eerie music box waltz in A minor, 3/4 at 96 bpm, 16 bars.
    beat = 60 / 96
    melody = [69, 72, 76, 74, 72, 71, 72, 69, 64, 67, 71, 69, 68, 71, 76, None,
              69, 72, 76, 77, 76, 74, 72, 74, 76, 72, 69, 71, 68, 64, 69, None]
    bass = [45, 52, 48, 43, 41, 48, 40, 47, 45, 52, 48, 43, 41, 40, 45, 45]
    notes = []
    for i, m in enumerate(melody):
        if m is not None:
            notes.append((i * 1.5 * beat, m))
    for b, m in enumerate(bass):
        bar = b * 3 * beat
        notes += [(bar, m + 12), (bar + beat, m + 19), (bar + 2 * beat, m + 24)]
    dur = 16 * 3 * beat + 2.0
    x = music_box_notes(notes, dur)
    rev = np.zeros_like(x)
    for dly, g in [(0.083, 0.35), (0.131, 0.28), (0.197, 0.2), (0.271, 0.15)]:
        k = int(dly * SR)
        rev[k:] += g * x[:-k]
    x = x + lp(rev, 3000)
    write('music', 'menu_music_box', loopify(stereo(x, np.roll(x, 400)), 2.0), 0.6)
    # Night theme: soft pad + pizzicato bass + celesta melody, D dorian, 80 bpm, 24 bars of 4/4.
    beat = 60 / 80
    bars = 24
    dur = bars * 4 * beat + 2.0
    n = int(dur * SR)
    pad = np.zeros(n)
    chords = [[50, 57, 62, 65], [48, 55, 60, 64], [46, 53, 58, 62], [45, 52, 57, 61]]
    for b in range(bars):
        ch = chords[(b // 2) % 4]
        s0 = int(b * 4 * beat * SR)
        ln = int(4 * beat * SR)
        tt = np.arange(ln) / SR
        seg = sum(np.sin(2 * np.pi * midi(m) * tt) + 0.3 * np.sin(2 * np.pi * midi(m) * 2.003 * tt) for m in ch)
        e = np.minimum(1, tt / 0.8) * np.minimum(1, (4 * beat - tt) / 0.8)
        pad[s0:s0 + ln] += lp(seg * e, 1200)[:max(0, min(ln, n - s0))] * 0.15
    pizz = []
    for b in range(bars):
        root = chords[(b // 2) % 4][0] - 12
        pizz += [(b * 4 * beat, root), (b * 4 * beat + 2 * beat, root + 7)]
    bassl = music_box_notes(pizz, dur, bright=0.2)
    mel_pat = [74, None, 77, 76, 74, None, 72, 74, 69, None, None, 72, 74, 76, 77, None,
               81, None, 79, 77, 76, None, 74, 72, 74, None, None, None, None, None, None, None]
    mel = []
    for b in range(4, bars):
        for k in range(8):
            m = mel_pat[((b - 4) * 8 + k) % len(mel_pat)]
            if m is not None:
                mel.append((b * 4 * beat + k * 0.5 * beat, m))
    celesta = music_box_notes(mel, dur, bright=0.6) * 0.5
    x = pad + 0.6 * bassl + celesta
    rev = np.zeros_like(x)
    for dly, g in [(0.09, 0.3), (0.15, 0.25), (0.23, 0.2), (0.33, 0.15)]:
        k = int(dly * SR)
        rev[k:] += g * x[:-k]
    x = x + lp(rev, 2500)
    write('music', 'night_theme', loopify(stereo(x, np.roll(x, 600)), 2.0), 0.55)
    # Day: very quiet thin drone (the ghost should feel exposed)
    dur = 30.0
    tt = t(dur)
    x = 0.3 * np.sin(2 * np.pi * 220 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * tt)) + 0.2 * np.sin(2 * np.pi * 330.5 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * tt + 2))
    write('music', 'day_theme', loopify(stereo(lp(x, 900), lp(x, 880)), 2.0), 0.25)


KENNEY = [
    # (pack glob, file, our name, credit)
    ('*RPG*', 'creak1.ogg', 'sfx/creak_floor_3', 'RPG Audio by Kenney (kenney.nl), CC0'),
    ('*RPG*', 'doorClose_2.ogg', 'sfx/door_slam_2', 'RPG Audio by Kenney (kenney.nl), CC0'),
    ('*RPG*', 'footstep03.ogg', 'sfx/footstep_3', 'RPG Audio by Kenney (kenney.nl), CC0'),
    ('*RPG*', 'footstep06.ogg', 'sfx/footstep_4', 'RPG Audio by Kenney (kenney.nl), CC0'),
    ('*RPG*', 'chop.ogg', 'sfx/mine_wood_3', 'RPG Audio by Kenney (kenney.nl), CC0'),
    ('*RPG*', 'metalPot2.ogg', 'sfx/craft_2', 'RPG Audio by Kenney (kenney.nl), CC0'),
    ('*interface*', 'click_002.ogg', 'sfx/ui_click_2', 'Interface Sounds by Kenney (kenney.nl), CC0'),
    ('*interface*', 'open_002.ogg', 'sfx/ui_open_2', 'Interface Sounds by Kenney (kenney.nl), CC0'),
    ('*interface*', 'close_002.ogg', 'sfx/ui_close_2', 'Interface Sounds by Kenney (kenney.nl), CC0'),
    ('*ingle*', 'jingles_NES08.ogg', 'sfx/level_up_2', 'Music Jingles by Kenney (kenney.nl), CC0'),
]


def kenney(base):
    for pack, f, ours, credit in KENNEY:
        hits = glob.glob(os.path.join(base, pack, '**', f), recursive=True)
        if not hits:
            print('kenney: missing', f)
            continue
        dst = os.path.join(OUT, ours + '.ogg')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(hits[0], dst)
        CREDITS.append((ours + '.ogg', credit))


def main():
    sfx()
    ambience()
    music()
    if '--kenney' in sys.argv:
        kenney(sys.argv[sys.argv.index('--kenney') + 1])
    with open(os.path.join(OUT, 'audio_sources.tsv'), 'w', encoding='utf-8') as fh:
        for p, c in sorted(CREDITS):
            fh.write(f'{p}\t{c}\n')
    print(len(CREDITS), 'files')


if __name__ == '__main__':
    main()
