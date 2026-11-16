"""Spectral tools I-IV (concept/characters/spectral_tools.png) and the Spectral Workbench (concept_art/basic ghost.png).

Held-item convention (decisions.md): origin at the butt of the handle, handle along +Z (Godot +Y), the working
end (blade edge, spade face, hammer face) points to -Y (Godot +Z, forward). `GRIP` empty where the ghost's
hand holds it; a second `GRIP_off` where the other hand goes for two-handed swings.
"""
import math

from mathutils import Euler, Vector

import lib_geo as G
from props_common import new, prop

TIER_EMIT = {1: 0.12, 2: 0.22, 3: 0.38, 4: 0.6}


def tier_mats(t):
    """Per-tier spectral materials: brighter and bluer as the tier rises."""
    e = TIER_EMIT[t]
    G.define_mat(f'SPECTRAL_blade_t{t}', 'spectral.png', 0.3, color=(0.66, 0.78, 0.9, 1), rough=0.2,
                 emit=(0.55, 0.85, 1.0), emit_strength=e, alpha=0.78 + 0.04 * t, emit_tex=True)
    G.define_mat(f'SPECTRAL_handle_t{t}', 'wood_grain.png', 0.5,
                 color=(0.9, 0.85, 0.8, 1) if t <= 2 else (0.8, 0.88, 1.0, 1), rough=0.6,
                 emit=(0.4, 0.6, 0.8), emit_strength=0.15 * t, alpha=0.92)
    return f'SPECTRAL_blade_t{t}', f'SPECTRAL_handle_t{t}'


def _handle(m, mat, length, r=0.028, bend=0.0):
    pts = [(0, 0, 0), (bend * 0.3, 0, length * 0.35), (bend, 0, length * 0.7), (bend * 0.6, 0, length)]
    m.tube(mat, pts, r, 7, taper=0.9)
    m.cyl(mat, r * 1.3, r * 1.1, 0.06, (0, 0, 0.02), segs=7, bevel=0.01)


def _wraps(m, z_list, r, mat='SPECTRAL_wrap'):
    for z in z_list:
        m.cyl(mat, r * 1.25, r * 1.25, 0.05, (0, 0, z), segs=7, bevel=0.01)


def _gem(m, pos, r, rot=(0, 0, 0)):
    m.cyl('SPECTRAL_gem', r, 0.0, r * 1.4, Vector(pos) + Vector((0, 0, r * 0.7)), rot=rot, segs=6, bevel=0)
    m.cyl('SPECTRAL_gem', 0.0, r, r * 1.0, Vector(pos) - Vector((0, 0, r * 0.5)), rot=rot, segs=6, bevel=0)


def _crystals(m, pos, s=1.0):
    for (dx, dz, h, tilt) in ((0, 0, 0.16, 0), (0.05, -0.02, 0.11, 0.5), (-0.05, -0.02, 0.1, -0.5)):
        p = Vector(pos) + Vector((dx * s, 0, dz * s))
        m.cyl('SPECTRAL_gem', 0.03 * s, 0.0, h * s, p + Vector((math.sin(tilt) * h * s / 2, 0, math.cos(tilt) * h * s / 2)),
              rot=(0, tilt, 0), segs=6, bevel=0)


def _ribbon(m, pos):
    p = Vector(pos)
    m.tube('SPECTRAL_wrap', [p, p + Vector((0.1, -0.02, -0.08)), p + Vector((0.16, -0.01, -0.25))], 0.02, 4, taper=0.6)
    m.tube('SPECTRAL_wrap', [p, p + Vector((0.06, 0.02, -0.12)), p + Vector((0.08, 0.03, -0.3))], 0.018, 4, taper=0.6)


def scythe(t):
    p = new(f'scythe_t{t}')
    m = p.main
    blade, handle = tier_mats(t)
    L = 1.05 + 0.05 * t
    _handle(m, handle, L, 0.026, bend=0.06 if t == 1 else 0.03)
    _wraps(m, [0.25] + ([L * 0.55] if t >= 2 else []), 0.026)
    # collar at the top
    top = Vector((0.018, 0, L))
    m.box('SPECTRAL_metal' if t >= 2 else handle, (0.09, 0.08, 0.14 + 0.02 * t), top + Vector((0, 0, -0.02)),
          bevel=0.015)
    # crescent blade sweeping forward (-Y) and down, in the YZ plane
    span = 0.55 + 0.08 * t
    outer, inner = [], []
    n = 14
    for i in range(n + 1):
        u = i / n
        a = math.radians(10 + 95 * u)
        ro = span * (1.0 - 0.15 * u)
        ri = span * (0.72 - 0.2 * u * u) if u < 1 else ro
        outer.append((-math.sin(a) * ro, 0.15 * span - (1 - math.cos(a)) * ro * 0.75))
        inner.append((-math.sin(a) * ri * 0.97, 0.15 * span - (1 - math.cos(a)) * ri * 0.75 - 0.08 * (1 - u)))
    if t == 1:  # rough nicks along the edge
        outer = [(y + (0.015 if i % 3 == 1 else 0.0), z) for i, (y, z) in enumerate(outer)]
    outline = [(y, z) for y, z in outer] + [(y, z) for y, z in reversed(inner)]
    m.ext(blade, [(y, z) for y, z in outline], 0.025, top + Vector((0, 0, 0.0)), rot=(0, 0, math.pi / 2), bevel=0.008)
    if t >= 3:
        _gem(m, top + Vector((0, -0.05, 0.0)), 0.035, rot=(math.pi / 2, 0, 0))
        m.cyl('SPECTRAL_metal', 0.03, 0.0, 0.08, (0, 0, -0.05), segs=6, bevel=0)  # pommel spike
    if t == 4:
        _crystals(m, top + Vector((0, 0.0, 0.05)), 1.0)
        _ribbon(m, top + Vector((0.04, 0, -0.08)))
    p.add(G.empty('GRIP', (0.0, 0, L * 0.38), size=0.06))
    p.add(G.empty('GRIP_off', (0.0, 0, L * 0.75), size=0.06))
    p.add(G.empty('FX_wisp', top + Vector((0, -span * 0.5, 0))))
    return p


def shovel(t):
    p = new(f'shovel_t{t}')
    m = p.main
    blade, handle = tier_mats(t)
    L = 0.95 + 0.04 * t
    # D-handle at the butt (z=0), blade at the top end -> flip: we build blade at the bottom (working end down)
    # Held items: handle along +Z; for the shovel the spade is at z=0..0.35 and the D grip at the top.
    sp_h = 0.36 + 0.02 * t
    out = [(-0.17, sp_h * 0.75), (0.17, sp_h * 0.75), (0.17, 0.12), (0.0, -0.02), (-0.17, 0.12)]
    if t >= 3:
        out = [(-0.18, sp_h * 0.8), (-0.05, sp_h * 0.85), (0.05, sp_h * 0.85), (0.18, sp_h * 0.8), (0.17, 0.12),
               (0.0, -0.04), (-0.17, 0.12)]
    m.ext(blade, out, 0.025, (0, 0, 0.0), bevel=0.008)
    m.tube('SPECTRAL_metal' if t >= 2 else handle, [(0, 0, sp_h * 0.6), (0, 0, sp_h + 0.08)], 0.04, 7, taper=0.7)
    m.tube(handle, [(0, 0, sp_h + 0.05), (0, 0, L)], 0.025, 7)
    _wraps(m, [sp_h + 0.1, L * 0.62], 0.025)
    # D grip
    d = [(-0.09, 0, L), (-0.1, 0, L + 0.12), (-0.05, 0, L + 0.18), (0.05, 0, L + 0.18), (0.1, 0, L + 0.12), (0.09, 0, L)]
    m.tube('SPECTRAL_metal' if t >= 2 else handle, d, 0.022, 6)
    m.box(handle, (0.2, 0.05, 0.05), (0, 0, L), bevel=0.012)
    if t >= 3:
        _gem(m, (0, -0.02, sp_h * 0.75), 0.035, rot=(math.pi / 2, 0, 0))
        m.ext('SPECTRAL_metal', [(-0.05, 0), (0.05, 0), (0.0, 0.08)], 0.02, (0, -0.02, sp_h * 0.8), bevel=0.004)
    if t == 4:
        _gem(m, (0, -0.02, L + 0.18), 0.03, rot=(math.pi / 2, 0, 0))
        _ribbon(m, (0.05, 0, L - 0.05))
    p.add(G.empty('GRIP', (0, 0, L - 0.05), size=0.06))
    p.add(G.empty('GRIP_off', (0, 0, L * 0.55), size=0.06))
    p.add(G.empty('FX_wisp', (0, -0.05, 0.1)))
    return p


def sledgehammer(t):
    p = new(f'sledgehammer_t{t}')
    m = p.main
    blade, handle = tier_mats(t)
    L = 0.85 + 0.05 * t
    _handle(m, handle, L, 0.03)
    _wraps(m, [0.12, 0.22] + ([L * 0.5] if t >= 2 else []), 0.03)
    if t >= 2:
        m.cyl('SPECTRAL_metal', 0.04, 0.04, 0.06, (0, 0, 0.02), segs=8, bevel=0.01)
    head = Vector((0, 0, L + 0.06))
    hw = 0.36 + 0.03 * t  # head length along Y (striking faces front/back)
    hs = 0.2 + 0.015 * t
    if t == 1:
        m.sphere(blade, 0.17, head, scale=(1.1, 1.5, 0.95), segs=8, rings=6, jitter=0.02)
    else:
        m.box(blade, (hs, hw, hs), head, bevel=0.04)
        for y in (-hw / 2 + 0.03, hw / 2 - 0.03):
            m.box('SPECTRAL_metal', (hs + 0.03, 0.05, hs + 0.03), head + Vector((0, y, 0)), bevel=0.012)
        m.box('SPECTRAL_metal', (hs + 0.035, 0.1, hs * 0.5), head, bevel=0.012)
    if t >= 3:
        _gem(m, head + Vector((hs / 2 + 0.01, 0, 0)), 0.035, rot=(0, math.pi / 2, 0))
        _gem(m, (0, 0, -0.04), 0.035)
    if t == 4:
        _crystals(m, head + Vector((0, 0.03, hs / 2)), 1.0)
    p.add(G.empty('GRIP', (0, 0, 0.18), size=0.06))
    p.add(G.empty('GRIP_off', (0, 0, L * 0.6), size=0.06))
    p.add(G.empty('FX_impact', head + Vector((0, -hw / 2, 0))))
    return p


for _t in (1, 2, 3, 4):
    prop(f'scythe_t{_t}', 'tool', desc=f'spectral scythe tier {"I II III IV".split()[_t - 1]}')(lambda t=_t: scythe(t))
    prop(f'shovel_t{_t}', 'tool', desc=f'spectral shovel tier {"I II III IV".split()[_t - 1]}')(lambda t=_t: shovel(t))
    prop(f'sledgehammer_t{_t}', 'tool', desc=f'spectral sledgehammer tier {"I II III IV".split()[_t - 1]}')(
        lambda t=_t: sledgehammer(t))


@prop('spectral_workbench', 'crafting', desc='Spectral Workbench with anvil, vise, scrolls and a blueprint')
def spectral_workbench():
    p = new('spectral_workbench')
    m = p.main
    W, D, H = 2.2, 0.95, 0.9
    m.box('wood_planks', (W, D, 0.12), (0, 0, H), bevel=0.03, jitter=0.006)
    for sx in (-W / 2 + 0.12, W / 2 - 0.12):
        for sy in (-D / 2 + 0.1, D / 2 - 0.1):
            m.box('wood', (0.15, 0.15, H - 0.06), (sx, sy, (H - 0.06) / 2), bevel=0.03)
        m.box('wood_dark', (0.12, D - 0.1, 0.1), (sx, 0, 0.18), bevel=0.02)
    m.box('wood_planks', (W - 0.3, D - 0.2, 0.06), (0, 0, 0.22), bevel=0.02)  # lower shelf
    m.box('wood', (0.6, 0.06, 0.2), (0.25, -D / 2 - 0.01, H - 0.17), bevel=0.02)  # drawer
    m.sphere('iron', 0.025, (0.25, -D / 2 - 0.05, H - 0.17), segs=6, rings=4)
    top = H + 0.06
    # blueprint sheet (spectral blue paper)
    m.box('cloth_blue', (0.75, 0.5, 0.01), (-0.2, 0.05, top + 0.005), rot=(0, 0, 0.1), bevel=0.002)
    for k in range(4):
        m.box('ink_dark', (0.5, 0.01, 0.004), (-0.2, -0.12 + k * 0.1, top + 0.012), rot=(0, 0, 0.1), bevel=0)
    # scrolls
    for k, (x, y, r) in enumerate(((-0.75, 0.15, 0.05), (-0.62, 0.3, 0.045))):
        m.cyl('paper', r, r, 0.5, (x, y, top + r), rot=(0, math.pi / 2, 0.3 * k), segs=8, bevel=0.01)
    # tools on the bench
    m.cyl('wood', 0.02, 0.02, 0.32, (0.15, -0.25, top + 0.02), rot=(0, math.pi / 2, 0.5), segs=6, bevel=0.005)
    m.box('iron', (0.06, 0.12, 0.06), (0.3, -0.33, top + 0.03), rot=(0, 0, 0.5), bevel=0.01)
    m.tube('iron', [(0.35, 0.25, top + 0.01), (0.55, 0.3, top + 0.01), (0.6, 0.35, top + 0.02)], 0.012, 4)
    m.tube('iron', [(0.35, 0.28, top + 0.01), (0.55, 0.36, top + 0.01)], 0.012, 4)
    # vise at the left end
    m.box('iron', (0.18, 0.2, 0.16), (-W / 2 + 0.2, -D / 2 + 0.1, top + 0.08), bevel=0.02)
    m.cyl('iron', 0.015, 0.015, 0.28, (-W / 2 + 0.2, -D / 2 - 0.05, top + 0.08), rot=(0, math.pi / 2, 0), segs=6)
    # toolbox
    m.box('iron', (0.3, 0.2, 0.16), (-0.85, -0.25, top + 0.08), bevel=0.02)
    m.tube('iron', [(-0.95, -0.25, top + 0.16), (-0.85, -0.25, top + 0.24), (-0.75, -0.25, top + 0.16)], 0.01, 4)
    # anvil on a stump to the right
    ax = W / 2 + 0.55
    m.cyl('bark', 0.3, 0.33, 0.55, (ax, 0.0, 0.275), segs=10, bevel=0.03, jitter=0.01)
    m.cyl('wood', 0.28, 0.28, 0.02, (ax, 0.0, 0.555), segs=10, bevel=0.005)
    m.box('iron', (0.24, 0.32, 0.14), (ax, 0, 0.63), bevel=0.02)
    m.box('iron', (0.14, 0.2, 0.14), (ax, 0, 0.74), bevel=0.015)
    m.box('iron', (0.3, 0.5, 0.12), (ax, 0.0, 0.86), bevel=0.02)
    m.cyl('iron', 0.08, 0.0, 0.3, (ax, -0.38, 0.86), rot=(math.pi / 2, 0, 0), segs=8, bevel=0)
    p.add(G.LightNode('LIGHT_forge', (ax, -0.2, 1.1), 15, (0.5, 0.8, 1.0), 0.2))
    p.add(G.empty('FX_sparks', (ax, 0, 0.95)))
    p.add(G.empty('MARK_use', (0, -1.0, 0), 0))
    p.add(G.empty('MARK_use_anvil', (ax, -0.8, 0), 0))
    p.collision.append(((W, D, H + 0.1), (0, 0, (H + 0.1) / 2)))
    p.collision.append(((0.6, 0.6, 0.95), (ax, 0, 0.47)))
    return p
