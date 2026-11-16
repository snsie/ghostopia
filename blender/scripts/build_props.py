"""Build every glTF prop: assets/props/<name>.gltf + blender/props.blend + previews.

blender -b --factory-startup -P blender/scripts/build_props.py -- [--only a,b] [--cat hauntable] [--no-render]

Previews: renders/task1/props/<name>.png (studio), hauntables also <name>_haunted.png (night, HAUNT_ shown).
Contact sheets are made afterwards with tools/contact_sheet.py (see README "Rebuild").
"""
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_geo as G  # noqa: E402
import lib_render as LR  # noqa: E402
from props_common import REGISTRY  # noqa: E402
import props_haunt  # noqa: E402,F401
import props_village  # noqa: E402,F401
import props_interior  # noqa: E402,F401
import props_graveyard  # noqa: E402,F401
import props_tools  # noqa: E402,F401

ROOT = G.ROOT
OUT = os.path.join(ROOT, 'assets', 'props')
REN = os.path.join(ROOT, 'renders', 'task1', 'props')


def args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    opt = {'only': None, 'cat': None, 'render': True}
    i = 0
    while i < len(a):
        if a[i] == '--only':
            opt['only'] = a[i + 1].split(',')
            i += 1
        elif a[i] == '--cat':
            opt['cat'] = a[i + 1]
            i += 1
        elif a[i] == '--no-render':
            opt['render'] = False
        i += 1
    return opt


def haunt_preview_mat():
    """Preview-only fresnel rim glow (what Godot's HAUNT_ shader should look like); never exported."""
    m = bpy.data.materials.get('HAUNT_preview')
    if m:
        return m
    m = bpy.data.materials.new('HAUNT_preview')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.3
    ramp = nt.nodes.new('ShaderNodeMapRange')
    ramp.inputs['From Min'].default_value = 0.3
    ramp.inputs['From Max'].default_value = 0.9
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.6, 0.45, 1.0, 1)
    em.inputs['Strength'].default_value = 3.2
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lw.outputs['Facing'], ramp.inputs['Value'])
    nt.links.new(ramp.outputs['Result'], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    m.use_backface_culling = True
    return m


def set_haunt_visible(objs, on):
    for o in objs:
        if o.name.startswith('HAUNT_'):
            o.hide_render = not on


def main():
    opt = args()
    G.standard_mats()
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    LR.setup_scene(res=(420, 420), samples=16, line=1.0)
    LR.ground(30, 0.0)
    names = [n for n, r in REGISTRY.items()
             if (not opt['only'] or n in opt['only']) and (not opt['cat'] or r['cat'] == opt['cat'])]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(REN, exist_ok=True)
    manifest_path = os.path.join(OUT, 'props.json')
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f).get('props', {})
    colls = []
    for name in names:
        t0 = time.time()
        reg = REGISTRY[name]
        coll = G.new_collection('PROP_' + name)
        prop = reg['fn']()
        root = G.build(prop, coll)
        objs = G.hierarchy(root)
        G.export_gltf(root, os.path.join(OUT, name + '.gltf'))
        kinds = sorted({o.name.split('_')[0] for o in objs if o.name.split('_')[0] in
                        ('INT', 'MARK', 'ANIM', 'LIGHT', 'FX', 'HAUNT', 'FLAME', 'GRIP')})
        lo, hi = LR.mesh_bounds([o for o in objs if not o.name.startswith('HAUNT_')])
        manifest[name] = {
            'gltf': f'res://assets/props/{name}.gltf', 'category': reg['cat'], 'hauntable': reg['haunt'],
            'desc': reg['desc'], 'nodes': sorted(o.name for o in objs if o.name.split('_')[0] in
                                                  ('INT', 'MARK', 'ANIM', 'LIGHT', 'FX', 'HAUNT', 'GRIP')),
            'size': [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)],
        }
        colls.append(coll)
        if opt['render']:
            for c in colls:
                c.hide_render = c is not coll
            vis = [o for o in objs if o.type == 'MESH']
            set_haunt_visible(objs, False)
            LR.set_mood('studio')
            LR.frame_camera([o for o in vis if not o.name.startswith('HAUNT_')])
            LR.render(os.path.join(REN, name + '.png'))
            if reg['haunt']:
                hm = haunt_preview_mat()
                for o in objs:
                    if o.name.startswith('HAUNT_'):
                        o.data.materials[0] = hm
                set_haunt_visible(objs, True)
                for o in objs:
                    if o.name.startswith('HAUNT_'):
                        o.visible_shadow = False
                LR.set_mood('night')
                LR.render(os.path.join(REN, name + '_haunted.png'))
                for o in objs:
                    if o.name.startswith('HAUNT_'):
                        o.data.materials[0] = G.get_mat('HAUNT_glow')
                LR.set_mood('night')
                set_haunt_visible(objs, False)
                LR.render(os.path.join(REN, name + '_night.png'))
        set_haunt_visible(objs, True)
        coll.hide_render = True
        # free the clean node names for the next prop (Blender would append .001 otherwise)
        for o in objs:
            if o.data is not None and o.data.users == 1:
                o.data.name = f'{name}|{o.data.name}'
            o.name = f'{name}|{o.name}'
        print(f'PROP {name} {time.time() - t0:.1f}s kinds={kinds}')
    with open(manifest_path, 'w') as f:
        json.dump({'note': 'generated by build_props.py; size = [x, y(up), z] metres in Godot axes',
                   'props': dict(sorted(manifest.items()))}, f, indent=1)
    if not opt['only'] and not opt['cat']:
        for c in colls:
            c.hide_render = False
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'props.blend'), compress=True)
    print('DONE')


main()
