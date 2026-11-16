"""Shared tileable prop textures -> assets/textures/*.png (numpy-painted).

Reuses the block painters (same hand-painted look as the voxels) at 128 px, plus prop-only ones.
Run: python blender/scripts/make_textures.py   (or inside Blender with -P)
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_tex as T  # noqa: E402
import make_block_textures as M  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'textures')
N = 128
R = T.rgb


def reuse(painter, seed, size=N):
    M.S = size
    t = painter(seed)
    col = T.apply_shade(t['col'], t['h'], strength=2.5, light=0.22, dark=0.3)
    M.S = 64
    return np.clip(col, 0, 1)


def grid():
    return T.grid(N)


def p_iron(seed):
    nz = T.value_noise(N, 6, seed, 4)
    col = T.ramp(nz, [(0, R(52, 50, 64)), (0.5, R(84, 82, 98)), (1, R(120, 118, 134))])
    rust = np.clip((T.value_noise(N, 5, seed + 1, 3) - 0.62) * 5, 0, 1)
    col = T.stamp(col, rust, R(150, 84, 50), 0.7)
    yy, xx = grid()
    for cy in (12, 76):
        for cx in (12, 76):
            col = T.stamp(col, T.disk_mask(N, cy, cx, 4), R(40, 38, 50))
            col = T.stamp(col, T.disk_mask(N, cy - 1.5, cx - 1.5, 1.8), R(150, 150, 166))
    return col


def p_brass(seed):
    nz = T.value_noise(N, 4, seed, 4)
    col = T.ramp(nz, [(0, R(130, 80, 34)), (0.5, R(196, 136, 56)), (0.85, R(232, 186, 96)), (1, R(250, 226, 160))])
    return col


def p_wax(seed):
    yy, xx = grid()
    n = T.value_noise(N, 6, seed, 3)
    drips = T.value_noise((N, N), 1, seed + 1, 1)
    streak = np.sin(xx * 0.3 + n * 4) * 0.5 + 0.5
    col = T.ramp(0.5 * streak + 0.5 * n, [(0, R(220, 200, 170)), (0.6, R(244, 232, 206)), (1, R(255, 250, 236))])
    return col


def p_plaid(seed):
    yy, xx = grid()
    base = R(150, 56, 60)
    col = np.zeros((N, N, 3)) + base
    for p, w, c in ((32, 10, R(110, 70, 120)), (32, 4, R(226, 168, 80)), (16, 2, R(70, 30, 40))):
        mx = ((xx % p) < w).astype(float)
        my = ((yy % p) < w).astype(float)
        col = T.stamp(col, mx, c, 0.55)
        col = T.stamp(col, my, c, 0.55)
    weave = ((xx + yy) % 4 < 2) * 0.08
    col = col * (0.92 + weave[..., None]) * (0.9 + 0.2 * T.value_noise(N, 6, seed, 2))[..., None]
    return col


def p_linen(seed):
    yy, xx = grid()
    weave = (np.sin(xx * 1.6) * np.sin(yy * 1.6)) * 0.04
    n = T.value_noise(N, 6, seed, 3)
    col = T.ramp(n, [(0, R(214, 204, 190)), (1, R(244, 238, 226))])
    return col * (1 + weave[..., None])


def p_quilt(seed):
    yy, xx = grid()
    cell = 32
    cid = (yy // cell).astype(int) * 4 + (xx // cell).astype(int)
    pal = [R(150, 120, 196), R(110, 120, 180), R(232, 220, 206), R(190, 120, 150), R(120, 150, 170)]
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(pal), 16)
    col = np.array(pal)[pick[cid]]
    seam = (((yy % cell) < 1.5) | ((xx % cell) < 1.5)).astype(float)
    stitch = ((((yy % cell) - 4) % 6 < 3) & (np.abs((xx % cell) - 3) < 0.8)).astype(float)
    col = T.stamp(col, seam, R(80, 60, 90), 0.7)
    col = T.stamp(col, stitch, R(250, 240, 230), 0.6)
    return col * (0.92 + 0.12 * T.value_noise(N, 8, seed, 2))[..., None]


def p_canvas(seed):
    col = p_linen(seed) * np.array([0.97, 0.94, 0.88])
    yy, xx = grid()
    seam = ((yy % 64) < 2).astype(float)
    return T.stamp(col, seam, R(170, 150, 130), 0.6)


def p_pumpkin(seed):
    yy, xx = grid()
    rib = np.abs(np.sin(xx / N * math.pi * 4))
    n = T.value_noise(N, 6, seed, 3)
    col = T.ramp(0.6 * rib + 0.4 * n, [(0, R(170, 70, 20)), (0.5, R(232, 118, 34)), (1, R(250, 160, 60))])
    return col


def p_wisteria(seed):
    t = M.p_leaves  # base of clusters
    f1, f2, idx, _ = T.voronoi(N, 70, seed)
    v = T.per_id_random(idx, seed + 1)
    col = T.ramp(v, [(0, R(130, 80, 190)), (0.5, R(176, 120, 230)), (1, R(220, 180, 250))])
    col = col * (0.75 + 0.35 * np.clip(1 - f1 / 6, 0, 1))[..., None]
    return col


def p_paper(seed):
    n = T.value_noise(N, 4, seed, 4)
    col = T.ramp(n, [(0, R(214, 190, 150)), (1, R(240, 224, 190))])
    yy, xx = grid()
    for k in range(6):
        y = 22 + k * 16
        col = T.stamp(col, T.line_mask(N, (y, 16), (y, 112 - (k % 3) * 18), 1.6), R(120, 96, 80), 0.5)
    return col


def p_rug(seed):
    yy, xx = grid()
    u = xx / N
    v = yy / N
    col = np.zeros((N, N, 3)) + R(128, 64, 96)
    inner = (np.abs(u - 0.5) < 0.40) & (np.abs(v - 0.5) < 0.40)
    col[inner] = R(150, 86, 118)
    border = ((np.abs(u - 0.5) < 0.44) & (np.abs(v - 0.5) < 0.44)) & ~inner
    col[border] = R(232, 206, 176)
    pat = (np.sin(u * 60) * np.sin(v * 60) > 0.3) & border
    col[pat] = R(110, 60, 90)
    d = np.abs(u - 0.5) + np.abs(v - 0.5)
    med = (d < 0.16) & (d > 0.11)
    col[med] = R(236, 210, 180)
    col[d < 0.05] = R(236, 210, 180)
    fringe = (np.abs(v - 0.5) > 0.47) & ((xx % 4) < 2)
    col[fringe] = R(236, 220, 200)
    return col * (0.9 + 0.15 * T.value_noise(N, 16, seed, 2))[..., None]


def p_portrait(seed):
    """Original painted portrait: an old village elder with a hat and a big moustache, eyes left blank
    (the INT_portrait_eyes mesh sits on top)."""
    n = 256
    yy, xx = T.grid(n)
    nz = T.value_noise(n, 6, seed, 4)
    col = T.ramp(nz * 0.6 + yy / n * 0.4, [(0, R(70, 46, 40)), (1, R(120, 84, 60))])
    # coat
    coat = T.ellipse_mask(n, 250, 128, 90, 110)
    col = T.stamp(col, coat, R(110, 70, 52))
    col = T.stamp(col, T.poly_mask(n, [(175, 112), (175, 144), (240, 128)]), R(232, 220, 200))
    # face
    face = T.ellipse_mask(n, 130, 128, 52, 44)
    col = T.stamp(col, face, R(232, 178, 140))
    col = T.stamp(col, T.ellipse_mask(n, 140, 128, 12, 14), R(214, 140, 112))  # nose
    # beard + moustache
    col = T.stamp(col, T.ellipse_mask(n, 170, 128, 26, 44), R(236, 232, 226))
    col = T.stamp(col, T.ellipse_mask(n, 152, 106, 10, 24), R(246, 244, 240))
    col = T.stamp(col, T.ellipse_mask(n, 152, 150, 10, 24), R(246, 244, 240))
    col = T.stamp(col, T.ellipse_mask(n, 140, 128, 10, 12), R(222, 150, 118))
    # brows
    col = T.stamp(col, T.ellipse_mask(n, 106, 108, 5, 14), R(236, 232, 226))
    col = T.stamp(col, T.ellipse_mask(n, 106, 148, 5, 14), R(236, 232, 226))
    # closed-eye lines (painted eyes are 'asleep'; the haunted eyes mesh opens them)
    col = T.stamp(col, T.line_mask(n, (120, 100), (122, 116), 3), R(80, 50, 40))
    col = T.stamp(col, T.line_mask(n, (122, 140), (120, 156), 3), R(80, 50, 40))
    # hat
    col = T.stamp(col, T.ellipse_mask(n, 84, 128, 14, 78), R(96, 70, 50))
    col = T.stamp(col, T.ellipse_mask(n, 60, 128, 34, 50) * (yy < 84), R(110, 80, 56))
    col = T.stamp(col, (np.abs(yy - 78) < 5) * T.ellipse_mask(n, 78, 128, 12, 50), R(70, 48, 36))
    col = T.apply_shade(col, T.blur(face * 0.5 + coat * 0.3, 3), strength=8)
    vign = np.clip(1 - (((yy - 128) / 150) ** 2 + ((xx - 128) / 150) ** 2), 0.5, 1)
    return col * vign[..., None]


def p_bone(seed):
    n = T.value_noise(N, 6, seed, 3)
    return T.ramp(n, [(0, R(206, 196, 176)), (1, R(244, 238, 224))])


def p_book(seed):
    yy, xx = grid()
    n = T.value_noise(N, 8, seed, 3)
    col = T.ramp(n, [(0, R(170, 160, 150)), (1, R(220, 212, 200))])
    bands = (np.abs((yy % 64) - 10) < 2.5) | (np.abs((yy % 64) - 54) < 2.5)
    col = T.stamp(col, bands.astype(float), R(250, 220, 140), 0.9)
    return col


def p_ceramic(seed):
    yy, xx = grid()
    n = T.value_noise(N, 4, seed, 3)
    col = T.ramp(n, [(0, R(220, 214, 200)), (1, R(250, 246, 236))])
    stripe = (np.abs((yy % 64) - 32) < 3).astype(float)
    return T.stamp(col, stripe, R(110, 120, 180), 0.8)


def p_crystal(seed):
    f1, f2, idx, _ = T.voronoi(N, 10, seed)
    v = T.per_id_random(idx, seed + 1)
    col = T.ramp(0.6 * v + 0.4 * np.clip(f1 / 30, 0, 1), [(0, R(150, 90, 230)), (0.6, R(200, 150, 255)), (1, R(250, 230, 255))])
    col = T.stamp(col, np.clip(1.5 - (f2 - f1), 0, 1), R(255, 240, 255), 0.7)
    return col


def p_portal(seed):
    n = 256
    yy, xx = T.grid(n)
    cy, cx = 128, 128
    dy, dx = (yy - cy) / 128, (xx - cx) / 128
    r = np.sqrt(dx * dx + dy * dy)
    a = np.arctan2(dy, dx)
    sw = np.sin(a * 2 + r * 9 + T.value_noise(n, 4, seed, 3) * 3) * 0.5 + 0.5
    v = np.clip(0.55 * sw + 0.5 * (1 - r), 0, 1)
    col = T.ramp(v, [(0, R(60, 20, 110)), (0.45, R(140, 60, 220)), (0.75, R(200, 130, 255)), (1, R(255, 220, 255))])
    rng = np.random.default_rng(seed)
    for _ in range(40):
        col = T.stamp(col, T.disk_mask(n, *rng.uniform(10, 246, 2), rng.uniform(0.8, 2.2)), R(255, 240, 255))
    return col


def p_window_glow(seed):
    yy, xx = grid()
    d = np.sqrt(((yy - 70) / 70) ** 2 + ((xx - 64) / 64) ** 2)
    col = T.ramp(np.clip(1 - d, 0, 1), [(0, R(220, 110, 40)), (0.6, R(255, 170, 70)), (1, R(255, 230, 150))])
    # hint of curtains at the sides
    cur = ((xx < 20) | (xx > 108)).astype(float) * 0.5
    return T.stamp(col, cur, R(200, 120, 70), 0.5)


def p_spectral(seed):
    yy, xx = grid()
    n = T.value_noise(N, 4, seed, 4)
    col = T.ramp(n, [(0, R(150, 200, 230)), (0.6, R(206, 236, 255)), (1, R(250, 254, 255))])
    sw = T.spiral_mask(N, 64, 64, 40, turns=2.5, width=3) + T.spiral_mask(N, 20, 100, 14, 2, 2)
    col = T.stamp(col, np.clip(sw, 0, 1), R(255, 255, 255), 0.8)
    return col


def p_straw(seed):
    return reuse(lambda s: M.p_thatch(s, True), seed)


def p_leaf_solid(seed):
    M.S = N
    t = M.p_leaves(seed)
    M.S = 64
    return np.clip(T.apply_shade(t['col'], t['h'], 2.5), 0, 1)


def p_grain(seed, base=R(176, 108, 72), dark=R(118, 70, 50), light=R(210, 142, 96)):
    yy, xx = grid()
    n = T.value_noise(N, 2, seed, 3)
    n2 = T.value_noise(N, 8, seed + 1, 2)
    g = np.sin(yy / N * 2 * math.pi * 6 + n * 7 + 0.4 * np.sin(xx / N * 2 * math.pi)) * 0.5 + 0.5
    v = 0.5 + 0.22 * (g - 0.5) + 0.25 * (n2 - 0.5) + 0.2 * (n - 0.5)
    col = T.ramp(v, [(0, dark), (0.5, base), (1, light)])
    # a few knots
    for cy, cx in ((40, 30), (96, 92)):
        k = T.ellipse_mask(N, cy, cx, 3, 7)
        col = T.stamp(col, k, dark * 0.8, 0.9)
    # fine streaks along u
    streak = T.value_noise((N, N), 1, seed + 3, 1)
    col = col * (0.92 + 0.12 * T.blur(np.random.default_rng(seed).random((N, N)), 1)[..., None] * 0
                 + 0.1 * (np.sin(yy * 1.9 + n * 20) * 0.5 + 0.5)[..., None])
    return col


def p_stone_smooth(seed):
    n = T.value_noise(N, 4, seed, 5)
    f1, f2, idx, _ = T.voronoi(N, 6, seed + 1)
    col = T.ramp(0.7 * n + 0.3 * T.per_id_random(idx, seed + 2), [(0, R(118, 108, 126)), (0.5, R(150, 140, 156)),
                                                                   (1, R(184, 176, 188))])
    crack = np.clip(1.0 - (f2 - f1), 0, 1) * (T.value_noise(N, 3, seed + 3, 2) > 0.55)
    col = T.stamp(col, crack, R(90, 80, 100), 0.6)
    spots = np.clip((T.value_noise(N, 10, seed + 4, 2) - 0.7) * 6, 0, 1)
    return T.stamp(col, spots, R(126, 140, 96), 0.5)


def build():
    os.makedirs(OUT, exist_ok=True)
    jobs = {
        'wood': lambda s: reuse(lambda q: M.planks(q, rows=4, nails=False), s),
        'wood_dark': lambda s: reuse(lambda q: M.planks(q, base=R(112, 72, 54), dark=R(70, 44, 40),
                                                          light=R(140, 92, 66), rows=3, nails=False), s),
        'wood_weathered': lambda s: reuse(lambda q: M.planks(q, base=R(140, 108, 90), dark=R(92, 70, 62),
                                                               light=R(178, 146, 120), rows=4, nails=False,
                                                               weather=0.3), s),
        'bark': lambda s: reuse(M.p_log_side, s),
        'stone': lambda s: reuse(M.p_stone, s),
        'stone_mossy': lambda s: reuse(M.p_mossy_bricks, s),
        'cobble': lambda s: reuse(M.p_cobble, s),
        'plaster': lambda s: reuse(lambda q: M.p_plaster(q, frame=False), s),
        'thatch': lambda s: reuse(lambda q: M.p_thatch(q, False), s),
        'slate': lambda s: reuse(M.p_slate, s),
        'dirt': lambda s: reuse(M.p_dirt, s),
        'grass': lambda s: reuse(M.p_grass_top, s),
        'grave_dirt': lambda s: reuse(M.p_grave_dirt, s),
        'wood_grain': p_grain,
        'wood_grain_dark': lambda s: p_grain(s, R(112, 72, 54), R(70, 44, 38), R(146, 98, 70)),
        'stone_smooth': p_stone_smooth,
        'iron': p_iron, 'brass': p_brass, 'wax': p_wax, 'cloth_plaid': p_plaid, 'cloth_linen': p_linen,
        'quilt': p_quilt, 'canvas': p_canvas, 'straw': p_straw, 'pumpkin': p_pumpkin, 'leaf': p_leaf_solid,
        'wisteria': p_wisteria, 'paper': p_paper, 'rug': p_rug, 'portrait': p_portrait, 'bone': p_bone,
        'book': p_book, 'ceramic': p_ceramic, 'crystal': p_crystal, 'portal': p_portal,
        'window_glow': p_window_glow, 'spectral': p_spectral,
    }
    for i, (name, fn) in enumerate(jobs.items()):
        img = fn(500 + i * 13)
        T.save_png(os.path.join(OUT, name + '.png'), img)
        print('texture', name, img.shape)
    # preview sheet
    tiles = []
    for name in jobs:
        a = T.load_png(os.path.join(OUT, name + '.png'))[..., :3]
        if a.shape[0] != N:
            a = a[::a.shape[0] // N, ::a.shape[1] // N]
        tiles.append(a)
    cols = 8
    rows = math.ceil(len(tiles) / cols)
    sheet = np.ones((rows * (N + 4), cols * (N + 4), 3)) * 0.45
    for k, a in enumerate(tiles):
        r, c = divmod(k, cols)
        sheet[r * (N + 4):r * (N + 4) + N, c * (N + 4):c * (N + 4) + N] = a
    os.makedirs(os.path.join(ROOT, 'renders', 'task1'), exist_ok=True)
    T.save_png(os.path.join(ROOT, 'renders', 'task1', 'prop_textures.png'), sheet)


if __name__ == '__main__':
    build()
    print('DONE')
