## `--autotest`: plays the core loop of the slice and checks every system, writing screenshots to
## renders/game/ (or <exe dir>/autotest/ in exported builds) and AUTOTEST lines to autotest.log.
## Exit code 0 when every step passed.
extends Node

var gw: Node
var _log: FileAccess
var _out := ""
var _fails: Array[String] = []
var _passes := 0
var _shot := 0
var _t0 := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_out = Game.output_dir()
	_log = FileAccess.open(_out.path_join("autotest.log"), FileAccess.WRITE)
	_t0 = Time.get_ticks_msec()
	DisplayServer.window_set_size(Vector2i(1600, 900))
	_run.call_deferred()


func log_line(s: String) -> void:
	var line := "AUTOTEST %7.1fs %s" % [(Time.get_ticks_msec() - _t0) / 1000.0, s]
	print(line)
	if _log:
		_log.store_line(line)
		_log.flush()


func check(name: String, ok: bool, detail: String = "") -> bool:
	if ok:
		_passes += 1
		log_line("PASS %s %s" % [name, detail])
	else:
		_fails.append(name)
		log_line("FAIL %s %s" % [name, detail])
	return ok


func wait(s: float) -> void:
	await get_tree().create_timer(s, true, false, true).timeout


func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	_shot += 1
	var img := get_viewport().get_texture().get_image()
	var p := _out.path_join("%02d_%s.png" % [_shot, name])
	img.save_png(p)
	log_line("SHOT %s" % p.get_file())


func set_time(t: float) -> void:
	gw.time_frozen = true
	Game.cycle_t = t
	gw.daynight.update(t)
	for n: Npc in gw.npcs:
		n.mode = Npc.Mode.SCHEDULE
		n._hidden_until = 0.0
		n._snap_to_schedule()


func ground(x: float, z: float, from_y: float = 46.0) -> float:
	return gw.world.ground_below(Vector3(x, from_y, z))


func drive(move: Vector2, seconds: float, vertical: float = 0.0) -> void:
	var p: Player = gw.player
	p.auto_move = move
	p.auto_vertical = vertical
	await wait(seconds)
	p.auto_move = Vector2.ZERO
	p.auto_vertical = 0.0


func _run() -> void:
	await frames(5)
	var p: Player = gw.player
	log_line("START build %s" % JSON.stringify(gw.build_stats))
	check("world_built", int(gw.build_stats.get("chunks", 0)) > 100, "chunks=%s faces=%s mesh_ms=%s" % [gw.build_stats.get("chunks"), gw.build_stats.get("faces"), gw.build_stats.get("mesh_ms")])
	check("villagers_spawned", gw.npcs.size() == 11, "%d" % gw.npcs.size())
	check("hauntables_bound", gw.level.hauntables.size() >= 70, "%d" % gw.level.hauntables.size())
	Game.ecto = 100.0
	var only: Array = Game.cmd.get("autotest", [])
	if only.has("haunting"):
		await _haunting_update()
		log_line("DONE %d passed, %d failed %s" % [_passes, _fails.size(), str(_fails)])
		get_tree().quit(0 if _fails.is_empty() else 1)
		return
	if only.has("slice"):
		await _next_slice()
		log_line("DONE %d passed, %d failed %s" % [_passes, _fails.size(), str(_fails)])
		get_tree().quit(0 if _fails.is_empty() else 1)
		return
	if only.has("scare"):
		await _scares()
		log_line("DONE %d passed, %d failed %s" % [_passes, _fails.size(), str(_fails)])
		get_tree().quit(0 if _fails.is_empty() else 1)
		return

	# --- title screen
	var title := TitleScreen.new()
	gw.ui_layer.add_child(title)
	await frames(3)
	await shot("title_screen")
	title.queue_free()
	await frames(2)

	# --- drift
	set_time(0.2)
	p.teleport(Game.player_pos, 90.0)
	await wait(1.2)
	var start := p.global_position
	var g0 := ground(start.x, start.z, start.y + 1.0)
	check("hover", absf(start.y - g0 - Game.tuning.f("player.hover_height_m", 1.0)) < 0.35, "feet %.2f above ground" % (start.y - g0))
	log_line("INFO camera spring %.2f / %.2f m, pitch %.2f" % [p.spring.get_hit_length(), p.spring.spring_length, p._pitch])
	await shot("graveyard_night_start")
	await drive(Vector2(0, 1), 2.0)
	check("drift", p.global_position.distance_to(start) > 3.0, "moved %.1f m" % p.global_position.distance_to(start))
	var ec := Game.ecto
	await drive(Vector2.ZERO, 1.0, 1.0)
	check("ascend_costs_ecto", Game.ecto < ec, "ecto %.0f -> %.0f" % [ec, Game.ecto])
	await wait(2.0)
	check("glide_back_down", p.global_position.y - ground(p.global_position.x, p.global_position.z, p.global_position.y) < 1.6, "")

	# --- phase through a cottage wall (plaster/timber are phaseable)
	p.teleport(Vector3(102.5, 22.05, 87.0), 180.0)
	await wait(0.5)
	await drive(Vector2(0, 1), 1.6)
	check("phase_through_wall", p.global_position.z < 84.6, "z=%.2f (wall at z 85)" % p.global_position.z)
	await wait(0.4)
	await shot("inside_pip_cottage")
	check("camera_pulls_in_indoors", p.indoors, "")

	# --- running water stops the ghost
	p.teleport(Vector3(90.5, ground(90.5, 100.5) + 1.0, 100.5), 270.0)
	await wait(0.4)
	await drive(Vector2(0, 1), 3.5)
	check("stopped_by_stream", p.global_position.x > 87.5, "x=%.2f (water x 85..88)" % p.global_position.x)
	await shot("stream_blocks_ghost")
	p.teleport(Vector3(92.0, ground(92.0, 118.5) + 1.0, 118.6), 270.0)
	await wait(0.4)
	await drive(Vector2(0, 1), 4.0)
	check("cross_bridge", p.global_position.x < 83.5, "x=%.2f" % p.global_position.x)

	# --- gathering: one of each node type, a memory fragment, a tier II tool
	await _mine_nodes()

	# --- scaring: Creak, BOO, level 2, Flicker, suspicion, charm
	await _scares()

	# --- day/night
	set_time(0.01)
	p.teleport(Vector3(118.0, 30.0, 112.0), 200.0)
	p.aim_at(Vector3(113, 22, 98))
	await wait(0.6)
	await shot("millbrook_dusk")
	set_time(0.25)
	await wait(0.4)
	await shot("millbrook_night")
	var nights := Game.nights
	gw._cycle_events(0.075, 0.085)
	check("new_night", Game.nights == nights + 1, "night %d" % Game.nights)
	if FileAccess.file_exists(Game.SAVE_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(Game.save_path()))
	gw._cycle_events(0.575, 0.585)
	check("dawn_autosave", Game.has_save(), "")
	set_time(0.62)
	await wait(0.4)
	await shot("millbrook_dawn")

	# --- scattered by daylight, respawn
	set_time(0.8)
	p.teleport(Vector3(140.0, ground(140, 140) + 1.0, 140.0), 0.0)
	Game.fright_essence = maxf(Game.fright_essence, 20.0)
	Game.hp = 0.6
	await wait(0.5)
	await shot("daylight_burns")
	var waited := 0.0
	while not p.scattered_now and waited < 12.0:
		await wait(0.25)
		waited += 0.25
	check("scattered_by_daylight", p.scattered_now, "after %.1fs" % waited)
	check("essence_dropped", not Game.dropped_essence.is_empty(), "%d piles" % Game.dropped_essence.size())
	await wait(Game.tuning.f("player.scatter_time_s", 2.5))
	await shot("scattered_screen")
	var btn := gw.screen.find_child("ReturnButton", true, false) as Button if gw.screen else null
	if btn:
		btn.pressed.emit()
	else:
		gw.close_screen()
		p.respawn()
	await wait(0.6)
	var r: Array = Game.markers_by_id["respawn"]["pos"]
	check("respawn_at_mausoleum", p.global_position.distance_to(Vector3(r[0], r[1], r[2])) < 2.5 and Game.hp >= Game.max_hp() - 0.01, "")
	check("shelter_in_mausoleum", p.sheltered, "")
	gw.sleep_until_dusk()
	await wait(1.6)
	check("sleep_skips_day", Game.phase() in ["dusk"], "t=%.3f" % Game.cycle_t)

	# --- UI screens
	set_time(0.25)
	p.teleport(Vector3(112.0, 22.5, 96.0), 180.0)
	await wait(0.5)
	await shot("hud_square_night")
	gw.open_journal()
	await frames(4)
	await shot("journal")
	gw.close_screen()
	gw.open_inventory(true)
	await frames(4)
	await shot("inventory_workbench")
	gw.close_screen()
	gw.open_pause()
	await frames(4)
	await shot("pause")
	gw.open_settings()
	await frames(4)
	await shot("settings")
	gw.close_screen()
	check("ui_screens", gw.screen == null and not get_tree().paused, "")

	# --- save and load
	var c := Vector3i(60, int(ground(60.5, 60.5)) - 1, 60)
	var before: int = gw.world.get_block_v(c)
	gw.world.set_block(c, 0)
	Game.inventory.add("bone", 3)
	var bones := Game.inventory.count("bone")
	var frags := Game.fragments.size()
	var legend := Game.town.legend_points
	check("save", gw.save_game(), ProjectSettings.globalize_path(Game.save_path()))
	gw.world.set_block(c, before)
	Game.inventory.remove("bone", 3)
	gw.load_game()
	await frames(3)
	check("load_world_edit", gw.world.get_block_v(c) == 0, "")
	check("load_inventory", Game.inventory.count("bone") == bones, "")
	check("load_fragments_and_legend", Game.fragments.size() == frags and absf(Game.town.legend_points - legend) < 0.01, "")
	check("load_villager_memory", (Game.minds["agnes"] as VillagerMind).scares_taken >= 1, "")

	# --- performance
	set_time(0.25)
	p.teleport(Vector3(112.0, 30.0, 120.0), 180.0)
	p.aim_at(Vector3(110, 21, 92))
	gw._fps_samples.clear()
	await wait(3.0)
	log_line("PERF avg_fps %.1f over the village at night, %s" % [gw.avg_fps(), RenderingServer.get_video_adapter_name()])

	log_line("DONE %d passed, %d failed %s" % [_passes, _fails.size(), str(_fails)])
	if _log:
		_log.close()
	get_tree().quit(0 if _fails.is_empty() else 1)


func _aim_and_mine(target: Vector3, tool: String, max_swings: int = 20) -> String:
	var p: Player = gw.player
	var inv := Game.inventory
	inv.selected = inv.hotbar.find(tool)
	p._refresh_tool()
	var status := ""
	for i in max_swings:
		p.aim_at(target)
		await frames(2)
		p._update_targets()
		p._swing_left = 0.0
		status = p.try_mine()
		await wait(0.12)
		if status in ["broke", "cut"]:
			break
		if status not in ["hit"]:
			break
	return status


func _approach(target: Vector3, face: Vector3) -> void:
	var p: Player = gw.player
	var at := target + face * 2.2
	at.y = maxf(at.y - 0.4, ground(at.x, at.z, at.y + 1.0) + 0.4)
	p.teleport(at, 0.0)
	await wait(0.3)


func _mine_nodes() -> void:
	var p: Player = gw.player
	var lvl: Level = gw.level
	set_time(0.2)
	var kinds := ["grave_weeds", "fiber_grass", "grave_dirt", "eerie_ore_vein"]
	var done := {}
	Game.tuning.data["mining"]["fragment_chance_mult"] = 1000.0   # forced: the autotest must see a fragment
	var frag0 := Game.fragments.size()
	for id: String in lvl.gather_nodes:
		var e: Dictionary = lvl.gather_nodes[id]
		var nd: Dictionary = e["data"]
		var k := String(nd["kind"])
		if not kinds.has(k) or done.has(k):
			continue
		var target := Vector3.ZERO
		var face := Vector3(0, 0, 1)
		if e["node"] != null:
			target = (e["node"] as Node3D).global_position + Vector3(0, 0.3, 0)
			face = Vector3(0.0, 0.5, 1.0).normalized()
		else:
			var cc: Vector3i = e["cell"]
			target = Vector3(cc) + Vector3(0.5, 0.5, 0.5)
			if nd.has("face"):
				var f: Array = nd["face"]
				face = Vector3(f[0], f[1], f[2])
			else:
				face = Vector3(0, 1, 0)
			if face.y > 0.5:
				face = Vector3(0, 1, 0.8).normalized()
		await _approach(target, face)
		var st: String = await _aim_and_mine(target, String(nd["tool"]))
		done[k] = st
		check("mine_%s" % k, st in ["broke", "cut"], "%s -> %s" % [id, st])
		if k == "eerie_ore_vein":
			await wait(1.0)
			await shot("mining_eerie_ore")
	await wait(Game.tuning.f("mining.fragment_pickup_s", 1.4) + 1.5)
	Game.tuning.data["mining"]["fragment_chance_mult"] = 1.0
	check("memory_fragment_collected", Game.fragments.size() > frag0, "%d fragments" % Game.fragments.size())
	# craft Sledgehammer II at the workbench (top up what one pass of mining doesn't give)
	var recipe: Dictionary = {}
	for r in Game.tuning.a("recipes"):
		if r["id"] == "sledgehammer_t2":
			recipe = r
	var topped := {}
	for item: String in recipe["needs"]:
		var miss := int(recipe["needs"][item]) - Game.inventory.count(item)
		if miss > 0:
			Game.inventory.add(item, miss)
			topped[item] = miss
	log_line("INFO topped up for the recipe: %s" % JSON.stringify(topped))
	p.teleport(gw.level.workbench_pos() + Vector3(0, 0.6, 0.6), 180.0)
	await wait(0.4)
	check("at_workbench", p.interact() == "workbench", "")
	await frames(3)
	await shot("workbench_crafting")
	check("craft_tier2", Game.inventory.craft(recipe) and Game.inventory.tool_tier("sledgehammer") == 2, "")
	gw.close_screen()
	await frames(2)
	for k2 in ["spectral_stone_vein", "iron_ore_vein"]:
		for id: String in lvl.gather_nodes:
			var e2: Dictionary = lvl.gather_nodes[id]
			if String(e2["data"]["kind"]) != k2 or e2["node"] != null:
				continue
			var cc2: Vector3i = e2["cell"]
			var f2: Array = e2["data"].get("face", [0, 1, 0])
			var face2 := Vector3(f2[0], f2[1], f2[2])
			if id.begins_with("ore_node_") and int(id.substr(9)) <= 17:
				continue   # the mausoleum's own walls; leave the home standing
			var target2 := Vector3(cc2) + Vector3(0.5, 0.5, 0.5)
			await _approach(target2, face2 if face2.y < 0.5 else Vector3(0, 1, 0.8).normalized())
			var st2: String = await _aim_and_mine(target2, "sledgehammer", 30)
			check("mine_%s_tier2" % k2, st2 == "broke", "%s -> %s" % [id, st2])
			break


func _scares() -> void:
	var p: Player = gw.player
	var dir: ScareDirector = gw.director
	var agnes: Npc = gw.npc_by_id("agnes")
	# 23:30 (t 0.286): Agnes rocks alone in Josiah's chair, her back to the room.
	set_time(0.30)
	await wait(0.5)
	var step: Dictionary = agnes.data["schedule"][agnes.step_index]
	log_line("INFO agnes step %s at %s" % [step["id"], agnes.global_position])
	# drift close and overhear her muttering
	var behind := agnes.global_position - agnes.forward * 1.6 + Vector3(0, 0.6, 0)
	p.teleport(behind, rad_to_deg(agnes.rotation.y))
	var heard_before := agnes.mind.heard_lines.size()
	for i in 3:
		dir._overhear_cd.clear()
		await wait(0.3)
	check("overhear_mutters", agnes.mind.heard_lines.size() > heard_before, "%d lines" % agnes.mind.heard_lines.size())
	check("fear_discovered", agnes.mind.fear_discovered, String(agnes.mind.fear))
	await shot("overheard_agnes")
	var door: Hauntable = gw.level.hauntables["door_cottage_1"]
	var candle: Hauntable = gw.level.hauntables["candle_1"]
	check("flicker_locked_at_level1", dir.haunt(candle, "snuff") == "locked", "")
	# build: creak the door until she's primed (sweet spot), never past her nerve
	var acts := 0
	while agnes.mind.frac() < ScareMath.stage_from("primed", Game.tuning.a("scare.stages")) and acts < 10:
		p.aim_at(door.world_pos())
		var action := "drift_open" if acts % 2 == 0 else "creak"
		var st := dir.haunt(door, action)
		if st == "ok":
			acts += 1
			log_line("INFO %s door: agnes unease %.1f / %.0f (%s)" % [action, agnes.mind.unease, agnes.mind.nerve, agnes.mind.stage(Game.tuning.d("scare"))])
			if acts == 1:
				await frames(2)
				await shot("creak_door")
		Game.ecto = 100.0
		await wait(Game.tuning.f("haunting.ecto_cost.creak", 4) * 0 + float(door.data.get("cooldown_s", 6.0)) + 0.1)
	check("creak_raises_unease", acts > 0 and agnes.mind.unease > 0.0, "%d acts" % acts)
	await shot("unease_meter_primed")
	# break: BOO from behind
	p.teleport(agnes.global_position - agnes.forward * 1.4 + Vector3(0, 0.5, 0), rad_to_deg(agnes.rotation.y))
	p.aim_at(agnes.head_pos())
	Game.ecto = 100.0
	var f0 := float(Game.path_fright["haunting"])
	var res: Dictionary = p.do_boo()
	await wait(0.35)
	await shot("boo_grade_stamp")
	check("boo_graded", String(res.get("outcome", "")) in ["spooked", "terrified", "legendary"], "%s score %s %s" % [res.get("outcome"), res.get("score"), res.get("parts")])
	check("fright_paid", float(Game.path_fright["haunting"]) > f0, "%.0f Fright" % Game.path_fright["haunting"])
	await wait(1.5)
	await shot("big_scare_reaction")
	check("haunting_level_2", Game.haunting_level() >= 2, "level %d" % Game.haunting_level())
	if Game.haunting_level() < 2:
		Game.add_fright(30.0, ["haunting"])
	# second scare: Flicker + Creak on the same door -> suspicion, a charm on the door
	await wait(Game.tuning.f("scare.recover_after_break_s", 14.0) + 4.0)
	set_time(0.31)
	await wait(0.5)
	p.teleport(agnes.global_position - agnes.forward * 1.6 + Vector3(0, 0.6, 0), rad_to_deg(agnes.rotation.y))
	var tries := 0
	var snuffed := false
	var hs := ["candle_1", "candle_2", "lantern_1"]
	while agnes.mind.frac() < ScareMath.stage_from("primed", Game.tuning.a("scare.stages")) and tries < 14:
		Game.ecto = 100.0
		for hid: String in hs:
			var h: Hauntable = gw.level.hauntables.get(hid)
			if h == null:
				continue
			if agnes.mind.frac() >= 0.78:
				break
			if not h.lit:
				h.set_lit(true)
			var st2 := dir.haunt(h, "snuff" if agnes.mind.frac() < 0.5 else "dim")
			if st2 == "ok" and h.kind == "candle":
				snuffed = true
		if agnes.mind.frac() < 0.8:
			dir.haunt(door, "creak")
		tries += 1
		await wait(1.0)
	check("flicker_candle", snuffed, "agnes unease %.1f / %.0f" % [agnes.mind.unease, agnes.mind.nerve])
	await shot("flicker_snuffed")
	while agnes.mind.suspicion < 0.4 and tries < 30:
		# keep the pressure on without bolting her: dim lights, let unease settle
		for hid: String in hs:
			var h2: Hauntable = gw.level.hauntables.get(hid)
			if h2 and h2.lit and agnes.mind.frac() < 0.85:
				dir.haunt(h2, "dim")
		tries += 1
		Game.ecto = 100.0
		await wait(1.0)
	check("suspicious_villager", not agnes.mind.fired_reactions.is_empty(), "suspicion %.2f, reactions %s" % [agnes.mind.suspicion, agnes.mind.fired_reactions])
	if agnes.mind.frac() < 0.8:
		agnes.mind.unease = agnes.mind.nerve * 0.82
		log_line("INFO topped agnes up to primed for the second break")
	p.teleport(agnes.global_position - agnes.forward * 1.4 + Vector3(0, 0.5, 0), rad_to_deg(agnes.rotation.y))
	p.aim_at(agnes.head_pos())
	Game.ecto = 100.0
	var res2: Dictionary = p.do_boo()
	check("second_break", String(res2.get("outcome", "")) in ["spooked", "terrified", "legendary"], "%s score %s %s" % [res2.get("outcome"), res2.get("score"), res2.get("parts")])
	await wait(0.5)
	check("charm_hung", Game.town.is_unhauntable("door_cottage_1"), "charms %s" % Game.town.charms.keys())
	check("legend_grows", Game.town.legend_points > 0.0, "%.0f points, '%s'" % [Game.town.legend_points, Game.town.legend_name()])
	await wait(1.0)
	await shot("charm_on_door")
	# a botched BOO on Bram (calm) makes him laugh it off
	var bram: Npc = gw.npc_by_id("bram")
	set_time(0.15)
	await wait(0.4)
	p.teleport(bram.global_position + bram.forward * 2.0 + Vector3(0, 0.5, 0), rad_to_deg(bram.rotation.y) + 180.0)
	var n0 := bram.mind.nerve
	Game.ecto = 100.0
	p._boo_cd = 0.0
	var res3: Dictionary = p.do_boo()
	check("botched_boo", String(res3.get("outcome", "")) == "botch" and bram.mind.nerve > n0, "%s %s" % [res3.get("outcome"), res3.get("reason")])
	await wait(0.6)
	await shot("botch_bram")


func _next_slice() -> void:
	var player: Player = gw.player
	set_time(0.25)
	check("flicker_initially_locked", not Game.ability_unlocked("flicker"))
	Game.add_fright(10, ["haunting"])
	check("flicker_after_first_spook", Game.ability_unlocked("flicker") and Game.pending_traits() == 1)
	Game.add_fright(65, ["haunting"])
	Game.choose_trait("haunting")
	Game.choose_trait("drift")
	Game.choose_trait("resilience")
	check("stacked_evolution", Game.pending_traits() == 0 and Game.max_hp() == 18.0)
	await shot("evolved_ghost")
	gw.open_inventory(false)
	await frames(3)
	var inventory: InventoryScreen = gw.screen
	for i in Inventory.TOOLS.size():
		inventory._select_slot(i + 5)
		inventory._assign(Inventory.TOOLS[i])
		check("assign_" + Inventory.TOOLS[i], Game.inventory.selected_id() == Inventory.TOOLS[i]
			and Game.inventory.hotbar.count(Inventory.TOOLS[i]) == 1)
	await shot("tool_hotbar")
	gw.close_screen()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	var key := InputEventKey.new()
	key.physical_keycode = KEY_W
	key.pressed = true
	player._input(key)
	key.pressed = false
	player._input(key)
	key.pressed = true
	player._input(key)
	check("double_tap_sprint", player._sprint_key == KEY_W)
	key.pressed = false
	player._input(key)
	check("release_ends_sprint", player._sprint_key == KEY_NONE)
	player._input(InputEventKey.new())
	player._notification(NOTIFICATION_APPLICATION_FOCUS_OUT)
	check("focus_loss_resets_sprint", player._direction_taps.is_empty())
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var possession: Node = player.possession
	var scarecrow: Hauntable = gw.level.hauntables["scarecrow_1"]
	var point := scarecrow.root.global_position
	player.teleport(point + Vector3(0, 0.9, 2.5), 180.0)
	player.aim_at(point + Vector3.UP * 1.15)
	await frames(12)
	possession.toggle()
	check("object_possession", possession.host == scarecrow.root)
	if possession.host:
		_press_host_action(player)
		await shot("object_possession")
		possession.release()
		possession.toggle()
		check("possession_cooldown", possession.host == null)
	Game.add_fright(25, ["haunting"])
	check("animal_unlock", Game.ability_unlocked("animal_possession") and not Game.ability_unlocked("villager_possession"))
	var dog: Node3D = possession.animals[0]
	var dog_pos := dog.global_position
	player.teleport(dog_pos + Vector3(0, 1.0, 1.3), 180.0)
	player.aim_at(dog_pos + Vector3.UP * 0.35)
	possession.toggle()
	check("animal_possession", possession.host == dog)
	if possession.host:
		_press_host_action(player)
		possession.left = 0.01
		await wait(0.1)
		check("animal_timeout", not possession.host and player.model.visible)
	Game.add_fright(50, ["haunting"])
	var agnes: Npc = gw.npc_by_id("agnes")
	for n: Npc in gw.npcs:
		n.visible = n == agnes
		n._hidden_until = 1.0e10 if n != agnes else 0.0
	agnes.global_position = Vector3(55.5, ground(55.5, 82.5), 82.5)
	agnes.asleep = false
	agnes.mode = Npc.Mode.SCHEDULE
	agnes._investigate_after = 0.0
	agnes.mind.unease = agnes.mind.nerve * 0.9
	var agnes_pos := agnes.global_position
	player.teleport(agnes_pos + Vector3(0, 1.0, 1.6), 180.0)
	player.aim_at(agnes.head_pos())
	possession.toggle()
	check("villager_possession", possession.host == agnes and agnes.possessed)
	if possession.host:
		_press_host_action(player)
		possession.release()
		check("villager_resumes_schedule", not agnes.possessed)
	var rooms: Array = gw.CavernSystem.ROOMS
	for i in rooms.size():
		var room: Dictionary = rooms[i]
		var c := Vector3(room.center) + Vector3(0.5, 0, 0.5)
		player.teleport(Vector3(c.x, room.surface + 0.15, c.z - 3), 180.0)
		check("enter_" + room.id, player.interact() == "cavern")
		player.aim_at(c + Vector3(0, 1.0, 1.8))
		await wait(0.65)
		check("cave_shelter_" + room.id, player.sheltered and gw.caverns.active == i)
		await shot(room.id)
		if i == 1:
			var enemy: Node3D = gw.caverns.enemies[i]
			player.teleport(enemy.global_position, 180.0)
			var health := Game.hp
			await wait(1.7)
			check("enemy_telegraphs_and_damages", Game.hp < health)
			Game.hp = Game.max_hp()
		player.teleport(c + Vector3(3.2, 1, 0), 180.0)
		await frames(5)
		check("memory_" + room.id, Game.fragments.has(room.id))
		player.teleport(c + Vector3(0, 0.9, -3), 180.0)
		check("exit_" + room.id, player.interact() == "cavern")
	check("save_slice", gw.save_game())
	gw.load_game()
	check("reload_slice", Game.fragments.size() == 3 and Game.trait_rank("drift") == 1
		and Game.inventory.hotbar[5] == "scythe")
	var legacy := Game._json(Game.save_path())
	legacy.erase("traits")
	legacy["version"] = 1
	var legacy_file := FileAccess.open(Game.save_path(), FileAccess.WRITE)
	legacy_file.store_string(JSON.stringify(legacy))
	legacy_file.close()
	gw.load_game()
	check("legacy_save_awards_unspent_traits", Game.pending_traits() == 4
		and Game.trait_rank("drift") == 0 and Game.fragments.size() == 3)

func _press_host_action(player: Player) -> void:
	var key := InputEventKey.new()
	key.physical_keycode = KEY_SPACE
	key.pressed = true
	player._unhandled_input(key)
	check("space_triggers_host_action_%d" % player.possession.tier, player.possession.acted)


func _haunting_update() -> void:
	var player: Player = gw.player
	set_time(0.25)
	var director: ScareDirector = gw.director
	var agnes: Npc = gw.npc_by_id("agnes")
	var bell: Hauntable = gw.level.hauntables["bell_1"]
	check("bell_locked", director.haunt(bell, "ring") == "locked")
	Game.add_fright(45.0, ["haunting"])
	for animal: Node3D in player.possession.animals:
		animal.global_position = bell.world_pos() + Vector3(1, 0, 1)
	agnes.global_position = bell.world_pos() + Vector3(1, 0, 1)
	agnes.asleep = false
	agnes.visible = true
	var before := agnes.mind.unease
	check("bell_rings", director.haunt(bell, "ring") == "ok")
	check("bell_builds_unease", agnes.mind.unease > before)
	check("bell_startles_animals", player.possession.animal_alarm.size() == 2)
	check("bell_animates", bell._tween != null and bell._tween.is_running())
	check("bell_cooldown", director.haunt(bell, "ring") == "cooldown")
	var tested := {}
	for h: Hauntable in gw.level.hauntables.values():
		if h.kind not in ["door", "floorboard", "candle", "oil_lamp", "lantern", "rocking_chair", "wardrobe", "portrait"]:
			continue
		if tested.has(h.kind) or not h.root.is_visible_in_tree():
			continue
		tested[h.kind] = true
		h.mood_on = true
		for action: String in [h.gentle_action(), h.strong_action()]:
			if action.is_empty():
				continue
			h._cooldown_until = 0.0
			h.set_lit(true)
			Game.ecto = 100.0
			agnes.global_position = h.world_pos() + Vector3(0.4, 0, 0)
			agnes.asleep = false
			agnes.mind.unease = 0
			check("haunt_%s_%s" % [h.kind, action], director.haunt(h, action) == "ok")
			if h.kind != "portrait" and h.data.get("source") != "carried":
				check("fear_%s_%s" % [h.kind, action], agnes.mind.unease > 0)
	Game.add_fright(255.0, ["haunting"])
	check("late_unlocks", Game.ability_unlocked("door_slam") and Game.ability_unlocked("blackout") and Game.ability_unlocked("aftershock"))
	var door: Hauntable = gw.level.hauntables["lantern_end_door_0"]
	door._cooldown_until = 0.0
	Game.ecto = 100
	check("strong_haunt_slams_door", door.strong_action() == "slam" and director.haunt(door, "slam") == "ok")
	var first: Hauntable = gw.level.hauntables["lantern_end_light_0"]
	var second: Hauntable = gw.level.hauntables["lantern_end_light_1"]
	var third: Hauntable = gw.level.hauntables["lantern_end_light_2"]
	for light: Hauntable in [first, second, third]:
		light.mood_on = true
		light.set_lit(true)
		light._cooldown_until = 0.0
	check("blackout_snuffs_nearby_lights", director.haunt(first, "snuff") == "ok" and not second.lit and not third.lit)
	var ward := TownMemory.new()
	ward.from_save({"charms": {"door": {"charm": "test", "nights": 3}}, "salt_lines": {"door": {"nights": 3}}})
	ward.new_night()
	check("old_charm_expires_at_nightfall", ward.charms.is_empty() and ward.salt_lines.door.nights == 2)
	for id in ["rowan", "moss"]:
		var resident: Npc = gw.npc_by_id(id)
		player.teleport(resident.global_position + Vector3(0, 1, 3), 180)
		player.aim_at(resident.head_pos())
		await frames(6)
		check("district_" + id, String(Game.area_at(resident.global_position).id) in ["lantern_end", "reedcross"])
		await shot("district_" + id)
	var sentinel: Node3D = gw.caverns.enemies[2]
	player.teleport(sentinel.global_position + Vector3(0, 1, -2.5), 0)
	player.aim_at(sentinel.global_position + Vector3.UP * 1.3)
	await frames(6)
	check("sentinel_uses_blender_rig", gw.caverns.sentinel_animation.has_animation("attack_slam"))
	await shot("blender_crystal_sentinel")
