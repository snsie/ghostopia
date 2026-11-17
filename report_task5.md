# Task 5 report: the game in Godot 4.7 (run 1, vertical slice)

## Done

- **Playable builds:**
  - `build/windows/Ghostopia.exe`: 133.9 MB, a single file with the pck embedded.
  - `build/macos/Ghostopia.zip`: 80.4 MB, universal, ad-hoc signed, not notarized. Mac players right-click → Open the
    first time (in the README).
  - The exported Windows build passes the full `--autotest` (46/46, `renders/game/autotest_windows_build.log`).
- **Export templates** 4.7.2 installed from the official `.tpz` (only the Windows x86_64 and macOS ones are unpacked).
  The block atlases now import as Texture2DArray.
- **Voxel world** (`scripts/voxel/`):
  - A custom threaded GDScript chunk mesher: 16³ chunks, face culling, atlas layers, per-vertex AO, slight vertex and
    brightness jitter on top of the baked bevel.
  - Separate passes for plants and water.
  - Per-chunk collision, with phaseable blocks on their own layer, and the running-water spirit barrier.
  - Block break and place remesh only the touched chunks; edits are saved as a diff.
  - Props and structure props are stamped from `millbrook_layout.json`.
  - **Decision: custom mesher, not Voxel Tools.** Meshing takes 1.9 s (editor) / 0.9–1.1 s (release) for 254 chunks
    and 100k faces; about 111–114 FPS (decisions.md).
- **The ghost:**
  - Chase camera that orbits (mouse / right stick), springs off walls and pulls in indoors.
  - Hovers about 1 block up, glides down, and rising costs Ectoplasm.
  - Phases through soft blocks and wooden props but not stone, ore or salt; an x-ray silhouette keeps it readable
    inside walls.
  - Stopped by the stream; crosses on the bridge.
  - Daylight drains HP outside shelters, with a dawn warning. At 0 HP it is Scattered (scatter clip, wisps), drops
    35 % of its Fright Essence where it fell (recoverable) and respawns at the mausoleum.
  - Sleeping in the mausoleum skips the day.
- **Gathering and building:**
  - Scythe, shovel and sledgehammer with the blocks.json tool and tier rules and task4 node hit counts, swing
    animations, hit sounds and crack overlays.
  - Drops go into the inventory.
  - Memory fragments float out of natural blocks into the journal.
  - Blocks are placed from the hotbar.
  - The Spectral Workbench crafts tier II tools and two block recipes.
- **Scaring** (`scripts/scare/`), read → build → break:
  - **Read:** drifting within 4 m lets you overhear a villager's muttered lines (speech bubbles and a HUD log). Three
    different lines reveal their fear: a toast, the journal's Villagers page, and the fear shown on the Unease meter.
  - **Build:** Creak (doors and floorboards) and Flicker (dim or snuff candles, lamps, lanterns and the lights villagers
    carry) raise Unease, with a fear-match multiplier, belief and the skeptic threshold.
    - Escalation uses the task2 clips: glance over the shoulder, "Hello? Who's there?", startle, uneasy and
      clutch-candle walks, and face expressions.
    - Overflow makes them bolt for a weak payout, and suspicion triggers each villager's reactions: more candles, the
      doll turned to the wall, Bram's pitchfork search, Marlow's investigation, charms, salt.
    - Unease decays after 6 s of quiet.
    - The Unease meter is a candle flame over the head, with a sweet-spot mark.
  - **Break:** BOO (manifest) is graded Spooked, Terrified or Legendary from primed, peak, fear match, alone, back
    turned, abilities, three different objects and a rigged doorway.
    - The big reaction: `big_scare_leap`, the hat flies off, the held light drops as a physics prop, a scream, a 0.6 s
      slow-motion beat, a camera punch-in and the grade stamp.
    - Legendary plays the ghost's celebrate clip.
  - **Failure:** an early BOO makes them laugh it off and grow braver; being seen gets "I SEE you!" and suspicion. Both
    salt a doorway.
  - **Town memory:** charms on objects reused across scares; salt lines that block the ghost; tavern rumors from the
    task4 templates, heard when the ghost drifts into the tavern; the legend name grows ("a draught in Millbrook" →
    "the Ghost of Millbrook" → "the Candle-Snuffing Ghost of Millbrook"); Pip witnesses (×3 legend points, "Did you SEE
    that?!").
  - **Remembrance:** per area, decays slowly and is restored by scares (×3 for believers). Low values blend the voxel
    shader and the whole mood toward `fading`: desaturated, with flickering violet block edges. **Heat** is tracked and
    shown with no consequence.
  - **Progression:** Haunting 1 Creak → 2 Flicker at 25 Fright. Presence raises HP, scare radius and manifest time.
    Every number is in **`assets/data/tuning.json`**.
- **Villager AI** (`npc.gd`):
  - Follows the task4 schedule by clock at the clips' no-slide speeds, with held items.
  - Reacts to the scare system, flees home (A* over voxels), relights candles, gets suspicious, sleeps and wakes to
    noise.
  - Doors open for them, and their carried lights are Flicker targets.
- **Cycle:** the inverted day/night from the task3 presets with smooth blends: custom sky, moon and sun, fog, exposure,
  saturation, glow, mood emission for windows and lanterns, and particle FX per mood (smoke, fireflies, mist, wisps,
  spray, worker ghosts). Night lasts 12 real minutes (`tuning.cycle.length_s`).
- **UI as code** (one `UiKit`):
  - The painted title screen with invisible buttons over its menu.
  - HUD: HP and Ectoplasm, a moon clock "until daylight" / "until nightfall", the hotbar with rendered tool icons,
    Haunting level and Fright bar, Presence, Heat and legend, candle-flame Unease meters, the grade stamp, overheard
    lines, toasts and target hints.
  - Journal: fragment cards, a Villagers page with discovered fears, a Legend page with rumors, charms and Remembrance.
  - Inventory with the workbench.
  - The Scattered screen, pause, and settings (audio buses, graphics toggles, render scale, mouse sensitivity,
    invert Y, controls list).
  - Only the three real tools appear.
- **Sound:** 63 files. They are synthesized creaks, slams, snuff, relight, whooshes, a cute BOO, gasps, cartoony
  screams and laughs, "hello?", mining hits per material, chimes and UI blips. Ambience: wind, crickets, stream,
  windmill and tavern murmur. Music: a music-box menu waltz and a night theme. Ten CC0 Kenney variants are added on top.
  Creaks, screams, mining and footsteps are positional; ambience layers fade by mood and place; music changes by
  state. Credits are in `assets/CREDITS.md`.
- **Save/load** (`user://save.json`): world block edits, inventory and tools, path Fright, Presence and essence,
  fragments, villager memory (nerve, suspicion, believer, heard lines), town memory (charms, salt, legend, rumors,
  Remembrance, Heat), node regrowth, dropped essence, time and position. Autosaves at dawn and on quit.
- **Tests:** 62 unit tests pass (`tools/run-tests.sh`). They cover Unease math, grading, fear matching, the botch and
  bolt rules, town memory, block rules, drop tables, fragment rolls, inventory and crafting, tuning loading, and the
  voxel mesher and world. A `SCRIPT ERROR` now fails the run.
- **Self-tests:**
  - `--autotest` plays the whole loop in about 2 minutes, 46 checks. It covers drifting, phasing through a wall, being
    stopped by the stream, crossing the bridge, and mining all six node types for a fragment. It crafts Sledgehammer II
    and mines tier II ore, and overhears Agnes until her fear is revealed (Flicker is locked at level 1). It Creaks the
    mill door until she's primed, then lands a BOO from behind (Terrified, which reaches Haunting 2). Next it runs
    Flicker plus Creak until she's suspicious, a Legendary break and a charm on the reused door, then a botched BOO on
    Bram. Finally it runs dusk → night → dawn with a new night and the dawn autosave, gets Scattered by daylight and
    respawns, sleeps through the day, opens every UI screen, and saves, loads and quits.
    Output: `renders/game/*.png` and `autotest.log`; a contact sheet is committed as
    `renders/game/contact_autotest.jpg`.
  - `--tour` shoots a view for each concept image; `renders/game/compare_*.jpg` sets each beside its concept and
    `contact_tour.jpg` collects them.

## Compared with the concept art

- **Millbrook night** (`compare_millbrook_night.jpg`): the layout matches, with warm windows, lantern pools, chimney
  smoke, the well, the charm board and the windmill on the rise. The concept is warmer, more saturated and busier: purple
  wisteria trees, ruins on the horizon, a huge moon in frame, and villagers drawn about twice their true size. The game's
  distance fog is a flat lavender.
- **Graveyard night:** the mausoleum's violet portal, candles, gravestones, worker ghosts and the eerie-ore outcrop read
  well. The concept's moss and overgrowth are much denser.
- **HUD** (`compare_hud.jpg`): same layout and style. The concept's Possession and Telekinesis bars aren't in the slice,
  and the scare-grade stamp matches.
- **Title, journal, inventory, Scattered, settings:** the same slate-and-cyan and parchment language. The journal cards
  show the vignette text instead of painted sepia images.
- **Cottage interior and mill:** they read as cosy, candle-lit rooms. The concept's cutaway framing isn't possible
  with real walls.

## Not done / weaker

- **No painted sepia vignette images** for fragment cards (text cards instead), and no ghost paper-doll in the
  inventory (cosmetics are run 2).
- **Audio is synthesized,** apart from a few Kenney files. It fits the cute tone, but the voices (screams, laughs,
  "hello?") are obviously synthetic. Real CC0 voice recordings would sell the comedy better.
- **Villagers are small** at true scale next to the concept's chunky characters, and their Unease meter is the only
  readable cue from far away.
- **The mill ladder is never climbed** (no climb clip, task4 issue). The loft candle is still a Flicker target from below.
- **No tray for Wren** (task4 issue): she serves empty-handed.
- **Rain doesn't exist,** so salt lines never wash away early.
- **Heat has no consequence** (Ghost Hunters are run 2), as the task asks.
- **Only tested on this Windows PC.** The macOS zip was exported and contains a signed `.app`, but nobody has launched
  it on a Mac yet.

## Open questions for Scott (feel and tuning; nothing was guessed silently — all in tuning.json)

1. **Is the scare fun?** The prototype gate itself. The autotest's Agnes scares take about 8 acts over 50 s with
   doors only, or 4–5 acts with candles. Is the sweet spot (80–100 % of nerve, the violet mark) wide enough, or does it
   feel fiddly? Knobs: `scare.stages`, `scare.overflow_at`, per-villager `nerve`.
2. **Town memory per scare vs per act:** I count a trick once per finished scare (a charm when an object is reused in a
   later scare within 2 nights), because the task4 per-act rule charmed a door on its second creak. Is that the
   adaptation you want, or should towns react faster?
3. **Botch salt lines:** every botch and bolt salts the nearest doorway for 2 nights. Too punishing for a ghost that's
   still learning?
4. **Flicker at 25 Fright** (one Terrified scare). Should Flicker come later, so the first night is all Creak?
5. **Daylight drain** of 0.16 HP/s (about 60 s from full to Scattered, half rate at dawn) and dropping 35 % of carried
   Fright Essence. Harsh enough to matter, gentle enough to be fun?
6. **Night length** is 12 minutes. Enough time to drift down (~35 s), read a villager and land two or three scares?
7. **The ghost's speed** (3.2 m/s, 5.2 with Shift), hover 1.05 m, rising 2.6 m/s at 14 Ecto/s, max 9 m above ground.
   And the camera: 3.4 m behind, 1.6 m indoors.
8. **Unease decay** waits 6 s after the last act, then drains 0.6/s (Agnes). Should villagers calm down faster, so you
   have to commit, or slower, to allow setups?
9. **Pip as witness** (×3 legend, but counts as company, so no "alone" bonus nearby). Is that trade-off right?
10. **Marlow's pronouns** (she/her, from task4) and **Pip's household**: still open from task4.
11. **The look:** should the night be darker and warmer (more like the concept), and should villagers be scaled up
    toward the concept's chunky proportions?

## Commits

One task5 commit: the code, data, assets, docs and comparison sheets. Raw screenshots and builds are gitignored.
