# Task 5: The game in Godot 4.7 (run 1: vertical slice)

## Mode: fully autonomous
- Don't ask questions or wait for confirmation. Make every decision yourself and record it in decisions.md.
- If something is unclear, choose a reasonable option in the target style and continue.
- Don't wait for Godot MCP or other tools to connect. Godot: `/c/Tools/Godot/godot.exe` (editor/run),
  `/c/Tools/Godot/godot_console.exe` (headless). Shell: Git Bash, never PowerShell.
- If a step fails, try another approach. If that fails too, record the problem in issues.md and move on.
- Don't stop until the task is complete. At the end write report_task5.md: what was done, what did not
  work, and **open questions for Scott about feel and tuning** (don't guess silently).
- Look at your results (autotest screenshots, tours) and compare with the concept art before calling
  anything done.
- Read first: CLAUDE.md, docs/design/design-plan.md (source of truth for every mechanic),
  `Ghostopia — concept art and tasks.md`, decisions.md, issues.md, report_task1–4.md, README schemas.

## External assets
- Sounds and music: free CC0/CC-BY only (Freesound, OpenGameArt, Kenney, Sonniss GDC bundles): creaks,
  door slams, floorboards, candle snuff, wind, crickets and night ambience, stream, windmill, tavern
  murmur, villager gasps/screams/laughs (cartoony, not horror), ghost whooshes and a soft "boo", mining
  hits per material, UI clicks, a cozy-eerie music box theme for the menu and a gentle night theme.
- Godot Asset Library only for things like sky/water shaders if they support 4.7.
- Record every downloaded asset in assets/CREDITS.md. If a site needs a login, skip it.

## Goal
A playable vertical slice that answers the prototype gate in the design plan: **is scaring a villager
with a creaking door and a snuffed candle fun?** Built at runtime from the task1–4 data.

## Steps
0. **Setup.** Install the Godot 4.7.2 export templates if missing (official `.tpz` from
   godotengine.org or the godotengine GitHub release → `%APPDATA%/Godot/export_templates/4.7.2.stable/`).
   Import the project: `godot_console --headless --path . --import`.
1. **Voxel world** (`scripts/voxel/`): a custom chunk mesher in GDScript (16³ chunks, face culling
   between opaque blocks, atlas UVs from blocks.json, a slight per-vertex jitter and the baked bevel so
   blocks look hand-made, not pixel-perfect), meshing on `WorkerThreadPool`, collision per chunk with
   **phaseable blocks on their own physics layer**, a transparent pass for water/glass, block
   break/place that remeshes only touched chunks. Load `millbrook_voxels.bin`, then instance props and
   structures' props from `millbrook_layout.json`. This decides the design plan's open question
   (custom mesher vs. the Voxel Tools module): record the decision and the measured meshing time and
   FPS in decisions.md so Scott can revisit it.
2. **The ghost** (`player.gd`): third-person chase camera (orbit with mouse/right stick, soft collision,
   pulls in inside cottages). Drifting: hovers about 1 block above the ground, glides down with no fall
   damage, ascending costs Ectoplasm. **Phasing** through phaseable blocks and props (not stone, ore,
   iron, salted/blessed blocks); the camera stays readable when inside a wall. **Running water** stops the
   ghost (the plank bridge is the crossing). Weightless: only spectral items. HP 10, Spectral.
   **Inverted day:** daylight drains HP slowly unless in a `shelter_*` area or underground; dawn warning.
   At 0 HP: **Scattered** (scatter animation + wisps), respawn at the mausoleum, drop some Fright Essence
   where you fell.
3. **Gathering and building:** scythe / shovel / sledgehammer on their nodes and blocks (tool and tier
   rules from blocks.json, swing animations, hit sounds, cracks), drops, and **memory fragments**
   floating out of mined natural blocks into the **journal**. Place blocks from the hotbar. Spectral
   Workbench in the mausoleum: craft tier II tools (the "harvest tier 2 nodes" loop on the gathering board).
4. **Scaring** (`scripts/scare/`, the heart of the slice; follow the design plan's read → build → break):
   - **Read:** drifting close lets you overhear the villager's muttered lines (speech bubbles), which hint
     at their fear; a small "fear discovered" note in the journal once you have heard enough.
   - **Build:** villagers have Unease (0–100), Belief, Nerve and a hidden fear. **Creak** (Haunting 1:
     doors, floorboards) and **Flicker** (Haunting 2: dim or snuff candles and lamps) raise Unease, more
     when they match the fear. Visible escalation with the task2 animations: glance over the shoulder,
     "hello?", clutch the candle, walk faster. **Sweet spot:** push too hard too early and they bolt
     (weak payout) or turn suspicious (fetch salt, relight candles, hang a charm), which makes them harder.
     Unease decays when you back off. Show it as the candle-flame meter above the head (HUD concept).
   - **Break:** **BOO** (manifest) when Unease is high and the target is vulnerable (alone, back turned,
     in a rigged doorway): the big funny reaction (big_scare_leap, hat flies, lantern drops, scream,
     a brief slow-motion beat, camera punch-in), graded **Spooked / Terrified / Legendary** from timing,
     fear match, vulnerability and combo of different objects. Fright Essence pays out to the Haunting
     path and Presence; Legendary unlocks a little celebrate animation.
   - **Failure is entertaining:** a botched BOO makes them laugh it off and grow braver, or spot you.
   - **Town memory and legend** from task4: charms and salt appear on used objects; rumor lines at the
     tavern; the legend name grows; Pip the child witnesses and spreads it.
   - **Remembrance:** per-area value from task3 areas; decays slowly, restored by scares (more for
     believers and Legendary grades); low Remembrance blends toward the `fading` look (desaturate,
     flicker block edges). No erosion of blocks in the slice. Heat is tracked and shown but has no
     consequence yet (Ghost Hunters are run 2).
   - **Progression:** Haunting starts at level 1 (Creak); enough Fright unlocks level 2 (Flicker).
     Presence raises HP, scare radius and manifest time. Keep all numbers in one data file
     (`assets/data/tuning.json`) so Scott can tune feel without touching code.
5. **Villager AI** (`npc.gd`): follows the task4 schedule, walks with the foot-planted animations at
   no-slide speeds, reacts to the scare system, flees home, relights candles, becomes suspicious, sleeps.
   Simple steering on the voxel ground first; add navigation only if they get stuck.
6. **Cycle:** inverted day/night from the task3 presets (night is play time, about 12 real minutes,
   `tuning`), smooth transitions, mood-dependent emission (windows, candles), ambience per mood. Sleep in
   the mausoleum to skip the day.
7. **UI as code** (one UiKit matching concept/ui: translucent dark slate panels, cyan corner brackets,
   white and gold rounded headings): title screen (the painted `concept/ui/title_screen.png` copied to
   `assets/ui/` with invisible buttons over its menu), HUD (HP, Ectoplasm, moon clock "until daylight",
   hotbar, Haunting Fright bar and level, Unease meter over the targeted villager, scare-grade stamp,
   overheard lines), journal (memory fragment cards, discovered fears, the legend), inventory with the
   workbench, the Scattered screen, pause and settings (audio, graphics, controls, mouse sensitivity,
   invert Y). Only the three real tools appear (no pickaxes or axes from the UI concept drift).
8. **Sound** per the list above; positional creaks and screams; music per state.
9. **Save/load:** world block edits, inventory, path levels, fragments, villager memory and charms,
   Remembrance, time of day. Autosave at dawn and on quit.
10. **Tests:** unit tests for pure logic (Unease math, grading, fear matching, block rules, drop tables,
    tuning loading) with `tools/run-tests.sh`; all must pass.
11. **`--autotest`:** plays through the core loop: drift, phase through a wall, get stopped by the stream,
    cross the bridge, mine each node type and collect a fragment, craft a tier II tool, Creak a door near
    a villager, Flicker a candle, land a BOO and get a grade, trigger a suspicious villager, get a charm
    hung, level Haunting to 2, dusk → night → dawn, get Scattered by daylight and respawn, open every UI
    screen, save, load, quit. Writes `renders/game/*.png` and `autotest.log` (`AUTOTEST` lines). Add
    `--tour` with views matching each concept image and compare them side by side.
12. **Ship** (pipeline 06, adapted: Windows and macOS, no web host): commit everything; export
    `Windows Desktop` → `build/windows/Ghostopia.exe` and `macOS` → `build/macos/Ghostopia.zip`
    (unsigned; note in README that Mac players right-click → Open the first time); run the exported
    Windows build with `--autotest` and check its log; record build sizes. Push only if Scott asks.

## Result
Playable Windows and macOS builds, the Godot project, README.md with controls and the full rebuild
steps, `assets/data/tuning.json`, passing unit tests and autotest, report_task5.md with Scott's open
questions about feel.
