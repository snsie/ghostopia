"""Side-by-side comparisons of the task3 island renders with the concept art.

python tools/compare_sheets.py   -> renders/task3/compare_<camera>_<mood>.jpg (concept left, render right)
"""
import os
import re
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'blender', 'scripts'))
OUT = os.path.join(ROOT, 'renders', 'task3')
H = 720


def cameras():
    """Read CAMERAS from build_island.py without importing Blender."""
    src = open(os.path.join(ROOT, 'blender', 'scripts', 'build_island.py'), encoding='utf-8').read()
    block = src[src.index('CAMERAS = {'):src.index('\n}\n', src.index('CAMERAS = {')) + 2]
    ns = {}
    exec(block, ns)
    return ns['CAMERAS']


def fit(im, h):
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)


def main():
    made = []
    for name, cd in cameras().items():
        for mood, concept in cd['concept'].items():
            r = os.path.join(OUT, f'{name}_{mood}.png')
            c = os.path.join(ROOT, 'concept', concept)
            if not (os.path.exists(r) and os.path.exists(c)):
                continue
            a, b = fit(Image.open(c).convert('RGB'), H), fit(Image.open(r).convert('RGB'), H)
            sheet = Image.new('RGB', (a.width + b.width + 12, H + 28), (24, 20, 34))
            sheet.paste(a, (0, 28))
            sheet.paste(b, (a.width + 12, 28))
            d = ImageDraw.Draw(sheet)
            d.text((8, 7), f'concept: {concept}', fill=(230, 225, 240))
            d.text((a.width + 20, 7), f'render: renders/task3/{name}_{mood}.png', fill=(230, 225, 240))
            p = os.path.join(OUT, f'compare_{name}_{mood}.jpg')
            sheet.save(p, quality=88)
            made.append(p)
    print('\n'.join(made))


if __name__ == '__main__':
    main()
