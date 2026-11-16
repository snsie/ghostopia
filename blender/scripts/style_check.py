"""Style check: blocks, a cottage, the well, the mausoleum and props in one small scene, every mood.

blender -b --factory-startup -P blender/scripts/style_check.py
-> renders/task1/style_check_{day,dusk,night}.png  (compare with concept/locations/millbrook_*.png)
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_render as LR  # noqa: E402
import lib_voxel as LV  # noqa: E402

ROOT = LV.ROOT
SX, SY, SZ = 44, 16, 34
GROUND = 4  # top terrain layer index; first air layer = GROUND + 1


def stamp(world, name, ax, az, ay=GROUND + 1):
    """Stamp blueprint `name` so its origin cell lands on world cell (ax, ay, az). Returns (doc, offset)."""
    with open(os.path.join(ROOT, 'assets', 'structures', name + '.json')) as f:
        doc = json.load(f)
    a = LV.decode_rle(doc['size'], doc['palette'], doc['rle'])
    ox, oy, oz = doc['origin']
    sx, sy, sz = a.shape
    for x in range(sx):
        for y in range(sy):
            for z in range(sz):
                b = a[x, y, z]
                if b == '_skip':
                    continue
                wx, wy, wz = ax + x - ox, ay + y - oy, az + z - oz
                if 0 <= wx < SX and 0 <= wy < SY and 0 <= wz < SZ:
                    world[wx, wy, wz] = b
    return doc


def terrain():
    w = np.full((SX, SY, SZ), 'air', dtype=object)
    rng = np.random.default_rng(3)
    w[:, :GROUND - 1, :] = 'stone'
    w[:, GROUND - 1, :] = 'dirt'
    w[:, GROUND, :] = 'grass'
    # graveyard hill (west/back): raised 3 blocks with stone cliffs and grave moss on top
    for x in range(0, 15):
        for z in range(0, 14):
            h = 3 if (x < 13 and z < 12) else 2
            for y in range(GROUND + 1, GROUND + 1 + h):
                w[x, y, z] = 'stone'
            w[x, GROUND + h, z] = 'grave_moss' if rng.random() < 0.9 else 'grave_dirt'
    # eerie ore + spectral stone vein in the cliff face
    for (x, y, z, b) in ((13, GROUND + 2, 6, 'eerie_ore'), (13, GROUND + 1, 7, 'eerie_ore'), (12, GROUND + 1, 12, 'spectral_stone'),
                         (13, GROUND + 1, 4, 'iron_ore'), (14, GROUND + 1, 9, 'spectral_stone')):
        w[x, y, z] = b
    # stream along z on the east, sand banks, running water one below the banks
    for z in range(SZ):
        cx = 33 + int(1.5 * math.sin(z * 0.25))
        for x in range(cx - 1, cx + 2):
            w[x, GROUND, z] = 'river_water'
            w[x, GROUND - 1, z] = 'river_water'
            w[x, GROUND - 2, z] = 'sand'
        for x in (cx - 2, cx + 2):
            w[x, GROUND, z] = 'sand'
    # cobbled path / packed path
    for x in range(14, 40):
        z = 24
        for dz in (0, 1):
            w[x, GROUND, z + dz] = 'cobble_path' if x < 30 else 'packed_path'
    for z in range(12, 24):
        w[18, GROUND, z] = 'packed_path'
        w[19, GROUND, z] = 'packed_path'
    # field: wheat east of the stream
    for x in range(37, 43):
        for z in range(4, 14):
            w[x, GROUND, z] = 'dirt'
            w[x, GROUND + 1, z] = 'wheat'
    # tall grass + flowers scattered
    for _ in range(70):
        x, z = rng.integers(0, SX), rng.integers(0, SZ)
        if w[x, GROUND, z] in ('grass', 'grave_moss'):
            y = GROUND + 1
            while y < SY - 1 and w[x, y, z] != 'air':
                y += 1
            if w[x, y - 1, z] in ('grass', 'grave_moss'):
                w[x, y, z] = 'tall_grass' if rng.random() < 0.6 else 'flowers'
    # a voxel oak
    for y in range(GROUND + 1, GROUND + 5):
        w[27, y, 30] = 'oak_log'
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(0, 3):
                if abs(dx) + abs(dz) + dy < 5:
                    w[27 + dx, GROUND + 5 + dy, 30 + dz] = 'leaves'
    return w


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    world = terrain()
    placed = []
    placed.append(('mausoleum', stamp(world, 'mausoleum', 6, 5, GROUND + 4), (6, GROUND + 4, 5)))
    placed.append(('cottage_a', stamp(world, 'cottage_a', 23, 17), (23, GROUND + 1, 17)))
    placed.append(('well', stamp(world, 'well', 22, 27), (22, GROUND + 1, 27)))
    placed.append(('plank_bridge', None, None))
    # bridge across the stream at z=25 (stream runs along z, so the bridge is rotated 90 deg)
    cx = 33 + int(1.5 * math.sin(25 * 0.25))
    for x in range(cx - 3, cx + 4):
        for z in (24, 25):
            world[x, GROUND, z] = 'timber_planks'
    coll = bpy.data.collections.new('STYLE')
    bpy.context.scene.collection.children.link(coll)
    vox = LV.build_voxel_mesh('style_voxels', world, (0, 0, 0), coll)
    vox.location = (0, 0, -GROUND - 1)  # world cell y=GROUND+1 bottom at z=0

    # props from the stamped blueprints
    lib = bpy.data.collections.new('LIB')
    bpy.context.scene.collection.children.link(lib)
    lib.hide_render = True
    cache = {}

    def load(name):
        if name in cache:
            return cache[name]
        path = os.path.join(ROOT, 'assets', 'props', name + '.gltf')
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path, export_import_convert_lighting_mode='RAW')
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            lib.objects.link(o)
            if o.type == 'LIGHT':
                o.data.energy *= 30.0
            if o.name.startswith('HAUNT_') or o.name.endswith('-colonly'):
                o.hide_render = True
        cache[name] = [o for o in new if o.parent is None][0]
        return cache[name]

    def inst(name, gx, gy, gz, yaw=0.0):
        """Godot-space metres in the world grid frame (cell centre x+0.5 ...), yaw deg."""
        root = load(name)

        def dup(o, parent):
            c = o.copy()
            coll.objects.link(c)
            c.parent = parent
            if parent is not None:
                c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
            for ch in o.children:
                dup(ch, c)
            return c
        r = dup(root, None)
        r.location = (gx - 0.5, -(gz - 0.5), gy - GROUND - 1)
        r.rotation_euler = (0, 0, math.radians(yaw))

    for name, doc, anchor in placed:
        if doc is None:
            continue
        ax, ay, az = anchor
        for p in doc['props']:
            x, y, z = p['pos']
            inst(p['prop'], ax + 0.5 + x, ay + y, az + 0.5 + z, p['yaw'])
    # graveyard dressing on the hill (top at GROUND+4)
    hill = GROUND + 4
    for (x, z, n, yaw) in ((2.5, 9.5, 'gravestone_spiral', 10), (4.5, 10.5, 'gravestone_round', -8),
                           (10.5, 10.5, 'gravestone_cross', 5), (11.5, 3.5, 'gravestone_celtic', -15),
                           (2.5, 4.5, 'dead_tree', 30), (12.5, 8.5, 'eerie_crystal_cluster', 0),
                           (9.0, 12.5, 'candle_cluster', 0), (3.5, 12.0, 'wilted_flowers', 0),
                           (8.5, 1.5, 'mushroom', 0), (1.5, 12.8, 'weed_clump', 0), (11.0, 12.0, 'dirt_mound', 0)):
        inst(n, x, hill, z, yaw)
    for k in range(6):
        inst('fence_wood', 1.0 + k, hill, 13.4, 0)
    # village dressing
    for (x, z, n, yaw) in ((21.0, 23.0, 'lantern_post', 0), (29.0, 23.0, 'lantern_post', 180),
                           (26.5, 26.5, 'notice_board', -20), (16.0, 22.5, 'barrel', 0), (16.8, 22.4, 'crate', 15),
                           (38.5, 15.0, 'scarecrow', -30), (36.0, 17.0, 'pumpkin', 0), (37.0, 18.0, 'pumpkin_small', 0),
                           (35.5, 18.5, 'pumpkin_vine', 0), (37.2, 16.6, 'pumpkin_vine', 40),
                           (30.5, 21.5, 'tree_oak', 0), (19.0, 29.5, 'bench', 0)):
        inst(n, x, GROUND + 1, z, yaw)
    for k in range(8):
        inst('fence_wood', 37.0 + k * 1.0, GROUND + 1, 3.4, 0)

    LR.setup_scene(res=(1672, 941), samples=32, line=1.1)
    objs = [vox]
    for mood in ('day', 'dusk', 'night'):
        LR.set_mood(mood)
        LR.frame_camera(objs, direction=(-0.35, -1.0, 0.85), margin=0.98)
        LR.render(os.path.join(ROOT, 'renders', 'task1', f'style_check_{mood}.png'))
    # close view on the village corner (cottage, well, path) at night, like millbrook_night.png
    near = [o for o in coll.objects if o.type == 'MESH' and not o.hide_render and o is not vox and
            18 <= o.matrix_world.translation.x <= 32 and -30 <= o.matrix_world.translation.y <= -14]
    LR.set_mood('night')
    LR.frame_camera(near, direction=(-0.35, -1.0, 0.7), margin=1.0)
    LR.render(os.path.join(ROOT, 'renders', 'task1', 'style_check_night_close.png'))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'style_check.blend'), compress=True)
    print('DONE')


main()
