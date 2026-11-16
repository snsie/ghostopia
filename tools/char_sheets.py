"""Turnaround and animation-strip sheets for task2 characters (system Python + Pillow).

    python tools/char_sheets.py [name ...]      # default: every folder in renders/task2/frames/

Reads renders/task2/frames/<name>/turn_<view>.png and <clip>_<k>.png, writes
renders/task2/<name>_turnaround.png and renders/task2/<name>_anims.png (one labelled row per clip).
"""
import glob
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REN = os.path.join(ROOT, 'renders', 'task2')
FR = os.path.join(REN, 'frames')
VIEWS = ['front', 'three_quarter', 'side', 'back']


def font(size):
    for f in ('arialbd.ttf', 'arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def turnaround(name):
    ims = [Image.open(os.path.join(FR, name, f'turn_{v}.png')).convert('RGB') for v in VIEWS
           if os.path.exists(os.path.join(FR, name, f'turn_{v}.png'))]
    if not ims:
        return
    w, h = ims[0].size
    top = 34
    out = Image.new('RGB', (w * len(ims), h + top), (60, 56, 62))
    d = ImageDraw.Draw(out)
    d.text((8, 6), f'{name}: front / three-quarter / side / back', fill=(240, 236, 230), font=font(20))
    for i, im in enumerate(ims):
        out.paste(im, (i * w, top))
    out.save(os.path.join(REN, f'{name}_turnaround.png'))


def expressions(name):
    files = sorted(glob.glob(os.path.join(FR, name, 'expr_*.png')), key=os.path.getmtime)
    if not files:
        return
    ims = [Image.open(f).convert('RGB') for f in files]
    w, h = ims[0].size
    top, lab = 34, 26
    out = Image.new('RGB', (w * len(ims), h + top + lab), (60, 56, 62))
    d = ImageDraw.Draw(out)
    d.text((8, 6), f'{name}: expressions (shape keys; calm = basis)', fill=(240, 236, 230), font=font(20))
    for i, (f, im) in enumerate(zip(files, ims)):
        out.paste(im, (i * w, top))
        e = os.path.basename(f)[5:-4]
        d.text((i * w + 8, top + h + 4), e, fill=(240, 236, 230), font=font(17))
    out.save(os.path.join(REN, f'{name}_expressions.png'))


def anims(name):
    files = glob.glob(os.path.join(FR, name, '*_[0-9].png'))
    clips = {}
    for f in files:
        m = re.match(r'(.+)_(\d)\.png$', os.path.basename(f))
        if m and not m.group(1).startswith(('turn', 'expr')):
            clips.setdefault(m.group(1), {})[int(m.group(2))] = f
    if not clips:
        return
    order = sorted(clips, key=lambda c: min(os.path.getmtime(p) for p in clips[c].values()))
    sample = Image.open(next(iter(clips[order[0]].values())))
    cw, ch = sample.size
    sc = 0.6
    cw2, ch2 = int(cw * sc), int(ch * sc)
    lab = 150
    top = 34
    out = Image.new('RGB', (lab + cw2 * 8, top + ch2 * len(order)), (60, 56, 62))
    d = ImageDraw.Draw(out)
    d.text((8, 6), f'{name}: 8 frames per clip', fill=(240, 236, 230), font=font(20))
    for r, c in enumerate(order):
        y = top + r * ch2
        d.text((8, y + ch2 // 2 - 10), c, fill=(240, 236, 230), font=font(17))
        for k in range(8):
            if k in clips[c]:
                im = Image.open(clips[c][k]).convert('RGB').resize((cw2, ch2), Image.LANCZOS)
                out.paste(im, (lab + k * cw2, y))
        d.line([(0, y), (out.width, y)], fill=(90, 84, 92))
    out.save(os.path.join(REN, f'{name}_anims.png'))


def main():
    names = sys.argv[1:] or sorted(os.listdir(FR))
    for n in names:
        if os.path.isdir(os.path.join(FR, n)):
            turnaround(n)
            expressions(n)
            anims(n)
            print('sheet', n)


if __name__ == '__main__':
    main()
