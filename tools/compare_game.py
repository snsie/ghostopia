"""Side-by-side sheets of the in-game tour shots and the concept art (task5).

    godot --path . -- --tour              -> renders/game/tour_<name>.png
    python tools/compare_game.py          -> renders/game/compare_<name>.jpg (concept left, game right)
"""
import os
import re

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'renders', 'game')
H = 540


def views():
    src = open(os.path.join(ROOT, 'scripts', 'debug', 'tour.gd'), encoding='utf-8').read()
    return re.findall(r'\["(\w+)", "([\w/]+\.png)"', src)


def fit(im):
    return im.resize((int(im.width * H / im.height), H), Image.LANCZOS)


def main():
    for name, concept in views():
        g = os.path.join(OUT, f'tour_{name}.png')
        c = os.path.join(ROOT, 'concept', concept)
        if not (os.path.exists(g) and os.path.exists(c)):
            continue
        a, b = fit(Image.open(c).convert('RGB')), fit(Image.open(g).convert('RGB'))
        sheet = Image.new('RGB', (a.width + b.width + 12, H + 26), (24, 20, 34))
        sheet.paste(a, (0, 26))
        sheet.paste(b, (a.width + 12, 26))
        d = ImageDraw.Draw(sheet)
        d.text((8, 6), f'concept: {concept}', fill=(230, 225, 240))
        d.text((a.width + 20, 6), f'game: renders/game/tour_{name}.png', fill=(230, 225, 240))
        p = os.path.join(OUT, f'compare_{name}.jpg')
        sheet.save(p, quality=85)
        print(p)


if __name__ == '__main__':
    main()
