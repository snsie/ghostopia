## A* over standable voxel cells (solid below, two free cells for the body), 4-way moves with one
## step up or down. Used when a villager must leave its precomputed task4 route (fleeing home,
## rejoining the schedule after a scare).
class_name VoxelPath
extends RefCounted


static func standable(w: VoxelWorld, c: Vector3i) -> bool:
	var below := w.get_block(c.x, c.y - 1, c.z)
	if w.reg.solid[below] == 0:
		return false
	return w.reg.solid[w.get_block(c.x, c.y, c.z)] == 0 and w.reg.solid[w.get_block(c.x, c.y + 1, c.z)] == 0 \
		and w.reg.liquid[w.get_block(c.x, c.y, c.z)] == 0


## Nearest standable cell to `p` within a few cells (or p's cell).
static func snap(w: VoxelWorld, p: Vector3) -> Vector3i:
	var c := w.cell_of(p)
	for r in 3:
		for dy in [0, -1, 1, -2, 2]:
			for dx in range(-r, r + 1):
				for dz in range(-r, r + 1):
					var q := c + Vector3i(dx, dy, dz)
					if standable(w, q):
						return q
	return c


## World-space waypoints (cell centres at foot height) from a to b, or [] when not found.
static func find(w: VoxelWorld, from: Vector3, to: Vector3, max_nodes: int = 30000) -> PackedVector3Array:
	var a := snap(w, from)
	var b := snap(w, to)
	var open: Array = [[0.0, a]]
	var came := {a: a}
	var cost := {a: 0.0}
	var n := 0
	var found := false
	while not open.is_empty() and n < max_nodes:
		n += 1
		var best := 0
		for i in open.size():
			if float(open[i][0]) < float(open[best][0]):
				best = i
		var cur: Vector3i = open[best][1]
		open.remove_at(best)
		if cur == b:
			found = true
			break
		for d: Vector3i in [Vector3i(1, 0, 0), Vector3i(-1, 0, 0), Vector3i(0, 0, 1), Vector3i(0, 0, -1)]:
			for dy in [0, 1, -1]:
				var nx: Vector3i = cur + d + Vector3i(0, dy, 0)
				if dy == 1 and w.reg.solid[w.get_block(cur.x, cur.y + 2, cur.z)] == 1:
					continue
				if not standable(w, nx):
					continue
				var nc := float(cost[cur]) + 1.0 + (0.4 if dy != 0 else 0.0)
				if not cost.has(nx) or nc < float(cost[nx]):
					cost[nx] = nc
					came[nx] = cur
					open.append([nc + Vector3(nx - b).length(), nx])
				break
	if not found:
		return PackedVector3Array()
	var cells: Array[Vector3i] = [b]
	while cells[-1] != a:
		cells.append(came[cells[-1]])
	cells.reverse()
	var out := PackedVector3Array()
	for c in cells:
		out.append(Vector3(c.x + 0.5, c.y, c.z + 0.5))
	return out
