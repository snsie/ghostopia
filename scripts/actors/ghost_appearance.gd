## Ghost appearance options, presets, shader application, eye styles, expressions, and particle FX.
## Used by CharacterizerScreen (at New Game and the Magic Mirror), Player, and HUD.
class_name GhostAppearance
extends RefCounted

const BODY_COLORS := [
	{"id": "moonlight", "name": "Moonlight White", "color": "#d6e3fa"},
	{"id": "ectoplasm", "name": "Ectoplasm Mint", "color": "#8cf5d2"},
	{"id": "wisteria", "name": "Phantom Wisteria", "color": "#c9a6ff"},
	{"id": "rose", "name": "Haunted Rose", "color": "#ffb0d4"},
	{"id": "lantern", "name": "Lantern Amber", "color": "#ffd080"},
	{"id": "frost", "name": "Glacier Ice", "color": "#94e4ff"},
	{"id": "crimson", "name": "Blood Moon", "color": "#ff7a7a"},
	{"id": "toxic", "name": "Witching Lime", "color": "#b8ff70"},
	{"id": "cobalt", "name": "Midnight Indigo", "color": "#6f86ff"},
	{"id": "obsidian", "name": "Shadow Veil", "color": "#38304c"},
	{"id": "gold", "name": "Cursed Gold", "color": "#ffe875"},
	{"id": "lavender", "name": "Misty Lavender", "color": "#e3d1ff"},
]

const RIM_COLORS := [
	{"id": "ice_blue", "name": "Ice Blue", "color": "#9ee0ff"},
	{"id": "violet", "name": "Arcane Violet", "color": "#b86bff"},
	{"id": "emerald", "name": "Soul Emerald", "color": "#4dffb5"},
	{"id": "gold", "name": "Candlelight Gold", "color": "#ffc84d"},
	{"id": "crimson", "name": "Banshee Red", "color": "#ff4d6a"},
	{"id": "magenta", "name": "Fae Magenta", "color": "#ff66e8"},
	{"id": "cyan", "name": "Spectral Cyan", "color": "#3df5ff"},
	{"id": "white", "name": "Pure Halo", "color": "#ffffff"},
	{"id": "orange", "name": "Pumpkin Ember", "color": "#ff8533"},
	{"id": "deep_blue", "name": "Abyssal Blue", "color": "#3b6eff"},
]

const SECONDARY_COLORS := [
	{"id": "royal_violet", "name": "Royal Violet", "color": "#7359d9"},
	{"id": "deep_teal", "name": "Deep Teal", "color": "#1f8a9c"},
	{"id": "midnight", "name": "Midnight Void", "color": "#1d1436"},
	{"id": "sunset", "name": "Dusk Coral", "color": "#ff5e7e"},
	{"id": "amber", "name": "Harvest Gold", "color": "#ff9e2c"},
	{"id": "lime", "name": "Ecto Glow", "color": "#45e680"},
	{"id": "frost_white", "name": "Silver Mist", "color": "#eef5ff"},
	{"id": "crimson_dark", "name": "Crypt Wine", "color": "#8f1d3f"},
	{"id": "indigo", "name": "Starlight Blue", "color": "#3246a8"},
	{"id": "plum", "name": "Weeping Plum", "color": "#692b7c"},
]

const PATTERN_COLORS := [
	{"id": "starlight", "name": "Starlight", "color": "#f2d9ff"},
	{"id": "gold", "name": "Gilded Ink", "color": "#ffd866"},
	{"id": "cyan", "name": "Spirit Cyan", "color": "#66f7ff"},
	{"id": "ink", "name": "Crypt Ink", "color": "#1c122e"},
	{"id": "crimson", "name": "Crimson Rune", "color": "#ff4f6d"},
	{"id": "mint", "name": "Spectral Mint", "color": "#6bffb8"},
	{"id": "violet", "name": "Hex Violet", "color": "#b05cff"},
	{"id": "white", "name": "Chalk White", "color": "#ffffff"},
]

const EYE_COLORS := [
	{"id": "ink", "name": "Classic Ink", "color": "#1a0f26"},
	{"id": "violet", "name": "Haunting Violet", "color": "#ad47ff"},
	{"id": "cyan", "name": "Soul Cyan", "color": "#4df2ff"},
	{"id": "gold", "name": "Lantern Gold", "color": "#ffcc33"},
	{"id": "crimson", "name": "Ruby Glare", "color": "#ff3b5c"},
	{"id": "emerald", "name": "Witch Green", "color": "#47ff88"},
	{"id": "white", "name": "Blank Wraith", "color": "#f5f8ff"},
	{"id": "pink", "name": "Lovesick Pink", "color": "#ff78d4"},
]

const GRADIENTS := [
	{"id": 0, "name": "None (Solid)"},
	{"id": 1, "name": "Hem Dip (Bottom Up)"},
	{"id": 2, "name": "Crown Fade (Top Down)"},
	{"id": 3, "name": "Core Aura (Radial)"},
	{"id": 4, "name": "Spirit Sash (Band)"},
	{"id": 5, "name": "Drifting Wave"},
]

const PATTERNS := [
	{"id": 0, "name": "None"},
	{"id": 1, "name": "Vertical Stripes"},
	{"id": 2, "name": "Spectral Rings"},
	{"id": 3, "name": "Polka Wisps"},
	{"id": 4, "name": "Starry Night"},
	{"id": 5, "name": "Mystic Swirls"},
	{"id": 6, "name": "Patchwork Stitches"},
	{"id": 7, "name": "Arcane Runes"},
	{"id": 8, "name": "Phantom Checkers"},
]

const FINISHES := [
	{"id": 0, "name": "Classic Sheet"},
	{"id": 1, "name": "Holographic Prism"},
	{"id": 2, "name": "Phantom Glitch"},
	{"id": 3, "name": "Cosmic Starfield"},
	{"id": 4, "name": "Living Plasma"},
	{"id": 5, "name": "Ashen Embers"},
	{"id": 6, "name": "Crystalline Facets"},
	{"id": 7, "name": "Shadow Ink"},
]

const EYE_STYLES := [
	{"id": 0, "name": "Classic Oval"},
	{"id": 1, "name": "Hollow Rings"},
	{"id": 2, "name": "Starry Sparkle"},
	{"id": 3, "name": "Heart Pupils"},
	{"id": 4, "name": "Cat Slits"},
	{"id": 5, "name": "Hypno Spirals"},
	{"id": 6, "name": "Radiant Orbs"},
	{"id": 7, "name": "Stitched Buttons"},
]

const EXPRESSIONS := [
	{"id": "calm", "name": "Calm / Neutral"},
	{"id": "happy", "name": "Cheerful"},
	{"id": "angry", "name": "Mischievous"},
	{"id": "scared", "name": "Wide-Eyed"},
	{"id": "closed", "name": "Serene / Sleepy"},
	{"id": "wink", "name": "Playful Squint"},
]

const FX_AURAS := [
	{"id": "none", "name": "None"},
	{"id": "wisps", "name": "Soul Wisps"},
	{"id": "fireflies", "name": "Moon Fireflies"},
	{"id": "sparkles", "name": "Starlight Dust"},
	{"id": "embers", "name": "Cinder Sparks"},
	{"id": "shadow_mist", "name": "Shadow Mist"},
	{"id": "hearts", "name": "Phantom Petals"},
	{"id": "runes", "name": "Arcane Orbs"},
]

const PRESETS := [
	{
		"name": "Classic Sheet",
		"data": {
			"body_color": "#d6e3fa", "rim_color": "#9ee0ff", "secondary_color": "#7359d9", "pattern_color": "#f2d9ff",
			"gradient_mode": 0, "gradient_strength": 0.65, "pattern_mode": 0, "pattern_scale": 1.0, "pattern_strength": 0.45,
			"finish_mode": 0, "alpha": 0.78, "glow_boost": 0.0, "pulse_speed": 0.0,
			"eye_style": 0, "eye_color": "#1a0f26", "eye_glow": 0.0, "expression": "calm",
			"fx": "none", "fx_color": "#9ee0ff",
		}
	},
	{
		"name": "Astral Starweaver",
		"data": {
			"body_color": "#6f86ff", "rim_color": "#b86bff", "secondary_color": "#1d1436", "pattern_color": "#ffd866",
			"gradient_mode": 1, "gradient_strength": 0.85, "pattern_mode": 4, "pattern_scale": 1.1, "pattern_strength": 0.75,
			"finish_mode": 3, "alpha": 0.84, "glow_boost": 0.25, "pulse_speed": 0.6,
			"eye_style": 2, "eye_color": "#ffd866", "eye_glow": 1.2, "expression": "happy",
			"fx": "sparkles", "fx_color": "#ffd866",
		}
	},
	{
		"name": "Ecto Phantasm",
		"data": {
			"body_color": "#8cf5d2", "rim_color": "#4dffb5", "secondary_color": "#1f8a9c", "pattern_color": "#66f7ff",
			"gradient_mode": 5, "gradient_strength": 0.7, "pattern_mode": 5, "pattern_scale": 1.0, "pattern_strength": 0.5,
			"finish_mode": 4, "alpha": 0.75, "glow_boost": 0.35, "pulse_speed": 1.0,
			"eye_style": 5, "eye_color": "#47ff88", "eye_glow": 1.5, "expression": "angry",
			"fx": "wisps", "fx_color": "#4dffb5",
		}
	},
	{
		"name": "Patchwork Poltergeist",
		"data": {
			"body_color": "#c9a6ff", "rim_color": "#ffc84d", "secondary_color": "#692b7c", "pattern_color": "#1c122e",
			"gradient_mode": 2, "gradient_strength": 0.6, "pattern_mode": 6, "pattern_scale": 1.2, "pattern_strength": 0.8,
			"finish_mode": 0, "alpha": 0.88, "glow_boost": 0.1, "pulse_speed": 0.0,
			"eye_style": 7, "eye_color": "#ffcc33", "eye_glow": 0.8, "expression": "wink",
			"fx": "fireflies", "fx_color": "#ffc84d",
		}
	},
	{
		"name": "Cinder Wraith",
		"data": {
			"body_color": "#38304c", "rim_color": "#ff8533", "secondary_color": "#8f1d3f", "pattern_color": "#ff4f6d",
			"gradient_mode": 1, "gradient_strength": 0.8, "pattern_mode": 7, "pattern_scale": 1.0, "pattern_strength": 0.6,
			"finish_mode": 5, "alpha": 0.86, "glow_boost": 0.4, "pulse_speed": 1.2,
			"eye_style": 4, "eye_color": "#ff3b5c", "eye_glow": 1.6, "expression": "angry",
			"fx": "embers", "fx_color": "#ff8533",
		}
	},
	{
		"name": "Prism Specter",
		"data": {
			"body_color": "#ffb0d4", "rim_color": "#3df5ff", "secondary_color": "#7359d9", "pattern_color": "#ffffff",
			"gradient_mode": 3, "gradient_strength": 0.7, "pattern_mode": 2, "pattern_scale": 1.0, "pattern_strength": 0.4,
			"finish_mode": 1, "alpha": 0.8, "glow_boost": 0.3, "pulse_speed": 0.8,
			"eye_style": 3, "eye_color": "#ff78d4", "eye_glow": 1.1, "expression": "happy",
			"fx": "hearts", "fx_color": "#ffb0d4",
		}
	},
]


static func defaults() -> Dictionary:
	return (PRESETS[0]["data"] as Dictionary).duplicate(true)


static func sanitize(raw: Dictionary) -> Dictionary:
	var d := defaults()
	for k: String in d.keys():
		if raw.has(k):
			d[k] = raw[k]
	d["gradient_mode"] = clampi(int(d["gradient_mode"]), 0, GRADIENTS.size() - 1)
	d["pattern_mode"] = clampi(int(d["pattern_mode"]), 0, PATTERNS.size() - 1)
	d["finish_mode"] = clampi(int(d["finish_mode"]), 0, FINISHES.size() - 1)
	d["eye_style"] = clampi(int(d["eye_style"]), 0, EYE_STYLES.size() - 1)
	d["alpha"] = clampf(float(d["alpha"]), 0.4, 0.98)
	d["gradient_strength"] = clampf(float(d["gradient_strength"]), 0.0, 1.0)
	d["pattern_scale"] = clampf(float(d["pattern_scale"]), 0.4, 2.5)
	d["pattern_strength"] = clampf(float(d["pattern_strength"]), 0.0, 1.0)
	d["glow_boost"] = clampf(float(d["glow_boost"]), 0.0, 1.5)
	d["pulse_speed"] = clampf(float(d["pulse_speed"]), 0.0, 3.0)
	d["eye_glow"] = clampf(float(d["eye_glow"]), 0.0, 2.5)
	return d


static func randomize_appearance(rng: RandomNumberGenerator) -> Dictionary:
	var d := defaults()
	d["body_color"] = BODY_COLORS[rng.randi() % BODY_COLORS.size()]["color"]
	d["rim_color"] = RIM_COLORS[rng.randi() % RIM_COLORS.size()]["color"]
	d["secondary_color"] = SECONDARY_COLORS[rng.randi() % SECONDARY_COLORS.size()]["color"]
	d["pattern_color"] = PATTERN_COLORS[rng.randi() % PATTERN_COLORS.size()]["color"]
	d["gradient_mode"] = rng.randi() % GRADIENTS.size()
	d["gradient_strength"] = snappedf(rng.randf_range(0.4, 0.95), 0.05)
	d["pattern_mode"] = rng.randi() % PATTERNS.size()
	d["pattern_scale"] = snappedf(rng.randf_range(0.7, 1.6), 0.1)
	d["pattern_strength"] = snappedf(rng.randf_range(0.35, 0.85), 0.05)
	d["finish_mode"] = rng.randi() % FINISHES.size()
	d["alpha"] = snappedf(rng.randf_range(0.65, 0.92), 0.02)
	d["glow_boost"] = snappedf(rng.randf_range(0.0, 0.6), 0.05)
	d["pulse_speed"] = snappedf(rng.randf_range(0.0, 1.6), 0.2) if rng.randf() > 0.35 else 0.0
	d["eye_style"] = rng.randi() % EYE_STYLES.size()
	d["eye_color"] = EYE_COLORS[rng.randi() % EYE_COLORS.size()]["color"]
	d["eye_glow"] = snappedf(rng.randf_range(0.0, 1.6), 0.2)
	d["expression"] = EXPRESSIONS[rng.randi() % EXPRESSIONS.size()]["id"]
	d["fx"] = FX_AURAS[rng.randi() % FX_AURAS.size()]["id"]
	d["fx_color"] = d["rim_color"]
	return d


static func apply_to_materials(app: Dictionary, sheet_mat: ShaderMaterial, eyes: MeshInstance3D,
		glow_light: OmniLight3D = null, haunting_rank: int = 0) -> void:
	var d := sanitize(app)
	var body_c := Color(String(d["body_color"]))
	var rim_c := Color(String(d["rim_color"]))
	var sec_c := Color(String(d["secondary_color"]))
	var pat_c := Color(String(d["pattern_color"]))
	if sheet_mat:
		sheet_mat.set_shader_parameter("body", Vector3(body_c.r, body_c.g, body_c.b))
		sheet_mat.set_shader_parameter("rim", Vector3(rim_c.r, rim_c.g, rim_c.b))
		sheet_mat.set_shader_parameter("secondary", Vector3(sec_c.r, sec_c.g, sec_c.b))
		sheet_mat.set_shader_parameter("pattern_col", Vector3(pat_c.r, pat_c.g, pat_c.b))
		sheet_mat.set_shader_parameter("alpha", float(d["alpha"]))
		sheet_mat.set_shader_parameter("gradient_mode", int(d["gradient_mode"]))
		sheet_mat.set_shader_parameter("gradient_strength", float(d["gradient_strength"]))
		sheet_mat.set_shader_parameter("pattern_mode", int(d["pattern_mode"]))
		sheet_mat.set_shader_parameter("pattern_scale", float(d["pattern_scale"]))
		sheet_mat.set_shader_parameter("pattern_strength", float(d["pattern_strength"]))
		sheet_mat.set_shader_parameter("finish_mode", int(d["finish_mode"]))
		sheet_mat.set_shader_parameter("glow_boost", float(d["glow_boost"]))
		sheet_mat.set_shader_parameter("pulse_speed", float(d["pulse_speed"]))
	if glow_light:
		glow_light.light_color = rim_c.lerp(body_c, 0.35)
	if eyes:
		var eye_c := Color(String(d["eye_color"]))
		var eye_glow := float(d["eye_glow"])
		var style := int(d["eye_style"])
		if haunting_rank > 0 and eye_c == Color("#1a0f26") and eye_glow == 0.0 and style == 0:
			eye_c = Color(0.68, 0.28, 1.0)
			eye_glow = 0.5 + 0.4 * haunting_rank
		elif haunting_rank > 0:
			eye_glow = maxf(eye_glow, 0.4 + 0.3 * haunting_rank)
		if style == 0 and eye_c == Color("#1a0f26") and eye_glow <= 0.001 and haunting_rank == 0:
			eyes.material_override = null
		elif style == 0:
			var sm := StandardMaterial3D.new()
			sm.albedo_color = eye_c
			if eye_glow > 0.001:
				sm.emission_enabled = true
				sm.emission = eye_c
				sm.emission_energy_multiplier = eye_glow
			eyes.material_override = sm
		else:
			var em := ShaderMaterial.new()
			em.shader = load("res://shaders/ghost_eyes.gdshader")
			em.set_shader_parameter("eye_col", Vector3(eye_c.r, eye_c.g, eye_c.b))
			em.set_shader_parameter("eye_glow", eye_glow)
			em.set_shader_parameter("eye_style", style)
			eyes.material_override = em
		apply_expression(eyes, String(d["expression"]))


static func apply_expression(eyes: MeshInstance3D, expr: String) -> void:
	if eyes == null:
		return
	for k in ["angry", "scared", "happy", "closed"]:
		Actors.set_shape(eyes, k, 0.0)
	match expr:
		"angry", "scared", "happy", "closed":
			Actors.set_shape(eyes, expr, 1.0)
		"wink":
			Actors.set_shape(eyes, "happy", 0.55)
			Actors.set_shape(eyes, "closed", 0.55)


static func build_fx_node(app: Dictionary) -> Node3D:
	var d := sanitize(app)
	var kind := String(d.get("fx", "none"))
	if kind == "none" or kind == "":
		return null
	var col := Color(String(d.get("fx_color", d.get("rim_color", "#9ee0ff"))))
	var root := Node3D.new()
	root.name = "AppearanceFx"
	match kind:
		"wisps":
			var p := Fx.wisps(col, 4.0, 1.6, 0.35)
			p.position = Vector3(0, 0.25, 0)
			root.add_child(p)
		"fireflies":
			var p := Fx.fireflies([-0.38, 0.05, -0.38, 0.38, 0.65, 0.38], 12, col)
			root.add_child(p)
		"sparkles":
			var p := Fx._particles(18, 1.2, col.lightened(0.25), 0.065, true, 2.8)
			var pm: ParticleProcessMaterial = p.process_material
			pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
			pm.emission_sphere_radius = 0.34
			pm.direction = Vector3.UP
			pm.spread = 180.0
			pm.initial_velocity_min = 0.04
			pm.initial_velocity_max = 0.18
			pm.scale_min = 0.4
			pm.scale_max = 1.2
			p.position = Vector3(0, 0.34, 0)
			root.add_child(p)
		"embers":
			var p := Fx._particles(16, 1.1, col, 0.055, true, 2.6)
			var pm: ParticleProcessMaterial = p.process_material
			pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
			pm.emission_sphere_radius = 0.25
			pm.direction = Vector3.UP
			pm.spread = 35.0
			pm.initial_velocity_min = 0.25
			pm.initial_velocity_max = 0.55
			pm.turbulence_enabled = true
			pm.turbulence_noise_strength = 0.5
			p.position = Vector3(0, 0.12, 0)
			root.add_child(p)
		"shadow_mist":
			var p := Fx._particles(14, 1.8, Color(col.r * 0.45, col.g * 0.45, col.b * 0.55, 0.55), 0.28, false, 1.0)
			var pm: ParticleProcessMaterial = p.process_material
			pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
			pm.emission_sphere_radius = 0.28
			pm.direction = Vector3(0, -1, 0)
			pm.spread = 90.0
			pm.initial_velocity_min = 0.04
			pm.initial_velocity_max = 0.12
			p.position = Vector3(0, 0.22, 0)
			root.add_child(p)
		"hearts":
			var p := Fx._particles(12, 1.6, col.lightened(0.15), 0.09, true, 2.2)
			var pm: ParticleProcessMaterial = p.process_material
			pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_RING
			pm.emission_ring_radius = 0.28
			pm.emission_ring_inner_radius = 0.18
			pm.emission_ring_height = 0.2
			pm.emission_ring_axis = Vector3.UP
			pm.direction = Vector3.UP
			pm.spread = 20.0
			pm.initial_velocity_min = 0.15
			pm.initial_velocity_max = 0.3
			p.position = Vector3(0, 0.28, 0)
			root.add_child(p)
		"runes":
			var p := Fx._particles(10, 2.0, col, 0.11, true, 2.5)
			var pm: ParticleProcessMaterial = p.process_material
			pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_RING
			pm.emission_ring_radius = 0.36
			pm.emission_ring_inner_radius = 0.32
			pm.emission_ring_height = 0.08
			pm.emission_ring_axis = Vector3.UP
			pm.orbit_velocity_min = 0.35
			pm.orbit_velocity_max = 0.55
			pm.direction = Vector3.UP
			pm.initial_velocity_min = 0.02
			pm.initial_velocity_max = 0.06
			p.position = Vector3(0, 0.3, 0)
			root.add_child(p)
	return root
