## Loads a clan unit written by blender/scripts/build_battle_units.py (mesh + vertex-animation
## texture) into an ArrayMesh, an RGBAH ImageTexture and a ShaderMaterial for crowd_unit.gdshader.
## The same mesh and VAT drive the crowd's MultiMesh and the near actors, so a promoted unit doesn't pop.
class_name UnitKit
extends RefCounted

const SHADER := "res://shaders/crowd_unit.gdshader"

var id := ""
var meta: Dictionary = {}
var mesh: ArrayMesh
var vat: ImageTexture
var clip_vec: Array[Vector4] = []   # (start row, frames, fps, loop) per clip, CLIP_* order
var height := 1.8

static var _cache: Dictionary = {}


static func load_unit(unit_id: String) -> UnitKit:
	if _cache.has(unit_id):
		return _cache[unit_id]
	var k := UnitKit.new()
	k.id = unit_id
	var meta_v: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://assets/battle/units/%s.json" % unit_id))
	if not meta_v is Dictionary:
		push_error("UnitKit: missing unit %s" % unit_id)
		return null
	k.meta = meta_v
	var vc := int(k.meta["vertex_count"])
	var ic := int(k.meta["index_count"])
	var raw := FileAccess.get_file_as_bytes(String(k.meta["mesh"]))
	var pos := raw.slice(0, vc * 12).to_float32_array()
	var nrm := raw.slice(vc * 12, vc * 24).to_float32_array()
	var col := raw.slice(vc * 24, vc * 40).to_float32_array()
	var idx := raw.slice(vc * 40, vc * 40 + ic * 4).to_int32_array()
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var colors := PackedColorArray()
	verts.resize(vc)
	norms.resize(vc)
	colors.resize(vc)
	for i in vc:
		verts[i] = Vector3(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2])
		norms[i] = Vector3(nrm[i * 3], nrm[i * 3 + 1], nrm[i * 3 + 2])
		colors[i] = Color(col[i * 4], col[i * 4 + 1], col[i * 4 + 2], col[i * 4 + 3])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_INDEX] = idx
	k.mesh = ArrayMesh.new()
	k.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var b: Dictionary = k.meta["bounds"]
	var lo := Vector3(b["min"][0], b["min"][1], b["min"][2])
	var hi := Vector3(b["max"][0], b["max"][1], b["max"][2])
	k.mesh.custom_aabb = AABB(lo, hi - lo)
	k.height = float(k.meta.get("height_m", 1.8))
	var size: Array = k.meta["vat_size"]
	var img := Image.create_from_data(int(size[0]), int(size[1]), false, Image.FORMAT_RGBAH,
		FileAccess.get_file_as_bytes(String(k.meta["vat"])))
	k.vat = ImageTexture.create_from_image(img)
	for name: String in k.meta.get("clip_order", []):
		var c: Dictionary = k.meta["clips"][name]
		k.clip_vec.append(Vector4(float(c["start"]), float(c["frames"]), float(c["fps"]), 1.0 if c["loop"] else 0.0))
	_cache[unit_id] = k
	return k


## A material for this unit. `multimesh` = read the animation from INSTANCE_CUSTOM; otherwise from
## the `actor_anim` instance uniform (near actors).
func material(multimesh: bool, tint: Color) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load(SHADER)
	m.set_shader_parameter("vat", vat)
	m.set_shader_parameter("frames", int(meta["frames"]))
	m.set_shader_parameter("clips", clip_vec)
	m.set_shader_parameter("tint", tint)
	m.set_shader_parameter("use_instance_custom", multimesh)
	return m
