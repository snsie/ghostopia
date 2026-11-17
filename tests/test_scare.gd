## Task5 scare logic: Unease math, fear matching, stages, vulnerability, grading, bolting, botches,
## suspicion reactions, overheard lines and town memory (charms, salt, legend, rumors).
extends "res://tests/framework/test_case.gd"

const TuningS := preload("res://scripts/core/tuning.gd")
const MathS := preload("res://scripts/scare/scare_math.gd")
const MindS := preload("res://scripts/scare/villager_mind.gd")
const TownS := preload("res://scripts/scare/town_memory.gd")
const POP := "res://assets/levels/millbrook_population.json"

var _scare: Dictionary
var _pop: Dictionary


func before_each() -> void:
	_scare = TuningS.load_file().d("scare")
	_pop = JSON.parse_string(FileAccess.get_file_as_string(POP))


func _villager(id: String) -> Dictionary:
	for v in _pop["villagers"]:
		if v["id"] == id:
			return v
	return {}


func test_unease_gain_belief_and_fear() -> void:
	var plain := MathS.unease_gain(10.0, 1.0, false, false, 1.0, _scare)
	assert_almost_eq(plain, 10.0, 0.001, "full belief = act value")
	var half := MathS.unease_gain(10.0, 0.0, false, false, 1.0, _scare)
	assert_almost_eq(half, 4.0, 0.001, "zero belief keeps the 0.4 floor")
	var fear := MathS.unease_gain(10.0, 1.0, true, false, 1.0, _scare)
	assert_almost_eq(fear, 17.5, 0.001, "fear match x1.75")
	assert_almost_eq(MathS.unease_gain(8.0, 1.0, false, true, 1.0, _scare), 0.0, 0.001, "skeptic ignores small acts")
	assert_true(MathS.unease_gain(12.0, 0.15, false, true, 1.0, _scare) > 0.0, "skeptic feels big acts")


func test_fear_matching() -> void:
	assert_true(MathS.fear_matches(["dark"], "dark"))
	assert_false(MathS.fear_matches(["dark"], "dolls"))
	assert_false(MathS.fear_matches(["dark"], null), "the witness has no fear")


func test_stages() -> void:
	var st: Array = _scare["stages"]
	assert_eq(MathS.stage_id(0.0, st), "calm")
	assert_eq(MathS.stage_id(0.3, st), "uneasy")
	assert_eq(MathS.stage_id(0.5, st), "nervous")
	assert_eq(MathS.stage_id(0.7, st), "scared")
	assert_eq(MathS.stage_id(0.85, st), "primed")


func test_decay_waits_for_delay() -> void:
	assert_almost_eq(MathS.decay(30.0, 1.0, 2.0, 1.0, 6.0), 30.0, 0.001, "no decay right after an act")
	assert_almost_eq(MathS.decay(30.0, 1.0, 2.0, 10.0, 6.0), 28.0, 0.001)
	assert_almost_eq(MathS.decay(1.0, 1.0, 2.0, 10.0, 6.0), 0.0, 0.001, "never negative")


func test_back_turned_and_seeing() -> void:
	var fwd := Vector3(0, 0, 1)
	assert_true(MathS.is_back_turned(fwd, Vector3(0, 0, -2), 100.0), "ghost straight behind")
	assert_false(MathS.is_back_turned(fwd, Vector3(1, 0, 1), 100.0), "ghost in front-right")
	assert_true(MathS.can_see(fwd, Vector3(0.5, 0, 3), 70.0, 7.0))
	assert_false(MathS.can_see(fwd, Vector3(0, 0, -3), 70.0, 7.0))
	assert_false(MathS.can_see(fwd, Vector3(0, 0, 9), 70.0, 7.0), "out of range")


func test_grades() -> void:
	var table: Dictionary = _scare["grade_score"]
	var grades: Array = _scare["grades"]
	var low := MathS.grade_score({"primed": true, "unease_frac": 0.82}, table)
	assert_eq(String(MathS.grade_for(int(low["score"]), grades)["id"]), "spooked")
	var mid := MathS.grade_score({"primed": true, "unease_frac": 0.95, "alone": true}, table)
	assert_eq(String(MathS.grade_for(int(mid["score"]), grades)["id"]), "terrified")
	# The design plan's Agnes example: primed + fear + alone + back turned + 3 abilities.
	var agnes := MathS.grade_score({"primed": true, "unease_frac": 0.85, "fear_match": true, "alone": true,
		"back_turned": true, "abilities": 3}, table)
	assert_eq(String(MathS.grade_for(int(agnes["score"]), grades)["id"]), "legendary")
	assert_has(agnes["parts"], "fear_match")


func test_payouts_rise_with_grade() -> void:
	var p: Dictionary = _scare["payout"]
	assert_true(MathS.fright_for("bolt", p) < MathS.fright_for("spooked", p))
	assert_true(MathS.fright_for("spooked", p) < MathS.fright_for("terrified", p))
	assert_true(MathS.fright_for("terrified", p) < MathS.fright_for("legendary", p))
	assert_almost_eq(MathS.remembrance_for("legendary", p, 3.0), 0.36, 0.0001, "believer x3")


func test_build_then_break_agnes() -> void:
	var m := MindS.from_data(_villager("agnes"))
	var candle := {"object": "candle_1", "kind": "candle", "ability": "flicker", "action": "snuff", "unease": 12.0,
		"fears": ["dark", "dolls"]}
	var door := {"object": "door_cottage_1", "kind": "door", "ability": "creak", "action": "creak", "unease": 8.0,
		"fears": ["loud_noises", "being_alone"]}
	var r := m.apply_act(candle, 1.0, _scare)
	assert_true(r["fear_match"], "candle_1 plays into dolls")
	assert_true(float(r["gain"]) > 12.0)
	m.apply_act(door, 3.0, _scare)
	m.apply_act(candle.merged({"object": "candle_2"}, true), 5.0, _scare)
	while m.frac() < 0.82:
		m.apply_act(door.merged({"object": "floorboard_x", "kind": "floorboard"}, true), 6.0, _scare)
	assert_eq(m.stage(_scare), "primed")
	var res := m.boo({"alone": true, "back_turned": true}, 7.0, _scare)
	assert_ne(String(res["outcome"]), "botch")
	assert_true(int(res["abilities"]) >= 2)
	assert_true(int(res["objects"]) >= 3)
	assert_true(String(res["outcome"]) in ["terrified", "legendary"], "got %s" % res["outcome"])
	assert_almost_eq(m.unease, 0.0, 0.001, "unease resets after the break")


func test_boo_too_early_botches_and_braves() -> void:
	var m := MindS.from_data(_villager("bram"))
	var n0 := m.nerve
	m.apply_act({"object": "door_cottage_5", "kind": "door", "ability": "creak", "action": "creak", "unease": 8.0,
		"fears": ["loud_noises"]}, 1.0, _scare)
	var res := m.boo({"alone": true}, 2.0, _scare)
	assert_eq(String(res["outcome"]), "botch")
	assert_eq(String(res["reason"]), "too_early")
	assert_true(m.nerve > n0, "botches make them braver")


func test_spotted_botch_adds_suspicion() -> void:
	var m := MindS.from_data(_villager("wren"))
	m.unease = m.nerve * 0.85
	var res := m.boo({"seen": true}, 1.0, _scare)
	assert_eq(String(res["outcome"]), "botch")
	assert_eq(String(res["reason"]), "spotted")
	assert_true(m.suspicion >= 0.5)


func test_overflow_bolts() -> void:
	var m := MindS.from_data(_villager("wren"))
	var r := {}
	for i in 20:
		r = m.apply_act({"object": "o%d" % i, "kind": "lantern", "ability": "flicker", "action": "snuff", "unease": 14.0,
			"fears": ["dark"]}, float(i), _scare)
		if r["bolted"]:
			break
	assert_true(r["bolted"], "pushing too hard makes them bolt")
	var b := m.bolt(_scare)
	assert_eq(String(b["outcome"]), "bolt")
	assert_true(float(b["fright"]) < MathS.fright_for("spooked", _scare["payout"]))


func test_suspicion_reactions_fire_once() -> void:
	var m := MindS.from_data(_villager("agnes"))
	var fired := []
	for i in 12:
		var r := m.apply_act({"object": "candle_2", "kind": "candle", "ability": "flicker", "action": "dim", "unease": 1.0,
			"fears": ["dark"], "same_trick_twice": true}, float(i * 100), _scare)
		fired.append_array(r["new_reactions"])
		m.unease = 0.0
	assert_true(fired.size() >= 2, "several reactions crossed")
	var actions := fired.map(func(x: Dictionary) -> String: return String(x["action"]))
	assert_eq(actions.count("light_more_candles"), 1, "each reaction fires once")


func test_skeptic_becomes_believer() -> void:
	var m := MindS.from_data(_villager("marlow"))
	assert_true(m.skeptic)
	m.unease = m.nerve * 0.9
	m.apply_act({"object": "door_cottage_3", "kind": "door", "ability": "creak", "action": "drift_open", "unease": 12.0,
		"fears": ["being_alone"]}, 1.0, _scare)
	var res := m.boo({"alone": true, "back_turned": true}, 2.0, _scare)
	assert_true(res.get("made_believer", false))
	assert_true(m.believer)


func test_pip_cannot_be_scared() -> void:
	var m := MindS.from_data(_villager("pip"))
	var r := m.apply_act({"object": "x", "kind": "door", "ability": "creak", "unease": 20.0, "fears": []}, 1.0, _scare)
	assert_almost_eq(float(r["gain"]), 0.0, 0.001)
	assert_eq(String(m.boo({}, 2.0, _scare)["outcome"]), "none")


func test_overheard_lines_reveal_fear() -> void:
	var m := MindS.from_data(_villager("agnes"))
	assert_false(m.hear_line(0, 3))
	assert_false(m.hear_line(0, 3), "the same line twice doesn't count")
	assert_false(m.hear_line(1, 3))
	assert_true(m.hear_line(4, 3))
	assert_true(m.fear_discovered)


func test_town_memory_charm_on_repeat() -> void:
	var t := TownS.new()
	t.setup(_pop["town_memory"], [{"id": "windmill", "remembrance": 0.8}])
	assert_false(t.record_act("door_cottage_1", "creak", 2, 2))
	assert_true(t.record_act("door_cottage_1", "creak", 2, 2), "second creak on the same door")
	t.hang_charm("door_cottage_1", "garlic_lavender", 3, "agnes")
	assert_true(t.is_unhauntable("door_cottage_1"))
	for i in 3:
		t.new_night()
	assert_false(t.is_unhauntable("door_cottage_1"), "charm comes down after 3 nights")


func test_town_memory_old_uses_expire() -> void:
	var t := TownS.new()
	t.setup(_pop["town_memory"], [])
	t.record_act("candle_2", "flicker", 2, 2)
	t.new_night()
	t.new_night()
	assert_false(t.record_act("candle_2", "flicker", 2, 2), "two nights later it's fresh again")


func test_legend_name_grows() -> void:
	var t := TownS.new()
	t.setup(_pop["town_memory"], [])
	assert_eq(t.legend_name(), "")
	t.add_legend(1)
	assert_eq(t.legend_name(), "a draught in Millbrook")
	t.count_epithet("candle", "snuff")
	t.count_epithet("candle", "snuff")
	t.count_epithet("door", "creak")
	assert_true(t.add_legend(5), "stage up")
	assert_eq(t.legend_name(), "the Candle-Snuffing Ghost of Millbrook")


func test_rumor_template_fills() -> void:
	var t := TownS.new()
	t.setup(_pop["town_memory"], [])
	var s := t.make_rumor("{victim} swears the {object} in {place} {trick_past} all by itself.",
		{"victim": "Agnes", "object": "candle", "place": "the mill", "action": "snuff"})
	assert_eq(s, "Agnes swears the candle in the mill went out all by itself.")


func test_remembrance_decay_and_restore() -> void:
	var t := TownS.new()
	t.setup(_pop["town_memory"], [{"id": "fields", "remembrance": 0.5}])
	t.decay_remembrance(100.0, 0.001, 0.0)
	assert_almost_eq(float(t.remembrance["fields"]), 0.4, 0.0001)
	t.add_remembrance("fields", 0.9)
	assert_almost_eq(float(t.remembrance["fields"]), 1.0, 0.0001, "clamped")


func test_save_roundtrip() -> void:
	var m := MindS.from_data(_villager("bram"))
	m.suspicion = 0.33
	m.nerve = 101.0
	m.hear_line(2, 3)
	var m2 := MindS.from_data(_villager("bram"))
	m2.from_save(JSON.parse_string(JSON.stringify(m.to_save())))
	assert_almost_eq(m2.suspicion, 0.33, 0.0001)
	assert_almost_eq(m2.nerve, 101.0, 0.0001)
	assert_eq(m2.heard_lines, [2] as Array[int])
