"""Quick top-down preview of the generated island (no Blender): highest block per column, coloured by the
mean colour of its top atlas tile, hill-shaded, with structure footprints, markers and areas drawn on top.

python tools/island_preview.py [out.png] [--scale 4] [--slice Y]
"""
import gzip
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def main():
    args = sys.argv[1:]
    out = args[0] if args and not args[0].startswith('--') else os.path.join(ROOT, 'renders', 'task3', 'debug_topdown.png')
    scale = int(args[args.index('--scale') + 1]) if '--scale' in args else 4
    sl = int(args[args.index('--slice') + 1]) if '--slice' in args else None
    lay = json.load(open(os.path.join(ROOT, 'assets', 'levels', 'millbrook_layout.json')))
    sx, sy, sz = lay['world']['size']
    raw = gzip.decompress(open(os.path.join(ROOT, 'assets', 'levels', 'millbrook_voxels.bin'), 'rb').read())
    W = np.frombuffer(raw, dtype=np.uint8).reshape(sy, sz, sx).transpose(2, 0, 1)   # -> [x, y, z]
    blocks = json.load(open(os.path.join(ROOT, 'assets', 'blocks', 'blocks.json')))
    atlas = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'blocks', 'blocks_atlas.png')).convert('RGBA')).astype(float)
    cols = blocks['atlas']['columns']
    col = np.zeros((256, 3))
    for b in blocks['blocks']:
        if 'tiles' not in b or not b['tiles']:
            continue
        t = b['tiles'].get('top', b['tiles'].get('side'))
        r, c = divmod(t, cols)
        tile = atlas[r * 64:(r + 1) * 64, c * 64:(c + 1) * 64]
        a = tile[..., 3:4] / 255
        col[b['index']] = (tile[..., :3] * a).sum((0, 1)) / max(1e-6, a.sum())
    if sl is not None:
        Wv = W[:, :sl + 1, :]
    else:
        Wv = W
    nz = Wv != 0
    top = np.where(nz.any(1), Wv.shape[1] - 1 - np.argmax(nz[:, ::-1, :], axis=1), -1)
    blk = np.take_along_axis(Wv, np.clip(top, 0, None)[:, None, :], axis=1)[:, 0, :]
    img = col[blk]
    shade = np.clip(0.55 + (top - 10) / 40.0, 0.35, 1.2)
    gx = np.gradient(top.astype(float), axis=0)
    gz = np.gradient(top.astype(float), axis=1)
    shade = shade * np.clip(1 - 0.12 * gx - 0.12 * gz, 0.6, 1.3)
    img = np.clip(img * shade[..., None], 0, 255)
    img[top < 0] = (20, 12, 40)
    im = Image.fromarray(img.transpose(1, 0, 2).astype(np.uint8)).resize((sx * scale, sz * scale), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for a in lay['areas']:
        if a['id'] == 'open_plains':
            continue
        x0, z0, x1, z1 = a['rect']
        d.rectangle([x0 * scale, z0 * scale, x1 * scale, z1 * scale], outline=(255, 255, 0))
        d.text((x0 * scale + 2, z0 * scale + 2), a['name'], fill=(255, 255, 0))
    kc = {'player_start': (255, 0, 0), 'hiding_spot': (0, 255, 255), 'ore_node': (200, 80, 255), 'grave_node': (120, 60, 20),
          'weed_node': (0, 200, 0), 'shelter': (255, 255, 255), 'wander': (255, 160, 0), 'work': (255, 0, 255),
          'villager_home': (0, 0, 255)}
    for m in lay['markers']:
        c = kc.get(m['kind'])
        if c:
            x, z = m['pos'][0] * scale, m['pos'][2] * scale
            d.ellipse([x - 3, z - 3, x + 3, z + 3], fill=c)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out)
    print(out)


if __name__ == '__main__':
    main()
