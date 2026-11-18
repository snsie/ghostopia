## Autoload `Game`: loaded data (tuning, blocks, layout, population, fragments, characters), the
## persistent run state (inventory, paths, fragments, villager memory, town memory, Remembrance,
## time), save/load, settings and the input map.
extends Node

signal toast(text: String, kind: String)
signal fragment_found(id: String)
signal level_up(path: String, level: int, unlock: String)
signal stats_changed
signal settings_changed

const SAVE_PATH := "user://save.json"
const SETTINGS_PATH := "user://settings.cfg"
const LAYOUT := "res://assets/levels/millbrook_layout.json"
const POPULATION := "res://assets/levels/millbrook_population.json"
const FRAGMENTS := "res://assets/data/memory_fragments.json"
const CHARACTERS := "res://assets/characters/characters.json"

var tuning: Tuning
var blocks: BlockRegistry
var layout: Dictionary
var population: Dictionary
var fragments_data: Dictionary
var characters: Dictionary
var fragment_roller := FragmentRoller.new()
var fragments_by_id: Dictionary = {}
var villagers_by_id: Dictionary = {}
var hauntables_by_id: Dictionary = {}
var markers_by_id: Dictionary = {}
var areas: Array = []

# Run state
var inventory := Inventory.new()
var minds: Dictionary = {}          # villager id -> VillagerMind
var town := TownMemory.new()
var fragments: Dictionary = {}      # collected id -> true
var path_fright: Dictionary = {"haunting": 0.0, "possession": 0.0, "telekinesis": 0.0}
var presence_fright: float = 0.0
var fright_essence: float = 0.0     # carried; dropped when scattered
var hp: float = 10.0
var ecto: float = 100.0
var cycle_t: float = 0.06
var nights: int = 0
var player_pos := Vector3.ZERO
var player_yaw := 0.0
var nodes_state: Dictionary = {}    # node id -> regrow time left (s)
var dropped_essence: Array = []     # [{pos: [x,y,z], amount}]
var scares_log: Array = []          # recent graded scares (for the journal)
var stats := {"scares": 0, "legendary": 0, "terrified": 0, "spooked": 0, "bolts": 0, "botches": 0,
	"blocks_mined": 0, "blocks_placed": 0}

var settings := {
	"master": 0.9, "music": 0.6, "sfx": 0.9, "ambience": 0.7,
	"fullscreen": false, "shadows": true, "outlines": true, "glow": true, "fog": true, "render_scale": 1.0,
	"mouse_sensitivity": 1.0, "invert_y": false, "vsync": true,
}

var cmd := {}   # command-line flags after `--`
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_parse_args()
	rng.seed = 20261117
	tuning = Tuning.load_file()
	blocks = BlockRegistry.load_file()
	layout = _json(LAYOUT)
	population = _json(POPULATION)
	fragments_data = _json(FRAGMENTS)
	for entry in [
		["fungal_grotto", "The Spore Keeper's Promise", "I left the brightest cap untouched. Some lights belong to the dark."],
		["flooded_ossuary", "The Ferryman's Lantern", "I lit the lantern for the last crossing and waited until dawn."],
		["crystal_hollow", "The Prospector's Echo", "The stones sang my name back to me, only softer."],
	]:
		fragments_data["fragments"].append({"id": entry[0], "owner_name": entry[1], "vignette": entry[1], "text": entry[2], "emotion": "nostalgia", "set": null})
	characters = _json(CHARACTERS).get("characters", {})
	fragment_roller.setup(fragments_data)
	for f in fragments_data.get("fragments", []):
		fragments_by_id[f["id"]] = f
	for v in population.get("villagers", []):
		villagers_by_id[v["id"]] = v
	for h in population.get("hauntables", []):
		hauntables_by_id[h["id"]] = h
	for m in layout.get("markers", []):
		markers_by_id[m["id"]] = m
	areas = layout.get("areas", [])
	var placeable := {}
	var items := tuning.d("items")
	for k: String in items:
		if items[k] is Dictionary and items[k].get("kind") == "block":
			placeable[k] = items[k]["block"]
	inventory.set_placeable(placeable)
	_build_input_map()
	load_settings()
	new_game()


func _parse_args() -> void:
	var args := OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		var a := args[i]
		if a.begins_with("--"):
			var key := a.substr(2)
			var vals: Array[String] = []
			while i + 1 < args.size() and not args[i + 1].begins_with("--"):
				i += 1
				vals.append(args[i])
			cmd[key] = vals
		i += 1


func has_flag(f: String) -> bool:
	return cmd.has(f)


static func _json(path: String) -> Dictionary:
	var v: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return v if v is Dictionary else {}


# ---------------------------------------------------------------- run state

var traits := {"haunting": 0, "drift": 0, "resilience": 0}


func trait_rank(id: String) -> int:
	return int(traits.get(id, 0))


func pending_traits() -> int:
	return maxi(0, int(presence_level().get("level", 1)) - 1 - trait_rank("haunting") - trait_rank("drift") - trait_rank("resilience"))


func choose_trait(id: String) -> void:
	if not traits.has(id) or pending_traits() == 0:
		return
	traits[id] += 1
	if id == "resilience":
		hp = minf(max_hp(), hp + 2.0)
	stats_changed.emit()


func new_game() -> void:
	inventory.setup(tuning.d("start"))
	minds.clear()
	var over := tuning.d("villager_overrides")
	for v in population.get("villagers", []):
		minds[v["id"]] = VillagerMind.from_data(v, over.get(v["id"], {}))
	town = TownMemory.new()
	town.setup(population.get("town_memory", {}), areas)
	fragments.clear()
	path_fright = {"haunting": 0.0, "possession": 0.0, "telekinesis": 0.0}
	for id in traits:
		traits[id] = 0
	presence_fright = 0.0
	fright_essence = 0.0
	hp = max_hp()
	ecto = tuning.f("player.ecto_max", 100.0)
	cycle_t = tuning.f("cycle.start_t", 0.06)
	nights = 0
	var sp: Dictionary = layout.get("spawn", {})
	var p: Array = sp.get("player_start", [28.1, 28.0, 92.5])
	player_yaw = float(sp.get("yaw", 90.0))
	# a few steps out of the doorway, so the chase camera isn't pressed against the mausoleum
	player_pos = Vector3(p[0], p[1], p[2]) + Vector3(sin(deg_to_rad(player_yaw)), 0.0, cos(deg_to_rad(player_yaw))) * 2.5
	nodes_state.clear()
	dropped_essence.clear()
	scares_log.clear()
	for k: String in stats:
		stats[k] = 0
	stats_changed.emit()


func presence_level() -> Dictionary:
	return tuning.level_for("presence.levels", presence_fright)


func max_hp() -> float:
	return float(presence_level().get("hp", tuning.f("player.hp_base", 10.0))) + 2.0 * trait_rank("resilience")


func haunting_level() -> int:
	return int(tuning.level_for("haunting.levels", path_fright["haunting"]).get("level", 1))


func ability_unlocked(ability: String) -> bool:
	for row in tuning.a("haunting.levels"):
		if row.get("unlock") == ability:
			return haunting_level() >= int(row["level"]) and not row.get("slice_locked", false)
	return false


## Pays Fright to every path used and to Presence; emits level-ups.
func add_fright(amount: float, paths: Array) -> void:
	var before_h := haunting_level()
	var before_p := int(presence_level().get("level", 1))
	for p: String in paths:
		path_fright[p] = float(path_fright.get(p, 0.0)) + amount
	presence_fright += amount
	fright_essence += amount
	var after_h := haunting_level()
	if after_h > before_h:
		var row := tuning.level_for("haunting.levels", path_fright["haunting"])
		level_up.emit("haunting", after_h, String(row.get("unlock", "")))
	var after_p := int(presence_level().get("level", 1))
	if after_p > before_p:
		hp = max_hp()
		level_up.emit("presence", after_p, "")
	stats_changed.emit()


func collect_fragment(id: String) -> void:
	if id == "" or fragments.has(id):
		return
	fragments[id] = true
	fragment_found.emit(id)
	var f: Dictionary = fragments_by_id.get(id, {})
	var set_id: Variant = f.get("set", null)
	if set_id != null:
		for s in fragments_data.get("sets", []):
			if s["id"] == set_id and (s["fragments"] as Array).all(func(x: String) -> bool: return fragments.has(x)):
				toast.emit("Set complete: %s can rest here now (run 2)" % String(s.get("unlocks_resident", "a worker")), "set")


func area_at(p: Vector3) -> Dictionary:
	var best: Dictionary = {}
	var best_pri := -999
	for a in areas:
		var r: Array = a["rect"]
		if p.x >= float(r[0]) and p.x < float(r[2]) and p.z >= float(r[1]) and p.z < float(r[3]):
			if int(a.get("priority", 0)) > best_pri:
				best = a
				best_pri = int(a.get("priority", 0))
	return best


## Phase name at cycle t ("dusk", "night", "dawn", "day").
func phase_at(t: float) -> String:
	var ph: Dictionary = layout["lighting"]["cycle"]["phases"]
	for k: String in ph:
		var r: Array = ph[k]
		var a := float(r[0])
		var b := float(r[1])
		if (a <= b and t >= a and t < b) or (a > b and (t >= a or t < b)):
			return k
	return "night"


func phase() -> String:
	return phase_at(cycle_t)


func cycle_length() -> float:
	return tuning.f("cycle.length_s", 1440.0)


## Nominal clock hour at t (interpolated from the layout cycle keys).
func hour_at(t: float) -> float:
	var keys: Array = layout["lighting"]["cycle"]["keys"]
	for i in keys.size() - 1:
		var a: Dictionary = keys[i]
		var b: Dictionary = keys[i + 1]
		if t >= float(a["t"]) and t <= float(b["t"]):
			var ha := float(a["hour"])
			var hb := float(b["hour"])
			if hb < ha:
				hb += 24.0
			var k := (t - float(a["t"])) / maxf(float(b["t"]) - float(a["t"]), 1e-6)
			return fmod(lerpf(ha, hb, k), 24.0)
	return 0.0


## Real seconds until daylight (start of the day phase); 0 while it's day.
func seconds_until_daylight() -> float:
	var day_start := float(layout["lighting"]["cycle"]["phases"]["dawn"][1])
	if phase() == "day":
		return 0.0
	var d := day_start - cycle_t
	if d < 0.0:
		d += 1.0
	return d * cycle_length()


func seconds_until_night() -> float:
	var night_start := float(layout["lighting"]["cycle"]["phases"]["night"][0])
	var d := night_start - cycle_t
	if d < 0.0:
		d += 1.0
	return d * cycle_length()


# ---------------------------------------------------------------- save / load

func save_path() -> String:
	return "user://autotest-save.json" if has_flag("autotest") else SAVE_PATH


func save_game(world_edits: Dictionary, extra: Dictionary = {}) -> bool:
	var minds_s := {}
	for k: String in minds:
		minds_s[k] = (minds[k] as VillagerMind).to_save()
	var d := {
		"version": 2, "traits": traits, "saved_at": Time.get_datetime_string_from_system(),
		"world_edits": world_edits, "inventory": inventory.to_save(), "path_fright": path_fright,
		"presence_fright": presence_fright, "fright_essence": fright_essence, "hp": hp, "ecto": ecto,
		"fragments": fragments.keys(), "minds": minds_s, "town": town.to_save(), "cycle_t": cycle_t,
		"nights": nights, "player_pos": [player_pos.x, player_pos.y, player_pos.z], "player_yaw": player_yaw,
		"nodes_state": nodes_state, "dropped_essence": dropped_essence, "stats": stats, "scares_log": scares_log,
	}
	d.merge(extra, true)
	var f := FileAccess.open(save_path(), FileAccess.WRITE)
	if f == null:
		push_error("Game: can't write %s" % save_path())
		return false
	f.store_string(JSON.stringify(d, "\t"))
	f.close()
	return true


func has_save() -> bool:
	return FileAccess.file_exists(save_path())


## Restores the run state; returns the save dictionary (world edits and extras for the world).
func load_game() -> Dictionary:
	if not has_save():
		return {}
	var d := _json(save_path())
	if d.is_empty():
		return {}
	new_game()
	inventory.from_save(d.get("inventory", {}))
	for k: String in d.get("path_fright", {}):
		path_fright[k] = float(d["path_fright"][k])
	presence_fright = float(d.get("presence_fright", 0.0))
	fright_essence = float(d.get("fright_essence", 0.0))
	for id in traits:
		traits[id] = maxi(0, int(d.get("traits", {}).get(id, 0)))
	hp = clampf(float(d.get("hp", max_hp())), 0.0, max_hp())
	ecto = float(d.get("ecto", 100.0))
	for id in d.get("fragments", []):
		fragments[String(id)] = true
	for k: String in d.get("minds", {}):
		if minds.has(k):
			(minds[k] as VillagerMind).from_save(d["minds"][k])
	town.from_save(d.get("town", {}))
	cycle_t = float(d.get("cycle_t", cycle_t))
	nights = int(d.get("nights", 0))
	var pp: Array = d.get("player_pos", [player_pos.x, player_pos.y, player_pos.z])
	player_pos = Vector3(pp[0], pp[1], pp[2])
	player_yaw = float(d.get("player_yaw", player_yaw))
	nodes_state = d.get("nodes_state", {})
	dropped_essence = d.get("dropped_essence", [])
	for k: String in d.get("stats", {}):
		stats[k] = int(d["stats"][k])
	scares_log = d.get("scares_log", [])
	stats_changed.emit()
	return d


# ---------------------------------------------------------------- settings and input

func load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load(SETTINGS_PATH) == OK:
		for k: String in settings:
			settings[k] = cf.get_value("settings", k, settings[k])
	apply_settings()


func save_settings() -> void:
	var cf := ConfigFile.new()
	for k: String in settings:
		cf.set_value("settings", k, settings[k])
	cf.save(SETTINGS_PATH)


func apply_settings() -> void:
	for bus in ["Master", "Music", "SFX", "Ambience"]:
		if AudioServer.get_bus_index(bus) < 0:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.bus_count - 1, bus)
			AudioServer.set_bus_send(AudioServer.bus_count - 1, "Master")
	_bus_vol("Master", settings["master"])
	_bus_vol("Music", settings["music"])
	_bus_vol("SFX", settings["sfx"])
	_bus_vol("Ambience", settings["ambience"])
	if not has_flag("autotest") and not has_flag("tour") and DisplayServer.get_name() != "headless":
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if settings["fullscreen"] else DisplayServer.WINDOW_MODE_WINDOWED)
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if settings["vsync"] else DisplayServer.VSYNC_DISABLED)
	settings_changed.emit()


func _bus_vol(bus: String, v: float) -> void:
	var i := AudioServer.get_bus_index(bus)
	if i >= 0:
		AudioServer.set_bus_volume_db(i, linear_to_db(maxf(float(v), 0.0001)))


const KEYS := {
	"move_forward": [KEY_W, KEY_UP], "move_back": [KEY_S, KEY_DOWN], "move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT], "ascend": [KEY_SPACE], "sink": [KEY_CTRL, KEY_C], "fast": [KEY_SHIFT],
	"possess": [KEY_G], "haunt": [KEY_E], "haunt_strong": [KEY_R], "boo": [KEY_F], "interact": [KEY_Q],
	"journal": [KEY_J], "inventory": [KEY_TAB, KEY_I], "pause": [KEY_ESCAPE],
	"slot_1": [KEY_1], "slot_2": [KEY_2], "slot_3": [KEY_3], "slot_4": [KEY_4], "slot_5": [KEY_5],
	"slot_6": [KEY_6], "slot_7": [KEY_7], "slot_8": [KEY_8], "slot_9": [KEY_9],
}
const MOUSE := {"use": MOUSE_BUTTON_LEFT, "place": MOUSE_BUTTON_RIGHT}
const PAD := {"use": JOY_BUTTON_RIGHT_SHOULDER, "place": JOY_BUTTON_LEFT_SHOULDER, "ascend": JOY_BUTTON_A,
	"sink": JOY_BUTTON_B, "haunt": JOY_BUTTON_X, "haunt_strong": JOY_BUTTON_Y, "boo": JOY_BUTTON_RIGHT_STICK,
	"pause": JOY_BUTTON_START, "inventory": JOY_BUTTON_BACK, "interact": JOY_BUTTON_DPAD_UP,
	"journal": JOY_BUTTON_DPAD_DOWN, "possess": JOY_BUTTON_DPAD_RIGHT}


func _build_input_map() -> void:
	for action: String in KEYS:
		_ensure_action(action)
		for k: int in KEYS[action]:
			var e := InputEventKey.new()
			e.physical_keycode = k as Key
			InputMap.action_add_event(action, e)
	for action: String in MOUSE:
		_ensure_action(action)
		var m := InputEventMouseButton.new()
		m.button_index = MOUSE[action]
		InputMap.action_add_event(action, m)
	for action: String in PAD:
		_ensure_action(action)
		var j := InputEventJoypadButton.new()
		j.button_index = PAD[action]
		InputMap.action_add_event(action, j)
	for pair in [["move_left", JOY_AXIS_LEFT_X, -1.0], ["move_right", JOY_AXIS_LEFT_X, 1.0],
			["move_forward", JOY_AXIS_LEFT_Y, -1.0], ["move_back", JOY_AXIS_LEFT_Y, 1.0]]:
		var ja := InputEventJoypadMotion.new()
		ja.axis = pair[1]
		ja.axis_value = pair[2]
		InputMap.action_add_event(pair[0], ja)


func _ensure_action(a: String) -> void:
	if not InputMap.has_action(a):
		InputMap.add_action(a, 0.2)


## Where self-test output goes: the project's renders/game in the editor, next to the exe when exported.
func output_dir() -> String:
	var d := ""
	if OS.has_feature("editor"):
		d = ProjectSettings.globalize_path("res://renders/game")
	else:
		d = OS.get_executable_path().get_base_dir().path_join("autotest")
	DirAccess.make_dir_recursive_absolute(d)
	return d
