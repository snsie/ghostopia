"""Cottage interior props (concept/locations/cottage_interior_night.png, concept/empty/cottage_interior_empty.png)."""
import math

from mathutils import Vector

import lib_geo as G
from props_common import add_flame, candle_geo, new, plank_panel, prop


@prop('hearth', 'interior', desc='stone fireplace with mantel, logs and fire; back against the wall (+Y)')
def hearth():
    p = new('hearth')
    m = p.main
    W, D = 1.9, 0.85
    m.box('cobble', (W + 0.3, D + 0.35, 0.16), (0, -0.12, 0.08), bevel=0.03, jitter=0.01)  # hearth slab
    for sx in (-1, 1):
        for k in range(4):
            m.box('cobble', (0.42, D, 0.34), (sx * (W / 2 - 0.21), 0.05, 0.33 + k * 0.33), bevel=0.04, jitter=0.012)
    m.box('cobble', (W, D, 0.4), (0, 0.05, 1.5), bevel=0.04, jitter=0.01)  # lintel course
    m.box('cobble', (W - 0.8, 0.25, 1.2), (0, D / 2 - 0.05, 0.75), bevel=0.03, jitter=0.01)  # back
    m.box('cobble', (W - 0.3, D - 0.3, 1.2), (0, 0.2, 2.3), bevel=0.04, jitter=0.012)  # chimney breast
    m.box('wood_dark', (W + 0.25, D + 0.12, 0.14), (0, -0.04, 1.77), bevel=0.03)  # mantel
    for sx in (-0.85, 0.85):
        m.box('wood_dark', (0.12, 0.3, 0.14), (sx, -0.3, 1.66), rot=(0.5, 0, 0), bevel=0.02)
    # andirons + grate
    for sx in (-0.3, 0.3):
        m.box('iron', (0.05, 0.4, 0.05), (sx, -0.05, 0.22), bevel=0.01)
        m.sphere('iron', 0.04, (sx, -0.27, 0.32), segs=6, rings=4)
        m.box('iron', (0.04, 0.04, 0.16), (sx, -0.27, 0.24), bevel=0.005)
    m.box('iron', (0.7, 0.03, 0.03), (0, -0.27, 0.36), bevel=0.005)
    for k in range(3):
        m.cyl('bark', 0.07, 0.07, 0.75, (0, 0.0 + k * 0.03, 0.27 + k * 0.08), rot=(0, math.pi / 2, (k - 1) * 0.35),
              segs=7, bevel=0.01)
    m.sphere('FLAME_ember', 0.18, (0, 0.0, 0.2), scale=(1.8, 1.0, 0.25), segs=8, rings=4, jitter=0.02)
    fire = p.add(G.Node('INT_fire', 'empty', (0, 0, 0.32)))
    fl = fire.add(G.MeshNode('FLAME_hearth', pivot=(0, 0, 0.32)))
    for (x, h, r) in ((-0.18, 0.4, 0.09), (0.0, 0.55, 0.12), (0.17, 0.38, 0.09)):
        fl.lathe('FLAME_fire', [(0.0, 0), (r, h * 0.25), (r * 0.8, h * 0.55), (r * 0.35, h * 0.85), (0.0, h)],
                 (x, -0.02, 0.3), segs=8)
        fl.lathe('FLAME_core', [(0.0, 0.0), (r * 0.6, h * 0.2), (r * 0.4, h * 0.45), (0.0, h * 0.65)],
                 (x, -0.06, 0.3), segs=8)
    fire.add(G.LightNode('LIGHT_hearth', (0, -0.45, 0.6), 120, (1.0, 0.55, 0.22), 0.25))
    fire.add(G.empty('FX_flame', (0, -0.05, 0.4)))
    p.add(G.empty('FX_smoke', (0, 0.25, 2.9)))
    # mantel decor: two candles
    for i, x in enumerate((-0.75, 0.7)):
        wick = candle_geo(m, (x, -0.05, 1.84), 0.04, 0.16 + 0.04 * i)
        add_flame(p, f'candle_{i + 1}', wick, energy=8)
    p.collision.append(((W, D, 2.9), (0, 0.05, 1.45)))
    return p


@prop('bed', 'interior', desc='wooden bed with quilt; headboard at +Y against the wall')
def bed():
    p = new('bed')
    m = p.main
    W, L = 1.1, 2.1
    for sx in (-W / 2, W / 2):
        for sy, h in ((L / 2, 1.15), (-L / 2, 0.75)):
            m.box('wood_dark', (0.1, 0.1, h), (sx, sy, h / 2), bevel=0.02)
            m.sphere('wood_dark', 0.07, (sx, sy, h + 0.04), segs=8, rings=5)
    m.box('wood', (W, 0.06, 0.6), (0, L / 2, 0.75), bevel=0.02)
    m.box('wood', (W, 0.06, 0.32), (0, -L / 2, 0.52), bevel=0.02)
    for sx in (-W / 2, W / 2):
        m.box('wood_dark', (0.06, L, 0.16), (sx, 0, 0.32), bevel=0.02)
    m.box('cloth_linen', (W - 0.08, L - 0.12, 0.2), (0, 0, 0.45), bevel=0.06)
    m.box('quilt', (W + 0.04, L * 0.66, 0.08), (0, -0.3, 0.57), bevel=0.04, jitter=0.01)
    m.box('quilt', (W + 0.06, 0.04, 0.3), (0, -0.3 - L * 0.33, 0.45), bevel=0.02)
    for sx in (-W / 2 - 0.02, W / 2 + 0.02):
        m.box('quilt', (0.04, L * 0.66, 0.26), (sx, -0.3, 0.46), bevel=0.02)
    m.box('cloth_linen', (W * 0.7, 0.35, 0.14), (0, L / 2 - 0.3, 0.62), bevel=0.06, jitter=0.01)
    p.collision.append(((W + 0.1, L, 0.65), (0, 0, 0.32)))
    p.add(G.empty('MARK_sleep', (0, 0.1, 0.62), 180))
    return p


@prop('table', 'interior', desc='kitchen table with lace runner')
def table():
    p = new('table')
    m = p.main
    m.box('wood_planks', (1.5, 0.85, 0.08), (0, 0, 0.78), bevel=0.025)
    for sx in (-0.62, 0.62):
        for sy in (-0.33, 0.33):
            m.box('wood', (0.1, 0.1, 0.74), (sx, sy, 0.37), bevel=0.02)
    for sy in (-0.33, 0.33):
        m.box('wood_dark', (1.2, 0.05, 0.1), (0, sy, 0.66), bevel=0.01)
    m.box('cloth_linen', (0.5, 0.9, 0.01), (0.1, 0, 0.825), bevel=0.003)
    p.collision.append(((1.5, 0.85, 0.82), (0, 0, 0.41)))
    p.add(G.empty('MARK_use', (0, -0.7, 0), 0))
    return p


@prop('chair', 'interior', desc='ladder-back kitchen chair')
def chair():
    p = new('chair')
    m = p.main
    for sx in (-0.2, 0.2):
        m.box('wood', (0.06, 0.06, 0.45), (sx, -0.18, 0.22), bevel=0.012)
        m.box('wood', (0.07, 0.07, 1.05), (sx, 0.19, 0.52), rot=(-0.06, 0, 0), bevel=0.015)
    m.box('wood_planks', (0.5, 0.48, 0.06), (0, 0, 0.47), bevel=0.02)
    for z in (0.7, 0.86, 1.0):
        m.box('wood', (0.42, 0.05, 0.08), (0, 0.21, z), rot=(-0.06, 0, 0), bevel=0.012)
    p.collision.append(((0.5, 0.5, 1.05), (0, 0, 0.52)))
    p.add(G.empty('MARK_sit', (0, -0.02, 0.5), 0))
    return p


@prop('shelf', 'interior', desc='standing shelf with jars and books (doll goes on the middle board)')
def shelf():
    p = new('shelf')
    m = p.main
    W, D, H = 1.0, 0.32, 1.9
    for sx in (-W / 2, W / 2):
        m.box('wood', (0.06, D, H), (sx, 0, H / 2), bevel=0.015)
    m.box('wood_planks', (W, 0.04, H), (0, D / 2 - 0.02, H / 2), bevel=0.01)
    for z in (0.05, 0.6, 1.15, 1.7):
        m.box('wood', (W + 0.04, D + 0.02, 0.05), (0, 0, z), bevel=0.012)
    m.box('wood_dark', (W + 0.12, D + 0.08, 0.08), (0, 0, H), bevel=0.02)
    # jars and books
    _jar(m, (-0.3, 0, 1.175), 0.09, 0.2, 'GLOW_jar')
    _jar(m, (-0.08, 0, 1.175), 0.07, 0.16, 'glass')
    _books(m, (0.25, 0, 1.175))
    _books(m, (-0.25, 0, 0.625), lean=True)
    _jar(m, (0.25, 0, 0.625), 0.08, 0.18, 'glass')
    _jar(m, (0.0, 0, 1.725), 0.06, 0.14, 'glass')
    _jar(m, (0.25, 0, 1.725), 0.07, 0.18, 'GLOW_jar')
    p.add(G.LightNode('LIGHT_jar', (-0.3, -0.05, 1.3), 4, (1.0, 0.7, 0.35), 0.05))
    p.add(G.empty('MARK_doll', (0.0, 0.0, 0.625), 0))
    p.collision.append(((W, D, H), (0, 0, H / 2)))
    return p


def _jar(m, base, r, h, glass_mat):
    b = Vector(base)
    m.lathe(glass_mat, [(0.0, 0.0), (r, 0.0), (r * 1.05, h * 0.75), (r * 0.7, h * 0.9), (r * 0.7, h), (0.0, h)], b,
            segs=10)
    m.cyl('wood', r * 0.75, r * 0.75, 0.03, b + Vector((0, 0, h + 0.015)), segs=10, bevel=0.005)
    if glass_mat == 'glass':
        m.cyl('wisteria' if r < 0.075 else 'leaf', r * 0.8, r * 0.85, h * 0.5, b + Vector((0, 0, h * 0.26)), segs=8,
              bevel=0.005)


def _books(m, base, lean=False):
    b = Vector(base)
    mats = ('book_red', 'book_purple', 'book_brown')
    if lean:
        for i, mat in enumerate(mats):
            m.box(mat, (0.22, 0.16, 0.04), b + Vector((0, 0, 0.02 + i * 0.042)), rot=(0, 0, i * 0.15), bevel=0.008)
    else:
        for i, mat in enumerate(mats):
            m.box(mat, (0.045, 0.17, 0.22 - i * 0.02), b + Vector((-0.06 + i * 0.05, 0, (0.22 - i * 0.02) / 2)),
                  bevel=0.008)
        m.box('book_brown', (0.045, 0.16, 0.2), b + Vector((0.1, 0, 0.1)), rot=(0, 0.35, 0), bevel=0.008)


@prop('jar', 'interior', desc='glass jar (herbs)')
def jar():
    p = new('jar')
    _jar(p.main, (0, 0, 0), 0.08, 0.2, 'glass')
    return p


@prop('jar_glow', 'interior', desc='glowing jar (fireflies / embers)')
def jar_glow():
    p = new('jar_glow')
    _jar(p.main, (0, 0, 0), 0.08, 0.2, 'GLOW_jar')
    p.add(G.LightNode('LIGHT_jar', (0, 0, 0.12), 4, (1.0, 0.7, 0.35), 0.05))
    return p


@prop('books', 'interior', desc='stack of books')
def books():
    p = new('books')
    m = p.main
    z = 0.0
    for i, (mat, w, d, h) in enumerate((('book_purple', 0.3, 0.22, 0.06), ('book_red', 0.27, 0.2, 0.05),
                                         ('book_brown', 0.25, 0.19, 0.06))):
        m.box(mat, (w, d, h), (0, 0, z + h / 2), rot=(0, 0, (i - 1) * 0.2), bevel=0.01)
        m.box('paper', (w - 0.03, d - 0.015, h - 0.016), (0.014, 0, z + h / 2), rot=(0, 0, (i - 1) * 0.2), bevel=0.004)
        z += h
    return p


@prop('rug', 'interior', desc='woven rug 2.2 x 1.5 m (no collision)')
def rug():
    p = new('rug')
    p.main.box('rug', (2.2, 1.5, 0.02), (0, 0, 0.01), bevel=0.005, uv='fit_top')
    return p


@prop('chest', 'interior', desc='iron-banded chest; lid hinged at the back')
def chest():
    p = new('chest')
    m = p.main
    W, D, H = 0.95, 0.55, 0.45
    m.box('wood_planks', (W, D, H), (0, 0, H / 2), bevel=0.02)
    for sx in (-0.3, 0.3):
        m.box('iron', (0.06, D + 0.02, H + 0.01), (sx, 0, H / 2), bevel=0.008)
    lid = p.add(G.MeshNode('INT_chest_lid', pivot=(0, D / 2, H)))
    lid.cyl('wood_planks', D / 2, D / 2, W, (0, 0, H), rot=(0, math.pi / 2, 0), segs=12, bevel=0.01)
    for sx in (-0.3, 0.3):
        lid.cyl('iron', D / 2 + 0.012, D / 2 + 0.012, 0.06, (sx, 0, H), rot=(0, math.pi / 2, 0), segs=12, bevel=0.005)
    lid.box('iron', (0.1, 0.03, 0.12), (0, -D / 2 - 0.01, H), bevel=0.01)
    p.collision.append(((W, D, H + D / 2), (0, 0, (H + D / 2) / 2)))
    return p


@prop('side_table', 'interior', desc='small side table with a drawer')
def side_table():
    p = new('side_table')
    m = p.main
    m.box('wood_planks', (0.6, 0.5, 0.06), (0, 0, 0.66), bevel=0.02)
    m.box('wood', (0.52, 0.42, 0.14), (0, 0, 0.56), bevel=0.015)
    m.box('wood_dark', (0.3, 0.02, 0.08), (0, -0.215, 0.56), bevel=0.008)
    m.sphere('brass', 0.02, (0, -0.235, 0.56), segs=6, rings=4)
    for sx in (-0.24, 0.24):
        for sy in (-0.18, 0.18):
            m.box('wood', (0.06, 0.06, 0.5), (sx, sy, 0.25), bevel=0.012)
    p.collision.append(((0.6, 0.5, 0.7), (0, 0, 0.35)))
    return p


@prop('basket', 'interior', desc='wicker basket with yarn balls')
def basket():
    p = new('basket')
    m = p.main
    m.lathe('straw', [(0.0, 0.0), (0.2, 0.0), (0.25, 0.25), (0.23, 0.25), (0.18, 0.03), (0.0, 0.03)], (0, 0, 0), segs=12)
    for (x, y, mat) in ((-0.07, 0.03, 'cloth_purple'), (0.08, -0.02, 'cloth_linen'), (0.0, 0.09, 'cloth_blue')):
        m.sphere(mat, 0.09, (x, y, 0.2), segs=8, rings=6)
    m.tube('rope', [(-0.24, 0, 0.25), (0, 0, 0.45), (0.24, 0, 0.25)], 0.015, 5)
    return p


@prop('curtains', 'interior', desc='curtain rod and two linen curtains for a 1 m window, wall-mounted (sill 1 m)')
def curtains():
    p = new('curtains')
    m = p.main
    m.cyl('brass', 0.02, 0.02, 1.5, (0, -0.12, 2.1), rot=(0, math.pi / 2, 0), segs=6, bevel=0.003)
    for sx in (-0.65, 0.65):
        m.sphere('brass', 0.035, (sx + (0.1 if sx > 0 else -0.1), -0.12, 2.1), segs=6, rings=4)
        for k in range(3):
            m.box('cloth_linen', (0.1, 0.06, 1.2), (sx + (k - 1) * 0.09, -0.12 - 0.02 * (k % 2), 1.48), bevel=0.02,
                  jitter=0.006)
        m.box('rope', (0.32, 0.08, 0.05), (sx, -0.14, 1.35), bevel=0.01)
    return p
