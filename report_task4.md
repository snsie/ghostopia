# Task 4 report: Millbrook comes to life (vertical slice)

## Done

- **Population data** (`assets/levels/millbrook_population.json`; schema in README "Population data"). Every gameplay
  number is a placeholder marked `"tuning": true`.
  - **Five villagers:**
    - Widow Agnes (mill) fears dolls: her late daughter Elsie's doll, Button.
    - Farmer Bram (east cottage) fears loud noises.
    - Wren (tavern maid, cottage_b) fears the dark.
    - Schoolteacher Marlow is the skeptic who fears being alone.
    - Pip is a witness, not a target.
  - **Per villager:** the task2 model, home, bed, personality and backstory, belief, fear, nerve, suspicion rate and
    bravery gain. Each has 6–7 muttered lines that hint at the fear, three escalating suspicious reactions (more
    candles, turning the doll to the wall, a horseshoe or charm on the door, salt), a break and a botch reaction.
    Marlow becomes a lasting believer when broken.
  - **Night schedules** cover one full cycle (17:00 → 17:00), keyed to the task3 day/night cycle (clock hours plus cycle
    `t`, no gaps). The night runs dusk chores at the well and fields → the tavern → walks home with candles and
    lanterns → bedtime (hearth or candle, check the door) → late sitters (Agnes rocking until 01:30, Marlow reading until
    01:15) → sleep → simple day plans.
  - **Each step** carries a marker or target prop, position and yaw, task2 clip and held item. It also records whether
    the villager is **alone**, who they are with, and which hiding spots are **behind** them.
  - **Walks** are real routes, found by A* over the voxel surface (paths preferred, furniture and fences avoided, the
    mill ladder as a link). Each has its length and speed, **dark stretches** away from lanterns and lit windows, the
    **bridge** crossing (Marlow's lone evening walk), and the hauntables and hiding spots along it.
  - **78 hauntables:** all 46 task1/task3 instances, plus 27 lanterns as Flicker targets, plus 5 carried lights (the
    candle in Agnes's hands, Wren's lantern...). Each has its kind, Haunting level (Creak 1: 14, Flicker 2: 48,
    decorative 3+: 16), Unease per action, fears, noise radius and cooldown.
  - **Coverage per villager:** 4–7 level-1/2 hauntables at home, 7–14 on their routes, and a fear object. The build
    computes this and the unit test checks it. For Agnes, the candle she keeps lit beside Button counts for her fear,
    so even Flicker reaches it.
  - **93 gathering nodes** on task3 markers: grave weeds, fiber grass, grave dirt, eerie-ore, spectral-stone and iron
    veins. Each has its tool, tier, hits, yields (from blocks.json), and regrowth in seconds and nights; ore re-forms
    only while Remembrance holds.
  - **Scare rules** for task5: Unease stages with clips and expressions, bolting, fear multiplier, grade scoring for
    Spooked / Terrified / Legendary (the design plan's Agnes example scores Legendary), payouts and suspicion.
  - **Town memory:**
    - Repeating a trick on the same object makes that villager hang a charm there; the object is un-hauntable for 3
      nights.
    - A botch puts a salt line across a door.
    - A Legendary scare adds a tavern rumor, and the legend name grows through stages up to "the {epithet} Ghost of
      Millbrook", with epithets per trick.
    - Ten rumor templates with pronoun placeholders.
  - **Effects (65 entries):** chimney smoke from each real chimney, hearth, candle and lantern flames bound by node
    prefix, fireflies and low mist zones, stream sparkle and waterfall spray (from the task3 water cells), the windmill
    sails' spin and the tavern sign's swing, violet wisps on every exposed eerie-ore face, the mausoleum doorway glow,
    gravestone wisps, and three worker ghosts idling at the graves.
- **Memory fragments** (`assets/data/memory_fragments.json`): 30 one-line vignettes, each with an owner, emotion,
  source blocks and areas, and a sepia journal-card subject.
  - **Three sets of five** unlock the worker ghosts as named residents: Hob Ashdown the blacksmith, Marigold Finch the
    gardener, Ned Ollery the baker.
  - **The other 15** are partial sets for run 2: Elsie and Josiah Brook (Agnes's family, so Button's story pays off),
    Old Wynn the bell-ringer, Hettie Lark, and three strays, including the kite child from the mining concept.
  - **Drop tables** for all 15 fragment-dropping blocks, each with at least 2 entries; every fragment drops from some
    block.
- **Code:**
  - `blender/scripts/lib_population_content.py`: the hand-written content.
  - `lib_population.py`: routing, cycle timing, analysis, checks, output (plain Python, deterministic, about 1 s).
  - `build_population.py`: the driver.
  - `population_render.py`: posing in Blender.
  - `tools/population_map.py`: the route map.
  - `build_island.blender_main` gained a render hook so task4 renders the exact task3 scene; task3 output was rebuilt
    and is byte-identical.
- **Renders** (`renders/task4/`):
  - Millbrook night / dusk / day, a closer square shot at night / dusk, the cottage interior night / day, the mill at
    night, the graveyard night / day.
  - Everyone stands at their schedule position for the shot's hour, with held items attached.
  - A `compare_*.jpg` for each shot (concept left, render right).
  - `population_map.png`: every route with its dark stretches, plus stops, hauntables and nodes.
- **Tests:** `tests/test_population.gd` (9 tests) checks that references resolve, the schedules are continuous and
  cover a cycle, Creak/Flicker levels, coverage, nodes, fragment sets and drop tables, town memory and effects. All 24
  project tests pass, and the Godot import is clean.
- README has the "Rebuild" command and the population and fragment schemas. decisions.md has the task4 conventions and
  the defaults Scott should review; issues.md is updated.

## Compared with the concept art

- **Millbrook night and the square close-up:** Bram (straw hat, lantern) and Marlow (lantern) cross the square with warm
  pools of light under them, Wren serves at the tavern's outdoor tables, chimney smoke rises and fireflies drift. That
  is the concept's "villagers walk with lanterns" moment. After the first comparison, Marlow got a lantern for her
  night walks: she had been a dark, unlit figure.
- **Millbrook dusk:** Agnes draws water at the well with Pip beside her, Marlow reads the charm board, and Bram works
  the wheat edge, like the busy dusk square of `millbrook_dusk.png`.
- **Cottage interior night:** Pip in the nightcap holds a candle by the wardrobe, the pose of the concept's child.
- **Mill night:** Agnes sits in the rocking chair with her candle beside Button's shelf.
- **Graveyard night:** the gardener and baker ghosts idle among the graves, the portal glows violet, and wisps rise from
  the ore outcrop.

## Not done / weaker than the concept

- **Villagers look small.** At true scale they are a few pixels tall in the wide Millbrook view, while the concept paints
  them about twice as large relative to the houses. That is why the closer square shot exists.
- **Agnes is seen from behind in the mill render.** The task3 chair faces away from that camera; in the concept she
  faces the viewer.
- **Effects are Blender stand-ins** (translucent and emissive spheres) for the previews. The data describes real
  particles for Godot. The windmill sails don't turn in a still render.
- **Lantern light reads violet-pink** on the blue night cobbles instead of the concept's warm orange. Lighting is the
  task3 preset; Godot should warm it in task5.
- **Missing pieces for task5:**
  - No tray prop for Wren's serving.
  - No mirrors anywhere, so no villager fears mirrors.
  - No climb clip for the mill ladder (the route marks the ladder waypoints).
- **Placeholders for Scott to review:** every number, plus the cast decisions: Pip as witness, Marlow's pronouns
  (she/her to match the task2 model; the task text says "him"), and Pip's household (parents away, cousin Wren looks in).
- **The test framework counts a GDScript runtime error as a pass** (seen once, now fixed in the test). Task5 should
  harden it.
- **No builds.** There is still no main scene or export presets; the game and its Windows/macOS builds start in task5,
  as with tasks 1–3.
