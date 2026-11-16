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
