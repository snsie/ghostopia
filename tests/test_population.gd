## Task4 population: millbrook_population.json and memory_fragments.json load the way the game will read them
## and keep their contracts (references into the layout, schedules covering the day, haunting coverage,
## fragment sets and drop tables).
extends "res://tests/framework/test_case.gd"

const POPULATION := "res://assets/levels/millbrook_population.json"
const FRAGMENTS := "res://assets/data/memory_fragments.json"
const LAYOUT := "res://assets/levels/millbrook_layout.json"
const FEARS := ["dark", "dolls", "being_alone", "loud_noises", "mirrors"]
const RESIDENTS := ["agnes", "bram", "wren", "marlow", "pip"]

var _pop: Dictionary
var _frag: Dictionary
var _layout: Dictionary
var _markers := {}
var _instances := {}
var _hauntables := {}


func before_each() -> void:
	_pop = JSON.parse_string(FileAccess.get_file_as_string(POPULATION))
	_frag = JSON.parse_string(FileAccess.get_file_as_string(FRAGMENTS))
	_layout = JSON.parse_string(FileAccess.get_file_as_string(LAYOUT))
	for m in _layout["markers"]:
		_markers[m["id"]] = m
	for i in _layout["instances"]:
		_instances[i["id"]] = i
	for h in _pop["hauntables"]:
		_hauntables[h["id"]] = h


func test_villagers_and_their_numbers() -> void:
	var ids := []
	for v in _pop["villagers"]:
		ids.append(v["id"])
		assert_true(ResourceLoader.exists(v["gltf"]), "%s model %s" % [v["id"], v["gltf"]])
		assert_true(_markers.has(v["bed"]), "%s bed" % v["id"])
		assert_true(float(v["belief"]) >= 0.0 and float(v["belief"]) <= 1.0, "%s belief" % v["id"])
		assert_true(v["tuning"], "%s tuning flag" % v["id"])
		if v["role"] == "target":
			assert_has(FEARS, v["fear"], "%s fear" % v["id"])
			assert_true(float(v["nerve"]) > 0.0, "%s nerve" % v["id"])
			var n: int = v["mutters"]["lines"].size()
			assert_true(n >= 5 and n <= 8, "%s has 5-8 mutters (%d)" % [v["id"], n])
			assert_true(v["suspicious_reactions"].size() >= 1, "%s reactions" % v["id"])
		else:
			assert_false(v["witness"]["can_be_scared"], "%s is a witness" % v["id"])
	for r in RESIDENTS:
		assert_has(ids, r)


func test_skeptic_and_witness_defaults() -> void:
	for v in _pop["villagers"]:
		if v["id"] == "marlow":
			assert_true(v["skeptic"])
			assert_true(float(v["belief"]) < 0.3)
			assert_true(v["on_break"]["becomes_believer"]["lasting"])
		if v["id"] == "agnes":
			assert_eq(String(v["fear"]), "dolls")
			assert_true(_hauntables.has(v["fear_object"]))
		if v["id"] == "pip":
			assert_eq(String(v["role"]), "witness")


func test_schedules_cover_the_whole_cycle() -> void:
	for v in _pop["villagers"]:
		var steps: Array = v["schedule"]
		var total := 0.0
		for i in steps.size():
			var s: Dictionary = steps[i]
			total += float(s["duration_s"])
			assert_true(float(s["duration_s"]) > 0.0, s["id"])
			if i > 0:
				assert_almost_eq(float(s["t_start"]), float(steps[i - 1]["t_end"]), 0.0002, "%s continuous" % s["id"])
			if s["kind"] == "stay":
				if s["marker"] != null:
					assert_true(_markers.has(s["marker"]), "%s marker %s" % [s["id"], s["marker"]])
				assert_true(s.has("facing_away_from") and s.has("alone"), s["id"])
			else:
				assert_true(s["route"].size() >= 2, "%s route" % s["id"])
				assert_true(float(s["length_m"]) > 0.0, s["id"])
		assert_almost_eq(total, float(_pop["cycle"]["length_s"]), 1.0, "%s schedule spans one cycle" % v["id"])


func test_night_has_lantern_walks_and_a_late_sitter() -> void:
	var lantern_walks := 0
	var late := {}
	var bridge := false
	for v in _pop["villagers"]:
		for s in v["schedule"]:
			if s["kind"] == "walk" and s["phase"] == "night" and s["light"] != null:
				lantern_walks += 1
			if s["kind"] == "walk" and "bridge" in s["crosses"]:
				bridge = true
			if s["activity"] in ["rock_in_chair", "read_late"]:
				late[v["id"]] = true
	assert_true(lantern_walks >= 3, "lantern walks home (%d)" % lantern_walks)
	assert_true(late.has("agnes") and late.has("marlow"))
	assert_true(bridge, "someone crosses the bridge at night")


func test_hauntables_reference_layout_and_slice_levels() -> void:
	for h in _pop["hauntables"]:
		if h["source"] == "carried":
			assert_has(RESIDENTS, h["carried_by"])
			continue
		assert_true(_instances.has(h["instance"]), "instance %s" % h["instance"])
		var lvl: int = int(h["level"])
		if h["kind"] in ["door", "floorboard"]:
			assert_eq(lvl, 1, h["id"])
			assert_eq(String(h["ability"]), "creak")
		elif h["kind"] in ["candle", "oil_lamp", "lantern"]:
			assert_eq(lvl, 2, h["id"])
			assert_eq(String(h["ability"]), "flicker")
		else:
			assert_true(lvl >= 3 and not h["slice_active"], h["id"])
		for f in h["fears"]:
			assert_has(FEARS, f, h["id"])
	# every layout hauntable is in the population list
	for i in _layout["instances"]:
		if i["hauntable"] != null:
			assert_true(_hauntables.has(i["id"]), "layout hauntable %s listed" % i["id"])


func test_every_villager_has_haunting_coverage() -> void:
	for v in _pop["villagers"]:
		var c: Dictionary = _pop["checks"][v["id"]]
		assert_true(c["home_level12"].size() >= 3, "%s home L1-2" % v["id"])
		assert_true(c["route_level12"].size() >= 3, "%s route L1-2" % v["id"])
		if v["fear"] != null:
			assert_true(c["fear_objects"].size() >= 1, "%s fear object" % v["id"])
		assert_true(c["ok"], v["id"])


func test_nodes_sit_on_layout_markers() -> void:
	var kinds := {}
	for n in _pop["nodes"]["list"]:
		assert_true(_markers.has(n["marker"]), n["id"])
		assert_has(["scythe", "shovel", "sledgehammer"], n["tool"])
		assert_true(float(n["regrow"]["seconds"]) > 0.0, n["id"])
		kinds[n["kind"]] = true
	for k in ["grave_weeds", "fiber_grass", "grave_dirt", "eerie_ore_vein", "spectral_stone_vein"]:
		assert_true(kinds.has(k), "node kind %s" % k)


func test_fragments_sets_and_drop_tables() -> void:
	var frags: Array = _frag["fragments"]
	assert_true(frags.size() >= 28 and frags.size() <= 32, "about 30 fragments (%d)" % frags.size())
	var ids := {}
	for f in frags:
		assert_false(ids.has(f["id"]), "unique %s" % f["id"])
		ids[f["id"]] = f
		assert_true(String(f["text"]).length() > 10)
		assert_true(String(f["vignette"]).length() > 10)
	assert_eq(_frag["sets"].size(), 3)
	for s in _frag["sets"]:
		assert_eq(s["fragments"].size(), 5, s["id"])
		assert_true(ResourceLoader.exists("res://assets/characters/%s.gltf" % s["unlocks_resident"]), s["id"])
	var blocks: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/blocks/blocks.json"))
	var in_table := {}
	for b in blocks["blocks"]:
		if b.get("fragment_chance") != null and float(b["fragment_chance"]) > 0.0:
			var t: Dictionary = _frag["drop_tables"][b["id"]]
			assert_true(t["entries"].size() >= 2, "drop table %s" % b["id"])
			for e in t["entries"]:
				assert_true(ids.has(e["fragment"]), e["fragment"])
				in_table[e["fragment"]] = true
	for id in ids:
		assert_true(in_table.has(id), "%s drops from some block" % id)


func test_town_memory_and_fx() -> void:
	var tm: Dictionary = _pop["town_memory"]
	var rules := []
	for r in tm["rules"]:
		rules.append(r["id"])
	for r in ["repeat_trick", "botched_scare", "legendary_scare"]:
		assert_has(rules, r)
	assert_true(tm["rumors"]["templates"].size() >= 6)
	assert_true(String(tm["legend"]["stages"][3]["name"]).contains("{epithet}"))
	var types := {}
	for f in _pop["fx"]["list"]:
		types[f["type"]] = true
	for t in ["chimney_smoke", "hearth_flame", "candle_flame", "lantern_glow", "fireflies", "low_mist", "water_sparkle",
			"waterfall_spray", "rotate", "ore_wisps", "portal_glow", "worker_ghost"]:
		assert_true(types.has(t), "fx %s" % t)
