# Task 3: The empty island: terrain, Millbrook layout, markers, light (run 1: vertical slice)

## Mode: fully autonomous
- Don't ask questions or wait for confirmation. Make every decision yourself and record it in decisions.md.
- If something is unclear in the concept art, choose a reasonable option in the target style and continue.
- Don't wait for Blender MCP, Godot MCP or other tools to connect. Run Blender from the command line:
  `"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/scripts/<script>.py -- <args>`.
  Shell: Git Bash, never PowerShell.
- If a step fails, try another approach. If that fails too, record the problem in issues.md and move on.
- Don't stop until the task is complete. At the end write report_task3.md: what was done, what did not work.
- Look at your results (renders per mood from the concept cameras) and compare with the concept art
  before calling anything done.
- Read first: CLAUDE.md, docs/design/design-plan.md, `Ghostopia — concept art and tasks.md`,
  decisions.md (obey task1/task2 conventions), issues.md, report_task1.md, report_task2.md.

## External assets
- Everything procedural in Python; no terrain plugins, no downloaded models.

## Goal
The vertical-slice world as data Godot can build: a finite floating island of voxels (the Veil's
edges crumble into the void, as on `concept/locations/world_map.png`), with Millbrook, the windmill,
the stream and the starting graveyard placed from task1 blueprints and props, gameplay markers, and
lighting presets for every mood. No characters.

## Inputs
- `concept/locations/world_map.png` (overall layout), `concept/empty/*.png` (what each place looks
  like with nobody in it; `millbrook_empty.png` has exactly the layout of the lit Millbrook images),
  `concept/locations/*` mood variants, task1 `assets/blocks/blocks.json`, `assets/structures/*.json`,
  `assets/props/*.gltf`.

## Design of the island (follow the concept art when the map and the scenes disagree)
- Size about 192 × 192 blocks, terrain height 0–48 with the playable surface around y = 16–28, edges
  breaking up into floating cubes and a cliff underside of stone and violet-veined spectral stone.
  Compress distances: the village square should be ~45 s of drifting from the graveyard.
- **Graveyard and mausoleum** on a hill in the west (the player's home and respawn), with a path and
  stairs down toward the village, a violet eerie-ore outcrop, grave-dirt patches and grave weeds.
- **Millbrook** in the centre: the square with the well and the charm board, four cottages and the
  tavern around it, cobble paths, flower boxes, lanterns on posts.
- **The stream** runs north to south through the village with a plank bridge on the main path; it is
  running water (blocks the ghost). The windmill stands on a rise in the north beside the stream.
- Wheat and pumpkin fields with the scarecrow in the east; forest clumps and rolling plains between.
- Underground: dirt → stone → spectral stone with ore pockets, so mining and working underground by
  day are possible; a few small caves.

## Steps
1. Write the island generator (`blender/scripts/build_island.py`): seeded and deterministic, a hand
   layout of zones (graveyard hill, village plateau, stream bed, windmill rise, fields, forest) shaped
   with noise, then strata and ore. Stamp the task1 structure blueprints and props at their places.
2. Output `assets/levels/millbrook_layout.json` (document the schema in README):
   - `world`: size, sea/void level, seed, `chunk_size` 16, and the voxel data itself as
     `assets/levels/millbrook_voxels.bin` (one byte per block id, x-z-y order, gzip) referenced here.
   - `instances`: prop glTF path, pos, yaw, owner structure, `hauntable` kind if any.
   - `markers` (kind, pos, yaw, owner): `player_start` (mausoleum door), `respawn`, `villager_home_*`,
     `bed_*`, `chair_*`, `hearth_*`, `work_*` (well, tavern bar, field, mill), `wander_*`, `door_*`,
     `window_*`, `hiding_spot_*` (behind wardrobes, under bridges: places the ghost lurks unseen),
     `ore_node_*`, `grave_node_*`, `weed_node_*`, `shelter_*` (daylight-safe places: mausoleum interior,
     caves).
   - `areas`: named regions (Graveyard, Millbrook Square, the four cottages by owner, Tavern, Windmill,
     Fields, Stream) with rects, for the HUD, for per-area Remembrance, and for town memory.
   - `water`: the stream's cells and flow direction. `kill_y`: below the island.
   - `lighting`: presets `night`, `dusk`, `day`, `fading` (sun/moon direction and colour, ambient, sky
     colours, fog colour and density, emission on/off for windows, saturation for `fading`), plus the
     day/night cycle keyframes (dusk → night → dawn → day).
   - `map`: the world rectangle the map image covers.
3. Render the island in Blender (voxels as instanced cubes with the task1 atlas, props as glTF) from
   cameras matching each concept image: Millbrook night/dusk/day/fading, the cottage interior, the
   windmill, the graveyard. Save side-by-side comparisons to `renders/task3/` and fix layout or light
   until they read like the concept art.
4. Render a top-down orthographic plan of the island to `renders/task3/millbrook_plan.png` with its world
   rectangle; it is the base for repainting the in-game map later.
5. README "Rebuild": add the island command after the characters.
6. Commit everything with a message saying what was built.

## Result
`assets/levels/millbrook_layout.json`, `millbrook_voxels.bin`, the island `.blend`, mood renders and
comparisons in `renders/task3/`, the plan render, report_task3.md.
