"""Millbrook village props (concept/locations/millbrook_*.png, concept/locations/mill_night.png)."""
import math

from mathutils import Vector

import lib_geo as G
from props_common import add_flame, candle_geo, lantern_geo, new, plank_panel, prop


@prop('window_cottage', 'village', desc='window for a 1x1 opening: frame, mullions, warm glass, open shutters')
def window_cottage():
    """Pivot = bottom centre of the opening, middle of the wall (place at sill height)."""
    p = new('window_cottage')
    m = p.main
    t = 0.09
    for (sx, sz, cx, cz) in ((1.0, t, 0, 0.045), (1.0, t, 0, 1.0 - 0.045), (t, 1.0, -0.455, 0.5), (t, 1.0, 0.455, 0.5)):
        m.box('wood_dark', (sx, 0.5, sz), (cx, -0.1, cz), bevel=0.015)
    m.box('wood_dark', (1.12, 0.22, 0.08), (0, -0.4, 0.0), bevel=0.02)  # sill
    m.box('wood_dark', (0.05, 0.08, 0.84), (0, -0.12, 0.5), bevel=0.008)
    m.box('wood_dark', (0.84, 0.08, 0.05), (0, -0.12, 0.5), bevel=0.008)
    m.box('GLOW_window', (0.84, 0.02, 0.84), (0, -0.08, 0.5), bevel=0, uv='fit')
    for side, sx in (('L', -1), ('R', 1)):
        hinge = (sx * 0.5, -0.36, 0.5)
        sh = p.add(G.MeshNode(f'INT_shutter_{side}', pivot=hinge))
        # open: lying flat against the outside wall beside the window
        plank_panel(sh, 'wood_planks', min(sx * 0.52, sx * 0.98), max(sx * 0.52, sx * 0.98), 0.06, 0.94, -0.38,
                    thick=0.04, n=3)
        sh.box('wood_dark', (0.44, 0.03, 0.06), (sx * 0.75, -0.41, 0.25), bevel=0.008)
        sh.box('wood_dark', (0.44, 0.03, 0.06), (sx * 0.75, -0.41, 0.75), bevel=0.008)
    p.add(G.LightNode('LIGHT_window', (0, 0.4, 0.55), 15, (1.0, 0.65, 0.3), 0.2))
    return p


@prop('window_round', 'village', desc='arched window (tavern, cottage gable) for a 1x1 opening')
def window_round():
    p = new('window_round')
    m = p.main
    from props_common import arch_outline
    outer = arch_outline(1.0, 1.0, 12)
    inner = arch_outline(0.8, 0.88, 12)
    # frame as ring: draw outer slab with glass inset in front
    m.ext('wood_dark', outer, 0.12, (0, -0.42, 0), bevel=0.015)
    m.ext('GLOW_window', [(x, z + 0.06) for x, z in inner], 0.02, (0, -0.49, 0), bevel=0, uv='fit')
    m.box('wood_dark', (0.05, 0.03, 0.85), (0, -0.505, 0.5), bevel=0.006)
    m.box('wood_dark', (0.8, 0.03, 0.05), (0, -0.505, 0.45), bevel=0.006)
    m.box('stone', (1.1, 0.2, 0.08), (0, -0.48, -0.02), bevel=0.02)
    p.add(G.LightNode('LIGHT_window', (0, 0.4, 0.55), 12, (1.0, 0.65, 0.3), 0.2))
    return p


@prop('flower_box', 'village', desc='window flower box, wall-mounted under a sill at 1 m')
def flower_box():
    p = new('flower_box')
    m = p.main
    m.box('wood_planks', (0.95, 0.24, 0.2), (0, -0.14, 0.88), bevel=0.02)
    m.box('dirt', (0.88, 0.18, 0.04), (0, -0.14, 0.98), bevel=0.01)
    for sx in (-0.38, 0.38):
        m.box('wood_dark', (0.05, 0.2, 0.2), (sx, -0.12, 0.72), rot=(0.7, 0, 0), bevel=0.01)
    G.seed(11)
    for k in range(9):
        x = -0.4 + k * 0.1
        m.sphere('leaf', 0.06, (x, -0.14, 1.03), scale=(1, 0.8, 0.6), segs=6, rings=4, jitter=0.01)
    for k in range(7):
        x = -0.36 + k * 0.12
        mat = 'cloth_purple' if k % 2 == 0 else 'cloth_linen'
        m.sphere(mat, 0.04, (x, -0.16 + 0.04 * (k % 2), 1.1), segs=6, rings=4)
    m.tube('vine', [(-0.3, -0.25, 1.0), (-0.32, -0.27, 0.85), (-0.28, -0.26, 0.75)], 0.015, 4)
    return p


@prop('barrel', 'village', desc='oak barrel with iron hoops')
def barrel():
    p = new('barrel')
    m = p.main
    prof = [(0.0, 0.0), (0.28, 0.0)] + [(0.28 + 0.06 * math.sin(i / 8 * math.pi), i / 8 * 0.8) for i in range(1, 8)] + \
           [(0.28, 0.8), (0.0, 0.8)]
    m.lathe('wood_planks', prof, (0, 0, 0), segs=14)
    m.cyl('wood_dark', 0.25, 0.25, 0.02, (0, 0, 0.8), segs=14, bevel=0.005)
    for z in (0.12, 0.3, 0.5, 0.68):
        r = 0.28 + 0.06 * math.sin(z / 0.8 * math.pi) + 0.012
        m.cyl('iron', r, r, 0.04, (0, 0, z), segs=14, bevel=0.005, cap=False)
    p.collision.append(((0.66, 0.66, 0.8), (0, 0, 0.4)))
    return p


@prop('crate', 'village', desc='wooden crate with braces')
def crate():
    p = new('crate')
    m = p.main
    m.box('wood_planks', (0.62, 0.62, 0.62), (0, 0, 0.31), bevel=0.02)
    for sy in (-0.32, 0.32):
        for (sx, sz, cx, cz) in ((0.66, 0.07, 0, 0.04), (0.66, 0.07, 0, 0.58), (0.07, 0.62, -0.3, 0.31),
                                 (0.07, 0.62, 0.3, 0.31)):
            m.box('wood_dark', (sx, 0.04, sz), (cx, sy, cz), bevel=0.01)
        m.box('wood_dark', (0.07, 0.04, 0.78), (0, sy, 0.31), rot=(0, 0.785, 0), bevel=0.01)
    p.collision.append(((0.62, 0.62, 0.62), (0, 0, 0.31)))
    return p


@prop('grain_sack', 'village', desc='lumpy burlap grain sack, tied top')
def grain_sack():
    p = new('grain_sack')
    m = p.main
    m.sphere('burlap', 0.25, (0, 0, 0.25), scale=(1, 0.85, 1.15), segs=10, rings=7, jitter=0.02)
    m.cyl('rope', 0.07, 0.07, 0.05, (0, 0, 0.5), segs=8, bevel=0.01)
    m.lathe('burlap', [(0.07, 0), (0.1, 0.06), (0.06, 0.1), (0.0, 0.09)], (0, 0, 0.52), segs=8, jitter=0.01)
    return p


@prop('bench', 'village', desc='plank bench, 1.6 m')
def bench():
    p = new('bench')
    m = p.main
    m.box('wood_planks', (1.6, 0.36, 0.07), (0, 0, 0.45), bevel=0.02)
    for sx in (-0.6, 0.6):
        m.box('wood_dark', (0.08, 0.3, 0.42), (sx, 0, 0.21), bevel=0.015)
        m.box('wood_dark', (0.06, 0.32, 0.06), (sx, 0, 0.1), bevel=0.01)
    p.collision.append(((1.6, 0.36, 0.5), (0, 0, 0.25)))
    p.add(G.empty('MARK_sit_1', (-0.4, -0.05, 0.48), 0))
    p.add(G.empty('MARK_sit_2', (0.4, -0.05, 0.48), 0))
    return p


@prop('stool', 'village', desc='round three-legged stool')
def stool():
    p = new('stool')
    m = p.main
    m.cyl('wood', 0.2, 0.2, 0.06, (0, 0, 0.47), segs=10, bevel=0.02)
    for k in range(3):
        a = k / 3 * 2 * math.pi
        m.cyl('wood_dark', 0.03, 0.03, 0.48, (math.cos(a) * 0.12, math.sin(a) * 0.12, 0.23),
              rot=(math.sin(a) * 0.15, -math.cos(a) * 0.15, 0), segs=6, bevel=0.008)
    p.add(G.empty('MARK_sit', (0, 0, 0.5), 0))
    return p


@prop('tavern_table', 'village', desc='outdoor tavern table with cloth and candle')
def tavern_table():
    p = new('tavern_table')
    m = p.main
    m.box('wood_planks', (1.3, 0.8, 0.07), (0, 0, 0.76), bevel=0.02)
    for sx in (-0.55, 0.55):
        for sy in (-0.3, 0.3):
            m.box('wood_dark', (0.08, 0.08, 0.73), (sx, sy, 0.37), bevel=0.015)
    m.box('cloth_red', (0.9, 0.82, 0.012), (0.1, 0, 0.8), rot=(0, 0, 0.1), bevel=0.004)
    m.box('cloth_red', (0.9, 0.012, 0.15), (0.1, -0.42, 0.73), rot=(0, 0, 0.0), bevel=0.004)
    wick = candle_geo(m, (-0.3, 0.1, 0.8), 0.03, 0.1)
    add_flame(p, 'candle', wick, energy=6)
    m.cyl('ceramic', 0.04, 0.035, 0.1, (0.3, -0.1, 0.85), segs=8, bevel=0.01)
    p.collision.append(((1.3, 0.8, 0.8), (0, 0, 0.4)))
    return p


@prop('fence_wood', 'village', desc='1 m fence segment along X: post at -X end + two rails')
def fence_wood():
    p = new('fence_wood')
    m = p.main
    m.box('wood_weathered', (0.16, 0.16, 1.05), (-0.5, 0, 0.52), bevel=0.03, jitter=0.01)
    m.box('wood_weathered', (0.18, 0.18, 0.06), (-0.5, 0, 1.06), bevel=0.02)
    for z in (0.4, 0.8):
        m.box('wood_weathered', (1.0, 0.07, 0.12), (0.0, -0.06, z), rot=(0, 0.02, 0), bevel=0.02, jitter=0.008)
        m.sphere('iron', 0.015, (-0.5, -0.1, z), segs=5, rings=3)
    p.collision.append(((1.0, 0.2, 1.0), (0, 0, 0.5)))
    return p


@prop('fence_post', 'village', desc='single fence post (closes a fence run)')
def fence_post():
    p = new('fence_post')
    m = p.main
    m.box('wood_weathered', (0.16, 0.16, 1.05), (0, 0, 0.52), bevel=0.03, jitter=0.01)
    m.box('wood_weathered', (0.18, 0.18, 0.06), (0, 0, 1.06), bevel=0.02)
    p.collision.append(((0.18, 0.18, 1.05), (0, 0, 0.52)))
    return p


@prop('lantern_post', 'village', desc='wooden lamp post with a hanging lantern')
def lantern_post():
    p = new('lantern_post')
    m = p.main
    m.box('cobble', (0.36, 0.36, 0.2), (0, 0, 0.1), bevel=0.04, jitter=0.01)
    m.box('wood_dark', (0.14, 0.14, 2.3), (0, 0, 1.25), bevel=0.03)
    m.box('wood_dark', (0.6, 0.1, 0.1), (0.25, 0, 2.3), bevel=0.02)
    m.box('wood_dark', (0.08, 0.08, 0.4), (0.12, 0, 2.12), rot=(0, -0.75, 0), bevel=0.015)
    m.tube('iron', [(0.48, 0, 2.25), (0.48, 0, 2.1)], 0.01, 4)
    lantern_geo(p, m, 'lantern', (0.48, 0, 1.68), scale=1.0)
    p.collision.append(((0.3, 0.3, 2.3), (0, 0, 1.15)))
    return p


@prop('lantern_wall', 'village', desc='wall lantern on an iron bracket, mounted at 2 m')
def lantern_wall():
    p = new('lantern_wall')
    m = p.main
    m.box('iron', (0.12, 0.04, 0.3), (0, -0.02, 2.15), bevel=0.01)
    m.tube('iron', [(0, -0.03, 2.25), (0, -0.2, 2.3), (0, -0.3, 2.27), (0, -0.32, 2.2)], 0.015, 5)
    lantern_geo(p, m, 'lantern', (0, -0.32, 1.75), scale=0.9)
    return p


@prop('lantern', 'village', desc='standalone square lantern (ground, tables, hand-held later)')
def lantern():
    p = new('lantern')
    lantern_geo(p, p.main, 'lantern', (0, 0, 0), scale=1.0)
    return p


@prop('well_roof', 'village', desc='well roof, crank and bucket; sits on the 3x3 voxel ring (top at 1 m)')
def well_roof():
    p = new('well_roof')
    m = p.main
    for sx in (-1.15, 1.15):
        m.box('wood_dark', (0.16, 0.16, 1.75), (sx, 0, 1.0 + 0.87), bevel=0.03)
    m.box('wood_dark', (2.7, 0.14, 0.14), (0, 0, 2.7), bevel=0.03)
    for side in (-1, 1):
        m.box('slate', (2.9, 1.0, 0.1), (0, side * 0.4, 2.95), rot=(side * 0.6, 0, 0), bevel=0.03, jitter=0.01)
    m.box('wood_dark', (2.9, 0.16, 0.12), (0, 0, 3.25), bevel=0.03)
    for sx in (-1.3, 1.3):
        m.ext('wood_dark', [(-0.75, 0), (0.75, 0), (0, 0.5)], 0.06, (sx, 0, 2.75), rot=(0, 0, math.pi / 2), bevel=0.01)
    crank = p.add(G.MeshNode('INT_crank', pivot=(0, 0, 2.2)))
    crank.cyl('wood', 0.09, 0.09, 2.2, (0, 0, 2.2), rot=(0, math.pi / 2, 0), segs=10, bevel=0.01)
    crank.cyl('rope', 0.1, 0.1, 0.4, (0, 0, 2.2), rot=(0, math.pi / 2, 0), segs=10, bevel=0.01)
    crank.box('iron', (0.04, 0.04, 0.3), (1.25, 0, 2.08), bevel=0.005)
    crank.cyl('wood', 0.03, 0.03, 0.2, (1.32, 0, 1.94), rot=(0, math.pi / 2, 0), segs=6, bevel=0.005)
    m.tube('rope', [(0, -0.1, 2.15), (0, -0.1, 1.6)], 0.012, 4)
    m.lathe('wood_planks', [(0.0, 0.0), (0.13, 0.0), (0.16, 0.22), (0.0, 0.22)], (0, -0.1, 1.38), segs=10)
    m.cyl('iron', 0.165, 0.165, 0.025, (0, -0.1, 1.55), segs=10, bevel=0.004, cap=False)
    m.tube('iron', [(-0.15, -0.1, 1.58), (0, -0.1, 1.68), (0.15, -0.1, 1.58)], 0.008, 4)
    lantern_geo(p, m, 'lantern', (1.15, -0.25, 1.75), scale=0.8)
    m.box('iron', (0.04, 0.2, 0.04), (1.15, -0.15, 2.1), bevel=0.005)
    p.collision.append(((0.2, 0.2, 1.8), (-1.15, 0, 1.9)))
    p.collision.append(((0.2, 0.2, 1.8), (1.15, 0, 1.9)))
    return p


@prop('notice_board', 'village', desc='village notice board covered in charms (dreamcatcher, bells, lavender, crystals)')
def notice_board():
    p = new('notice_board')
    m = p.main
    for sx in (-0.85, 0.85):
        m.box('wood_dark', (0.16, 0.16, 2.2), (sx, 0, 1.1), bevel=0.03)
    m.box('wood_dark', (2.1, 0.22, 0.16), (0, 0, 2.25), bevel=0.04)
    m.box('wood_dark', (1.9, 0.18, 0.1), (0, 0, 0.5), bevel=0.03)
    plank_panel(m, 'wood_planks', -0.78, 0.78, 0.55, 2.15, 0.02, thick=0.06, n=6)
    # dreamcatcher
    ring = [(-0.05 + math.cos(a) * 0.22, -0.06, 1.55 + math.sin(a) * 0.22) for a in [k / 20 * 2 * math.pi for k in range(21)]]
    m.tube('brass', ring, 0.015, 5)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        m.tube('rope', [(-0.05, -0.06, 1.55), (-0.05 + math.cos(a) * 0.21, -0.06, 1.55 + math.sin(a) * 0.21)], 0.004, 3)
    for k, x in enumerate((-0.2, -0.05, 0.1)):
        m.tube('rope', [(x, -0.06, 1.33), (x, -0.06, 1.15)], 0.005, 3)
        m.ext('cloth_purple', [(-0.03, 0), (0.03, 0), (0, -0.14)], 0.01, (x, -0.06, 1.15), bevel=0.003)
    # paper notes + charms
    for (x, z, w, h, r) in ((-0.55, 1.75, 0.3, 0.38, 0.08), (0.5, 1.2, 0.26, 0.32, -0.1), (-0.5, 0.9, 0.22, 0.24, 0.05)):
        m.box('paper', (w, 0.01, h), (x, -0.035, z), rot=(0, r, 0), bevel=0.003)
    for x in (0.35, 0.55):
        m.tube('rope', [(x, -0.06, 2.1), (x, -0.06, 1.85)], 0.005, 3)
        m.lathe('brass', [(0.0, 0.1), (0.03, 0.09), (0.05, 0.02), (0.06, 0.0), (0.0, 0.0)], (x, -0.07, 1.75), segs=8)
    # lavender bundle
    for k in range(5):
        m.cyl('vine', 0.006, 0.006, 0.35, (0.55 + (k - 2) * 0.02, -0.07, 1.55), rot=(0, (k - 2) * 0.08, 0), segs=4, bevel=0)
        m.cyl('wisteria', 0.022, 0.015, 0.14, (0.55 + (k - 2) * 0.035, -0.08, 1.38), rot=(0, (k - 2) * 0.08, 0), segs=6,
              bevel=0.005)
    # crystal pendants + horseshoe
    for x in (-0.3, 0.2):
        m.cyl('FLAME_crystal', 0.035, 0.0, 0.12, (x, -0.07, 1.0), segs=6, bevel=0)
        m.cyl('FLAME_crystal', 0.0, 0.035, 0.05, (x, -0.07, 1.085), segs=6, bevel=0)
    shoe = [(0.0 + math.cos(a) * 0.1, -0.06, 0.85 + math.sin(a) * 0.1) for a in [math.radians(-30 + k * 24) for k in range(11)]]
    m.tube('iron', shoe, 0.018, 5)
    # candles + small barrels at the foot
    for i, x in enumerate((-0.35, -0.2)):
        wick = candle_geo(m, (x, -0.35, 0.0), 0.04, 0.16 - i * 0.05)
        add_flame(p, f'candle_{i + 1}', wick, energy=6)
    p.collision.append(((1.9, 0.25, 2.3), (0, 0, 1.15)))
    return p


@prop('tavern_sign', 'village', desc='hanging tavern sign with a mug; swings on ANIM_sign, mounted at 2.6 m')
def tavern_sign():
    p = new('tavern_sign')
    m = p.main
    m.box('iron', (0.1, 0.04, 0.25), (0, -0.02, 2.8), bevel=0.01)
    m.box('wood_dark', (0.06, 0.95, 0.08), (0, -0.48, 2.85), bevel=0.015)
    m.tube('iron', [(0, -0.05, 2.65), (0, -0.5, 2.82)], 0.015, 4)
    s = p.add(G.MeshNode('ANIM_sign', pivot=(0, -0.6, 2.8)))
    for y in (-0.38, -0.82):
        s.tube('iron', [(0, y, 2.81), (0, y, 2.6)], 0.008, 4)
    s.box('wood_planks', (0.07, 0.6, 0.5), (0, -0.6, 2.33), bevel=0.02)
    s.box('wood_dark', (0.09, 0.64, 0.06), (0, -0.6, 2.6), bevel=0.01)
    for sx in (-0.045, 0.045):
        s.lathe('brass', [(0.0, 0), (0.08, 0), (0.09, 0.18), (0.0, 0.18)], (sx * 1.0, -0.6, 2.22), segs=8,
                rot=(0, math.pi / 2 * (1 if sx > 0 else -1), 0))
        s.box('canvas', (0.03, 0.17, 0.05), (sx * 1.2, -0.6, 2.42), bevel=0.01)
    return p


@prop('tavern_awning', 'village', desc='cloth awning on two posts in front of the tavern (wall-mounted at 2.4 m)')
def tavern_awning():
    p = new('tavern_awning')
    m = p.main
    m.box('cloth_red', (2.6, 1.6, 0.04), (0, -0.78, 2.15), rot=(-0.3, 0, 0), bevel=0.01, jitter=0.01)
    for k in range(9):
        x = -1.15 + k * 0.29
        m.ext('cloth_red', [(-0.13, 0), (0.13, 0), (0.0, -0.12)], 0.02, (x, -1.53, 1.92), bevel=0.003)
    for sx in (-1.25, 1.25):
        m.box('wood_dark', (0.12, 0.12, 1.95), (sx, -1.5, 0.97), bevel=0.02)
    m.box('wood_dark', (2.7, 0.1, 0.1), (0, -1.5, 1.92), bevel=0.02)
    p.collision.append(((0.12, 0.12, 1.95), (-1.25, -1.5, 0.97)))
    p.collision.append(((0.12, 0.12, 1.95), (1.25, -1.5, 0.97)))
    return p


@prop('windmill_sails', 'village', desc='four canvas sails on lattice arms; ANIM_sails spins about the axle (Godot Z)')
def windmill_sails():
    """Mounted on the mill's upper front wall plane; hub 7.5 m above the prop pivot (8.5 m on windmill_base)."""
    p = new('windmill_sails')
    hub_z = 7.5
    m = p.main
    m.cyl('wood_dark', 0.22, 0.22, 0.9, (0, -0.35, hub_z), rot=(math.pi / 2, 0, 0), segs=10, bevel=0.03)
    s = p.add(G.MeshNode('ANIM_sails', pivot=(0, -0.85, hub_z)))
    s.cyl('wood_dark', 0.32, 0.32, 0.2, (0, -0.85, hub_z), rot=(math.pi / 2, 0, 0), segs=12, bevel=0.03)
    s.cyl('iron', 0.12, 0.12, 0.24, (0, -0.9, hub_z), rot=(math.pi / 2, 0, 0), segs=8, bevel=0.02)
    L = 5.8
    for k in range(4):
        a = k * math.pi / 2 + math.radians(20)
        ca, sa = math.cos(a), math.sin(a)

        def P(r, w, y=-0.95):
            # r along the arm, w across it (in the sail plane XZ)
            return (ca * r - sa * w, y, hub_z + sa * r + ca * w)
        s.box('wood_dark', (L, 0.12, 0.14), P(L / 2, 0), rot=(0, -a, 0), bevel=0.03)
        # lattice
        for i in range(9):
            r = 1.0 + i * 0.6
            s.box('wood', (0.06, 0.06, 0.95), P(r, 0.45, -0.97), rot=(0, -a, 0), bevel=0.01)
        for w in (0.05, 0.92):
            s.box('wood', (L - 1.0, 0.06, 0.06), P(0.95 + (L - 1.0) / 2, w, -0.97), rot=(0, -a, 0), bevel=0.01)
        # canvas
        s.box('canvas', (L - 1.1, 0.02, 0.84), P(1.0 + (L - 1.1) / 2, 0.48, -1.0), rot=(0, -a, 0), bevel=0.005)
        for i in range(4):
            r = 1.6 + i * 1.15
            s.box('rope', (0.05, 0.03, 0.88), P(r, 0.48, -1.02), rot=(0, -a, 0), bevel=0.005)
    return p


@prop('millstone', 'village', desc='millstone pair on a timber frame with a hopper')
def millstone():
    p = new('millstone')
    m = p.main
    for sx in (-0.7, 0.7):
        for sy in (-0.6, 0.6):
            m.box('wood_dark', (0.14, 0.14, 0.55), (sx, sy, 0.27), bevel=0.02)
    m.box('wood_planks', (1.6, 1.4, 0.1), (0, 0, 0.6), bevel=0.02)
    m.cyl('stone', 0.6, 0.6, 0.2, (0, 0, 0.75), segs=16, bevel=0.03, jitter=0.01)
    m.cyl('stone', 0.58, 0.58, 0.2, (0, 0, 0.96), segs=16, bevel=0.03, jitter=0.01)
    m.cyl('wood_dark', 0.08, 0.08, 0.3, (0, 0, 1.15), segs=8, bevel=0.01)
    # hopper
    m.lathe('wood_planks', [(0.08, 0.0), (0.45, 0.45), (0.45, 0.55), (0.0, 0.55)], (0, 0, 1.25), segs=4,
            rot=(0, 0, math.pi / 4))
    for sx in (-0.4, 0.4):
        m.box('wood_dark', (0.1, 0.1, 1.2), (sx, 0.55, 1.2), bevel=0.02)
    m.box('wood_dark', (1.0, 0.1, 0.1), (0, 0.55, 1.75), bevel=0.02)
    p.collision.append(((1.6, 1.4, 1.2), (0, 0, 0.6)))
    return p


@prop('ladder', 'village', desc='steep wooden ladder, 3.2 m (mill loft)')
def ladder():
    p = new('ladder')
    m = p.main
    H = 3.3
    for sx in (-0.25, 0.25):
        m.box('wood', (0.08, 0.1, H / math.cos(0.25)), (sx, 0.42, H / 2), rot=(-0.25, 0, 0), bevel=0.02)
    for i in range(10):
        z = 0.3 + i * 0.32
        y = math.tan(0.25) * (z - H / 2) + 0.42
        m.cyl('wood_dark', 0.03, 0.03, 0.5, (0, y, z), rot=(0, math.pi / 2, 0), segs=6, bevel=0.005)
    p.add(G.empty('MARK_climb_bottom', (0, -0.2, 0), 180))
    p.add(G.empty('MARK_climb_top', (0, 1.2, H), 180))
    return p


@prop('tree_oak', 'village', desc='round oak tree with painted canopy (decorative)')
def tree_oak():
    p = new('tree_oak')
    m = p.main
    m.tube('bark', [(0, 0, -0.2), (0.05, 0.02, 1.0), (-0.05, 0.0, 2.0), (0.1, -0.05, 2.8)], 0.32, 8, taper=0.45)
    for a in (0.3, 2.2, 4.1):
        m.tube('bark', [(math.cos(a) * 0.1, math.sin(a) * 0.1, 0.3), (math.cos(a) * 0.55, math.sin(a) * 0.55, -0.05)],
               0.12, 6, taper=0.5)
    m.tube('bark', [(0, 0, 1.9), (0.7, 0.2, 2.6), (1.1, 0.3, 3.0)], 0.12, 6, taper=0.5)
    m.tube('bark', [(0, 0, 2.1), (-0.8, -0.1, 2.8)], 0.11, 6, taper=0.5)
    G.seed(42)
    for (x, y, z, r) in ((0, 0, 3.6, 1.4), (1.1, 0.3, 3.2, 1.0), (-1.1, -0.1, 3.3, 1.05), (0.3, -0.9, 3.0, 0.9),
                         (-0.3, 0.9, 3.1, 0.95), (0.2, 0.1, 4.4, 0.9)):
        m.sphere('leaf', r, (x, y, z), scale=(1, 1, 0.85), segs=10, rings=7, jitter=r * 0.08)
    p.collision.append(((0.6, 0.6, 2.4), (0, 0, 1.2)))
    return p


@prop('wisteria', 'village', desc='hanging wisteria cluster (eaves decor), wall-mounted top at 3.3 m')
def wisteria():
    p = new('wisteria')
    m = p.main
    G.seed(5)
    for k in range(5):
        x = -0.5 + k * 0.25
        L = 0.5 + 0.35 * ((k * 7) % 3) / 2
        m.lathe('wisteria', [(0.0, 0.0), (0.06, 0.08), (0.1, L * 0.6), (0.08, L), (0.0, L + 0.02)],
                (x, -0.18, 3.25 - L), segs=8, jitter=0.012)
        m.sphere('leaf', 0.12, (x, -0.12, 3.3), scale=(1.3, 0.6, 0.6), segs=6, rings=4, jitter=0.02)
    m.tube('vine', [(-0.7, -0.08, 3.35), (0.0, -0.1, 3.3), (0.7, -0.08, 3.36)], 0.025, 5)
    return p


@prop('broom', 'village', desc='broom leaning on a wall')
def broom():
    p = new('broom')
    m = p.main
    t = 0.18  # lean back toward the wall (+Y)
    ax = Vector((0, math.sin(t), math.cos(t)))
    m.cyl('wood', 0.022, 0.022, 1.3, ax * (0.3 + 0.65), rot=(-t, 0, 0), segs=6, bevel=0.005)
    m.lathe('straw', [(0.0, 0.0), (0.14, 0.0), (0.12, 0.12), (0.03, 0.35), (0.0, 0.35)], (0, 0, 0), segs=8, rot=(-t, 0, 0))
    m.cyl('rope', 0.035, 0.035, 0.05, ax * 0.33, rot=(-t, 0, 0), segs=6, bevel=0.005)
    return p


@prop('bucket', 'village', desc='wooden bucket')
def bucket():
    p = new('bucket')
    m = p.main
    m.lathe('wood_planks', [(0.0, 0.0), (0.15, 0.0), (0.18, 0.3), (0.0, 0.3)], (0, 0, 0), segs=10)
    m.cyl('water', 0.165, 0.165, 0.01, (0, 0, 0.27), segs=10, bevel=0)
    for z in (0.06, 0.24):
        r = 0.15 + 0.03 * z / 0.3 + 0.01
        m.cyl('iron', r, r, 0.025, (0, 0, z), segs=10, bevel=0.003, cap=False)
    m.tube('iron', [(-0.18, 0, 0.28), (0, 0, 0.45), (0.18, 0, 0.28)], 0.008, 4)
    return p


@prop('mug', 'village', desc='tankard on a table')
def mug():
    p = new('mug')
    m = p.main
    m.cyl('wood_planks', 0.05, 0.05, 0.12, (0, 0, 0.06), segs=8, bevel=0.01)
    m.cyl('canvas', 0.045, 0.045, 0.02, (0, 0, 0.125), segs=8, bevel=0.008)
    m.tube('wood_dark', [(0.05, 0, 0.1), (0.09, 0, 0.09), (0.09, 0, 0.03), (0.05, 0, 0.03)], 0.012, 4)
    return p


@prop('pumpkin', 'village', desc='large ribbed pumpkin with stem')
def pumpkin():
    return _pumpkin('pumpkin', 0.32)


@prop('pumpkin_small', 'village', desc='small pumpkin')
def pumpkin_small():
    return _pumpkin('pumpkin_small', 0.2)


def _pumpkin(name, r):
    p = new(name)
    m = p.main
    from props_common import G as GG  # noqa
    import bmesh
    bm = G.bm_sphere(r, 16, 10)
    for v in bm.verts:
        a = math.atan2(v.co.y, v.co.x)
        k = 1 + 0.08 * math.cos(8 * a)
        v.co.x *= k * 1.1
        v.co.y *= k * 1.1
        v.co.z *= 0.78
    m.put(bm, 'pumpkin', (0, 0, r * 0.75))
    m.tube('wood_dark', [(0, 0, r * 1.4), (0.02, 0, r * 1.6), (0.06, 0.0, r * 1.7)], r * 0.12, 6, taper=0.7)
    m.tube('vine', [(0.0, 0.0, r * 1.45), (r * 0.6, -r * 0.4, r * 1.2), (r * 1.0, -r * 0.8, r * 0.6),
                    (r * 1.3, -r * 0.7, r * 0.2)], 0.012, 4)
    m.sphere('leaf', r * 0.45, (-r * 0.9, r * 0.6, r * 0.15), scale=(1, 0.8, 0.3), segs=8, rings=4, jitter=0.01)
    p.collision.append(((r * 2.2, r * 2.2, r * 1.5), (0, 0, r * 0.75)))
    return p


@prop('pumpkin_vine', 'village', desc='leafy pumpkin vine patch, 1x1 m (ground cover)')
def pumpkin_vine():
    p = new('pumpkin_vine')
    m = p.main
    G.seed(9)
    for k in range(9):
        a = k * 2.4
        r = 0.12 + 0.3 * ((k * 0.37) % 1.0)
        x, y = math.cos(a) * r, math.sin(a) * r
        m.sphere('leaf', 0.16, (x, y, 0.1 + 0.04 * (k % 2)), scale=(1, 0.9, 0.35), rot=(0.3 * math.sin(a), 0.3, a),
                 segs=8, rings=4, jitter=0.02)
    m.tube('vine', [(-0.45, -0.1, 0.03), (0, 0.05, 0.08), (0.45, 0.0, 0.03)], 0.015, 4)
    return p
