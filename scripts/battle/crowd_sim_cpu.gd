## CPU reference of the crowd sim. Same data layout and the same rules, in the same order, as the
## GPU compute shaders (shaders/crowd/crowd_step.glsl), so headless unit tests and `--autotest` (no
## RenderingDevice there) exercise the real logic. Each step reads the previous state and writes a new
## one (double-buffered like the GPU); melee damage goes through two accumulators by frame parity, so a
## blow struck this frame lands next frame on both versions.
class_name CrowdSimCpu
extends RefCounted

const L := preload("res://scripts/battle/crowd_layout.gd")

var n := 0
var units := PackedFloat32Array()            # current state, n * STRIDE
var acc_a := PackedFloat32Array()            # melee damage accumulators, swapped by frame parity
var acc_b := PackedFloat32Array()
var parity := 0
var p: CrowdParams
var terrain: BattleTerrain
var clan_params := PackedFloat32Array()      # 8 floats per clan
var clans := 0
var clan_start := PackedInt32Array()
var clan_size := PackedInt32Array()
var spheres := PackedFloat32Array()          # queued for the next step
var summary := PackedInt32Array()
var nearby: Array[PackedFloat32Array] = []   # [index, record...], nearest bands first
var ghost := Vector3(-1000, 0, -1000)
var frame := 0
var mm_all := PackedFloat32Array()           # every unit's multimesh instance (clans are contiguous)
var write_multimesh := true
var frozen_from := -1                         # units at or past this index are neighbours only (near tier)

var _gx := 0
var _gz := 0
var _count := PackedInt32Array()
var _items := PackedInt32Array()


func setup(p_terrain: BattleTerrain, params: CrowdParams, starts: PackedInt32Array, sizes: PackedInt32Array,
		init_units: PackedFloat32Array, p_clan_params: PackedFloat32Array) -> void:
	terrain = p_terrain
	p = params
	clan_start = starts
	clan_size = sizes
	clans = starts.size()
	units = init_units.duplicate()
	n = units.size() / L.STRIDE
	clan_params = p_clan_params.duplicate()
	acc_a = PackedFloat32Array()
	acc_a.resize(n)
	acc_b = PackedFloat32Array()
	acc_b.resize(n)
	summary = PackedInt32Array()
	summary.resize(L.SUM_SIZE)
	_gx = ceili(terrain.w / p.cell_m)
	_gz = ceili(terrain.h / p.cell_m)
	_count.resize(_gx * _gz)
	_items.resize(_gx * _gz * p.cell_cap)
	mm_all = PackedFloat32Array()
	mm_all.resize(n * L.MM_STRIDE)


func set_clan(c: int, block: PackedFloat32Array) -> void:
	for k in 8:
		clan_params[c * 8 + k] = block[k]


func add_sphere(center: Vector3, radius: float, form_dmg: float, resolve_dmg: float, clan_mask: int,
		target: int = -1, falloff: float = 0.6, flags: int = 0) -> void:
	if spheres.size() >= L.SPHERE_MAX * L.SPHERE_STRIDE:
		return
	spheres.append_array(PackedFloat32Array([center.x, center.y, center.z, radius,
		form_dmg, resolve_dmg, float(clan_mask), float(target),
		falloff, float(flags), 0.0, 0.0]))


func write_unit(i: int, rec: PackedFloat32Array) -> void:
	for k in L.STRIDE:
		units[i * L.STRIDE + k] = rec[k]


func read_unit(i: int) -> PackedFloat32Array:
	return units.slice(i * L.STRIDE, (i + 1) * L.STRIDE)


## Melee damage that lands on unit i at the start of the next step.
func incoming(i: int) -> float:
	return acc_a[i] if parity == 0 else acc_b[i]


## One clan's slice of the multimesh buffer.
func clan_mm(c: int) -> PackedFloat32Array:
	return mm_all.slice(clan_start[c] * L.MM_STRIDE, (clan_start[c] + clan_size[c]) * L.MM_STRIDE)


func get_f(i: int, field: int) -> float:
	return units[i * L.STRIDE + field]


# ---------------------------------------------------------------- step

func step(dt: float) -> void:
	var S := L.STRIDE
	var src := units
	var dst := units.duplicate()
	var acc_read := acc_a if parity == 0 else acc_b
	var acc_write := acc_b if parity == 0 else acc_a
	_bin(src)
	for k in L.SUM_SIZE:
		if k < L.SUM_ROUTS or k >= L.SUM_FLANK:
			summary[k] = 0
	var near_bands: Array = []
	for b in L.NEAR_BANDS:
		near_bands.append([])
	var nsph := spheres.size() / L.SPHERE_STRIDE
	var cell_m := p.cell_m
	var cap := p.cell_cap
	var sep2 := p.sep_radius * p.sep_radius
	var fear2 := p.fear_radius * p.fear_radius
	var engage2 := p.engage * p.engage
	var near_r := L.NEAR_BANDS * L.NEAR_BAND_M
	for i in n:
		var o := i * S
		var state := int(src[o + L.STATE])
		var clan := int(src[o + L.CLAN])
		var px := src[o + L.PX]
		var pz := src[o + L.PZ]
		var is_actor := src[o + L.ACTOR] > 0.5
		if frozen_from >= 0 and i >= frozen_from:
			continue
		# summary + nearby list see the state at the start of the step
		summary[L.SUM_STATE + state * L.MAX_CLANS + clan] += 1
		if (state == L.FIGHT or state == L.ROUT) and not is_actor:
			var gd := Vector2(px - ghost.x, pz - ghost.z).length()
			if gd < near_r:
				var band := int(gd / L.NEAR_BAND_M)
				if near_bands[band].size() < L.NEAR_BAND_CAP:
					var entry := PackedFloat32Array([float(i)])
					entry.append_array(src.slice(o, o + S))
					near_bands[band].append(entry)
		if state == L.LEFT or is_actor:
			_mm(dst, i, clan)
			continue
		if state == L.SCATTERED:
			dst[o + L.STATE_T] = src[o + L.STATE_T] + dt
			if dst[o + L.STATE_T] >= p.dissolve_s:
				dst[o + L.STATE] = L.LEFT
			_mm(dst, i, clan)
			continue
		var cpo := clan * 8
		var c_speed := clan_params[cpo]
		var c_regen := clan_params[cpo + 1]
		var c_fear := clan_params[cpo + 2]
		var c_dmg := clan_params[cpo + 3]
		var c_spread := clan_params[cpo + 5]
		var form := src[o + L.FORM]
		var resolve := src[o + L.RESOLVE]
		var flash := maxf(0.0, src[o + L.FLASH] - dt * 4.0)
		# incoming melee (struck last frame)
		var dmg := acc_read[i]
		var shaken := p.shaken_mult if resolve < p.shaken_below else 1.0
		if dmg > 0.0:
			form -= dmg * shaken
			resolve -= dmg * p.hit_resolve_k
			flash = 1.0
		# hit spheres (BOO, throws, rockfalls, near-actor blows, clan-wide shocks)
		for s in nsph:
			var so := s * L.SPHERE_STRIDE
			var tgt := int(spheres[so + 7])
			if tgt >= 0 and tgt != i:
				continue
			if (int(spheres[so + 6]) & (1 << clan)) == 0:
				continue
			var dx := px - spheres[so]
			var dz := pz - spheres[so + 2]
			var r := spheres[so + 3]
			var d := sqrt(dx * dx + dz * dz)
			if d > r:
				continue
			var k := 1.0 - spheres[so + 8] * d / maxf(r, 0.001)
			var fm := c_fear if (int(spheres[so + 9]) & L.SPH_SCARE) != 0 else 1.0
			var fd := spheres[so + 4] * k
			if fd > 0.0:
				form -= fd * shaken
				resolve -= fd * p.hit_resolve_k
				flash = 1.0
			resolve -= spheres[so + 5] * k * fm
		# neighbours from the spatial hash
		var sepx := 0.0
		var sepz := 0.0
		var best := -1
		var best_d2 := engage2
		var n_rout := 0
		var n_new_rout := 0
		var n_new_scatter := 0
		var n_allies := 0
		var n_close := 0
		var gcx := clampi(int(px / cell_m), 0, _gx - 1)
		var gcz := clampi(int(pz / cell_m), 0, _gz - 1)
		for cz in range(maxi(0, gcz - 1), mini(_gz, gcz + 2)):
			for cx in range(maxi(0, gcx - 1), mini(_gx, gcx + 2)):
				var gc := cx + _gx * cz
				var cnt := mini(_count[gc], cap)
				for k2 in cnt:
					var j := _items[gc * cap + k2]
					if j == i:
						continue
					var oj := j * S
					var sj := int(src[oj + L.STATE])
					var dx2 := px - src[oj + L.PX]
					var dz2 := pz - src[oj + L.PZ]
					var d2 := dx2 * dx2 + dz2 * dz2
					if sj != L.SCATTERED and d2 < sep2:
						n_close += 1
						if d2 > 1e-6:
							var dd := sqrt(d2)
							var push := (p.sep_radius - dd) / p.sep_radius / dd
							sepx += dx2 * push
							sepz += dz2 * push
						else:
							var a := (src[o + L.SEED] - src[oj + L.SEED]) * 40.0
							sepx += cos(a)
							sepz += sin(a)
					if int(src[oj + L.CLAN]) != clan:
						if sj == L.FIGHT and d2 < best_d2:
							best_d2 = d2
							best = j
					elif d2 < fear2:
						if sj == L.ROUT:
							n_rout += 1
							n_allies += 1
							if src[oj + L.STATE_T] == 0.0:
								n_new_rout += 1
						elif sj == L.SCATTERED:
							if src[oj + L.STATE_T] == 0.0:
								n_new_scatter += 1
								n_allies += 1
						else:
							n_allies += 1
		# Resolve: fear spreads by the share of nearby allies that are breaking (density-independent);
		# calm units (no enemy in engage range, nobody breaking nearby) recover
		var inv_allies := 1.0 / maxf(1.0, float(n_allies))
		var fear_hit := (n_rout * p.rout_drain * dt + n_new_rout * p.rout_shock + n_new_scatter * p.scatter_shock) * inv_allies * c_spread
		resolve -= fear_hit
		if n_rout == 0 and dmg <= 0.0 and fear_hit <= 0.0 and best < 0:
			resolve = minf(p.resolve, resolve + (p.regen + c_regen) * dt)
		var new_state := state
		var state_t := src[o + L.STATE_T] + dt
		if form <= 0.0:
			form = 0.0
			new_state = L.SCATTERED
			state_t = 0.0
			summary[L.SUM_SCATTERS + clan] += 1
		elif resolve <= 0.0 and state == L.FIGHT:
			resolve = 0.0
			new_state = L.ROUT
			state_t = 0.0
			summary[L.SUM_ROUTS + clan] += 1
		resolve = maxf(resolve, 0.0)
		# movement
		var vx := src[o + L.VX]
		var vz := src[o + L.VZ]
		var yaw := src[o + L.YAW]
		var attack_cd := src[o + L.ATTACK_CD] - dt
		var anim_t := src[o + L.ANIM_T]
		var clip := int(src[o + L.CLIP])
		var strike := int(src[o + L.STRIKE])
		var target := -1
		var want_x := 0.0
		var want_z := 0.0
		var face_x := 0.0
		var face_z := 0.0
		var c := terrain.cell(px, pz)
		var in_water := (terrain.flags[c] & L.T_WATER) != 0
		if new_state == L.FIGHT:
			if best >= 0:
				var ob := best * S
				var tx := src[ob + L.PX] - px
				var tz := src[ob + L.PZ] - pz
				var td := sqrt(tx * tx + tz * tz)
				target = best
				face_x = tx
				face_z = tz
				if td <= p.reach:
					if attack_cd <= 0.0 and strike == 0:
						attack_cd = p.attack_cd * (0.8 + 0.4 * src[o + L.SEED])
						strike = best + 1
						clip = L.CLIP_ATTACK
						anim_t = 0.0
				else:
					var sp := p.speed * c_speed
					want_x = tx / td * sp
					want_z = tz / td * sp
			else:
				var f := terrain.fields[clan * 2]
				var sp2 := p.speed * c_speed
				want_x = f[c * 2] * sp2
				want_z = f[c * 2 + 1] * sp2
		elif new_state == L.ROUT:
			var fh := terrain.fields[clan * 2 + 1]
			want_x = fh[c * 2] * p.flee_speed
			want_z = fh[c * 2 + 1] * p.flee_speed
			strike = 0
		else:
			strike = 0
		# the pending blow lands at the strike point of the attack clip
		if strike > 0 and clip == L.CLIP_ATTACK and anim_t + dt >= p.strike_at and anim_t < p.strike_at:
			var tj := strike - 1
			var otj := tj * S
			var sx := src[otj + L.PX] - px
			var sz := src[otj + L.PZ] - pz
			var st := int(src[otj + L.STATE])
			if st == L.FIGHT and sx * sx + sz * sz <= (p.reach * 1.3) * (p.reach * 1.3):
				acc_write[tj] += p.attack_dmg * c_dmg
			strike = 0
		if clip == L.CLIP_ATTACK and anim_t >= p.attack_clip_s:
			strike = 0
		# crowd pressure: a packed unit stops pushing forward instead of crushing into the ones ahead
		var press := clampf(1.0 - maxf(0.0, float(n_close) - p.press_free) * p.press_k, 0.15, 1.0)
		want_x *= press
		want_z *= press
		var mult := p.wade_mult if in_water else 1.0
		var tvx := (want_x + sepx * p.sep_strength) * mult
		var tvz := (want_z + sepz * p.sep_strength) * mult
		var a2 := minf(1.0, p.accel * dt)
		vx += (tvx - vx) * a2
		vz += (tvz - vz) * a2
		var nx := px + vx * dt
		var nz := pz + vz * dt
		if not terrain.passable_at(nx, nz, clan):
			if terrain.passable_at(nx, pz, clan):
				nz = pz
				vz = 0.0
			elif terrain.passable_at(px, nz, clan):
				nx = px
				vx = 0.0
			else:
				nx = px
				nz = pz
				vx = 0.0
				vz = 0.0
		var nc := terrain.cell(nx, nz)
		var py := terrain.heights[nc]
		if terrain.flags[nc] & L.T_WATER:
			py -= p.wade_sink
		if new_state == L.ROUT and terrain.is_home(nc, clan):
			new_state = L.LEFT
		# facing and animation
		var spd := sqrt(vx * vx + vz * vz)
		if face_x != 0.0 or face_z != 0.0:
			yaw = lerp_angle(yaw, atan2(face_x, face_z), minf(1.0, dt * 10.0))
		elif spd > 0.2:
			yaw = lerp_angle(yaw, atan2(vx, vz), minf(1.0, dt * 8.0))
		if new_state == L.ROUT:
			if clip != L.CLIP_FLEE:
				clip = L.CLIP_FLEE
				anim_t = 0.0
			anim_t += dt * maxf(0.6, spd / p.flee_speed)
		elif clip == L.CLIP_ATTACK and anim_t < p.attack_clip_s:
			anim_t += dt
		else:
			var want_clip := L.CLIP_WALK if spd > 0.35 else L.CLIP_IDLE
			if want_clip != clip:
				clip = want_clip
				anim_t = src[o + L.SEED]
			anim_t += dt * (maxf(0.5, spd / p.speed) if clip == L.CLIP_WALK else 1.0)
		dst[o + L.PX] = nx
		dst[o + L.PZ] = nz
		dst[o + L.VX] = vx
		dst[o + L.VZ] = vz
		dst[o + L.FORM] = form
		dst[o + L.RESOLVE] = resolve
		dst[o + L.STATE] = float(new_state)
		dst[o + L.ATTACK_CD] = maxf(attack_cd, -1.0)
		dst[o + L.ANIM_T] = anim_t
		dst[o + L.YAW] = wrapf(yaw, -PI, PI)
		dst[o + L.PY] = py
		dst[o + L.TARGET] = float(target)
		dst[o + L.STATE_T] = state_t
		dst[o + L.FLASH] = flash
		dst[o + L.CLIP] = float(clip)
		dst[o + L.STRIKE] = float(strike)
		# flank stats for the HUD (fighting units only)
		if new_state == L.FIGHT:
			var fl := L.flank_of(nx, terrain.mid_x)
			summary[L.SUM_FLANK + clan * 2 + fl] += 1
			summary[L.SUM_FLANK_RES + clan * 2 + fl] += int(resolve * 16.0)
			if target >= 0 and best_d2 <= p.reach * p.reach * 1.2:
				summary[L.SUM_ENGAGED + clan] += 1
				var fo := L.SUM_FRONT + (clan * 2 + fl) * 3
				summary[fo] += 1
				summary[fo + 1] += int(nx * 4.0)
				summary[fo + 2] += int(nz * 4.0)
		_mm(dst, i, clan)
	units = dst
	var zero := PackedFloat32Array()
	zero.resize(n)
	if parity == 0:
		acc_a = zero
		acc_b = acc_write
	else:
		acc_b = zero
		acc_a = acc_write
	parity = 1 - parity
	spheres.clear()
	frame += 1
	nearby.clear()
	for b in L.NEAR_BANDS:
		for e: PackedFloat32Array in near_bands[b]:
			nearby.append(e)


func _bin(src: PackedFloat32Array) -> void:
	_count.fill(0)
	var cap := p.cell_cap
	var cell_m := p.cell_m
	for i in n:
		var o := i * L.STRIDE
		var st := int(src[o + L.STATE])
		if st == L.LEFT:
			continue
		if st == L.SCATTERED and src[o + L.STATE_T] > 0.0:
			continue
		var gc := clampi(int(src[o + L.PX] / cell_m), 0, _gx - 1) + _gx * clampi(int(src[o + L.PZ] / cell_m), 0, _gz - 1)
		var slot := _count[gc]
		_count[gc] = slot + 1
		if slot < cap:
			_items[gc * cap + slot] = i


## Writes unit i's MultiMesh instance (transform 3x4 + custom) from the new state.
func _mm(dst: PackedFloat32Array, i: int, clan: int) -> void:
	if not write_multimesh:
		return
	var o := i * L.STRIDE
	var m := i * L.MM_STRIDE
	var st := int(dst[o + L.STATE])
	var s := 1.0
	var code := 0.0
	if st == L.LEFT or dst[o + L.ACTOR] > 0.5:
		s = 0.0
	elif st == L.SCATTERED:
		var k := dst[o + L.STATE_T] / p.dissolve_s
		s = 1.0 + 0.35 * k
		code = 1.0 + clampf(k, 0.0, 1.0)
	elif st == L.ROUT:
		code = 0.5
	var yaw := dst[o + L.YAW]
	var cs := cos(yaw) * s
	var sn := sin(yaw) * s
	mm_all[m] = cs
	mm_all[m + 1] = 0.0
	mm_all[m + 2] = sn
	mm_all[m + 3] = dst[o + L.PX]
	mm_all[m + 4] = 0.0
	mm_all[m + 5] = s
	mm_all[m + 6] = 0.0
	mm_all[m + 7] = dst[o + L.PY]
	mm_all[m + 8] = -sn
	mm_all[m + 9] = 0.0
	mm_all[m + 10] = cs
	mm_all[m + 11] = dst[o + L.PZ]
	mm_all[m + 12] = dst[o + L.CLIP]
	mm_all[m + 13] = dst[o + L.ANIM_T]
	mm_all[m + 14] = code
	mm_all[m + 15] = dst[o + L.FLASH]
