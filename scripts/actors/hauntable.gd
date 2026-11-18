## One hauntable object (population `hauntables[]`): a door, floorboard, candle, lamp or lantern in
## the world, or the light in a villager's hand. Plays the act on its `INT_` parts, dims/snuffs its
## `LIGHT_`/`FLAME_` nodes and shows its `HAUNT_` glow shell while haunted.
class_name Hauntable
extends Node

signal acted(h: Hauntable, action: String)

var id: String
var kind: String
var data: Dictionary
var root: Node3D
var int_nodes: Array[Node3D] = []
var lights: Array[OmniLight3D] = []
var flames: Array[Node3D] = []
var haunt_nodes: Array[Node3D] = []
var particles: Array[GPUParticles3D] = []
var rest_rot: Array[Vector3] = []
var rest_pos: Array[Vector3] = []
var base_energy: Array[float] = []

var lit := true
var dimmed := false
var mood_on := true          # lanterns are off by day
var door_open := 0.0         # 0..1
var _door_target := 0.0
var _hold_open_until := 0.0
var _glow_until := 0.0
var _cooldown_until := 0.0
var _dim_until := 0.0
var _flicker_phase := randf() * 10.0
var _tween: Tween


func setup(p_id: String, p_data: Dictionary, p_root: Node3D) -> void:
	id = p_id
	data = p_data
	kind = String(p_data.get("kind", ""))
	root = p_root
	name = "H_" + id
	_collect(root)
	for n in int_nodes:
		rest_rot.append(n.rotation)
		rest_pos.append(n.position)
	for l in lights:
		base_energy.append(l.light_energy)
	for h in haunt_nodes:
		h.visible = false


func _collect(n: Node) -> void:
	var nm := String(n.name)
	if nm.begins_with("INT_") and n is Node3D and not nm.ends_with("-colonly") and not (n is CollisionObject3D):
		var under_int := false
		var p := n.get_parent()
		while p != null and p != root.get_parent():
			if String(p.name).begins_with("INT_"):
				under_int = true
			p = p.get_parent()
		if not under_int:
			int_nodes.append(n)
	if n is OmniLight3D and nm.begins_with("LIGHT_"):
		lights.append(n)
	if nm.begins_with("FLAME_") and n is Node3D:
		flames.append(n)
	if nm.begins_with("HAUNT_") and n is Node3D:
		haunt_nodes.append(n)
	if n is GPUParticles3D:
		particles.append(n)
	for c in n.get_children():
		_collect(c)


func world_pos() -> Vector3:
	if not int_nodes.is_empty() and is_instance_valid(int_nodes[0]):
		return int_nodes[0].global_position
	return root.global_position if is_instance_valid(root) else Vector3.ZERO


func ability() -> String:
	return String(data.get("ability", ""))


func is_light() -> bool:
	return ability() == "flicker"


func on_cooldown(now: float) -> bool:
	return now < _cooldown_until


## Actions the ghost can use on it now: [gentle, strong].
func actions() -> Array:
	return data.get("actions", [])


func gentle_action() -> String:
	var a := actions()
	return String(a[0]) if a.size() > 0 else ""


func strong_action() -> String:
	var a := actions()
	if kind == "door":
		return "drift_open"   # slam is Haunted Furniture (level 3)
	if kind == "rocking_chair":
		return "rock_wildly"
	if kind == "portrait":
		return "tilt_portrait"
	return String(a[1]) if a.size() > 1 else ""


func can_act(action: String) -> bool:
	if is_light():
		return lit and mood_on
	return action != ""


func act(action: String, now: float) -> void:
	_cooldown_until = now + float(data.get("cooldown_s", 6.0))
	show_glow(Game.tuning.f("haunting.haunt_glow_s", 1.6))
	if ability() == "haunted_furniture":
		_animate_furniture(action == strong_action())
		acted.emit(self, action)
		return
	match action:
		"creak":
			if kind == "door":
				_swing_door(0.18, 0.5)
				Sfx.play_at("creak_door", world_pos(), 2.0)
			else:
				_creak_board()
				Sfx.play_at("creak_floor", world_pos(), 0.0)
		"drift_open":
			_door_target = 1.0
			_hold_open_until = now + 7.0
			Sfx.play_at("creak_door", world_pos(), 3.0, 30.0, 0.15)
		"slam":
			_door_target = 0.0
			Sfx.play_at("door_slam", world_pos(), 4.0)
		"dim":
			set_dim(true, now + 14.0)
			Sfx.play_at("whoosh", world_pos(), -8.0)
		"snuff":
			set_lit(false)
			Sfx.play_at("candle_snuff", world_pos(), 0.0)
	acted.emit(self, action)


func _animate_furniture(strong: bool) -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween().set_parallel(true)
	for i in int_nodes.size():
		var part := int_nodes[i]
		if part is StaticBody3D:
			continue
		var rest := rest_rot[i]
		var axis := Vector3.RIGHT if kind == "rocking_chair" else Vector3.UP
		var amount := 0.36 if strong else 0.13
		_tween.tween_property(part, "rotation", rest + axis * amount, 0.14)
	_tween.chain().set_parallel(true)
	for i in int_nodes.size():
		if not int_nodes[i] is StaticBody3D:
			_tween.tween_property(int_nodes[i], "rotation", rest_rot[i], 0.4)
	Sfx.play_at("creak_door", world_pos(), 0.0 if strong else -8.0)


func set_lit(v: bool) -> void:
	lit = v
	dimmed = false
	_apply_light()
	if v:
		Sfx.play_at("candle_relight", world_pos(), -6.0)


func set_dim(v: bool, until: float = 0.0) -> void:
	dimmed = v
	_dim_until = until
	_apply_light()


func set_mood_on(v: bool) -> void:
	if mood_on == v:
		return
	mood_on = v
	_apply_light()


func _apply_light() -> void:
	var on := lit and mood_on
	var k := Game.tuning.f("haunting.dim_energy", 0.3) if dimmed else 1.0
	for f in flames:
		f.visible = on
		f.scale = Vector3.ONE * (0.55 if dimmed else 1.0)
	for i in lights.size():
		lights[i].visible = on
		lights[i].light_energy = base_energy[i] * k
	for p in particles:
		p.emitting = on


func show_glow(seconds: float) -> void:
	_glow_until = Time.get_ticks_msec() / 1000.0 + seconds
	for h in haunt_nodes:
		h.visible = true


func open_for_villager(now: float) -> void:
	if kind != "door":
		return
	_door_target = maxf(_door_target, 0.85)
	_hold_open_until = maxf(_hold_open_until, now + 1.5)


func _swing_door(amount: float, secs: float) -> void:
	if int_nodes.is_empty():
		return
	if _tween:
		_tween.kill()
	_tween = create_tween()
	var n := int_nodes[0]
	var base := rest_rot[0].y + door_open * deg_to_rad(80.0)
	_tween.tween_property(n, "rotation:y", base + amount, secs * 0.6).set_trans(Tween.TRANS_SINE)
	_tween.tween_property(n, "rotation:y", base + amount * 0.4, secs * 0.4)
	_tween.tween_property(n, "rotation:y", base, secs).set_trans(Tween.TRANS_SINE)


func _creak_board() -> void:
	if int_nodes.is_empty():
		return
	var n := int_nodes[0]
	var tw := create_tween()
	tw.tween_property(n, "position:y", rest_pos[0].y - 0.025, 0.15)
	tw.tween_property(n, "position:y", rest_pos[0].y + 0.01, 0.2)
	tw.tween_property(n, "position:y", rest_pos[0].y, 0.3)


func _process(dt: float) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	if not haunt_nodes.is_empty() and haunt_nodes[0].visible and now > _glow_until:
		for h in haunt_nodes:
			h.visible = false
	if kind == "door" and not int_nodes.is_empty():
		var t := _door_target
		if Game.get_tree().paused:
			return
		if now > _hold_open_until:
			_door_target = 0.0
		if absf(door_open - t) > 0.001:
			door_open = move_toward(door_open, t, dt * (0.35 if t > door_open else 1.2))
			if not (_tween and _tween.is_running()):
				int_nodes[0].rotation.y = rest_rot[0].y + door_open * deg_to_rad(80.0)
	if dimmed and _dim_until > 0.0 and now > _dim_until:
		set_dim(false)
	if lit and mood_on and not lights.is_empty():
		_flicker_phase += dt * 9.0
		var fl := 1.0 + 0.07 * sin(_flicker_phase) * sin(_flicker_phase * 0.37 + 1.3)
		var k := Game.tuning.f("haunting.dim_energy", 0.3) if dimmed else 1.0
		for i in lights.size():
			lights[i].light_energy = base_energy[i] * k * fl
