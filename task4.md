# Task 4: Bring Millbrook to life (run 1: vertical slice)

## Mode: fully autonomous
- Don't ask questions or wait for confirmation. Make every decision yourself and record it in decisions.md.
- If something is unclear in the concept art, choose a reasonable option in the target style and continue.
- Don't wait for Blender MCP, Godot MCP or other tools to connect. Run Blender from the command line:
  `"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/scripts/<script>.py -- <args>`.
  Shell: Git Bash, never PowerShell.
- If a step fails, try another approach. If that fails too, record the problem in issues.md and move on.
- Don't stop until the task is complete. At the end write report_task4.md: what was done, what did not work.
- Look at your results and compare with the concept art before calling anything done.
- Read first: CLAUDE.md, docs/design/design-plan.md (especially "The scare: read, build, break" and
  "Keeping the 50th scare fresh"), `Ghostopia — concept art and tasks.md`, decisions.md, issues.md and
  report_task1–3.md.

## External assets
- Everything procedural in Python; characters come from task2, props from task1.

## Goal
Who lives in Millbrook, what each of them fears, where they are at every hour of the night, what can
be haunted in their homes, what lies in the ground, and what memories it holds, as data for Godot.
Plus ambient effects. All gameplay numbers here are placeholders marked `"tuning": true`; Scott tunes
feel later.

## Steps
1. **Villagers** (`assets/levels/millbrook_population.json`, `villagers`): for each, the task2 model,
   home, personality, `belief` (0–1), `fear` (one of: dark, dolls, being_alone, loud_noises, mirrors),
   `nerve` (how much Unease they take before breaking), `suspicion_rate`, `bravery_gain` (how much
   braver a botched scare makes them), muttered lines that hint at the fear (5–8 each, overheard when
   the ghost drifts close), and how they react when suspicious (fetch salt, light more candles, hang a
   charm). Defaults, recorded in decisions.md as Scott's to change:
   - **Widow Agnes** (windmill): high belief, fears **dolls** (her late daughter's doll on the shelf),
     sits up late in her rocking chair. The design plan's example scare is hers.
   - **Farmer Bram** (east cottage): medium belief, fears **loud noises**; the scare_reactions sheet is him.
   - **Tavern maid Wren** (tavern): high belief, fears **the dark**; closes the tavern late, walks home
     with a lantern.
   - **Schoolteacher Marlow** (cottage by the square): a **skeptic**, low belief, fears **being alone**;
     shrugs off small scares, but breaking him makes a lasting believer (big Remembrance).
   - **The child, Pip**, is a **witness, not a target**: Pip can't be scared, but sees scares and spreads
     the legend fastest (cute, not cruel). Record this as a decision Scott should confirm.
2. **Night schedule** (`schedule`, keyed to the task3 day/night cycle): dusk chores at the well and
   fields; evening at the tavern; walking home with lanterns (vulnerable routes: alone, dark stretches,
   the bridge); bedtime routines (relight the hearth, light candles, check the door); sleep; one villager
   who stays up late (Agnes in her chair, Marlow reading). Each step: marker, animation, duration,
   held item, and whether they are **alone** and **facing away** from common hiding spots.
3. **Hauntables** (`hauntables`): every task1 hauntable instance in the slice with its kind (door,
   floorboard, candle, oil lamp, rocking chair, wardrobe, portrait, doll, bell, scarecrow), which
   Haunting level it needs (Creak = doors and floorboards at level 1; Flicker = candles and lamps at
   level 2; the rest are level 3+ and only decorative in the slice), its Unease value, and which fears
   it plays into (a doll for dolls, a snuffed candle for the dark, a slammed door for loud noises).
   Make sure every villager's home and route has at least three level-1/2 hauntables and one object
   tied to their fear.
4. **Gathering nodes** (`nodes`): grave weeds and fiber grass (scythe), grave-dirt patches (shovel:
   dirt, bones, buried trinkets), eerie-ore and spectral-stone veins (sledgehammer), all at task3
   markers, with tier requirements and regrowth times.
5. **Memory fragments** (`assets/data/memory_fragments.json`): about 30 one-line vignettes of the people
   who lived and died here (tender, specific, a little melancholy; e.g. "She always saved the last
   pumpkin seed for next year."), each with an id, a source (which block or area drops it), an owner
   (which past person it belongs to; group them into 3 sets of 5 that later unlock named residents),
   and a sepia vignette subject for its journal card. Also drop tables per block from blocks.json.
6. **Town memory** (`town_memory`): what Millbrook remembers and how it adapts: repeat the same trick on
   the same object → that villager hangs a charm there (object un-hauntable for N nights); a botched
   scare → salt line across that door; a Legendary scare → a rumor line added to the tavern and the
   legend name grows ("the Creaking Ghost of Millbrook"). Rumor and legend text templates.
7. **Effects** (`fx`): chimney smoke, hearth and candle flames, lantern glow, fireflies and low mist at
   night, the stream's sparkle and waterfall spray, windmill sails turning, violet wisps rising from ore,
   ghostly glow at the mausoleum doorway, worker ghosts idling at the graves (2–3 for ambience only).
8. Render the populated scene from the concept cameras (night, dusk, day) to `renders/task4/` with
   villagers at their schedule positions, and compare with `concept/locations/*` side by side; fix
   style mismatches.
9. Document the population and fragment schemas in README.md. README "Rebuild": add the population
   command.
10. Commit everything with a message saying what was added.

## Result
`assets/levels/millbrook_population.json`, `assets/data/memory_fragments.json`, renders in
`renders/task4/`, README schema docs, report_task4.md.
