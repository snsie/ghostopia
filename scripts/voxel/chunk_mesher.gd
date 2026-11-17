## Builds the mesh and collision faces of one 16^3 chunk from the voxel array. Pure and thread-safe
## (reads only), so the world runs it on WorkerThreadPool.
##
## Output surfaces: opaque cubes (face culling, per-vertex AO, atlas layer in UV2.x, slight vertex
## jitter so blocks look hand-made), cross plants (double-sided), water (transparent, top lowered).
## Collision: faces of non-phaseable solids (the ghost's walls) and of phaseable solids (camera,
## villagers, raycasts) as separate triangle lists.
class_name ChunkMesher
extends RefCounted

const CHUNK := 16
const WATER_TOP := 0.86

# Face order: +X, -X, +Y, -Y, +Z, -Z
const NORMALS: Array[Vector3i] = [Vector3i(1, 0, 0), Vector3i(-1, 0, 0), Vector3i(0, 1, 0), Vector3i(0, -1, 0),
	Vector3i(0, 0, 1), Vector3i(0, 0, -1)]
const SHADE := [0.86, 0.86, 1.0, 0.62, 0.93, 0.93]   # cheap directional shade baked in vertex colour
const AO_LEVELS := [0.5, 0.68, 0.84, 1.0]

static var _corners: Array = []      # per face: 4 Vector3 corners (clockwise seen from outside)
static var _uvs: Array = []          # per face: 4 Vector2
static var _tangents: Array = []     # per face: Plane(tangent, w)
static var _ao_axes: Array = []      # per face: [axis_a: Vector3i, axis_b: Vector3i]


static func _static_init() -> void:
	var raw := [
		[Vector3(1, 1, 1), Vector3(1, 1, 0), Vector3(1, 0, 0), Vector3(1, 0, 1)],
		[Vector3(0, 1, 0), Vector3(0, 1, 1), Vector3(0, 0, 1), Vector3(0, 0, 0)],
		[Vector3(0, 1, 0), Vector3(1, 1, 0), Vector3(1, 1, 1), Vector3(0, 1, 1)],
		[Vector3(0, 0, 1), Vector3(1, 0, 1), Vector3(1, 0, 0), Vector3(0, 0, 0)],
		[Vector3(0, 1, 1), Vector3(1, 1, 1), Vector3(1, 0, 1), Vector3(0, 0, 1)],
		[Vector3(1, 1, 0), Vector3(0, 1, 0), Vector3(0, 0, 0), Vector3(1, 0, 0)],
	]
	for f in 6:
		var n := Vector3(NORMALS[f])
		var c: Array = raw[f]
		# Godot front faces are clockwise seen from outside: cross(e1, e2) points away from the normal.
		if (c[1] - c[0]).cross(c[2] - c[0]).dot(n) > 0.0:
			c = [c[0], c[3], c[2], c[1]]
		_corners.append(c)
		var uv: Array = []
		var t := Vector3.ZERO
		if f == 2 or f == 3:
			t = Vector3(1, 0, 0)
			for p: Vector3 in c:
				uv.append(Vector2(p.x, p.z if f == 2 else 1.0 - p.z))
		else:
			var right := (-n).cross(Vector3.UP)
			t = right
			for p: Vector3 in c:
				var u := p.dot(right)
				if right.x < 0.0 or right.z < 0.0:
					u += 1.0
				uv.append(Vector2(u, 1.0 - p.y))
		_uvs.append(uv)
		# Image "up" (-v) is the binormal for OpenGL-style normal maps.
		var up_dir := Vector3(0, 0, -1) if f == 2 else (Vector3(0, 0, 1) if f == 3 else Vector3.UP)
		var w := 1.0 if n.cross(t).dot(up_dir) >= 0.0 else -1.0
		_tangents.append(Plane(t, w))
		var axes: Array[Vector3i] = []
		for ax: Vector3i in [Vector3i(1, 0, 0), Vector3i(0, 1, 0), Vector3i(0, 0, 1)]:
			if absf(Vector3(ax).dot(Vector3(NORMALS[f]))) < 0.5:
				axes.append(ax)
		_ao_axes.append(axes)


## `vox` world voxels (x fastest, then z, then y), `size` world size in cells, `cpos` chunk coords.
static func build(vox: PackedByteArray, size: Vector3i, cpos: Vector3i, reg: BlockRegistry, jitter: float) -> Dictionary:
	var sx := size.x
	var sz := size.z
	var sxz := sx * sz
	var x0 := cpos.x * CHUNK
	var y0 := cpos.y * CHUNK
	var z0 := cpos.z * CHUNK
	var opaque := reg.opaque
	var solid := reg.solid
	var phase := reg.phaseable
	var crossb := reg.cross
	var liquid := reg.liquid

	var o := _Surf.new()
	var pl := _Surf.new()
	var wa := _Surf.new()
	var col_solid := PackedVector3Array()
	var col_phase := PackedVector3Array()
	var origin := Vector3(x0, y0, z0)

	for y in range(y0, mini(y0 + CHUNK, size.y)):
		for z in range(z0, mini(z0 + CHUNK, sz)):
			var row := sx * (z + sz * y)
			for x in range(x0, mini(x0 + CHUNK, sx)):
				var b := vox[row + x]
				if b == 0:
					continue
				var lp := Vector3(x - x0, y - y0, z - z0)
				if crossb[b] == 1:
					_add_cross(pl, lp, reg.tiles_side[b], x, y, z)
					continue
				var is_liq := liquid[b] == 1
				var is_solid := solid[b] == 1
				var is_phase := phase[b] == 1
				for f in 6:
					var nd: Vector3i = NORMALS[f]
					var nx := x + nd.x
					var ny := y + nd.y
					var nz := z + nd.z
					var nb := 0
					if nx >= 0 and nx < sx and ny >= 0 and ny < size.y and nz >= 0 and nz < sz:
						nb = vox[nx + sx * (nz + sz * ny)]
					# collision
					if is_solid:
						if not is_phase:
							if not (solid[nb] == 1 and phase[nb] == 0):
								_add_col(col_solid, lp, f)
						elif solid[nb] == 0:
							_add_col(col_phase, lp, f)
					# visible faces
					if is_liq:
						if nb == b or opaque[nb] == 1:
							continue
						if f != 2 and liquid[nb] == 1:
							continue
						_add_face(wa, lp, f, reg.tiles_side[b], Color(1, 1, 1, 1), true, x, y, z, 0.0, vox, size, opaque, false)
						continue
					if opaque[nb] == 1:
						continue
					if nb == b and opaque[b] == 0:
						continue   # leaves next to leaves
					var tile := reg.tiles_side[b]
					if f == 2:
						tile = reg.tiles_top[b]
					elif f == 3:
						tile = reg.tiles_bottom[b]
					elif f == 4 and reg.tiles_front[b] >= 0:
						tile = reg.tiles_front[b]
					var h := _hash3(x, y, z)
					var tint := 0.95 + 0.1 * float(h & 255) / 255.0
					var emis := 1.0 if reg.emissive[b] == 1 else 0.0
					_add_face(o, lp, f, tile, Color(tint, tint, tint, 1), false, x, y, z, emis, vox, size, opaque, true, jitter, origin)
	return {"opaque": o.arrays(), "plants": pl.arrays(), "water": wa.arrays(),
		"col_solid": col_solid, "col_phase": col_phase}


static func _hash3(x: int, y: int, z: int) -> int:
	var h := x * 73856093 ^ y * 19349663 ^ z * 83492791
	h = (h ^ (h >> 13)) * 1274126177
	return absi(h ^ (h >> 16))


static func _jitter_at(wx: int, wy: int, wz: int, amount: float) -> Vector3:
	if amount <= 0.0:
		return Vector3.ZERO
	var h := _hash3(wx, wy, wz)
	return Vector3(float(h & 1023) / 1023.0 - 0.5, float((h >> 10) & 1023) / 1023.0 - 0.5,
		float((h >> 20) & 1023) / 1023.0 - 0.5) * (2.0 * amount)


static func _is_opaque_at(vox: PackedByteArray, size: Vector3i, opaque: PackedByteArray, x: int, y: int, z: int) -> int:
	if x < 0 or y < 0 or z < 0 or x >= size.x or y >= size.y or z >= size.z:
		return 0
	return opaque[vox[x + size.x * (z + size.z * y)]]


static func _add_face(s: _Surf, lp: Vector3, f: int, tile: int, tint: Color, water: bool, x: int, y: int, z: int,
		emis: float, vox: PackedByteArray, size: Vector3i, opaque: PackedByteArray, ao: bool,
		jitter: float = 0.0, origin: Vector3 = Vector3.ZERO) -> void:
	var corners: Array = _corners[f]
	var uvs: Array = _uvs[f]
	var n := Vector3(NORMALS[f])
	var base := s.verts.size()
	var aos: Array[int] = [3, 3, 3, 3]
	if ao:
		var axes: Array = _ao_axes[f]
		var a: Vector3i = axes[0]
		var b: Vector3i = axes[1]
		var out := Vector3i(x, y, z) + NORMALS[f]
		for k in 4:
			var c: Vector3 = corners[k]
			var ca := Vector3(a).dot(c)
			var cb := Vector3(b).dot(c)
			var sa := a if ca > 0.5 else -a
			var sb := b if cb > 0.5 else -b
			var p1 := out + sa
			var p2 := out + sb
			var p3 := out + sa + sb
			var s1 := _is_opaque_at(vox, size, opaque, p1.x, p1.y, p1.z)
			var s2 := _is_opaque_at(vox, size, opaque, p2.x, p2.y, p2.z)
			var s3 := _is_opaque_at(vox, size, opaque, p3.x, p3.y, p3.z)
			aos[k] = 0 if (s1 == 1 and s2 == 1) else 3 - (s1 + s2 + s3)
	var shade: float = SHADE[f]
	for k in 4:
		var c: Vector3 = corners[k]
		var p := lp + c
		if water and f != 3 and c.y > 0.5:
			p.y = lp.y + WATER_TOP
		if jitter > 0.0:
			p += _jitter_at(int(origin.x + p.x), int(origin.y + p.y), int(origin.z + p.z), jitter)
		s.verts.append(p)
		s.normals.append(n)
		s.tangents.append_array(PackedFloat32Array([_tangents[f].normal.x, _tangents[f].normal.y, _tangents[f].normal.z, _tangents[f].d]))
		s.uvs.append(uvs[k])
		s.uv2s.append(Vector2(tile, emis))
		var l: float = AO_LEVELS[aos[k]] * shade
		s.colors.append(Color(tint.r * l, tint.g * l, tint.b * l, 1.0))
	if aos[0] + aos[2] < aos[1] + aos[3]:
		s.indices.append_array(PackedInt32Array([base + 1, base + 2, base + 3, base + 1, base + 3, base]))
	else:
		s.indices.append_array(PackedInt32Array([base, base + 1, base + 2, base, base + 2, base + 3]))


static func _add_cross(s: _Surf, lp: Vector3, tile: int, x: int, y: int, z: int) -> void:
	var h := _hash3(x, y, z)
	var off := Vector3(float(h & 255) / 255.0 - 0.5, 0.0, float((h >> 8) & 255) / 255.0 - 0.5) * 0.25
	var quads := [[Vector3(0.12, 0, 0.12), Vector3(0.88, 0, 0.88)], [Vector3(0.88, 0, 0.12), Vector3(0.12, 0, 0.88)]]
	for q in quads:
		var a: Vector3 = lp + q[0] + off
		var b: Vector3 = lp + q[1] + off
		var base := s.verts.size()
		var pts := [a + Vector3(0, 1, 0), b + Vector3(0, 1, 0), b, a]
		var uv := [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)]
		var n := (b - a).cross(Vector3.UP).normalized()
		for k in 4:
			s.verts.append(pts[k])
			s.normals.append(Vector3.UP.lerp(n, 0.3).normalized())
			s.tangents.append_array(PackedFloat32Array([1, 0, 0, 1]))
			s.uvs.append(uv[k])
			s.uv2s.append(Vector2(tile, 0.0))
			var top := 1.0 if k < 2 else 0.0
			s.colors.append(Color(0.75 + 0.25 * top, 0.75 + 0.25 * top, 0.75 + 0.25 * top, top))
		s.indices.append_array(PackedInt32Array([base, base + 1, base + 2, base, base + 2, base + 3]))


static func _add_col(arr: PackedVector3Array, lp: Vector3, f: int) -> void:
	var c: Array = _corners[f]
	arr.append(lp + c[0]); arr.append(lp + c[1]); arr.append(lp + c[2])
	arr.append(lp + c[0]); arr.append(lp + c[2]); arr.append(lp + c[3])


class _Surf:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var tangents := PackedFloat32Array()
	var colors := PackedColorArray()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var indices := PackedInt32Array()

	func arrays() -> Array:
		if verts.is_empty():
			return []
		var a := []
		a.resize(Mesh.ARRAY_MAX)
		a[Mesh.ARRAY_VERTEX] = verts
		a[Mesh.ARRAY_NORMAL] = normals
		a[Mesh.ARRAY_TANGENT] = tangents
		a[Mesh.ARRAY_COLOR] = colors
		a[Mesh.ARRAY_TEX_UV] = uvs
		a[Mesh.ARRAY_TEX_UV2] = uv2s
		a[Mesh.ARRAY_INDEX] = indices
		return a
