"""Starting graveyard + mausoleum props (concept/locations/graveyard_*.png, concept_art/mausoleum.png)."""
import math

from mathutils import Vector

import lib_geo as G
from props_common import add_flame, arch_outline, candle_geo, lantern_geo, new, prop


def _moss(m, base, n, spread=(0.25, 0.08, 0.3), size=0.06):
    b = Vector(base)
    for k in range(n):
        off = Vector((G._rng.uniform(-1, 1) * spread[0], G._rng.uniform(-1, 1) * spread[1],
                      G._rng.uniform(-1, 1) * spread[2]))
        m.sphere('vine', size * G._rng.uniform(0.7, 1.3), b + off, scale=(1.3, 0.6, 0.5), segs=6, rings=4, jitter=0.01)


def _grave_base(p, m, w=0.8):
    m.box('grave_dirt', (w, 1.4, 0.12), (0, -0.55, 0.05), bevel=0.05, jitter=0.02)
    p.add(G.empty('MARK_worker_spawn', (0.0, -0.9, 0.12), 0))
    p.add(G.empty('FX_wisp', (0.0, -0.1, 1.1)))
    p.add(G.empty('MARK_tend', (0.0, -1.5, 0), 0))


@prop('gravestone_round', 'graveyard', desc='round-topped gravestone with an epitaph panel')
def gravestone_round():
    p = new('gravestone_round')
    m = p.main
    _grave_base(p, m)
    m.ext('stone_smooth', arch_outline(0.62, 0.95, 10), 0.16, (0, 0, 0), rot=(0.06, 0, 0.04), bevel=0.03, jitter=0.006)
    m.ext('stone_smooth', [(x * 0.8, z * 0.8 + 0.2) for x, z in arch_outline(0.62, 0.7, 10)], 0.02, (0, -0.085, 0),
          rot=(0.06, 0, 0.04), bevel=0.005)
    for z in (0.62, 0.52, 0.42):
        m.box('ink_dark', (0.28 - (0.62 - z) * 0.3, 0.01, 0.025), (0, -0.1 + 0.06 * z, z), rot=(0.06, 0, 0.04), bevel=0)
    _moss(m, (0, -0.02, 0.95), 4, (0.22, 0.06, 0.05))
    p.collision.append(((0.65, 0.2, 1.0), (0, 0, 0.5)))
    return p


@prop('gravestone_spiral', 'graveyard', desc='tall gravestone carved with the Veil spiral')
def gravestone_spiral():
    p = new('gravestone_spiral')
    m = p.main
    _grave_base(p, m)
    m.ext('stone_smooth', arch_outline(0.66, 1.15, 10), 0.18, (0, 0, 0), rot=(0.0, 0, -0.06), bevel=0.035, jitter=0.006)
    pts = []
    for i in range(60):
        t = i / 59
        a = t * 2.3 * 2 * math.pi
        r = 0.17 * t
        pts.append((math.cos(a) * r, -0.1, 0.75 + math.sin(a) * r))
    m.tube('stone_smooth', pts, 0.016, 5)
    _moss(m, (0, -0.02, 1.15), 5, (0.25, 0.08, 0.06))
    _moss(m, (-0.3, -0.05, 0.4), 3, (0.04, 0.05, 0.3))
    p.collision.append(((0.66, 0.2, 1.15), (0, 0, 0.57)))
    return p


@prop('gravestone_cross', 'graveyard', desc='leaning stone cross on a plinth')
def gravestone_cross():
    p = new('gravestone_cross')
    m = p.main
    _grave_base(p, m)
    m.box('stone_smooth', (0.5, 0.3, 0.22), (0, 0, 0.11), bevel=0.04, jitter=0.01)
    cross = [(-0.08, 0), (0.08, 0), (0.08, 0.62), (0.26, 0.62), (0.26, 0.78), (0.08, 0.78), (0.08, 0.98),
             (-0.08, 0.98), (-0.08, 0.78), (-0.26, 0.78), (-0.26, 0.62), (-0.08, 0.62)]
    m.ext('stone_smooth', cross, 0.15, (0, 0, 0.2), rot=(0.08, 0, 0.1), bevel=0.03, jitter=0.005)
    _moss(m, (0.0, -0.02, 0.95), 3, (0.2, 0.05, 0.08))
    p.collision.append(((0.5, 0.3, 1.2), (0, 0, 0.6)))
    return p


@prop('gravestone_celtic', 'graveyard', desc='ringed (celtic-style) cross gravestone')
def gravestone_celtic():
    p = new('gravestone_celtic')
    m = p.main
    _grave_base(p, m)
    m.box('stone_smooth', (0.6, 0.34, 0.25), (0, 0, 0.12), bevel=0.04, jitter=0.01)
    cross = [(-0.1, 0), (0.1, 0), (0.1, 0.8), (0.34, 0.8), (0.34, 1.0), (0.1, 1.0), (0.1, 1.28),
             (-0.1, 1.28), (-0.1, 1.0), (-0.34, 1.0), (-0.34, 0.8), (-0.1, 0.8)]
    m.ext('stone_smooth', cross, 0.17, (0, 0, 0.23), bevel=0.03, jitter=0.005)
    ring = [(math.cos(a) * 0.22, -0.0, 1.13 + math.sin(a) * 0.22) for a in [k / 20 * 2 * math.pi for k in range(21)]]
    m.tube('stone_smooth', ring, 0.045, 6)
    _moss(m, (-0.2, -0.05, 1.0), 4, (0.12, 0.05, 0.15))
    p.collision.append(((0.6, 0.34, 1.5), (0, 0, 0.75)))
    return p


def _gargoyle_body(m, base, s=1.0, wings=True):
    b = Vector(base)

    def V(x, y, z):
        return b + Vector((x * s, y * s, z * s))
    m.box('stone', (0.5 * s, 0.4 * s, 0.14 * s), V(0, 0, 0.07), bevel=0.03 * s, jitter=0.01 * s)  # plinth
    m.sphere('stone', 0.2 * s, V(0, 0.02, 0.33), scale=(1.0, 0.9, 1.15), segs=10, rings=7, jitter=0.01 * s)  # body
    for sx in (-1, 1):
        m.sphere('stone', 0.09 * s, V(sx * 0.13, -0.1, 0.2), scale=(0.9, 1.3, 0.9), segs=8, rings=5)  # haunches
        m.sphere('stone', 0.05 * s, V(sx * 0.1, -0.2, 0.18), scale=(1, 1.4, 0.7), segs=6, rings=4)  # feet/claws
        m.cyl('stone', 0.035 * s, 0.03 * s, 0.22 * s, V(sx * 0.12, -0.13, 0.33), rot=(0.4, 0, 0), segs=6, bevel=0.01)
    m.sphere('stone', 0.17 * s, V(0, -0.08, 0.62), scale=(1.15, 1.0, 0.95), segs=12, rings=8, jitter=0.006 * s)  # head
    m.sphere('stone', 0.08 * s, V(0, -0.22, 0.57), scale=(1.3, 0.9, 0.7), segs=8, rings=5)  # snout
    for sx in (-1, 1):
        m.cyl('stone', 0.05 * s, 0.0, 0.18 * s, V(sx * 0.13, -0.04, 0.78), rot=(0.3, sx * 0.5, 0), segs=6, bevel=0)  # horns
        m.ext('stone', [(0, 0), (0.12, 0.02), (0.05, 0.14)], 0.04 * s, V(sx * 0.17, -0.05, 0.64),
              rot=(0, 0, sx * 0.4), bevel=0.008, uv='box')  # ears
        m.sphere('eye_dark', 0.025 * s, V(sx * 0.065, -0.235, 0.65), scale=(1, 0.5, 0.8), segs=6, rings=4)
        m.box('bone', (0.025 * s, 0.02 * s, 0.05 * s), V(sx * 0.04, -0.29, 0.53), rot=(0, 0, 0), bevel=0.004)  # fangs
    if wings:
        for sx in (-1, 1):
            outline = [(0, 0), (0.2, 0.3), (0.42, 0.5), (0.62, 0.42), (0.55, 0.3), (0.62, 0.18), (0.48, 0.12),
                       (0.48, 0.0), (0.32, 0.05), (0.2, -0.05)]
            m.ext('stone', [(sx * x * s, z * s) for x, z in outline], 0.05 * s, V(sx * 0.12, 0.12, 0.38),
                  rot=(0, 0, -sx * 0.35), bevel=0.012)
    else:
        for sx in (-1, 1):
            m.sphere('stone', 0.14 * s, V(sx * 0.15, 0.1, 0.42), scale=(0.5, 1.0, 1.2), segs=8, rings=5)
    # curled tail
    tail = [V(0.0 + 0.12 * math.cos(a), 0.2 + 0.1 * math.sin(a), 0.12 + 0.02 * a) for a in
            [k / 10 * 3.5 for k in range(11)]]
    m.tube('stone', tail, 0.03 * s, 5, taper=0.4)


@prop('mausoleum_gargoyle_winged', 'graveyard', desc='winged ridge gargoyle (front gable top)')
def mausoleum_gargoyle_winged():
    p = new('mausoleum_gargoyle_winged')
    _gargoyle_body(p.main, (0, 0, 0), 1.25, wings=True)
    _moss(p.main, (0, 0.0, 0.1), 3, (0.2, 0.15, 0.04), size=0.05)
    return p


@prop('mausoleum_gargoyle_corner', 'graveyard', desc='crouched corner gargoyle with folded wings')
def mausoleum_gargoyle_corner():
    p = new('mausoleum_gargoyle_corner')
    _gargoyle_body(p.main, (0, 0, 0), 0.95, wings=False)
    return p


@prop('mausoleum_spiral_emblem', 'graveyard', desc='round stone plaque with a raised spiral, wall-mounted (centre 0 m, offset by placement)')
def mausoleum_spiral_emblem():
    p = new('mausoleum_spiral_emblem')
    m = p.main
    m.cyl('stone', 0.38, 0.38, 0.08, (0, -0.04, 0.4), rot=(math.pi / 2, 0, 0), segs=16, bevel=0.025)
    ring = [(math.cos(a) * 0.36, -0.09, 0.4 + math.sin(a) * 0.36) for a in [k / 24 * 2 * math.pi for k in range(25)]]
    m.tube('stone', ring, 0.03, 5)
    pts = []
    for i in range(70):
        t = i / 69
        a = t * 2.5 * 2 * math.pi
        pts.append((math.cos(a) * 0.28 * t, -0.09, 0.4 + math.sin(a) * 0.28 * t))
    m.tube('stone', pts, 0.022, 5)
    return p


@prop('mausoleum_portal', 'graveyard', desc='violet glowing doorway for a 1x2 opening, stone frame, open rusty gate')
def mausoleum_portal():
    p = new('mausoleum_portal')
    m = p.main
    # proud stone frame around the 1x2 opening
    for sx in (-0.62, 0.62):
        m.box('stone_mossy', (0.26, 0.3, 2.25), (sx, -0.58, 1.12), bevel=0.04, jitter=0.008)
    m.box('stone_mossy', (1.55, 0.34, 0.3), (0, -0.6, 2.3), bevel=0.04, jitter=0.008)
    m.box('stone', (0.36, 0.36, 0.3), (0, -0.62, 2.32), bevel=0.04)  # keystone
    # portal surface + inner glow
    m.box('FLAME_portal', (1.0, 0.04, 2.0), (0, -0.3, 1.0), bevel=0, uv='fit')
    m.box('FLAME_portal', (0.96, 0.02, 1.96), (0, 0.3, 1.0), bevel=0, uv='fit')
    # steps
    m.box('stone', (1.5, 0.45, 0.12), (0, -0.9, 0.06), bevel=0.03, jitter=0.01)
    m.box('stone', (1.3, 0.3, 0.12), (0, -0.7, 0.18), bevel=0.03, jitter=0.01)
    _moss(m, (-0.65, -0.72, 1.8), 4, (0.08, 0.05, 0.4))
    _moss(m, (0.0, -0.7, 2.45), 3, (0.6, 0.05, 0.03))
    gate = p.add(G.MeshNode('INT_gate', pivot=(-0.48, -0.75, 0)))
    # gate modelled open (swung outward ~110 deg)
    a = math.radians(-110)
    for i in range(6):
        x = 0.08 + i * 0.16
        pos = Vector((-0.48 + math.cos(a) * x, -0.75 + math.sin(a) * x, 1.0))
        gate.cyl('iron', 0.02, 0.02, 1.9, pos, segs=6, bevel=0.004)
        gate.cyl('iron', 0.0, 0.035, 0.08, pos + Vector((0, 0, 0.98)), segs=6, bevel=0)
    for z in (0.3, 1.7):
        c = Vector((-0.48 + math.cos(a) * 0.47, -0.75 + math.sin(a) * 0.47, z))
        gate.box('iron', (0.9, 0.04, 0.05), c, rot=(0, 0, a), bevel=0.006)
    gate.cols.append(((0.9, 0.05, 1.9), (-0.48 + math.cos(a) * 0.47, -0.75 + math.sin(a) * 0.47, 0.95)))
    p.add(G.LightNode('LIGHT_portal', (0, -0.9, 1.1), 90, (0.65, 0.35, 1.0), 0.4))
    p.add(G.empty('FX_wisp', (0, -0.4, 1.2)))
    p.add(G.empty('MARK_respawn', (0, 1.0, 0.0), 180))
    p.add(G.empty('MARK_door_outside', (0, -1.4, 0.24), 0))
    return p


@prop('mausoleum_window', 'graveyard', desc='narrow arched window glowing violet, for a 1x1 opening')
def mausoleum_window():
    p = new('mausoleum_window')
    m = p.main
    m.ext('stone', arch_outline(0.9, 1.1, 10), 0.14, (0, -0.47, -0.05), bevel=0.02)
    m.ext('FLAME_portal', [(x, z + 0.05) for x, z in arch_outline(0.55, 0.9, 10)], 0.02, (0, -0.55, 0.0), bevel=0,
          uv='fit')
    m.box('stone', (0.05, 0.03, 0.9), (0, -0.57, 0.45), bevel=0.005)
    return p


@prop('dead_tree', 'graveyard', desc='twisted dead tree with hanging lanterns')
def dead_tree():
    p = new('dead_tree')
    m = p.main
    G.seed(17)
    trunk = [(0, 0, -0.3), (0.1, 0.05, 0.8), (-0.15, 0.0, 1.7), (0.1, -0.1, 2.6), (0.0, 0.0, 3.2)]
    m.tube('bark', trunk, 0.55, 9, taper=0.45)
    for a in (0.4, 1.9, 3.3, 4.8):
        m.tube('bark', [(math.cos(a) * 0.2, math.sin(a) * 0.2, 0.4), (math.cos(a) * 0.8, math.sin(a) * 0.8, 0.0),
                        (math.cos(a) * 1.0, math.sin(a) * 1.0, -0.15)], 0.16, 6, taper=0.3)

    def branch(start, d, length, r, depth):
        if depth == 0 or r < 0.025:
            return
        end = Vector(start) + d * length
        mid = (Vector(start) + end) / 2 + Vector((G._rng.uniform(-0.2, 0.2), G._rng.uniform(-0.2, 0.2), 0.1))
        m.tube('bark', [start, mid, end], r, 6, taper=0.6)
        for k in range(2):
            nd = (d + Vector((G._rng.uniform(-0.8, 0.8), G._rng.uniform(-0.8, 0.8), G._rng.uniform(0.0, 0.6)))).normalized()
            branch(end, nd, length * 0.65, r * 0.6, depth - 1)
    branch((0.0, 0.0, 2.4), Vector((1, 0.2, 0.55)).normalized(), 1.7, 0.26, 3)
    branch((0.0, 0.0, 2.7), Vector((-1, -0.1, 0.65)).normalized(), 1.6, 0.24, 3)
    branch((0.05, 0.0, 3.0), Vector((0.1, 0.3, 1)).normalized(), 1.3, 0.2, 3)
    # moss on the trunk
    _moss(m, (0.0, -0.3, 1.0), 6, (0.25, 0.05, 0.6), size=0.09)
    # hanging lanterns from the two main limbs
    for i, (x, y, z) in enumerate(((1.25, 0.25, 2.95), (-1.15, -0.12, 3.2))):
        m.tube('iron', [(x, y, z), (x, y, z - 0.45)], 0.008, 4)
        lantern_geo(p, m, f'lantern_{i + 1}', (x, y, z - 0.86), scale=0.85)
    p.collision.append(((0.8, 0.8, 3.0), (0, 0, 1.5)))
    return p


@prop('wilted_flowers', 'graveyard', desc='drooping bell flowers (grave decor)')
def wilted_flowers():
    p = new('wilted_flowers')
    m = p.main
    G.seed(23)
    for k in range(4):
        x, y = G._rng.uniform(-0.15, 0.15), G._rng.uniform(-0.1, 0.1)
        h = G._rng.uniform(0.35, 0.6)
        tip = (x + 0.12, y - 0.05, h - 0.08)
        m.tube('vine', [(x, y, 0), (x + 0.02, y, h * 0.7), (x + 0.08, y - 0.03, h), tip], 0.012, 4)
        m.lathe('wood_dark', [(0.0, 0.0), (0.04, 0.02), (0.035, 0.07), (0.0, 0.08)], tip, segs=6, rot=(math.pi, 0, 0))
        m.sphere('vine', 0.05, (x, y, h * 0.4), scale=(1.4, 0.4, 0.5), segs=6, rings=4)
    return p


@prop('mushroom', 'graveyard', desc='small cluster of pale mushrooms')
def mushroom():
    p = new('mushroom')
    m = p.main
    for (x, y, h, r) in ((0, 0, 0.18, 0.09), (0.12, 0.05, 0.11, 0.06), (-0.08, 0.08, 0.08, 0.045)):
        m.cyl('bone', r * 0.35, r * 0.4, h, (x, y, h / 2), segs=8, bevel=0.01)
        m.lathe('wisteria', [(0.0, 0.0), (r, 0.0), (r * 0.9, r * 0.35), (r * 0.5, r * 0.65), (0.0, r * 0.75)],
                (x, y, h - 0.01), segs=10)
    return p


@prop('eerie_crystal_cluster', 'graveyard', desc='glowing eerie crystals growing from rock (ore outcrop decor)')
def eerie_crystal_cluster():
    p = new('eerie_crystal_cluster')
    m = p.main
    m.sphere('stone', 0.35, (0, 0, 0.1), scale=(1.3, 1.0, 0.6), segs=8, rings=5, jitter=0.05)
    for (x, y, h, r, tx, ty) in ((0, 0, 0.7, 0.1, 0, 0), (0.2, 0.05, 0.45, 0.08, 0.3, 0.1),
                                 (-0.2, 0.0, 0.5, 0.08, -0.35, 0.05), (0.05, -0.18, 0.35, 0.06, 0.1, -0.4),
                                 (-0.1, 0.18, 0.4, 0.06, -0.1, 0.4)):
        pos = Vector((x, y, 0.15))
        m.cyl('FLAME_crystal', r, r * 0.9, h, pos + Vector((0, 0, h / 2)), rot=(ty, tx, 0), segs=6, bevel=0)
        tip_rot = (ty, tx, 0)
        d = Vector((0, 0, h)).copy()
        d.rotate(__import__('mathutils').Euler(tip_rot))
        m.cyl('FLAME_crystal', r * 0.9, 0.0, r * 2.0, pos + d + d.normalized() * r, rot=tip_rot, segs=6, bevel=0)
    p.add(G.LightNode('LIGHT_crystal', (0, -0.3, 0.6), 30, (0.62, 0.35, 1.0), 0.3))
    p.collision.append(((0.8, 0.7, 0.6), (0, 0, 0.3)))
    return p


@prop('dirt_mound', 'graveyard', desc='freshly dug grave dirt with a bone (shovel node)')
def dirt_mound():
    p = new('dirt_mound')
    m = p.main
    m.sphere('grave_dirt', 0.45, (0, 0, 0.0), scale=(1.2, 0.9, 0.45), segs=10, rings=6, jitter=0.05)
    for k in range(5):
        a = k / 5 * 2 * math.pi
        m.sphere('grave_dirt', 0.1, (math.cos(a) * 0.5, math.sin(a) * 0.4, 0.05), segs=6, rings=4, jitter=0.02)
    m.cyl('bone', 0.025, 0.025, 0.22, (0.1, -0.2, 0.2), rot=(0.3, 1.2, 0), segs=6, bevel=0.005)
    for e in (-1, 1):
        m.sphere('bone', 0.03, (0.1 + e * 0.1, -0.2 - e * 0.03, 0.2 + e * 0.04), segs=6, rings=4)
    return p


@prop('weed_clump', 'graveyard', desc='grave weeds / fibre grass clump (scythe node)')
def weed_clump():
    p = new('weed_clump')
    m = p.main
    G.seed(31)
    for k in range(12):
        a = k / 12 * 2 * math.pi + G._rng.uniform(-0.2, 0.2)
        h = G._rng.uniform(0.35, 0.75)
        r0 = G._rng.uniform(0.0, 0.12)
        base = (math.cos(a) * r0, math.sin(a) * r0, 0)
        tip = (math.cos(a) * (r0 + h * 0.5), math.sin(a) * (r0 + h * 0.5), h)
        mid = ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2, h * 0.7)
        m.tube('vine', [base, mid, tip], 0.03, 4, taper=0.1)
    m.sphere('leaf', 0.18, (0, 0, 0.05), scale=(1.2, 1.2, 0.4), segs=8, rings=4, jitter=0.03)
    return p


@prop('stone_pillar', 'graveyard', desc='graveyard fence pillar with a cap stone')
def stone_pillar():
    p = new('stone_pillar')
    m = p.main
    m.box('stone_mossy', (0.5, 0.5, 1.2), (0, 0, 0.6), bevel=0.05, jitter=0.012)
    m.box('stone', (0.62, 0.62, 0.16), (0, 0, 1.28), bevel=0.05, jitter=0.01)
    m.lathe('stone', [(0.22, 0), (0.2, 0.1), (0.1, 0.18), (0.0, 0.2)], (0, 0, 1.36), segs=4, rot=(0, 0, math.pi / 4))
    _moss(m, (0, -0.2, 1.3), 3, (0.2, 0.05, 0.05))
    p.collision.append(((0.5, 0.5, 1.5), (0, 0, 0.75)))
    return p


@prop('grave_candles', 'graveyard', desc='candles on a stone block in front of a grave', haunt=False)
def grave_candles():
    p = new('grave_candles')
    m = p.main
    m.box('stone', (0.4, 0.35, 0.3), (0, 0, 0.15), bevel=0.04, jitter=0.01)
    m.cyl('wax', 0.13, 0.15, 0.02, (0, 0, 0.31), segs=10, bevel=0.005, jitter=0.005)
    for i, (x, h) in enumerate(((-0.07, 0.2), (0.07, 0.13))):
        wick = candle_geo(m, (x, 0, 0.31), 0.045, h)
        add_flame(p, f'candle_{i + 1}', wick, energy=8)
    return p
