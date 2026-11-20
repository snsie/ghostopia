## Builds the initial unit buffer from a population JSON (clans with formation rects): a solid block
## per clan, front rank toward the enemy, centred, skipping cells the clan can't stand on.
class_name CrowdSpawner
extends RefCounted

const L := preload("res://scripts/battle/crowd_layout.gd")


## Returns {units, starts, sizes, ids, walkers}. `scale` shrinks every clan's count (CPU fallback).
static func spawn(pop: Dictionary, terrain: BattleTerrain, p: CrowdParams, seed: int, scale: float = 1.0) -> Dictionary:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var units := PackedFloat32Array()
	var starts := PackedInt32Array()
	var sizes := PackedInt32Array()
	var ids: Array[String] = []
	var walkers: Array[bool] = []
	var clans: Array = pop.get("clans", [])
	for ci in clans.size():
		var cd: Dictionary = clans[ci]
		ids.append(String(cd["id"]))
		walkers.append(bool(cd.get("water_walker", false)))
	for ci in clans.size():
		var cd: Dictionary = clans[ci]
		var want := maxi(1, roundi(float(cd.get("count", 100)) * scale))
		var f: Dictionary = cd.get("formation", {})
		var rect: Array = f.get("rect", [0, 0, 10, 10])
		var sp := float(f.get("spacing_m", 1.15))
		var yaw := deg_to_rad(float(f.get("facing_yaw", 0.0)))
		var front_z := float(rect[3]) if cos(yaw) > 0.0 else float(rect[1])
		var cx := (float(rect[0]) + float(rect[2])) * 0.5
		var slots: Array = []
		var z := float(rect[1]) + sp * 0.5
		while z < float(rect[3]):
			var x := float(rect[0]) + sp * 0.5
			while x < float(rect[2]):
				slots.append(Vector3(x, z, absf(x - cx) * 0.45 + absf(z - front_z)))
				x += sp
			z += sp
		slots.sort_custom(func(a: Vector3, b: Vector3) -> bool: return a.z < b.z)
		starts.append(units.size() / L.STRIDE)
		var placed := 0
		for s: Vector3 in slots:
			if placed >= want:
				break
			var px := s.x + rng.randf_range(-0.15, 0.15)
			var pz := s.y + rng.randf_range(-0.15, 0.15)
			if not terrain.in_grid(px, pz):
				continue
			var c := terrain.cell(px, pz)
			if terrain.flags[c] & (L.T_BLOCKED | L.T_WATER):
				continue
			var u := L.blank()
			u[L.PX] = px
			u[L.PZ] = pz
			u[L.FORM] = p.form
			u[L.RESOLVE] = p.resolve * rng.randf_range(0.85, 1.0)
			u[L.CLAN] = float(ci)
			u[L.STATE] = float(L.FIGHT)
			u[L.ATTACK_CD] = rng.randf_range(0.0, p.attack_cd)
			u[L.SEED] = rng.randf()
			u[L.ANIM_T] = u[L.SEED]
			u[L.YAW] = yaw
			u[L.PY] = terrain.heights[c]
			u[L.STATE_T] = 1.0
			u[L.CLIP] = float(L.CLIP_IDLE)
			units.append_array(u)
			placed += 1
		sizes.append(placed)
	return {"units": units, "starts": starts, "sizes": sizes, "ids": ids, "walkers": walkers}
