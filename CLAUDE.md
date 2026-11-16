# Ghostopia (working title)

Cute-spooky third-person voxel survival game in Godot 4: you are a ghost in the Veil, an afterlife
built from memories, and you grow by scaring the living. Built with the **game-pipeline** skill
(concept art from ChatGPT → Blender Python → Godot → shipped build). Load that skill for any
pipeline stage.

- Mechanics (source of truth): `docs/design/design-plan.md`. Design and feel decisions are Scott's.
- Art and production plan (style block, prompts, task scope): `Ghostopia — concept art and tasks.md`.
- Task files `task1.md`–`task5.md` run in order, one fresh session each, in autonomous mode.
  Every task logs to `decisions.md`, `issues.md` and `report_taskN.md`.

## Tools

- Godot 4.7.2: `/c/Tools/Godot/godot.exe` (editor), `/c/Tools/Godot/godot_console.exe` (headless).
- Blender 5.2: `"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"`, run headless:
  `blender -b --factory-startup -P blender/scripts/<script>.py -- <args>`.
- Python 3.13 (`python`). Image tooling needs `numpy pillow opencv-python`.
- Shell: Bash (Git Bash), never PowerShell.
- Concept art is ordered from ChatGPT through the browser-use plugin driving Scott's own Chrome.
  Ask before each download.

## Fixed decisions

- Camera: third person, chase cam behind the ghost.
- Platforms: Windows and macOS (every task ends with both builds).
- World: hybrid. Godot generates voxel terrain at runtime. Blender scripts produce block textures,
  props, furniture, characters and hand-built landmark layouts (village, mill, graveyard) as JSON
  that Godot stamps into the voxel world.
- Vertical slice: Open Plains / Millbrook village + starting graveyard, Haunting levels 1–2.
- Original IP only: relics and cosmetics are original designs, never licensed characters.

## Commands

- Unit tests (headless): `tools/run-tests.sh` or `tools/run-tests.sh <substring>`; exit 0 = pass.
  Tests extend `"res://tests/framework/test_case.gd"` by path and name methods `test_*`.
- Game self-test: `--autotest` and `--tour` modes (added in task5).
- Re-import assets: `/c/Tools/Godot/godot_console.exe --headless --path . --import`.

## Layout

`concept/` and `concept_art/` reference images (ignored by Godot) · `blender/scripts/` generators
(`lib_*.py` shared) · `assets/` generated glTF, textures, level JSON, UI, audio · `scripts/` GDScript
· `renders/` previews · `build/` exports · `tests/` unit tests · `docs/design/` design plan.
