# Task 1 report: blocks, structures and props (vertical slice)

## Done

- **Conventions** written into `decisions.md` first and kept: 1 block = 1 m, Godot +Z front, base-centre
  pivots, the blueprint format (anchor, origin, `_skip`/`air` palette, RLE, rooms), node prefixes
  `INT_ MARK_ ANIM_ LIGHT_ FX_ HAUNT_ FLAME_ GRIP -colonly`, material prefixes
  `GLOW_ FLAME_ HAUNT_ SPECTRAL_`, glTF Separate with shared textures, lights RAW × 1/30.
- **`props_list.md`:** every block, structure and prop by location, with its source concept image and
  a status section.
- **Block textures** (`make_block_textures.py`): 40 numpy-painted 64 × 64 tiles in an 8-column atlas
  (`blocks_atlas.png`, plus normal, height and emission atlases). Colours are sampled from
  `block_palette.png`. Side tiles have the baked hand-painted bevel (light top-left, dark bottom-right,
  irregular inset, light ink rim). Terrain tops are seamless. Ore crystals and spectral-stone veins
  emit light.
- **`blocks.json`:** 28 blocks (the 15 palette blocks + 13 needed for buildings and terrain). Each has
  id/index, tiles per face, shape (cube/cross), solid, phaseable, transparent, liquid, running_water,
  tool, tier I–IV, hardness, drops, fragment_chance, light and emissive.
- **Prop textures** (`make_textures.py`): 37 shared 128 px textures in `assets/textures/`. They reuse
  the block painters, so props and voxels look like one game. They include an original painted portrait
  and a portal swirl.
- **Props** (`build_props.py` + `props_*.py`): 84 glTF files in `assets/props/`, with
  `assets/props/props.json` (category, hauntable flag, node list, size) and `blender/props.blend`.
  - **Hauntables:** door (hinged), interior door, floorboard (centre pivot), candle, candle cluster,
    oil lamp, rocking chair (rocker-contact pivot), wardrobe (two hinged doors), portrait (eyes on a
    separate node), cloth doll, scarecrow, bell (yoke pivot). Each has `HAUNT_` shells.
  - **Lights:** candles, lamps, lanterns, the hearth and windows each have the `LIGHT_` node, the flame
    mesh and the emissive material as separate nodes, so code can dim or snuff them.
  - **Others:** windmill sails on `ANIM_sails`, the tavern sign on `ANIM_sign`, collision boxes on
    furniture, and doors whose collider swings with the leaf.
  - **Graveyard:** 4 gravestones with worker-spawn markers and wisp FX, winged and corner gargoyles,
    spiral emblem, violet portal doorway with a rusty gate, mausoleum window, dead tree with lanterns,
    crystals, mounds, weeds.
  - **Tools:** 12 spectral tools (scythe, shovel, sledgehammer × tiers I–IV) with `GRIP`/`GRIP_off`,
    and the Spectral Workbench with anvil.
- **Structures** (`build_structures.py`): 10 voxel blueprints in `assets/structures/`.
  - One parametric generator (size, roof type and pitch, chimney side, stone courses, braces,
    partition, windows) makes cottage_a–d and the tavern. The other builders make the tapered windmill
    (with loft), the well over a water shaft, the plank bridge, the mausoleum and the graveyard gate.
  - Openings are real (1 × 2 doors, 1 × 1 windows filled by props). Interiors are hollow with ≥ 3 m
    clear. cottage_a follows `cottage_interior_empty.png`.
  - Every blueprint carries placed props, markers (entry, door, window, hearth, sit, sleep, hide,
    creak, climb, respawn, storage, villager home…) and room boxes.
- **Previews in `renders/task1/`:**
  - Blocks: atlas tiles, cube sheets (studio and night).
  - Props: prop textures, one sheet per category, and hauntables at night normal vs. haunted.
  - Structures: day, night and cutaway interiors.
  - `style_check_{day,dusk,night,night_close}.png`: blocks, cottage, well, mausoleum, graveyard, field
    and stream in one scene.
- **Verification:**
  - Godot 4.7.2 headless import of all assets is clean (see issues.md for one transient run).
  - No `.001` node names in any glTF.
  - Every blueprint's RLE adds up to its size and its palette starts with `_skip`, `air`.
  - Existing unit tests pass (2/2).
- **README "Rebuild"**: the exact commands in order. `assets/CREDITS.md` records that nothing was
  downloaded.

## Compared with the concept art

- **Blocks:** the cube sheet reads as the same family as `block_palette.png` (palette, bevel, chunky
  painted detail).
- **Props:** rocking chair, wardrobe, portrait, candle, lantern, bell, scarecrow, gravestones,
  gargoyles and tools match their sheets in shape and colour.
- **Haunted look:** the violet rim glow in the previews is a Blender stand-in for the Godot shader.
- **Buildings:** the cottages read as Millbrook's half-timbered thatched cottages with glowing windows,
  and the close night view (`style_check_night_close.png`) matches `millbrook_night.png` in layout and
  palette.

## Not done / weaker than the concept

- Voxel roofs are stepped stairs. The concept's soft, overhanging, mossy thatch isn't reproduced;
  roof-edge trim props or a sloped-roof block shape would close the gap.
- Previews have no bloom, fog, fireflies or particles. Night scenes are flatter and less saturated
  than the paintings, and the mood belongs to Godot's lighting presets (task3/task5).
- The haunt glow and prop ink outlines need Godot shaders. The glTF carries only placeholder materials
  and named nodes for them.
- The well is a square 3 × 3 ring (the concept's is round), and the decorative `tree_oak` canopy is
  simple.
- The mausoleum cutaway preview doesn't show the interior (cosmetic, see issues.md).
- No builds: there is no game until task5, as the task says.
