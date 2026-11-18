## In-game HUD (concept/ui/hud.png): HP and Ectoplasm, the moon clock "until daylight", the hotbar,
## the Haunting Fright bar and level, the candle-flame Unease meter over villagers, the scare-grade
## stamp, overheard lines, toasts, pickups and the target hint.
class_name Hud
extends Control

var gw: Node
var hp_bar: ProgressBar
var hp_label: Label
var ecto_bar: ProgressBar
var ecto_label: Label
var clock: MoonClock
var clock_time: Label
var clock_caption: Label
var haunt_bar: ProgressBar
var haunt_label: Label
var presence_label: Label
var heat_bar: ProgressBar
var legend_label: Label
var area_label: Label
var hint_label: Label
var target_label: Label
var slots: Array[Dictionary] = []
var stamp: Label
var stamp_sub: Label
var toasts: VBoxContainer
var overheard_box: VBoxContainer
var pickup_label: Label
var meters: MeterLayer
var crosshair: Crosshair
var banner: Label
var clock_panel: PanelContainer
var hotbar_panel: PanelContainer
var paths_panel: PanelContainer
var _hint_until := 0.0
var _pickup_until := 0.0


func setup(p_gw: Node) -> void:
	gw = p_gw
	theme = UiKit.theme()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	meters = MeterLayer.new()
	meters.gw = gw
	meters.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	meters.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(meters)
	crosshair = Crosshair.new()
	crosshair.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(crosshair)
	_build_status()
	_build_clock()
	_build_hotbar()
	_build_paths()
	_build_center()
	Game.toast.connect(toast)
	Game.level_up.connect(_on_level_up)
	Game.fragment_found.connect(_on_fragment)


func _ignore(c: Control) -> void:
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for ch in c.get_children():
		if ch is Control:
			_ignore(ch)


func _build_status() -> void:
	var p := UiKit.panel()
	p.position = Vector2(18, 18)
	add_child(p)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 14)
	p.add_child(hb)
	var icon := GhostIcon.new()
	icon.custom_minimum_size = Vector2(64, 72)
	hb.add_child(icon)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 2)
	hb.add_child(vb)
	var r1 := HBoxContainer.new()
	r1.add_child(UiKit.heading("HP", 22))
	hp_label = UiKit.heading("10 / 10", 22, UiKit.GOLD)
	hp_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hp_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	r1.add_child(hp_label)
	vb.add_child(r1)
	hp_bar = UiKit.bar(UiKit.GREEN, 230, 16)
	vb.add_child(hp_bar)
	var r2 := HBoxContainer.new()
	r2.add_child(UiKit.heading("ECTOPLASM", 18))
	ecto_label = UiKit.heading("100 / 100", 18)
	ecto_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ecto_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	r2.add_child(ecto_label)
	vb.add_child(r2)
	ecto_bar = UiKit.bar(UiKit.ECTO, 230, 12)
	vb.add_child(ecto_bar)
	_ignore(p)


func _build_clock() -> void:
	var p := UiKit.panel()
	clock_panel = p
	add_child(p)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	p.add_child(hb)
	clock = MoonClock.new()
	clock.custom_minimum_size = Vector2(70, 70)
	hb.add_child(clock)
	var vb := VBoxContainer.new()
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	hb.add_child(vb)
	clock_time = UiKit.heading("00:00", 40, UiKit.GOLD)
	vb.add_child(clock_time)
	clock_caption = UiKit.heading("UNTIL DAYLIGHT", 16)
	vb.add_child(clock_caption)
	_ignore(p)


func _build_hotbar() -> void:
	var p := UiKit.panel()
	hotbar_panel = p
	add_child(p)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 8)
	p.add_child(hb)
	for i in 9:
		var slot := Panel.new()
		slot.custom_minimum_size = Vector2(70, 70)
		var st := UiKit._box(Color(0.08, 0.11, 0.2, 0.9), UiKit.CYAN * Color(1, 1, 1, 0.4), 2, 8)
		slot.add_theme_stylebox_override("panel", st)
		hb.add_child(slot)
		var icon := TextureRect.new()
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		icon.offset_left = 6
		icon.offset_top = 6
		icon.offset_right = -6
		icon.offset_bottom = -6
		slot.add_child(icon)
		var num := UiKit.label(str(i + 1), 14, UiKit.WHITE)
		num.position = Vector2(4, 0)
		slot.add_child(num)
		var cnt := UiKit.label("", 16, UiKit.GOLD)
		cnt.position = Vector2(38, 46)
		cnt.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		cnt.custom_minimum_size = Vector2(26, 0)
		slot.add_child(cnt)
		slots.append({"panel": slot, "icon": icon, "count": cnt, "style": st})
	_ignore(p)
	pickup_label = UiKit.heading("", 20, UiKit.GOLD)
	pickup_label.custom_minimum_size = Vector2(600, 0)
	pickup_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(pickup_label)


func _build_paths() -> void:
	var p := UiKit.panel()
	paths_panel = p
	add_child(p)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 4)
	p.add_child(vb)
	var r := HBoxContainer.new()
	var hicon := GhostIcon.new()
	hicon.custom_minimum_size = Vector2(36, 40)
	r.add_child(hicon)
	r.add_child(UiKit.heading("Haunting Fright", 19))
	haunt_label = UiKit.heading("Lv.1", 22, UiKit.GOLD)
	haunt_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	haunt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	r.add_child(haunt_label)
	vb.add_child(r)
	haunt_bar = UiKit.bar(UiKit.GREEN, 240, 14)
	vb.add_child(haunt_bar)
	presence_label = UiKit.label("Presence Lv.1 · Fright Essence 0", 16, Color(0.8, 0.9, 1.0))
	vb.add_child(presence_label)
	var hr := HBoxContainer.new()
	hr.add_child(UiKit.label("Heat ", 15, Color(1.0, 0.7, 0.55)))
	heat_bar = UiKit.bar(Color(1.0, 0.45, 0.3), 160, 8)
	heat_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	hr.add_child(heat_bar)
	vb.add_child(hr)
	legend_label = UiKit.label("", 15, UiKit.VIOLET.lightened(0.4))
	vb.add_child(legend_label)
	_ignore(p)


func _build_center() -> void:
	area_label = UiKit.heading("", 22, UiKit.WHITE)
	area_label.custom_minimum_size = Vector2(600, 0)
	area_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(area_label)
	banner = UiKit.heading("", 30, UiKit.RED)
	banner.custom_minimum_size = Vector2(800, 0)
	banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(banner)
	toasts = VBoxContainer.new()
	toasts.custom_minimum_size = Vector2(660, 0)
	toasts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(toasts)
	target_label = UiKit.heading("", 20, UiKit.WHITE)
	target_label.custom_minimum_size = Vector2(600, 0)
	target_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(target_label)
	hint_label = UiKit.heading("", 18, UiKit.GOLD)
	hint_label.custom_minimum_size = Vector2(600, 0)
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(hint_label)
	overheard_box = VBoxContainer.new()
	overheard_box.custom_minimum_size = Vector2(420, 0)
	overheard_box.alignment = BoxContainer.ALIGNMENT_END
	overheard_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(overheard_box)
	stamp = UiKit.heading("", 96, UiKit.GOLD)
	stamp.custom_minimum_size = Vector2(900, 0)
	stamp.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	stamp.add_theme_constant_override("outline_size", 22)
	stamp.add_theme_color_override("font_outline_color", Color(0.42, 0.18, 0.75, 0.95))
	stamp.pivot_offset = Vector2(450, 60)
	stamp.visible = false
	add_child(stamp)
	stamp_sub = UiKit.heading("", 22, UiKit.WHITE)
	stamp_sub.custom_minimum_size = Vector2(900, 0)
	stamp_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	stamp_sub.visible = false
	add_child(stamp_sub)


func _layout() -> void:
	var vs := get_viewport_rect().size
	clock_panel.position = Vector2(vs.x - clock_panel.size.x - 18, 18)
	hotbar_panel.position = Vector2((vs.x - hotbar_panel.size.x) * 0.5, vs.y - hotbar_panel.size.y - 16)
	paths_panel.position = Vector2(18, vs.y - paths_panel.size.y - 18)
	pickup_label.position = Vector2((vs.x - 600) * 0.5, vs.y - hotbar_panel.size.y - 56)
	area_label.position = Vector2((vs.x - 600) * 0.5, 20)
	banner.position = Vector2((vs.x - 800) * 0.5, 60)
	toasts.position = Vector2((vs.x - 660) * 0.5, 104)
	target_label.position = Vector2((vs.x - 600) * 0.5, vs.y * 0.5 + 34)
	hint_label.position = Vector2((vs.x - 600) * 0.5, vs.y * 0.5 + 66)
	overheard_box.position = Vector2(vs.x - 440, vs.y - 130 - overheard_box.size.y)
	stamp.position = Vector2((vs.x - 900) * 0.5, vs.y * 0.5 - 230)
	stamp_sub.position = Vector2((vs.x - 900) * 0.5, vs.y * 0.5 - 100)
	crosshair.position = vs * 0.5


func _process(_dt: float) -> void:
	if gw == null or gw.player == null:
		return
	_layout()
	var now := Time.get_ticks_msec() / 1000.0
	var mh := Game.max_hp()
	hp_bar.max_value = mh
	hp_bar.value = Game.hp
	hp_label.text = "%d / %d" % [ceili(Game.hp), int(mh)]
	var em := Game.tuning.f("player.ecto_max", 100.0)
	ecto_bar.max_value = em
	ecto_bar.value = Game.ecto
	ecto_label.text = "%d / %d" % [int(Game.ecto), int(em)]
	var ph := Game.phase()
	var secs := Game.seconds_until_daylight()
	if ph == "day":
		secs = Game.seconds_until_night()
		clock_caption.text = "UNTIL NIGHTFALL"
		clock_time.add_theme_color_override("font_color", UiKit.RED)
	else:
		clock_caption.text = "UNTIL DAYLIGHT"
		clock_time.add_theme_color_override("font_color", UiKit.GOLD if secs > 60.0 else UiKit.RED)
	clock_time.text = "%02d:%02d" % [int(secs) / 60, int(secs) % 60]
	clock.t = Game.cycle_t
	clock.queue_redraw()
	var lvl := Game.haunting_level()
	var f := float(Game.path_fright["haunting"])
	var cur := Game.tuning.level_for("haunting.levels", f)
	var nxt := Game.tuning.next_level("haunting.levels", f)
	haunt_label.text = "Lv.%d %s" % [lvl, String(cur.get("name", ""))]
	if nxt.is_empty():
		haunt_bar.value = 100
		haunt_label.text = "All abilities unlocked"
	else:
		var a := float(cur.get("fright", 0))
		var b := float(nxt.get("fright", 1))
		haunt_label.text = "%d Fright to %s" % [ceili(b - f), nxt.get("name", "")]
		haunt_bar.value = (f - a) / maxf(b - a, 1.0) * 100.0
	presence_label.text = "Presence Lv.%d · Fright Essence %d" % [int(Game.presence_level().get("level", 1)), int(Game.fright_essence)]
	heat_bar.value = Game.town.heat
	var ln := Game.town.legend_name()
	legend_label.text = ("Legend: " + ln) if ln != "" else "Nobody has noticed you yet"
	var area := Game.area_at(gw.player.global_position)
	var rem := float(Game.town.remembrance.get(area.get("id", ""), 1.0))
	area_label.text = "%s  ·  Remembrance %d%%" % [String(area.get("name", "The Veil")), int(rem * 100)]
	area_label.add_theme_color_override("font_color", UiKit.WHITE if rem >= Game.tuning.f("remembrance.fading_below", 0.4) else Color(0.7, 0.65, 0.85))
	_update_hotbar()
	_update_target()
	banner.text = ""
	if ph == "dawn" or (ph == "night" and Game.cycle_t > Game.tuning.f("cycle.dawn_warning_t", 0.555)):
		banner.text = "Dawn is coming. Get underground or to the mausoleum!" if not gw.player.sheltered else ""
	elif ph == "day" and not gw.player.sheltered:
		banner.text = "Daylight burns! Find shelter."
	if now > _hint_until:
		hint_label.text = ""
	if now > _pickup_until:
		pickup_label.text = ""


func _update_hotbar() -> void:
	var inv := Game.inventory
	for i in 9:
		var id := inv.hotbar[i]
		var s: Dictionary = slots[i]
		(s["icon"] as TextureRect).texture = UiKit.icon_for(id) if id != "" else null
		var cnt := "" if id == "" or inv.is_tool(id) else str(inv.count(id))
		(s["count"] as Label).text = cnt
		var st: StyleBoxFlat = s["style"]
		st.border_color = UiKit.GOLD if i == inv.selected else UiKit.CYAN * Color(1, 1, 1, 0.4)
		st.set_border_width_all(3 if i == inv.selected else 2)
		st.bg_color = Color(0.14, 0.2, 0.32, 0.95) if i == inv.selected else Color(0.08, 0.11, 0.2, 0.9)


func _update_target() -> void:
	var pl: Player = gw.player
	var txt := ""
	if pl.target_hauntable:
		var h := pl.target_hauntable
		var g := h.gentle_action()
		var s := h.strong_action()
		var nm := h.kind.replace("_", " ").capitalize()
		if Game.town.is_unhauntable(h.id):
			txt = "%s  ·  charmed" % nm
		elif not Game.ability_unlocked(h.ability()):
			txt = "%s  ·  needs Haunting %d (%s)" % [nm, int(h.data.get("level", 1)), h.ability().capitalize()]
		elif h.is_light() and not h.lit:
			txt = "%s  ·  out" % nm
		else:
			txt = "%s   [E] %s   [R] %s" % [nm, g.replace("_", " ").capitalize(), s.replace("_", " ").capitalize()]
	elif pl.near_workbench():
		txt = "[Q] Spectral Workbench"
	elif pl.global_position.distance_to(_respawn()) < 3.0:
		txt = "[Q] Sleep until dusk" if Game.phase() in ["day", "dawn"] else "Mausoleum"
	elif not pl.target_node.is_empty():
		var nd: Dictionary = gw.level.gather_nodes[pl.target_node["id"]]["data"]
		txt = "%s  ·  scythe" % String(nd["kind"]).replace("_", " ").capitalize()
	elif pl.target_block.get("hit", false):
		var b: int = pl.target_block["block"]
		var info := Game.blocks.info(b)
		txt = "%s  ·  %s %s" % [String(info.get("name", "")), String(info.get("tool", "")), String(info.get("tier_name", ""))]
	target_label.text = txt
	crosshair.active = pl.target_hauntable != null


func _respawn() -> Vector3:
	var r: Dictionary = Game.markers_by_id.get("respawn", {})
	var p: Array = r.get("pos", [0, -100, 0])
	return Vector3(p[0], p[1], p[2])


func hint(text: String) -> void:
	hint_label.text = text
	_hint_until = Time.get_ticks_msec() / 1000.0 + 2.5


func pickup(text: String) -> void:
	pickup_label.text = text
	_pickup_until = Time.get_ticks_msec() / 1000.0 + 2.0


func toast(text: String, kind: String = "info") -> void:
	var p := UiKit.panel()
	var col := {"fear": UiKit.GOLD, "memory": Color(1.0, 0.75, 0.6), "legend": UiKit.VIOLET.lightened(0.35),
		"level": UiKit.GREEN, "fragment": Color(1.0, 0.88, 0.6), "set": UiKit.GOLD}.get(kind, UiKit.WHITE) as Color
	var l := UiKit.label(text, 19, col)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	p.add_child(l)
	_ignore(p)
	toasts.add_child(p)
	while toasts.get_child_count() > 4:
		toasts.get_child(0).queue_free()
		toasts.remove_child(toasts.get_child(0))
	var tw := create_tween()
	tw.tween_interval(4.5)
	tw.tween_property(p, "modulate:a", 0.0, 0.8)
	tw.tween_callback(p.queue_free)


func overheard(who: String, line: String) -> void:
	var p := UiKit.panel()
	var vb := VBoxContainer.new()
	p.add_child(vb)
	vb.add_child(UiKit.label(who, 15, UiKit.GOLD))
	var l := UiKit.label("“%s”" % line, 18)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(380, 0)
	vb.add_child(l)
	_ignore(p)
	overheard_box.add_child(p)
	while overheard_box.get_child_count() > 3:
		var c := overheard_box.get_child(0)
		overheard_box.remove_child(c)
		c.queue_free()
	var tw := create_tween()
	tw.tween_interval(6.0)
	tw.tween_property(p, "modulate:a", 0.0, 1.0)
	tw.tween_callback(p.queue_free)


func show_grade(res: Dictionary) -> void:
	var outcome := String(res.get("outcome", ""))
	var text := ""
	var col := UiKit.GOLD
	var sub := ""
	match outcome:
		"legendary":
			text = "LEGENDARY!"
			col = Color(1.0, 0.86, 0.3)
		"terrified":
			text = "TERRIFIED!"
		"spooked":
			text = "SPOOKED!"
			col = Color(0.85, 0.95, 1.0)
		"bolt":
			text = "BOLTED"
			col = Color(0.75, 0.75, 0.85)
			sub = "Pushed too hard: %s ran for it. Weak payout." % res.get("villager_name", "")
		"botch":
			text = "BOTCHED"
			col = Color(1.0, 0.55, 0.5)
			sub = "%s %s" % [res.get("villager_name", ""), "spotted you!" if res.get("reason") == "spotted" else "laughed it off and got braver."]
		_:
			return
	if outcome in ["legendary", "terrified", "spooked"]:
		var parts: Array = res.get("parts", [])
		sub = "%s  ·  +%d Fright  ·  %s" % [res.get("villager_name", ""), int(res.get("fright", 0)),
			", ".join(parts.map(func(x: String) -> String: return x.replace("_", " ").replace("unease over 0 9", "at the peak")))]
		if res.get("witnessed", false):
			sub += "  ·  Pip saw it!"
	stamp.text = text
	stamp.add_theme_color_override("font_color", col)
	stamp_sub.text = sub
	stamp.visible = true
	stamp_sub.visible = true
	stamp.modulate.a = 1.0
	stamp_sub.modulate.a = 1.0
	stamp.scale = Vector2(2.2, 2.2)
	stamp.rotation = deg_to_rad(-8)
	Sfx.play("grade_stamp", 0.0, 0.0)
	var tw := create_tween()
	tw.set_ignore_time_scale(true)
	tw.tween_property(stamp, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_interval(2.0)
	tw.tween_property(stamp, "modulate:a", 0.0, 0.8)
	tw.parallel().tween_property(stamp_sub, "modulate:a", 0.0, 0.8)
	tw.tween_callback(func() -> void:
		stamp.visible = false
		stamp_sub.visible = false)


func _on_level_up(path: String, level: int, unlock: String) -> void:
	Sfx.play("level_up")
	if path == "haunting":
		toast("Haunting level %d! You can now %s." % [level, unlock.replace("_", " ").capitalize() if unlock != "" else "do more"], "level")
	else:
		toast("Presence level %d · Choose a ghost trait in Inventory" % level, "level")


func _on_fragment(id: String) -> void:
	var f: Dictionary = Game.fragments_by_id.get(id, {})
	toast("Memory fragment: “%s”  (%s)" % [f.get("text", ""), f.get("owner_name", "")], "fragment")


# ---------------------------------------------------------------- drawn widgets

class GhostIcon:
	extends Control
	func _draw() -> void:
		var s := size
		var c := Vector2(s.x * 0.5, s.y * 0.42)
		var r := minf(s.x, s.y) * 0.36
		var pts := PackedVector2Array()
		for i in 17:
			var a := PI + PI * float(i) / 16.0
			pts.append(c + Vector2(cos(a), sin(a)) * r)
		var bottom := s.y * 0.92
		pts.append(Vector2(c.x + r, bottom - r * 0.2))
		for i in 4:
			var x := c.x + r - (2.0 * r) * float(i + 1) / 4.0
			pts.append(Vector2(x + r * 0.25, bottom))
			pts.append(Vector2(x, bottom - r * 0.25))
		draw_colored_polygon(pts, Color(0.95, 0.97, 1.0))
		draw_polyline(pts + PackedVector2Array([pts[0]]), Color(0.55, 0.85, 1.0, 0.8), 2.0)
		draw_circle(c + Vector2(-r * 0.35, 0), r * 0.16, Color(0.08, 0.06, 0.15))
		draw_circle(c + Vector2(r * 0.35, 0), r * 0.16, Color(0.08, 0.06, 0.15))


class MoonClock:
	extends Control
	var t := 0.0
	func _draw() -> void:
		var c := size * 0.5
		var r := minf(size.x, size.y) * 0.46
		draw_circle(c, r, Color(0.08, 0.12, 0.25))
		draw_arc(c, r, 0, TAU, 48, UiKit.CYAN, 2.0)
		# night progress ring
		var night := clampf((t - 0.08) / 0.5, 0.0, 1.0)
		draw_arc(c, r - 4, -PI / 2, -PI / 2 + TAU * night, 48, UiKit.GOLD, 3.0)
		draw_circle(c, r * 0.62, Color(0.88, 0.93, 1.0))
		draw_circle(c + Vector2(r * 0.28, -r * 0.1), r * 0.55, Color(0.08, 0.12, 0.25))


class Crosshair:
	extends Control
	var active := false
	func _process(_dt: float) -> void:
		queue_redraw()
	func _draw() -> void:
		var col := UiKit.VIOLET.lightened(0.3) if active else Color(1, 1, 1, 0.75)
		draw_arc(Vector2.ZERO, 7.0 if active else 4.0, 0, TAU, 20, col, 2.0)
		if active:
			draw_arc(Vector2.ZERO, 13.0, 0, TAU, 24, Color(col, 0.4), 1.5)


## Candle-flame Unease meters over villagers (and a little fear icon once the fear is known).
class MeterLayer:
	extends Control
	var gw: Node
	func _process(_dt: float) -> void:
		queue_redraw()
	func _draw() -> void:
		if gw == null or gw.player == null:
			return
		var cam: Camera3D = gw.player.camera
		var pl: Player = gw.player
		var font := UiKit.font_heavy()
		for n: Npc in gw.npcs:
			if not n.visible or not n.is_target():
				continue
			var d := n.global_position.distance_to(pl.global_position)
			var show := n == pl.target_npc or (n.mind.unease > 0.5 and d < 16.0)
			if not show or d > 22.0:
				continue
			var hp := n.head_pos() + Vector3(0, 0.3, 0)
			if cam.is_position_behind(hp):
				continue
			var sp := cam.unproject_position(hp)
			var frac := clampf(n.mind.frac(), 0.0, 1.0)
			var w := 92.0
			var h := 14.0
			var origin := sp + Vector2(-w * 0.5 + 12, 0)
			# flame icon
			var fc := Color(1.0, 0.85, 0.3).lerp(Color(1.0, 0.25, 0.15), frac)
			var flame := PackedVector2Array([sp + Vector2(-w * 0.5 - 8, 8), sp + Vector2(-w * 0.5 + 2, -2),
				sp + Vector2(-w * 0.5 - 2, -16), sp + Vector2(-w * 0.5 - 12, -2)])
			draw_colored_polygon(flame, fc)
			draw_circle(sp + Vector2(-w * 0.5 - 5, 3), 6.0, fc)
			draw_rect(Rect2(origin, Vector2(w, h)), Color(0.04, 0.03, 0.1, 0.85))
			var segs := 6
			for i in segs:
				var a := float(i) / float(segs)
				if frac > a:
					var cc := Color(1.0, 0.85, 0.3).lerp(Color(1.0, 0.2, 0.15), a)
					var fill := clampf((frac - a) * segs, 0.0, 1.0)
					draw_rect(Rect2(origin + Vector2(w * a + 1, 2), Vector2((w / segs - 2) * fill, h - 4)), cc)
			# sweet spot marker (primed) and overflow edge
			var primed := ScareMath.stage_from("primed", Game.tuning.a("scare.stages"))
			draw_line(origin + Vector2(w * primed, -3), origin + Vector2(w * primed, h + 3), UiKit.VIOLET.lightened(0.4), 2.0)
			draw_rect(Rect2(origin, Vector2(w, h)), UiKit.CYAN * Color(1, 1, 1, 0.6), false, 1.5)
			var label := String(n.data["name"])
			if n.mind.fear_discovered:
				label += "  · fears " + String(n.mind.fear).replace("_", " ")
			if frac >= primed:
				label += "  · BOO now!"
			draw_string(font, origin + Vector2(0, -6), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(1, 1, 1, 0.95))
