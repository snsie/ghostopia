## Particle and small procedural effects built in code: flames, smoke, wisps, fireflies, spray,
## mist, memory-fragment wisps, scatter bursts, block cracks, charms.
class_name Fx
extends RefCounted

static var _soft_tex: Texture2D


static func soft_texture() -> Texture2D:
	if _soft_tex == null:
		var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
		for y in 32:
			for x in 32:
				var d := Vector2(x - 15.5, y - 15.5).length() / 15.5
				var a := clampf(1.0 - d, 0.0, 1.0)
				img.set_pixel(x, y, Color(1, 1, 1, a * a))
		_soft_tex = ImageTexture.create_from_image(img)
	return _soft_tex


static func _quad_mat(col: Color, additive: bool, energy: float = 1.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD if additive else BaseMaterial3D.BLEND_MODE_MIX
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.albedo_texture = soft_texture()
	m.albedo_color = Color(col.r * energy, col.g * energy, col.b * energy, col.a)
	m.vertex_color_use_as_albedo = true
	m.no_depth_test = false
	m.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	return m


static func _particles(amount: int, life: float, col: Color, size: float, additive: bool, energy: float = 1.0) -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = maxi(1, amount)
	p.lifetime = life
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	q.material = _quad_mat(col, additive, energy)
	p.draw_pass_1 = q
	var pm := ParticleProcessMaterial.new()
	pm.gravity = Vector3.ZERO
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 0))
	g.add_point(0.2, Color(1, 1, 1, 1))
	g.set_color(g.get_point_count() - 1, Color(1, 1, 1, 0))
	var gt := GradientTexture1D.new()
	gt.gradient = g
	pm.color_ramp = gt
	p.process_material = pm
	p.visibility_aabb = AABB(Vector3(-4, -2, -4), Vector3(8, 10, 8))
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return p


static func flame(col: Color, size: float = 0.07, amount: int = 8) -> GPUParticles3D:
	var p := _particles(amount, 0.4, col, size, true, 1.6)
	var pm: ParticleProcessMaterial = p.process_material
	pm.direction = Vector3.UP
	pm.spread = 12.0
	pm.initial_velocity_min = 0.12
	pm.initial_velocity_max = 0.3
	pm.scale_min = 0.6
	pm.scale_max = 1.0
	return p


static func smoke(col: Color, alpha: float) -> GPUParticles3D:
	var p := _particles(14, 6.0, Color(col.r, col.g, col.b, alpha), 1.1, false)
	var pm: ParticleProcessMaterial = p.process_material
	pm.direction = Vector3(0.2, 1, 0.08)
	pm.spread = 10.0
	pm.initial_velocity_min = 0.5
	pm.initial_velocity_max = 0.8
	pm.scale_min = 0.5
	pm.scale_max = 1.4
	var sc := Curve.new()
	sc.add_point(Vector2(0, 0.4))
	sc.add_point(Vector2(1, 1.6))
	var ct := CurveTexture.new()
	ct.curve = sc
	pm.scale_curve = ct
	p.visibility_aabb = AABB(Vector3(-5, -1, -5), Vector3(10, 12, 10))
	return p


static func wisps(col: Color, rate: float, life: float, rise: float) -> GPUParticles3D:
	var p := _particles(maxi(2, int(rate * life)), life, col, 0.12, true, 2.0)
	var pm: ParticleProcessMaterial = p.process_material
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	pm.emission_sphere_radius = 0.35
	pm.direction = Vector3.UP
	pm.spread = 25.0
	pm.initial_velocity_min = rise * 0.6
	pm.initial_velocity_max = rise
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 0.4
	return p


static func fireflies(box: Array, count: int, col: Color) -> GPUParticles3D:
	var p := _particles(count, 4.0, col, 0.09, true, 3.0)
	var pm: ParticleProcessMaterial = p.process_material
	var lo := Vector3(box[0], box[1], box[2])
	var hi := Vector3(box[3], box[4], box[5])
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = (hi - lo) * 0.5
	pm.initial_velocity_min = 0.05
	pm.initial_velocity_max = 0.3
	pm.spread = 180.0
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 1.2
	p.position = (lo + hi) * 0.5
	p.visibility_aabb = AABB(-(hi - lo) * 0.6, (hi - lo) * 1.2)
	return p


static func spray(col: Color) -> GPUParticles3D:
	var p := _particles(24, 1.2, Color(col.r, col.g, col.b, 0.5), 0.35, false)
	var pm: ParticleProcessMaterial = p.process_material
	pm.direction = Vector3(0, 1, 0.6)
	pm.spread = 50.0
	pm.initial_velocity_min = 0.6
	pm.initial_velocity_max = 1.4
	pm.gravity = Vector3(0, -2.0, 0)
	return p


static func mist(box: Array, col: Color) -> GPUParticles3D:
	var p := _particles(60, 9.0, Color(col.r, col.g, col.b, 0.13), 4.0, false)
	var pm: ParticleProcessMaterial = p.process_material
	var lo := Vector3(box[0], box[1], box[2])
	var hi := Vector3(box[3], box[4], box[5])
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = (hi - lo) * 0.5
	pm.direction = Vector3(1, 0, 0.3)
	pm.spread = 30.0
	pm.initial_velocity_min = 0.1
	pm.initial_velocity_max = 0.25
	p.position = (lo + hi) * 0.5
	p.visibility_aabb = AABB(-(hi - lo) * 0.6, (hi - lo) * 1.2)
	return p


## A one-shot burst (scatter wisps, BOO puff, block break dust). Frees itself.
static func burst(parent: Node, pos: Vector3, col: Color, amount: int, speed: float, life: float, size: float = 0.12,
		additive: bool = true) -> void:
	var p := _particles(amount, life, col, size, additive, 2.0)
	p.one_shot = true
	p.explosiveness = 0.95
	var pm: ParticleProcessMaterial = p.process_material
	pm.direction = Vector3.UP
	pm.spread = 180.0
	pm.initial_velocity_min = speed * 0.4
	pm.initial_velocity_max = speed
	pm.gravity = Vector3(0, -0.5, 0)
	parent.add_child(p)
	p.global_position = pos
	p.emitting = true
	p.finished.connect(p.queue_free)


## Glowing memory wisp that floats out of a mined block.
static func memory_wisp() -> Node3D:
	var root := Node3D.new()
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.12
	sm.height = 0.24
	mi.mesh = sm
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(1.0, 0.86, 0.55)
	m.emission_enabled = true
	m.emission = Color(1.0, 0.8, 0.5)
	m.emission_energy_multiplier = 4.0
	mi.material_override = m
	root.add_child(mi)
	var trail := wisps(Color(1.0, 0.85, 0.6), 8.0, 0.8, 0.1)
	root.add_child(trail)
	var l := OmniLight3D.new()
	l.light_color = Color(1.0, 0.82, 0.55)
	l.light_energy = 1.2
	l.omni_range = 3.0
	root.add_child(l)
	return root


## A charm villagers hang on a used object: garlic and lavender, a horseshoe, a salt vial.
static func charm(kind: String) -> Node3D:
	var root := Node3D.new()
	var string_m := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.008
	cyl.bottom_radius = 0.008
	cyl.height = 0.25
	string_m.mesh = cyl
	string_m.position = Vector3(0, 0.12, 0)
	var sm := StandardMaterial3D.new()
	sm.albedo_color = Color(0.45, 0.32, 0.2)
	string_m.material_override = sm
	root.add_child(string_m)
	var body := MeshInstance3D.new()
	var bm := StandardMaterial3D.new()
	match kind:
		"horseshoe":
			var t := TorusMesh.new()
			t.inner_radius = 0.06
			t.outer_radius = 0.09
			body.mesh = t
			body.rotation.x = PI / 2
			bm.albedo_color = Color(0.55, 0.55, 0.6)
			bm.metallic = 0.8
		"salt_vial":
			var c := CylinderMesh.new()
			c.top_radius = 0.035
			c.bottom_radius = 0.045
			c.height = 0.12
			body.mesh = c
			bm.albedo_color = Color(0.92, 0.95, 1.0, 0.8)
			bm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_:
			var s := SphereMesh.new()
			s.radius = 0.06
			s.height = 0.11
			body.mesh = s
			bm.albedo_color = Color(0.95, 0.92, 0.8)
			var lav := MeshInstance3D.new()
			var ls := CapsuleMesh.new()
			ls.radius = 0.02
			ls.height = 0.16
			lav.mesh = ls
			lav.position = Vector3(0.05, 0.04, 0)
			lav.rotation.z = -0.4
			var lm := StandardMaterial3D.new()
			lm.albedo_color = Color(0.65, 0.5, 0.9)
			lav.material_override = lm
			root.add_child(lav)
	body.material_override = bm
	root.add_child(body)
	return root


## Crack overlay cube for a block being mined; `stage` 0..1.
static func crack_material(stage: float) -> StandardMaterial3D:
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var rng := RandomNumberGenerator.new()
	rng.seed = 99
	var lines := int(2 + stage * 9)
	for i in lines:
		var p := Vector2(32, 32) + Vector2(rng.randf_range(-6, 6), rng.randf_range(-6, 6))
		var a := rng.randf() * TAU
		var length := 10.0 + stage * 26.0
		for s in int(length):
			a += rng.randf_range(-0.5, 0.5)
			p += Vector2(cos(a), sin(a))
			if p.x >= 0 and p.y >= 0 and p.x < 64 and p.y < 64:
				img.set_pixelv(Vector2i(p), Color(0.05, 0.02, 0.08, 0.85))
	var m := StandardMaterial3D.new()
	m.albedo_texture = ImageTexture.create_from_image(img)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	return m
