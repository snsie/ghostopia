# Ghostopia — concept art and tasks

Working title. Full mechanics: [docs/design/design-plan.md](docs/design/design-plan.md) (source of truth;
this file is the art and production plan that grows from it).

## 1. Pitch

A cute-spooky **third-person voxel survival game**. You are a small Basic Ghost who wakes in the Veil, a
chunky block world stitched together from the memories of the dead. Living villagers from a parallel
mortal world bleed through into it and can't see you, so at night you drift into their homes and
**scare them**: read each villager's hidden fear, build their Unease with creaks and flickers, then break
them with a perfectly timed big scare graded Spooked, Terrified or Legendary. Scares pay **Fright**,
which levels three paths (Haunting, Possession, Telekinesis). They also make the living *remember*,
and Remembrance is what keeps the land, your walls and your graveyard from crumbling into the Hollow.
By day you shelter in your mausoleum, mine blocks for materials and memory fragments, and tend graves
whose ghosts work for you. Cycle: **inverted day/night** (night is your time, daylight drains you).
Platforms: Windows and macOS.

**Vertical slice (run 1):** the Open Plains biome. One farming village (Millbrook) with a mill on a
river, three or four cottages with interiors, fields, and your starting graveyard with a small
mausoleum on a hill. The ghost drifts, glides and phases through soft blocks. You mine with the
spectral scythe, shovel and sledgehammer, and mined blocks drop memory fragments. Haunting levels 1 and 2
(Creak, Flicker) work against four villagers who each have a fear, Belief, an Unease meter, visible
escalation and big funny breaks, and who remember your tricks. Prototype gate: is scaring a villager with a
creaking door and a snuffed candle fun?

**Run 2+:** Suburban Block, Urban, Hellscape, memory pockets, crypt dungeons, Possession and
Telekinesis paths, graveyard base building, folklore defenses, raids.

## 2. Style block

Derived from Scott's reference boards in `concept_art/` (see section 6). Paste at the start of every
image prompt, and attach `concept_art/basic ghosts.png` (characters, props) or `concept_art/biomes.png`
(locations) with "keep exactly the same art style as the reference image":

```text
Game concept art for a cute-spooky survival game: stylized hand-painted cartoon look with soft
painterly shading and light sketchy ink outlines, chunky rounded forms, a world built from slightly
beveled, irregular hand-painted blocks (voxel-based but soft, not pixel art), cute expressive
characters, soft shadows, glowing magical shaders with gentle bloom, playful with a melancholy
undertone, no photorealism, no gore, no pixel art. Setting: the Veil, an afterlife stitched together
from half-remembered memories of the living, around a quiet old farming village. Consistent palette:
ghost white with pale ice-blue glow, eerie violet-purple magic glow, warm weathered timber brown,
mossy green, cool grey stone, ember orange firelight. Soft painterly lighting, readable silhouettes,
three-quarter view from slightly above, 16:9.
```

## 3. Mood add-ons

- **Night (play time):** `Night, deep blue sky with a huge soft moon, pale ice-blue ghost glow and violet magic against warm orange windows, fireflies and low mist, cozy-eerie, not horror.`
- **Dusk:** `Dusk, lavender and peach sky, long blue shadows, the first candles being lit in windows, a sense of the night about to begin.`
- **Day (living world bleeds through):** `Pale washed-out daylight, slightly overexposed and hazy, colours a little bleached, the ghost world feels thin and exposed.`
- **Fading (low Remembrance):** `Low remembrance: colours desaturated toward grey, block edges flickering and crumbling into floating cubes, a starless void eating the edge of the land.`

## 4. Prompts

All prompts below = style block + mood add-on + subject + `no text`.

### 4.1 Locations: vertical slice (night, dusk, day; the village also fading)

**Millbrook village** (`concept/locations/millbrook_<mood>.png`):

```text
Millbrook, a half-remembered old farming village built from chunky voxel blocks: a cluster of four
crooked timber-and-plaster cottages with thatched block roofs and glowing windows around a small
square with a stone well and a notice board covered in charms; a wooden windmill on a rise beside a
slow stream crossed by a little plank bridge; a tavern with a hanging lantern; wheat and pumpkin
fields with a scarecrow; dirt paths leading out toward dark rolling plains and, on a hill, a small
graveyard. Doors and shutters look openable, candles and lanterns sit in windows. Two or three
villagers in simple clothes walk with lanterns, unaware of a small cute ghost hovering nearby.
```

**Cottage interior** (`concept/locations/cottage_interior_<mood>.png`; night and day only):

```text
Interior of a cozy old village cottage built from chunky voxel blocks, cutaway three-quarter view: a
main room with a hearth, a creaky plank floor, a wooden door to a bedroom, a tall wardrobe, a rocking
chair, a shelf with a cloth doll and jars, a portrait on the wall, candles and an oil lamp as the only
light, a window to the moonlit village. A villager in a nightcap holds a candle and glances nervously
over her shoulder while a small cute ghost peeks out from behind the wardrobe. Every hauntable object
is clearly readable.
```

**The mill** (`concept/locations/mill_<mood>.png`; night):

```text
Inside and around an old wooden windmill on a rise above a slow dark stream: big canvas sails turning
slowly, grain sacks, a millstone, a steep ladder to a loft, a single candle on a windowsill, an
elderly widow's rocking chair beside a shelf with a faded doll. The stream glints in the moonlight; a
small cute ghost hovers at its bank, unable to cross the running water.
```

**Starting graveyard** (`concept/locations/graveyard_<mood>.png`):

```text
A small forgotten graveyard on a hill above the village, built from chunky voxel blocks: a tiny
moss-covered stone mausoleum with a rusty gate as the ghost's home, a handful of leaning gravestones
with candles and wilted flowers, overgrown grave weeds and fiber grass, a twisted dead tree, patches
of dark graveyard dirt and a vein of faintly glowing eerie ore in a rocky outcrop. A few translucent
little worker ghosts float among the graves. The village glows warmly in the valley below.
```

**Mining close-up** (`concept/locations/mining_night.png`):

```text
Close-up gameplay moment: a small cute ghost swings a translucent glowing spectral sledgehammer at a
voxel block of eerie ore in a rocky hillside; the block cracks and releases a drifting wisp of light
containing a faint sepia vignette of a memory (a child flying a kite). Nearby blocks of graveyard
dirt, stone and grass, a spectral scythe and shovel floating beside the ghost.
```

### 4.2 Empty locations (for task3 layouts; night)

Same prompts as 4.1 for Millbrook, the cottage interior, the mill and the graveyard, plus:
`Empty scene: no people, no ghosts, no animals, no loose items, only terrain blocks, architecture and
fixed props.` → `concept/empty/<place>_empty.png`

### 4.3 World map

`concept/locations/world_map.png`:

```text
Top-down stylized overview map of a compact voxel afterlife world: the village of Millbrook in the
center with its square and four cottages, a river running north to south with a watermill and a plank
bridge, wheat and pumpkin fields to the east, a hill with a small graveyard and mausoleum to the west,
rolling plains around it, and all edges of the land crumbling into a dark starless void. Clear
readable layout like a game level map. No text, no labels, no frame.
```

### 4.4 Characters

Characters add: `full-body character concept, front view, side view and back view, neutral grey background, character sheet, no text`.

- **Basic Ghost (player)**: already defined by `concept_art/basic ghosts.png` (turnaround + T-pose) and `concept_art/basic ghost.png` (tool poses). A small cute bed-sheet ghost about knee height to an adult: a rounded head, glossy white cloth with a pale ice-blue glow, a soft draped hem that ripples at the bottom, no legs, **no mouth**, two large dark oval eyes whose shape carries the expression (angry slant, wide, happy squint), and sheet "arms" that pop out to hold tools. Only order more if task2 needs it: `concept/characters/basic_ghost_expressions.png`, `Expression sheet of this exact ghost (attach basic ghosts.png): neutral, curious, mischievous, angry, scared, proud, and a big BOO pose with arms raised.`
- **Ghost evolutions (run 2)** `concept/characters/ghost_evolutions.png`: `Four variants of the same small cute ghost side by side: Haunter carrying a tiny lantern and trailing short ghostly chains; Shade darker and blurred at the edges with a faint outline of a cat it last possessed; Poltergeist with small debris (a spoon, a book, pebbles) orbiting it and crackling sparks; a hybrid Haunter-Poltergeist mixing both.`
- **Villagers** `concept/characters/villagers.png`: `Lineup of five chunky cartoon villagers from an old farming village with simple blocky proportions and big expressive faces: an elderly widow in a shawl holding a candle; a burly farmer in overalls with a pitchfork; a nervous young tavern maid with an apron and lantern; a skeptical bespectacled schoolteacher with crossed arms; a curious child in a nightshirt holding a cloth doll. Each has a small charm (garlic, horseshoe, salt pouch) on their belt.`
- **Scare reactions** `concept/characters/scare_reactions.png`: `Animation reference sheet of one chunky cartoon villager (the burly farmer) through the stages of being scared: calm; glancing over his shoulder; calling out "hello?" with a raised lantern; walking fast clutching a candle; a huge exaggerated leap with his hat flying off and the lantern dropping; fleeing with arms flailing; and laughing it off bravely. Clear poses, motion lines.`
- **Worker ghosts and Forgotten Soul** `concept/characters/worker_ghosts.png`: `Tiny translucent worker ghosts, smaller than the player ghost, wearing little caps and aprons from their past lives (a blacksmith, a gardener, a baker), carrying spectral tools; and next to them a Forgotten Soul: a taller, ragged, grey-faded ghost with hollow glowing eyes and tattered edges, sad rather than gory.`

### 4.5 Hauntable props and blocks (task1 reference)

- **Hauntable props** `concept/characters/hauntable_props.png`: `Prop sheet on a neutral grey background, chunky voxel-styled cartoon furniture and objects, each shown normal and "haunted" with a soft mint glow: a wooden door, a creaky floorboard, a candle, an oil lamp, a rocking chair, a tall wardrobe, a portrait with eyes, a cloth doll, a scarecrow, a bell. No text.`
- **Block palette** `concept/characters/block_palette.png`: `Texture sheet of voxel game blocks, each shown as a single cube in three-quarter view on a neutral grey background in a neat grid: grass, dirt, dark graveyard dirt with bone flecks, sand, cobblestone, spectral stone with faint teal veins, eerie ore with glowing crystals, iron ore, thatch, timber planks, plaster wall, wheat, grave moss, a gravestone, river water. Hand-painted cartoon textures, 16x16-pixel-ish chunky detail upscaled. No text.`
- **Spectral tools** `concept/characters/spectral_tools.png`: `Item sheet: translucent glowing mint-teal spectral tools for a cute ghost, a scythe, a shovel and a sledgehammer, each in four upgrade tiers from rough and dim (I) to ornate and bright (IV). Neutral grey background, no text.`

### 4.6 UI

UI add (matches the info panels on every reference board): `game UI design, translucent dark slate-blue panels with thin glowing cyan corner-bracket frames, bold rounded sans-serif headings in white and golden yellow, square item slots with small painted icons, green progress bars, readable`.

- **Title screen** `concept/ui/title_screen.png`: `Title screen: the game title "GHOSTOPIA" painted in bold white and golden-yellow rounded letters with a pale ice-blue glow over a moonlit voxel graveyard on a hill with the warm village below, the small cute ghost peeking from behind a gravestone; menu items "Continue", "New Game", "Settings", "Quit" on a parchment panel on the left.` (This one keeps its text.)
- **HUD** `concept/ui/hud.png`: `Gameplay HUD over a night village scene: top-left a ghostly HP bar and an Ectoplasm meter; top-right a small moon clock showing time until daylight; bottom a hotbar of nine slots with spectral tools and blocks; three small Fright bars for Haunting, Possession and Telekinesis with level numbers; above a nearby villager's head an Unease meter shaped like a candle flame, with a tiny fear icon; center a large scare-grade stamp "TERRIFIED!" fading out.`
- **Journal** `concept/ui/journal.png`: `Memory journal screen: an open leather-bound book; the left page shows a grid of collected memory fragment cards as small sepia vignettes, some still blank; the right page shows one fragment enlarged with a short handwritten line and the face of the person it belongs to.`
- **Inventory and crafting** `concept/ui/inventory.png`: `Inventory and crafting screen: a grid of item slots with blocks, materials and spectral tools; a Spectral Workbench recipe panel; a ghost paper-doll on the left with cosmetic slots.`
- **Scattered (death) screen** `concept/ui/scattered.png`: `"Scattered" screen: the small ghost bursting into glowing wisps that drift back toward a distant mausoleum, a dim overlay and a parchment panel with "Return to Mausoleum".`
- **Pause/settings** `concept/ui/settings.png`: `Settings screen on a parchment panel: sliders and toggles for audio, graphics, controls, with a little ghost bookmark.`

### 4.7 Run 2 locations (order later, not for the slice)

Suburban Block (1970s suburb rendered slightly wrong, looping streets), Urban (vivid present-day city with
Ghost Hunter vans), Hellscape (regret pools, burning memories, demon strongholds), memory pockets (foggy
battlefield, wrong-coloured childhood beach, endless hospital corridor), crypt dungeon, demon portal.
Relics and cosmetics must be original designs on slasher archetypes (a masked stalker, a cursed doll, a
clawed glove), never licensed film characters.

### 4.8 Underveil (run 2; see "The Underveil" in `docs/design/design-plan.md`)

Underveil mood add-on (use instead of the surface moods): `Deep underground, no sky: lit only by glowing
fungus, votive candles, lanterns and the soft pulse of memory veins in the rock; cool dark blue-violet
shadows with warm pools of clan light, drifting motes, cozy-eerie, not horror.`

Locations (`concept/locations/underveil_<place>.png`, plus an empty version per 4.2 for task3):

- **Glowcap Warrens** (Mycelial Kin): `A vast cavern forest of giant glowing teal mushrooms built from chunky voxel blocks, little homes carved into the stalks, spore lanterns on ropes, a slow fungus farm, gentle mushroom-capped dead folk tending it, a small cute ghost being welcomed.`
- **The Drowned Nave** (Drowned Parish): `A sunken stone chapel half-flooded in an underground lake, pews poking out of still water, a bell tower rising from the water with its rope trailing, orange votive candles floating on the surface, a waterlogged congregation singing from hymnals, a ferryman's boat at a landing.`
- **The Barrow Halls** (Barrow Host): `Huge earthen burial-mound halls under the ground, timber-and-turf vaults, bronze lanterns, stacked shields and war horns, a stone throne for a chieftain wearing a bone-and-iron crown, warband dead sharpening bronze blades.`
- **The Sunken Ford** (the war front): `A wide underground river crossed by a shallow stone ford and a broken bridge, a huge glowing memory vein running through the cliff above it; on one bank a host of drowned parishioners with bells and votive light, on the other an army of barrow warriors with bronze lanterns and shields; hundreds of small figures, a battle about to begin, a tiny cute ghost watching from a ledge.`
- **The Candle Court** (Velvet Wake): `An elegant underground ballroom for an endless funeral feast: long tables, black lace, tall candelabras, mirrors draped in velvet, charming veiled mourners raising glasses; something slightly wrong (candles burning downward, a mourner whose reflection is missing).`
- **Ossuary Deep** (Bonewardens): `A cold cavern fortress built from stacked bones and skulls in tidy voxel patterns, white cold light, skeleton patrols in bone armor on the walls, a gate of ribs.`
- **Underveil map** `concept/locations/underveil_map.png`: `Top-down stylized map of an underground world of linked cavern regions joined by tunnels and dark rivers: a mushroom forest, a flooded chapel lake, earthen burial halls, a ford on the central river, a candlelit ballroom, a bone fortress, and three shafts leading up to a village on the surface. Readable like a game level map. No text, no labels, no frame.`

Clans (character add from 4.4; `concept/characters/clan_<name>.png`): one lineup per clan of a common
soldier, a captain, a banner or bell bearer and a civilian, all cute-spooky with no gore:
Mycelial Kin (mushroom-cap hats, spore lanterns), Drowned Parish (waterlogged Sunday clothes, hymnals,
bell ropes), Barrow Host (bronze, bone-and-iron crowns, earthen shields, war horns), Bonewardens (bone
armor, tidy skeletons), Velvet Wake (black lace, veils, wine glasses, a hidden tell on each).

## 5. Task files

`task1.md`–`task5.md`, written from the pipeline templates and scoped to the vertical slice:

| Task | Scope for the slice |
| --- | --- |
| task1 | Block textures and block library, cottage/mill/mausoleum architecture kits, hauntable props, spectral tools |
| task2 | Basic Ghost (rig: float, drift, glide, phase, mine, boo), villager rig and scare-reaction animations, worker ghost |
| task3 | Voxel terrain generator settings for the Open Plains, Millbrook/mill/graveyard landmark layouts as JSON stamped into the world, gameplay markers, night/dusk/day/fading light presets |
| task4 | Four villagers with fears, Belief and nightly schedules, hauntable object placement, ore and grave nodes, memory fragment tables, ambient effects |
| task5 | Godot game: third-person ghost controller, voxel chunks, mining, Creak and Flicker, Unease/Nerve and scare grading, town memory, journal, HUD, save/load, sound, `--autotest`, Windows and macOS builds |

## 6. Reference boards (`concept_art/`, from Scott)

These set the art direction. Every task that builds the matching asset reads its board first.

| Board | Use it for | Task |
| --- | --- | --- |
| `basic ghosts.png` | Player ghost model: turnaround, T-pose, glossy sheet material, eye shapes | task2 |
| `basic ghost.png` | Tool poses (scythe, shovel, sledgehammer), weeds/dirt/eerie-ore nodes, Spectral Workbench with anvil, worker ghosts | task1, task2, task4 |
| `mausoleum.png` | Mausoleum (mossy spectral stone, gargoyles, spiral emblems, violet glowing doorway), gravestones, worker spawns | task1 |
| `building and crafting.png` | Building tiers 1–4 kits: rough wood, mossy cut stone, riveted metal, ethereal crystal | task1 (tiers 1–2 for the slice) |
| `biomes.png` | Open Plains layout and village density (thatched cottages, windmill, well, fields, forest edge); later biomes for run 2 | task3 |
| `crypts.png` | Crypt dungeon, skeleton raiders/archers, demon portal, fire demon, imp, relic drops | run 2 |
| `witch.png` | Cauldron and spellbook stand (not yet in the design plan) | run 2 |
| `town raids.png` | Angry town mob (torch and pitchfork villagers) only | run 2 |
| `horror cosmetics.png` | Concept only: worker cosmetics and a relic display cabinet | run 2 |

**IP: do not build from these parts, and never attach these boards as image references:**

- `horror cosmetics.png` shows Jason's mask, Freddy's glove, Chucky, Michael Myers and Ghostface.
  Relics and cosmetics must be original designs on the same archetypes (design plan, IP note).
- `town raids.png` shows Ghostbusters: tan jumpsuits, proton packs, the no-ghost logo and the trap box.
  Ghost Hunters must use the design plan's own original gear instead: detection gear, salt guns,
  iron nets and spirit jars, with an original uniform and emblem.

## 7. Concept art status (run 1)

All 27 vertical-slice images from section 4 are in `concept/` (ordered 2026-11-15, `millbrook_night.png`
used as the style reference for the rest). Mood variants of Millbrook keep the exact same layout, so
`concept/empty/millbrook_empty.png` doubles as the layout reference for task3.

Known drift to ignore when building:

- `ui/title_screen.png` and a few UI screens draw the ghost with a small mouth and blush. The game model
  follows `concept_art/basic ghosts.png`: no mouth.
- `ui/hud.png` and `ui/inventory.png` show pickaxes and an axe among the tools. The game has only the
  scythe, shovel and sledgehammer (`characters/spectral_tools.png`).
- `ui/hud.png` shows Possession and Telekinesis bars at levels 3–5; the slice has only Haunting 1–2.
