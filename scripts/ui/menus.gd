## The Scattered screen, the pause menu and the settings panel (audio, graphics, controls, mouse
## sensitivity, invert Y), all built from the UiKit.
class_name Menus
extends RefCounted


static func scattered(dropped: float, on_return: Callable) -> Control:
	var root := Control.new()
	root.theme = UiKit.theme()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(UiKit.dim(0.6))
	var p := UiKit.parchment()
	p.custom_minimum_size = Vector2(560, 300)
	root.add_child(UiKit.centered(p))
	var vb := VBoxContainer.new()
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	vb.add_theme_constant_override("separation", 14)
	p.add_child(vb)
	var h := UiKit.heading("Scattered", 52, Color(0.92, 0.96, 1.0))
	h.add_theme_color_override("font_outline_color", Color(0.25, 0.4, 0.7))
	h.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(h)
	var t := UiKit.ink_label("Daylight burned you into wisps. They drift home to the mausoleum." +
		("\nYou dropped %d Fright Essence where you fell — go back for it." % int(dropped) if dropped > 0 else ""), 20)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(t)
	var b := UiKit.button("Return to Mausoleum", on_return)
	b.name = "ReturnButton"
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	vb.add_child(b)
	return root


static func pause(actions: Dictionary) -> Control:
	var root := Control.new()
	root.theme = UiKit.theme()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(UiKit.dim(0.5))
	var p := UiKit.panel()
	p.custom_minimum_size = Vector2(380, 0)
	root.add_child(UiKit.centered(p))
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 10)
	p.add_child(vb)
	var h := UiKit.heading("Paused", 40, UiKit.GOLD)
	h.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(h)
	for key: String in actions:
		var b := UiKit.button(key, actions[key])
		b.name = key.replace(" ", "")
		vb.add_child(b)
	return root


static func settings(on_close: Callable) -> Control:
	var root := Control.new()
	root.theme = UiKit.theme()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(UiKit.dim(0.55))
	var p := UiKit.parchment()
	p.custom_minimum_size = Vector2(760, 600)
	root.add_child(UiKit.centered(p))
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 8)
	p.add_child(vb)
	var top := HBoxContainer.new()
	var h := UiKit.ink_label("Settings", 38)
	h.add_theme_font_override("font", UiKit.font_heavy())
	h.add_theme_color_override("font_color", Color(0.35, 0.16, 0.08))
	h.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(h)
	# the little ghost bookmark
	var bm := Hud.GhostIcon.new()
	bm.custom_minimum_size = Vector2(46, 52)
	top.add_child(bm)
	vb.add_child(top)
	vb.add_child(_section("Audio"))
	for k in [["Master", "master"], ["Music", "music"], ["Sound effects", "sfx"], ["Ambience", "ambience"]]:
		vb.add_child(_slider(k[0], k[1], 0.0, 1.0, 0.05))
	vb.add_child(_section("Graphics"))
	var g := GridContainer.new()
	g.columns = 3
	vb.add_child(g)
	for k in [["Fullscreen", "fullscreen"], ["Shadows", "shadows"], ["Ink outlines", "outlines"], ["Bloom", "glow"], ["Fog", "fog"], ["V-Sync", "vsync"]]:
		g.add_child(_check(k[0], k[1]))
	vb.add_child(_slider("Render scale", "render_scale", 0.5, 1.0, 0.05))
	vb.add_child(_section("Controls"))
	vb.add_child(_slider("Mouse sensitivity", "mouse_sensitivity", 0.2, 3.0, 0.05))
	vb.add_child(_check("Invert Y", "invert_y"))
	var keys := UiKit.ink_label("WASD drift · Space rise (Ectoplasm) · Ctrl sink · Shift faster · Mouse look · LMB tool / place · RMB place · 1-9 hotbar · E haunt (gentle) · R haunt (strong) · F BOO · Q workbench / sleep · J journal · Tab inventory · Esc pause", 15)
	vb.add_child(keys)
	var close := UiKit.button("Done", func() -> void:
		Game.save_settings()
		on_close.call())
	close.name = "DoneButton"
	close.size_flags_horizontal = Control.SIZE_SHRINK_END
	vb.add_child(close)
	return root


static func _section(t: String) -> Label:
	var l := UiKit.ink_label(t, 24)
	l.add_theme_font_override("font", UiKit.font_heavy())
	l.add_theme_color_override("font_color", Color(0.35, 0.16, 0.08))
	return l


static func _slider(label: String, key: String, lo: float, hi: float, step: float) -> HBoxContainer:
	var row := HBoxContainer.new()
	var l := UiKit.ink_label(label, 18)
	l.custom_minimum_size = Vector2(220, 0)
	l.autowrap_mode = TextServer.AUTOWRAP_OFF
	row.add_child(l)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = float(Game.settings[key])
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.custom_minimum_size = Vector2(300, 28)
	s.value_changed.connect(func(v: float) -> void:
		Game.settings[key] = v
		Game.apply_settings())
	row.add_child(s)
	return row


static func _check(label: String, key: String) -> CheckBox:
	var c := CheckBox.new()
	c.text = label
	c.button_pressed = bool(Game.settings[key])
	c.add_theme_color_override("font_color", UiKit.INK)
	c.add_theme_color_override("font_pressed_color", UiKit.INK)
	c.add_theme_color_override("font_hover_color", Color(0.5, 0.25, 0.1))
	c.toggled.connect(func(v: bool) -> void:
		Game.settings[key] = v
		Game.apply_settings())
	return c
