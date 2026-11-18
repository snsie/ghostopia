## The Basic Ghost: drifting (hovers ~1 block up, glides down, ascending costs Ectoplasm), phasing
## through soft blocks and props (collides only with non-phaseable voxels, stone props and spirit
## barriers: running water, salt lines), the third-person chase camera, the three spectral tools,
## block placing, haunting, BOO, daylight drain, scattering and respawn.
class_name Player
extends CharacterBody3D

signal scattered(dropped: float)
signal respawned
signal mined(block_id: String, drops: Dictionary)

var gw: Node          # the World node (world, level, director, hud)
var world: VoxelWorld
var level: Level
var model: Node3D
var ap: AnimationPlayer
var eyes: MeshInstance3D
var sheet_mat: ShaderMaterial
var xray_mat: ShaderMaterial
var tool_socket: Node3D
var tool_node: Node3D
var tool_id := ""

var cam_yaw: Node3D
var cam_pitch: Node3D
var spring: SpringArm3D
var camera: Camera3D
var _yaw := 0.0
var _pitch := -0.25
var _dist := 3.4
var _punch := 0.0

var auto_move := Vector2.ZERO      # autotest/tour input override (x = right, y = forward)
var auto_vertical := 0.0           # +1 ascend, -1 sink
var input_enabled := true:
	set(value):
		input_enabled = value
		if not value:
			_clear_sprint_taps()
var _direction_taps: Dictionary = {}
var possession: Node
var _sprint_key: Key = KEY_NONE
var phasing := false
var manifest_left := 0.0
var scattered_now := false
var target_hauntable: Hauntable
var target_npc: Npc
var target_block := {}             # voxel raycast result within reach
var target_node := {}              # weed/grass node
var _swing_left := 0.0
var _mine_cell := Vector3i(-999, 0, 0)
var _mine_hits := 0
var _crack: MeshInstance3D
var _crack_mats: Array[StandardMaterial3D] = []
var _hurt_t := 0.0
var _clip := ""
var _clip_lock := 0.0
var _rooms: Array[AABB] = []
var _shelters: Array[Dictionary] = []
var indoors := false
var sheltered := false
var _boo_cd := 0.0


func setup(p_gw: Node) -> void:
	gw = p_gw
	world = gw.world
	level = gw.level
	name = "Player"
	motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	collision_layer = 0
	collision_mask = VoxelWorld.L_SOLID | VoxelWorld.L_PROP_SOLID | VoxelWorld.L_BARRIER
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = Game.tuning.f("player.radius_m", 0.28)
	cap.height = Game.tuning.f("player.height_m", 0.62)
	cs.shape = cap
	cs.position.y = cap.height * 0.5
	add_child(cs)
	model = (load("res://assets/characters/ghost.gltf") as PackedScene).instantiate()
	add_child(model)
	ap = Actors.find_prefix(model, "AnimationPlayer") as AnimationPlayer
	Actors.setup_loops(ap, Game.characters.get("ghost", {}))
	ap.playback_default_blend_time = 0.15
	eyes = Actors.find_prefix(model, "ghost_eyes") as MeshInstance3D
	tool_socket = Actors.find_prefix(model, "HELD_tool") as Node3D
	var manifest_node := Actors.find_prefix(model, "MATERIAL_manifest") as Node3D
	if manifest_node:
		manifest_node.visible = false
	var body := Actors.find_prefix(model, "ghost_body") as MeshInstance3D
	sheet_mat = ShaderMaterial.new()
	sheet_mat.shader = load("res://shaders/ghost.gdshader")
	xray_mat = ShaderMaterial.new()
	xray_mat.shader = load("res://shaders/ghost_xray.gdshader")
	sheet_mat.next_pass = xray_mat
	if body and body.mesh:
		for s in body.mesh.get_surface_count():
			body.set_surface_override_material(s, sheet_mat)
	# The ghost's own glow lights the world around it but not its own sheet (visual layer 2).
	var meshes: Array = []
	Actors.find_all_prefix(model, "", meshes)
	for m in meshes:
		if m is VisualInstance3D:
			(m as VisualInstance3D).layers = 2
	var glow := OmniLight3D.new()
	glow.light_cull_mask = 1
	glow.light_color = Color(0.62, 0.86, 1.0)
	glow.light_energy = 0.6
	glow.omni_range = 3.5
	glow.position.y = 0.4
	glow.shadow_enabled = false
	add_child(glow)
	_build_camera()
	_crack = MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3.ONE * 1.004
	_crack.mesh = bm
	_crack.visible = false
	_crack.top_level = true
	add_child(_crack)
	for i in 5:
		_crack_mats.append(Fx.crack_material(float(i + 1) / 5.0))
	for st in Game.layout.get("structures", []):
		for r in st.get("rooms", []):
			var mn := Vector3(r["min"][0], r["min"][1], r["min"][2])
			var mx := Vector3(r["max"][0], r["max"][1], r["max"][2])
			_rooms.append(AABB(mn, mx - mn))
	for m in Game.layout.get("markers", []):
		if m["kind"] == "shelter":
			_shelters.append(m)
	Game.inventory.changed.connect(_refresh_tool)
	Game.stats_changed.connect(_refresh_evolution)
	_refresh_evolution()
	possession = (load("res://scripts/actors/possession.gd") as GDScript).new()
	add_child(possession)
	possession.setup(self)
	_refresh_tool()


func _build_camera() -> void:
	cam_yaw = Node3D.new()
	cam_yaw.top_level = true
	add_child(cam_yaw)
	cam_pitch = Node3D.new()
	cam_yaw.add_child(cam_pitch)
	spring = SpringArm3D.new()
	spring.collision_mask = VoxelWorld.L_SOLID | VoxelWorld.L_PHASE
	spring.margin = 0.2
	var sph := SphereShape3D.new()
	sph.radius = 0.2
	spring.shape = sph
	cam_pitch.add_child(spring)
	camera = Camera3D.new()
	camera.fov = Game.tuning.f("camera.fov", 70.0)
	camera.near = 0.05
	camera.far = 400.0
	spring.add_child(camera)
	_dist = Game.tuning.f("camera.distance_m", 3.4)
	spring.spring_length = _dist


func teleport(p: Vector3, yaw_deg: float) -> void:
	global_position = p
	velocity = Vector3.ZERO
	_yaw = deg_to_rad(yaw_deg) + PI
	rotation.y = deg_to_rad(yaw_deg)
	_update_camera(0.0, true)


## Points the camera (and so the crosshair ray) at a world point; used by the autotest and tour.
func aim_at(p: Vector3) -> void:
	var pivot := global_position + Vector3(0, Game.tuning.f("camera.height_m", 0.9), 0)
	var d := (p - pivot).normalized()
	_yaw = atan2(-d.x, -d.z)
	_pitch = asin(clampf(d.y, -1.0, 1.0))
	_update_camera(0.0, true)


func look_yaw() -> float:
	return _yaw


func set_look(yaw: float, pitch: float) -> void:
	_yaw = yaw
	_pitch = pitch


func _refresh_evolution() -> void:
	var haunting := Game.trait_rank("haunting")
	var drift := Game.trait_rank("drift")
	var resilience := Game.trait_rank("resilience")
	if eyes:
		if haunting > 0:
			var material := StandardMaterial3D.new()
			material.albedo_color = Color(0.68, 0.28, 1.0)
			material.emission_enabled = true
			material.emission = material.albedo_color
			material.emission_energy_multiplier = 0.5 + 0.4 * haunting
			eyes.material_override = material
		else:
			eyes.material_override = null
	sheet_mat.set_shader_parameter("drift_rank", float(drift))
	sheet_mat.set_shader_parameter("resilience_rank", float(resilience))


func _clear_sprint_taps() -> void:
	_direction_taps.clear()
	_sprint_key = KEY_NONE


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_clear_sprint_taps()


func _input(event: InputEvent) -> void:
	if not event is InputEventKey or event.echo:
		return
	var key: Key = event.physical_keycode
	if not event.pressed:
		if _sprint_key == key:
			_sprint_key = KEY_NONE
		return
	if not input_enabled or scattered_now or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		_clear_sprint_taps()
		return
	for direction in ["move_left", "move_right", "move_forward", "move_back"]:
		if not event.is_action_pressed(direction):
			continue
		var now := Time.get_ticks_msec()
		var previous: int = _direction_taps.get(key, -1000)
		_direction_taps[key] = now
		if now - previous <= 250:
			_sprint_key = key
		break


func _unhandled_input(e: InputEvent) -> void:
	if not input_enabled or scattered_now:
		return
	if e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var sens := Game.tuning.f("camera.mouse_sensitivity", 0.0028) * float(Game.settings["mouse_sensitivity"])
		var inv := -1.0 if Game.settings["invert_y"] else 1.0
		_yaw -= e.relative.x * sens
		_pitch = clampf(_pitch - e.relative.y * sens * inv, deg_to_rad(Game.tuning.f("camera.pitch_min_deg", -70)),
			deg_to_rad(Game.tuning.f("camera.pitch_max_deg", 55)))
	if e.is_action_pressed("possess"):
		possession.toggle()
		get_viewport().set_input_as_handled()
		return
	if possession.host:
		if e.is_action_pressed("haunt"):
			possession.action()
		get_viewport().set_input_as_handled()
		return
	if e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			Game.inventory.selected = posmod(Game.inventory.selected - 1, 9)
			_refresh_tool()
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			Game.inventory.selected = posmod(Game.inventory.selected + 1, 9)
			_refresh_tool()
	for i in 9:
		if e.is_action_pressed("slot_%d" % (i + 1)):
			Game.inventory.selected = i
			_refresh_tool()
	if e.is_action_pressed("haunt") and target_hauntable:
		gw.director.haunt(target_hauntable, target_hauntable.gentle_action())
	elif e.is_action_pressed("haunt_strong") and target_hauntable:
		gw.director.haunt(target_hauntable, target_hauntable.strong_action())
	elif e.is_action_pressed("boo"):
		do_boo()
	elif e.is_action_pressed("interact"):
		interact()
	elif e.is_action_pressed("place"):
		try_place()


func _physics_process(dt: float) -> void:
	possession.update(dt)
	if possession.host:
		velocity = Vector3.ZERO
		_tick_state(dt, Vector3.ZERO, 0.0)
		_update_camera(dt, false)
		return
	if scattered_now:
		_clear_sprint_taps()
		_update_camera(dt, false)
		return
	var inp := Vector2.ZERO
	var vert := auto_vertical
	var fast := false
	if input_enabled:
		inp = Input.get_vector("move_left", "move_right", "move_back", "move_forward")
		if Input.is_action_pressed("ascend"):
			vert = 1.0
		elif Input.is_action_pressed("sink"):
			vert = -1.0
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			_clear_sprint_taps()
		fast = Input.is_action_pressed("fast") or _sprint_key != KEY_NONE
		var rs := Vector2(Input.get_joy_axis(0, JOY_AXIS_RIGHT_X), Input.get_joy_axis(0, JOY_AXIS_RIGHT_Y))
		if rs.length() > 0.2:
			var s := deg_to_rad(Game.tuning.f("camera.stick_sensitivity_deg_s", 160)) * dt
			_yaw -= rs.x * s
			_pitch = clampf(_pitch - rs.y * s * (-1.0 if Game.settings["invert_y"] else 1.0), -1.2, 0.95)
	if auto_move != Vector2.ZERO:
		inp = auto_move
	var t := Game.tuning
	var basis_y := Basis(Vector3.UP, _yaw)
	var wish := basis_y * Vector3(inp.x, 0, -inp.y)
	var spd := t.f("player.fast_speed_mps", 5.2) if fast else t.f("player.move_speed_mps", 3.2)
	spd *= 1.0 + 0.05 * Game.trait_rank("drift")
	var hv := Vector3(velocity.x, 0, velocity.z).lerp(wish * spd, clampf(dt * t.f("player.accel", 9.0), 0.0, 1.0))
	# vertical: hover over the first solid cell below, glide down, ascend with Ectoplasm, sink to phase
	var feet := global_position
	var feet_block := world.get_block_v(world.cell_of(feet + Vector3(0, 0.1, 0)))
	var inside_solid := Game.blocks.solid[feet_block] == 1
	var ground := world.ground_below(feet + Vector3(0, 0.05, 0))
	var hover := ground + t.f("player.hover_height_m", 1.0)
	var vy := 0.0
	if vert > 0.0 and Game.ecto > 0.5 and feet.y - ground < t.f("player.ascend_max_above_ground_m", 9.0):
		vy = t.f("player.ascend_mps", 2.6)
		Game.ecto = maxf(0.0, Game.ecto - t.f("player.ascend_ecto_per_s", 14.0) * dt)
	elif vert < 0.0:
		vy = -t.f("player.sink_mps", 2.2)
		var below := world.get_block_v(world.cell_of(feet + Vector3(0, -0.15, 0)))
		if Game.blocks.solid[below] == 1 and Game.blocks.phaseable[below] == 0:
			vy = 0.0
	elif inside_solid:
		vy = 0.0
	else:
		var diff := hover - feet.y
		if diff > 0.0:
			vy = minf(diff * t.f("player.hover_spring", 4.0), 3.0)
		else:
			vy = maxf(diff * t.f("player.hover_spring", 4.0), -t.f("player.glide_down_mps", 1.4))
	velocity = Vector3(hv.x, vy, hv.z)
	move_and_slide()
	if global_position.y < float(Game.layout.get("kill_y", -16.0)):
		_respawn_at_mausoleum()
	if hv.length() > 0.2:
		rotation.y = lerp_angle(rotation.y, atan2(hv.x, hv.z), clampf(dt * 10.0, 0.0, 1.0))
	var body_block := world.get_block_v(world.cell_of(global_position + Vector3(0, 0.35, 0)))
	var now_phasing := Game.blocks.solid[body_block] == 1 or _in_prop()
	if now_phasing and not phasing:
		_play_clip("phase", 0.4)
		Sfx.play_at("whoosh", global_position, -10.0)
	phasing = now_phasing
	sheet_mat.set_shader_parameter("phase", 1.0 if phasing else 0.0)
	_tick_state(dt, hv, vy)
	_update_camera(dt, false)


func _in_prop() -> bool:
	return false


func _tick_state(dt: float, hv: Vector3, vy: float) -> void:
	var t := Game.tuning
	Game.ecto = minf(t.f("player.ecto_max", 100.0), Game.ecto + t.f("player.ecto_regen_per_s", 3.0) * dt)
	Game.player_pos = global_position
	Game.player_yaw = rad_to_deg(rotation.y)
	_boo_cd = maxf(0.0, _boo_cd - dt)
	# rooms and shelter
	indoors = false
	for r in _rooms:
		if r.grow(0.2).has_point(global_position + Vector3(0, 0.3, 0)):
			indoors = true
			break
	sheltered = world.natural_cover(global_position + Vector3(0, 0.3, 0)) >= t.i("player.shelter_needs_natural_blocks_above", 2)
	if gw.caverns and gw.caverns.room_at(global_position) >= 0:
		sheltered = true
		indoors = true
	for m in _shelters:
		var p: Array = m["pos"]
		if global_position.distance_to(Vector3(p[0], p[1], p[2])) < float(m.get("radius", 1.5)) + 1.5:
			sheltered = true
	# daylight drain (inverted day)
	var ph := Game.phase()
	if (ph == "day" or ph == "dawn") and not sheltered:
		var k := t.f("player.dawn_drain_mult", 0.5) if ph == "dawn" else 1.0
		Game.hp -= t.f("player.daylight_drain_hp_per_s", 0.16) * k * dt
		_hurt_t -= dt
		if _hurt_t <= 0.0:
			_hurt_t = t.f("player.hurt_flash_every_s", 1.5)
			sheet_mat.set_shader_parameter("hurt", 1.0)
			create_tween().tween_method(func(v: float) -> void: sheet_mat.set_shader_parameter("hurt", v), 1.0, 0.0, 0.5)
			Sfx.play("hurt", -10.0)
	if Game.hp <= 0.0:
		possession.release()
		scatter()
		return
	# manifest
	if manifest_left > 0.0:
		manifest_left -= dt
		sheet_mat.set_shader_parameter("manifest", clampf(manifest_left * 2.0, 0.0, 1.0))
	# dropped essence pickup
	for i in range(Game.dropped_essence.size() - 1, -1, -1):
		var d: Dictionary = Game.dropped_essence[i]
		var p: Array = d["pos"]
		if global_position.distance_to(Vector3(p[0], p[1], p[2])) < 1.6:
			Game.fright_essence += float(d["amount"])
			Game.dropped_essence.remove_at(i)
			Game.toast.emit("Recovered %d Fright Essence" % int(d["amount"]), "info")
			Sfx.play("pickup")
			gw.refresh_essence_markers()
	# targeting and tools
	_update_targets()
	_swing_left = maxf(0.0, _swing_left - dt)
	if input_enabled and Input.is_action_pressed("use") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		use_selected()
	# animation
	_clip_lock -= dt
	if _clip_lock <= 0.0:
		if vy > 0.5:
			_play("ascend")
		elif vy < -0.6:
			_play("glide_down")
		elif hv.length() > 0.4:
			_play("drift")
		else:
			_play("idle_float")


func _play(clip: String) -> void:
	if _clip != clip and ap.has_animation(clip):
		_clip = clip
		ap.play(clip)


func _play_clip(clip: String, lock: float) -> void:
	if not ap.has_animation(clip):
		return
	_clip = clip
	ap.stop()
	ap.play(clip)
	_clip_lock = lock if lock > 0.0 else ap.get_animation(clip).length


func set_expression(key: String, seconds: float) -> void:
	for k in ["angry", "scared", "happy", "closed"]:
		Actors.set_shape(eyes, k, 1.0 if k == key else 0.0)
	if seconds > 0.0:
		get_tree().create_timer(seconds).timeout.connect(func() -> void:
			for k in ["angry", "scared", "happy", "closed"]:
				Actors.set_shape(eyes, k, 0.0))


func _update_camera(dt: float, snap: bool) -> void:
	var t := Game.tuning
	var want := t.f("camera.distance_indoor_m", 1.6) if indoors else t.f("camera.distance_m", 3.4)
	if _punch > 0.0:
		_punch -= dt
		want = t.f("camera.boo_punch_in_m", 1.3)
	_dist = want if snap else lerpf(_dist, want, clampf(dt * t.f("camera.zoom_lerp", 6.0), 0.0, 1.0))
	spring.spring_length = _dist
	# inside a phaseable block the camera ignores phaseable walls so it stays behind the ghost
	spring.collision_mask = VoxelWorld.L_SOLID if phasing else (VoxelWorld.L_SOLID | VoxelWorld.L_PHASE)
	cam_yaw.global_position = global_position + Vector3(0, t.f("camera.height_m", 0.9), 0)
	if possession and possession.host:
		cam_yaw.global_position = possession.host.global_position + Vector3.UP * 0.8
	cam_yaw.rotation = Vector3(0, _yaw, 0)
	cam_pitch.rotation = Vector3(_pitch, 0, 0)
	xray_mat.set_shader_parameter("strength", 1.0 if phasing else 0.35)


func punch_in(seconds: float) -> void:
	_punch = seconds


# ---------------------------------------------------------------- targeting

func aim_ray() -> Array:
	var vp := get_viewport()
	var center := vp.get_visible_rect().size * 0.5
	return [camera.project_ray_origin(center), camera.project_ray_normal(center)]


func _update_targets() -> void:
	var t := Game.tuning
	var ray := aim_ray()
	var from: Vector3 = ray[0]
	var dir: Vector3 = ray[1]
	# block / node within reach of the ghost (the ray starts at the camera; skip the stretch behind the ghost)
	var skip := maxf(0.0, (global_position + Vector3(0, 0.4, 0) - from).dot(dir) - 0.6)
	var start := from + dir * skip
	var reach := t.f("player.reach_m", 4.5) + 0.6
	target_block = world.raycast(start, dir, reach)
	target_node = level.pick_prop_node(start, dir, reach)
	if not target_node.is_empty() and target_block.get("hit", false) and float(target_block["dist"]) < float(target_node["dist"]):
		target_node = {}
	var sel := Game.inventory.selected_id()
	if target_block.get("hit", false) and Game.inventory.is_tool(sel):
		var c: Vector3i = target_block["cell"]
		_crack.global_position = Vector3(c) + Vector3(0.5, 0.5, 0.5)
		_crack.global_rotation = Vector3.ZERO
		_crack.visible = c == _mine_cell and _mine_hits > 0
	else:
		_crack.visible = false
	# hauntable: closest to the crosshair inside the aim cone and range
	var best: Hauntable = null
	var best_a := deg_to_rad(t.f("haunting.aim_cone_deg", 14.0))
	var rng := t.f("haunting.range_m", 7.0)
	for id: String in level.hauntables:
		if not is_instance_valid(level.hauntables[id]):
			continue
		var h: Hauntable = level.hauntables[id]
		if not is_instance_valid(h.root) or not h.root.is_visible_in_tree():
			continue
		if not bool(h.data.get("slice_active", false)) and h.ability() != "haunted_furniture":
			continue
		var p := h.world_pos()
		if p.distance_to(global_position) > rng:
			continue
		var a := dir.angle_to(p - from)
		if a < best_a:
			best_a = a
			best = h
	target_hauntable = best
	# villager for the Unease meter: nearest in view within 14 m
	var bn: Npc = null
	var bd := 14.0
	for n: Npc in gw.npcs:
		if not n.visible:
			continue
		var d := n.global_position.distance_to(global_position)
		if d < bd and dir.angle_to(n.head_pos() - from) < 0.6:
			bd = d
			bn = n
	target_npc = bn


# ---------------------------------------------------------------- verbs

func _refresh_tool() -> void:
	var sel := Game.inventory.selected_id()
	var want := ""
	if Game.inventory.is_tool(sel):
		want = "%s_t%d" % [sel, maxi(1, Game.inventory.tool_tier(sel))]
	if want == tool_id:
		return
	tool_id = want
	if tool_node:
		tool_node.queue_free()
		tool_node = null
	if want == "" or tool_socket == null:
		return
	var ps := load("res://assets/props/%s.gltf" % want) as PackedScene
	if ps == null:
		return
	tool_node = ps.instantiate()
	tool_socket.add_child(tool_node)
	# Task1/2 convention: align the tool's GRIP with the hand socket; tools are scaled 0.75 for the
	# 0.6 m ghost (issues.md, task2).
	var s := 0.75
	tool_node.scale = Vector3.ONE * s
	var grip := Actors.find_prefix(tool_node, "GRIP") as Node3D
	if grip:
		tool_node.position = -grip.position * s


func use_selected() -> void:
	if _swing_left > 0.0:
		return
	var sel := Game.inventory.selected_id()
	if Game.inventory.is_tool(sel):
		try_mine()
	elif Game.inventory.block_for(sel) != "":
		try_place()


func _tool_clip(tool: String) -> String:
	return {"scythe": "swing_scythe", "shovel": "dig_shovel", "sledgehammer": "smash_hammer"}.get(tool, "swing_scythe")


## One swing at the targeted node or block with the selected tool. Returns a status string.
func try_mine() -> String:
	var t := Game.tuning
	var tool := Game.inventory.selected_id()
	if not Game.inventory.is_tool(tool):
		return "no tool"
	var tier := Game.inventory.tool_tier(tool)
	_swing_left = t.f("mining.swing_s", 0.42)
	_play_clip(_tool_clip(tool), _swing_left)
	if not target_node.is_empty():
		return gw.gather.hit_node(String(target_node["id"]), tool, tier, self)
	if not target_block.get("hit", false):
		return "nothing"
	var c: Vector3i = target_block["cell"]
	var b: int = target_block["block"]
	var why := Game.blocks.mine_check(b, tool, tier)
	if why != "":
		gw.hud.hint("This block %s" % why)
		Sfx.play_at("mine_stone", Vector3(c) + Vector3.ONE * 0.5, -10.0)
		return why
	if c != _mine_cell:
		_mine_cell = c
		_mine_hits = 0
	_mine_hits += 1
	var need: int = gw.gather.hits_for_cell(c, b, tier)
	Sfx.play_at(gw.gather.hit_sound(b), Vector3(c) + Vector3.ONE * 0.5, -2.0)
	Fx.burst(get_parent(), Vector3(c) + Vector3(0.5, 0.6, 0.5), Color(0.8, 0.95, 1.0, 0.8), 6, 1.2, 0.4, 0.06)
	_crack.material_override = _crack_mats[clampi(int(float(_mine_hits) / float(need) * 5.0) - 1, 0, 4)]
	if _mine_hits >= need:
		_mine_hits = 0
		_mine_cell = Vector3i(-999, 0, 0)
		gw.gather.break_block(c, b, self)
		return "broke"
	return "hit"


func try_place() -> String:
	var item := Game.inventory.selected_id()
	var block_id := Game.inventory.block_for(item)
	if block_id == "" or Game.inventory.count(item) <= 0:
		return "nothing to place"
	if not target_block.get("hit", false):
		return "no surface"
	var c: Vector3i = target_block["cell"] + target_block["normal"]
	var cur := world.get_block_v(c)
	if cur != 0 and Game.blocks.cross[cur] == 0:
		return "occupied"
	for n: Npc in gw.npcs:
		if world.cell_of(n.global_position) == c or world.cell_of(n.global_position + Vector3.UP) == c:
			return "villager in the way"
	world.set_block(c, Game.blocks.index_of(block_id))
	Game.inventory.remove(item, 1)
	Game.stats["blocks_placed"] += 1
	_swing_left = 0.25
	Sfx.play_at("block_place", Vector3(c) + Vector3.ONE * 0.5)
	return "placed"


func do_boo() -> Dictionary:
	if _boo_cd > 0.0:
		return {}
	var cost := Game.tuning.f("scare.boo.ecto_cost", 20.0)
	if Game.ecto < cost:
		gw.hud.hint("Not enough Ectoplasm to manifest")
		return {}
	Game.ecto -= cost
	_boo_cd = Game.tuning.f("scare.boo.cooldown_s", 3.0)
	manifest_left = float(Game.presence_level().get("manifest_s", 1.6))
	sheet_mat.set_shader_parameter("manifest", 1.0)
	_play_clip("boo", 0.0)
	set_expression("angry", 1.5)
	Sfx.play_at("boo", global_position + Vector3(0, 0.4, 0), 2.0)
	Fx.burst(get_parent(), global_position + Vector3(0, 0.4, 0), Color(0.7, 0.9, 1.0), 24, 2.5, 0.7)
	return gw.director.boo(self)


func interact() -> String:
	if gw.caverns and gw.caverns.interact():
		return "cavern"
	if level.workbench and global_position.distance_to(level.workbench_pos()) < Game.tuning.f("workbench_reach_m", 3.0):
		gw.open_inventory(true)
		return "workbench"
	var r: Dictionary = Game.markers_by_id.get("respawn", {})
	if not r.is_empty():
		var p: Array = r["pos"]
		if global_position.distance_to(Vector3(p[0], p[1], p[2])) < 3.0:
			gw.sleep_until_dusk()
			return "sleep"
	return ""


func near_workbench() -> bool:
	return level.workbench != null and global_position.distance_to(level.workbench_pos()) < Game.tuning.f("workbench_reach_m", 3.0)


func scatter() -> void:
	if scattered_now:
		return
	scattered_now = true
	Game.hp = 0.0
	velocity = Vector3.ZERO
	_play_clip("scatter", 0.0)
	set_expression("scared", 0.0)
	Sfx.play("scatter")
	var drop := floorf(Game.fright_essence * Game.tuning.f("player.scatter_drop_fraction", 0.35))
	if drop > 0.0:
		Game.fright_essence -= drop
		Game.dropped_essence.append({"pos": [global_position.x, global_position.y, global_position.z], "amount": drop})
	Fx.burst(get_parent(), global_position + Vector3(0, 0.3, 0), Color(0.75, 0.92, 1.0), 60, 3.0, 2.0, 0.14)
	create_tween().tween_method(func(v: float) -> void: sheet_mat.set_shader_parameter("scatter", v), 0.0, 1.0, 1.0)
	gw.refresh_essence_markers()
	scattered.emit(drop)


func respawn() -> void:
	_respawn_at_mausoleum()
	scattered_now = false
	Game.hp = Game.max_hp() * Game.tuning.f("player.respawn_hp_fraction", 1.0)
	sheet_mat.set_shader_parameter("scatter", 0.0)
	set_expression("", 0.0)
	_play_clip("idle_float", 0.1)
	respawned.emit()


func _respawn_at_mausoleum() -> void:
	var r: Dictionary = Game.markers_by_id.get("respawn", {})
	var p: Array = r.get("pos", [24.9, 28.0, 92.5])
	teleport(Vector3(p[0], p[1] + 0.2, p[2]), float(r.get("yaw", 90.0)))
