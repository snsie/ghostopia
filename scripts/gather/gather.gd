## Mining and gathering: hits per block/node (tool, tier, hardness; node hit counts from the
## population data), drops into the inventory, memory fragments floating out of natural blocks
## into the journal, node regrowth timers.
class_name Gather
extends Node

var gw: Node
var world: VoxelWorld
var level: Level
var _wisps: Array[Dictionary] = []   # {node, id, t, from}


func setup(p_gw: Node) -> void:
	gw = p_gw
	world = gw.world
	level = gw.level


func hits_for_cell(c: Vector3i, b: int, tier: int) -> int:
	var t := Game.tuning
	var nid: Variant = level.cell_nodes.get(c)
	var speed: Array = t.a("mining.tier_speed")
	if nid != null:
		var hits := int(level.gather_nodes[nid]["data"].get("hits", 3))
		var k := float(speed[clampi(tier - 1, 0, speed.size() - 1)]) if not speed.is_empty() else 1.0
		return maxi(1, int(ceil(hits / k)))
	return Game.blocks.hits_needed(b, tier, t.f("mining.hits_per_hardness", 2.0), speed, t.i("mining.min_hits", 1))


func hit_sound(b: int) -> String:
	var tool := String(Game.blocks.info(b).get("tool", "shovel"))
	var cat := String(Game.blocks.info(b).get("category", ""))
	if tool == "sledgehammer":
		return "mine_stone"
	if tool == "shovel":
		return "mine_dirt"
	if cat == "plant" or Game.blocks.id_of(b) in ["leaves", "thatch"]:
		return "mine_plant"
	return "mine_wood"


func break_block(c: Vector3i, b: int, player: Node3D) -> void:
	var bid := Game.blocks.id_of(b)
	var nid: Variant = level.cell_nodes.get(c)
	var drops := {}
	var frag_chance := -1.0
	var area := String(Game.area_at(Vector3(c)).get("id", "open_plains"))
	if nid != null:
		var nd: Dictionary = level.gather_nodes[nid]["data"]
		drops = BlockRegistry.roll_drop_list(nd.get("yields", Game.blocks.info(b).get("drops", [])), Game.rng)
		frag_chance = float(nd.get("fragment_chance", -1.0))
		area = String(nd.get("area", area))
		Game.nodes_state[nid] = float(nd.get("regrow", {}).get("seconds", 1200))
		level.gather_nodes[nid]["alive"] = false
	else:
		drops = Game.blocks.roll_drops(b, Game.rng)
	world.set_block(c, 0)
	Game.stats["blocks_mined"] += 1
	Sfx.play_at("block_break", Vector3(c) + Vector3.ONE * 0.5, 0.0)
	Fx.burst(gw, Vector3(c) + Vector3(0.5, 0.5, 0.5), _dust_color(bid), 18, 2.0, 0.7, 0.1, false)
	_give(drops)
	if Game.blocks.natural[b] == 1:
		var mult := Game.tuning.f("mining.fragment_chance_mult", 1.0)
		var f := Game.fragment_roller.roll(bid, area, Game.fragments, Game.rng, mult, frag_chance)
		if f != "":
			spawn_fragment(f, Vector3(c) + Vector3(0.5, 0.5, 0.5))
	(player as Player).mined.emit(bid, drops)


func _dust_color(bid: String) -> Color:
	match bid:
		"eerie_ore":
			return Color(0.7, 0.5, 1.0)
		"spectral_stone":
			return Color(0.5, 0.95, 0.9)
		"stone", "cobblestone", "iron_ore":
			return Color(0.6, 0.6, 0.65)
		"grass", "leaves", "tall_grass":
			return Color(0.45, 0.65, 0.35)
	return Color(0.5, 0.38, 0.28)


func hit_node(id: String, tool: String, tier: int, player: Node3D) -> String:
	var e: Dictionary = level.gather_nodes.get(id, {})
	if e.is_empty() or not e["alive"]:
		return "nothing"
	var nd: Dictionary = e["data"]
	if String(nd.get("tool", "scythe")) != tool:
		gw.hud.hint("Cut weeds with the scythe")
		return "wrong tool"
	if tier < int(nd.get("tier", 1)):
		gw.hud.hint("Needs a better %s" % tool)
		return "tier"
	e["hits"] = int(e.get("hits", 0)) + 1
	var vis: Node3D = e["node"]
	Sfx.play_at("mine_plant", vis.global_position, 0.0)
	var tw := create_tween()
	tw.tween_property(vis, "rotation:z", 0.25, 0.08)
	tw.tween_property(vis, "rotation:z", 0.0, 0.15)
	if int(e["hits"]) < hits_for_node(nd, tier):
		return "hit"
	e["hits"] = 0
	level.set_node_alive(id, false)
	Game.nodes_state[id] = float(nd.get("regrow", {}).get("seconds", 600))
	Fx.burst(gw, vis.global_position + Vector3(0, 0.3, 0), Color(0.5, 0.7, 0.35), 14, 1.6, 0.6, 0.08, false)
	_give(BlockRegistry.roll_drop_list(nd.get("yields", []), Game.rng))
	var block_key := "tall_grass"
	var f := Game.fragment_roller.roll(block_key, String(nd.get("area", "")), Game.fragments, Game.rng,
		Game.tuning.f("mining.fragment_chance_mult", 1.0), float(nd.get("fragment_chance", 0.03)))
	if f != "":
		spawn_fragment(f, vis.global_position + Vector3(0, 0.4, 0))
	(player as Player).mined.emit(String(nd["kind"]), {})
	return "cut"


func hits_for_node(nd: Dictionary, tier: int) -> int:
	var speed: Array = Game.tuning.a("mining.tier_speed")
	var k := float(speed[clampi(tier - 1, 0, speed.size() - 1)]) if not speed.is_empty() else 1.0
	return maxi(1, int(ceil(float(nd.get("hits", 1)) / k)))


func _give(drops: Dictionary) -> void:
	var parts: Array[String] = []
	for k: String in drops:
		Game.inventory.add(k, int(drops[k]))
		var nm := String(Game.tuning.d("items").get(k, {}).get("name", k.capitalize()))
		parts.append("+%d %s" % [int(drops[k]), nm])
	if not parts.is_empty():
		gw.hud.pickup(", ".join(parts))
		Sfx.play("pickup", -6.0)


func spawn_fragment(id: String, at: Vector3) -> void:
	var w := Fx.memory_wisp()
	gw.add_child(w)
	w.global_position = at
	_wisps.append({"node": w, "id": id, "t": 0.0, "from": at})
	Sfx.play_at("fragment_chime", at, 0.0)


func _process(dt: float) -> void:
	var player: Node3D = gw.player
	for i in range(_wisps.size() - 1, -1, -1):
		var e: Dictionary = _wisps[i]
		e["t"] = float(e["t"]) + dt
		var n: Node3D = e["node"]
		var t := float(e["t"])
		var rise := Game.tuning.f("mining.fragment_pickup_s", 1.4)
		if t < rise:
			n.global_position = (e["from"] as Vector3) + Vector3(sin(t * 5.0) * 0.15, t * 0.8, cos(t * 4.0) * 0.15)
		else:
			var target := player.global_position + Vector3(0, 0.4, 0)
			n.global_position = n.global_position.lerp(target, clampf(dt * 6.0, 0.0, 1.0))
			if n.global_position.distance_to(target) < 0.35 or t > rise + 3.0:
				n.queue_free()
				_wisps.remove_at(i)
				Game.collect_fragment(String(e["id"]))
