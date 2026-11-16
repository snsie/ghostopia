"""Millbrook island generator (task3). Pure numpy: runs in plain Python and inside Blender.

World grid W[x, y, z] = uint8 block index from blocks.json (0 = air), Godot axes:
x -> east, y -> up, z -> south. Cell (x, y, z) fills [x, x+1] x [y, y+1] x [z, z+1] metres.
H[x, z] = y of the top solid block of the terrain column (-1 = void).

Everything is seeded: rng(name) gives an independent stream per feature, so changing one feature
does not reshuffle the others. Hand layout constants are at the top (cell coordinates).
"""
import gzip
import json
import math
import os
import zlib

import numpy as np

import lib_voxel as LV

ROOT = LV.ROOT
SX, SY, SZ = 192, 48, 192
CHUNK = 16
SEED = 20261116
GROUND = 20                      # village surface: top solid block y (first air = 21)
CENTRE = (96.0, 96.0)
ISLAND_R = 84.0                  # mean island radius in cells; the edge wobbles +-4

# ---------------------------------------------------------------- hand layout (cells, Godot axes)
SQUARE = dict(c=(113.0, 100.0), r=(9.5, 8.5))           # Millbrook square (cobbles)
GRAVE_HILL = dict(c=(28.0, 92.0), r=(14.0, 16.0), top=27)  # graveyard plateau
MILL_RISE = dict(c=(98.0, 50.0), r=(12.5, 11.5), top=26)   # windmill rise
HIGHLAND_TOP = 24                                           # north highland the stream comes from
FIELDS = dict(wheat=(137, 105, 157, 118), pumpkins=(124, 123, 144, 130))  # x0, z0, x1, z1 inclusive

# (blueprint, instance id, anchor cell (x, z), yaw deg, resident or None, area name)
STRUCTURES = [
    ('mausoleum', 'mausoleum', (24, 92), 90, None, 'Graveyard'),
    ('graveyard_gate', 'graveyard_gate', (40, 92), 90, None, 'Graveyard'),
    ('windmill_base', 'windmill', (98, 50), 0, 'agnes', 'Windmill'),
    ('cottage_a', 'pip_cottage', (104, 82), 0, 'pip', "Pip's Cottage"),
    ('cottage_c', 'marlow_cottage', (121, 83), 0, 'marlow', "Marlow's Cottage"),
    ('cottage_b', 'wren_cottage', (131, 100), -90, 'wren', "Wren's Cottage"),
    ('cottage_d', 'bram_cottage', (166, 108), -90, 'bram', "Bram's Cottage"),
    ('tavern', 'tavern', (96, 108), 90, None, 'Tavern'),
    ('well', 'well', (113, 100), 0, None, 'Millbrook Square'),
    ('plank_bridge', 'bridge', (86, 118), 90, None, 'Stream'),
]

# Stream centreline (x, z) from the north edge to the south edge, and its bank heights by z:
# the bank top block y; water fills bank-1 and bank-2, sand bed below. Drops = waterfalls.
STREAM_PTS = [(79, 4), (80, 22), (83, 36), (84, 50), (85, 62), (86, 74), (86, 110), (86, 126),
              (84, 142), (85, 158), (88, 172), (88, 190)]
STREAM_BANKS = [(0, 24), (63, 22), (70, 20), (150, 19), (166, 18)]  # (from z, bank top y)

# Paths: (block, width, [(x, z, h or None), ...]); h = top block y at that point (None = terrain).
# Heights are interpolated linearly along the path, so a drop of n over >= n metres becomes stairs.
PATHS = [
    # graveyard: mausoleum door -> gate -> stairs down the hill -> bridge -> square
    ('cobble_path', 3, [(28.0, 92.5, 27), (40.5, 92.5, 27), (42.0, 92.5, 27), (50.0, 93.5, 20), (54, 95, 20)]),
    ('packed_path', 3, [(54, 95, 20), (64, 101, None), (74, 110, None), (80, 118.5, 20), (83, 118.5, 20)]),
    ('cobble_path', 3, [(89, 118.5, 20), (95, 117.5, 20), (101, 113, 20), (106, 108, 20)]),
    # square -> north path -> windmill rise (stairs) -> mill door
    ('cobble_path', 3, [(112.5, 92, 20), (112.0, 82, 20), (108, 72, 20), (103.5, 66, 23), (99.5, 60.5, 26),
                        (97.5, 56.5, 26)]),
    # square -> east past Wren's cottage -> between the fields -> Bram's cottage
    ('cobble_path', 3, [(122, 101, 20), (128, 101.5, 20)]),
    ('packed_path', 3, [(128, 101.5, 20), (140, 101.0, None), (156, 101.0, None), (160, 105.5, 20),
                        (161.5, 109.5, 20)]),
    # cottage doors to the square
    ('cobble_path', 2, [(103.5, 87, 20), (106, 93, 20)]),
    ('cobble_path', 2, [(121.5, 87, 20), (119, 93, 20)]),
    ('cobble_path', 2, [(101, 107.5, 20), (105.5, 105, 20)]),
    # square -> south, out to the plains and the south forest
    ('packed_path', 3, [(111, 110, 20), (109, 124, None), (106, 140, None), (110, 156, None)]),
    # mill -> north highland spring path along the stream
    ('packed_path', 2, [(92, 52, None), (90, 40, None), (88, 26, None)]),
]

FOREST = [  # (x, z, radius, density) clumps of voxel oaks
    (52, 40, 20, 0.022), (60, 150, 22, 0.02), (150, 40, 22, 0.02), (160, 150, 16, 0.022),
    (120, 160, 14, 0.018), (36, 132, 12, 0.02), (132, 64, 12, 0.016), (70, 72, 10, 0.016),
]

CAVES = [  # (id, start (x, y, z), direction (dx, dy, dz), steps)
    ('graveyard_cave', (30.5, 24.5, 109.0), (0.15, -0.35, -1.0), 26),
    ('mill_cave', (112.0, 24.5, 50.0), (-1.0, -0.4, 0.2), 24),
    ('sinkhole_cave', (122.0, 21.0, 152.0), (0.0, -1.0, 0.0), 12),
]


def rng(name):
    return np.random.default_rng([SEED, zlib.crc32(name.encode())])


def blocks():
    doc = LV.blocks_doc()
    return {b['id']: b['index'] for b in doc['blocks']}, {b['index']: b for b in doc['blocks']}


IDX, BDEF = blocks()


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def value_noise(name, n, cell, octaves=3, persistence=0.5):
    """n x n fractal value noise in about [-1, 1], indexed [x, z]."""
    r = rng(name)
    out = np.zeros((n, n))
    amp, tot, c = 1.0, 0.0, float(cell)
    for _ in range(octaves):
        g = int(math.ceil(n / c)) + 3
        lat = r.uniform(-1, 1, (g, g))
        xs = np.arange(n) / c
        i = np.floor(xs).astype(int)
        f = xs - i
        f = f * f * (3 - 2 * f)
        v00 = lat[np.ix_(i, i)]
        v10 = lat[np.ix_(i + 1, i)]
        v01 = lat[np.ix_(i, i + 1)]
        v11 = lat[np.ix_(i + 1, i + 1)]
        fx, fz = f[:, None], f[None, :]
        out += amp * ((v00 * (1 - fx) + v10 * fx) * (1 - fz) + (v01 * (1 - fx) + v11 * fx) * fz)
        tot += amp
        amp *= persistence
        c /= 2
    return out / tot


def rot_xz(yaw, x, z):
    """Godot rotation.y by yaw degrees applied to a local (x, z) offset."""
    t = math.radians(yaw)
    c, s = math.cos(t), math.sin(t)
    if abs(yaw) % 90 == 0:
        c, s = round(c), round(s)
    return x * c + z * s, -x * s + z * c


def ellipse_e(X, Z, c, r):
    return np.sqrt(((X - c[0]) / r[0]) ** 2 + ((Z - c[1]) / r[1]) ** 2)


def load_blueprint(name):
    with open(os.path.join(ROOT, 'assets', 'structures', name + '.json')) as f:
        return json.load(f)


def polyline_samples(pts, step=0.25):
    """Yield (x, z, s, i, t) along a polyline of (x, z[, h]) points; i = segment, t in [0, 1]."""
    out = []
    s = 0.0
    for i in range(len(pts) - 1):
        x0, z0 = pts[i][0], pts[i][1]
        x1, z1 = pts[i + 1][0], pts[i + 1][1]
        L = math.hypot(x1 - x0, z1 - z0)
        n = max(1, int(L / step))
        for k in range(n + (1 if i == len(pts) - 2 else 0)):
            t = k / n
            out.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, s + L * t, i, t))
        s += L
    return out


# ============================================================================== the generator
class Island:
    def __init__(self):
        self.W = np.zeros((SX, SY, SZ), dtype=np.uint8)
        self.H = np.full((SX, SZ), -1, dtype=np.int32)
        self.top = np.full((SX, SZ), IDX['grass'], dtype=np.uint8)
        self.reserved = np.zeros((SX, SZ), dtype=bool)   # no trees / scatter here
        self.instances = []
        self.markers = []
        self.areas = []
        self.structures = []
        self.water = []
        self.notes = []
        X, Z = np.meshgrid(np.arange(SX) + 0.5, np.arange(SZ) + 0.5, indexing='ij')
        self.X, self.Z = X, Z
        self._props = json.load(open(os.path.join(ROOT, 'assets', 'props', 'props.json')))['props']
        self._uid = {}

    # ------------------------------------------------------------------ helpers
    def uid(self, base):
        n = self._uid.get(base, 0) + 1
        self._uid[base] = n
        return f'{base}_{n}'

    def surface_y(self, x, z):
        """First air y above the terrain column containing metre point (x, z)."""
        return int(self.H[int(x), int(z)]) + 1

    def add_instance(self, prop, pos, yaw, owner=None, tags=(), hauntable=None):
        p = self._props[prop]
        kind = hauntable
        if kind is None and p.get('hauntable'):
            kind = HAUNT_KIND.get(prop, prop)
        self.instances.append({
            'id': self.uid(prop), 'prop': prop, 'gltf': f'res://assets/props/{prop}.gltf',
            'pos': [round(float(v), 3) for v in pos], 'yaw': round(float(yaw) % 360, 2),
            'owner': owner, 'hauntable': kind, 'tags': list(tags)})

    def add_marker(self, kind, pos, yaw=0.0, owner=None, mid=None, **extra):
        m = {'kind': kind, 'id': mid or self.uid(kind), 'pos': [round(float(v), 3) for v in pos],
             'yaw': round(float(yaw) % 360, 2), 'owner': owner}
        m.update(extra)
        self.markers.append(m)
        return m

    def ground_prop(self, prop, x, z, yaw=0.0, owner=None, tags=(), dy=0.0):
        self.add_instance(prop, (x, self.surface_y(x, z) + dy, z), yaw, owner, tags)

    # ------------------------------------------------------------------ 1. heightmap
    def heightmap(self):
        X, Z = self.X, self.Z
        dx, dz = X - CENTRE[0], Z - CENTRE[1]
        ang = np.arctan2(dz, dx)
        r = rng('edge')
        R = np.full_like(X, ISLAND_R)
        for k in range(2, 9):
            R += r.uniform(-1, 1) * (3.2 / k ** 0.7) * np.sin(k * ang + r.uniform(0, 2 * math.pi))
        d = np.sqrt(dx * dx + dz * dz) / R           # 0 centre .. 1 edge
        self.d = d
        n1 = value_noise('plains', SX, 40, 3)
        n2 = value_noise('plains_fine', SX, 12, 2)
        h = GROUND + 0.4 + 2.6 * n1 + 0.8 * n2
        # north highland (the stream's source), terraced down toward the village
        hn = value_noise('highland_edge', SX, 24, 2)
        zedge = 58 + 6 * hn
        high = HIGHLAND_TOP + 0.6 * n2
        steps = HIGHLAND_TOP - np.floor((Z - zedge) / 4.0).clip(0, 4)
        hh = np.where(Z < zedge, high, steps)
        hmask = (smoothstep(150, 120, X) * smoothstep(40, 62, X))  # only in the north-west/centre
        h = np.where(hmask > 0.5, np.maximum(h, hh), h)
        # village plateau: flat GROUND around the square
        dv = np.hypot(X - SQUARE['c'][0], Z - SQUARE['c'][1])
        mv = 1 - smoothstep(30, 44, dv)
        h = h * (1 - mv) + GROUND * mv
        # fields: flat
        for (x0, z0, x1, z1) in FIELDS.values():
            m = (X > x0 - 4) & (X < x1 + 5) & (Z > z0 - 4) & (Z < z1 + 5)
            h = np.where(m, GROUND, h)
        # windmill rise (stone terraces)
        e = ellipse_e(X, Z, MILL_RISE['c'], MILL_RISE['r']) + 0.06 * n2
        hr = np.where(e < 1.0, MILL_RISE['top'], np.where(e < 1.22, MILL_RISE['top'] - 2, -99))
        h = np.maximum(h, hr)
        # graveyard hill: plateau, a terrace, a lower step; its west side is the island cliff
        e = ellipse_e(X, Z, GRAVE_HILL['c'], GRAVE_HILL['r']) + 0.07 * n2
        top = GRAVE_HILL['top']
        hg = np.where(e < 1.0, top, np.where(e < 1.17, top - 3, np.where(e < 1.42, top - 5, -99)))
        h = np.maximum(h, hg)
        H = np.round(h).astype(np.int32)
        # edge crumble: columns near the rim drop or vanish
        rr = rng('crumble')
        jitter = rr.uniform(0, 1, H.shape)
        H = np.where((d > 0.955) & (jitter < (d - 0.955) / 0.045 * 0.6), H - rr.integers(1, 4, H.shape), H)
        H = np.where((d > 0.975) & (jitter < (d - 0.975) / 0.025 * 0.9), -1, H)
        H[d >= 1.0] = -1
        self.H = H

    # ------------------------------------------------------------------ 2. pads under structures
    def footprint(self, name, anchor, yaw):
        doc = load_blueprint(name)
        sx, sy, sz = doc['size']
        ox, oy, oz = doc['origin']
        xs, zs = [], []
        for x in (0, sx - 1):
            for z in (0, sz - 1):
                rx, rz = rot_xz(yaw, x - ox, z - oz)
                xs.append(anchor[0] + int(round(rx)))
                zs.append(anchor[1] + int(round(rz)))
        return min(xs), min(zs), max(xs), max(zs)

    def pads(self):
        for (name, sid, (ax, az), yaw, res, area) in STRUCTURES:
            x0, z0, x1, z1 = self.footprint(name, (ax, az), yaw)
            if name == 'plank_bridge':
                continue  # the stream sets the bank height there
            h = self.H[ax, az]
            if name in ('mausoleum', 'graveyard_gate'):
                h = GRAVE_HILL['top']
            elif name == 'windmill_base':
                h = MILL_RISE['top']
            else:
                h = GROUND
            m = 1 if name not in ('well', 'graveyard_gate') else 0
            self.H[x0 - m:x1 + m + 1, z0 - m:z1 + m + 1] = h
            self.reserved[x0 - 2:x1 + 3, z0 - 2:z1 + 3] = True

    # ------------------------------------------------------------------ 3. paths and the square
    def paths(self):
        self.path_cells = np.zeros((SX, SZ), dtype=bool)
        # square: cobbles on an irregular ellipse
        n2 = value_noise('square', SX, 6, 1)
        e = ellipse_e(self.X, self.Z, SQUARE['c'], SQUARE['r']) + 0.08 * n2
        m = e < 1.0
        self.H[m] = GROUND
        u = rng('square_mix').uniform(0, 1, m.shape)
        self.top[m] = np.where(u < 0.3, IDX['cobblestone'], IDX['cobble_path'])[m]
        dw = np.hypot(self.X - SQUARE['c'][0], self.Z - SQUARE['c'][1])
        ring = (dw > 1.8) & (dw < 3.3)
        self.top[ring] = IDX['grass']
        self.well_ring = ring
        self.path_cells |= m
        self.reserved |= ellipse_e(self.X, self.Z, SQUARE['c'], (SQUARE['r'][0] + 2, SQUARE['r'][1] + 2)) < 1
        for block, width, pts in PATHS:
            hs = [p[2] if p[2] is not None else int(self.H[int(p[0]), int(p[1])]) for p in pts]
            best = {}
            for (x, z, s, i, t) in polyline_samples(pts):
                h = hs[i] + (hs[i + 1] - hs[i]) * t
                rad = width / 2.0
                for cx in range(int(x - rad - 1), int(x + rad + 2)):
                    for cz in range(int(z - rad - 1), int(z + rad + 2)):
                        dd = math.hypot(cx + 0.5 - x, cz + 0.5 - z)
                        if dd <= rad and 0 <= cx < SX and 0 <= cz < SZ:
                            if (cx, cz) not in best or dd < best[(cx, cz)][0]:
                                best[(cx, cz)] = (dd, h)
            for (cx, cz), (dd, h) in best.items():
                if self.H[cx, cz] < 0:
                    continue
                self.H[cx, cz] = int(round(h))
                self.top[cx, cz] = IDX[block]
                self.path_cells[cx, cz] = True
                self.reserved[max(0, cx - 1):cx + 2, max(0, cz - 1):cz + 2] = True

    # ------------------------------------------------------------------ 4. strata
    def fill(self):
        H = self.H
        r = rng('strata')
        d = self.d
        # thickness: a deep keel in the middle, thin at the rim (inverted craggy cone)
        nt = value_noise('keel', SX, 10, 2)
        thick = 3 + 21 * np.clip(1 - d ** 2, 0, 1) ** 0.9 + 4 * nt
        bot = np.clip(np.round(H - thick), 1, None).astype(np.int32)
        bot = np.where(H < 0, SY + 1, bot)
        self.bot = bot
        Y = np.arange(SY)[None, :, None]
        Hc, Bc = H[:, None, :], bot[:, None, :]
        solid = (Y >= Bc) & (Y <= Hc)
        depth = Hc - Y
        W = np.where(solid, IDX['stone'], 0).astype(np.uint8)
        nd = value_noise('dirt', SX, 8, 1)
        dirt_depth = np.round(3 + 1.2 * nd).astype(np.int32)[:, None, :]
        W[solid & (depth >= 1) & (depth <= dirt_depth)] = IDX['dirt']
        # cliffs: where a column stands >= 2 above a neighbour, show stone under the grass
        Hp = np.pad(H, 1, mode='edge')
        lowest = np.minimum.reduce([Hp[:-2, 1:-1], Hp[2:, 1:-1], Hp[1:-1, :-2], Hp[1:-1, 2:]])
        lowest = np.where(lowest < 0, H - 6, lowest)   # rim columns: stone faces toward the void
        cliff = (H - lowest >= 2)[:, None, :]
        W[solid & cliff & (depth >= 1)] = IDX['stone']
        # spectral stone deep down, with violet-veined (eerie ore) streaks on the underside
        spec = np.round(9 + 2.5 * value_noise('spec', SX, 14, 2)).astype(np.int32)[:, None, :]
        W[solid & (Y <= spec) & (depth > 4)] = IDX['spectral_stone']
        skin = solid & (Y - Bc <= 1) & (depth > 3)
        u = r.uniform(0, 1, W.shape)
        W[skin & (u < 0.45)] = IDX['spectral_stone']
        W[skin & (u < 0.035)] = IDX['eerie_ore']
        # top blocks
        topc = np.where(H >= 0, H, 0)
        xs, zs = np.nonzero(H >= 0)
        W[xs, topc[xs, zs], zs] = self.top[xs, zs]
        self.W = W

    # ------------------------------------------------------------------ 5. the stream
    def stream(self):
        W, H = self.W, self.H
        banks = sorted(STREAM_BANKS)

        def bank_at(z):
            b = banks[0][1]
            for z0, h in banks:
                if z >= z0:
                    b = h
            return b
        cells = {}
        samples = polyline_samples(STREAM_PTS, 0.2)
        for k, (x, z, s, i, t) in enumerate(samples):
            x0, z0 = STREAM_PTS[i]
            x1, z1 = STREAM_PTS[i + 1]
            L = math.hypot(x1 - x0, z1 - z0)
            fx, fz = (x1 - x0) / L, (z1 - z0) / L
            cz = int(z)
            cx = int(round(x))
            hb = bank_at(cz)
            for ox in range(-4, 5):
                gx = cx + ox
                if not (0 <= gx < SX and 0 <= cz < SZ) or H[gx, cz] < 0:
                    continue
                if abs(ox) <= 1:
                    cells[(gx, cz)] = (hb, fx, fz)
                elif abs(ox) == 2:
                    if (gx, cz) not in cells:
                        cells.setdefault(('bank', gx, cz), hb)
                else:
                    if (gx, cz) not in cells and H[gx, cz] < hb:   # embankment, no water walls
                        cells.setdefault(('bank', gx, cz), hb)
        r = rng('stream')
        for key, v in cells.items():
            if key[0] != 'bank':
                continue
            _, gx, cz = key
            if (gx, cz) in cells:
                continue
            hb = v
            H[gx, cz] = hb
            W[gx, :, cz] = np.where((np.arange(SY) >= self.bot[gx, cz]) & (np.arange(SY) <= hb),
                                    np.where(np.arange(SY) >= hb - 2, IDX['dirt'], IDX['stone']), 0)
            W[gx, hb, cz] = IDX['sand'] if r.random() < 0.55 else (IDX['grass'] if r.random() < 0.6 else IDX['stone'])
            self.top[gx, cz] = W[gx, hb, cz]
            self.reserved[gx, cz] = True
        wcells = []
        for key, v in cells.items():
            if key[0] == 'bank':
                continue
            gx, cz = key
            hb, fx, fz = v
            H[gx, cz] = hb - 3
            col = np.arange(SY)
            W[gx, :, cz] = np.where((col >= self.bot[gx, cz]) & (col <= hb - 3), IDX['stone'], 0)
            W[gx, hb - 3, cz] = IDX['sand']
            W[gx, hb + 1:, cz] = 0
            for y in (hb - 2, hb - 1):
                W[gx, y, cz] = IDX['river_water']
                wcells.append((gx, y, cz, fx, fz))
            self.reserved[max(0, gx - 2):gx + 3, max(0, cz - 1):cz + 2] = True
        # waterfalls: water cells whose downstream neighbour sits lower -> falls flag
        wset = {(c[0], c[1], c[2]) for c in wcells}
        out = []
        for (gx, y, cz, fx, fz) in sorted(wcells, key=lambda c: (c[2], c[0], c[1])):
            fall = (gx, y, cz + 1) not in wset and (gx, y - 1, cz + 1) in wset or \
                   (gx, y, cz + 1) not in wset and (gx, y - 2, cz + 1) in wset
            out.append([gx, y, cz, round(fx, 2), round(fz, 2), 1 if fall else 0])
        self.stream_cells = out
        # fill the gap under waterfall lips so water reads as a falling sheet
        for (gx, y, cz, fx, fz, fall) in out:
            if fall:
                for yy in range(y - 2, y):
                    if W[gx, yy, cz] == 0 and W[gx, yy, cz + 1] == IDX['river_water']:
                        W[gx, yy, cz] = IDX['river_water']
        self.water.append({'id': 'stream', 'block': 'river_water', 'running_water': True,
                           'note': 'cells are [x, y, z, flow_x, flow_z, waterfall]; flow is a unit vector in the '
                                   'x-z plane (Godot axes); the stream runs north to south and falls off the '
                                   'south rim into the void. Spirits cannot cross it (running water rule); '
                                   'the plank bridge is the crossing.',
                           'cells': out})

    # ------------------------------------------------------------------ 6. caves and ore
    def caves(self):
        W = self.W
        protect = self.reserved & ~self.path_cells
        self.cave_info = []
        for cid, start, direc, steps in CAVES:
            r = rng('cave_' + cid)
            p = np.array(start, dtype=float)
            dvec = np.array(direc, dtype=float)
            dvec /= np.linalg.norm(dvec)
            chamber = None
            pts = []
            for k in range(steps):
                rad = 1.6 + 0.6 * r.random() + (1.2 if k == steps - 1 else 0)
                pts.append((p.copy(), rad))
                turn = r.normal(0, 0.35, 3)
                turn[1] *= 0.3
                dvec = dvec + turn * 0.4
                if p[1] < 9:
                    dvec[1] = abs(dvec[1]) * 0.2
                dvec /= np.linalg.norm(dvec)
                p = p + dvec * 1.3
                chamber = p.copy()
            for (c, rad) in pts:
                x0, x1 = int(c[0] - rad - 1), int(c[0] + rad + 2)
                y0, y1 = int(c[1] - rad - 1), int(c[1] + rad + 2)
                z0, z1 = int(c[2] - rad - 1), int(c[2] + rad + 2)
                for x in range(max(1, x0), min(SX - 1, x1)):
                    for z in range(max(1, z0), min(SZ - 1, z1)):
                        if protect[x, z] and c[1] > self.H[x, z] - 4:
                            continue
                        for y in range(max(2, y0), min(SY - 1, y1)):
                            if (x + 0.5 - c[0]) ** 2 + ((y + 0.5 - c[1]) * 1.25) ** 2 + (z + 0.5 - c[2]) ** 2 > rad * rad:
                                continue
                            if y <= self.bot[x, z] + 1:
                                continue
                            near_water = (W[max(0, x - 1):x + 2, max(0, y - 1):y + 3, max(0, z - 1):z + 2] == IDX['river_water']).any()
                            if near_water:
                                continue
                            W[x, y, z] = 0
            # floor of the last chamber
            cx, cy, cz = (int(v) for v in pts[-1][0])
            fy = cy
            while fy > 1 and W[cx, fy - 1, cz] == 0:
                fy -= 1
            self.cave_info.append((cid, (cx + 0.5, fy, cz + 0.5), pts))
            # glowing ore on the chamber walls
            rad = pts[-1][1] + 1.5
            for x in range(cx - 4, cx + 5):
                for y in range(cy - 4, cy + 5):
                    for z in range(cz - 4, cz + 5):
                        if not (0 < x < SX - 1 and 0 < y < SY - 1 and 0 < z < SZ - 1):
                            continue
                        if W[x, y, z] in (IDX['stone'], IDX['spectral_stone'], IDX['dirt']) and \
                                (W[x - 1:x + 2, y - 1:y + 2, z - 1:z + 2] == 0).any() and r.random() < 0.10:
                            W[x, y, z] = IDX['eerie_ore'] if r.random() < 0.6 else IDX['iron_ore']
        # ore pockets in the rock
        r = rng('ore')
        for kind, n, ylo, yhi, host in (('iron_ore', 40, 5, 17, ('stone',)), ('eerie_ore', 22, 2, 11, ('spectral_stone', 'stone'))):
            hosts = [IDX[h] for h in host]
            placed = 0
            tries = 0
            while placed < n and tries < 4000:
                tries += 1
                x, y, z = r.integers(4, SX - 4), r.integers(ylo, yhi + 1), r.integers(4, SZ - 4)
                if W[x, y, z] not in hosts or y > self.H[x, z] - 3:
                    continue
                for _ in range(r.integers(3, 8)):
                    ax, ay, az = x + r.integers(-1, 2), y + r.integers(-1, 2), z + r.integers(-1, 2)
                    if W[ax, ay, az] in hosts and ay < self.H[ax, az] - 2:
                        W[ax, ay, az] = IDX[kind]
                placed += 1

    # ------------------------------------------------------------------ 7. graveyard
    def graveyard(self):
        W, H = self.W, self.H
        top = GRAVE_HILL['top']
        r = rng('graveyard')
        e = ellipse_e(self.X, self.Z, GRAVE_HILL['c'], GRAVE_HILL['r'])
        plateau = (e < 0.97) & (H == top)
        # grave moss patches + weeds on the plateau
        nm = value_noise('gmoss', SX, 5, 1)
        for x, z in zip(*np.nonzero(plateau & ~self.path_cells)):
            if nm[x, z] > 0.25:
                W[x, top, z] = IDX['grave_moss']
        # eerie ore outcrop north-east of the mausoleum (concept: violet crystal rocks)
        ocx, ocz = 34, 80
        ore_cells = []
        for x in range(ocx - 3, ocx + 4):
            for z in range(ocz - 3, ocz + 3):
                dd = math.hypot((x - ocx) / 3.2, (z - ocz) / 2.6)
                hgt = int(round(3.4 * (1 - dd) + r.uniform(-0.4, 0.4)))
                for y in range(top + 1, top + 1 + max(0, hgt)):
                    W[x, y, z] = IDX['stone'] if r.random() < 0.7 else IDX['spectral_stone']
                    ore_cells.append((x, y, z))
                if hgt > 0:
                    self.reserved[x, z] = True
        for (x, y, z) in ore_cells:
            exposed = W[x, y + 1, z] == 0 or W[x + 1, y, z] == 0 or W[x - 1, y, z] == 0 or W[x, y, z + 1] == 0 or W[x, y, z - 1] == 0
            if exposed and r.random() < 0.42:
                W[x, y, z] = IDX['eerie_ore']
        # crystals on and around the outcrop
        for (x, z) in ((33.5, 82.6), (37.4, 79.5), (31.2, 79.2)):
            self.ground_prop('eerie_crystal_cluster', x, z, r.uniform(0, 360), owner='graveyard', tags=['ore'])
        # graves: two rows facing the central path; plot (grave dirt) between stone and path
        stones = ['gravestone_round', 'gravestone_cross', 'gravestone_spiral', 'gravestone_celtic']
        gi = 0
        for row_z, yaw, plot_dz in ((86, 0, (1, 2)), (98, 180, (-2, -1))):
            for k, gx in enumerate((31, 34, 37)):
                name = stones[gi % 4]
                gi += 1
                lean = r.uniform(-7, 7)
                self.add_instance(name, (gx + 0.5, top + 1, row_z + 0.5), yaw + lean, owner='graveyard',
                                  tags=['grave'])
                for dz in plot_dz:
                    W[gx, top, row_z + dz] = IDX['grave_dirt']
                    self.reserved[gx, row_z + dz] = True
                pz = row_z + 0.5 + sum(plot_dz) / 2.0
                self.add_marker('grave_node', (gx + 0.5, top + 1, pz), yaw, owner='graveyard',
                                block='grave_dirt', grave=name)
                if (k + gi) % 2 == 0:
                    self.add_instance('grave_candles', (gx + 1.3, top + 1, row_z + 0.5 + (0.9 if yaw == 0 else -0.9)), 0,
                                      owner='graveyard', tags=['light'])
                else:
                    self.add_instance('wilted_flowers', (gx + 0.0, top + 1, row_z + 0.5 + (1.0 if yaw == 0 else -1.0)),
                                      r.uniform(0, 360), owner='graveyard')
        # two old graves behind the mausoleum + loose grave-dirt patches
        for (gx, gz, name, yaw) in ((19, 86, 'gravestone_round', 70), (19, 99, 'gravestone_spiral', 110)):
            self.add_instance(name, (gx + 0.5, top + 1, gz + 0.5), yaw, owner='graveyard', tags=['grave'])
            W[gx + 1, top, gz] = IDX['grave_dirt']
            W[gx + 2, top, gz] = IDX['grave_dirt']
            self.add_marker('grave_node', (gx + 2.0, top + 1, gz + 0.5), yaw, owner='graveyard', block='grave_dirt',
                            grave=name)
        for (px, pz) in ((33, 102), (24, 104), (40, 86)):
            for ddx, ddz in ((0, 0), (1, 0), (0, 1), (1, 1)):
                if r.random() < 0.85 and not self.path_cells[px + ddx, pz + ddz]:
                    W[px + ddx, top, pz + ddz] = IDX['grave_dirt']
            self.ground_prop('dirt_mound', px + 1.0, pz + 1.0, r.uniform(0, 360), owner='graveyard')
            self.add_marker('grave_node', (px + 1.0, top + 1, pz + 1.0), 0, owner='graveyard', block='grave_dirt')
        # dead tree with lanterns, mushrooms, weeds
        self.ground_prop('dead_tree', 18.5, 81.5, 30, owner='graveyard')
        for (x, z) in ((21.5, 101.5), (38.5, 101.0), (16.5, 92.5), (36.0, 89.0), (25.5, 84.0), (29.5, 102.5)):
            self.ground_prop('weed_clump', x, z, r.uniform(0, 360), owner='graveyard', tags=['weed'])
            self.add_marker('weed_node', (x, self.surface_y(x, z), z), 0, owner='graveyard', source='weed_clump')
        for (x, z) in ((17.5, 85.5), (22.5, 80.5), (30.5, 100.5), (39.5, 97.0), (20.0, 96.0)):
            self.ground_prop('mushroom', x, z, r.uniform(0, 360), owner='graveyard')
        weeds = 0
        for x, z in zip(*np.nonzero(plateau & ~self.reserved & ~self.path_cells)):
            if r.random() < 0.13 and W[x, top + 1, z] == 0:
                W[x, top + 1, z] = IDX['tall_grass']
                weeds += 1
                if weeds % 3 == 0:
                    self.add_marker('weed_node', (x + 0.5, top + 1, z + 0.5), 0, owner='graveyard', source='grave_weeds')
            elif r.random() < 0.05 and W[x, top + 1, z] == 0:
                W[x, top + 1, z] = IDX['flowers']
        # fence round the plateau rim (gap at the gate in the east)
        cx, cz = GRAVE_HILL['c']
        rx, rz = GRAVE_HILL['r'][0] - 1.1, GRAVE_HILL['r'][1] - 1.1
        n = int(2 * math.pi * math.sqrt((rx * rx + rz * rz) / 2) / 1.08)
        for k in range(n):
            a = 2 * math.pi * k / n
            x, z = cx + rx * math.cos(a), cz + rz * math.sin(a)
            if abs(z - 92.5) < 6 and x > cx:
                continue   # gate wall there
            if self.H[int(x), int(z)] != top or self.path_cells[int(x), int(z)] or self.reserved[int(x), int(z)]:
                continue
            tx, tz = -math.sin(a), math.cos(a)
            yaw = math.degrees(math.atan2(-tz, tx))
            self.add_instance('fence_wood', (x, top + 1, z), yaw, owner='graveyard', tags=['fence'])
        self.ground_prop('lantern_post', 43.5, 96.0, 90, owner='graveyard', tags=['light', 'lantern_post'])

    # ------------------------------------------------------------------ 8. village dressing, fields, mill
    def village(self):
        W = self.W
        r = rng('village')
        sx, sz = SQUARE['c']
        # charm (notice) board east of the well, bell frame, benches, barrels
        self.ground_prop('notice_board', sx + 6.0, sz - 1.0, 0, owner='square', tags=['charm_board'])
        self.ground_prop('bell', sx + 9.5, sz - 7.5, -30, owner='square')
        self.ground_prop('bench', sx - 4.5, sz + 4.0, 20, owner='square', tags=['seat'])
        self.ground_prop('bench', sx + 4.0, sz + 5.0, -15, owner='square', tags=['seat'])
        for (x, z, p, yaw) in ((sx + 7.6, sz - 0.2, 'barrel', 0), (sx + 4.6, sz + 0.4, 'bucket', 0),
                               (sx + 7.4, sz + 0.8, 'candle_cluster', 0), (sx - 1.8, sz + 1.6, 'flower_box', 30),
                               (101.4, 114.6, 'barrel', 0), (102.2, 115.3, 'crate', 12), (126.5, 96.0, 'crate', -8),
                               (126.0, 95.2, 'barrel', 0)):
            self.ground_prop(p, x, z, yaw, owner='square')
        # lantern posts along the paths (lanterns on posts, per the concept)
        posts = [(103.0, 92.0, 135), (123.5, 92.5, -135), (103.0, 109.0, 45), (124.0, 108.5, -45),
                 (114.5, 80.0, 180), (110.0, 70.0, 160), (101.0, 61.0, 160), (93.0, 116.0, 0), (80.5, 116.0, 0),
                 (68.0, 102.5, 30), (56.0, 92.5, 60), (137.0, 99.0, 0), (150.0, 99.0, 0), (160.0, 103.0, -90),
                 (113.5, 118.0, 180), (108.5, 134.0, 180)]
        for (x, z, yaw) in posts:
            self.ground_prop('lantern_post', x, z, yaw, owner='village', tags=['light', 'lantern_post'])
        # oak props (painted trees) around the village edge
        for (x, z) in ((98.0, 92.0), (128.5, 88.5), (124.0, 115.5), (94.5, 99.0), (108.0, 74.0), (128.0, 110.0),
                       (90.5, 64.0), (116.5, 72.0)):
            self.ground_prop('tree_oak', x, z, r.uniform(0, 360), owner='village', tags=['tree'])
            self.reserved[int(x) - 2:int(x) + 3, int(z) - 2:int(z) + 3] = True
        # flowers around the square and cottages
        dv = np.hypot(self.X - sx, self.Z - sz)
        cand = (dv < 30) & (dv > 9) & ~self.path_cells & (self.H == GROUND)
        clump = value_noise('flower_clumps', SX, 5, 2)
        for x, z in zip(*np.nonzero(cand)):
            if W[x, GROUND, z] == IDX['grass'] and W[x, GROUND + 1, z] == 0 and clump[x, z] > 0.28 and r.random() < 0.55:
                W[x, GROUND + 1, z] = IDX['flowers']
        for x, z in zip(*np.nonzero(self.well_ring)):
            if W[x, GROUND + 1, z] == 0 and r.random() < 0.45:
                W[x, GROUND + 1, z] = IDX['flowers']
        # fields: wheat (dirt + wheat crosses), pumpkins (dirt + props), fences, scarecrow
        x0, z0, x1, z1 = FIELDS['wheat']
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                W[x, GROUND, z] = IDX['dirt']
                W[x, GROUND + 1:, z] = 0
                if (z - z0) % 4 != 3:
                    W[x, GROUND + 1, z] = IDX['wheat']
        self.reserved[x0 - 2:x1 + 3, z0 - 2:z1 + 3] = True
        self.add_instance('scarecrow', ((x0 + x1) / 2 + 1.0, GROUND + 1, (z0 + z1) / 2 + 0.5), 200, owner='fields')
        W[int((x0 + x1) / 2 + 1), GROUND + 1, int((z0 + z1) / 2)] = 0
        px0, pz0, px1, pz1 = FIELDS['pumpkins']
        for x in range(px0, px1 + 1):
            for z in range(pz0, pz1 + 1):
                W[x, GROUND, z] = IDX['dirt'] if (x + z) % 5 else IDX['grass']
                W[x, GROUND + 1:, z] = 0
        self.reserved[px0 - 2:px1 + 3, pz0 - 2:pz1 + 3] = True
        for x in range(px0 + 1, px1, 2):
            for z in range(pz0 + 1, pz1, 3):
                jx, jz = r.uniform(-0.3, 0.3, 2)
                p = 'pumpkin' if r.random() < 0.55 else 'pumpkin_small'
                self.add_instance(p, (x + 0.5 + jx, GROUND + 1, z + 0.5 + jz), r.uniform(0, 360), owner='fields',
                                  tags=['crop'])
                self.add_instance('pumpkin_vine', (x + 0.5 - jx, GROUND + 1, z + 1.5), r.uniform(0, 360),
                                  owner='fields')
        self.ground_prop('crate', px1 + 1.5, pz0 - 0.5, 10, owner='fields')
        self.ground_prop('basket', px1 + 0.8, pz0 - 0.2, 0, owner='fields')
        for (fx0, fz0, fx1, fz1, gate) in ((x0 - 1, z0 - 1, x1 + 1, z1 + 1, ('n', 142)),
                                            (px0 - 1, pz0 - 1, px1 + 1, pz1 + 1, ('n', 128))):
            self.fence_rect(fx0, fz0, fx1, fz1, gate, owner='fields')
        # windmill rise: fence along the south rim, grain sacks and crates by the door
        mx, mz = MILL_RISE['c']
        top = MILL_RISE['top']
        for k in range(-5, 6):
            x = mx + k * 1.1 + 0.5
            z = mz + MILL_RISE['r'][1] - 0.9
            if abs(x - 99.0) < 2.2:
                continue   # path gap
            if self.H[int(x), int(z)] == top:
                self.add_instance('fence_wood', (x, top + 1, z), 0, owner='windmill', tags=['fence'])
        for (x, z, p, yaw) in ((94.6, 57.0, 'grain_sack', 0), (95.3, 57.4, 'grain_sack', 30), (102.2, 56.8, 'crate', 5),
                               (102.9, 57.5, 'barrel', 0)):
            self.ground_prop(p, x, z, yaw, owner='windmill')

    def fence_rect(self, x0, z0, x1, z1, gate, owner):
        side, gpos = gate
        for x in range(x0, x1 + 1):
            for z, s in ((z0, 'n'), (z1, 's')):
                if s == side and abs(x - gpos) <= 1:
                    continue
                self.add_instance('fence_wood', (x + 0.5, self.surface_y(x, z), z + 0.5), 0, owner=owner, tags=['fence'])
        for z in range(z0 + 1, z1):
            for x in (x0, x1):
                self.add_instance('fence_wood', (x + 0.5, self.surface_y(x, z), z + 0.5), 90, owner=owner, tags=['fence'])

    # ------------------------------------------------------------------ 9. trees and plains scatter
    def vegetation(self):
        W, H = self.W, self.H
        r = rng('trees')
        trees = []
        ok = (H >= 0) & ~self.reserved & (self.d < 0.93)
        ok &= ellipse_e(self.X, self.Z, GRAVE_HILL['c'], GRAVE_HILL['r']) > 1.6   # keep the graveyard views open
        for (fx, fz, rad, dens) in FOREST:
            n = int(math.pi * rad * rad * dens)
            for _ in range(n * 3):
                if n <= 0:
                    break
                a, rr = r.uniform(0, 2 * math.pi), rad * math.sqrt(r.uniform(0, 1))
                x, z = int(fx + rr * math.cos(a)), int(fz + rr * math.sin(a))
                if not (3 <= x < SX - 3 and 3 <= z < SZ - 3) or not ok[x, z]:
                    continue
                if any(abs(x - tx) + abs(z - tz) < 5 for tx, tz in trees):
                    continue
                if W[x, H[x, z], z] not in (IDX['grass'], IDX['grave_moss'], IDX['dirt']):
                    continue
                trees.append((x, z))
                n -= 1
        # a few lone trees on the plains
        for _ in range(60):
            x, z = r.integers(8, SX - 8), r.integers(8, SZ - 8)
            if ok[x, z] and self.d[x, z] < 0.85 and all(abs(x - tx) + abs(z - tz) > 9 for tx, tz in trees):
                trees.append((x, z))
        self.trees = trees
        for (x, z) in trees:
            y0 = H[x, z] + 1
            th = int(r.integers(4, 7))
            for y in range(y0, min(SY - 1, y0 + th)):
                W[x, y, z] = IDX['oak_log']
            W[x, y0 - 1, z] = IDX['dirt']
            cy = y0 + th - 0.5
            rad = r.uniform(2.3, 3.3)
            for ax in range(x - 4, x + 5):
                for az in range(z - 4, z + 5):
                    for ay in range(int(cy - 3), int(cy + 4)):
                        if not (0 <= ax < SX and 0 <= az < SZ and 0 <= ay < SY):
                            continue
                        dd = math.sqrt((ax - x) ** 2 + ((ay - cy) * 1.3) ** 2 + (az - z) ** 2)
                        if dd < rad - 0.4 or (dd < rad + 0.5 and r.random() < 0.55):
                            if W[ax, ay, az] == 0:
                                W[ax, ay, az] = IDX['leaves']
            self.reserved[x - 1:x + 2, z - 1:z + 2] = True
        # tall grass and wildflowers on open grass
        free = (H >= 0) & ~self.path_cells
        u = r.uniform(0, 1, H.shape)
        # neat lawns in the village: no weeds within 30 m of the square, flower clumps only
        dv = np.hypot(self.X - SQUARE['c'][0], self.Z - SQUARE['c'][1])
        u = np.where((dv < 30) & (u < 0.07), 1.0, u)
        nf = value_noise('flowers', SX, 9, 1)
        for x, z in zip(*np.nonzero(free & (u < 0.16))):
            y = H[x, z]
            if W[x, y, z] != IDX['grass'] or W[x, y + 1, z] != 0:
                continue
            W[x, y + 1, z] = IDX['flowers'] if (nf[x, z] > 0.3 and u[x, z] < 0.09) else (
                IDX['tall_grass'] if u[x, z] < 0.07 else 0)

    # ------------------------------------------------------------------ 10. structures
    def stamp_structures(self):
        W = self.W
        for (name, sid, (ax, az), yaw, res, area) in STRUCTURES:
            doc = load_blueprint(name)
            a = LV.decode_rle(doc['size'], doc['palette'], doc['rle'])
            ox, oy, oz = doc['origin']
            if name == 'plank_bridge':
                ay = STREAM_BANK_AT(az) + 1
            else:
                ay = int(self.H[ax, az]) + 1
            sx, sy, sz = a.shape
            for x in range(sx):
                for z in range(sz):
                    rx, rz = rot_xz(yaw, x - ox, z - oz)
                    wx, wz = ax + int(round(rx)), az + int(round(rz))
                    for y in range(sy):
                        b = a[x, y, z]
                        if b == '_skip':
                            continue
                        wy = ay + y - oy
                        if 0 <= wx < SX and 0 <= wy < SY and 0 <= wz < SZ:
                            W[wx, wy, wz] = 0 if b == 'air' else IDX[b]
                    # nothing grows inside a footprint
                    if any(a[x, y, z] != '_skip' for y in range(sy)):
                        for wy in range(ay, SY):
                            if W[wx, wy, wz] in (IDX['tall_grass'], IDX['flowers'], IDX['leaves']):
                                W[wx, wy, wz] = 0
            pivot = (ax + 0.5, ay, az + 0.5)
            rec = {'id': sid, 'blueprint': name, 'json': f'res://assets/structures/{name}.json',
                   'anchor': [ax, ay, az], 'pivot': [pivot[0], pivot[1], pivot[2]], 'yaw': yaw % 360,
                   'resident': res, 'area': area, 'rooms': []}
            fp = self.footprint(name, (ax, az), yaw)
            rec['footprint'] = [fp[0], fp[1], fp[2] + 1, fp[3] + 1]
            for room in doc.get('rooms', []):
                (x0, y0, z0), (x1, y1, z1) = room['min'], room['max']
                cs = [rot_xz(yaw, x, z) for x in (x0, x1) for z in (z0, z1)]
                rec['rooms'].append({'name': room['name'],
                                     'min': [round(pivot[0] + min(c[0] for c in cs), 3), pivot[1] + y0,
                                             round(pivot[2] + min(c[1] for c in cs), 3)],
                                     'max': [round(pivot[0] + max(c[0] for c in cs), 3), pivot[1] + y1,
                                             round(pivot[2] + max(c[1] for c in cs), 3)]})
            self.structures.append(rec)

            def world(p):
                rx, rz = rot_xz(yaw, p[0], p[2])
                return (pivot[0] + rx, pivot[1] + p[1], pivot[2] + rz)
            owner = sid
            for p in doc.get('props', []):
                self.add_instance(p['prop'], world(p['pos']), yaw + p.get('yaw', 0), owner=owner, tags=p.get('tags', []))
            for m in doc.get('markers', []):
                self.structure_marker(m, world(m['pos']), yaw + m.get('yaw', 0), sid, res, name)

    def structure_marker(self, m, pos, yaw, sid, res, bp):
        k, mid = m['kind'], m['id']
        who = res or sid
        extra = {'source': f'{bp}:{mid}'}
        if res:
            extra['resident'] = res
        mapping = {
            'spawn_villager': ('villager_home', f'villager_home_{who}'),
            'sleep': ('bed', f'bed_{who}'),
            'hearth': ('hearth', f'hearth_{who}'),
            'hide': ('hiding_spot', f'hiding_spot_{who}_{mid.replace("hide_", "")}'),
            'creak': ('creak', f'creak_{who}_{mid.replace("creak_", "")}'),
            'door': ('door', f'door_{who}_{mid.replace("door_", "")}'),
            'window': ('window', f'window_{who}_{mid.replace("window_", "")}'),
            'entry': ('entry', f'entry_{who}_{mid.replace("entry_", "")}'),
            'sit': ('chair', f'chair_{who}_{mid.replace("sit_", "")}'),
            'respawn': ('respawn', 'respawn'),
            'storage': ('storage', f'storage_{who}'),
            'spawn_worker': ('worker_spawn', f'worker_spawn_{who}'),
            'climb': ('climb', f'climb_{who}_{mid}'),
            'hub': ('anim_hub', f'sails_hub_{who}'),
            'roof_ridge': ('roof_ridge', f'roof_ridge_{who}'),
            'crossing': ('crossing', f'crossing_{who}'),
        }
        if bp == 'well' and k == 'use':
            kind, nid = 'work', 'work_well'
        elif bp == 'well' and k == 'stand':
            kind, nid = 'wander', 'wander_well'
        elif bp == 'tavern' and mid == 'barkeep':
            kind, nid = 'work', 'work_tavern_bar'
        elif bp == 'plank_bridge' and k == 'stand':
            kind, nid = 'wander', 'wander_bridge'
        elif bp == 'graveyard_gate':
            kind, nid = 'entry', f'entry_graveyard_{mid.replace("gate_", "")}'
        elif k in mapping:
            kind, nid = mapping[k]
        else:
            kind, nid = k, f'{k}_{who}_{mid}'
        self.add_marker(kind, pos, yaw, owner=sid, mid=nid, **extra)

    # ------------------------------------------------------------------ 11. floating cubes past the rim
    def floating_cubes(self):
        W = self.W
        r = rng('float')
        n = 0
        for _ in range(4000):
            if n >= 260:
                break
            a = r.uniform(0, 2 * math.pi)
            dd = r.uniform(1.0, 1.13)
            x = int(CENTRE[0] + ISLAND_R * dd * math.cos(a) * r.uniform(0.98, 1.06))
            z = int(CENTRE[1] + ISLAND_R * dd * math.sin(a) * r.uniform(0.98, 1.06))
            if not (1 <= x < SX - 2 and 1 <= z < SZ - 2) or self.H[x, z] >= 0:
                continue
            # height near the rim's surface, sinking with distance
            y = int(GROUND - 1 - (dd - 1.0) * 70 + r.integers(-5, 3))
            if not (2 <= y < SY - 3):
                continue
            size = 1 if r.random() < 0.6 else 2
            for ax in range(x, x + size):
                for az in range(z, z + size):
                    for ay in range(y, y + (1 if size == 1 else r.integers(1, 3))):
                        if self.H[ax, az] < 0:
                            W[ax, ay, az] = IDX['grass'] if ay == y and r.random() < 0.25 else (
                                IDX['spectral_stone'] if r.random() < 0.3 else IDX['stone'])
            n += 1
        self.floating = n

    # ------------------------------------------------------------------ 12. markers
    def gameplay_markers(self):
        W = self.W
        maus = next(s for s in self.structures if s['id'] == 'mausoleum')
        ent = next(m for m in self.markers if m['id'] == 'entry_mausoleum_front')
        self.add_marker('player_start', ent['pos'], (maus['yaw']) % 360, owner='mausoleum', mid='player_start',
                        note='outside the mausoleum door, facing out toward the village')
        crypt = maus['rooms'][0]
        c = [(crypt['min'][i] + crypt['max'][i]) / 2 for i in range(3)]
        self.add_marker('shelter', (c[0], crypt['min'][1], c[2]), maus['yaw'], owner='mausoleum',
                        mid='shelter_mausoleum', radius=1.5, note='daylight-safe: inside the mausoleum')
        for cid, (fx, fy, fz), pts in self.cave_info:
            self.add_marker('shelter', (fx, fy, fz), 0, owner=cid, mid=f'shelter_{cid}', radius=2.0,
                            note='daylight-safe: cave chamber')
            ex, ey, ez = pts[0][0]
            self.add_marker('cave_entrance', (ex, ey, ez), 0, owner=cid, mid=f'cave_entrance_{cid}')
        # work spots
        sx, sz = SQUARE['c']
        x0, z0, x1, z1 = FIELDS['wheat']
        for k, (x, z) in enumerate(((x0 + 3.5, z0 + 3.5), (x0 + 11.5, z1 - 2.5), (x1 - 3.5, z0 + 6.5))):
            self.add_marker('work', (x, GROUND + 1, z), 90 * k, owner='fields', mid=f'work_field_{k + 1}', job='work_field')
        px0, pz0, px1, pz1 = FIELDS['pumpkins']
        self.add_marker('work', (px0 + 4.5, GROUND + 1, pz0 + 4.0), 0, owner='fields', mid='work_field_pumpkins',
                        job='work_field')
        mill = next(s for s in self.structures if s['id'] == 'windmill')
        mx, my, mz = mill['pivot']
        wx, wz = rot_xz(mill['yaw'], -1.0, 0.4)
        self.add_marker('work', (mx + wx, my, mz + wz), 180, owner='windmill', mid='work_mill', job='millstone')
        self.add_marker('work', (sx + 6.0, GROUND + 1, sz + 0.2), 180, owner='square', mid='work_charm_board',
                        job='hang_charm')
        tav = next(s for s in self.structures if s['id'] == 'tavern')
        tx, ty, tz = tav['pivot']
        ox, oz = rot_xz(tav['yaw'], -2.0, 5.0)
        self.add_marker('work', (tx + ox, ty, tz + oz), tav['yaw'] + 180, owner='tavern', mid='work_tavern_tables',
                        job='serve_drinks')
        # wander points (villager evening strolls)
        for nm, (x, z) in (('square_n', (sx, sz - 7)), ('square_e', (sx + 8, sz + 3)), ('square_w', (sx - 8, sz - 2)),
                           ('square_s', (sx - 1, sz + 8)), ('path_west', (70, 107)), ('path_mill', (106, 70)),
                           ('fields_gate', (142, 102.5)), ('pumpkin_gate', (128, 120.5)),
                           ('south_path', (108.5, 130)), ('mill_terrace', (101, 57.5)), ('stream_bank', (90.5, 96)),
                           ('graveyard_gate_outside', (52, 94.5))):
            self.add_marker('wander', (x, self.surface_y(x, z), z), 0, owner='village', mid=f'wander_{nm}')
        # hiding spots outdoors: beside the bridge abutments, behind the tavern barrels, behind the well,
        # in the wheat, behind the charm board
        for nm, (x, z) in (('bridge_nw', (82.5, 116.2)), ('bridge_se', (89.6, 120.8)), ('tavern_barrels', (101.6, 116.0)),
                           ('well_back', (113.5, 97.4)), ('wheat', (140.5, 112.5)), ('charm_board', (sx + 6.0, sz - 2.0)),
                           ('graveyard_tree', (19.5, 83.5)), ('mill_sacks', (94.0, 57.8))):
            self.add_marker('hiding_spot', (x, self.surface_y(x, z), z), 0, owner='village', mid=f'hiding_spot_{nm}')
        # lantern posts are light sources villagers relight
        # ore nodes: every exposed ore block above a floor (not the underside streaks)
        ore = np.isin(W, [IDX['eerie_ore'], IDX['iron_ore'], IDX['spectral_stone']])
        solid_below = np.maximum.accumulate((W != 0) & ~np.isin(W, [IDX['river_water']]), axis=1)
        k = 0
        for x, y, z in zip(*np.nonzero(ore)):
            b = W[x, y, z]
            if b == IDX['spectral_stone'] and not (y > self.H[x, z] - 3):
                continue   # deep spectral stone is ordinary rock; only surface/cave veins are nodes
            for (dx, dy, dz, yaw) in ((0, 1, 0, 0), (1, 0, 0, 90), (-1, 0, 0, 270), (0, 0, 1, 0), (0, 0, -1, 180)):
                nx, ny, nz = x + dx, y + dy, z + dz
                if not (0 <= nx < SX and 0 < ny < SY and 0 <= nz < SZ):
                    continue
                if W[nx, ny, nz] == 0 and solid_below[nx, ny - 1, nz] and ny > self.bot[nx, nz] + 1:
                    if b == IDX['spectral_stone'] and self.d[x, z] > 0.9:
                        break
                    k += 1
                    self.add_marker('ore_node', (x + 0.5, y, z + 0.5), yaw, owner=self.area_of(x, z),
                                    mid=f'ore_node_{k}', block=BDEF[int(b)]['id'], cell=[int(x), int(y), int(z)],
                                    face=[dx, dy, dz])
                    break

    def area_of(self, x, z):
        for a in sorted(self.areas, key=lambda a: -a['priority']):
            x0, z0, x1, z1 = a['rect']
            if x0 <= x < x1 and z0 <= z < z1:
                return a['id']
        return 'open_plains'

    # ------------------------------------------------------------------ 13. areas
    def build_areas(self):
        A = self.areas
        cx, cz = GRAVE_HILL['c']
        rx, rz = GRAVE_HILL['r']
        A.append(dict(id='graveyard', name='Graveyard', kind='graveyard', rect=[cx - rx - 1, cz - rz - 1, cx + rx + 6, cz + rz + 1],
                      priority=2, remembrance=0.6, consecrated=True))
        sx, sz = SQUARE['c']
        A.append(dict(id='millbrook_square', name='Millbrook Square', kind='village', rect=[sx - 13, sz - 11, sx + 13, sz + 11],
                      priority=2, remembrance=0.8))
        for s in self.structures:
            if s['resident'] or s['id'] == 'tavern':
                x0, z0, x1, z1 = s['footprint']
                name = next(t[5] for t in STRUCTURES if t[1] == s['id'])
                A.append(dict(id=s['id'], name=name, kind='home' if s['resident'] else 'tavern',
                              rect=[x0 - 1, z0 - 1, x1 + 1, z1 + 1], priority=3, resident=s['resident'],
                              remembrance=0.8, interior=s['rooms']))
        mx, mz = MILL_RISE['c']
        A.append(dict(id='windmill_rise', name='Windmill', kind='landmark',
                      rect=[mx - 15, mz - 14, mx + 15, mz + 14], priority=2, remembrance=0.7))
        x0, z0, x1, z1 = FIELDS['wheat']
        px0, pz0, px1, pz1 = FIELDS['pumpkins']
        A.append(dict(id='fields', name='Fields', kind='fields', rect=[min(x0, px0) - 2, z0 - 2, max(x1, px1) + 3, pz1 + 3],
                      priority=1, remembrance=0.7))
        xs = [c[0] for c in self.stream_cells]
        zs = [c[2] for c in self.stream_cells]
        A.append(dict(id='stream', name='Stream', kind='stream', rect=[min(xs) - 3, min(zs), max(xs) + 4, max(zs) + 1],
                      priority=1, remembrance=0.7, note='narrow: test the stream cells, not just the rect'))
        A.append(dict(id='open_plains', name='Open Plains', kind='wilds', rect=[0, 0, SX, SZ], priority=0,
                      remembrance=0.5))
        for a in A:
            a['rect'] = [float(v) for v in a['rect']]
            a.setdefault('y', [0, SY])

    # ------------------------------------------------------------------ run
    def generate(self):
        self.heightmap()
        self.pads()
        self.paths()
        self.fill()
        self.stream()
        self.caves()
        self.graveyard()
        self.village()
        self.vegetation()
        self.stamp_structures()
        self.floating_cubes()
        self.build_areas()
        self.gameplay_markers()
        for inst in self.instances:
            inst['area'] = self.area_of(inst['pos'][0], inst['pos'][2])
        for m in self.markers:
            m['area'] = self.area_of(m['pos'][0], m['pos'][2])
        return self


def STREAM_BANK_AT(z):
    b = STREAM_BANKS[0][1]
    for z0, h in sorted(STREAM_BANKS):
        if z >= z0:
            b = h
    return b


HAUNT_KIND = {
    'door_cottage': 'door', 'door_interior': 'door', 'floorboard': 'floorboard', 'candle': 'candle',
    'candle_cluster': 'candle', 'oil_lamp': 'oil_lamp', 'rocking_chair': 'rocking_chair', 'wardrobe': 'wardrobe',
    'portrait': 'portrait', 'cloth_doll': 'doll', 'scarecrow': 'scarecrow', 'bell': 'bell',
}


# ============================================================================== lighting presets
def _dir(elev, azim):
    """Unit vector the light travels along (Godot axes) for a source at elevation/azimuth (deg).
    Azimuth: 0 = source in the north (-Z), 90 = east (+X), 180 = south, 270 = west."""
    e, a = math.radians(elev), math.radians(azim)
    src = (math.sin(a) * math.cos(e), math.sin(e), -math.cos(a) * math.cos(e))
    return [round(-v, 4) for v in src]


def lighting():
    def light(elev, azim, color, energy, shadows=True):
        return {'elevation_deg': elev, 'azimuth_deg': azim, 'direction': _dir(elev, azim), 'color': color,
                'energy': energy, 'shadows': shadows}
    presets = {
        'night': {
            'desc': 'Play time: deep blue sky, huge soft moon, warm orange windows, low violet mist.',
            'sun': None,
            'moon': light(38, 40, '#b4c2ff', 0.9),
            'ambient': {'color': '#5a5cc4', 'energy': 0.85},
            'sky': {'top': '#0b0a29', 'horizon': '#3d3a7c', 'void': '#140a2a', 'moon_disc': True, 'stars': True},
            'fog': {'color': '#4c4794', 'density': 0.010, 'height_fog': {'y': 21.5, 'falloff': 0.6, 'density': 0.05}},
            'emission': {'windows': True, 'lanterns': True, 'flames': True, 'glow_energy': 1.0},
            'lamps_energy': 1.6, 'saturation': 1.1, 'exposure': 1.3, 'glow_bloom': 0.6, 'fireflies': True},
        'dusk': {
            'desc': 'Lavender and peach sky, long blue shadows, the first candles lit.',
            'sun': light(11, 285, '#ffa774', 1.25),
            'moon': None,
            'ambient': {'color': '#8a66b0', 'energy': 0.85},
            'sky': {'top': '#3a2b6d', 'horizon': '#f3a37d', 'void': '#24123d', 'moon_disc': False, 'stars': False},
            'fog': {'color': '#b98fb3', 'density': 0.007, 'height_fog': {'y': 21.0, 'falloff': 0.5, 'density': 0.03}},
            'emission': {'windows': True, 'lanterns': True, 'flames': True, 'glow_energy': 0.75},
            'lamps_energy': 0.9, 'saturation': 1.08, 'exposure': 1.2, 'glow_bloom': 0.45, 'fireflies': False},
        'dawn': {
            'desc': 'Transition only: pale pink east, candles going out, the living world waking.',
            'sun': light(7, 95, '#ffc6b0', 0.8),
            'moon': None,
            'ambient': {'color': '#9a8ab0', 'energy': 0.55},
            'sky': {'top': '#6a6aa8', 'horizon': '#ffd0c0', 'void': '#3a2a50', 'moon_disc': False, 'stars': False},
            'fog': {'color': '#d8c4d8', 'density': 0.009, 'height_fog': {'y': 21.0, 'falloff': 0.5, 'density': 0.05}},
            'emission': {'windows': False, 'lanterns': True, 'flames': True, 'glow_energy': 0.4},
            'lamps_energy': 0.4, 'saturation': 0.95, 'exposure': 1.05, 'glow_bloom': 0.3, 'fireflies': False},
        'day': {
            'desc': 'Living world bleeds through: pale, washed-out, slightly overexposed and hazy; daylight drains the ghost.',
            'sun': light(52, 150, '#fff3df', 1.05),
            'moon': None,
            'ambient': {'color': '#c9d0ea', 'energy': 0.95},
            'sky': {'top': '#9cb3dc', 'horizon': '#ece6f3', 'void': '#8a7aa8', 'moon_disc': False, 'stars': False},
            'fog': {'color': '#e9e5f2', 'density': 0.006, 'height_fog': None},
            'emission': {'windows': False, 'lanterns': False, 'flames': True, 'glow_energy': 0.0},
            'lamps_energy': 0.25, 'saturation': 0.68, 'exposure': 1.06, 'glow_bloom': 0.15, 'fireflies': False},
        'fading': {
            'desc': 'Low Remembrance: colours drained toward grey, edges crumbling into floating cubes, a starless void.',
            'sun': None,
            'moon': light(45, 30, '#d2cfe2', 0.75),
            'ambient': {'color': '#a49dc2', 'energy': 1.05},
            'sky': {'top': '#77729a', 'horizon': '#bdb4d4', 'void': '#1a1024', 'moon_disc': False, 'stars': False},
            'fog': {'color': '#8a80a8', 'density': 0.016, 'height_fog': {'y': 22.0, 'falloff': 0.4, 'density': 0.06}},
            'emission': {'windows': True, 'lanterns': True, 'flames': True, 'glow_energy': 0.55},
            'lamps_energy': 0.6, 'saturation': 0.38, 'exposure': 1.3, 'glow_bloom': 0.3, 'fireflies': False,
            'crumble': True, 'void_edge_glow': '#9a5cff'},
    }
    cycle = {
        'tuning': True,
        'length_s': 1200,
        'start_t': 0.04,
        'note': 'Inverted day: night is the ghost\'s working time, so it gets half the cycle. t in [0, 1); Godot '
                'blends the two presets around t. hour is the nominal clock shown on the HUD moon clock.',
        'keys': [
            {'t': 0.00, 'hour': 18.5, 'preset': 'dusk'},
            {'t': 0.08, 'hour': 20.0, 'preset': 'night'},
            {'t': 0.58, 'hour': 4.5, 'preset': 'night'},
            {'t': 0.64, 'hour': 6.0, 'preset': 'dawn'},
            {'t': 0.70, 'hour': 7.5, 'preset': 'day'},
            {'t': 0.94, 'hour': 17.0, 'preset': 'day'},
            {'t': 1.00, 'hour': 18.5, 'preset': 'dusk'},
        ],
        'phases': {'dusk': [0.94, 0.08], 'night': [0.08, 0.58], 'dawn': [0.58, 0.70], 'day': [0.70, 0.94]},
    }
    return presets, cycle


# ============================================================================== output
def write(isl, out_dir=None):
    out_dir = out_dir or os.path.join(ROOT, 'assets', 'levels')
    os.makedirs(out_dir, exist_ok=True)
    W = isl.W
    # x fastest, then z, then y: W[x, y, z] -> transpose to [y, z, x] then C-order flatten
    raw = np.ascontiguousarray(W.transpose(1, 2, 0)).tobytes()
    bin_path = os.path.join(out_dir, 'millbrook_voxels.bin')
    with open(bin_path, 'wb') as f:
        f.write(gzip.compress(raw, compresslevel=9, mtime=0))
    counts = {BDEF[int(i)]['id']: int(c) for i, c in zip(*np.unique(W, return_counts=True))}
    presets, cycle = lighting()
    spawn = next(m for m in isl.markers if m['kind'] == 'player_start')
    sq = next(m for m in isl.markers if m['id'] == 'wander_square_n')
    doc = {
        'name': 'millbrook', 'version': 1, 'generator': 'blender/scripts/build_island.py (lib_island.py)',
        'units': 'metres; 1 block = 1 m; Godot axes: x east, y up, z south; yaw = Godot rotation.y in degrees',
        'world': {
            'size': [SX, SY, SZ], 'chunk_size': CHUNK, 'chunks': [SX // CHUNK, SY // CHUNK, SZ // CHUNK],
            'seed': SEED, 'origin': [0, 0, 0], 'void_level': 0, 'surface_y': GROUND + 1,
            'playable_y': [16, 30],
            'voxels': {'path': 'res://assets/levels/millbrook_voxels.bin', 'encoding': 'gzip',
                       'order': 'x fastest, then z, then y: index = x + sx * (z + sz * y)', 'cell_type': 'u8',
                       'bytes': len(raw), 'blocks': 'res://assets/blocks/blocks.json'},
            'palette': [BDEF[i]['id'] if i in BDEF else None for i in range(max(BDEF) + 1)],
            'block_counts': counts,
            'island': {'centre': list(CENTRE), 'radius': ISLAND_R, 'floating_cubes': isl.floating},
        },
        'kill_y': -16.0,
        'spawn': {'player_start': spawn['pos'], 'yaw': spawn['yaw']},
        'distances': {'graveyard_to_square_path_m': round(isl.path_len, 1),
                      'drift_time_s_at_2_2mps': round(isl.path_len / 2.2, 1),
                      'square_marker': sq['pos']},
        'structures': isl.structures,
        'instances': isl.instances,
        'markers': isl.markers,
        'areas': isl.areas,
        'water': isl.water,
        'lighting': {'default': 'night', 'presets': presets, 'cycle': cycle},
        'map': {'world_rect': [0.0, 0.0, float(SX), float(SZ)], 'axes': 'image x -> world +x (east), image y -> world +z (south)',
                'plan_render': 'renders/task3/millbrook_plan.png', 'image': None,
                'note': 'Orthographic top-down plan of the whole world rect; base for the painted in-game map.'},
    }
    with open(os.path.join(out_dir, 'millbrook_layout.json'), 'w') as f:
        json.dump(doc, f, indent=1)
    return doc


def path_length():
    """Graveyard door -> square centre along the PATHS polylines used for the drift-time check."""
    L = 0.0
    for block, w, pts in PATHS[:3]:
        for a, b in zip(pts, pts[1:]):
            L += math.hypot(b[0] - a[0], b[1] - a[1])
    L += math.hypot(SQUARE['c'][0] - 106, SQUARE['c'][1] - 108) + 6.0   # bridge span + square
    return L


def build():
    isl = Island().generate()
    isl.path_len = path_length()
    return isl


if __name__ == '__main__':
    import time
    t = time.time()
    isl = build()
    doc = write(isl)
    print('instances', len(isl.instances), 'markers', len(isl.markers), 'areas', len(isl.areas),
          'stream cells', len(isl.stream_cells), 'floating', isl.floating, 'path', round(isl.path_len, 1),
          'time', round(time.time() - t, 1))
