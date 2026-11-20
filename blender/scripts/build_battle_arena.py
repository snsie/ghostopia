"""Battle prototype arena: one flat cavern region at the Sunken Ford (placeholder geometry).

A 128 x 32 x 128 voxel cavern: stone floor, irregular walls, a ceiling with stalactites, a few pillars,
an underground river running east-west across the middle (running water: spirits can't cross) and one
shallow stone ford (still water) where the Barrow Host can cross. A Memory Vein glows in the ford bed
and the ceiling above it. The Drowned Parish holds the north bank with a bell tower behind its lines;
the Barrow Host holds the south bank. Each side has a tunnel mouth home where routing units flee.

Writes:
  assets/levels/sunken_ford_layout.json      world, markers (player start, bell, throwables, lights)
  assets/levels/sunken_ford_voxels.bin       gzip uint8 block indices, x fastest, then z, then y
  assets/levels/sunken_ford_population.json  the two clans: unit model, count, formation, home, colours

Godot axes: x east, y up, z south. 1 block = 1 m.

Run:  blender -b --factory-startup -P blender/scripts/build_battle_arena.py
      (or plain `python blender/scripts/build_battle_arena.py`; it only needs numpy)
"""
import gzip
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
LEVELS = os.path.join(ROOT, 'assets', 'levels')

SX, SY, SZ = 128, 32, 128
FLOOR = 7            # standing height: the top floor block is y = 6
CEIL = 24            # first ceiling block
RIVER_Z = (58, 66)   # running water rows [z0, z1)
FORD_X = (50, 78)    # the ford columns [x0, x1)
SEED = 20261119


def block_ids():
    data = json.load(open(os.path.join(ROOT, 'assets', 'blocks', 'blocks.json')))
    return {b['id']: b['index'] for b in data['blocks']}


def value_noise(rng, cells, scale):
    """Smooth 2D noise in [0, 1] on a SX x SZ grid from a coarse random lattice."""
    gx, gz = SX // scale + 2, SZ // scale + 2
    lat = rng.random((gz, gx))
    xs = np.arange(SX) / scale
    zs = np.arange(SZ) / scale
    x0 = np.floor(xs).astype(int)
    z0 = np.floor(zs).astype(int)
    fx = xs - x0
    fz = zs - z0
    fx = fx * fx * (3 - 2 * fx)
    fz = fz * fz * (3 - 2 * fz)
    a = lat[np.ix_(z0, x0)]
    b = lat[np.ix_(z0, x0 + 1)]
    c = lat[np.ix_(z0 + 1, x0)]
    d = lat[np.ix_(z0 + 1, x0 + 1)]
    top = a + (b - a) * fx[None, :]
    bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fz[:, None]   # [z, x]


def build():
    ids = block_ids()
    rng = np.random.default_rng(SEED)
    vox = np.zeros((SY, SZ, SX), dtype=np.uint8)   # [y, z, x]
    stone, dirt, moss = ids['stone'], ids['dirt'], ids['grave_moss']
    sand, cobble, bricks = ids['sand'], ids['cobblestone'], ids['mossy_stone_bricks']
    river, still, ore = ids['river_water'], ids['still_water'], ids['eerie_ore']

    # bedrock and floor
    vox[:FLOOR, :, :] = stone
    n1 = value_noise(rng, None, 9)
    n2 = value_noise(rng, None, 5)
    top = np.full((SZ, SX), stone, dtype=np.uint8)
    top[(n1 > 0.55)] = dirt
    north = np.arange(SZ)[:, None] < RIVER_Z[0]
    north = np.broadcast_to(north, (SZ, SX))
    top[(n2 > 0.62) & north] = sand          # silt on the Parish bank
    top[(n2 > 0.60) & ~north] = moss         # barrow moss on the south bank
    vox[FLOOR - 1] = top

    # ceiling with stalactites
    vox[CEIL:, :, :] = stone
    for _ in range(170):
        x, z = int(rng.integers(4, SX - 4)), int(rng.integers(4, SZ - 4))
        length = int(rng.integers(1, 6))
        vox[CEIL - length:CEIL, z, x] = stone
        if length > 3:
            for dx, dz in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                vox[CEIL - length + 2:CEIL, z + dz, x + dx] = stone

    # irregular cavern walls (3-7 blocks thick)
    wall_n = value_noise(rng, None, 7)
    for z in range(SZ):
        for x in range(SX):
            edge = min(x, z, SX - 1 - x, SZ - 1 - z)
            thick = 3 + int(wall_n[z, x] * 4.5)
            if edge < thick:
                vox[FLOOR:CEIL, z, x] = stone

    # home tunnels: north (Parish) and south (Barrow), 12 wide
    homes = {
        'parish': {'rect': [56, 0, 72, 5], 'tunnel_x': [56, 72], 'side': 'north'},
        'barrow': {'rect': [56, SZ - 5, 72, SZ], 'tunnel_x': [56, 72], 'side': 'south'},
    }
    for x in range(56, 72):
        for z in range(0, 12):
            vox[FLOOR:FLOOR + 6, z, x] = 0
        for z in range(SZ - 12, SZ):
            vox[FLOOR:FLOOR + 6, z, x] = 0
    vox[FLOOR - 1, 0:12, 56:72] = cobble
    vox[FLOOR - 1, SZ - 12:SZ, 56:72] = cobble

    # the river: two blocks deep, running east-west
    z0, z1 = RIVER_Z
    vox[FLOOR - 3, z0:z1, :] = stone
    vox[FLOOR - 2:FLOOR, z0:z1, :] = river
    # banks: a line of bricks
    for z in (z0 - 1, z1):
        vox[FLOOR - 1, z, 4:SX - 4] = bricks
    # the ford: still water over a cobble bed, with flush stepping stones and the vein
    fx0, fx1 = FORD_X
    vox[FLOOR - 2, z0:z1, fx0:fx1] = cobble
    vox[FLOOR - 1, z0:z1, fx0:fx1] = still
    for z in range(z0, z1):
        for x in range(fx0, fx1):
            if (x * 7 + z * 3) % 9 == 0:
                vox[FLOOR - 1, z, x] = bricks
            if abs(z - (z0 + z1) / 2 + 0.5) < 0.6 and x % 3 != 0:
                vox[FLOOR - 2, z, x] = ore
    # the Memory Vein: a glowing seam in the ceiling above the ford
    for x in range(fx0 - 6, fx1 + 6):
        zc = (z0 + z1) / 2 + 3.0 * math.sin(x * 0.21)
        for dz in (-1, 0, 1):
            z = int(round(zc + dz))
            if rng.random() < 0.8:
                vox[CEIL, z, x] = ore

    # pillars that split the battle line (flanks)
    pillars = [(34, 46), (94, 47), (30, 80), (98, 79), (64, 32), (64, 94)]
    for px, pz in pillars:
        r = 2.2
        for z in range(pz - 3, pz + 4):
            for x in range(px - 3, px + 4):
                if (x - px) ** 2 + (z - pz) ** 2 <= r * r:
                    vox[FLOOR:CEIL, z, x] = stone

    # the Parish bell tower (north, behind the lines)
    bx, bz = 64, 13
    for y in range(FLOOR, FLOOR + 9):
        for z in range(bz - 2, bz + 3):
            for x in range(bx - 2, bx + 3):
                shell = max(abs(x - bx), abs(z - bz)) == 2
                if shell or y == FLOOR + 8:
                    if not (y >= FLOOR + 5 and y < FLOOR + 8 and abs(x - bx) < 2 and z > bz):
                        vox[y, z, x] = cobble
    vox[FLOOR + 9, bz - 2:bz + 3, bx - 2:bx + 3] = 0
    for x, z in ((bx - 2, bz - 2), (bx + 2, bz - 2), (bx - 2, bz + 2), (bx + 2, bz + 2)):
        vox[FLOOR + 9:FLOOR + 12, z, x] = cobble
    vox[FLOOR + 12, bz - 2:bz + 3, bx - 2:bx + 3] = cobble

    # the Barrow mound (south, behind the lines): a low earthen hump with a bronze lantern on it
    mx, mz = 64, 112
    for z in range(mz - 6, mz + 7):
        for x in range(mx - 9, mx + 10):
            h = 2.6 - math.hypot((x - mx) / 9.0, (z - mz) / 6.0) * 2.6
            for y in range(int(math.ceil(h))):
                vox[FLOOR + y, z, x] = moss if y == int(math.ceil(h)) - 1 else dirt

    return vox, ids, homes, pillars, (bx, bz), (mx, mz)


def main():
    vox, ids, homes, pillars, bell, mound = build()
    os.makedirs(LEVELS, exist_ok=True)
    raw = vox.tobytes()   # [y][z][x] with x fastest: index = x + SX * (z + SZ * y)
    with open(os.path.join(LEVELS, 'sunken_ford_voxels.bin'), 'wb') as fh:
        fh.write(gzip.compress(raw, 9))
    rng = np.random.default_rng(SEED + 1)
    throwables = []
    for bank_z in ((48, 55), (69, 76)):
        for _ in range(7):
            for _try in range(50):
                x = float(rng.uniform(40, 88))
                z = float(rng.uniform(*bank_z))
                if all(math.hypot(x - t['pos'][0], z - t['pos'][2]) > 4.5 for t in throwables):
                    break
            throwables.append({'kind': 'throwable', 'id': 'boulder_%d' % len(throwables),
                               'pos': [round(x, 2), float(FLOOR), round(z, 2)], 'radius': 0.45})
    lights = []
    for x in range(20, 112, 14):
        lights.append({'kind': 'light', 'style': 'votive', 'pos': [x + 0.5, FLOOR + 0.4, 50.5], 'color': '#ffad5c', 'range': 9.0, 'energy': 1.1})
        lights.append({'kind': 'light', 'style': 'bronze_lantern', 'pos': [x + 7.5, FLOOR + 1.6, 76.5], 'color': '#ffc46b', 'range': 9.0, 'energy': 1.1})
    for x in range(48, 82, 8):
        lights.append({'kind': 'light', 'style': 'vein', 'pos': [x + 0.5, FLOOR + 1.0, 62.0], 'color': '#b38cff', 'range': 11.0, 'energy': 1.4})
    lights.append({'kind': 'light', 'style': 'votive', 'pos': [bell[0] + 0.5, FLOOR + 10.5, bell[1] + 0.5], 'color': '#ffad5c', 'range': 12.0, 'energy': 1.6})
    lights.append({'kind': 'light', 'style': 'bronze_lantern', 'pos': [mound[0] + 0.5, FLOOR + 4.0, mound[1] + 0.5], 'color': '#ffc46b', 'range': 14.0, 'energy': 1.6})
    layout = {
        'name': 'sunken_ford_arena',
        'version': 1,
        'generator': 'blender/scripts/build_battle_arena.py',
        'units': 'metres; 1 block = 1 m; Godot axes: x east, y up, z south',
        'note': 'Battle prototype arena (placeholder geometry). Not part of the Millbrook slice.',
        'world': {
            'size': [SX, SY, SZ], 'chunk_size': 16, 'floor_y': FLOOR, 'ceiling_y': CEIL,
            'voxels': {'path': 'res://assets/levels/sunken_ford_voxels.bin', 'encoding': 'gzip',
                       'order': 'x fastest, then z, then y: index = x + sx * (z + sz * y)'},
        },
        'river': {'z': list(RIVER_Z), 'ford_x': list(FORD_X), 'block': 'river_water', 'running_water': True,
                  'ford_block': 'still_water'},
        'kill_y': -8.0,
        'spawn': {'player_start': [64.0, FLOOR + 0.2, 52.0], 'yaw': 180.0},
        'markers': [
            {'kind': 'bell', 'id': 'parish_bells', 'pos': [bell[0] + 0.5, FLOOR + 9.0, bell[1] + 0.5],
             'clan': 'drowned_parish', 'haunt_range_m': 9.0},
            {'kind': 'vein', 'id': 'sunken_ford_vein', 'pos': [64.0, FLOOR, 62.0]},
            {'kind': 'mound', 'id': 'barrow_mound', 'pos': [mound[0] + 0.5, FLOOR + 2.6, mound[1] + 0.5]},
        ] + throwables + lights,
        'pillars': [[p[0], p[1]] for p in pillars],
    }
    with open(os.path.join(LEVELS, 'sunken_ford_layout.json'), 'w') as fh:
        json.dump(layout, fh, indent=1)
    population = {
        'name': 'sunken_ford_battle',
        'generator': 'blender/scripts/build_battle_arena.py',
        'note': 'Two clans of about 500 each for the battle-fun gate. Formation rects are [x0, z0, x1, z1].',
        'clans': [
            {'id': 'drowned_parish', 'name': 'Drowned Parish', 'unit': 'parish_soldier', 'count': 500,
             'formation': {'rect': [34, 20, 94, 46], 'spacing_m': 1.15, 'facing_yaw': 0.0},
             'home': homes['parish'], 'color': '#ffad5c', 'tint': '#7fb5c4',
             'water_walker': True, 'fear': 'silence', 'fear_object': 'parish_bells'},
            {'id': 'barrow_host', 'name': 'Barrow Host', 'unit': 'barrow_warrior', 'count': 500,
             'formation': {'rect': [34, 78, 94, 104], 'spacing_m': 1.15, 'facing_yaw': 180.0},
             'home': homes['barrow'], 'color': '#ffc46b', 'tint': '#c49a6a',
             'water_walker': False, 'fear': 'namelessness', 'fear_object': None},
        ],
    }
    with open(os.path.join(LEVELS, 'sunken_ford_population.json'), 'w') as fh:
        json.dump(population, fh, indent=1)
    solid = int((vox != 0).sum())
    print('ARENA %dx%dx%d, %d solid cells, %d throwables, %d lights' % (SX, SY, SZ, solid, len(throwables), len(lights)))


if __name__ == '__main__':
    main()
