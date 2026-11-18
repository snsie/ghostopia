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


func action() -> void:
	if not host or acted:
		return
	acted = true
	var point := host.global_position
	if host is Npc:
		host.say("What was that?!")
		return
	if tier == 0:
		var rest := host.rotation
		var tw := host.create_tween()
		tw.tween_property(host, "rotation", rest + Vector3(0.4, 0, 0), 0.11)
		tw.tween_property(host, "rotation", rest, 0.22)
	var sound := "creak_floor" if tier == 0 else ("dog_bark" if host.name == "Dog" else "cat_hiss")
	Sfx.play_at(sound, point)
	for n: Npc in player.gw.npcs:
		if n.global_position.distance_to(point) < 5.0:
			n.investigate(point)


func release() -> void:
	if not host:
		return
	cooldowns[host] = clock + 30.0
	if host is Npc:
		host.possessed = false
		host._rejoin()
	elif tier == 0:
		host.global_transform = home
	host = null
	target = null
	player.model.show()
	player.gw.hud.hint("")
