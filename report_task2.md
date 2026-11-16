# Task 2 report: the ghost, villagers and worker ghosts (vertical slice)

## Done

- **Character toolkit** (`blender/scripts/lib_char.py`):
  - Skeleton builder, lofted bodies (superellipse cross-sections), parametric surfaces.
  - Skinning by code (1/dᵏ to allowed bones or custom weight functions, ≤ 3 influences).
  - Face features with one shape key per expression.
  - A pose solver: world-axis rotations converted to bone-local quaternions, analytic two-bone IK with
    pole vectors, world-space rotation targets, automatic pelvis drop that keeps both feet reachable.
  - Clip baking into one NLA track per clip, and glTF export with skins, morph targets and lights
    (RAW × 1/30 as in task1).
- **Basic Ghost (player)** (`char_ghost.py`, `assets/characters/ghost.gltf`):
  - Body: a 0.6 m sheet (dome head, six folds, pointed hem rolling inward).
  - Materials: glossy translucent `GHOST_sheet`, plus `GHOST_manifest` on a hidden holder node.
  - Eyes: two dark ovals as a separate mesh with shape keys `angry scared happy closed`. No mouth.
  - Arms and rig: sheet arms hidden inside the body by bone scale; 13-bone rig (spine chain, arm
    chains, 3 hem bones).
  - `HELD_tool` socket that fits the task1 tool `GRIP`; the other hand IKs onto `GRIP_off`.
  - All 13 clips: `idle_float drift glide_down ascend phase swing_scythe dig_shovel smash_hammer
    haunt_cast boo hurt scatter celebrate`.
- **Five villagers** (`char_villagers.py`, `assets/characters/villager_*.gltf`):
  - Rig and bodies: one shared 21-bone skeleton; bodies from lofts and clothes as shells, all skinned
    by code.
  - Faces: one mesh each with shape keys `uneasy scared terrified relieved asleep` (calm = basis).
  - Hats: separate meshes on a `hat` bone.
  - Charms: garlic, horseshoe and salt pouch on the belts.
  - Items: `HELD_R` / `HELD_L` sockets with the default items. Candle and lantern reuse task1's prop
    code, keeping `INT_`/`FLAME_`/`LIGHT_` nodes, so Flicker can snuff a carried candle. Pitchfork,
    book and doll are new.
  - All 20 shared clips are baked for each villager's proportions. Walking and running use a
    foot-planted gait.
- **Worker ghosts** (`worker_blacksmith|gardener|baker.gltf`):
  - 0.75-scale bean-shaped ghost bodies wearing the worker_ghosts.png outfits (caps with goggles,
    sunhat, toque, aprons with emblems).
  - Tools as `ITEM_*` nodes, plus a `HELD_block` socket.
  - Clips `idle_float`, `carry`, `work`.
- **`characters_list.md`**: heights, silhouettes, materials, held items, clip lists, no-slide speeds,
  scale check. **`assets/characters/characters.json`**: the same data for Godot, including loop flags,
  `item_clips` and the big_scare_leap event frames.
- **Renders** (`renders/task2/`):
  - Per character: `<name>_turnaround.png` (front, ¾, side, back), `<name>_anims.png` (8 frames per
    clip; ghost tool clips show the real task1 tools, workers' carry shows a block, sit and rock use a
    seat) and `<name>_expressions.png`.
  - `lineup_front.png` / `lineup_three_quarter.png`: everyone at true scale, imported back from the
    glTFs, next to a 1 m block, a 1 × 2 doorway with the task1 door, and the ghost hovering 1 block up.
- **Verification**:
  - Godot 4.7.2 imports all nine glTFs (second import clean).
  - New `tests/test_characters.gd` (5 tests) checks every file's skeleton, bones, clips, sockets and
    blend shapes, and the door fit. All 7 tests pass.
  - A numerical check confirms no foot sliding: every planted foot in every gait clip of every villager
    moves at the stated speed within 0.5 mm/s.
- README "Rebuild" has the task2 commands; `decisions.md` has the task2 conventions (binding for later
  tasks) and decisions; `issues.md` has the problems and workarounds; `assets/CREDITS.md` notes that
  nothing was downloaded.

## Compared with the concept art

- **Ghost**: the turnaround matches basic ghosts.png: rounded dome, draped sheet with a wavy pointed
  hem, two dark oval eyes, no mouth. The angry, scared and happy eye shapes match the sheet.
  - The tool poses follow basic ghost.png: scythe sweep, shovel plunge and lever, two-handed hammer
    smash.
- **Villagers**: each is recognisable from villagers.png: hooded widow with a candle, bearded farmer in
  a straw hat and overalls with a pitchfork, maid with a bonnet, apron and lantern, bespectacled teacher
  with a bun, coat and book, and a curly-haired child with a doll.
  - Proportions are chunky with big heads.
  - big_scare_leap follows scare_reactions.png: arms up, hat flying off, lantern dropped.
  - laugh_it_off rubs the back of the head, also as on scare_reactions.png.
- **Workers**: the outfits match worker_ghosts.png.

## Not done / weaker than the concept

- **Materials are flat painted colours** with the task1 cloth textures. There is no hand-painted
  texture detail: no plaid shading on folds, no hair strands, no patch stitching. Nothing outlines them
  either: the concept's soft painterly shading and ink outlines come from Godot's outline pass and
  shaders in task5.
- **Hands are mittens**, without separate fingers; the doll stays the task1 sitting rag doll (the
  concept child holds a plush bunny).
- **Cloth doesn't simulate.** Skirts and the shawl follow the legs and arms by skin weights, so wide
  steps can push a knee close to the skirt surface. The flee clip looks fine at game distance.
- **The ghost's fresnel rim and translucency** are a preview stand-in in Blender; Godot needs the rim
  shader (as for task1's haunt glow).
- **No item swaps in the strips.** `sweep`, `work_field` (for everyone except the farmer) and
  `serve_drinks` are mimed in the strips; Godot attaches the task1 `broom`, a hoe or a tray to `HELD_*`.
- **Held items don't detach.** The dropped lantern and the flying hat need Godot physics at the
  event frames. The hat flies along a baked arc and lands behind the villager; the lantern stays in the
  hand in the clip.
- **No builds.** The project has no main scene or export presets yet; the game and its Windows / macOS
  builds start in task5, as with task1.
