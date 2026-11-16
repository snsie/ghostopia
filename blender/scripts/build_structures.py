"""Voxel structure blueprints -> assets/structures/<name>.json (+ previews, blender/structures.blend).

blender -b --factory-startup -P blender/scripts/build_structures.py -- [--only cottage_a,well] [--no-render]
(the JSON part also runs in plain Python: python blender/scripts/build_structures.py --json-only)

Grid axes = Godot axes (x east, y up, z south = front). Format: see decisions.md "Structure blueprints".
Placement coordinates below are "cell-centre" floats: cell i spans [i-0.5, i+0.5]; metres = c - origin.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_voxel as LV  # noqa: E402

ROOT = LV.ROOT
OUT = os.path.join(ROOT, 'assets', 'structures')


class Bp:
    """Blueprint under construction."""

    def __init__(self, name, sx, sy, sz, origin, desc=''):
        self.name = name
        self.g = LV.Grid(sx, sy, sz)
        self.origin = origin  # (ox, oy, oz) cell indices
        self.props = []
        self.markers = []
        self.rooms = []
        self.desc = desc

    # cell-centre coords -> metres relative to the pivot (Godot axes)
    def m(self, x, y, z):
        ox, oy, oz = self.origin
        return [round(x - ox, 3), round(y, 3), round(z - oz, 3)]

    def prop(self, name, x, y, z, yaw=0, tags=None):
        """x, z cell-centre coords; y metres above the floor/ground (0 = ground at the pivot)."""
        self.props.append({'prop': name, 'gltf': f'res://assets/props/{name}.gltf', 'pos': self.m(x, y, z),
                           'yaw': yaw, 'tags': tags or []})

    def marker(self, kind, x, y, z, yaw=0, id_=None, **extra):
        d = {'kind': kind, 'id': id_ or f'{kind}_{len(self.markers)}', 'pos': self.m(x, y, z), 'yaw': yaw}
        d.update(extra)
        self.markers.append(d)

    def room(self, name, x0, x1, z0, z1, h):
        """Room AABB from cell ranges (inclusive) -> metres."""
        lo = self.m(x0 - 0.5, 0, z0 - 0.5)
        hi = self.m(x1 + 0.5, h, z1 + 0.5)
        self.rooms.append({'name': name, 'min': lo, 'max': hi})

    def to_json(self):
        palette, rle = self.g.to_json()
        return {'name': self.name, 'version': 1, 'desc': self.desc, 'size': list(self.g.size),
                'origin': list(self.origin), 'palette': palette, 'rle': rle,
                'props': self.props, 'markers': self.markers, 'rooms': self.rooms}


# ----------------------------------------------------------------------------- cottage / tavern generator
def house(name, W, D, wall_h=4, roof='thatch', pitch=1, chimney='left', stone_courses=1, brace=False,
          partition=None, part_door_z=None, door_x=None, front_windows=(), back_windows=(), left_windows=(),
          right_windows=(), gable_window=False, desc=''):
    """Timber-framed house. Walls x in [1, W], z in [1, D]; roof overhangs one block all round.

    partition: cell x of an interior wall (two rooms) or None. Returns (bp, info dict).
    """
    sx, sz = W + 2, D + 2
    half = (sz - 1) / 2
    n_layers = int(math.floor(half * pitch)) + 1
    roof_top = wall_h + 1 + n_layers
    sy = 1 + roof_top + 3
    ox, oz = sx // 2, sz // 2
    bp = Bp(name, sx, sy, sz, (ox, 1, oz), desc)
    g = bp.g
    Y0 = 1  # first layer above ground
    top = Y0 + wall_h - 1  # top plate layer
    roof_mat = 'thatch' if roof == 'thatch' else 'slate_roof'
    # foundation + floor
    g.box(1, 0, 1, W, 0, D, 'cobblestone')
    g.box(2, 0, 2, W - 1, 0, D - 1, 'timber_planks')
    # interior air (walls fill over it)
    g.box(1, Y0, 1, W, sy - 1, D, 'air')
    # walls
    for y in range(Y0, top + 1):
        for x in range(1, W + 1):
            for z in range(1, D + 1):
                if not (x in (1, W) or z in (1, D)):
                    continue
                corner = x in (1, W) and z in (1, D)
                along = x if z in (1, D) else z
                if y < Y0 + stone_courses:
                    b = 'cobblestone'
                elif y == top:
                    b = 'timber_beam'
                elif corner or along % 3 == 1:
                    b = 'timber_beam'
                else:
                    b = 'plaster_brace' if (brace and y == top - 1 and along % 3 == 2) else 'plaster_wall'
                g.set(x, y, z, b)
    # partition wall
    if partition:
        for y in range(Y0, top + 1):
            for z in range(2, D):
                g.set(partition, y, z, 'timber_beam' if (y == top or z % 3 == 1) else 'plaster_wall')
    # roof: ridge along x, slopes front/back, 2-thick stair so it is closed
    for k in range(n_layers + 1):
        y = top + 1 + k
        zf = int(k / pitch)
        zb = sz - 1 - zf
        if zf > zb:
            break
        for x in range(0, sx):
            for z in (zf, zf + 1, zb, zb - 1):
                if 0 <= z < sz and zf <= z <= zb:
                    g.set(x, y, z, roof_mat)
        # everything strictly outside the slopes at this layer: leave world untouched
        for x in range(0, sx):
            for z in range(0, sz):
                if z < zf or z > zb:
                    g.set(x, y, z, '_skip')
        # gable walls (fill between slopes at x=1 and x=W)
        for x in (1, W):
            for z in range(zf + 2, zb - 1):
                g.set(x, y, z, 'timber_beam' if z == (sz - 1) // 2 or z == sz // 2 else 'plaster_wall')
    ridge_y = top + 1 + n_layers
    # clear above the roof
    for y in range(ridge_y + 1, sy):
        g.box(0, y, 0, sx - 1, y, sz - 1, '_skip')
    # ground-level ring outside the walls (under the eaves) is left alone
    for y in range(0, top + 1):
        for x in range(0, sx):
            for z in range(0, sz):
                if x in (0, sx - 1) or z in (0, sz - 1):
                    g.set(x, y, z, '_skip')
    # chimney
    cz = (D + 1) // 2 + 0
    cx = 1 if chimney == 'left' else W
    out_x = 0 if chimney == 'left' else W + 1
    for y in range(0, ridge_y + 2):
        g.set(cx, y, cz, 'cobblestone')
    for y in range(Y0, top + 1):
        g.set(out_x, y, cz, 'cobblestone')
    g.set(cx, ridge_y + 2, cz, '_skip')
    # door + windows
    door_x = door_x if door_x is not None else (W + 1) // 2
    for y in (Y0, Y0 + 1):
        g.set(door_x, y, D, 'air')
    bp.prop('door_cottage', door_x, 0, D, 0, ['door', 'hauntable'])
    bp.marker('entry', door_x, 0, D + 1.2, 180, 'entry_front')
    bp.marker('door', door_x, 0, D, 0, 'door_front')
    win = []
    for x in front_windows:
        win.append((x, D, 0))
    for x in back_windows:
        win.append((x, 1, 180))
    for z in left_windows:
        win.append((1, z, -90))
    for z in right_windows:
        win.append((W, z, 90))
    for i, (x, z, yaw) in enumerate(win):
        g.set(x, Y0 + 1, z, 'air')
        bp.prop('window_cottage', x, 1.0, z, yaw, ['window', 'glow'])
        bp.marker('window', x, 1.0, z, yaw, f'window_{i}')
    if gable_window:
        gx = W if chimney == 'left' else 1
        gz = (sz - 1) // 2
        g.set(gx, top + 2, gz, 'air')
        bp.prop('window_round', gx, top + 1.0, gz, 90 if gx == W else -90, ['window', 'glow'])
    if partition and part_door_z:
        for y in (Y0, Y0 + 1):
            g.set(partition, y, part_door_z, 'air')
        bp.prop('door_interior', partition, 0, part_door_z, 90, ['door', 'hauntable', 'interior'])
        bp.marker('door', partition, 0, part_door_z, 90, 'door_bedroom')
    info = dict(W=W, D=D, top=top, ridge_y=ridge_y, chimney=(cx, cz), door_x=door_x, sx=sx, sz=sz)
    bp.marker('roof_ridge', sx / 2 - 0.5, ridge_y - 0.0, (sz - 1) / 2, 0, 'ridge')
    return bp, info


def wall_pos(info, wall, along, depth):
    """Cell-centre position for a prop standing with its back against an interior wall face."""
    W, D = info['W'], info['D']
    if wall == 'back':
        return along, 1.5 + depth / 2, 0
    if wall == 'front':
        return along, D - 0.5 - depth / 2, 180
    if wall == 'left':
        return 1.5 + depth / 2, along, 90
    if wall == 'right':
        return W - 0.5 - depth / 2, along, -90
    raise ValueError(wall)


def place_wall(bp, info, prop, wall, along, depth, y=0.0, tags=None, x_face=None):
    x, z, yaw = wall_pos(info, wall, along, depth)
    if wall in ('left', 'right'):
        x, z = x, z
        bp.prop(prop, x, y, z, yaw, tags)
        return x, z, yaw
    bp.prop(prop, x, y, z, yaw, tags)
    return x, z, yaw


def outside_front(bp, info, prop, x, y=0.0, out=0.0, tags=None):
    """Wall-mounted prop on the outer face of the front wall (pivot on the wall plane)."""
    bp.prop(prop, x, y, info['D'] + 0.5 + out, 0, tags)


def interior_cottage_a(bp, info):
    """Follows concept/empty/cottage_interior_empty.png: hearth left, window back, rocking chair on a rug,
    shelf with doll, side table + oil lamp, wardrobe, portrait, door to the bedroom."""
    cx, cz = info['chimney']
    hx, hz, hy = wall_pos(info, 'left', cz, 0.85)
    bp.prop('hearth', hx, 0, hz, hy, ['hearth', 'light'])
    bp.marker('hearth', hx + 0.9, 0, hz, -90, 'hearth')
    bp.prop('rug', 3.7, 0, cz, 90, ['decor'])
    bp.prop('rocking_chair', 3.9, 0, cz + 0.4, -70, ['hauntable', 'seat'])
    bp.marker('sit', 3.9, 0.55, cz + 0.4, -70, 'sit_rocking_chair')
    x, z, yaw = wall_pos(info, 'back', 4.6, 0.32)
    bp.prop('shelf', x, 0, z, yaw, ['decor'])
    bp.prop('cloth_doll', x, 0.625, z - 0.02, yaw, ['hauntable'])
    bp.prop('portrait', 2.0, 0, 1.5, 0, ['hauntable'])
    x, z, yaw = wall_pos(info, 'back', 2.2, 0.5)
    bp.prop('side_table', x, 0, z + 0.4, yaw)
    bp.prop('oil_lamp', x, 0.69, z + 0.4, 0, ['hauntable', 'light'])
    x, z, yaw = wall_pos(info, 'right', 3.0, 0.6) if False else (5.5 - 0.3, 3.0, -90)
    bp.prop('wardrobe', x, 0, z, yaw, ['hauntable', 'hide'])
    bp.marker('hide', x, 0, z, yaw, 'hide_wardrobe')
    bp.prop('floorboard', 4.0, 0, 5.7, 0, ['hauntable', 'creak'])
    bp.marker('creak', 4.0, 0, 5.7, 0, 'creak_floorboard')
    bp.prop('candle', 3.0, 1.0, 1.3, 0, ['hauntable', 'light'])
    bp.prop('books', 2.35, 0.69, 2.3, 20)
    bp.prop('basket', 2.1, 0, 5.8, 0)
    # bedroom (x 7..8)
    bp.prop('bed', 7.5, 0, 1.5 + 1.05, 0, ['bed'])
    bp.marker('sleep', 7.5, 0.62, 2.6, 180, 'sleep_bed')
    bp.prop('chest', 7.5, 0, 4.25, 0)
    bp.prop('side_table', 8.2, 0, 5.8, -90)
    bp.prop('candle', 8.2, 0.69, 5.8, 0, ['hauntable', 'light'])
    bp.prop('rug', 7.6, 0, 4.9, 90, ['decor'])
    bp.room('main', 2, 5, 2, info['D'] - 1, info['top'])
    bp.room('bedroom', 7, info['W'] - 1, 2, info['D'] - 1, info['top'])
    bp.marker('spawn_villager', 7.5, 0, 4.9, 180, 'villager_home')


def interior_cottage_b(bp, info):
    """Kitchen-living room with table + chairs, hearth right, bedroom left."""
    cx, cz = info['chimney']
    hx, hz, hy = wall_pos(info, 'right', cz, 0.85)
    bp.prop('hearth', hx, 0, hz, hy, ['hearth', 'light'])
    bp.marker('hearth', hx - 0.9, 0, hz, 90, 'hearth')
    bp.prop('table', 6.0, 0, 3.6, 0)
    bp.prop('chair', 6.4, 0, 2.85, 0, ['seat'])
    bp.prop('chair', 5.6, 0, 4.35, 180, ['seat'])
    bp.marker('sit', 6.4, 0.5, 2.85, 0, 'sit_chair_1')
    bp.marker('sit', 5.6, 0.5, 4.35, 180, 'sit_chair_2')
    bp.prop('candle', 6.2, 0.82, 3.6, 0, ['hauntable', 'light'])
    bp.prop('mug', 5.7, 0.82, 3.4, 0)
    x, z, yaw = wall_pos(info, 'back', 7.4, 0.32)
    bp.prop('shelf', x, 0, z, yaw)
    bp.prop('portrait', 5.2, 0, 1.5, 0, ['hauntable'])
    bp.prop('rocking_chair', 7.6, 0, 4.3, 120, ['hauntable', 'seat'])
    bp.prop('floorboard', 5.0, 0, 5.0, 0, ['hauntable', 'creak'])
    bp.marker('creak', 5.0, 0, 5.0, 0, 'creak_floorboard')
    bp.prop('barrel', 4.1, 0, 2.0, 0)
    bp.prop('oil_lamp', 4.1, 0.8, 2.0, 0, ['hauntable', 'light'])
    # bedroom (x 2..2): partition at x=3
    bp.prop('bed', 2.05, 0, 1.5 + 1.05, 0, ['bed'])
    bp.marker('sleep', 2.05, 0.62, 2.6, 180, 'sleep_bed')
    bp.prop('wardrobe', 2.1, 0, info['D'] - 0.5 - 0.3, 180, ['hauntable', 'hide'])
    bp.marker('hide', 2.1, 0, info['D'] - 0.8, 180, 'hide_wardrobe')
    bp.prop('candle', 2.1, 1.0, 1.3, 0, ['hauntable', 'light'])
    bp.room('main', 4, info['W'] - 1, 2, info['D'] - 1, info['top'])
    bp.room('bedroom', 2, 2, 2, info['D'] - 1, info['top'])
    bp.marker('spawn_villager', 2.1, 0, 4.0, 180, 'villager_home')


def interior_cottage_c(bp, info):
    """One-room cottage: bed in the corner, hearth, chair and doll (the widow's daughter's room)."""
    cx, cz = info['chimney']
    hx, hz, hy = wall_pos(info, 'left', cz, 0.85)
    bp.prop('hearth', hx, 0, hz, hy, ['hearth', 'light'])
    bp.marker('hearth', hx + 0.9, 0, hz, -90, 'hearth')
    bp.prop('bed', 5.5, 0, 2.55, 0, ['bed'])
    bp.marker('sleep', 5.5, 0.62, 2.6, 180, 'sleep_bed')
    bp.prop('side_table', 4.4, 0, 1.85, 0)
    bp.prop('candle', 4.4, 0.69, 1.85, 0, ['hauntable', 'light'])
    bp.prop('chair', 3.6, 0, 4.6, -100, ['seat'])
    bp.marker('sit', 3.6, 0.5, 4.6, -100, 'sit_chair')
    bp.prop('cloth_doll', 5.6, 0.62, 3.2, 200, ['hauntable'])
    bp.prop('chest', 5.5, 0, 4.4, -90)
    bp.prop('portrait', 3.6, 0, 1.5, 0, ['hauntable'])
    bp.prop('rug', 3.8, 0, 3.4, 0, ['decor'])
    bp.prop('floorboard', 4.2, 0, 4.5, 0, ['hauntable', 'creak'])
    bp.marker('creak', 4.2, 0, 4.5, 0, 'creak_floorboard')
    bp.room('main', 2, info['W'] - 1, 2, info['D'] - 1, info['top'])
    bp.marker('spawn_villager', 4.6, 0, 3.5, 180, 'villager_home')


def interior_cottage_d(bp, info):
    """Farmer's cottage: kitchen table, crates, hearth right, bedroom left with wardrobe."""
    cx, cz = info['chimney']
    hx, hz, hy = wall_pos(info, 'right', cz, 0.85)
    bp.prop('hearth', hx, 0, hz, hy, ['hearth', 'light'])
    bp.marker('hearth', hx - 0.9, 0, hz, 90, 'hearth')
    bp.prop('table', 6.0, 0, 5.2, 90)
    bp.prop('chair', 5.25, 0, 5.2, -90, ['seat'])
    bp.marker('sit', 5.25, 0.5, 5.2, -90, 'sit_chair')
    bp.prop('oil_lamp', 6.0, 0.82, 5.5, 0, ['hauntable', 'light'])
    bp.prop('crate', 7.9, 0, 2.0, 10)
    bp.prop('grain_sack', 7.0, 0, 2.0, 0)
    bp.prop('barrel', 5.3, 0, 2.0, 0)
    bp.prop('portrait', 6.4, 0, 1.5, 0, ['hauntable'])
    bp.prop('floorboard', 6.2, 0, 3.5, 0, ['hauntable', 'creak'])
    bp.marker('creak', 6.2, 0, 3.5, 0, 'creak_floorboard')
    # bedroom x 2..3, partition at 4
    bp.prop('bed', 2.6, 0, 2.55, 0, ['bed'])
    bp.marker('sleep', 2.6, 0.62, 2.6, 180, 'sleep_bed')
    bp.prop('wardrobe', 2.3, 0, info['D'] - 0.8, 180, ['hauntable', 'hide'])
    bp.marker('hide', 2.3, 0, info['D'] - 0.8, 180, 'hide_wardrobe')
    bp.prop('candle', 3.4, 1.0, 1.3, 0, ['hauntable', 'light'])
    bp.room('main', 5, info['W'] - 1, 2, info['D'] - 1, info['top'])
    bp.room('bedroom', 2, 3, 2, info['D'] - 1, info['top'])
    bp.marker('spawn_villager', 2.6, 0, 4.4, 180, 'villager_home')


def exterior_common(bp, info, wisteria=False, lantern_side=1):
    D, dx = info['D'], info['door_x']
    bp.prop('lantern_wall', dx + lantern_side * 0.95, 0, D + 0.5, 0, ['light'])
    for p in bp.props:
        if p['prop'] == 'window_cottage' and abs(p['yaw']) < 1:
            x = p['pos'][0] + bp.origin[0]
            bp.prop('flower_box', x, 0, D + 0.5, 0, ['decor'])
    if wisteria:
        bp.prop('wisteria', dx - 2.0, 0.3, D + 0.5, 0, ['decor'])


def cottage_a():
    bp, info = house('cottage_a', 9, 7, chimney='left', partition=6, part_door_z=5, door_x=4,
                     front_windows=(2, 7), back_windows=(3,), right_windows=(4,), gable_window=True,
                     desc='Thatched cottage, two rooms; interior follows cottage_interior_empty.png (MN centre).')
    interior_cottage_a(bp, info)
    exterior_common(bp, info)
    bp.prop('bucket', 5.4, 0, info['D'] + 1.0, 0)
    return bp


def cottage_b():
    bp, info = house('cottage_b', 9, 6, chimney='right', stone_courses=2, partition=3, part_door_z=4, door_x=6,
                     front_windows=(4, 8), back_windows=(5,), left_windows=(3,),
                     desc='Wide thatched cottage with stone base and wisteria (MN right).')
    interior_cottage_b(bp, info)
    exterior_common(bp, info, wisteria=True, lantern_side=-1)
    bp.prop('broom', 7.2, 0, info['D'] + 0.8, 0)
    bp.prop('barrel', 2.0, 0, info['D'] + 1.0, 0)
    return bp


def cottage_c():
    bp, info = house('cottage_c', 7, 6, pitch=2, chimney='left', door_x=4, front_windows=(2, 6),
                     right_windows=(3,), desc='Narrow cottage with a steep thatch roof (MN back right).')
    interior_cottage_c(bp, info)
    exterior_common(bp, info)
    return bp


def cottage_d():
    bp, info = house('cottage_d', 9, 7, chimney='right', stone_courses=2, brace=True, partition=4, part_door_z=5,
                     door_x=6, front_windows=(2, 8), back_windows=(6,), left_windows=(3,), gable_window=True,
                     desc='Farmer\'s cottage, braced timber frame, two rooms (MN back centre).')
    interior_cottage_d(bp, info)
    exterior_common(bp, info, wisteria=True)
    bp.prop('crate', 8.4, 0, info['D'] + 1.2, 15)
    return bp


def tavern():
    bp, info = house('tavern', 11, 7, roof='slate', chimney='left', stone_courses=2, door_x=7,
                     front_windows=(3, 5, 10), back_windows=(4, 8), right_windows=(4,),
                     desc='The tavern: slate roof, stone base, awning, hanging sign, outdoor tables (MN left).')
    D, W = info['D'], info['W']
    cx, cz = info['chimney']
    hx, hz, hy = wall_pos(info, 'left', cz, 0.85)
    bp.prop('hearth', hx, 0, hz, hy, ['hearth', 'light'])
    bp.marker('hearth', hx + 0.9, 0, hz, -90, 'hearth')
    # bar counter of crates + barrels along the back right
    for x in (7.0, 7.65, 8.3):
        bp.prop('crate', x, 0, 2.6, 0)
    bp.prop('barrel', 9.6, 0, 1.95, 0)
    bp.prop('barrel', 9.6, 0, 2.6, 0)
    bp.prop('barrel', 9.6, 0.8, 2.3, 0)
    bp.prop('shelf', 8.0, 0, 1.66, 0)
    bp.prop('mug', 7.3, 0.62, 2.6, 0)
    bp.prop('mug', 8.0, 0.62, 2.55, 40)
    bp.marker('stand', 7.6, 0, 1.9, 0, 'barkeep')
    for i, (x, z) in enumerate(((4.0, 4.0), (6.5, 5.0))):
        bp.prop('table', x, 0, z, 0)
        bp.prop('stool', x - 0.5, 0, z - 0.7, 0, ['seat'])
        bp.prop('stool', x + 0.5, 0, z + 0.7, 0, ['seat'])
        bp.prop('candle', x, 0.82, z, 0, ['hauntable', 'light'])
        bp.marker('sit', x - 0.5, 0.5, z - 0.7, 0, f'sit_table{i}_a')
        bp.marker('sit', x + 0.5, 0.5, z + 0.7, 180, f'sit_table{i}_b')
    bp.prop('portrait', 5.6, 0, 1.5, 0, ['hauntable'])
    bp.prop('floorboard', 5.5, 0, 6.0, 0, ['hauntable', 'creak'])
    bp.marker('creak', 5.5, 0, 6.0, 0, 'creak_floorboard')
    bp.prop('lantern', 2.6, 0.0, 6.0, 0, ['light'])
    bp.room('main', 2, W - 1, 2, D - 1, info['top'])
    # outside
    exterior_common(bp, info, lantern_side=1)
    bp.prop('tavern_sign', 9.0, 0, D + 0.5, 0, ['sign'])
    bp.prop('tavern_awning', 3.0, 0, D + 0.5, 0)
    bp.prop('tavern_table', 3.0, 0, D + 1.8, 0)
    bp.prop('bench', 3.0, 0, D + 2.6, 180, ['seat'])
    bp.prop('barrel', 5.4, 0, D + 1.2, 0)
    bp.prop('barrel', 0.6, 0, D + 1.0, 0)
    return bp


# ----------------------------------------------------------------------------- landmarks
def windmill_base():
    """Stone + timber mill (mill_night.png): 9x9 lower storey (stone base, loft floor at 4 m), inset 7x7 upper
    storey, steep slate roof; sails glTF on the upper front wall (hub 8.5 m)."""
    W = D = 9
    sx, sz = W + 2, D + 2
    lower_h, upper_top = 4, 10
    sy = 1 + upper_top + 8
    bp = Bp('windmill_base', sx, sy, sz, (sx // 2, 1, sz // 2),
            'Windmill: stone base, rough-wood tapered tower, loft with ladder, steep slate roof. Sails = windmill_sails.')
    g = bp.g
    g.box(1, 0, 1, W, 0, D, 'cobblestone')
    g.box(2, 0, 2, W - 1, 0, D - 1, 'cobble_path')
    g.box(1, 1, 1, W, sy - 1, D, 'air')
    for y in range(1, lower_h + 1):
        for x in range(1, W + 1):
            for z in range(1, D + 1):
                if not (x in (1, W) or z in (1, D)):
                    continue
                corner = x in (1, W) and z in (1, D)
                if y <= 2:
                    b = 'cobblestone'
                elif corner or y == lower_h or (x + z) % 4 == 0:
                    b = 'timber_beam'
                else:
                    b = 'rough_wood'
                g.set(x, y, z, b)
    g.box(2, lower_h, 2, W - 1, lower_h, D - 1, 'timber_planks')
    g.set(6, lower_h, 3, 'air')
    g.set(6, lower_h, 4, 'air')
    x0, x1, z0, z1 = 2, W - 1, 2, D - 1
    g.box(1, lower_h + 1, 1, W, sy - 1, D, '_skip')
    g.box(x0, lower_h + 1, z0, x1, sy - 1, z1, 'air')
    for y in range(lower_h + 1, upper_top + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if not (x in (x0, x1) or z in (z0, z1)):
                    continue
                corner = x in (x0, x1) and z in (z0, z1)
                g.set(x, y, z, 'timber_beam' if (corner or y == upper_top) else 'rough_wood')
    pitch = 2
    rz0, rz1 = z0 - 1, z1 + 1
    ridge = upper_top
    for k in range(0, 14):
        y = upper_top + 1 + k
        zf = rz0 + int(k / pitch)
        zb = rz1 - int(k / pitch)
        if zf > zb or y >= sy:
            break
        for x in range(x0 - 1, x1 + 2):
            for z in range(rz0, rz1 + 1):
                if z < zf or z > zb:
                    g.set(x, y, z, '_skip')
                elif z in (zf, zf + 1, zb, zb - 1):
                    g.set(x, y, z, 'slate_roof')
        for x in (x0, x1):
            for z in range(zf + 2, zb - 1):
                g.set(x, y, z, 'rough_wood')
        ridge = y
    for y in range(ridge + 1, sy):
        g.box(0, y, 0, sx - 1, y, sz - 1, '_skip')
    for y in range(0, lower_h + 1):
        for x in range(sx):
            for z in range(sz):
                if x in (0, sx - 1) or z in (0, sz - 1):
                    g.set(x, y, z, '_skip')
    dx = 4
    for y in (1, 2):
        g.set(dx, y, D, 'air')
    bp.prop('door_cottage', dx, 0, D, 0, ['door', 'hauntable'])
    bp.marker('entry', dx, 0, D + 1.2, 180, 'entry_front')
    bp.marker('door', dx, 0, D, 0, 'door_front')
    wins = [(7, 2, D, 0), (1, 2, 5, -90), (W, 2, 6, 90), (4, 7, z1, 0), (x1, 7, 4, 90), (x0, 7, 6, -90),
            (5, 7, z0, 180)]
    for i, (x, y, z, yaw) in enumerate(wins):
        g.set(x, y, z, 'air')
        bp.prop('window_cottage', x, y - 1.0, z, yaw, ['window', 'glow'])
        bp.marker('window', x, y - 1.0, z, yaw, f'window_{i}')
    bp.prop('windmill_sails', 5, 1.0, z1 + 0.5, 0, ['anim'])
    bp.marker('hub', 5, 8.5, z1 + 1.4, 0, 'sails_hub')
    bp.prop('millstone', 4.0, 0, 4.2, 0)
    for (x, z, r) in ((2.3, 7.6, 0), (2.9, 8.0, 40), (2.2, 2.3, 0), (2.9, 2.2, 20)):
        bp.prop('grain_sack', x, 0, z, r)
    bp.prop('barrel', 7.9, 0, 2.1, 0)
    bp.prop('barrel', 8.0, 0, 2.8, 0)
    bp.prop('ladder', 6.0, 0, 2.2, 180, ['climb'])
    bp.marker('climb', 6.0, 0, 1.6, 0, 'ladder_bottom')
    bp.prop('rocking_chair', 6.9, 0, 7.0, -150, ['hauntable', 'seat'])
    bp.marker('sit', 6.9, 0.55, 7.0, -150, 'sit_rocking_chair')
    x, z, yaw = W - 0.5 - 0.16, 4.8, -90
    bp.prop('shelf', x, 0, z, yaw)
    bp.prop('cloth_doll', x, 0.625, z, yaw, ['hauntable', 'widow_doll'])
    bp.prop('candle', 7.0, 1.0, D - 0.3, 180, ['hauntable', 'light'])
    bp.prop('lantern', 4.0, 0.62, 5.0, 0, ['light'])
    bp.prop('rug', 6.3, 0, 7.4, 0)
    bp.prop('bed', 4.0, 4.0, 2.5 + 1.05, 0, ['bed'])
    bp.marker('sleep', 4.0, 4.62, 3.6, 180, 'sleep_bed')
    bp.prop('chest', 4.0, 4.0, 6.9, 180)
    bp.prop('grain_sack', 7.2, 4.0, 7.0, 0)
    bp.prop('candle', 5.4, 4.0, 7.1, 0, ['hauntable', 'light'])
    bp.room('ground', 2, W - 1, 2, D - 1, 3)
    bp.room('loft', 3, W - 2, 3, D - 2, 4)
    bp.rooms[-1]['min'][1] = 4.0
    bp.rooms[-1]['max'][1] = float(upper_top)
    bp.marker('spawn_villager', 5.6, 0, 6.6, 180, 'villager_home')
    bp.prop('lantern_post', 7.6, 0, D + 1.6, 180, ['light'])
    return bp


def well():
    """Round-ish 3x3 stone well over a 3-deep shaft with still water; roof/crank/bucket = well_roof."""
    bp = Bp('well', 3, 5, 3, (1, 3, 1), 'Village well: cobble ring + shaft with still water; well_roof prop on top.')
    g = bp.g
    g.box(0, 0, 0, 2, 3, 2, 'cobblestone')
    g.set(1, 0, 1, 'still_water')
    g.set(1, 1, 1, 'still_water')
    g.set(1, 2, 1, 'air')
    g.set(1, 3, 1, 'air')
    g.box(0, 4, 0, 2, 4, 2, 'air')
    bp.prop('well_roof', 1, 0, 1, 0, ['light'])
    bp.marker('use', 1, 0, 2.3, 180, 'well_use')
    bp.marker('stand', 1, 0, 3.0, 180, 'well_gather')
    return bp


def plank_bridge():
    """Plank bridge across a 3-wide stream running along X; deck is the ground layer."""
    L, Wd = 7, 3
    bp = Bp('plank_bridge', Wd, 3, L, (1, 1, L // 2),
            'Plank bridge spanning a 3-block stream (z 2..4) whose water surface is one block below the banks.')
    g = bp.g
    g.box(0, 0, 0, Wd - 1, 0, L - 1, 'timber_planks')
    for z in (0, L - 1):
        g.box(0, 0, z, Wd - 1, 0, z, 'cobblestone')
    for x, off in ((0, -0.42), (Wd - 1, 0.42)):
        for z in range(1, L - 2):
            bp.prop('fence_wood', x + off, 0, z + 0.5, 90, ['rail'])
        bp.prop('fence_post', x + off, 0, L - 1.5, 0, ['rail'])
    bp.prop('lantern_post', Wd - 1 + 0.4, 0, L - 1.2, 180, ['light'])
    bp.marker('stand', 1, 0, 3, 0, 'bridge_middle')
    bp.marker('crossing', 1, 0, 3, 0, 'running_water_crossing')
    return bp


def mausoleum():
    """Tiny tier-2 mausoleum (graveyard_night.png, mausoleum.png): mossy spectral-stone bricks, low gable to the
    front, spectral-stone base course, violet portal doorway, gargoyles + spiral emblems as props."""
    W, D = 5, 5
    sx, sz = W + 2, D + 2
    wall_h = 3
    sy = 1 + wall_h + 4
    bp = Bp('mausoleum', sx, sy, sz, (sx // 2, 1, sz // 2),
            'Starting mausoleum: home, respawn point and storage. Tier-2 spectral stone.')
    g = bp.g
    top = wall_h
    g.box(1, 0, 1, W, 0, D, 'mossy_stone_bricks')
    g.box(1, 1, 1, W, sy - 1, D, 'air')
    for y in range(1, top + 1):
        for x in range(1, W + 1):
            for z in range(1, D + 1):
                if x in (1, W) or z in (1, D):
                    g.set(x, y, z, 'spectral_stone' if y == 1 else 'mossy_stone_bricks')
    # roof: ridge along z (gable faces the front), slopes along x
    for k in range(0, 6):
        y = top + 1 + k
        xl = 2 * k
        xr = sx - 1 - 2 * k
        if xl > xr:
            break
        for x in range(sx):
            for z in range(sz):
                if x < xl or x > xr:
                    g.set(x, y, z, '_skip')
                elif x in (xl, xl + 1, xr, xr - 1):
                    g.set(x, y, z, 'mossy_stone_bricks' if z < sz - 1 else '_skip')
        for z in (1, D):  # gable walls (front pediment + back)
            for x in range(xl, xr + 1):
                if g.get(x, y, z) in ('air', '_skip') and 1 <= x <= W:
                    g.set(x, y, z, 'mossy_stone_bricks')
        ridge = y
    for y in range(ridge + 1, sy):
        g.box(0, y, 0, sx - 1, y, sz - 1, '_skip')
    for y in range(0, top + 1):
        for x in range(sx):
            for z in range(sz):
                if x in (0, sx - 1) or z in (0, sz - 1):
                    g.set(x, y, z, '_skip')
    # front corner pilasters stick out one block
    for x in (1, W):
        for y in range(1, top + 1):
            g.set(x, y, D + 1, 'mossy_stone_bricks' if y > 1 else 'spectral_stone')
    dx = 3
    for y in (1, 2):
        g.set(dx, y, D, 'air')
    bp.prop('mausoleum_portal', dx, 0, D, 0, ['door', 'portal', 'light'])
    bp.marker('door', dx, 0, D, 0, 'door_front')
    bp.marker('entry', dx, 0, D + 1.6, 180, 'entry_front')
    for i, z in enumerate((3,)):
        g.set(W, 2, z, 'air')
        bp.prop('mausoleum_window', W, 1.0, z, 90, ['window', 'glow'])
        g.set(1, 2, z, 'air')
        bp.prop('mausoleum_window', 1, 1.0, z, -90, ['window', 'glow'])
    # gargoyles + emblems (mausoleum.png)
    bp.prop('mausoleum_gargoyle_winged', dx, float(ridge), D + 0.2, 0, ['decor'])
    bp.prop('mausoleum_gargoyle_corner', 1, float(top), D + 1, 20, ['decor'])
    bp.prop('mausoleum_gargoyle_corner', W, float(top), D + 1, -20, ['decor'])
    bp.prop('mausoleum_spiral_emblem', dx, top + 1.1, D + 0.5, 0, ['decor'])
    bp.prop('mausoleum_spiral_emblem', W + 0.5, 1.4, 2.0, 90, ['decor'])
    # inside: storage chest, candles, respawn
    bp.prop('chest', dx, 0, 2.0, 0, ['storage'])
    bp.marker('storage', dx, 0, 2.9, 180, 'storage_chest')
    bp.prop('candle_cluster', 2.0, 0, 2.0, 0, ['light'])
    bp.prop('candle_cluster', 4.0, 0, 2.0, 0, ['light'])
    bp.marker('respawn', dx, 0, 3.4, 0, 'respawn')
    bp.marker('spawn_worker', dx, 0, D + 2.4, 0, 'worker_spawn')
    bp.room('crypt', 2, W - 1, 2, D - 1, top)
    # graves in front belong to the graveyard layout (task3); candles on the steps
    bp.prop('grave_candles', 1.6, 0, D + 1.6, 0, ['light'])
    bp.prop('grave_candles', 4.4, 0, D + 1.6, 0, ['light'])
    return bp


def graveyard_gate():
    """Two mossy pillars with a 2-wide gap, low walls either side (graveyard_empty.png)."""
    L = 9
    bp = Bp('graveyard_gate', L, 3, 1, (L // 2, 1, 0), 'Graveyard entrance: low mossy wall, pillars, 2-wide gap.')
    g = bp.g
    g.box(0, 0, 0, L - 1, 0, 0, 'cobblestone')
    g.box(0, 1, 0, L - 1, 1, 0, 'mossy_stone_bricks')
    g.box(0, 2, 0, L - 1, 2, 0, '_skip')
    for x in (3, 4, 5):
        g.set(x, 1, 0, 'air')
    for x in (2, 6):
        g.set(x, 1, 0, '_skip')
        bp.prop('stone_pillar', x, 0, 0, 0, ['pillar'])
    bp.prop('lantern_post', 7.2, 0, 0.9, 180, ['light'])
    bp.marker('entry', 4, 0, 1.2, 180, 'gate_outside')
    bp.marker('entry', 4, 0, -1.2, 0, 'gate_inside')
    return bp


BUILDERS = {'cottage_a': cottage_a, 'cottage_b': cottage_b, 'cottage_c': cottage_c, 'cottage_d': cottage_d,
            'tavern': tavern, 'windmill_base': windmill_base, 'well': well, 'plank_bridge': plank_bridge,
            'mausoleum': mausoleum, 'graveyard_gate': graveyard_gate}


def write_all(names):
    os.makedirs(OUT, exist_ok=True)
    out = {}
    for n in names:
        bp = BUILDERS[n]()
        doc = bp.to_json()
        with open(os.path.join(OUT, n + '.json'), 'w') as f:
            json.dump(doc, f, indent=None, separators=(',', ':'))
        out[n] = (bp, doc)
        solid = sum(1 for v in bp.g.a.flat if v not in ('_skip', 'air'))
        print(f'STRUCT {n} size={doc["size"]} solid={solid} props={len(doc["props"])} markers={len(doc["markers"])}')
    with open(os.path.join(OUT, 'index.json'), 'w') as f:
        json.dump({'structures': {n: {'json': f'res://assets/structures/{n}.json', 'desc': d[1]['desc'],
                                      'size': d[1]['size'], 'origin': d[1]['origin']} for n, d in out.items()}},
                  f, indent=1)
    return out


# ----------------------------------------------------------------------------- Blender previews
def render_previews(built, args):
    import bpy
    import lib_render as LR
    from mathutils import Vector
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    lib = bpy.data.collections.new('PROP_LIBRARY')
    bpy.context.scene.collection.children.link(lib)
    lib.hide_render = True
    lib.hide_viewport = True
    cache = {}

    def load(name):
        if name in cache:
            return cache[name]
        path = os.path.join(ROOT, 'assets', 'props', name + '.gltf')
        if not os.path.exists(path):
            cache[name] = None
            return None
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
        roots = [o for o in new if o.parent is None]
        cache[name] = roots[0] if roots else None
        return cache[name]

    def instance(root, coll, loc, yaw):
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
        r.location = loc
        r.rotation_mode = 'XYZ'
        r.rotation_euler = (0, 0, math.radians(yaw))
        return r

    LR.setup_scene(res=(1280, 900), samples=24, line=1.2)
    out_dir = os.path.join(ROOT, 'renders', 'task1', 'structures')
    os.makedirs(out_dir, exist_ok=True)
    LR.ground(200, -0.001, color=(0.35, 0.42, 0.28, 1))
    colls = {}
    for n, (bp, doc) in built.items():
        coll = bpy.data.collections.new('STRUCT_' + n)
        bpy.context.scene.collection.children.link(coll)
        colls[n] = coll
        a = LV.decode_rle(doc['size'], doc['palette'], doc['rle'])
        vox = LV.build_voxel_mesh(n + '_voxels', a, doc['origin'], coll)
        for p in doc['props']:
            root = load(p['prop'])
            if root is None:
                continue
            x, y, z = p['pos']
            instance(root, coll, Vector((x, -z, y)), p['yaw'])
    for n, coll in colls.items():
        for c in colls.values():
            c.hide_render = c is not coll
        objs = [o for o in coll.objects if o.type == 'MESH' and not o.hide_render]
        vox = bpy.data.objects[n + '_voxels']
        frame = [o for o in coll.all_objects if o.type == 'MESH' and not o.hide_render and
                 not o.name.startswith('HAUNT_')]
        for mood in ('day', 'night'):
            LR.set_mood(mood)
            LR.frame_camera(frame, direction=(-0.8, -1.0, 0.75), margin=1.06)
            LR.render(os.path.join(out_dir, f'{n}_{mood}.png'))
        if n.startswith('cottage') or n in ('tavern', 'windmill_base', 'mausoleum'):
            # cutaway: hide everything above 3.2 m and the front wall (voxels rebuilt without them)
            doc = built[n][1]
            a = LV.decode_rle(doc['size'], doc['palette'], doc['rle'])
            sx, sy, sz = a.shape
            oy = doc['origin'][1]
            cut = a.copy()
            cut_y = oy + 3 if n != 'windmill_base' else oy + 3
            cut[:, cut_y:, :] = '_skip'
            front = max(z for z in range(sz) if any(cut[x, oy, z] not in ('_skip', 'air') for x in range(sx)))
            cut[:, oy:, front] = '_skip'
            if n == 'mausoleum':
                cut[:, oy:, front - 1] = '_skip'
            vox.hide_render = True
            cv = LV.build_voxel_mesh(n + '_cutaway', cut, doc['origin'], coll)
            hidden = []
            for o in coll.objects:
                if o.parent is None and o is not vox and o is not cv:
                    # props above the cut or in the front wall are hidden for the cutaway
                    if o.location.z > 3.0 or o.location.y < -(front - doc['origin'][2] - 0.6):
                        for h in [o] + list(o.children_recursive):
                            if not h.hide_render:
                                h.hide_render = True
                                hidden.append(h)
            LR.set_mood('night')
            LR.frame_camera([cv], direction=(-0.55, -1.0, 1.1), margin=1.05)
            LR.render(os.path.join(out_dir, f'{n}_cutaway_night.png'))
            for h in hidden:
                h.hide_render = False
            vox.hide_render = False
            cv.hide_render = True
    for c in colls.values():
        c.hide_render = False
    if not args.get('only'):
        # lay structures out side by side in the .blend library
        x = 0.0
        for n, coll in colls.items():
            for o in coll.objects:
                if o.parent is None:
                    o.location.x += x
            x += built[n][1]['size'][0] + 6
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'structures.blend'), compress=True)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args = {'only': None, 'render': True}
    for i, a in enumerate(argv):
        if a == '--only':
            args['only'] = argv[i + 1].split(',')
        if a in ('--no-render', '--json-only'):
            args['render'] = False
    names = args['only'] or list(BUILDERS)
    built = write_all(names)
    if args['render']:
        try:
            import bpy  # noqa: F401
        except ImportError:
            print('no bpy: skipping previews')
        else:
            render_previews(built, args)
    print('DONE')


if __name__ == "__main__":
    main()
