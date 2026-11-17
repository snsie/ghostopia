## Loads assets/data/tuning.json (every feel number of the slice) and reads values by path.
## Pure: no scene access, so tests can load it.
class_name Tuning
extends RefCounted

const PATH := "res://assets/data/tuning.json"

var data: Dictionary = {}


static func load_file(path: String = PATH) -> Tuning:
	var t := Tuning.new()
	var text := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if parsed is Dictionary:
		t.data = parsed
	else:
		push_error("Tuning: could not parse %s" % path)
	return t


static func from_dict(d: Dictionary) -> Tuning:
	var t := Tuning.new()
	t.data = d
	return t


## Value at a dotted path ("player.hp_base"), or `fallback` when any key is missing.
func get_value(path: String, fallback: Variant = null) -> Variant:
	var cur: Variant = data
	for key in path.split("."):
		if cur is Dictionary and (cur as Dictionary).has(key):
			cur = cur[key]
		elif cur is Array and key.is_valid_int() and int(key) < (cur as Array).size():
			cur = cur[int(key)]
		else:
			return fallback
	return cur


func f(path: String, fallback: float = 0.0) -> float:
	var v: Variant = get_value(path, fallback)
	return float(v) if (v is float or v is int) else fallback


func i(path: String, fallback: int = 0) -> int:
	var v: Variant = get_value(path, fallback)
	return int(v) if (v is float or v is int) else fallback


func d(path: String) -> Dictionary:
	var v: Variant = get_value(path, {})
	return v if v is Dictionary else {}


func a(path: String) -> Array:
	var v: Variant = get_value(path, [])
	return v if v is Array else []


## Level row (from a `levels` array with a `fright` threshold) reached with `fright` points.
func level_for(path: String, fright: float) -> Dictionary:
	var best: Dictionary = {}
	for row in a(path):
		if fright >= float(row.get("fright", 0)) and not row.get("slice_locked", false):
			best = row
	return best


## The next level row above `fright`, or {} at the top.
func next_level(path: String, fright: float) -> Dictionary:
	for row in a(path):
		if fright < float(row.get("fright", 0)):
			return row
	return {}
