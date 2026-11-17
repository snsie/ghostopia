## Memory fragment drops (memory_fragments.json drop_tables): roll the block's chance, then pick by
## weight among fragments not yet collected, x3 for entries whose `areas` include the mining area.
class_name FragmentRoller
extends RefCounted

const AREA_MULT := 3.0

var tables: Dictionary = {}
var fragments: Dictionary = {}   # id -> fragment


func setup(fragment_json: Dictionary) -> void:
	tables = fragment_json.get("drop_tables", {})
	for f in fragment_json.get("fragments", []):
		fragments[f["id"]] = f


## `chance_override` < 0 uses the table's chance (gathering nodes pass their own).
func roll(block_id: String, area: String, collected: Dictionary, rng: RandomNumberGenerator,
		chance_mult: float = 1.0, chance_override: float = -1.0) -> String:
	var t: Dictionary = tables.get(block_id, {})
	if t.is_empty():
		return ""
	var chance := float(t.get("chance", 0.0)) if chance_override < 0.0 else chance_override
	if rng.randf() > chance * chance_mult:
		return ""
	return pick(block_id, area, collected, rng)


func pick(block_id: String, area: String, collected: Dictionary, rng: RandomNumberGenerator) -> String:
	var t: Dictionary = tables.get(block_id, {})
	var pool: Array = []
	var total := 0.0
	for e in t.get("entries", []):
		if collected.has(e["fragment"]):
			continue
		var w := float(e.get("weight", 1.0))
		if (e.get("areas", []) as Array).has(area):
			w *= AREA_MULT
		pool.append([e["fragment"], w])
		total += w
	if pool.is_empty():
		return ""
	var r := rng.randf() * total
	for p in pool:
		r -= float(p[1])
		if r <= 0.0:
			return String(p[0])
	return String(pool[-1][0])
