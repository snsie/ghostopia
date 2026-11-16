## Task3 island: millbrook_layout.json and millbrook_voxels.bin load the way the game will read them,
## and the data keeps its contracts (markers, grounded props, water, spawn, lighting).
extends "res://tests/framework/test_case.gd"

const LAYOUT := "res://assets/levels/millbrook_layout.json"
const RESIDENTS := ["agnes", "pip", "marlow", "wren", "bram"]
const PLANTS := ["air", "tall_grass", "flowers", "wheat"]

var _layout: Dictionary
var _vox: PackedByteArray
var _palette: Array
var _size: Array


func before_each() -> void:
	_layout = JSON.parse_string(FileAccess.get_file_as_string(LAYOUT))
	var w: Dictionary = _layout["world"]
	_size = w["size"]
	_palette = w["palette"]
	var raw := FileAccess.get_file_as_bytes(w["voxels"]["path"])
	_vox = raw.decompress_dynamic(-1, FileAccess.COMPRESSION_GZIP)


func _block(x: int, y: int, z: int) -> String:
	var sx: int = _size[0]
	var sy: int = _size[1]
	var sz: int = _size[2]
	if x < 0 or y < 0 or z < 0 or x >= sx or y >= sy or z >= sz:
		return "air"
	var id = _palette[_vox[x + sx * (z + sz * y)]]
	return "air" if id == null else String(id)


func _stands_free(p: Array) -> bool:
	## The cell at p is open (air or a plant) and the cell below is solid ground.
	var x := int(floor(p[0]))
	var y := int(round(p[1]))
	var z := int(floor(p[2]))
	return _block(x, y, z) in PLANTS and not (_block(x, y - 1, z) in PLANTS)


func test_voxels_decompress_to_world_size() -> void:
	assert_eq(_vox.size(), int(_size[0]) * int(_size[1]) * int(_size[2]))
	assert_eq(int(_layout["world"]["chunk_size"]), 16)


func test_palette_matches_blocks_json() -> void:
	var doc: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/blocks/blocks.json"))
	for b in doc["blocks"]:
		assert_eq(String(_palette[int(b["index"])]), String(b["id"]), "palette index %d" % int(b["index"]))


func test_required_markers() -> void:
	var ids := {}
	var kinds := {}
	for m in _layout["markers"]:
		assert_false(ids.has(m["id"]), "unique marker id %s" % m["id"])
		ids[m["id"]] = m
		kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
	for id in ["player_start", "respawn", "shelter_mausoleum", "work_well", "work_tavern_bar", "work_mill",
			"work_field_1"]:
		assert_true(ids.has(id), "marker %s" % id)
	for r in RESIDENTS:
		for pre in ["villager_home_", "bed_", "door_"]:
			var found := false
			for id in ids:
				if String(id).begins_with(pre + r):
					found = true
			assert_true(found, "%s%s" % [pre, r])
	for k in ["chair", "hearth", "wander", "window", "hiding_spot", "ore_node", "grave_node", "weed_node", "shelter"]:
		assert_true(kinds.get(k, 0) > 0, "marker kind %s" % k)


func test_spawn_and_outdoor_markers_stand_on_ground() -> void:
	var start: Dictionary
	for m in _layout["markers"]:
		if m["kind"] == "player_start":
			start = m
		if m["kind"] in ["wander", "player_start", "grave_node", "work"] and m["owner"] in ["village", "fields", "square", "graveyard", "mausoleum"]:
			assert_true(_stands_free(m["pos"]), "%s at %s" % [m["id"], str(m["pos"])])
	assert_eq(String(start["area"]), "graveyard")


func test_standalone_props_are_grounded() -> void:
	var structs := {}
	for s in _layout["structures"]:
		structs[s["id"]] = true
	for i in _layout["instances"]:
		assert_true(String(i["gltf"]).begins_with("res://assets/props/"), i["id"])
		if structs.has(i["owner"]):
			continue
		assert_true(_stands_free(i["pos"]), "%s at %s" % [i["id"], str(i["pos"])])


func test_stream_cells_are_running_water() -> void:
	var stream: Dictionary = _layout["water"][0]
	assert_true(stream["running_water"])
	assert_true(stream["cells"].size() > 300)
	for c in stream["cells"]:
		assert_eq(_block(int(c[0]), int(c[1]), int(c[2])), "river_water")


func test_lighting_presets() -> void:
	var presets: Dictionary = _layout["lighting"]["presets"]
	for p in ["night", "dusk", "day", "fading"]:
		assert_true(presets.has(p), "preset %s" % p)
		assert_true(presets[p].has("fog") and presets[p].has("sky") and presets[p].has("ambient"), p)
	assert_false(presets["day"]["emission"]["windows"])
	assert_true(presets["night"]["emission"]["windows"])
	assert_true(float(presets["fading"]["saturation"]) < 0.5)
	assert_true(_layout["lighting"]["cycle"]["keys"].size() >= 6)


func test_kill_y_below_the_island() -> void:
	assert_true(float(_layout["kill_y"]) < float(_layout["world"]["void_level"]))
