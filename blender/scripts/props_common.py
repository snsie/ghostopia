"""Shared prop pieces (flames, candles, lantern cages, plank panels) and the prop registry."""
import math

from mathutils import Vector

import lib_geo as G

REGISTRY = {}


def prop(name, cat, haunt=False, desc=''):
    """Decorator: register a builder fn() -> G.Prop."""
    def deco(fn):
        REGISTRY[name] = dict(fn=fn, cat=cat, haunt=haunt, desc=desc)
        return fn
    return deco


def new(name, haunt=False, seed=None):
    G.seed(seed if seed is not None else (sum(map(ord, name)) * 7))
    p = G.Prop(name)
    p.haunt = haunt
    return p


def flame_node(name, base, h=0.09, r=0.025):
    """Teardrop flame mesh (FLAME_* node) with pivot at its base."""
    n = G.MeshNode('FLAME_' + name, pivot=base)
    b = Vector(base)
    n.lathe('FLAME_fire', [(0.0, 0), (r, h * 0.25), (r * 0.9, h * 0.5), (r * 0.45, h * 0.8), (0.0, h)],
            b, segs=8)
    n.lathe('FLAME_core', [(0.0, 0.002), (r * 0.55, h * 0.22), (r * 0.4, h * 0.45), (0.0, h * 0.65)],
            b + Vector((0, -0.004, 0)), segs=8)
    return n


def add_flame(parent, name, base, h=0.09, r=0.025, energy=8.0, color=(1.0, 0.62, 0.3), int_node=True,
              light_offset=0.06):
    """INT_<name> empty at the wick with FLAME_<name> mesh, LIGHT_<name> and FX_flame children."""
    base = Vector(base)
    holder = G.Node(('INT_' if int_node else 'FIRE_') + name, 'empty', base)
    holder.props['size'] = 0.05
    parent.add(holder)
    holder.add(flame_node(name, base, h, r))
    holder.add(G.LightNode('LIGHT_' + name, base + Vector((0, 0, light_offset)), energy, color, 0.03))
    fx = G.empty('FX_flame_' + name, base + Vector((0, 0, h)), size=0.05)
    holder.add(fx)
    return holder


def candle_geo(m, base, r=0.035, h=0.14, drips=3):
    """Wax candle with drips on mesh node m; returns the wick top position."""
    b = Vector(base)
    m.cyl('wax', r, r * 0.95, h, b + Vector((0, 0, h / 2)), segs=10, bevel=0.008)
    m.cyl('wax', r * 1.08, r * 1.0, 0.012, b + Vector((0, 0, h - 0.004)), segs=10, bevel=0.004)
    for k in range(drips):
        a = k / drips * 2 * math.pi + 0.6
        dl = h * (0.35 + 0.25 * ((k * 37) % 5) / 5)
        m.cyl('wax', 0.008, 0.012, dl, b + Vector((math.cos(a) * r, math.sin(a) * r, h - dl / 2)), segs=6,
              bevel=0.003)
    m.cyl('ink_dark', 0.003, 0.003, 0.02, b + Vector((0, 0, h + 0.01)), segs=4, bevel=0)
    return b + Vector((0, 0, h + 0.012))


def plank_panel(m, mat, x0, x1, z0, z1, y, thick=0.06, n=None, vertical=True, gap=0.008, bevel=0.012):
    """A panel made of separate planks (vertical or horizontal) in the XZ plane at depth y."""
    if vertical:
        w = x1 - x0
        n = n or max(2, round(w / 0.2))
        pw = w / n
        for i in range(n):
            cx = x0 + pw * (i + 0.5)
            m.box(mat, (pw - gap, thick, z1 - z0), (cx, y, (z0 + z1) / 2), bevel=bevel, jitter=0.003)
    else:
        hgt = z1 - z0
        n = n or max(2, round(hgt / 0.2))
        ph = hgt / n
        for i in range(n):
            cz = z0 + ph * (i + 0.5)
            m.box(mat, (x1 - x0, thick, ph - gap), ((x0 + x1) / 2, y, cz), bevel=bevel, jitter=0.003)


def arch_outline(w, h, segs=10, spring=None):
    """Rectangle w x h (x centred, z from 0) with a semicircular top; list of (x, z)."""
    r = w / 2
    spring = h - r if spring is None else spring
    pts = [(-r, 0), (r, 0), (r, spring)]
    for i in range(1, segs):
        a = i / segs * math.pi
        pts.append((math.cos(a) * r, spring + math.sin(a) * r))
    pts.append((-r, spring))
    return pts


def lantern_geo(parent, m, name, base, scale=1.0, hang=False):
    """Square iron-frame lantern with glass, flame, light. base = bottom centre."""
    s = scale
    b = Vector(base)
    m.box('iron', (0.2 * s, 0.2 * s, 0.04 * s), b + Vector((0, 0, 0.02 * s)), bevel=0.01)
    m.box('GLOW_lamp_glass', (0.15 * s, 0.15 * s, 0.2 * s), b + Vector((0, 0, 0.14 * s)), bevel=0.01)
    for dx in (-1, 1):
        for dy in (-1, 1):
            m.box('iron', (0.025 * s, 0.025 * s, 0.24 * s), b + Vector((dx * 0.085 * s, dy * 0.085 * s, 0.14 * s)),
                  bevel=0.005)
    m.lathe('iron', [(0.13 * s, 0), (0.12 * s, 0.03 * s), (0.04 * s, 0.1 * s), (0.0, 0.11 * s)],
            b + Vector((0, 0, 0.255 * s)), segs=4, rot=(0, 0, math.pi / 4))
    ring = [b + Vector((math.cos(a) * 0.04 * s, 0, 0.39 * s + math.sin(a) * 0.04 * s))
            for a in [k / 10 * 2 * math.pi for k in range(11)]]
    m.tube('iron', ring, 0.008 * s, 5)
    return add_flame(parent, name, b + Vector((0, 0, 0.07 * s)), h=0.08 * s, r=0.022 * s, energy=25 * s,
                     int_node=True, light_offset=0.08 * s)
