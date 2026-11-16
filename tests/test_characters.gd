## Task2 characters: every glTF loads, has its skeleton, sockets, expressions and the clips from task2.md,
## and characters.json agrees with the files.
extends "res://tests/framework/test_case.gd"

const DIR := "res://assets/characters/"
const VILLAGER_CLIPS := ["idle", "walk", "walk_uneasy", "look_over_shoulder", "call_out", "clutch_candle_walk",
	"startle", "big_scare_leap", "flee", "laugh_it_off", "suspicious_search", "hang_charm", "scatter_salt",
	"relight_candle", "sit", "rock_in_chair", "sleep", "sweep", "work_field", "serve_drinks"]
const GHOST_CLIPS := ["idle_float", "drift", "glide_down", "ascend", "phase", "swing_scythe", "dig_shovel",
	"smash_hammer", "haunt_cast", "boo", "hurt", "scatter", "celebrate"]
const WORKER_CLIPS := ["idle_float", "carry", "work"]
const VILLAGER_BONES := ["root", "hips", "spine", "chest", "neck", "head", "hat", "shoulder_L", "upperarm_L",
	"forearm_L", "hand_L", "shoulder_R", "upperarm_R", "forearm_R", "hand_R", "thigh_L", "shin_L", "foot_L",
	"thigh_R", "shin_R", "foot_R"]


func _manifest() -> Dictionary:
	var f := FileAccess.open(DIR + "characters.json", FileAccess.READ)
	return JSON.parse_string(f.get_as_text())["characters"]


func _load(name: String) -> Node3D:
	var scene := load(DIR + name + ".gltf") as PackedScene
	assert_true(scene != null, "%s.gltf should import as a scene" % name)
	return add_to_tree(scene.instantiate()) as Node3D


func _anim_names(root: Node) -> Array:
	var ap := root.find_children("*", "AnimationPlayer", true, false)
	assert_eq(ap.size(), 1, "one AnimationPlayer")
	return Array((ap[0] as AnimationPlayer).get_animation_list())


func _skeleton(root: Node) -> Skeleton3D:
	var sk := root.find_children("*", "Skeleton3D", true, false)
	assert_eq(sk.size(), 1, "one Skeleton3D")
	return sk[0] as Skeleton3D


func _blend_shapes(root: Node, mesh_name: String) -> Array:
	var out := []
	var node := root.find_child(mesh_name, true, false) as MeshInstance3D
	assert_true(node != null, "mesh %s" % mesh_name)
	if node:
		for i in node.mesh.get_blend_shape_count():
			out.append(String(node.mesh.get_blend_shape_name(i)))
	return out


func test_manifest_lists_nine_characters() -> void:
	var m := _manifest()
	assert_eq(m.size(), 9)
	for n in ["ghost", "worker_blacksmith", "worker_gardener", "worker_baker", "villager_widow",
			"villager_farmer", "villager_maid", "villager_teacher", "villager_child"]:
		assert_true(m.has(n), "manifest has %s" % n)


func test_ghost() -> void:
	var g := _load("ghost")
	var clips := _anim_names(g)
	for c in GHOST_CLIPS:
		assert_has(clips, c)
	assert_eq(_skeleton(g).get_bone_count(), 13)
	assert_true(g.find_child("HELD_tool", true, false) != null, "HELD_tool socket")
	assert_true(g.find_child("MATERIAL_manifest", true, false) != null, "manifest material holder")
	var shapes := _blend_shapes(g, "ghost_eyes")
	for e in ["angry", "scared", "happy", "closed"]:
		assert_has(shapes, e)


func test_workers() -> void:
	for w in ["worker_blacksmith", "worker_gardener", "worker_baker"]:
		var n := _load(w)
		var clips := _anim_names(n)
		for c in WORKER_CLIPS:
			assert_has(clips, c)
		for s in ["HELD_R", "HELD_L", "HELD_block"]:
			assert_true(n.find_child(s, true, false) != null, "%s %s" % [w, s])


func test_villagers_share_one_skeleton_and_all_clips() -> void:
	var m := _manifest()
	for v in ["widow", "farmer", "maid", "teacher", "child"]:
		var name: String = "villager_" + v
		var n := _load(name)
		var sk := _skeleton(n)
		assert_eq(sk.get_bone_count(), VILLAGER_BONES.size(), name)
		for b in VILLAGER_BONES:
			assert_true(sk.find_bone(b) >= 0, "%s bone %s" % [name, b])
		var clips := _anim_names(n)
		for c in VILLAGER_CLIPS:
			assert_has(clips, c)
		for s in ["HELD_R", "HELD_L"]:
			assert_true(n.find_child(s, true, false) != null, "%s %s" % [name, s])
		var shapes := _blend_shapes(n, name + "_face")
		for e in ["uneasy", "scared", "terrified", "relieved"]:
			assert_has(shapes, e)
		var info: Dictionary = m[name]
		for c in ["walk", "walk_uneasy", "clutch_candle_walk", "flee"]:
			assert_true(float(info["no_slide_speed_mps"][c]) > 0.2, "%s %s speed" % [name, c])


func test_villagers_fit_the_door() -> void:
	# task1: door openings are 1 x 2 blocks; the tallest villager (farmer with hat) must pass under 2 m
	var m := _manifest()
	for v in ["widow", "farmer", "maid", "teacher", "child"]:
		var info: Dictionary = m["villager_" + v]
		assert_true(float(info["head_top"]) < 2.0, v)
