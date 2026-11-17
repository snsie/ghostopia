## Block types from assets/blocks/blocks.json, indexed by their stable integer `index` (0 = air).
## Pure data + rules (tool/tier, phasing, drops); thread-safe reads for the mesher.
class_name BlockRegistry
extends RefCounted

const PATH := "res://assets/blocks/blocks.json"
const TOOLS := ["none", "scythe", "shovel", "sledgehammer"]

var blocks: Array[Dictionary] = []          # by index
var by_id: Dictionary = {}                  # id -> index
var tile_count: int = 0
var columns: int = 8

# Flat lookup tables by index (fast for meshing and physics).
var opaque := PackedByteArray()             # solid cube, not transparent: culls neighbours
var solid := PackedByteArray()              # has collision (cubes, not liquids, not cross plants)
var phaseable := PackedByteArray()          # the ghost passes through
var cross := PackedByteArray()              # crossed-quad plants
var liquid := PackedByteArray()
var running := PackedByteArray()            # running water: spirits can't cross
var natural := PackedByteArray()
var emissive := PackedByteArray()
var tiles_top := PackedInt32Array()
var tiles_side := PackedInt32Array()
var tiles_bottom := PackedInt32Array()
var tiles_front := PackedInt32Array()        # -1 when none


static func load_file(path: String = PATH) -> BlockRegistry:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	var r := BlockRegistry.new()
	if parsed is Dictionary:
		r._build(parsed)
	else:
		push_error("BlockRegistry: could not parse %s" % path)
	return r


func _build(json: Dictionary) -> void:
	var atlas: Dictionary = json.get("atlas", {})
	columns = int(atlas.get("columns", 8))
	tile_count = int(atlas.get("tile_count", 40))
	var list: Array = json.get("blocks", [])
	var n := 0
	for b in list:
		n = maxi(n, int(b.get("index", 0)) + 1)
	blocks.resize(n)
	for arr in [opaque, solid, phaseable, cross, liquid, running, natural, emissive]:
		arr.resize(n)
	for arr in [tiles_top, tiles_side, tiles_bottom, tiles_front]:
		arr.resize(n)
	for b in list:
		var idx := int(b.get("index", 0))
		blocks[idx] = b
		by_id[String(b["id"])] = idx
		var is_cross: bool = b.get("shape", "cube") == "cross"
		var is_liquid: bool = b.get("liquid", false)
		var is_solid: bool = b.get("solid", false) and not is_liquid and not is_cross
		cross[idx] = 1 if is_cross else 0
		liquid[idx] = 1 if is_liquid else 0
		solid[idx] = 1 if is_solid else 0
		opaque[idx] = 1 if (is_solid and not b.get("transparent", false)) else 0
		phaseable[idx] = 1 if b.get("phaseable", false) else 0
		running[idx] = 1 if b.get("running_water", false) else 0
		natural[idx] = 1 if b.get("natural", false) else 0
		emissive[idx] = 1 if b.get("emissive", false) else 0
		var tiles: Dictionary = b.get("tiles", {})
		var side := int(tiles.get("side", 0))
		tiles_side[idx] = side
		tiles_top[idx] = int(tiles.get("top", side))
		tiles_bottom[idx] = int(tiles.get("bottom", side))
		tiles_front[idx] = int(tiles.get("front", -1))


func index_of(id: String) -> int:
	return int(by_id.get(id, -1))


func id_of(index: int) -> String:
	if index < 0 or index >= blocks.size() or blocks[index].is_empty():
		return "air"
	return String(blocks[index]["id"])


func info(index: int) -> Dictionary:
	if index < 0 or index >= blocks.size():
		return {}
	return blocks[index]


func is_mineable(index: int) -> bool:
	var b := info(index)
	return index > 0 and not b.is_empty() and float(b.get("hardness", -1)) >= 0.0 and String(b.get("tool", "none")) != "none"


## Why a tool can or can't mine a block: "" = ok, else a short reason for the HUD.
func mine_check(index: int, tool: String, tier: int) -> String:
	if not is_mineable(index):
		return "can't be mined"
	var b := info(index)
	var need_tool := String(b.get("tool", "none"))
	if need_tool != tool:
		return "needs the %s" % need_tool
	var need_tier := int(b.get("tier", 1))
	if tier < need_tier:
		return "needs a tier %s %s" % [_roman(need_tier), need_tool]
	return ""


## Swings needed to break the block with a tool of `tier`.
func hits_needed(index: int, tier: int, hits_per_hardness: float, tier_speed: Array, min_hits: int = 1) -> int:
	var hardness := float(info(index).get("hardness", 1.0))
	var speed := 1.0
	if tier - 1 >= 0 and tier - 1 < tier_speed.size():
		speed = float(tier_speed[tier - 1])
	return maxi(min_hits, int(ceil(hardness * hits_per_hardness / speed)))


## Rolls the blocks.json drop list with `rng`. Returns {item: count}.
func roll_drops(index: int, rng: RandomNumberGenerator) -> Dictionary:
	return roll_drop_list(info(index).get("drops", []), rng)


static func roll_drop_list(drops: Array, rng: RandomNumberGenerator) -> Dictionary:
	var out := {}
	for dr in drops:
		if rng.randf() <= float(dr.get("chance", 1.0)):
			var c := rng.randi_range(int(dr.get("min", 1)), int(dr.get("max", 1)))
			if c > 0:
				out[dr["item"]] = int(out.get(dr["item"], 0)) + c
	return out


static func _roman(n: int) -> String:
	return ["0", "I", "II", "III", "IV"][clampi(n, 0, 4)]
