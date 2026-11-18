## The memory journal (concept/ui/journal.png): an open leather-bound book. Left page: a grid of
## memory fragment cards (sepia vignettes, blank cards for the ones not found). Right page: the
## selected fragment, or the Villagers tab (discovered fears, overheard lines) or the Legend tab.
class_name JournalScreen
extends Control

signal closed

var _right: VBoxContainer
var _grid: GridContainer
var _tab := "memories"
var _selected := ""


func _ready() -> void:
	theme = UiKit.theme()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(UiKit.dim(0.6))
	var book := PanelContainer.new()
	var leather := UiKit._box(Color(0.32, 0.18, 0.1), Color(0.6, 0.42, 0.2), 4, 18)
	leather.content_margin_left = 22
	leather.content_margin_right = 22
	leather.content_margin_top = 22
	leather.content_margin_bottom = 22
	leather.shadow_color = Color(0, 0, 0, 0.5)
	leather.shadow_size = 16
	book.add_theme_stylebox_override("panel", leather)
	book.custom_minimum_size = Vector2(1240, 720)
	add_child(UiKit.centered(book))
	var vb := VBoxContainer.new()
	book.add_child(vb)
	var tabs := HBoxContainer.new()
	tabs.add_theme_constant_override("separation", 10)
	vb.add_child(tabs)
	tabs.add_child(UiKit.heading("Memory Journal", 30, UiKit.GOLD))
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tabs.add_child(sp)
	for t in [["Memories", "memories"], ["Villagers", "villagers"], ["Legend", "legend"], ["Haunting", "haunting"]]:
		var b := UiKit.button(t[0], _set_tab.bind(t[1]))
		b.custom_minimum_size = Vector2(150, 40)
		tabs.add_child(b)
	tabs.add_child(UiKit.button("Close", func() -> void: closed.emit()))
	var pages := HBoxContainer.new()
	pages.add_theme_constant_override("separation", 14)
	pages.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vb.add_child(pages)
	var left := UiKit.parchment()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	pages.add_child(left)
	var lscroll := ScrollContainer.new()
	lscroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	left.add_child(lscroll)
	_grid = GridContainer.new()
	_grid.columns = 5
	_grid.add_theme_constant_override("h_separation", 10)
	_grid.add_theme_constant_override("v_separation", 10)
	lscroll.add_child(_grid)
	var right := UiKit.parchment()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	pages.add_child(right)
	var rscroll := ScrollContainer.new()
	rscroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	right.add_child(rscroll)
	_right = VBoxContainer.new()
	_right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_right.add_theme_constant_override("separation", 10)
	rscroll.add_child(_right)
	_fill_cards()
	_set_tab("memories")


func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("journal") or e.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		closed.emit()


func _fill_cards() -> void:
	for c in _grid.get_children():
		c.queue_free()
	for f in Game.fragments_data.get("fragments", []):
		var have := Game.fragments.has(f["id"])
		var card := Button.new()
		card.custom_minimum_size = Vector2(104, 128)
		var st := UiKit._box(Color(0.78, 0.66, 0.46) if have else Color(0.85, 0.79, 0.66), Color(0.45, 0.3, 0.16, 0.9), 2, 6)
		card.add_theme_stylebox_override("normal", st)
		var sth := st.duplicate() as StyleBoxFlat
		sth.border_color = Color(0.85, 0.55, 0.15)
		card.add_theme_stylebox_override("hover", sth)
		card.add_theme_stylebox_override("pressed", sth)
		card.add_theme_stylebox_override("focus", sth)
		card.clip_text = true
		var l := UiKit.ink_label(String(f["vignette"]).left(60) + "…" if have else "?", 12 if have else 40)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		l.offset_left = 6
		l.offset_right = -6
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		if not have:
			l.add_theme_color_override("font_color", Color(0.5, 0.4, 0.3, 0.5))
		card.add_child(l)
		card.pressed.connect(func() -> void:
			Sfx.ui("ui_click")
			_selected = String(f["id"])
			_set_tab("memories"))
		_grid.add_child(card)


func _set_tab(t: String) -> void:
	_tab = t
	for c in _right.get_children():
		c.queue_free()
	match t:
		"memories":
			_show_fragment()
		"villagers":
			_show_villagers()
		"haunting":
			_show_haunting()
		"legend":
			_show_legend()


func _show_fragment() -> void:
	var total: int = Game.fragments_data.get("fragments", []).size()
	_right.add_child(_ink_heading("Memories found: %d / %d" % [Game.fragments.size(), total]))
	var f: Dictionary = Game.fragments_by_id.get(_selected, {})
	if f.is_empty() or not Game.fragments.has(_selected):
		for id: String in Game.fragments:
			f = Game.fragments_by_id[id]
	if f.is_empty() or not Game.fragments.has(String(f.get("id", ""))):
		_right.add_child(UiKit.ink_label("Mine natural blocks — grass, dirt, graveyard earth, stone, eerie ore — and memories of the dead float out of them.", 20))
		return
	var card := PanelContainer.new()
	var st := UiKit._box(Color(0.72, 0.58, 0.38), Color(0.4, 0.26, 0.12), 3, 8)
	st.content_margin_left = 20
	st.content_margin_right = 20
	st.content_margin_top = 30
	st.content_margin_bottom = 30
	card.add_theme_stylebox_override("panel", st)
	var v := UiKit.ink_label(String(f["vignette"]).capitalize().left(1) + String(f["vignette"]).substr(1), 18)
	v.add_theme_color_override("font_color", Color(0.3, 0.18, 0.08))
	v.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	card.add_child(v)
	_right.add_child(card)
	var t := UiKit.ink_label("“%s”" % f["text"], 24)
	t.add_theme_font_override("font", UiKit.font_heavy())
	_right.add_child(t)
	_right.add_child(UiKit.ink_label("— %s   ·   %s" % [f.get("owner_name", ""), String(f.get("emotion", "")).capitalize()], 18))
	var set_id: Variant = f.get("set", null)
	if set_id != null:
		for s in Game.fragments_data.get("sets", []):
			if s["id"] == set_id:
				var have := (s["fragments"] as Array).filter(func(x: String) -> bool: return Game.fragments.has(x)).size()
				_right.add_child(UiKit.ink_label("Set: %d / %d — completing it lets %s rest in your graveyard (run 2)." % [have, (s["fragments"] as Array).size(), f.get("owner_name", "")], 17))


func _show_villagers() -> void:
	_right.add_child(_ink_heading("The living of Millbrook"))
	for v in Game.population.get("villagers", []):
		var m: VillagerMind = Game.minds[v["id"]]
		var box := VBoxContainer.new()
		var name_l := UiKit.ink_label(String(v["name"]), 22)
		name_l.add_theme_font_override("font", UiKit.font_heavy())
		box.add_child(name_l)
		if v["role"] == "witness":
			box.add_child(UiKit.ink_label("Can't be scared. Sees everything and tells everyone (legend ×3).", 17))
		else:
			var fear := "Fears: " + (String(m.fear).replace("_", " ") if m.fear_discovered else "??? (drift close and listen: %d / %d lines)" % [m.heard_lines.size(), Game.tuning.i("overhear.lines_to_reveal_fear", 3)])
			box.add_child(UiKit.ink_label(fear, 17))
			var belief := "believer" if m.believer else ("skeptic" if m.skeptic else "believes")
			box.add_child(UiKit.ink_label("Belief: %s · Nerve %d · Suspicion %d%% · Scared %d×" % [belief, int(m.nerve), int(m.suspicion * 100), m.scares_taken], 16))
			if m.fear_discovered:
				box.add_child(UiKit.ink_label(String(v.get("fear_story", "")), 15))
		_right.add_child(box)


func _show_haunting() -> void:
	_right.add_child(_ink_heading("Haunting Fright: %d" % int(Game.path_fright["haunting"])))
	_right.add_child(UiKit.ink_label("Haunt props to build Unease. A successful BOO or a villager bolting earns Fright. Match their fear and scare them while alone and facing away for a better reward.", 17))
	var descriptions := {
		"flicker": "Dim or snuff lamps and lanterns to frighten nearby villagers.",
		"haunted_furniture": "Rock chairs, rattle wardrobes, and tilt portraits.",
		"bell_ringing": "Ring a bell to startle villagers and animals within earshot.",
		"object_possession": "Possess dolls or scarecrows and press Space to scare.",
		"animal_possession": "Possess a cat or dog and press Space to hiss or bark.",
		"villager_possession": "Possess an isolated, primed villager and press Space to vomit.",
		"door_slam": "Use strong Haunt on a door to slam it shut.",
		"blackout": "Snuff a light and up to two lights close to it.",
		"aftershock": "Your possession scare leaves a second pulse of fear.",
	}
	var fright := float(Game.path_fright["haunting"])
	var next := Game.tuning.next_level("haunting.levels", fright)
	if next.is_empty():
		_right.add_child(UiKit.ink_label("All haunting abilities unlocked.", 17))
	else:
		_right.add_child(UiKit.ink_label("Next: %s · %d Fright to go" % [next.name, ceili(float(next.fright) - fright)], 19))
		_right.add_child(UiKit.ink_label(descriptions.get(next.unlock, ""), 17))


func _show_legend() -> void:
	var ln := Game.town.legend_name()
	_right.add_child(_ink_heading(ln.capitalize() if ln != "" else "No legend yet"))
	_right.add_child(UiKit.ink_label("Legend points: %d   ·   Heat: %d" % [int(Game.town.legend_points), int(Game.town.heat)], 18))
	_right.add_child(UiKit.ink_label("Scares: %d (Legendary %d, Terrified %d, Spooked %d) · bolted %d · botched %d" % [
		Game.stats["scares"], Game.stats["legendary"], Game.stats["terrified"], Game.stats["spooked"], Game.stats["bolts"], Game.stats["botches"]], 16))
	_right.add_child(_ink_heading("Rumors at the tavern"))
	if Game.town.rumors.is_empty():
		_right.add_child(UiKit.ink_label("Nobody is talking about you. Yet.", 17))
	for r in Game.town.rumors:
		_right.add_child(UiKit.ink_label("“%s”" % r["text"], 17))
	_right.add_child(_ink_heading("Charms and salt"))
	for k: String in Game.town.charms:
		_right.add_child(UiKit.ink_label("%s: %s (%d nights)" % [k.replace("_", " "), String(Game.town.charms[k]["charm"]).replace("_", " "), int(Game.town.charms[k]["nights"])], 16))
	for k: String in Game.town.salt_lines:
		_right.add_child(UiKit.ink_label("Salt across %s (%d nights)" % [k.replace("_", " "), int(Game.town.salt_lines[k]["nights"])], 16))
	_right.add_child(_ink_heading("Remembrance"))
	for a in Game.areas:
		_right.add_child(UiKit.ink_label("%s: %d%%" % [a["name"], int(float(Game.town.remembrance.get(a["id"], 0)) * 100)], 15))


func _ink_heading(t: String) -> Label:
	var l := UiKit.ink_label(t, 24)
	l.add_theme_font_override("font", UiKit.font_heavy())
	l.add_theme_color_override("font_color", Color(0.35, 0.16, 0.08))
	return l
