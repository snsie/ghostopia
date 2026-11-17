"""Renders the spectral tool glTFs (all tiers) to transparent 128 px icons for the hotbar (task5).

    blender -b --factory-startup -P blender/scripts/render_icons.py   -> assets/ui/icons/<tool>_t<n>.png
"""
import math
import os

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'ui', 'icons')
TOOLS = ['scythe', 'shovel', 'sledgehammer']


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        try:
            sc.render.engine = 'BLENDER_EEVEE'
        except TypeError:
            pass
    sc.render.resolution_x = 128
    sc.render.resolution_y = 128
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (0.5, 0.55, 0.7, 1)
    bg.inputs[1].default_value = 0.8
    sc.world = world
    return sc


def render(tool, tier):
    sc = reset()
    path = os.path.join(ROOT, 'assets', 'props', f'{tool}_t{tier}.gltf')
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in sc.objects if o.type == 'MESH']
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    center = (lo + hi) / 2
    size = max(hi - lo)
    # Boost emission/opacity a little so the translucent spectral tools read as icons.
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        p = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if p and 'Alpha' in p.inputs:
            p.inputs['Alpha'].default_value = max(0.8, p.inputs['Alpha'].default_value)
    cam_data = bpy.data.cameras.new('cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = size * 1.12
    cam = bpy.data.objects.new('cam', cam_data)
    sc.collection.objects.link(cam)
    d = Vector((1.0, -1.0, 0.25)).normalized()
    cam.location = center + d * size * 3
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    # roll so the tool lies diagonally (handle bottom-left, head top-right)
    cam.rotation_euler.rotate_axis('Z', math.radians(-38))
    sc.camera = cam
    light = bpy.data.lights.new('key', 'SUN')
    light.energy = 3.0
    lo_ = bpy.data.objects.new('key', light)
    lo_.rotation_euler = (math.radians(40), 0, math.radians(30))
    sc.collection.objects.link(lo_)
    sc.render.filepath = os.path.join(OUT, f'{tool}_t{tier}.png')
    bpy.ops.render.render(write_still=True)
    print('icon', sc.render.filepath)


def main():
    os.makedirs(OUT, exist_ok=True)
    for t in TOOLS:
        for tier in range(1, 5):
            render(t, tier)


main()
