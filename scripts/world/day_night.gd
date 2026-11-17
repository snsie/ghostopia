## The inverted day/night cycle from the task3 lighting presets: blends sky, moon and sun, ambient,
## fog, exposure, saturation and glow between the cycle keys, switches mood emission (windows,
## lanterns), blends toward the `fading` look where Remembrance is low, and sets the ambience.
class_name DayNight
extends Node

var env: Environment
var sky_mat: ShaderMaterial
var moon: DirectionalLight3D
var sun: DirectionalLight3D
var presets: Dictionary
var keys: Array
var level: Level
var world: VoxelWorld
var fade_k := 0.0           # 0..1 blend toward the fading preset (player's area)
var current_phase := ""
var _emission_phase := ""


func setup(p_level: Level, p_world: VoxelWorld, parent: Node) -> void:
	level = p_level
	world = p_world
	var lighting: Dictionary = Game.layout["lighting"]
	presets = lighting["presets"]
	keys = lighting["cycle"]["keys"]
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/sky.gdshader")
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.glow_hdr_threshold = 0.9
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_sky_affect = 0.2
	env.adjustment_enabled = true
	env.ssao_enabled = false
	var we := WorldEnvironment.new()
	we.environment = env
	parent.add_child(we)
	moon = DirectionalLight3D.new()
	moon.name = "Moon"
	moon.shadow_enabled = true
	moon.directional_shadow_max_distance = 60.0
	parent.add_child(moon)
	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 60.0
	parent.add_child(sun)
	apply_settings()


func apply_settings() -> void:
	var sh: bool = Game.settings["shadows"]
	moon.shadow_enabled = sh
	sun.shadow_enabled = sh
	env.glow_enabled = Game.settings["glow"]
	env.fog_enabled = Game.settings["fog"]


## The two presets around t and the blend factor.
func blend_at(t: float) -> Array:
	for i in keys.size() - 1:
		var a: Dictionary = keys[i]
		var b: Dictionary = keys[i + 1]
		if t >= float(a["t"]) and t <= float(b["t"]):
			var k := (t - float(a["t"])) / maxf(float(b["t"]) - float(a["t"]), 1e-6)
			return [String(a["preset"]), String(b["preset"]), smoothstep(0.0, 1.0, k)]
	return ["night", "night", 0.0]


func _c(p: Dictionary, path: String, fallback: Color) -> Color:
	var cur: Variant = p
	for k in path.split("."):
		if cur is Dictionary and cur.has(k) and cur[k] != null:
			cur = cur[k]
		else:
			return fallback
	return Color(String(cur))


func _f(p: Dictionary, path: String, fallback: float) -> float:
	var cur: Variant = p
	for k in path.split("."):
		if cur is Dictionary and cur.has(k) and cur[k] != null:
			cur = cur[k]
		else:
			return fallback
	return float(cur)


func _light_params(p: Dictionary, which: String) -> Dictionary:
	var l: Variant = p.get(which)
	if l == null:
		return {"energy": 0.0, "color": Color.WHITE, "dir": Vector3(0, -1, 0)}
	var d: Array = l["direction"]
	return {"energy": float(l["energy"]), "color": Color(String(l["color"])), "dir": Vector3(d[0], d[1], d[2]).normalized()}


func update(t: float) -> void:
	var bl := blend_at(t)
	var a: Dictionary = presets[bl[0]]
	var b: Dictionary = presets[bl[1]]
	var k: float = bl[2]
	var fp: Dictionary = presets.get("fading", {})
	var fk := fade_k
	var mix3 := func(path: String, fb: Color) -> Color:
		return _c(a, path, fb).lerp(_c(b, path, fb), k).lerp(_c(fp, path, fb), fk)
	var mixf := func(path: String, fb: float) -> float:
		return lerpf(lerpf(_f(a, path, fb), _f(b, path, fb), k), _f(fp, path, fb), fk)
	sky_mat.set_shader_parameter("top_color", mix3.call("sky.top", Color.BLACK))
	sky_mat.set_shader_parameter("horizon_color", mix3.call("sky.horizon", Color.BLACK))
	sky_mat.set_shader_parameter("void_color", mix3.call("sky.void", Color.BLACK))
	var stars_a := 1.0 if a.get("sky", {}).get("stars", false) else 0.0
	var stars_b := 1.0 if b.get("sky", {}).get("stars", false) else 0.0
	sky_mat.set_shader_parameter("stars", lerpf(stars_a, stars_b, k) * (1.0 - fk))
	var moon_a := 1.0 if a.get("sky", {}).get("moon_disc", false) else 0.0
	var moon_b := 1.0 if b.get("sky", {}).get("moon_disc", false) else 0.0
	sky_mat.set_shader_parameter("moon", lerpf(moon_a, moon_b, k))
	for pair in [[moon, "moon"], [sun, "sun"]]:
		var L: DirectionalLight3D = pair[0]
		var pa := _light_params(a, pair[1])
		var pb := _light_params(b, pair[1])
		var e := lerpf(float(pa["energy"]), float(pb["energy"]), k)
		var dir: Vector3 = (pa["dir"] if float(pa["energy"]) > 0.0 else pb["dir"])
		if float(pa["energy"]) > 0.0 and float(pb["energy"]) > 0.0:
			dir = (pa["dir"] as Vector3).lerp(pb["dir"], k).normalized()
		L.light_energy = e * (1.0 - fk * 0.2)
		L.light_color = (pa["color"] as Color).lerp(pb["color"], k)
		L.visible = e > 0.01
		if dir.length() > 0.1:
			L.look_at_from_position(Vector3.ZERO, dir, Vector3.UP if absf(dir.y) < 0.99 else Vector3.FORWARD)
		if pair[1] == "moon":
			sky_mat.set_shader_parameter("moon_dir", -dir)
	env.ambient_light_color = mix3.call("ambient.color", Color.GRAY)
	env.ambient_light_energy = mixf.call("ambient.energy", 0.8) * Game.tuning.f("world.ambient_mult", 0.5)
	env.fog_light_color = mix3.call("fog.color", Color.GRAY)
	env.fog_density = mixf.call("fog.density", 0.01) * 0.6
	var hfa: Variant = a.get("fog", {}).get("height_fog")
	var hfb: Variant = b.get("fog", {}).get("height_fog")
	var hd := lerpf(float(hfa["density"]) if hfa else 0.0, float(hfb["density"]) if hfb else 0.0, k)
	env.fog_height = lerpf(float(hfa["y"]) if hfa else 21.0, float(hfb["y"]) if hfb else 21.0, k)
	env.fog_height_density = hd * 0.5
	env.tonemap_exposure = mixf.call("exposure", 1.2) * Game.tuning.f("world.exposure_mult", 0.85)
	env.adjustment_saturation = mixf.call("saturation", 1.0)
	env.glow_intensity = 0.6 + mixf.call("glow_bloom", 0.4)
	env.glow_bloom = mixf.call("glow_bloom", 0.4) * 0.25
	# Mood emission switches at the dominant preset
	var dom: Dictionary = a if k < 0.5 else b
	var ph := Game.phase_at(t)
	current_phase = ph
	var emis_key := "%s_%s" % [bl[0] if k < 0.5 else bl[1], ph]
	if emis_key != _emission_phase:
		_emission_phase = emis_key
		var win_e := Game.tuning.f("world.window_glow_energy", 2.2) * float(dom.get("emission", {}).get("glow_energy", 1.0))
		level.set_mood(ph, dom.get("emission", {}), win_e)
	world.set_mood_emission(lerpf(1.0, 0.25, 1.0 if ph == "day" else 0.0))


## Ambience layers for the phase and where the ghost is.
func ambience_for(pos: Vector3) -> Dictionary:
	var ph := current_phase
	var lv := {}
	if ph in ["night", "dusk"]:
		lv["night_crickets_loop"] = 0.8 if ph == "night" else 0.4
		lv["wind_loop"] = 0.35
	else:
		lv["day_loop"] = 0.6
		lv["wind_loop"] = 0.2
	var stream_d := absf(pos.x - 85.0)
	if pos.z > 10.0 and pos.z < 180.0:
		lv["stream_loop"] = clampf(1.0 - stream_d / 18.0, 0.0, 1.0) * 0.8
	var mill := Vector3(98.5, 30.0, 51.0)
	lv["windmill_loop"] = clampf(1.0 - pos.distance_to(mill) / 22.0, 0.0, 1.0) * 0.7
	var tav := Vector3(96.5, 21.0, 108.5)
	if ph in ["dusk", "night"] and Game.hour_at(Game.cycle_t) > 18.0:
		lv["tavern_murmur_loop"] = clampf(1.0 - pos.distance_to(tav) / 16.0, 0.0, 1.0) * 0.7
	return lv
