"""Basic Ghost (player) and the worker ghosts (concept_art/basic ghosts.png, basic ghost.png,
concept/characters/worker_ghosts.png).

The body is one sheet surface of revolution: a dome head flaring into a draped hem with folds and a
rolled edge that turns inward (the dark inside of the sheet shows under the hem). Arms are mitten tubes
that sit inside the sheet: animations scale `upperarm_*` to ~0 to hide them and to 1 to pop them out.
Eyes are a separate mesh with shape keys (calm, angry, scared, happy, closed). No mouth.
"""
import math

from mathutils import Matrix, Quaternion, Vector

import lib_char as C
import lib_geo as G
from lib_char import Pose, qeuler, smooth, lerp

EXPRS = ['calm', 'angry', 'scared', 'happy', 'closed']


def ghost_mats():
    d = G.define_mat
    d('GHOST_sheet', None, 1, color=(0.92, 0.95, 1.0, 1), rough=0.28, emit=(0.62, 0.84, 1.0), emit_strength=0.18,
      alpha=0.86)
    d('GHOST_manifest', None, 1, color=(0.97, 0.98, 1.0, 1), rough=0.25, emit=(0.75, 0.9, 1.0), emit_strength=0.55)
    d('GHOST_eye', None, 1, color=(0.1, 0.06, 0.15, 1), rough=0.15)
    d('leather', 'canvas.png', 0.3, color=(0.45, 0.28, 0.18, 1), rough=0.7)
    d('leather_dark', 'canvas.png', 0.3, color=(0.3, 0.2, 0.16, 1), rough=0.7)
    d('cloth_cap_purple', 'cloth_linen.png', 0.3, color=(0.42, 0.33, 0.5, 1))
    d('cloth_green', 'canvas.png', 0.35, color=(0.52, 0.6, 0.36, 1))
    d('cloth_cream', 'cloth_linen.png', 0.3, color=(0.96, 0.92, 0.82, 1))
    d('cloth_white', 'cloth_linen.png', 0.3, color=(1.0, 1.0, 1.0, 1))
    d('glass_goggle', None, 1, color=(0.75, 0.6, 0.35, 1), rough=0.15, metal=0.6)
    d('flower_yellow', None, 1, color=(1.0, 0.82, 0.25, 1), rough=0.6)
    d('bread', 'wood_grain.png', 0.3, color=(1.0, 0.82, 0.55, 1), rough=0.6)
    d('SPECTRAL_tin', None, 1, color=(0.75, 0.88, 0.95, 1), rough=0.25, metal=0.4, emit=(0.55, 0.85, 1.0),
      emit_strength=0.25, alpha=0.75)


# ----------------------------------------------------------------------------- body shape
def catmull(pts, x):
    """Interpolate a list of (key, value) sorted by key with Catmull-Rom."""
    ks = [p[0] for p in pts]
    if x <= ks[0]:
        return pts[0][1]
    if x >= ks[-1]:
        return pts[-1][1]
    i = max(j for j in range(len(ks) - 1) if ks[j] <= x)
    t = (x - ks[i]) / (ks[i + 1] - ks[i])
    p0 = pts[max(0, i - 1)][1]
    p1, p2 = pts[i][1], pts[i + 1][1]
    p3 = pts[min(len(pts) - 1, i + 2)][1]
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


class SheetShape:
    """Radius profile r(z) of the sheet, depth squash, folds and the hem edge."""

    def __init__(self, s=1.0, kind='player'):
        self.s = s
        if kind == 'player':
            # (z, r) from the top of the head down to the hem, metres for a 0.6 m ghost
            prof = [(0.600, 0.0), (0.597, 0.035), (0.588, 0.067), (0.57, 0.095), (0.545, 0.117), (0.512, 0.131),
                    (0.47, 0.138), (0.42, 0.14), (0.36, 0.142), (0.3, 0.148), (0.24, 0.16), (0.17, 0.178),
                    (0.1, 0.198), (0.045, 0.214), (0.0, 0.224)]
            self.folds, self.fold_amp, self.edge_amp, self.depth = 6, 0.03, 0.06, 0.92
        else:  # worker: bean shaped, narrower hem with wisp points (worker_ghosts.png)
            prof = [(0.600, 0.0), (0.597, 0.042), (0.585, 0.082), (0.562, 0.116), (0.525, 0.143), (0.475, 0.16),
                    (0.415, 0.166), (0.345, 0.161), (0.27, 0.156), (0.2, 0.158), (0.13, 0.165), (0.07, 0.175),
                    (0.03, 0.183), (0.0, 0.188)]
            self.folds, self.fold_amp, self.edge_amp, self.depth = 5, 0.018, 0.06, 0.92
        self.prof = [(z, r) for z, r in prof]
        self.top = 0.6
        self.phase = [0.0, 0.7, 1.9, 0.4, 2.6, 1.1, 3.0, 0.2]

    def r(self, z):
        """Radius at height z (unscaled metres)."""
        pts = sorted(self.prof, key=lambda p: p[0])
        return max(0.0, catmull(pts, z))

    def fold(self, th, z):
        a = self.fold_amp * smooth((0.34 - z) / 0.34) ** 1.3
        n = self.folds
        w = math.sin(n * th + 0.5 * math.sin(2 * th + 0.4))
        return a * w

    def edge(self, th):
        """How far the hem edge hangs below z=0 at angle th (points at the folds)."""
        n = self.folds
        w = 0.5 + 0.5 * math.sin(n * th + 0.5 * math.sin(2 * th + 0.4))
        return self.edge_amp * (w ** 2) - self.edge_amp * 0.4

    def point(self, th, z, inset=0.0):
        r = self.r(z) + self.fold(th, z) - inset
        x = math.cos(th) * r
        y = math.sin(th) * r * self.depth
        return Vector((x, y, z)) * self.s

    def surf(self, p):
        """Project p horizontally onto the outer sheet; returns (point, normal)."""
        z = p.z / self.s
        th = math.atan2(p.y / self.depth, p.x)
        q = self.point(th, z)
        dz = 0.004
        q2 = self.point(th, z + dz)
        q3 = self.point(th + 0.01, z)
        n = (q3 - q).cross(q2 - q).normalized()
        if n.dot(Vector((math.cos(th), math.sin(th), 0))) < 0:
            n = -n
        return q, n


def sheet_mesh(shape, nu=56, nv=34):
    """The sheet: outer surface top->hem, rolled edge, inner surface up into the body (closed)."""
    hem_in = 0.016  # cloth thickness at the edge

    def fn(u, v):
        th = -math.pi / 2 + u * 2 * math.pi  # seam at the back (+Y)
        th = th + math.pi  # start at the back
        e = shape.edge(th)
        if v <= 0.78:
            t = v / 0.78
            z = shape.top * (1 - t) ** 1.0
            z = shape.top - (shape.top - (-e)) * (t ** 1.08)
            return shape.point(th, max(z, -e) if t < 1 else -e)
        if v <= 0.84:
            t = (v - 0.78) / 0.06
            z = -e + 0.004 * math.sin(t * math.pi)
            return shape.point(th, z, inset=hem_in * t) + Vector((0, 0, 0))
        t = (v - 0.84) / 0.16
        z = -e + (0.2 + e) * t
        p = shape.point(th, z, inset=hem_in)
        # close the inside: shrink toward the centre near the top of the inner surface
        k = 1 - smooth((t - 0.6) / 0.4) * 0.97
        return Vector((p.x * k, p.y * k, p.z))

    import bmesh
    bm = C.bm_grid_surface(fn, nu, nv, closed_u=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# ----------------------------------------------------------------------------- rig
def ghost_skeleton(name, s=1.0):
    sk = C.Skeleton(name)
    S = lambda *a: Vector(a) * s  # noqa: E731
    sk.add('root', S(0, 0, 0), S(0, 0, 0.08))
    sk.add('body', S(0, 0, 0.08), S(0, 0, 0.28), 'root')
    sk.add('chest', S(0, 0, 0.28), S(0, 0, 0.40), 'body')
    sk.add('head', S(0, 0, 0.40), S(0, 0, 0.60), 'chest')
    for side, sx in (('L', 1), ('R', -1)):
        sk.add(f'upperarm_{side}', S(sx * 0.08, 0, 0.33), S(sx * 0.17, 0.012, 0.33), 'chest', up=(0, 0, 1))
        sk.add(f'forearm_{side}', S(sx * 0.17, 0.012, 0.33), S(sx * 0.255, 0, 0.33), f'upperarm_{side}', up=(0, 0, 1))
        sk.add(f'hand_{side}', S(sx * 0.255, 0, 0.33), S(sx * 0.30, 0, 0.33), f'forearm_{side}', up=(0, 0, 1))
        sk.chain(f'upperarm_{side}', f'forearm_{side}', f'hand_{side}')
    hem = {'hem_F': -math.pi / 2, 'hem_BL': math.pi / 2 - 1.0, 'hem_BR': math.pi / 2 + 1.0}
    for n, th in hem.items():
        c, sn = math.cos(th), math.sin(th)
        sk.add(n, S(c * 0.1, sn * 0.1, 0.17), S(c * 0.2, sn * 0.18, 0.02), 'body', up=(0, 0, 1))
    sk.hem_angles = hem
    sk.scale = s
    return sk


def sheet_weights(sk, s):
    hem = sk.hem_angles

    def fn(p):
        z = p.z / s
        w = {}
        # vertical chain
        wb = 1 - smooth((z - 0.24) / 0.1)
        wh = smooth((z - 0.36) / 0.1)
        wc = max(0.0, 1 - wb - wh)
        w['body'], w['chest'], w['head'] = wb, wc, wh
        # hem ripple below 0.24 m
        k = smooth((0.24 - z) / 0.2) * 0.9
        if k > 0:
            th = math.atan2(p.y, p.x)
            hw = {}
            for n, a in hem.items():
                d = math.cos(th - a)
                hw[n] = max(0.0, d) ** 2 + 1e-3
            tot = sum(hw.values())
            for n in hw:
                w[n] = k * hw[n] / tot
            w['body'] *= (1 - k)
        return w
    return fn


# ----------------------------------------------------------------------------- build
def eye_features(shape, s, z=0.44, x=0.046, w=0.022, h=0.032):
    feats = []
    for side, sx in (('L', 1), ('R', -1)):
        # point on the sheet whose x is exactly sx * x (front = -Y)
        th = -math.acos(max(-1.0, min(1.0, sx * x / shape.r(z))))
        p, n = shape.surf(shape.point(th, z))
        f = C.Feature(f'eye_{side}', 'GHOST_eye', p, n, (0, 0, 1), w * s, h * s, lift=0.0015 * s,
                      depth=0.005 * s, nu=12, nv=8, mirror=(sx < 0))
        f.shape('calm')
        # angry: the top is cut by a slant that drops toward the nose (inner side = -u)
        def a_bot(u):
            return -0.95 * math.sqrt(max(0, 1 - u * u))

        def a_top(u):
            return max(a_bot(u) + 0.25, min(math.sqrt(max(0, 1 - u * u)), 0.62 + 0.5 * u))
        f.shape('angry', 1.05, top=a_top, bottom=a_bot)
        f.shape('scared', 1.15, dy=0.08, top=lambda u: 1.3 * math.sqrt(max(0, 1 - u * u)),
                bottom=lambda u: -1.3 * math.sqrt(max(0, 1 - u * u)))
        f.shape('happy', 1.1, dy=0.1, top=lambda u: 0.42 - 0.62 * u * u + 0.16,
                bottom=lambda u: 0.42 - 0.62 * u * u - 0.16, thick=0.3)
        f.shape('closed', 1.1, dy=-0.15, top=lambda u: 0.06 * u * u + 0.07, bottom=lambda u: 0.06 * u * u - 0.07,
                thick=0.2)
        feats.append(f)
    return feats


def arm_geometry(cm, sk, side, s):
    sx = 1 if side == 'L' else -1
    sh = sk.head(f'upperarm_{side}')
    el = sk.head(f'forearm_{side}')
    wr = sk.head(f'hand_{side}')
    tip = sk.tail(f'hand_{side}')
    rule = ('dist', [f'upperarm_{side}', f'forearm_{side}', f'hand_{side}'], 4)
    secs = [(sh - Vector((sx * 0.02 * s, 0, 0)), 0.042 * s, 0.036 * s), (sh, 0.044 * s, 0.037 * s),
            (el, 0.034 * s, 0.03 * s), (wr, 0.029 * s, 0.026 * s)]
    cm.loft('GHOST_sheet', rule, secs, 10, side=(0, 0, 1))
    # mitten hand + thumb nub (sheet fabric)
    cm.sphere('GHOST_sheet', ('rigid', f'hand_{side}'), 0.036 * s, (wr + tip) / 2, scale=(1.15, 0.9, 1.0),
              segs=12, rings=8)
    cm.sphere('GHOST_sheet', ('rigid', f'hand_{side}'), 0.016 * s, wr + Vector((sx * 0.02, -0.022, 0.012)) * s,
              segs=8, rings=6)


def build_ghost(name, coll, s=1.0, kind='player', outfit=None):
    """Returns dict(rig, body, eyes, skel, extra objects)."""
    ghost_mats()
    shape = SheetShape(s, kind)
    sk = ghost_skeleton(name, s)
    rig = C.build_armature(sk, coll)
    cm = C.CharMesh(f'{name}_body', smooth_angle=80)
    cm.add(sheet_mesh(shape), 'GHOST_sheet', ('fn', sheet_weights(sk, s)), uv='box')
    for side in ('L', 'R'):
        arm_geometry(cm, sk, side, s)
    outfit_objs = []
    if outfit:
        outfit(cm, sk, shape, s)
    body = cm.build(coll, rig, sk)
    eyes = C.build_face(f'{name}_eyes', eye_features(shape, s), EXPRS, shape.surf, coll, rig, sk, 'head')
    res = dict(rig=rig, body=body, eyes=eyes, skel=sk, shape=shape, faces=[eyes], name=name, s=s)
    # held-item sockets: HELD_tool at the right palm, axes = character frame (handle up, working end forward)
    import bpy
    for nm, bone in (('HELD_tool', 'hand_R'),) if kind == 'player' else (('HELD_R', 'hand_R'), ('HELD_L', 'hand_L'),
                                                                          ('HELD_block', 'chest')):
        e = bpy.data.objects.new(nm, None)
        e.empty_display_size = 0.06 * s
        e.empty_display_type = 'ARROWS'
        coll.objects.link(e)
        if bone == 'chest':
            pos = Vector((0, -0.17, 0.66)) * s
        else:
            pos = (sk.head(bone) + sk.tail(bone)) / 2
        C.attach_to_bone(e, rig, bone, Matrix.Translation(pos))
        res[nm] = e
    if kind == 'player':
        # material holder for the manifested state (Godot swaps ghost_body's material to it; hidden at load)
        me = bpy.data.meshes.new('MATERIAL_manifest')
        me.from_pydata([(0, 0, 0.3), (0.001, 0, 0.3), (0, 0.001, 0.3)], [], [(0, 1, 2)])
        me.uv_layers.new(name='UVMap')
        me.materials.append(G.get_mat('GHOST_manifest'))
        hold = bpy.data.objects.new('MATERIAL_manifest', me)
        coll.objects.link(hold)
        hold.parent = rig
        res['manifest'] = hold
    return res


# ----------------------------------------------------------------------------- outfits (worker ghosts)
def _chest_rule():
    return ('rigid', 'chest')


def outfit_blacksmith(cm, sk, shape, s):
    S = lambda *a: Vector(a) * s  # noqa: E731
    # flat cap with goggles (purple-brown, concept), a strap band
    cm.lathe('cloth_cap_purple', ('rigid', 'head'), [(0.0, 0.0), (0.155, 0.0), (0.165, 0.02), (0.15, 0.06),
                                                     (0.11, 0.09), (0.0, 0.1)], S(0, 0.0, 0.515), segs=18)
    cm.box('cloth_cap_purple', ('rigid', 'head'), S(0.2, 0.1, 0.022), S(0, -0.16, 0.522), rot=(0.25, 0, 0),
           bevel=0.01)
    cm.cyl('leather_dark', ('rigid', 'head'), 0.158 * s, 0.158 * s, 0.025 * s, S(0, 0, 0.53), segs=18, bevel=0.005)
    for sx in (-1, 1):
        g = S(sx * 0.045, -0.115, 0.585)
        cm.cyl('brass', ('rigid', 'head'), 0.032 * s, 0.032 * s, 0.03 * s, g, rot=(1.2, 0, 0), segs=12, bevel=0.006)
        cm.cyl('glass_goggle', ('rigid', 'head'), 0.024 * s, 0.024 * s, 0.032 * s, g + S(0, -0.004, 0.0),
               rot=(1.2, 0, 0), segs=12, bevel=0.003)
    # leather apron (bib + skirt) over the front, a belt with pouches
    _apron(cm, shape, s, 'leather', bib=True, z0=0.07, z1=0.36, width=0.75)
    _belt(cm, shape, s, 'leather_dark', 0.2)
    for sx in (-0.11, 0.1):
        p, n = shape.surf(S(sx, -0.3, 0.17))
        cm.box('leather_dark', ('fn', sheet_weights(sk, s)), S(0.05, 0.03, 0.055), p + n * 0.012 * s, bevel=0.008)
    p, n = shape.surf(S(0.0, -0.3, 0.28))
    cm.ext('iron', ('rigid', 'chest'), [(-0.03, 0), (0.03, 0), (0.02, 0.012), (0.045, 0.03), (-0.045, 0.03),
                                        (-0.02, 0.012)], 0.006 * s, p + n * 0.006 * s, rot=(math.pi / 2, 0, 0))


def outfit_gardener(cm, sk, shape, s):
    S = lambda *a: Vector(a) * s  # noqa: E731
    # wide straw sunhat with a green band and a yellow flower
    cm.lathe('straw', ('rigid', 'head'), [(0.0, 0.11), (0.1, 0.105), (0.14, 0.06), (0.16, 0.02), (0.24, -0.005),
                                          (0.255, -0.02), (0.0, -0.02)], S(0, 0, 0.5), segs=22)
    cm.cyl('cloth_green', ('rigid', 'head'), 0.145 * s, 0.15 * s, 0.03 * s, S(0, 0, 0.53), segs=18, bevel=0.005)
    for k in range(5):
        a = k / 5 * 2 * math.pi
        cm.sphere('flower_yellow', ('rigid', 'head'), 0.018 * s, S(0.11 + 0.022 * math.cos(a), -0.08,
                                                                    0.56 + 0.022 * math.sin(a)), segs=6, rings=4)
    cm.sphere('brass', ('rigid', 'head'), 0.014 * s, S(0.11, -0.09, 0.56), segs=6, rings=4)
    cm.add(_leaf_bm(), 'leaf', ('rigid', 'head'), S(0.06, -0.12, 0.56), rot=(1.3, 0.3, 0.5), scale=(s, s, s))
    _apron(cm, shape, s, 'cloth_green', bib=True, z0=0.07, z1=0.34, width=0.7)
    p, n = shape.surf(S(0.0, -0.3, 0.16))
    cm.box('leather', ('fn', sheet_weights(sk, s)), S(0.08, 0.035, 0.065), p + n * 0.02 * s, bevel=0.01)
    for k in range(3):
        cm.add(_leaf_bm(), 'leaf', ('fn', sheet_weights(sk, s)), p + n * 0.03 * s + S(-0.02 + 0.02 * k, 0, 0.05),
               rot=(1.2, 0.2 * (k - 1), 0.4 * (k - 1)), scale=(s, s, s))


def outfit_baker(cm, sk, shape, s):
    S = lambda *a: Vector(a) * s  # noqa: E731
    # tall puffy toque
    cm.cyl('cloth_white', ('rigid', 'head'), 0.15 * s, 0.155 * s, 0.07 * s, S(0, 0, 0.55), segs=18, bevel=0.01)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        cm.sphere('cloth_white', ('rigid', 'head'), 0.08 * s, S(0.085 * math.cos(a), 0.085 * math.sin(a), 0.66),
                  segs=10, rings=6)
    cm.sphere('cloth_white', ('rigid', 'head'), 0.1 * s, S(0, 0, 0.68), segs=12, rings=8)
    # red neckerchief with a knot at the side
    cm.add(C.bm_loft([(S(0, 0, 0.37), 0.172 * s, 0.158 * s), (S(0, 0, 0.405), 0.165 * s, 0.152 * s)], 18,
                     cap0=None, cap1=None, side=(1, 0, 0)), 'cloth_red', ('rigid', 'chest'))
    cm.sphere('cloth_red', ('rigid', 'chest'), 0.03 * s, S(-0.13, -0.11, 0.38), segs=8, rings=6)
    for sx in (-1, 1):
        cm.tube('cloth_red', ('rigid', 'chest'), [S(-0.13, -0.11, 0.38), S(-0.13 + sx * 0.04, -0.14, 0.33)],
                0.018 * s, 6, taper=0.5)
    _apron(cm, shape, s, 'cloth_cream', bib=False, z0=0.05, z1=0.22, width=0.72)
    _belt(cm, shape, s, 'cloth_cream', 0.22)
    p, n = shape.surf(S(0.0, -0.3, 0.13))
    for k in range(5):  # wheat emblem
        cm.sphere('straw', ('fn', sheet_weights(sk, s)), 0.009 * s, p + n * 0.012 * s + S(0, 0, -0.02 + k * 0.014),
                  scale=(1, 0.5, 1.6), segs=6, rings=4)


def _leaf_bm():
    return G.bm_extrude2d([(0, 0), (0.02, 0.02), (0.022, 0.045), (0, 0.065), (-0.022, 0.045), (-0.02, 0.02)],
                          0.004, 0.001, 1)


def _belt(cm, shape, s, mat, z):
    secs = []
    cm.add(C.bm_loft([(Vector((0, 0, (z - 0.012) * s)), shape.r(z) * s * 1.06, shape.r(z) * s * shape.depth * 1.06),
                      (Vector((0, 0, (z + 0.012) * s)), shape.r(z) * s * 1.05, shape.r(z) * s * shape.depth * 1.05)],
                     24, cap0=None, cap1=None), mat, ('rigid', 'body'))


def _apron(cm, shape, s, mat, bib, z0, z1, width):
    """Apron panel following the front of the sheet (offset outward), skinned like the sheet."""
    span = width * math.pi / 2

    def fn(u, v):
        th = -math.pi / 2 + (u - 0.5) * span
        z = z0 + (z1 - z0) * v
        p = shape.point(th, z) / 1.0
        p = Vector((p.x, p.y, z)) * 1.0
        r = Vector((p.x, p.y, 0))
        out = r.normalized() * 0.008
        return (Vector((p.x, p.y, z)) + out) * s if False else (Vector((p.x, p.y, z)) + out)

    import bmesh

    def f2(u, v):
        th = -math.pi / 2 + (u - 0.5) * span * (1 - 0.25 * v if bib else 1)
        z = z0 + (z1 - z0) * v
        q = shape.point(th, z)  # already scaled
        out = Vector((math.cos(th), math.sin(th), 0)) * 0.009 * s
        return q + out

    bm = C.bm_grid_surface(f2, 14, 10)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=-0.006 * s)
    sk_rule = ('fn', lambda p: {'body': 1.0} if p.z / s < 0.28 else {'chest': 1.0})
    cm.add(bm, mat, sk_rule)
    if bib:  # straps over the shoulders
        for sx in (-1, 1):
            pts = [shape.point(-math.pi / 2 + sx * span * 0.36, z1 - 0.005) + Vector((0, -0.006, 0)) * s,
                   shape.point(-math.pi / 2 + sx * 0.9, 0.4) + Vector((0, -0.004, 0.004)) * s,
                   shape.point(math.pi / 2 - sx * 0.6, 0.36) + Vector((0, 0.006, 0.0)) * s,
                   shape.point(math.pi / 2 - sx * 0.25, 0.22) + Vector((0, 0.008, 0.0)) * s]
            cm.tube(mat, ('rigid', 'chest'), pts, 0.008 * s, 6)


# ----------------------------------------------------------------------------- held things for the workers
def worker_items(kind, coll, res):
    """Small tools as separate nodes under HELD_R / HELD_L (Godot hides them while carrying)."""
    import bpy
    s = res['s']
    S = lambda *a: Vector(a) * s  # noqa: E731
    items = []
    node = G.MeshNode('ITEM_' + {'blacksmith': 'hammer', 'gardener': 'watering_can', 'baker': 'bread'}[kind])
    if kind == 'blacksmith':
        G.define_mat('SPECTRAL_hammer', None, 1, color=(0.62, 0.45, 0.95, 1), rough=0.3, emit=(0.6, 0.35, 1.0),
                     emit_strength=1.2, alpha=0.9)
        node.cyl('wood_dark', 0.016 * s, 0.016 * s, 0.24 * s, S(0, 0, 0.06), segs=8)
        node.box('SPECTRAL_hammer', S(0.08, 0.15, 0.08), S(0, 0, 0.19), bevel=0.012)
        hand = 'HELD_R'
    elif kind == 'gardener':
        node.cyl('SPECTRAL_tin', 0.06 * s, 0.055 * s, 0.11 * s, S(0, -0.02, -0.08), segs=14, bevel=0.008)
        node.tube('SPECTRAL_tin', [S(0, 0.035, -0.045), S(0, 0.02, 0.02), S(0, -0.05, 0.02), S(0, -0.07, -0.04)],
                  0.008 * s, 6)
        node.tube('SPECTRAL_tin', [S(0, -0.07, -0.09), S(0, -0.13, -0.05), S(0, -0.17, -0.0)], 0.012 * s, 6,
                  taper=1.3)
        node.cyl('SPECTRAL_tin', 0.022 * s, 0.022 * s, 0.012 * s, S(0, -0.175, 0.005), rot=(-0.9, 0, 0), segs=10)
        hand = 'HELD_L'
    else:
        node.sphere('bread', 0.045 * s, S(0, -0.02, 0.0), scale=(1.8, 1.0, 0.8), segs=14, rings=8)
        for k in range(3):
            node.box('cloth_cream', S(0.006, 0.05, 0.006), S(-0.04 + 0.04 * k, -0.04, 0.027), rot=(0, 0, 0.5),
                     bevel=0.003)
        hand = 'HELD_R'
    G.seed(5)
    ob = G._mesh_object(node, coll)
    held = res[hand]
    ob.parent = held
    ob.matrix_parent_inverse = Matrix()
    ob.location = (0, 0, 0)
    items.append(ob)
    res['item'] = ob
    return items


# ----------------------------------------------------------------------------- animation helpers
def hide_arms(p, k=1.0):
    """k=1 fully hidden inside the sheet, 0 = out."""
    sc = lerp(1.0, 0.04, k)
    for side in ('L', 'R'):
        p.s[f'upperarm_{side}'] = (sc, sc, sc)


HEM_ANGLES = {'hem_F': -math.pi / 2, 'hem_BL': math.pi / 2 - 1.0, 'hem_BR': math.pi / 2 + 1.0}


def hem_ripple(p, t, amp=6.0, speed=1.0, trail=0.0, flare=0.0):
    """Hem bones: ripple in/out about their tangent axis (+ = inward), trail backward (+trail = tips to +Y,
    i.e. behind a ghost moving forward), flare outward (+flare)."""
    for i, (n, th) in enumerate(HEM_ANGLES.items()):
        ph = t * 2 * math.pi * speed + i * 2.1
        axis = Vector((-math.sin(th), math.cos(th), 0))
        p.rot(n, Quaternion(axis, math.radians(amp * math.sin(ph) - flare)))
        if trail:
            p.rot_e(n, x=trail)


def chest_frame(sk):
    return sk.head('chest')


def arm_ik(p, sk, side, target, pole=None):
    """Hand target in armature space."""
    sx = 1 if side == 'L' else -1
    pole = pole or Vector((sx * 0.3, 0.6, -0.6))
    p.ik[f'upperarm_{side}'] = (Vector(target), pole)


# ----------------------------------------------------------------------------- player clips
def keyed(keys, t):
    """keys: [(time, value)], value numbers or Vectors; smoothstep between keys."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            u = smooth((t - t0) / max(1e-6, t1 - t0))
            if isinstance(a, Quaternion):
                return a.slerp(b, u)
            return a + (b - a) * u
    return keys[-1][1]


def tool_offset(tool):
    """GRIP_off - GRIP along the handle (tool +Z) for the task1 tools (tier I lengths)."""
    return {'scythe': 0.825 - 0.418, 'shovel': 0.5445 - 0.94, 'sledgehammer': 0.54 - 0.18}[tool]


def two_hand(p, sk, s, grip_pos, tool_rot, tool, pole_r=None, pole_l=None):
    """Right hand on GRIP at grip_pos with the tool rotated by tool_rot; left hand IK to GRIP_off."""
    arm_ik(p, sk, 'R', grip_pos, pole_r)
    p.wrot['hand_R'] = tool_rot
    off = tool_rot @ Vector((0, 0, tool_offset(tool)))
    arm_ik(p, sk, 'L', grip_pos + off, pole_l)
    p.wrot['hand_L'] = tool_rot


def player_clips(res):
    sk, s = res['skel'], res['s']
    S = lambda *a: Vector(a) * s  # noqa: E731
    clips = {}

    def base(t, bob=0.02, period=2.0, arms=1.0):
        p = Pose()
        p.move('root', (0, 0, bob * s * math.sin(2 * math.pi * t / period)))
        hide_arms(p, arms)
        p.shapes = {}
        return p

    def idle_float(f):
        t = f / 24
        p = base(t, 0.025, 2.0)
        p.rot_e('head', y=2.5 * math.sin(2 * math.pi * t / 2.0 + 0.6), x=1.5 * math.sin(2 * math.pi * t / 2.0))
        p.rot_e('chest', y=-1.2 * math.sin(2 * math.pi * t / 2.0 + 0.6))
        hem_ripple(p, t / 2.0, amp=5, speed=2)
        return p
    clips['idle_float'] = (48, idle_float, True)

    def drift(f):
        t = f / 24
        p = base(t, 0.015, 1.0)
        p.rot_e('root', x=13)
        p.rot_e('head', x=-6 + 1.5 * math.sin(2 * math.pi * t))
        hem_ripple(p, t, amp=7, speed=2, trail=16)
        return p
    clips['drift'] = (24, drift, True)

    def glide_down(f):
        t = f / 24
        p = base(t, 0.01, 1.0)
        p.rot_e('root', x=6)
        p.s['body'] = (1.04, 0.95, 1.04)
        p.rot_e('head', x=-8)
        hem_ripple(p, t, amp=5, speed=2, flare=22 + 4 * math.sin(4 * math.pi * t))
        return p
    clips['glide_down'] = (24, glide_down, True)

    def ascend(f):
        t = f / 24
        p = base(t, 0.01, 1.0)
        p.s['root'] = (0.94, 1.08, 0.94)
        p.rot_e('head', x=10)
        hem_ripple(p, t, amp=4, speed=2, flare=-14)
        return p
    clips['ascend'] = (24, ascend, True)

    def phase(f):
        t = f / 24
        p = base(t, 0.0)
        sq = keyed([(0, 0.0), (0.2, 1.0), (0.45, -1.0), (0.7, 0.3), (1.0, 0.0)], t)
        # sq > 0 squash (wide, short), < 0 stretch forward (long along Y, thin)
        if sq >= 0:
            p.s['root'] = (1 + 0.18 * sq, 1 - 0.18 * sq, 1 + 0.12 * sq)
        else:
            k = -sq
            p.s['root'] = (1 - 0.18 * k, 1 - 0.08 * k, 1 + 0.35 * k)
        p.rot_e('root', x=keyed([(0, 0), (0.2, -6), (0.45, 14), (0.7, 4), (1.0, 0)], t))
        p.move('root', (0, keyed([(0, 0.0), (0.45, -0.08), (1.0, 0.0)], t) * s, 0))
        hem_ripple(p, t, amp=6, speed=2, trail=20 * max(0, -sq))
        p.shapes = {'closed': keyed([(0, 0), (0.25, 0.0), (0.4, 1.0), (0.6, 1.0), (0.8, 0.0)], t)}
        return p
    clips['phase'] = (24, phase, False)

    def tool_rot(h, f):
        """Rotation taking the tool's +Z (handle, butt -> working end) to h and its -Y (working face) toward f."""
        h = Vector(h).normalized()
        f = Vector(f)
        f = (f - h * f.dot(h)).normalized()
        y = -f
        x = y.cross(h)
        return Matrix((x, y, h)).transposed().to_quaternion()

    def tool_clip(keys, tool, expr, lean=None):
        """keys: [(time, grip_pos, handle_dir, face_dir)] -> pose fn (two hands on the tool)."""
        qs = [(t, tool_rot(h, f)) for t, g, h, f in keys]
        gs = [(t, S(*g)) for t, g, h, f in keys]

        def fn(fr):
            t = fr / 24
            p = base(t, 0.0, arms=0.0)
            qr = qeuler(x=keyed(lean[0], t), z=keyed(lean[1], t)) if lean else Quaternion()
            p.rot('root', qr)
            two_hand(p, sk, s, qr @ keyed(gs, t), qr @ keyed(qs, t), tool,
                     pole_r=Vector((-0.4, 0.5, -0.6)), pole_l=Vector((0.4, 0.5, -0.6)))
            hem_ripple(p, t, amp=6, speed=2)
            p.shapes = {expr[0]: expr[1]}
            return p
        return fn

    # scythe: ready (blade up-front) -> wind up over the right shoulder -> chop down across to the front-left
    sc = [(0.0, (-0.1, -0.16, 0.3), (-0.25, -0.45, 1), (0, -1, -0.4)),
          (0.3, (-0.17, -0.02, 0.4), (-0.75, 0.35, 0.6), (-0.2, -0.6, 0.5)),
          (0.5, (-0.05, -0.2, 0.28), (0.2, -0.95, 0.05), (0, -0.2, -1)),
          (0.62, (0.06, -0.17, 0.24), (0.75, -0.6, -0.2), (0, 0.1, -1)),
          (0.85, (0.04, -0.15, 0.26), (0.6, -0.55, 0.2), (0, 0, -1)),
          (1.1, (-0.1, -0.16, 0.3), (-0.25, -0.45, 1), (0, -1, -0.4))]
    clips['swing_scythe'] = (26, tool_clip(sc, 'scythe', ('angry', 0.7),
                                           ([(0, 0), (0.3, -4), (0.55, 10), (1.1, 0)],
                                            [(0, 0), (0.3, -28), (0.6, 22), (1.1, 0)])), False)
    # shovel (spade at the tool origin, GRIP near the D-handle): handle runs from the spade up-back to the hands
    sh = [(0.0, (-0.04, -0.13, 0.36), (0, 0.45, 1), (0, -1, 0.3)),
          (0.3, (-0.04, -0.16, 0.42), (0, 0.25, 1), (0, -1, 0.2)),
          (0.5, (-0.04, -0.2, 0.24), (0, 0.4, 1), (0, -1, 0.2)),
          (0.75, (-0.04, -0.04, 0.26), (0, 1, 0.65), (0, -0.5, 1)),
          (0.95, (-0.04, -0.17, 0.42), (0, 0.1, 1), (0, -0.6, 1)),
          (1.17, (-0.04, -0.13, 0.36), (0, 0.45, 1), (0, -1, 0.3))]
    clips['dig_shovel'] = (28, tool_clip(sh, 'shovel', ('angry', 0.4),
                                         ([(0, 3), (0.5, 14), (0.75, 4), (0.95, -4), (1.17, 3)],
                                          [(0, 0), (1.17, 0)])), False)
    # sledgehammer (head at the top): raised over the head behind -> smash down in front -> recoil
    hm = [(0.0, (-0.04, -0.17, 0.3), (0, -0.55, 1), (0, -1, -0.5)),
          (0.35, (-0.04, 0.0, 0.5), (0, 0.75, 0.6), (0, -0.6, 0.8)),
          (0.5, (-0.04, -0.18, 0.4), (0, -0.7, 0.7), (0, -0.6, -0.6)),
          (0.6, (-0.04, -0.22, 0.24), (0, -1, -0.25), (0, -0.2, -1)),
          (0.72, (-0.04, -0.21, 0.27), (0, -1, -0.05), (0, -0.1, -1)),
          (1.0, (-0.04, -0.17, 0.3), (0, -0.55, 1), (0, -1, -0.5))]
    clips['smash_hammer'] = (24, tool_clip(hm, 'sledgehammer', ('angry', 1.0),
                                           ([(0, 0), (0.35, -10), (0.6, 16), (1.0, 0)], [(0, 0), (1.0, 0)])), False)

    def haunt_cast(f):
        t = f / 24
        p = base(t, 0.01, 1.5, arms=keyed([(0, 1.0), (0.25, 0.0), (1.25, 0.0), (1.5, 1.0)], t))
        reach = keyed([(0, 0.0), (0.4, 1.0), (1.1, 1.0), (1.5, 0.0)], t)
        p.rot_e('root', x=14 * reach)
        p.move('root', (0, -0.04 * reach * s, 0))
        for side, sx in (('L', 1), ('R', -1)):
            wig = 0.012 * math.sin(2 * math.pi * t * 4 + sx) * reach
            arm_ik(p, sk, side, S(sx * (0.12 - 0.05 * reach), -0.12 - 0.17 * reach, 0.36 + wig / s * 0 + 0.02 * reach)
                   + Vector((0, 0, wig)))
        p.rot_e('head', x=-6 * reach)
        hem_ripple(p, t, amp=7, speed=3, trail=8 * reach)
        p.shapes = {'angry': reach}
        return p
    clips['haunt_cast'] = (36, haunt_cast, False)

    def boo(f):
        t = f / 24
        rise = keyed([(0, 0.0), (0.3, -0.25), (0.55, 1.0), (1.2, 1.0), (1.6, 0.0)], t)
        p = base(t, 0.0, arms=keyed([(0, 1.0), (0.35, 1.0), (0.5, 0.0), (1.3, 0.0), (1.55, 1.0)], t))
        p.move('root', (0, 0, 0.14 * max(0, rise) * s))
        sq = min(0, rise)
        p.s['root'] = (1 - sq * 0.4 + 0.06 * max(0, rise), 1 + sq * 0.6 + 0.1 * max(0, rise), 1 - sq * 0.3)
        p.rot_e('root', x=-8 * max(0, rise))
        shake = 3 * math.sin(2 * math.pi * t * 9) * max(0, rise)
        p.rot_e('head', y=shake)
        for side, sx in (('L', 1), ('R', -1)):
            arm_ik(p, sk, side, S(sx * 0.32, -0.08, 0.45) * 1.0, Vector((sx * 0.2, 0.6, -0.8)))
        hem_ripple(p, t, amp=9, speed=3, flare=20 * max(0, rise))
        p.shapes = {'scared': max(0, rise)}
        return p
    clips['boo'] = (40, boo, False)

    def hurt(f):
        t = f / 24
        h = keyed([(0, 0.0), (0.08, 1.0), (0.3, 0.7), (0.6, 0.0)], t)
        p = base(t, 0.0)
        p.rot_e('root', x=-18 * h, y=6 * math.sin(2 * math.pi * t * 6) * h)
        p.move('root', (0, 0.06 * h * s, 0))
        p.s['root'] = (1 + 0.12 * h, 1 - 0.12 * h, 1 + 0.08 * h)
        hem_ripple(p, t, amp=10 * h + 3, speed=3, trail=-12 * h)
        p.shapes = {'closed': h}
        return p
    clips['hurt'] = (15, hurt, False)

    def scatter(f):
        t = f / 24
        b = keyed([(0, 0.0), (0.25, 1.0)], t)
        gone = keyed([(0.3, 0.0), (0.8, 1.0)], t)
        p = base(t, 0.0, arms=0.0)
        sc = (1 + 0.35 * b) * (1 - 0.97 * gone)
        p.s['root'] = (sc * (1 + 0.15 * b), sc * (1 - 0.1 * b), sc * (1 + 0.15 * b))
        p.move('root', (0, 0, 0.18 * gone * s))
        for side, sx in (('L', 1), ('R', -1)):
            arm_ik(p, sk, side, S(sx * 0.33, 0.0, 0.42), Vector((sx * 0.2, 0.6, -0.8)))
        hem_ripple(p, t, amp=10, speed=4, flare=40 * b)
        p.shapes = {'scared': b}
        return p
    clips['scatter'] = (20, scatter, False)

    def celebrate(f):
        t = f / 24
        p = base(t, 0.0, arms=keyed([(0, 1.0), (0.2, 0.0), (1.8, 0.0), (2.0, 1.0)], t))
        hop = abs(math.sin(math.pi * t * 2)) * keyed([(0, 0.0), (0.2, 1.0), (1.8, 1.0), (2.0, 0.0)], t)
        p.move('root', (0, 0, 0.1 * hop * s))
        p.rot_e('root', z=360 * smooth((t - 0.5) / 0.7))
        for side, sx in (('L', 1), ('R', -1)):
            wave = 0.05 * math.sin(2 * math.pi * t * 3 + (0 if sx > 0 else math.pi))
            arm_ik(p, sk, side, S(sx * 0.22, -0.05, 0.62 + wave), Vector((sx * 0.4, 0.5, -0.5)))
        hem_ripple(p, t, amp=8, speed=3)
        p.shapes = {'happy': keyed([(0, 0.0), (0.2, 1.0), (1.8, 1.0), (2.0, 0.0)], t)}
        return p
    clips['celebrate'] = (48, celebrate, False)
    return clips


# ----------------------------------------------------------------------------- worker clips
def worker_clips(res, kind):
    sk, s = res['skel'], res['s']
    S = lambda *a: Vector(a) * s  # noqa: E731
    clips = {}

    def hold(p, t):
        """Default arm pose per outfit (both nubs out, holding the outfit's item)."""
        if kind == 'blacksmith':
            arm_ik(p, sk, 'R', S(-0.24, -0.08, 0.34))
            p.wrot['hand_R'] = qeuler(x=-10, y=20)
            arm_ik(p, sk, 'L', S(0.17, -0.12, 0.27))
        elif kind == 'gardener':
            arm_ik(p, sk, 'L', S(0.22, -0.1, 0.26))
            p.wrot['hand_L'] = qeuler()
            arm_ik(p, sk, 'R', S(-0.17, -0.12, 0.27))
        else:
            arm_ik(p, sk, 'R', S(-0.12, -0.2, 0.33))
            p.wrot['hand_R'] = qeuler(z=-70)
            arm_ik(p, sk, 'L', S(0.17, -0.12, 0.28))

    def idle_float(f):
        t = f / 24
        p = Pose()
        p.move('root', (0, 0, 0.02 * s * math.sin(2 * math.pi * t / 2.0)))
        p.rot_e('head', y=3 * math.sin(2 * math.pi * t / 2.0 + 0.6))
        hold(p, t)
        hem_ripple(p, t / 2, amp=6, speed=2)
        return p
    clips['idle_float'] = (48, idle_float, True)

    def carry(f):
        t = f / 24
        p = Pose()
        p.move('root', (0, 0, 0.012 * s * math.sin(2 * math.pi * t * 2)))
        p.rot_e('root', x=4)
        for side, sx in (('L', 1), ('R', -1)):
            arm_ik(p, sk, side, S(sx * 0.13, -0.16, 0.56), Vector((sx * 0.6, 0.4, -0.6)))
            p.wrot[f'hand_{side}'] = qeuler(x=-60)
        p.rot_e('head', x=-4)
        hem_ripple(p, t, amp=6, speed=2, trail=10)
        return p
    clips['carry'] = (24, carry, True)

    def work(f):
        t = f / 24
        p = Pose()
        p.move('root', (0, 0, 0.01 * s * math.sin(2 * math.pi * t * 2)))
        ph = (t / 1.0) % 1.0
        if kind == 'blacksmith':
            a = keyed([(0, 0.0), (0.45, 1.0), (0.6, -0.15), (0.7, 0.0), (1.0, 0.0)], ph)
            arm_ik(p, sk, 'R', S(-0.17, -0.17 + 0.06 * a, 0.3 + 0.18 * a), Vector((-0.6, 0.4, -0.6)))
            p.wrot['hand_R'] = qeuler(x=-80 + 120 * a)
            arm_ik(p, sk, 'L', S(0.14, -0.16, 0.26))
            p.rot_e('root', x=-4 * a + 6 * max(0, -a) * 4)
        elif kind == 'gardener':
            tip = 0.5 + 0.5 * math.sin(2 * math.pi * ph)
            arm_ik(p, sk, 'L', S(0.2, -0.18, 0.3 + 0.03 * tip))
            p.wrot['hand_L'] = qeuler(x=25 + 20 * tip)
            arm_ik(p, sk, 'R', S(-0.17, -0.12, 0.27))
            p.rot_e('root', x=6)
        else:
            k = math.sin(2 * math.pi * ph)
            arm_ik(p, sk, 'R', S(-0.08, -0.22, 0.26 + 0.03 * k))
            p.wrot['hand_R'] = qeuler(z=-70, x=-10 * k)
            arm_ik(p, sk, 'L', S(0.08, -0.22, 0.26 - 0.03 * k))
            p.rot_e('root', x=8)
        hem_ripple(p, t, amp=5, speed=2)
        p.rot_e('head', x=-6)
        return p
    clips['work'] = (24, work, True)
    return clips
