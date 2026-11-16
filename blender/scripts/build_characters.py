"""Build every task2 character: rig + skinned meshes + face shape keys + baked clips (one NLA track each)
-> assets/characters/<name>.gltf, assets/characters/characters.json, blender/characters.blend and previews.

blender -b --factory-startup -P blender/scripts/build_characters.py -- [--only ghost,villager_farmer]
        [--no-render] [--no-strips] [--clips idle,walk]

Previews (frames are gitignored, sheets are committed):
  renders/task2/frames/<name>/turn_<view>.png, <clip>_<k>.png  (8 frames per clip)
  then `python tools/char_sheets.py` builds renders/task2/<name>_turnaround.png and <name>_anims.png.
"""
import json
import math
import os
import subprocess
import sys
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_char as C  # noqa: E402
import lib_geo as G  # noqa: E402
import lib_render as LR  # noqa: E402
import char_ghost as CG  # noqa: E402
import char_villagers as CV  # noqa: E402

ROOT = G.ROOT
OUT = os.path.join(ROOT, 'assets', 'characters')
REN = os.path.join(ROOT, 'renders', 'task2')
FRAMES = os.path.join(REN, 'frames')


def args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    opt = {'only': None, 'render': True, 'strips': True, 'clips': None}
    i = 0
    while i < len(a):
        if a[i] == '--only':
            opt['only'] = a[i + 1].split(',')
            i += 1
        elif a[i] == '--clips':
            opt['clips'] = a[i + 1].split(',')
            i += 1
        elif a[i] == '--no-render':
            opt['render'] = False
        elif a[i] == '--no-strips':
            opt['strips'] = False
        i += 1
    return opt


# ----------------------------------------------------------------------------- registry
def make_ghost(coll):
    res = CG.build_ghost('ghost', coll, 1.0, 'player')
    res['clips'] = CG.player_clips(res)
    res['kind'] = 'ghost'
    res['preview_tools'] = {'swing_scythe': 'scythe_t1', 'dig_shovel': 'shovel_t1', 'smash_hammer': 'sledgehammer_t1'}
    return res


def make_worker(kind):
    outfit = {'blacksmith': CG.outfit_blacksmith, 'gardener': CG.outfit_gardener, 'baker': CG.outfit_baker}[kind]

    def fn(coll):
        res = CG.build_ghost(f'worker_{kind}', coll, 0.75, 'worker', outfit)
        CG.worker_items(kind, coll, res)
        res['clips'] = CG.worker_clips(res, kind)
        res['kind'] = 'worker'
        res['hide_item_in'] = ['carry']
        res['preview_swap'] = {'carry': preview_block(res)}
        return res
    return fn


def preview_block(res):
    """A small grass block on HELD_block for the carry strip (Godot shows the real carried block item)."""
    import numpy as np
    import lib_voxel as LV
    state = {}

    def swap(on):
        if on:
            ob = LV.build_voxel_mesh('PREVIEW_block', np.full((1, 1, 1), 'grass', dtype=object))
            ob.data.transform(Matrix.Translation((0, 0, -0.5)))
            ob.parent = res['HELD_block']
            ob.matrix_parent_inverse = Matrix()
            ob.matrix_basis = Matrix.Scale(0.26 * res['s'], 4)
            state['ob'] = ob
        elif state.get('ob'):
            bpy.data.objects.remove(state.pop('ob'), do_unlink=True)
    return swap


CHARS = {
    'ghost': make_ghost,
    'worker_blacksmith': make_worker('blacksmith'),
    'worker_gardener': make_worker('gardener'),
    'worker_baker': make_worker('baker'),
}
for _v in CV.VILLAGERS:
    CHARS[f'villager_{_v}'] = (lambda v: (lambda coll: CV.build_villager(v, coll)))(_v)


# ----------------------------------------------------------------------------- preview materials
def ghost_preview_mat(name='GHOST_preview', alpha=1.0):
    """Fresnel rim (ice blue) over glossy white: what Godot's ghost shader should look like; preview only."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pb = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pb.inputs['Base Color'].default_value = (0.9, 0.93, 1.0, 1)
    pb.inputs['Roughness'].default_value = 0.3
    pb.inputs['Alpha'].default_value = alpha
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.45
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.35
    mr.inputs['From Max'].default_value = 1.0
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.55, 0.8, 1.0, 1)
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 1.6
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(lw.outputs['Facing'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], mul.inputs[0])
    nt.links.new(mul.outputs[0], em.inputs['Strength'])
    nt.links.new(pb.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Surface'])
    return m


def apply_preview_materials(res):
    for ob in [res['body']] + list(res['rig'].children_recursive):
        if ob.type != 'MESH':
            continue
        for i, slot in enumerate(ob.material_slots):
            if slot.material and slot.material.name.startswith('GHOST_sheet'):
                ob.material_slots[i].material = ghost_preview_mat()
    if res.get('manifest'):
        res['manifest'].hide_render = True


# ----------------------------------------------------------------------------- preview tools (task1 glTFs)
def attach_preview_tool(res, tool):
    """Build the task1 tool (props_tools) and hang it on HELD_tool by its GRIP; returns the root object."""
    import props_tools  # noqa: F401
    from props_common import REGISTRY
    coll = res['coll']
    p = REGISTRY[tool]['fn']()
    grip = next(c for c in p.children if c.name == 'GRIP').pivot
    root = G.build(p, coll)
    for o in G.hierarchy(root):
        if o.type == 'EMPTY' and o is not root:
            o.hide_render = True
        o.name = f'PREVIEW|{tool}|{o.name}'
    held = res['HELD_tool']
    root.parent = held
    root.matrix_parent_inverse = Matrix()
    root.matrix_basis = Matrix.Translation(-grip)
    return root


# ----------------------------------------------------------------------------- rendering
def deformed_bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for ob in objs:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        for v in me.vertices:
            w = mw @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
    return lo, hi


def place_camera(lo, hi, direction, res_xy, margin=1.08):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res_xy
    cam = bpy.data.objects.get('PREVIEW_cam')
    if cam is None:
        cd = bpy.data.cameras.new('PREVIEW_cam')
        cam = bpy.data.objects.new('PREVIEW_cam', cd)
        sc.collection.objects.link(cam)
    sc.camera = cam
    centre = (lo + hi) / 2
    d = Vector(direction).normalized()
    size = (hi - lo).length
    cam.location = centre + d * (size * 3 + 4)
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.clip_end = size * 10 + 50
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    xs, ys = [], []
    for x in (lo.x, hi.x):
        for y in (lo.y, hi.y):
            for z in (lo.z, hi.z):
                p = inv @ Vector((x, y, z))
                xs.append(p.x)
                ys.append(p.y)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    cam.location = cam.matrix_world @ Vector((cx, cy, 0))
    ex, ey = max(xs) - min(xs), max(ys) - min(ys)
    aspect = res_xy[0] / res_xy[1]
    cam.data.ortho_scale = max(ex, ey * aspect) * margin
    return cam


VIEWS = {'front': (0, -1, 0.12), 'three_quarter': (-0.75, -1, 0.3), 'side': (-1, 0, 0.12), 'back': (0, 1, 0.12)}
STRIP_DIR = (-0.8, -1, 0.35)


def render_turnaround(res, objs):
    name = res['name']
    # the turnaround shows frame 0 of the first (idle) clip, like the concept sheets; rest pose = A-pose
    first = next(iter(res['clips']))
    C.play(res['rig'], res['faces'], first, 0)
    lo, hi = deformed_bounds(objs)
    big = max(hi.x - lo.x, hi.y - lo.y)
    c = (lo + hi) / 2
    lo2 = Vector((c.x - big / 2, c.y - big / 2, lo.z))
    hi2 = Vector((c.x + big / 2, c.y + big / 2, hi.z))
    for v, d in VIEWS.items():
        place_camera(lo2, hi2, d, (360, 440))
        LR.render(os.path.join(FRAMES, name, f'turn_{v}.png'))
    C.rest_pose(res['rig'], res['faces'])


def render_expressions(res):
    """Front close-up of the head for the basis and every shape key (renders/task2/<name>_expressions.png)."""
    name = res['name']
    rig = res['rig']
    face = res['faces'][0]
    C.rest_pose(rig, res['faces'])
    hb = rig.pose.bones['head']
    top = rig.matrix_world @ hb.tail
    lo, hi = deformed_bounds([face])
    c = (lo + hi) / 2
    r = max(hi.x - lo.x, hi.z - lo.z) * 0.85
    lo2 = Vector((c.x - r, c.y, min(c.z - r, lo.z - 0.02)))
    hi2 = Vector((c.x + r, c.y, max(c.z + r * 0.9, top.z if res['kind'] == 'villager' else c.z + r)))
    keys = face.data.shape_keys.key_blocks
    for e in ['calm'] + [k.name for k in keys[1:]]:
        for k in keys[1:]:
            k.value = 1.0 if k.name == e else 0.0
        place_camera(lo2, hi2, (0, -1, 0.08), (240, 240), margin=1.15)
        LR.render(os.path.join(FRAMES, name, f'expr_{e}.png'))
    for k in keys[1:]:
        k.value = 0.0


def clip_frames(n, loop, count=8):
    if loop:
        return [round(k * n / count) for k in range(count)]
    return [round(k * n / (count - 1)) for k in range(count)]


def render_strips(res, objs, only=None):
    name = res['name']
    rig = res['rig']
    faces = res['faces']
    for clip, (n, fn, loop) in res['clips'].items():
        if only and clip not in only:
            continue
        frames = clip_frames(n, loop)
        tool = res.get('preview_tools', {}).get(clip)
        tool_root = attach_preview_tool(res, tool) if tool else None
        hide_item = clip in res.get('hide_item_in', [])
        items = [o for o in rig.children_recursive if o.name.startswith(f'{name}|ITEM_') or
                 o.name.startswith('ITEM_')]
        for o in items:
            for x in [o] + list(o.children_recursive):
                x['_hr'] = x.hide_render
                if hide_item:
                    x.hide_render = True
        swap = res.get('preview_swap', {}).get(clip)
        if swap:
            swap(True)
        lift = res.get('preview_lift', {}).get(clip, 0.0)
        seat = None
        if lift:
            rig.location.z = lift
            seat = bpy.data.objects.new('PREVIEW_seat', bpy.data.meshes.new('PREVIEW_seat'))
            import bmesh
            bm = G.bm_box((0.5, 0.48, lift), 0.02)
            bm.to_mesh(seat.data)
            bm.free()
            seat.location = (0, 0.04, lift / 2)
            seat.data.materials.append(G.get_mat('wood'))
            res['coll'].objects.link(seat)
        # one camera for the whole clip (union of the sampled frames)
        lo = Vector((1e9, 1e9, 1e9))
        hi = -lo
        for f in frames:
            C.play(rig, faces, clip, f)
            a, b = deformed_bounds(objs + ([tool_root] + list(tool_root.children_recursive) if tool_root else []) +
                                   ([seat] if seat else []) +
                                   [o for o in bpy.data.objects if o.name.startswith('PREVIEW_block')])
            lo = Vector(map(min, lo, a))
            hi = Vector(map(max, hi, b))
        lo.z = min(lo.z, 0.0)
        place_camera(lo, hi, res.get('strip_dir', STRIP_DIR), (300, 360), margin=1.1)
        for k, f in enumerate(frames):
            C.play(rig, faces, clip, f)
            LR.render(os.path.join(FRAMES, name, f'{clip}_{k}.png'))
        if swap:
            swap(False)
        rig.location.z = 0.0
        if seat:
            bpy.data.objects.remove(seat, do_unlink=True)
        for o in items:
            for x in [o] + list(o.children_recursive):
                x.hide_render = x.get('_hr', False)
        if tool_root:
            for o in [tool_root] + list(tool_root.children_recursive):
                bpy.data.objects.remove(o, do_unlink=True)
    C.rest_pose(rig, faces)


# ----------------------------------------------------------------------------- main
def char_info(res, path):
    rig = res['rig']
    C.rest_pose(rig, res['faces'])
    objs = [o for o in rig.children_recursive if o.type == 'MESH' and not o.name.startswith('MATERIAL_')]
    lo, hi = deformed_bounds(objs)
    nodes = sorted(o.name for o in rig.children_recursive)
    info = {
        'gltf': f'res://assets/characters/{res["name"]}.gltf',
        'kind': res['kind'],
        'size': [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)],
        'bones': list(res['skel'].order),
        'nodes': nodes,
        'expressions': list(res['faces'][0].data.shape_keys.key_blocks.keys())[1:] if res['faces'] else [],
        'clips': {c: {'frames': n, 'seconds': round(n / 24, 3), 'loop': loop}
                  for c, (n, fn, loop) in res['clips'].items()},
    }
    info.update(res.get('info', {}))
    return info


def main():
    opt = args()
    G.standard_mats()
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    LR.setup_scene(res=(300, 360), samples=12, line=0.9)
    LR.ground(30, 0.0)
    LR.set_mood('studio')
    os.makedirs(OUT, exist_ok=True)
    manifest_path = os.path.join(OUT, 'characters.json')
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f).get('characters', {})
    names = [n for n in CHARS if not opt['only'] or n in opt['only']]
    colls = []
    for name in names:
        t0 = time.time()
        coll = G.new_collection('CHAR_' + name)
        res = CHARS[name](coll)
        res['coll'] = coll
        rig = res['rig']
        for clip, (n, fn, loop) in res['clips'].items():
            C.bake_clip(rig, res['skel'], clip, n, fn, res['faces'])
        C.rest_pose(rig, res['faces'])
        path = os.path.join(OUT, name + '.gltf')
        C.export_character(rig, path)
        manifest[name] = char_info(res, path)
        t1 = time.time()
        if opt['render']:
            for c in colls:
                c.hide_render = True
            apply_preview_materials(res)
            LR.set_mood('studio')
            objs = [o for o in rig.children_recursive if o.type == 'MESH']
            render_turnaround(res, objs)
            render_expressions(res)
            if opt['strips']:
                render_strips(res, objs, opt['clips'])
        coll.hide_render = True
        colls.append(coll)
        # free node names for the next character (Blender would add .001 otherwise)
        for o in [rig] + list(rig.children_recursive):
            if not o.name.startswith(name):
                o.name = f'{name}|{o.name}'
        print(f'CHAR {name} build+export {t1 - t0:.1f}s render {time.time() - t1:.1f}s')
    with open(manifest_path, 'w') as f:
        json.dump({'note': 'generated by build_characters.py; size = [x, y(up), z] metres in Godot axes (rest pose)',
                   'characters': dict(sorted(manifest.items()))}, f, indent=1)
    if not opt['only']:
        for c in colls:
            c.hide_render = False
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'characters.blend'), compress=True)
    if opt['render']:
        try:
            subprocess.run(['python', os.path.join(ROOT, 'tools', 'char_sheets.py')] + names, check=False)
        except Exception as e:  # noqa: BLE001
            print('char_sheets failed', e)
    print('DONE')


main()
