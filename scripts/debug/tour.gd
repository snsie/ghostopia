## `--tour`: screenshots matching each concept image (renders/game/tour_<name>.png); then
## `python tools/compare_game.py` puts them side by side with the concept art.
##   --tour                         all concept views
##   --tour x,z,yaw[,pitch[,y]] ... ghost-view shots at given spots
##   --tour cam,px,py,pz,tx,ty,tz   free-camera shots
extends Node

const VIEWS := [
	# name, concept, cycle t, fading, camera pos, look target, hud
	["millbrook_night", "locations/millbrook_night.png", 0.27, 0.0, Vector3(124, 40, 132), Vector3(106, 22, 92), false],
	["millbrook_dusk", "locations/millbrook_dusk.png", 0.03, 0.0, Vector3(124, 40, 132), Vector3(106, 22, 92), false],
	["millbrook_day", "locations/millbrook_day.png", 0.8, 0.0, Vector3(124, 40, 132), Vector3(106, 22, 92), false],
	["millbrook_fading", "locations/millbrook_fading.png", 0.27, 1.0, Vector3(124, 40, 132), Vector3(106, 22, 92), false],
	["graveyard_night", "locations/graveyard_night.png", 0.27, 0.0, Vector3(46, 36, 108), Vector3(29, 28, 91), false],
	["graveyard_day", "locations/graveyard_day.png", 0.8, 0.0, Vector3(46, 36, 108), Vector3(29, 28, 91), false],
	["mill_night", "locations/mill_night.png", 0.30, 0.0, Vector3(90, 34, 66), Vector3(99, 29, 52), false],
	["cottage_interior_night", "locations/cottage_interior_night.png", 0.27, 0.0, Vector3(104.2, 23.5, 84.0), Vector3(101.8, 21.6, 80.4), false],
	["cottage_interior_day", "locations/cottage_interior_day.png", 0.8, 0.0, Vector3(104.2, 23.5, 84.0), Vector3(101.8, 21.6, 80.4), false],
	["mining_night", "locations/mining_night.png", 0.27, 0.0, Vector3(36.5, 31, 84.5), Vector3(33, 28.5, 79.5), false],
	["world_map", "locations/world_map.png", 0.27, 0.0, Vector3(96, 190, 150), Vector3(96, 20, 96), false],
	["hud", "ui/hud.png", 0.2, 0.0, Vector3.ZERO, Vector3(113, 22, 100), true],
]

var gw: Node
var _out := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_out = Game.output_dir()
	DisplayServer.window_set_size(Vector2i(1600, 900))
	_run.call_deferred()


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var p := _out.path_join("tour_%s.png" % name)
	get_viewport().get_texture().get_image().save_png(p)
	print("TOUR %s" % p)


func _wait(s: float) -> void:
	await get_tree().create_timer(s, true, false, true).timeout


func _set_time(t: float) -> void:
	gw.time_frozen = true
	Game.cycle_t = t
	for n: Npc in gw.npcs:
		n.mode = Npc.Mode.SCHEDULE
		n._hidden_until = 0.0
		n._snap_to_schedule()
	gw.daynight.update(t)


func _run() -> void:
	await _wait(0.5)
	var args: Array = Game.cmd.get("tour", [])
	var cam := Camera3D.new()
	cam.fov = 55.0
	cam.far = 600.0
	gw.add_child(cam)
	var p: Player = gw.player
	if args.is_empty():
		for v in VIEWS:
			_set_time(v[2])
			for k: String in Game.town.remembrance:
				Game.town.remembrance[k] = 0.05 if float(v[3]) > 0.5 else float(_start_rem(k))
			gw.world.set_remembrance(Game.areas, Game.town.remembrance, 0.4, 0.1)
			gw.daynight.fade_k = float(v[3])
			gw.hud.visible = v[6]
			if v[6]:
				p.teleport(Vector3(116.0, 22.2, 106.0), 200.0)
				p.aim_at(v[5])
				p.camera.current = true
			else:
				p.teleport((v[4] as Vector3) + Vector3(0, -50, 0) if v[0] == "world_map" else Vector3(36, 29.2, 82) if v[0] == "mining_night" else Vector3(28, 29, 92), 0.0)
				if v[0] == "mining_night":
					p.aim_at(Vector3(33, 28.5, 79.5))
					var inv := Game.inventory
					inv.selected = inv.hotbar.find("sledgehammer")
					p._refresh_tool()
				cam.global_position = v[4]
				cam.look_at(v[5], Vector3.UP)
				cam.current = true
			gw.daynight.update(v[2])
			await _wait(1.2)
			await _shot(v[0])
	else:
		var i := 0
		for a: String in args:
			var parts := a.split(",")
			i += 1
			if parts[0] == "cam":
				cam.global_position = Vector3(float(parts[1]), float(parts[2]), float(parts[3]))
				cam.look_at(Vector3(float(parts[4]), float(parts[5]), float(parts[6])), Vector3.UP)
				cam.current = true
			else:
				var x := float(parts[0])
				var z := float(parts[1])
				var y: float = float(parts[4]) if parts.size() > 4 else float(gw.world.ground_below(Vector3(x, 46, z))) + 1.0
				p.teleport(Vector3(x, y, z), float(parts[2]))
				if parts.size() > 3:
					p.set_look(p.look_yaw(), deg_to_rad(float(parts[3])))
				p.camera.current = true
			await _wait(1.0)
			await _shot("spot_%02d" % i)
	get_tree().quit(0)


func _start_rem(id: String) -> float:
	for a in Game.areas:
		if a["id"] == id:
			return float(a.get("remembrance", 0.5))
	return 0.5
