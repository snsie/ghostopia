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
