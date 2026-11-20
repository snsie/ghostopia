## Headless balance probe for the battle prototype: runs the Sunken Ford battle on the CPU reference sim
## and prints how it unfolds, then replays it with a scare at a flank under different conditions.
##   godot_console --headless --path . -s res://tools/battle_probe.gd -- [seconds] [scale]
extends SceneTree

const L := preload("res://scripts/battle/crowd_layout.gd")

var reg: BlockRegistry
var layout: Dictionary
var pop: Dictionary
var tuning: Tuning
var terrain: BattleTerrain
var params: CrowdParams


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var seconds := float(args[0]) if args.size() > 0 else 120.0
	var scale := float(args[1]) if args.size() > 1 else 1.0
	tuning = Tuning.load_file()
	reg = BlockRegistry.load_file()
	layout = JSON.parse_string(FileAccess.get_file_as_string("res://assets/levels/sunken_ford_layout.json"))
	pop = JSON.parse_string(FileAccess.get_file_as_string("res://assets/levels/sunken_ford_population.json"))
	var w: Dictionary = layout["world"]
	var size := Vector3i(int(w["size"][0]), int(w["size"][1]), int(w["size"][2]))
	var vox := FileAccess.get_file_as_bytes(String(w["voxels"]["path"])).decompress_dynamic(-1, FileAccess.COMPRESSION_GZIP)
	var t0 := Time.get_ticks_msec()
	terrain = BattleTerrain.from_voxels(vox, size, reg, int(w["floor_y"]), int(w["ceiling_y"]))
	var walkers: Array[bool] = []
	for ci in pop["clans"].size():
		var cd: Dictionary = pop["clans"][ci]
		terrain.mark_home(ci, cd["home"]["rect"])
		walkers.append(bool(cd.get("water_walker", false)))
	var wc_over: Variant = JSON.parse_string(args[3]) if args.size() > 3 else null
	var wc := float(tuning.get_value("battle.crowd.water_cost", 2.5))
	var goal := String(tuning.get_value("battle.attack_goal", "ford"))
	if wc_over is Dictionary:
		wc = float(wc_over.get("water_cost", wc))
		goal = String(wc_over.get("attack_goal", goal))
	terrain.setup_clans(walkers, wc, goal)
	print("terrain + flow fields: %d ms" % (Time.get_ticks_msec() - t0))
	var crowd := tuning.d("battle.crowd").duplicate()
	if args.size() > 3:
		var over: Variant = JSON.parse_string(args[3])
		if over is Dictionary:
			for k: String in over:
				if k.begins_with("bells.") or k.begins_with("ghost."):
					var parts := k.split(".")
					tuning.data["battle"][parts[0]][parts[1]] = over[k]
				elif k.begins_with("clans."):
					var cp := k.split(".")
					tuning.data["battle"]["clans"][cp[1]][cp[2]] = over[k]
				else:
					crowd[k] = over[k]
	params = CrowdParams.from_tuning(crowd)
	var mode := String(args[2]) if args.size() > 2 else "all"
	if mode in ["all", "plain"]:
		_run("no ghost", seconds, scale, "")
	for m in ["boo_bells_ringing", "silence_only", "silence_then_boo"]:
		if mode in ["all", m]:
			_run(m, seconds, scale, m)
	quit(0)


func _clan_blocks(silenced: bool) -> PackedFloat32Array:
	var cp := PackedFloat32Array()
	var bells := tuning.d("battle.bells")
	for cd: Dictionary in pop["clans"]:
		var ct: Dictionary = tuning.d("battle.clans").get(cd["id"], {})
		var regen := float(ct.get("regen_bonus", 0.0))
		var fear := float(ct.get("fear_mult", 1.0))
		var spread := float(ct.get("contagion_mult", 1.0))
		if cd["id"] == "drowned_parish":
			if silenced:
				fear = float(bells["silenced_fear_mult"])
				spread = float(bells.get("silenced_contagion_mult", fear))
			else:
				regen += float(bells["ringing_regen_bonus"])
				fear = float(bells.get("ringing_fear_mult", 1.0))
				spread = float(bells.get("ringing_contagion_mult", fear))
		cp.append_array(CrowdParams.clan_block(float(ct.get("speed_mult", 1.0)), regen, fear, float(ct.get("dmg_mult", 1.0)), bool(cd.get("water_walker", false)), spread))
	return cp


func _run(label: String, seconds: float, scale: float, scenario: String) -> void:
	var sp: Dictionary = CrowdSpawner.spawn(pop, terrain, params, 20261119, scale)
	var sim := CrowdSimCpu.new()
	sim.write_multimesh = false
	sim.setup(terrain, params, sp["starts"], sp["sizes"], sp["units"], _clan_blocks(false))
	var dt := 1.0 / 30.0
	var steps := int(seconds / dt)
	var step_us := 0
	var scare_at := 45.0
	var routs_at_scare := 0
	var g := tuning.d("battle.ghost")
	print("\n=== %s: %d units ===" % [label, sim.n])
	for k in steps:
		var t := k * dt
		if scenario != "" and absf(t - scare_at) < dt * 0.5:
			if scenario in ["silence_only", "silence_then_boo"]:
				sim.set_clan(0, _clan_blocks(true).slice(0, 8))
				sim.add_sphere(Vector3(64, 7, 64), 400.0, 0.0, float(tuning.get_value("battle.bells.silence_shock", 20.0)), 1, -1, 0.0, 0)
			routs_at_scare = sim.summary[L.SUM_ROUTS + 0]
		if scenario in ["boo_bells_ringing", "silence_then_boo"] and absf(t - (scare_at + 3.0)) < dt * 0.5:
			var spot := _flank_point(sim, 0, 0)
			sim.add_sphere(spot, float(g["boo_radius_m"]), float(g["boo_form"]), float(g["boo_resolve"]), 1, -1, float(g["boo_falloff"]), L.SPH_SCARE | L.SPH_GHOST)
			print("  BOO at %s (t=%.1f)" % [spot, t])
		var a := Time.get_ticks_usec()
		sim.step(dt)
		step_us += Time.get_ticks_usec() - a
		if scenario != "" and t > scare_at and int((t - scare_at) / dt) % int(5.0 / dt) == 0 and t < scare_at + 31.0:
			print("  +%4.1fs parish routs since scare %d" % [t - scare_at, sim.summary[L.SUM_ROUTS + 0] - routs_at_scare])
		if k % int(15.0 / dt) == 0 or k == steps - 1:
			_report(sim, t)
	print("  step avg %.2f ms" % (step_us / 1000.0 / steps))


func _flank_point(sim: CrowdSimCpu, clan: int, flank: int) -> Vector3:
	var sx := 0.0
	var sz := 0.0
	var n := 0
	for i in sim.n:
		if int(sim.get_f(i, L.CLAN)) != clan or int(sim.get_f(i, L.STATE)) != L.FIGHT:
			continue
		var x := sim.get_f(i, L.PX)
		if L.flank_of(x, terrain.mid_x) != flank or int(sim.get_f(i, L.TARGET)) < 0:
			continue
		sx += x
		sz += sim.get_f(i, L.PZ)
		n += 1
	if n == 0:
		return Vector3(48, 7, 56)
	var cx := sx / n
	var cz := sz / n
	# snap to the engaged unit nearest the centroid (the ghost BOOs from among the front line)
	var best := Vector3(cx, 7, cz)
	var bd := 1e9
	for i in sim.n:
		if int(sim.get_f(i, L.CLAN)) != clan or int(sim.get_f(i, L.TARGET)) < 0 or int(sim.get_f(i, L.STATE)) != L.FIGHT:
			continue
		var d := Vector2(sim.get_f(i, L.PX) - cx, sim.get_f(i, L.PZ) - cz).length()
		if d < bd:
			bd = d
			best = Vector3(sim.get_f(i, L.PX), 7, sim.get_f(i, L.PZ))
	var cnt := 0
	var rs := 0.0
	for i in sim.n:
		if int(sim.get_f(i, L.CLAN)) == clan and int(sim.get_f(i, L.STATE)) == L.FIGHT and Vector2(sim.get_f(i, L.PX) - best.x, sim.get_f(i, L.PZ) - best.z).length() < 5.0:
			cnt += 1
			rs += sim.get_f(i, L.RESOLVE)
	print("  %d parish within 5 m of the BOO, mean Resolve %.1f" % [cnt, rs / maxf(1, cnt)])
	return best


func _report(sim: CrowdSimCpu, t: float) -> void:
	var s := sim.summary
	var mx := 0
	var over := 0
	for v in sim._count:
		mx = maxi(mx, v)
		if v > sim.p.cell_cap:
			over += 1
	var line := "  t=%5.1f [cell max %d, %d cells over cap]" % [t, mx, over]
	for c in 2:
		var fight := s[L.SUM_STATE + L.FIGHT * L.MAX_CLANS + c]
		var rout := s[L.SUM_STATE + L.ROUT * L.MAX_CLANS + c]
		var out := s[L.SUM_STATE + L.LEFT * L.MAX_CLANS + c] + s[L.SUM_STATE + L.SCATTERED * L.MAX_CLANS + c]
		var fw := s[L.SUM_FLANK + c * 2]
		var fe := s[L.SUM_FLANK + c * 2 + 1]
		var rw := s[L.SUM_FLANK_RES + c * 2] / 16.0 / maxf(1.0, fw)
		var re := s[L.SUM_FLANK_RES + c * 2 + 1] / 16.0 / maxf(1.0, fe)
		line += " | %s fight %3d rout %3d out %3d eng %3d resW %4.1f resE %4.1f (routs %d scat %d)" % [
			"P" if c == 0 else "B", fight, rout, out, s[L.SUM_ENGAGED + c], rw, re, s[L.SUM_ROUTS + c], s[L.SUM_SCATTERS + c]]
	print(line)
