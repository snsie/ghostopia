"""Contact sheet with labels (system Python + Pillow).

    python tools/contact_sheet.py OUT.png --cols 6 --cell 256 [--title T] img1.png[=label] img2.png[=label] ...
    python tools/contact_sheet.py OUT.png --cols 6 --dir renders/task1/props    # all PNGs in a folder
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for f in ('arialbd.ttf', 'arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('items', nargs='*')
    ap.add_argument('--cols', type=int, default=6)
    ap.add_argument('--cell', type=int, default=256)
    ap.add_argument('--dir')
    ap.add_argument('--title', default='')
    a = ap.parse_args()
    items = list(a.items)
    if a.dir:
        items += sorted(glob.glob(os.path.join(a.dir, '*.png')))
    entries = []
    for it in items:
        path, _, label = it.partition('=')
        entries.append((path, label or os.path.splitext(os.path.basename(path))[0]))
    cols = min(a.cols, max(1, len(entries)))
    rows = (len(entries) + cols - 1) // cols
    lab = 22
    top = 40 if a.title else 0
    sheet = Image.new('RGB', (cols * a.cell, rows * (a.cell + lab) + top), (58, 52, 62))
    d = ImageDraw.Draw(sheet)
    f = font(15)
    if a.title:
        d.text((10, 8), a.title, fill=(240, 220, 150), font=font(22))
    for i, (path, label) in enumerate(entries):
        r, c = divmod(i, cols)
        im = Image.open(path).convert('RGB')
        im.thumbnail((a.cell, a.cell))
        x = c * a.cell + (a.cell - im.width) // 2
        y = top + r * (a.cell + lab)
        sheet.paste(im, (x, y))
        d.text((c * a.cell + 6, y + a.cell + 2), label, fill=(235, 235, 245), font=f)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    print('sheet', a.out, len(entries))


if __name__ == '__main__':
    main()
