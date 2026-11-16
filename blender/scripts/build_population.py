"""Task 4: populate Millbrook -> population JSON + memory fragments + populated renders.

Plain Python (data only, a few seconds):
    python blender/scripts/build_population.py --json-only
Blender (data + renders/task4/* + blender/millbrook_population.blend):
    blender -b --factory-startup -P blender/scripts/build_population.py -- [--no-render] [--only millbrook,mill]
                                                                            [--moods night,day] [--res 1280x720]

Data: lib_population.py (routing, schedules, analysis) + lib_population_content.py (villagers, lines, rules,
fragments). Renders reuse the task3 island scene (build_island.blender_main) and add the villagers at their
schedule positions for each shot's hour, the worker ghosts and stand-ins for the effects.
"""
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lib_population as LP  # noqa: E402

ROOT = LP.ROOT
OUT = os.path.join(ROOT, 'renders', 'task4')


def argv():
    a = sys.argv
    return a[a.index('--') + 1:] if '--' in a else a[1:]


def report(doc, frag, steps):
    print(f'villagers {len(doc["villagers"])}, hauntables {len(doc["hauntables"])}, '
          f'nodes {len(doc["nodes"]["list"])}, fx {len(doc["fx"]["list"])}, fragments {len(frag["fragments"])}')
    for v in doc['villagers']:
        c = doc['checks'][v['id']]
        print(f'  {v["id"]:7s} home L1-2 {len(c["home_level12"])}, route L1-2 {len(c["route_level12"])}, '
              f'fear objects {len(c["fear_objects"])} (L1-2 {len(c["fear_objects_level12"])}) ok={c["ok"]}')
        for s in v['schedule']:
            extra = ''
            if s['kind'] == 'walk':
                extra = (f'{s["length_m"]:5.1f} m dark {s["dark_m"]:4.1f} m {"+".join(s["crosses"])} '
                         f'haunt {len(s["hauntables_on_route"])}')
            else:
                extra = f'{s.get("marker") or s.get("target")} behind={len(s["facing_away_from"])}'
            print(f'     {s["start"]}-{s["end"]} {s["kind"]:4s} {s["activity"]:18s} alone={str(s["alone"]):5s} '
                  f'({s["alone_fraction"]:.2f}) vuln={str(s["vulnerable"]):5s} {extra}')


def main():
    t = time.time()
    doc, frag, steps = LP.build()
    LP.write(doc, frag)
    report(doc, frag, steps)
    print(f'data written ({time.time() - t:.1f}s)')
    subprocess.call(['python', os.path.join(ROOT, 'tools', 'population_map.py')])   # renders/task4/population_map.png
    try:
        import bpy  # noqa: F401
    except ImportError:
        print('DONE (json only)')
        return
    if '--json-only' in argv():
        print('DONE')
        return
    import population_render as PR
    renders = PR.render_all(doc, steps)
    if renders:
        subprocess.call(['python', os.path.join(ROOT, 'tools', 'compare_sheets.py'), '--task', 'task4'])
    print('DONE')


main()
