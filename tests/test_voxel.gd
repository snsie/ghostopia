## Task5 voxel mesher and world: face culling, collision layers for phaseable vs solid blocks,
## raycasts, edits and the full island build (timing printed for decisions.md).
extends "res://tests/framework/test_case.gd"

const BlocksS := preload("res://scripts/voxel/block_registry.gd")
const MesherS := preload("res://scripts/voxel/chunk_mesher.gd")
const WorldS := preload("res://scripts/voxel/voxel_world.gd")

var _b: BlocksS


func before_each() -> void:
	_b = BlocksS.load_file()


func _tiny(cells: Dictionary) -> PackedByteArray:
	var v := PackedByteArray()
	v.resize(16 * 16 * 16)
	for c: Vector3i in cells:
		v[c.x + 16 * (c.z + 16 * c.y)] = _b.index_of(cells[c])
	return v


func _faces(arr: Array) -> int:
	return 0 if arr.is_empty() else (arr[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 6


func test_single_block_has_six_faces() -> void:
	var r := MesherS.build(_tiny({Vector3i(5, 5, 5): "stone"}), Vector3i(16, 16, 16), Vector3i.ZERO, _b, 0.0)
	assert_eq(_faces(r["opaque"]), 6)
	assert_eq((r["col_solid"] as PackedVector3Array).size(), 36, "6 faces x 2 triangles x 3 verts")
	assert_eq((r["col_phase"] as PackedVector3Array).size(), 0)


func test_neighbours_cull_shared_faces() -> void:
	var r := MesherS.build(_tiny({Vector3i(5, 5, 5): "stone", Vector3i(6, 5, 5): "stone"}), Vector3i(16, 16, 16), Vector3i.ZERO, _b, 0.0)
	assert_eq(_faces(r["opaque"]), 10)


func test_phaseable_blocks_collide_on_their_own_layer() -> void:
	var r := MesherS.build(_tiny({Vector3i(5, 5, 5): "stone", Vector3i(6, 5, 5): "dirt"}), Vector3i(16, 16, 16), Vector3i.ZERO, _b, 0.0)
	# Stone keeps the face toward the dirt (the ghost inside the dirt still hits the stone).
	assert_eq((r["col_solid"] as PackedVector3Array).size(), 36)
	assert_eq((r["col_phase"] as PackedVector3Array).size(), 30, "dirt: 5 faces, none toward the stone")


func test_plants_and_water_go_to_their_passes() -> void:
	var r := MesherS.build(_tiny({Vector3i(2, 2, 2): "wheat", Vector3i(8, 2, 8): "river_water"}), Vector3i(16, 16, 16), Vector3i.ZERO, _b, 0.0)
	assert_eq(_faces(r["opaque"]), 0)
	assert_eq(_faces(r["plants"]), 2, "two crossed quads")
	assert_eq(_faces(r["water"]), 6)
	assert_eq((r["col_solid"] as PackedVector3Array).size(), 0, "water and plants have no collision")


func test_front_faces_point_outward() -> void:
	var r := MesherS.build(_tiny({Vector3i(5, 5, 5): "stone"}), Vector3i(16, 16, 16), Vector3i.ZERO, _b, 0.0)
	var a: Array = r["opaque"]
	var v: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	var n: PackedVector3Array = a[Mesh.ARRAY_NORMAL]
	var ind: PackedInt32Array = a[Mesh.ARRAY_INDEX]
	for t in range(0, ind.size(), 3):
		var cr := (v[ind[t + 1]] - v[ind[t]]).cross(v[ind[t + 2]] - v[ind[t]])
		assert_true(cr.dot(n[ind[t]]) < 0.0, "clockwise seen from outside (Godot front face)")


func _world() -> WorldS:
	var w := WorldS.new()
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/levels/millbrook_layout.json"))
	w.load_level(layout, _b, 0.03)
	return w


func test_raycast_and_ground() -> void:
	var w := _world()
	add_to_tree(w)
	var spawn := Vector3(28.1, 28.0, 92.5)
	var g := w.ground_below(spawn + Vector3(0, 2, 0))
	assert_almost_eq(g, 28.0, 0.01, "ground at the mausoleum door")
	var hit := w.raycast(spawn + Vector3(0, 3, 0), Vector3.DOWN, 10.0)
	assert_true(hit["hit"])
	assert_eq((hit["normal"] as Vector3i), Vector3i(0, 1, 0))
	assert_eq((hit["cell"] as Vector3i).y, 27)


func test_edits_roundtrip() -> void:
	var w := _world()
	add_to_tree(w)
	var c := Vector3i(30, 27, 100)
	var before := w.get_block_v(c)
	w.set_block(c, 0)
	assert_eq(w.get_block_v(c), 0)
	var saved := w.edits_for_save()
	assert_eq(saved.size(), 1)
	w.set_block(c, before)
	assert_eq(w.edits_for_save().size(), 0, "putting the block back clears the edit")
	w.apply_edits(saved)
	assert_eq(w.get_block_v(c), 0)


func test_full_island_build() -> void:
	var w := _world()
	add_to_tree(w)
	var stats := w.build_all()
	print("   island build: %d chunks, %d faces, meshing %.0f ms on %d threads, nodes %.0f ms" % [
		stats["chunks"], stats["faces"], stats["mesh_ms"], stats["threads"], stats["nodes_ms"]])
	assert_true(int(stats["chunks"]) > 100)
	assert_true(int(stats["faces"]) > 20000)
	assert_true(w.get_node_or_null("SpiritBarrier").get_child_count() > 20, "running water barrier built")
