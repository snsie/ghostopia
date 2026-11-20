## Battle prototype HUD: both clans' strength and per-flank Resolve (so the player can read which flank
## is wavering), the Parish bells, the ghost's HP / Ectoplasm / BOO, the Read panel for the targeted
## undead, scare grades, toasts, the end-of-battle panel and a small perf line.
class_name BattleHud
extends Control

var bw: Node
var _clan_panels: Array[Dictionary] = []
var _hp: ProgressBar
var _ecto: ProgressBar
var _boo: Label
var _tools: Label
var _tk: Label
var _bells: Label
var _target: PanelContainer
var _t_name: Label
var _t_form: ProgressBar
var _t_res: ProgressBar
var _t_state: Label
var _hint: Label
var _hint_until := 0.0
var _toasts: VBoxContainer
var _grade: Label
var _grade_until := 0.0
var _perf: Label
var _help: Label
var _end: Control


func setup(p_bw: Node) -> void:
	bw = p_bw
	theme = UiKit.theme()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build_top()
	_build_status()
	_build_target()
	_build_center()


func _ignore(c: Control) -> void:
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for ch in c.get_children():
		if ch is Control:
			_ignore(ch)


func _build_top() -> void:
	var row := HBoxContainer.new()
	row.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	row.add_theme_constant_override("separation", 18)
	row.position = Vector2(-470, 12)
	row.custom_minimum_size = Vector2(940, 0)
	add_child(row)
	for c in bw.clan_ids.size():
		var p := UiKit.panel()
		p.custom_minimum_size = Vector2(460, 0)
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 3)
		p.add_child(v)
		var col: Color = bw.clan_colors[c]
		var name := UiKit.label(bw.clan_names[c], 22, col)
		v.add_child(name)
		var strength := UiKit.bar(col, 430, 14)
		v.add_child(strength)
		var counts := UiKit.label("", 15)
		v.add_child(counts)
		var flanks := HBoxContainer.new()
		flanks.add_theme_constant_override("separation", 10)
		v.add_child(flanks)
		var fw := VBoxContainer.new()
		var fe := VBoxContainer.new()
		var lw := UiKit.label("West flank Resolve", 13, UiKit.WHITE.darkened(0.15))
		var le := UiKit.label("East flank Resolve", 13, UiKit.WHITE.darkened(0.15))
		var bwb := UiKit.bar(Color(0.7, 0.85, 1.0), 205, 10)
		var beb := UiKit.bar(Color(0.7, 0.85, 1.0), 205, 10)
		fw.add_child(lw)
		fw.add_child(bwb)
		fe.add_child(le)
		fe.add_child(beb)
		flanks.add_child(fw)
		flanks.add_child(fe)
		var extra := UiKit.label("", 15, UiKit.GOLD)
		v.add_child(extra)
		row.add_child(p)
		_clan_panels.append({"strength": strength, "counts": counts, "west": bwb, "east": beb, "extra": extra,
			"lw": lw, "le": le})
	_ignore(row)
	_toasts = VBoxContainer.new()
	_toasts.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	_toasts.position = Vector2(-380, 200)
	_toasts.custom_minimum_size = Vector2(360, 0)
	_toasts.add_theme_constant_override("separation", 6)
	add_child(_toasts)


func _build_status() -> void:
	var p := UiKit.panel()
	p.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	p.position = Vector2(16, -190)
	var v := VBoxContainer.new()
	p.add_child(v)
	v.add_child(UiKit.label("Ghost", 18, Color(0.7, 0.9, 1.0)))
	_hp = UiKit.bar(Color(0.55, 0.85, 1.0), 260, 14)
	v.add_child(_hp)
	_ecto = UiKit.bar(Color(0.55, 1.0, 0.75), 260, 10)
	v.add_child(_ecto)
	_boo = UiKit.label("", 16)
	v.add_child(_boo)
	_tk = UiKit.label("", 15, UiKit.GOLD)
	v.add_child(_tk)
	add_child(p)
	_ignore(p)
	_tools = UiKit.label("", 17)
	_tools.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_tools.position = Vector2(-300, -44)
	_tools.custom_minimum_size = Vector2(600, 0)
	_tools.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_tools)
	_hint = UiKit.label("", 19, UiKit.WHITE)
	_hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_hint.position = Vector2(-400, -84)
	_hint.custom_minimum_size = Vector2(800, 0)
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_hint)
	_bells = UiKit.label("", 17, Color(1.0, 0.75, 0.45))
	_bells.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_bells.position = Vector2(-300, 178)
	_bells.custom_minimum_size = Vector2(600, 0)
	_bells.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_bells)
	_perf = UiKit.label("", 13, UiKit.WHITE.darkened(0.3))
	_perf.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_perf.position = Vector2(-520, -50)
	_perf.custom_minimum_size = Vector2(500, 0)
	_perf.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	add_child(_perf)
	_help = UiKit.label("WASD drift · Space/Ctrl up/down · LMB swing tool (1 scythe, 2 shovel, 3 sledgehammer) · F BOO · E silence the bells / lift and throw a boulder · Esc menu", 15, UiKit.WHITE.darkened(0.1))
	_help.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_help.position = Vector2(-620, -20)
	_help.custom_minimum_size = Vector2(1240, 0)
	_help.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_help)
	for c: Control in [_tools, _hint, _bells, _perf, _help]:
		_ignore(c)


func _build_target() -> void:
	_target = UiKit.panel()
	_target.set_anchors_and_offsets_preset(Control.PRESET_CENTER_RIGHT)
	_target.position = Vector2(-300, -60)
	var v := VBoxContainer.new()
	_target.add_child(v)
	_t_name = UiKit.label("", 18)
	v.add_child(_t_name)
	v.add_child(UiKit.label("Form", 13))
	_t_form = UiKit.bar(Color(0.95, 0.6, 0.5), 240, 12)
	v.add_child(_t_form)
	v.add_child(UiKit.label("Resolve", 13))
	_t_res = UiKit.bar(Color(0.7, 0.85, 1.0), 240, 12)
	v.add_child(_t_res)
	_t_state = UiKit.label("", 15, UiKit.GOLD)
	v.add_child(_t_state)
	add_child(_target)
	_ignore(_target)
	_target.visible = false


func _build_center() -> void:
	var r := _Reticle.new()
	r.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	add_child(r)
	_grade = UiKit.heading("", 34, UiKit.GOLD)
	_grade.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_grade.position = Vector2(-500, 240)
	_grade.custom_minimum_size = Vector2(1000, 0)
	_grade.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(_grade)
	_ignore(_grade)


func hint(text: String) -> void:
	_hint.text = text
	_hint_until = Time.get_ticks_msec() / 1000.0 + 2.5


func toast(text: String, kind: String = "info") -> void:
	var p := UiKit.panel()
	var col := {"fear": UiKit.GOLD, "grade": UiKit.GOLD, "bad": Color(1.0, 0.6, 0.55)}.get(kind, UiKit.WHITE) as Color
	var l := UiKit.label(text, 18, col)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(330, 0)
	p.add_child(l)
	_ignore(p)
	_toasts.add_child(p)
	while _toasts.get_child_count() > 5:
		var first := _toasts.get_child(0)
		_toasts.remove_child(first)
		first.queue_free()
	get_tree().create_timer(6.0).timeout.connect(func() -> void:
		if is_instance_valid(p):
			p.queue_free())


func show_grade(text: String) -> void:
	_grade.text = text
	_grade_until = Time.get_ticks_msec() / 1000.0 + 4.0


func show_end(title: String, lines: Array[String], on_restart: Callable, on_quit: Callable) -> void:
	if _end:
		_end.queue_free()
	_end = Control.new()
	_end.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_end.add_child(UiKit.dim(0.45))
	var p := UiKit.parchment()
	p.custom_minimum_size = Vector2(620, 0)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	p.add_child(v)
	var h := UiKit.heading(title, 36, UiKit.INK)
	h.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(h)
	for line in lines:
		var l := UiKit.ink_label(line, 20)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		v.add_child(l)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 16)
	row.add_child(UiKit.button("Fight again", on_restart))
	row.add_child(UiKit.button("Quit to title", on_quit))
	v.add_child(row)
	_end.add_child(UiKit.centered(p))
	add_child(_end)


func hide_end() -> void:
	if _end:
		_end.queue_free()
		_end = null


func _process(_dt: float) -> void:
	if bw == null or not bw.started:
		return
	var now := Time.get_ticks_msec() / 1000.0
	var tot: Array = bw.clan_totals()
	for c in _clan_panels.size():
		var cp: Dictionary = _clan_panels[c]
		var t: Dictionary = tot[c]
		(cp["strength"] as ProgressBar).value = 100.0 * float(t["fighting"]) / maxf(1.0, float(t["start"]))
		(cp["counts"] as Label).text = "%d fighting · %d routing · %d scattered · %d fled" % [t["fighting"], t["routing"], t["scattered"], t["fled"]]
		(cp["west"] as ProgressBar).value = float(t["res_w"])
		(cp["east"] as ProgressBar).value = float(t["res_e"])
		(cp["lw"] as Label).text = "West flank Resolve %d (%d)" % [roundi(t["res_w"]), t["n_w"]]
		(cp["le"] as Label).text = "East flank Resolve %d (%d)" % [roundi(t["res_e"]), t["n_e"]]
		(cp["extra"] as Label).text = String(t.get("extra", ""))
	_bells.text = bw.bells_text()
	_hp.max_value = Game.max_hp()
	_hp.value = Game.hp
	_ecto.value = Game.ecto
	var cd: float = bw.player._boo_cd
	_boo.text = "F · BOO ready" if cd <= 0.0 else "F · BOO in %.1f s" % cd
	_tk.text = bw.telekinesis_text()
	var sel := Game.inventory.selected_id()
	var names := []
	for i in 3:
		var id: String = ["scythe", "shovel", "sledgehammer"][i]
		names.append(("[%d %s]" if id == sel else " %d %s ") % [i + 1, id.capitalize()])
	_tools.text = "   ".join(names)
	var a: NearActor = bw.read_target
	_target.visible = a != null and is_instance_valid(a)
	if _target.visible:
		var L := preload("res://scripts/battle/crowd_layout.gd")
		_t_name.text = "%s soldier" % bw.clan_names[a.clan()]
		(_t_name as Label).add_theme_color_override("font_color", bw.clan_colors[a.clan()])
		_t_form.value = a.rec[L.FORM]
		_t_res.value = a.rec[L.RESOLVE]
		var st: String = ["Fighting", "Routing!", "Scattering", "Gone"][clampi(a.state(), 0, 3)]
		if a.state() == L.FIGHT and a.rec[L.RESOLVE] < bw.params.shaken_below:
			st = "Shaken: takes extra damage"
		_t_state.text = st
	if now > _hint_until:
		_hint.text = ""
	_grade.visible = now < _grade_until
	_help.visible = bw.elapsed < 25.0
	_perf.text = bw.perf_text()


class _Reticle:
	extends Control

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		draw_arc(Vector2.ZERO, 7.0, 0.0, TAU, 24, Color(1, 1, 1, 0.8), 1.6, true)
		draw_circle(Vector2.ZERO, 1.6, Color(1, 1, 1, 0.9))
