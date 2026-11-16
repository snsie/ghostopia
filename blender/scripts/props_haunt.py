"""Hauntable props (concept/characters/hauntable_props.png): each has INT_ pivots and HAUNT_ shells."""
import math

from mathutils import Vector

import lib_geo as G
from props_common import add_flame, arch_outline, candle_geo, new, plank_panel, prop


@prop('door_cottage', 'hauntable', haunt=True, desc='arched plank door for a 1x2 opening, hinge left')
def door_cottage():
    p = new('door_cottage', haunt=True)
    m = p.main
    # arch infill (static) fills the square top corners of the 1x2 voxel gap around the arched leaf
    for sx in (-1, 1):
        pts = [(sx * 0.5, 2.0), (sx * 0.5, 1.5)]
        for i in range(0, 11):
            t = math.pi / 2 - i / 10 * math.pi / 2
            pts.append((sx * math.sin(t) * 0.47, 1.5 + math.cos(t) * 0.47 + 0.03 * (1 - math.sin(t))))
        pts.append((0.0, 2.0))
        m.ext('wood_dark', pts, 0.9, (0, 0, 0), bevel=0.01)
    m.box('stone', (1.0, 0.95, 0.06), (0, 0, 0.03), bevel=0.02)  # threshold step
    # leaf (hinged on the left seen from outside = -X)
    leaf = p.add(G.MeshNode('INT_door', pivot=(-0.47, -0.05, 0)))
    outline = arch_outline(0.92, 1.96, 12)
    leaf.ext('wood', [(x, z + 0.02) for x, z in outline], 0.08, (0, -0.05, 0), bevel=0.012)
    # vertical plank grooves (thin dark strips on both faces)
    for x in (-0.23, 0.0, 0.23):
        top = 1.5 + math.sqrt(max(0.0, 0.46 ** 2 - x * x)) - 0.03
        for y in (-0.092, -0.008):
            leaf.box('wood_dark', (0.018, 0.006, top - 0.06), (x, y, (top + 0.06) / 2), bevel=0)
    for z in (0.35, 1.45):
        leaf.box('iron', (0.86, 0.1, 0.07), (-0.02, -0.05, z), bevel=0.01)
        for x in (-0.38, -0.1, 0.18):
            leaf.sphere('iron', 0.018, (x, -0.102, z), segs=6, rings=4)
    ring = [(0.25 + math.cos(a) * 0.07, -0.11, 1.0 + math.sin(a) * 0.07) for a in
            [k / 12 * 2 * math.pi for k in range(13)]]
    leaf.tube('iron', ring, 0.013, 6)
    leaf.cyl('iron', 0.03, 0.03, 0.03, (0.25, -0.1, 1.07), rot=(math.pi / 2, 0, 0), segs=8)
    leaf.cols.append(((0.92, 0.08, 1.96), (0, -0.05, 0.99)))
    p.add(G.empty('MARK_door_inside', (0, 0.8, 0), 180))
    p.add(G.empty('MARK_door_outside', (0, -0.8, 0), 0))
    p.extras['hinge'] = 'left'
    return p


@prop('door_interior', 'hauntable', haunt=True, desc='plain plank bedroom door, 1x2 opening')
def door_interior():
    p = new('door_interior', haunt=True)
    leaf = p.add(G.MeshNode('INT_door', pivot=(-0.47, 0, 0)))
    plank_panel(leaf, 'wood', -0.46, 0.46, 0.02, 1.97, 0.0, thick=0.06, n=4)
    for z in (0.3, 1.0, 1.7):
        leaf.box('wood_dark', (0.88, 0.08, 0.1), (0, 0, z), bevel=0.012)
    leaf.box('wood_dark', (0.1, 0.08, 1.2), (0, 0.0, 1.0), rot=(0, 0.62, 0), bevel=0.01)
    leaf.sphere('brass', 0.035, (0.35, -0.07, 1.0), segs=8, rings=5)
    leaf.sphere('brass', 0.035, (0.35, 0.07, 1.0), segs=8, rings=5)
    leaf.cols.append(((0.92, 0.07, 1.95), (0, 0, 0.995)))
    return p


@prop('floorboard', 'hauntable', haunt=True, desc='creaky floorboard patch 1x1 m, loose centre board')
def floorboard():
    p = new('floorboard', haunt=True)
    m = p.main
    for i, x in enumerate((-0.4, -0.2, 0.2, 0.4)):
        m.box('wood_weathered', (0.19, 1.0, 0.05), (x, 0, 0.025), bevel=0.012, jitter=0.004)
        m.sphere('iron', 0.012, (x, -0.42, 0.052), segs=5, rings=3)
        m.sphere('iron', 0.012, (x, 0.42, 0.052), segs=5, rings=3)
    m.box('vine', (0.15, 0.2, 0.012), (-0.4, 0.3, 0.056), bevel=0.004)
    loose = p.add(G.MeshNode('INT_floorboard', pivot=(0, 0, 0.03)))
    loose.box('wood_weathered', (0.19, 1.0, 0.05), (0, 0, 0.032), rot=(0.02, 0, 0), bevel=0.012, jitter=0.004)
    loose.sphere('iron', 0.012, (0, -0.42, 0.06), segs=5, rings=3)
    p.add(G.empty('MARK_creak', (0, 0, 0.06)))
    return p


def _holder(m, base=(0, 0, 0)):
    b = Vector(base)
    m.lathe('brass', [(0.0, 0), (0.1, 0.0), (0.11, 0.02), (0.1, 0.035), (0.04, 0.03), (0.045, 0.06),
                      (0.0, 0.06)], b, segs=14)
    ring = [b + Vector((0.11 + 0.035 + math.cos(a) * 0.035, 0, 0.03 + math.sin(a) * 0.035))
            for a in [k / 12 * 2 * math.pi for k in range(13)]]
    m.tube('brass', ring, 0.008, 6)
    return b + Vector((0, 0, 0.05))


@prop('candle', 'hauntable', haunt=True, desc='candle in a brass dish; snuffable')
def candle():
    p = new('candle', haunt=True)
    top = _holder(p.main)
    wick = candle_geo(p.main, top, 0.035, 0.15)
    add_flame(p, 'candle', wick, energy=10)
    return p


@prop('candle_cluster', 'hauntable', haunt=True, desc='three melted candles in a wax pool (graves, mantels)')
def candle_cluster():
    p = new('candle_cluster', haunt=True)
    m = p.main
    m.cyl('wax', 0.13, 0.15, 0.025, (0, 0, 0.012), segs=12, bevel=0.01, jitter=0.006)
    for i, (x, y, h, r) in enumerate(((-0.06, 0.02, 0.22, 0.04), (0.06, 0.03, 0.15, 0.035), (0.0, -0.06, 0.1, 0.03))):
        wick = candle_geo(m, (x, y, 0.02), r, h)
        add_flame(p, f'candle_{i + 1}', wick, energy=7)
    return p


@prop('oil_lamp', 'hauntable', haunt=True, desc='brass oil lamp with glass chimney')
def oil_lamp():
    p = new('oil_lamp', haunt=True)
    m = p.main
    m.lathe('brass', [(0.0, 0), (0.1, 0), (0.11, 0.025), (0.08, 0.05), (0.09, 0.09), (0.11, 0.12),
                      (0.08, 0.15), (0.05, 0.16), (0.0, 0.16)], (0, 0, 0), segs=14)
    m.lathe('GLOW_lamp_glass', [(0.045, 0.0), (0.075, 0.07), (0.08, 0.12), (0.05, 0.2), (0.045, 0.24)],
            (0, 0, 0.16), segs=14)
    for k in range(4):
        a = k / 4 * 2 * math.pi + math.pi / 4
        m.box('brass', (0.016, 0.016, 0.25), (math.cos(a) * 0.088, math.sin(a) * 0.088, 0.285), bevel=0.004)
    m.lathe('brass', [(0.0, 0), (0.09, 0), (0.1, 0.02), (0.06, 0.05), (0.03, 0.06), (0.0, 0.06)],
            (0, 0, 0.4), segs=14)
    handle = [(math.cos(a) * 0.09, 0, 0.47 + math.sin(a) * 0.07) for a in
              [k / 10 * math.pi for k in range(11)]]
    m.tube('brass', handle, 0.012, 6)
    m.cyl('brass', 0.012, 0.012, 0.06, (0.12, 0, 0.12), rot=(0, math.pi / 2, 0), segs=6)
    add_flame(p, 'lamp', (0, 0, 0.2), h=0.07, r=0.02, energy=18)
    return p


@prop('rocking_chair', 'hauntable', haunt=True, desc='rocking chair with plaid blanket; rocks about the runner contact')
def rocking_chair():
    p = new('rocking_chair', haunt=True)
    c = p.add(G.MeshNode('INT_rocker', pivot=(0, 0, 0)))
    # runners: arcs in YZ
    for sx in (-0.26, 0.26):
        pts = []
        R = 1.6
        for i in range(13):
            a = math.radians(-22 + 44 * i / 12)
            pts.append((math.sin(a) * R, R - math.cos(a) * R + 0.03))
        top = [(y, z + 0.06) for y, z in reversed(pts)]
        outline = pts + top
        c.ext('wood_dark', outline, 0.06, (sx, 0, 0), rot=(0, 0, math.pi / 2), bevel=0.012)
    for sx in (-0.26, 0.26):
        for sy in (-0.22, 0.22):
            c.box('wood', (0.06, 0.06, 0.42), (sx, sy, 0.3), bevel=0.012)
    c.box('wood', (0.6, 0.55, 0.07), (0, 0, 0.5), bevel=0.02)
    c.box('cloth_plaid', (0.5, 0.45, 0.06), (0, -0.02, 0.56), bevel=0.025)
    # back
    for sx in (-0.26, 0.26):
        c.box('wood', (0.07, 0.07, 0.75), (sx, 0.24, 0.9), rot=(-0.12, 0, 0), bevel=0.015)
    c.box('wood', (0.66, 0.09, 0.12), (0, 0.29, 1.28), rot=(-0.12, 0, 0), bevel=0.03)
    for sx in (-0.13, 0.0, 0.13):
        c.box('wood', (0.05, 0.04, 0.6), (sx, 0.26, 0.95), rot=(-0.12, 0, 0), bevel=0.01)
    # arms
    for sx in (-0.31, 0.31):
        c.box('wood', (0.08, 0.5, 0.06), (sx, -0.02, 0.78), bevel=0.02)
        c.box('wood', (0.05, 0.05, 0.25), (sx, -0.22, 0.66), bevel=0.01)
    # blanket draped over the back and left arm
    c.box('cloth_plaid', (0.5, 0.06, 0.55), (-0.05, 0.31, 0.95), rot=(-0.12, 0, 0.06), bevel=0.02, jitter=0.01)
    c.box('cloth_plaid', (0.12, 0.32, 0.5), (-0.36, 0.02, 0.6), rot=(0, 0.1, 0), bevel=0.03, jitter=0.012)
    c.cols.append(((0.7, 0.7, 1.3), (0, 0, 0.65)))
    p.add(G.empty('MARK_sit', (0, -0.05, 0.55), 0))
    return p


@prop('wardrobe', 'hauntable', haunt=True, desc='tall wardrobe with two hinged doors; ghost hide spot')
def wardrobe():
    p = new('wardrobe', haunt=True)
    m = p.main
    W, D, H = 1.2, 0.6, 2.05
    m.box('wood_dark', (W, D, 0.22), (0, 0, 0.16), bevel=0.03)  # plinth
    for sx in (-1, 1):
        m.box('wood_dark', (0.12, D + 0.04, 0.1), (sx * (W / 2 - 0.08), 0, 0.05), bevel=0.02)
    m.box('wood', (W - 0.02, D - 0.04, H - 0.4), (0, 0.0, 0.27 + (H - 0.4) / 2), bevel=0.02)
    m.box('wood_dark', (W + 0.1, D + 0.08, 0.1), (0, 0, H - 0.08), bevel=0.03)
    crown = arch_outline(W * 0.8, 0.28, 12, spring=0.0)
    m.ext('wood_dark', [(x, z * 1.0 + H - 0.04) for x, z in crown], 0.12, (0, -0.2, 0), bevel=0.02)
    m.sphere('wood', 0.07, (0, -0.27, H + 0.08), scale=(1.6, 0.5, 1), segs=8, rings=5)
    # drawer in the plinth
    m.box('wood', (W - 0.2, 0.04, 0.14), (0, -D / 2 - 0.01, 0.16), bevel=0.012)
    for sx in (-0.25, 0.25):
        m.cyl('brass', 0.03, 0.03, 0.03, (sx, -D / 2 - 0.04, 0.16), rot=(math.pi / 2, 0, 0), segs=8)
    # vines on the left
    m.tube('vine', [(-W / 2 - 0.02, -0.25, 0.3), (-W / 2 - 0.03, -0.3, 0.9), (-W / 2, -0.32, 1.5),
                    (-W / 2 + 0.1, -0.33, 2.0)], 0.02, 5)
    for z in (0.6, 1.0, 1.4, 1.8):
        m.sphere('vine', 0.06, (-W / 2 - 0.02, -0.33, z), scale=(1, 0.4, 0.7), segs=6, rings=4)
    hy = -D / 2 + 0.0
    for side, sx in (('L', -1), ('R', 1)):
        hinge = (sx * (W / 2 - 0.05), hy - 0.02, 0)
        d = p.add(G.MeshNode(f'INT_wardrobe_door_{side}', pivot=hinge))
        cx = sx * (W / 4 - 0.01)
        plank_panel(d, 'wood', cx - W / 4 + 0.04, cx + W / 4 - 0.04, 0.3, H - 0.16, hy - 0.04, thick=0.05, n=3)
        d.box('wood_dark', (W / 2 - 0.06, 0.04, 0.08), (cx, hy - 0.07, 0.45), bevel=0.01)
        d.box('wood_dark', (W / 2 - 0.06, 0.04, 0.08), (cx, hy - 0.07, H - 0.3), bevel=0.01)
        ring = [(-sx * 0.07 + math.cos(a) * 0.045, hy - 0.1, 1.15 + math.sin(a) * 0.045) for a in
                [k / 12 * 2 * math.pi for k in range(13)]]
        d.tube('brass', ring, 0.01, 6)
        d.cyl('brass', 0.022, 0.022, 0.03, (-sx * 0.07, hy - 0.08, 1.2), rot=(math.pi / 2, 0, 0), segs=8)
        d.cols.append(((W / 2 - 0.06, 0.05, H - 0.46), (cx, hy - 0.04, (H + 0.14) / 2)))
    p.collision.append(((W, D - 0.06, H), (0, 0.03, H / 2)))
    p.add(G.empty('MARK_hide', (0, 0.0, 0.3), 0))
    return p


@prop('portrait', 'hauntable', haunt=True, desc='wall portrait of an old villager; eyes are a separate turning mesh')
def portrait():
    p = new('portrait', haunt=True)
    m = p.main
    zc = 1.6
    W, H = 0.7, 0.85
    # ornate frame: 4 bars + corner bosses + top crest
    t = 0.1
    for (sx, sz, cx, cz) in ((W + t, t, 0, zc + H / 2), (W + t, t, 0, zc - H / 2), (t, H, -W / 2, zc), (t, H, W / 2, zc)):
        m.box('brass', (sx, 0.07, sz), (cx, -0.04, cz), bevel=0.025)
    for cx in (-W / 2, W / 2):
        for cz in (zc - H / 2, zc + H / 2):
            m.sphere('brass', 0.07, (cx, -0.08, cz), scale=(1, 0.5, 1), segs=8, rings=5)
    m.ext('brass', [(-0.18, 0), (0.18, 0), (0.1, 0.1), (0.0, 0.16), (-0.1, 0.1)], 0.05, (0, -0.05, zc + H / 2 + 0.03),
          bevel=0.015)
    m.ext('brass', [(-0.14, 0), (0.14, 0), (0.0, -0.1)], 0.05, (0, -0.05, zc - H / 2 - 0.03), bevel=0.015)
    m.box('portrait', (W - 0.02, 0.02, H - 0.02), (0, -0.03, zc), bevel=0, uv='fit')
    # eye whites (static), pupils on INT_portrait_eyes
    ex = 0.075
    ez = zc + (0.5 - 121 / 256) * (H - 0.02)
    for sx in (-1, 1):
        m.sphere('bone', 0.03, (sx * ex, -0.045, ez), scale=(1.2, 0.35, 0.8), segs=8, rings=5)
    eyes = p.add(G.MeshNode('INT_portrait_eyes', pivot=(0, -0.05, ez)))
    for sx in (-1, 1):
        eyes.sphere('eye_dark', 0.016, (sx * ex, -0.055, ez), scale=(1, 0.4, 1), segs=8, rings=4)
    p.add(G.empty('MARK_look', (0, -0.05, ez)))
    return p


@prop('cloth_doll', 'hauntable', haunt=True, desc='sitting rag doll with yarn braids; possessable later')
def cloth_doll():
    p = new('cloth_doll', haunt=True)
    d = p.add(G.MeshNode('INT_doll', pivot=(0, 0, 0)))
    d.lathe('cloth_red', [(0.0, 0.02), (0.13, 0.02), (0.12, 0.08), (0.08, 0.2), (0.0, 0.21)], (0, 0, 0), segs=10,
            jitter=0.004)
    d.lathe('cloth_linen', [(0.0, 0.05), (0.1, 0.05), (0.07, 0.17), (0.0, 0.18)], (0, -0.04, 0), segs=10)
    for sx in (-0.06, 0.06):
        d.cyl('cloth_linen', 0.035, 0.03, 0.16, (sx, -0.1, 0.035), rot=(math.pi / 2, 0, 0), segs=8, bevel=0.01)
        d.sphere('wood_dark', 0.035, (sx, -0.18, 0.04), scale=(1, 1.2, 0.8), segs=8, rings=5)
    for sx in (-1, 1):
        d.cyl('cloth_linen', 0.025, 0.025, 0.13, (sx * 0.12, -0.02, 0.13), rot=(0, sx * 0.5, 0), segs=6, bevel=0.008)
    d.sphere('cloth_linen', 0.09, (0, -0.01, 0.29), scale=(1, 0.95, 0.95), segs=12, rings=8)
    d.sphere('rope', 0.095, (0, 0.03, 0.315), scale=(1.05, 0.8, 0.9), segs=12, rings=8)  # yarn hair
    d.lathe('cloth_red', [(0.11, 0.0), (0.1, 0.03), (0.06, 0.06), (0.0, 0.065)], (0, 0.02, 0.33), segs=12,
            rot=(-0.5, 0, 0))  # small bonnet on the back of the head
    for sx in (-1, 1):
        d.sphere('eye_dark', 0.014, (sx * 0.032, -0.095, 0.3), scale=(1, 0.5, 1), segs=6, rings=4)
        d.sphere('cloth_red', 0.016, (sx * 0.052, -0.088, 0.27), scale=(1, 0.4, 0.7), segs=6, rings=4)
        d.tube('rope', [(sx * 0.085, 0.0, 0.31), (sx * 0.11, 0.0, 0.24), (sx * 0.1, 0.0, 0.16)], 0.02, 6, taper=0.6)
        d.sphere('cloth_red', 0.016, (sx * 0.1, 0.0, 0.17), segs=6, rings=4)
    d.cols.append(((0.26, 0.3, 0.38), (0, -0.04, 0.19)))
    return p


@prop('scarecrow', 'hauntable', haunt=True, desc='field scarecrow on a stone base; Puppet target later')
def scarecrow():
    p = new('scarecrow', haunt=True)
    base = p.main
    for (x, y, s) in ((-0.15, 0.05, 0.3), (0.18, -0.08, 0.26), (0.02, 0.2, 0.22)):
        base.box('cobble', (s, s, s * 0.8), (x, y, s * 0.4), bevel=0.04, jitter=0.01)
    base.cyl('grass', 0.45, 0.4, 0.06, (0, 0, 0.03), segs=10, bevel=0.02, jitter=0.02)
    for k in range(5):
        a = k / 5 * 2 * math.pi
        base.sphere('cloth_purple', 0.04, (math.cos(a) * 0.32, math.sin(a) * 0.32, 0.09), segs=6, rings=4)
    s = p.add(G.MeshNode('INT_scarecrow', pivot=(0, 0, 0.0)))
    s.box('wood_weathered', (0.1, 0.1, 1.9), (0, 0.04, 0.95), bevel=0.02)
    s.box('wood_weathered', (1.5, 0.08, 0.08), (0, 0.04, 1.45), bevel=0.02)
    # coat: torso + sleeves, purple-grey with patches
    s.box('cloth_purple', (0.5, 0.3, 0.6), (0, 0, 1.25), bevel=0.06, jitter=0.015)
    s.lathe('cloth_purple', [(0.3, 0.0), (0.27, 0.15), (0.22, 0.3)], (0, 0, 0.8), segs=8, jitter=0.02)
    for sx in (-1, 1):
        s.box('cloth_purple', (0.45, 0.2, 0.2), (sx * 0.42, 0.0, 1.45), bevel=0.05, jitter=0.012)
        for k in range(5):
            s.cyl('straw', 0.012, 0.005, 0.22, (sx * (0.72 + 0.04 * k / 4), 0.0, 1.45 + (k - 2) * 0.03),
                  rot=(0, sx * (math.pi / 2 + (k - 2) * 0.25), 0), segs=4, bevel=0)
        s.box('cloth_red', (0.1, 0.03, 0.1), (sx * 0.15, -0.16, 1.15), rot=(0, 0.3 * sx, 0), bevel=0.01)
    s.box('cloth_red', (0.38, 0.32, 0.08), (0, 0, 1.58), bevel=0.03)
    s.box('cloth_red', (0.08, 0.04, 0.3), (0.12, -0.17, 1.42), rot=(0, 0.15, 0), bevel=0.02)
    s.sphere('burlap', 0.2, (0, -0.01, 1.78), scale=(0.98, 0.95, 1.0), segs=12, rings=8, jitter=0.006)
    s.lathe('burlap', [(0.07, 0.0), (0.1, -0.06), (0.06, -0.1), (0.0, -0.1)], (0, 0, 1.62), segs=8)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        s.cyl('straw', 0.012, 0.004, 0.14, (math.cos(a) * 0.08, math.sin(a) * 0.08, 1.52),
              rot=(math.sin(a) * 0.4, -math.cos(a) * 0.4, 0), segs=4, bevel=0)
    for sx in (-1, 1):
        s.sphere('ink_dark', 0.03, (sx * 0.075, -0.18, 1.82), scale=(1, 0.5, 1.2), segs=6, rings=4)
    smile = [(math.cos(a) * 0.1, -0.19 + abs(math.cos(a)) * 0.04, 1.73 + (math.sin(a) + 1) * 0.0 - 0.0 +
              (-math.sin(a)) * 0.04) for a in [math.pi + k / 8 * math.pi for k in range(9)]]
    s.tube('ink_dark', smile, 0.008, 4)
    # witch-style hat
    s.lathe('wood_weathered', [(0.0, 0.0), (0.38, 0.0), (0.37, 0.03), (0.17, 0.05), (0.13, 0.25), (0.06, 0.4),
                               (0.0, 0.46)], (0, 0, 1.92), segs=12, rot=(0.15, 0.1, 0), jitter=0.01)
    s.cols.append(((0.5, 0.35, 2.0), (0, 0, 1.0)))
    return p


@prop('bell', 'hauntable', haunt=True, desc='brass bell on a wooden gallows post; swings about the yoke')
def bell():
    p = new('bell', haunt=True)
    m = p.main
    m.box('cobble', (0.5, 0.5, 0.3), (-0.3, 0, 0.15), bevel=0.04, jitter=0.01)
    m.box('wood_weathered', (0.16, 0.16, 2.1), (-0.3, 0, 1.2), bevel=0.03)
    m.box('wood_weathered', (1.0, 0.14, 0.14), (0.05, 0, 2.15), bevel=0.03)
    m.box('wood_weathered', (0.1, 0.1, 0.5), (-0.13, 0, 1.92), rot=(0, -0.78, 0), bevel=0.02)
    m.tube('vine', [(-0.22, -0.09, 0.3), (-0.24, -0.1, 0.9), (-0.2, -0.09, 1.5), (-0.25, -0.1, 2.0),
                    (0.1, -0.09, 2.2)], 0.018, 5)
    for z in (0.7, 1.2, 1.7, 2.1):
        m.sphere('vine', 0.07, (-0.24, -0.11, z), scale=(1, 0.4, 0.8), segs=6, rings=4)
    m.tube('rope', [(0.38, -0.09, 2.08), (0.38, -0.09, 2.22), (0.38, 0.09, 2.22), (0.38, 0.09, 2.08)], 0.02, 6)
    b = p.add(G.MeshNode('INT_bell', pivot=(0.38, 0, 2.08)))
    b.tube('rope', [(0.38, 0, 2.08), (0.38, 0, 1.85)], 0.02, 6)
    b.lathe('brass', [(0.0, 1.85), (0.05, 1.85), (0.08, 1.8), (0.1, 1.68), (0.13, 1.58), (0.17, 1.52),
                      (0.16, 1.5), (0.0, 1.52)], (0.38, 0, 0), segs=16)
    b.sphere('iron', 0.03, (0.38, 0, 1.53), segs=6, rings=4)
    p.add(G.empty('FX_ring', (0.38, 0, 1.7)))
    p.collision.append(((0.5, 0.5, 2.2), (-0.3, 0, 1.1)))
    return p
