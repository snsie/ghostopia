"""Task 4: who lives in Millbrook, where they are at every hour, what can be haunted, what lies in the
ground and what memories it holds. Pure Python + numpy (no Blender), deterministic.

    python blender/scripts/build_population.py --json-only
        -> assets/levels/millbrook_population.json + assets/data/memory_fragments.json

Reads the task1-3 data (layout JSON + voxels, blocks.json, props.json, characters.json) and never edits it.
Every gameplay number is a placeholder: sections carry `"tuning": true`, and Scott tunes feel later.
Hand-authored content (villagers, lines, fragments, rumour templates) lives in lib_population_content.py.
"""
import gzip
import heapq
import json
import math
import os

import numpy as np

import lib_population_content as PC

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
LAYOUT = os.path.join(ROOT, 'assets', 'levels', 'millbrook_layout.json')
VOXELS = os.path.join(ROOT, 'assets', 'levels', 'millbrook_voxels.bin')
BLOCKS = os.path.join(ROOT, 'assets', 'blocks', 'blocks.json')
PROPS = os.path.join(ROOT, 'assets', 'props', 'props.json')
CHARS = os.path.join(ROOT, 'assets', 'characters', 'characters.json')
OUT_POP = os.path.join(ROOT, 'assets', 'levels', 'millbrook_population.json')
OUT_FRAG = os.path.join(ROOT, 'assets', 'data', 'memory_fragments.json')

WALK_SPEED_FACTOR = 1.2      # villagers walk at 1.2 x the clip's no-slide speed (Godot scales playback to match)
DARK_MIN_STRETCH = 4.0       # metres of unlit outdoor route before it counts as a dark stretch
HAUNT_NEAR_ROUTE = 3.0       # a hauntable this close to a route counts as "on the route"
HIDE_NEAR = 9.0              # hiding spots / hauntables this close are checked for "behind the villager"
BEHIND_DEG = 100.0           # angle from the facing direction beyond which something is "behind"
COMPANY_OUTDOOR = 10.0       # another villager this close outdoors (same time) means "not alone"


def r2(v, n=2):
    return [round(float(a), n) for a in v] if isinstance(v, (list, tuple, np.ndarray)) else round(float(v), n)


def facing(yaw):
    a = math.radians(yaw)
    return math.sin(a), math.cos(a)       # Godot: yaw 0 faces +Z, 90 faces +X


def held_socket(char_info, item, default_item):
    """Hand socket for a held item: the default item keeps its own hand, anything else goes in the other one."""
    own = next((k for k, v in char_info.get('items', {}).items() if v == default_item), 'R')
    if item == default_item:
        return 'HELD_' + own
    return 'HELD_L' if own == 'R' else 'HELD_R'


def yaw_to(dx, dz):
    return round(math.degrees(math.atan2(dx, dz)), 1) % 360.0


def hhmm(h):
    h = h % 24.0
    m = int(round(h * 60))
    return f'{(m // 60) % 24:02d}:{m % 60:02d}'


# ============================================================================== data access
class World:
    def __init__(self):
        self.layout = json.load(open(LAYOUT, encoding='utf-8'))
        bdoc = json.load(open(BLOCKS, encoding='utf-8'))
        self.blocks = {b['id']: b for b in bdoc['blocks']}
        self.bindex = {b['index']: b for b in bdoc['blocks']}
        self.props = json.load(open(PROPS, encoding='utf-8'))['props']
        self.chars = json.load(open(CHARS, encoding='utf-8'))['characters']
        sx, sy, sz = self.layout['world']['size']
        self.size = (sx, sy, sz)
        raw = gzip.decompress(open(VOXELS, 'rb').read())
        self.W = np.frombuffer(raw, np.uint8).reshape(sy, sz, sx).transpose(2, 0, 1)   # W[x, y, z]
        self.markers = {m['id']: m for m in self.layout['markers']}
        self.instances = {i['id']: i for i in self.layout['instances']}
        self.structures = {s['id']: s for s in self.layout['structures']}
        self.areas = {a['id']: a for a in self.layout['areas']}

    def block(self, x, y, z):
        sx, sy, sz = self.size
        if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
            return 'air'
        return self.bindex[int(self.W[x, y, z])]['id']

    def area_at(self, p):
        best = None
        for a in self.layout['areas']:
            x0, z0, x1, z1 = a['rect']
            if x0 <= p[0] <= x1 and z0 <= p[2] <= z1 and (best is None or a['priority'] > best['priority']):
                best = a
        return best['id'] if best else 'open_plains'

    def indoors(self, p):
        """A roof (any solid block) within 8 cells above the head."""
        x, y, z = int(math.floor(p[0])), int(round(p[1])), int(math.floor(p[2]))
        for yy in range(y + 2, min(y + 10, self.size[1])):
            b = self.block(x, yy, z)
            if b != 'air' and self.blocks[b].get('solid') and not self.blocks[b].get('liquid'):
                return True
        return False

    def room_of(self, p):
        for s in self.layout['structures']:
            for r in s.get('rooms', []):
                mn, mx = r['min'], r['max']
                if all(mn[i] - 0.05 <= p[i] <= mx[i] + 0.05 for i in range(3)):
                    return s['id'], r['name']
        return None, None

    def resident_of(self, owner):
        s = self.structures.get(owner)
        return s['resident'] if s else None


# ============================================================================== day/night cycle
class Cycle:
    """Hours are 'unwrapped' from 17:00 (day) to 41:00 (17:00 next day). T is the cycle position, also
    unwrapped: T(17:00) = -0.06 ... T(41:00) = 0.94; the Godot cycle t = T mod 1."""

    def __init__(self, layout):
        c = layout['lighting']['cycle']
        self.length = c['length_s']
        ts, hs = [], []
        prev = None
        for k in c['keys']:
            h = k['hour']
            if prev is not None and h < prev:
                h += 24.0
            hs.append(h)
            ts.append(k['t'])
            prev = h
        self.ts, self.hs = np.array(ts), np.array(hs)   # t 0..1, hours 18.5 .. 42.5

    def T(self, h):
        if h < 18.5:
            return float(np.interp(h + 24.0, self.hs, self.ts)) - 1.0
        return float(np.interp(h, self.hs, self.ts))

    def H(self, T):
        if T < 0:
            return float(np.interp(T + 1.0, self.ts, self.hs)) - 24.0
        return float(np.interp(T, self.ts, self.hs))

    def phase(self, h):
        t = self.T(h) % 1.0
        if 0.08 <= t < 0.58:
            return 'night'
        if 0.58 <= t < 0.70:
            return 'dawn'
        if 0.70 <= t < 0.94:
            return 'day'
        return 'dusk'

    def seconds(self, h0, h1):
        return (self.T(h1) - self.T(h0)) * self.length

    def add_seconds(self, h, s):
        return self.H(self.T(h) + s / self.length)


# ============================================================================== navigation
WALL_PROPS = {'fence_wood': 40.0, 'fence_post': 40.0}
FURNITURE = {'barrel', 'crate', 'bench', 'bed', 'wardrobe', 'table', 'tavern_table', 'chest', 'hearth', 'shelf',
             'rocking_chair', 'chair', 'stool', 'side_table', 'millstone', 'grain_sack', 'notice_board', 'bell',
             'scarecrow', 'lantern_post', 'tree_oak', 'dead_tree', 'pumpkin', 'basket', 'bucket', 'gravestone_round',
             'gravestone_cross', 'gravestone_spiral', 'gravestone_celtic', 'dirt_mound', 'stone_pillar', 'books',
             'mausoleum_gargoyle_winged', 'eerie_crystal_cluster', 'ladder'}
TRUNK = {'tree_oak': (0.9, 0.9), 'dead_tree': (1.0, 1.0)}
PATH_BLOCKS = {'cobble_path': 1.0, 'packed_path': 1.0, 'cobblestone': 1.05, 'timber_planks': 1.0, 'rough_wood': 1.05,
               'stone': 1.3, 'mossy_stone_bricks': 1.2}


class Nav:
    """A* over standable cells (solid below, two open cells above). Soft costs keep villagers on paths
    and around furniture; fences are nearly impassable. Vertical links model the mill ladder."""

    def __init__(self, world):
        self.w = world
        W = world.W
        N = 256
        solid = np.zeros(N, bool)
        opn = np.zeros(N, bool)
        liquid = np.zeros(N, bool)
        crop = np.zeros(N, np.float32)
        floor_cost = np.full(N, 1.7, np.float32)
        for b in world.blocks.values():
            i = b['index']
            liquid[i] = bool(b.get('liquid'))
            if b['id'] == 'air':
                opn[i] = True
            elif b.get('shape') == 'cross':
                opn[i] = True
                crop[i] = 3.0 if b['id'] == 'wheat' else 0.4
            elif b.get('solid') and not b.get('liquid'):
                solid[i] = True
            floor_cost[i] = PATH_BLOCKS.get(b['id'], 1.7 if b['id'] != 'sand' else 2.0)
        below = np.zeros_like(W, bool)
        below[:, 1:, :] = solid[W[:, :-1, :]]
        head = np.zeros_like(W, bool)
        head[:, :-1, :] = opn[W[:, 1:, :]]
        self.walk = below & opn[W] & head
        cost = np.zeros(W.shape, np.float32)
        cost[:, 1:, :] = floor_cost[W[:, :-1, :]]
        cost += crop[W]
        # keep a little off walls: +0.4 next to a non-walkable column at the same height
        near = np.zeros_like(self.walk)
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near |= ~np.roll(np.roll(self.walk, dx, 0), dz, 2)
        cost += 0.4 * near
        self.cost = cost
        self._props()
        self.links = {}
        for m in world.layout['markers']:
            if m['kind'] == 'climb':
                bot = self.snap(m['pos'])
                top = self.snap([m['pos'][0], m['pos'][1] + 4.0, m['pos'][2] + 1.5], ylim=0.6, rad=3.0)
                self.links.setdefault(bot, []).append(top)
                self.links.setdefault(top, []).append(bot)
                self.ladders = getattr(self, 'ladders', []) + [(bot, top, m['id'])]

    def _props(self):
        for inst in self.w.layout['instances']:
            name = inst['prop']
            if name in WALL_PROPS:
                add = WALL_PROPS[name]
            elif name in FURNITURE:
                add = 6.0
            else:
                continue
            sx, _, sz = self.w.props[name]['size']
            if name in TRUNK:
                sx, sz = TRUNK[name]
            x, y, z = inst['pos']
            fx, fz = facing(inst['yaw'])     # local +Z
            rx, rz = fz, -fx                 # local +X
            cy = int(round(y))
            for u in np.arange(-sx / 2, sx / 2 + 1e-6, 0.2):
                for v in np.arange(-sz / 2, sz / 2 + 1e-6, 0.2):
                    px, pz = x + u * rx + v * fx, z + u * rz + v * fz
                    cx, cz = int(math.floor(px)), int(math.floor(pz))
                    if 0 <= cx < self.w.size[0] and 0 <= cz < self.w.size[2]:
                        self.cost[cx, cy, cz] = max(self.cost[cx, cy, cz], 1.0 + add)

    def snap(self, p, ylim=1.6, rad=2.5):
        x, y, z = p
        best, bd = None, 1e9
        r = int(math.ceil(rad))
        for cx in range(int(math.floor(x)) - r, int(math.floor(x)) + r + 1):
            for cz in range(int(math.floor(z)) - r, int(math.floor(z)) + r + 1):
                for cy in range(int(math.floor(y - ylim)), int(math.ceil(y + ylim)) + 1):
                    if not (0 <= cx < self.w.size[0] and 1 <= cy < self.w.size[1] - 1 and 0 <= cz < self.w.size[2]):
                        continue
                    if not self.walk[cx, cy, cz]:
                        continue
                    d = (cx + 0.5 - x) ** 2 + (cz + 0.5 - z) ** 2 + 0.5 * (cy - y) ** 2 + 0.6 * max(0, self.cost[cx, cy, cz] - 3)
                    if d < bd:
                        best, bd = (cx, cy, cz), d
        if best is None:
            raise ValueError(f'no standable cell near {p}')
        return best

    def astar(self, a, b):
        walk, cost = self.walk, self.cost
        sx, sy, sz = self.w.size
        openh = [(0.0, 0.0, a)]
        g = {a: 0.0}
        came = {}
        bx, by, bz = b
        while openh:
            f, gc, cur = heapq.heappop(openh)
            if cur == b:
                break
            if gc > g.get(cur, 1e18):
                continue
            x, y, z = cur
            nbrs = []
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dz == 0:
                        continue
                    for dy in (0, 1, -1):
                        nx, ny, nz = x + dx, y + dy, z + dz
                        if not (0 <= nx < sx and 1 <= ny < sy - 2 and 0 <= nz < sz) or not walk[nx, ny, nz]:
                            continue
                        if dx and dz and not ((walk[x + dx, ny, z] or walk[x + dx, y, z]) and
                                              (walk[x, ny, z + dz] or walk[x, y, z + dz])):
                            continue   # no corner cutting past walls
                        step = (1.4142 if dx and dz else 1.0) * 0.5 * (cost[x, y, z] + cost[nx, ny, nz]) + 0.6 * abs(dy)
                        nbrs.append(((nx, ny, nz), step))
                        break
            for t in self.links.get(cur, []):
                nbrs.append((t, 8.0))
            for n, st in nbrs:
                ng = gc + st
                if ng < g.get(n, 1e18):
                    g[n] = ng
                    came[n] = cur
                    h = math.sqrt((n[0] - bx) ** 2 + (n[2] - bz) ** 2 + (n[1] - by) ** 2)
                    heapq.heappush(openh, (ng + h, ng, n))
        if b not in came and a != b:
            raise ValueError(f'no route {a} -> {b}')
        path = [b]
        while path[-1] != a:
            path.append(came[path[-1]])
        return path[::-1]

    def route(self, p0, p1):
        a, b = self.snap(p0), self.snap(p1)
        cells = self.astar(a, b)
        pts = [(c[0] + 0.5, float(c[1]), c[2] + 0.5) for c in cells]
        ladder = set()
        for i in range(1, len(cells)):
            if cells[i] in self.links.get(cells[i - 1], []):
                ladder.add(i)
        # exact endpoints, then simplify (keep height changes and ladder ends)
        pts = [tuple(p0)] + pts[1:-1] + [tuple(p1)] if len(pts) > 1 else [tuple(p0), tuple(p1)]
        keep = simplify(pts, 0.3, ladder)
        out = [pts[i] for i in keep]
        lad = [k for k, i in enumerate(keep) if i in ladder]
        return out, lad


def simplify(pts, eps, force):
    """Ramer-Douglas-Peucker in xz, keeping points where the height changes and forced indices."""
    n = len(pts)
    keep = {0, n - 1} | set(force) | {i - 1 for i in force if i > 0}
    for i in range(1, n - 1):
        if abs(pts[i][1] - pts[i - 1][1]) > 0.01 or abs(pts[i + 1][1] - pts[i][1]) > 0.01:
            keep.add(i)
    ks = sorted(keep)
    res = set(ks)
    for a, b in zip(ks, ks[1:]):
        stack = [(a, b)]
        while stack:
            i, j = stack.pop()
            if j - i < 2:
                continue
            ax, az = pts[i][0], pts[i][2]
            bx, bz = pts[j][0], pts[j][2]
            L = math.hypot(bx - ax, bz - az) or 1e-9
            dmax, imax = 0, None
            for k in range(i + 1, j):
                d = abs((bx - ax) * (az - pts[k][2]) - (ax - pts[k][0]) * (bz - az)) / L
                if d > dmax:
                    dmax, imax = d, k
            if dmax > eps:
                res.add(imax)
                stack += [(i, imax), (imax, j)]
    return sorted(res)


def polyline_len(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def sample_polyline(pts, step):
    """[(dist_along, (x, y, z))] every `step` metres, ends included."""
    out = [(0.0, tuple(pts[0]))]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1):
            f = k / n
            out.append((acc + f * L, tuple(a[i] + (b[i] - a[i]) * f for i in range(3))))
        acc += L
    return out


def point_at(pts, frac):
    total = polyline_len(pts)
    target = total * frac
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if acc + L >= target and L > 0:
            f = (target - acc) / L
            return tuple(a[i] + (b[i] - a[i]) * f for i in range(3)), yaw_to(b[0] - a[0], b[2] - a[2])
        acc += L
    a, b = pts[-2], pts[-1]
    return tuple(pts[-1]), yaw_to(b[0] - a[0], b[2] - a[2])


# ============================================================================== hauntables
def build_hauntables(w):
    out = []
    for inst in w.layout['instances']:
        kind = inst.get('hauntable')
        if not kind and inst['prop'] in PC.EXTRA_HAUNTABLE_PROPS:
            kind = PC.EXTRA_HAUNTABLE_PROPS[inst['prop']]
        if not kind:
            continue
        k = PC.HAUNT_KINDS[kind]
        sid, room = w.room_of(inst['pos'])
        owner = inst['owner']
        h = {
            'id': inst['id'], 'kind': kind, 'instance': inst['id'], 'prop': inst['prop'],
            'pos': r2(inst['pos'], 3), 'yaw': inst['yaw'], 'owner': owner, 'area': inst['area'],
            'resident': w.resident_of(owner), 'room': room,
            'source': 'layout' if inst.get('hauntable') else 'population',
            'haunt_shell': bool(w.props[inst['prop']].get('hauntable')),
            'path': k['path'], 'level': k['level'], 'ability': k['ability'], 'slice_active': k['level'] <= 2,
            'actions': k['actions'], 'unease': dict(k['unease']), 'fears': list(k['fears']),
            'noise_radius_m': k['noise_radius_m'], 'cooldown_s': k['cooldown_s'],
            'int_nodes': [n for n in w.props[inst['prop']]['nodes'] if n.startswith('INT_')],
        }
        link = PC.FEAR_LINKS.get(inst['id'])
        if link:
            for f in link['fears']:
                if f not in h['fears']:
                    h['fears'].append(f)
            h['fear_note'] = link['note']
        if not h['haunt_shell']:
            h['note'] = 'No HAUNT_ shell in the glTF: Godot draws the haunt rim on the INT_ part with a shader overlay.'
        out.append(h)
    return out


# ============================================================================== schedules
class Scheduler:
    def __init__(self, w, nav, cyc, hauntables):
        self.w, self.nav, self.cyc = w, nav, cyc
        self.hauntables = hauntables
        self.hiding = [m for m in w.layout['markers'] if m['kind'] == 'hiding_spot']
        self.lights = self._lights()

    def _lights(self):
        L = []
        for inst in self.w.layout['instances']:
            r = PC.LIGHT_RADIUS.get(inst['prop'])
            if r:
                x, y, z = inst['pos']
                L.append((x, y + 1.0, z, r))
        return np.array(L)

    # ---- resolve a place spec to (pos, yaw, marker id, target id)
    def place(self, spec):
        w = self.w
        if 'marker' in spec:
            m = w.markers[spec['marker']]
            p = list(m['pos'])
            yaw = spec.get('yaw', m['yaw'])
            if m['kind'] in ('chair', 'bed'):
                return p, yaw, m['id'], None
            if 'offset' in spec:
                fx, fz = facing(m['yaw'])
                d = spec['offset']
                p = [p[0] + fx * d, p[1], p[2] + fz * d]
            cell = self.nav.snap([p[0], p[1] - 0.5, p[2]], ylim=1.6, rad=1.5)   # window markers sit at sill height
            return [p[0], float(cell[1]), p[2]], yaw, m['id'], None
        if 'inside_door' in spec:   # stand just inside a front door, facing out
            d = w.markers[spec['inside_door']]
            e = w.markers[spec['inside_door'].replace('door_', 'entry_')]
            vx, vz = d['pos'][0] - e['pos'][0], d['pos'][2] - e['pos'][2]
            n = math.hypot(vx, vz)
            p = [d['pos'][0] + vx / n * 0.9, d['pos'][1], d['pos'][2] + vz / n * 0.9]
            return p, yaw_to(-vx, -vz), d['id'], d['id']
        if 'at_instance' in spec:   # stand in front of a prop (candle, lamp...), facing it
            inst = w.instances[spec['at_instance']]
            fx, fz = facing(inst['yaw'])
            d = spec.get('dist', 0.75)
            x, z = inst['pos'][0] + fx * d, inst['pos'][2] + fz * d
            cell = self.nav.snap([x, inst['pos'][1], z], ylim=1.6, rad=1.5)
            y = float(cell[1])
            return [x, y, z], yaw_to(-fx, -fz), None, inst['id']
        raise ValueError(spec)

    def build(self, vid, v):
        cyc = self.cyc
        speed = self.w.chars[v['character']]['no_slide_speed_mps']['walk'] * WALK_SPEED_FACTOR
        steps = []
        h = 17.0
        prev = None
        for i, s in enumerate(v['schedule']):
            pos, yaw, marker, target = self.place(s['at'])
            if prev is not None and math.dist(prev[0], pos) > 1.2:
                pts, lad = self.nav.route(prev[0], pos)
                L = polyline_len(pts)
                dur = L / speed + 4.0 * len(lad)
                h1 = cyc.add_seconds(h, dur)
                steps.append(dict(kind='walk', activity=s.get('walk_as', 'walk'), start=h, end=h1, route=pts,
                                  ladder=lad, length=L, speed=speed, held=s.get('walk_held', v['walk_held']),
                                  clip=s.get('walk_clip', 'walk'), duration=dur, light=s.get('walk_light')))
                h = h1
            until = s['until']
            if until <= h + 1e-6:
                raise ValueError(f'{vid}: step {i} "{s["activity"]}" starts {hhmm(h)} after its end {hhmm(until)}')
            steps.append(dict(kind='stay', activity=s['activity'], start=h, end=until, pos=pos, yaw=yaw, marker=marker,
                              target=target, clip=s['clip'], held=s.get('held'), note=s.get('note'),
                              vulnerable=s.get('vulnerable', False), expression=s.get('expression', 'calm'),
                              witness_view=s.get('witness_view')))
            h = until
            prev = (pos, yaw)
        if abs(h - 41.0) > 1e-6:
            raise ValueError(f'{vid}: schedule ends at {hhmm(h)}, not 17:00')
        first = steps[0]
        if math.dist(prev[0], first['pos']) > 1.2:
            raise ValueError(f'{vid}: the day does not end where the evening starts')
        return steps

    # ---- analysis
    def darkness(self, pts):
        samples = sample_polyline(pts, 0.5)
        dark = []
        for d, p in samples:
            if self.w.indoors(p):
                dark.append(False)
                continue
            if len(self.lights):
                dd = np.sqrt((self.lights[:, 0] - p[0]) ** 2 + (self.lights[:, 2] - p[2]) ** 2 +
                             0.3 * (self.lights[:, 1] - p[1]) ** 2)
                dark.append(bool((dd > self.lights[:, 3]).all()))
            else:
                dark.append(True)
        stretches = []
        i = 0
        while i < len(samples):
            if dark[i]:
                j = i
                while j + 1 < len(samples) and dark[j + 1]:
                    j += 1
                a, b = samples[i][0], samples[j][0]
                if b - a >= DARK_MIN_STRETCH:
                    stretches.append([round(a, 1), round(b, 1)])
                i = j + 1
            else:
                i += 1
        return stretches

    def near_route(self, pts, items, rad, key='pos'):
        samples = [p for _, p in sample_polyline(pts, 0.5)]
        S = np.array(samples)
        out = []
        for it in items:
            p = np.array(it[key])
            d = np.sqrt(((S - p) ** 2).sum(1)).min()
            if d <= rad:
                out.append((it, float(d)))
        return out

    def behind(self, pos, yaw, area_id):
        fx, fz = facing(yaw)
        res = []
        cands = [(m['id'], m['pos'], 'hiding_spot') for m in self.hiding]
        cands += [(h['id'], h['pos'], 'hauntable') for h in self.hauntables if h['kind'] in ('wardrobe', 'door')]
        interior = self.w.areas.get(area_id, {}).get('kind') in ('home', 'tavern')
        for cid, p, typ in cands:
            dx, dz = p[0] - pos[0], p[2] - pos[2]
            d = math.hypot(dx, dz)
            if d < 0.3 or d > HIDE_NEAR or abs(p[1] - pos[1]) > 2.5:
                continue
            if interior and self.w.area_at(p) != area_id:
                continue
            ang = math.degrees(math.acos(max(-1, min(1, (dx * fx + dz * fz) / d))))
            if ang >= BEHIND_DEG:
                res.append(cid)
        return sorted(set(res))


def place_at_hour(steps, h):
    """Position, yaw, clip, phase within the step for unwrapped hour h (17..41)."""
    for s in steps:
        if s['start'] <= h < s['end'] or (h >= 41 and s is steps[-1]):
            if s['kind'] == 'stay':
                return s['pos'], s['yaw'], s['clip'], s
            f = (h - s['start']) / max(1e-6, s['end'] - s['start'])
            p, yaw = point_at(s['route'], f)
            return list(p), yaw, s['clip'], s
    raise ValueError(h)


def company(all_steps, cyc, w, nav):
    """Who shares time and space with whom, step by step. Indoors: the same area. Outdoors: within
    COMPANY_OUTDOOR metres at the same moment (walks are sampled every 2 s)."""
    res = {}
    for vid, steps in all_steps.items():
        for si, s in enumerate(steps):
            T0, T1 = cyc.T(s['start']), cyc.T(s['end'])
            n = max(2, int((T1 - T0) * cyc.length / 2.0))
            alone_samples = 0
            comp = set()
            for k in range(n):
                T = T0 + (T1 - T0) * (k + 0.5) / n
                h = cyc.H(T)
                p, _, _, _ = place_at_hour(steps, h)
                a = w.area_at(p)
                ind = w.areas[a]['kind'] in ('home', 'tavern') and w.indoors(p)
                here = False
                for oid, osteps in all_steps.items():
                    if oid == vid:
                        continue
                    q, _, _, ostep = place_at_hour(osteps, h)
                    if ostep['activity'] == 'sleep':
                        continue          # a sleeping villager is no company and no witness
                    if ind:
                        if w.area_at(q) == a and w.indoors(q):
                            here = True
                            comp.add(oid)
                    else:
                        if not w.indoors(q) and math.dist(p, q) <= COMPANY_OUTDOOR:
                            here = True
                            comp.add(oid)
                if not here:
                    alone_samples += 1
            res[(vid, si)] = (alone_samples / n, sorted(comp))
    return res


# ============================================================================== main build
def build():
    w = World()
    cyc = Cycle(w.layout)
    nav = Nav(w)
    hauntables = build_hauntables(w)
    hmap = {h['id']: h for h in hauntables}
    sch = Scheduler(w, nav, cyc, hauntables)

    all_steps = {vid: sch.build(vid, v) for vid, v in PC.VILLAGERS.items()}
    comp = company(all_steps, cyc, w, nav)

    # carried lights become hauntables too (Flicker on the candle in Agnes's hands...)
    for vid, v in PC.VILLAGERS.items():
        items = sorted({s['held'] for s in all_steps[vid] if s.get('held') in ('candle', 'lantern')})
        for it in items:
            k = PC.HAUNT_KINDS[it]
            hid = f'carried_{it}_{vid}'
            during = [i for i, s in enumerate(all_steps[vid]) if s.get('held') == it]
            h = {'id': hid, 'kind': it, 'instance': None, 'prop': it, 'pos': None, 'yaw': None, 'owner': vid,
                 'area': None, 'resident': vid, 'room': None, 'source': 'carried', 'carried_by': vid,
                 'socket': held_socket(w.chars[v['character']], it, v['default_item']),
                 'node': f'ITEM_{it}' if it == v['default_item'] else None,
                 'attach_prop': None if it == v['default_item'] else f'res://assets/props/{it}.gltf',
                 'during_steps': during, 'haunt_shell': it == 'candle',
                 'path': k['path'], 'level': k['level'], 'ability': k['ability'], 'slice_active': True,
                 'actions': k['actions'], 'unease': {a: round(u * 1.5, 1) for a, u in k['unease'].items()},
                 'fears': list(k['fears']), 'noise_radius_m': k['noise_radius_m'], 'cooldown_s': k['cooldown_s'],
                 'int_nodes': ['INT_' + it],
                 'note': 'Snuffing the light in their own hands: 1.5x Unease. The villager relights it (relight_candle) '
                         'unless they bolt.'}
            hauntables.append(h)
            hmap[hid] = h

    villagers = []
    checks = {}
    for vid, v in PC.VILLAGERS.items():
        steps = all_steps[vid]
        home = v['home']
        out_steps = []
        route_hauntables = {}
        for si, s in enumerate(steps):
            alone_frac, who = comp[(vid, si)]
            o = {
                'id': f'{vid}_{si:02d}_{s["activity"]}', 'kind': s['kind'], 'activity': s['activity'],
                'start_hour': round(s['start'] % 24, 3), 'end_hour': round(s['end'] % 24, 3),
                'start': hhmm(s['start']), 'end': hhmm(s['end']),
                't_start': round(cyc.T(s['start']) % 1.0, 4), 't_end': round(cyc.T(s['end']) % 1.0, 4),
                'duration_s': round(cyc.seconds(s['start'], s['end']), 1),
                'phase': cyc.phase(s['start']),
                'animation': s['clip'], 'held_item': s.get('held'),
                'alone': alone_frac >= 0.999, 'alone_fraction': round(alone_frac, 2), 'company': who,
            }
            if s['kind'] == 'stay':
                area = w.area_at(s['pos'])
                o.update({'marker': s['marker'], 'target': s['target'], 'pos': r2(s['pos'], 3), 'yaw': r2(s['yaw'], 1),
                          'area': area, 'indoors': w.indoors(s['pos']), 'expression': s['expression']})
                beh = sch.behind(s['pos'], s['yaw'], area)
                o['facing_away_from'] = beh
                o['back_to_hiding_spot'] = bool(beh)
                o['asleep'] = s['activity'] == 'sleep'
                o['vulnerable'] = (bool(o['alone'] and beh) or s['vulnerable']) and not o['asleep']
                if o['asleep']:
                    o['note'] = ('Asleep: takes no Unease until woken by a noise within a hauntable\'s '
                                 'noise_radius_m (wakes at the nervous stage).')
                if s.get('note'):
                    o['note'] = s['note'] + (' ' + o['note'] if o.get('note') else '')
                if s.get('witness_view'):
                    o['witness_view'] = s['witness_view']
            else:
                pts = s['route']
                dark = sch.darkness(pts) if cyc.phase(s['start']) in ('dusk', 'night', 'dawn') else []
                near_h = sch.near_route(pts, [h for h in hauntables if h['pos']], HAUNT_NEAR_ROUTE)
                near_hide = sch.near_route(pts, sch.hiding, 5.0)
                crosses = []
                bx0, bz0, bx1, bz1 = w.structures['bridge']['footprint']
                if any(bx0 <= p[0] <= bx1 + 1 and bz0 <= p[2] <= bz1 + 1 for _, p in sample_polyline(pts, 0.5)):
                    crosses.append('bridge')
                o.update({'from': out_steps[-1]['marker'] if out_steps and out_steps[-1].get('marker') else
                          (out_steps[-1]['activity'] if out_steps else None),
                          'route': [r2(p, 2) for p in pts], 'ladder_waypoints': s['ladder'],
                          'length_m': round(s['length'], 1), 'speed_mps': round(s['speed'], 3),
                          'light': s.get('light') or (s.get('held') if s.get('held') in ('candle', 'lantern') else None),
                          'dark_stretches_m': dark, 'dark_m': round(sum(b - a for a, b in dark), 1),
                          'crosses': crosses,
                          'hauntables_on_route': [h['id'] for h, _ in sorted(near_h, key=lambda t: t[1])],
                          'hiding_spots_on_route': [m['id'] for m, _ in near_hide],
                          'facing_away_from': 'moving: everything already passed is behind'})
                o['vulnerable'] = bool(o['alone_fraction'] >= 0.5 and (dark or crosses))
                for h, _ in near_h:
                    route_hauntables[h['id']] = h
            out_steps.append(o)
        # home + route hauntables (slice levels 1-2) and fear objects
        home_h = [h for h in hauntables if h['owner'] == home and h['source'] != 'carried']
        carried = [h for h in hauntables if h.get('carried_by') == vid]
        home_l12 = sorted({h['id'] for h in home_h if h['level'] <= 2})
        route_l12 = sorted({hid for hid, h in route_hauntables.items() if h['level'] <= 2 and h['owner'] != home}
                           | {h['id'] for h in carried})
        fear = v['fear']
        fear_objs = sorted({h['id'] for h in home_h + list(route_hauntables.values()) + carried if fear and fear in h['fears']})
        fear_l12 = sorted({hid for hid in fear_objs if hmap[hid]['level'] <= 2})
        checks[vid] = {'home_level12': home_l12, 'route_level12': route_l12, 'fear_objects': fear_objs,
                       'fear_objects_level12': fear_l12,
                       'ok': len(home_l12) >= 3 and len(route_l12) >= 3 and (not fear or len(fear_objs) >= 1)}
        ch = w.chars[v['character']]
        rec = {
            'id': vid, 'name': v['name'], 'pronouns': v['pronouns'], 'role': v['role'],
            'character': v['character'], 'gltf': ch['gltf'], 'height_m': round(ch['size'][1], 2),
            'home': home, 'home_area': w.structures[home]['area'] if home in w.structures else None,
            'home_marker': f'villager_home_{vid}', 'bed': f'bed_{vid}',
            'personality': v['personality'], 'backstory': v['backstory'],
            'belief': v['belief'], 'fear': fear, 'fear_story': v.get('fear_story'),
            'fear_object': v.get('fear_object'), 'skeptic': v.get('skeptic', False),
            'nerve': v['nerve'], 'suspicion_rate': v['suspicion_rate'], 'bravery_gain': v['bravery_gain'],
            'unease_decay_per_s': v['unease_decay_per_s'],
            'default_item': v['default_item'], 'charm': v['charm'],
            'walk_speed_mps': round(ch['no_slide_speed_mps']['walk'] * WALK_SPEED_FACTOR, 3),
            'flee_speed_mps': round(ch['no_slide_speed_mps']['flee'], 3),
            'mutters': {'lines': v['mutters'], 'hint': v['mutter_hint'], **PC.MUTTER_RULES},
            'suspicious_reactions': v['reactions'],
            'on_break': v['on_break'], 'on_botch': v['on_botch'],
            'schedule': out_steps, 'tuning': True,
        }
        if v['role'] == 'witness':
            rec['witness'] = v['witness']
        villagers.append(rec)

    nodes = build_nodes(w)
    fx = build_fx(w, nav)
    doc = {
        'name': 'millbrook', 'version': 1, 'generator': 'blender/scripts/build_population.py (lib_population.py)',
        'layout': 'res://assets/levels/millbrook_layout.json',
        'fragments': 'res://assets/data/memory_fragments.json',
        'units': 'metres, Godot axes (x east, y up, z south); yaw = Godot rotation.y in degrees (0 faces +Z); '
                 'hours are clock hours, t is the day/night cycle position from the layout (lighting.cycle)',
        'tuning_note': 'Every gameplay number here is a placeholder (sections carry "tuning": true); Scott tunes feel.',
        'cycle': {'length_s': cyc.length, 'keys': w.layout['lighting']['cycle']['keys'],
                  'schedule_starts': '17:00', 'night_seconds_per_hour': round(cyc.seconds(21, 22), 1),
                  'day_seconds_per_hour': round(cyc.seconds(10, 11), 1)},
        'scare_rules': PC.SCARE_RULES,
        'villagers': villagers,
        'hauntables': hauntables,
        'hauntable_kinds': PC.HAUNT_KINDS,
        'nodes': nodes,
        'town_memory': PC.TOWN_MEMORY,
        'fx': fx,
        'checks': checks,
    }
    frag = build_fragments(w)
    return doc, frag, all_steps


# ============================================================================== nodes
def build_nodes(w):
    out = []
    graves = [m for m in w.layout['markers'] if m['kind'] == 'grave_node']
    for m in w.layout['markers']:
        if m['kind'] == 'weed_node':
            near_grave = any(math.dist(m['pos'], g['pos']) < 2.6 for g in graves)
            kind = 'grave_weeds' if near_grave else 'fiber_grass'
        elif m['kind'] == 'grave_node':
            kind = 'grave_dirt'
        elif m['kind'] == 'ore_node':
            kind = {'eerie_ore': 'eerie_ore_vein', 'spectral_stone': 'spectral_stone_vein', 'iron_ore': 'iron_ore_vein'}[m['block']]
        else:
            continue
        spec = dict(PC.NODE_KINDS[kind])
        if spec.get('block') and spec['block'] in w.blocks:     # voxel nodes drop what blocks.json says
            spec['yields'] = w.blocks[spec['block']]['drops']
        n = {'id': m['id'].replace('_node_', '_') if m['kind'] != 'ore_node' else m['id'], 'kind': kind,
             'marker': m['id'], 'pos': r2(m['pos'], 3), 'area': m['area'], 'tool': spec['tool'], 'tier': spec['tier'],
             'block': m.get('block') or spec.get('block'), 'hits': spec['hits'], 'yields': spec['yields'],
             'regrow': spec['regrow'], 'fragment_chance': spec['fragment_chance']}
        if m.get('cell'):
            n['cell'] = m['cell']
            n['face'] = m['face']
        if m.get('grave'):
            n['grave'] = m['grave']
        if kind == 'grave_dirt' and m.get('grave'):
            n['yields'] = spec['yields'] + [{'item': 'buried_trinket', 'min': 1, 'max': 1, 'chance': 0.04,
                                              'note': 'marked graves keep a little more'}]
        out.append(n)
    return {'tuning': True, 'kinds': PC.NODE_KINDS, 'list': out}


# ============================================================================== effects
def build_fx(w, nav):
    L = w.layout
    fx = []
    # chimney smoke: the highest stone column of each house with a hearth
    hearths = {m['owner']: m for m in L['markers'] if m['kind'] == 'hearth'}
    for sid, hm in hearths.items():
        s = w.structures[sid]
        x0, z0, x1, z1 = s['footprint']
        best = None
        for x in range(x0 - 1, x1 + 2):
            for z in range(z0 - 1, z1 + 2):
                col = w.W[x, :, z]
                ys = np.nonzero(col)[0]
                if not len(ys):
                    continue
                y = int(ys.max())
                b = w.bindex[int(col[y])]['id']
                if b in ('cobblestone', 'stone', 'mossy_stone_bricks') and y > s['anchor'][1] + 3:
                    if best is None or y > best[0]:
                        best = (y, x, z)
        if best:
            y, x, z = best
            fx.append(dict(id=f'chimney_smoke_{sid}', type='chimney_smoke', pos=[x + 0.5, y + 1.0, z + 0.5],
                           owner=sid, resident=s['resident'], when='hearth_lit', moods=['dusk', 'night', 'dawn', 'day'],
                           **PC.FX_PARAMS['chimney_smoke']))
    # flames and glows bound to prop nodes (Godot finds the FX_/LIGHT_ nodes by prefix)
    fx.append(dict(id='hearth_flames', type='hearth_flame', attach={'props': ['hearth'], 'node_prefix': 'FX_flame'},
                   when='hearth_lit', **PC.FX_PARAMS['hearth_flame']))
    fx.append(dict(id='candle_flames', type='candle_flame',
                   attach={'props': ['candle', 'candle_cluster', 'grave_candles', 'oil_lamp', 'hearth'],
                           'node_prefix': 'FX_flame_candle', 'also': 'FX_flame_lamp'},
                   when='lit', **PC.FX_PARAMS['candle_flame']))
    fx.append(dict(id='lantern_glows', type='lantern_glow',
                   attach={'props': ['lantern_post', 'lantern_wall', 'lantern'], 'node_prefix': 'FX_flame_lantern'},
                   moods=['dusk', 'night', 'dawn'], **PC.FX_PARAMS['lantern_glow']))
    fx.append(dict(id='carried_lights', type='lantern_glow', attach={'villager_sockets': ['HELD_R', 'HELD_L'],
                   'node_prefix': 'FX_flame'}, when='carried and lit', **PC.FX_PARAMS['lantern_glow']))
    # fireflies and low mist volumes (night)
    for fid, box, count in PC.FIREFLY_ZONES:
        fx.append(dict(id=f'fireflies_{fid}', type='fireflies', box=box, count=count, moods=['dusk', 'night'],
                       **PC.FX_PARAMS['fireflies']))
    for mid, box, dens in PC.MIST_ZONES:
        fx.append(dict(id=f'mist_{mid}', type='low_mist', box=box, density=dens, moods=['night', 'dawn'],
                       **PC.FX_PARAMS['low_mist']))
    # the stream: sparkles along the surface, spray where it falls
    cells = L['water'][0]['cells']
    falls = [c for c in cells if c[5]]
    surf = {}
    for c in cells:
        if not c[5]:
            key = (c[0] // 6, c[2] // 6)
            if key not in surf or c[1] > surf[key][1]:
                surf[key] = c
    spark = [[c[0] + 0.5, c[1] + 0.92, c[2] + 0.5] for _, c in sorted(surf.items(), key=lambda t: (t[1][2], t[1][0]))]
    fx.append(dict(id='stream_sparkle', type='water_sparkle', points=spark, moods=['dusk', 'night', 'dawn', 'day'],
                   **PC.FX_PARAMS['water_sparkle']))
    # waterfall spray: the lowest waterfall cell of each fall column cluster
    groups = {}
    for c in falls:
        key = (c[0] // 4, c[2] // 4)
        if key not in groups or c[1] < groups[key][1]:
            groups[key] = c
    for k, c in sorted(groups.items(), key=lambda t: (t[1][2], t[1][0])):
        fx.append(dict(id=f'waterfall_spray_{len([f for f in fx if f["type"] == "waterfall_spray"]) + 1}',
                       type='waterfall_spray', pos=[c[0] + 0.5, c[1] + 0.2, c[2] + 0.5],
                       flow=[c[3], 0.0, c[4]], moods=['dusk', 'night', 'dawn', 'day'], **PC.FX_PARAMS['waterfall_spray']))
    # windmill sails
    sails = next(i for i in L['instances'] if i['prop'] == 'windmill_sails')
    hub = next(m for m in L['markers'] if m['kind'] == 'anim_hub')
    fx.append(dict(id='windmill_sails', type='rotate', instance=sails['id'], node='ANIM_sails', axis='local_z',
                   hub=hub['pos'], moods=['dusk', 'night', 'dawn', 'day'], **PC.FX_PARAMS['windmill_sails']))
    sign = [i for i in L['instances'] if i['prop'] == 'tavern_sign']
    for s in sign:
        fx.append(dict(id='tavern_sign_swing', type='swing', instance=s['id'], node='ANIM_sign', axis='local_x',
                       amplitude_deg=6.0, period_s=3.2, tuning=True))
    # violet wisps from exposed eerie ore and the crystal clusters
    for m in L['markers']:
        if m['kind'] == 'ore_node' and m['block'] == 'eerie_ore':
            c = m['cell']
            f = m['face']
            fx.append(dict(id=f'ore_wisps_{m["id"]}', type='ore_wisps', node=m['id'],
                           pos=[c[0] + 0.5 + 0.55 * f[0], c[1] + 0.5 + 0.55 * f[1], c[2] + 0.5 + 0.55 * f[2]],
                           moods=['dusk', 'night', 'dawn'], **PC.FX_PARAMS['ore_wisps']))
    for i in L['instances']:
        if i['prop'] == 'eerie_crystal_cluster':
            fx.append(dict(id=f'ore_wisps_{i["id"]}', type='ore_wisps', instance=i['id'],
                           pos=[i['pos'][0], i['pos'][1] + 0.9, i['pos'][2]], moods=['dusk', 'night', 'dawn'],
                           **PC.FX_PARAMS['ore_wisps']))
    # mausoleum doorway glow
    door = w.markers['door_mausoleum_front']
    portal = next(i for i in L['instances'] if i['prop'] == 'mausoleum_portal')
    fx.append(dict(id='mausoleum_glow', type='portal_glow', instance=portal['id'], node='FX_wisp',
                   pos=[door['pos'][0] + 0.3, door['pos'][1] + 1.1, door['pos'][2]],
                   moods=['dusk', 'night', 'dawn', 'day'], **PC.FX_PARAMS['portal_glow']))
    # gravestone wisps (FX_wisp nodes on the task1 gravestones)
    fx.append(dict(id='gravestone_wisps', type='grave_wisps',
                   attach={'props': ['gravestone_round', 'gravestone_cross', 'gravestone_spiral', 'gravestone_celtic'],
                           'node_prefix': 'FX_wisp'}, moods=['night'], **PC.FX_PARAMS['grave_wisps']))
    # worker ghosts idling at the graves (ambience only in the slice)
    for wg in PC.WORKER_GHOSTS:
        g = w.markers[wg['grave']]
        fx.append(dict(id=f'worker_{wg["character"].split("_")[1]}', type='worker_ghost', character=wg['character'],
                       gltf=f'res://assets/characters/{wg["character"]}.gltf', grave=wg['grave'],
                       pos=[g['pos'][0] + wg['offset'][0], g['pos'][1] + 0.35, g['pos'][2] + wg['offset'][1]],
                       yaw=wg['yaw'], animation=wg['clip'], wander_radius_m=wg['wander'], bob_m=0.08, bob_period_s=2.4,
                       ambience_only=True, moods=['dusk', 'night', 'dawn'], tuning=True))
    return {'tuning': True, 'note': 'Godot builds GPUParticles3D / meshes from these; `attach` entries bind to prop '
                                    'nodes by prefix on every instance of the listed props.', 'list': fx}


# ============================================================================== memory fragments
def build_fragments(w):
    blocks = w.blocks
    frags = []
    owners = {o['id']: o for o in PC.OWNERS}
    for f in PC.FRAGMENTS:
        o = owners[f['owner']]
        frags.append({'id': f['id'], 'text': f['text'], 'owner': f['owner'], 'owner_name': o['name'],
                      'set': o.get('set'), 'emotion': f['emotion'], 'source': f['source'],
                      'vignette': f['vignette']})
    # drop tables: every block with a fragment_chance gets the fragments whose source lists it
    tables = {}
    for bid, b in sorted(blocks.items(), key=lambda t: t[1]['index']):
        if not b.get('fragment_chance'):
            continue
        entries = []
        for f in frags:
            src = f['source']
            if bid in src['blocks']:
                entries.append({'fragment': f['id'], 'weight': src.get('weight', 1.0), 'areas': src.get('areas', [])})
        tables[bid] = {'chance': b['fragment_chance'], 'entries': entries}
    sets = []
    for o in PC.OWNERS:
        if o.get('set'):
            sets.append({'id': o['set'], 'owner': o['id'], 'name': o['name'], 'pronouns': o['pronouns'],
                         'fragments': [f['id'] for f in frags if f['owner'] == o['id']],
                         'unlocks_resident': o['resident'], 'resident_skill': o['skill'], 'grave_wish': o['grave_wish']})
    return {
        'version': 1, 'generator': 'blender/scripts/build_population.py (lib_population_content.py)',
        'note': 'Memory fragments drop when natural blocks are mined. Roll the block\'s `chance`; on a hit pick from '
                'its table by weight among fragments not yet collected, x3 weight for entries whose `areas` contain '
                'the area the block was mined in (an empty `areas` list means anywhere). If every fragment of the '
                'table is collected, drop nothing (or a duplicate as crafting material, task5\'s choice).',
        'tuning': True,
        'owners': PC.OWNERS,
        'sets': sets,
        'fragments': frags,
        'drop_tables': tables,
        'journal': PC.JOURNAL,
    }


def write(doc, frag):
    os.makedirs(os.path.dirname(OUT_FRAG), exist_ok=True)
    with open(OUT_POP, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    with open(OUT_FRAG, 'w', encoding='utf-8') as f:
        json.dump(frag, f, indent=1, ensure_ascii=False)
