## Battle prototype (Underveil battle-fun gate): the Sunken Ford cavern with the Drowned Parish against
## the Barrow Host, about 500 a side, and the player's ghost in the middle of it.
##
## Builds the arena from blender/scripts/build_battle_arena.py's JSON + voxels, the crowd tier (GPU
## compute when a RenderingDevice exists, else the CPU reference sim; `--crowd cpu|gpu` forces one),
## the near tier (the 32 nearest units as CPU actors), and the ghost's verbs against an army:
##   tool swings hit near actors (Form), BOO and thrown boulders reach the crowd as hit spheres,
##   E at the bell tower silences the Parish bells (their fear: silence).
## Scares are graded by how many units break in the next few seconds. It stands in for the World node
## the Player expects (`world`, `level`, `director`, `hud`, ...), so the ghost controller is unchanged.
class_name BattleWorld
extends Node3D

const L := preload("res://scripts/battle/crowd_layout.gd")
const LAYOUT := "res://assets/levels/sunken_ford_layout.json"
const POPULATION := "res://assets/levels/sunken_ford_population.json"

# ---- the Player's `gw` contract
var world: VoxelWorld
var level: Level
var director: Node
var gather: Variant = null
var caverns: Variant = null
var npcs: Array[Npc] = []
var hud: BattleHud
var player: Player

# ---- battle state
var layout: Dictionary
var pop: Dictionary
var bt: Dictionary                  # tuning.battle
var terrain: BattleTerrain
var params: CrowdParams
var sim                              # CrowdSimGpu or CrowdSimCpu
var gpu := false
var near: NearTier
var kits: Array[UnitKit] = []
var mm: Array[MultiMesh] = []
var clan_ids: Array[String] = []
var clan_names: Array[String] = []
var clan_colors: Array[Color] = []
var clan_blocks := PackedFloat32Array()
var started := false
var ended := false
var elapsed := 0.0
var read_target: NearActor
var ui_layer: CanvasLayer
var screen: Control
var time_scale := 1.0
var parish := 0                      # clan index of the Drowned Parish

var bells_left := 0.0               # seconds the bells stay silent
var bell_pos := Vector3.ZERO
var _ring_t := 0.0
var boulders: Array[Dictionary] = []
var held := -1
var scares: Array[Dictionary] = []
var best_grade := ""
var stats := {"boos": 0, "throws": 0, "silences": 0, "hits": 0, "scattered_by_ghost": 0, "routs_by_scares": 0}
var winner := -1
var _frame_ms: Array[float] = []
var _respawn_at := Vector3.ZERO
var _respawn_yaw := 180.0
var _loading: Control
var _spawn_info: Dictionary
var _scream_cd := 0.0
var _last_routs := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	director = self
	ui_layer = CanvasLayer.new()
	ui_layer.layer = 10
	add_child(ui_layer)
	_loading = UiKit.centered(UiKit.heading("Descending to the Sunken Ford…", 40))
	_loading.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ui_layer.add_child(_loading)
	await get_tree().process_frame
	await get_tree().process_frame
	build()
	if Game.has_flag("autotest"):
		var runner: Node = (load("res://scripts/battle/battle_autotest.gd") as GDScript).new()
		runner.set("bw", self)
		add_child(runner)
	elif Game.has_flag("battle-parity"):
		var parity: Node = (load("res://scripts/battle/battle_parity.gd") as GDScript).new()
		parity.set("bw", self)
		add_child(parity)
	elif Game.has_flag("battle-bench"):
		var bench: Node = (load("res://scripts/battle/battle_bench.gd") as GDScript).new()
		bench.set("bw", self)
		add_child(bench)
	else:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func build() -> void:
	var t0 := Time.get_ticks_msec()
	bt = Game.tuning.d("battle")
	layout = Game._json(LAYOUT)
	pop = Game._json(POPULATION)
	Game.hp = Game.max_hp()
	Game.ecto = Game.tuning.f("player.ecto_max", 100.0)
	Game.inventory.setup(Game.tuning.d("start"))
	Game.inventory.selected = 0
	Game.cycle_t = 0.3
	# the cavern
	world = VoxelWorld.new()
	world.name = "VoxelWorld"
	add_child(world)
	world.load_level(layout, Game.blocks, Game.tuning.f("world.vertex_jitter_m", 0.035))
	var wstats := world.build_all()
	world.set_mood_emission(1.0)
	_environment()
	_lights_and_props()
	# the crowd
	params = CrowdParams.from_tuning(bt.get("crowd", {}))
	var w: Dictionary = layout["world"]
	terrain = BattleTerrain.from_voxels(world.vox, world.size, Game.blocks, int(w["floor_y"]), int(w["ceiling_y"]))
	var walkers: Array[bool] = []
	var clans: Array = pop.get("clans", [])
	for ci in clans.size():
		var cd: Dictionary = clans[ci]
		terrain.mark_home(ci, cd["home"]["rect"])
		walkers.append(bool(cd.get("water_walker", false)))
		clan_ids.append(String(cd["id"]))
		clan_names.append(String(cd["name"]))
		clan_colors.append(Color(String(cd.get("tint", "#ffffff"))).lightened(0.25))
		if cd["id"] == "drowned_parish":
			parish = ci
	terrain.setup_clans(walkers, params.water_cost, String(bt.get("attack_goal", "ford")))
	var scale := float(bt.get("cpu_fallback_scale", 1.0))
	if Game.cmd.has("units") and not Game.cmd["units"].is_empty():
		scale = float(Game.cmd["units"][0]) / 1000.0
	var want_gpu := CrowdSimGpu.available() and not Game.has_flag("autotest") and not Game.has_flag("battle-parity")
	if Game.cmd.has("crowd") and not Game.cmd["crowd"].is_empty():
		want_gpu = String(Game.cmd["crowd"][0]) == "gpu" and CrowdSimGpu.available()
	_spawn_info = CrowdSpawner.spawn(pop, terrain, params, 20261119, scale)
	clan_blocks = _clan_blocks()
	var arena := AABB(Vector3(0, 0, 0), Vector3(terrain.w, 32, terrain.h))
	var actor_mats: Array[ShaderMaterial] = []
	for ci in clans.size():
		var cd: Dictionary = clans[ci]
		var kit := UnitKit.load_unit(String(cd["unit"]))
		kits.append(kit)
		var m := MultiMesh.new()
		m.transform_format = MultiMesh.TRANSFORM_3D
		m.use_custom_data = true
		m.mesh = kit.mesh
		m.instance_count = int(_spawn_info["sizes"][ci])
		m.custom_aabb = arena
		mm.append(m)
		var mi := MultiMeshInstance3D.new()
		mi.name = "Crowd_%s" % cd["id"]
		mi.multimesh = m
		mi.material_override = kit.material(true, Color.WHITE)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.custom_aabb = arena
		add_child(mi)
		actor_mats.append(kit.material(false, Color.WHITE))
	if want_gpu:
		var rids: Array[RID] = []
		for m in mm:
			rids.append(m.get_rid())
		sim = CrowdSimGpu.new()
		sim.readback_every = int(bt.get("near", {}).get("readback_every_frames", 4))
		sim.setup(terrain, params, _spawn_info["starts"], _spawn_info["sizes"], _spawn_info["units"], clan_blocks, rids)
		gpu = true
	else:
		sim = CrowdSimCpu.new()
		sim.setup(terrain, params, _spawn_info["starts"], _spawn_info["sizes"], _spawn_info["units"], clan_blocks)
		_upload_cpu_multimesh()
	near = NearTier.new()
	near.name = "NearTier"
	add_child(near)
	near.setup(sim, params, terrain, kits, actor_mats, clan_blocks, bt.get("near", {}))
	near.unit_scattered.connect(_on_actor_scattered)
	# the ghost
	level = Level.new()
	player = Player.new()
	add_child(player)
	player.setup(self)
	var sp: Dictionary = layout.get("spawn", {})
	var ps: Array = sp.get("player_start", [64, 7.2, 52])
	_respawn_at = Vector3(ps[0], float(ps[1]) + 1.0, ps[2])
	_respawn_yaw = float(sp.get("yaw", 180.0))
	player.teleport(_respawn_at, _respawn_yaw)
	player.scattered.connect(_on_player_scattered)
	for n: Node in [world, near, player]:
		n.process_mode = Node.PROCESS_MODE_PAUSABLE
	hud = BattleHud.new()
	ui_layer.add_child(hud)
	hud.setup(self)
	_loading.queue_free()
	started = true
	Sfx.music("")
	print("BATTLE built in %d ms: %d units (%s), %s, voxel chunks %d" % [Time.get_ticks_msec() - t0, sim.n,
		" + ".join(Array(_spawn_info["sizes"]).map(func(x: int) -> String: return str(x))), "GPU crowd" if gpu else "CPU crowd", wstats.get("chunks", 0)])
	hud.toast("The Drowned Parish and the Barrow Host march on the Sunken Ford.", "info")
	hud.toast("The Parish fear silence. Their bell tower stands behind their lines.", "fear")


func _clan_blocks() -> PackedFloat32Array:
	var cp := PackedFloat32Array()
	var bells: Dictionary = bt.get("bells", {})
	for ci in clan_ids.size():
		var ct: Dictionary = bt.get("clans", {}).get(clan_ids[ci], {})
		var regen := float(ct.get("regen_bonus", 0.0))
		var fear := float(ct.get("fear_mult", 1.0))
		var spread := float(ct.get("contagion_mult", 1.0))
		if ci == parish:
			if bells_left > 0.0:
				fear = float(bells.get("silenced_fear_mult", 1.8))
				spread = float(bells.get("silenced_contagion_mult", 1.8))
			else:
				regen += float(bells.get("ringing_regen_bonus", 0.5))
				fear = float(bells.get("ringing_fear_mult", 0.85))
				spread = float(bells.get("ringing_contagion_mult", 0.6))
		cp.append_array(CrowdParams.clan_block(float(ct.get("speed_mult", 1.0)), regen, fear, float(ct.get("dmg_mult", 1.0)),
			bool(pop["clans"][ci].get("water_walker", false)), spread))
	return cp


func _apply_clan_blocks() -> void:
	clan_blocks = _clan_blocks()
	for ci in clan_ids.size():
		var b := clan_blocks.slice(ci * 8, ci * 8 + 8)
		sim.set_clan(ci, b)
		near.set_clan(ci, b)


func _upload_cpu_multimesh() -> void:
	for ci in mm.size():
		RenderingServer.multimesh_set_buffer(mm[ci].get_rid(), sim.clan_mm(ci))


# ---------------------------------------------------------------- arena dressing

func _environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.02, 0.02, 0.05)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.36, 0.36, 0.52)
	env.ambient_light_energy = 0.4
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.0
	env.glow_enabled = true
	env.glow_intensity = 0.7
	env.glow_bloom = 0.06
	env.fog_enabled = true
	env.fog_light_color = Color(0.10, 0.09, 0.18)
	env.fog_density = 0.006
	env.fog_sky_affect = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	# soft cool bounce from the vein-lit ceiling so the armies read at a distance
	var d := DirectionalLight3D.new()
	d.light_color = Color(0.86, 0.84, 1.0)
	d.light_energy = 0.45
	d.rotation_degrees = Vector3(-55, 35, 0)
	d.shadow_enabled = false
	add_child(d)


func _lights_and_props() -> void:
	var lantern := load("res://assets/props/lantern_post.gltf") as PackedScene
	var bell_scene := load("res://assets/props/bell.gltf") as PackedScene
	for m: Dictionary in layout.get("markers", []):
		var p: Array = m["pos"]
		var pos := Vector3(p[0], p[1], p[2])
		match String(m["kind"]):
			"light":
				var o := OmniLight3D.new()
				o.light_color = Color(String(m.get("color", "#ffffff")))
				o.light_energy = float(m.get("energy", 1.0))
				o.omni_range = float(m.get("range", 8.0))
				o.shadow_enabled = false
				add_child(o)
				o.position = pos
				if m.get("style") == "bronze_lantern" and lantern:
					var l := lantern.instantiate() as Node3D
					add_child(l)
					l.position = Vector3(pos.x, float(layout["world"]["floor_y"]), pos.z)
				elif m.get("style") == "votive":
					var f := Fx.flame(o.light_color, 0.06, 6)
					add_child(f)
					f.position = pos
			"bell":
				bell_pos = pos
				if bell_scene:
					var b := bell_scene.instantiate() as Node3D
					add_child(b)
					b.position = pos
					b.scale = Vector3.ONE * 1.6
				var lab := Label3D.new()
				lab.text = "The Parish bells\nE · silence them"
				lab.billboard = BaseMaterial3D.BILLBOARD_ENABLED
				lab.modulate = Color(1.0, 0.75, 0.45)
				lab.pixel_size = 0.01
				lab.no_depth_test = false
				add_child(lab)
				lab.position = pos + Vector3(0, 3.6, 0)
			"throwable":
				_add_boulder(pos, float(m.get("radius", 0.45)))


func _add_boulder(home: Vector3, radius: float) -> void:
	var node := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = radius
	sm.height = radius * 1.7
	sm.radial_segments = 7
	sm.rings = 4
	node.mesh = sm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.42, 0.42, 0.5)
	mat.roughness = 0.95
	mat.emission_enabled = true
	mat.emission = Color(0.55, 0.45, 1.0)
	mat.emission_energy_multiplier = 0.0
	node.material_override = mat
	add_child(node)
	var rest := home + Vector3(0, radius * 0.75, 0)
	node.position = rest
	node.rotation = Vector3(randf() * 3.0, randf() * 3.0, 0)
	boulders.append({"node": node, "home": rest, "state": "idle", "vel": Vector3.ZERO, "t": 0.0, "mat": mat, "radius": radius})


# ---------------------------------------------------------------- loop

func _process(dt: float) -> void:
	if not started or get_tree().paused:
		return
	var t_us := Time.get_ticks_usec()
	dt = minf(dt, 1.0 / 20.0)
	elapsed += dt
	_tick_bells(dt)
	_tick_boulders(dt)
	var g := player.global_position
	sim.ghost = g
	near.tick(dt, g)
	sim.step(dt)
	if not gpu:
		_upload_cpu_multimesh()
	_tick_actor_swings(dt)
	_update_read_target()
	_tick_grades()
	_check_end()
	_frame_ms.append((Time.get_ticks_usec() - t_us) / 1000.0)
	if _frame_ms.size() > 120:
		_frame_ms.pop_front()


func _unhandled_input(e: InputEvent) -> void:
	if not started:
		return
	if e.is_action_pressed("pause"):
		if screen:
			close_screen()
		elif not ended:
			open_pause()
		get_viewport().set_input_as_handled()
		return
	if screen or get_tree().paused or player.scattered_now:
		return
	if e.is_action_pressed("haunt"):
		haunt_action()
		get_viewport().set_input_as_handled()
	elif e is InputEventMouseButton and e.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and not ended:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


# ---------------------------------------------------------------- the ghost's verbs

## Called by Player.try_mine: in battle a swing hits undead, never blocks.
func tool_swing(p: Player, tool: String, tier: int) -> String:
	var g: Dictionary = bt.get("ghost", {})
	var dmg := float(g.get("tool_dmg", {}).get(tool, 24.0)) * (1.0 + float(g.get("tool_tier_bonus", 0.25)) * (tier - 1))
	var res := dmg * float(g.get("tool_resolve_k", 0.35))
	var reach := float(g.get("tool_reach_m", 2.4))
	var ray := p.aim_ray()
	var dir: Vector3 = ray[1]
	var flat := Vector2(dir.x, dir.z).normalized()
	var origin := p.global_position + Vector3(0, 0.4, 0)
	var hits: Array[NearActor] = []
	var best: NearActor = null
	var best_a := deg_to_rad(float(g.get("tool_cone_deg", 40.0)))
	var sweep := deg_to_rad(float(g.get("scythe_sweep_deg", 110.0))) * 0.5
	for a in near.actors:
		if not a.alive():
			continue
		var to := a.global_position + Vector3(0, 0.9, 0) - origin
		var horiz := Vector2(to.x, to.z)
		if horiz.length() > reach + 0.35 or absf(to.y) > 2.2:
			continue
		var ang := absf(flat.angle_to(horiz.normalized())) if horiz.length() > 0.05 else 0.0
		if tool == "scythe":
			if ang <= sweep:
				hits.append(a)
		elif ang < best_a:
			best_a = ang
			best = a
	if best:
		hits.append(best)
	if hits.is_empty():
		Sfx.play_at("whoosh", origin, -6.0)
		return "miss"
	for a in hits:
		near.hit_actor(a, dmg, res)
		a.set_meta("ghost_hit_t", elapsed)
		Fx.burst(self, a.global_position + Vector3(0, 1.0, 0), Color(0.8, 0.95, 1.0), 10, 2.0, 0.35, 0.08)
		stats["hits"] += 1
	Sfx.play_at("mine_stone" if tool == "sledgehammer" else "mine_wood", origin, 0.0)
	if tool == "sledgehammer":
		player.punch_in(0.15)
	return "hit"


## Director contract: the ghost's BOO.
func boo(p: Player) -> Dictionary:
	var g: Dictionary = bt.get("ghost", {})
	var center := p.global_position
	var r := float(g.get("boo_radius_m", 5.0))
	add_hit(center, r, float(g.get("boo_form", 30.0)), float(g.get("boo_resolve", 95.0)), 15, -1,
		float(g.get("boo_falloff", 0.6)), L.SPH_SCARE | L.SPH_GHOST)
	for a in near.actors:
		if a.global_position.distance_to(center) < r:
			a.aggro = float(g.get("aggro_s", 6.0))
	stats["boos"] += 1
	_start_scare("BOO")
	Fx.burst(self, center + Vector3(0, 0.4, 0), Color(0.75, 0.92, 1.0), 40, 6.0, 0.8, 0.12)
	p.punch_in(0.5)
	_hitstop(0.16, 0.35)
	return {}


## Director contract (Millbrook hauntables); nothing to haunt that way here.
func haunt(_h: Variant, _a: Variant) -> void:
	pass


## E: silence the bells when aiming at the tower in range; otherwise lift or throw a boulder.
func haunt_action() -> String:
	var ray := player.aim_ray()
	var from: Vector3 = ray[0]
	var dir: Vector3 = ray[1]
	if held >= 0:
		return _throw_held(dir)
	var bells: Dictionary = bt.get("bells", {})
	if bell_pos != Vector3.ZERO and player.global_position.distance_to(bell_pos) < float(bells.get("haunt_range_m", 9.0)) \
			and dir.angle_to(bell_pos - from) < deg_to_rad(22.0):
		return silence_bells()
	var g: Dictionary = bt.get("ghost", {})
	var best := -1
	var best_a := deg_to_rad(14.0)
	for i in boulders.size():
		var b: Dictionary = boulders[i]
		if b["state"] != "idle":
			continue
		var pos: Vector3 = (b["node"] as Node3D).global_position
		if pos.distance_to(player.global_position) > float(g.get("throw_range_m", 8.0)):
			continue
		var a := dir.angle_to(pos - from)
		if a < best_a:
			best_a = a
			best = i
	if best < 0:
		hud.hint("Aim at a boulder (or the bell tower) and press E")
		return "nothing"
	var cost := float(g.get("throw_ecto", 15.0))
	if Game.ecto < cost:
		hud.hint("Not enough Ectoplasm to lift it")
		return "no ecto"
	Game.ecto -= cost
	held = best
	boulders[best]["state"] = "held"
	(boulders[best]["mat"] as StandardMaterial3D).emission_energy_multiplier = 1.2
	Sfx.play_at("whoosh", player.global_position, -4.0)
	hud.hint("E · throw it where you aim")
	return "lifted"


func _throw_held(dir: Vector3) -> String:
	var g: Dictionary = bt.get("ghost", {})
	var b: Dictionary = boulders[held]
	b["state"] = "flying"
	b["vel"] = dir * float(g.get("throw_speed_mps", 16.0)) + Vector3(0, 2.5, 0)
	b["t"] = 0.0
	held = -1
	stats["throws"] += 1
	player.face_aim()
	Sfx.play_at("whoosh", player.global_position, 0.0)
	return "thrown"


func silence_bells() -> String:
	var bells: Dictionary = bt.get("bells", {})
	if bells_left > 0.0:
		hud.hint("The bells are already silent (%d s)" % ceili(bells_left))
		return "already"
	bells_left = float(bells.get("silence_s", 45.0))
	_apply_clan_blocks()
	add_hit(Vector3(64, 7, 64), 10000.0, 0.0, float(bells.get("silence_shock", 12.0)), 1 << parish, -1, 0.0, L.SPH_GHOST)
	stats["silences"] += 1
	_start_scare("Silence")
	Sfx.play_at("door_slam", bell_pos, 4.0, 120.0)
	hud.toast("The bells fall silent. The Drowned Parish falters: their fear is in play.", "fear")
	Fx.burst(self, bell_pos, Color(1.0, 0.7, 0.4), 30, 3.0, 1.2, 0.1)
	return "silenced"


## A hit sphere for both tiers this frame.
func add_hit(center: Vector3, radius: float, form_dmg: float, resolve_dmg: float, mask: int, target: int,
		falloff: float, flags: int) -> void:
	sim.add_sphere(center, radius, form_dmg, resolve_dmg, mask, target, falloff, flags)
	near.add_sphere(center, radius, form_dmg, resolve_dmg, mask, target, falloff, flags)


func _hitstop(seconds: float, scale: float) -> void:
	if Game.has_flag("autotest") or Game.has_flag("battle-bench"):
		return
	Engine.time_scale = scale
	get_tree().create_timer(seconds, true, false, true).timeout.connect(func() -> void: Engine.time_scale = 1.0)


# ---------------------------------------------------------------- bells, boulders, actors

func _tick_bells(dt: float) -> void:
	var bells: Dictionary = bt.get("bells", {})
	if bells_left > 0.0:
		bells_left -= dt
		if bells_left <= 0.0:
			bells_left = 0.0
			_apply_clan_blocks()
			hud.toast("A bell-ringer has climbed the tower. The Parish bells ring again.", "bad")
		return
	_ring_t -= dt
	if _ring_t <= 0.0:
		_ring_t = float(bells.get("ring_every_s", 3.0))
		Sfx.play_at("bell_ring", bell_pos, -4.0, 140.0)


func bells_text() -> String:
	if bells_left > 0.0:
		return "Parish bells SILENCED · %d s · their fear is in play" % ceili(bells_left)
	return "Parish bells ringing · the Parish are steadied"


func telekinesis_text() -> String:
	if held >= 0:
		return "Holding a boulder · E to throw"
	return "E · lift a boulder (%d Ecto)" % int(bt.get("ghost", {}).get("throw_ecto", 15.0))


func _tick_boulders(dt: float) -> void:
	var g: Dictionary = bt.get("ghost", {})
	for i in boulders.size():
		var b: Dictionary = boulders[i]
		var node: Node3D = b["node"]
		match String(b["state"]):
			"held":
				var side := player.global_transform.basis.x * 0.7
				var want := player.global_position + Vector3(0, 1.3, 0) + side
				node.global_position = node.global_position.lerp(want, minf(1.0, dt * 10.0))
				node.rotate_y(dt * 2.0)
			"flying":
				b["t"] = float(b["t"]) + dt
				var v: Vector3 = b["vel"]
				v.y -= 9.8 * dt
				b["vel"] = v
				var np := node.global_position + v * dt
				node.rotate_x(dt * 6.0)
				var ground := terrain.heights[terrain.cell(np.x, np.z)] if terrain.in_grid(np.x, np.z) else 0.0
				var blocked := world.get_block_v(world.cell_of(np)) != 0 and Game.blocks.solid[world.get_block_v(world.cell_of(np))] == 1
				var hit_unit := false
				for a in near.actors:
					if a.alive() and a.global_position.distance_to(np - Vector3(0, 0.9, 0)) < 0.9:
						hit_unit = true
						break
				if np.y <= ground + float(b["radius"]) or blocked or hit_unit or float(b["t"]) > 4.0:
					node.global_position = np
					_boulder_impact(b)
				else:
					node.global_position = np
			"spent":
				b["t"] = float(b["t"]) - dt
				if float(b["t"]) <= 0.0:
					b["state"] = "idle"
					node.global_position = b["home"]
					node.visible = true
					(b["mat"] as StandardMaterial3D).emission_energy_multiplier = 0.0


func _boulder_impact(b: Dictionary) -> void:
	var g: Dictionary = bt.get("ghost", {})
	var node: Node3D = b["node"]
	var at := node.global_position
	add_hit(at, float(g.get("throw_radius_m", 2.4)), float(g.get("throw_form", 70.0)), float(g.get("throw_resolve", 22.0)),
		15, -1, 0.5, L.SPH_SCARE | L.SPH_GHOST)
	for a in near.actors:
		if a.global_position.distance_to(at) < float(g.get("throw_radius_m", 2.4)):
			a.set_meta("ghost_hit_t", elapsed)
	_start_scare("Boulder")
	Fx.burst(self, at, Color(0.7, 0.62, 0.55), 26, 4.0, 0.7, 0.14)
	Fx.burst(self, at, Color(0.7, 0.55, 1.0), 14, 3.0, 0.6, 0.08)
	Sfx.play_at("block_break", at, 4.0, 60.0)
	node.visible = false
	b["state"] = "spent"
	b["t"] = float(g.get("throw_respawn_s", 20.0))


## Units the ghost has angered swing at it when it drifts into reach.
func _tick_actor_swings(_dt: float) -> void:
	if player.scattered_now:
		return
	var g: Dictionary = bt.get("ghost", {})
	var gp := player.global_position
	for a in near.actors:
		if a.state() != L.FIGHT or a.aggro <= 0.0 or a.swing_cd > 0.0:
			continue
		var d := Vector2(a.global_position.x - gp.x, a.global_position.z - gp.z).length()
		if d < 1.6 and absf(a.global_position.y + 1.0 - gp.y) < 2.2:
			a.swing_cd = 1.6
			a.rec[L.CLIP] = float(L.CLIP_ATTACK)
			a.rec[L.ANIM_T] = 0.0
			Game.hp = maxf(0.0, Game.hp - float(g.get("hurt_by_unit", 0.6)))
			player.sheet_mat.set_shader_parameter("hurt", 1.0)
			create_tween().tween_method(func(v: float) -> void: player.sheet_mat.set_shader_parameter("hurt", v), 1.0, 0.0, 0.4)
			Sfx.play("hurt", -4.0)
			hud.hint("A %s soldier strikes you!" % clan_names[a.clan()])


func _on_actor_scattered(a: NearActor) -> void:
	Fx.burst(self, a.global_position + Vector3(0, 1.0, 0), Color(0.7, 0.9, 1.0), 22, 2.5, 1.2, 0.1)
	Sfx.play_at("scatter", a.global_position, -6.0)
	if a.has_meta("ghost_hit_t") and elapsed - float(a.get_meta("ghost_hit_t")) < 1.5:
		stats["scattered_by_ghost"] += 1
		var mat := "drowned silver" if a.clan() == parish else "barrow bronze"
		hud.hint("Scattered! +1 %s" % mat)


func _update_read_target() -> void:
	var ray := player.aim_ray()
	var from: Vector3 = ray[0]
	var dir: Vector3 = ray[1]
	var best: NearActor = null
	var best_a := deg_to_rad(9.0)
	for a in near.actors:
		if not a.alive() or a.global_position.distance_to(player.global_position) > 14.0:
			continue
		var ang := dir.angle_to(a.head_pos() - Vector3(0, 0.5, 0) - from)
		if ang < best_a:
			best_a = ang
			best = a
	read_target = best


func respawn_point() -> Array:
	return [_respawn_at, _respawn_yaw]


func _on_player_scattered(_dropped: float) -> void:
	hud.toast("You were scattered! Re-forming on the Parish bank…", "bad")
	get_tree().create_timer(3.0).timeout.connect(func() -> void:
		Game.hp = Game.max_hp()
		player.respawn())


# Player contract stubs (Millbrook-only screens)
func refresh_essence_markers() -> void:
	pass


func open_characterizer(_new: bool) -> void:
	pass


func open_inventory(_bench: bool) -> void:
	pass


func sleep_until_dusk() -> void:
	pass


# ---------------------------------------------------------------- grading and the end

func total_routs() -> int:
	var t := 0
	for c in clan_ids.size():
		t += sim.summary[L.SUM_ROUTS + c] + near.routs[c]
	return t


func _start_scare(kind: String) -> void:
	# a new scare closes the window of the one before it (the cascade goes to the latest scare)
	for s in scares:
		if not s["done"]:
			_grade_scare(s)
	scares.append({"kind": kind, "t": elapsed, "routs0": total_routs(), "done": false, "routs": 0})


func _tick_grades() -> void:
	var window := float(bt.get("grade", {}).get("window_s", 10.0))
	_scream_cd -= get_process_delta_time()
	var tr := total_routs()
	if tr > _last_routs and _scream_cd <= 0.0:
		# the sound of a line breaking: a scream from the panic, quicker the faster they break
		var burst := tr - _last_routs
		_scream_cd = 0.45 if burst < 3 else 0.2
		var at := player.global_position + Vector3(randf_range(-6, 6), 0, randf_range(-6, 6))
		Sfx.play_at("scream" if burst >= 2 else "gasp", at, -8.0 + minf(6.0, burst * 1.5), 60.0, 0.25)
	_last_routs = tr
	for s in scares:
		if s["done"]:
			continue
		s["routs"] = total_routs() - int(s["routs0"])
		if elapsed - float(s["t"]) >= window:
			_grade_scare(s)
		elif int(s["routs"]) >= 5:
			hud.show_grade("%s · %d broke and ran" % [s["kind"], s["routs"]])


func grade_for(routs: int) -> String:
	var g: Dictionary = bt.get("grade", {})
	if routs >= int(g.get("legendary", 100)):
		return "Legendary"
	if routs >= int(g.get("terrified", 40)):
		return "Terrified"
	if routs >= int(g.get("spooked", 10)):
		return "Spooked"
	return ""


func _grade_scare(s: Dictionary) -> void:
	s["done"] = true
	s["routs"] = total_routs() - int(s["routs0"])
	var grade := grade_for(int(s["routs"]))
	s["grade"] = grade
	stats["routs_by_scares"] += int(s["routs"])
	if grade == "":
		return
	var order := ["", "Spooked", "Terrified", "Legendary"]
	if order.find(grade) > order.find(best_grade):
		best_grade = grade
	hud.show_grade("%s! %s broke %d" % [grade, s["kind"], s["routs"]])
	hud.toast("%s: %s · %d routed" % [s["kind"], grade, s["routs"]], "grade")
	Sfx.play("grade_stamp")


func clan_totals() -> Array:
	var out := []
	var s: PackedInt32Array = sim.summary
	for c in clan_ids.size():
		var start := int(_spawn_info["sizes"][c])
		var fighting := s[L.SUM_STATE + L.FIGHT * L.MAX_CLANS + c]
		var routing := s[L.SUM_STATE + L.ROUT * L.MAX_CLANS + c]
		var scattered := s[L.SUM_SCATTERS + c] + near.scatters[c]
		var fled := maxi(0, start - fighting - routing - scattered)
		var nw := s[L.SUM_FLANK + c * 2]
		var ne := s[L.SUM_FLANK + c * 2 + 1]
		var d := {"start": start, "fighting": fighting, "routing": routing, "scattered": scattered, "fled": fled,
			"n_w": nw, "n_e": ne,
			"res_w": s[L.SUM_FLANK_RES + c * 2] / 16.0 / maxf(1.0, nw),
			"res_e": s[L.SUM_FLANK_RES + c * 2 + 1] / 16.0 / maxf(1.0, ne)}
		if c == parish:
			d["extra"] = "Fears silence · " + ("bells SILENT" if bells_left > 0.0 else "bells ringing")
		else:
			d["extra"] = "Can't cross running water · holds the fords"
		out.append(d)
	return out


func _check_end() -> void:
	if ended or elapsed < 5.0 or sim.summary.is_empty():
		return
	var tot := clan_totals()
	var ratio := float(bt.get("grade", {}).get("win_ratio", 0.75))
	for c in tot.size():
		var t: Dictionary = tot[c]
		if float(t["fighting"]) < float(t["start"]) * (1.0 - ratio):
			winner = 1 - c
			_end_battle(c)
			return


func _end_battle(loser: int) -> void:
	ended = true
	var lines: Array[String] = []
	lines.append("The %s hold the Sunken Ford. The %s break and fade back into the dark." % [clan_names[winner], clan_names[loser]])
	lines.append("Battle time %d:%02d" % [int(elapsed) / 60, int(elapsed) % 60])
	lines.append("Your best scare: %s" % (best_grade if best_grade != "" else "none graded"))
	lines.append("BOOs %d · boulders %d · bells silenced %d · undead you scattered %d · routs after your scares %d" % [
		stats["boos"], stats["throws"], stats["silences"], stats["scattered_by_ghost"], stats["routs_by_scares"]])
	print("BATTLE END winner=%s t=%.1f best=%s stats=%s" % [clan_ids[winner], elapsed, best_grade, JSON.stringify(stats)])
	if Game.has_flag("autotest") or Game.has_flag("battle-bench"):
		return
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.show_end("The battle is over", lines, restart, quit_to_title)


# ---------------------------------------------------------------- menus

func open_screen(c: Control) -> void:
	close_screen()
	screen = c
	ui_layer.add_child(c)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().paused = true
	Sfx.ui("ui_open")


func close_screen() -> void:
	if screen and is_instance_valid(screen):
		screen.queue_free()
		Sfx.ui("ui_close")
	screen = null
	get_tree().paused = false
	if not ended and not Game.has_flag("autotest") and not Game.has_flag("battle-bench"):
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func open_pause() -> void:
	open_screen(Menus.pause({
		"Resume": close_screen,
		"Restart the battle": restart,
		"Settings": func() -> void: open_screen(Menus.settings(close_screen)),
		"Quit to title": quit_to_title,
		"Quit game": func() -> void: get_tree().quit(),
	}))


func restart() -> void:
	get_tree().paused = false
	Engine.time_scale = 1.0
	_free_gpu()
	get_tree().reload_current_scene()


func quit_to_title() -> void:
	get_tree().paused = false
	Engine.time_scale = 1.0
	Game.cmd.erase("battle")
	_free_gpu()
	get_tree().change_scene_to_file("res://scenes/main.tscn")


## Stops the battle, lets in-flight GPU readbacks land, frees the GPU buffers, then quits. The self-test
## modes quit through here: quitting mid-step with readbacks pending crashed on exit now and then (issues.md).
func shutdown_and_quit(code: int) -> void:
	started = false
	for k in 6:
		await get_tree().process_frame
	_free_gpu()
	for k in 6:
		await get_tree().process_frame
	get_tree().quit(code)


func _free_gpu() -> void:
	if gpu and sim:
		sim.free_gpu()


func _exit_tree() -> void:
	# GPU buffers are freed by restart() / quit_to_title(); at app exit the device is torn down whole
	if level:
		level.free()
		level = null


func perf_text() -> String:
	var avg := 0.0
	for f in _frame_ms:
		avg += f
	avg /= maxf(1.0, _frame_ms.size())
	return "%d fps · %s crowd %d units · %d near actors · battle logic %.2f ms" % [
		Engine.get_frames_per_second(), "GPU" if gpu else "CPU", sim.n, near.actors.size(), avg]
