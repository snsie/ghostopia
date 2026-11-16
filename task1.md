# Task 1: Blocks, structures and props in Blender (run 1: vertical slice)

## Mode: fully autonomous
- Don't ask questions or wait for confirmation. Make every decision yourself and record it in decisions.md.
- If something is unclear in the concept art, choose a reasonable option in the target style and continue.
- Don't wait for Blender MCP, Godot MCP or other tools to connect. Work with what is there: run Blender
  from the command line with Python scripts:
  `"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/scripts/<script>.py -- <args>`.
  Godot headless: `/c/Tools/Godot/godot_console.exe`. Shell: Git Bash, never PowerShell.
- If a step fails, try another approach. If that fails too, record the problem in issues.md and move on.
- Don't stop until the task is complete. At the end write a short report in report_task1.md:
  what was done, what did not work.
- Look at your results (preview renders, contact sheets) and compare with the concept art before
  calling anything done.
- Read first: CLAUDE.md, docs/design/design-plan.md (mechanics, source of truth),
  `Ghostopia — concept art and tasks.md` (style block, scope; sections 6–7 say which reference board
  feeds which asset and which drift to ignore), then decisions.md and issues.md if they exist.
- Original IP only. Never model anything from `concept_art/horror cosmetics.png` or the Ghostbusters
  parts of `concept_art/town raids.png` (uniforms, packs, logo, trap box).

## External assets
- Build all models and textures yourself in Blender with Python scripts. No paid 3D generation services.
- No terrain plugins.
- Only free assets with open licences (CC0, CC-BY) if anything is downloaded; record every one in
  assets/CREDITS.md: file, source, author, licence, link. If a site needs a login, skip it.

## Goal
Everything static that the vertical slice (Millbrook village, its windmill, the starting graveyard)
is built from: block textures and block definitions for the voxel world, voxel structure blueprints
for the buildings, and glTF props for every detail and hauntable object. Style: stylized hand-painted
cartoon, light ink outlines, chunky slightly beveled irregular blocks, palette of ghost white /
ice-blue glow, violet magic, warm timber, moss green, cool grey stone, ember orange.

## Inputs
- `concept/characters/block_palette.png` (the 15 blocks), `concept/characters/hauntable_props.png`
  (each prop normal and haunted), `concept/characters/spectral_tools.png`
- `concept/locations/` (Millbrook night/dusk/day/fading, cottage interior, mill, graveyard, mining),
  `concept/empty/`, `concept/locations/world_map.png`
- `concept_art/mausoleum.png`, `concept_art/building and crafting.png` (tiers 1–2 only for the slice),
  `concept_art/basic ghost.png` (workbench, nodes)

## Conventions (write into decisions.md first; every later task obeys them)
- **1 block = 1 m.** Blender Z up → Godot Y up. Front faces Blender −Y = Godot +Z. Pivot = centre of
  the base on the ground. A villager is ~1.8 m (2 blocks), the player ghost ~0.6 m.
- **Hybrid world:** terrain and buildings are voxels that Godot meshes at runtime; Blender produces the
  block textures and definitions, structure blueprints (block placements), and glTF only for things
  that are not cubes (props, doors, furniture, the windmill sails, gravestones, the mausoleum details).
- Node prefixes in glTF: `INT_<kind>_*` hauntable/interactive parts with the pivot where they move
  (door hinge, chair rocker contact, wardrobe door hinge, floorboard centre); `MARK_<kind>` empties;
  `ANIM_*` looped motion (windmill sails); `LIGHT_*` point lights (export RAW, ×1/30);
  `FX_<kind>` empties where Godot spawns particles (flame, smoke, wisp); `*-colonly` collision.
- Hauntable props carry a **haunt glow** material slot or emissive mask (violet + ice-blue) that Godot
  switches on when the object is haunted; flames and window glass carry mood-dependent emission.
- Export glTF Separate (`.gltf` + `.bin`) with shared textures in `assets/textures/`.

## Steps
0. Tooling: `python -m pip install --user numpy pillow opencv-python` (image tools outside Blender;
   Blender's bundled Python already has numpy). Create `decisions.md` and `issues.md` if missing.
1. Study the art. Write `props_list.md`: every block type, structure and prop the slice needs, by
   location, and which concept image defines it. At minimum: the 15 blocks of the palette; cottages
   (4, varied), tavern, windmill, well, charm-covered notice board, plank bridge, fences, lanterns and
   lamp posts, barrels, crates, benches, flower boxes, pumpkins, wheat, scarecrow, the mausoleum (tier-2
   spectral stone, gargoyles, spiral emblems, violet glowing doorway), gravestones (3–4 variants),
   dead tree, candles; interiors (hearth, bed, table, chairs, shelf, jars, books, rug); the Spectral
   Workbench with anvil.
2. **Block textures** (`blender/scripts/make_block_textures.py` → `assets/blocks/`): numpy-painted,
   tileable, one 64×64 texture per face type (top/side/bottom where they differ) packed into one atlas
   `assets/blocks/blocks_atlas.png` + a normal/height atlas. Bake the hand-painted bevel into the
   texture: lighter top-left edge, darker bottom-right edge, slight irregular inset, as on the palette
   sheet. Colours sampled from `block_palette.png`.
3. **Block definitions** `assets/blocks/blocks.json`: per block `id`, `name`, atlas tiles per face,
   `solid`, `phaseable` (ghost passes through soft blocks: wood, dirt, grass, glass, plants, thatch,
   wheat; not stone, iron, ore, salt-cured or blessed), `transparent`, `liquid` + `running_water`
   (the stream: spirits can't cross), `tool` (scythe / shovel / sledgehammer / none), `tier` (I–IV),
   `hardness`, `drops`, `fragment_chance` (memory fragment on mining natural blocks), `light`.
   Add `glowing ore` emission for eerie ore and the teal veins of spectral stone.
4. **Structure blueprints** (`blender/scripts/build_structures.py` → `assets/structures/*.json`):
   each building as a voxel blueprint: size, block palette, run-length-encoded block list, plus
   `props` (glTF prop, local pos, yaw) and `markers` (doors, beds, chairs, hearth, windows, candles,
   where an NPC sits or sleeps). Real openings: doors and windows are gaps the door/shutter props fill.
   Interiors are hollow with ceilings ≥ 3 blocks so a 2-block villager and the camera fit; the cottage
   interiors follow `cottage_interior_night.png` and `empty/cottage_interior_empty.png`. One generator
   with parameters (size, roof pitch, thatch/slate roof, timber pattern, chimney side) yields the four
   cottages and the tavern; separate builders for the windmill base, well, bridge and mausoleum.
   Render each blueprint in Blender as cubes with the atlas for previews.
5. **Props** (`build_props.py` → `assets/props/*.gltf`): chunky, slightly beveled, hand-painted like the
   concept sheets. Hauntables with `INT_` pivots: door (hinged), floorboard, candle (flame `FX_flame`,
   snuffable), oil lamp, rocking chair, wardrobe (two hinged doors), portrait (eyes as a separate
   mesh that can turn), cloth doll, scarecrow, bell. Windmill sails as `ANIM_sails`. Gravestones and the
   mausoleum details. Spectral tools (scythe, shovel, sledgehammer, tiers I–IV) as held items with a
   `GRIP` empty, translucent ice-blue material.
6. **Lights:** every lantern, candle, hearth and window glow has `LIGHT_*` + emissive material; candles
   and lamps must be dimmable/snuffable from code (light + flame mesh + emission are separate nodes).
7. Collision: simple `-colonly` boxes for props; voxels collide via the Godot mesher.
8. Previews: a contact sheet per category (blocks, structures, props, hauntables normal vs haunted,
   tools) in `renders/task1/`, plus a `style_check.py` render that puts a cottage, the well, the
   mausoleum and a few blocks side by side under night and day lighting. Compare with the concept art;
   fix and re-run until they read as the same game.
9. README "Rebuild" section: the exact commands, in order (block textures → structures → props).
10. Commit everything (`git add -A && git commit`), message saying what was built. No builds yet
    (there is no game until task5).

## Result
props_list.md, `assets/blocks/` (atlas, normal atlas, blocks.json), `assets/structures/*.json`,
`assets/props/*.gltf`, `.blend` libraries in `blender/`, contact sheets in `renders/task1/`,
conventions in decisions.md, report_task1.md.
