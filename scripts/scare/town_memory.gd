## Millbrook remembers: which tricks were used where, charms on objects, salt lines on doors,
## legend points and the legend's name, tavern rumors, per-area Remembrance and Heat.
## Pure state; the world shows it.
class_name TownMemory
extends RefCounted

var night: int = 0
var uses: Dictionary = {}          # object id -> [{ability, night}]
var charms: Dictionary = {}        # object id -> {charm, nights, by}
var salt_lines: Dictionary = {}    # door marker id -> {nights, by}
var legend_points: float = 0.0
var epithet_counts: Dictionary = {}  # epithet key -> count (Terrified/Legendary only)
var rumors: Array[Dictionary] = []   # {text, teller, night}
var remembrance: Dictionary = {}     # area id -> 0..1
var heat: float = 0.0
var legend_stage: int = 0

var _legend: Dictionary = {}       # population town_memory.legend
var _rumor_data: Dictionary = {}   # population town_memory.rumors


func setup(population_town_memory: Dictionary, areas: Array) -> void:
	_legend = population_town_memory.get("legend", {})
	_rumor_data = population_town_memory.get("rumors", {})
	for a in areas:
		if not remembrance.has(a["id"]):
			remembrance[a["id"]] = float(a.get("remembrance", 0.5))


## Records a haunting act. True when this is the repeat that makes the villager hang a charm.
func record_act(object_id: String, ability: String, within_nights: int, count: int) -> bool:
	var list: Array = uses.get(object_id, [])
	list.append({"ability": ability, "night": night})
	uses[object_id] = list
	var n := 0
	for u in list:
		if u["ability"] == ability and night - int(u["night"]) < within_nights:
			n += 1
	return n >= count and not charms.has(object_id)


func used_before(object_id: String, ability: String) -> bool:
	for u in uses.get(object_id, []):
		if u["ability"] == ability:
			return true
	return false


func hang_charm(object_id: String, charm: String, nights: int, by: String) -> void:
	charms[object_id] = {"charm": charm, "nights": nights, "by": by}


func is_unhauntable(object_id: String) -> bool:
	return charms.has(object_id)


func add_salt(door_id: String, nights: int, by: String) -> void:
	salt_lines[door_id] = {"nights": nights, "by": by}


func new_night() -> void:
	night += 1
	for dict in [charms, salt_lines]:
		for k in dict.keys():
			dict[k]["nights"] = int(dict[k]["nights"]) - 1
			if int(dict[k]["nights"]) <= 0:
				dict.erase(k)


## Adds legend points; returns true when the legend reached a new stage (for a toast).
func add_legend(points: float) -> bool:
	legend_points += points
	var st := _stage_index()
	if st > legend_stage:
		legend_stage = st
		return true
	return false


func count_epithet(kind: String, action: String) -> void:
	var key := "%s.%s" % [kind, action]
	var epis: Dictionary = _legend.get("epithets", {})
	if not epis.has(key):
		key = kind
	epithet_counts[key] = int(epithet_counts.get(key, 0)) + 1


func epithet() -> String:
	var epis: Dictionary = _legend.get("epithets", {})
	var best := ""
	var best_n := 0
	for k: String in epithet_counts:
		if int(epithet_counts[k]) > best_n and epis.has(k):
			best = k
			best_n = int(epithet_counts[k])
	return String(epis.get(best, "Creaking")) if best != "" else "Creaking"


func _stage_index() -> int:
	var idx := 0
	var stages: Array = _legend.get("stages", [])
	for i in stages.size():
		if legend_points >= float(stages[i].get("points", 0)):
			idx = i
	return idx


func stage_remembrance_bonus() -> float:
	var stages: Array = _legend.get("stages", [])
	if stages.is_empty():
		return 0.0
	return float(stages[_stage_index()].get("remembrance_bonus", 0.0))


## "the Creaking Ghost of Millbrook", or "" before anyone has noticed.
func legend_name() -> String:
	var stages: Array = _legend.get("stages", [])
	if stages.is_empty():
		return ""
	var nm: Variant = stages[_stage_index()].get("name", null)
	if nm == null:
		return ""
	return String(nm).format({"town": _legend.get("town", "Millbrook"), "epithet": epithet()})


## Fills a rumor template. `ctx`: victim, pronouns {subject, object, possessive}, object, place,
## action, hour, teller.
func make_rumor(template: String, ctx: Dictionary) -> String:
	var pr: Dictionary = ctx.get("pronouns", {"subject": "they", "object": "them", "possessive": "their"})
	var trick: Dictionary = _rumor_data.get("trick_past", {})
	var legend := legend_name()
	if legend == "":
		legend = "the ghost"
	return template.format({
		"victim": ctx.get("victim", "someone"), "they": pr.get("subject", "they"), "them": pr.get("object", "them"),
		"their": pr.get("possessive", "their"), "object": ctx.get("object", "door"), "place": ctx.get("place", "the village"),
		"trick_past": trick.get(ctx.get("action", "creak"), "moved"), "legend": legend, "hour": ctx.get("hour", "midnight"),
		"teller": ctx.get("teller", "someone")})


func add_rumor(text: String, teller: String, max_rumors: int) -> void:
	rumors.append({"text": text, "teller": teller, "night": night})
	while rumors.size() > max_rumors:
		rumors.pop_front()


func rumor_templates() -> Array:
	return _rumor_data.get("templates", [])


func add_remembrance(area: String, amount: float) -> void:
	if remembrance.has(area):
		remembrance[area] = clampf(float(remembrance[area]) + amount, 0.0, 1.0)


func decay_remembrance(dt: float, rate: float, floor_v: float) -> void:
	for k: String in remembrance:
		remembrance[k] = maxf(floor_v, float(remembrance[k]) - rate * dt)


func to_save() -> Dictionary:
	return {"night": night, "uses": uses, "charms": charms, "salt_lines": salt_lines, "legend_points": legend_points,
		"epithet_counts": epithet_counts, "rumors": rumors, "remembrance": remembrance, "heat": heat,
		"legend_stage": legend_stage}


func from_save(d: Dictionary) -> void:
	night = int(d.get("night", 0))
	uses = d.get("uses", {})
	charms = d.get("charms", {})
	salt_lines = d.get("salt_lines", {})
	legend_points = float(d.get("legend_points", 0.0))
	epithet_counts = d.get("epithet_counts", {})
	rumors.assign(d.get("rumors", []))
	for k: String in d.get("remembrance", {}):
		remembrance[k] = float(d["remembrance"][k])
	heat = float(d.get("heat", 0.0))
	legend_stage = int(d.get("legend_stage", 0))
