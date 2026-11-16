"""True-scale lineup of every task2 character (imported back from the exported glTFs, so this also checks
the files) next to a 1 m block, a 1 x 2 cottage doorway with the task1 door, and a hovering ghost.

blender -b --factory-startup -P blender/scripts/char_lineup.py
-> renders/task2/lineup_front.png, renders/task2/lineup_three_quarter.png, renders/task2/scale_check.json
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
CH = os.path.join(ROOT, 'assets', 'characters')
OUT = os.path.join(ROOT, 'renders', 'task2')

ORDER = ['villager_widow', 'villager_farmer', 'ghost', 'villager_maid', 'villager_teacher', 'villager_child',
         'worker_blacksmith', 'worker_gardener', 'worker_baker']


def import_gltf(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    return new, roots


def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for ob in objs:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            w = ev.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
    return lo, hi


def set_first_frame(objs, clip):
    """The glTF importer makes the first animation (idle / idle_float) active; show its frame 0."""
    for o in objs:
        ad = o.animation_data
        if ad and ad.action:
            print('LINEUP', o.name, 'action', ad.action.name)
    bpy.context.scene.frame_set(0)


def wall_with_door(x0):
    g = np.full((3, 3, 1), 'plaster_wall', dtype=object)
    g[1, 0, 0] = 'air'
    g[1, 1, 0] = 'air'
    g[0, 0, 0] = g[2, 0, 0] = 'cobblestone'
    g[:, 2, 0] = 'timber_beam'
    wall = LV.build_voxel_mesh('LINEUP_wall', g, origin=(1, 0, 0))
    wall.location.x = x0
    objs, roots = import_gltf(os.path.join(ROOT, 'assets', 'props', 'door_cottage.gltf'))
    for r in roots:
        r.location.x += x0
    for o in objs:
        if o.name.startswith('INT_door'):
            o.rotation_mode = 'XYZ'
            o.rotation_euler.z += math.radians(-105)  # swing the leaf open, inward
        if o.name.startswith('HAUNT_') or o.name.endswith('-colonly'):
            o.hide_render = True
    return [wall] + objs


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    LR.setup_scene(res=(2200, 700), samples=32, line=1.2)
    LR.ground(60, 0.0)
    report = {}
    scene_objs = []
    x = 0.0
    # 1 m block and the doorway at the left
    blk = LV.build_voxel_mesh('LINEUP_block', np.full((1, 1, 1), 'grass', dtype=object))
    blk.location.x = x
    scene_objs.append(blk)
    x += 1.4
    scene_objs += wall_with_door(x)
    door_x = x
    x += 1.8
    spans = {}
    for name in ORDER:
        path = os.path.join(CH, name + '.gltf')
        objs, roots = import_gltf(path)
        clip = 'idle_float' if 'ghost' in name else 'idle'
        set_first_frame(objs, clip)
        # parentless meshes are the importer's bone-shape helpers, not part of the character
        meshes = [o for o in objs if o.type == 'MESH' and o.parent is not None and not o.name.startswith('MATERIAL_')]
        for o in objs:
            if o.type == 'MESH' and o.parent is None:
                o.hide_render = True
        for o in objs:
            if o.name.startswith('MATERIAL_'):
                o.hide_render = True
        lo, hi = bounds(meshes)
        w = hi.x - lo.x
        hover = 1.0 if name == 'ghost' else 0.0
        if name == 'ghost':
            # the ghost hovers one block up on a pillar of nothing, next to the farmer row
            pass
        for r in roots:
            r.location.x += x + w / 2 - (lo.x + hi.x) / 2
            r.location.z += hover
        bpy.context.view_layer.update()
        lo2, hi2 = bounds(meshes)
        spans[name] = (lo2, hi2)
        anims = len(bpy.data.actions)
        report[name] = {'height_m': round(hi.z - lo.z, 3), 'width_x_m': round(hi.x - lo.x, 3),
                        'depth_y_m': round(hi.y - lo.y, 3), 'bottom_z': round(lo2.z, 3), 'top_z': round(hi2.z, 3)}
        scene_objs += meshes
        x += w + 0.35
    # a second ghost resting on a 1 m block, to show "1 block up" literally
    blk2 = LV.build_voxel_mesh('LINEUP_block2', np.full((1, 1, 1), 'dirt', dtype=object))
    blk2.location.x = x + 0.5
    scene_objs.append(blk2)
    objs, roots = import_gltf(os.path.join(CH, 'ghost.gltf'))
    set_first_frame(objs, 'idle_float')
    for o in objs:
        if o.name.startswith('MATERIAL_'):
            o.hide_render = True
    for r in roots:
        r.location.x += x + 0.5
        r.location.z += 1.0
    for o in objs:
        if o.type == 'MESH' and o.parent is None:
            o.hide_render = True
    scene_objs += [o for o in objs if o.type == 'MESH' and o.parent is not None]
    # ghost preview material (fresnel rim) on all ghost sheets
    sys.path.insert(0, HERE)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            for i, s in enumerate(o.material_slots):
                if s.material and s.material.name.startswith('GHOST_sheet'):
                    o.material_slots[i].material = ghost_mat()
    LR.set_mood('studio')
    LR.frame_camera(scene_objs, direction=(0, -1, 0.08), margin=1.04)
    LR.render(os.path.join(OUT, 'lineup_front.png'))
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 2200, 1000
    LR.frame_camera(scene_objs, direction=(-0.45, -1, 0.45), margin=1.04)
    LR.render(os.path.join(OUT, 'lineup_three_quarter.png'))
    # scale checks against task1 (door 1 x 2 m, ceilings >= 3 m, ghost hover vs. villager waist)
    checks = {}
    for name, r in report.items():
        if name.startswith('villager'):
            checks[name] = {'fits_door_height_2m': r['height_m'] < 2.0, 'fits_door_width_1m': r['width_x_m'] < 1.0,
                            'under_3m_ceiling': r['height_m'] < 3.0}
    g = report['ghost']
    with open(os.path.join(ROOT, 'assets', 'characters', 'characters.json')) as f:
        info = json.load(f)['characters']
    waists = {n: info[n].get('hip_height') for n in info if n.startswith('villager')}
    checks['ghost_hover_1m'] = {'ghost_bottom_z': g['bottom_z'], 'ghost_top_z': g['top_z'],
                                'villager_hip_heights': waists}
    with open(os.path.join(OUT, 'scale_check.json'), 'w') as f:
        json.dump({'sizes': report, 'checks': checks}, f, indent=1)
    print(json.dumps(checks, indent=1))
    print('DONE')


def ghost_mat():
    m = bpy.data.materials.get('GHOST_preview_lineup')
    if m:
        return m
    m = bpy.data.materials.new('GHOST_preview_lineup')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    pb = nt.nodes.new('ShaderNodeBsdfPrincipled')
    pb.inputs['Base Color'].default_value = (0.9, 0.93, 1.0, 1)
    pb.inputs['Roughness'].default_value = 0.3
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.45
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.55, 0.8, 1.0, 1)
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(lw.outputs['Facing'], em.inputs['Strength'])
    nt.links.new(pb.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs['Surface'])
    return m


main()
