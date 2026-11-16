"""Task 4 renders: the task3 island scene (build_island.blender_main) plus the villagers at their schedule
positions for each shot's hour, the worker ghosts and stand-ins for the effects (smoke, fireflies, wisps,
spray, sparkles). Called by build_population.py inside Blender; writes renders/task4/<camera>_<mood>.png and
blender/millbrook_population.blend.
"""
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_population as LP  # noqa: E402

ROOT = LP.ROOT
OUT = os.path.join(ROOT, 'renders', 'task4')

# Same framings as task3 (build_island.CAMERAS); `hours` = clock hour per mood (unwrapped: 17..41) used to pose
# everyone from their schedules. compare_sheets.py --task task4 reads this dict as text.
CAMERAS = {
    'millbrook': dict(pos=(118.0, 36.0, 140.0), look=(116.5, 20.0, 94.0), lens=24,
                      moods=['night', 'dusk', 'day'], hours={'night': 21.75, 'dusk': 18.5, 'day': 36.0},
                      concept={'night': 'locations/millbrook_night.png', 'dusk': 'locations/millbrook_dusk.png',
                               'day': 'locations/millbrook_day.png'}),
    'square_close': dict(pos=(117.0, 27.5, 120.0), look=(112.0, 21.5, 99.0), lens=28,
                         moods=['night', 'dusk'], hours={'night': 21.75, 'dusk': 18.5},
                         concept={'night': 'locations/millbrook_night.png', 'dusk': 'locations/millbrook_dusk.png'}),
    'cottage_interior': dict(struct='pip_cottage', rel_pos=(-0.4, 5.6, 6.9), rel_look=(-1.0, 0.3, 0.2), lens=20,
                             moods=['night', 'day'], cutaway='front_roof', hours={'night': 21.5, 'day': 30.58},
                             concept={'night': 'locations/cottage_interior_night.png',
                                      'day': 'locations/cottage_interior_day.png'}),
    'mill': dict(struct='windmill', rel_pos=(-5.0, 4.5, 16.5), rel_look=(-0.8, 3.6, 0.0), lens=22,
                 moods=['night'], cutaway='front_ground', hours={'night': 23.5},
                 concept={'night': 'locations/mill_night.png'}),
    'graveyard': dict(pos=(49.0, 35.0, 99.0), look=(25.5, 29.0, 91.0), lens=26, moods=['night', 'day'],
                      hours={'night': 23.0, 'day': 36.0},
                      concept={'night': 'locations/graveyard_night.png', 'day': 'locations/graveyard_day.png'}),
}

FRAME = {'idle': 0, 'walk': 5, 'sit': 0, 'rock_in_chair': 12, 'sleep': 0, 'sweep': 10, 'work_field': 14,
         'relight_candle': 30, 'look_over_shoulder': 22, 'call_out': 26, 'serve_drinks': 14, 'idle_float': 10,
         'work': 12}
# held items Godot attaches from task1 props: (prop, socket, offset down in metres)
ATTACH = {'bucket': ('bucket', 'HELD_R', 0.42), 'broom': ('broom', 'HELD_R', 0.75), 'lantern': ('lantern', 'HELD_L', 0.40),
          'candle': ('candle', 'HELD_R', 0.02)}
SCENE_FRAME = 1000


def render_all(doc, steps):
    import build_island as BI
    import lib_island as LI
    isl = LI.build()
    import json
    layout = json.load(open(LP.LAYOUT, encoding='utf-8'))
    state = {}

    def hook(event, ctx, **kw):
        if event == 'setup':
            setup(ctx, doc, steps, state)
        elif event == 'shot':
            shot(ctx, doc, steps, state, kw['name'], kw['mood'], kw['cd'])
        elif event == 'save':
            shot(ctx, doc, steps, state, 'millbrook', 'night', CAMERAS['millbrook'])
    renders = BI.blender_main(isl, layout, cameras=CAMERAS, out=OUT, hook=hook, plan=False,
                              blend_path=os.path.join(ROOT, 'blender', 'millbrook_population.blend'))
    return renders


# ============================================================================== setup
def setup(ctx, doc, steps, state):
    bpy = ctx['bpy']
    t0 = time.time()
    coll = bpy.data.collections.new('POPULATION')
    ctx['sc'].collection.children.link(coll)
    state['coll'] = coll
    state['chars'] = {}
    state['default'] = {v['id']: v['default_item'] for v in doc['villagers']}
    for v in doc['villagers']:
        state['chars'][v['id']] = import_char(ctx, v['character'], coll)
    state['workers'] = {}
    for f in doc['fx']['list']:
        if f['type'] == 'worker_ghost':
            state['workers'][f['id']] = (import_char(ctx, f['character'], coll), f)
    state['attach'] = {}
    state['fx'] = build_fx(ctx, doc, coll)
    print(f'population scene: {len(state["chars"])} villagers, {len(state["workers"])} workers ({time.time() - t0:.1f}s)')


def import_char(ctx, name, coll):
    bpy = ctx['bpy']
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, 'assets', 'characters', name + '.gltf'),
                              export_import_convert_lighting_mode='RAW')
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for uc in list(o.users_collection):
            uc.objects.unlink(o)
        coll.objects.link(o)
        if o.type == 'LIGHT':
            o.data.energy *= 30.0
            o['base_energy'] = o.data.energy
            ctx['lights_all'].append(o)
        if o.parent is None and o.type == 'MESH':     # importer's bone-shape icosphere
            o.hide_render = o.hide_viewport = True
        if o.name.startswith(('HAUNT_', 'MATERIAL_')) or o.name.endswith('-colonly'):
            o.hide_render = True
    rig = next(o for o in new if o.type == 'ARMATURE')
    items = [o for o in new if o.name.startswith('ITEM_')]
    sockets = {o.name.split('.')[0]: o for o in new if o.name.startswith('HELD_')}
    return dict(name=name, rig=rig, objs=new, items=items, sockets=sockets)


def pose(ch, clip, frame):
    """Show `clip` at `frame` when the scene is at SCENE_FRAME: mute every other NLA track, slide the strip."""
    ad = ch['rig'].animation_data
    ad.action = None
    found = False
    for tr in ad.nla_tracks:
        tr.mute = tr.name != clip
        if tr.name == clip:
            found = True
            st = tr.strips[0]
            length = st.frame_end - st.frame_start
            st.frame_start_ui = SCENE_FRAME - frame - 1
            st.extrapolation = 'HOLD'
            _ = length
    if not found:
        raise KeyError(f'{ch["name"]} has no clip {clip}')


def place(ch, pos, yaw, show=True):
    rig = ch['rig']
    rig.location = (pos[0], -pos[2], pos[1])
    rig.rotation_mode = 'XYZ'
    rig.rotation_euler = (0.0, 0.0, math.radians(yaw))
    for o in ch['objs']:
        if o.parent is None and o.type == 'MESH':
            continue
        if o.name.startswith(('HAUNT_', 'MATERIAL_')) or o.name.endswith('-colonly'):
            continue
        o.hide_render = not show


def attach(ctx, state, vid, ch, item):
    """Task1 prop parented to a hand socket (Godot does the same at runtime)."""
    bpy = ctx['bpy']
    key = (vid, item)
    if key in state['attach']:
        return state['attach'][key]
    prop, _, down = ATTACH[item]
    sock = LP.held_socket(ctx_char_info(None, {'character': ch['name']}), item, state['default'][vid])
    c = ctx['prop_coll'](prop)
    e = bpy.data.objects.new(f'HELDITEM_{vid}_{item}', None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = c
    state['coll'].objects.link(e)
    s = ch['sockets'].get(sock) or ch['sockets'].get('HELD_R')
    e.parent = s
    e.location = (0.0, 0.0, -down)
    state['attach'][key] = e
    return e


# ============================================================================== shots
def shot(ctx, doc, steps, state, name, mood, cd):
    bpy = ctx['bpy']
    h = cd['hours'][mood]
    vmap = {v['id']: v for v in doc['villagers']}
    for e in state['attach'].values():
        e.hide_render = True
    print(f'shot {name} {mood} at {LP.hhmm(h)}:')
    for vid, ch in state['chars'].items():
        pos, yaw, clip, st = LP.place_at_hour(steps[vid], h)
        v = vmap[vid]
        place(ch, pos, yaw)
        pose(ch, clip, FRAME.get(clip, 0))
        held = st.get('held')
        cinfo = ctx_char_info(doc, v)
        show_default = clip in cinfo['item_clips'] and (held in (None, v['default_item']) or
                                                       (vid == 'bram' and held == 'lantern'))
        if st['activity'] == 'sleep':
            show_default = False
        for o in ch['items']:
            o.hide_render = not show_default
            for c in o.children_recursive:
                c.hide_render = not show_default
        if held and held != v['default_item'] and held in ATTACH:
            attach(ctx, state, vid, ch, held).hide_render = False
        print(f'   {vid:7s} {st["activity"]:18s} {clip:18s} held={held} at {LP.r2(pos, 1)} yaw {yaw}')
    for wid, (ch, f) in state['workers'].items():
        show = mood in f['moods']
        place(ch, f['pos'], f['yaw'], show)
        pose(ch, f['animation'], FRAME.get(f['animation'], 0))
    for grp, objs in state['fx'].items():
        moods = objs[0]
        for o in objs[1]:
            o.hide_render = mood not in moods
    ctx['sc'].frame_set(SCENE_FRAME)


def ctx_char_info(doc, v):
    import json
    cache = ctx_char_info.__dict__.setdefault('c', {})
    if not cache:
        cache.update(json.load(open(LP.CHARS, encoding='utf-8'))['characters'])
    return cache[v['character']]


# ============================================================================== effect stand-ins
def mat_emit(bpy, name, hexcol, strength, alpha=1.0, base=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    h = hexcol.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)
    b.inputs['Base Color'].default_value = (*(base or lin), 1)
    b.inputs['Emission Color'].default_value = (*lin, 1)
    b.inputs['Emission Strength'].default_value = strength
    b.inputs['Roughness'].default_value = 0.9
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
    return m


def blobs(bpy, name, spheres, mat, coll, subdiv=1):
    """One mesh of many icospheres: spheres = [(x, y, z) Godot, radius]."""
    import bmesh
    from mathutils import Matrix
    bm = bmesh.new()
    for (x, y, z), r in spheres:
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r,
                                   matrix=Matrix.Translation((x, -z, y)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.visible_shadow = False
    try:
        ob.visible_volume_scatter = False
    except Exception:
        pass
    coll.objects.link(ob)
    return ob


def build_fx(ctx, doc, coll):
    bpy = ctx['bpy']
    rnd = random.Random(2026)
    groups = {}
    fx = doc['fx']['list']

    def add(key, moods, ob):
        groups.setdefault(key, (moods, []))[1].append(ob)

    smoke_m = mat_emit(bpy, 'FX_smoke', '#8e8aa6', 0.12, alpha=0.18)
    fly_m = mat_emit(bpy, 'FX_firefly', '#d6ff7a', 14.0)
    wisp_m = mat_emit(bpy, 'FX_wisp', '#a46bff', 9.0)
    spray_m = mat_emit(bpy, 'FX_spray', '#e6f2ff', 0.6, alpha=0.35)
    spark_m = mat_emit(bpy, 'FX_sparkle', '#cfe8ff', 10.0)
    gw_m = mat_emit(bpy, 'FX_gravewisp', '#bfe4ff', 6.0)
    for f in fx:
        t = f['type']
        if t == 'chimney_smoke':
            x, y, z = f['pos']
            sp = []
            for k in range(12):
                a = k / 11
                sp.append(((x + 0.16 * k + rnd.uniform(-0.15, 0.15), y + 0.15 + k * 0.38 + rnd.uniform(-0.1, 0.1),
                            z + 0.06 * k + rnd.uniform(-0.15, 0.15)), 0.22 + a * 0.5))
            add('smoke', ['dusk', 'night', 'dawn', 'day'], blobs(bpy, f['id'], sp, smoke_m, coll, 2))
        elif t == 'fireflies':
            x0, y0, z0, x1, y1, z1 = f['box']
            sp = [((rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(z0, z1)), 0.045) for _ in range(f['count'])]
            add('fireflies', f['moods'], blobs(bpy, f['id'], sp, fly_m, coll, 1))
        elif t in ('ore_wisps', 'portal_glow'):
            x, y, z = f['pos']
            n = 3 if t == 'ore_wisps' else 7
            sp = [((x + rnd.uniform(-0.35, 0.35), y + rnd.uniform(0.0, 1.4), z + rnd.uniform(-0.35, 0.35)),
                   rnd.uniform(0.04, 0.09)) for _ in range(n)]
            add('wisps', f['moods'], blobs(bpy, f['id'], sp, wisp_m, coll, 1))
            if t == 'portal_glow':
                ld = bpy.data.lights.new(f['id'] + '_light', 'POINT')
                ld.color = (0.64, 0.42, 1.0)
                ld.energy = 120.0
                ld.shadow_soft_size = 0.5
                lo = bpy.data.objects.new(f['id'] + '_light', ld)
                lo.location = (x + 0.8, -z, y)
                coll.objects.link(lo)
                add('portal_light', f['moods'], lo)
        elif t == 'waterfall_spray':
            x, y, z = f['pos']
            sp = [((x + rnd.uniform(-1.0, 1.0), y + rnd.uniform(-0.1, 0.9), z + rnd.uniform(-0.6, 1.0)),
                   rnd.uniform(0.12, 0.3)) for _ in range(14)]
            add('spray', f['moods'], blobs(bpy, f['id'], sp, spray_m, coll, 1))
        elif t == 'water_sparkle':
            sp = []
            for p in f['points']:
                for _ in range(3):
                    sp.append(((p[0] + rnd.uniform(-1.2, 1.2), p[1], p[2] + rnd.uniform(-1.2, 1.2)), 0.035))
            add('sparkle', ['dusk', 'night', 'dawn'], blobs(bpy, f['id'], sp, spark_m, coll, 1))
    # gravestone wisps: above each gravestone instance
    sp = []
    for e in ctx['inst_objs']:
        if e.instance_collection and e.instance_collection.name.startswith('P_gravestone'):
            x, z, y = e.location.x, -e.location.y, e.location.z
            sp += [((x + rnd.uniform(-0.3, 0.3), y + 1.2 + rnd.uniform(0, 0.8), z + rnd.uniform(-0.3, 0.3)), 0.05)
                   for _ in range(2)]
    if sp:
        add('grave_wisps', ['night'], blobs(bpy, 'FX_grave_wisps', sp, gw_m, coll, 1))
    return groups
