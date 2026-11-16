"""Render every block as a cube on a grey sheet (like block_palette.png), studio and night.

blender -b --factory-startup -P blender/scripts/preview_blocks.py
-> renders/task1/blocks_studio.png, renders/task1/blocks_night.png
"""
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_render as LR  # noqa: E402
import lib_voxel as LV  # noqa: E402

ROOT = LV.ROOT
OUT = os.path.join(ROOT, 'renders', 'task1')


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    blocks = [b for b in LV.blocks_doc()['blocks'] if b['id'] != 'air']
    cols = 7
    objs = []
    for i, b in enumerate(blocks):
        r, c = divmod(i, cols)
        g = np.full((1, 1, 1), b['id'], dtype=object)
        ob = LV.build_voxel_mesh('blk_' + b['id'], g)
        ob.location = (c * 1.9, r * 2.2, 0)  # rows go back (+Y) so nearer rows don't hide farther ones
        objs.append(ob)
    LR.setup_scene(res=(1600, 1000), samples=32, line=1.3)
    LR.ground(80, -0.001)
    for mood in ('studio', 'night'):
        LR.set_mood(mood)
        LR.frame_camera(objs, direction=(-0.55, -1.0, 0.9), margin=1.05)
        LR.render(os.path.join(OUT, f'blocks_{mood}.png'))
    print('DONE')


main()
