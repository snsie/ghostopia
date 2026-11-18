## Owns the temporary host and leaves the ghost at the entry point.
extends Node

const LABELS := ["object_possession", "animal_possession", "villager_possession"]
const DURATION := [8.0, 6.0, 4.0]

var player: Player
var host: Node3D
var target: Node3D
var tier := 0
var target_tier := 0
var left := 0.0
var acted := false
var home: Transform3D
var rooted := false
var cooldowns := {}
var animals: Array[Node3D] = []
var animal_homes: Array[Vector3] = []
var clock := 0.0
var animal_alarm := {}


static func animal_voice(dog: bool) -> AudioStreamWAV:
	var rate := 16000
	var data := PackedByteArray()
	data.resize(rate)
	var rng := RandomNumberGenerator.new()
	rng.seed = 897
	for i in rate >> 1:
		var t := float(i) / rate
		var envelope := sin(PI * t * 2.0)
		var noise := rng.randf_range(-1.0, 1.0)
		var wave := noise
		if dog:
			wave = sin(TAU * (290.0 * t - 180.0 * t * t)) * 0.75 + 0.25 * noise
			envelope *= pow(absf(sin(TAU * t * 3.0)), 2)
		else:
			wave *= 0.5 + 0.5 * sin(TAU * t * 1660.0)
		data.encode_s16(i * 2, int(wave * envelope * 9500.0))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.data = data
	return stream


func setup(p: Player) -> void:
	player = p
	Sfx.register_stream("dog_bark", animal_voice(true))
	Sfx.register_stream("cat_hiss", animal_voice(false))
	for i in 2:
		var animal := Node3D.new()
		animal.name = ["Dog", "Cat"][i]
		player.gw.add_child(animal)
		var point := Vector3(111.0 + 3 * i, 32.0, 86.0)
		point.y = player.world.ground_below(point)
		animal.global_position = point
		animals.append(animal)
		animal_homes.append(point)
		var color := Color.SANDY_BROWN if i == 0 else Color.DARK_SLATE_GRAY
		_part(animal, Vector3(0, 0.27, 0), Vector3(0.33, 0.35, 0.65), color)
		_part(animal, Vector3(0, 0.43, -0.34), Vector3(0.27, 0.28, 0.26), color)
		for side in [-1, 1]:
			_part(animal, Vector3(side * 0.10, 0.59, -0.34), Vector3(0.08, 0.15, 0.09), color)
			for end in [-1, 1]:
				_part(animal, Vector3(side * 0.10, 0.11, end * 0.22), Vector3(0.09, 0.22, 0.10), color)
		_part(animal, Vector3(0, 0.43, 0.37), Vector3(0.08, 0.23, 0.09), color)


func _part(parent: Node3D, pos: Vector3, size: Vector3, color: Color) -> void:
	var part := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	part.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	part.material_override = material
	part.position = pos
	parent.add_child(part)


func update(dt: float) -> void:
	clock += dt
	for i in animals.size():
		var animal := animals[i]
		if animal != host:
			var phase := clock * 0.3 + i * PI
			var goal := animal_homes[i] + Vector3(cos(phase), 0, sin(phase)) * 2.0
			if animal_alarm.has(animal):
				var alarm: Dictionary = animal_alarm[animal]
				if clock < float(alarm.until):
					goal = animal.global_position + (animal.global_position - Vector3(alarm.point)).normalized() * 4.0
				else:
					animal_alarm.erase(animal)
			_walk(animal, goal - animal.global_position, dt, false)
	if host:
		if player.scattered_now:
			release()
			return
		left -= dt
		if left <= 0.0:
			release()
			return
		var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		var direction := Basis(Vector3.UP, player._yaw) * Vector3(input.x, 0, input.y)
		_walk(host, direction, dt, true)
		if host is Npc and input.length() > 0.1:
			host._play_walk(1.6)
		player.gw.hud.hint("Possessing %s · %.1f s · G to release" % [_name(host), left])
		return
	var previous := target
	_find_target()
	if not target and previous:
		player.gw.hud.hint("")
	if target:
		player.gw.hud.hint("G / D-pad right · Possess %s" % _name(target))


func _name(node: Node3D) -> String:
	if node is Npc:
		return String(node.data.get("name", node.id))
	for h in player.level.hauntables.values():
		if h.root == node:
			return String(h.kind).capitalize()
	return String(node.name)


func _walk(node: Node3D, vector: Vector3, dt: float, controlled: bool) -> void:
	vector.y = 0.0
	if vector.length() < 0.04:
		return
	var direction := vector.normalized()
	node.rotation.y = atan2(-direction.x, -direction.z)
	if controlled and rooted:
		return
	var start := node.global_position
	var next := start + direction * minf(vector.length(), dt * (1.6 if controlled else 0.65))
	if controlled and next.distance_to(player.global_position) > 8.0:
		return
	var floor_y := player.world.ground_below(next + Vector3.UP * 0.55)
	if absf(floor_y - start.y) > 0.65:
		return
	var ray := player.world.raycast(start + Vector3.UP * 0.25, direction, next.distance_to(start) + 0.17, true)
	if not ray.get("hit", false):
		node.global_position = Vector3(next.x, floor_y, next.z)


func _find_target() -> void:
	target = null
	var ray := player.aim_ray()
	var origin: Vector3 = ray[0]
	var direction: Vector3 = ray[1]
	var best := deg_to_rad(13.0)
	for index in LABELS.size():
		if not Game.ability_unlocked(LABELS[index]):
			continue
		var candidates: Array = []
		match index:
			0:
				for h in player.level.hauntables.values():
					if h.kind in ["doll", "scarecrow"]:
						candidates.append(h.root)
			1:
				candidates.append_array(animals)
			2:
				for n: Npc in player.gw.npcs:
					if _villager_eligible(n):
						candidates.append(n)
		for node: Node3D in candidates:
			if not node.is_visible_in_tree() or clock < float(cooldowns.get(node, 0.0)):
				continue
			var point := (node as Npc).head_pos() if node is Npc else node.global_position + Vector3.UP * (1.15 if _name(node) == "Scarecrow" else 0.35)
			if point.distance_to(player.global_position) > 4.0:
				continue
			var offset := point - origin
			var angle := direction.angle_to(offset)
			if angle >= best:
				continue
			if player.world.raycast(origin, offset.normalized(), maxf(0.0, offset.length() - 0.18), true).get("hit", false):
				continue
			best = angle
			target = node
			target_tier = index


func _villager_eligible(n: Npc) -> bool:
	var threshold := ScareMath.stage_from(String(Game.tuning.d("scare.boo").get("needs_stage", "primed")), Game.tuning.a("scare.stages"))
	if not n.available_to_chat() or not n.is_target() or not n.is_awake() or n.mind.frac() < threshold or n.mind.frac() >= 1.0:
		return false
	for other: Npc in player.gw.npcs:
		if other != n and other.visible and other.is_awake() and other.global_position.distance_to(n.global_position) < Game.tuning.f("scare.vulnerability.alone_radius_m", 10.0):
			return false
	return true


func toggle() -> void:
	if host:
		release()
		return
	_find_target()
	if not target:
		return
	host = target
	tier = target_tier
	left = DURATION[tier]
	home = host.global_transform
	acted = false
	rooted = tier == 0 and _name(host) == "Scarecrow"
	if host is Npc:
		host.possessed = true
	player.model.hide()
	player._clear_sprint_taps()


func startle_animals(point: Vector3, radius: float) -> void:
	for animal in animals:
		if animal.global_position.distance_to(point) <= radius:
			animal_alarm[animal] = {"point": point, "until": clock + 4.0}
			Sfx.play_at("dog_bark" if animal.name == "Dog" else "cat_hiss", animal.global_position)


func _effect(point: Vector3, color: Color, duration: float) -> MeshInstance3D:
	var effect := MeshInstance3D.new()
	effect.mesh = SphereMesh.new()
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color
	effect.material_override = material
	add_child(effect)
	effect.global_position = point
	effect.scale = Vector3.ONE * 0.12
	var animation := effect.create_tween()
	animation.tween_property(effect, "scale", Vector3(0.7, 0.24, 0.8), duration)
	animation.tween_callback(effect.queue_free)
	return effect


func action() -> void:
	if not host or acted:
		return
	acted = true
	var point := host.global_position
	var source := _name(host)
	if host is Npc:
		var rest_x := host.rotation.x
		var motion := host.create_tween()
		motion.tween_property(host, "rotation:x", rest_x + 0.35, 0.22)
		motion.tween_property(host, "rotation:x", rest_x, 0.5)
		_effect(host.head_pos() - Vector3.UP * 0.35 + host.forward * 0.32, Color.YELLOW_GREEN, 0.7)
		Sfx.play_at("gasp", host.head_pos(), -1.0)
	if tier == 0:
		var rest := host.rotation
		var tw := host.create_tween()
		tw.tween_property(host, "rotation", rest + Vector3(0.4, 0, 0), 0.11)
		tw.tween_property(host, "rotation", rest, 0.22)
	var sound := "creak_floor" if tier == 0 else ("dog_bark" if host.name == "Dog" else "cat_hiss")
	if not host is Npc:
		Sfx.play_at(sound, point)
	player.gw.director.possession_scare(point, source, 22.0, host as Npc)
	if Game.ability_unlocked("aftershock"):
		var echo := _effect(point + Vector3.UP * 0.5, Color.MEDIUM_PURPLE, 2.2)
		echo.create_tween().tween_interval(2.0).finished.connect(func() -> void:
			Sfx.play_at("whoosh", point)
			player.gw.director.possession_scare(point, source + "_aftershock", 11.0))


func release() -> void:
	if not host:
		return
	cooldowns[host] = clock + 30.0
	if host is Npc:
		host.possessed = false
		host._rejoin()
		if acted:
			host.say("What happened to me?")
			player.gw.director.possession_scare(host.global_position, "released_host", 18.0, null, host)
	elif tier == 0:
		host.global_transform = home
	host = null
	target = null
	player.model.show()
	player.gw.hud.hint("")
