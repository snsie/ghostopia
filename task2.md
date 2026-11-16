# Task 2: The ghost, villagers and worker ghosts (run 1: vertical slice)

## Mode: fully autonomous
- Don't ask questions or wait for confirmation. Make every decision yourself and record it in decisions.md.
- If something is unclear in the concept art, choose a reasonable option in the target style and continue.
- Don't wait for Blender MCP, Godot MCP or other tools to connect. Run Blender from the command line:
  `"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/scripts/<script>.py -- <args>`.
  Shell: Git Bash, never PowerShell.
- If a step fails, try another approach. If that fails too, record the problem in issues.md and move on.
- Don't stop until the task is complete. At the end write report_task2.md: what was done, what did not work.
- Look at your results (preview renders, contact sheets, animation strips) and compare with the concept
  art before calling anything done.
- Read first: CLAUDE.md, docs/design/design-plan.md, `Ghostopia — concept art and tasks.md`
  (sections 6–7), decisions.md (task1 conventions: obey them), issues.md, report_task1.md.
- Original IP only. Never model anything from `concept_art/horror cosmetics.png` or the Ghostbusters
  parts of `concept_art/town raids.png`.

## External assets
- Build all models, rigs and animations yourself in Blender with Python scripts. No paid 3D generation.
- Animations: make them in Blender first. Only if they still look bad after several attempts (foot
  sliding, jerks, unnatural poses), find a free CC0/CC-BY one and retarget it to your rigs; record it in
  assets/CREDITS.md. If a site needs a login, skip it.

## Goal
Rigged, animated glTF characters for the slice, in the same style and scale as task1 (1 block = 1 m).

## Inputs
- **Player ghost:** `concept_art/basic ghosts.png` (turnaround, T-pose, glossy sheet material, eye
  shapes) and `concept_art/basic ghost.png` (tool-holding poses). These override every other image:
  **no mouth**; the drift in `concept/ui/` (mouth, blush) is to be ignored.
- `concept/characters/villagers.png` (front/side/back of five villagers), `scare_reactions.png`
  (the farmer's reaction stages), `worker_ghosts.png`, `spectral_tools.png`.
- `concept/locations/cottage_interior_night.png`, `mill_night.png`, `mining_night.png` for poses in context.

## Steps
1. Write `characters_list.md`: each character's height, silhouette, materials, held items, and the
   animation list below, plus (after step 5) the drift/walk/run speeds at which nothing slides.
2. **Basic Ghost (player), ~0.6 m:** a rounded head and a cloth sheet with a soft rippling hem, no legs.
   Glossy white material with a pale ice-blue rim/fresnel glow and a soft translucency; a separate
   **manifested** material state (more opaque, brighter) that Godot switches to when the living can see
   it. Eyes: two dark ovals as separate meshes driven by shape keys (neutral, angry slant, wide/scared,
   happy squint, closed). Sheet arms that are hidden inside the sheet at rest and extend for holding
   tools and for the BOO pose. Rig: a small spine chain for the sheet body and head, arm chains,
   2–3 hem bones for secondary motion. `HELD_tool` empty in the right hand that fits the task1 tool `GRIP`.
   Animations (separate NLA tracks, 24 fps, short names): `idle_float` (gentle bob, hem ripple),
   `drift` (forward lean, trailing hem), `glide_down`, `ascend`, `phase` (squash and stretch through a
   wall), `swing_scythe`, `dig_shovel`, `smash_hammer`, `haunt_cast` (reaching into an object to haunt
   it), `boo` (big manifest scare: rise, arms out, eyes wide), `hurt`, `scatter` (burst apart; Godot adds
   the wisp particles), `celebrate` (after a Legendary scare).
3. **Villagers (one shared humanoid skeleton, ~20 bones):** chunky cartoon proportions from the sheet:
   the elderly widow (shawl, candle), the burly farmer (overalls, straw hat, pitchfork), the tavern maid
   (apron, lantern), the skeptical schoolteacher (glasses, crossed arms, satchel), the child (nightshirt,
   cloth doll). Bodies from lofts, clothes as shells, skinning by code (≤3 bones per vertex), each wears
   its charm (garlic, horseshoe, salt pouch). Faces: eyes and brows as shape keys or texture swaps for
   calm / uneasy / scared / terrified / relieved. Held-item empties `HELD_R` / `HELD_L` for candle,
   lantern, pitchfork, book, doll; hat as a separate node so it can fly off.
   Shared animations: `idle`, `walk`, `walk_uneasy` (faster, glancing), `look_over_shoulder`,
   `call_out` (raise lantern: "hello?"), `clutch_candle_walk`, `startle` (small jump), `big_scare_leap`
   (the huge leap from scare_reactions.png: arms up, hat off, lantern dropped), `flee`, `laugh_it_off`,
   `suspicious_search` (looking around with a lantern), `hang_charm`, `scatter_salt`, `relight_candle`,
   `sit`, `rock_in_chair` (widow), `sleep`, `sweep` / `work_field` / `serve_drinks` (one work loop each).
   No root motion; foot-planted IK gait so feet don't slide.
4. **Worker ghosts:** small (~0.45 m) versions of the player ghost body wearing the blacksmith, gardener
   and baker outfits from worker_ghosts.png; animations `idle_float`, `carry` (holding a block),
   `work` (tool loop). The Forgotten Soul is run 2: skip it.
5. Export each to `assets/characters/<name>.gltf` with its animations; render a turnaround and an
   animation strip (8 frames per clip) per character to `renders/task2/`, and one contact sheet with
   everyone side by side at true scale next to a 1 m block and a task1 cottage door.
6. Check scale against task1: villagers fit through cottage doors and under ceilings; the ghost floats
   at about villager waist height when hovering 1 block up.
7. README "Rebuild": add the character commands after task1's.
8. Commit everything with a message saying what was built.

## Result
characters_list.md (with no-slide speeds), rigged and animated glTF characters, renders and contact
sheets in `renders/task2/`, report_task2.md.
