## A promoted undead: one of the ~32 units nearest the ghost, owned by the CPU. It is a real node the
## ghost can hit with its tools, Read (HUD) and later possess or talk to. Its rules run in the near tier's
## CPU sim (the same rules as the crowd); this node only holds the unit record and shows it, using the
## same mesh and baked animation as the crowd so promotion doesn't pop.
class_name NearActor
extends CharacterBody3D

const L := preload("res://scripts/battle/crowd_layout.gd")

var index := -1                    # the unit's index in the crowd buffer
var rec := PackedFloat32Array()    # authoritative state while promoted (global TARGET/STRIKE)
var pending_dmg := 0.0             # melee damage that lands next step
var aggro := 0.0                   # seconds left angry at the ghost
var swing_cd := 0.0                # cooldown of swings at the ghost
var mesh_node: MeshInstance3D
var _clan := -1


func _init() -> void:
	collision_layer = VoxelWorld.L_ACTORS
	collision_mask = 0
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.7
	cs.shape = cap
	cs.position.y = 0.85
	add_child(cs)
	mesh_node = MeshInstance3D.new()
	mesh_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mesh_node)


func bind(i: int, record: PackedFloat32Array, kit: UnitKit, mat: ShaderMaterial) -> void:
	index = i
	rec = record.duplicate()
	rec[L.ACTOR] = 1.0
	pending_dmg = 0.0
	aggro = 0.0
	swing_cd = 0.0
	var clan := int(rec[L.CLAN])
	if clan != _clan:
		mesh_node.mesh = kit.mesh
		mesh_node.material_override = mat
		_clan = clan
	visible = true
	sync_visual(0.0)


func clan() -> int:
	return int(rec[L.CLAN])


func state() -> int:
	return int(rec[L.STATE])


func alive() -> bool:
	return state() == L.FIGHT or state() == L.ROUT


func head_pos() -> Vector3:
	return global_position + Vector3(0, 1.5, 0)


func sync_visual(dissolve_s: float) -> void:
	global_position = Vector3(rec[L.PX], rec[L.PY], rec[L.PZ])
	rotation = Vector3(0, rec[L.YAW], 0)
	var code := 0.0
	var st := state()
	if st == L.ROUT:
		code = 0.5
	elif st == L.SCATTERED:
		code = 1.0 + clampf(rec[L.STATE_T] / maxf(dissolve_s, 0.01), 0.0, 1.0)
	mesh_node.set_instance_shader_parameter("actor_anim", Vector4(rec[L.CLIP], rec[L.ANIM_T], code, rec[L.FLASH]))
