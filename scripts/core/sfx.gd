## Autoload `Sfx`: one-shot sounds (2D and positional), music per game state and ambience layers
## per mood. Sounds live in assets/audio/{sfx,ambience,music}/; `play("creak_door")` picks one of
## creak_door_1..n at random. Missing files are skipped silently (logged once).
extends Node

const ROOT := "res://assets/audio"

var _cache: Dictionary = {}       # name -> Array[AudioStream]
var _music: AudioStreamPlayer
var _music_name := ""
var _amb: Dictionary = {}         # name -> AudioStreamPlayer
var _amb_target: Dictionary = {}  # name -> linear volume target
var _missing: Dictionary = {}
var _listener_pos := Vector3.ZERO


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_music = AudioStreamPlayer.new()
	_music.bus = "Music"
	add_child(_music)
	_music.finished.connect(func() -> void: _music.play())


func _variants(name: String) -> Array:
	if _cache.has(name):
		return _cache[name]
	var out: Array = []
	for sub in ["sfx", "ambience", "music"]:
		var single := "%s/%s/%s.ogg" % [ROOT, sub, name]
		if ResourceLoader.exists(single):
			out.append(load(single))
		for i in range(1, 9):
			var p := "%s/%s/%s_%d.ogg" % [ROOT, sub, name, i]
			if ResourceLoader.exists(p):
				out.append(load(p))
	if out.is_empty() and not _missing.has(name):
		_missing[name] = true
		print("Sfx: no sound for '%s'" % name)
	_cache[name] = out
	return out


func play(name: String, volume_db: float = 0.0, pitch_jitter: float = 0.06) -> void:
	var v := _variants(name)
	if v.is_empty():
		return
	var p := AudioStreamPlayer.new()
	p.stream = v[randi() % v.size()]
	p.bus = "SFX"
	p.volume_db = volume_db
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	add_child(p)
	p.play()
	p.finished.connect(p.queue_free)


func play_at(name: String, pos: Vector3, volume_db: float = 0.0, max_dist: float = 30.0, pitch_jitter: float = 0.08) -> void:
	var v := _variants(name)
	if v.is_empty():
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = v[randi() % v.size()]
	p.bus = "SFX"
	p.volume_db = volume_db
	p.max_distance = max_dist
	p.unit_size = 4.0
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	add_child(p)
	p.global_position = pos
	p.play()
	p.finished.connect(p.queue_free)


func ui(name: String = "ui_click") -> void:
	play(name, -4.0, 0.03)


func music(name: String, fade_s: float = 1.5) -> void:
	if name == _music_name:
		return
	_music_name = name
	var v := _variants(name)
	var tw := create_tween()
	tw.tween_property(_music, "volume_db", -40.0, fade_s * 0.5)
	tw.tween_callback(func() -> void:
		if v.is_empty():
			_music.stop()
			return
		_music.stream = v[0]
		_music.play())
	tw.tween_property(_music, "volume_db", 0.0, fade_s * 0.5)


## Sets the target volume (0..1) of each ambience loop; others fade out.
func ambience(levels: Dictionary) -> void:
	for k: String in _amb:
		_amb_target[k] = 0.0
	for k: String in levels:
		if not _amb.has(k):
			var v := _variants(k)
			if v.is_empty():
				continue
			var p := AudioStreamPlayer.new()
			p.stream = v[0]
			p.bus = "Ambience"
			p.volume_db = -60.0
			add_child(p)
			p.play()
			p.finished.connect(p.play)
			_amb[k] = p
		_amb_target[k] = float(levels[k])


func _process(dt: float) -> void:
	for k: String in _amb:
		var p: AudioStreamPlayer = _amb[k]
		var target := linear_to_db(maxf(float(_amb_target.get(k, 0.0)), 0.0001))
		p.volume_db = move_toward(p.volume_db, target, dt * 25.0)
