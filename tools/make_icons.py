"""Item icons for the hotbar and inventory (task5), painted with Pillow + numpy.

Blocks: a small isometric cube built from the block atlas tiles (top + two shaded sides).
Materials: simple painted shapes with an ink outline in the game palette.
Tools are rendered from the glTFs by blender/scripts/render_icons.py.

    python tools/make_icons.py            -> assets/ui/icons/<item>.png (96x96, transparent)
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'assets', 'ui', 'icons')
S = 96
INK = (28, 20, 44, 255)


def atlas_tiles():
    b = json.load(open(os.path.join(ROOT, 'assets', 'blocks', 'blocks.json')))
    atlas = Image.open(os.path.join(ROOT, 'assets', 'blocks', 'blocks_atlas.png')).convert('RGBA')
    cols = b['atlas']['columns']
    ts = b['tile_size']

    def tile(i):
        x, y = (i % cols) * ts, (i // cols) * ts
        return atlas.crop((x, y, x + ts, y + ts))
    return {bl['id']: bl for bl in b['blocks']}, tile


def warp(img, quad, size):
    """Map the square `img` onto quad (4 points: tl, tr, br, bl) in a size x size canvas."""
    w, h = img.size
    # PIL QUAD transform maps output quad -> input rect; we need the inverse, so use perspective coeffs.
    coeffs = find_coeffs(quad, [(0, 0), (w, 0), (w, h), (0, h)])
    return img.transform((size, size), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def find_coeffs(pa, pb):
    m = []
    for p1, p2 in zip(pa, pb):
        m.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
        m.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])
    A = np.array(m, dtype=float)
    B = np.array(pb, dtype=float).reshape(8)
    res = np.linalg.solve(A, B)
    return res.tolist()


def shade(img, k):
    a = np.asarray(img).astype(float)
    a[..., :3] *= k
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def cube_icon(top, left, right):
    c = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    cx, top_y, half, edge = S / 2, 10, 38, 40
    t = [(cx, top_y), (cx + half, top_y + half * 0.55), (cx, top_y + half * 1.1), (cx - half, top_y + half * 0.55)]
    l = [t[3], t[2], (t[2][0], t[2][1] + edge), (t[3][0], t[3][1] + edge)]
    r = [t[2], t[1], (t[1][0], t[1][1] + edge), (t[2][0], t[2][1] + edge)]
    for img, quad, k in ((top, t, 1.0), (left, l, 0.78), (right, r, 0.6)):
        layer = warp(shade(img, k), quad, S)
        c = Image.alpha_composite(c, layer)
    d = ImageDraw.Draw(c)
    for poly in (t, l, r):
        d.line(poly + [poly[0]], fill=INK, width=2)
    return c


def outline(img, width=3):
    a = img.split()[3]
    grow = a.filter(ImageFilter.MaxFilter(width * 2 + 1))
    base = Image.new('RGBA', img.size, INK)
    base.putalpha(grow)
    return Image.alpha_composite(base, img)


def canvas():
    return Image.new('RGBA', (S, S), (0, 0, 0, 0))


def material_icon(item):
    c = canvas()
    d = ImageDraw.Draw(c)
    if item == 'wood':
        for i, (x, y) in enumerate([(20, 52), (44, 40), (30, 26)]):
            d.rounded_rectangle((x, y, x + 46, y + 18), 8, fill=(132, 88, 52, 255))
            d.ellipse((x + 34, y, x + 52, y + 18), fill=(196, 150, 96, 255))
            d.ellipse((x + 39, y + 5, x + 47, y + 13), fill=(150, 104, 62, 255))
    elif item == 'fiber':
        for i in range(9):
            a = -0.6 + i * 0.15
            x0, y0 = 48, 84
            x1, y1 = x0 + math.sin(a) * 60, y0 - math.cos(a) * 66
            d.line((x0, y0, (x0 + x1) / 2 + 6, (y0 + y1) / 2, x1, y1), fill=(150, 180, 90, 255), width=4)
        d.rectangle((38, 62, 58, 70), fill=(186, 150, 90, 255))
    elif item == 'grave_moss':
        for (x, y, r) in [(30, 50, 18), (54, 44, 20), (46, 62, 18), (66, 60, 14)]:
            d.ellipse((x - r, y - r, x + r, y + r), fill=(84, 128, 74, 255))
        for (x, y) in [(36, 44), (58, 38), (50, 58)]:
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(140, 190, 110, 255))
    elif item == 'bone':
        d.rounded_rectangle((26, 42, 70, 54), 6, fill=(236, 228, 206, 255))
        for (x, y) in [(22, 40), (22, 56), (74, 40), (74, 56)]:
            d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(236, 228, 206, 255))
    elif item == 'buried_trinket':
        d.ellipse((26, 26, 70, 70), fill=(214, 170, 72, 255))
        d.ellipse((34, 34, 62, 62), fill=(240, 206, 110, 255))
        d.polygon([(48, 38), (54, 48), (48, 58), (42, 48)], fill=(150, 90, 200, 255))
        d.line((48, 26, 48, 12), fill=(170, 140, 80, 255), width=3)
    elif item == 'eerie_shard':
        for (x, h, w) in [(36, 56, 14), (52, 70, 16), (66, 44, 12)]:
            d.polygon([(x, 84 - h), (x + w / 2, 84 - h + 12), (x + w / 2, 84), (x - w / 2, 84), (x - w / 2, 84 - h + 12)],
                      fill=(160, 100, 255, 255))
            d.line((x, 84 - h + 4, x, 80), fill=(220, 190, 255, 255), width=2)
    elif item == 'iron':
        d.polygon([(18, 64), (34, 40), (78, 40), (80, 64)], fill=(120, 124, 138, 255))
        d.polygon([(34, 40), (78, 40), (70, 30), (40, 30)], fill=(170, 176, 190, 255))
    elif item == 'wheat':
        for k in (-1, 0, 1):
            x = 48 + k * 14
            d.line((48, 86, x, 24), fill=(206, 170, 80, 255), width=3)
            for j in range(5):
                y = 28 + j * 8
                d.ellipse((x - 6, y - 4, x + 2, y + 4), fill=(236, 196, 96, 255))
                d.ellipse((x - 2, y - 4, x + 6, y + 4), fill=(236, 196, 96, 255))
    elif item == 'flower':
        d.line((48, 86, 48, 46), fill=(90, 140, 70, 255), width=4)
        for i in range(6):
            a = i * math.pi / 3
            x, y = 48 + math.cos(a) * 14, 38 + math.sin(a) * 14
            d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(176, 120, 230, 255))
        d.ellipse((40, 30, 56, 46), fill=(250, 220, 110, 255))
    elif item == 'fright_essence':
        d.rounded_rectangle((34, 36, 62, 84), 12, fill=(150, 210, 255, 200))
        d.rectangle((40, 22, 56, 36), fill=(196, 160, 120, 255))
        d.ellipse((38, 52, 58, 76), fill=(170, 120, 255, 255))
    else:
        d.ellipse((24, 24, 72, 72), fill=(200, 200, 220, 255))
    return outline(c)


def main():
    os.makedirs(OUT, exist_ok=True)
    blocks, tile = atlas_tiles()
    tuning = json.load(open(os.path.join(ROOT, 'assets', 'data', 'tuning.json')))
    made = []
    for item, info in tuning['items'].items():
        if not isinstance(info, dict):
            continue
        p = os.path.join(OUT, f'{item}.png')
        if info['kind'] == 'block':
            b = blocks[info['block']]
            t = b['tiles']
            side = t.get('front', t['side'])
            img = cube_icon(tile(t['top']), tile(side), tile(t['side']))
        elif info['kind'] == 'material':
            img = material_icon(item)
        else:
            continue
        img.save(p)
        made.append(os.path.relpath(p, ROOT))
    print('\n'.join(made))


if __name__ == '__main__':
    main()
