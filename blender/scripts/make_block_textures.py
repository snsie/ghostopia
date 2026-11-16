"""Block textures + block definitions for the voxel world.

Writes assets/blocks/blocks_atlas.png (albedo, RGBA), blocks_normal.png, blocks_height.png,
blocks_emission.png, blocks.json and renders/task1/block_tiles.png (flat tile sheet).

Run with system Python or inside Blender:
    python blender/scripts/make_block_textures.py
    blender -b --factory-startup -P blender/scripts/make_block_textures.py
Colours sampled from concept/characters/block_palette.png (see decisions.md).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_tex as T  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'blocks')
S = 64
COLS = 8


def R(*c):
    return T.rgb(*c)


# ----------------------------------------------------------------------------- helpers
def tile(col, h, emit=None, alpha=None):
    return {'col': col, 'h': h, 'emit': emit, 'alpha': alpha}


def stones(seed, n, base, dark, light, var=0.12, mortar_col=None, aspect=(1, 1), round_=3.0):
    f1, f2, idx, _ = T.voronoi(S, n, seed, aspect)
    edge = f2 - f1
    hh = np.clip(edge / round_, 0, 1)
    hh = 1 - (1 - hh) ** 2
    v = T.per_id_random(idx, seed + 1)
    tint = T.per_id_random(idx, seed + 2, -var, var)
    nz = T.value_noise(S, 8, seed + 3, 3)
    col = T.ramp(0.35 + 0.4 * v * 0.5 + 0.35 * nz, [(0, dark), (0.5, base), (1, light)])
    col = col * (1 + tint[..., None])
    h = hh * (0.7 + 0.3 * nz)
    mcol = mortar_col if mortar_col is not None else dark * 0.55
    mort = np.clip(1.4 - edge, 0, 1)[..., None]
    col = col * (1 - mort) + mcol * mort
    return col, h, edge, idx


def finish(t, seed, cube=True, **kw):
    col = T.apply_shade(t['col'], t['h'], strength=3.0, light=0.25, dark=0.35)
    h = t['h']
    if cube:
        col, h = T.bevel_tile(col, h, seed, **kw)
    t['col'] = np.clip(col, 0, 1)
    t['h'] = np.clip(h, 0, 1)
    return t


def moss_over(col, h, seed, cover, top_band=0, drip=0):
    """Paint moss patches (cover = 0..1 amount) and an optional top band with drips."""
    nz = T.value_noise(S, 5, seed, 3)
    m = np.clip((nz - (1 - cover)) * 6, 0, 1)
    if top_band:
        yy, xx = T.grid(S)
        dn = T.value_noise(S, 6, seed + 9, 2)
        drips = (T.value_noise((1, S), 10, seed + 5, 1)[0] > 0.62) * drip
        band = top_band + (dn - 0.5) * 6 + drips[None, :] * (6 + 6 * dn)
        m = np.maximum(m, np.clip((band - yy) * 0.8, 0, 1))
    mc = T.ramp(T.value_noise(S, 10, seed + 2, 2), [(0, R(92, 112, 40)), (0.5, R(140, 156, 52)), (1, R(178, 182, 70))])
    col = col * (1 - m[..., None]) + mc * m[..., None]
    h = np.maximum(h, m * (0.75 + 0.2 * T.value_noise(S, 12, seed + 4, 1)))
    return col, h


def flowers(col, h, seed, n, petal, centre=R(250, 214, 90), r=2.2):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        cy, cx = rng.uniform(8, S - 8, 2)
        for k in range(5):
            a = k / 5 * 2 * math.pi + rng.uniform(0, 1)
            m = T.disk_mask(S, cy + math.sin(a) * r, cx + math.cos(a) * r, r * 0.8)
            col = T.stamp(col, m, petal)
            h = np.maximum(h, m * 0.95)
        col = T.stamp(col, T.disk_mask(S, cy, cx, r * 0.55), centre)
    return col, h


def leaves_clover(col, h, seed, n, colr):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        cy, cx = rng.uniform(4, S - 4, 2)
        for k in range(3):
            a = k / 3 * 2 * math.pi + rng.uniform(0, 1)
            m = T.disk_mask(S, cy + math.sin(a) * 2.3, cx + math.cos(a) * 2.3, 2.1)
            col = T.stamp(col, m, colr * rng.uniform(0.9, 1.15))
            h = np.maximum(h, m * 0.9)
    return col, h


def pebbles(col, h, seed, n, c=R(150, 140, 150), r=(1.5, 3.0)):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        cy, cx = rng.uniform(5, S - 5, 2)
        rr = rng.uniform(*r)
        m = T.ellipse_mask(S, cy, cx, rr * 0.8, rr)
        col = T.stamp(col, m, c * rng.uniform(0.85, 1.15))
        h = np.maximum(h, m * (0.8 + 0.2 * T.disk_mask(S, cy - 0.6, cx - 0.6, rr * 0.5)))
    return col, h


# ----------------------------------------------------------------------------- painters
def dirt_tile(seed, base=R(138, 88, 72), dark=R(94, 58, 54), light=R(178, 118, 96), peb=6):
    col, h, edge, idx = stones(seed, 22, base, dark, light, var=0.08, mortar_col=dark * 0.95, round_=7)
    nz = T.value_noise(S, 12, seed + 7, 3)
    col = col * (0.82 + 0.3 * nz[..., None])
    col = T.lerp(col, base * (0.85 + 0.3 * T.value_noise(S, 5, seed + 8, 3))[..., None], 0.35)
    h = h * 0.45 + nz * 0.4
    col, h = pebbles(col, h, seed + 11, peb)
    return tile(col, h)


def p_dirt(seed):
    return dirt_tile(seed)


def p_grass_top(seed):
    nz = T.value_noise(S, 6, seed, 4)
    col = T.ramp(nz, [(0, R(84, 112, 42)), (0.45, R(124, 148, 50)), (0.8, R(158, 170, 62)), (1, R(176, 182, 80))])
    h = 0.5 + 0.3 * nz
    blades = T.value_noise(S, 24, seed + 1, 1)
    col = col * (0.88 + 0.22 * blades[..., None])
    col, h = leaves_clover(col, h, seed + 2, 4, R(100, 140, 52))
    return tile(col, h)


def p_grass_side(seed):
    t = dirt_tile(seed + 50)
    col, h = moss_over(t['col'], t['h'], seed, 0.0, top_band=15, drip=1.0)
    col, h = leaves_clover(col, h, seed + 3, 1, R(110, 150, 54))
    return tile(col, h)


def p_grave_dirt(seed):
    t = dirt_tile(seed, base=R(96, 68, 92), dark=R(64, 46, 62), light=R(124, 90, 118), peb=4)
    col, h = t['col'], t['h']
    # roots
    rng = np.random.default_rng(seed + 4)
    for _ in range(2):
        y = rng.uniform(4, 20)
        x = rng.uniform(10, 54)
        pts = [(y, x)]
        for k in range(5):
            y += rng.uniform(3, 6)
            x += rng.uniform(-4, 4)
            pts.append((y, x))
        m = T.polyline_mask(S, pts, 1.6)
        col = T.stamp(col, m, R(120, 78, 50))
        h = np.maximum(h, m * 0.7)
    # bone fleck
    by, bx = rng.uniform(34, 50), rng.uniform(18, 46)
    m = np.maximum(T.line_mask(S, (by, bx - 5), (by + 1, bx + 5), 2.0),
                   np.maximum(T.disk_mask(S, by - 1, bx - 6, 1.5), T.disk_mask(S, by + 2, bx + 6, 1.5)))
    m = np.maximum(m, np.maximum(T.disk_mask(S, by + 1.2, bx - 6, 1.4), T.disk_mask(S, by, bx + 6.4, 1.4)))
    col = T.stamp(col, m, R(236, 226, 214))
    h = np.maximum(h, m * 0.9)
    col, h = pebbles(col, h, seed + 9, 3, c=R(110, 110, 150))
    return tile(col, h)


def p_sand(seed):
    yy, xx = T.grid(S)
    nz = T.value_noise(S, 4, seed, 3)
    sw = np.sin((yy * 0.18 + nz * 6 + xx * 0.05)) * 0.5 + 0.5
    v = 0.55 * nz + 0.45 * T.posterize(sw, 3)
    col = T.ramp(v, [(0, R(204, 140, 88)), (0.5, R(230, 172, 118)), (1, R(246, 198, 144))])
    h = 0.4 + 0.3 * sw * nz
    rng = np.random.default_rng(seed)
    for _ in range(14):
        cy, cx = rng.uniform(4, 60, 2)
        col = T.stamp(col, T.disk_mask(S, cy, cx, 0.8), R(170, 120, 90))
    col, h = pebbles(col, h, seed + 1, 2, c=R(170, 150, 150), r=(1.2, 2))
    return tile(col, h)


def p_cobble(seed, moss=0.25):
    col, h, edge, idx = stones(seed, 13, R(150, 132, 146), R(96, 84, 102), R(190, 170, 176), var=0.1, round_=4)
    if moss:
        nz = T.value_noise(S, 5, seed + 5, 2)
        m = np.clip(1.8 - edge, 0, 1) * np.clip((nz - (1 - moss)) * 5, 0, 1)
        col = T.stamp(col, m, R(120, 150, 52))
    return tile(col, h)


def p_stone(seed):
    col, h, edge, idx = stones(seed, 7, R(138, 128, 148), R(90, 84, 104), R(176, 166, 182), var=0.07, round_=6)
    nz = T.value_noise(S, 10, seed + 3, 3)
    col = col * (0.9 + 0.2 * nz[..., None])
    # cracks
    rng = np.random.default_rng(seed + 8)
    y, x = rng.uniform(8, 20), rng.uniform(12, 50)
    pts = [(y, x)]
    for _ in range(4):
        y += rng.uniform(4, 9)
        x += rng.uniform(-6, 6)
        pts.append((y, x))
    m = T.polyline_mask(S, pts, 1.0)
    col = T.stamp(col, m, R(70, 62, 82), 0.8)
    h = h * (1 - 0.4 * m)
    return tile(col, h)


def p_spectral_stone(seed):
    col, h, edge, idx = stones(seed, 9, R(116, 124, 140), R(70, 80, 100), R(158, 166, 176), var=0.08, round_=4)
    col, h = moss_over(col, h, seed + 1, 0.18)
    # glowing teal veins along some cell edges
    nz = T.value_noise(S, 3, seed + 2, 2)
    vein = np.clip(1.6 - edge, 0, 1) * np.clip((nz - 0.45) * 5, 0, 1)
    vein = np.maximum(vein, T.spiral_mask(S, 40, 22, 9, turns=2.0, width=1.8) * 0.95)
    glow = T.blur(vein, 1)
    col = T.stamp(col, glow, R(90, 220, 220), 0.6)
    col = T.stamp(col, vein, R(170, 255, 250))
    emit = (T.TEAL[None, None, :] * np.clip(vein + glow * 0.5, 0, 1)[..., None])
    return tile(col, h, emit=emit)


def p_eerie_ore(seed):
    col, h, edge, idx = stones(seed, 10, R(108, 76, 146), R(66, 46, 100), R(148, 110, 186), var=0.1, round_=4)
    rng = np.random.default_rng(seed + 3)
    emit = np.zeros((S, S, 3))
    crystals = [(17, 42, 13), (42, 17, 11), (49, 47, 8)]
    for cy, cx, r in crystals:
        a = rng.uniform(-0.4, 0.4)
        pts = []
        for k in range(6):
            ang = a + k / 6 * 2 * math.pi
            rr = r * (1.25 if k in (0, 3) else 0.7)
            pts.append((cy + math.sin(ang) * rr * 1.2, cx + math.cos(ang) * rr * 0.7))
        m = T.poly_mask(S, pts)
        facet = T.poly_mask(S, [pts[0], pts[1], pts[2], (cy, cx)])
        col = T.stamp(col, m, R(176, 110, 240))
        col = T.stamp(col, facet * m, R(226, 176, 255))
        col = T.stamp(col, T.disk_mask(S, cy - r * 0.5, cx - r * 0.15, 1.2), R(255, 240, 255))
        h = np.maximum(h, m * 0.98)
        g = T.blur(m, 2)
        emit += T.VIOLET[None, None, :] * np.clip(m * 0.9 + g * 0.6, 0, 1)[..., None]
    halo = T.blur(np.clip(emit.sum(-1), 0, 1), 3)
    col = T.stamp(col, halo * 0.5, R(150, 90, 220))
    return tile(col, h, emit=np.clip(emit, 0, 1))


def p_iron_ore(seed):
    t = p_cobble(seed, moss=0.05)
    col, h = t['col'] * 0.95, t['h']
    rng = np.random.default_rng(seed + 4)
    for cy, cx, r in [(16, 44, 8), (40, 18, 9), (47, 48, 7)]:
        pts = [(cy + math.sin(k / 5 * 6.283 + rng.uniform(-0.3, 0.3)) * r * rng.uniform(0.7, 1.1),
                cx + math.cos(k / 5 * 6.283) * r * rng.uniform(0.7, 1.1)) for k in range(5)]
        m = T.poly_mask(S, pts)
        rim = np.clip(T.blur(m, 1) - m * 0.3, 0, 1) * (1 - m)
        col = T.stamp(col, rim * 2.0, R(176, 92, 48))
        col = T.stamp(col, m, R(196, 160, 160))
        col = T.stamp(col, m * T.disk_mask(S, cy - 1.5, cx - 1.5, r * 0.6), R(236, 220, 226))
        h = np.maximum(h, m)
    return tile(col, h)


def p_thatch(seed, top=False):
    """Shaggy straw: two overlapping layers of tufts, each tuft a bundle of strands with a ragged tip."""
    yy, xx = T.grid(S)
    rng = np.random.default_rng(seed)
    col = np.zeros((S, S, 3)) + R(120, 74, 36)
    h = np.zeros((S, S)) + 0.1
    k_ = S / 64.0
    layer_h = 32 * k_
    for layer in (2, 1, 0):
        y0 = -8 * k_ + layer * layer_h * 0.75
        for k in range(int(26 * k_)):
            x = k * 64 / 22 + rng.uniform(-2, 2)
            length = layer_h * rng.uniform(0.8, 1.1)
            lean = rng.uniform(-3, 3) * k_
            w = rng.uniform(2.2, 3.4) * (0.8 + 0.2 * k_)
            for xo in (0, S, -S):
                m = T.line_mask(S, (y0, x + xo), (y0 + length, x + xo + lean), w, soft=1.2)
                t = np.clip((yy - y0) / length, 0, 1)
                shade = T.lerp(R(250, 208, 120), R(176, 110, 50), t[..., None] ** 1.5)
                c = shade * rng.uniform(0.85, 1.1)
                col = T.stamp(col, m, c)
                h = np.where(m > 0.5, 0.35 + 0.5 * t + 0.1 * rng.uniform(), h)
        # dark shadow line under the layer's tips
        tipy = y0 + layer_h * 0.95 + 2 * np.sin(xx * 0.9 / k_ + layer)
        sh = np.clip(1 - np.abs(yy - tipy - 1.5) / 2.5, 0, 1) * 0.5
        col = col * (1 - sh[..., None])
    col = col * (0.9 + 0.2 * T.value_noise(S, 10, seed + 3, 2))[..., None]
    if not top:
        band = np.clip(1 - np.abs(yy - 52 * k_) / 1.4, 0, 1)
        col = T.stamp(col, band, R(104, 66, 38))
    return tile(col, h)


def planks(seed, base=R(170, 104, 70), dark=R(116, 70, 52), light=R(204, 136, 92), rows=4, vertical=False,
           nails=True, weather=0.0):
    yy, xx = T.grid(S)
    if vertical:
        yy, xx = xx, yy
    rng = np.random.default_rng(seed)
    rh = S / rows
    row = np.floor(yy / rh).astype(int)
    fy = yy - row * rh
    # each row split at a random point
    split = rng.uniform(16, 48, rows)
    seg = (xx > split[row]).astype(int)
    pid = row * 2 + seg
    tint = T.per_id_random(pid, seed + 1, -0.1, 0.1)
    grain = T.value_noise((S, S), 3, seed + 2, 3)
    if vertical:
        grain = grain.T
    gl = np.sin((fy / rh) * 9 + grain * 10 + pid * 1.3) * 0.5 + 0.5
    v = 0.5 + 0.25 * (gl - 0.5) + 0.25 * (T.value_noise(S, 8, seed + 3, 2) - 0.5)
    col = T.ramp(v, [(0, dark), (0.5, base), (1, light)]) * (1 + tint[..., None])
    edge_y = np.minimum(fy, rh - fy)
    edge_x = np.abs(xx - split[row])
    edge = np.minimum(edge_y, edge_x)
    h = np.clip(edge / 2.5, 0, 1) * (0.8 + 0.2 * gl)
    gap = np.clip(1.3 - edge, 0, 1)[..., None]
    col = col * (1 - gap) + dark * 0.45 * gap
    if weather:
        col = col * (1 - weather) + col.mean(-1, keepdims=True) * np.array([1.0, 0.97, 1.02]) * weather
    if nails:
        for r in range(rows):
            for x in (4.5, S - 5.5):
                cy, cx = r * rh + rh / 2, x
                if vertical:
                    cy, cx = cx, cy
                m = T.disk_mask(S, cy, cx, 1.4)
                col = T.stamp(col, m, R(70, 66, 80))
                col = T.stamp(col, T.disk_mask(S, cy - 0.5, cx - 0.5, 0.6), R(150, 150, 164))
    return tile(col, h)


def p_timber_planks(seed):
    return planks(seed)


def p_rough_wood(seed):
    t = planks(seed, base=R(140, 100, 76), dark=R(90, 64, 56), light=R(176, 134, 104), rows=4, vertical=True,
               nails=True, weather=0.25)
    col, h = moss_over(t['col'], t['h'], seed + 4, 0.08)
    return tile(col, h)


def p_beam_side(seed):
    t = planks(seed, base=R(112, 72, 54), dark=R(70, 44, 40), light=R(140, 92, 66), rows=1, vertical=True,
               nails=False)
    yy, xx = T.grid(S)
    n = T.value_noise(S, 3, seed + 5, 3)
    g = np.sin(xx * 0.8 + n * 9) * 0.5 + 0.5
    col = t['col'] * (0.85 + 0.25 * g[..., None])
    for cy, cx in ((20, 22), (46, 40)):
        knot = T.ellipse_mask(S, cy, cx, 4, 2.5)
        col = T.stamp(col, knot, R(66, 40, 34), 0.8)
    return tile(col, t['h'] * (0.8 + 0.2 * g))


def p_beam_end(seed):
    yy, xx = T.grid(S)
    d = np.sqrt((yy - 30) ** 2 + (xx - 33) ** 2)
    rings = np.sin(d * 0.9 + T.value_noise(S, 4, seed, 2) * 4) * 0.5 + 0.5
    col = T.ramp(0.3 + 0.4 * rings, [(0, R(90, 58, 44)), (1, R(160, 110, 76))])
    return tile(col, 0.5 + 0.2 * rings)


def p_plaster(seed, brace=False, frame=True):
    nz = T.value_noise(S, 6, seed, 4)
    f1, f2, idx, _ = T.voronoi(S, 14, seed + 1)
    edge = f2 - f1
    col = T.ramp(0.5 * nz + 0.3 * T.per_id_random(idx, seed + 2), [(0, R(206, 176, 160)), (0.5, R(234, 210, 192)), (1, R(246, 230, 214))])
    h = 0.55 + 0.2 * np.clip(edge / 3, 0, 1) + 0.1 * nz
    col = T.stamp(col, np.clip(1.2 - edge, 0, 1), R(196, 164, 152), 0.6)
    if frame or brace:
        beam = T.ramp(T.value_noise(S, 6, seed + 5, 2), [(0, R(96, 60, 44)), (1, R(140, 92, 64))])
        yy, xx = T.grid(S)
        m = np.zeros((S, S))
        if frame:
            m = np.maximum(m, ((yy < 7) | (yy > S - 8) | (xx < 7) | (xx > S - 8)).astype(float))
        if brace:
            m = np.maximum(m, T.line_mask(S, (S - 6, 6), (6, S - 6), 9))
        col = col * (1 - m[..., None]) + beam * m[..., None]
        h = np.where(m > 0.5, 0.95, h * 0.85)
    return tile(col, h)


def p_wheat(seed):
    col = np.zeros((S, S, 3))
    alpha = np.zeros((S, S))
    h = np.zeros((S, S))
    rng = np.random.default_rng(seed)
    for k in range(12):
        x0 = 3 + k * 5.2 + rng.uniform(-2, 2)
        top = rng.uniform(4, 16)
        lean = rng.uniform(-4, 4)
        stalk = T.line_mask(S, (S, x0), (top + 8, x0 + lean), 2.0)
        c_st = R(196, 150, 62) * rng.uniform(0.85, 1.1)
        col = T.stamp(col, stalk, c_st)
        alpha = np.maximum(alpha, stalk)
        # ear: stacked grains
        for g in range(6):
            gy = top + g * 2.2
            gx = x0 + lean * (1 - (gy - top) / 40)
            for side in (-1, 1):
                m = T.ellipse_mask(S, gy + 1, gx + side * 1.7, 2.0, 1.4)
                col = T.stamp(col, m, R(240, 184, 80) * rng.uniform(0.9, 1.1))
                alpha = np.maximum(alpha, m)
                h = np.maximum(h, m)
        # leaf
        ly = rng.uniform(34, 50)
        leaf = T.line_mask(S, (ly, x0), (ly - 6, x0 + rng.choice([-5, 5])), 1.8)
        col = T.stamp(col, leaf, R(200, 156, 70))
        alpha = np.maximum(alpha, leaf)
    col = T.apply_shade(col, h * 0.5, 3.0)
    edgeink = np.clip(T.blur(alpha, 1) - alpha, 0, 1) * 0 + (alpha < 0.9) * alpha
    col = col * (1 - 0.4 * edgeink[..., None]) + T.INK * 0.4 * edgeink[..., None]
    return tile(col, h, alpha=alpha)


def p_tall_grass(seed):
    col = np.zeros((S, S, 3))
    alpha = np.zeros((S, S))
    rng = np.random.default_rng(seed)
    for k in range(16):
        x0 = rng.uniform(4, 60)
        top = rng.uniform(10, 34)
        bend = rng.uniform(-10, 10)
        pts = [(S, x0), ((S + top) / 2, x0 + bend * 0.3), (top, x0 + bend)]
        m = T.polyline_mask(S, pts, rng.uniform(2.0, 3.2))
        c = T.lerp(R(90, 120, 40), R(170, 186, 70), rng.uniform(0, 1))
        col = T.stamp(col, m, c)
        alpha = np.maximum(alpha, m)
    yy, _ = T.grid(S)
    col = col * (0.75 + 0.35 * (1 - yy / S))[..., None]
    return tile(col, alpha * 0.5, alpha=alpha)


def p_flowers(seed):
    t = p_tall_grass(seed)
    col, alpha, h = t['col'], t['alpha'], t['h']
    rng = np.random.default_rng(seed + 1)
    for k in range(6):
        cy, cx = rng.uniform(10, 30), rng.uniform(8, 56)
        petal = R(176, 120, 236) if k % 2 == 0 else R(248, 244, 236)
        for j in range(5):
            a = j / 5 * 6.283
            m = T.disk_mask(S, cy + math.sin(a) * 2.6, cx + math.cos(a) * 2.6, 2.2)
            col = T.stamp(col, m, petal)
            alpha = np.maximum(alpha, m)
        m = T.disk_mask(S, cy, cx, 1.4)
        col = T.stamp(col, m, R(250, 214, 90))
    return tile(col, h, alpha=alpha)


def p_grave_moss_top(seed):
    t = p_grass_top(seed)
    col = t['col'] * np.array([0.95, 0.95, 0.85])
    col, h = flowers(col, t['h'], seed + 5, 1, R(176, 120, 236), r=2.6)
    col, h = leaves_clover(col, h, seed + 6, 6, R(96, 140, 60))
    return tile(col, h)


def p_grave_moss_side(seed):
    t = p_grave_dirt(seed + 30)
    col, h = moss_over(t['col'], t['h'], seed, 0.3, top_band=20, drip=1.0)
    col, h = leaves_clover(col, h, seed + 7, 4, R(110, 150, 54))
    return tile(col, h)


def p_gravestone_front(seed):
    t = p_stone(seed)
    col, h = t['col'] * 0.98, t['h'] * 0.6 + 0.2
    yy, xx = T.grid(S)
    # raised arched slab panel
    arch = ((np.abs(xx - 32) < 20) & (yy > 14) & (yy < 58)) | (T.disk_mask(S, 18, 32, 20) > 0.5) & (yy <= 18)
    arch = arch.astype(float)
    inner = (((np.abs(xx - 32) < 15) & (yy > 18) & (yy < 54)) | ((T.disk_mask(S, 20, 32, 15) > 0.5) & (yy <= 20))).astype(float)
    h = np.maximum(h, arch * 0.85 - inner * 0.25)
    groove = np.clip(arch - inner, 0, 1) * (1 - inner)
    col = T.stamp(col, inner, R(160, 148, 160), 0.6)
    col = T.stamp(col, np.clip(T.blur(arch, 1) - arch, 0, 1) * 3, R(70, 60, 80), 0.9)
    cross = ((np.abs(xx - 32) < 2.5) & (yy > 22) & (yy < 46)) | ((np.abs(yy - 30) < 2.5) & (np.abs(xx - 32) < 9))
    h = np.where(cross, 0.35, h)
    col = T.stamp(col, cross.astype(float), R(80, 70, 92), 0.7)
    col, h = moss_over(col, h, seed + 4, 0.12)
    return tile(col, h)


def p_water(seed, deep=False):
    yy, xx = T.grid(S)
    nz = T.value_noise(S, 4, seed, 3)
    rip = np.sin(yy * 0.35 + nz * 8) * 0.5 + 0.5
    v = 0.45 * nz + 0.55 * T.posterize(rip, 4)
    if deep:
        stops = [(0, R(40, 70, 120)), (0.6, R(60, 104, 160)), (1, R(110, 160, 210))]
    else:
        stops = [(0, R(56, 112, 160)), (0.55, R(96, 156, 206)), (1, R(170, 226, 250))]
    col = T.ramp(v, stops)
    foam = (rip > 0.93) * (nz > 0.45)
    col = T.stamp(col, foam.astype(float), R(220, 246, 255), 0.85)
    alpha = np.full((S, S), 0.72 if not deep else 0.82)
    emit = T.ICE_BLUE[None, None, :] * foam[..., None] * 0.35
    return tile(col, 0.5 + 0.1 * rip, emit=emit, alpha=alpha)


def p_mossy_bricks(seed):
    edge, bid, row = T.bricks(S, 4, 2, seed, jitter=0.12)
    v = T.per_id_random(bid % 997, seed + 1)
    nz = T.value_noise(S, 8, seed + 2, 3)
    col = T.ramp(0.4 * v + 0.6 * nz, [(0, R(104, 104, 124)), (0.5, R(140, 138, 152)), (1, R(178, 176, 186))])
    h = np.clip(edge / 3, 0, 1) * (0.8 + 0.2 * nz)
    mort = np.clip(1.4 - edge, 0, 1)[..., None]
    col = col * (1 - mort) + R(60, 56, 76) * mort
    col, h = moss_over(col, h, seed + 3, 0.28, top_band=6, drip=0.6)
    return tile(col, h)


def p_slate(seed, top=False):
    edge, bid, row = T.bricks(S, 5, 3, seed, jitter=0.2)
    yy, xx = T.grid(S)
    rh = S / 5
    fy = yy - row * rh
    v = T.per_id_random(bid % 997, seed + 1)
    nz = T.value_noise(S, 8, seed + 2, 2)
    col = T.ramp(0.45 * v + 0.35 * nz + 0.2 * (fy / rh), [(0, R(76, 70, 104)), (0.5, R(108, 100, 136)), (1, R(146, 136, 170))])
    h = 0.3 + 0.6 * (fy / rh)
    shade = np.clip(1 - fy / 3, 0, 1)
    col = col * (1 - 0.45 * shade[..., None])
    gap = np.clip(1.2 - edge, 0, 1)[..., None] * (fy[..., None] > 2)
    col = col * (1 - gap) + R(50, 44, 70) * gap
    col, h = moss_over(col, h, seed + 4, 0.12)
    return tile(col, h)


def p_log_side(seed):
    yy, xx = T.grid(S)
    n = T.value_noise((S, S), 2, seed, 3)
    furrow = np.sin(xx * 0.55 + n * 6) * 0.5 + 0.5
    col = T.ramp(0.6 * furrow + 0.4 * T.value_noise(S, 8, seed + 1, 2), [(0, R(70, 48, 44)), (0.6, R(112, 80, 62)), (1, R(146, 108, 80))])
    col, h = moss_over(col, furrow, seed + 2, 0.12)
    return tile(col, h)


def p_log_top(seed):
    t = p_beam_end(seed)
    yy, xx = T.grid(S)
    d = np.sqrt((yy - 32) ** 2 + (xx - 32) ** 2)
    bark = (d > 26).astype(float)
    col = T.stamp(t['col'], bark, R(96, 66, 52))
    return tile(col, t['h'])


def p_leaves(seed):
    f1, f2, idx, _ = T.voronoi(S, 22, seed)
    nz = T.value_noise(S, 6, seed + 1, 3)
    hh = np.clip(1 - f1 / 8, 0, 1)
    col = T.ramp(0.5 * hh + 0.5 * nz, [(0, R(48, 80, 44)), (0.5, R(86, 124, 56)), (1, R(146, 170, 74))])
    col = T.stamp(col, np.clip(1.3 - (f2 - f1), 0, 1), R(40, 64, 40), 0.7)
    alpha = np.where((f1 > 7.2) & (nz < 0.4), 0.0, 1.0)
    return tile(col, hh, alpha=alpha)


def p_path_top(seed):
    t = dirt_tile(seed, base=R(160, 120, 98), dark=R(118, 86, 76), light=R(190, 152, 124), peb=10)
    return t


def p_plaster_top(seed):
    return planks(seed, base=R(112, 72, 54), dark=R(70, 44, 40), light=R(140, 92, 66), rows=2, nails=False)


# ----------------------------------------------------------------------------- tiles + blocks
TILE_PAINTERS = [
    # name, painter, cube-bevel
    ('grass_top', p_grass_top, False),
    ('grass_side', p_grass_side, True),
    ('dirt', p_dirt, True),
    ('grave_dirt', p_grave_dirt, True),
    ('sand', p_sand, True),
    ('cobblestone', p_cobble, True),
    ('spectral_stone', p_spectral_stone, True),
    ('eerie_ore', p_eerie_ore, True),
    ('iron_ore', p_iron_ore, True),
    ('thatch_side', lambda s: p_thatch(s, False), True),
    ('thatch_top', lambda s: p_thatch(s, True), True),
    ('timber_planks', p_timber_planks, True),
    ('plaster_wall', p_plaster, True),
    ('plaster_brace', lambda s: p_plaster(s, brace=True), True),
    ('plaster_top', p_plaster_top, True),
    ('wheat', p_wheat, False),
    ('grave_moss_top', p_grave_moss_top, False),
    ('grave_moss_side', p_grave_moss_side, True),
    ('gravestone_front', p_gravestone_front, True),
    ('gravestone_side', p_stone, True),
    ('river_water', p_water, False),
    ('still_water', lambda s: p_water(s, True), False),
    ('stone', p_stone, True),
    ('mossy_stone_bricks', p_mossy_bricks, True),
    ('timber_beam_side', p_beam_side, True),
    ('timber_beam_end', p_beam_end, True),
    ('slate_side', p_slate, True),
    ('slate_top', lambda s: p_slate(s, True), True),
    ('rough_wood', p_rough_wood, True),
    ('oak_log_side', p_log_side, True),
    ('oak_log_top', p_log_top, True),
    ('leaves', p_leaves, False),
    ('tall_grass', p_tall_grass, False),
    ('flowers', p_flowers, False),
    ('path_top', p_path_top, False),
    ('cobble_plain', lambda s: p_cobble(s, 0.0), False),
    # seamless top faces for terrain (no bevel rim, so the ground doesn't read as a grid)
    ('dirt_top', p_dirt, False),
    ('sand_top', p_sand, False),
    ('grave_dirt_top', p_grave_dirt, False),
    ('stone_top', p_stone, False),
]


def B(id_, name, faces, **kw):
    d = dict(id=id_, name=name, faces=faces, shape='cube', solid=True, phaseable=False, transparent=False,
             liquid=False, running_water=False, tool='none', tier=1, hardness=1.0, drops=None,
             fragment_chance=0.0, light=None, emissive=False, natural=False, category='building')
    d.update(kw)
    if d['drops'] is None:
        d['drops'] = [{'item': id_, 'min': 1, 'max': 1, 'chance': 1.0}]
    return d


SOFT = dict(phaseable=True)
LIQ = dict(solid=False, transparent=True, liquid=True, tool='none', hardness=-1, drops=[])
PLANT = dict(shape='cross', solid=False, transparent=True, phaseable=True, tool='scythe', hardness=0.2)

BLOCKS = [
    B('grass', 'Grass', {'top': 'grass_top', 'side': 'grass_side', 'bottom': 'dirt_top'}, **SOFT, tool='shovel',
      hardness=0.6, natural=True, fragment_chance=0.02, category='terrain',
      drops=[{'item': 'dirt', 'min': 1, 'max': 1, 'chance': 1.0}, {'item': 'fiber', 'min': 1, 'max': 1, 'chance': 0.3}]),
    B('dirt', 'Dirt', {'top': 'dirt_top', 'side': 'dirt', 'bottom': 'dirt_top'}, **SOFT, tool='shovel', hardness=0.5, natural=True, fragment_chance=0.03,
      category='terrain'),
    B('grave_dirt', 'Graveyard Dirt', {'top': 'grave_dirt_top', 'side': 'grave_dirt', 'bottom': 'grave_dirt_top'}, **SOFT, tool='shovel', hardness=0.6, natural=True,
      fragment_chance=0.08, category='terrain',
      drops=[{'item': 'grave_dirt', 'min': 1, 'max': 1, 'chance': 1.0}, {'item': 'bone', 'min': 1, 'max': 2, 'chance': 0.25},
             {'item': 'buried_trinket', 'min': 1, 'max': 1, 'chance': 0.03}]),
    B('sand', 'Sand', {'top': 'sand_top', 'side': 'sand', 'bottom': 'sand_top'}, **SOFT, tool='shovel', hardness=0.4, natural=True, fragment_chance=0.02,
      category='terrain'),
    B('cobblestone', 'Cobblestone', {'all': 'cobblestone'}, tool='sledgehammer', hardness=2.0, category='building'),
    B('spectral_stone', 'Spectral Stone', {'all': 'spectral_stone'}, tool='sledgehammer', tier=2, hardness=3.0,
      natural=True, fragment_chance=0.10, emissive=True, light={'level': 3, 'color': '#5af2e6'}, category='terrain'),
    B('eerie_ore', 'Eerie Ore', {'all': 'eerie_ore'}, tool='sledgehammer', tier=1, hardness=2.5, natural=True,
      fragment_chance=0.25, emissive=True, light={'level': 6, 'color': '#a060ff'}, category='ore',
      drops=[{'item': 'eerie_shard', 'min': 1, 'max': 3, 'chance': 1.0}, {'item': 'spectral_stone', 'min': 1, 'max': 1, 'chance': 0.3}]),
    B('iron_ore', 'Iron Ore', {'all': 'iron_ore'}, tool='sledgehammer', tier=2, hardness=3.5, natural=True,
      fragment_chance=0.05, category='ore', drops=[{'item': 'iron', 'min': 1, 'max': 2, 'chance': 1.0}]),
    B('thatch', 'Thatch', {'top': 'thatch_top', 'side': 'thatch_side', 'bottom': 'thatch_top'}, **SOFT, tool='scythe',
      hardness=0.4, drops=[{'item': 'fiber', 'min': 2, 'max': 3, 'chance': 1.0}]),
    B('timber_planks', 'Timber Planks', {'all': 'timber_planks'}, **SOFT, tool='scythe', hardness=1.0,
      drops=[{'item': 'wood', 'min': 1, 'max': 1, 'chance': 1.0}]),
    B('plaster_wall', 'Plaster Wall', {'side': 'plaster_wall', 'top': 'plaster_top', 'bottom': 'plaster_top'},
      **SOFT, tool='scythe', hardness=0.8, drops=[{'item': 'wood', 'min': 1, 'max': 1, 'chance': 0.5}]),
    B('plaster_brace', 'Braced Plaster Wall', {'side': 'plaster_brace', 'top': 'plaster_top', 'bottom': 'plaster_top'},
      **SOFT, tool='scythe', hardness=0.8, drops=[{'item': 'wood', 'min': 1, 'max': 1, 'chance': 0.5}]),
    B('wheat', 'Wheat', {'all': 'wheat'}, **PLANT, natural=True, fragment_chance=0.02, category='plant',
      drops=[{'item': 'wheat', 'min': 1, 'max': 2, 'chance': 1.0}, {'item': 'fiber', 'min': 1, 'max': 1, 'chance': 0.5}]),
    B('grave_moss', 'Grave Moss', {'top': 'grave_moss_top', 'side': 'grave_moss_side', 'bottom': 'grave_dirt'}, **SOFT,
      tool='scythe', hardness=0.5, natural=True, fragment_chance=0.06, category='terrain',
      drops=[{'item': 'grave_moss', 'min': 1, 'max': 2, 'chance': 1.0}, {'item': 'grave_dirt', 'min': 1, 'max': 1, 'chance': 1.0}]),
    B('gravestone', 'Gravestone Block', {'front': 'gravestone_front', 'side': 'gravestone_side', 'top': 'stone',
                                         'bottom': 'stone'}, tool='sledgehammer', hardness=3.0, category='graveyard',
      directional=True),
    B('river_water', 'River Water', {'all': 'river_water'}, **LIQ, running_water=True, category='liquid'),
    B('still_water', 'Still Water', {'all': 'still_water'}, **LIQ, category='liquid'),
    B('stone', 'Stone', {'top': 'stone_top', 'side': 'stone', 'bottom': 'stone_top'}, tool='sledgehammer', hardness=2.5, natural=True, fragment_chance=0.03,
      category='terrain', drops=[{'item': 'cobblestone', 'min': 1, 'max': 1, 'chance': 1.0}]),
    B('mossy_stone_bricks', 'Mossy Spectral Bricks', {'all': 'mossy_stone_bricks'}, tool='sledgehammer', tier=2,
      hardness=3.0, category='building', build_tier=2),
    B('timber_beam', 'Timber Beam', {'side': 'timber_beam_side', 'top': 'timber_beam_end', 'bottom': 'timber_beam_end'},
      **SOFT, tool='scythe', hardness=1.2, drops=[{'item': 'wood', 'min': 1, 'max': 1, 'chance': 1.0}]),
    B('slate_roof', 'Slate Roof', {'top': 'slate_top', 'side': 'slate_side', 'bottom': 'slate_side'},
      tool='sledgehammer', hardness=1.5, category='building'),
    B('rough_wood', 'Rough Wood', {'all': 'rough_wood'}, **SOFT, tool='scythe', hardness=0.8, build_tier=1,
      drops=[{'item': 'wood', 'min': 1, 'max': 1, 'chance': 1.0}]),
    B('oak_log', 'Oak Log', {'top': 'oak_log_top', 'bottom': 'oak_log_top', 'side': 'oak_log_side'}, **SOFT,
      tool='scythe', hardness=1.5, natural=True, fragment_chance=0.03, category='terrain',
      drops=[{'item': 'wood', 'min': 2, 'max': 3, 'chance': 1.0}]),
    B('leaves', 'Leaves', {'all': 'leaves'}, **SOFT, transparent=True, tool='scythe', hardness=0.2, natural=True,
      fragment_chance=0.01, category='terrain', drops=[{'item': 'fiber', 'min': 1, 'max': 1, 'chance': 0.4}]),
    B('tall_grass', 'Grave Weeds', {'all': 'tall_grass'}, **PLANT, natural=True, fragment_chance=0.03,
      category='plant', drops=[{'item': 'fiber', 'min': 1, 'max': 2, 'chance': 1.0}]),
    B('flowers', 'Wildflowers', {'all': 'flowers'}, **PLANT, natural=True, fragment_chance=0.04, category='plant',
      drops=[{'item': 'flower', 'min': 1, 'max': 1, 'chance': 1.0}]),
    B('packed_path', 'Packed Path', {'top': 'path_top', 'side': 'dirt', 'bottom': 'dirt_top'}, **SOFT, tool='shovel',
      hardness=0.6, natural=True, fragment_chance=0.02, category='terrain',
      drops=[{'item': 'dirt', 'min': 1, 'max': 1, 'chance': 1.0}]),
    B('cobble_path', 'Cobbled Path', {'all': 'cobble_plain'}, tool='sledgehammer', hardness=2.0, category='building',
      drops=[{'item': 'cobblestone', 'min': 1, 'max': 1, 'chance': 1.0}]),
]

TIER_NAMES = {1: 'I', 2: 'II', 3: 'III', 4: 'IV'}


def bleed(col, alpha, iters=12):
    """Fill colour of transparent pixels from opaque neighbours (no dark fringes when filtered)."""
    m = (alpha > 0.5).astype(float)
    c = col * m[..., None]
    w = m.copy()
    for _ in range(iters):
        c2 = T.blur(c, 1, wrap=False)
        w2 = T.blur(w, 1, wrap=False)
        fill = (w < 0.5) & (w2 > 1e-4)
        c[fill] = c2[fill] / w2[fill][..., None]
        w[fill] = 1.0
    out = col.copy()
    out[m < 0.5] = c[m < 0.5]
    return out


def build():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'renders', 'task1'), exist_ok=True)
    n = len(TILE_PAINTERS)
    rows = math.ceil(n / COLS)
    atlas = np.zeros((rows * S, COLS * S, 4))
    normal = np.zeros((rows * S, COLS * S, 3))
    normal[..., :] = (0.5, 0.5, 1.0)
    height = np.zeros((rows * S, COLS * S, 3))
    emission = np.zeros((rows * S, COLS * S, 3))
    tile_index = {}
    for i, (name, painter, cube) in enumerate(TILE_PAINTERS):
        seed = 1000 + i * 17
        t = painter(seed)
        t = finish(t, seed, cube=cube)
        r, c = divmod(i, COLS)
        sl = (slice(r * S, (r + 1) * S), slice(c * S, (c + 1) * S))
        alpha = t['alpha'] if t['alpha'] is not None else np.ones((S, S))
        if t['alpha'] is not None:
            t['col'] = bleed(t['col'], alpha)
        atlas[sl[0], sl[1], :3] = t['col']
        atlas[sl[0], sl[1], 3] = alpha
        normal[sl[0], sl[1]] = T.normal_from_height(t['h'], 2.5, wrap=not cube)
        height[sl[0], sl[1]] = t['h'][..., None]
        if t['emit'] is not None:
            emission[sl[0], sl[1]] = np.clip(t['emit'], 0, 1)
        tile_index[name] = i
        print('tile', i, name)
    T.save_png(os.path.join(OUT, 'blocks_atlas.png'), atlas)
    T.save_png(os.path.join(OUT, 'blocks_normal.png'), normal)
    T.save_png(os.path.join(OUT, 'blocks_height.png'), height)
    T.save_png(os.path.join(OUT, 'blocks_emission.png'), emission)

    # flat preview sheet (tiles at 3x on grey, labels drawn by contact-sheet tool later)
    big = np.repeat(np.repeat(atlas, 3, 0), 3, 1)
    bg = np.ones_like(big[..., :3]) * np.array([0.47, 0.43, 0.45])
    a = big[..., 3:4]
    T.save_png(os.path.join(ROOT, 'renders', 'task1', 'block_tiles.png'), big[..., :3] * a + bg * (1 - a))

    blocks = []
    for k, b in enumerate(BLOCKS):
        faces = {}
        f = b['faces']
        if 'all' in f:
            faces = {'top': f['all'], 'bottom': f['all'], 'side': f['all']}
        else:
            faces = dict(f)
            faces.setdefault('bottom', faces.get('side'))
            faces.setdefault('top', faces.get('side'))
        tiles = {face: tile_index[t] for face, t in faces.items()}
        e = {k2: v for k2, v in b.items() if k2 != 'faces'}
        e['index'] = k + 1
        e['tiles'] = tiles
        e['tier_name'] = TIER_NAMES[e['tier']]
        blocks.append(e)
    doc = {
        'version': 1,
        'tile_size': S,
        'atlas': {'albedo': 'res://assets/blocks/blocks_atlas.png',
                  'normal': 'res://assets/blocks/blocks_normal.png',
                  'height': 'res://assets/blocks/blocks_height.png',
                  'emission': 'res://assets/blocks/blocks_emission.png',
                  'columns': COLS, 'rows': rows, 'tile_count': n,
                  'note': 'tile index = row*columns + col; import as Texture2DArray with columns x rows slices'},
        'tile_names': [t[0] for t in TILE_PAINTERS],
        'faces_note': 'tiles: top/bottom/side, optional front (+Z face when the block is placed facing south); '
                      'directional blocks rotate front toward the placer',
        'tools': ['none', 'scythe', 'shovel', 'sledgehammer'],
        'blocks': [{'id': 'air', 'index': 0, 'name': 'Air', 'solid': False, 'transparent': True, 'phaseable': True}]
                  + blocks,
    }
    with open(os.path.join(OUT, 'blocks.json'), 'w') as f:
        json.dump(doc, f, indent=1)
    print('blocks', len(blocks), 'tiles', n, 'atlas', atlas.shape)
    return doc


if __name__ == '__main__':
    build()
    print('DONE')
