"""Numpy texture painting: noise, cells, bricks, shading from height, normal maps, PNG I/O.

Runs in Blender's bundled Python and in system Python (numpy only, no PIL needed).
Conventions: images are float arrays (H, W, C) in 0..1, row 0 = TOP of the image.
Light comes from the top-left, as on the concept sheets.
"""
import math
import struct
import zlib

import numpy as np

# ---------------------------------------------------------------- palette (style block)
INK = np.array([0.16, 0.11, 0.18])          # dark violet-brown ink line
GHOST_WHITE = np.array([0.94, 0.96, 1.0])
ICE_BLUE = np.array([0.62, 0.86, 1.0])
VIOLET = np.array([0.62, 0.34, 0.95])
TEAL = np.array([0.35, 0.95, 0.90])
EMBER = np.array([1.0, 0.58, 0.18])


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def rgb(r, g, b):
    return np.array([r, g, b]) / 255.0


# ---------------------------------------------------------------- PNG I/O
def save_png(path, img):
    """img: float (H,W,3|4) 0..1 or uint8. Writes 8-bit RGB/RGBA PNG."""
    a = np.asarray(img)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    h, w, c = a.shape
    ctype = {3: 2, 4: 6}[c]
    raw = b''.join(b'\x00' + a[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(data)


def load_png(path):
    """Minimal PNG reader for 8-bit RGB/RGBA non-interlaced files (what save_png writes)."""
    with open(path, 'rb') as f:
        d = f.read()
    pos, idat = 8, b''
    while pos < len(d):
        n = struct.unpack('>I', d[pos:pos + 4])[0]
        t = d[pos + 4:pos + 8]
        body = d[pos + 8:pos + 8 + n]
        if t == b'IHDR':
            w, h, bd, ct = struct.unpack('>IIBB', body[:10])
        elif t == b'IDAT':
            idat += body
        pos += 12 + n
    c = {2: 3, 6: 4, 0: 1}[ct]
    raw = zlib.decompress(idat)
    stride = w * c
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    i = 0
    for y in range(h):
        ft = raw[i]
        line = np.frombuffer(raw[i + 1:i + 1 + stride], np.uint8).astype(np.int32)
        i += 1 + stride
        if ft == 0:
            cur = line
        elif ft == 2:
            cur = (line + prev) & 255
        else:
            cur = np.zeros(stride, np.int32)
            for x in range(stride):
                left = cur[x - c] if x >= c else 0
                up = prev[x]
                ul = prev[x - c] if x >= c else 0
                if ft == 1:
                    p = left
                elif ft == 3:
                    p = (left + up) // 2
                else:
                    pa, pb, pc = abs(up - ul), abs(left - ul), abs(left + up - 2 * ul)
                    p = left if pa <= pb and pa <= pc else (up if pb <= pc else ul)
                cur[x] = (line[x] + p) & 255
        out[y] = cur
        prev = cur
    return out.reshape(h, w, c).astype(np.float32) / 255.0


# ---------------------------------------------------------------- noise and cells
def value_noise(size, cells, seed, octaves=3, persistence=0.5, tile=True):
    """Tileable fractal value noise in 0..1. size=(h,w) or int, cells = base grid cells."""
    if isinstance(size, int):
        size = (size, size)
    h, w = size
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        grid = rng.random((c, c))
        ys = np.arange(h) * c / h
        xs = np.arange(w) * c / w
        y0 = np.floor(ys).astype(int)
        x0 = np.floor(xs).astype(int)
        fy = ys - y0
        fx = xs - x0
        fy = fy * fy * (3 - 2 * fy)
        fx = fx * fx * (3 - 2 * fx)
        y1 = (y0 + 1) % c
        x1 = (x0 + 1) % c
        a = grid[y0][:, x0]
        b = grid[y0][:, x1]
        cc = grid[y1][:, x0]
        d = grid[y1][:, x1]
        top = a + (b - a) * fx[None, :]
        bot = cc + (d - cc) * fx[None, :]
        out += amp * (top + (bot - top) * fy[:, None])
        tot += amp
        amp *= persistence
    return out / tot


def voronoi(size, n, seed, aspect=(1.0, 1.0), points=None):
    """Tileable Voronoi. Returns f1, f2 (pixel distances), idx (cell id per pixel), points."""
    if isinstance(size, int):
        size = (size, size)
    h, w = size
    rng = np.random.default_rng(seed)
    if points is None:
        points = rng.random((n, 2)) * [h, w]
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    best1 = np.full((h, w), 1e9)
    best2 = np.full((h, w), 1e9)
    idx = np.zeros((h, w), int)
    for i, (py, px) in enumerate(points):
        dy = np.abs(yy - py)
        dx = np.abs(xx - px)
        dy = np.minimum(dy, h - dy) * aspect[0]
        dx = np.minimum(dx, w - dx) * aspect[1]
        d = np.sqrt(dy * dy + dx * dx)
        m1 = d < best1
        best2 = np.where(m1, best1, np.minimum(best2, d))
        idx = np.where(m1, i, idx)
        best1 = np.where(m1, d, best1)
    return best1, best2, idx, points


def bricks(size, rows, cols, seed, offset=0.5, jitter=0.15, mortar=1.5):
    """Running-bond bricks. Returns edge distance (px), brick id, row id."""
    if isinstance(size, int):
        size = (size, size)
    h, w = size
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    rh = h / rows
    row = np.floor(yy / rh).astype(int)
    fy = yy - row * rh
    # per-row random widths
    edge = np.zeros((h, w))
    bid = np.zeros((h, w), int)
    for r in range(rows):
        bw = w / cols
        cuts = [(k + (offset if r % 2 else 0) + rng.uniform(-jitter, jitter)) * bw for k in range(cols + 1)]
        cuts = sorted(c % w for c in cuts)
        m = row == r
        x = xx[m]
        # distance to nearest cut (wrapping)
        dist = np.full(x.shape, 1e9)
        which = np.zeros(x.shape, int)
        for ci, c in enumerate(cuts):
            dd = np.abs(x - c)
            dd = np.minimum(dd, w - dd)
            dist = np.minimum(dist, dd)
        for ci, c in enumerate(cuts):
            which += (x >= c)
        which = which % len(cuts)
        dy = np.minimum(fy[m], rh - fy[m])
        edge[m] = np.minimum(dist, dy)
        bid[m] = r * 100 + which
    return edge, bid, row


def ramp(v, stops):
    """Map scalar field v (0..1) through colour stops [(pos, rgb), ...]."""
    v = np.clip(v, 0, 1)
    pos = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops])
    out = np.zeros(v.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(v, pos, cols[:, c])
    return out


def per_id_random(idx, seed, lo=0.0, hi=1.0):
    rng = np.random.default_rng(seed)
    vals = rng.uniform(lo, hi, int(idx.max()) + 1)
    return vals[idx]


def posterize(v, levels):
    return np.round(v * levels) / levels


# ---------------------------------------------------------------- shading
def shade_from_height(h, strength=4.0, wrap=True):
    """Top-left lit relief term in about -1..1."""
    if wrap:
        dx = np.roll(h, -1, 1) - np.roll(h, 1, 1)
        dy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    else:
        p = np.pad(h, 1, mode='edge')
        dx = p[1:-1, 2:] - p[1:-1, :-2]
        dy = p[2:, 1:-1] - p[:-2, 1:-1]
    return np.clip((dx + dy) * strength, -1, 1)


def apply_shade(col, h, strength=4.0, light=0.35, dark=0.45, wrap=True):
    s = shade_from_height(h, strength, wrap)
    lit = np.clip(s, 0, 1)[..., None]
    sh = np.clip(-s, 0, 1)[..., None]
    col = col * (1 + light * lit)
    col = col * (1 - dark * sh)
    return col


def normal_from_height(h, strength=3.0, wrap=True):
    """Tangent-space normal (OpenGL +Y up), returns RGB 0..1. Image row 0 is the top (= +V)."""
    if wrap:
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
        dy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * 0.5  # +Y = up the image
    else:
        p = np.pad(h, 1, mode='edge')
        dx = (p[1:-1, 2:] - p[1:-1, :-2]) * 0.5
        dy = (p[:-2, 1:-1] - p[2:, 1:-1]) * 0.5
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], -1)


def blur(a, r=1, wrap=True):
    """Box blur radius r (cheap, separable)."""
    out = a.astype(float)
    for axis in (0, 1):
        acc = np.zeros_like(out)
        for k in range(-r, r + 1):
            if wrap:
                acc += np.roll(out, k, axis)
            else:
                pad = [(0, 0)] * out.ndim
                pad[axis] = (r, r)
                p = np.pad(out, pad, mode='edge')
                sl = [slice(None)] * out.ndim
                sl[axis] = slice(r + k, r + k + out.shape[axis])
                acc += p[tuple(sl)]
        out = acc / (2 * r + 1)
    return out


# ---------------------------------------------------------------- drawing
def grid(size):
    if isinstance(size, int):
        size = (size, size)
    return np.mgrid[0:size[0], 0:size[1]].astype(float)


def disk_mask(size, cy, cx, r, soft=0.8):
    yy, xx = grid(size)
    d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    return np.clip((r - d) / soft + 0.5, 0, 1)


def ellipse_mask(size, cy, cx, ry, rx, soft=0.8):
    yy, xx = grid(size)
    d = np.sqrt(((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2)
    return np.clip((1 - d) * min(ry, rx) / soft + 0.5, 0, 1)


def seg_dist(size, p0, p1):
    yy, xx = grid(size)
    (y0, x0), (y1, x1) = p0, p1
    vy, vx = y1 - y0, x1 - x0
    L = vy * vy + vx * vx + 1e-9
    t = np.clip(((yy - y0) * vy + (xx - x0) * vx) / L, 0, 1)
    py, px = y0 + t * vy, x0 + t * vx
    return np.sqrt((yy - py) ** 2 + (xx - px) ** 2)


def line_mask(size, p0, p1, width, soft=0.7):
    return np.clip((width * 0.5 - seg_dist(size, p0, p1)) / soft + 0.5, 0, 1)


def polyline_mask(size, pts, width, soft=0.7):
    m = np.zeros(size if isinstance(size, tuple) else (size, size))
    for a, b in zip(pts[:-1], pts[1:]):
        m = np.maximum(m, line_mask(size, a, b, width, soft))
    return m


def poly_mask(size, pts):
    """Fill a polygon (list of (y,x)) with even-odd rule."""
    yy, xx = grid(size)
    inside = np.zeros(yy.shape, bool)
    n = len(pts)
    for i in range(n):
        y0, x0 = pts[i]
        y1, x1 = pts[(i + 1) % n]
        cond = ((y0 > yy) != (y1 > yy))
        xint = (x1 - x0) * (yy - y0) / (y1 - y0 + 1e-12) + x0
        inside ^= cond & (xx < xint)
    return inside.astype(float)


def spiral_mask(size, cy, cx, r, turns=2.2, width=1.6):
    pts = []
    steps = 80
    for i in range(steps + 1):
        t = i / steps
        a = t * turns * 2 * math.pi
        rr = r * t
        pts.append((cy + rr * math.sin(a), cx + rr * math.cos(a)))
    return polyline_mask(size, pts, width)


def stamp(dst, mask, color, alpha=1.0):
    m = np.clip(mask * alpha, 0, 1)[..., None]
    return dst * (1 - m) + np.asarray(color) * m


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- tile finishing (blocks)
def bevel_tile(col, height, seed, inset=2.5, bevel=5.0, ink=0.55, rim_light=0.22, rim_dark=0.35):
    """Bake the hand-painted cube bevel into a block face tile.

    Lighter top-left edge, darker bottom-right edge, irregular slight inset, light ink rim.
    Returns new colour and height.
    """
    h, w = height.shape
    yy, xx = grid((h, w))
    n = value_noise((h, w), 6, seed, 2)
    d_top = yy + (n - 0.5) * inset
    d_left = xx + (n - 0.5) * inset
    d_bot = (h - 1 - yy) + (0.5 - n) * inset
    d_right = (w - 1 - xx) + (0.5 - n) * inset
    d = np.minimum(np.minimum(d_top, d_left), np.minimum(d_bot, d_right))
    fall = np.clip(d / bevel, 0, 1)
    fall = 1 - (1 - fall) ** 2
    height = height * (0.35 + 0.65 * fall) + 0.25 * fall
    tl = np.clip(1 - np.minimum(d_top, d_left) / bevel, 0, 1)
    br = np.clip(1 - np.minimum(d_bot, d_right) / bevel, 0, 1)
    col = col * (1 + rim_light * tl[..., None]) * (1 - rim_dark * br[..., None])
    rim = np.clip(1.6 - d, 0, 1)[..., None]
    col = col * (1 - rim * ink) + INK * rim * ink
    return np.clip(col, 0, 1), height
