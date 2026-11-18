## The voxel island: loads millbrook_voxels.bin, meshes 16^3 chunks on WorkerThreadPool, builds
## per-chunk collision (non-phaseable blocks on layer 1, phaseable on layer 2), the running-water
## spirit barrier (layer 5), block edits that remesh only the touched chunks, DDA raycasts and
## the per-area Remembrance texture the voxel shader fades with.
class_name VoxelWorld
extends Node3D

signal built(stats: Dictionary)

const L_SOLID := 1        # bit values
const L_PHASE := 2
const L_PROP_PHASE := 4
const L_PROP_SOLID := 8
const L_BARRIER := 16
const L_ACTORS := 64

var reg: BlockRegistry
var size := Vector3i(192, 48, 192)
var chunks := Vector3i(12, 3, 12)
var vox := PackedByteArray()
var original := PackedByteArray()
var edits: Dictionary = {}          # cell index -> block index (differences from the file)
var jitter := 0.035

var mat_opaque: ShaderMaterial
var mat_plants: ShaderMaterial
var mat_water: ShaderMaterial
var remembrance_img: Image
var remembrance_tex: ImageTexture

var _chunk_nodes: Dictionary = {}   # Vector3i -> {mesh: MeshInstance3D, solid: StaticBody3D, phase: StaticBody3D}
var _dirty: Dictionary = {}
var _results: Array = []
var _mutex := Mutex.new()
var _jobs: Array[Vector3i] = []
var _barrier: StaticBody3D
var _surface_cache := PackedInt32Array()


func load_level(layout: Dictionary, registry: BlockRegistry, jitter_m: float) -> void:
	reg = registry
	jitter = jitter_m
	var w: Dictionary = layout["world"]
	size = Vector3i(int(w["size"][0]), int(w["size"][1]), int(w["size"][2]))
	chunks = Vector3i(ceili(size.x / 16.0), ceili(size.y / 16.0), ceili(size.z / 16.0))
	var bytes := FileAccess.get_file_as_bytes(String(w["voxels"]["path"]))
	vox = bytes.decompress_dynamic(-1, FileAccess.COMPRESSION_GZIP)
	if vox.size() != size.x * size.y * size.z:
		push_error("VoxelWorld: voxel file has %d cells, expected %d" % [vox.size(), size.x * size.y * size.z])
	original = vox.duplicate()
	_make_materials()
	_compute_surface()


func _make_materials() -> void:
	var albedo: TextureLayered = load("res://assets/blocks/blocks_atlas.png")
	var normal: TextureLayered = load("res://assets/blocks/blocks_normal.png")
	var emission: TextureLayered = load("res://assets/blocks/blocks_emission.png")
	remembrance_img = Image.create(size.x, size.z, false, Image.FORMAT_R8)
	remembrance_img.fill(Color(1, 1, 1))
	remembrance_tex = ImageTexture.create_from_image(remembrance_img)
	mat_opaque = ShaderMaterial.new()
	mat_opaque.shader = load("res://shaders/voxel.gdshader")
	mat_plants = ShaderMaterial.new()
	mat_plants.shader = load("res://shaders/voxel_plants.gdshader")
	mat_water = ShaderMaterial.new()
	mat_water.shader = load("res://shaders/voxel_water.gdshader")
	for m: ShaderMaterial in [mat_opaque, mat_plants, mat_water]:
		m.set_shader_parameter("albedo_tex", albedo)
		m.set_shader_parameter("remembrance_tex", remembrance_tex)
		m.set_shader_parameter("world_size", Vector2(size.x, size.z))
	mat_opaque.set_shader_parameter("normal_tex", normal)
	mat_opaque.set_shader_parameter("emission_tex", emission)


func set_remembrance(areas: Array, values: Dictionary, fading_below: float, faded_at: float) -> void:
	# Paint each area's rect, lowest priority first, so the highest priority wins where they overlap.
	var sorted := areas.duplicate()
	sorted.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return int(a.get("priority", 0)) < int(b.get("priority", 0)))
	for a in sorted:
		var r: Array = a["rect"]
		var v := float(values.get(a["id"], 1.0))
		var rect := Rect2i(int(r[0]), int(r[1]), int(r[2]) - int(r[0]), int(r[3]) - int(r[1]))
		remembrance_img.fill_rect(rect, Color(v, v, v))
	remembrance_tex.update(remembrance_img)
	for m: ShaderMaterial in [mat_opaque, mat_plants, mat_water]:
		m.set_shader_parameter("fading_below", fading_below)
		m.set_shader_parameter("faded_at", faded_at)


func idx(x: int, y: int, z: int) -> int:
	return x + size.x * (z + size.z * y)


func in_bounds(x: int, y: int, z: int) -> bool:
	return x >= 0 and y >= 0 and z >= 0 and x < size.x and y < size.y and z < size.z


func get_block(x: int, y: int, z: int) -> int:
	if not in_bounds(x, y, z):
		return 0
	return vox[idx(x, y, z)]


func get_block_v(c: Vector3i) -> int:
	return get_block(c.x, c.y, c.z)


func cell_of(p: Vector3) -> Vector3i:
	return Vector3i(floori(p.x), floori(p.y), floori(p.z))


func set_block(c: Vector3i, b: int) -> void:
	if not in_bounds(c.x, c.y, c.z):
		return
	var i := idx(c.x, c.y, c.z)
	vox[i] = b
	if original[i] == b:
		edits.erase(i)
	else:
		edits[i] = b
	_compute_surface_column(c.x, c.z)
	var cp := Vector3i(c.x >> 4, c.y >> 4, c.z >> 4)
	_dirty[cp] = true
	for ax in 3:
		var l := c[ax] & 15
		if l == 0:
			var n := cp
			n[ax] -= 1
			_dirty[n] = true
		elif l == 15:
			var n2 := cp
			n2[ax] += 1
			_dirty[n2] = true


func apply_edits(saved: Dictionary) -> void:
	vox = original.duplicate()
	edits.clear()
	for k: String in saved:
		var i := int(k)
		var b := int(saved[k])
		if i >= 0 and i < vox.size():
			vox[i] = b
			edits[i] = b
	_compute_surface()
	for cp: Vector3i in _all_chunk_coords():
		_dirty[cp] = true


func edits_for_save() -> Dictionary:
	var out := {}
	for i: int in edits:
		out[str(i)] = edits[i]
	return out


func _all_chunk_coords() -> Array[Vector3i]:
	var out: Array[Vector3i] = []
	for cy in chunks.y:
		for cz in chunks.z:
			for cx in chunks.x:
				out.append(Vector3i(cx, cy, cz))
	return out


func _chunk_has_content(cp: Vector3i) -> bool:
	for y in range(cp.y * 16, mini(cp.y * 16 + 16, size.y)):
		for z in range(cp.z * 16, mini(cp.z * 16 + 16, size.z)):
			var row := size.x * (z + size.z * y)
			for x in range(cp.x * 16, mini(cp.x * 16 + 16, size.x)):
				if vox[row + x] != 0:
					return true
	return false


## Meshes every chunk on the worker pool, then creates the nodes. Returns timing stats.
func build_all() -> Dictionary:
	var t0 := Time.get_ticks_usec()
	_jobs.clear()
	for cp in _all_chunk_coords():
		if _chunk_has_content(cp):
			_jobs.append(cp)
	_results.resize(_jobs.size())
	var tid := WorkerThreadPool.add_group_task(_mesh_job, _jobs.size(), -1, true, "chunk meshing")
	WorkerThreadPool.wait_for_group_task_completion(tid)
	var t1 := Time.get_ticks_usec()
	var faces := 0
	for k in _jobs.size():
		faces += _apply_chunk(_jobs[k], _results[k])
	_results.clear()
	var t2 := Time.get_ticks_usec()
	_build_barrier()
	var stats := {"chunks": _jobs.size(), "mesh_ms": (t1 - t0) / 1000.0, "nodes_ms": (t2 - t1) / 1000.0,
		"faces": faces, "threads": OS.get_processor_count()}
	built.emit(stats)
	return stats


func _mesh_job(k: int) -> void:
	var res := ChunkMesher.build(vox, size, _jobs[k], reg, jitter)
	_mutex.lock()
	_results[k] = res
	_mutex.unlock()


func _process(_dt: float) -> void:
	if _dirty.is_empty():
		return
	var keys := _dirty.keys()
	_dirty.clear()
	for cp: Vector3i in keys:
		if cp.x < 0 or cp.y < 0 or cp.z < 0 or cp.x >= chunks.x or cp.y >= chunks.y or cp.z >= chunks.z:
			continue
		_apply_chunk(cp, ChunkMesher.build(vox, size, cp, reg, jitter))


func remesh_now() -> void:
	_process(0.0)


func _apply_chunk(cp: Vector3i, res: Dictionary) -> int:
	var nodes: Dictionary = _chunk_nodes.get(cp, {})
	if nodes.is_empty():
		var mi := MeshInstance3D.new()
		mi.name = "chunk_%d_%d_%d" % [cp.x, cp.y, cp.z]
		mi.position = Vector3(cp * 16)
		add_child(mi)
		var sb := StaticBody3D.new()
		sb.collision_layer = L_SOLID
		sb.collision_mask = 0
		mi.add_child(sb)
		var cs := CollisionShape3D.new()
		sb.add_child(cs)
		var pb := StaticBody3D.new()
		pb.collision_layer = L_PHASE
		pb.collision_mask = 0
		mi.add_child(pb)
		var cs2 := CollisionShape3D.new()
		pb.add_child(cs2)
		nodes = {"mesh": mi, "solid": cs, "phase": cs2}
		_chunk_nodes[cp] = nodes
	var mesh := ArrayMesh.new()
	var faces := 0
	for pair in [["opaque", mat_opaque], ["plants", mat_plants], ["water", mat_water]]:
		var arr: Array = res.get(pair[0], [])
		if arr.is_empty():
			continue
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		mesh.surface_set_material(mesh.get_surface_count() - 1, pair[1])
		faces += (arr[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 6
	(nodes["mesh"] as MeshInstance3D).mesh = mesh if mesh.get_surface_count() > 0 else null
	for pair in [["col_solid", "solid"], ["col_phase", "phase"]]:
		var tris: PackedVector3Array = res.get(pair[0], PackedVector3Array())
		var cs: CollisionShape3D = nodes[pair[1]]
		if tris.is_empty():
			cs.shape = null
			cs.disabled = true
		else:
			var sh := ConcavePolygonShape3D.new()
			sh.backface_collision = true
			sh.set_faces(tris)
			cs.shape = sh
			cs.disabled = false
	return faces


## Running water is a wall for spirits: one tall box per run of stream cells along z, except where a
## bridge deck covers the water.
func _build_barrier() -> void:
	if _barrier:
		_barrier.queue_free()
	_barrier = StaticBody3D.new()
	_barrier.name = "SpiritBarrier"
	_barrier.collision_layer = L_BARRIER
	_barrier.collision_mask = 0
	add_child(_barrier)
	var cols: Dictionary = {}   # Vector2i -> [ymin, ymax]
	for i in vox.size():
		if reg.running[vox[i]] == 1:
			var x := i % size.x
			var z := (i / size.x) % size.z
			var y := i / (size.x * size.z)
			var key := Vector2i(x, z)
			var cur: Array = cols.get(key, [y, y])
			cols[key] = [mini(cur[0], y), maxi(cur[1], y)]
	var boxes := 0
	for key: Vector2i in cols:
		var ymin: int = cols[key][0]
		var ymax: int = cols[key][1]
		var bridged := false
		for dy in range(1, 4):
			var b := get_block(key.x, ymax + dy, key.y)
			if reg.solid[b] == 1:
				bridged = true
		if bridged:
			continue
		var cs := CollisionShape3D.new()
		var box := BoxShape3D.new()
		var h := float(ymax - ymin) + 1.0 + 3.0 + 12.0
		box.size = Vector3(1.0, h, 1.0)
		cs.shape = box
		cs.position = Vector3(key.x + 0.5, ymin - 3.0 + h * 0.5, key.y + 0.5)
		_barrier.add_child(cs)
		boxes += 1


func _compute_surface() -> void:
	_surface_cache.resize(size.x * size.z)
	for z in size.z:
		for x in size.x:
			_compute_surface_column(x, z)


func _compute_surface_column(x: int, z: int) -> void:
	var top := -1
	for y in range(size.y - 1, -1, -1):
		var b := vox[idx(x, y, z)]
		if reg.solid[b] == 1 or reg.liquid[b] == 1:
			top = y
			break
	_surface_cache[x + size.x * z] = top


## Highest solid or liquid cell in a column (-1 if none).
func surface_y(x: int, z: int) -> int:
	if x < 0 or z < 0 or x >= size.x or z >= size.z:
		return -1
	return _surface_cache[x + size.x * z]


## Y of the top of the first solid (or liquid) cell at or below `p` (p.y - 30 if none).
func ground_below(p: Vector3, include_liquid: bool = true) -> float:
	var c := cell_of(p)
	if c.x < 0 or c.z < 0 or c.x >= size.x or c.z >= size.z:
		return p.y - 30.0
	for y in range(mini(c.y, size.y - 1), -1, -1):
		var b := vox[idx(c.x, y, c.z)]
		if reg.solid[b] == 1 or (include_liquid and reg.liquid[b] == 1):
			return float(y + 1)
	return p.y - 30.0


## Count of natural solid blocks above `p` (underground check for daylight).
func natural_cover(p: Vector3, limit: int = 24) -> int:
	var c := cell_of(p)
	var n := 0
	for y in range(c.y + 1, mini(c.y + 1 + limit, size.y)):
		var b := get_block(c.x, y, c.z)
		if reg.solid[b] == 1 and reg.natural[b] == 1:
			n += 1
	return n


## Any solid block above `p` within `limit` cells (roofs count).
func roofed(p: Vector3, limit: int = 12) -> bool:
	var c := cell_of(p)
	for y in range(c.y + 1, mini(c.y + 1 + limit, size.y)):
		if reg.opaque[get_block(c.x, y, c.z)] == 1:
			return true
	return false


## Voxel DDA. Returns {hit, cell, normal, block, dist}. Skips air and liquids; plants count.
func raycast(from: Vector3, dir: Vector3, max_dist: float, solid_only := false) -> Dictionary:
	dir = dir.normalized()
	var c := cell_of(from)
	var step := Vector3i(signi(int(signf(dir.x))), signi(int(signf(dir.y))), signi(int(signf(dir.z))))
	var t_max := Vector3.ZERO
	var t_delta := Vector3.ZERO
	for ax in 3:
		if absf(dir[ax]) < 1e-9:
			t_max[ax] = INF
			t_delta[ax] = INF
		else:
			var nb := float(c[ax] + (1 if step[ax] > 0 else 0))
			t_max[ax] = (nb - from[ax]) / dir[ax]
			t_delta[ax] = absf(1.0 / dir[ax])
	var normal := Vector3i.ZERO
	var t := 0.0
	while t <= max_dist:
		var b := get_block_v(c)
		if b != 0 and reg.liquid[b] == 0 and (not solid_only or reg.solid[b] == 1):
			return {"hit": true, "cell": c, "normal": normal, "block": b, "dist": t}
		var ax := 0
		if t_max.y < t_max[ax]:
			ax = 1
		if t_max.z < t_max[ax]:
			ax = 2
		t = t_max[ax]
		t_max[ax] += t_delta[ax]
		c[ax] += step[ax]
		normal = Vector3i.ZERO
		normal[ax] = -step[ax]
	return {"hit": false}


## The task3 water cells' flow is (nearly) north to south; the shader scrolls along +Z.
func set_mood_emission(strength: float) -> void:
	mat_opaque.set_shader_parameter("emission_strength", strength)
