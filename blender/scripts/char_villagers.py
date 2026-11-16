"""Villagers of Millbrook (concept/characters/villagers.png, scare_reactions.png, cottage_interior_night.png).

One shared humanoid skeleton (21 bones, same names for everyone; proportions differ per villager):
    root > hips > spine > chest > neck > head > hat
    chest > shoulder_L/R > upperarm_L/R > forearm_L/R > hand_L/R
    hips > thigh_L/R > shin_L/R > foot_L/R
Bodies are lofts, clothes are shells over them, everything is skinned by code (<= 3 bones per vertex).
Faces are one mesh per villager with shape keys calm / uneasy / scared / terrified / relieved (+ asleep).
Hats are a separate mesh on the `hat` bone, so Godot can hide it and throw a physics hat.

Clips are written as control poses (body-level controls: hand targets in the chest frame, foot targets in
the root frame, torso and head angles, expression weights) that are keyed and smoothstepped; walking and
running use a foot-planted gait: a stance foot moves backward at exactly the clip's no-slide speed.
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

import lib_char as C
import lib_geo as G
from lib_char import Pose, qeuler, smooth, lerp

VILLAGERS = ['widow', 'farmer', 'maid', 'teacher', 'child']
EXPRS = ['calm', 'uneasy', 'scared', 'terrified', 'relieved', 'asleep']


def mats():
    d = G.define_mat
    d('skin', None, 1, color=(1.0, 0.77, 0.63, 1), rough=0.7)
    d('skin_ruddy', None, 1, color=(0.98, 0.68, 0.55, 1), rough=0.7)
    d('blush', None, 1, color=(0.98, 0.55, 0.52, 1), rough=0.8)
    d('nose_tip', None, 1, color=(0.97, 0.62, 0.5, 1), rough=0.7)
    d('eye_black', None, 1, color=(0.07, 0.04, 0.06, 1), rough=0.2)
    d('eye_shine', None, 1, color=(1, 1, 1, 1), rough=0.3, emit=(1, 1, 1), emit_strength=0.4)
    d('mouth', None, 1, color=(0.38, 0.12, 0.13, 1), rough=0.6)
    d('hair_grey', 'cloth_linen.png', 0.15, color=(0.86, 0.85, 0.88, 1))
    d('hair_white', 'cloth_linen.png', 0.15, color=(0.96, 0.95, 0.93, 1))
    d('hair_brown', 'wood_grain.png', 0.2, color=(0.62, 0.4, 0.3, 1))
    d('hair_dark', 'wood_grain_dark.png', 0.2, color=(0.6, 0.42, 0.36, 1))
    d('dress_purple', 'cloth_linen.png', 0.35, color=(0.5, 0.36, 0.56, 1))
    d('dress_plum', 'canvas.png', 0.35, color=(0.42, 0.28, 0.45, 1))
    d('dress_lilac', 'cloth_linen.png', 0.35, color=(0.66, 0.52, 0.72, 1))
    d('shawl', 'canvas.png', 0.3, color=(0.5, 0.33, 0.55, 1))
    d('overalls', 'canvas.png', 0.35, color=(0.5, 0.35, 0.26, 1))
    d('coat_slate', 'canvas.png', 0.35, color=(0.42, 0.42, 0.55, 1))
    d('waistcoat', 'canvas.png', 0.3, color=(0.78, 0.6, 0.3, 1))
    d('cream', 'cloth_linen.png', 0.3, color=(0.97, 0.93, 0.84, 1))
    d('apron_white', 'cloth_linen.png', 0.3, color=(1.0, 0.98, 0.93, 1))
    d('boot', 'canvas.png', 0.3, color=(0.42, 0.27, 0.19, 1), rough=0.6)
    d('belt', 'canvas.png', 0.3, color=(0.36, 0.22, 0.15, 1), rough=0.6)
    d('garlic', None, 1, color=(0.98, 0.96, 0.9, 1), rough=0.6)
    d('lavender', None, 1, color=(0.6, 0.45, 0.85, 1), rough=0.8)
    d('glasses', None, 1, color=(0.15, 0.1, 0.1, 1), rough=0.3, metal=0.5)
    d('salt', None, 1, color=(1, 1, 1, 1), rough=0.9)
    G.define_mat('leather', 'canvas.png', 0.3, color=(0.45, 0.28, 0.18, 1), rough=0.7)


# ----------------------------------------------------------------------------- proportions
# heights in metres; the farmer is the 1.8 m reference villager (2 blocks), hat included under 2 m doors
PROPS = {
    'farmer': dict(top=1.74, head_c=1.5, head_r=(0.215, 0.2, 0.235), neck_z=1.28, chest_z=1.02, hip_z=0.74,
                   knee_z=0.4, ankle_z=0.1, hip_w=0.13, sh_w=0.27, sh_z=1.24, ua=0.3, fa=0.27, hand=0.13,
                   foot=0.24, arm_a=17, posture=4, hat=True),
    'widow': dict(top=1.5, head_c=1.29, head_r=(0.19, 0.18, 0.205), neck_z=1.08, chest_z=0.86, hip_z=0.62,
                  knee_z=0.34, ankle_z=0.08, hip_w=0.1, sh_w=0.2, sh_z=1.04, ua=0.25, fa=0.22, hand=0.1,
                  foot=0.18, arm_a=16, posture=12, hat=False),
    'maid': dict(top=1.6, head_c=1.38, head_r=(0.19, 0.18, 0.21), neck_z=1.16, chest_z=0.93, hip_z=0.7,
                 knee_z=0.39, ankle_z=0.08, hip_w=0.09, sh_w=0.18, sh_z=1.12, ua=0.26, fa=0.23, hand=0.1,
                 foot=0.18, arm_a=14, posture=2, hat=True),
    'teacher': dict(top=1.68, head_c=1.47, head_r=(0.18, 0.17, 0.2), neck_z=1.26, chest_z=1.0, hip_z=0.78,
                    knee_z=0.43, ankle_z=0.08, hip_w=0.09, sh_w=0.19, sh_z=1.22, ua=0.28, fa=0.25, hand=0.1,
                    foot=0.19, arm_a=12, posture=-2, hat=False),
    'child': dict(top=1.1, head_c=0.9, head_r=(0.19, 0.18, 0.2), neck_z=0.69, chest_z=0.56, hip_z=0.42,
                  knee_z=0.23, ankle_z=0.06, hip_w=0.07, sh_w=0.13, sh_z=0.66, ua=0.16, fa=0.15, hand=0.075,
                  foot=0.13, arm_a=14, posture=0, hat=True),
}


def skeleton(name, P):
    sk = C.Skeleton(name)
    hz, top = P['hip_z'], P['top']
    sk.add('root', (0, 0, 0), (0, 0, 0.12))
    sk.add('hips', (0, 0, hz), (0, 0, hz + 0.1), 'root')
    sk.add('spine', (0, 0, hz + 0.1), (0, 0, P['chest_z']), 'hips')
    sk.add('chest', (0, 0, P['chest_z']), (0, 0, P['neck_z']), 'spine')
    head_base = P['head_c'] - P['head_r'][2] * 0.85
    sk.add('neck', (0, 0, P['neck_z']), (0, 0, head_base), 'chest')
    sk.add('head', (0, 0, head_base), (0, 0, top), 'neck')
    sk.add('hat', (0, 0, top - 0.06), (0, 0, top + 0.1), 'head')
    a = math.radians(P['arm_a'])
    for side, sx in (('L', 1), ('R', -1)):
        sh = Vector((sx * P['sh_w'], 0.0, P['sh_z']))
        d = Vector((sx * math.sin(a), 0, -math.cos(a)))
        el = sh + d * P['ua'] + Vector((0, 0.025, 0))
        wr = sh + d * (P['ua'] + P['fa'])
        sk.add(f'shoulder_{side}', (sx * 0.05, 0, P['sh_z'] + 0.02), sh, 'chest', up=(0, 0, 1))
        sk.add(f'upperarm_{side}', sh, el, f'shoulder_{side}', up=(0, -1, 0))
        sk.add(f'forearm_{side}', el, wr, f'upperarm_{side}', up=(0, -1, 0))
        sk.add(f'hand_{side}', wr, wr + d * P['hand'], f'forearm_{side}', up=(0, -1, 0))
        sk.chain(f'upperarm_{side}', f'forearm_{side}', f'hand_{side}')
    for side, sx in (('L', 1), ('R', -1)):
        hp = Vector((sx * P['hip_w'], 0, hz))
        kn = Vector((sx * P['hip_w'], -0.025, P['knee_z']))
        an = Vector((sx * P['hip_w'], 0, P['ankle_z']))
        sk.add(f'thigh_{side}', hp, kn, 'hips', up=(0, -1, 0))
        sk.add(f'shin_{side}', kn, an, f'thigh_{side}', up=(0, -1, 0))
        sk.add(f'foot_{side}', an, an + Vector((0, -P['foot'] * 0.75, -P['ankle_z'] + 0.03)), f'shin_{side}',
               up=(0, 0, 1))
        sk.chain(f'thigh_{side}', f'shin_{side}', f'foot_{side}')
    return sk


# ----------------------------------------------------------------------------- head helpers
def head_surf(P):
    c = Vector((0, 0, P['head_c']))
    rx, ry, rz = P['head_r']

    def surf(p):
        d = p - c
        k = 1.0 / math.sqrt((d.x / rx) ** 2 + (d.y / ry) ** 2 + (d.z / rz) ** 2)
        ps = c + d * k
        q = ps - c
        n = Vector((q.x / rx ** 2, q.y / ry ** 2, q.z / rz ** 2)).normalized()
        return ps, n
    return surf


def on_head(P, x, z, out=0.0):
    """Point on the front of the head at (x, z) relative to the head centre (fractions of the radii)."""
    rx, ry, rz = P['head_r']
    y = -ry * math.sqrt(max(0.0, 1 - x * x - z * z))
    ps, n = head_surf(P)(Vector((x * rx, y, P['head_c'] + z * rz)))
    return ps + n * out, n


EYE_X, EYE_Z = 0.3, -0.03


def face_features(P, mouth_lift=0.0, brow_mat='hair_brown', eye_scale=1.0, mouth_z=-0.47):
    rx, ry, rz = P['head_r']
    feats = []
    ew, eh = 0.15 * rx * eye_scale, 0.23 * rz * eye_scale
    circ = (lambda k: (lambda u: k * math.sqrt(max(0, 1 - u * u))))
    ncirc = (lambda k: (lambda u: -k * math.sqrt(max(0, 1 - u * u))))
    for side, sx in (('L', 1), ('R', -1)):
        c, n = on_head(P, sx * EYE_X, EYE_Z)
        e = C.Feature(f'eye_{side}', 'eye_black', c, n, (0, 0, 1), ew, eh, lift=0.002, depth=0.006, nu=10, nv=8,
                      mirror=sx < 0)
        e.shape('calm')
        e.shape('uneasy', 0.9, top=lambda u: 0.75 * math.sqrt(max(0, 1 - u * u)) - 0.15 * u,
                bottom=ncirc(0.95))
        e.shape('scared', 1.15, dy=0.1, top=circ(1.2), bottom=ncirc(1.2))
        e.shape('terrified', 1.35, dy=0.2, top=circ(1.45), bottom=ncirc(1.35))
        e.shape('relieved', 1.1, dy=0.1, top=lambda u: 0.32 - 0.55 * u * u + 0.12,
                bottom=lambda u: 0.32 - 0.55 * u * u - 0.1, thick=0.3)
        e.shape('asleep', 1.0, dy=-0.25, top=lambda u: -0.25 * u * u + 0.08, bottom=lambda u: -0.25 * u * u - 0.06,
                thick=0.2)
        feats.append(e)
        # highlight (white dot, upper outer)
        hc = c + Vector((sx * 0.3 * ew, 0, 0.42 * eh))
        hp, hn = head_surf(P)(hc)
        h = C.Feature(f'shine_{side}', 'eye_shine', hp, hn, (0, 0, 1), 0.3 * ew, 0.3 * ew, lift=0.0045, nu=6, nv=4)
        h.shape('calm')
        h.shape('uneasy', 0.9, dy=-0.3)
        h.shape('scared', 1.1, dx=0.0, dy=0.6)
        h.shape('terrified', 1.2, dy=1.2)
        z0 = (lambda u: 0.0)
        h.shape('relieved', 0.05, top=z0, bottom=z0)
        h.shape('asleep', 0.05, top=z0, bottom=z0)
        feats.append(h)
        # brows: strip around a centre curve c(u); +tilt raises the inner end (worried)
        bc, bn = on_head(P, sx * (EYE_X + 0.02), EYE_Z + 0.27)
        bw, bh = 0.15 * rx, 0.1 * rz
        b = C.Feature(f'brow_{side}', brow_mat, bc, bn, (0, 0, 1), bw, bh, lift=0.004, depth=0.004, nu=8, nv=2,
                      mirror=sx < 0)

        def brow(dy, tilt, arch, th=0.28):
            return dict(top=lambda u: dy + arch * (1 - u * u) - tilt * u + th,
                        bottom=lambda u: dy + arch * (1 - u * u) - tilt * u - th)
        b.shape('calm', **brow(0.0, 0.15, 0.3))
        b.shape('uneasy', **brow(0.15, 0.45, 0.1))
        b.shape('scared', **brow(0.75, 0.5, 0.25))
        b.shape('terrified', **brow(1.25, 0.65, 0.3))
        b.shape('relieved', **brow(0.35, -0.2, 0.45))
        b.shape('asleep', **brow(-0.1, 0.0, 0.2))
        feats.append(b)
        # rosy cheeks
        cc, cn = on_head(P, sx * 0.47, -0.3)
        ch = C.Feature(f'cheek_{side}', 'blush', cc, cn, (0, 0, 1), 0.12 * rx, 0.07 * rz, lift=0.0015, nu=6, nv=4)
        ch.shape('calm')
        feats.append(ch)
    mc, mn = on_head(P, 0.0, mouth_z, mouth_lift)
    m = C.Feature('mouth', 'mouth', mc, mn, (0, 0, 1), 0.17 * rx, 0.1 * rz, lift=0.003, depth=0.002, nu=12, nv=6)
    m.shape('calm', 0.8, top=lambda u: 0.45 * u * u - 0.1 + 0.16, bottom=lambda u: 0.45 * u * u - 0.1 - 0.16)
    m.shape('uneasy', 0.75, top=lambda u: 0.12 * math.sin(3.2 * u) + 0.15, bottom=lambda u: 0.12 * math.sin(3.2 * u) - 0.15)
    m.shape('scared', 0.55, dy=-0.2, top=circ(0.75), bottom=ncirc(0.95))
    m.shape('terrified', 1.0, dy=-0.55, top=circ(0.9), bottom=ncirc(1.7))
    m.shape('relieved', 1.25, dy=-0.1, top=lambda u: 0.25 + 0.25 * u * u,
            bottom=lambda u: 0.25 + 0.25 * u * u - 1.5 * math.sqrt(max(0, 1 - u * u)) - 0.05)
    m.shape('asleep', 0.5, top=lambda u: 0.1, bottom=lambda u: -0.1)
    feats.append(m)
    return feats


# ----------------------------------------------------------------------------- body building helpers
class Body:
    def __init__(self, name, P, sk):
        self.P, self.sk, self.name = P, sk, name
        self.cm = C.CharMesh(f'{name}_body', smooth_angle=75)
        self.hat = None

    # rules
    def torso_rule(self):
        return ('dist', ['hips', 'spine', 'chest'], 3)

    def arm_rule(self, side):
        return ('dist', [f'shoulder_{side}', f'upperarm_{side}', f'forearm_{side}', f'hand_{side}'], 4)

    def leg_rule(self, side):
        return ('dist', ['hips', f'thigh_{side}', f'shin_{side}'], 4)

    def skirt_rule(self, spread=0.45):
        P = self.P

        def fn(p):
            z = p.z
            k = spread * smooth((P['hip_z'] + 0.02 - z) / (P['hip_z'] * 0.8))
            side_l = smooth((p.x / max(0.05, P['hip_w'] * 2.5) + 1) / 2)
            w = {'hips': 1 - k + 1e-3}
            if k > 0:
                w['thigh_L'] = k * side_l
                w['thigh_R'] = k * (1 - side_l)
            if z > P['hip_z'] + 0.05:
                w['spine'] = smooth((z - P['hip_z'] - 0.05) / 0.15)
            return w
        return ('fn', fn)

    def torso(self, mat, prof, segs=18, power=2.2, cap0='round', cap1=None):
        """prof: [(z, rx, ry, yoff)]"""
        secs = [(Vector((0, yo, z)), rx, ry) for z, rx, ry, yo in prof]
        self.cm.loft(mat, self.torso_rule(), secs, segs, power=power, cap0=cap0, cap1=cap1)

    def neck(self, mat='skin', r=0.06):
        P = self.P
        secs = [(Vector((0, 0.01, P['neck_z'] - 0.04)), r, r), (Vector((0, 0.01, P['head_c'] - 0.05)), r * 0.95,
                                                               r * 0.95)]
        self.cm.loft(mat, ('dist', ['chest', 'neck', 'head'], 3), secs, 10, cap0=None, cap1=None)

    def head(self, mat='skin', nose=0.032, nose_mat='nose_tip', ears=True):
        P = self.P
        rx, ry, rz = P['head_r']
        c = Vector((0, 0, P['head_c']))
        self.cm.sphere(mat, ('rigid', 'head'), 1.0, c, scale=(rx, ry, rz), segs=24, rings=16)
        np_, nn = on_head(P, 0.0, -0.2)
        self.cm.sphere(nose_mat, ('rigid', 'head'), nose, np_ + nn * nose * 0.4, scale=(1.05, 0.9, 0.9), segs=10,
                       rings=8)
        if ears:
            for sx in (-1, 1):
                self.cm.sphere(mat, ('rigid', 'head'), rz * 0.2, c + Vector((sx * rx * 0.97, 0.01, -0.05 * rz)),
                               scale=(0.45, 0.8, 1.0), segs=10, rings=6)

    def arm(self, side, sleeve, cuff=None, sleeve_end=1.0, r_sh=0.07, r_el=0.058, r_wr=0.045, skin='skin',
            puff=0.0):
        sk = self.sk
        sh = sk.head(f'upperarm_{side}')
        el = sk.head(f'forearm_{side}')
        wr = sk.head(f'hand_{side}')
        sx = 1 if side == 'L' else -1
        inner = sh + Vector((-sx * 0.05, 0, 0.0))
        rule = self.arm_rule(side)
        # sleeve to `sleeve_end` (0..1 of the forearm), bare skin after
        mid = el.lerp(wr, sleeve_end) if sleeve_end < 1 else wr
        r_mid = lerp(r_el, r_wr, sleeve_end)
        secs = [(inner, r_sh * 0.95, r_sh * 0.9), (sh, r_sh + puff, r_sh * 0.95 + puff),
                (sh.lerp(el, 0.5), (r_sh + r_el) / 2 + puff * 0.6, (r_sh + r_el) / 2 * 0.95 + puff * 0.6),
                (el, r_el, r_el * 0.95), (mid, r_mid, r_mid * 0.95)]
        self.cm.loft(sleeve, rule, secs, 12, cap0='round', cap1='flat' if sleeve_end < 1 else None)
        if sleeve_end < 1:
            self.cm.loft(skin, rule, [(mid - (wr - el).normalized() * 0.02, r_mid * 0.85, r_mid * 0.8),
                                      (wr, r_wr * 0.9, r_wr * 0.85)], 10, cap0=None, cap1=None)
            if cuff:
                self.cm.loft(cuff, rule, [(mid - (wr - el).normalized() * 0.005, r_mid * 1.12, r_mid * 1.08),
                                          (mid + (wr - el).normalized() * 0.03, r_mid * 1.1, r_mid * 1.05)], 12,
                             cap0='flat', cap1='flat')
        elif cuff:
            self.cm.loft(cuff, rule, [(wr - (wr - el).normalized() * 0.04, r_wr * 1.2, r_wr * 1.15),
                                      (wr, r_wr * 1.15, r_wr * 1.1)], 12, cap0='flat', cap1='flat')
        self.hand(side, skin)

    def hand(self, side, skin='skin'):
        sk, P = self.sk, self.P
        wr = sk.head(f'hand_{side}')
        tip = sk.tail(f'hand_{side}')
        d = (tip - wr).normalized()
        sx = 1 if side == 'L' else -1
        L = P['hand']
        rule = ('rigid', f'hand_{side}')
        # chunky mitten: palm + finger block + thumb
        self.cm.sphere(skin, rule, 1.0, wr + d * L * 0.4, scale=(L * 0.42, L * 0.36, L * 0.48), segs=12, rings=8)
        self.cm.sphere(skin, rule, 1.0, wr + d * L * 0.78, scale=(L * 0.38, L * 0.3, L * 0.32), segs=12, rings=8)
        self.cm.sphere(skin, rule, 1.0, wr + d * L * 0.35 + Vector((-sx * 0.0, -L * 0.33, 0)),
                       scale=(L * 0.15, L * 0.15, L * 0.28), segs=8, rings=6)

    def leg(self, side, mat, r_th=0.09, r_kn=0.07, r_an=0.055, top_extra=0.0, cap0='round'):
        sk = self.sk
        hp, kn, an = sk.head(f'thigh_{side}'), sk.head(f'shin_{side}'), sk.head(f'foot_{side}')
        secs = [(hp + Vector((0, 0, 0.06 + top_extra)), r_th * 1.05, r_th), (hp, r_th, r_th * 0.98),
                (kn, r_kn, r_kn * 0.98), (an + Vector((0, 0, 0.03)), r_an, r_an)]
        self.cm.loft(mat, self.leg_rule(side), secs, 12, cap0=cap0, cap1='flat')

    def boot(self, side, mat='boot', h=0.12, cuff=None):
        sk, P = self.sk, self.P
        an = sk.head(f'foot_{side}')
        L = P['foot']
        rule = ('dist', [f'shin_{side}', f'foot_{side}'], 6)
        base = Vector((an.x, 0, 0))
        secs = [(base + Vector((0, 0.06, 0.04)), 0.055, 0.04), (base + Vector((0, 0.0, 0.05)), 0.065, 0.05),
                (base + Vector((0, -L * 0.45, 0.045)), 0.07, 0.045), (base + Vector((0, -L * 0.72, 0.04)), 0.062, 0.038)]
        secs = [(c, rx * L / 0.22, ry * L / 0.22 + 0.006) for c, rx, ry in secs]
        self.cm.loft(mat, ('rigid', f'foot_{side}'), secs, 12, side=(1, 0, 0), power=2.4)
        # shaft
        self.cm.loft(mat, rule, [(an + Vector((0, 0.005, -0.04)), 0.062 * L / 0.22, 0.062 * L / 0.22),
                                 (an + Vector((0, 0, h)), 0.06 * L / 0.22, 0.058 * L / 0.22)], 12, cap0=None,
                     cap1='flat' if not cuff else None)
        if cuff:
            self.cm.loft(cuff, rule, [(an + Vector((0, 0, h - 0.01)), 0.068 * L / 0.22, 0.066 * L / 0.22),
                                      (an + Vector((0, 0, h + 0.025)), 0.07 * L / 0.22, 0.068 * L / 0.22)], 12,
                         cap0='flat', cap1='flat')

    def skirt(self, mat, z_top, z_bot, r_top, r_bot, ry_scale=0.9, segs=24, frill=0.0, yoff=0.0, rule=None):
        n = 6
        secs = []
        for i in range(n + 1):
            t = i / n
            z = lerp(z_top, z_bot, t)
            r = lerp(r_top, r_bot, t ** 0.8)
            secs.append((Vector((0, yoff * t, z)), r, r * ry_scale))
        bm = C.bm_loft(secs, segs, cap0=None, cap1=None)
        if frill:
            for v in bm.verts:
                if abs(v.co.z - z_bot) < 1e-4:
                    a = math.atan2(v.co.y, v.co.x)
                    v.co.z += frill * math.sin(a * 9)
        self.cm.add(bm, mat, rule or self.skirt_rule())

    def panel(self, mat, rule, fn, nu=10, nv=8, thick=0.008):
        """Front panel (apron, bib) from a surface fn(u, v) -> point, solidified."""
        import bmesh
        bm = C.bm_grid_surface(fn, nu, nv)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick)
        self.cm.add(bm, mat, rule)

    def belt(self, z, rx, ry, mat='belt', h=0.045, yoff=0.0):
        self.cm.loft(mat, ('rigid', 'hips') if z < self.P['hip_z'] + 0.12 else self.torso_rule(),
                     [(Vector((0, yoff, z - h / 2)), rx, ry), (Vector((0, yoff, z + h / 2)), rx, ry)], 24,
                     cap0='flat', cap1='flat')

    def hair_cap(self, mat, scale=(1.06, 1.07, 1.04), offset=(0, 0.03, 0.04), brow=0.32, side=0.62):
        """Hair shell over the head with the face left open (below `brow` and inside `side` x rx)."""
        import bmesh
        P = self.P
        rx, ry, rz = P['head_r']
        hb = G.bm_sphere(1.0, 26, 16)
        bmesh.ops.scale(hb, vec=(rx * scale[0], ry * scale[1], rz * scale[2]), verts=hb.verts)
        off = Vector(offset)
        kill = []
        for f in hb.faces:
            c = f.calc_center_median() + off
            if c.y < -ry * 0.2 and c.z < rz * brow and abs(c.x) < rx * side:
                kill.append(f)
            elif c.y < -ry * 0.55 and c.z < rz * brow + 0.02:
                kill.append(f)
        bmesh.ops.delete(hb, geom=kill, context='FACES')
        bmesh.ops.solidify(hb, geom=hb.faces[:], thickness=0.012)
        self.cm.add(hb, mat, ('rigid', 'head'), loc=Vector((0, 0, P['head_c'])) + off)

    def blobs(self, mat, rule, pts):
        for c, r, sc in pts:
            self.cm.sphere(mat, rule, r, c, scale=sc, segs=10, rings=7)

    # charms on the belt (design plan: garlic, horseshoe, salt pouch)
    def garlic(self, pos):
        rule = ('rigid', 'hips')
        p = Vector(pos)
        self.cm.lathe('garlic', rule, [(0.0, 0.0), (0.03, 0.012), (0.038, 0.035), (0.025, 0.06), (0.008, 0.075),
                                       (0.004, 0.09), (0.0, 0.092)], p + Vector((0, 0, -0.09)), segs=10)
        self.cm.tube('belt', rule, [p + Vector((0, 0, -0.005)), p + Vector((0, 0, 0.03))], 0.005, 5)

    def horseshoe(self, pos, s=1.0):
        p = Vector(pos)
        pts = [p + Vector((math.cos(a) * 0.04 * s, 0, -0.03 * s + math.sin(a) * 0.045 * s))
               for a in [math.radians(-30 - 240 * k / 10) for k in range(11)]]
        self.cm.tube('iron', ('rigid', 'hips'), pts, 0.011 * s, 6)

    def pouch(self, pos, mat='leather', r=0.05, salt=True):
        p = Vector(pos)
        rule = ('rigid', 'hips')
        self.cm.sphere(mat, rule, r, p, scale=(1.0, 0.7, 1.15), segs=10, rings=7)
        self.cm.cyl('belt', rule, r * 0.35, r * 0.4, 0.02, p + Vector((0, 0, r * 1.05)), segs=8)
        if salt:
            self.cm.sphere('salt', rule, r * 0.35, p + Vector((0, -r * 0.55, r * 0.2)), scale=(1, 0.5, 0.8),
                           segs=8, rings=5)

    def make_hat(self, coll, rig, build_fn):
        cm = C.CharMesh(f'{self.name}_hat', smooth_angle=70)
        build_fn(cm)
        node = cm.node
        ob = G._mesh_object(node, coll)
        C.rigid_object(ob, rig, self.sk, 'hat')
        self.hat = ob
        return ob


# ----------------------------------------------------------------------------- the five villagers
def widow(B):
    P, cm = B.P, B.cm
    hz = P['hip_z']
    B.torso('dress_plum', [(hz - 0.06, 0.15, 0.13, 0.0), (hz + 0.08, 0.2, 0.18, 0.0), (hz + 0.24, 0.22, 0.19, -0.02),
                           (P['chest_z'] + 0.05, 0.2, 0.17, 0.0), (P['neck_z'] - 0.05, 0.14, 0.12, 0.01),
                           (P['neck_z'] + 0.02, 0.07, 0.07, 0.01)])
    B.neck()
    B.head()
    for side in ('L', 'R'):
        B.arm(side, 'dress_plum', cuff='cream', sleeve_end=0.85, r_sh=0.07, r_el=0.06, r_wr=0.045)
        B.leg(side, 'dress_plum', 0.075, 0.06, 0.045)
        B.boot(side, 'boot', 0.08)
    B.skirt('dress_purple', hz + 0.12, 0.07, 0.21, 0.31, frill=0.012)
    # white apron with a patch
    def apron(u, v):
        x = (u - 0.5) * 0.36
        z = lerp(hz + 0.12, 0.2, v)
        r = lerp(0.215, 0.31, (1 - (z - 0.07) / (hz + 0.05)) ** 0.8) + 0.012
        y = -math.sqrt(max(0.0, r * r * 0.81 - x * x * 0.9))
        return Vector((x, y - 0.006, z))
    B.panel('apron_white', B.skirt_rule(0.35), apron)
    B.belt(hz + 0.13, 0.205, 0.185, 'cream', 0.03)
    # shawl: cape over the shoulders down to the elbows, fringed, and a hood around the head
    sh_z = P['sh_z']
    secs = [(Vector((0, 0.02, P['neck_z'] + 0.02)), 0.12, 0.11), (Vector((0, 0.02, sh_z)), 0.26, 0.22),
            (Vector((0, 0.03, sh_z - 0.12)), 0.31, 0.25), (Vector((0, 0.04, sh_z - 0.26)), 0.33, 0.27)]
    import bmesh
    bm = C.bm_loft(secs, 28, cap0=None, cap1=None, power=2.0)
    for v in bm.verts:
        if v.co.z < sh_z - 0.25:
            a = math.atan2(v.co.y, v.co.x)
            v.co.z -= 0.035 * (0.5 + 0.5 * math.sin(a * 14)) + 0.08 * max(0, -math.sin(a)) * 0.0
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.012)

    def shawl_rule(p):
        if p.z > sh_z - 0.04 or abs(p.x) < 0.18:
            return {'chest': 1.0}
        side = 'L' if p.x > 0 else 'R'
        return {'chest': 0.6, f'shoulder_{side}': 0.25, f'upperarm_{side}': 0.15}
    cm.add(bm, 'shawl', ('fn', shawl_rule))
    # hood: a shell around the back of the head, open at the face
    rx, ry, rz = P['head_r']
    c = Vector((0, 0.025, P['head_c'] + 0.02))
    hb = G.bm_sphere(1.0, 24, 14)
    bmesh.ops.scale(hb, vec=(rx * 1.16, ry * 1.18, rz * 1.13), verts=hb.verts)
    kill = [f for f in hb.faces if f.calc_center_median().y < -ry * 0.45 and f.calc_center_median().z > -rz * 0.85]
    bmesh.ops.delete(hb, geom=kill, context='FACES')
    bmesh.ops.solidify(hb, geom=hb.faces[:], thickness=0.014)
    cm.add(hb, 'shawl', ('rigid', 'head'), loc=c)
    # grey curls framing the face + bun
    hc = Vector((0, 0, P['head_c']))
    B.hair_cap('hair_grey', brow=0.42, side=0.75)
    B.blobs('hair_grey', ('rigid', 'head'), [
        (hc + Vector((sx * rx * 0.86, -ry * 0.3, rz * 0.3 - k * 0.11)), 0.05, (0.8, 0.8, 1))
        for sx in (-1, 1) for k in range(4)] +
        [(hc + Vector((sx * rx * 0.38, -ry * 0.78, rz * 0.6)), 0.05, (1.7, 0.7, 0.7)) for sx in (-1, 1)] +
        [(hc + Vector((0, ry * 0.9, rz * 0.3)), 0.07, (1.2, 1.0, 1.0))])
    # brooch, charms: garlic + lavender pouch
    cm.cyl('brass', ('rigid', 'chest'), 0.02, 0.02, 0.012, Vector((0, -0.14, P['neck_z'] - 0.05)),
           rot=(math.pi / 2, 0, 0), segs=10)
    B.garlic((0.12, -0.2, hz + 0.08))
    B.pouch((-0.15, -0.17, hz + 0.02), 'leather', 0.045, salt=False)
    for k in range(3):
        cm.cyl('lavender', ('rigid', 'hips'), 0.006, 0.004, 0.09, Vector((-0.16 + 0.015 * k, -0.18, hz + 0.1)),
               rot=(0.2 * (k - 1), 0.25 * (k - 1), 0), segs=5)
    return dict(brow_mat='hair_grey', hold='candle', items={'R': 'candle'})


def farmer(B):
    P, cm = B.P, B.cm
    hz = P['hip_z']
    import bmesh
    # plaid shirt torso with a round belly; overalls over it
    B.torso('cloth_plaid', [(hz - 0.04, 0.2, 0.18, 0.0), (hz + 0.12, 0.27, 0.25, -0.03), (hz + 0.3, 0.29, 0.25, -0.03),
                            (P['chest_z'] + 0.1, 0.28, 0.21, 0.0), (P['neck_z'] - 0.06, 0.22, 0.15, 0.01),
                            (P['neck_z'] + 0.03, 0.09, 0.09, 0.01)])
    B.neck('skin_ruddy', 0.075)
    B.head('skin_ruddy', nose=0.048)
    for side in ('L', 'R'):
        B.arm(side, 'cloth_plaid', cuff='cloth_plaid', sleeve_end=0.3, r_sh=0.1, r_el=0.08, r_wr=0.062,
              skin='skin_ruddy')
        B.leg(side, 'overalls', 0.115, 0.095, 0.08, top_extra=0.05)
        B.boot(side, 'boot', 0.16, cuff='boot')
    # overalls: lower torso shell + bib + straps
    B.cm.loft('overalls', B.torso_rule(), [(Vector((0, 0, hz - 0.08)), 0.215, 0.195),
                                           (Vector((0, -0.03, hz + 0.12)), 0.285, 0.265),
                                           (Vector((0, -0.03, hz + 0.24)), 0.3, 0.265)], 22, cap0='round', cap1=None)

    def bib(u, v):
        x = (u - 0.5) * 0.3
        z = lerp(hz + 0.22, P['chest_z'] + 0.08, v)
        ry = lerp(0.27, 0.235, v)
        rx = lerp(0.305, 0.285, v)
        y = -ry * math.sqrt(max(0.0, 1 - (x / rx) ** 2)) - 0.012
        return Vector((x, y - 0.03 * (1 - v), z))
    B.panel('overalls', B.torso_rule(), bib, 8, 8, 0.01)
    for sx in (-1, 1):
        pts = [Vector((sx * 0.12, -0.23, P['chest_z'] + 0.07)), Vector((sx * 0.17, -0.12, P['sh_z'] + 0.02)),
               Vector((sx * 0.15, 0.12, P['sh_z'] + 0.0)), Vector((-sx * 0.05, 0.22, P['chest_z']))]
        B.cm.tube('overalls', ('rigid', 'chest'), pts, 0.022, 6)
        B.cm.cyl('brass', ('rigid', 'chest'), 0.025, 0.025, 0.015, Vector((sx * 0.12, -0.245, P['chest_z'] + 0.07)),
                 rot=(math.pi / 2, 0, 0), segs=10)
    B.cm.box('overalls', B.torso_rule(), (0.13, 0.02, 0.1), Vector((0, -0.265, P['chest_z'] - 0.02)), bevel=0.01)
    B.belt(hz + 0.1, 0.29, 0.27, 'belt', 0.05, yoff=-0.03)
    B.cm.box('brass', ('rigid', 'hips'), (0.07, 0.02, 0.06), Vector((0, -0.3, hz + 0.1)), bevel=0.01)
    B.horseshoe((-0.17, -0.25, hz + 0.06), 1.2)
    B.pouch((0.23, -0.15, hz + 0.02), 'leather', 0.06, salt=False)
    # patches on the knee
    kn = B.sk.head('shin_R')
    B.cm.box('cloth_plaid', ('dist', ['thigh_R', 'shin_R'], 4), (0.09, 0.02, 0.09), kn + Vector((0, -0.095, 0.03)),
             bevel=0.008)
    # white beard, moustache, side hair; bald crown under the hat
    rx, ry, rz = P['head_r']
    hc = Vector((0, 0, P['head_c']))
    beard = [(hc + Vector((x * rx, -ry * 0.72 + abs(x) * 0.08, z * rz)), r, sc) for x, z, r, sc in (
        (0, -0.72, 0.13, (1.25, 0.75, 0.95)), (-0.45, -0.55, 0.1, (1, 0.8, 1)), (0.45, -0.55, 0.1, (1, 0.8, 1)),
        (-0.7, -0.2, 0.08, (0.8, 0.9, 1.2)), (0.7, -0.2, 0.08, (0.8, 0.9, 1.2)), (0, -0.95, 0.09, (1.1, 0.8, 0.8)))]
    B.blobs('hair_white', ('rigid', 'head'), beard)
    for sx in (-1, 1):
        B.cm.sphere('hair_white', ('rigid', 'head'), 0.06, hc + Vector((sx * 0.08, -ry * 0.98, -0.45 * rz)),
                    scale=(1.6, 0.7, 0.75), segs=10, rings=6)
        B.cm.sphere('hair_white', ('rigid', 'head'), 0.07, hc + Vector((sx * rx * 0.85, 0.05, 0.1 * rz)),
                    scale=(0.7, 1.2, 1.0), segs=10, rings=6)

    def hat(cm2):
        top = P['top']
        rule = ('rigid', 'hat')
        cm2.lathe('straw', rule, [(0.0, 0.2), (0.15, 0.19), (0.2, 0.12), (0.215, 0.03), (0.36, -0.0), (0.4, -0.035),
                                  (0.37, -0.045), (0.21, -0.01), (0.0, -0.01)], Vector((0, 0.0, top - 0.07)), segs=26)
        cm2.cyl('cloth_purple', rule, 0.218, 0.216, 0.05, Vector((0, 0, top - 0.03)), segs=24, bevel=0.005)
        for k in range(6):  # frayed straw tufts on the brim
            a = k / 6 * 2 * math.pi + 0.3
            cm2.box('straw', rule, (0.03, 0.05, 0.01), Vector((math.cos(a) * 0.39, math.sin(a) * 0.39, top - 0.11)),
                    rot=(0.3, 0, a), bevel=0.004)
    return dict(brow_mat='hair_white', hold='pitchfork', items={'R': 'pitchfork'}, hat=hat, mouth_lift=0.1,
                mouth_z=-0.55)


def maid(B):
    P, cm = B.P, B.cm
    hz = P['hip_z']
    import bmesh
    B.torso('dress_purple', [(hz - 0.04, 0.13, 0.11, 0.0), (hz + 0.08, 0.15, 0.13, 0.0), (hz + 0.18, 0.14, 0.12, 0.0),
                             (P['chest_z'] + 0.06, 0.17, 0.14, -0.01), (P['neck_z'] - 0.05, 0.14, 0.11, 0.01),
                             (P['neck_z'] + 0.02, 0.06, 0.06, 0.01)])
    B.neck()
    B.head()
    for side in ('L', 'R'):
        B.arm(side, 'cream', cuff='cream', sleeve_end=0.0, r_sh=0.06, r_el=0.05, r_wr=0.04, puff=0.03)
        B.leg(side, 'skin', 0.065, 0.05, 0.04)
        B.boot(side, 'boot', 0.12)
    # white blouse top + laced bodice over it
    B.cm.loft('cream', B.torso_rule(), [(Vector((0, 0.01, P['chest_z'] + 0.1)), 0.175, 0.145),
                                        (Vector((0, 0.01, P['neck_z'] - 0.02)), 0.15, 0.12),
                                        (Vector((0, 0.01, P['neck_z'] + 0.03)), 0.08, 0.075)], 18, cap0=None,
              cap1=None)
    B.skirt('dress_lilac', hz + 0.14, 0.24, 0.16, 0.3, frill=0.01)
    B.skirt('dress_purple', 0.25, 0.2, 0.3, 0.305, frill=0.008)

    def apron(u, v):
        x = (u - 0.5) * 0.3
        z = lerp(hz + 0.12, 0.28, v)
        r = lerp(0.165, 0.3, ((hz + 0.14 - z) / (hz - 0.1)) ** 0.8) + 0.015
        y = -math.sqrt(max(0.0, r * r * 0.81 - x * x * 0.9))
        return Vector((x, y - 0.005, z))
    B.panel('apron_white', B.skirt_rule(0.3), apron)
    B.belt(hz + 0.13, 0.155, 0.135, 'apron_white', 0.04)
    for sx in (-1, 1):  # bow at the back
        B.cm.sphere('apron_white', ('rigid', 'hips'), 0.05, Vector((sx * 0.05, 0.16, hz + 0.13)), scale=(1.2, 0.5, 0.8),
                    segs=10, rings=6)
        B.cm.tube('apron_white', ('rigid', 'hips'), [Vector((sx * 0.02, 0.16, hz + 0.12)),
                                                    Vector((sx * 0.06, 0.18, hz - 0.05))], 0.018, 6, taper=0.7)
    # salt pouch on a strap + garlic sprig
    B.pouch((-0.17, -0.12, hz - 0.02), 'leather', 0.05, salt=True)
    B.cm.tube('leather', ('rigid', 'chest'), [Vector((0.13, -0.11, P['sh_z'])), Vector((-0.05, -0.15, P['chest_z'])),
                                              Vector((-0.17, -0.12, hz + 0.03))], 0.012, 5)
    for k in range(3):
        B.cm.add(G.bm_extrude2d([(0, 0), (0.015, 0.02), (0, 0.05), (-0.015, 0.02)], 0.004, 0.001, 1), 'leaf',
                 ('rigid', 'hips'), loc=Vector((-0.12 + 0.02 * k, -0.15, hz + 0.02)), rot=(1.3, 0, 0.4 * (k - 1)))
    # wavy brown hair down the back and sides
    rx, ry, rz = P['head_r']
    hc = Vector((0, 0, P['head_c']))
    B.hair_cap('hair_brown', brow=0.4, side=0.72)
    hair = [None]
    for k in range(5):
        for sx in (-1, 1):
            hair.append((hc + Vector((sx * rx * 0.85, 0.06 - 0.03 * (k == 0), -0.15 * rz - k * 0.065)), 0.06,
                         (0.9, 1.0, 1.0)))
    for k in range(4):
        hair.append((hc + Vector((0.06 * (k - 1.5), ry * 0.7, -0.45 * rz - 0.03 * k)), 0.075, (1, 0.8, 1.2)))
    B.blobs('hair_brown', ('dist', ['head', 'neck', 'chest'], 3), hair[1:])
    for sx in (-1, 1):
        B.cm.sphere('hair_brown', ('rigid', 'head'), 0.06, hc + Vector((sx * rx * 0.45, -ry * 0.82, 0.55 * rz)),
                    scale=(1.4, 0.6, 0.7), segs=10, rings=6)

    def hat(cm2):
        rule = ('rigid', 'hat')
        hb = G.bm_sphere(1.0, 20, 12)
        import bmesh as bm_
        bm_.ops.scale(hb, vec=(rx * 1.12, ry * 1.14, rz * 1.04), verts=hb.verts)
        kill = [f for f in hb.faces if f.calc_center_median().z < rz * 0.15 or f.calc_center_median().y < -ry * 0.6]
        bm_.ops.delete(hb, geom=kill, context='FACES')
        bm_.ops.solidify(hb, geom=hb.faces[:], thickness=0.012)
        cm2.add(hb, 'apron_white', rule, loc=hc + Vector((0, 0.03, 0.07)))
        cm2.loft('apron_white', rule, [(hc + Vector((0, 0.02, rz * 0.22)), rx * 1.13, ry * 1.12),
                                      (hc + Vector((0, 0.02, rz * 0.3)), rx * 1.16, ry * 1.15)], 20, cap0=None,
                 cap1=None)
        for sx in (-1, 1):
            cm2.sphere('apron_white', rule, 0.04, hc + Vector((sx * 0.03, ry * 1.1, -rz * 0.05)),
                       scale=(1.2, 0.5, 0.8), segs=8, rings=5)
    return dict(brow_mat='hair_brown', hold='lantern', items={'R': 'lantern'}, hat=hat)


def teacher(B):
    P, cm = B.P, B.cm
    hz = P['hip_z']
    import bmesh
    B.torso('waistcoat', [(hz - 0.04, 0.13, 0.11, 0.0), (hz + 0.1, 0.145, 0.125, 0.0), (hz + 0.2, 0.14, 0.12, 0.0),
                          (P['chest_z'] + 0.08, 0.165, 0.13, -0.005), (P['neck_z'] - 0.05, 0.14, 0.105, 0.01),
                          (P['neck_z'] + 0.03, 0.06, 0.06, 0.01)])
    B.neck()
    B.head()
    for side in ('L', 'R'):
        B.arm(side, 'coat_slate', cuff='coat_slate', sleeve_end=1.0, r_sh=0.065, r_el=0.055, r_wr=0.045)
        B.leg(side, 'dress_plum', 0.065, 0.05, 0.04)
        B.boot(side, 'boot', 0.13)
    B.skirt('dress_purple', hz + 0.1, 0.1, 0.16, 0.27, frill=0.008)
    # long slate coat: open at the front, from the shoulders to the knees
    sh = P['sh_z']

    def coat(u, v):
        a = math.radians(-60 + 300 * u) - math.pi / 2  # open at the front (-Y)
        z = lerp(sh + 0.03, P['knee_z'] + 0.02, v)
        if z > P['chest_z']:
            t = (z - P['chest_z']) / (sh + 0.03 - P['chest_z'])
            rx, ry = lerp(0.18, 0.205, t), lerp(0.145, 0.15, t)
        elif z > hz:
            t = (z - hz) / (P['chest_z'] - hz)
            rx, ry = lerp(0.17, 0.18, t), lerp(0.14, 0.145, t)
        else:
            t = (hz - z) / (hz - P['knee_z'])
            rx, ry = lerp(0.17, 0.26, t), lerp(0.14, 0.23, t)
        return Vector((math.cos(a) * rx * 1.04, math.sin(a) * ry * 1.04, z))
    B.panel('coat_slate', B.skirt_rule(0.35), coat, 24, 10, 0.012)
    # lapels + collar
    for sx in (-1, 1):
        B.cm.ext('coat_slate', ('rigid', 'chest'), [(0, 0), (0.05, 0.0), (0.02, 0.16), (-0.01, 0.16)], 0.012,
                 Vector((sx * 0.07, -0.145, P['chest_z'] + 0.02)), rot=(math.pi / 2 - 0.15, 0, sx * 0.2))
    B.cm.loft('cream', ('rigid', 'chest'), [(Vector((0, 0.01, P['neck_z'] - 0.02)), 0.075, 0.07),
                                            (Vector((0, 0.01, P['neck_z'] + 0.04)), 0.068, 0.064)], 14, cap0='flat',
              cap1='flat')
    # satchel strap across + charms (horseshoe and a little salt vial)
    B.cm.tube('leather', ('rigid', 'chest'), [Vector((-0.15, -0.12, P['sh_z'] + 0.02)),
                                              Vector((0.05, -0.17, P['chest_z'])), Vector((0.2, -0.05, hz + 0.08))],
              0.014, 5)
    B.cm.box('book_red', ('rigid', 'hips'), (0.06, 0.2, 0.17), Vector((0.21, 0.0, hz + 0.0)), bevel=0.015)
    B.cm.box('leather', ('rigid', 'hips'), (0.065, 0.21, 0.07), Vector((0.21, 0.0, hz + 0.06)), bevel=0.012)
    B.horseshoe((-0.1, -0.15, hz + 0.04), 0.9)
    B.cm.cyl('glass', ('rigid', 'hips'), 0.02, 0.025, 0.06, Vector((-0.04, -0.16, hz + 0.02)), segs=8)
    B.cm.cyl('salt', ('rigid', 'hips'), 0.017, 0.022, 0.035, Vector((-0.04, -0.16, hz + 0.005)), segs=8)
    B.belt(hz + 0.08, 0.15, 0.13, 'belt', 0.03)
    # dark hair with a top bun, glasses
    rx, ry, rz = P['head_r']
    hc = Vector((0, 0, P['head_c']))
    B.hair_cap('hair_dark', brow=0.45, side=0.75)
    B.blobs('hair_dark', ('rigid', 'head'), [
        (hc + Vector((0, 0.01, rz + 0.04)), 0.085, (1.0, 1.0, 0.85)),
        (hc + Vector((0.04, 0.02, rz + 0.1)), 0.05, (1, 1, 0.8))] +
        [(hc + Vector((sx * rx * 0.88, -0.02, -0.1 * rz - 0.05 * k)), 0.045, (0.8, 1.0, 1.0))
         for sx in (-1, 1) for k in range(3)] +
        [(hc + Vector((sx * rx * 0.4, -ry * 0.83, 0.55 * rz)), 0.05, (1.6, 0.6, 0.6)) for sx in (-1, 1)])
    for sx in (-1, 1):
        c, n = on_head(P, sx * EYE_X, EYE_Z, 0.02)
        B.cm.add(G.bm_tube([c + Vector((math.cos(a) * 0.058, 0, math.sin(a) * 0.058))
                            for a in [k / 16 * 2 * math.pi for k in range(17)]], 0.006, 5), 'glasses',
                 ('rigid', 'head'))
        side = on_head(P, sx * 0.85, -0.05, 0.005)[0]
        B.cm.tube('glasses', ('rigid', 'head'), [c + Vector((sx * 0.058, 0, 0)), side,
                                                 side + Vector((0, 0.12, 0))], 0.005, 4)
    c1 = on_head(P, 0.12, EYE_Z, 0.025)[0]
    B.cm.tube('glasses', ('rigid', 'head'), [c1, Vector((0, c1.y - 0.01, c1.z + 0.01)), Vector((-c1.x, c1.y, c1.z))],
              0.005, 4)
    return dict(brow_mat='hair_dark', hold='crossed', items={'L': 'book'})


def child(B):
    P, cm = B.P, B.cm
    hz = P['hip_z']
    import bmesh
    B.torso('cream', [(hz - 0.03, 0.11, 0.095, 0.0), (hz + 0.06, 0.125, 0.11, -0.01), (P['chest_z'], 0.13, 0.11, 0.0),
                      (P['neck_z'] - 0.03, 0.1, 0.085, 0.01), (P['neck_z'] + 0.02, 0.05, 0.05, 0.01)])
    B.neck(r=0.045)
    B.head()
    for side in ('L', 'R'):
        B.arm(side, 'cream', cuff='cream', sleeve_end=0.9, r_sh=0.05, r_el=0.042, r_wr=0.034, puff=0.01)
        B.leg(side, 'skin', 0.05, 0.04, 0.033)
        B.boot(side, 'cream', 0.09, cuff='cream')
    # nightshirt down to the shins
    B.skirt('cream', hz + 0.1, 0.17, 0.125, 0.2, frill=0.008)
    B.belt(hz + 0.04, 0.122, 0.106, 'rope', 0.018)
    B.garlic((-0.09, -0.11, hz + 0.0))
    # curly hair: many blobs
    rx, ry, rz = P['head_r']
    hc = Vector((0, 0, P['head_c']))
    B.hair_cap('hair_brown', brow=0.42, side=0.75)
    curls = []
    import random
    rnd = random.Random(11)
    for k in range(34):
        th = rnd.uniform(-math.pi, math.pi)
        ph = rnd.uniform(-0.25, 1.25)
        dirv = Vector((math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph)))
        if dirv.y < -0.2 and dirv.z < 0.5 and abs(dirv.x) < 0.8:
            continue  # keep the face clear
        if dirv.z > 0.45:
            continue  # under the nightcap
        p = hc + Vector((dirv.x * rx, dirv.y * ry, dirv.z * rz)) * 1.02 + Vector((0, 0.02, 0.02))
        curls.append((p, rnd.uniform(0.045, 0.06), (1, 1, 1)))
    B.blobs('hair_brown', ('rigid', 'head'), curls)

    def hat(cm2):
        rule = ('rigid', 'hat')
        base = hc + Vector((0, 0.03, rz * 0.62))
        cm2.loft('cream', rule, [(base, rx * 0.95, ry * 0.95), (base + Vector((0, 0.03, 0.06)), rx * 0.82, ry * 0.8),
                                 (base + Vector((0, 0.08, 0.14)), 0.09, 0.085),
                                 (base + Vector((0, 0.17, 0.17)), 0.05, 0.05),
                                 (base + Vector((0, 0.25, 0.1)), 0.025, 0.025)], 16, cap0='flat', cap1='round')
        cm2.sphere('cream', rule, 0.04, base + Vector((0, 0.27, 0.06)), segs=10, rings=7)
        cm2.loft('cream', rule, [(base + Vector((0, 0, -0.01)), rx * 0.99, ry * 0.99),
                                 (base + Vector((0, 0, 0.025)), rx * 0.98, ry * 0.98)], 20, cap0=None, cap1=None)
    return dict(brow_mat='hair_brown', hold='doll', items={'L': 'doll'}, hat=hat)


BUILDERS = {'widow': widow, 'farmer': farmer, 'maid': maid, 'teacher': teacher, 'child': child}


# ----------------------------------------------------------------------------- held items
def build_item(kind, coll):
    """Item prop trees (task1 helpers where they exist). Returns (root object, grip point in item space)."""
    import props_common as PC
    import props_haunt  # noqa: F401
    if kind == 'candle':
        p = PC.REGISTRY['candle']['fn']()
        p.haunt = False
        grip = Vector((0, 0, -0.02))
    elif kind == 'lantern':
        p = PC.new('lantern_held')
        PC.lantern_geo(p, p.main, 'lantern', (0, 0, 0), scale=0.9)
        grip = Vector((0, 0, 0.39 * 0.9))
    elif kind == 'doll':
        p = PC.REGISTRY['cloth_doll']['fn']()
        p.haunt = False
        grip = Vector((0, -0.02, 0.17))
    elif kind == 'pitchfork':
        p = PC.new('pitchfork')
        m = p.main
        m.tube('wood', [(0, 0, 0), (0.01, 0, 0.8), (0, 0, 1.45)], 0.022, 7)
        m.box('iron', (0.2, 0.035, 0.04), (0, 0, 1.47), bevel=0.01)
        for x in (-0.085, 0.0, 0.085):
            m.tube('iron', [(x, 0, 1.47), (x * 1.1, 0, 1.62), (x * 1.05, -0.01, 1.75)], 0.012, 5, taper=0.5)
        grip = Vector((0, 0, 0.8))
    elif kind == 'book':
        p = PC.new('book_held')
        m = p.main
        m.box('book_red', (0.15, 0.04, 0.2), (0, 0, 0), bevel=0.01)
        m.box('paper', (0.14, 0.032, 0.19), (0.008, 0, 0), bevel=0.004)
        grip = Vector((0, 0, -0.04))
    else:
        raise ValueError(kind)
    root = G.build(p, coll)
    for o in list(G.hierarchy(root)):
        if o.name.endswith('-colonly'):  # no physics bodies inside a character
            bpy.data.objects.remove(o, do_unlink=True)
    for o in G.hierarchy(root):
        if o.type == 'EMPTY' and o is not root:
            o.empty_display_size = 0.03
    root.name = 'ITEM_' + kind
    return root, grip


# ----------------------------------------------------------------------------- control poses
DEF = dict(root=(0, 0, 0), rot=(0, 0, 0), hips=(0, 0, 0), hips_rot=(0, 0, 0), spine=(0, 0, 0), neck=(0, 0, 0),
           shrug=(0, 0), hand_L=None, hand_R=None, elbow_L=(0.35, 0.7, -0.4), elbow_R=(0.35, 0.7, -0.4),
           hrot_L=None, hrot_R=None, foot_L=(0, 0, 0), foot_R=(0, 0, 0), fpitch=(0, 0), knee=(0.15, 1.0, 0.0),
           expr=None, hat=0.0, ground=True)


def mix(a, b, t):
    if a is None or b is None:
        return b if t >= 0.5 else a
    if isinstance(a, dict):
        out = {}
        for k in set(a) | set(b):
            out[k] = lerp(a.get(k, 0.0), b.get(k, 0.0), t)
        return out
    if isinstance(a, (tuple, list)):
        return tuple(lerp(x, y, t) for x, y in zip(a, b))
    if isinstance(a, bool):
        return b if t >= 0.5 else a
    return lerp(a, b, t)


def ctrl(**kw):
    c = dict(DEF)
    c['expr'] = {'calm': 0.0}
    c.update(kw)
    return c


def over(c, **kw):
    d = dict(c)
    d.update(kw)
    return d


def add(c, **kw):
    """Add offsets to tuple/number controls."""
    d = dict(c)
    for k, v in kw.items():
        a = d.get(k)
        if a is None:
            d[k] = v
        elif isinstance(a, tuple):
            d[k] = tuple(x + y for x, y in zip(a, v))
        else:
            d[k] = a + v
    return d


def keyed(keys, t):
    """keys: [(time, ctrl)] -> smoothstepped ctrl."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            return {k: mix(a[k], b[k], smooth((t - t0) / max(1e-6, t1 - t0))) for k in a}
    return keys[-1][1]


class Villager:
    def __init__(self, name, P, sk, info):
        self.name, self.P, self.sk, self.info = name, P, sk, info
        self.leg_len = (sk.head('shin_L') - sk.head('thigh_L')).length + (sk.head('foot_L') - sk.head('shin_L')).length
        self.sh_mid = Vector((0, 0, P['sh_z']))
        self.arm_len = P['ua'] + P['fa']

    def hang(self, side):
        """Relaxed hanging hand target (x from midline, fwd, up from shoulder height)."""
        a = math.radians(self.P['arm_a'])
        L = self.arm_len * 0.97
        return (self.P['sh_w'] + math.sin(a) * L, 0.05, -math.cos(a) * L)

    def hold(self, style=None):
        """Default hands for the villager's hold style -> dict of controls."""
        P = self.P
        style = style or self.info['hold']
        sw = P['sh_w']
        dz = P['sh_z'] - P['hip_z']  # shoulder to hip height
        if style == 'candle':
            return dict(hand_R=(0.05, 0.27, -dz * 0.62), hand_L=(0.03, 0.25, -dz * 0.75), hrot_R=(0, 0, 0),
                        hrot_L=(0, 0, 0), elbow_L=(0.6, 0.5, -0.5), elbow_R=(0.6, 0.5, -0.5))
        if style == 'pitchfork':
            return dict(hand_R=(sw + 0.1, 0.18, -dz * 0.7), hrot_R=(0, 0, 0), hand_L=self.hang('L'))
        if style == 'lantern':
            return dict(hand_R=(sw + 0.06, 0.1, -self.arm_len * 0.92), hrot_R=(0, 0, 0),
                        hand_L=(0.05, 0.2, -dz * 0.3), hrot_L=(-20, 0, -60), elbow_L=(0.6, 0.4, -0.6))
        if style == 'crossed':
            return dict(hand_R=(-0.13, 0.2, -dz * 0.52), hrot_R=None, elbow_R=(0.6, 0.2, -0.4),
                        hand_L=(0.08, 0.2, -dz * 0.45), hrot_L=(0, 0, -15), elbow_L=(0.6, 0.3, -0.6))
        if style == 'doll':
            return dict(hand_L=(0.04, 0.2, -dz * 0.6), hrot_L=(0, 0, 0), elbow_L=(0.6, 0.4, -0.5),
                        hand_R=(0.06, 0.17, -dz * 0.85), hrot_R=None, elbow_R=(0.6, 0.4, -0.5))
        return dict(hand_L=self.hang('L'), hand_R=self.hang('R'))

    def base(self, **kw):
        c = ctrl(spine=(self.P['posture'], 0, 0), neck=(-self.P['posture'] * 0.8, 0, 0))
        c.update(self.hold())
        c.update(kw)
        return c

    # ------------------------------------------------------------------ ctrl -> Pose
    def pose(self, c):
        sk, P = self.sk, self.P
        p = Pose()
        qr = qeuler(*c['rot'])
        if 'root_q' in c and c['root_q'] is not None:
            qr = c['root_q']
        p.rot('root', qr)
        p.move('root', Vector(c['root']))
        p.move('hips', Vector(c['hips']))
        p.rot('hips', qeuler(*c['hips_rot']))
        sp = c['spine']
        p.rot('spine', qeuler(sp[0] * 0.5, sp[1] * 0.5, sp[2] * 0.5))
        p.rot('chest', qeuler(sp[0] * 0.5, sp[1] * 0.5, sp[2] * 0.5))
        nk = c['neck']
        p.rot('neck', qeuler(nk[0] * 0.4, nk[1] * 0.4, nk[2] * 0.4))
        p.rot('head', qeuler(nk[0] * 0.6, nk[1] * 0.6, nk[2] * 0.6))
        p.rot_e('shoulder_L', y=-c['shrug'][0])
        p.rot_e('shoulder_R', y=c['shrug'][1])
        # legs
        root_t = Vector(c['root'])
        for i, side in enumerate(('L', 'R')):
            sx = 1 if side == 'L' else -1
            f = c[f'foot_{side}']
            an = sk.head(f'foot_{side}')
            tgt = root_t + qr @ (an + Vector((sx * f[0], -f[1], f[2])))
            kp = c['knee']
            pole = qr @ Vector((sx * kp[0], -kp[1], kp[2]))
            p.ik[f'thigh_{side}'] = (tgt, pole)
            p.wrot[f'foot_{side}'] = qr @ qeuler(c['fpitch'][i], 0, 0)
            if c['ground']:
                p.ground.setdefault('hips', []).append((f'thigh_{side}', tgt, self.leg_len * 0.995))
        p.shapes = dict(c['expr'] or {})
        # first pass: chest frame for the hand targets
        _, M = C.solve(sk, p)
        Wc = (M['chest'].to_quaternion() @ sk.rest['chest'].to_quaternion().inverted())
        mid = (M['upperarm_L'].to_translation() + M['upperarm_R'].to_translation()) / 2
        for side in ('L', 'R'):
            sx = 1 if side == 'L' else -1
            h = c[f'hand_{side}'] or self.hang(side)
            tgt = mid + Wc @ Vector((sx * h[0], -h[1], h[2]))
            e = c[f'elbow_{side}']
            pole = Wc @ Vector((sx * e[0], e[1], e[2]))
            p.ik[f'upperarm_{side}'] = (tgt, pole)
            hr = c[f'hrot_{side}']
            if hr is not None:
                # hand rotation in the chest frame (pitch, roll, yaw), mirrored for the left hand
                p.wrot[f'hand_{side}'] = Wc @ qeuler(hr[0], hr[1] * sx * -1, hr[2] * sx * -1)
        if c['hat'] > 0:
            fly = c['hat']
            hp = M['hat'].to_translation()
            start = hp
            peak = root_t + qr @ (sk.head('hat') + Vector((0.12, 0.45, 0.9)))
            land = root_t + qr @ Vector((0.25, 0.75, 0.0))
            if fly < 0.6:
                u = fly / 0.6
                pos = start.lerp(peak, smooth(u)) + Vector((0, 0, 0.25 * math.sin(math.pi * u)))
            else:
                u = (fly - 0.6) / 0.4
                pos = peak.lerp(land, u) + Vector((0, 0, 0.3 * math.sin(math.pi * u * 0.5) * (1 - u)))
            p.wpos['hat'] = pos
            p.wrot['hat'] = qr @ qeuler(-280 * fly, 40 * fly, 90 * fly)
        return p


# ----------------------------------------------------------------------------- gait
def gait(V, c, ph, stride, duty=0.6, lift=0.08, bob=0.025, sway=0.025, yaw=7.0, arm=0.12, run=False):
    """Foot-planted cycle at phase ph in [0, 1). Stance feet move backward at stride / (duty * T)."""
    c = dict(c)
    for side, off in (('L', 0.0), ('R', 0.5)):
        q = (ph + off) % 1.0
        if q < duty:
            s = q / duty
            fwd = stride / 2 - stride * s
            up = 0.0
            pitch = 0.0
            if run:
                pitch = 18 * smooth((s - 0.6) / 0.4)
        else:
            s = (q - duty) / (1 - duty)
            fwd = -stride / 2 + stride * smooth(s)
            up = lift * math.sin(math.pi * s) ** 0.8
            pitch = 25 * math.sin(math.pi * s) * (1 - 1.7 * s)
        f0 = c[f'foot_{side}']
        c[f'foot_{side}'] = (f0[0], f0[1] + fwd, f0[2] + up)
        fp = list(c['fpitch'])
        fp[0 if side == 'L' else 1] += pitch
        c['fpitch'] = tuple(fp)
    k = 4 * math.pi
    lowest = duty - 0.5 if duty > 0.5 else 0.0
    c['hips'] = tuple(a + b for a, b in zip(c['hips'], (sway * math.cos(2 * math.pi * (ph - duty / 2)), 0,
                                                         -bob * (0.5 + 0.5 * math.cos(k * (ph - lowest / 2))))))
    c['hips_rot'] = tuple(a + b for a, b in zip(c['hips_rot'], (0, -3 * math.cos(2 * math.pi * (ph - duty / 2)),
                                                                 -yaw * math.cos(2 * math.pi * ph))))
    c['spine'] = tuple(a + b for a, b in zip(c['spine'], (1.5 * math.cos(k * ph), 0, yaw * 1.2 * math.cos(2 * math.pi * ph))))
    if arm:
        sw = arm * math.cos(2 * math.pi * ph)
        for side, sgn in (('L', -1), ('R', 1)):
            h = c[f'hand_{side}'] or V.hang(side)
            c[f'hand_{side}'] = (h[0], h[1] + sgn * sw, h[2] + abs(sw) * 0.25)
    return c


# ----------------------------------------------------------------------------- clips
def clips(V):
    P = V.P
    L = V.leg_len
    dz = P['sh_z'] - P['hip_z']
    out = {}
    speeds = {}
    child = P['top'] < 1.3

    def T(f):
        return f / 24.0

    # idle
    def idle(f):
        t = T(f)
        b = math.sin(2 * math.pi * t / 2.0)
        c = V.base()
        c = add(c, spine=(1.2 * b, 0.6 * math.sin(2 * math.pi * t / 2 + 1), 0), shrug=(1.5 * b, 1.5 * b),
                neck=(-0.8 * b, 2 * math.sin(2 * math.pi * t / 2 + 0.4), 1.5 * math.sin(2 * math.pi * t / 2 + 1.2)),
                hips=(0.006 * math.sin(2 * math.pi * t / 2 + 1), 0, 0))
        return V.pose(c)
    out['idle'] = (48, idle, True)

    def walker(name, period, stride, cycles=1, **gk):
        # snap the cycle to whole frames so the loop closes exactly at 24 fps
        n = max(8, round(period * 24))
        period = n / 24.0
        frames = n * cycles

        def fn(f):
            ph = (T(f) / period) % 1.0
            c = V.base()
            c = extra.get(name, lambda c, f: c)(c, f)
            c = gait(V, c, ph, stride, **gk)
            return V.pose(c)
        speeds[name] = round(stride / (gk.get('duty', 0.6) * period), 3)
        dur[name] = frames / 24.0
        out[name] = (frames, fn, True)

    extra = {}
    dur = {}
    per = 1.0 if not child else 0.8
    walker('walk', per, 0.62 * L)

    def uneasy_extra(c, f):
        t = T(f)
        g = math.sin(2 * math.pi * t / dur['walk_uneasy'])  # glance left, then right, over the loop
        return add(over(c, expr={'uneasy': 1.0}), shrug=(7, 7), spine=(6, 0, 0),
                   neck=(4, 0, 38 * math.copysign(smooth(abs(g) * 1.6), g)))
    extra['walk_uneasy'] = uneasy_extra
    walker('walk_uneasy', 0.75 * per, 0.58 * L, 2, bob=0.02, arm=0.06)

    def clutch_extra(c, f):
        c = over(c, hand_R=(0.03, 0.24, -dz * 0.45), hand_L=(0.02, 0.22, -dz * 0.55), hrot_R=(0, 0, 0),
                 hrot_L=(0, 0, 0), elbow_L=(0.7, 0.4, -0.5), elbow_R=(0.7, 0.4, -0.5), expr={'scared': 1.0})
        return add(c, shrug=(10, 10), spine=(10, 0, 0), neck=(-4, 0, 0))
    extra['clutch_candle_walk'] = clutch_extra
    walker('clutch_candle_walk', 0.7 * per, 0.55 * L, 2, bob=0.02, arm=0.0)

    def flee_extra(c, f):
        t = T(f)
        w = math.sin(2 * math.pi * t / dur['flee'])
        c = over(c, hand_L=(P['sh_w'] + 0.12, 0.15 + 0.12 * w, 0.18 + 0.08 * w),
                 hand_R=(P['sh_w'] + 0.12, 0.15 - 0.12 * w, 0.18 - 0.08 * w), hrot_L=None, hrot_R=None,
                 elbow_L=(0.6, 0.3, -0.7), elbow_R=(0.6, 0.3, -0.7), expr={'terrified': 1.0})
        return add(c, spine=(16, 0, 0), neck=(-14, 0, 0), shrug=(8, 8))
    extra['flee'] = flee_extra
    walker('flee', 0.58 * per, 0.85 * L, 1, duty=0.4, lift=0.18, bob=0.045, sway=0.015,
           yaw=10, arm=0.0, run=True)

    def keyed_clip(name, frames, keys, loop=False, post=None):
        def fn(f):
            t = T(f)
            c = keyed(keys, t)
            if post:
                c = post(c, t)
            return V.pose(c)
        out[name] = (frames, fn, loop)

    b = V.base()
    sw = P['sh_w']
    hang = dict(hand_L=V.hang('L'), hand_R=V.hang('R'))

    # look over the right shoulder
    look = over(b, spine=(P['posture'], 2, -28), neck=(-P['posture'] * 0.8 - 5, -8, -62), expr={'uneasy': 1.0},
                hips_rot=(0, 0, -6), shrug=(0, 6))
    keyed_clip('look_over_shoulder', 48, [(0, over(b, expr={'uneasy': 0.4})), (0.45, look), (1.3, add(look, neck=(3, 0, 6))),
                                          (2.0, over(b, expr={'uneasy': 0.4}))])

    # call out "hello?": raise the held item high, other hand cupped at the mouth
    co = over(b, hand_R=(sw + 0.05, 0.3, 0.32), hrot_R=(0, 0, 0), hand_L=(0.06, 0.32, 0.12 + P['head_c'] - P['sh_z'] - 0.2),
              hrot_L=(-10, 0, 70), elbow_L=(0.7, 0.2, -0.6), elbow_R=(0.6, 0.4, -0.4),
              spine=(P['posture'] + 6, 0, 4), neck=(-14, 0, 6), expr={'uneasy': 0.6, 'scared': 0.4})
    keyed_clip('call_out', 48, [(0, b), (0.4, co), (0.75, add(co, neck=(-4, 0, -4), spine=(-3, 0, 0))),
                                (1.25, add(co, neck=(2, 0, 10))), (1.5, co), (2.0, b)])

    # startle: small jump
    crouch = add(over(b, expr={'scared': 1.0}), hips=(0, 0, -0.06), shrug=(14, 14), spine=(6, 0, 0))
    flinch = over(crouch, hand_L=(0.16, 0.3, 0.02), hand_R=(0.16, 0.3, 0.02), hrot_L=(0, 0, 0), hrot_R=(0, 0, 0),
                  elbow_L=(0.6, 0.3, -0.7), elbow_R=(0.6, 0.3, -0.7), root=(0, 0.04, 0.12), hips=(0, 0, 0),
                  foot_L=(0, 0, 0.0), foot_R=(0, 0, 0.0), spine=(-6, 0, 0), neck=(-10, 0, 0))
    keyed_clip('startle', 24, [(0, b), (0.1, crouch), (0.25, flinch), (0.42, add(crouch, root=(0, 0.04, 0))),
                               (1.0, over(b, expr={'uneasy': 1.0}))])

    # big scare leap: anticipation, huge leap with arms up (hat flies, lantern dropped at frame 11), landing
    ant = add(over(b, expr={'scared': 1.0}), hips=(0, 0.02, -0.14), spine=(14, 0, 0), shrug=(10, 10))
    air = over(b, root=(0, 0.1, 0.62 if not child else 0.4), hips=(0, 0, 0), spine=(-18, 0, 0), neck=(-16, 0, 0),
               hand_L=(sw + 0.22, 0.12, 0.42), hand_R=(sw + 0.22, 0.12, 0.42), hrot_L=None, hrot_R=None,
               elbow_L=(0.8, 0.2, -0.4), elbow_R=(0.8, 0.2, -0.4), foot_L=(0.06, -0.1, 0.24), foot_R=(0.04, 0.12, 0.3),
               fpitch=(30, 20), expr={'terrified': 1.0}, shrug=(16, 16), hat=0.5)
    land = add(over(b, expr={'terrified': 1.0}, root=(0, 0.1, 0), hat=1.0, hand_L=(sw + 0.16, 0.22, -0.3),
                    hand_R=(sw + 0.16, 0.22, -0.3), hrot_L=None, hrot_R=None, elbow_L=(0.8, 0.2, -0.5),
                    elbow_R=(0.8, 0.2, -0.5)),
               hips=(0, 0, -0.16), spine=(18, 0, 0))
    keyed_clip('big_scare_leap', 40, [(0, over(b, expr={'uneasy': 1.0})), (0.2, ant),
                                      (0.45, over(air, hat=0.35)), (0.75, add(air, root=(0, 0.05, 0.08), hat=0.25)),
                                      (1.15, land), (1.67, over(land, hips=(0, 0, -0.04), spine=(P['posture'] + 6, 0, 0),
                                                                 hat=1.0))])

    # laugh it off: rub the back of the head, hand on hip, chuckle bounce
    la = over(b, hand_R=(0.12, -0.02, P['head_c'] - P['sh_z'] + 0.02), hrot_R=None, elbow_R=(0.9, 0.2, 0.1),
              hand_L=(sw + 0.1, 0.02, -dz * 0.85), hrot_L=None, elbow_L=(0.9, -0.3, 0.0), spine=(-4, 0, 0),
              neck=(-16, 6, 0), expr={'relieved': 1.0})

    def chuckle(c, t):
        k = smooth((t - 0.35) / 0.2) * (1 - smooth((t - 2.1) / 0.3))
        return add(c, spine=(4 * math.sin(2 * math.pi * t * 5) * k, 0, 0), shrug=(5 * math.sin(2 * math.pi * t * 5) * k,) * 2,
                   hand_R=(0.02 * math.sin(2 * math.pi * t * 3) * k, 0, 0))
    keyed_clip('laugh_it_off', 60, [(0, over(b, expr={'scared': 0.5})), (0.4, la), (2.1, la), (2.5, b)], post=chuckle)

    # suspicious search (loop): item raised forward, scanning left and right
    def search(f):
        t = T(f)
        s = math.sin(2 * math.pi * t / 4.0)
        s2 = math.sin(2 * math.pi * t / 4.0 - 0.5)
        c = over(b, hand_R=(sw * 0.6, 0.38, -0.08), hrot_R=(0, 0, 0), elbow_R=(0.6, 0.5, -0.5),
                 expr={'uneasy': 1.0})
        c = add(c, spine=(8, 0, 30 * s), neck=(4, 0, 28 * s2), hips_rot=(0, 0, 8 * s))
        return V.pose(c)
    out['suspicious_search'] = (96, search, True)

    # hang a charm: reach up and forward (door frame), fiddle, return
    up = over(b, hand_R=(0.12, 0.38, 0.5), hrot_R=None, elbow_R=(0.6, 0.3, -0.7),
              hand_L=(0.1, 0.32, 0.38), hrot_L=None, elbow_L=(0.6, 0.3, -0.7), neck=(-22, 0, 0),
              spine=(-2, 0, 0), fpitch=(0, 0), expr={'calm': 1.0})

    def fiddle(c, t):
        k = smooth((t - 0.6) / 0.2) * (1 - smooth((t - 1.7) / 0.2))
        return add(c, hand_R=(0.03 * math.sin(2 * math.pi * t * 2.5) * k, 0, 0.02 * math.sin(2 * math.pi * t * 5) * k))
    keyed_clip('hang_charm', 60, [(0, b), (0.55, up), (1.8, up), (2.5, b)], post=fiddle)

    # scatter salt: left hand holds the pouch at the waist, right hand throws three handfuls across the front
    pouch = over(b, hand_L=(0.1, 0.25, -dz * 0.8), hrot_L=(0, 0, 0), elbow_L=(0.7, 0.4, -0.5), expr={'uneasy': 0.6})
    grab = over(pouch, hand_R=(0.06, 0.27, -dz * 0.75), hrot_R=None, elbow_R=(0.7, 0.4, -0.5))
    throw_l = over(pouch, hand_R=(-0.25, 0.45, -dz * 0.45), hrot_R=None, spine=(P['posture'] + 6, 0, 18),
                   elbow_R=(0.7, 0.3, -0.4))
    throw_r = over(pouch, hand_R=(sw + 0.25, 0.45, -dz * 0.5), hrot_R=None, spine=(P['posture'] + 6, 0, -18),
                   elbow_R=(0.7, 0.3, -0.4))
    throw_c = over(pouch, hand_R=(0.05, 0.55, -dz * 0.4), hrot_R=None, spine=(P['posture'] + 10, 0, 0),
                   elbow_R=(0.7, 0.3, -0.4))
    keyed_clip('scatter_salt', 60, [(0, b), (0.3, grab), (0.55, throw_l), (0.8, grab), (1.05, throw_c), (1.3, grab),
                                    (1.55, throw_r), (2.0, pouch), (2.5, b)])

    # relight a candle: the light stays upright in the right hand at the chest, the left hand strikes a
    # match twice and brings it to the wick
    hold = over(b, hand_R=(0.04, 0.26, -dz * 0.55), hrot_R=(0, 0, 0), elbow_R=(0.7, 0.4, -0.5),
                hand_L=(0.12, 0.3, -dz * 0.5), hrot_L=None, elbow_L=(0.7, 0.4, -0.5), neck=(18, 0, 0),
                spine=(P['posture'] + 4, 0, 0), expr={'uneasy': 0.7})
    strike = add(hold, hand_L=(0.08, 0.04, -0.03))
    wick = over(hold, hand_L=(0.02, 0.3, -dz * 0.38), expr={'calm': 1.0})
    keyed_clip('relight_candle', 60, [(0, b), (0.35, hold), (0.55, strike), (0.7, hold), (0.9, strike), (1.05, hold),
                                      (1.6, wick), (2.1, wick), (2.5, b)])

    # sit (loop): pivot = seat surface (MARK_sit), feet 0.48 m below on the floor
    seat_h = 0.48
    hz = P['hip_z']
    sit = over(b, hips=(0, 0.06, 0.1 - hz), foot_L=(0.03, 0.34, -seat_h), foot_R=(0.03, 0.34, -seat_h),
               knee=(0.1, 1.0, 0.4), ground=False, spine=(P['posture'] * 0.6 - 4, 0, 0),
               hand_L=(0.13, 0.3, -(P['sh_z'] - hz) + 0.12), hand_R=(0.13, 0.3, -(P['sh_z'] - hz) + 0.12),
               hrot_L=None, hrot_R=None, elbow_L=(0.6, 0.5, -0.5), elbow_R=(0.6, 0.5, -0.5))
    if V.info['hold'] in ('candle', 'doll'):
        sit = over(sit, **{k: v for k, v in V.hold().items()})
        sit = add(sit, hand_L=(0, 0.02, 0.0), hand_R=(0, 0.02, 0.0))

    def sit_fn(f):
        t = T(f)
        bth = math.sin(2 * math.pi * t / 2.0)
        return V.pose(add(sit, spine=(1.2 * bth, 0, 0), shrug=(1.2 * bth, 1.2 * bth),
                          neck=(0, 0, 2 * math.sin(2 * math.pi * t / 2 + 0.5))))
    out['sit'] = (48, sit_fn, True)

    def rock_fn(f):
        t = T(f)
        r = math.sin(2 * math.pi * t / 2.5)
        return V.pose(add(sit, spine=(-3 * r, 0, 0), neck=(2 * r, 0, 0), foot_L=(0, 0.03 * r, 0.01 * max(0, r)),
                          foot_R=(0, 0.03 * r, 0.01 * max(0, r)), fpitch=(-8 * max(0, -r), -8 * max(0, -r))))
    out['rock_in_chair'] = (60, rock_fn, True)

    # sleep (loop): lying on the back on the pivot plane (MARK_sleep), head toward the facing direction (-Y)
    back = P['head_r'][1] * 0.9
    q_lie = Quaternion((1, 0, 0), math.radians(90)) @ Quaternion((0, 0, 1), math.radians(180))
    sl = over(b, root_q=q_lie, root=(0, -P['top'] * 0.5 + 0.05, back), ground=False, spine=(0, 0, 0),
              neck=(-6, 0, 10), hand_L=(sw + 0.02, 0.12, -V.arm_len * 0.85), hand_R=(0.12, 0.22, -dz * 0.6),
              hrot_L=None, hrot_R=None, elbow_R=(0.7, 0.3, -0.4), knee=(0.1, 1.0, 0.0),
              foot_L=(0.02, 0.0, 0.0), foot_R=(-0.01, 0.0, 0.0), fpitch=(30, 30), expr={'asleep': 1.0})

    def sleep_fn(f):
        t = T(f)
        bth = math.sin(2 * math.pi * t / 3.0)
        c = add(sl, spine=(1.5 * bth, 0, 0), shrug=(1.5 * bth, 1.5 * bth))
        c['root_q'] = q_lie
        return V.pose(c)
    out['sleep'] = (72, sleep_fn, True)

    # sweep (loop): both hands on a broom held at the right side, sweeping across the front
    def sweep_fn(f):
        t = T(f)
        s = math.sin(2 * math.pi * t / 1.5)
        c = over(b, hand_R=(0.02 - 0.16 * s, 0.32, -dz * 0.95), hand_L=(0.04 - 0.08 * s, 0.24, -dz * 0.45),
                 hrot_R=(55, 0, 25 * s), hrot_L=(55, 0, 25 * s), elbow_L=(0.7, 0.4, -0.5), elbow_R=(0.7, 0.4, -0.5),
                 spine=(P['posture'] + 14, 0, -12 * s), neck=(10, 0, 4 * s), expr={'calm': 1.0})
        return V.pose(c)
    out['sweep'] = (36, sweep_fn, True)

    # work the field (loop): raise the tool, plunge it into the ground in front, lever it back
    raise_ = over(b, hand_R=(0.12, 0.3, -dz * 0.2), hand_L=(0.06, 0.32, 0.02), hrot_R=(50, 0, 0), hrot_L=(50, 0, 0),
                  elbow_L=(0.7, 0.4, -0.5), elbow_R=(0.7, 0.4, -0.5), spine=(P['posture'] - 4, 0, 0), neck=(6, 0, 0),
                  expr={'calm': 1.0})
    plunge = over(raise_, hand_R=(0.1, 0.45, -dz * 1.0), hand_L=(0.06, 0.42, -dz * 0.65), hrot_R=(125, 0, 0),
                  hrot_L=(125, 0, 0), spine=(P['posture'] + 26, 0, 0), neck=(8, 0, 0), hips=(0, 0.04, -0.05))
    lever = over(plunge, hand_R=(0.1, 0.3, -dz * 0.75), hand_L=(0.06, 0.3, -dz * 0.4), hrot_R=(95, 0, 0),
                 hrot_L=(95, 0, 0), spine=(P['posture'] + 14, 0, 0))
    keyed_clip('work_field', 40, [(0, raise_), (0.45, plunge), (0.75, plunge), (1.2, lever), (1.67, raise_)], loop=True)

    # serve drinks (loop): tray on the right palm at shoulder height, the left hand sets a mug down and comes back
    tray = over(b, hand_R=(sw + 0.08, 0.3, -0.02), hrot_R=(0, 0, 0), elbow_R=(0.8, 0.2, -0.6),
                hand_L=(0.1, 0.25, -dz * 0.55), hrot_L=None, elbow_L=(0.6, 0.4, -0.6), expr={'relieved': 0.3})
    place = over(tray, hand_L=(0.08, 0.5, -dz * 0.62), spine=(P['posture'] + 14, 0, -6), neck=(10, 0, 0),
                 hand_R=(sw + 0.08, 0.28, 0.0))
    keyed_clip('serve_drinks', 48, [(0, tray), (0.6, add(tray, hand_L=(-0.05, 0.05, 0.22))), (1.1, place),
                                    (1.5, place), (2.0, tray)], loop=True)
    return out, speeds


# ----------------------------------------------------------------------------- build one villager
def build_villager(v, coll):
    mats()
    P = PROPS[v]
    name = f'villager_{v}'
    sk = skeleton(name, P)
    rig = C.build_armature(sk, coll)
    B = Body(name, P, sk)
    info = BUILDERS[v](B)
    body = B.cm.build(coll, rig, sk)
    feats = face_features(P, info.get('mouth_lift', 0.0), info.get('brow_mat', 'hair_brown'),
                          mouth_z=info.get('mouth_z', -0.42))
    face = C.build_face(f'{name}_face', feats, EXPRS, head_surf(P), coll, rig, sk, 'head')
    res = dict(rig=rig, body=body, face=face, faces=[face], skel=sk, name=name, kind='villager', s=1.0)
    if info.get('hat'):
        res['hat'] = B.make_hat(coll, rig, info['hat'])
    # held-item sockets in the palms; axes = character frame at rest (items stand upright, face forward)
    for side in ('L', 'R'):
        e = bpy.data.objects.new(f'HELD_{side}', None)
        e.empty_display_size = 0.06
        e.empty_display_type = 'ARROWS'
        coll.objects.link(e)
        wr, tip = sk.head(f'hand_{side}'), sk.tail(f'hand_{side}')
        pos = wr.lerp(tip, 0.45) + Vector((0, -0.01, 0))
        C.attach_to_bone(e, rig, f'hand_{side}', Matrix.Translation(pos))
        res[f'HELD_{side}'] = e
    for side, kind in info.get('items', {}).items():
        root, grip = build_item(kind, coll)
        root.parent = res[f'HELD_{side}']
        root.matrix_parent_inverse = Matrix()
        k = 0.7 if kind == 'doll' else 1.0
        root.matrix_basis = Matrix.Translation(-grip * k) @ Matrix.Scale(k, 4)
    V = Villager(name, P, sk, info)
    out, speeds = clips(V)
    res['clips'] = out
    res['villager'] = V
    hat_h = 0.0
    res['info'] = {'no_slide_speed_mps': speeds, 'hold': info['hold'],
                   'items': info.get('items', {}), 'leg_length': round(V.leg_len, 3),
                   'hip_height': P['hip_z'], 'head_top': P['top'], 'hat': bool(info.get('hat')),
                   'events': {'big_scare_leap': {'hat_off_frame': 8, 'drop_item_frame': 11, 'land_frame': 28}}}
    # clips that show the default held item; in every other clip Godot hides (or swaps) the HELD_* items
    shown = set(ITEM_CLIPS)
    if info['hold'] in ('candle', 'doll'):
        shown |= {'sit', 'rock_in_chair'}
    if info['hold'] == 'pitchfork':
        shown |= {'work_field'}
    res['info']['item_clips'] = sorted(c for c in out if c in shown)
    res['hide_item_in'] = [c for c in out if c not in shown]
    res['preview_lift'] = {'sit': 0.48, 'rock_in_chair': 0.48}
    res['strip_dir'] = (-0.9, -1, 0.3)
    return res


ITEM_CLIPS = ['idle', 'walk', 'walk_uneasy', 'look_over_shoulder', 'call_out', 'clutch_candle_walk', 'startle',
              'big_scare_leap', 'suspicious_search', 'relight_candle']
