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

## Task 4 conventions (2026-11-16): population data — binding for task5
- **Files:** `assets/levels/millbrook_population.json` (villagers, schedules, hauntables, nodes, town memory, fx,
  scare rules, coverage checks) and `assets/data/memory_fragments.json` (owners, sets, fragments, drop tables). Schema in
  README. Built by `build_population.py` from `lib_population_content.py` (hand-written) + `lib_population.py` (analysis).
- **Every gameplay number is a placeholder** marked `"tuning": true`. Feel is Scott's.
- **Schedules** cover one whole cycle from 17:00 to 17:00 with no gaps; each step has clock hours *and* cycle `t`
  (the layout's 1200 s cycle). A night hour lasts about 71 s, a day hour about 30 s.
- **Walks are precomputed routes** (A* over standable voxel cells, preferring cobble/packed paths and avoiding furniture
  and fences; the mill ladder is a vertical link). Godot may follow the waypoints directly or re-path with a navmesh;
  the waypoints are known to be walkable. Walk speed = 1.2 × the clip's no-slide speed (Godot scales playback to match).
- **Hauntable ids = layout instance ids.** Extra entries: `source: population` (lanterns, kind `lantern`, Flicker,
  no HAUNT shell: Godot draws the rim on `INT_lantern` with a shader overlay) and `source: carried` (the candle or
  lantern in a villager's hand, `carried_by`, ×1.5 Unease).
- **Held items:** the default item stays in its own hand (`characters.json` `items`); any other item (bucket, broom,
  lantern, candle) goes in the other hand, placed by the task1 prop pivot hanging below the socket.

## Decisions made during task4 (2026-11-16) — defaults for Scott to change
- **Villager defaults as the task text gives them:** Widow Agnes (mill) fears **dolls**: her late daughter Elsie's rag
  doll, named **Button**, on the mill shelf (`cloth_doll_1`). Farmer Bram (east cottage) fears **loud noises**. Wren
  (tavern maid) fears **the dark**. Schoolteacher Marlow is the **skeptic** (belief 0.15, fears **being alone**, ignores
  single acts under 10 Unease, breaking her makes a lasting believer with 3× Remembrance). **Pip is a witness, not a
  target**: can't be scared, sees scares within 18 m (through windows too), legend points ×3, tells Wren and the tavern.
  **Scott to confirm Pip's witness role.**
- **Marlow's pronouns are she/her** in the data, to match the task2 teacher model (bun, long skirt). The task text
  calls Marlow "him"; it is one field (`pronouns`) plus her lines if Scott prefers him.
- **Pip's household:** Pip lives in cottage_a (the cottage interior concept, where the child in a nightcap holds a
  candle) while their parents are away at the market town for the season; cousin Wren looks in on Pip every night
  on her way home, and Marlow walks Pip home from the tavern. Cute, not cruel. Alternatives for Scott: move a parent
  villager in (run 2), or give Pip a bed in Wren's cottage.
- **Wren's home stays cottage_b** (task3). "Wren (tavern)" in the task is her workplace: she sweeps the step at dusk,
  serves until 22:00, tends the bar, sweeps up alone at 23:00 (vulnerable), snuffs the candles, looks in on Pip and
  walks home with her lantern after midnight.
- **Night plans:** dusk chores (Agnes draws water at the well with Pip playing near; Bram in the wheat with his back to
  the tall stalks; Wren sweeps the tavern step; Marlow reads the charm board), evening at the tavern (four seats
  assigned), walks home with lights (Agnes with her candle up the north path to the mill; Bram east between the fields
  with a lantern; Marlow's lone evening walk to the **bridge** and back with a lantern; Wren after midnight), bedtime
  (relight the hearth or a candle, check the door), late sitters (**Agnes rocks in Josiah's chair until 01:30**, Marlow
  reads until 01:15), sleep, then simple day plans (mill, fields, tavern, lessons in the square, Pip playing).
- **Marlow carries a lantern on her night walks.** The concept shows every villager out at night with a light, and an
  unlit dark figure read wrong in the comparison; it also gives her route a carried Flicker target.
- **Computed, not hand-set:** `alone` (no awake villager in the same interior, or outdoors within 10 m at the same
  moment), `facing_away_from` (hiding spots, doors and wardrobes within 9 m more than 100° behind them), `vulnerable`
  (alone and back to a hiding spot, or flagged in the content), `dark_stretches_m` (outdoor route metres beyond the
  reach of lantern posts, wall lanterns and lit windows; at dusk, night and dawn only), `crosses: bridge`.
- **Sleepers** take no Unease until a noise within a hauntable's `noise_radius_m` wakes them (at the nervous stage),
  and a sleeping villager is no company and no witness.
- **Haunting levels:** doors and floorboards = Creak (1); candles, oil lamps and lanterns = Flicker (2); rocking chair,
  wardrobe, portrait, bell = Haunted Furniture (3); doll and scarecrow = Possession Puppet (3). Level 3+ is decorative
  in the slice (`slice_active: false`).
- **Fear links:** doors play into loud noises (slam) and being alone (drifting open); floorboards, rocking chairs and
  portraits into being alone; lights into the dark; dolls and the scarecrow into dolls. `candle_1`, the candle Agnes
  keeps lit beside Button, also counts for **dolls**, so the slice (Flicker) has a way into her fear before the doll
  itself becomes hauntable at level 3. **Nobody fears mirrors** in the slice: there are no mirror props yet.
- **Coverage:** every villager has 4–7 level 1–2 hauntables at home and 7–14 on their routes, plus a fear object
  (checked by the build and the unit test).
- **Scare rules** (placeholders for task5): Unease stages at 25/45/65/80 % of nerve (glance, "Hello?", clutch the
  candle, primed), over 100 % = bolt (30 % payout); fear match ×1.75; grade score (primed 1, >90 % 1, fear 2, alone 1,
  back turned 1, 2 and 3 abilities +1 each, rigged doorway 1): Spooked < 3 ≤ Terrified < 6 ≤ Legendary, so the design
  plan's Agnes example scores Legendary.
- **Town memory:** the same trick on the same object twice within 2 nights → that villager hangs their charm there
  (garlic and lavender, horseshoe, salt vial...), the object is un-hauntable for 3 nights. A botch → salt line across the
  nearest door (2 nights, rain washes it). Legendary → a tavern rumor and +2 legend points; Pip witnessing ×3; legend
  name stages from "a draught in Millbrook" to "the {epithet} Ghost of Millbrook", the epithet from the most used trick
  ("the Creaking Ghost of Millbrook").
- **Nodes:** weed markers within 2.6 m of a grave are grave weeds (grave moss + fiber), the rest fiber grass. Voxel
  nodes use the blocks.json drops and tiers (eerie ore tier I, spectral stone and iron tier II). Regrowth in seconds and
  nights; ore veins re-form only while the area's Remembrance is ≥ 0.5.
- **Memory fragments:** 30 lines. The three sets of five belong to the worker ghosts' past lives, so completing a set
  gives that worker a name and a grave: **Hob Ashdown** the blacksmith (faster tool upgrades), **Marigold Finch** the
  gardener (grave moss, slower weeds), **Ned Ollery** the baker (nearby workers work faster). The other 15 are partial
  sets for run 2 (Elsie and Josiah Brook, Agnes's daughter and husband; Old Wynn the bell-ringer; Hettie Lark the first
  schoolmistress) and three strays (the kite child from the mining concept). Each has an emotion for the Memory Loom.
- **Effects:** smoke from the highest stone column of each house with a hearth (the mill has no hearth or chimney),
  flames and glows bound by node prefix, fireflies and mist as world boxes, stream sparkle points every ~6 m, spray at
  each waterfall foot, sails at 3.5 rpm, violet wisps on every exposed eerie-ore face and crystal cluster, the
  mausoleum portal glow, gravestone wisps, and three worker ghosts (blacksmith, gardener, baker) at graves, hidden by day.
- **Renders:** the task3 cameras plus `square_close` (villagers are only a few pixels tall in the wide concept framing);
  each shot poses everyone from their schedule at a fixed hour (night 21:45, dusk 18:30, day 12:00, mill 23:30,
  cottage 21:30). Effects are Blender stand-ins (spheres); the real particles are Godot's job.
- **`build_island.blender_main` takes `cameras`, `out`, `hook`, `blend_path`, `plan`** so task4 renders the same scene;
  its `main()` now runs only as a script. Task3 output is unchanged (rebuilt and diffed).

## Task 5 conventions (2026-11-17): the game — binding for run 2
- **All feel numbers in `assets/data/tuning.json`** (player, camera, presence, haunting, scare, overhear, town memory,
  Remembrance, Heat, mining, items, recipes, NPC, world look). The scare section is a copy of the task4 `scare_rules`
  (same values) extended for task5; **tuning.json wins** at runtime. Villager personalities (belief, nerve, fear, lines)
  stay in the population file; `villager_overrides` in tuning.json can override any of their numbers by id.
- **Collision layers:** 1 non-phaseable voxels, 2 phaseable voxels, 3 wooden (phaseable) props, 4 stone props
  (gravestones, pillars, millstone, mausoleum parts, lantern posts, the bell), 5 spirit barriers (running-water columns,
  salt lines), 7 actors. The ghost (a floating CharacterBody3D) collides with 1, 4 and 5 only. The camera spring uses
  1+2, or only 1 while the ghost is inside a block, so the view stays behind it. A second "x-ray" pass draws the
  ghost's silhouette through walls.
- **UI is code** (`UiKit`), font Fredoka (OFL). Game state, save and settings live in the `Game` autoload; sounds in
  `Sfx` (missing sounds are skipped, so audio can be swapped file by file).
- **Self-tests:** `--autotest` (46 checks, exit code) and `--tour` (one view per concept image) run windowed; the
  exported exe supports both and writes next to itself (`autotest/`).

## Decisions made during task5 (2026-11-17) — Scott may revisit
- **Custom GDScript chunk mesher, not the Voxel Tools module** (the design plan's open question). Measured on this PC
  (20 threads, RTX 5070 Ti, 1600 × 900):
  - 254 non-empty 16³ chunks, 100,093 faces.
  - Meshing on WorkerThreadPool: **1.94 s in the editor build, 1.07 s in the exported release**.
  - Node and collision creation 0.1–0.2 s; the whole world is ready in about 3 s (editor) / 1.8 s (release).
  - **About 111–114 FPS** over the village at night with shadows, glow, fog and the ink outline.
  - A single-chunk remesh after a block edit takes a few ms on the main thread.

  Good enough for the 192 × 48 × 192 slice. The open world (run 2) may need chunk streaming or a GDExtension mesher.
- **Mesher look:**
  - Per-vertex AO and a ±5 % per-block brightness jitter.
  - A deterministic 3.5 cm vertex jitter; shared corners move together, so there are no cracks.
  - The baked task1 bevel/ink tiles, normal maps from `blocks_normal.png`, ore emission from `blocks_emission.png`.
  - Leaves and other `transparent` solids don't cull each other; plants are crossed quads that sway.
  - Water is a separate transparent pass, its top lowered to 0.86, scrolling south.
- **Running-water barrier:** one tall box per stream column, from 3 below the bed to 12 above the surface. Columns with
  a solid block within 3 cells above the water (the plank bridge) are skipped. The ghost can rise at most 9 m above
  the ground, so it can't hop over.
- **Hover 1.05 m** (1.0 grazed the cobblestone footing course of the cottages); gliding down at 1.4 m/s. Inside a solid
  phaseable block the ghost holds its height until you rise or sink, so it can tunnel underground.
- **Shelter from daylight** means being within a `shelter_*` marker's radius (+1.5 m), or having at least 2 *natural*
  solid blocks overhead (caves, dug tunnels). Cottage roofs don't count: thatch isn't natural.
- **Night length:** the cycle is 1440 s, so night (half the cycle) lasts 12 min. The layout's `t` keys and the task4
  schedules are cycle fractions and stay unchanged, so villagers keep their timing.
- **Town memory counts a trick once per finished scare, not per act.**
  - Task4's rule ("the same trick on the same object twice within 2 nights → charm"), applied per act, would charm a
    door on its second creak, in the middle of building Unease.
  - Now every object used in a scare that ended in a break or bolt is recorded.
  - Using it again in a later scare within 2 nights gets it charmed by the villager who was scared. Until then, reuse
    doubles suspicion.
  - **Question for Scott.**
- **Haunting 2 (Flicker) at 25 Fright:** one Terrified scare or three Spooked ones, so Flicker arrives in the first
  night. Presence levels at 60/160/320/560 Fright raise HP 10→18, the BOO radius 4→6.4 m and manifest time 1.6→3.2 s.
- **Grade score** is task4's table plus `three_objects` (+1 for three different objects in the chain). The slice has
  only two abilities (Creak, Flicker), and the task asks for a combo of different objects. In the autotest, the first
  Agnes scare (doors only, alone, back turned) grades Terrified; the second (candle by Button, door, candle) Legendary.
- **BOO:** costs 20 Ectoplasm, has a 3 s cooldown and needs the `primed` stage (80 % of nerve).
  - A villager who sees you manifest before they're primed botches it as "spotted" (suspicion +0.5).
  - Otherwise an early BOO botches as "too early": they laugh it off and nerve rises by their bravery gain.
  - Both botches salt the nearest doorway for 2 nights.
  - Vulnerability checks: *alone* = no other awake villager (Pip counts) within 10 m; *back turned* = the ghost is more
    than 100° off their facing; *rigged doorway* = the last door used in the chain is within 2.2 m of them.
- **Who hears an act:**
  - Doors and floorboards reach every villager within the hauntable's `noise_radius_m`; loudness falls to 50 % at the
    edge, and drift-open carries 80 % as far. They wake sleepers at the nervous stage.
  - Lights reach whoever is within 7 m; a carried light reaches only its carrier.
  - A nearby awake villager relights a snuffed light after 7 s (1.5 s with Wren's spare candle).
- **Villagers follow the schedule by clock:** their position along the precomputed route is the fraction of the step's
  time, so walk speed always matches the clip's no-slide speed × playback. After a reaction they rejoin with an A* path
  over standable voxels at 1.25 × walk speed. When fleeing they run home (or to their `flee_to`) and stay out of sight
  for about 14 s. Doors swing open for them.
- **Workbench placement:** the crypt is 3 × 3 and full (chest, candles, respawn point), so the Spectral Workbench
  stands in the yard just outside the mausoleum door (30.5, 28, 88.6), facing the path.
- **Spawn 2.5 m out of the mausoleum door:** the layout's `player_start` puts the chase camera against the wall.
- **Tools are scaled 0.75** on the ghost (issues.md, task2) and attached by their `GRIP` node to `HELD_tool`.
- **Lighting:**
  - The task3 presets drive everything.
  - Godot's ambient light is stronger than Blender's, so `world.ambient_mult` is 0.5 and `world.exposure_mult` 0.85
    (both in tuning).
  - Lanterns and candles are tinted warm orange (#ffad5c / #ffb24d) and given real ranges (8 m / 5 m), as task4 asked.
  - A custom sky shader draws the gradient, the stars and the big moon.
- **Ink outline** on props and characters is a screen-space depth-edge pass (toggle in settings); voxels keep their
  baked ink.
- **Audio:** every sound is synthesized by `tools/make_audio.py` (CC0, ours), plus ten CC0 Kenney variants. A
  background agent had downloaded more packs, but some had provenance I couldn't verify (itch.io CC-BY packs), so only
  the official Kenney packs were used. The screams and laughs are formant synthesis: cute and comic, but clearly
  synthetic.
- **Export:**
  - Windows: x86_64 with the pck embedded.
  - macOS: universal zip, ad-hoc signed with Godot's built-in signer, not notarized; ETC2/ASTC import is enabled for
    Apple Silicon.
  - Only the needed export templates were unpacked.
