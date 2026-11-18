## Stamps the task1-4 data into the scene: every glTF prop from the layout (with collision layers,
## warm light ranges, mood glow materials, haunt-glow shader), the hauntables, the gathering nodes,
## the Spectral Workbench, particle effects from the population `fx`, charms and salt lines.
class_name Level
extends Node3D

const SOLID_PROPS := ["gravestone_round", "gravestone_cross", "gravestone_spiral", "gravestone_celtic", "stone_pillar",
	"millstone", "mausoleum_portal", "mausoleum_window", "mausoleum_gargoyle_corner", "mausoleum_gargoyle_winged",
	"mausoleum_spiral_emblem", "lantern_post", "bell"]

var world: VoxelWorld
var hauntables: Dictionary = {}        # id -> Hauntable
var instances: Dictionary = {}         # instance id -> Node3D
var glow_materials: Array[BaseMaterial3D] = []
var flame_materials: Array[BaseMaterial3D] = []
var window_lights: Array[OmniLight3D] = []
var gather_nodes: Dictionary = {}      # id -> {data, node (Node3D or null), alive, cell}
var cell_nodes: Dictionary = {}        # Vector3i -> node id
var fx_nodes: Array[Dictionary] = []   # {node, moods}
var workbench: Node3D
var magic_mirror: Node3D
var sails: Node3D
var sign_node: Node3D
var charm_nodes: Dictionary = {}       # object id -> Node3D
var salt_nodes: Dictionary = {}        # door id -> StaticBody3D
var haunt_material: ShaderMaterial
var _scenes: Dictionary = {}
var _t := 0.0


func build(p_world: VoxelWorld) -> void:
	world = p_world
	haunt_material = ShaderMaterial.new()
	haunt_material.shader = load("res://shaders/haunt_glow.gdshader")
	var by_instance := {}
	for h in Game.population.get("hauntables", []):
		if h.get("instance") != null:
			by_instance[h["instance"]] = h
	for inst in Game.layout.get("instances", []):
		var n := _instance(inst)
		if n == null:
			continue
		instances[inst["id"]] = n
		if by_instance.has(inst["id"]):
			_make_hauntable(by_instance[inst["id"]], n)
	_place_workbench()
	_place_magic_mirror()
	_build_nodes()
	_build_fx()
	sails = _find_prefix(instances.get("windmill_sails_1"), "ANIM_sails")
	sign_node = _find_prefix(instances.get("tavern_sign_1"), "ANIM_sign")


func scene(path: String) -> PackedScene:
	if not _scenes.has(path):
		_scenes[path] = load(path) if ResourceLoader.exists(path) else null
	return _scenes[path]


func _instance(inst: Dictionary) -> Node3D:
	var ps := scene(String(inst["gltf"]))
	if ps == null:
		return null
	var n: Node3D = ps.instantiate()
	n.name = String(inst["id"])
	var p: Array = inst["pos"]
	n.position = Vector3(p[0], p[1], p[2])
	n.rotation.y = deg_to_rad(float(inst.get("yaw", 0.0)))
	add_child(n)
	_prepare(n, String(inst["prop"]))
	return n


## Collision layers, light ranges and colours, glow/flame materials, hidden haunt shells.
func _prepare(n: Node, prop: String) -> void:
	var solid := SOLID_PROPS.has(prop)
	var stack: Array[Node] = [n]
	var lantern_col := Color(Game.tuning.get_value("world.lantern_color", "#ffad5c"))
	var candle_col := Color(Game.tuning.get_value("world.candle_color", "#ffb24d"))
	while not stack.is_empty():
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		var nm := String(c.name)
		if c is StaticBody3D:
			(c as StaticBody3D).collision_layer = VoxelWorld.L_PROP_SOLID if solid else VoxelWorld.L_PROP_PHASE
			(c as StaticBody3D).collision_mask = 0
		elif c is OmniLight3D:
			var l := c as OmniLight3D
			l.shadow_enabled = false
			l.omni_attenuation = 1.4
			if nm.contains("lantern"):
				l.light_color = lantern_col
				l.omni_range = Game.tuning.f("world.lantern_range_m", 8.0)
				l.light_energy *= 2.4
			elif nm.contains("window"):
				l.light_color = Color(1.0, 0.72, 0.42)
				l.omni_range = 4.5
				l.light_energy *= 2.0
				window_lights.append(l)
			elif nm.contains("forge"):
				l.light_color = Color(0.6, 0.85, 1.0)
				l.omni_range = 5.0
				l.light_energy *= 2.0
			else:
				l.light_color = candle_col
				l.omni_range = Game.tuning.f("world.candle_range_m", 5.0)
				l.light_energy *= 2.4
		elif c is MeshInstance3D:
			var mi := c as MeshInstance3D
			if nm.begins_with("HAUNT_"):
				mi.visible = false
				for s in mi.get_surface_override_material_count():
					mi.set_surface_override_material(s, haunt_material)
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				continue
			if mi.mesh == null:
				continue
			for s in mi.mesh.get_surface_count():
				var m := mi.mesh.surface_get_material(s)
				if m is BaseMaterial3D:
					var mname := String(m.resource_name)
					if mname.begins_with("GLOW_") and not glow_materials.has(m):
						glow_materials.append(m)
					elif mname.begins_with("FLAME_") and not flame_materials.has(m):
						(m as BaseMaterial3D).emission_energy_multiplier = Game.tuning.f("world.flame_glow_energy", 3.0)
						flame_materials.append(m)
			if nm.begins_with("FLAME_"):
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _find_prefix(n: Node, prefix: String) -> Node3D:
	if n == null:
		return null
	if String(n.name).begins_with(prefix) and n is Node3D:
		return n
	for c in n.get_children():
		var r := _find_prefix(c, prefix)
		if r:
			return r
	return null


func _make_hauntable(data: Dictionary, n: Node3D) -> Hauntable:
	var h := Hauntable.new()
	n.add_child(h)
	h.setup(String(data["id"]), data, n)
	for f in h.flames:
		if h.kind in ["candle", "oil_lamp", "lantern"]:
			var p := Fx.flame(Color(Game.tuning.get_value("world.candle_color", "#ffb24d")))
			f.get_parent().add_child(p)
			p.position = f.position + Vector3(0, 0.03, 0)
			h.particles.append(p)
	hauntables[h.id] = h
	return h


## Carried lights: the villager script calls this with the held item node.
func register_carried(data: Dictionary, item_root: Node3D) -> Hauntable:
	var h := Hauntable.new()
	item_root.add_child(h)
	h.setup(String(data["id"]), data, item_root)
	for l in h.lights:
		l.shadow_enabled = false
		l.omni_range = Game.tuning.f("world.lantern_range_m", 8.0) * 0.8
		l.light_color = Color(Game.tuning.get_value("world.lantern_color", "#ffad5c"))
		l.light_energy = 1.6
	h.base_energy.clear()
	for l in h.lights:
		h.base_energy.append(l.light_energy)
	hauntables[h.id] = h
	return h


func _place_workbench() -> void:
	var ps := scene("res://assets/props/spectral_workbench.gltf")
	if ps == null:
		return
	workbench = ps.instantiate()
	workbench.name = "spectral_workbench"
	# In the mausoleum doorway yard, against the north wall outside the crypt (the crypt is 3x3 and
	# full: chest, candles, respawn point). Faces south, toward the path.
	workbench.position = Vector3(30.5, 28.0, 88.6)
	workbench.rotation.y = 0.0
	add_child(workbench)
	_prepare(workbench, "spectral_workbench")
	var spark := Fx.wisps(Color(0.55, 0.9, 1.0), 2.0, 2.0, 0.4)
	workbench.add_child(spark)
	spark.position = Vector3(1.65, 1.0, 0.0)


func workbench_pos() -> Vector3:
	return workbench.global_position + Vector3(0, 0, 0.8) if workbench else Vector3.ZERO


func _place_magic_mirror() -> void:
	magic_mirror = Node3D.new()
	magic_mirror.name = "magic_mirror"
	# Opposite the Spectral Workbench in the mausoleum doorway yard, facing north toward the path.
	magic_mirror.position = Vector3(30.5, 28.0, 96.4)
	magic_mirror.rotation.y = PI
	add_child(magic_mirror)

	var frame_mat := StandardMaterial3D.new()
	frame_mat.albedo_color = Color(0.24, 0.18, 0.34)
	frame_mat.metallic = 0.55
	frame_mat.roughness = 0.35

	var trim_mat := StandardMaterial3D.new()
	trim_mat.albedo_color = Color(0.88, 0.72, 0.36)
	trim_mat.metallic = 0.75
	trim_mat.roughness = 0.25
	trim_mat.emission_enabled = true
	trim_mat.emission = Color(0.65, 0.5, 0.2)
	trim_mat.emission_energy_multiplier = 0.3

	# Pedestal base
	var base := MeshInstance3D.new()
	var base_cyl := CylinderMesh.new()
	base_cyl.top_radius = 0.46
	base_cyl.bottom_radius = 0.54
	base_cyl.height = 0.18
	base.mesh = base_cyl
	base.position = Vector3(0, 0.09, 0)
	base.material_override = frame_mat
	magic_mirror.add_child(base)

	# Side pillars
	for sx in [-0.42, 0.42]:
		var post := MeshInstance3D.new()
		var pc := CylinderMesh.new()
		pc.top_radius = 0.06
		pc.bottom_radius = 0.075
		pc.height = 1.65
		post.mesh = pc
		post.position = Vector3(sx, 0.95, 0)
		post.material_override = frame_mat
		magic_mirror.add_child(post)

		var finial := MeshInstance3D.new()
		var sp := SphereMesh.new()
		sp.radius = 0.09
		sp.height = 0.18
		finial.mesh = sp
		finial.position = Vector3(sx, 1.82, 0)
		finial.material_override = trim_mat
		magic_mirror.add_child(finial)

	# Outer oval frame
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.42
	torus.outer_radius = 0.52
	ring.mesh = torus
	ring.position = Vector3(0, 1.12, 0)
	ring.rotation.x = PI * 0.5
	ring.scale = Vector3(0.92, 1.0, 1.32)
	ring.material_override = trim_mat
	magic_mirror.add_child(ring)

	# Glowing spectral mirror glass
	var glass := MeshInstance3D.new()
	var g_cyl := CylinderMesh.new()
	g_cyl.top_radius = 0.44
	g_cyl.bottom_radius = 0.44
	g_cyl.height = 0.05
	glass.mesh = g_cyl
	glass.position = Vector3(0, 1.12, 0)
	glass.rotation.x = PI * 0.5
	glass.scale = Vector3(0.92, 1.0, 1.32)
	var glass_mat := ShaderMaterial.new()
	glass_mat.shader = load("res://shaders/ghost.gdshader")
	glass_mat.set_shader_parameter("body", Vector3(0.45, 0.78, 1.0))
	glass_mat.set_shader_parameter("rim", Vector3(0.78, 0.52, 1.0))
	glass_mat.set_shader_parameter("secondary", Vector3(0.22, 0.14, 0.48))
	glass_mat.set_shader_parameter("gradient_mode", 3)
	glass_mat.set_shader_parameter("finish_mode", 1)
	glass_mat.set_shader_parameter("alpha", 0.88)
	glass_mat.set_shader_parameter("pulse_speed", 0.8)
	glass.material_override = glass_mat
	magic_mirror.add_child(glass)

	var light := OmniLight3D.new()
	light.light_color = Color(0.68, 0.52, 1.0)
	light.light_energy = 1.4
	light.omni_range = 4.5
	light.position = Vector3(0, 1.15, 0.35)
	light.shadow_enabled = false
	magic_mirror.add_child(light)

	var wisps := Fx.wisps(Color(0.75, 0.55, 1.0), 2.5, 2.2, 0.35)
	wisps.position = Vector3(0, 1.0, 0.1)
	magic_mirror.add_child(wisps)


func mirror_pos() -> Vector3:
	return magic_mirror.global_position + Vector3(0, 0, -0.7) if magic_mirror else Vector3.ZERO


func _build_nodes() -> void:
	var weed_props := {}
	for inst in Game.layout.get("instances", []):
		if inst["prop"] == "weed_clump":
			var p: Array = inst["pos"]
			weed_props[Vector2i(int(floor(float(p[0]))), int(floor(float(p[2]))))] = instances.get(inst["id"])
	for nd in Game.population.get("nodes", {}).get("list", []):
		var entry := {"data": nd, "alive": true, "node": null, "cell": null}
		var p: Array = nd["pos"]
		var pos := Vector3(p[0], p[1], p[2])
		if nd.get("block") == null:
			var key := Vector2i(int(floor(pos.x)), int(floor(pos.z)))
			var vis: Node3D = weed_props.get(key)
			if vis == null:
				var ps := scene("res://assets/props/weed_clump.gltf")
				vis = ps.instantiate()
				vis.position = pos
				vis.rotation.y = randf() * TAU
				add_child(vis)
				_prepare(vis, "weed_clump")
			if nd["kind"] == "grave_weeds":
				vis.scale = Vector3(1.15, 1.25, 1.15)
			entry["node"] = vis
		else:
			var cell := Vector3i(int(floor(pos.x)), int(floor(pos.y)) - 1, int(floor(pos.z)))
			if nd.has("cell"):
				var c: Array = nd["cell"]
				cell = Vector3i(int(c[0]), int(c[1]), int(c[2]))
			entry["cell"] = cell
			cell_nodes[cell] = nd["id"]
		gather_nodes[nd["id"]] = entry
		var left := float(Game.nodes_state.get(nd["id"], 0.0))
		if left > 0.0:
			set_node_alive(String(nd["id"]), false)


func set_node_alive(id: String, alive: bool) -> void:
	var e: Dictionary = gather_nodes.get(id, {})
	if e.is_empty():
		return
	e["alive"] = alive
	if e["node"] != null:
		(e["node"] as Node3D).visible = alive
	elif alive and e["cell"] != null:
		var b := Game.blocks.index_of(String(e["data"]["block"]))
		if world.get_block_v(e["cell"]) == 0:
			world.set_block(e["cell"], b)


## Weed/grass nodes the ray passes near (within `reach`). Returns {id, dist} or {}.
func pick_prop_node(from: Vector3, dir: Vector3, reach: float) -> Dictionary:
	var best := {}
	var best_d := reach
	for id: String in gather_nodes:
		var e: Dictionary = gather_nodes[id]
		if not e["alive"] or e["node"] == null:
			continue
		var c: Vector3 = (e["node"] as Node3D).global_position + Vector3(0, 0.3, 0)
		var t := (c - from).dot(dir)
		if t < 0.0 or t > best_d:
			continue
		if (from + dir * t).distance_to(c) < 0.55:
			best_d = t
			best = {"id": id, "dist": t}
	return best


func tick_nodes(dt: float) -> void:
	var mult := Game.tuning.f("nodes.regrow_mult", 1.0)
	for id: String in Game.nodes_state.keys():
		var left := float(Game.nodes_state[id]) - dt / maxf(mult, 0.01)
		var e: Dictionary = gather_nodes.get(id, {})
		var cond := String(e.get("data", {}).get("regrow", {}).get("condition", ""))
		if left <= 0.0:
			if cond != "" and float(Game.town.remembrance.get(e["data"].get("area", ""), 1.0)) < 0.5:
				Game.nodes_state[id] = 30.0
				continue
			Game.nodes_state.erase(id)
			set_node_alive(id, true)
		else:
			Game.nodes_state[id] = left


func _build_fx() -> void:
	for f in Game.population.get("fx", {}).get("list", []):
		var moods: Array = f.get("moods", ["dusk", "night", "dawn", "day"])
		var col := Color(f.get("color", "#ffffff"))
		var node: Node3D = null
		match String(f["type"]):
			"chimney_smoke":
				node = Fx.smoke(col, float(f.get("alpha", 0.45)))
			"fireflies":
				node = Fx.fireflies(f["box"], int(f.get("count", 30)), col)
			"waterfall_spray":
				node = Fx.spray(col)
			"ore_wisps":
				node = Fx.wisps(col, float(f.get("rate", 1.2)), float(f.get("lifetime_s", 3.5)), float(f.get("rise_mps", 0.35)))
			"low_mist":
				node = Fx.mist(f["box"], col)
			"portal_glow":
				node = Fx.wisps(col, 3.0, 4.0, 0.3)
				var l := OmniLight3D.new()
				l.light_color = col
				l.light_energy = 1.6
				l.omni_range = float(f.get("light_range_m", 5.0))
				node.add_child(l)
			"worker_ghost":
				node = _worker_ghost(f)
			"grave_wisps":
				for inst in Game.layout.get("instances", []):
					if (f["attach"]["props"] as Array).has(inst["prop"]) and instances.has(inst["id"]):
						var w := Fx.wisps(col, 0.5, 4.0, 0.25)
						var anchor := _find_prefix(instances[inst["id"]], "FX_wisp")
						(anchor if anchor else instances[inst["id"]]).add_child(w)
						fx_nodes.append({"node": w, "moods": moods})
				continue
			"hearth_flame":
				for inst in Game.layout.get("instances", []):
					if inst["prop"] == "hearth" and instances.has(inst["id"]):
						var anchor := _find_prefix(instances[inst["id"]], "FX_flame")
						var hf := Fx.flame(col, 0.25, 22)
						(anchor if anchor else instances[inst["id"]]).add_child(hf)
				continue
			_:
				continue
		if node == null:
			continue
		if f.has("pos"):
			var p: Array = f["pos"]
			node.position = Vector3(p[0], p[1], p[2])
		add_child(node)
		fx_nodes.append({"node": node, "moods": moods})


func _worker_ghost(f: Dictionary) -> Node3D:
	var ps := scene(String(f["gltf"]))
	if ps == null:
		return null
	var n: Node3D = ps.instantiate()
	n.rotation.y = deg_to_rad(float(f.get("yaw", 0.0)))
	var ap := n.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if ap and ap.has_animation(String(f.get("animation", "idle_float"))):
		var a := ap.get_animation(String(f.get("animation", "idle_float")))
		a.loop_mode = Animation.LOOP_LINEAR
		ap.play(String(f.get("animation", "idle_float")))
	Actors.ghostify(n, 0.55)
	return n


func set_mood(phase: String, emission: Dictionary, window_energy: float) -> void:
	var windows_on: bool = emission.get("windows", true)
	var lanterns_on: bool = emission.get("lanterns", true)
	for m in glow_materials:
		m.emission_enabled = true
		m.emission_energy_multiplier = window_energy if windows_on else 0.0
	for l in window_lights:
		l.visible = windows_on
	for id: String in hauntables:
		var h: Hauntable = hauntables[id]
		if h.kind == "lantern" and h.data.get("source") != "carried":
			h.set_mood_on(lanterns_on)
	for e in fx_nodes:
		var on: bool = (e["moods"] as Array).has(phase)
		(e["node"] as Node3D).visible = on
		for c in (e["node"] as Node3D).get_children():
			if c is GPUParticles3D:
				(c as GPUParticles3D).emitting = on
		if e["node"] is GPUParticles3D:
			(e["node"] as GPUParticles3D).emitting = on


func _process(dt: float) -> void:
	_t += dt
	if sails:
		sails.rotation.z += dt * TAU * 3.5 / 60.0
	if sign_node:
		sign_node.rotation.x = deg_to_rad(6.0) * sin(_t * TAU / 3.2)


# ---------------------------------------------------------------- charms and salt

func show_charm(object_id: String, charm: String) -> void:
	if charm_nodes.has(object_id):
		return
	var h: Hauntable = hauntables.get(object_id)
	if h == null:
		return
	var c := Fx.charm(charm)
	add_child(c)
	c.global_position = h.world_pos() + Vector3(0, 0.25 if h.is_light() else 1.6, 0)
	charm_nodes[object_id] = c


func clear_charms_not_in(active: Dictionary) -> void:
	for k: String in charm_nodes.keys():
		if not active.has(k):
			(charm_nodes[k] as Node).queue_free()
			charm_nodes.erase(k)


func show_salt(door_id: String) -> void:
	if salt_nodes.has(door_id):
		return
	var m: Dictionary = Game.markers_by_id.get(door_id, {})
	if m.is_empty():
		return
	var p: Array = m["pos"]
	var sb := StaticBody3D.new()
	sb.collision_layer = VoxelWorld.L_BARRIER
	sb.collision_mask = 0
	sb.position = Vector3(p[0], p[1], p[2])
	sb.rotation.y = deg_to_rad(float(m.get("yaw", 0.0)))
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(1.4, 3.0, 0.5)
	cs.shape = box
	cs.position = Vector3(0, 1.5, 0.55)
	sb.add_child(cs)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(1.3, 0.04, 0.22)
	mi.mesh = bm
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.97, 0.96, 0.92)
	mat.emission_enabled = true
	mat.emission = Color(0.85, 0.9, 1.0)
	mat.emission_energy_multiplier = 0.25
	mi.material_override = mat
	mi.position = Vector3(0, 0.03, 0.55)
	sb.add_child(mi)
	add_child(sb)
	salt_nodes[door_id] = sb


func clear_salt_not_in(active: Dictionary) -> void:
	for k: String in salt_nodes.keys():
		if not active.has(k):
			(salt_nodes[k] as Node).queue_free()
			salt_nodes.erase(k)
