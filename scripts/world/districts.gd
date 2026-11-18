## Two outlying settlements, authored against Millbrook's base voxel layout.
extends RefCounted

const DISTRICTS := [
	{"id": "lantern_end", "name": "Lantern End", "x": 64, "z": 109, "y": 23,
		"residents": [["rowan", "Rowan", "dark"], ["ivy", "Ivy", "dolls"], ["nell", "Nell", "loud_noises"]]},
	{"id": "reedcross", "name": "Reedcross", "x": 129, "z": 124, "y": 21,
		"residents": [["moss", "Moss", "being_alone"], ["fern", "Fern", "dark"], ["bram", "Bram", "loud_noises"]]},
]

const HOUSES := [Vector2i(-8, -4), Vector2i(5, -5), Vector2i(5, 5)]


static func register(layout: Dictionary, population: Dictionary) -> void:
	var templates: Array = population.villagers.duplicate()
	var haunt_templates := {}
	for prop: Dictionary in population.hauntables:
		if not haunt_templates.has(prop.kind):
			haunt_templates[prop.kind] = prop
	for district: Dictionary in DISTRICTS:
		var x: int = district.x
		var y: int = district.y
		var z: int = district.z
		var id: String = district.id
		layout.areas.append({"id": id, "name": district.name, "rect": [x - 11, z - 9, x + 11, z + 10],
			"priority": 40, "remembrance": 0.6})
		for i in district.residents.size():
			var resident: Array = district.residents[i]
			var lot: Vector2i = HOUSES[i]
			var door_at := [x + lot.x + 2.5, y, z + lot.y + 4.0]
			var porch := [door_at[0], y, door_at[2] + 1.25]
			var plaza := [x - 1.5 + i, y, z + 1.5]
			var npc: Dictionary = templates[i].duplicate(true)
			npc.merge({"id": resident[0], "name": resident[1], "role": "target", "fear": resident[2],
				"home": id, "home_marker": resident[0] + "_home", "fear_story": "I keep thinking about what lurks beyond the village.",
				"mutter": "", "mutters": {"lines": ["Some nights the settlement feels watched.", "I never liked " + String(resident[2]).replace("_", " ") + "."], "radius_m": 6.0},
				"suspicious_reactions": [], "on_break": {}, "on_botch": {},
				"schedule": [
					{"kind": "stay", "t_start": 0.0, "t_end": 0.12, "pos": porch, "animation": "idle"},
					{"kind": "walk", "t_start": 0.12, "t_end": 0.126, "route": [porch, plaza], "speed_mps": 1.2},
					{"kind": "stay", "t_start": 0.126, "t_end": 0.38, "pos": plaza, "animation": "idle", "yaw": float(i * 100)},
					{"kind": "walk", "t_start": 0.38, "t_end": 0.386, "route": [plaza, porch], "speed_mps": 1.2},
					{"kind": "stay", "t_start": 0.386, "t_end": 1.0, "pos": porch, "animation": "idle"},
				]}, true)
			population.villagers.append(npc)
			layout.markers.append({"id": npc.home_marker, "kind": "villager_home", "pos": porch})
			_add_prop(layout, population, haunt_templates, "door", id + "_door_" + str(i), door_at, "door_cottage")
			_add_prop(layout, population, haunt_templates, "lantern", id + "_light_" + str(i), [x - 2 + i * 2, y, z - 1], "lantern")
		_add_prop(layout, population, haunt_templates, "bell", id + "_bell", [x, y, z + 3], "bell")
		_add_prop(layout, population, haunt_templates, "doll", id + "_doll", [x - 3, y, z + 2], "cloth_doll")


static func _add_prop(layout: Dictionary, population: Dictionary, templates: Dictionary, kind: String, id: String, point: Array, model: String) -> void:
	var path := "res://assets/props/%s.gltf" % model
	if not ResourceLoader.exists(path) or not templates.has(kind):
		return
	layout.instances.append({"id": id, "prop": model, "gltf": path, "pos": point, "yaw": 0.0})
	var data: Dictionary = templates[kind].duplicate(true)
	data.merge({"id": id, "instance": id, "source": "layout", "pos": point, "slice_active": true}, true)
	population.hauntables.append(data)


static func build(world: VoxelWorld) -> void:
	var path := world.reg.index_of("cobble_path")
	var wall := world.reg.index_of("timber_planks")
	var roof := world.reg.index_of("slate_roof")
	for district: Dictionary in DISTRICTS:
		var origin := Vector3i(district.x, district.y, district.z)
		for x in range(-10, 11):
			for z in range(-8, 10):
				for dy in range(-4, 1):
					world.set_block(origin + Vector3i(x, dy - 1, z), path)
				for y in range(0, 8):
					world.set_block(origin + Vector3i(x, y, z), 0)
		for lot: Vector2i in HOUSES:
			for x in 5:
				for z in 5:
					var cell := origin + Vector3i(lot.x + x, 0, lot.y + z)
					world.set_block(cell + Vector3i(0, -1, 0), wall)
					if x in [0, 4] or z in [0, 4]:
						for y in 3:
							if not (x == 2 and z == 4 and y < 2):
								world.set_block(cell + Vector3i(0, y, 0), wall)
					world.set_block(cell + Vector3i(0, 3 + mini(x, 4 - x), 0), roof)
	world.original = world.vox.duplicate()
	world.edits.clear()
