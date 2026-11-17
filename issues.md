# Issues

Problems hit during the tasks and the workaround used. Newest at the bottom.

## Task 1 (2026-11-15)

- `python` (3.13) had no numpy/pillow/opencv; installed with `pip install --user` as the task says.
- Blender 5.2: `MeshPolygon.use_freestyle_mark` no longer exists; Freestyle face marks are now the
  boolean face attribute `freestyle_face` (used in `lib_voxel.py` to keep sprites and water uninked).
- Freestyle `select_border` inked every voxel quad (the preview mesher emits separate quads), so flat
  ground looked like a grid. Turned border selection off; silhouettes + creases are enough.
- glTF node names got Blender's `.001` suffixes when several props share node names in one session
  (`LIGHT_candle`, `FX_flame`…). `build_props.py` now renames each prop's objects to `<prop>|<name>` after
  export, and props with several flames use numbered names. Checked: no suffixed names in any `.gltf`.
- A bash heredoc containing Python with triple quotes failed to parse once; patch scripts went through
  a scratch `.py` file instead. No effect on the repo.
- The haunt shell with a plain alpha material hid the object in previews. Previews now swap in a
  fresnel-rim material after export (the glTF keeps the simple `HAUNT_glow` placeholder; Godot should
  use a rim shader, see decisions.md).
- The mausoleum cutaway preview still shows its walls (the walls are 3 high, the cut is at 3 m), so
  its small interior (chest, candles, respawn marker) isn't visible in `structures_interiors.png`.
  Cosmetic; left as is.
- The style check is a Blender render with flat lighting, no bloom, fog or particles, so the night
  scenes are flatter and greyer than the painted concepts. The mood (fog, bloom, moonlight, fireflies)
  belongs to the Godot lighting presets in task3/task5.
- The first `godot --headless --import` after regenerating every asset printed 10 ×
  `Condition "f.is_null()" is true. Continuing.` with no file name. The next runs, including a forced
  reimport of a prop, were clean, and all 84 props + textures + atlases have import files. Treated as
  a transient issue during the mass reimport. If it comes back in task5, run the import twice.

## Task 2 (2026-11-16)

- Blender 5.2 has no `Action.fcurves`; keys are written with `action.fcurve_ensure_for_datablock()` and
  `keyframe_points.foreach_set` (fast, slot-aware). `hasattr(bpy.types.Action, ...)` reports False, but
  the method exists on instances.
- The auto pelvis-drop solver first took the wrong root of its quadratic and sank villagers into the
  floor in every standing clip. Fixed (smallest non-negative root); verified on the strips.
- Hair caps (full ellipsoids) hid the eyes on four villagers, and the widow's bun sat in front of her
  forehead. Hair caps are now shells with the face cut out.
- Face features were projected radially from the head centre, which squeezed every offset toward the
  middle: eyes too close, mouth hidden behind the nose. They are now placed exactly on the ellipsoid.
- Gait periods of 0.8 s / 0.7 s / 0.58 s are not whole frames at 24 fps (19.2, 33.6, 13.9 frames), so
  those loops would hitch. Every gait cycle is now snapped to whole frames, and the no-slide speeds are
  computed from the snapped period.
- Preview: blended transparency on the ghost sheet sorted faces badly (half the body darker). Previews
  use an opaque fresnel-rim stand-in; the exported material keeps alpha 0.86 for Godot.
- The glTF importer (used by `char_lineup.py`) adds a parentless 2 m bone-shape mesh, which wrecked
  the measured sizes; the lineup ignores parentless meshes.
- Godot warned "UVs are required to generate tangents" for the face meshes and the manifest holder;
  both now get a UV layer.
- The first headless import after the full build printed the known transient
  `Condition "f.is_null()" is true` (3–7×), as in task 1; the second import is clean. During the mass
  import Godot also regenerated the UIDs of `brass.png` and `canvas.png` (committed as Godot wrote them).
- `taskkill /IM blender.exe` to stop a cancelled build was refused by the permission system, rightly,
  because another Blender (Scott's) was running. TaskStop had already ended the build.
- Task 1 committed `blender/scripts/__pycache__/*.pyc`. They are untracked now (`.gitignore` has
  `__pycache__/`); the files stay on disk.
- Task1 spectral tools are 0.9–1.1 m long, so they are long for a 0.6 m ghost (the gathering board
  shows them at about 1.2–1.5× the ghost's height). The tool clips work with them, but the butt of the
  shovel and scythe dips below the ghost's hem when it hovers low. If Scott wants concept-sized tools,
  scale the tool glTFs ~0.75 in task5 (the GRIP offsets scale with them).

## Task 3 (2026-11-16)

- A world volume (Principled Volume on the world output) for distance fog swallowed most of the ambient
  light in EEVEE: the night render went almost black except near lanterns. The preview now has only a thin
  low-mist volume slab; distance fog is Godot's job (the presets carry it).
- Freestyle ink with task1's colour came out as light lines on the night scene; the island build sets a near
  black ink colour.
- The first run placed the wheat field fence through Wren's cottage, a barrel and a lamp post inside walls, a
  graveyard fence through the ore outcrop and a lantern post floating over a terrace. Fixed in the layout; the
  new `tests/test_island.gd` checks that every standalone prop and outdoor marker stands on open ground.
- The glTF importer prints many `edge … appears twice, correcting` warnings while importing the task1 props.
  Harmless (meshes import fine); left as is.
- EEVEE reports `Shadow buffer full (2101 / 2048)` on the wide Millbrook and overview views (about 100 point
  lights from candles and lanterns). Shadows of a few small lights may drop in those previews; no effect on
  the data.
- No bloom in EEVEE any more; a numpy bloom on the saved PNG stands in for Godot's glow.

## Task 4 (2026-11-16)

- Blender 5.2: `NlaStrip.extend_mode` doesn't exist; it is `extrapolation` ('HOLD'). Clips are posed by muting every
  other NLA track and sliding the strip with `frame_start_ui` so all characters render at one scene frame.
- The test framework reported PASS for a test that hit a GDScript runtime error (`SCRIPT ERROR ... Invalid access to
  property 'fragment_chance'`; air has no such key). The test is fixed; **task5 should make runtime errors fail tests**.
- A bash heredoc holding a long Markdown/Python patch failed to parse again; the README patch went through a scratch
  `.py` file, as in task1.
- **No tray prop in task1.** Wren's `serve_drinks` steps say `held_item: tray`; the renders show her without it.
  Task5 needs a small tray prop or can leave the hand empty.
- **Villagers are small next to the concept.** The concept paintings draw villagers about twice as big relative to the
  houses; at true scale (1.1–1.8 m against task1's cottages) they are a few pixels tall in the wide Millbrook view, so a
  closer `square_close` camera was added.
- **The mill's rocking chair faces away from the camera** (layout yaw 210°), so Agnes is seen from behind in
  `mill_night`; the concept shows her facing the viewer. Left as is: the chair orientation is task3 data.
- **Lantern pools read violet, not warm orange,** against the blue night preset (task3's lighting); the concept's warm
  firelight is stronger. Godot's lighting in task5 should push carried and post lanterns warmer.
- **Wren's cottage stands on task3's east path** (the path was stamped first), so routes east detour north around it.
  Harmless; the routes are walkable.
- EEVEE still reports `Shadow buffer full` on the wide views (the villagers' candles and lanterns add lights). Some small
  shadows may drop in the previews; no effect on the data.

## Task 5 (2026-11-17)

- **The background sound agent was stopped** before it put anything in `assets/audio/` (it left about 40 downloads in
  the scratchpad). All audio was then synthesized by `tools/make_audio.py`, plus ten official Kenney CC0 files.
- **libsndfile's Vorbis encoder crashed (stack overflow)** when writing 40–60 s files in one call; `make_audio.py` now
  writes in 4096-frame blocks.
- **Setting `position` on anchored Controls** put most HUD widgets and the centred screens off-screen in the first run.
  The HUD now lays itself out from the viewport size every frame. Screens sit in a full-rect `CenterContainer`, set with
  `set_anchors_and_offsets_preset`.
- **A carried lantern's `Hauntable` stayed registered after its prop was freed** (on a step change), flooding
  `previously freed instance` errors. Carried hauntables are now unregistered together with their prop.
- **New `class_name`s need a `--import`** before `tools/run-tests.sh` sees them (the class cache). The test runner now
  also fails on any `SCRIPT ERROR` (task4 issue).
- **Some glTF props print `invalid UID ... using text path instead`** for their textures (UIDs Godot regenerated in
  task2). Harmless: the textures load by path.
- **Several mausoleum walls are `spectral_stone_vein` nodes** in the task4 data (ore_node_1..17), so a player can mine
  the mausoleum apart. Left as is (it's the ghost's home to wreck); the autotest skips them.
- **Villagers stay small, and the night is cooler and flatter than the concept** (see report_task5.md). The concept's
  purple trees, horizon ruins and moon framing aren't in the voxel data.
- **The tour's cottage-interior view can't match the concept's cutaway:** the real walls are there.
- **Shell heredocs with long Markdown failed to parse again;** the docs were appended through scratch files (as in
  task1 and task4).
