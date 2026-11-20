## Battle prototype crowd sim (CPU reference): flow fields, movement, separation, melee, Form,
## Resolve, rout spread, hit spheres, river rules and the summary. The GPU shaders follow the same
## rules; `--battle-bench` runs those on real hardware.
extends "res://tests/framework/test_case.gd"

const L := preload("res://scripts/battle/crowd_layout.gd")
const TerrainS := preload("res://scripts/battle/battle_terrain.gd")
const SimS := preload("res://scripts/battle/crowd_sim_cpu.gd")
const ParamsS := preload("res://scripts/battle/crowd_params.gd")
const SpawnS := preload("res://scripts/battle/crowd_spawner.gd")

const W := 40
const H := 40


## A flat 40 x 40 field, a river across rows 18-21 with a ford at x 16-23, homes at the far edges.
func _terrain(walkers: Array[bool] = [true, false]) -> BattleTerrain:
	var hs := PackedFloat32Array()
	hs.resize(W * H)
	hs.fill(7.0)
	var fl := PackedInt32Array()
	fl.resize(W * H)
	for z in H:
		for x in W:
			var c := x + W * z
			if x == 0 or x == W - 1:
				fl[c] = L.T_BLOCKED
			elif z >= 18 and z < 22:
				fl[c] = L.T_FORD if (x >= 16 and x < 24) else L.T_WATER
	var t: BattleTerrain = TerrainS.from_grid(W, H, hs, fl)
	t.mark_home(0, [1, 0, W - 1, 2])
	t.mark_home(1, [1, H - 2, W - 1, H])
	t.setup_clans(walkers, 2.5, "enemy_home")
	return t


func _params() -> CrowdParams:
	var p: CrowdParams = ParamsS.new()
	return p


func _unit(clan: int, x: float, z: float) -> PackedFloat32Array:
	var u := L.blank()
	u[L.PX] = x
	u[L.PZ] = z
	u[L.FORM] = 100.0
	u[L.RESOLVE] = 100.0
	u[L.CLAN] = float(clan)
	u[L.STATE] = float(L.FIGHT)
	u[L.PY] = 7.0
	u[L.STATE_T] = 1.0
	u[L.SEED] = fmod(x * 0.37 + z * 0.11, 1.0)
	return u


func _sim(t: BattleTerrain, list: Array, p: CrowdParams = null) -> CrowdSimCpu:
	var buf := PackedFloat32Array()
	var counts := [0, 0]
	for u: PackedFloat32Array in list:
		buf.append_array(u)
		counts[int(u[L.CLAN])] += 1
	var cp := PackedFloat32Array()
	cp.append_array(CrowdParams.clan_block(1.0, 0.0, 1.0, 1.0, true))
	cp.append_array(CrowdParams.clan_block(1.0, 0.0, 1.0, 1.0, false))
	var s: CrowdSimCpu = SimS.new()
	# units of a clan must be contiguous; tests list clan 0 first
	s.setup(t, p if p else _params(), PackedInt32Array([0, counts[0]]), PackedInt32Array(counts), buf, cp)
	return s


func _run(s: CrowdSimCpu, seconds: float, dt: float = 1.0 / 30.0) -> void:
	for k in int(seconds / dt):
		s.step(dt)


# ---------------------------------------------------------------- flow fields

func test_flow_field_points_toward_the_enemy_home() -> void:
	var t := _terrain()
	var f := t.flow(0, 10.5, 8.5)
	assert_true(f.y > 0.5, "clan 0 attacks south, got %s" % f)
	var home := t.flow(1, 10.5, 30.5)
	assert_true(home.y < -0.5, "clan 0's home field points north, got %s" % home)


func test_ford_goal_draws_both_clans_to_the_ford() -> void:
	var t := _terrain()
	t.setup_clans([true, false] as Array[bool], 2.5, "ford")
	var a := t.flow(0, 20.5, 8.5)
	var b := t.flow(2, 20.5, 30.5)
	assert_true(a.y > 0.9, "clan 0 heads south to the ford: %s" % a)
	assert_true(b.y < -0.9, "clan 1 heads north to the ford: %s" % b)
	assert_almost_eq(t.dist_at(0, 20.5, 19.5), 0.0, 0.001, "the ford is the goal")


func test_non_walkers_must_use_the_ford() -> void:
	var t := _terrain()
	assert_false(t.passable(t.cell(5.5, 19.5), 1), "barrow can't enter running water")
	assert_true(t.passable(t.cell(20.5, 19.5), 1), "the ford is passable")
	assert_true(t.passable(t.cell(5.5, 19.5), 0), "water walkers enter the river")
	# from the far west the Barrow path to the north home bends through the ford
	var dw := t.dist_at(2, 3.5, 25.5)
	var straight := 25.5 - 1.0
	assert_true(dw > straight + 8.0, "detour via the ford: %f" % dw)
	assert_true(t.dist_at(0, 3.5, 12.5) < INF, "parish reach the south home")


# ---------------------------------------------------------------- movement

func test_units_follow_the_flow_field() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(0, 20.5, 5.5)])
	_run(s, 2.0)
	assert_true(s.get_f(0, L.PZ) > 7.5, "moved south toward the enemy: %f" % s.get_f(0, L.PZ))
	assert_eq(int(s.get_f(0, L.CLIP)), L.CLIP_WALK, "walking")


func test_separation_pushes_overlapping_units_apart() -> void:
	var t := _terrain()
	var p := _params()
	p.speed = 0.0
	var s := _sim(t, [_unit(0, 20.0, 8.0), _unit(0, 20.2, 8.0)], p)
	_run(s, 1.0)
	var d := absf(s.get_f(0, L.PX) - s.get_f(1, L.PX))
	assert_true(d > 0.6, "pushed apart to %f" % d)


func test_barrow_unit_stops_at_running_water() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(1, 5.5, 23.0)])
	var p := s.p
	p.speed = 2.0
	# point it straight north by giving it a home field target... just drive it with a sphere-free run
	_run(s, 6.0)
	var z := s.get_f(0, L.PZ)
	var x := s.get_f(0, L.PX)
	assert_true(not (z >= 18.0 and z < 22.0 and (x < 16.0 or x >= 24.0)), "never stood in the river: %f, %f" % [x, z])


# ---------------------------------------------------------------- melee, Form, Resolve

func test_melee_blow_lands_after_the_strike_point() -> void:
	var t := _terrain()
	var a := _unit(0, 20.0, 10.0)
	a[L.ATTACK_CD] = 0.0
	var b := _unit(1, 20.0, 11.0)
	b[L.ATTACK_CD] = 99.0
	var s := _sim(t, [a, b])
	s.step(1.0 / 30.0)
	assert_eq(int(s.get_f(0, L.CLIP)), L.CLIP_ATTACK, "swing started")
	assert_eq(int(s.get_f(0, L.TARGET)), 1, "targets the enemy")
	assert_almost_eq(s.get_f(1, L.FORM), 100.0, 0.01, "no damage before the strike point")
	_run(s, 0.45)
	assert_true(s.get_f(1, L.FORM) < 100.0, "the blow landed: %f" % s.get_f(1, L.FORM))
	assert_almost_eq(s.get_f(1, L.FORM), 100.0 - s.p.attack_dmg, 0.01, "one blow")
	assert_true(s.get_f(1, L.RESOLVE) < 100.0, "a hit lowers Resolve a little")


func test_shaken_units_take_extra_damage() -> void:
	var t := _terrain()
	var calm := _unit(1, 10.0, 10.0)
	var shaken := _unit(1, 30.0, 10.0)
	shaken[L.RESOLVE] = 20.0
	var s := _sim(t, [calm, shaken])
	s.add_sphere(Vector3(10, 7, 10), 0.5, 10.0, 0.0, 2, 0, 0.0)
	s.add_sphere(Vector3(30, 7, 10), 0.5, 10.0, 0.0, 2, 1, 0.0)
	s.step(1.0 / 30.0)
	assert_almost_eq(s.get_f(0, L.FORM), 90.0, 0.01)
	assert_almost_eq(s.get_f(1, L.FORM), 100.0 - 10.0 * s.p.shaken_mult, 0.01, "x1.5 when shaken")


func test_form_zero_scatters_and_counts() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(1, 10.0, 10.0)])
	s.add_sphere(Vector3(10, 7, 10), 1.0, 150.0, 0.0, 2, -1, 0.0)
	s.step(1.0 / 30.0)
	assert_eq(int(s.get_f(0, L.STATE)), L.SCATTERED)
	assert_eq(s.summary[L.SUM_SCATTERS + 1], 1, "cumulative scatter count")
	_run(s, 1.0)
	assert_eq(int(s.get_f(0, L.STATE)), L.LEFT, "dissolved out of the battle")


func test_resolve_zero_routs_and_flees_home() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(0, 20.5, 12.0)])
	s.add_sphere(Vector3(20.5, 7, 12), 2.0, 0.0, 200.0, 1, -1, 0.0, L.SPH_SCARE)
	s.step(1.0 / 30.0)
	assert_eq(int(s.get_f(0, L.STATE)), L.ROUT)
	assert_eq(s.summary[L.SUM_ROUTS + 0], 1)
	var z0 := s.get_f(0, L.PZ)
	_run(s, 1.0)
	assert_true(s.get_f(0, L.PZ) < z0 - 1.0, "flees north to its home")
	assert_eq(int(s.get_f(0, L.CLIP)), L.CLIP_FLEE)
	_run(s, 8.0)
	assert_eq(int(s.get_f(0, L.STATE)), L.LEFT, "left the field at home")


func test_rout_spreads_to_nearby_allies() -> void:
	var t := _terrain()
	var p := _params()
	p.speed = 0.0
	p.flee_speed = 0.0
	var list: Array = []
	for k in 4:
		var u := _unit(0, 18.0 + k * 1.0, 10.0)
		u[L.RESOLVE] = 20.0
		list.append(u)
	var far := _unit(0, 30.0, 10.0)
	far[L.RESOLVE] = 20.0
	list.append(far)
	var s := _sim(t, list, p)
	# break the first one
	s.add_sphere(Vector3(18, 7, 10), 0.4, 0.0, 100.0, 1, 0, 0.0)
	_run(s, 6.0)
	var routed := 0
	for k in 4:
		if int(s.get_f(k, L.STATE)) == L.ROUT:
			routed += 1
	assert_eq(routed, 4, "the panic cascaded down the line")
	assert_eq(int(s.get_f(4, L.STATE)), L.FIGHT, "a unit 12 m away holds")


func test_calm_units_hold_against_one_rout() -> void:
	var t := _terrain()
	var p := _params()
	p.speed = 0.0
	p.flee_speed = 0.0
	var a := _unit(0, 18.0, 10.0)
	var b := _unit(0, 19.0, 10.0)
	var s := _sim(t, [a, b], p)
	s.add_sphere(Vector3(18, 7, 10), 0.4, 0.0, 200.0, 1, 0, 0.0)
	_run(s, 3.0)
	assert_eq(int(s.get_f(1, L.STATE)), L.FIGHT, "full Resolve absorbs one neighbour breaking")


# ---------------------------------------------------------------- hit spheres

func test_hit_spheres_respect_radius_clan_and_target() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(0, 10.0, 10.0), _unit(1, 11.0, 10.0), _unit(1, 16.0, 10.0)])
	s.add_sphere(Vector3(10.5, 7, 10), 3.0, 20.0, 10.0, 2, -1, 0.0)   # clan 1 only
	s.step(1.0 / 30.0)
	assert_almost_eq(s.get_f(0, L.FORM), 100.0, 0.01, "clan mask excludes clan 0")
	assert_true(s.get_f(1, L.FORM) < 100.0, "inside the sphere")
	assert_almost_eq(s.get_f(2, L.FORM), 100.0, 0.01, "outside the radius")
	s.add_sphere(Vector3(11, 7, 10), 50.0, 5.0, 0.0, 3, 2, 0.0)       # target unit 2 only
	s.step(1.0 / 30.0)
	assert_true(s.get_f(2, L.FORM) < 100.0, "the targeted unit")
	assert_true(s.get_f(0, L.FORM) >= 99.99, "others untouched")


func test_scare_spheres_use_the_clan_fear_multiplier() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(0, 10.0, 10.0), _unit(1, 30.0, 10.0)])
	s.set_clan(0, CrowdParams.clan_block(1.0, 0.0, 2.0, 1.0, true))
	s.add_sphere(Vector3(10, 7, 10), 1.0, 0.0, 20.0, 1, -1, 0.0, L.SPH_SCARE)
	s.add_sphere(Vector3(30, 7, 10), 1.0, 0.0, 20.0, 2, -1, 0.0, L.SPH_SCARE)
	s.step(1.0 / 30.0)
	assert_almost_eq(s.get_f(0, L.RESOLVE), 60.0, 0.5, "fear in play doubles the scare")
	assert_almost_eq(s.get_f(1, L.RESOLVE), 80.0, 0.5)


# ---------------------------------------------------------------- summary + battle

func test_summary_counts_states_and_flanks() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(0, 5.0, 5.0), _unit(0, 30.0, 5.0), _unit(1, 30.0, 30.0)])
	s.step(1.0 / 30.0)
	s.step(1.0 / 30.0)
	assert_eq(s.summary[L.SUM_STATE + L.FIGHT * L.MAX_CLANS + 0], 2)
	assert_eq(s.summary[L.SUM_STATE + L.FIGHT * L.MAX_CLANS + 1], 1)
	assert_eq(s.summary[L.SUM_FLANK + 0], 1, "clan 0 west")
	assert_eq(s.summary[L.SUM_FLANK + 1], 1, "clan 0 east")


func test_nearby_list_is_sorted_by_distance_to_the_ghost() -> void:
	var t := _terrain()
	var s := _sim(t, [_unit(0, 10.0, 10.0), _unit(0, 12.0, 10.0), _unit(1, 30.0, 30.0)])
	s.ghost = Vector3(12.2, 7, 10)
	s.step(1.0 / 30.0)
	assert_eq(s.nearby.size(), 2, "two within range")
	assert_eq(int(s.nearby[0][0]), 1, "nearest first")


func test_spawned_armies_meet_and_fight() -> void:
	var t := _terrain()
	var pop := {"clans": [
		{"id": "a", "count": 30, "water_walker": true, "formation": {"rect": [10, 4, 30, 12], "spacing_m": 1.15, "facing_yaw": 0.0}},
		{"id": "b", "count": 30, "water_walker": false, "formation": {"rect": [10, 27, 30, 35], "spacing_m": 1.15, "facing_yaw": 180.0}},
	]}
	var p := _params()
	var sp: Dictionary = SpawnS.spawn(pop, t, p, 7)
	assert_eq(sp["sizes"], PackedInt32Array([30, 30]))
	var cp := PackedFloat32Array()
	cp.append_array(CrowdParams.clan_block(1.0, 0.0, 1.0, 1.0, true))
	cp.append_array(CrowdParams.clan_block(1.0, 0.0, 1.0, 1.0, false))
	var s: CrowdSimCpu = SimS.new()
	s.setup(t, p, sp["starts"], sp["sizes"], sp["units"], cp)
	_run(s, 25.0)
	var hurt := 0
	for i in s.n:
		if s.get_f(i, L.FORM) < 100.0 or int(s.get_f(i, L.STATE)) != L.FIGHT:
			hurt += 1
	assert_true(hurt > 10, "the armies met and fought: %d hurt" % hurt)


func test_actors_are_skipped_but_seen_by_their_neighbours() -> void:
	var t := _terrain()
	var p := _params()
	p.speed = 0.0
	p.flee_speed = 0.0
	var actor := _unit(0, 20.0, 10.0)
	actor[L.ACTOR] = 1.0
	actor[L.STATE] = float(L.ROUT)
	actor[L.STATE_T] = 0.0
	var ally := _unit(0, 21.0, 10.0)
	var enemy := _unit(1, 20.0, 11.0)
	var s := _sim(t, [actor, ally, enemy], p)
	var x0 := s.get_f(0, L.PX)
	s.step(1.0 / 30.0)
	assert_almost_eq(s.get_f(0, L.PX), x0, 0.0001, "the crowd doesn't move an actor")
	assert_true(s.get_f(1, L.RESOLVE) < 100.0, "an actor breaking shakes its crowd neighbours")
	assert_almost_eq(s.mm_all[0 * L.MM_STRIDE + 5], 0.0, 0.0001, "the actor's crowd instance is hidden")


func test_frozen_units_are_neighbours_only() -> void:
	var t := _terrain()
	var a := _unit(0, 20.0, 10.0)
	a[L.ATTACK_CD] = 0.0
	var b := _unit(1, 20.0, 11.0)
	var s := _sim(t, [a, b])
	s.frozen_from = 1
	_run(s, 0.5)
	assert_almost_eq(s.get_f(1, L.PZ), 11.0, 0.0001, "frozen unit never moves")
	assert_true(s.incoming(1) > 0.0 or s.get_f(0, L.STRIKE) == 0.0, "a blow aimed at a frozen unit waits in its accumulator")


func test_summary_reports_the_front_line() -> void:
	var t := _terrain()
	var p := _params()
	p.speed = 0.0
	var s := _sim(t, [_unit(0, 10.0, 10.0), _unit(1, 10.0, 11.0)], p)
	s.step(1.0 / 30.0)
	s.step(1.0 / 30.0)
	var f := L.front_point(s.summary, 0, 0, 7.0)
	assert_true(f != Vector3.INF, "clan 0 west is engaged")
	assert_almost_eq(f.x, 10.0, 0.3)
	assert_almost_eq(f.z, 10.0, 0.3)
	assert_eq(L.front_point(s.summary, 0, 1, 7.0), Vector3.INF, "nobody fights on the east flank")
