"""Battle prototype: placeholder clan soldiers for the crowd (Drowned Parish, Barrow Host).

Each unit is a chunky low-poly figure built from coloured boxes (voxel style, flat shaded) with
rigid parts (torso, head, arms, legs, weapon, hat/shield). The animation is computed per part and
baked into a vertex-animation texture (VAT) so hundreds of units can play it on the GPU from one
MultiMesh: every vertex's position and normal for every frame of every clip.

Writes, per unit, into assets/battle/units/:
  <id>.json       metadata: vertex/index counts, clips (start row, frames, fps, loop), bounds
  <id>_mesh.bin   float32 rest positions (x,y,z), float32 normals, float32 colours (r,g,b,a), uint32 indices
  <id>_vat.bin    float16 RGBA texture, width = vertex count, height = 2 * frames:
                  rows [0, F) positions, rows [F, 2F) normals (Godot axes)
and a preview contact sheet to renders/battle/units_preview.png (Blender only).

Godot axes throughout: x right, y up, the unit faces +Z (decisions.md, task1 convention).

Run:  blender -b --factory-startup -P blender/scripts/build_battle_units.py
      (python blender/scripts/build_battle_units.py also works; it skips the preview render)
"""
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'battle', 'units')
RENDERS = os.path.join(ROOT, 'renders', 'battle')

FPS = 15.0
# name, frames, loop
CLIPS = [('idle', 16, True), ('walk', 12, True), ('attack', 10, False), ('flee', 8, True)]


# Vertex colour alpha is a material flag for the Godot shader: 1 = matte, 0 = glows (eyes, flames).
GLOW = 0.0


def hexc(h, a=1.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


# ---------------------------------------------------------------- geometry

def box(size, center, color):
    """24 vertices (4 per face) so every face is flat-shaded. Returns (verts, normals, colors, tris)."""
    sx, sy, sz = (s * 0.5 for s in size)
    cx, cy, cz = center
    faces = [
        ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
        ((-1, 0, 0), [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)]),
        ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]),
        ((0, -1, 0), [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)]),
        ((0, 0, 1), [(1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, 1)]),
        ((0, 0, -1), [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)]),
    ]
    v, n, c, t = [], [], [], []
    for normal, quad in faces:
        base = len(v)
        for q in quad:
            v.append((cx + q[0] * sx, cy + q[1] * sy, cz + q[2] * sz))
            n.append(normal)
            c.append(color)
        # Godot front faces are clockwise seen from outside
        t += [(base, base + 2, base + 1), (base, base + 3, base + 2)]
    return v, n, c, t


class Part:
    """A rigid part: boxes in the part's local frame around a pivot, with a parent part."""

    def __init__(self, name, pivot, parent=None):
        self.name = name
        self.pivot = np.array(pivot, dtype=np.float64)   # in the parent's local frame (rest)
        self.parent = parent
        self.boxes = []

    def add(self, size, center, color):
        self.boxes.append((size, center, color))
        return self


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def pose_matrix(p):
    """p = dict(rx, ry, rz, dx, dy, dz) -> 4x4 local transform about the pivot."""
    r = rot_y(p.get('ry', 0.0)) @ rot_x(p.get('rx', 0.0)) @ rot_z(p.get('rz', 0.0))
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = (p.get('dx', 0.0), p.get('dy', 0.0), p.get('dz', 0.0))
    return m


def build_unit(parts):
    """Flattens parts into vertex arrays and a per-vertex part index."""
    verts, norms, cols, tris, owner = [], [], [], [], []
    for pi, part in enumerate(parts):
        for size, center, color in part.boxes:
            v, n, c, t = box(size, center, color)
            base = len(verts)
            verts += v
            norms += n
            cols += c
            tris += [(a + base, b + base, cc + base) for a, b, cc in t]
            owner += [pi] * len(v)
    return (np.array(verts), np.array(norms), np.array(cols, dtype=np.float32),
            np.array(tris, dtype=np.uint32), np.array(owner))


def world_matrices(parts, pose):
    mats = []
    for part in parts:
        local = np.eye(4)
        local[:3, 3] = part.pivot
        local = local @ pose_matrix(pose.get(part.name, {}))
        if part.parent is not None:
            mats.append(mats[parts.index(part.parent)] @ local)
        else:
            mats.append(local)
    return mats


def bake_frame(parts, verts, norms, owner, pose):
    mats = world_matrices(parts, pose)
    out_v = np.empty_like(verts)
    out_n = np.empty_like(norms)
    for pi, m in enumerate(mats):
        sel = owner == pi
        out_v[sel] = (m[:3, :3] @ verts[sel].T).T + m[:3, 3]
        out_n[sel] = (m[:3, :3] @ norms[sel].T).T
    return out_v, out_n


# ---------------------------------------------------------------- the two clans

def parish_soldier():
    """Drowned Parish: waterlogged Sunday coat, pale drowned skin, wide black hat with a votive candle,
    a hymnal in the left hand and a boat hook in the right."""
    coat = hexc('#2f4f5c')
    coat_dark = hexc('#223a45')
    collar = hexc('#dfe6e0')
    skin = hexc('#9cc0b8')
    eye = hexc('#ffb24d', GLOW)
    hat = hexc('#1d1f2b')
    trousers = hexc('#2a2c3a')
    wood = hexc('#7a5a3c')
    iron = hexc('#5b6470')
    candle = hexc('#f2e6c8')
    flame = hexc('#ffb24d', GLOW)
    hymnal = hexc('#5a2430')
    hips = Part('hips', (0, 0.62, 0))
    hips.add((0.42, 0.18, 0.28), (0, 0.0, 0), coat_dark)
    torso = Part('torso', (0, 0.08, 0), hips)
    torso.add((0.48, 0.46, 0.32), (0, 0.24, 0), coat)
    torso.add((0.52, 0.22, 0.34), (0, -0.04, 0), coat)          # coat skirt
    torso.add((0.30, 0.08, 0.34), (0, 0.46, 0.0), collar)
    head = Part('head', (0, 0.50, 0.01), torso)
    head.add((0.36, 0.34, 0.34), (0, 0.18, 0), skin)
    head.add((0.08, 0.07, 0.02), (-0.08, 0.20, 0.175), eye)
    head.add((0.08, 0.07, 0.02), (0.08, 0.20, 0.175), eye)
    head.add((0.58, 0.05, 0.56), (0, 0.37, 0), hat)              # brim
    head.add((0.32, 0.20, 0.32), (0, 0.49, 0), hat)              # crown
    head.add((0.06, 0.10, 0.06), (0.10, 0.64, 0.04), candle)
    head.add((0.04, 0.06, 0.04), (0.10, 0.72, 0.04), flame)
    arm_l = Part('arm_l', (-0.30, 0.40, 0), torso)
    arm_l.add((0.14, 0.44, 0.14), (0, -0.20, 0), coat)
    arm_l.add((0.12, 0.10, 0.12), (0, -0.46, 0), skin)
    arm_l.add((0.10, 0.22, 0.16), (0, -0.50, 0.10), hymnal)
    arm_r = Part('arm_r', (0.30, 0.40, 0), torso)
    arm_r.add((0.14, 0.44, 0.14), (0, -0.20, 0), coat)
    arm_r.add((0.12, 0.10, 0.12), (0, -0.46, 0), skin)
    weapon = Part('weapon', (0, -0.48, 0.04), arm_r)
    weapon.add((0.05, 0.05, 1.10), (0, 0, 0.30), wood)            # boat hook shaft, forward
    weapon.add((0.06, 0.18, 0.06), (0, 0.06, 0.86), iron)
    weapon.add((0.06, 0.06, 0.12), (0, 0.14, 0.80), iron)
    leg_l = Part('leg_l', (-0.11, 0.0, 0), hips)
    leg_l.add((0.15, 0.56, 0.17), (0, -0.30, 0), trousers)
    leg_l.add((0.16, 0.08, 0.24), (0, -0.58, 0.03), hat)
    leg_r = Part('leg_r', (0.11, 0.0, 0), hips)
    leg_r.add((0.15, 0.56, 0.17), (0, -0.30, 0), trousers)
    leg_r.add((0.16, 0.08, 0.24), (0, -0.58, 0.03), hat)
    return [hips, torso, head, arm_l, arm_r, weapon, leg_l, leg_r]


def barrow_warrior():
    """Barrow Host: broad warband dead in a fur cloak, bone-and-iron crown, earthen round shield on
    the left arm and a bronze sword in the right."""
    tunic = hexc('#6b4a2b')
    fur = hexc('#6e5a43')
    skin = hexc('#a99a86')
    eye = hexc('#ffc46b', GLOW)
    bone = hexc('#c9a978')
    iron = hexc('#4a4a52')
    bronze = hexc('#c08a3a')
    shield = hexc('#5a4632')
    boots = hexc('#3a2d24')
    hips = Part('hips', (0, 0.56, 0))
    hips.add((0.50, 0.18, 0.32), (0, 0.0, 0), tunic)
    hips.add((0.54, 0.06, 0.34), (0, 0.06, 0), bronze)            # belt
    torso = Part('torso', (0, 0.08, 0), hips)
    torso.add((0.56, 0.44, 0.36), (0, 0.24, 0), tunic)
    torso.add((0.66, 0.16, 0.42), (0, 0.44, -0.02), fur)          # fur mantle
    torso.add((0.58, 0.40, 0.08), (0, 0.18, -0.21), fur)          # cloak back
    head = Part('head', (0, 0.52, 0.0), torso)
    head.add((0.36, 0.34, 0.34), (0, 0.17, 0.01), skin)
    head.add((0.09, 0.06, 0.02), (-0.08, 0.19, 0.185), eye)
    head.add((0.09, 0.06, 0.02), (0.08, 0.19, 0.185), eye)
    head.add((0.40, 0.08, 0.38), (0, 0.36, 0.01), iron)           # crown band
    for i, x in enumerate((-0.15, -0.05, 0.05, 0.15)):
        head.add((0.06, 0.12 + 0.04 * (i % 2), 0.06), (x, 0.45, 0.17), bone)
    head.add((0.10, 0.05, 0.08), (0, 0.06, 0.18), bone)           # jaw guard
    arm_l = Part('arm_l', (-0.36, 0.40, 0), torso)
    arm_l.add((0.16, 0.42, 0.16), (0, -0.19, 0), tunic)
    arm_l.add((0.13, 0.10, 0.13), (0, -0.44, 0), skin)
    arm_l.add((0.08, 0.56, 0.56), (-0.07, -0.30, 0.10), shield)   # round-ish earthen shield
    arm_l.add((0.06, 0.14, 0.14), (-0.13, -0.30, 0.10), bronze)   # boss
    arm_r = Part('arm_r', (0.36, 0.40, 0), torso)
    arm_r.add((0.16, 0.42, 0.16), (0, -0.19, 0), tunic)
    arm_r.add((0.13, 0.10, 0.13), (0, -0.44, 0), skin)
    weapon = Part('weapon', (0, -0.46, 0.04), arm_r)
    weapon.add((0.06, 0.06, 0.16), (0, 0, -0.02), boots)           # grip
    weapon.add((0.20, 0.05, 0.05), (0, 0, 0.07), bronze)           # guard
    weapon.add((0.07, 0.04, 0.62), (0, 0, 0.40), bronze)           # blade, forward
    leg_l = Part('leg_l', (-0.14, 0.0, 0), hips)
    leg_l.add((0.18, 0.50, 0.19), (0, -0.27, 0), tunic)
    leg_l.add((0.20, 0.10, 0.26), (0, -0.52, 0.03), boots)
    leg_r = Part('leg_r', (0.14, 0.0, 0), hips)
    leg_r.add((0.18, 0.50, 0.19), (0, -0.27, 0), tunic)
    leg_r.add((0.20, 0.10, 0.26), (0, -0.52, 0.03), boots)
    return [hips, torso, head, arm_l, arm_r, weapon, leg_l, leg_r]


# ---------------------------------------------------------------- animation

def pose_at(clip, t, style):
    """Part poses at clip time t in [0, 1). `style` tweaks the clans (the Parish shuffles, the Barrow
    marches)."""
    tau = 2 * math.pi
    p = {}
    heavy = style == 'barrow'
    if clip == 'idle':
        s = math.sin(t * tau)
        p['hips'] = {'dy': 0.012 * s}
        p['torso'] = {'rx': 0.03 * s, 'rz': 0.02 * math.sin(t * tau * 0.5 + 1)}
        p['head'] = {'ry': 0.12 * math.sin(t * tau + 0.6), 'rx': -0.04 * s}
        p['arm_l'] = {'rx': -0.25 if not heavy else -0.35, 'rz': -0.05}
        p['arm_r'] = {'rx': -0.55 - 0.05 * s, 'rz': 0.05}
        p['weapon'] = {'rx': 0.35}
    elif clip == 'walk':
        s = math.sin(t * tau)
        swing = 0.55 if heavy else 0.42
        p['hips'] = {'dy': 0.035 * abs(math.cos(t * tau)), 'ry': 0.08 * s}
        p['torso'] = {'rx': 0.10 if heavy else 0.14, 'ry': -0.10 * s}
        p['head'] = {'rx': -0.08}
        p['leg_l'] = {'rx': swing * s}
        p['leg_r'] = {'rx': -swing * s}
        p['arm_l'] = {'rx': (-0.30 if heavy else -0.25) - 0.15 * s}
        p['arm_r'] = {'rx': -0.55 + 0.25 * s}
        p['weapon'] = {'rx': 0.35}
    elif clip == 'attack':
        # wind up (0 - 0.45), strike (0.45 - 0.65), recover
        if t < 0.45:
            k = t / 0.45
            raise_a = -2.3 * (k * k * (3 - 2 * k))
            lean = -0.12 * k
        elif t < 0.65:
            k = (t - 0.45) / 0.2
            raise_a = -2.3 + 2.7 * (k * k * (3 - 2 * k))
            lean = -0.12 + 0.40 * k
        else:
            k = (t - 0.65) / 0.35
            raise_a = 0.4 - 0.95 * (k * k * (3 - 2 * k))
            lean = 0.28 * (1 - k)
        p['torso'] = {'rx': lean, 'ry': 0.25 * lean}
        p['arm_r'] = {'rx': raise_a, 'rz': 0.12}
        p['weapon'] = {'rx': 0.35 + (0.4 if heavy else 0.2) * min(1.0, max(0.0, -raise_a / 2.3))}
        p['arm_l'] = {'rx': -0.9 if heavy else -0.35, 'rz': -0.15}
        p['leg_l'] = {'rx': 0.25}
        p['leg_r'] = {'rx': -0.15}
        p['hips'] = {'dy': -0.03 * math.sin(min(1.0, t / 0.65) * math.pi)}
    elif clip == 'flee':
        s = math.sin(t * tau)
        p['hips'] = {'dy': 0.06 * abs(math.cos(t * tau))}
        p['torso'] = {'rx': 0.32, 'rz': 0.08 * s}
        p['head'] = {'rx': -0.35, 'ry': 0.35 * math.sin(t * tau * 0.5)}   # glancing back
        p['leg_l'] = {'rx': 0.8 * s}
        p['leg_r'] = {'rx': -0.8 * s}
        p['arm_l'] = {'rx': -2.6 + 0.35 * s, 'rz': -0.35}                  # arms up, flailing
        p['arm_r'] = {'rx': -2.6 - 0.35 * s, 'rz': 0.35}
        p['weapon'] = {'rx': 1.2}                                          # weapon dropped low
    return p


# ---------------------------------------------------------------- bake + write

def bake(unit_id, parts, style):
    verts, norms, cols, tris, owner = build_unit(parts)
    rows_v, rows_n = [], []
    clips = {}
    row = 0
    for name, frames, loop in CLIPS:
        clips[name] = {'start': row, 'frames': frames, 'fps': FPS, 'loop': loop,
                       'length_s': frames / FPS}
        for f in range(frames):
            t = f / frames if loop else f / max(1, frames - 1)
            v, n = bake_frame(parts, verts, norms, owner, pose_at(name, t, style))
            rows_v.append(v)
            rows_n.append(n)
            row += 1
    total = row
    vc = len(verts)
    vat = np.zeros((total * 2, vc, 4), dtype=np.float16)
    for r in range(total):
        vat[r, :, :3] = rows_v[r]
        vat[r, :, 3] = 1.0
        vat[total + r, :, :3] = rows_n[r]
    rest_v, rest_n = bake_frame(parts, verts, norms, owner, pose_at('idle', 0.0, style))
    allv = np.concatenate(rows_v)
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, unit_id + '_mesh.bin'), 'wb') as fh:
        fh.write(rest_v.astype(np.float32).tobytes())
        fh.write(rest_n.astype(np.float32).tobytes())
        fh.write(cols.astype(np.float32).tobytes())
        fh.write(tris.astype(np.uint32).tobytes())
    with open(os.path.join(OUT, unit_id + '_vat.bin'), 'wb') as fh:
        fh.write(vat.tobytes())
    meta = {
        'id': unit_id,
        'generator': 'blender/scripts/build_battle_units.py',
        'units': 'metres, Godot axes (x right, y up, faces +Z)',
        'vertex_count': int(vc),
        'index_count': int(tris.size),
        'mesh': 'res://assets/battle/units/%s_mesh.bin' % unit_id,
        'mesh_layout': 'float32 positions[vc*3], float32 normals[vc*3], float32 colors[vc*4], uint32 indices[ic]',
        'vat': 'res://assets/battle/units/%s_vat.bin' % unit_id,
        'vat_format': 'RGBAH (float16 x4), width = vertex_count, height = 2 * frames; rows [0,F) positions, [F,2F) normals',
        'vat_size': [int(vc), int(total * 2)],
        'frames': int(total),
        'clips': clips,
        'clip_order': [c[0] for c in CLIPS],
        'bounds': {'min': [float(x) for x in lo], 'max': [float(x) for x in hi]},
        'height_m': float(hi[1]),
    }
    with open(os.path.join(OUT, unit_id + '.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)
    print('UNIT %s: %d verts, %d tris, %d frames, height %.2f m' % (unit_id, vc, len(tris), total, hi[1]))
    return verts, cols, tris, owner, rows_v


def preview(baked):
    """Contact sheet: each unit in idle / walk / attack wind-up / attack strike / flee."""
    try:
        import bpy
    except ImportError:
        print('preview skipped (not running inside Blender)')
        return
    sys.path.insert(0, HERE)
    import lib_render
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    sc = lib_render.setup_scene(res=(1400, 640), samples=16, freestyle=True, line=1.0)
    lib_render.set_mood('studio')
    mat = bpy.data.materials.new('vcol')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    attr = nt.nodes.new('ShaderNodeVertexColor')
    attr.layer_name = 'Col'
    nt.links.new(attr.outputs[0], bsdf.inputs[0])
    try:
        bsdf.inputs['Roughness'].default_value = 0.85
    except Exception:
        pass
    objs = []
    picks = [('idle', 0), ('walk', 3), ('walk', 9), ('attack', 4), ('attack', 6), ('flee', 2)]
    starts = {}
    row = 0
    for name, frames, loop in CLIPS:
        starts[name] = row
        row += frames
    for ui, (uid, (verts, cols, tris, owner, rows_v)) in enumerate(baked.items()):
        for k, (clip, f) in enumerate(picks):
            v = rows_v[starts[clip] + f]
            # Godot (x, y, z) -> Blender (x, -z, y)
            bv = [(float(p[0]) + k * 1.6, float(-p[2]) + ui * 2.4, float(p[1])) for p in v]
            me = bpy.data.meshes.new('%s_%s_%d' % (uid, clip, f))
            # Godot fronts are clockwise, Blender's counter-clockwise: flip the winding
            me.from_pydata(bv, [], [(int(t[0]), int(t[2]), int(t[1])) for t in tris])
            me.update()
            ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
            for i in range(len(bv)):
                ca.data[i].color = tuple(float(x) for x in cols[i])
            for poly in me.polygons:
                poly.use_smooth = False
            ob = bpy.data.objects.new(me.name, me)
            ob.data.materials.append(mat)
            sc.collection.objects.link(ob)
            objs.append(ob)
    lib_render.ground(size=60)
    lib_render.frame_camera(objs, direction=(0.35, -1.0, 0.45), margin=1.08)
    lib_render.render(os.path.join(RENDERS, 'units_preview.png'))
    print('PREVIEW', os.path.join(RENDERS, 'units_preview.png'))


def main():
    baked = {}
    baked['parish_soldier'] = bake('parish_soldier', parish_soldier(), 'parish')
    baked['barrow_warrior'] = bake('barrow_warrior', barrow_warrior(), 'barrow')
    preview(baked)


if __name__ == '__main__':
    main()
