# Task 1 asset list (vertical slice: Millbrook, the mill, the starting graveyard)

What the slice is built from, by location, and the concept image that defines each item.
Status column is filled in at the end of task1 (✅ built, ⚠️ simplified, ❌ not built).

Image keys: **BP** `concept/characters/block_palette.png` · **HP** `concept/characters/hauntable_props.png` ·
**ST** `concept/characters/spectral_tools.png` · **MN/MD/MY** `concept/locations/millbrook_night|dusk|day.png` ·
**ME** `concept/empty/millbrook_empty.png` · **CI** `concept/locations/cottage_interior_night.png` ·
**CE** `concept/empty/cottage_interior_empty.png` · **MI** `concept/locations/mill_night.png` ·
**GN** `concept/locations/graveyard_night.png` · **GE** `concept/empty/graveyard_empty.png` ·
**MZ** `concept_art/mausoleum.png` · **BG** `concept_art/basic ghost.png` ·
**BC** `concept_art/building and crafting.png` · **MC** `concept/locations/mining_night.png`

## 1. Blocks (`assets/blocks/`)

The 15 palette blocks (BP), plus the extra blocks the buildings and terrain need.

| id | Source | Faces | Notes |
|---|---|---|---|
| grass | BP r1c1 | top / side / bottom(=dirt) | flowers + clover on top, moss drip on side |
| dirt | BP r1c2 | all | reddish-brown clods, pebbles |
| grave_dirt | BP r1c3 | all | violet-dark soil, roots, bone flecks |
| sand | BP r1c4 | all | warm sand, swirls (stream banks) |
| cobblestone | BP r1c5 | all | grey-violet stones, moss in cracks (paths, well, foundations, chimneys) |
| spectral_stone | BP r2c1 | all | stone with glowing teal veins + spiral (emissive veins) |
| eerie_ore | BP r2c2 | all | violet stone + glowing crystals (emissive) |
| iron_ore | BP r2c3 | all | grey stone + rusty/silver nuggets |
| thatch | BP r2c4 | top / side | straw roof block |
| timber_planks | BP r2c5 | all | warm planks, nails (floors, doors-frames, bridge deck) |
| plaster_wall | BP r3c1 | side / top | cream plaster in a timber frame with a brace |
| wheat | BP r3c2 | cross | crop, `shape: cross` |
| grave_moss | BP r3c3 | top / side | mossy grave earth with violet flower |
| gravestone | BP r3c4 | front / side / top | carved cross block (placeable grave marker block) |
| river_water | BP r3c5 | all | the stream, `running_water` |
| stone | GN / GE cliffs | all | natural cool grey-violet rock under the terrain |
| mossy_stone_bricks | GN, MZ, BC tier 2 | all | cut spectral stone bricks with moss (mausoleum, graveyard walls) |
| timber_beam | MN cottages, CE | side / end | dark half-timber frame posts and beams |
| slate_roof | MN tavern | top / side | violet-grey slate shingles (tavern, well roof) |
| rough_wood | BC tier 1 | all | weathered vertical boards (tier-1 build block, mill walls) |
| oak_log | MN trees | top / side | trunk |
| leaves | MN trees | all | leafy canopy, transparent edges |
| tall_grass | GN | cross | grave weeds / fibre grass (scythe node) |
| flowers | MN, GN | cross | violet + white wildflowers |
| packed_path | MN lanes | top / side | trodden dirt path |
| still_water | well | all | water that spirits *can* cross |

## 2. Structures (voxel blueprints, `assets/structures/`)

| Name | Source | Notes |
|---|---|---|
| cottage_a | MN centre, CE | thatch roof, timber frame, chimney left, 2 rooms (main + bedroom) |
| cottage_b | MN right | thatch, wider, chimney right, wisteria, porch steps |
| cottage_c | MN back-right | thatch, narrow, tall roof, chimney left |
| cottage_d | MN / CE | thatch, stone lower course, chimney right, L-ish annex |
| tavern | MN left | slate roof, stone base, chimney, awning, hanging sign, outdoor tables |
| windmill_base | MN top-left, MI | stone + timber tower, open ground floor with millstone, loft; sails = glTF |
| well | MN centre | round cobble well; roof + crank = glTF prop on top |
| plank_bridge | MN bottom | timber deck spanning a 3-block stream, rails |
| mausoleum | GN, GE, MZ | tier-2 mossy spectral stone, gabled roof, steps, violet doorway; gargoyles + spirals = glTF |
| graveyard_wall | GN, GE | low mossy stone wall segment with posts |

## 3. Props (glTF, `assets/props/`)

### Village (Millbrook)
| Prop | Source | Hauntable / special |
|---|---|---|
| door_cottage | HP r1 door, MN | **INT_door** hinge, HAUNT shell |
| door_round (arched cottage door) | MN | INT_door hinge (used by cottages) |
| window_cottage (frame, glass, shutters) | MN, CE | GLOW_ glass, INT_shutter hinges |
| notice_board (charms) | MN centre | dreamcatcher, bells, charms, lavender |
| well_roof (roof, crank, bucket) | MN | `INT_crank` |
| fence_wood (1 m segment), fence_post | MN, GN | |
| lantern_post (lamp post) | MN, GN | LIGHT_lantern, GLOW_lantern, FLAME_ |
| lantern_hanging / wall lantern | MN cottages, tavern | LIGHT_lantern |
| barrel, crate, sack (grain) | MN, MI | |
| bench, tavern_table, stool | MN tavern | MARK_sit |
| flower_box | MN windows | |
| pumpkin (2 sizes), pumpkin_vine | MN fields | |
| scarecrow | HP r3, MN | **INT_scarecrow** (Puppet later), HAUNT shell |
| tavern_sign, tavern_awning | MN | sign swings: ANIM_sign |
| windmill_sails | MN, MI | **ANIM_sails** (spins about the axle) |
| millstone, hopper, grain sacks, ladder | MI | |
| bell (on post) | HP r3 | **INT_bell** swing pivot at the yoke |
| tree_oak | MN | trunk + canopy (non-voxel decorative tree) |
| wisteria (hanging vine cluster) | MN, CE | decor |
| broom, bucket, mug | MN | small decor |

### Cottage interiors
| Prop | Source | Hauntable / special |
|---|---|---|
| hearth (stone fireplace + logs) | CI, CE | FLAME_, LIGHT_hearth, FX_flame, FX_smoke |
| bed | CI (bedroom), CE | MARK_sleep |
| table, chair | CI | MARK_sit |
| rocking_chair | HP r2, CI | **INT_rocker** pivot on the rocker contact, HAUNT shell, MARK_sit |
| wardrobe | HP r2, CI | **INT_wardrobe_door_L/R** hinges, HAUNT shell, MARK_hide (ghost peeks) |
| shelf (with jars, books) | CI, CE | |
| jar (glowing variant) | CI | GLOW_ |
| books (stack) | CI | |
| rug | CI, CE | no collision |
| portrait | HP r2, CI | **INT_portrait_eyes** separate mesh that turns, HAUNT shell |
| cloth_doll | HP r3, CI | **INT_doll** (whole doll), HAUNT shell |
| candle (in holder) | HP r1, CI | **INT_candle**: FLAME_candle + LIGHT_candle + FX_flame, HAUNT shell |
| candle_cluster (3 candles) | CE, GN | 3 × FLAME/LIGHT |
| oil_lamp | HP r1, CI | **INT_lamp**: FLAME_, GLOW_ glass, LIGHT_lamp, HAUNT shell |
| floorboard | HP r1 | **INT_floorboard** pivot at the centre (creak wobble), HAUNT shell |
| chest | CI | lid INT_chest_lid hinge |
| side_table, basket | CE | |
| curtains | CI | decor |

### Graveyard + mausoleum
| Prop | Source | Hauntable / special |
|---|---|---|
| gravestone_round, gravestone_spiral, gravestone_cross, gravestone_celtic | GN, GE, MZ | MARK_worker_spawn, FX_wisp |
| mausoleum_gargoyle (winged ridge gargoyle, corner gargoyle) | GN, MZ | |
| mausoleum_spiral_emblem | GN, MZ | |
| mausoleum_portal (violet glowing doorway) | GN, MZ | FLAME_portal (always glows), LIGHT_portal, FX_wisp |
| mausoleum_gate (rusty) | prompt 4.1 graveyard | INT_gate hinge |
| dead_tree | GN, GE | twisted trunk + branches, hanging lanterns |
| candle_cluster (graves) | GN | see interiors |
| wilted_flowers, mushroom | GN | decor |
| eerie_crystal_cluster | GN, MC | FLAME_crystal, LIGHT_crystal |
| dirt_mound (dig spot) | GN, BG | |
| weed_clump (scythe node) | BG | |

### Spectral tools + crafting
| Prop | Source | Notes |
|---|---|---|
| scythe_t1..t4, shovel_t1..t4, sledgehammer_t1..t4 | ST, BG, MC | held items, `GRIP` empty, SPECTRAL_ translucent ice-blue, violet crystals from tier III |
| spectral_workbench (with anvil, tools, blueprint) | BG | MARK_use, crafting station |

## Status at the end of task1 (2026-11-16)

✅ **Blocks:** all 26 listed above, plus `plaster_brace` and `cobble_path` (28 blocks, 40 atlas tiles).
`assets/blocks/blocks.json` holds the per-block data (faces, tools, tiers, phasing, drops, light).

✅ **Structures:** all 10: cottage_a–d, tavern, windmill_base, well, plank_bridge, mausoleum,
graveyard_gate. `assets/structures/index.json` lists them.

✅ **Props:** 84 glTF files, listed with their node names and sizes in `assets/props/props.json`.
- Built under different names or merged into another prop:
  - The arched cottage door is `door_cottage`, and `door_interior` is the bedroom door, so there is
    no separate `door_round`.
  - The mausoleum's rusty gate is `INT_gate` inside `mausoleum_portal`.
  - The hopper is part of `millstone`.
- Extra props: `window_round`, `lantern`, `stone_pillar` and `grave_candles`.
- `curtains` and `pumpkin_vine` are built but not placed in any blueprint yet; they're for task3/4.
- ⚠️ `tree_oak` is decorative only. The world generator will probably use voxel `oak_log` and
  `leaves` trees instead.
