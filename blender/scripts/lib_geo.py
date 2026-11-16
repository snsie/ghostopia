"""Mesh builders, materials, world-scale UVs, prop node trees and glTF export (Blender 5.x).

Coordinates are Blender's: Z up, front = -Y. Every primitive builds in its own temporary bmesh
(bevel, jitter, transform) and is merged into the node it belongs to.

A prop is a tree of nodes:
    Prop(name)                  root empty at the origin (pivot = centre of base on the ground)
      MeshNode(name + '_mesh')  static geometry (several materials)
      MeshNode('INT_door', pivot=hinge)   moving part with its pivot where it moves
      Empty('MARK_sit', loc, yaw), Empty('FX_flame', loc), Light('LIGHT_candle', ...)
Haunt shells (HAUNT_*) and -colonly boxes are generated from the meshes.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
TEX_DIR = os.path.join(ROOT, 'assets', 'textures')

# ----------------------------------------------------------------------------- materials
# name: (texture file or None, uv metres per repeat, base colour factor, roughness, extras)
MATS = {}


def define_mat(name, tex=None, scale=1.0, color=(1, 1, 1, 1), rough=0.85, metal=0.0, emit=None,
               emit_strength=0.0, alpha=1.0, emit_tex=False):
    MATS[name] = dict(tex=tex, scale=scale, color=color, rough=rough, metal=metal, emit=emit,
                      emit_strength=emit_strength, alpha=alpha, emit_tex=emit_tex)


def standard_mats():
    d = define_mat
    d('wood', 'wood_grain.png', 0.6)
    d('wood_dark', 'wood_grain_dark.png', 0.6)
    d('wood_planks', 'wood.png', 0.75)
    d('wood_planks_dark', 'wood_dark.png', 0.75)
    d('wood_weathered', 'wood_weathered.png', 0.75)
    d('bark', 'bark.png', 0.8)
    d('stone', 'stone.png', 0.8)
    d('stone_mossy', 'stone_mossy.png', 0.9)
    d('cobble', 'cobble.png', 0.8)
    d('plaster', 'plaster.png', 1.0)
    d('thatch', 'thatch.png', 0.8)
    d('slate', 'slate.png', 0.8)
    d('iron', 'iron.png', 0.5, rough=0.6, metal=0.5)
    d('brass', 'brass.png', 0.4, rough=0.4, metal=0.8)
    d('wax', 'wax.png', 0.25, rough=0.6)
    d('cloth_plaid', 'cloth_plaid.png', 0.35)
    d('cloth_linen', 'cloth_linen.png', 0.4)
    d('cloth_red', 'cloth_linen.png', 0.4, color=(0.75, 0.25, 0.22, 1))
    d('cloth_purple', 'cloth_linen.png', 0.4, color=(0.46, 0.36, 0.56, 1))
    d('burlap', 'canvas.png', 0.4, color=(0.86, 0.66, 0.42, 1))
    d('stone_smooth', 'stone_smooth.png', 0.8)
    d('cloth_blue', 'cloth_linen.png', 0.4, color=(0.45, 0.5, 0.75, 1))
    d('quilt', 'quilt.png', 0.6)
    d('canvas', 'canvas.png', 1.0)
    d('straw', 'straw.png', 0.4)
    d('pumpkin', 'pumpkin.png', 0.5)
    d('leaf', 'leaf.png', 0.6)
    d('vine', 'leaf.png', 0.4, color=(0.75, 0.9, 0.6, 1))
    d('wisteria', 'wisteria.png', 0.4)
    d('paper', 'paper.png', 0.3)
    d('rug', 'rug.png', 0.0)  # fit
    d('portrait', 'portrait.png', 0.0)  # fit
    d('bone', 'bone.png', 0.3)
    d('dirt', 'dirt.png', 0.8)
    d('grass', 'grass.png', 0.8)
    d('grave_dirt', 'grave_dirt.png', 0.8)
    d('book_red', 'book.png', 0.3, color=(0.7, 0.25, 0.25, 1))
    d('book_purple', 'book.png', 0.3, color=(0.5, 0.32, 0.62, 1))
    d('book_brown', 'book.png', 0.3, color=(0.6, 0.42, 0.3, 1))
    d('ceramic', 'ceramic.png', 0.3)
    d('rope', 'straw.png', 0.2, color=(0.8, 0.65, 0.45, 1))
    d('ink_dark', None, 1, color=(0.12, 0.08, 0.12, 1), rough=0.5)
    d('eye_dark', None, 1, color=(0.06, 0.04, 0.08, 1), rough=0.3)
    d('glass', None, 1, color=(0.7, 0.8, 0.9, 1), rough=0.1, alpha=0.35)
    d('water', None, 1, color=(0.3, 0.5, 0.75, 1), rough=0.1, alpha=0.8)
    # always glowing
    d('FLAME_fire', None, 1, color=(1.0, 0.62, 0.2, 1), emit=(1.0, 0.55, 0.15), emit_strength=6.0)
    d('FLAME_core', None, 1, color=(1.0, 0.92, 0.6, 1), emit=(1.0, 0.9, 0.55), emit_strength=8.0)
    d('FLAME_ember', None, 1, color=(0.9, 0.3, 0.1, 1), emit=(1.0, 0.35, 0.08), emit_strength=3.0)
    d('FLAME_crystal', 'crystal.png', 0.3, color=(1, 1, 1, 1), emit=(0.62, 0.34, 0.95), emit_strength=2.5,
      emit_tex=True)
    d('FLAME_portal', 'portal.png', 0.0, emit=(0.75, 0.4, 1.0), emit_strength=4.0, emit_tex=True)
    d('FLAME_spectral_vein', None, 1, color=(0.35, 0.95, 0.9, 1), emit=(0.35, 0.95, 0.9), emit_strength=3.0)
    # mood-dependent glow
    d('GLOW_window', 'window_glow.png', 0.0, emit=(1.0, 0.7, 0.35), emit_strength=2.5, emit_tex=True)
    d('GLOW_lamp_glass', None, 1, color=(1.0, 0.8, 0.5, 1), rough=0.1, emit=(1.0, 0.62, 0.25), emit_strength=1.4,
      alpha=0.6)
    d('GLOW_jar', None, 1, color=(1.0, 0.75, 0.4, 1), rough=0.1, emit=(1.0, 0.55, 0.2), emit_strength=0.9,
      alpha=0.7)
    # haunt glow + spectral tools
    d('HAUNT_glow', None, 1, color=(0.62, 0.4, 1.0, 1), rough=0.3, emit=(0.55, 0.45, 1.0), emit_strength=2.5,
      alpha=0.16)
    d('HAUNT_eyes', None, 1, color=(0.75, 0.9, 1.0, 1), emit=(0.65, 0.85, 1.0), emit_strength=6.0)
    d('SPECTRAL_blade', 'spectral.png', 0.3, color=(0.85, 0.95, 1.0, 1), rough=0.2, emit=(0.55, 0.85, 1.0),
      emit_strength=0.8, alpha=0.82, emit_tex=True)
    d('SPECTRAL_handle', 'wood.png', 0.5, color=(0.85, 0.92, 1.0, 1), rough=0.6, emit=(0.4, 0.6, 0.8),
      emit_strength=0.25, alpha=0.9)
    d('SPECTRAL_metal', 'iron.png', 0.3, color=(0.85, 0.92, 1.0, 1), rough=0.35, metal=0.3, emit=(0.5, 0.8, 1.0),
      emit_strength=0.15, alpha=0.9)
    d('SPECTRAL_wrap', 'cloth_linen.png', 0.2, color=(0.8, 0.82, 0.9, 1), emit=(0.5, 0.7, 0.9), emit_strength=0.05,
      alpha=0.92)
    d('SPECTRAL_gem', 'crystal.png', 0.2, emit=(0.62, 0.34, 0.95), emit_strength=1.2, alpha=0.9, emit_tex=True)


_mat_cache = {}


def get_mat(name):
    if name in _mat_cache and _mat_cache[name].name in bpy.data.materials:
        return _mat_cache[name]
    spec = MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = spec['color']
    bsdf.inputs['Roughness'].default_value = spec['rough']
    bsdf.inputs['Metallic'].default_value = spec['metal']
    img_node = None
    if spec['tex']:
        path = os.path.join(TEX_DIR, spec['tex'])
        img = bpy.data.images.get(spec['tex']) or bpy.data.images.load(path, check_existing=True)
        img_node = nt.nodes.new('ShaderNodeTexImage')
        img_node.image = img
        img_node.interpolation = 'Linear'
        col = spec['color']
        if col[:3] != (1, 1, 1):
            mix = nt.nodes.new('ShaderNodeMix')
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs['Factor'].default_value = 1.0
            nt.links.new(img_node.outputs['Color'], mix.inputs['A'])
            mix.inputs['B'].default_value = col
            nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
        else:
            nt.links.new(img_node.outputs['Color'], bsdf.inputs['Base Color'])
    if spec['emit']:
        bsdf.inputs['Emission Color'].default_value = (*spec['emit'], 1)
        bsdf.inputs['Emission Strength'].default_value = spec['emit_strength']
        if spec['emit_tex'] and img_node is not None:
            nt.links.new(img_node.outputs['Color'], bsdf.inputs['Emission Color'])
    if spec['alpha'] < 1.0:
        bsdf.inputs['Alpha'].default_value = spec['alpha']
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
        try:
            m.blend_method = 'BLEND'
        except Exception:
            pass
    elif spec['tex'] and name in ('leaf_cut',):
        nt.links.new(img_node.outputs['Alpha'], bsdf.inputs['Alpha'])
    m.diffuse_color = spec['color']
    if name.startswith('HAUNT_'):
        m.use_backface_culling = True
        try:
            m.use_transparency_overlap = False
        except Exception:
            pass
    _mat_cache[name] = m
    return m


# ----------------------------------------------------------------------------- primitives
_rng = random.Random(7)


def seed(s):
    _rng.seed(s)


def _xf(bm, loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    M = Matrix.Translation(Vector(loc)) @ Euler(rot, 'XYZ').to_matrix().to_4x4()
    if scale is not None:
        M = M @ Matrix.Diagonal((*scale, 1))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])


def _bevel(bm, width, segs=2, angle=None):
    if width <= 0:
        return
    edges = bm.edges[:]
    if angle is not None:
        edges = [e for e in edges if e.is_manifold and e.calc_face_angle(0) > angle]
    if not edges:
        return
    try:
        bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type='OFFSET', segments=segs, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
    except Exception as e:  # noqa
        print('bevel failed', e)


def _jitter(bm, amount):
    if amount <= 0:
        return
    for v in bm.verts:
        v.co += Vector((_rng.uniform(-amount, amount), _rng.uniform(-amount, amount), _rng.uniform(-amount, amount)))


def bm_box(size, bevel=0.03, segs=2, jitter=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts[:])
    _bevel(bm, min(bevel, min(size) * 0.45), segs)
    _jitter(bm, jitter)
    return bm


def bm_cyl(r1, r2, depth, segs=10, bevel=0.02, bsegs=1, jitter=0.0, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    if bevel > 0:
        _bevel(bm, min(bevel, depth * 0.4, max(r1, r2) * 0.4), bsegs, angle=math.radians(50))
    _jitter(bm, jitter)
    return bm


def bm_sphere(r, segs=10, rings=6, jitter=0.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    _jitter(bm, jitter)
    return bm


def bm_lathe(profile, segs=12, jitter=0.0, close_top=True, close_bottom=True):
    """profile: list of (radius, z) from bottom to top."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(segs):
            a = i / segs * 2 * math.pi
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new([a[i], a[j], b[j], b[i]])
    if close_bottom and profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if close_top and profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _jitter(bm, jitter)
    return bm


def bm_extrude2d(outline, thickness, bevel=0.015, segs=1, jitter=0.0):
    """outline: list of (x, z) in the XZ plane (front view), extruded along Y, centred on y=0."""
    bm = bmesh.new()
    front = [bm.verts.new((x, -thickness / 2, z)) for x, z in outline]
    back = [bm.verts.new((x, thickness / 2, z)) for x, z in outline]
    n = len(outline)
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([front[i], back[i], back[j], front[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # triangulate n-gons for robust export
    if bevel > 0:
        _bevel(bm, min(bevel, thickness * 0.45), segs, angle=math.radians(30))
    _jitter(bm, jitter)
    return bm


def bm_tube(points, radius, segs=6, taper=1.0, cap=True):
    """Tube along a polyline of Vector-like points; radius tapers to radius*taper at the end."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    n = len(pts)
    prev_side = None
    for i, p in enumerate(pts):
        if i == 0:
            d = (pts[1] - pts[0])
        elif i == n - 1:
            d = (pts[-1] - pts[-2])
        else:
            d = (pts[i + 1] - pts[i - 1])
        d.normalize()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        side = d.cross(up).normalized()
        if prev_side is not None and side.dot(prev_side) < 0:
            side = -side
        prev_side = side
        up2 = side.cross(d).normalized()
        r = radius * (1 + (taper - 1) * i / max(1, n - 1))
        ring = [bm.verts.new(p + (side * math.cos(a) + up2 * math.sin(a)) * r)
                for a in [k / segs * 2 * math.pi for k in range(segs)]]
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(segs):
            m = (k + 1) % segs
            bm.faces.new([a[k], a[m], b[m], b[k]])
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def bm_prism(w, d, h, bevel=0.02):
    """Triangular prism (gable): base w (x) by d (y), apex at height h centred."""
    bm = bm_extrude2d([(-w / 2, 0), (w / 2, 0), (0, h)], d, bevel=bevel)
    return bm


# ----------------------------------------------------------------------------- nodes
class Node:
    def __init__(self, name, kind='empty', pivot=(0, 0, 0), rot=(0, 0, 0)):
        self.name = name
        self.kind = kind
        self.pivot = Vector(pivot)
        self.rot = rot  # applied to the object (mesh geometry is stored un-rotated around pivot)
        self.children = []
        self.props = {}

    def add(self, child):
        self.children.append(child)
        return child


class MeshNode(Node):
    """Mesh geometry is given in PROP space (absolute); stored relative to the pivot."""

    def __init__(self, name, pivot=(0, 0, 0), haunt=False, smooth_angle=40):
        super().__init__(name, 'mesh', pivot)
        self.bm = bmesh.new()
        self.mats = []
        self.pieces = []  # (faces, uvmode, offset)
        self.haunt = haunt
        self.smooth_angle = smooth_angle
        self.cols = []  # collision boxes (size, loc in prop space) that move with this node

    def _mat_index(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def put(self, src, mat, loc=(0, 0, 0), rot=(0, 0, 0), scale=None, uv='box', smooth=True):
        _xf(src, loc, rot, scale)
        mi = self._mat_index(mat)
        vmap = {}
        for v in src.verts:
            vmap[v] = self.bm.verts.new(v.co - self.pivot)
        faces = []
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mi
            nf.smooth = smooth
            faces.append(nf)
        src.free()
        self.pieces.append((faces, uv, (_rng.random(), _rng.random())))
        return faces

    # convenience wrappers
    def box(self, mat, size, loc, rot=(0, 0, 0), bevel=0.03, segs=2, jitter=0.0, uv='box'):
        return self.put(bm_box(size, bevel, segs, jitter), mat, loc, rot, uv=uv)

    def cyl(self, mat, r1, r2, depth, loc, rot=(0, 0, 0), segs=10, bevel=0.02, jitter=0.0, cap=True):
        return self.put(bm_cyl(r1, r2, depth, segs, bevel, 1, jitter, cap), mat, loc, rot)

    def sphere(self, mat, r, loc, scale=(1, 1, 1), segs=10, rings=6, jitter=0.0, rot=(0, 0, 0)):
        return self.put(bm_sphere(r, segs, rings, jitter), mat, loc, rot, scale)

    def lathe(self, mat, profile, loc, segs=12, rot=(0, 0, 0), jitter=0.0):
        return self.put(bm_lathe(profile, segs, jitter), mat, loc, rot)

    def ext(self, mat, outline, thickness, loc, rot=(0, 0, 0), bevel=0.015, uv='box', jitter=0.0):
        return self.put(bm_extrude2d(outline, thickness, bevel, 1, jitter), mat, loc, rot, uv=uv)

    def tube(self, mat, points, radius, segs=6, taper=1.0):
        return self.put(bm_tube(points, radius, segs, taper), mat)

    def finalize_uv(self):
        bm = self.bm
        uvl = bm.loops.layers.uv.verify()
        bm.normal_update()
        for faces, mode, off in self.pieces:
            if not faces:
                continue
            # major axis of the piece: wood grain / plank direction follows the long side
            vs = [l.vert.co for f in faces for l in f.loops]
            ext = [max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3)]
            major = max(range(3), key=lambda i: ext[i])
            if mode in ('fit', 'fit_top'):
                xs = [l.vert.co.x for f in faces for l in f.loops]
                zs = [(l.vert.co.z if mode == 'fit' else l.vert.co.y) for f in faces for l in f.loops]
                x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
                x0 += self.pivot.x
                x1 += self.pivot.x
                pz = self.pivot.z if mode == 'fit' else self.pivot.y
                z0 += pz
                z1 += pz
            for f in faces:
                if not f.is_valid:
                    continue
                n = f.normal
                ax = max(range(3), key=lambda i: abs(n[i]))
                sc = MATS[self.mats[f.material_index]]['scale'] or 1.0
                for l in f.loops:
                    c = l.vert.co + self.pivot
                    if mode == 'fit_top':
                        u = (c.x - x0) / max(1e-6, x1 - x0)
                        v = (c.y - z0) / max(1e-6, z1 - z0)
                    elif mode == 'fit':
                        u = (c.x - x0) / max(1e-6, x1 - x0)
                        v = (c.z - z0) / max(1e-6, z1 - z0)
                        if n.y > 0.5:
                            u = 1 - u
                    elif ax == 2:
                        u, v = c.x / sc + off[0], c.y / sc + off[1]
                        if major == 1:
                            u, v = v, u
                    elif ax == 0:
                        u, v = (c.y if n.x > 0 else -c.y) / sc + off[0], c.z / sc + off[1]
                        if major == 2:
                            u, v = v, u
                    else:
                        u, v = (-c.x if n.y > 0 else c.x) / sc + off[0], c.z / sc + off[1]
                        if major == 2:
                            u, v = v, u
                    l[uvl].uv = (u, v)


class LightNode(Node):
    def __init__(self, name, loc, energy=10.0, color=(1.0, 0.7, 0.4), radius=0.05):
        super().__init__(name, 'light', loc)
        self.energy = energy
        self.color = color
        self.radius = radius


class Prop(Node):
    def __init__(self, name):
        super().__init__(name, 'empty', (0, 0, 0))
        self.main = self.add(MeshNode(name + '_mesh'))
        self.collision = []  # list of (size, loc)
        self.haunt = False
        self.extras = {}

    def mesh(self):
        return self.main


def empty(name, loc=(0, 0, 0), yaw_deg=0.0, size=0.2):
    n = Node(name, 'empty', loc, rot=(0, 0, math.radians(yaw_deg)))
    n.props['size'] = size
    return n


# ----------------------------------------------------------------------------- build into Blender
def _mesh_object(node, coll):
    node.finalize_uv()
    me = bpy.data.meshes.new(node.name)
    node.bm.to_mesh(me)
    for m in node.mats:
        me.materials.append(get_mat(m))
    try:
        me.set_sharp_from_angle(angle=math.radians(node.smooth_angle))
    except Exception:
        pass
    ob = bpy.data.objects.new(node.name, me)
    coll.objects.link(ob)
    return ob


def _haunt_shell(src_ob, name, coll, offset=0.018):
    me = src_ob.data.copy()
    me.name = name
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(get_mat('HAUNT_glow'))
    for p in me.polygons:
        p.material_index = 0
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def build(prop, coll=None):
    """Create Blender objects for a Prop tree. Returns the root object."""
    coll = coll or bpy.context.scene.collection

    def rec(node, parent_ob, parent_abs, prefix_kind):
        if node.kind == 'mesh':
            if not node.bm.faces:
                return None
            ob = _mesh_object(node, coll)
        elif node.kind == 'light':
            ld = bpy.data.lights.new(node.name, 'POINT')
            ld.energy = node.energy
            ld.color = node.color
            ld.shadow_soft_size = node.radius
            ob = bpy.data.objects.new(node.name, ld)
            coll.objects.link(ob)
        else:
            ob = bpy.data.objects.new(node.name, None)
            ob.empty_display_size = node.props.get('size', 0.2)
            ob.empty_display_type = 'PLAIN_AXES'
            coll.objects.link(ob)
        ob.parent = parent_ob
        ob.location = node.pivot - parent_abs
        ob.rotation_euler = node.rot
        for k, v in node.props.items():
            if k != 'size':
                ob[k] = v
        if node.kind == 'mesh' and (node.haunt or (prefix_kind and node.name.startswith('INT_'))):
            if getattr(prop, 'haunt', False):
                hname = 'HAUNT_' + node.name.replace('INT_', '').replace(prop.name + '_mesh', prop.name)
                sh = _haunt_shell(ob, hname, coll)
                sh.parent = ob
        for i, (size, loc) in enumerate(getattr(node, 'cols', [])):
            bm = bm_box(size, 0)
            _xf(bm, Vector(loc) - node.pivot)
            cname = f'{node.name}_col{i}-colonly'
            me = bpy.data.meshes.new(cname)
            bm.to_mesh(me)
            bm.free()
            cob = bpy.data.objects.new(cname, me)
            coll.objects.link(cob)
            cob.parent = ob
            cob.display_type = 'WIRE'
            cob.hide_render = True
        for c in node.children:
            rec(c, ob, node.pivot, prefix_kind)
        return ob

    root = rec(prop, None, Vector((0, 0, 0)), True)
    # main mesh haunt shell
    if prop.haunt:
        main = bpy.data.objects.get(prop.main.name)
        if main is not None and main.type == 'MESH':
            sh = _haunt_shell(main, 'HAUNT_static', coll)
            sh.parent = main
    for i, (size, loc) in enumerate(prop.collision):
        bm = bm_box(size, 0)
        _xf(bm, loc)
        me = bpy.data.meshes.new(f'{prop.name}_col{i}-colonly')
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f'{prop.name}_col{i}-colonly', me)
        coll.objects.link(ob)
        ob.parent = root
        ob.display_type = 'WIRE'
        ob.hide_render = True
    for k, v in prop.extras.items():
        root[k] = v
    return root


def hierarchy(root):
    out = [root]
    for c in root.children:
        out += hierarchy(c)
    return out


def export_gltf(root, path):
    """Export one prop hierarchy as glTF Separate; lights RAW x 1/30; textures referenced in place."""
    objs = hierarchy(root)
    lights = [o for o in objs if o.type == 'LIGHT']
    saved = [(o, o.data.energy) for o in lights]
    for o, e in saved:
        o.data.energy = e / 30.0
    hidden = [(o, o.hide_render) for o in objs]
    for o in objs:
        o.hide_render = False
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLTF_SEPARATE', use_selection=True,
                              export_yup=True, export_apply=True, export_lights=True,
                              export_import_convert_lighting_mode='RAW', export_keep_originals=True,
                              export_extras=True, export_animations=False, export_cameras=False)
    for o, e in saved:
        o.data.energy = e
    for o, h in hidden:
        o.hide_render = h


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)


def new_collection(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c
