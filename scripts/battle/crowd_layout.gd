## The crowd's shared data layout: one record of STRIDE floats per unit, identical in the CPU
## reference sim (crowd_sim_cpu.gd), the GPU compute shaders (shaders/crowd/*.glsl), promotion and
## demotion of near actors, and the readback. Change it here and in shaders/crowd/crowd_common.glsl together.
extends RefCounted

const STRIDE := 20

# v0
const PX := 0
const PZ := 1
const VX := 2
const VZ := 3
# v1
const FORM := 4
const RESOLVE := 5
const CLAN := 6
const STATE := 7
# v2
const ATTACK_CD := 8
const ANIM_T := 9
const YAW := 10
const PY := 11
# v3
const TARGET := 12        # buffer index of the enemy being fought, -1 when none
const STATE_T := 13       # seconds in the current state (0 on the frame of a transition)
const FLASH := 14         # hit flash 1 -> 0
const SEED := 15          # per-unit random in [0, 1)
# v4
const CLIP := 16
const STRIKE := 17        # pending strike: target index + 1, 0 = none
const SPARE1 := 18
const ACTOR := 19         # 1 = promoted: a near actor on the CPU owns this unit; the crowd sim doesn't
                          # step or draw it, but neighbours still see its real state (fear spreads both ways)

# unit states
const FIGHT := 0
const ROUT := 1
const SCATTERED := 2      # Form hit zero: dissolving into wisps, then LEFT
const LEFT := 3           # out of this battle (fled home or scattered)

# animation clips (order of build_battle_units.py CLIPS)
const CLIP_IDLE := 0
const CLIP_WALK := 1
const CLIP_ATTACK := 2
const CLIP_FLEE := 3

# terrain cell flags
const T_BLOCKED := 1
const T_WATER := 2        # running water: only water walkers enter
const T_FORD := 4
const T_HOME0 := 8        # home zone of clan 0 (clan c: T_HOME0 << c)

# hit sphere: 12 floats
const SPHERE_STRIDE := 12
const SPHERE_MAX := 64
const SPH_SCARE := 1      # Resolve damage is multiplied by the clan's fear multiplier
const SPH_GHOST := 2      # caused by the ghost (cascade attribution)

# multimesh instance: transform 3x4 (12) + custom data (4)
const MM_STRIDE := 16

# summary: per clan (MAX_CLANS) counts
const MAX_CLANS := 4
const SUM_STATE := 0          # [state * MAX_CLANS + clan] for states 0..3 (+ actors under their own state)
const SUM_ROUTS := 20         # cumulative routs per clan (never cleared)
const SUM_SCATTERS := 24      # cumulative scatters per clan (never cleared)
const SUM_FLANK := 28         # per clan per flank (west 0 / east 1): count of FIGHT units -> 8 entries
const SUM_FLANK_RES := 36     # per clan per flank: sum of Resolve * 16 (fixed point) -> 8 entries
const SUM_ENGAGED := 44       # per clan: fighting units with a target in reach
const SUM_FRONT := 48         # front line: per (clan * 2 + flank) 3 entries: engaged count, sum x * 4, sum z * 4
const SUM_SIZE := 72
# every entry except the cumulative [SUM_ROUTS, SUM_FLANK) is recounted every frame

# nearby list (readback for promotion): distance bands around the ghost
const NEAR_BANDS := 8
const NEAR_BAND_M := 1.5
const NEAR_BAND_CAP := 40
const NEAR_ENTRY := STRIDE + 1    # buffer index, then the unit record


static func blank() -> PackedFloat32Array:
	var u := PackedFloat32Array()
	u.resize(STRIDE)
	u[TARGET] = -1.0
	return u


static func flank_of(x: float, mid_x: float) -> int:
	return 0 if x < mid_x else 1


## The engaged front of one clan's flank from a summary (Vector3.INF when nobody is fighting there).
static func front_point(summary: PackedInt32Array, clan: int, flank: int, y: float) -> Vector3:
	var o := SUM_FRONT + (clan * 2 + flank) * 3
	if summary.size() <= o + 2 or summary[o] <= 0:
		return Vector3.INF
	var n := float(summary[o])
	return Vector3(summary[o + 1] / 4.0 / n, y, summary[o + 2] / 4.0 / n)
