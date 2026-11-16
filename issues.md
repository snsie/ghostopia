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
