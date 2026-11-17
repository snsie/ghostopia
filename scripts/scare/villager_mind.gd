## One villager's side of the scare (read -> build -> break), without any scene code:
## Unease, Nerve (grows with every botch), Belief, hidden fear, suspicion, the chain of acts that
## builds the current scare, and the overheard lines that reveal the fear.
class_name VillagerMind
extends RefCounted

var id: String
var role: String = "target"
var fear: Variant = null
var belief: float = 0.5
var base_nerve: float = 60.0
var nerve: float = 60.0
var skeptic: bool = false
var believer: bool = false
var suspicion_rate: float = 0.5
var bravery_gain: float = 0.1
var decay_rate: float = 0.6
var reactions: Array = []          # suspicious_reactions from the population data

var unease: float = 0.0
var suspicion: float = 0.0
var last_act_time: float = -1000.0
var chain: Array[Dictionary] = []  # acts since the last calm moment
var fired_reactions: Array[float] = []
var lines_heard: int = 0
var heard_lines: Array[int] = []
var fear_discovered: bool = false
var flicker_mult: float = 1.0      # lowered by "light more candles"
var unease_mult_after: float = 1.0 # Marlow's investigation
var unease_mult_until: float = -1.0
var scares_taken: int = 0


static func from_data(v: Dictionary, overrides: Dictionary = {}) -> VillagerMind:
	var m := VillagerMind.new()
	var src := v.duplicate()
	src.merge(overrides, true)
	m.id = String(src.get("id", ""))
	m.role = String(src.get("role", "target"))
	m.fear = src.get("fear", null)
	m.belief = float(src.get("belief", 0.5))
	m.base_nerve = float(src.get("nerve", 60.0)) if src.get("nerve") != null else 9999.0
	m.nerve = m.base_nerve
	m.skeptic = bool(src.get("skeptic", false))
	m.suspicion_rate = float(src.get("suspicion_rate", 0.5))
	m.bravery_gain = float(src.get("bravery_gain", 0.1))
	m.decay_rate = float(src.get("unease_decay_per_s", 0.6))
	m.reactions = src.get("suspicious_reactions", [])
	return m


func can_be_scared() -> bool:
	return role == "target"


func frac() -> float:
	return unease / maxf(nerve, 0.001)


func stage(scare: Dictionary) -> String:
	return ScareMath.stage_id(frac(), scare.get("stages", []))


func stage_index(scare: Dictionary) -> int:
	return ScareMath.stage_index(frac(), scare.get("stages", []))


## Applies one haunting act. `act` = {object, kind, ability, action, unease, fears, same_trick_twice,
## mult}. Returns {gain, fear_match, stage_before, stage_after, bolted, new_reactions: [reaction]}.
func apply_act(act: Dictionary, now: float, scare: Dictionary) -> Dictionary:
	var out := {"gain": 0.0, "fear_match": false, "stage_before": stage(scare), "stage_after": stage(scare),
		"bolted": false, "new_reactions": []}
	if not can_be_scared():
		return out
	var fm := ScareMath.fear_matches(act.get("fears", []), fear)
	var mult := float(act.get("mult", 1.0))
	if act.get("ability", "") == "flicker":
		mult *= flicker_mult
	if now < unease_mult_until:
		mult *= unease_mult_after
	var gain := ScareMath.unease_gain(float(act.get("unease", 0.0)), belief, fm, skeptic and not believer, mult, scare)
	unease += gain
	last_act_time = now
	if gain > 0.0:
		chain.append({"object": act.get("object", ""), "kind": act.get("kind", ""), "ability": act.get("ability", ""),
			"action": act.get("action", ""), "fear_match": fm, "time": now, "door": act.get("kind", "") == "door",
			"pos": act.get("pos", Vector3.ZERO)})
	var sus: Dictionary = scare.get("suspicion", {})
	suspicion += ScareMath.suspicion_gain(suspicion_rate, bool(act.get("same_trick_twice", false)), sus)
	out["new_reactions"] = _cross_reactions()
	out["gain"] = gain
	out["fear_match"] = fm
	out["stage_after"] = stage(scare)
	if frac() >= float(scare.get("overflow_at", 1.0)):
		out["bolted"] = true
	return out


func _cross_reactions() -> Array:
	var fired: Array = []
	for r in reactions:
		var at := float(r.get("at_suspicion", 99.0))
		if suspicion >= at and not fired_reactions.has(at):
			fired_reactions.append(at)
			fired.append(r)
	return fired


## Pushed past their nerve without a break: they bolt for a weak payout and grow braver.
func bolt(scare: Dictionary) -> Dictionary:
	var res := {"outcome": "bolt", "grade": {"id": "bolt", "name": "Bolted"}, "fright": 0.0, "abilities": _abilities(),
		"objects": _objects(), "fear_match": _chain_fear_match()}
	res["fright"] = ScareMath.fright_for("bolt", scare.get("payout", {}))
	_grow_braver(scare)
	_reset_chain()
	return res


## The break. `ctx` = {alone, back_turned, rigged_doorway, seen}. Returns {outcome: grade id or
## "botch", grade, score, parts, fright, fear_match, abilities, objects, reason}.
func boo(ctx: Dictionary, now: float, scare: Dictionary) -> Dictionary:
	var stages: Array = scare.get("stages", [])
	var needs := ScareMath.stage_from(String(scare.get("boo", {}).get("needs_stage", "primed")), stages)
	var f := frac()
	var res := {"abilities": _abilities(), "objects": _objects(), "fear_match": _chain_fear_match(), "frac": f}
	if not can_be_scared():
		res["outcome"] = "none"
		return res
	if f < needs or ctx.get("seen", false):
		res["outcome"] = "botch"
		res["reason"] = "spotted" if ctx.get("seen", false) and f >= needs else "too_early"
		if ctx.get("seen", false):
			suspicion += float(scare.get("suspicion", {}).get("seen_manifesting", 0.5))
			res["new_reactions"] = _cross_reactions()
		_grow_braver(scare)
		_reset_chain()
		return res
	var sc := ScareMath.grade_score({
		"primed": f >= needs, "unease_frac": f, "fear_match": res["fear_match"],
		"alone": ctx.get("alone", false), "back_turned": ctx.get("back_turned", false),
		"abilities": int(res["abilities"]) + 0, "objects": res["objects"],
		"rigged_doorway": ctx.get("rigged_doorway", false)}, scare.get("grade_score", {}))
	var g := ScareMath.grade_for(int(sc["score"]), scare.get("grades", []))
	res["outcome"] = String(g.get("id", "spooked"))
	res["grade"] = g
	res["score"] = sc["score"]
	res["parts"] = sc["parts"]
	res["fright"] = ScareMath.fright_for(res["outcome"], scare.get("payout", {}))
	scares_taken += 1
	if skeptic and not believer:
		believer = true
		res["made_believer"] = true
		belief = maxf(belief, 0.6)
	_reset_chain()
	return res


func tick(dt: float, now: float, scare: Dictionary) -> void:
	var delay := float(scare.get("decay_delay_s", 6.0))
	unease = ScareMath.decay(unease, dt, decay_rate * float(scare.get("decay_mult", 1.0)), now - last_act_time, delay)
	suspicion = maxf(0.0, suspicion - float(scare.get("suspicion", {}).get("decay_per_s", 0.0)) * dt)
	var window := float(scare.get("combo_window_s", 45.0))
	while not chain.is_empty() and now - float(chain[0]["time"]) > window:
		chain.pop_front()
	if unease <= 0.0 and not chain.is_empty() and now - last_act_time > delay:
		chain.clear()


## A new night: suspicion fades, the per-night reactions can fire again.
func new_night(scare: Dictionary) -> void:
	suspicion *= 1.0 - float(scare.get("suspicion", {}).get("decay_per_night", 0.5))
	fired_reactions = fired_reactions.filter(func(at: float) -> bool: return suspicion >= at)
	flicker_mult = 1.0


## Overheard line `idx`; returns true when this line reveals the fear.
func hear_line(idx: int, lines_to_reveal: int) -> bool:
	if not heard_lines.has(idx):
		heard_lines.append(idx)
	lines_heard += 1
	if not fear_discovered and heard_lines.size() >= lines_to_reveal:
		fear_discovered = true
		return true
	return false


func _grow_braver(scare: Dictionary) -> void:
	nerve += nerve * bravery_gain * float(scare.get("botch_bravery_mult", 1.0))
	unease = 0.0


func _reset_chain() -> void:
	chain.clear()
	unease = 0.0


func _abilities() -> int:
	var s := {}
	for c in chain:
		s[c["ability"]] = true
	return s.size()


func _objects() -> int:
	var s := {}
	for c in chain:
		s[c["object"]] = true
	return s.size()


func _chain_fear_match() -> bool:
	for c in chain:
		if c["fear_match"]:
			return true
	return false


## The latest door used in the chain (for the rigged-doorway check), or {}.
func last_door_act() -> Dictionary:
	for i in range(chain.size() - 1, -1, -1):
		if chain[i]["door"]:
			return chain[i]
	return {}


func to_save() -> Dictionary:
	return {"nerve": nerve, "suspicion": suspicion, "believer": believer, "belief": belief,
		"heard_lines": heard_lines, "fear_discovered": fear_discovered, "fired": fired_reactions,
		"scares_taken": scares_taken}


func from_save(d: Dictionary) -> void:
	nerve = float(d.get("nerve", nerve))
	suspicion = float(d.get("suspicion", 0.0))
	believer = bool(d.get("believer", false))
	belief = float(d.get("belief", belief))
	heard_lines.assign(d.get("heard_lines", []).map(func(x: Variant) -> int: return int(x)))
	lines_heard = heard_lines.size()
	fear_discovered = bool(d.get("fear_discovered", false))
	fired_reactions.assign(d.get("fired", []).map(func(x: Variant) -> float: return float(x)))
	scares_taken = int(d.get("scares_taken", 0))
