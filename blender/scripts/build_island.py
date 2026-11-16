"""Task 3: the Millbrook island (vertical slice) -> layout JSON + voxels + .blend + mood renders.

Plain Python (layout + voxels only, about 1 s):
    python blender/scripts/build_island.py --json-only
Blender (layout + voxels + blender/millbrook_island.blend + renders/task3/*):
    blender -b --factory-startup -P blender/scripts/build_island.py -- [--no-render] [--only millbrook,mill]
                                                                        [--moods night,day] [--res 1280x720]
                                                                        [--no-plan] [--no-blend]

The generator lives in lib_island.py (pure numpy). Renders use the lighting presets written into
millbrook_layout.json, so Blender previews and Godot share one source of truth for the moods.
"""
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402

import lib_island as LI  # noqa: E402

ROOT = LI.ROOT
OUT = os.path.join(ROOT, 'renders', 'task3')
FOG_K = float(os.environ.get('FOG_K', '0.12'))


def argv():
    a = sys.argv
    return a[a.index('--') + 1:] if '--' in a else a[1:]


def opt(name, default=None):
    a = argv()
    return a[a.index(name) + 1] if name in a else default


# ============================================================================== cameras
# name: Godot-space camera position, look-at point, lens (mm), moods, concept image per mood, cutaway
CAMERAS = {
    'millbrook': dict(pos=(118.0, 36.0, 140.0), look=(116.5, 20.0, 94.0), lens=24,
                      moods=['night', 'dusk', 'day', 'fading'],
                      concept={'night': 'empty/millbrook_empty.png', 'dusk': 'locations/millbrook_dusk.png',
                               'day': 'locations/millbrook_day.png', 'fading': 'locations/millbrook_fading.png'}),
    'cottage_interior': dict(struct='pip_cottage', rel_pos=(-0.4, 5.6, 6.6), rel_look=(-1.4, 0.5, -0.9), lens=20,
                             moods=['night', 'day'], cutaway='front_roof',
                             concept={'night': 'empty/cottage_interior_empty.png',
                                      'day': 'locations/cottage_interior_day.png'}),
    'mill': dict(struct='windmill', rel_pos=(-5.0, 4.5, 16.5), rel_look=(-0.8, 3.6, 0.0), lens=22,
                 moods=['night'], cutaway='front_ground',
                 concept={'night': 'empty/mill_empty.png'}),
    'graveyard': dict(pos=(49.0, 35.0, 99.0), look=(25.5, 29.0, 91.0), lens=26, moods=['night', 'day'],
                      concept={'night': 'empty/graveyard_empty.png', 'day': 'locations/graveyard_day.png'}),
    'overview': dict(pos=(124.0, 92.0, 268.0), look=(98.0, 10.0, 98.0), lens=30, moods=['night'],
                     concept={'night': 'locations/world_map.png'}),
}


# ============================================================================== Blender side
def blender_main(isl, doc):
    import bpy
    from mathutils import Vector

    t0 = time.time()
    only = set(opt('--only').split(',')) if opt('--only') else None
    moods_only = set(opt('--moods').split(',')) if opt('--moods') else None
    res = tuple(int(v) for v in (opt('--res') or '1280x720').split('x'))

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    sc = bpy.context.scene
    W = isl.W
    blocks = LI.LV.blocks_doc()
    cols, rows = blocks['atlas']['columns'], blocks['atlas']['rows']
    import lib_voxel as LV
    mats = LV.atlas_materials()
    mat_list = [mats['VOX_opaque'], mats['VOX_cutout'], mats['VOX_water']]
    for m in mat_list:   # glowing ore / spectral veins brighter in the island scene
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Emission Strength'].default_value = 3.0
    # water: tint + slight emission so the stream glints like the concept's glowing blue water
    bw = next(n for n in mats['VOX_water'].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bw.inputs['Alpha'].default_value = 0.82

    # ---- per-block tables
    N = 256
    cube = np.zeros(N, bool)
    cross = np.zeros(N, bool)
    liquid = np.zeros(N, bool)
    transp = np.zeros(N, bool)
    tiles = np.zeros((N, 4), np.int32)   # top, bottom, side, front
    for b in blocks['blocks']:
        i = b['index']
        if b['id'] == 'air':
            continue
        t = b['tiles']
        tiles[i] = (t.get('top', t['side']), t.get('bottom', t['side']), t['side'], t.get('front', t['side']))
        if b.get('shape') == 'cross':
            cross[i] = True
        else:
            cube[i] = True
        liquid[i] = bool(b.get('liquid'))
        transp[i] = bool(b.get('transparent'))
    matidx = np.where(liquid, 2, np.where(transp | cross, 1, 0)).astype(np.int32)

    # direction -> (tile column in `tiles`, corners in Godot axes BL BR TR TL)
    FACES = [
        ((1, 0, 0), 2, [(1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)]),
        ((-1, 0, 0), 2, [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
        ((0, 0, 1), 3, [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
        ((0, 0, -1), 2, [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)]),
        ((0, 1, 0), 0, [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)]),
        ((0, -1, 0), 1, [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    ]
    ins = 0.004

    def tile_uv(t):
        r, c = np.divmod(t, cols)
        u0 = c / cols + ins / cols
        u1 = (c + 1) / cols - ins / cols
        v1 = 1 - r / rows - ins / rows
        v0 = 1 - (r + 1) / rows + ins / rows
        return np.stack([np.stack([u0, v0], -1), np.stack([u1, v0], -1), np.stack([u1, v1], -1),
                         np.stack([u0, v1], -1)], 1)   # (n, 4, 2)

    def mesh_region(Wr, x0, z0, name, coll):
        """Wr: padded sub-array [x, y, z] with a 1-cell border of neighbours."""
        core = Wr[1:-1, 1:-1, 1:-1]
        V, UV, M = [], [], []
        for (dx, dy, dz), tk, corners in FACES:
            nb = Wr[1 + dx:Wr.shape[0] - 1 + dx, 1 + dy:Wr.shape[1] - 1 + dy, 1 + dz:Wr.shape[2] - 1 + dz]
            see = (nb == 0) | cross[nb] | ((transp[nb] | liquid[nb]) & (nb != core))
            vis = cube[core] & see
            i, j, k = np.nonzero(vis)
            if not len(i):
                continue
            b = core[i, j, k]
            c = np.array(corners, float)                       # (4, 3) Godot
            gx = (x0 + i)[:, None] + c[None, :, 0]
            gy = j[:, None] + c[None, :, 1]
            gz = (z0 + k)[:, None] + c[None, :, 2]
            if dy == 1:   # water surface sits a little lower
                low = liquid[b] & (nb[i, j, k] == 0)
                gy = gy - 0.12 * low[:, None]
            V.append(np.stack([gx, -gz, gy], -1))
            UV.append(tile_uv(tiles[b, tk]))
            M.append(matidx[b])
        # crossed sprites
        i, j, k = np.nonzero(cross[core])
        if len(i):
            b = core[i, j, k]
            for quad in ([(0.15, 0, 0.15), (0.85, 0, 0.85), (0.85, 1, 0.85), (0.15, 1, 0.15)],
                         [(0.85, 0, 0.15), (0.15, 0, 0.85), (0.15, 1, 0.85), (0.85, 1, 0.15)]):
                for rev in (False, True):
                    q = list(reversed(quad)) if rev else quad
                    c = np.array(q, float)
                    gx = (x0 + i)[:, None] + c[None, :, 0]
                    gy = j[:, None] + c[None, :, 1]
                    gz = (z0 + k)[:, None] + c[None, :, 2]
                    V.append(np.stack([gx, -gz, gy], -1))
                    uv = tile_uv(tiles[b, 2])
                    if rev:
                        uv = uv[:, [1, 0, 3, 2]]
                    UV.append(uv)
                    M.append(np.ones(len(i), np.int32))
        if not V:
            return None
        V = np.concatenate(V).reshape(-1, 3)
        UV = np.concatenate(UV).reshape(-1, 2)
        M = np.concatenate(M)
        nv, nf = len(V), len(M)
        me = bpy.data.meshes.new(name)
        me.vertices.add(nv)
        me.vertices.foreach_set('co', V.astype(np.float32).ravel())
        me.loops.add(nv)
        me.loops.foreach_set('vertex_index', np.arange(nv, dtype=np.int32))
        me.polygons.add(nf)
        me.polygons.foreach_set('loop_start', np.arange(0, nv, 4, dtype=np.int32))
        me.update(calc_edges=True)
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', UV.astype(np.float32).ravel())
        for m in mat_list:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', M.astype(np.int32))
        try:
            fm = me.attributes.new('freestyle_face', 'BOOLEAN', 'FACE')
            fm.data.foreach_set('value', (M != 0))
        except Exception as e:  # noqa
            print('freestyle marks unavailable', e)
        me.validate()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob

    vox_coll = bpy.data.collections.new('VOXELS')
    sc.collection.children.link(vox_coll)
    CS = 32
    chunk_objs = {}

    def build_chunks(Wsrc, keys=None):
        Wp = np.pad(Wsrc, 1)
        for cx in range(0, LI.SX, CS):
            for cz in range(0, LI.SZ, CS):
                if keys is not None and (cx, cz) not in keys:
                    continue
                old = chunk_objs.pop((cx, cz), None)
                if old is not None:
                    me = old.data
                    bpy.data.objects.remove(old)
                    bpy.data.meshes.remove(me)
                sub = Wp[cx:cx + CS + 2, :, cz:cz + CS + 2]
                ob = mesh_region(sub, cx, cz, f'island_{cx:03d}_{cz:03d}', vox_coll)
                if ob is not None:
                    chunk_objs[(cx, cz)] = ob
    build_chunks(W)
    nfaces = sum(len(o.data.polygons) for o in chunk_objs.values())
    print(f'voxel mesh: {len(chunk_objs)} chunks, {nfaces} faces ({time.time() - t0:.1f}s)')

    # ---- props as collection instances
    lib = {}
    inst_coll = bpy.data.collections.new('PROPS')
    sc.collection.children.link(inst_coll)
    lights_all = []

    def prop_coll(name):
        if name in lib:
            return lib[name]
        c = bpy.data.collections.new('P_' + name)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, 'assets', 'props', name + '.gltf'),
                                  export_import_convert_lighting_mode='RAW')
        for o in [o for o in bpy.data.objects if o not in before]:
            for uc in list(o.users_collection):
                uc.objects.unlink(o)
            c.objects.link(o)
            if o.type == 'LIGHT':
                o.data.energy *= 30.0
                o['base_energy'] = o.data.energy
                lights_all.append(o)
            if o.name.startswith('HAUNT_') or '|HAUNT_' in o.name or o.name.endswith('-colonly') or 'MATERIAL_' in o.name:
                o.hide_render = True
        lib[name] = c
        return c

    inst_objs = []
    for inst in doc['instances']:
        c = prop_coll(inst['prop'])
        e = bpy.data.objects.new(inst['id'], None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = c
        x, y, z = inst['pos']
        e.location = (x, -z, y)
        e.rotation_euler = (0, 0, math.radians(inst['yaw']))
        e['owner'] = inst['owner'] or ''
        inst_coll.objects.link(e)
        inst_objs.append(e)
    print(f'props: {len(lib)} glTFs, {len(inst_objs)} instances ({time.time() - t0:.1f}s)')

    # glow / flame materials (mood-dependent emission)
    glow_mats = []
    for m in bpy.data.materials:
        if m.name.startswith('GLOW_') and m.use_nodes:
            b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b is not None:
                m['base_em'] = b.inputs['Emission Strength'].default_value
                glow_mats.append((m, b))

    # ---- lighting rig from the presets
    import lib_render as LR
    LR.setup_scene(res=res, samples=32, freestyle=True, line=1.0)
    ls = sc.view_layers[0].freestyle_settings.linesets[0].linestyle
    ls.color = (0.02, 0.012, 0.03)   # linear; the task1 ink colour reads light against a night scene
    ls.alpha = 0.7
    sc.render.film_transparent = False
    try:
        sc.eevee.volumetric_end = 260.0
        sc.eevee.volumetric_tile_size = '8'
        sc.eevee.volumetric_samples = 48
        sc.eevee.use_shadows = True
        sc.eevee.shadow_resolution_scale = 1.0
    except Exception as e:  # noqa
        print('eevee volume settings', e)

    def hex_rgb(h):
        h = h.lstrip('#')
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)   # sRGB -> linear

    def sun_obj(name):
        ob = bpy.data.objects.get(name)
        if ob is None:
            ld = bpy.data.lights.new(name, 'SUN')
            ob = bpy.data.objects.new(name, ld)
            sc.collection.objects.link(ob)
        return ob

    world = bpy.data.worlds.new('ISLAND_world')
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -1.0
    mr.inputs['From Max'].default_value = 1.0
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    # moon disc / stars: a sharp glow toward the moon direction
    moon_dot = nt.nodes.new('ShaderNodeVectorMath')
    moon_dot.operation = 'DOT_PRODUCT'
    nt.links.new(tc.outputs['Generated'], moon_dot.inputs[0])
    moon_mr = nt.nodes.new('ShaderNodeMapRange')
    moon_mr.inputs['From Min'].default_value = 0.9985
    moon_mr.inputs['From Max'].default_value = 0.9990
    nt.links.new(moon_dot.outputs['Value'], moon_mr.inputs['Value'])
    halo_mr = nt.nodes.new('ShaderNodeMapRange')
    halo_mr.inputs['From Min'].default_value = 0.985
    halo_mr.inputs['From Max'].default_value = 1.0
    nt.links.new(moon_dot.outputs['Value'], halo_mr.inputs['Value'])
    halo_pow = nt.nodes.new('ShaderNodeMath')
    halo_pow.operation = 'POWER'
    halo_pow.inputs[1].default_value = 3.0
    nt.links.new(halo_mr.outputs['Result'], halo_pow.inputs[0])
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 140.0
    nt.links.new(tc.outputs['Generated'], vor.inputs['Vector'])
    star_mr = nt.nodes.new('ShaderNodeMapRange')
    star_mr.inputs['From Min'].default_value = 0.06
    star_mr.inputs['From Max'].default_value = 0.0
    nt.links.new(vor.outputs['Distance'], star_mr.inputs['Value'])
    star_gate = nt.nodes.new('ShaderNodeMath')   # only above the horizon
    star_gate.operation = 'MULTIPLY'
    star_up = nt.nodes.new('ShaderNodeMapRange')
    star_up.inputs['From Min'].default_value = 0.05
    star_up.inputs['From Max'].default_value = 0.3
    nt.links.new(sep.outputs['Z'], star_up.inputs['Value'])
    nt.links.new(star_mr.outputs['Result'], star_gate.inputs[0])
    nt.links.new(star_up.outputs['Result'], star_gate.inputs[1])
    star_amt = nt.nodes.new('ShaderNodeMath')
    star_amt.operation = 'MULTIPLY'
    nt.links.new(star_gate.outputs['Value'], star_amt.inputs[0])
    add1 = nt.nodes.new('ShaderNodeMix')
    add1.data_type = 'RGBA'
    add1.blend_type = 'ADD'
    add1.inputs['Factor'].default_value = 1.0
    nt.links.new(ramp.outputs['Color'], add1.inputs['A'])
    moon_col = nt.nodes.new('ShaderNodeMath')
    moon_col.operation = 'ADD'
    nt.links.new(moon_mr.outputs['Result'], moon_col.inputs[0])
    halo_amt = nt.nodes.new('ShaderNodeMath')
    halo_amt.operation = 'MULTIPLY'
    nt.links.new(halo_pow.outputs['Value'], halo_amt.inputs[0])
    nt.links.new(halo_amt.outputs['Value'], moon_col.inputs[1])
    sum_lights = nt.nodes.new('ShaderNodeMath')
    sum_lights.operation = 'ADD'
    nt.links.new(moon_col.outputs['Value'], sum_lights.inputs[0])
    nt.links.new(star_amt.outputs['Value'], sum_lights.inputs[1])
    tint = nt.nodes.new('ShaderNodeMix')
    tint.data_type = 'RGBA'
    tint.blend_type = 'MULTIPLY'
    tint.inputs['Factor'].default_value = 1.0
    tint.inputs['A'].default_value = (0.85, 0.9, 1.0, 1)
    nt.links.new(sum_lights.outputs['Value'], tint.inputs['B'])
    nt.links.new(tint.outputs['Result'], add1.inputs['B'])
    sky_bg = nt.nodes.new('ShaderNodeBackground')
    nt.links.new(add1.outputs['Result'], sky_bg.inputs['Color'])
    amb_bg = nt.nodes.new('ShaderNodeBackground')
    lp = nt.nodes.new('ShaderNodeLightPath')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
    nt.links.new(amb_bg.outputs['Background'], mix.inputs[1])
    nt.links.new(sky_bg.outputs['Background'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')   # not linked: a world volume swallowed the ambient
    # light in EEVEE, so distance fog is left to Godot; the preview keeps only the low mist slab below.

    # low mist: a flat volume slab over the plains
    mist_me = bpy.data.meshes.new('MIST')
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mist_me)
    bm.free()
    mist = bpy.data.objects.new('MIST', mist_me)
    sc.collection.objects.link(mist)
    mist.scale = (900, 900, 3.0)
    mist.location = (96, -96, 21.2)
    mm = bpy.data.materials.new('MIST_vol')
    mm.use_nodes = True
    mnt = mm.node_tree
    mnt.nodes.clear()
    mo = mnt.nodes.new('ShaderNodeOutputMaterial')
    mv = mnt.nodes.new('ShaderNodeVolumePrincipled')
    # density fades toward the top of the slab
    mtc = mnt.nodes.new('ShaderNodeTexCoord')
    msep = mnt.nodes.new('ShaderNodeSeparateXYZ')
    mnt.links.new(mtc.outputs['Generated'], msep.inputs[0])
    mfade = mnt.nodes.new('ShaderNodeMapRange')
    mfade.inputs['From Min'].default_value = 1.0
    mfade.inputs['From Max'].default_value = 0.0
    mnt.links.new(msep.outputs['Z'], mfade.inputs['Value'])
    mmul = mnt.nodes.new('ShaderNodeMath')
    mmul.operation = 'MULTIPLY'
    mnt.links.new(mfade.outputs['Result'], mmul.inputs[0])
    mnt.links.new(mmul.outputs['Value'], mv.inputs['Density'])
    mnt.links.new(mv.outputs['Volume'], mo.inputs['Volume'])
    mist_me.materials.append(mm)
    mist.visible_shadow = False

    presets = doc['lighting']['presets']

    def set_mood(mood):
        p = presets[mood]
        sky = p['sky']
        ramp.color_ramp.elements[0].position = 0.5
        ramp.color_ramp.elements[0].color = (*hex_rgb(sky['void']), 1)
        ramp.color_ramp.elements[1].position = 1.0
        ramp.color_ramp.elements[1].color = (*hex_rgb(sky['top']), 1)
        while len(ramp.color_ramp.elements) > 2:
            ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
        e = ramp.color_ramp.elements.new(0.52)
        e.color = (*hex_rgb(sky['horizon']), 1)
        e2 = ramp.color_ramp.elements.new(0.64)
        hz, tp = hex_rgb(sky['horizon']), hex_rgb(sky['top'])
        e2.color = (*[hz[i] * 0.45 + tp[i] * 0.55 for i in range(3)], 1)
        amb = p['ambient']
        amb_bg.inputs['Color'].default_value = (*hex_rgb(amb['color']), 1)
        amb_bg.inputs['Strength'].default_value = amb['energy'] * 1.1
        sky_bg.inputs['Strength'].default_value = 1.0
        key = p['sun'] or p['moon']
        sun = sun_obj('KEY_light')
        d = key['direction']
        dv = Vector((d[0], -d[2], d[1])).normalized()
        sun.rotation_euler = dv.to_track_quat('-Z', 'Y').to_euler()
        sun.data.color = hex_rgb(key['color'])
        sun.data.energy = key['energy'] * (3.2 if p['sun'] else 2.6)
        sun.data.angle = math.radians(3)
        src = -dv
        moon_dot.inputs[1].default_value = src
        on = 1.0 if sky.get('moon_disc') else 0.0
        moon_mr.inputs['To Max'].default_value = 6.0 * on
        halo_amt.inputs[1].default_value = 0.5 * on
        star_amt.inputs[1].default_value = 1.4 if sky.get('stars') else 0.0
        fog = p['fog']
        vol.inputs['Color'].default_value = (*hex_rgb(fog['color']), 1)
        vol.inputs['Density'].default_value = fog['density'] * FOG_K
        try:
            vol.inputs['Emission Color'].default_value = (*hex_rgb(fog['color']), 1)
            vol.inputs['Emission Strength'].default_value = fog['density'] * FOG_K * 0.5
        except Exception:
            pass
        hf = fog.get('height_fog')
        mist.hide_render = hf is None
        if hf:
            mv.inputs['Color'].default_value = (*hex_rgb(fog['color']), 1)
            mmul.inputs[1].default_value = hf['density'] * FOG_K * 2.0
        em = p['emission']
        for m, b in glow_mats:
            b.inputs['Emission Strength'].default_value = m['base_em'] * (em['glow_energy'] if em['windows'] else 0.0)
        for lo in lights_all:
            lo.data.energy = lo['base_energy'] * p['lamps_energy'] * 2.0
        sc.view_settings.exposure = math.log2(p['exposure']) * 1.4
        return p

    # ---- camera
    cam_data = bpy.data.cameras.new('CAM')
    cam = bpy.data.objects.new('CAM', cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam_data.clip_start = 0.3
    cam_data.clip_end = 1200

    def place_cam(pos, look, lens):
        p = Vector((pos[0], -pos[2], pos[1]))
        lk = Vector((look[0], -look[2], look[1]))
        cam.location = p
        cam.rotation_euler = (lk - p).to_track_quat('-Z', 'Y').to_euler()
        cam_data.type = 'PERSP'
        cam_data.lens = lens
        cam_data.sensor_width = 36

    struct = {s['id']: s for s in doc['structures']}

    def cutaway(kind, s):
        """World copy with part of a structure removed + list of instances to hide."""
        Wc = W.copy()
        ax, ay, az = s['anchor']
        yaw = s['yaw']
        bp = LI.load_blueprint(s['blueprint'])
        ox, oy, oz = bp['origin']
        sx, sy, sz = bp['size']
        hide = []
        for x in range(sx):
            for z in range(sz):
                rx, rz = LI.rot_xz(yaw, x - ox, z - oz)
                wx, wz = ax + int(round(rx)), az + int(round(rz))
                lz = z - oz
                for wy in range(ay, LI.SY):
                    ly = wy - ay
                    if kind == 'front_roof' and (ly >= 3 or lz >= 3):
                        Wc[wx, wy, wz] = 0
                    elif kind == 'front_ground' and lz >= 3 and ly < 4:
                        Wc[wx, wy, wz] = 0
        # flowers / weeds in front of the cut
        piv = s['pivot']
        for e in inst_objs:
            if e['owner'] != s['id']:
                continue
            x, y, z = e.location.x, e.location.z, -e.location.y
            lx, lz = LI.rot_xz(-yaw, x - piv[0], z - piv[2])
            ly = y - piv[1]
            if kind == 'front_roof' and (ly >= 2.6 or lz >= 2.6):
                hide.append(e)
            if kind == 'front_ground' and lz >= 2.6 and ly < 3.6 and e.name.split('_')[0] in ('window', 'door'):
                hide.append(e)
            if kind == 'front_ground' and 'sails' in e.name:
                pass
        return Wc, hide

    def postprocess(path, p):
        """Saturation and a soft bloom (EEVEE has no bloom any more; Godot does glow itself)."""
        img = bpy.data.images.load(path, check_existing=False)
        w, h = img.size
        px = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(px)
        a = px.reshape(h, w, 4)
        rgb = a[..., :3]
        lum = (rgb * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
        rgb = lum + (rgb - lum) * p['saturation']
        bloom = p.get('glow_bloom', 0)
        if bloom > 0:
            bright = np.clip(rgb - 0.62, 0, None)
            small = bright[::4, ::4]
            for _ in range(3):
                for ax in (0, 1):
                    small = (np.roll(small, 1, ax) + small + np.roll(small, -1, ax) + np.roll(small, 2, ax) +
                             np.roll(small, -2, ax)) / 5
            up = np.repeat(np.repeat(small, 4, 0), 4, 1)[:h, :w]
            rgb = rgb + up * bloom * 1.6
        a[..., :3] = np.clip(rgb, 0, 1)
        img.pixels.foreach_set(a.ravel())
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        bpy.data.images.remove(img)

    renders = []
    os.makedirs(OUT, exist_ok=True)
    if '--no-render' not in argv():
        for name, cd in CAMERAS.items():
            if only and name not in only:
                continue
            hide = []
            changed = None
            if 'struct' in cd:
                s = struct[cd['struct']]
                piv = s['pivot']

                def rel(v, s=s, piv=piv):
                    rx, rz = LI.rot_xz(s['yaw'], v[0], v[2])
                    return (piv[0] + rx, piv[1] + v[1], piv[2] + rz)
                pos, look = rel(cd['rel_pos']), rel(cd['rel_look'])
                if cd.get('cutaway'):
                    Wc, hide = cutaway(cd['cutaway'], s)
                    ax, az = s['anchor'][0], s['anchor'][2]
                    changed = {((ax + dx) // CS * CS, (az + dz) // CS * CS) for dx in (-7, 7) for dz in (-7, 7)}
                    build_chunks(Wc, changed)
            else:
                pos, look = cd['pos'], cd['look']
            for e in hide:
                e.hide_render = True
            place_cam(pos, look, cd['lens'])
            for mood in cd['moods']:
                if moods_only and mood not in moods_only:
                    continue
                p = set_mood(mood)
                path = os.path.join(OUT, f'{name}_{mood}.png')
                t1 = time.time()
                sc.render.filepath = path
                bpy.ops.render.render(write_still=True)
                postprocess(path, p)
                renders.append((name, mood, path))
                print(f'render {name}_{mood} {time.time() - t1:.1f}s')
            for e in hide:
                e.hide_render = False
            if changed:
                build_chunks(W, changed)
        if '--no-plan' not in argv() and (not only or 'plan' in only):
            render_plan(bpy, sc, cam, cam_data, set_mood, mist, doc)
    if '--no-blend' not in argv():
        set_mood('night')
        place_cam(CAMERAS['millbrook']['pos'], CAMERAS['millbrook']['look'], CAMERAS['millbrook']['lens'])
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'millbrook_island.blend'), compress=True)
    print(f'blender part done in {time.time() - t0:.1f}s')
    return renders


def render_plan(bpy, sc, cam, cam_data, set_mood, mist, doc):
    """Top-down orthographic plan of the world rect (image x -> +x east, image y -> +z south)."""
    x0, z0, x1, z1 = doc['map']['world_rect']
    px_per_m = 12
    sc.render.resolution_x = int((x1 - x0) * px_per_m)
    sc.render.resolution_y = int((z1 - z0) * px_per_m)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(x1 - x0, z1 - z0)
    cam.location = ((x0 + x1) / 2, -(z0 + z1) / 2, 200)
    cam.rotation_euler = (0, 0, 0)
    p = set_mood('day')
    mist.hide_render = True
    vol_density = None
    world = sc.world
    v = next(n for n in world.node_tree.nodes if n.type == 'PRINCIPLED_VOLUME')
    vol_density = v.inputs['Density'].default_value
    v.inputs['Density'].default_value = 0.0
    sc.render.use_freestyle = False
    path = os.path.join(OUT, 'millbrook_plan.png')
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    v.inputs['Density'].default_value = vol_density
    sc.render.use_freestyle = True
    doc['map']['plan_px_per_m'] = px_per_m
    print('plan', path)


def main():
    t = time.time()
    isl = LI.build()
    doc = LI.write(isl)
    print(f'layout: {len(doc["instances"])} instances, {len(doc["markers"])} markers, {len(doc["areas"])} areas, '
          f'{len(isl.stream_cells)} stream cells, path {isl.path_len:.1f} m ({time.time() - t:.1f}s)')
    try:
        import bpy  # noqa: F401
    except ImportError:
        print('DONE (json only)')
        return
    if '--json-only' in argv():
        print('DONE')
        return
    renders = blender_main(isl, doc)
    if renders:
        subprocess.call(['python', os.path.join(ROOT, 'tools', 'compare_sheets.py')])
    print('DONE')


main()
