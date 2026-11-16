# Decisions

Every choice made without asking Scott. Newest sections at the bottom. Later tasks obey the
**Conventions** section; change it only with a new dated entry here.

## Conventions (task1, 2026-11-15) — binding for every later task

### Units, axes, pivots
- **1 block = 1 m.** Blender Z up → Godot Y up (glTF exporter `export_yup`).
- **Front faces Blender −Y = Godot +Z** for structures, props, characters and markers. A marker faces
  where a character standing on it faces.
- **Pivot = centre of the base on the ground** (wall-mounted props: pivot on the wall plane at floor
  level, the prop sticks out toward −Y / Godot +Z; mount height is baked into the mesh).
- Scale references: villager ≈ 1.8 m (2 blocks), player ghost ≈ 0.6 m, door opening 1 × 2 blocks,
  interior ceilings ≥ 3 blocks clear.

### Voxel world
- Hybrid: Godot generates terrain and meshes all voxels at runtime. Blender produces block textures,
  `assets/blocks/blocks.json`, structure blueprints `assets/structures/*.json`, and glTF only for
  non-cube things.
- Block atlas `assets/blocks/blocks_atlas.png`: **8 columns × N rows of 64×64 tiles, no padding**,
  tile index = row × 8 + col. Godot should import it as a **Texture2DArray** (horizontal slices 8,
  vertical slices N) so mipmaps never bleed between tiles; `blocks_normal.png` (tangent-space,
  OpenGL/+Y convention, which Godot expects) and `blocks_height.png` use the same grid.
  Texture filtering: **linear + mipmaps** (the style is painterly, "not pixel art"); the Texture2DArray
  import keeps tiles from bleeding into each other.
- Ink outline and bevel are **baked into every tile** (dark 1 px rim, light top-left, dark
  bottom-right, irregular inset). So voxels get outlines without a shader.
- Block ids are lowercase snake_case strings; `blocks.json` also gives each a stable integer `index`
  (0 = air). Blueprints reference block ids, never integers.
- Block `shape`: `cube` (default) or `cross` (two crossed quads, for wheat / tall grass / flowers).
  `transparent: true` blocks don't cull neighbours' faces.
- `phaseable`: the ghost passes through soft blocks (wood, dirt, grass, glass, plants, thatch, wheat,
  sand, leaves, plaster). Never through stone, cobble, iron, ore, slate, salt-cured or blessed blocks.
- `running_water: true` blocks (the stream) are uncrossable for spirits (folklore rule).

### Structure blueprints (`assets/structures/<name>.json`)
- Coordinates are **Godot axes**: x → east (+X), y → up, z → south (+Z = the building's front).
- `size: [sx, sy, sz]`; `origin: [ox, oy, oz]`. **Anchor** = the world cell where the pivot stands:
  the first air cell above the terrain surface. Local cell (x, y, z) goes to world cell
  `anchor + (x - ox, y - oy, z - oz)`. So layers below `oy` are foundations / shafts that replace
  terrain (`oy` = 1 for houses, 3 for the well), and layer `oy` is the first layer above ground.
- **Pivot** = centre of the origin cell's footprint at ground level (world `anchor + (0.5, 0, 0.5)` in
  metres). Footprints are odd-sized, so this is the true centre.
- `palette`: list of block ids. **Index 0 is always `"_skip"`** (leave the world cell untouched: outside
  sloped roofs, eave rings, around chimneys), **index 1 is always `"air"`** (carve: interiors,
  doorways, windows). Other entries are block ids from `blocks.json`.
- `rle`: flat list `[count, palette_index, count, palette_index, ...]` over cells in order
  `i = x + sx * (z + sz * y)` (x fastest, then z, then y layers bottom-up).
- `rooms`: `{name, min, max}` axis-aligned boxes in metres relative to the pivot (for NPC AI / haunting).
- Floor surface inside houses = 0 m (top of the foundation layer). Windows: sill at 1 m, opening
  1 × 1. Doors: 1 × 2 opening from 0 m. Loft in the windmill: 4 m.
- `props`: `{ "prop": "<name>", "gltf": "res://assets/props/<name>.gltf", "pos": [x, y, z] (metres,
  relative to the pivot, Godot axes), "yaw": deg (0 = prop front faces +Z, positive = counter-
  clockwise seen from above, i.e. Godot rotation.y), "tags": [...] }`.
- `markers`: `{ "kind": "door|window|bed|chair|hearth|candle|sit|sleep|stand|spawn|entry|...",
  "pos": [...], "yaw": deg, "id": "..." }`.
- Openings are real: doors are 1 × 2 air gaps (door prop fills them, hinge on the left seen from
  outside), windows are air gaps filled by a window prop (frame + glass + shutters).

### glTF node prefixes (props, structures, later characters)
- `INT_<kind>_<part>` hauntable / interactive part with its pivot where it moves (door hinge, chair
  rocker contact, wardrobe door hinges, floorboard centre, portrait eyes, bell yoke, candle flame).
- `MARK_<kind>` empties (sit, sleep, stand, use, spawn, look-at).
- `ANIM_<name>` simple looped motion driven by code (windmill sails spin about local Godot Z).
- `LIGHT_<kind>` point lights (KHR_lights_punctual), exported **RAW with ×1/30** (70 W in Blender →
  2.33 in Godot). Light, flame mesh (`FLAME_*` node) and emissive material are separate nodes so a
  candle can be dimmed or snuffed from code.
- `FX_<kind>` empties where Godot spawns particles (`FX_flame`, `FX_smoke`, `FX_wisp`, `FX_sparks`).
- `HAUNT_<kind>` haunt-glow shell meshes (violet + ice-blue, additive). **Godot hides every
  `HAUNT_*` node at load** and shows it while the object is haunted.
- `GRIP` empty on held tools: where the ghost's main hand holds it; `GRIP_off` for the second hand.
  See "Spectral tools" below for the orientation.
- `*-colonly` simple box collision meshes (Godot makes StaticBody3D). Hollow/walk-through props
  (rugs, flowers, wheat) have none.

### Materials
- Shared tileable textures in `assets/textures/` (painted with numpy, 128×128 or 256×256).
- Material-name prefixes Godot relies on:
  - `GLOW_*`: mood-dependent emission (window glass, lamp glass): on at night/dusk, off by day.
  - `FLAME_*`: always emissive (flames, embers, eerie crystals).
  - `HAUNT_*`: haunt glow (violet/ice-blue emissive, alpha blend).
  - `SPECTRAL_*`: translucent ice-blue spectral tools (alpha + emission).
- Outlines on glTF props: not baked into geometry; Godot draws them (inverted-hull `next_pass` or a
  post-process in task5). Preview renders use Blender Freestyle to match.

### Export
- glTF **Separate** (`.gltf` + `.bin`), textures referenced from `assets/textures/` (relative
  `../textures/`), one file per prop, `.blend` libraries saved in `blender/`.

### Prop pivots for openings and wall-mounted props
- Door props (`door_cottage`, `door_interior`, `mausoleum_portal`): pivot = bottom centre of the 1 × 2
  opening, in the middle of the wall thickness. Window props (`window_cottage`, `window_round`,
  `mausoleum_window`): pivot = bottom centre of the 1 × 1 opening (place at sill height 1 m), middle of
  the wall. `yaw` turns the outside face toward the street.
- Wall-mounted props (portrait, flower_box, lantern_wall, curtains, wisteria, tavern_sign,
  tavern_awning, windmill_sails, mausoleum_spiral_emblem): pivot on the wall plane at floor level, the
  prop sticks out toward its front; mount heights are baked in (portrait centre 1.6 m, lantern 2 m,
  sign 2.6 m, sails hub 7.5 m above the pivot).
- Haunt-glow shell names: `HAUNT_<part>` for each moving `INT_` part, `HAUNT_static` for the
  non-moving rest of the prop.
- Several flames in one prop: `INT_candle_1..n`, each with `FLAME_candle_n`, `LIGHT_candle_n`,
  `FX_flame_candle_n`. Godot code matches on the prefix (`FX_flame*`, `LIGHT_*`), never full names.

### Spectral tools
- Origin at the butt of the handle, handle along Godot +Y, the working end (blade edge, spade face,
  hammer face) toward Godot +Z (forward). `GRIP` = main hand, `GRIP_off` = second hand. Godot attaches
  the tool by aligning `GRIP` with the hand bone.
- Tiers I–IV get brighter emission and translucency (`SPECTRAL_*_t1..t4` materials), violet gems from
  tier III, crystal cluster + ribbon at tier IV (as on `spectral_tools.png`).

## Decisions made during task1 (2026-11-15/16)
- **Materials in glTF are simple PBR placeholders** for some effects Godot must do itself:
  `HAUNT_glow` should become an additive fresnel rim shader (violet → ice-blue), see
  `renders/task1/hauntables_normal_vs_haunted.png` for the intended look; ink outlines on props and
  bloom on `FLAME_*`/`GLOW_*` are also Godot's job (previews use Blender Freestyle, no bloom).
- **Terrain top faces have no bevel/ink rim** (`grass_top`, `dirt_top`, `sand_top`, `grave_dirt_top`,
  `stone_top`, `grave_moss_top`, `path_top`, `cobble_plain`). With the rim on every tile, flat ground
  read as a checkerboard (style check). Sides keep the bevel, so steps and cliffs still read as
  chunky blocks.
- Extra blocks beyond the 15 on the palette sheet: stone, mossy_stone_bricks (tier-2 build block),
  timber_beam, plaster_brace, slate_roof, rough_wood (tier-1 build block), oak_log, leaves, tall_grass,
  flowers, packed_path, cobble_path, still_water (the well; spirits *can* cross it). 28 blocks in total.
- Tool/tier table: shovel → dirt, grass, sand, grave dirt, path; scythe → plants, thatch, all wood,
  plaster, grave moss, leaves; sledgehammer → stone, cobble, ores, slate, bricks, gravestone.
  Tier II needed for iron ore, spectral stone and mossy bricks; everything else is tier I.
  `eerie_ore` is tier I (the gathering board shows the starter sledgehammer on it).
  `fragment_chance` only on natural blocks (0.01 leaves … 0.25 eerie ore).
- Building outline per concept: four thatched cottages (two with two rooms, two with one or two), slate-
  roofed tavern, tapered two-storey windmill (9 × 9 stone/timber base, 7 × 7 upper storey, loft at
  4 m), 3 × 3 well over a water shaft, plank bridge for a 3-wide stream, compact 5 × 5 mausoleum with a
  low gable (a first 5 × 6 version with a full-pitch roof looked like a ziggurat next to the cottages).
- Voxel roofs are 2-thick stairs (pitch 1 on cottages, 2 on cottage_c and the mill, ½ on the
  mausoleum), so they are closed from inside. The concept's soft overhanging thatch is approximated;
  roof-edge trim props could soften it later.
- `cottage_a` follows `cottage_interior_empty.png` exactly (hearth left, back window, rocking chair on a
  rug, shelf with the doll, side table + oil lamp, wardrobe, portrait, door to the bedroom); no table,
  because the concept has none. The other cottages get kitchen tables instead.
- The widow's doll sits on the mill's shelf (tag `widow_doll`), per the design plan's example scare.
- Previews use orthographic three-quarter cameras (like the concept sheets) and EEVEE + Freestyle;
  per-item frames are gitignored and only the contact sheets are committed (the frames are 60+ MB and
  rebuild in about a minute).
- Rebuild order is textures → block textures → props → structures → style check. The task text says
  structures before props; the structure JSON doesn't depend on props, but the structure previews
  stamp the real prop glTFs, so props go first.

## Task 2 conventions (2026-11-16): characters — binding for task3–task5

### Files and nodes
- One glTF Separate per character in `assets/characters/<name>.gltf` (+ `.bin`, textures shared from
  `assets/textures/`), plus `assets/characters/characters.json` (size, bones, nodes, expressions, clips with
  frame counts and loop flags, no-slide speeds, item clips, events). Built by `build_characters.py`.
- Names: `ghost`, `worker_blacksmith|gardener|baker`, `villager_widow|farmer|maid|teacher|child`.
  Nodes per character: `<name>_rig` (skeleton), `<name>_body` (skinned body + clothes), `<name>_face` or
  `ghost_eyes` (shape keys), `<name>_hat` (villagers with a hat, skinned rigidly to the `hat` bone),
  `HELD_*` sockets, `ITEM_*` held items under them, `MATERIAL_manifest` (ghost only).
- Pivot = centre of the base on the ground, front = Godot +Z (as task1). The ghost's pivot is the
  bottom of its hem; Godot floats it by placing the pivot.
- 24 fps, one glTF animation per clip with the short names from task2.md, **no root motion**. Loop
  flags live in `characters.json` (`clips.<name>.loop`); Godot sets `loop_mode` from it at load.
- Glb would duplicate textures; Separate keeps the task1 rule.

### Skeletons
- Villagers share one 21-bone skeleton (same names and hierarchy, per-villager proportions):
  `root hips spine chest neck head hat shoulder_L/R upperarm_L/R forearm_L/R hand_L/R thigh_L/R shin_L/R
  foot_L/R`. `hat` is a bone (not in the ~20 of the task text) so the hat is a separate mesh that the
  big_scare_leap animation can throw off; hatless villagers keep the bone unused.
- Ghost skeleton (13 bones): `root body chest head upperarm_L/R forearm_L/R hand_L/R hem_F hem_BL hem_BR`.
  Worker ghosts use the same skeleton at 0.75 scale.
- Animations are baked per character by code (rotations as world-axis deltas, analytic two-bone IK,
  foot-planted gait), so each glTF carries clips that fit its own proportions.

### Held items
- `HELD_tool` (ghost, right palm), `HELD_R` / `HELD_L` (villagers and workers), `HELD_block` (workers,
  above the head for `carry`). At rest every socket's axes equal the character frame (Godot +Y up,
  +Z forward), so an item attached with identity rotation stands upright and faces forward.
- Godot attaches an item by placing the item's `GRIP` node (task1 tools) on the socket; items without
  a `GRIP` are placed by their pivot. Built-in villager items (`ITEM_candle`, `ITEM_lantern`,
  `ITEM_pitchfork`, `ITEM_book`, `ITEM_doll`) already sit with their grip on the socket.
- `characters.json` lists per villager the `item_clips` that show the default item; Godot hides the
  `HELD_*` children in all other clips (or swaps in a broom / tray for sweep / serve_drinks).
- The candle and lantern keep task1's `INT_`/`FLAME_`/`LIGHT_`/`FX_` nodes, so Flicker can snuff the
  candle a villager is carrying. The lantern drop and hat-off moments of `big_scare_leap` are in
  `characters.json` `events` (frame numbers) for Godot to spawn physics props.

### Ghost materials and expressions
- `GHOST_sheet` (translucent white, pale ice-blue emission) is the normal state; `GHOST_manifest`
  (opaque, brighter) lives on the hidden `MATERIAL_manifest` triangle. Godot hides that node at load and
  sets it as `ghost_body`'s surface override when the living can see the ghost. The ice-blue fresnel rim
  is a Godot shader job (previews use a Blender fresnel stand-in, as task1 did for the haunt glow).
- Ghost eyes: shape keys `angry scared happy closed` (basis = calm). Villager face: `uneasy scared
  terrified relieved asleep` (basis = calm). `asleep` is an extra key for the sleep loop.
- Ghost arms are hidden by scaling `upperarm_*` to 0.04 inside the sheet; clips pop them out.

### Markers the clips assume
- `sit`, `rock_in_chair`: pivot on the seat surface (`MARK_sit`), feet reach 0.48 m down. The rocking
  chair's own rocking is its `INT_` node; the villager adds a matching body sway (period 2.5 s).
- `sleep`: pivot on the mattress (`MARK_sleep`, yaw 180 on the bed); the villager lies on the back,
  head toward its facing direction, so it lands on the pillow.

## Decisions made during task2 (2026-11-16)
- **All animation made in Blender by code; nothing downloaded.** The foot-planted gait has no sliding
  (planted-foot speed error ≤ 0.5 mm/s, checked numerically), and the key-pose clips read clearly on
  the strips, so the CC0 fallback was not needed.
- **Every villager gets all 20 shared clips**, including `rock_in_chair` and the three work loops, since
  they cost nothing on the shared skeleton and give task4 freedom (e.g. the maid can sweep). The intended
  owners are: widow `rock_in_chair` + `sweep`, farmer `work_field`, maid `serve_drinks`.
- **Hold styles per villager** change the arms in idle/walk-type clips (widow: candle held at the
  chest in both hands; farmer: pitchfork upright; maid: lantern hanging, other hand at the chest; teacher:
  one arm crossed, book against the chest; child: doll hugged). Clip names stay shared.
- **Child wears a nightcap** (from `cottage_interior_night.png`), which gives the child a hat node too.
  The teacher has no hat (her bun is hair).
- **Teacher's held item is the book**, with the satchel on her hip; the potion-like vial on
  villagers.png is a salt vial (a folklore charm), not a potion.
- **Proportions:** chunky heads about 1/4 of the height (child about 1/3), short legs, mitten hands.
  Heights: widow 1.50, farmer 1.74 (+hat), maid 1.60, teacher 1.68, child 1.10 m.
- **Faces are geometry, not texture swaps** (eye/brow/mouth/cheek patches on the head with shape keys),
  so expressions stay crisp at any distance and blend smoothly inside clips.
- **Ghost T-pose rest** keeps the arms out (as on basic ghosts.png); every clip scales them in or out.
- **Ghost tool clips use the tier I tool lengths** for the two-hand IK. Higher tiers are a few cm longer;
  the left hand lands within reach of `GRIP_off`.
- **Worker ghosts are 0.75 × the player ghost** (0.51–0.61 m with hats) and bean-shaped, as on
  worker_ghosts.png.
- **Previews show frame 0 of the idle clip** in the turnarounds (the rest pose is the A/T-pose), plus
  an expression sheet per character.

## Task 3 conventions (2026-11-16): level data — binding for task4–task5
- **Level files:** `assets/levels/millbrook_layout.json` + `millbrook_voxels.bin` (schema in README "Level data").
  World origin = cell (0, 0, 0) corner; Godot axes and metres as everywhere else.
- **Voxel file:** gzip of `u8` block indices from `blocks.json` (0 = air), order **x fastest, then z, then y**,
  the same order as blueprint RLE. 192 × 48 × 192 cells, chunk size 16. The voxels already contain every
  stamped structure; `structures` in the JSON only describes them.
- **Marker ids** are `<kind>_<resident or place>[_<detail>]`. Residents: `agnes` (windmill), `pip`
  (cottage_a), `marlow` (cottage_c), `wren` (cottage_b), `bram` (cottage_d). Structure instance ids:
  `mausoleum`, `graveyard_gate`, `windmill`, `pip_cottage`, `marlow_cottage`, `wren_cottage`, `bram_cottage`,
  `tavern`, `well`, `bridge`. Blueprint markers are renamed (sit → `chair_*`, sleep → `bed_*`, hide →
  `hiding_spot_*`, spawn_villager → `villager_home_*`) and keep their origin in `source`.
- **Lighting presets live in the layout JSON** and the Blender previews render from them, so Godot and the
  previews share one definition. `direction` is the vector the light travels (Godot DirectionalLight3D
  looks down its −Z: point −Z along it). Energies are Godot units (the preview multiplies by about 3).
- **Day/night cycle (tuning):** 1200 s; night gets half the cycle (inverted day): dusk → night (t 0.08–0.58)
  → dawn → day (0.70–0.94) → dusk. A `dawn` preset was added for the transition.
- **Export note for task5:** `.bin` and `.json` under `assets/levels/` are not Godot resources; the export
  presets must include them (`include_filter` `*.json, *.bin`).

## Decisions made during task3 (2026-11-16)
- **Graveyard in the west**, as the task text and `world_map.png` say. `millbrook_empty.png` paints the
  graveyard hill upper right of a view that otherwise looks north (windmill upper left, fields lower right),
  so in the Millbrook render the graveyard is off-frame to the left. Everything else follows
  `millbrook_empty.png`: the stream runs on the **west** side of the village with the tavern on its east
  bank, the bridge south-west of the square on the main path, the mill on a rise to the north-west.
- **Fields south-east of the square** (wheat behind, pumpkins in front, as in the lit Millbrook images'
  lower right); Bram's cottage beyond them in the east.
- **Homes:** cottage_a (the interior concept) is Pip's, Marlow's is the narrow cottage_c by the square,
  Wren's is cottage_b facing the square from the east (task4 has her walking home from the tavern),
  Bram's is the farmer's cottage_d by the fields, Agnes lives in the mill. The tavern has no resident.
  A child living alone is odd; task4 can move a guardian in or treat Pip as staying with Wren.
- **Island:** round-ish (radius 84 ± 4, wobbly), 192 × 192 world; the playable surface is y 20–27 (village
  top block 20, mill rise 26, graveyard plateau 27, north highland 24); a deep keel underneath (bottom at
  y 1 in the middle, thin at the rim) of stone, spectral stone and eerie-ore streaks; 260 floating cubes
  past the crumbling rim. North highland terraces down to the village, so the stream has two waterfalls
  above the village and two small drops south of it, then falls off the south rim.
- **Distances:** the path from the mausoleum door to the square is about 102 m (stairs included):
  46 s at 2.2 m/s, about 30–40 s at the ghost's 2.5–4 m/s drift. Close to the task's ~45 s; the layout
  constants at the top of `lib_island.py` move zones if Scott wants it tighter.
- **Stream:** 3 wide, two cells deep, surface one block below the banks (the bridge blueprint assumes
  that), sand bed, sand/grass/stone banks. Water cells carry a flow vector and a waterfall flag.
- **Hiding spots:** wardrobes (from the blueprints), beside the bridge abutments (the deck sits right on
  the water, so there is no room under it), behind the tavern barrels, the well, the charm board, in the
  wheat, behind the dead tree and the mill's grain sacks.
- **Shelters:** the mausoleum crypt plus three small caves (graveyard hill, mill rise, a sinkhole in the
  south forest), each ending in a chamber with eerie and iron ore on the walls.
- **Ore nodes** are exposed ore blocks with a floor below the open side (the underside streaks don't
  count): the graveyard outcrop and cave walls. Hidden ore pockets (iron in stone y 5–17, eerie ore in
  spectral stone y ≤ 11) are plain voxels to dig for.
- **The square** mixes cobble path and cobblestone blocks, with a ring of grass and flowers round the well
  (concept). Village lawns get no weeds within 30 m of the square, only flower clumps.
- **Renders:** voxels are meshed per 32 × 32 chunk with hidden faces culled (equivalent to instanced cubes,
  and fast: ~104k faces); props are collection instances of the task1 glTFs. EEVEE + Freestyle ink lines,
  ink colour darkened for the island (task1's ink reads light on a dark night scene). Saturation and a
  soft bloom are applied to the saved PNG, since EEVEE has no bloom. Comparison sheets are JPEG.
- **Cutaways** for the cottage interior (front wall and everything above 3 m removed) and the mill (front of
  the ground floor removed) are render-only; the voxel data is untouched.
