# Battle prototype report: the Underveil battle-fun gate

Branch `battle-prototype` (from `underveil-design`). Brief: `docs/design/underveil-handoff.md`. Choices made without
asking are in `decisions.md` ("Battle prototype"), problems and workarounds in `issues.md`. How to run everything:
README, "Battle prototype".

**The gate question is Scott's:** does breaking a flank with one well-timed scare feel great? The build is ready to
play. Title screen → "Battle prototype: the Sunken Ford", or `Ghostopia.exe -- --battle`.

## What it is

The Drowned Parish (north bank, 500) and the Barrow Host (south bank, 500) march on the Sunken Ford, the Memory Vein
both clans want, and grind each other down there for 3–4 minutes. The ghost drifts through the battle:

- **Tools** hit the undead around it: the scythe sweeps, the sledgehammer scatters a unit in about 3 blows.
- **BOO** frightens everything within 5 m.
- **E on a boulder** lifts it, and E again throws it into the crowd.
- **E at the bell tower** behind the Parish lines silences the bells. The Parish fear silence: for 45 s the whole clan
  is shaken, and both scares and panic hit them 1.8× harder.

The intended play is to watch the HUD's per-flank Resolve, wait for a flank to wear down, silence the bells, then BOO
into it. The flank breaks, the runners shake the units around them, and the line collapses. Each scare is graded by
how many break in the next 10 s: Spooked 10, Terrified 40, Legendary 100.

Measured on the CPU probe, at the same moment of the same battle:

| Scare | Parish routs in 10 s |
|---|---|
| None | 0 (a grind) |
| BOO, bells ringing | about 3–20 |
| Bells silenced, no BOO | 0 |
| Bells silenced, then one BOO | about 130–160: the flank breaks, the other flank holds |

## Acceptance

| Brief | Status |
|---|---|
| 60 fps at 1080p, 1,000 crowd + 32 near actors, logged by `--battle-bench` | **Done** on Scott's PC (RTX 5070 Ti, Vulkan): about **630 fps**. Frame p50 1.55 ms, p95 1.9 ms, p99 2.1 ms. GPU render 1.14 ms, battle logic 0.8–0.9 ms. 32 actors throughout. Exported build: 648 fps (`renders/battle/battle_bench_windows_build.json`). The 5070 Ti is high-end, not mid-range. |
| Runs on macOS (Metal) with frame times logged | **Not verified**: no Mac here. The macOS build exports with the compute shader. Run `Ghostopia.app/Contents/MacOS/Ghostopia -- --battle-bench` on a Mac. |
| Unit tests for the CPU sim | **Done**: `tests/test_battle_crowd.gd`, 20 tests: flow fields and the ford, movement, separation, the river rule, melee timing, shaken damage, Form → scatter, Resolve → rout → flee home, rout spread vs calm units, hit spheres (radius, clan, target, fear mult), summary, front line, nearby list, actors and frozen neighbours, a spawned battle. Full suite: 89 passed. |
| `--autotest` covers entering the arena, a hit that scatters a unit, a scare that routs a flank | **Done**: `-- --battle --autotest`, 8 checks, all pass on the CPU crowd, the GPU crowd and the exported Windows build. Silence then BOO routed 138–277 in 11 s, all graded Legendary; the Parish west flank dropped from about 220 to 40–75 fighting while the east flank held. |
| Screenshots before and after a rout, compared by eye | **Done**: `renders/battle/battle_04_before_rout.png` and `battle_05_after_rout.png`. Before: a tight Parish line along the river. After: the west flank turns into pale, arm-waving figures streaming north, and the HUD shows "BOO · N broke and ran". |
| decisions.md, issues.md, report | Done (this file). |
| Windows and macOS builds | Done: `build/windows/Ghostopia.exe`, `build/macos/Ghostopia.zip`. |

## Scope items

1. **Arena:** 128 × 128 cavern, river with one ford, built by `blender/scripts/build_battle_arena.py`. It also has
   pillars, the bell tower, a Barrow mound, home tunnels, a vein, lights and boulders.
2. **Two clans of 500:** placeholder box soldiers with baked idle, walk, attack and flee
   (`build_battle_units.py`, vertex-animation textures). Preview: `renders/battle/units_preview.png`.
3. **GPU crowd** in a compute shader: flow fields toward the ford, separation, crowd pressure, melee with a strike
   point, Form, Resolve. It writes straight into the MultiMesh buffers.
4. **Rout cascade:** Resolve drains by the share of nearby allies breaking. Routers flee home along their own flow
   field.
5. **Ghost damage:** tools hit near actors; BOO and thrown boulders reach the crowd as hit spheres.
6. **Promotion and demotion** of the 32 nearest units into `NearActor` nodes and back, carrying position, Form,
   Resolve, clan and animation. The autotest checks that a demoted unit returns with its state.
7. **One clan fear:** the Parish bells.
8. **CPU reference version** with the same data layout. `--battle-parity` steps the GPU and CPU sims side by side:
   they agree within 2.7 % after 60 s.
9. **`--battle-bench`:** GPU crowd, 1080p, vsync off, ghost sweeping the front and BOOing every 6 s. It logs p50, p95
   and p99 frame times, GPU and CPU render time, battle logic time, actors, readbacks and promotions.

## Not done / known limits

- **No macOS frame times** (see above).
- **No mid-range GPU benchmark.** The headroom suggests it's fine.
- Placeholder art only: box soldiers, a stone cavern, no clan concept art (the brief says don't order any yet).
- **Near actors are not rigged glTFs**, and possession and dialogue with them aren't in. The Read panel shows clan,
  Form, Resolve and whether the unit is shaken.
- **Crowd blows on a near actor are approximated** on the CPU at the attacker's swing rate.
- The Barrow Host's own fear (namelessness), captains, banner bearers, haunted war gear, and rockfalls from the
  ceiling aren't in.
- **Scattering pays nothing yet:** a hint names the material, but no such inventory items exist.
- The battle ends when a clan drops under 25 % fighting. Scattered units don't re-form (there's no war sim yet).
- **Balance is a starting point:** BOO's Resolve hit sits near a threshold (95 → almost nothing, 110 → ~50 routs
  alone), so it's the first knob to try if BOO feels too weak or too strong. Everything is in tuning.json → `battle`,
  and `tools/battle_probe.gd` replays the scenarios headless.

## Files

New: `scripts/battle/*` (12 scripts), `shaders/crowd/crowd_sim.glsl`, `shaders/crowd_unit.gdshader`,
`scenes/battle.tscn`, `blender/scripts/build_battle_{arena,units}.py`, `assets/levels/sunken_ford_*`,
`assets/battle/units/*`, `tests/test_battle_crowd.gd`, `tools/battle_probe.gd`, `renders/battle/*`.

Changed:

- `scripts/actors/player.gd`: two hooks, `tool_swing` and `respawn_point`, used only when the world provides them.
- `scripts/world/world.gd`: the `--battle`, `--battle-bench` and `--battle-parity` redirects.
- `scripts/ui/title_screen.gd`: the "Battle prototype" button.
- `assets/data/tuning.json`: the `battle` section.
- `README.md`, `decisions.md`, `issues.md`.

The Millbrook slice is otherwise untouched; its `--autotest` still passes.
