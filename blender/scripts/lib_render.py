"""Preview rendering: moods (studio/day/dusk/night/fading), framed ortho cameras, Freestyle ink lines."""
import math
import os

import bpy
from mathutils import Vector

MOODS = {
    #          sun energy, sun colour,        sun rot (deg x, z), world colour,        world str, exposure
    'studio': (3.2, (1.0, 0.97, 0.92), (50, -35), (0.50, 0.47, 0.50), 1.0, 0.0),
    'day':    (4.0, (1.0, 0.97, 0.90), (45, -35), (0.62, 0.70, 0.82), 1.0, 0.2),
    'dusk':   (2.0, (1.0, 0.70, 0.55), (72, -60), (0.40, 0.30, 0.50), 0.9, 0.0),
    'night':  (1.5, (0.55, 0.62, 1.0), (40, -30), (0.13, 0.11, 0.32), 1.0, 0.35),
    'fading': (1.6, (0.8, 0.8, 0.85), (50, -35), (0.30, 0.30, 0.34), 1.0, 0.0),
}

BG = {'studio': (0.47, 0.43, 0.45, 1)}


def setup_scene(res=(512, 512), samples=24, freestyle=True, line=1.1, transparent=False):
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_EEVEE'
    except TypeError as e:
        print('engine', e)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.eevee.taa_render_samples = samples
    except Exception:
        pass
    for attr, val in (('use_shadows', True), ('use_raytracing', False), ('shadow_ray_count', 1)):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except Exception:
        pass
    sc.render.use_freestyle = freestyle
    if freestyle:
        sc.render.line_thickness_mode = 'ABSOLUTE'
        sc.render.line_thickness = line
        vl = sc.view_layers[0]
        vl.use_freestyle = True
        fs = vl.freestyle_settings
        fs.crease_angle = math.radians(120)
        if not fs.linesets:
            fs.linesets.new('ink')
        ls = fs.linesets[0]
        ls.select_by_visibility = True
        ls.select_silhouette = True
        ls.select_border = False  # voxel quads are separate faces; borders would ink every block
        ls.select_crease = True
        ls.select_by_face_marks = True
        ls.face_mark_negation = 'EXCLUSIVE'
        ls.face_mark_condition = 'ONE'
        ls.linestyle.color = (0.16, 0.10, 0.17)
        ls.linestyle.thickness = line
        ls.linestyle.alpha = 0.85
    return sc


def set_mood(mood):
    sc = bpy.context.scene
    energy, col, (rx, rz), wcol, wstr, expo = MOODS[mood]
    sun = bpy.data.objects.get('KEY_sun')
    if sun is None:
        ld = bpy.data.lights.new('KEY_sun', 'SUN')
        sun = bpy.data.objects.new('KEY_sun', ld)
        sc.collection.objects.link(sun)
    sun.data.energy = energy
    sun.data.color = col
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    world = sc.world or bpy.data.worlds.new('World')
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*wcol, 1)
    bg.inputs['Strength'].default_value = wstr
    sc.view_settings.exposure = expo
    # fill light so shadow sides are not black (painted look has soft shadows)
    fill = bpy.data.objects.get('KEY_fill')
    if fill is None:
        ld = bpy.data.lights.new('KEY_fill', 'SUN')
        fill = bpy.data.objects.new('KEY_fill', ld)
        sc.collection.objects.link(fill)
    fill.data.energy = energy * 0.25
    fill.data.color = (0.75, 0.8, 1.0) if mood != 'dusk' else (0.6, 0.55, 0.9)
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(60), 0, math.radians(150))
    # lamps/candles: brighter at night
    for ob in sc.objects:
        if ob.type == 'LIGHT' and ob.name.startswith('LIGHT_'):
            base = ob.get('base_energy', ob.data.energy)
            ob['base_energy'] = base
            ob.data.energy = base * (1.0 if mood in ('night', 'dusk') else 0.3)


def mesh_bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    found = False
    for ob in objs:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
            found = True
    if not found:
        return Vector((-1, -1, 0)), Vector((1, 1, 2))
    return lo, hi


def frame_camera(objs, direction=(-0.75, -1.0, 0.8), margin=1.12, ortho=True, lens=50):
    sc = bpy.context.scene
    cam = bpy.data.objects.get('PREVIEW_cam')
    if cam is None:
        cd = bpy.data.cameras.new('PREVIEW_cam')
        cam = bpy.data.objects.new('PREVIEW_cam', cd)
        sc.collection.objects.link(cam)
    sc.camera = cam
    bpy.context.view_layer.update()
    lo, hi = mesh_bounds(objs)
    centre = (lo + hi) / 2
    d = Vector(direction).normalized()
    size = (hi - lo).length
    cam.location = centre + d * (size * 3 + 5)
    rot = (-d).to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot.to_euler()
    cam.data.clip_end = size * 10 + 100
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    xs, ys = [], []
    for x in (lo.x, hi.x):
        for y in (lo.y, hi.y):
            for z in (lo.z, hi.z):
                p = inv @ Vector((x, y, z))
                xs.append(p.x)
                ys.append(p.y)
    ex, ey = max(xs) - min(xs), max(ys) - min(ys)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    # recentre in camera plane
    cam.location = cam.matrix_world @ Vector((cx, cy, 0))
    aspect = sc.render.resolution_x / sc.render.resolution_y
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = max(ex, ey * aspect) * margin
    else:
        cam.data.type = 'PERSP'
        cam.data.lens = lens
    return cam


def render(path):
    sc = bpy.context.scene
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def ground(size=40, z=0.0, color=(0.47, 0.43, 0.45, 1), name='PREVIEW_ground'):
    """Neutral matte ground plane that catches shadows (like the grey concept sheets)."""
    ob = bpy.data.objects.get(name)
    if ob is None:
        me = bpy.data.meshes.new(name)
        h = size / 2
        me.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = color
        b.inputs['Roughness'].default_value = 1.0
        me.materials.append(m)
    ob.location.z = z
    return ob
