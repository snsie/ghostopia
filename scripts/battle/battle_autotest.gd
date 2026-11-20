## `--battle --autotest`: plays the battle prototype's gate checks and writes AUTOTEST lines to
## battle_autotest.log plus screenshots (renders/game/battle_*.png in the editor, <exe dir>/autotest/
## in exports). Uses the CPU reference crowd by default (as headless tests do); add `--crowd gpu` to
## run the same steps on the GPU crowd. Exit code 0 when every step passed.
##   godot --path . -- --battle --autotest [--crowd gpu]
extends Node

const L := preload("res://scripts/battle/crowd_layout.gd")

var bw: BattleWorld
var _log: FileAccess
var _out := ""
var _fails: Array[String] = []
var _passes := 0
var _t0 := 0
var _cam: Camera3D


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_out = Game.output_dir()
	DirAccess.make_dir_recursive_absolute(_out)
	_log = FileAccess.open(_out.path_join("battle_autotest.log"), FileAccess.WRITE)
	_t0 = Time.get_ticks_msec()
	if DisplayServer.get_name() != "headless":
		DisplayServer.window_set_size(Vector2i(1600, 900))
	_run.call_deferred()


func log_line(s: String) -> void:
	var line := "AUTOTEST %7.1fs %s" % [(Time.get_ticks_msec() - _t0) / 1000.0, s]
	print(line)
	if _log:
		_log.store_line(line)
		_log.flush()


func check(name: String, ok: bool, detail: String = "") -> bool:
	if ok:
		_passes += 1
		log_line("PASS %s %s" % [name, detail])
	else:
		_fails.append(name)
		log_line("FAIL %s %s" % [name, detail])
	return ok


func wait(s: float) -> void:
	await get_tree().create_timer(s, true, false, true).timeout


func shot(name: String) -> void:
	if DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var p := _out.path_join("battle_%s.png" % name)
	img.save_png(p)
	log_line("SHOT %s" % p.get_file())


## A screenshot from a fixed vantage camera (the chase cam stays on the ghost).
func vantage(name: String, from: Vector3, at: Vector3) -> void:
	if _cam == null:
		_cam = Camera3D.new()
		_cam.fov = 62.0
		_cam.far = 400.0
		bw.add_child(_cam)
	_cam.global_position = from
	_cam.look_at(at, Vector3.UP)
	_cam.current = true
	await get_tree().process_frame
	await shot(name)
	bw.player.camera.current = true


func _sim_units() -> Array:
	# [index, record] for every unit, from the CPU crowd (the GPU only reads back the nearby list)
	var out := []
	if bw.sim is CrowdSimCpu:
		for i in bw.sim.n:
			out.append([i, bw.sim.read_unit(i)])
	return out


func _engaged_point(clan: int, flank: int) -> Vector3:
	var fp := L.front_point(bw.sim.summary, clan, flank, 7.0)
	if fp != Vector3.INF:
		return fp
	var sx := 0.0
	var sz := 0.0
	var n := 0
	for e in _sim_units():
		var r: PackedFloat32Array = e[1]
		if int(r[L.CLAN]) != clan or int(r[L.STATE]) != L.FIGHT or int(r[L.TARGET]) < 0:
			continue
		if L.flank_of(r[L.PX], bw.terrain.mid_x) != flank:
			continue
		sx += r[L.PX]
		sz += r[L.PZ]
		n += 1
	if n == 0:
		return Vector3(54, 7, 58)
	return Vector3(sx / n, 7.0, sz / n)


func _totals(c: int) -> Dictionary:
	return bw.clan_totals()[c]


func _run() -> void:
	while not bw.started:
		await get_tree().process_frame
	var p: Player = bw.player
	var near: NearTier = bw.near
	log_line("crowd: %s, %d units" % ["GPU" if bw.gpu else "CPU", bw.sim.n])
	# 1. entering the arena
	var c := bw.terrain.cell(p.global_position.x, p.global_position.z)
	check("enter_arena", bw.sim.n >= 900 and bw.world != null and (bw.terrain.flags[c] & L.T_BLOCKED) == 0
		and p.global_position.y > 6.0 and p.global_position.y < 24.0,
		"units %d, ghost at %s" % [bw.sim.n, p.global_position])
	await wait(1.0)
	await vantage("01_overview", Vector3(42, 20, 26), Vector3(64, 7, 62))
	# 2. the armies meet at the ford
	var t := 0.0
	while t < 45.0:
		await wait(1.0)
		t += 1.0
		var s: PackedInt32Array = bw.sim.summary
		if s[L.SUM_ENGAGED + 0] > 20 and s[L.SUM_ENGAGED + 1] > 20:
			break
	var sum: PackedInt32Array = bw.sim.summary
	check("armies_engage", sum[L.SUM_ENGAGED + 0] > 20 and sum[L.SUM_ENGAGED + 1] > 20,
		"engaged %d / %d after %.0f s" % [sum[L.SUM_ENGAGED + 0], sum[L.SUM_ENGAGED + 1], t])
	await vantage("02_lines_meet", Vector3(40, 15, 44), Vector3(62, 7, 63))
	# 3. the near tier promotes the units around the ghost
	var front := _engaged_point(bw.parish, 1)
	p.teleport(front + Vector3(0, 1.6, -3.0), 180.0)
	await wait(1.0)
	check("near_tier_promotes", near.actors.size() >= 16, "%d actors near the ghost" % near.actors.size())
	# 4. a tool hit that scatters a unit
	Game.inventory.selected = 2   # sledgehammer
	p._refresh_tool()
	var scat0: int = bw.stats["scattered_by_ghost"]
	var victim: NearActor = null
	var swings := 0
	while swings < 14 and int(bw.stats["scattered_by_ghost"]) == scat0:
		if victim == null or not is_instance_valid(victim) or victim.index < 0 or not victim.alive():
			victim = _nearest_actor(p.global_position)
		if victim == null:
			await wait(0.3)
			swings += 1
			continue
		var vp := victim.global_position
		p.teleport(vp + Vector3(0, 1.0, -1.3), 0.0)
		p.aim_at(vp + Vector3(0, 0.9, 0))
		p._swing_left = 0.0
		var r := p.try_mine()
		swings += 1
		await wait(0.45)
	check("hit_scatters_unit", int(bw.stats["scattered_by_ghost"]) > scat0,
		"%d swings, %d scattered by the ghost, %d hits" % [swings, bw.stats["scattered_by_ghost"], bw.stats["hits"]])
	await shot("03_hit_scatter")
	# 5. demotion carries the state back to the crowd
	var a := _nearest_actor(p.global_position)
	var idx := a.index if a else -1
	var form := a.rec[L.FORM] if a else 0.0
	var px := a.rec[L.PX] if a else 0.0
	p.teleport(Vector3(64, 8.2, 30), 180.0)
	await wait(1.0)
	var demoted := near.actors.is_empty() or not near.by_index.has(idx)
	var carried := true
	if bw.sim is CrowdSimCpu and idx >= 0:
		var r2: PackedFloat32Array = bw.sim.read_unit(idx)
		carried = r2[L.ACTOR] < 0.5 and absf(r2[L.FORM] - form) < 25.0 and absf(r2[L.PX] - px) < 6.0
	check("demotion_keeps_state", demoted and carried, "unit %d back in the crowd (actors now %d)" % [idx, near.actors.size()])
	# 6. silence the bells, then one BOO at the Parish west flank
	while bw.elapsed < 50.0:
		await wait(1.0)
	p.teleport(bw.bell_pos + Vector3(0, -6.0, 6.0), 180.0)
	p.aim_at(bw.bell_pos)
	await get_tree().process_frame
	var res := bw.haunt_action()
	check("silence_bells", res == "silenced" and bw.bells_left > 0.0, res)
	await wait(2.5)
	var spot := _engaged_point(bw.parish, 0)
	var view_from := Vector3(spot.x - 14.0, 14.0, spot.z - 16.0)
	p.teleport(spot + Vector3(0, 1.2, -0.5), 180.0)
	p.aim_at(spot + Vector3(0, 0, 4))
	await get_tree().process_frame
	await vantage("04_before_rout", view_from, spot)
	var tw0: Dictionary = _totals(bw.parish)
	var routs0: int = bw.total_routs()
	Game.ecto = 100.0
	p._boo_cd = 0.0
	p.do_boo()
	await wait(4.0)
	await vantage("05_after_rout", view_from, spot)
	await wait(7.0)
	var routed := bw.total_routs() - routs0
	var tw1: Dictionary = _totals(bw.parish)
	var graded := ""
	for s2: Dictionary in bw.scares:
		if s2["kind"] == "BOO":
			graded = String(s2.get("grade", ""))
	check("scare_routs_flank", routed >= int(bw.bt["grade"]["terrified"]),
		"%d routed in 11 s (grade %s); Parish west flank %d -> %d units at Resolve %.0f -> %.0f, east %d units" % [
			routed, graded, tw0["n_w"], tw1["n_w"], tw0["res_w"], tw1["res_w"], tw1["n_e"]])
	await vantage("06_flank_broken", Vector3(40, 18, 30), Vector3(58, 7, 60))
	# 7. the battle keeps running consistently
	await wait(10.0)
	var ok := true
	var detail := ""
	for ci in bw.clan_ids.size():
		var tt: Dictionary = _totals(ci)
		var sum_states := int(tt["fighting"]) + int(tt["routing"]) + int(tt["scattered"]) + int(tt["fled"])
		ok = ok and sum_states == int(tt["start"])
		detail += "%s %d fighting / %d routing / %d scattered / %d fled; " % [bw.clan_ids[ci], tt["fighting"], tt["routing"], tt["scattered"], tt["fled"]]
	check("counts_consistent", ok, detail)
	log_line("perf: %s" % bw.perf_text())
	log_line("SUMMARY %d passed, %d failed %s" % [_passes, _fails.size(), str(_fails)])
	bw.shutdown_and_quit(0 if _fails.is_empty() else 1)


func _nearest_actor(from: Vector3) -> NearActor:
	var best: NearActor = null
	var bd := 1e9
	for a in bw.near.actors:
		if not a.alive() or a.state() != L.FIGHT:
			continue
		var d := a.global_position.distance_to(from)
		if d < bd:
			bd = d
			best = a
	return best
