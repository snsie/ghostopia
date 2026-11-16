# Task 3 report: the empty island (vertical slice)

## Done

- **Island generator** (`blender/scripts/lib_island.py`, pure numpy, seeded; `build_island.py` drives it):
  - **Shape:** a 192 × 48 × 192 voxel world holding a round-ish floating island (radius 84 ± 4).
    - The rim crumbles: columns drop and vanish near the edge, and 260 floating cubes drift past it.
    - Underneath is a deep craggy keel of stone and spectral stone with violet eerie-ore streaks.
  - **Hand layout shaped with noise:**
    - Graveyard plateau in the west (y 27) with two terraces and a cliff to the void.
    - North highland (y 24) terracing down to the village plateau (y 20).
    - Windmill rise (y 26) on its south edge.
    - Rolling plains, eight forest clumps of voxel oaks, and lone trees.
  - **Strata:** grass, then 3–4 dirt, then stone. Cliffs show stone under the grass, and spectral stone
    lies below y ≈ 9.
  - **Ore and caves:**
    - 40 iron-ore and 22 eerie-ore pockets.
    - Three small caves (graveyard hill, mill rise, a south-forest sinkhole), each ending in a chamber with
      ore on its walls.
  - **The stream:** runs from the north rim to the south rim, 3 wide and 2 deep, with sand banks.
    - Two waterfalls come down from the highland and two small drops follow south of the village; then it
      falls off the edge.
    - The plank bridge stands on the main path south-west of the square.
  - **Paths:** cobbled in the village, packed earth outside. Height profiles turn into stairs on the
    graveyard hill and the mill rise.
  - **Structures:** all 10 task1 blueprints are stamped at their places, rotated in steps of 90°. Their
    props, markers and rooms are transformed into world space.
  - **Dressing:**
    - Graveyard: eight graves with grave-dirt plots, candles and wilted flowers; the eerie-ore outcrop with
      crystals; the dead tree; weeds, mushrooms and the rim fence.
    - Square: well, charm board, bell, benches, barrels, and a flower ring round the well.
    - Elsewhere: 19 lantern posts, oak props, flower clumps, the fenced wheat field with the scarecrow, the
      pumpkin patch, and grain sacks and a fence at the mill.
- **Layout data** (`assets/levels/millbrook_layout.json` + `millbrook_voxels.bin`, gzip, x-z-y order):
  - **Contents:**
    - 10 structures, 507 prop instances (46 hauntable, by kind) and 223 markers.
    - Markers include `player_start`, `respawn`, 5 × `villager_home`/`bed`, chairs, hearths, 9 `work`,
      14 `wander`, doors, 28 windows, 11 `hiding_spot`, 56 `ore_node`, 11 `grave_node`, 26 `weed_node`,
      4 `shelter`, creaks and cave entrances.
    - 12 areas: Graveyard, Millbrook Square, the four cottages by owner, Tavern, Windmill, Fields, Stream,
      Open Plains.
    - 1000 stream cells with a flow vector and a waterfall flag.
    - `kill_y`.
    - Lighting presets `night`, `dusk`, `dawn`, `day` and `fading`, plus the day/night cycle keyframes
      (night gets half the cycle).
    - The `map` rect.
  - **Docs:** the schema is in README "Level data".
  - **Determinism:** plain Python and Blender write byte-identical files.
- **Blender scene:** `blender/millbrook_island.blend`.
  - Voxels are meshed in 32 × 32 chunks with hidden faces culled (about 104k faces).
  - Props are collection instances of the task1 glTFs.
  - Moods are read from the layout's own lighting presets, so the previews and Godot share one
    definition.
- **Renders** (`renders/task3/`):
  - Millbrook night/dusk/day/fading, cottage interior night/day (cutaway), mill night (cutaway),
    graveyard night/day, island overview at night.
  - A `compare_*.jpg` for each: concept left, render right.
  - `millbrook_plan.png`: top-down orthographic, 12 px/m, covering world rect [0, 0, 192, 192].
  - `layout_markers.png`: a debug map with areas and markers.
- **Tests:** `tests/test_island.gd` has 8 tests. They decompress the voxels the way the game will, then
  check:
  - the palette against `blocks.json`;
  - required markers per resident, and unique ids;
  - that every standalone prop and outdoor marker stands on open ground;
  - that the stream cells are running water;
  - the lighting presets and the cycle.
  All 15 project tests pass. The Godot import is clean.
- README "Rebuild" has the island commands, and the docs, decisions.md and issues.md are updated.

## Compared with the concept art

- **Millbrook** (`compare_millbrook_*`): the composition matches `millbrook_empty.png` for everything
  except the graveyard:
  - Tavern lower left, the stream behind it with waterfalls coming down from the mill rise.
  - Windmill top left on its rise, two cottages behind the well, Wren's cottage on the right.
  - Wheat field lower right, cobbled square with the well and charm board, lanterns on posts.
  - Night has warm windows and lantern pools under a blue-violet sky. Dusk has a peach horizon and long
    shadows. Day is pale and washed out. Fading is drained toward lavender grey.
- **Cottage interior:** the cutaway shows the cottage_a room as the concept arranges it: the hearth glowing
  on the left wall, the rocking chair on the rug, the shelf with the doll, the side table and lamp, the
  bedroom door and the bed.
- **Mill:** the front cutaway shows the millstone, grain sacks, the rocking chair and the lit window, with
  the stream to the left and a lantern post and barrels on the terrace.
- **Graveyard:** the mausoleum shows its violet portal and gargoyles. The flagged path leads to the gate
  and stairs, between the rows of graves with candles, and the eerie-ore outcrop glows violet as on the
  concept.
- **Overview vs `world_map.png`:** the same reading. It is a floating island over the void with crumbling,
  glowing cubes; the graveyard hill is upper left, the mill is at the top beside the stream, the village
  and bridge are in the centre, and the fields are to the east.

## Not done / weaker than the concept

- **The graveyard is not in the Millbrook view.** The concept paints it upper right of a north-facing view;
  the task and the world map put it in the west. That is recorded in decisions.md.
- **The world is much roomier than the paintings.** At the task's 192 × 192 size, the village fills a small
  part of the island and wide plains and forest surround it. The concept views compress everything into
  one tight scene.
- **Roofs are task1's stepped voxel stairs**, not the soft overhanging thatch. The cottage room is
  narrower than the painted one. These are task1 limits; the island stamps the blueprints as they are.
- **Mood features left to Godot:** the previews have no distance fog (an EEVEE world volume darkened
  everything), no fireflies, smoke or bloom beyond a simple post-process bloom, and no moon in most
  framings.
  - The fading mood is only a colour grade in the preview. The flickering, crumbling blocks of low
    Remembrance are game logic for task5.
- **No under-bridge hiding spot.** The bridge deck sits directly on the water, so the hiding spots are
  beside its abutments instead.
- **The drift time is approximate.** The graveyard-to-square path is ~102 m: about 46 s at 2.2 m/s, and
  less at the ghost's 2.5–4 m/s drift.
- **No builds.** There is still no main scene or export presets. The game and its Windows/macOS builds start
  in task5, as in task1 and task2. Task5 must include `assets/levels/*.json, *.bin` in the export filter.
