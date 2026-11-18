## Task5 pure rules: tuning loading, block rules (tools, tiers, phasing, running water), drop tables,
## memory-fragment rolls, inventory and Workbench crafting.
extends "res://tests/framework/test_case.gd"

const TuningS := preload("res://scripts/core/tuning.gd")
const BlocksS := preload("res://scripts/voxel/block_registry.gd")
const InvS := preload("res://scripts/gather/inventory.gd")
const FragS := preload("res://scripts/gather/fragment_roller.gd")

var _t: TuningS
var _b: BlocksS


func before_each() -> void:
	_t = TuningS.load_file()
	_b = BlocksS.load_file()


func test_tuning_loads_every_section() -> void:
	for key in ["cycle", "player", "camera", "presence", "haunting", "scare", "overhear", "town_memory",
			"remembrance", "heat", "mining", "items", "start", "recipes", "npc", "world"]:
		assert_true(_t.data.has(key), "tuning has %s" % key)
	assert_eq(_t.i("player.hp_base"), 10, "Basic Ghost HP 10")
	assert_almost_eq(_t.f("missing.path", 3.5), 3.5, 0.0001, "fallback")
	assert_almost_eq(_t.f("cycle.length_s") * 0.5 / 60.0, 12.0, 0.01, "about 12 real minutes of night")


func test_tuning_levels() -> void:
	assert_eq(int(_t.level_for("haunting.levels", 0)["level"]), 1)
	assert_eq(String(_t.level_for("haunting.levels", 0)["unlock"]), "creak")
	var lv2 := _t.level_for("haunting.levels", _t.f("haunting.levels.1.fright"))
	assert_eq(String(lv2["unlock"]), "flicker")
	assert_eq(String(_t.level_for("haunting.levels", 35)["unlock"]), "haunted_furniture")
	assert_eq(String(_t.level_for("haunting.levels", 44)["unlock"]), "haunted_furniture")
	assert_eq(String(_t.level_for("haunting.levels", 45)["unlock"]), "bell_ringing")
	assert_eq(String(_t.level_for("haunting.levels", 60)["unlock"]), "object_possession")
	assert_eq(String(_t.level_for("haunting.levels", 100)["unlock"]), "animal_possession")
	assert_eq(String(_t.level_for("haunting.levels", 150)["unlock"]), "villager_possession")
	assert_eq(int(_t.level_for("presence.levels", 0)["hp"]), 10)
	assert_eq(int(_t.next_level("haunting.levels", 0)["level"]), 2)


func test_scare_tuning_matches_population_grades() -> void:
	var pop: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/levels/millbrook_population.json"))
	var rules: Dictionary = pop["scare_rules"]
	assert_almost_eq(_t.f("scare.fear_match_mult"), float(rules["fear_match_mult"]), 0.0001)
	assert_eq(_t.a("scare.grades").size(), (rules["grades"] as Array).size())
	assert_eq(_t.a("scare.stages").size(), (rules["unease"]["stages"] as Array).size())


func test_block_rules() -> void:
	var stone := _b.index_of("stone")
	var dirt := _b.index_of("dirt")
	var iron := _b.index_of("iron_ore")
	var eerie := _b.index_of("eerie_ore")
	assert_eq(_b.index_of("air"), 0)
	assert_eq(_b.mine_check(dirt, "shovel", 1), "")
	assert_ne(_b.mine_check(dirt, "scythe", 1), "", "wrong tool")
	assert_eq(_b.mine_check(eerie, "sledgehammer", 1), "", "eerie ore is tier I")
	assert_ne(_b.mine_check(iron, "sledgehammer", 1), "", "iron needs tier II")
	assert_eq(_b.mine_check(iron, "sledgehammer", 2), "")
	assert_ne(_b.mine_check(_b.index_of("river_water"), "shovel", 4), "", "water can't be mined")
	assert_eq(_b.phaseable[dirt], 1)
	assert_eq(_b.phaseable[stone], 0, "the ghost can't phase stone")
	assert_eq(_b.phaseable[iron], 0)
	assert_eq(_b.running[_b.index_of("river_water")], 1)
	assert_eq(_b.running[_b.index_of("still_water")], 0, "the well is crossable")
	assert_eq(_b.cross[_b.index_of("wheat")], 1)
	assert_eq(_b.opaque[_b.index_of("leaves")], 0, "leaves don't cull")
	assert_eq(_b.solid[_b.index_of("river_water")], 0)


func test_hits_scale_with_tier() -> void:
	var stone := _b.index_of("stone")
	var speed: Array = _t.a("mining.tier_speed")
	var h1 := _b.hits_needed(stone, 1, _t.f("mining.hits_per_hardness"), speed)
	var h2 := _b.hits_needed(stone, 2, _t.f("mining.hits_per_hardness"), speed)
	assert_true(h1 > h2, "tier II mines faster (%d vs %d)" % [h1, h2])
	assert_true(_b.hits_needed(_b.index_of("tall_grass"), 1, 2.0, speed) >= 1)


func test_drop_tables() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var total := {}
	for i in 200:
		var d := _b.roll_drops(_b.index_of("grave_dirt"), rng)
		for k: String in d:
			total[k] = int(total.get(k, 0)) + int(d[k])
	assert_eq(int(total.get("grave_dirt", 0)), 200, "always drops itself")
	assert_true(int(total.get("bone", 0)) > 0, "bones sometimes")
	var eerie := BlocksS.roll_drop_list(_b.info(_b.index_of("eerie_ore"))["drops"], rng)
	assert_true(int(eerie.get("eerie_shard", 0)) >= 1)


func test_fragment_rolls() -> void:
	var fj: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/data/memory_fragments.json"))
	var r := FragS.new()
	r.setup(fj)
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	var got := {}
	for i in 400:
		var f := r.roll("eerie_ore", "graveyard", got, rng)
		if f != "":
			assert_false(got.has(f), "never a duplicate")
			got[f] = true
	assert_true(got.size() >= 2, "eerie ore drops several fragments")
	assert_eq(r.roll("cobblestone", "graveyard", {}, rng), "", "built blocks hold no memories")
	assert_eq(r.roll("eerie_ore", "x", {}, rng, 1.0, 0.0), "", "chance 0 never drops")


func test_inventory_and_crafting() -> void:
	var inv := InvS.new()
	inv.set_placeable({"dirt": "dirt", "rough_wood": "rough_wood"})
	inv.setup(_t.d("start"))
	assert_eq(inv.tool_tier("sledgehammer"), 1)
	assert_eq(inv.hotbar[0], "scythe")
	assert_has(inv.hotbar, "rough_wood", "starting blocks get a slot")
	inv.add("dirt", 3)
	assert_has(inv.hotbar, "dirt")
	var recipe: Dictionary = {}
	for r in _t.a("recipes"):
		if r["id"] == "sledgehammer_t2":
			recipe = r
	assert_false(inv.can_craft(recipe))
	assert_true(inv.missing_for(recipe).has("eerie_shard"))
	for k: String in recipe["needs"]:
		inv.add(k, int(recipe["needs"][k]))
	assert_true(inv.craft(recipe))
	assert_eq(inv.tool_tier("sledgehammer"), 2)
	assert_false(inv.can_craft(recipe), "already tier II")
	assert_eq(inv.count("eerie_shard"), 0)
	assert_true(inv.remove("dirt", 3))
	assert_false(inv.remove("dirt", 1))


func test_every_recipe_item_exists() -> void:
	var items := _t.d("items")
	for r in _t.a("recipes"):
		for k: String in r["needs"]:
			assert_true(items.has(k), "%s needs known item %s" % [r["id"], k])
	for k: String in items:
		if items[k] is Dictionary and items[k].get("kind") == "block":
			assert_true(_b.index_of(String(items[k]["block"])) > 0, "item %s places a real block" % k)
