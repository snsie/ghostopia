## A villager: follows the task4 schedule (stay steps at markers, walk steps along the precomputed
## routes at no-slide speeds), and reacts to the scare system: escalation clips, bolting and fleeing
## home, the big break, botches, suspicious actions, waking up. Leaves the route only with an A*
## path over the voxels (fleeing, rejoining) and then snaps back to the schedule.
class_name Npc
extends Node3D

signal said(npc: Npc, line: String)

enum Mode { SCHEDULE, CLIP, PATH }

var id: String
var data: Dictionary
var mind: VillagerMind
var char_data: Dictionary
var model: Node3D
var ap: AnimationPlayer
var face: MeshInstance3D
var hat: Node3D
var held_r: Node3D
var held_l: Node3D
var builtin_item: Node3D          # ITEM_* under a socket
var builtin_item_id := ""
var extra_item: Node3D
var extra_item_id := ""
var carried: Hauntable            # the light in their hand (Flicker target)
var carried_data: Dictionary
var level: Level
var world: VoxelWorld
var bubble: Label3D

var mode := Mode.SCHEDULE
var step_index := -1
var asleep := false
var awake_until := 0.0
var indoors := false
var forward := Vector3.FORWARD
var speed := 0.0
var _clip := ""
var _clip_end := 0.0
var _after_clip := ""            # "flee" | "rejoin" | ""
var _path := PackedVector3Array()
var _path_i := 0
var _path_speed := 1.0
var _path_clip := "walk"
var _path_then := ""             # "rejoin" | "schedule" | "hide"
var _hidden_until := 0.0
var _door_check := 0.0
var _relight_at := -1.0
var _relight_target: Hauntable
var _bubble_until := 0.0
var _cum: Dictionary = {}        # step index -> PackedFloat32Array of cumulative route lengths
var _spare_light := false
var _foot_t := 0.0
var _now := 0.0


func setup(p_data: Dictionary, p_level: Level, p_world: VoxelWorld) -> void:
	data = p_data
	id = String(data["id"])
	name = "npc_" + id
	level = p_level
	world = p_world
	mind = Game.minds[id]
	char_data = Game.characters.get(String(data["character"]), {})
	model = (load(String(data["gltf"])) as PackedScene).instantiate()
	add_child(model)
	ap = Actors.find_prefix(model, "AnimationPlayer") as AnimationPlayer
	Actors.setup_loops(ap, char_data)
	ap.playback_default_blend_time = 0.2
	face = Actors.find_prefix(model, String(data["character"]) + "_face") as MeshInstance3D
	hat = Actors.find_prefix(model, String(data["character"]) + "_hat") as Node3D
	held_r = Actors.find_prefix(model, "HELD_R") as Node3D
	held_l = Actors.find_prefix(model, "HELD_L") as Node3D
	var items: Dictionary = char_data.get("items", {})
	for side: String in items:
		var sock := held_r if side == "R" else held_l
		if sock and sock.get_child_count() > 0:
			builtin_item = sock.get_child(0)
			builtin_item_id = String(items[side])
	for l in _all_lights(model):
		l.shadow_enabled = false
		l.omni_range = 6.0
		l.light_color = Color(Game.tuning.get_value("world.lantern_color", "#ffad5c"))
	for h in Game.population.get("hauntables", []):
		if h.get("source") == "carried" and h.get("carried_by") == id:
			carried_data = h
	if not carried_data.is_empty():
		if carried_data.get("node") != null and builtin_item:
			carried = level.register_carried(carried_data, builtin_item)
	bubble = Label3D.new()
	bubble.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	bubble.no_depth_test = true
	bubble.fixed_size = true
	bubble.pixel_size = 0.0011
	bubble.font_size = 40
	bubble.outline_size = 14
	bubble.modulate = Color(1, 1, 0.94)
	bubble.outline_modulate = Color(0.08, 0.06, 0.16, 0.95)
	bubble.width = 520
	bubble.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bubble.position = Vector3(0, head_height() + 0.95, 0)
	bubble.visible = false
	add_child(bubble)
	for i in (data["schedule"] as Array).size():
		var s: Dictionary = data["schedule"][i]
		if s["kind"] == "walk":
			var cum := PackedFloat32Array([0.0])
			var r: Array = s["route"]
			for k in range(1, r.size()):
				cum.append(cum[-1] + _v(r[k]).distance_to(_v(r[k - 1])))
			_cum[i] = cum
	_snap_to_schedule()


static func _v(a: Array) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))


func _all_lights(n: Node) -> Array[OmniLight3D]:
	var out: Array[OmniLight3D] = []
	var stack: Array[Node] = [n]
	while not stack.is_empty():
		var c: Node = stack.pop_back()
		if c is OmniLight3D:
			out.append(c)
		stack.append_array(c.get_children())
	return out


func head_height() -> float:
	return float(char_data.get("head_top", 1.6))


func head_pos() -> Vector3:
	return global_position + Vector3(0, head_height() + 0.25, 0)


func is_awake() -> bool:
	return not asleep or _now < awake_until


func is_target() -> bool:
	return mind.can_be_scared()


# ---------------------------------------------------------------- schedule

func _step_at(t: float) -> int:
	var sch: Array = data["schedule"]
	for i in sch.size():
		var a := float(sch[i]["t_start"])
		var b := float(sch[i]["t_end"])
		if (a <= b and t >= a and t < b) or (a > b and (t >= a or t < b)):
			return i
	return 0


func _step_frac(s: Dictionary, t: float) -> float:
	var a := float(s["t_start"])
	var b := float(s["t_end"])
	var span := b - a
	if span <= 0.0:
		span += 1.0
	var e := t - a
	if e < 0.0:
		e += 1.0
	return clampf(e / span, 0.0, 1.0)


## Where the schedule puts this villager at cycle time t: {pos, yaw, moving, step}.
func schedule_pose(t: float) -> Dictionary:
	var i := _step_at(t)
	var s: Dictionary = data["schedule"][i]
	if s["kind"] == "stay":
		return {"pos": _v(s["pos"]), "yaw": deg_to_rad(float(s.get("yaw", 0.0))), "moving": false, "step": i}
	var r: Array = s["route"]
	var cum: PackedFloat32Array = _cum[i]
	var d := _step_frac(s, t) * cum[-1]
	for k in range(1, r.size()):
		if d <= cum[k] or k == r.size() - 1:
			var seg := maxf(cum[k] - cum[k - 1], 0.0001)
			var a := _v(r[k - 1])
			var b := _v(r[k])
			var p := a.lerp(b, clampf((d - cum[k - 1]) / seg, 0.0, 1.0))
			var dir := b - a
			return {"pos": p, "yaw": atan2(dir.x, dir.z), "moving": true, "step": i}
	return {"pos": _v(r[-1]), "yaw": 0.0, "moving": false, "step": i}


func _snap_to_schedule() -> void:
	var pose := schedule_pose(Game.cycle_t)
	global_position = pose["pos"]
	rotation.y = pose["yaw"]
	_enter_step(int(pose["step"]))


func _enter_step(i: int) -> void:
	step_index = i
	var s: Dictionary = data["schedule"][i]
	asleep = bool(s.get("asleep", false)) or String(s.get("animation", "")) == "sleep"
	indoors = bool(s.get("indoors", false))
	_set_item(s.get("held_item", null), String(s.get("animation", "")))
	if carried and not carried_data.is_empty():
		var active: bool = (carried_data.get("during_steps", []) as Array).has(i)
		carried.root.visible = active
		if active and not carried.lit and not asleep:
			carried.set_lit(true)


func _set_item(item: Variant, clip: String) -> void:
	var want := "" if item == null else String(item)
	var item_clips: Array = char_data.get("item_clips", [])
	if builtin_item:
		builtin_item.visible = (want == builtin_item_id) or (want == "" and item_clips.has(clip) and builtin_item_id in ["candle", "pitchfork", "lantern"] and false)
		if want == "" and builtin_item_id in ["book", "doll"] and item_clips.has(clip):
			builtin_item.visible = true
	if want == extra_item_id:
		return
	if extra_item:
		if carried and carried.root == extra_item:
			level.hauntables.erase(carried.id)
			carried = null
		extra_item.queue_free()
		extra_item = null
	extra_item_id = ""
	if want == "" or want == builtin_item_id or want == "tray" or want == "doll" or want == "book" or want == "pitchfork":
		return
	var path := "res://assets/props/%s.gltf" % want
	if not ResourceLoader.exists(path):
		return
	var sock := held_l if (builtin_item and builtin_item.get_parent() == held_r) else held_r
	if sock == null:
		return
	extra_item = (load(path) as PackedScene).instantiate()
	sock.add_child(extra_item)
	extra_item_id = want
	for l in _all_lights(extra_item):
		l.shadow_enabled = false
		l.omni_range = 6.0
		l.light_color = Color(Game.tuning.get_value("world.lantern_color", "#ffad5c"))
		l.light_energy = 1.4
	# The prop pivot is its base: hang lanterns and buckets below the hand, stand candles on it.
	extra_item.position = Vector3(0, -0.32, 0) if want in ["lantern", "bucket"] else Vector3(0, -0.02, 0)
	if want == "broom":
		extra_item.position = Vector3(0, -0.7, 0.05)
	if not carried_data.is_empty() and carried_data.get("attach_prop") != null and String(carried_data["attach_prop"]).ends_with(want + ".gltf"):
		carried = level.register_carried(carried_data, extra_item)


# ---------------------------------------------------------------- update

var possessed := false
var _investigate_after := 0.0


func available_to_chat() -> bool:
	return not possessed and mode == Mode.SCHEDULE and visible and is_awake() and _now >= _investigate_after


func chat_with(other: Npc, now: float) -> void:
	var greetings := {"agnes": "The millstones have been restless.", "pip": "Did you see the lights?", "marlow": "Keep your lantern close."}
	say(greetings.get(id, "How is your evening?") if mind.frac() < 0.5 else "I don't like how quiet it is.")
	other.say("Let's keep walking." if other.mind.frac() >= 0.5 else "Evening, %s." % data.get("name", id))
	_investigate_after = now + 25.0
	other._investigate_after = now + 25.0
	play_clip("idle", 2.0, "rejoin")
	other.play_clip("idle", 2.0, "rejoin")


func investigate(point: Vector3) -> void:
	if possessed or mode != Mode.SCHEDULE or not is_awake() or _now < _investigate_after:
		return
	if global_position.distance_to(point) > 7.0 or global_position.distance_to(point) < 1.0:
		return
	_investigate_after = _now + 25.0
	var lines := {"agnes": "The mill makes stranger sounds than that.", "pip": "Hello? Is somebody there?"}
	say(lines.get(id, "I thought I heard something."))
	_go(global_position.lerp(point, 0.5), 0.9, "walk", "rejoin")


func tick(dt: float, now: float) -> void:
	_now = now
	if possessed:
		return
	if now < _hidden_until:
		return
	if not visible:
		visible = true
	match mode:
		Mode.SCHEDULE:
			_tick_schedule(dt)
		Mode.CLIP:
			if now >= _clip_end:
				_end_clip()
		Mode.PATH:
			_tick_path(dt)
	_door_check -= dt
	if _door_check <= 0.0:
		_door_check = 0.25
		_open_doors()
	if _relight_at > 0.0 and now >= _relight_at and is_awake():
		_relight_at = -1.0
		if _relight_target and is_instance_valid(_relight_target) and not _relight_target.lit:
			play_clip("relight_candle", 2.2, "")
			_relight_target.set_lit(true)
	if bubble.visible and now > _bubble_until:
		bubble.visible = false
	_update_face()


func _tick_schedule(dt: float) -> void:
	var pose := schedule_pose(Game.cycle_t)
	var si := int(pose["step"])
	if si != step_index:
		_enter_step(si)
	var target: Vector3 = pose["pos"]
	var d := global_position.distance_to(target)
	if d > 3.0 and mode == Mode.SCHEDULE:
		_rejoin()
		return
	var prev := global_position
	global_position = target
	speed = (global_position - prev).length() / maxf(dt, 0.0001)
	var s: Dictionary = data["schedule"][step_index]
	if pose["moving"]:
		rotation.y = lerp_angle(rotation.y, float(pose["yaw"]), clampf(dt * 8.0, 0.0, 1.0))
		_play_walk(float(s.get("speed_mps", 0.6)))
	else:
		rotation.y = lerp_angle(rotation.y, float(pose["yaw"]), clampf(dt * 4.0, 0.0, 1.0))
		var clip := String(s.get("animation", "idle"))
		if asleep and now_awake():
			clip = "idle"
			if mind.frac() < Game.tuning.f("scare.fall_asleep_again_below", 0.2) and _now > awake_until:
				awake_until = 0.0
		if clip == "walk":
			clip = "idle"
		_play(clip, 1.0)
	forward = Vector3(sin(rotation.y), 0, cos(rotation.y))


func now_awake() -> bool:
	return _now < awake_until


func _play_walk(mps: float) -> void:
	var clip := String(_stage_row().get("walk", "walk"))
	if not ap.has_animation(clip):
		clip = "walk"
	var ns: Dictionary = char_data.get("no_slide_speed_mps", {})
	var base := float(ns.get(clip, ns.get("walk", 0.6)))
	_play(clip, clampf(mps / maxf(base, 0.05), 0.3, 3.0))
	_foot_t -= get_process_delta_time()
	if _foot_t <= 0.0:
		_foot_t = 0.5 / clampf(mps / maxf(base, 0.05), 0.4, 3.0)
		if get_viewport().get_camera_3d() and get_viewport().get_camera_3d().global_position.distance_to(global_position) < 12.0:
			Sfx.play_at("footstep", global_position, -14.0, 14.0)


func _stage_row() -> Dictionary:
	var st: Array = Game.tuning.a("scare.stages")
	if st.is_empty():
		return {}
	return st[ScareMath.stage_index(mind.frac(), st)]


func _play(clip: String, spd: float) -> void:
	if not ap.has_animation(clip):
		clip = "idle"
	if _clip != clip:
		_clip = clip
		ap.play(clip)
	ap.speed_scale = spd


func play_clip(clip: String, seconds: float, then: String) -> void:
	if not ap.has_animation(clip):
		return
	mode = Mode.CLIP
	_clip = ""
	_play(clip, 1.0)
	var len := ap.get_animation(clip).length
	_clip_end = _now + (seconds if seconds > 0.0 else len)
	_after_clip = then


func _end_clip() -> void:
	var then := _after_clip
	_after_clip = ""
	mode = Mode.SCHEDULE
	if then == "flee":
		flee()
	elif then == "rejoin":
		_rejoin()


func _rejoin() -> void:
	var pose := schedule_pose(fmod(Game.cycle_t + 8.0 / Game.cycle_length(), 1.0))
	_go(pose["pos"], float(Game.tuning.f("npc.rejoin_speed_mult", 1.25)) * float(data.get("walk_speed_mps", 0.6)), "walk", "schedule")


func flee() -> void:
	var to: Vector3 = _home_point()
	var ob: Dictionary = data.get("on_break", {})
	var ft := String(ob.get("flee_to", ""))
	if ft.begins_with("marker:"):
		var m: Dictionary = Game.markers_by_id.get(ft.substr(7), {})
		if not m.is_empty():
			to = _v(m["pos"])
	elif ft.begins_with("area:"):
		for st in Game.layout["structures"]:
			if st["id"] == ft.substr(5):
				var pv: Array = st["pivot"]
				to = Vector3(pv[0], pv[1], pv[2])
	_go(to, float(data.get("flee_speed_mps", 2.0)) * Game.tuning.f("npc.flee_speed_mult", 1.0), "flee", "hide")


func _home_point() -> Vector3:
	var m: Dictionary = Game.markers_by_id.get(String(data.get("home_marker", "")), {})
	if m.is_empty():
		return global_position
	return _v(m["pos"])


func _go(to: Vector3, mps: float, clip: String, then: String) -> void:
	_path = VoxelPath.find(world, global_position, to, Game.tuning.i("npc.path_max_nodes", 30000))
	_path_i = 0
	_path_speed = mps
	_path_clip = clip
	_path_then = then
	if _path.is_empty():
		# No path: they slip out of sight and come back where the schedule wants them.
		_hide(4.0)
		return
	mode = Mode.PATH


func _hide(seconds: float) -> void:
	visible = false
	_hidden_until = _now + seconds
	mode = Mode.SCHEDULE
	var pose := schedule_pose(Game.cycle_t)
	global_position = pose["pos"]


func _tick_path(dt: float) -> void:
	if _path_i >= _path.size():
		match _path_then:
			"rejoin":
				_rejoin()
			"hide":
				_hide(Game.tuning.f("scare.recover_after_break_s", 14.0))
			_:
				mode = Mode.SCHEDULE
		return
	var target := _path[_path_i]
	var to := target - global_position
	var step := _path_speed * dt
	if to.length() <= step:
		global_position = target
		_path_i += 1
	else:
		global_position += to.normalized() * step
		var flat := Vector3(to.x, 0, to.z)
		if flat.length() > 0.01:
			rotation.y = lerp_angle(rotation.y, atan2(flat.x, flat.z), clampf(dt * 10.0, 0.0, 1.0))
	forward = Vector3(sin(rotation.y), 0, cos(rotation.y))
	var ns: Dictionary = char_data.get("no_slide_speed_mps", {})
	var base := float(ns.get(_path_clip, ns.get("walk", 0.6)))
	_play(_path_clip, clampf(_path_speed / maxf(base, 0.05), 0.3, 3.0))


func _open_doors() -> void:
	for id2: String in level.hauntables:
		var h: Hauntable = level.hauntables[id2]
		if h.kind == "door" and h.world_pos().distance_to(global_position) < Game.tuning.f("npc.door_open_radius_m", 1.3) + 0.5:
			h.open_for_villager(_now)


func _update_face() -> void:
	if face == null:
		return
	var st := String(_stage_row().get("expression", "calm"))
	for k in ["uneasy", "scared", "terrified"]:
		Actors.set_shape(face, k, 1.0 if k == st else 0.0)
	Actors.set_shape(face, "asleep", 1.0 if (asleep and not now_awake()) else 0.0)


# ---------------------------------------------------------------- reactions

func say(line: String, seconds: float = 4.5) -> void:
	if line == "":
		return
	bubble.text = line
	bubble.visible = true
	_bubble_until = _now + seconds
	said.emit(self, line)


## Stage escalation from an act (glance, "hello?", startle).
var _scream_after := 0.0


func react_stage(stage_before: String, stage_after: String) -> void:
	if stage_after == stage_before:
		return
	if stage_after in ["scared", "primed"] and stage_before not in ["scared", "primed"] and _now >= _scream_after:
		Sfx.play_at("scream", head_pos(), -2.0)
		_scream_after = _now + 12.0
	if mode == Mode.PATH:
		return
	for s in Game.tuning.a("scare.stages"):
		if s["id"] == stage_after:
			if s.get("line"):
				say(String(s["line"]), 3.0)
				Sfx.play_at("hello", head_pos(), -2.0)
			if s.get("clip") != null and not (asleep and not now_awake()):
				play_clip(String(s["clip"]), 0.0, "")
			if stage_after in ["scared", "primed"]:
				Sfx.play_at("gasp", head_pos(), -4.0)


func wake(unease_frac: float) -> void:
	if not asleep:
		return
	awake_until = _now + 25.0
	mind.unease = maxf(mind.unease, mind.nerve * unease_frac)
	say("Wh-what? Who's there?", 3.0)


## The break: the big funny leap, scream, dropped light, hat off, then flee.
func break_scare(grade: String) -> void:
	var ob: Dictionary = data.get("on_break", {})
	say(String(ob.get("line", "AAAH!")), 3.5)
	Sfx.play_at("scream", head_pos(), 4.0, 40.0, 0.1)
	play_clip("big_scare_leap", 0.0, "flee")
	var ev: Dictionary = char_data.get("events", {}).get("big_scare_leap", {})
	var fps := 24.0
	get_tree().create_timer(float(ev.get("hat_off_frame", 8)) / fps, true, false, true).timeout.connect(_hat_off)
	get_tree().create_timer(float(ev.get("drop_item_frame", 11)) / fps, true, false, true).timeout.connect(_drop_item)


func _hat_off() -> void:
	if hat == null or not hat.visible:
		return
	hat.visible = false
	var body := RigidBody3D.new()
	body.collision_layer = 0
	body.collision_mask = VoxelWorld.L_SOLID | VoxelWorld.L_PHASE
	var copy := hat.duplicate() as Node3D
	body.add_child(copy)
	copy.transform = Transform3D.IDENTITY
	var cs := CollisionShape3D.new()
	var sp := SphereShape3D.new()
	sp.radius = 0.15
	cs.shape = sp
	body.add_child(cs)
	get_parent().add_child(body)
	body.global_transform = hat.global_transform
	body.linear_velocity = Vector3(randf_range(-0.6, 0.6), 4.2, randf_range(-0.6, 0.6)) - forward * 0.8
	body.angular_velocity = Vector3(randf_range(-6, 6), randf_range(-4, 4), randf_range(-6, 6))
	get_tree().create_timer(6.0).timeout.connect(func() -> void:
		if is_instance_valid(body):
			body.queue_free()
		if is_instance_valid(hat):
			hat.visible = true)


func _drop_item() -> void:
	var item: Node3D = extra_item if extra_item else (builtin_item if builtin_item and builtin_item.visible else null)
	if item == null:
		return
	var body := RigidBody3D.new()
	body.collision_layer = 0
	body.collision_mask = VoxelWorld.L_SOLID | VoxelWorld.L_PHASE
	var path := "res://assets/props/%s.gltf" % (extra_item_id if extra_item else builtin_item_id)
	if ResourceLoader.exists(path):
		var vis: Node3D = (load(path) as PackedScene).instantiate()
		for l in _all_lights(vis):
			l.queue_free()
		body.add_child(vis)
	var cs := CollisionShape3D.new()
	var bx := BoxShape3D.new()
	bx.size = Vector3(0.2, 0.3, 0.2)
	cs.shape = bx
	cs.position.y = 0.15
	body.add_child(cs)
	get_parent().add_child(body)
	body.global_position = item.global_position
	body.linear_velocity = forward * 1.2 + Vector3(0, 2.0, 0)
	body.angular_velocity = Vector3(3, 1, 2)
	item.visible = false
	if carried and carried.root == item:
		carried.set_lit(false)
	Sfx.play_at("block_place", item.global_position, -2.0)
	get_tree().create_timer(10.0).timeout.connect(func() -> void:
		if is_instance_valid(body):
			body.queue_free()
		if is_instance_valid(item):
			item.visible = true
		if carried and is_instance_valid(carried) and carried.root == item:
			carried.set_lit(true))


func botch(reason: String) -> void:
	var ob: Dictionary = data.get("on_botch", {}) if data.get("on_botch") != null else {}
	var clip := String(ob.get("animation", "laugh_it_off"))
	if reason == "spotted":
		say("I SEE you! Out! Out of here!", 3.5)
		play_clip("call_out", 0.0, "")
	else:
		say(String(ob.get("line", "Ha! Nearly had me.")), 3.5)
		play_clip(clip, 0.0, "")
		if clip == "laugh_it_off":
			Sfx.play_at("laugh", head_pos(), 0.0)


func bolt() -> void:
	say("Nope. Nope nope nope!", 2.5)
	Sfx.play_at("scream", head_pos(), 0.0)
	flee()


## A suspicious reaction from the population data (animation + line); the director applies effects.
func suspicious(reaction: Dictionary) -> void:
	say(String(reaction.get("line", "")), 4.0)
	play_clip(String(reaction.get("animation", "suspicious_search")), 2.5, "")
	if reaction.get("action") == "carry_spare_light":
		_spare_light = true


## A light near them went out: relight it after a moment (they're awake and not fleeing).
func notice_snuffed(h: Hauntable, delay: float) -> void:
	if not is_awake() or mode == Mode.PATH:
		return
	_relight_target = h
	_relight_at = _now + (1.5 if _spare_light else delay)
	_spare_light = false


func to_save() -> Dictionary:
	return {}
