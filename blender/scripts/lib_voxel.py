"""Voxel helpers: blocks.json access, blueprint grids (Godot axes), RLE, and a Blender preview mesher.

Grid convention (decisions.md): numpy array g[x, y, z] of palette strings or block indices, Godot axes
(x east, y up, z south = front). Blender position of Godot point (x, y, z) is (x, -z, y).
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BLOCKS_JSON = os.path.join(ROOT, 'assets', 'blocks', 'blocks.json')

_doc = None


def blocks_doc():
    global _doc
    if _doc is None:
        with open(BLOCKS_JSON) as f:
            _doc = json.load(f)
    return _doc


def block_by_id():
    return {b['id']: b for b in blocks_doc()['blocks']}


# ----------------------------------------------------------------------------- blueprint grid
class Grid:
    """Blueprint under construction. Cells hold block ids; '_skip' = leave world untouched."""

    def __init__(self, sx, sy, sz, fill='_skip'):
        self.a = np.full((sx, sy, sz), fill, dtype=object)

    @property
    def size(self):
        return self.a.shape

    def inside(self, x, y, z):
        sx, sy, sz = self.a.shape
        return 0 <= x < sx and 0 <= y < sy and 0 <= z < sz

    def set(self, x, y, z, b):
        if self.inside(x, y, z):
            self.a[x, y, z] = b

    def get(self, x, y, z):
        return self.a[x, y, z] if self.inside(x, y, z) else '_skip'

    def box(self, x0, y0, z0, x1, y1, z1, b, only=None):
        """Fill inclusive box. only: set of ids that may be overwritten (None = all)."""
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    if self.inside(x, y, z) and (only is None or self.a[x, y, z] in only):
                        self.a[x, y, z] = b

    def shell(self, x0, y0, z0, x1, y1, z1, b):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    if x in (x0, x1) or z in (z0, z1):
                        self.set(x, y, z, b)

    def to_json(self):
        sx, sy, sz = self.a.shape
        palette = ['_skip', 'air']
        for v in np.unique(self.a.astype(str)):
            if v not in palette:
                palette.append(v)
        pidx = {p: i for i, p in enumerate(palette)}
        flat = []
        for y in range(sy):
            for z in range(sz):
                for x in range(sx):
                    flat.append(pidx[self.a[x, y, z]])
        rle = []
        cur, n = flat[0], 0
        for v in flat:
            if v == cur:
                n += 1
            else:
                rle += [n, cur]
                cur, n = v, 1
        rle += [n, cur]
        return palette, rle


def decode_rle(size, palette, rle):
    sx, sy, sz = size
    flat = []
    for i in range(0, len(rle), 2):
        flat += [rle[i + 1]] * rle[i]
    a = np.empty((sx, sy, sz), dtype=object)
    k = 0
    for y in range(sy):
        for z in range(sz):
            for x in range(sx):
                a[x, y, z] = palette[flat[k]]
                k += 1
    return a


# ----------------------------------------------------------------------------- Blender mesher
_FACES = {
    # dir: (normal, face key, 4 corners as (x,y,z) offsets in Godot axes BL, BR, TR, TL)
    (1, 0, 0): ('side', [(1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)]),
    (-1, 0, 0): ('side', [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
    (0, 0, 1): ('front', [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    (0, 0, -1): ('side', [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)]),
    (0, 1, 0): ('top', [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)]),
    (0, -1, 0): ('bottom', [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
}


def _tile_uv(tile, cols, rows, inset=0.004):
    r, c = divmod(tile, cols)
    u0, u1 = c / cols + inset / cols, (c + 1) / cols - inset / cols
    v1 = 1 - r / rows - inset / rows
    v0 = 1 - (r + 1) / rows + inset / rows
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def atlas_materials():
    import bpy
    out = {}
    blocks_dir = os.path.join(ROOT, 'assets', 'blocks')
    for name, clip, alpha in (('VOX_opaque', False, 1.0), ('VOX_cutout', True, 1.0), ('VOX_water', False, 0.75)):
        m = bpy.data.materials.get(name)
        if m is None:
            m = bpy.data.materials.new(name)
            m.use_nodes = True
            nt = m.node_tree
            b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
            tex = nt.nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(os.path.join(blocks_dir, 'blocks_atlas.png'), check_existing=True)
            tex.interpolation = 'Linear'
            em = nt.nodes.new('ShaderNodeTexImage')
            em.image = bpy.data.images.load(os.path.join(blocks_dir, 'blocks_emission.png'), check_existing=True)
            em.interpolation = 'Linear'
            em.image.colorspace_settings.name = 'sRGB'
            uv = nt.nodes.new('ShaderNodeUVMap')
            nt.links.new(uv.outputs['UV'], tex.inputs['Vector'])
            nt.links.new(uv.outputs['UV'], em.inputs['Vector'])
            nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
            nt.links.new(em.outputs['Color'], b.inputs['Emission Color'])
            b.inputs['Emission Strength'].default_value = 2.5
            b.inputs['Roughness'].default_value = 0.9 if alpha == 1 else 0.15
            if clip:
                nt.links.new(tex.outputs['Alpha'], b.inputs['Alpha'])
                try:
                    m.surface_render_method = 'DITHERED'
                except Exception:
                    pass
            elif alpha < 1:
                b.inputs['Alpha'].default_value = alpha
                try:
                    m.surface_render_method = 'BLENDED'
                except Exception:
                    pass
        out[name] = m
    return out


def build_voxel_mesh(name, grid, origin=(0, 0, 0), coll=None):
    """grid: numpy object array [x,y,z] of block ids ('_skip'/'air' empty). origin = cell at pivot."""
    import bpy
    doc = blocks_doc()
    cols, rows = doc['atlas']['columns'], doc['atlas']['rows']
    bdef = block_by_id()
    sx, sy, sz = grid.shape
    ox, oy, oz = origin

    def empty(b):
        return b in ('_skip', 'air')

    def see_through(b, me):
        if empty(b):
            return True
        d = bdef[b]
        if d.get('shape') == 'cross':
            return True
        if d.get('transparent') and b != me:
            return True
        return False

    verts, faces, uvs, mats = [], [], [], []
    mat_names = ['VOX_opaque', 'VOX_cutout', 'VOX_water']

    def add_quad(corners, uv, mi):
        base = len(verts)
        for (x, y, z) in corners:
            verts.append((x - ox - 0.5, -(z - oz - 0.5), y - oy))
        faces.append((base, base + 1, base + 2, base + 3))
        uvs.append(uv)
        mats.append(mi)

    for x in range(sx):
        for y in range(sy):
            for z in range(sz):
                b = grid[x, y, z]
                if empty(b):
                    continue
                d = bdef[b]
                tiles = d['tiles']
                if d.get('shape') == 'cross':
                    uv = _tile_uv(tiles['side'], cols, rows)
                    for c in ([(0.15, 0, 0.15), (0.85, 0, 0.85), (0.85, 1, 0.85), (0.15, 1, 0.15)],
                              [(0.85, 0, 0.15), (0.15, 0, 0.85), (0.15, 1, 0.85), (0.85, 1, 0.15)]):
                        cc = [(x + a, y + bb, z + e) for a, bb, e in c]
                        add_quad(cc, uv, 1)
                        add_quad(list(reversed(cc)), [uv[1], uv[0], uv[3], uv[2]], 1)
                    continue
                mi = 2 if d.get('liquid') else (1 if d.get('transparent') else 0)
                for (dx, dy, dz), (key, corners) in _FACES.items():
                    nb = grid[x + dx, y + dy, z + dz] if (0 <= x + dx < sx and 0 <= y + dy < sy and 0 <= z + dz < sz) else 'air'
                    if not see_through(nb, b):
                        continue
                    if d.get('liquid') and nb == b:
                        continue
                    tk = key if key in tiles else 'side'
                    uv = _tile_uv(tiles[tk], cols, rows)
                    cc = [(x + a, y + bb, z + e) for a, bb, e in corners]
                    if d.get('liquid') and key == 'top':
                        cc = [(a, bb - 0.12, e) for a, bb, e in cc]
                    add_quad(cc, uv, mi)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name='UVMap')
    for p, uv in zip(me.polygons, uvs):
        for li, k in zip(p.loop_indices, range(4)):
            uvl.data[li].uv = uv[k]
    mt = atlas_materials()
    for n in mat_names:
        me.materials.append(mt[n])
    for p, mi in zip(me.polygons, mats):
        p.material_index = mi
    # sprites + water: no ink outline (lib_render excludes Freestyle-marked faces)
    try:
        fm = me.attributes.new('freestyle_face', 'BOOLEAN', 'FACE')
        fm.data.foreach_set('value', [mi != 0 for mi in mats])
    except Exception as e:  # noqa
        print('freestyle marks unavailable', e)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def godot_to_blender(p):
    x, y, z = p
    return (x, -z, y)
