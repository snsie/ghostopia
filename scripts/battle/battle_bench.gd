## `--battle-bench [measure_s] [warmup_s]`: runs the battle on the GPU crowd at 1080p with vsync off,
## the ghost hovering along the front line (so the near tier holds its full 32 actors), BOOing every few
## seconds, and logs frame times to battle_bench.log / battle_bench.json next to the autotest output.
##   godot --path . -- --battle-bench 40 20
##   Ghostopia.exe -- --battle-bench           (exported build; Ghostopia.app on macOS)
extends Node

const L := preload("res://scripts/battle/crowd_layout.gd")

var bw: Node
var _out := ""
var _log: FileAccess


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_out = Game.output_dir()
	DirAccess.make_dir_recursive_absolute(_out)
	_log = FileAccess.open(_out.path_join("battle_bench.log"), FileAccess.WRITE)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	if DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_WINDOWED:
		DisplayServer.window_set_size(Vector2i(1920, 1080))
	_run.call_deferred()


func log_line(s: String) -> void:
	print("BENCH " + s)
	if _log:
		_log.store_line(s)
		_log.flush()


func _arg(i: int, fallback: float) -> float:
	var a: Array = Game.cmd.get("battle-bench", [])
	return float(a[i]) if a.size() > i else fallback


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var p := _out.path_join("bench_%s.png" % name)
	img.save_png(p)
	log_line("SHOT %s" % p.get_file())


func _place(t: float) -> void:
	# drift back and forth along the ford, just above the melee, looking down the line
	var x := 64.0 + sin(t * 0.25) * 12.0
	var p: Player = bw.player
	p.teleport(Vector3(x, 8.6, 57.0), 180.0)
	p.aim_at(Vector3(x + cos(t * 0.25) * 6.0, 7.5, 64.0))


func _run() -> void:
	while not bw.started:
		await get_tree().process_frame
	var measure := _arg(0, 40.0)
	var warm := _arg(1, 20.0)
	var vp := get_viewport().get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	log_line("adapter: %s (%s) · %s · %s" % [RenderingServer.get_video_adapter_name(), RenderingServer.get_video_adapter_vendor(),
		OS.get_name(), RenderingServer.get_current_rendering_driver_name() if RenderingServer.has_method("get_current_rendering_driver_name") else ""])
	log_line("window %s · crowd %s · units %d · near max %d" % [DisplayServer.window_get_size(), "GPU" if bw.gpu else "CPU", bw.sim.n, bw.near.max_count])
	var t := 0.0
	while t < warm:
		_place(t)
		await get_tree().process_frame
		t += get_process_delta_time()
	await _shot("before")
	var frames: Array[float] = []
	var gpu_ms: Array[float] = []
	var cpu_ms: Array[float] = []
	var logic_ms: Array[float] = []
	var actors: Array[int] = []
	var last := Time.get_ticks_usec()
	var boo_t := 0.0
	var start_rb: int = bw.sim.readbacks if bw.gpu else 0
	var start_promo: int = bw.near.promotions
	t = 0.0
	while t < measure:
		_place(warm + t)
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		var dt_ms := (now - last) / 1000.0
		last = now
		t += dt_ms / 1000.0
		frames.append(dt_ms)
		gpu_ms.append(RenderingServer.viewport_get_measured_render_time_gpu(vp))
		cpu_ms.append(RenderingServer.viewport_get_measured_render_time_cpu(vp) + RenderingServer.get_frame_setup_time_cpu())
		logic_ms.append(bw._frame_ms.back() if not bw._frame_ms.is_empty() else 0.0)
		actors.append(bw.near.actors.size())
		boo_t += dt_ms / 1000.0
		if boo_t > 6.0:
			boo_t = 0.0
			Game.ecto = 100.0
			bw.player._boo_cd = 0.0
			bw.player.do_boo()
	await _shot("after")
	var res := {
		"adapter": RenderingServer.get_video_adapter_name(), "os": OS.get_name(), "crowd": "GPU" if bw.gpu else "CPU",
		"units": bw.sim.n, "window": [DisplayServer.window_get_size().x, DisplayServer.window_get_size().y],
		"frames": frames.size(), "seconds": t,
		"fps_avg": frames.size() / maxf(t, 0.001),
		"frame_ms": _stats(frames), "gpu_render_ms": _stats(gpu_ms), "cpu_render_ms": _stats(cpu_ms),
		"battle_logic_ms": _stats(logic_ms),
		"near_actors_avg": _avg_i(actors), "near_actors_max": actors.max() if not actors.is_empty() else 0,
		"readbacks": (bw.sim.readbacks - start_rb) if bw.gpu else -1,
		"promotions": bw.near.promotions - start_promo,
		"clans": bw.clan_totals(),
		"target_60fps": _stats(frames)["p95"] <= 16.7,
	}
	log_line(JSON.stringify(res, "  "))
	var f := FileAccess.open(_out.path_join("battle_bench.json"), FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(res, "  "))
	log_line("RESULT fps %.1f · frame p50 %.2f / p95 %.2f / p99 %.2f ms · GPU %.2f ms · logic %.2f ms · actors %.1f" % [
		res["fps_avg"], res["frame_ms"]["p50"], res["frame_ms"]["p95"], res["frame_ms"]["p99"], res["gpu_render_ms"]["avg"],
		res["battle_logic_ms"]["avg"], res["near_actors_avg"]])
	bw.shutdown_and_quit(0)


func _stats(a: Array[float]) -> Dictionary:
	if a.is_empty():
		return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
	var s := a.duplicate()
	s.sort()
	var sum := 0.0
	for v in s:
		sum += v
	return {"avg": sum / s.size(), "p50": s[int(s.size() * 0.5)], "p95": s[mini(s.size() - 1, int(s.size() * 0.95))],
		"p99": s[mini(s.size() - 1, int(s.size() * 0.99))], "max": s.back()}


func _avg_i(a: Array[int]) -> float:
	var s := 0
	for v in a:
		s += v
	return float(s) / maxf(1.0, a.size())
