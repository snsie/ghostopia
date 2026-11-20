## The near tier: the ~32 units closest to the ghost become NearActor nodes run on the CPU, and go back
## to the crowd when the ghost moves away, carrying their state (position, Form, Resolve, clan, animation).
##
## Each frame the actors step in a small CPU sim (CrowdSimCpu) together with the crowd units around them
## from the latest crowd snapshot, frozen as neighbours, so they follow exactly the crowd's rules.
## Their records go back into the crowd buffer flagged ACTOR, so the crowd fights them, separates from
## them and feels them break. Blows between the tiers:
##   actor -> crowd: a single-target hit sphere in the crowd sim
##   crowd -> actor: the crowd unit's swing rate applied on the CPU when its target is the actor
## (the crowd's own accumulator for an actor is discarded; decisions.md).
class_name NearTier
extends Node3D

const L := preload("res://scripts/battle/crowd_layout.gd")

signal unit_routed(actor: NearActor)
signal unit_scattered(actor: NearActor)

var sim                                  # CrowdSimCpu or CrowdSimGpu (the crowd)
var p: CrowdParams
var terrain: BattleTerrain
var max_count := 32
var promote_r := 9.0
var demote_r := 12.0
var actors: Array[NearActor] = []
var by_index: Dictionary = {}            # crowd index -> NearActor
var routs := PackedInt32Array([0, 0, 0, 0])
var scatters := PackedInt32Array([0, 0, 0, 0])
var promotions := 0
var demotions := 0
var enabled := true

var _mini := CrowdSimCpu.new()
var _pool: Array[NearActor] = []
var _kits: Array[UnitKit] = []
var _mats: Array[ShaderMaterial] = []
var _snapshot: Array[PackedFloat32Array] = []
var _snap_age := 0.0
var _snap_fresh := false
var _last_rb := -1
var _clan_params := PackedFloat32Array()
var _spheres := PackedFloat32Array()
var _requested: Dictionary = {}          # GPU: crowd index -> snapshots waited for the GPU to accept


func setup(p_sim, params: CrowdParams, p_terrain: BattleTerrain, kits: Array[UnitKit], mats: Array[ShaderMaterial],
		clan_params: PackedFloat32Array, tuning_near: Dictionary) -> void:
	sim = p_sim
	p = params
	terrain = p_terrain
	_kits = kits
	_mats = mats
	_clan_params = clan_params.duplicate()
	max_count = int(tuning_near.get("count", 32))
	promote_r = float(tuning_near.get("promote_radius_m", 9.0))
	demote_r = float(tuning_near.get("demote_radius_m", 12.0))
	_mini.write_multimesh = false
	_mini.setup(terrain, p, PackedInt32Array([0]), PackedInt32Array([0]), PackedFloat32Array(), _clan_params)


func set_clan(c: int, block: PackedFloat32Array) -> void:
	for k in 8:
		_clan_params[c * 8 + k] = block[k]


## The same sphere the crowd gets this frame, so actors feel BOO, throws and clan-wide shocks too.
func add_sphere(center: Vector3, radius: float, form_dmg: float, resolve_dmg: float, clan_mask: int,
		target: int, falloff: float, flags: int) -> void:
	_spheres.append_array(PackedFloat32Array([center.x, center.y, center.z, radius,
		form_dmg, resolve_dmg, float(clan_mask), float(target), falloff, float(flags), 0.0, 0.0]))


func tick(dt: float, ghost: Vector3) -> void:
	_snap_age += dt
	var fresh := false
	if sim is CrowdSimCpu:
		fresh = true
	elif sim.readbacks != _last_rb:
		fresh = true
		_last_rb = sim.readbacks
	if fresh:
		_snapshot = sim.nearby.duplicate()
		_snap_age = 0.0
		_snap_fresh = true
		if enabled:
			_select(ghost)
	if actors.is_empty():
		_spheres.clear()
		return
	_step_actors(dt)
	_spheres.clear()
	_snap_fresh = false


# ---------------------------------------------------------------- promotion / demotion

func _select(ghost: Vector3) -> void:
	var g := Vector2(ghost.x, ghost.z)
	var gpu := not (sim is CrowdSimCpu)
	if gpu:
		# two-phase promotion: build actors only from units the GPU froze for us (exact records)
		for e: PackedFloat32Array in _snapshot:
			var idx := int(e[0])
			var act := e[1 + L.ACTOR]
			if act > 0.25 and act < 0.75 and _requested.has(idx) and not by_index.has(idx):
				_requested.erase(idx)
				_promote(e)
		for idx: int in _requested.keys():
			_requested[idx] = int(_requested[idx]) + 1
			if int(_requested[idx]) > 6:
				_requested.erase(idx)
	# demote the ones the ghost left behind
	for a in actors.duplicate():
		var d := Vector2(a.rec[L.PX], a.rec[L.PZ]).distance_to(g)
		if d > demote_r or a.state() == L.LEFT:
			demote(a)
	# candidates from the crowd snapshot, nearest first (the list is already banded by distance)
	var cands: Array = []
	for e: PackedFloat32Array in _snapshot:
		var idx := int(e[0])
		if by_index.has(idx) or _requested.has(idx) or e[1 + L.ACTOR] > 0.25:
			continue
		var st := int(e[1 + L.STATE])
		if st != L.FIGHT and st != L.ROUT:
			continue
		var d2 := Vector2(e[1 + L.PX], e[1 + L.PZ]).distance_to(g)
		if d2 <= promote_r:
			cands.append([d2, e])
	cands.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
	var swaps := 0
	for c in cands:
		if actors.size() + _requested.size() < max_count:
			_take(c[1], gpu)
			continue
		# full: swap out the farthest actor when this candidate is clearly closer
		var far: NearActor = null
		var far_d := -1.0
		for a in actors:
			var da := Vector2(a.rec[L.PX], a.rec[L.PZ]).distance_to(g)
			if da > far_d:
				far_d = da
				far = a
		if far and float(c[0]) < far_d - 2.5 and swaps < 4:
			demote(far)
			_take(c[1], gpu)
			swaps += 1
		else:
			break


func _take(e: PackedFloat32Array, gpu: bool) -> void:
	if gpu:
		_requested[int(e[0])] = 0
		sim.request_promotion(int(e[0]))
	else:
		_promote(e)


func _promote(e: PackedFloat32Array) -> void:
	var idx := int(e[0])
	var r := e.slice(1, 1 + L.STRIDE)
	if r[L.ACTOR] < 0.25:
		# CPU crowd: the snapshot is this frame's, carried forward along its velocity if it aged
		r[L.PX] += r[L.VX] * _snap_age
		r[L.PZ] += r[L.VZ] * _snap_age
	# (GPU: a pending unit has been frozen since the GPU accepted it, so its record is exact)
	r[L.SPARE1] = 0.0
	r[L.STRIKE] = 0.0
	var a: NearActor
	if _pool.is_empty():
		a = NearActor.new()
		add_child(a)
	else:
		a = _pool.pop_back()
	var clan := int(r[L.CLAN])
	a.bind(idx, r, _kits[clan], _mats[clan])
	actors.append(a)
	by_index[idx] = a
	sim.write_unit(idx, a.rec)
	promotions += 1


## Hands the unit back to the crowd with its current state.
func demote(a: NearActor) -> void:
	var r := a.rec.duplicate()
	r[L.ACTOR] = 0.0
	r[L.STRIKE] = 0.0
	sim.write_unit(a.index, r)
	by_index.erase(a.index)
	actors.erase(a)
	a.visible = false
	a.index = -1
	_pool.append(a)
	demotions += 1


func demote_all() -> void:
	for a in actors.duplicate():
		demote(a)


# ---------------------------------------------------------------- the actors' step

func _step_actors(dt: float) -> void:
	var S := L.STRIDE
	var local: Dictionary = {}           # crowd index -> local index
	var buf := PackedFloat32Array()
	for k in actors.size():
		local[actors[k].index] = k
		var own := actors[k].rec.duplicate()
		own[L.ACTOR] = 0.0          # inside the near tier's own sim the actors are the ones being stepped
		buf.append_array(own)
	var frozen: Array[PackedFloat32Array] = []
	for e: PackedFloat32Array in _snapshot:
		var idx := int(e[0])
		if by_index.has(idx) or local.has(idx):
			continue
		local[idx] = actors.size() + frozen.size()
		var r := e.slice(1, 1 + S)
		r[L.PX] += r[L.VX] * _snap_age
		r[L.PZ] += r[L.VZ] * _snap_age
		var st := int(r[L.STATE])
		# a crowd unit that broke since the last snapshot shocks the actors once, on the fresh frame
		if (st == L.ROUT or st == L.SCATTERED) and _snap_fresh and r[L.STATE_T] <= 0.25:
			r[L.STATE_T] = 0.0
		else:
			r[L.STATE_T] = maxf(r[L.STATE_T], 1.0)
		frozen.append(r)
		buf.append_array(r)
	var n_act := actors.size()
	# global -> local indices for targets and pending strikes
	for k in buf.size() / S:
		var t := int(buf[k * S + L.TARGET])
		buf[k * S + L.TARGET] = float(local.get(t, -1)) if t >= 0 else -1.0
		var s := int(buf[k * S + L.STRIKE])
		if s > 0:
			buf[k * S + L.STRIKE] = float(local.get(s - 1, -1) + 1)
	var n := buf.size() / S
	_mini.clan_params = _clan_params
	_mini.units = buf
	_mini.n = n
	_mini.frozen_from = n_act
	var acc := PackedFloat32Array()
	acc.resize(n)
	var acc_next := PackedFloat32Array()
	acc_next.resize(n)
	for k in n_act:
		acc[k] = actors[k].pending_dmg
	# crowd units swinging at an actor: their swing rate lands on the actor (CPU side of the seam)
	var swing := p.attack_dmg / p.attack_cd
	for r: PackedFloat32Array in frozen:
		if int(r[L.STATE]) != L.FIGHT:
			continue
		var t := int(local.get(int(r[L.TARGET]), -1))
		if t < 0 or t >= n_act:
			continue
		var tr := actors[t].rec
		var dx := tr[L.PX] - r[L.PX]
		var dz := tr[L.PZ] - r[L.PZ]
		if dx * dx + dz * dz <= p.reach * p.reach * 1.3:
			acc[t] += swing * _clan_params[int(r[L.CLAN]) * 8 + 3] * dt
	_mini.acc_a = acc
	_mini.acc_b = acc_next
	_mini.parity = 0
	_mini.spheres = _spheres
	_mini.ghost = Vector3(-1000, 0, -1000)
	_mini.step(dt)
	var to_global: Array[int] = []
	to_global.resize(n)
	for idx: int in local:
		to_global[local[idx]] = idx
	# actors' blows on crowd units go to the crowd as single-target hits
	for j in range(n_act, n):
		var dmg := _mini.incoming(j)
		if dmg > 0.0:
			sim.add_sphere(Vector3(_mini.units[j * S + L.PX], 0, _mini.units[j * S + L.PZ]), 1000.0, dmg, 0.0, 15, to_global[j], 0.0, 0)
	for k in n_act:
		var a := actors[k]
		var before := a.state()
		var r := _mini.read_unit(k)
		var t := int(r[L.TARGET])
		r[L.TARGET] = float(to_global[t]) if t >= 0 else -1.0
		var s := int(r[L.STRIKE])
		if s > 0:
			r[L.STRIKE] = float(to_global[s - 1] + 1)
		r[L.ACTOR] = 1.0
		a.rec = r
		a.pending_dmg = _mini.incoming(k)
		a.aggro = maxf(0.0, a.aggro - dt)
		a.swing_cd = maxf(0.0, a.swing_cd - dt)
		var after := a.state()
		var c := clampi(a.clan(), 0, 3)
		if before == L.FIGHT and after == L.ROUT:
			routs[c] += 1
			unit_routed.emit(a)
		elif before != L.SCATTERED and after == L.SCATTERED:
			scatters[c] += 1
			unit_scattered.emit(a)
		a.sync_visual(p.dissolve_s)
		sim.write_unit(a.index, a.rec)
	for a in actors.duplicate():
		if a.state() == L.LEFT:
			demote(a)


# ---------------------------------------------------------------- the ghost's blows

## A direct hit from the ghost (tool swing): Form damage (x shaken), a little Resolve, a flash.
func hit_actor(a: NearActor, form_dmg: float, resolve_dmg: float) -> void:
	var shaken := p.shaken_mult if a.rec[L.RESOLVE] < p.shaken_below else 1.0
	a.rec[L.FORM] -= form_dmg * shaken
	a.rec[L.RESOLVE] = maxf(0.0, a.rec[L.RESOLVE] - resolve_dmg)
	a.rec[L.FLASH] = 1.0
	a.aggro = 6.0


func actor_at(index: int) -> NearActor:
	return by_index.get(index)
