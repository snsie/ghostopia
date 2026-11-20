## The crowd's view of a battle region: a 1 m grid of stand heights and flags (blocked, running water,
## ford, clan homes) baked from the voxels, plus one flow field per clan goal (attack = toward the
## enemy's home, home = toward its own tunnel for routing units). Flow fields are Dijkstra distance
## fields turned into unit directions, baked once, so pathing cost doesn't grow with unit count.
class_name BattleTerrain
extends RefCounted

const L := preload("res://scripts/battle/crowd_layout.gd")
const INF_DIST := 1.0e9

var w := 0                            # cells along x
var h := 0                            # cells along z
var heights := PackedFloat32Array()   # stand height (y of the feet) per cell
var flags := PackedInt32Array()
var clan_count := 0
var water_walker: Array[bool] = []
var water_cost := 2.5
## fields[clan * 2 + 0] = attack, [clan * 2 + 1] = home: PackedFloat32Array of (dx, dz) per cell
var fields: Array[PackedFloat32Array] = []
var dists: Array[PackedFloat32Array] = []
var mid_x := 64.0


static func from_grid(p_w: int, p_h: int, p_heights: PackedFloat32Array, p_flags: PackedInt32Array) -> BattleTerrain:
	var t := BattleTerrain.new()
	t.w = p_w
	t.h = p_h
	t.heights = p_heights
	t.flags = p_flags
	t.mid_x = p_w * 0.5
	return t


## Bakes the grid from a VoxelWorld-style buffer (x fastest, then z, then y).
static func from_voxels(vox: PackedByteArray, size: Vector3i, reg: BlockRegistry, floor_y: int, ceiling_y: int) -> BattleTerrain:
	var t := BattleTerrain.new()
	t.w = size.x
	t.h = size.z
	t.mid_x = size.x * 0.5
	t.heights.resize(t.w * t.h)
	t.flags.resize(t.w * t.h)
	var sxz := size.x * size.z
	for z in t.h:
		for x in t.w:
			var c := x + t.w * z
			var stand := -1
			var below := 0
			for y in range(maxi(1, floor_y - 3), ceiling_y - 2):
				var b := vox[x + size.x * z + sxz * y]
				if b != 0:
					continue
				var under := vox[x + size.x * z + sxz * (y - 1)]
				if under == 0:
					continue
				if vox[x + size.x * z + sxz * (y + 1)] != 0 or vox[x + size.x * z + sxz * (y + 2)] != 0:
					continue
				stand = y
				below = under
				break
			if stand < 0 or stand > floor_y + 3:
				t.flags[c] = L.T_BLOCKED
				t.heights[c] = float(floor_y)
				continue
			t.heights[c] = float(stand)
			if reg.running[below] == 1:
				t.flags[c] = L.T_WATER
			elif reg.liquid[below] == 1:
				t.flags[c] = L.T_FORD
	return t


func cell(x: float, z: float) -> int:
	var cx := clampi(floori(x), 0, w - 1)
	var cz := clampi(floori(z), 0, h - 1)
	return cx + w * cz


func in_grid(x: float, z: float) -> bool:
	return x >= 0.0 and z >= 0.0 and x < float(w) and z < float(h)


func passable(c: int, clan: int) -> bool:
	var f := flags[c]
	if f & L.T_BLOCKED:
		return false
	if f & L.T_WATER and not water_walker[clan]:
		return false
	return true


func passable_at(x: float, z: float, clan: int) -> bool:
	return in_grid(x, z) and passable(cell(x, z), clan)


func mark_home(clan: int, rect: Array) -> void:
	for z in range(int(rect[1]), int(rect[3])):
		for x in range(int(rect[0]), int(rect[2])):
			if x >= 0 and z >= 0 and x < w and z < h:
				flags[x + w * z] |= L.T_HOME0 << clan


func is_home(c: int, clan: int) -> bool:
	return (flags[c] & (L.T_HOME0 << clan)) != 0


## Sets the clans and bakes every flow field. The attack goal is "ford" (every clan converges on the
## contested ford cells, where the Memory Vein runs) or "enemy_home" (clan c marches on clan c+1's home).
func setup_clans(walkers: Array[bool], p_water_cost: float = 2.5, attack_goal: String = "ford") -> void:
	clan_count = walkers.size()
	water_walker = walkers
	water_cost = p_water_cost
	fields.clear()
	dists.clear()
	for c in clan_count:
		var enemy := (c + 1) % clan_count
		for k in 2:
			var goals := PackedInt32Array()
			for i in w * h:
				if not passable(i, c):
					continue
				if k == 0 and attack_goal == "ford":
					if flags[i] & L.T_FORD:
						goals.append(i)
				elif is_home(i, enemy if k == 0 else c):
					goals.append(i)
			var d := distance_field(goals, c)
			dists.append(d)
			fields.append(direction_field(d, c))


## Dijkstra from the goal cells over the cells clan `clan` can enter (8-connected, no corner
## cutting; running water costs `water_cost` for water walkers).
func distance_field(goals: PackedInt32Array, clan: int) -> PackedFloat32Array:
	var dist := PackedFloat32Array()
	dist.resize(w * h)
	dist.fill(INF_DIST)
	var heap := _Heap.new()
	for g in goals:
		dist[g] = 0.0
		heap.push(g, 0.0)
	var offs := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1),
		Vector2i(1, 1), Vector2i(1, -1), Vector2i(-1, 1), Vector2i(-1, -1)]
	while heap.size() > 0:
		var top := heap.pop()
		var c: int = top[0]
		var dc: float = top[1]
		if dc > dist[c]:
			continue
		var cx := c % w
		var cz := c / w
		for o: Vector2i in offs:
			var nx := cx + o.x
			var nz := cz + o.y
			if nx < 0 or nz < 0 or nx >= w or nz >= h:
				continue
			var n := nx + w * nz
			if not passable(n, clan):
				continue
			if o.x != 0 and o.y != 0:
				if not passable(cx + o.x + w * cz, clan) or not passable(cx + w * (cz + o.y), clan):
					continue
			var step := 1.41421 if (o.x != 0 and o.y != 0) else 1.0
			if flags[n] & L.T_WATER:
				step *= water_cost
			var nd := dc + step
			if nd < dist[n]:
				dist[n] = nd
				heap.push(n, nd)
	return dist


## Unit direction per cell: the cost-weighted sum of the steps toward lower-distance neighbours.
func direction_field(dist: PackedFloat32Array, clan: int) -> PackedFloat32Array:
	var dirs := PackedFloat32Array()
	dirs.resize(w * h * 2)
	for cz in h:
		for cx in w:
			var c := cx + w * cz
			var dc := dist[c]
			if dc >= INF_DIST or dc <= 0.0:
				continue
			var gx := 0.0
			var gz := 0.0
			var best := dc
			var bx := 0
			var bz := 0
			for oz in range(-1, 2):
				for ox in range(-1, 2):
					if ox == 0 and oz == 0:
						continue
					var nx := cx + ox
					var nz := cz + oz
					if nx < 0 or nz < 0 or nx >= w or nz >= h:
						continue
					var n := nx + w * nz
					if dist[n] >= dc or not passable(n, clan):
						continue
					if ox != 0 and oz != 0 and (not passable(cx + ox + w * cz, clan) or not passable(cx + w * (cz + oz), clan)):
						continue
					var len := 1.41421 if (ox != 0 and oz != 0) else 1.0
					var k := (dc - dist[n]) / len
					gx += ox / len * k
					gz += oz / len * k
					if dist[n] < best:
						best = dist[n]
						bx = ox
						bz = oz
			var l := sqrt(gx * gx + gz * gz)
			if l < 1e-5:
				# saddle: fall back to the steepest neighbour
				gx = bx
				gz = bz
				l = maxf(sqrt(gx * gx + gz * gz), 1e-5)
			dirs[c * 2] = gx / l
			dirs[c * 2 + 1] = gz / l
	return dirs


func flow(field: int, x: float, z: float) -> Vector2:
	var c := cell(x, z)
	var f := fields[field]
	return Vector2(f[c * 2], f[c * 2 + 1])


func dist_at(field: int, x: float, z: float) -> float:
	return dists[field][cell(x, z)]


## All fields packed one after another (for the GPU): [field][cell][dx, dz].
func packed_fields() -> PackedFloat32Array:
	var out := PackedFloat32Array()
	for f in fields:
		out.append_array(f)
	return out


class _Heap:
	var keys := PackedInt32Array()
	var pri := PackedFloat32Array()

	func size() -> int:
		return keys.size()

	func push(k: int, p: float) -> void:
		keys.append(k)
		pri.append(p)
		var i := keys.size() - 1
		while i > 0:
			var parent := (i - 1) >> 1
			if pri[parent] <= pri[i]:
				break
			_swap(i, parent)
			i = parent

	func pop() -> Array:
		var out := [keys[0], pri[0]]
		var last := keys.size() - 1
		keys[0] = keys[last]
		pri[0] = pri[last]
		keys.resize(last)
		pri.resize(last)
		var i := 0
		var n := last
		while true:
			var l := i * 2 + 1
			var r := l + 1
			var m := i
			if l < n and pri[l] < pri[m]:
				m = l
			if r < n and pri[r] < pri[m]:
				m = r
			if m == i:
				break
			_swap(i, m)
			i = m
		return out

	func _swap(a: int, b: int) -> void:
		var tk := keys[a]
		keys[a] = keys[b]
		keys[b] = tk
		var tp := pri[a]
		pri[a] = pri[b]
		pri[b] = tp
