## Helpers shared by the ghost, villagers and worker ghosts: animation loop flags from
## characters.json, translucent ghost materials, node lookup by prefix.
class_name Actors
extends RefCounted


static func find_prefix(n: Node, prefix: String) -> Node:
	if n == null:
		return null
	if String(n.name).begins_with(prefix):
		return n
	for c in n.get_children():
		var r := find_prefix(c, prefix)
		if r:
			return r
	return null


static func find_all_prefix(n: Node, prefix: String, out: Array) -> void:
	if String(n.name).begins_with(prefix):
		out.append(n)
	for c in n.get_children():
		find_all_prefix(c, prefix, out)


static func setup_loops(ap: AnimationPlayer, char_data: Dictionary) -> void:
	var clips: Dictionary = char_data.get("clips", {})
	for name in ap.get_animation_list():
		var a := ap.get_animation(name)
		var c: Dictionary = clips.get(String(name), {})
		a.loop_mode = Animation.LOOP_LINEAR if c.get("loop", false) else Animation.LOOP_NONE


## Swaps the ghost sheet material(s) for the translucent ghost shader.
static func ghostify(n: Node, alpha: float) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/ghost.gdshader")
	mat.set_shader_parameter("alpha", alpha)
	var meshes: Array = []
	find_all_prefix(n, "", meshes)
	for m in meshes:
		if m is MeshInstance3D:
			var mi := m as MeshInstance3D
			if mi.mesh == null:
				continue
			for s in mi.mesh.get_surface_count():
				var sm := mi.mesh.surface_get_material(s)
				var nm := String(sm.resource_name) if sm else ""
				if nm.begins_with("GHOST_") or nm.begins_with("WORKER_") or nm.contains("sheet") or nm.contains("ghost"):
					mi.set_surface_override_material(s, mat)
	return mat


static func set_shape(mesh: MeshInstance3D, key: String, v: float) -> void:
	if mesh == null or mesh.mesh == null:
		return
	var i := mesh.find_blend_shape_by_name(key)
	if i >= 0:
		mesh.set_blend_shape_value(i, v)
