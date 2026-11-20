## `--battle-parity [seconds]`: steps the GPU crowd and the CPU reference side by side from the same
## start (fixed 1/30 s steps, no ghost) and logs both summaries, so a rule that drifted between
## shaders/crowd/crowd_sim.glsl and crowd_sim_cpu.gd shows up. Needs a GPU (run windowed).
##   godot --path . -- --battle-parity 60
extends Node

const L := preload("res://scripts/battle/crowd_layout.gd")

var bw: BattleWorld
var _log: FileAccess


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var out := Game.output_dir()
	DirAccess.make_dir_recursive_absolute(out)
	_log = FileAccess.open(out.path_join("battle_parity.log"), FileAccess.WRITE)
	_run.call_deferred()


func log_line(s: String) -> void:
	print("PARITY " + s)
	if _log:
		_log.store_line(s)
		_log.flush()


func _line(tag: String, s: PackedInt32Array) -> String:
	var out := tag
	for c in 2:
		out += " | clan %d fight %3d rout %3d out %3d routs %3d scat %3d eng %3d" % [c,
			s[L.SUM_STATE + L.FIGHT * L.MAX_CLANS + c], s[L.SUM_STATE + L.ROUT * L.MAX_CLANS + c],
			s[L.SUM_STATE + L.LEFT * L.MAX_CLANS + c] + s[L.SUM_STATE + L.SCATTERED * L.MAX_CLANS + c],
			s[L.SUM_ROUTS + c], s[L.SUM_SCATTERS + c], s[L.SUM_ENGAGED + c]]
	return out


func _run() -> void:
	while not bw.started:
		await get_tree().process_frame
	bw.started = false
	bw.near.demote_all()
	var a: Array = Game.cmd.get("battle-parity", [])
	var seconds := float(a[0]) if a.size() > 0 else 60.0
	var info: Dictionary = bw._spawn_info
	var cpu := CrowdSimCpu.new()
	cpu.write_multimesh = false
	cpu.setup(bw.terrain, bw.params, info["starts"], info["sizes"], info["units"], bw.clan_blocks)
	var rids: Array[RID] = []
	var keep: Array[MultiMesh] = []
	for ci in info["sizes"].size():
		var m := MultiMesh.new()
		m.transform_format = MultiMesh.TRANSFORM_3D
		m.use_custom_data = true
		m.instance_count = int(info["sizes"][ci])
		keep.append(m)
		rids.append(m.get_rid())
	var gpu := CrowdSimGpu.new()
	gpu.readback_every = 1
	gpu.setup(bw.terrain, bw.params, info["starts"], info["sizes"], info["units"], bw.clan_blocks, rids)
	var dt := 1.0 / 30.0
	var steps := int(seconds / dt)
	var cpu_us := 0
	for k in steps:
		var t0 := Time.get_ticks_usec()
		cpu.step(dt)
		cpu_us += Time.get_ticks_usec() - t0
		gpu.step(dt)
		await get_tree().process_frame
		if k % int(10.0 / dt) == 0:
			log_line(_line("t=%5.1f CPU" % (k * dt), cpu.summary))
			log_line(_line("t=%5.1f GPU" % (k * dt), gpu.summary))
	for k in 6:
		await get_tree().process_frame
	log_line(_line("END CPU", cpu.summary))
	log_line(_line("END GPU", gpu.summary))
	var worst := 0.0
	for c in 2:
		for key in [L.SUM_SCATTERS + c, L.SUM_STATE + L.FIGHT * L.MAX_CLANS + c]:
			var x := float(cpu.summary[key])
			var y := float(gpu.summary[key])
			worst = maxf(worst, absf(x - y) / maxf(50.0, maxf(x, y)))
	log_line("worst relative difference %.3f (CPU %.2f ms per step)" % [worst, cpu_us / 1000.0 / steps])
	gpu.free_gpu()
	bw.shutdown_and_quit(0 if worst < 0.15 else 1)
