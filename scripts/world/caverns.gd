## Authored pockets cut into the base island before player edits are applied.
extends Node3D

const ROOMS := [
	{"name": "Fungal Grotto", "id": "fungal_grotto", "center": Vector3i(53, 13, 89), "surface": 22,
		"color": Color(0.21, 0.92, 0.75), "resident": "Spore Keeper", "enemy": "Territorial wisp",
		"line": "The wisps guard the bright caps. Walk the edges and they will let you pass.", "notes": [110.0, 164.81, 196.0]},
	{"name": "Flooded Ossuary", "id": "flooded_ossuary", "center": Vector3i(108, 12, 103), "surface": 21,
		"color": Color(1.0, 0.61, 0.23), "resident": "Ferryman", "enemy": "Drowned shade",
		"line": "The drowned follow anything that moves. Keep the boat lantern behind you.", "notes": [73.42, 110.0, 146.83]},
	{"name": "Crystal Hollow", "id": "crystal_hollow", "center": Vector3i(146, 12, 115), "surface": 22,
		"color": Color(0.66, 0.37, 1.0), "resident": "Prospector", "enemy": "Crystal sentinel",
		"line": "Stand still when the crystals wake. They listen for footsteps.", "notes": [130.81, 195.99, 261.63]},
]

var game_world: Node
var active := -1
var enemies: Array[Node3D] = []
var fragments: Array[Node3D] = []
var attack_time := 0.0
var recovery := 0.0


static func carve(world: VoxelWorld) -> void:
	for room in ROOMS:
		var c: Vector3i = room.center
		for x in range(-6, 7):
			for z in range(-5, 6):
				var distance := Vector2(x / 6.0, z / 5.0).length()
				if distance > 1.04:
					continue
				var height := 3 if distance > 0.73 else 4
				for y in range(height):
					world.set_block(c + Vector3i(x, y, z), 0)
				var floor_id := "mossy_stone_bricks" if room.id == "fungal_grotto" else "spectral_stone"
				world.set_block(c + Vector3i(x, -1, z), world.reg.index_of(floor_id))
				if room.id == "flooded_ossuary" and z > 1:
					world.set_block(c + Vector3i(x, 0, z), world.reg.index_of("still_water"))
		for y in range(c.y, int(room.surface)):
			for x in range(-1, 2):
				world.set_block(Vector3i(c.x + x, y, c.z - 3), 0)
		world.set_block(Vector3i(c.x, room.surface - 1, c.z - 3), world.reg.index_of("dirt"))
	world.original = world.vox.duplicate()
	world.edits.clear()


func setup(gw: Node) -> void:
	game_world = gw
	for i in ROOMS.size():
		var room: Dictionary = ROOMS[i]
		var c := Vector3(room.center) + Vector3(0.5, 0, 0.5)
		var color: Color = room.color
		var entrance := Vector3(c.x, room.surface + 0.15, c.z - 3.0)
		_label(room.name + "\nQ · Enter", entrance + Vector3.UP * 0.65, color)
		_label("Q · Return to the surface", c + Vector3(0, 1.6, -3), color)
		_label(room.resident, c + Vector3(-3, 1.5, 0), color)
		_shape(c + Vector3(-3, 0.55, 0), Vector3(0.65, 1.1, 0.65), color, 0)
		_light(c + Vector3(0, 2.4, 0), color, 7.0)
		for j in 6:
			var angle := j * TAU / 6.0
			var point := c + Vector3(cos(angle) * 4.0, 0.4, sin(angle) * 3.0)
			if i == 0:
				var stem_height := 0.45 + float(j % 3) * 0.23
				_shape(point, Vector3(0.16, stem_height, 0.16), color.darkened(0.25), 1)
				_shape(point + Vector3.UP * stem_height * 0.48, Vector3(0.85, 0.28, 0.85), color, 0)
			elif i == 1:
				_shape(point, Vector3(0.48, 0.9 + float(j % 3) * 0.26, 0.48), color.darkened(0.45), 1)
				_shape(point + Vector3.UP * 0.58, Vector3(0.33, 0.37, 0.33), color.lightened(0.3), 0)
			else:
				var crystal := _shape(point, Vector3(0.48, 0.95 + float(j % 3) * 0.4, 0.48), color, 2)
				crystal.rotation.z = sin(angle) * 0.24
			_light(point + Vector3.UP * 0.3, color, 2.5)
		var enemy := _shape(c + Vector3(1.5, 0.88, 1.6), Vector3(0.55, 0.72, 0.55), color.darkened(0.18), i)
		enemies.append(enemy)
		fragments.append(_shape(c + Vector3(3.2, 1.0, 0), Vector3(0.30, 0.48, 0.30), color.lightened(0.45), 2))
		Sfx.register_stream(room.id, _music(room.notes))


func _shape(point: Vector3, size: Vector3, color: Color, style: int) -> MeshInstance3D:
	var item := MeshInstance3D.new()
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = 0.55
	match style:
		0: item.mesh = SphereMesh.new()
		1: item.mesh = BoxMesh.new()
		2:
			var prism := CylinderMesh.new()
			prism.top_radius = 0.0
			prism.radial_segments = 5
			item.mesh = prism
	item.material_override = material
	item.scale = size
	add_child(item)
	item.position = point
	return item


func _label(words: String, point: Vector3, color: Color) -> void:
	var label := Label3D.new()
	label.text = words
	label.modulate = color
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.pixel_size = 0.005
	add_child(label)
	label.position = point


func _light(point: Vector3, color: Color, radius: float) -> void:
	var light := OmniLight3D.new()
	light.light_color = color
	light.light_energy = 1.2
	light.omni_range = radius
	add_child(light)
	light.position = point


func room_at(point: Vector3) -> int:
	for i in ROOMS.size():
		var c := Vector3(ROOMS[i].center)
		if AABB(c - Vector3(6, 0.8, 5), Vector3(13, 5.5, 11)).has_point(point):
			return i
	return -1


func interact() -> bool:
	var player: Player = game_world.player
	for room in ROOMS:
		var c := Vector3(room.center) + Vector3(0.5, 0, 0.5)
		var entrance := Vector3(c.x, room.surface + 0.15, c.z - 3)
		var exit := c + Vector3(0, 0.9, -3)
		if player.global_position.distance_to(entrance) < 2.4:
			player.teleport(exit, 180.0)
			return true
		if player.global_position.distance_to(exit) < 2.0:
			player.teleport(entrance + Vector3(1.9, 0.9, 0), 180.0)
			return true
		if player.global_position.distance_to(c + Vector3(-3, 0.8, 0)) < 2.1:
			game_world.hud.toast("%s: %s" % [room.resident, room.line], "info")
			return true
	return false


func tick(dt: float) -> void:
	var player: Player = game_world.player
	var pos := player.global_position
	var index := room_at(pos)
	if index != active:
		attack_time = 0.0
		recovery = 0.65
		active = index
		if index >= 0:
			game_world.hud.toast(ROOMS[index].name, "info")
	for i in fragments.size():
		fragments[i].visible = not Game.fragments.has(ROOMS[i].id)
		fragments[i].rotate_y(dt * 0.65)
	if index < 0 or player.scattered_now:
		return
	var room: Dictionary = ROOMS[index]
	var fragment := fragments[index]
	if fragment.visible and pos.distance_to(fragment.global_position) < 1.05:
		Game.collect_fragment(room.id)
	var enemy := enemies[index]
	var center := Vector3(room.center) + Vector3(0.5, 0.88, 0.5)
	var goal := Vector3(pos.x, center.y, pos.z)
	var distance := enemy.global_position.distance_to(pos)
	var triggered := (index == 0 and pos.distance_to(center) < 3.6) or index == 1 or (index == 2 and player.velocity.length() > 0.7)
	if attack_time > 0.0:
		enemy.material_override.emission_energy_multiplier = 1.4 + 0.5 * sin(attack_time * 29.0)
		attack_time -= dt
		if attack_time <= 0.0:
			enemy.material_override.emission_energy_multiplier = 0.55
			if distance < 1.45:
				Game.hp = maxf(0.0, Game.hp - (1.0 + index * 0.5))
				Sfx.play("hurt")
			recovery = 1.4
		return
	recovery = maxf(0.0, recovery - dt)
	if triggered:
		enemy.global_position = enemy.global_position.move_toward(goal, dt * (0.75 + index * 0.22))
		if distance < 1.3 and recovery == 0.0:
			attack_time = 0.65
			game_world.hud.hint("%s is about to strike!" % room.enemy)
			Sfx.play_at("whoosh", enemy.global_position)
	else:
		enemy.global_position = enemy.global_position.move_toward(center + Vector3(1.5, 0, 1.6), dt * 0.55)


func _music(frequencies: Array) -> AudioStreamWAV:
	var rate := 16000
	var samples := rate * 8
	var data := PackedByteArray()
	data.resize(samples * 2)
	for i in samples:
		var t := float(i) / rate
		var sample := 0.0
		for j in frequencies.size():
			var frequency := roundf(frequencies[j] * 8.0) / 8.0
			sample += sin(TAU * frequency * t) * (0.45 + 0.35 * cos(TAU * (j + 1) * t / 8.0))
		data.encode_s16(i * 2, int(sample * 1750.0))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = rate
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	stream.loop_end = samples
	stream.data = data
	return stream
