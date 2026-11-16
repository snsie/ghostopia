"""Character toolkit (task2): skeletons, lofted bodies, skinning by code, face shape keys, a pose solver
(FK + analytic two-bone IK), baking clips into NLA tracks, and glTF export with animations.

Coordinates are Blender armature space = world (the rig object sits at the origin): Z up, the character
faces -Y, its left side is +X.

Pose model
----------
Every bone gets a *world-axis delta rotation* q relative to its parent (\"rotate the forearm 30 deg about
world X\"), a translation t (in the parent's delta frame) and a local scale. The local Blender quaternion is
R_b^-1 q R_b with R_b the bone's rest orientation, so bone roll never matters. A bone can also be given a
world rotation target (feet flat on the floor, an item held upright) or be solved as the upper bone of a
two-bone IK chain (upper -> lower -> end) with a target for the end bone's head and a pole direction.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

import lib_geo as G

FPS = 24
I_Q = Quaternion()


# ----------------------------------------------------------------------------- small math
def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def qeuler(x=0.0, y=0.0, z=0.0):
    """World-axis rotation in degrees, applied X (pitch) then Y (roll) then Z (yaw)."""
    q = Quaternion((0, 0, 1), math.radians(z)) @ Quaternion((0, 1, 0), math.radians(y)) @ \
        Quaternion((1, 0, 0), math.radians(x))
    return q


def frame_mat(a, n):
    """Orthonormal 3x3 with columns (a, n', a x n') where n' is n made perpendicular to a."""
    a = a.normalized()
    n = (n - a * n.dot(a))
    if n.length < 1e-8:
        n = a.orthogonal()
    n.normalize()
    c = a.cross(n)
    m = Matrix((a, n, c)).transposed()
    return m


# ----------------------------------------------------------------------------- skeleton
class Skeleton:
    """Bone list in hierarchy order: name -> head, tail, parent, roll-up vector."""

    def __init__(self, name):
        self.name = name
        self.bones = {}
        self.order = []
        self.rest = {}   # name -> 4x4 rest matrix in armature space (filled by build_armature)
        self.chains = {}  # upper -> (lower, end)

    def add(self, name, head, tail, parent=None, up=(0, -1, 0), deform=True):
        self.bones[name] = dict(head=Vector(head), tail=Vector(tail), parent=parent, up=Vector(up), deform=deform)
        self.order.append(name)
        return name

    def chain(self, upper, lower, end):
        self.chains[upper] = (lower, end)

    def head(self, b):
        return self.bones[b]['head']

    def tail(self, b):
        return self.bones[b]['tail']

    def parent(self, b):
        return self.bones[b]['parent']


def build_armature(skel, coll):
    arm = bpy.data.armatures.new(skel.name + '_rig')
    ob = bpy.data.objects.new(skel.name + '_rig', arm)
    coll.objects.link(ob)
    arm.display_type = 'STICK'
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n in skel.order:
        b = skel.bones[n]
        eb = arm.edit_bones.new(n)
        eb.head = b['head']
        eb.tail = b['tail']
        eb.align_roll(b['up'])
        eb.use_deform = b['deform']
        if b['parent']:
            eb.parent = arm.edit_bones[b['parent']]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for n in skel.order:
        skel.rest[n] = arm.bones[n].matrix_local.copy()
    for pb in ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return ob


# ----------------------------------------------------------------------------- geometry
def bm_loft(sections, segs=12, side=(1, 0, 0), cap0='round', cap1='round', power=2.0, cap_len=0.8):
    """Tube through cross-sections [(centre, rx, ry), ...]. rx runs along `side`, ry along tangent x side.

    power 2 = ellipse, >2 = rounded box (chunky). Caps: 'round' (dome), 'flat', None (open).
    """
    bm = bmesh.new()
    cs = [Vector(s[0]) for s in sections]
    n = len(cs)
    sidev = Vector(side)
    rings = []

    def ring(c, t, rx, ry):
        s = (sidev - t * sidev.dot(t))
        if s.length < 1e-6:
            s = t.orthogonal()
        s.normalize()
        f = t.cross(s)
        vs = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            ca, sa = math.cos(a), math.sin(a)
            e = 2.0 / power
            x = math.copysign(abs(ca) ** e, ca)
            y = math.copysign(abs(sa) ** e, sa)
            vs.append(bm.verts.new(c + s * (x * rx) + f * (y * ry)))
        return vs

    tans = []
    for i in range(n):
        a = cs[max(0, i - 1)]
        b = cs[min(n - 1, i + 1)]
        tans.append((b - a).normalized())
    for i, sec in enumerate(sections):
        rings.append(ring(cs[i], tans[i], sec[1], sec[2]))

    def cap(idx, sign, kind):
        c, t = cs[idx], tans[idx] * sign
        rx, ry = sections[idx][1], sections[idx][2]
        if kind is None:
            return None
        if kind == 'flat':
            pole = bm.verts.new(c)
            return [pole], []
        ext = min(rx, ry) * cap_len
        extra = []
        for k in (1, 2):
            phi = k / 3 * math.pi / 2
            extra.append(ring(c + t * ext * math.sin(phi), tans[idx], rx * math.cos(phi), ry * math.cos(phi)))
        pole = bm.verts.new(c + t * ext)
        return [pole], extra

    def bridge(r0, r1):
        for k in range(segs):
            k2 = (k + 1) % segs
            try:
                bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
            except ValueError:
                pass

    for i in range(n - 1):
        bridge(rings[i], rings[i + 1])
    for idx, sign, kind in ((0, -1, cap0), (n - 1, 1, cap1)):
        res = cap(idx, sign, kind)
        if res is None:
            continue
        pole, extra = res
        prev = rings[idx]
        for r in extra:
            if sign < 0:
                bridge(r, prev)
            else:
                bridge(prev, r)
            prev = r
        for k in range(segs):
            k2 = (k + 1) % segs
            try:
                if sign < 0:
                    bm.faces.new((prev[k2], prev[k], pole[0]))
                else:
                    bm.faces.new((prev[k], prev[k2], pole[0]))
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_grid_surface(fn, nu, nv, closed_u=False):
    """Parametric surface p = fn(u, v) with u, v in [0, 1]. Returns bmesh."""
    bm = bmesh.new()
    cols = nu if closed_u else nu + 1
    vs = [[bm.verts.new(fn((i / nu), j / nv)) for j in range(nv + 1)] for i in range(cols)]
    for i in range(nu):
        i2 = (i + 1) % cols if closed_u else i + 1
        for j in range(nv):
            try:
                bm.faces.new((vs[i][j], vs[i2][j], vs[i2][j + 1], vs[i][j + 1]))
            except ValueError:
                pass
    return bm


class CharMesh:
    """Geometry pieces with a material and a skinning rule each; becomes one skinned mesh object."""

    def __init__(self, name, smooth_angle=70):
        self.node = G.MeshNode(name, smooth_angle=smooth_angle)
        self.parts = []  # (faces, rule)

    def add(self, bm, mat, rule, loc=(0, 0, 0), rot=(0, 0, 0), scale=None, uv='box', smooth=True):
        faces = self.node.put(bm, mat, loc, rot, scale, uv=uv, smooth=smooth)
        self.parts.append((faces, rule))
        return faces

    def loft(self, mat, rule, sections, segs=12, **kw):
        return self.add(bm_loft(sections, segs, **kw), mat, rule)

    def sphere(self, mat, rule, r, loc, scale=(1, 1, 1), segs=12, rings=8, rot=(0, 0, 0)):
        return self.add(G.bm_sphere(r, segs, rings), mat, rule, loc, rot, scale)

    def box(self, mat, rule, size, loc, rot=(0, 0, 0), bevel=0.02, segs=2):
        return self.add(G.bm_box(size, bevel, segs), mat, rule, loc, rot)

    def cyl(self, mat, rule, r1, r2, depth, loc, rot=(0, 0, 0), segs=10, bevel=0.01):
        return self.add(G.bm_cyl(r1, r2, depth, segs, bevel, 1), mat, rule, loc, rot)

    def lathe(self, mat, rule, profile, loc, segs=14, rot=(0, 0, 0)):
        return self.add(G.bm_lathe(profile, segs), mat, rule, loc, rot)

    def tube(self, mat, rule, pts, r, segs=8, taper=1.0):
        return self.add(G.bm_tube(pts, r, segs, taper), mat, rule)

    def ext(self, mat, rule, outline, thick, loc, rot=(0, 0, 0), bevel=0.01):
        return self.add(G.bm_extrude2d(outline, thick, bevel, 1), mat, rule, loc, rot)

    def build(self, coll, rig_ob, skel):
        node = self.node
        node.bm.verts.index_update()
        vparts = []
        for faces, rule in self.parts:
            idx = set()
            for f in faces:
                if f.is_valid:
                    for v in f.verts:
                        idx.add(v.index)
            vparts.append((idx, rule))
        ob = G._mesh_object(node, coll)
        if rig_ob is not None:
            skin(ob, rig_ob, skel, vparts)
        return ob


# ----------------------------------------------------------------------------- skinning
def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.dot(ab))))
    return (a + ab * t - p).length


def weights_for(p, rule, skel):
    kind = rule[0]
    if kind == 'rigid':
        return {rule[1]: 1.0}
    if kind == 'dist':
        bones, k = rule[1], (rule[2] if len(rule) > 2 else 4.0)
        w = {}
        for b in bones:
            d = seg_dist(p, skel.head(b), skel.tail(b))
            w[b] = 1.0 / max(1e-4, d) ** k
        return w
    if kind == 'fn':
        return rule[1](p)
    raise ValueError(rule)


def skin(ob, rig_ob, skel, vparts, max_inf=3):
    me = ob.data
    groups = {}
    for idx, rule in vparts:
        for i in idx:
            w = weights_for(me.vertices[i].co, rule, skel)
            top = sorted(w.items(), key=lambda kv: -kv[1])[:max_inf]
            s = sum(x for _, x in top)
            if s <= 0:
                continue
            for b, x in top:
                if x / s < 0.01:
                    continue
                groups.setdefault(b, []).append((i, x / s))
    for b in skel.order:
        vg = ob.vertex_groups.new(name=b)
        for i, x in groups.get(b, []):
            vg.add([i], x, 'REPLACE')
    ob.parent = rig_ob
    mod = ob.modifiers.new('rig', 'ARMATURE')
    mod.object = rig_ob


def rigid_object(ob, rig_ob, skel, bone):
    """Skin a whole object rigidly to one bone (hats: separate node, still driven by the skeleton)."""
    ob.parent = rig_ob
    for b in skel.order:
        vg = ob.vertex_groups.new(name=b)
        if b == bone:
            vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')
    mod = ob.modifiers.new('rig', 'ARMATURE')
    mod.object = rig_ob


def attach_to_bone(ob, rig_ob, bone, world_matrix):
    """Parent an object/empty to a bone keeping a given rest-pose world matrix (exported as a joint child)."""
    ob.parent = rig_ob
    ob.parent_type = 'BONE'
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = world_matrix
    bpy.context.view_layer.update()


# ----------------------------------------------------------------------------- face features + shape keys
class Feature:
    """A flat-ish face feature (eye, brow, mouth, highlight) on a head surface, with one shape per expression.

    The feature is a (nu x nv) grid over u in [-1, 1] (left-right) and s in [-1, 1] (bottom-top of the
    column). A shape is (width, dx, dy, top(u), bottom(u), thickness) in feature units (w, h): column x = u*width
    + dx, spans from bottom(u) to top(u) (+dy). Points are projected onto the head surface and lifted a bit.
    """

    def __init__(self, name, mat, centre, normal, up, w, h, lift=0.002, depth=0.0, nu=12, nv=6, mirror=False):
        self.name, self.mat = name, mat
        self.c = Vector(centre)
        self.n = Vector(normal).normalized()
        upv = Vector(up)
        self.v = (upv - self.n * upv.dot(self.n)).normalized()
        self.u = self.v.cross(self.n)  # +u = character's left when the normal faces -Y... see below
        # u should point to the viewer's right (character's left, +X) when the feature faces the viewer (-Y)
        if self.u.x < 0:
            self.u = -self.u
        self.w, self.h, self.lift, self.depth = w, h, lift, depth
        self.nu, self.nv = nu, nv
        self.mirror = mirror  # mirror shapes in u (for the right-side copy of eyes/brows)
        self.shapes = {}

    def shape(self, expr, width=1.0, dx=0.0, dy=0.0, top=None, bottom=None, thick=1.0):
        self.shapes[expr] = (width, dx, dy, top or (lambda u: math.sqrt(max(0.0, 1 - u * u))),
                             bottom or (lambda u: -math.sqrt(max(0.0, 1 - u * u))), thick)

    def points(self, expr, surf):
        width, dx, dy, top, bot, thick = self.shapes.get(expr, self.shapes['calm'])
        pts = []
        for i in range(self.nu + 1):
            u = -0.985 + 1.97 * i / self.nu
            uu = -u if self.mirror else u
            t, b = top(uu) + dy, bot(uu) + dy
            for j in range(self.nv + 1):
                s = -1 + 2 * j / self.nv
                x = (u * width + (-dx if self.mirror else dx)) * self.w
                y = (b + (t - b) * (s + 1) / 2) * self.h
                dome = self.depth * thick * math.sqrt(max(0, 1 - u * u)) * math.sqrt(max(0, 1 - s * s))
                p = self.c + self.u * x + self.v * y
                ps, nn = surf(p)
                pts.append(ps + nn * (self.lift + dome))
        return pts

    def faces(self, base):
        out = []
        cols = self.nv + 1
        for i in range(self.nu):
            for j in range(self.nv):
                a = base + i * cols + j
                out.append((a, a + cols, a + cols + 1, a + 1))
        return out


def build_face(name, features, exprs, surf, coll, rig_ob, skel, bone):
    """One mesh with all features; shape keys = exprs (first = basis)."""
    verts, faces, fmat = [], [], []
    mats = []
    for f in features:
        if f.mat not in mats:
            mats.append(f.mat)
        base = len(verts)
        verts += f.points(exprs[0], surf)
        fs = f.faces(base)
        faces += fs
        fmat += [mats.index(f.mat)] * len(fs)
    me = bpy.data.meshes.new(name)
    # winding: make normals face outward (along feature normal)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    for m in mats:
        me.materials.append(G.get_mat(m))
    for p, mi in zip(me.polygons, fmat):
        p.material_index = mi
        p.use_smooth = True
    # UVs = the feature's own grid (Godot needs UVs to build tangents)
    uvs = []
    for f in features:
        for i in range(f.nu + 1):
            for j in range(f.nv + 1):
                uvs.append((i / f.nu, j / f.nv))
    uvl = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        uvl.data[loop.index].uv = uvs[loop.vertex_index]
    me.update()
    # flip faces whose normal points into the head
    flip = []
    k = 0
    for f in features:
        for _ in f.faces(0):
            if me.polygons[k].normal.dot(f.n) < 0:
                flip.append(k)
            k += 1
    if flip:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in flip])
        bm.to_mesh(me)
        bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.shape_key_add(name='Basis')
    for e in exprs[1:]:
        kb = ob.shape_key_add(name=e, from_mix=False)
        pts = []
        for f in features:
            pts += f.points(e, surf)
        for i, p in enumerate(pts):
            kb.data[i].co = p
    if rig_ob is not None:
        rigid_object(ob, rig_ob, skel, bone)
    return ob


# ----------------------------------------------------------------------------- pose + solver
class Pose:
    def __init__(self):
        self.q = {}      # bone -> world-axis delta rotation (relative to parent)
        self.t = {}      # bone -> translation (parent delta frame)
        self.s = {}      # bone -> local scale (x, y, z), y = along the bone
        self.ik = {}     # upper -> (target, pole)
        self.wrot = {}   # bone -> world rotation (total delta)
        self.wpos = {}   # bone -> world head position (translation solved from it)
        self.shapes = {}  # expression -> weight
        self.ground = {}  # hips bone: feet that must stay reachable (auto pelvis drop)

    def rot(self, bone, q):
        self.q[bone] = q @ self.q.get(bone, Quaternion())
        return self

    def rot_e(self, bone, x=0.0, y=0.0, z=0.0):
        return self.rot(bone, qeuler(x, y, z))

    def move(self, bone, v):
        self.t[bone] = self.t.get(bone, Vector()) + Vector(v)
        return self


def solve(skel, pose):
    """Returns (local transforms {bone: (loc, quat, scale)}, pose matrices {bone: 4x4})."""
    M, W, local = {}, {}, {}
    wrot = dict(pose.wrot)
    for b in skel.order:
        p = skel.parent(b)
        Rb = skel.rest[b]
        rq = Rb.to_quaternion()
        if p:
            base = M[p] @ (skel.rest[p].inverted() @ Rb)
            Wp = W[p]
        else:
            base = Rb.copy()
            Wp = Quaternion()
        q = pose.q.get(b, Quaternion())
        t = pose.t.get(b, Vector())
        if b in pose.wpos:
            t = Wp.inverted() @ (Vector(pose.wpos[b]) - base.to_translation())
        if b in pose.ground:
            # lower this bone (pelvis) until every foot target is within reach
            for upper, target, length in pose.ground[b]:
                for _ in range(3):
                    Lm = Matrix.LocRotScale(rq.inverted() @ t, rq.inverted() @ q @ rq, None)
                    hip = (base @ Lm @ (Rb.inverted() @ skel.rest[upper])).to_translation()
                    d = (Vector(target) - hip)
                    if d.length <= length:
                        break
                    # solve |d + dz*Z| = length for dz >= 0 (moving the hip down by dz)
                    bq = d.z
                    cq = d.dot(d) - length * length
                    disc = bq * bq - cq
                    if disc > 0:
                        roots = [r for r in (-bq - math.sqrt(disc), -bq + math.sqrt(disc)) if r >= 0]
                        dz = min(roots) if roots else (d.length - length)
                    else:
                        dz = d.length - length
                    t = t + Wp.inverted() @ Vector((0, 0, -abs(dz) - 1e-4))
        if b in skel.chains and b in pose.ik:
            lower, end = skel.chains[b]
            target, pole = pose.ik[b]
            H = base.to_translation()
            a = (skel.head(lower) - skel.head(b)).length
            c_len = (skel.head(end) - skel.head(lower)).length
            T = Vector(target)
            d = T - H
            dist = max(1e-4, min(d.length, (a + c_len) * 0.9995, ))
            dist = max(dist, abs(a - c_len) + 1e-3)
            u = d.normalized()
            pv = Vector(pole)
            pv = (pv - u * pv.dot(u))
            if pv.length < 1e-6:
                pv = u.orthogonal()
            pv.normalize()
            cosA = (a * a + dist * dist - c_len * c_len) / (2 * a * dist)
            cosA = max(-1.0, min(1.0, cosA))
            sinA = math.sqrt(1 - cosA * cosA)
            K = H + (u * cosA + pv * sinA) * a
            E = H + u * dist
            # rest frames
            h0, k0, e0 = skel.head(b), skel.head(lower), skel.head(end)
            u0 = (e0 - h0).normalized()
            v0 = (k0 - h0) - u0 * (k0 - h0).dot(u0)
            if v0.length < 1e-6:
                v0 = Vector(skel.bones[b].get('pole', (0, -1, 0)))
            n0 = u0.cross(v0.normalized())
            n1 = u.cross(pv)
            Ru = frame_mat(K - H, n1) @ frame_mat(k0 - h0, n0).transposed()
            Rl = frame_mat(E - K, n1) @ frame_mat(e0 - k0, n0).transposed()
            Wu, Wl = Ru.to_quaternion(), Rl.to_quaternion()
            q = Wp.inverted() @ Wu
            wrot[lower] = Wl
        if b in wrot:
            q = Wp.inverted() @ wrot[b]
        lq = rq.inverted() @ q @ rq
        lt = rq.inverted() @ t
        s = Vector(pose.s.get(b, (1, 1, 1)))
        L = Matrix.LocRotScale(lt, lq, s)
        M[b] = base @ L
        W[b] = Wp @ q
        local[b] = (lt, lq, s)
    return local, M


# ----------------------------------------------------------------------------- baking clips
def _fc(act, ob, path, i, group):
    return act.fcurve_ensure_for_datablock(ob, path, index=i, group_name=group)


def bake_clip(rig_ob, skel, name, n_frames, pose_fn, face_obs=(), extra=None):
    """Sample pose_fn(frame) for frame 0..n_frames and store as an NLA track named `name` on the rig and on
    each face object's shape keys (the glTF exporter merges same-named tracks into one animation).
    extra(frame, local, M) may return {object: matrix_basis} for non-bone objects (unused for now)."""
    act = bpy.data.actions.new(f'{rig_ob.name}|{name}')
    ad = rig_ob.animation_data or rig_ob.animation_data_create()
    ad.action = act
    data = {b: ([], [], []) for b in skel.order}
    shapes = []
    prevq = {}
    for f in range(n_frames + 1):
        pose = pose_fn(f)
        local, _ = solve(skel, pose)
        for b in skel.order:
            lt, lq, s = local[b]
            if b in prevq and prevq[b].dot(lq) < 0:
                lq = -lq
            prevq[b] = lq
            data[b][0].append(lt)
            data[b][1].append(lq)
            data[b][2].append(s)
        shapes.append(dict(pose.shapes))
    for b in skel.order:
        pb = rig_ob.pose.bones[b]
        for path, arr, nc in (('location', data[b][0], 3), ('rotation_quaternion', data[b][1], 4),
                              ('scale', data[b][2], 3)):
            dp = pb.path_from_id(path)
            for i in range(nc):
                fc = _fc(act, rig_ob, dp, i, b)
                fc.keyframe_points.add(len(arr))
                co = []
                for f, val in enumerate(arr):
                    co += [f, val[i]]
                fc.keyframe_points.foreach_set('co', co)
                fc.keyframe_points.foreach_set("interpolation", [1] * len(arr))  # LINEAR
                fc.update()
    ad.action = None
    tr = ad.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 0, act)
    tr.mute = False
    for fo in face_obs:
        key = fo.data.shape_keys
        kad = key.animation_data or key.animation_data_create()
        sact = bpy.data.actions.new(f'{fo.name}|{name}')
        kad.action = sact
        for kb in key.key_blocks[1:]:
            fc = _fc(sact, key, f'key_blocks["{kb.name}"].value', 0, 'face')
            fc.keyframe_points.add(n_frames + 1)
            co = []
            for f in range(n_frames + 1):
                co += [f, shapes[f].get(kb.name, 0.0)]
            fc.keyframe_points.foreach_set('co', co)
            fc.update()
        kad.action = None
        t2 = kad.nla_tracks.new()
        t2.name = name
        t2.strips.new(name, 0, sact)
    return act


def play(rig_ob, face_obs, name, frame):
    """Show clip `name` at `frame` (for preview renders): solo its NLA track on the rig and the faces."""
    for ob in [rig_ob] + [fo.data.shape_keys for fo in face_obs]:
        ad = ob.animation_data
        if ad is None:
            continue
        for tr in ad.nla_tracks:
            tr.mute = tr.name != name
            tr.is_solo = False
    bpy.context.scene.frame_set(int(frame))


def rest_pose(rig_ob, face_obs):
    for ob in [rig_ob] + [fo.data.shape_keys for fo in face_obs]:
        ad = ob.animation_data
        if ad is None:
            continue
        for tr in ad.nla_tracks:
            tr.mute = True
    for pb in rig_ob.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    for fo in face_obs:
        for kb in fo.data.shape_keys.key_blocks[1:]:
            kb.value = 0.0
    bpy.context.scene.frame_set(0)


# ----------------------------------------------------------------------------- export
def export_character(rig_ob, path):
    """glTF Separate with skins, shape keys and one animation per NLA track; lights RAW x 1/30."""
    objs = [rig_ob] + list(rig_ob.children_recursive)
    lights = [o for o in objs if o.type == 'LIGHT']
    saved = [(o, o.data.energy) for o in lights]
    for o, e in saved:
        o.data.energy = e / 30.0
    hidden = [(o, o.hide_render, o.hide_get()) for o in objs]
    for ob in [rig_ob] + [o.data.shape_keys for o in objs if o.type == 'MESH' and o.data.shape_keys]:
        if ob.animation_data:
            for tr in ob.animation_data.nla_tracks:
                tr.mute = False
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.hide_set(False)
        o.hide_render = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig_ob
    bpy.context.scene.frame_set(0)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLTF_SEPARATE', use_selection=True, export_yup=True, export_apply=False,
        export_lights=True, export_import_convert_lighting_mode='RAW', export_keep_originals=True,
        export_extras=True, export_cameras=False, export_animations=True, export_animation_mode='NLA_TRACKS',
        export_skins=True, export_morph=True, export_morph_normal=False, export_morph_animation=True,
        export_influence_nb=4, export_force_sampling=True, export_frame_step=1, export_optimize_animation_size=True,
        export_anim_slide_to_zero=True, export_reset_pose_bones=True, export_rest_position_armature=True)
    for o, e in saved:
        o.data.energy = e
    for o, hr, hv in hidden:
        o.hide_render = hr
        o.hide_set(hv)
