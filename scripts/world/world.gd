## Main scene: title screen, then builds Millbrook at runtime from the task1-4 data (voxels, props,
## villagers, the ghost), runs the inverted day/night cycle, the scare director and the UI flow
## (HUD, journal, inventory/workbench, Scattered, pause, settings), save/load and the self-tests.
extends Node3D

var world: VoxelWorld
var level: Level
var player: Player
var director: ScareDirector
var gather: Gather
var daynight: DayNight
var hud: Hud
var npcs: Array[Npc] = []
var ui_layer: CanvasLayer
const CavernSystem = preload("res://scripts/world/caverns.gd")
var caverns: Node3D
var _conversation_at := 0.0
var screen: Control          # the open modal screen (journal, inventory, pause...) or null
var title: TitleScreen
var started := false
var build_stats := {}
var _night_seen := -1
var _dawn_saved := false
var _amb_t := 0.0
var _outline: MeshInstance3D
var _essence_nodes: Array[Node3D] = []
var _loading: Control
var _warned_dawn := false
var _fps_samples: Array[float] = []
var time_frozen := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	ui_layer = CanvasLayer.new()
	ui_layer.layer = 10
	add_child(ui_layer)
	get_tree().auto_accept_quit = false
	if Game.has_flag("autotest") or Game.has_flag("tour"):
		await start_game(false)
		var script_path := "res://scripts/debug/autotest.gd" if Game.has_flag("autotest") else "res://scripts/debug/tour.gd"
		var runner: Node = (load(script_path) as GDScript).new()
		runner.set("gw", self)
		add_child(runner)
	else:
		show_title()


func show_title() -> void:
	title = TitleScreen.new()
	ui_layer.add_child(title)
	title.continue_pressed.connect(func() -> void: _start_from_title(true))
	title.new_game_pressed.connect(func() -> void: open_characterizer(true))
	title.settings_pressed.connect(func() -> void: open_screen(Menus.settings(close_screen)))
	title.quit_pressed.connect(quit_game)


func _start_from_title(load_save: bool) -> void:
	if title:
		title.queue_free()
		title = null
	await start_game(load_save)


func _show_loading(text: String) -> void:
	_loading = Control.new()
	_loading.theme = UiKit.theme()
	_loading.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/ui/title_screen.png")
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.modulate = Color(0.45, 0.45, 0.6)
	_loading.add_child(bg)
	var l := UiKit.heading(text, 40, UiKit.WHITE)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_loading.add_child(UiKit.centered(l))
	ui_layer.add_child(_loading)


func start_game(load_save: bool, keep_appearance: bool = false) -> void:
	_show_loading("Drifting into the Veil…")
	await get_tree().process_frame
	await get_tree().process_frame
	var save := {}
	if load_save:
		save = Game.load_game()
	else:
		Game.new_game(keep_appearance)
	var t0 := Time.get_ticks_msec()
	world = VoxelWorld.new()
	world.name = "VoxelWorld"
	add_child(world)
	world.load_level(Game.layout, Game.blocks, Game.tuning.f("world.vertex_jitter_m", 0.035))
	CavernSystem.carve(world)
	preload("res://scripts/world/districts.gd").build(world)
	if save.has("world_edits"):
		world.apply_edits(save["world_edits"])
	build_stats = world.build_all()
	build_stats["load_ms"] = Time.get_ticks_msec() - t0
	level = Level.new()
	level.name = "Level"
	add_child(level)
	level.build(world)
	gather = Gather.new()
	gather.name = "Gather"
	add_child(gather)
	director = ScareDirector.new()
	director.name = "Director"
	add_child(director)
	player = Player.new()
	add_child(player)
	gather.setup(self)
	director.setup(self)
	player.setup(self)
	for v in Game.population.get("villagers", []):
		var n := Npc.new()
		add_child(n)
		n.setup(v, level, world)
		npcs.append(n)
	daynight = DayNight.new()
	daynight.name = "DayNight"
	add_child(daynight)
	daynight.setup(level, world, self)
	hud = Hud.new()
	ui_layer.add_child(hud)
	hud.setup(self)
	director.graded.connect(hud.show_grade)
	player.scattered.connect(_on_scattered)
	caverns = CavernSystem.new()
	add_child(caverns)
	caverns.setup(self)
	_make_outline()
	player.teleport(Game.player_pos, Game.player_yaw)
	director.restore_memory_visuals()
	refresh_essence_markers()
	for n: Node in [world, level, gather, director, player, daynight]:
		n.process_mode = Node.PROCESS_MODE_PAUSABLE
	for n in npcs:
		n.process_mode = Node.PROCESS_MODE_PAUSABLE
	build_stats["total_ms"] = Time.get_ticks_msec() - t0
	print("WORLD built: %s" % JSON.stringify(build_stats))
	daynight.update(Game.cycle_t)
	_night_seen = Game.nights
	_loading.queue_free()
	started = true
	apply_settings()
	Game.settings_changed.connect(apply_settings)
	if not Game.has_flag("autotest") and not Game.has_flag("tour"):
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		hud.toast("Night falls on Millbrook. Drift down to the village and listen to the living.", "info")


func _make_outline() -> void:
	_outline = MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(2, 2)
	q.flip_faces = true
	_outline.mesh = q
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/outline.gdshader")
	_outline.material_override = m
	_outline.extra_cull_margin = 16384.0
	_outline.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	player.camera.add_child(_outline)
	_outline.position = Vector3(0, 0, -0.5)


func apply_settings() -> void:
	if not started:
		return
	_outline.visible = bool(Game.settings["outlines"])
	daynight.apply_settings()
	get_viewport().scaling_3d_scale = float(Game.settings["render_scale"])


func npc_by_id(id: String) -> Npc:
	for n in npcs:
		if n.id == id:
			return n
	return null


# ---------------------------------------------------------------- loop

func _process(dt: float) -> void:
	if not started:
		return
	var paused := get_tree().paused
	if not paused:
		_fps_samples.append(Engine.get_frames_per_second())
		if _fps_samples.size() > 600:
			_fps_samples.pop_front()
		var now := Time.get_ticks_msec() / 1000.0
		if not time_frozen:
			var prev := Game.cycle_t
			Game.cycle_t = fmod(Game.cycle_t + dt / Game.cycle_length(), 1.0)
			_cycle_events(prev, Game.cycle_t)
		var area := Game.area_at(player.global_position)
		var rem := float(Game.town.remembrance.get(area.get("id", ""), 1.0))
		var fb := Game.tuning.f("remembrance.fading_below", 0.4)
		var fa := Game.tuning.f("remembrance.fully_faded_at", 0.1)
		daynight.fade_k = move_toward(daynight.fade_k, clampf((fb - rem) / maxf(fb - fa, 0.01), 0.0, 1.0), dt * 0.3)
		daynight.update(Game.cycle_t)
		director.tick(dt, now)
		for n in npcs:
			n.tick(dt, now)
		level.tick_nodes(dt)
		caverns.tick(dt)
		_try_conversation(now)
	_amb_t -= dt
	if _amb_t <= 0.0:
		_amb_t = 0.5
		Sfx.ambience({} if caverns.active >= 0 else daynight.ambience_for(player.global_position))
		var ph := Game.phase()
		if caverns.active >= 0:
			Sfx.music(CavernSystem.ROOMS[caverns.active].id)
		else:
			Sfx.music("night_theme" if ph in ["night", "dusk"] else "day_theme")


func _try_conversation(now: float) -> void:
	if now < _conversation_at:
		return
	_conversation_at = now + 4.0
	for i in npcs.size():
		var first: Npc = npcs[i]
		if not first.available_to_chat() or first.global_position.distance_to(player.global_position) > 12.0:
			continue
		for j in range(i + 1, npcs.size()):
			var second: Npc = npcs[j]
			if second.available_to_chat() and first.global_position.distance_to(second.global_position) < 2.2:
				first.chat_with(second, now)
				_conversation_at = now + 30.0
				return


func _cycle_events(prev: float, t: float) -> void:
	var night_start := float(Game.layout["lighting"]["cycle"]["phases"]["night"][0])
	var dawn_t := float(Game.layout["lighting"]["cycle"]["phases"]["dawn"][0])
	var warn := Game.tuning.f("cycle.dawn_warning_t", 0.555)
	if _crossed(prev, t, night_start):
		Game.nights += 1
		director.new_night()
		hud.toast("Night %d. The living are out with their lanterns." % (Game.nights + 1), "info")
	if _crossed(prev, t, warn):
		Sfx.play("dawn_warning")
		hud.toast("Dawn is near. Shelter underground or in the mausoleum.", "memory")
	if _crossed(prev, t, dawn_t) and Game.tuning.get_value("cycle.autosave_at_dawn", true):
		save_game()
		hud.toast("Autosaved at dawn", "info")


static func _crossed(prev: float, t: float, mark: float) -> bool:
	if prev <= t:
		return prev < mark and t >= mark
	return prev < mark or t >= mark


func slowmo(seconds: float, scale: float) -> void:
	Engine.time_scale = scale
	var tm := get_tree().create_timer(seconds, true, false, true)
	tm.timeout.connect(func() -> void: Engine.time_scale = 1.0)


func avg_fps() -> float:
	if _fps_samples.is_empty():
		return 0.0
	var s := 0.0
	for f in _fps_samples:
		s += f
	return s / _fps_samples.size()


# ---------------------------------------------------------------- UI flow

func _unhandled_input(e: InputEvent) -> void:
	if not started or title:
		return
	if screen != null or player.possession.host:
		return
	if e.is_action_pressed("pause"):
		open_pause()
	elif e.is_action_pressed("journal"):
		open_journal()
	elif e.is_action_pressed("inventory"):
		open_inventory(player.near_workbench())
	elif e is InputEventMouseButton and e.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and not player.scattered_now:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func open_screen(c: Control) -> void:
	close_screen()
	screen = c
	ui_layer.add_child(c)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if started:
		get_tree().paused = true
	Sfx.ui("ui_open")


func close_screen() -> void:
	if screen and is_instance_valid(screen):
		screen.queue_free()
		Sfx.ui("ui_close")
	screen = null
	if title:
		return
	get_tree().paused = false
	if started and not player.scattered_now and not Game.has_flag("autotest") and not Game.has_flag("tour"):
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func open_journal() -> void:
	var j := JournalScreen.new()
	j.closed.connect(close_screen)
	open_screen(j)


func open_inventory(at_workbench: bool) -> void:
	var inv := InventoryScreen.new()
	inv.at_workbench = at_workbench
	inv.closed.connect(close_screen)
	open_screen(inv)


func open_characterizer(for_new_game: bool) -> void:
	if for_new_game:
		Game.set_appearance(GhostAppearance.defaults())
	var ch := CharacterizerScreen.new()
	ch.is_new_game = for_new_game
	if for_new_game:
		ch.confirmed.connect(func() -> void:
			close_screen()
			if title:
				title.queue_free()
				title = null
			await start_game(false, true))
		ch.cancelled.connect(close_screen)
	else:
		ch.confirmed.connect(close_screen)
		ch.cancelled.connect(close_screen)
	open_screen(ch)


func open_pause() -> void:
	var p := Menus.pause({
		"Resume": close_screen,
		"Journal": open_journal,
		"Inventory": func() -> void: open_inventory(player.near_workbench()),
		"Settings": open_settings,
		"Save": func() -> void:
			save_game()
			hud.toast("Saved", "info"),
		"Load": func() -> void:
			close_screen()
			load_game(),
		"Quit to title": quit_to_title,
		"Quit game": quit_game,
	})
	open_screen(p)


func open_settings() -> void:
	open_screen(Menus.settings(close_screen))


func _on_scattered(dropped: float) -> void:
	var s := Menus.scattered(dropped, func() -> void:
		close_screen()
		player.respawn())
	get_tree().create_timer(Game.tuning.f("player.scatter_time_s", 2.5) * 0.5).timeout.connect(func() -> void:
		if player.scattered_now:
			open_screen(s))


func refresh_essence_markers() -> void:
	for n in _essence_nodes:
		if is_instance_valid(n):
			n.queue_free()
	_essence_nodes.clear()
	for d in Game.dropped_essence:
		var p: Array = d["pos"]
		var w := Fx.wisps(Color(0.7, 0.5, 1.0), 6.0, 1.5, 0.4)
		add_child(w)
		w.global_position = Vector3(p[0], p[1] + 0.3, p[2])
		_essence_nodes.append(w)


func sleep_until_dusk() -> void:
	var ph := Game.phase()
	if not ph in ["day", "dawn"]:
		hud.hint("You only sleep through the day")
		return
	var fade := ColorRect.new()
	fade.color = Color(0, 0, 0, 0)
	fade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ui_layer.add_child(fade)
	var s := Game.tuning.f("cycle.sleep_fade_s", 1.2)
	var tw := create_tween()
	tw.tween_property(fade, "color:a", 1.0, s * 0.5)
	tw.tween_callback(func() -> void:
		Game.cycle_t = Game.tuning.f("cycle.sleep_skip_to_t", 0.95)
		Game.hp = Game.max_hp()
		for n in npcs:
			n._snap_to_schedule()
		save_game()
		hud.toast("You slept through the day. Dusk again.", "info"))
	tw.tween_property(fade, "color:a", 0.0, s * 0.5)
	tw.tween_callback(fade.queue_free)


func save_game() -> bool:
	return Game.save_game(world.edits_for_save())


func load_game() -> void:
	if not Game.has_save():
		hud.hint("No save yet")
		return
	player.possession.release()
	var save := Game.load_game()
	world.apply_edits(save.get("world_edits", {}))
	world.remesh_now()
	for id: String in level.gather_nodes:
		level.set_node_alive(id, not Game.nodes_state.has(id))
	level.clear_charms_not_in(Game.town.charms)
	level.clear_salt_not_in(Game.town.salt_lines)
	director.restore_memory_visuals()
	player.teleport(Game.player_pos, Game.player_yaw)
	for n in npcs:
		n.mind = Game.minds[n.id]
		n._snap_to_schedule()
	refresh_essence_markers()
	hud.toast("Loaded", "info")


func quit_to_title() -> void:
	if started:
		save_game()
	get_tree().paused = false
	Engine.time_scale = 1.0
	get_tree().reload_current_scene()


func quit_game() -> void:
	if started:
		save_game()
	get_tree().quit()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		quit_game()
