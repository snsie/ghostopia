## The scare rules as pure functions: Unease gain and decay, stages, fear matching, vulnerability,
## grading (Spooked / Terrified / Legendary) and payouts. Numbers come from tuning.json `scare`.
class_name ScareMath
extends RefCounted


## Unease added by one act. `act_unease` is the hauntable's per-action value (population data),
## `belief` 0..1, `fear_match` true when the act plays into the villager's fear,
## `mult` any reaction multiplier (suspicious villagers, carried lights).
static func unease_gain(act_unease: float, belief: float, fear_match: bool, skeptic: bool, mult: float, scare: Dictionary) -> float:
	if skeptic and act_unease < float(scare.get("skeptic_ignores_acts_below", 10)):
		return 0.0
	var floor_b := float(scare.get("belief_floor", 0.4))
	var g := act_unease * (floor_b + (1.0 - floor_b) * clampf(belief, 0.0, 1.0)) * mult
	if fear_match:
		g *= float(scare.get("fear_match_mult", 1.75))
	return g


static func fear_matches(act_fears: Array, villager_fear: Variant) -> bool:
	return villager_fear != null and act_fears.has(villager_fear)


## Index into `stages` for a given Unease fraction (unease / nerve).
static func stage_index(frac: float, stages: Array) -> int:
	var idx := 0
	for i in stages.size():
		if frac >= float(stages[i].get("from", 0.0)):
			idx = i
	return idx


static func stage_id(frac: float, stages: Array) -> String:
	if stages.is_empty():
		return "calm"
	return String(stages[stage_index(frac, stages)].get("id", "calm"))


static func stage_from(stage: String, stages: Array) -> float:
	for s in stages:
		if s.get("id", "") == stage:
			return float(s.get("from", 0.0))
	return 1.0


## Unease after `dt` seconds: it decays only once `since_last_act` passes the delay.
static func decay(unease: float, dt: float, rate_per_s: float, since_last_act: float, delay_s: float) -> float:
	if since_last_act < delay_s:
		return unease
	return maxf(0.0, unease - rate_per_s * dt)


## True when `to_ghost` (villager -> ghost, flattened) is more than `deg` degrees from where the
## villager faces: the ghost is behind them.
static func is_back_turned(villager_forward: Vector3, to_ghost: Vector3, deg: float) -> bool:
	var f := Vector2(villager_forward.x, villager_forward.z)
	var g := Vector2(to_ghost.x, to_ghost.z)
	if f.length_squared() < 1e-6 or g.length_squared() < 1e-6:
		return false
	return rad_to_deg(absf(f.angle_to(g))) > deg


## True when the villager sees the ghost (inside the cone and range).
static func can_see(villager_forward: Vector3, to_ghost: Vector3, cone_deg: float, range_m: float) -> bool:
	if to_ghost.length() > range_m:
		return false
	var f := Vector2(villager_forward.x, villager_forward.z)
	var g := Vector2(to_ghost.x, to_ghost.z)
	if f.length_squared() < 1e-6 or g.length_squared() < 1e-6:
		return true
	return rad_to_deg(absf(f.angle_to(g))) <= cone_deg


## Score of a break scare. `ctx` keys: primed, unease_frac, fear_match, alone, back_turned,
## abilities (distinct abilities used in the chain), objects (distinct objects), rigged_doorway.
## Returns {score, parts: [names]} so the HUD can show why.
static func grade_score(ctx: Dictionary, table: Dictionary) -> Dictionary:
	var conds := {
		"primed": bool(ctx.get("primed", false)),
		"unease_over_0_9": float(ctx.get("unease_frac", 0.0)) > 0.9,
		"fear_match": bool(ctx.get("fear_match", false)),
		"alone": bool(ctx.get("alone", false)),
		"back_turned": bool(ctx.get("back_turned", false)),
		"two_abilities": int(ctx.get("abilities", 0)) >= 2,
		"three_abilities": int(ctx.get("abilities", 0)) >= 3,
		"rigged_doorway": bool(ctx.get("rigged_doorway", false)),
		"three_objects": int(ctx.get("objects", 0)) >= 3,
	}
	var score := 0
	var parts: Array[String] = []
	for key: String in conds:
		if conds[key]:
			score += int(table.get(key, 0))
			parts.append(key)
	return {"score": score, "parts": parts}


static func grade_for(score: int, grades: Array) -> Dictionary:
	var best: Dictionary = grades[0] if not grades.is_empty() else {"id": "spooked", "name": "Spooked"}
	for g in grades:
		if score >= int(g.get("min_score", 0)):
			best = g
	return best


## Fright for an outcome id (bolt / spooked / terrified / legendary).
static func fright_for(outcome: String, payout: Dictionary) -> float:
	return float(payout.get("fright", {}).get(outcome, 0.0))


static func remembrance_for(outcome: String, payout: Dictionary, villager_mult: float) -> float:
	return float(payout.get("remembrance", {}).get(outcome, 0.0)) * villager_mult


## Suspicion added by one act.
static func suspicion_gain(rate: float, same_trick_twice: bool, sus: Dictionary) -> float:
	var g := float(sus.get("per_act", 0.08)) * rate
	if same_trick_twice:
		g *= float(sus.get("same_trick_twice_mult", 2.0))
	return g


## Noise loudness at a distance (1 at the source, `falloff` at the edge, 0 beyond).
static func noise_factor(dist: float, radius: float, falloff: float) -> float:
	if radius <= 0.0 or dist > radius:
		return 0.0
	return lerpf(1.0, falloff, dist / radius)
