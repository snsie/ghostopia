"""Top-down map of the Millbrook population over the task3 plan render: every villager's walks (dark stretches
dashed bright), stationary steps, hauntables (level 1-2 filled, level 3 hollow), nodes and worker ghosts.

python tools/population_map.py [out.png] [--crop x0,z0,x1,z1] [--scale 6] [--villager agnes]
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
POP = os.path.join(ROOT, 'assets', 'levels', 'millbrook_population.json')
LAYOUT = os.path.join(ROOT, 'assets', 'levels', 'millbrook_layout.json')
PLAN = os.path.join(ROOT, 'renders', 'task3', 'millbrook_plan.png')
COLORS = {'agnes': (196, 120, 255), 'bram': (255, 150, 60), 'wren': (255, 230, 90), 'marlow': (90, 200, 255),
          'pip': (130, 255, 150)}


def opt(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default


def main():
    out = next((a for a in sys.argv[1:] if a.endswith('.png')), os.path.join(ROOT, 'renders', 'task4', 'population_map.png'))
    crop = [float(v) for v in (opt('--crop') or '14,40,176,160').split(',')]
    scale = float(opt('--scale') or 7)
    only = opt('--villager')
    pop = json.load(open(POP, encoding='utf-8'))
    lay = json.load(open(LAYOUT, encoding='utf-8'))
    base = Image.open(PLAN).convert('RGB')
    ppm = base.width / lay['map']['world_rect'][2]
    x0, z0, x1, z1 = crop
    base = base.crop((int(x0 * ppm), int(z0 * ppm), int(x1 * ppm), int(z1 * ppm)))
    W, H = int((x1 - x0) * scale), int((z1 - z0) * scale)
    base = base.resize((W, H), Image.LANCZOS)
    base = Image.blend(base, Image.new('RGB', base.size, (20, 18, 32)), 0.55)
    d = ImageDraw.Draw(base)

    def P(p):
        return ((p[0] - x0) * scale, (p[2] - z0) * scale)

    for h in pop['hauntables']:
        if not h['pos']:
            continue
        c = (255, 120, 200) if h['level'] <= 2 else (180, 160, 200)
        x, y = P(h['pos'])
        r = 3.2
        if h['level'] <= 2:
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        else:
            d.ellipse((x - r, y - r, x + r, y + r), outline=c, width=1)
    for n in pop['nodes']['list']:
        x, y = P(n['pos'])
        d.rectangle((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=(150, 255, 230))
    for f in pop['fx']['list']:
        if f['type'] == 'worker_ghost':
            x, y = P(f['pos'])
            d.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(220, 240, 255), width=2)
    for v in pop['villagers']:
        if only and v['id'] != only:
            continue
        col = COLORS.get(v['id'], (255, 255, 255))
        for s in v['schedule']:
            if s['kind'] == 'walk':
                pts = [P(p) for p in s['route']]
                d.line(pts, fill=col, width=2)
                # dark stretches: overlay white dashes
                acc = 0.0
                seg = []
                for a, b in zip(s['route'], s['route'][1:]):
                    L = math.dist(a, b)
                    for da, db in s['dark_stretches_m']:
                        lo, hi = max(acc, da), min(acc + L, db)
                        if hi > lo and L > 0:
                            fa, fb = (lo - acc) / L, (hi - acc) / L
                            pa = [a[i] + (b[i] - a[i]) * fa for i in range(3)]
                            pb = [a[i] + (b[i] - a[i]) * fb for i in range(3)]
                            seg.append((P(pa), P(pb)))
                    acc += L
                for pa, pb in seg:
                    d.line([pa, pb], fill=(255, 255, 255), width=1)
            else:
                x, y = P(s['pos'])
                r = 4.5
                d.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=(0, 0, 0))
                a = math.radians(s['yaw'])
                d.line([(x, y), (x + math.sin(a) * 9, y + math.cos(a) * 9)], fill=(0, 0, 0), width=2)
                if s['phase'] in ('dusk', 'night'):
                    d.text((x + 6, y - 6), f'{s["start"]} {s["activity"]}', fill=col)
    # legend
    y = 6
    for vid, col in COLORS.items():
        d.rectangle((6, y, 18, y + 10), fill=col)
        d.text((22, y - 1), vid, fill=(240, 240, 240))
        y += 14
    d.text((6, y + 2), 'white = dark stretch (night)   pink dot = L1-2 hauntable   hollow = L3   teal = node',
           fill=(240, 240, 240))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    base.save(out)
    print(out, base.size)


if __name__ == '__main__':
    main()
