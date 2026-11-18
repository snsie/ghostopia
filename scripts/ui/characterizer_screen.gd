## Ghost appearance customizer used both as the New Game character creation step and at the
## Magic Mirror in the mausoleum yard. Includes a live rotatable 3D ghost preview, presets,
## randomize, and tabs for Colors & Gradients, Patterns & Shaders, Eyes & Expressions, and Aura FX.
class_name CharacterizerScreen
extends Control

signal confirmed
signal cancelled

var is_new_game := false
var _backup: Dictionary = {}
var _tab := 0
var _tab_buttons: Array[Button] = []
var _controls_box: VBoxContainer
var _preview_model: Node3D
var _preview_eyes: MeshInstance3D
var _preview_sheet_mat: ShaderMaterial
var _preview_light: OmniLight3D
var _preview_fx: Node3D
var _preview_yaw := 0.0
var _dragging := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	theme = UiKit.theme()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_backup = Game.appearance.duplicate(true)
	if is_new_game:
		var bg := TextureRect.new()
		bg.texture = load("res://assets/ui/title_screen.png")
		bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		bg.modulate = Color(0.35, 0.32, 0.52)
		add_child(bg)
	add_child(UiKit.dim(0.62 if is_new_game else 0.55))

	var panel := UiKit.panel()
	panel.custom_minimum_size = Vector2(1160, 680)
	add_child(UiKit.centered(panel))

	var root_vb := VBoxContainer.new()
	root_vb.add_theme_constant_override("separation", 12)
	panel.add_child(root_vb)

	# Header
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 12)
	var title_txt := "Shape Your Spirit" if is_new_game else "Magic Mirror"
	header.add_child(UiKit.heading(title_txt, 34, UiKit.GOLD))
	var sub_txt := "Customize your ghost before drifting into the Veil (you can change this anytime at your base mirror)." \
		if is_new_game else "Peer into the spectral glass to reshape your sheet, eyes, and aura."
	var sub_lbl := UiKit.label(sub_txt, 16, Color(0.82, 0.88, 1.0))
	sub_lbl.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	header.add_child(sub_lbl)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)
	var rand_btn := UiKit.button("Randomize", _on_randomize)
	rand_btn.name = "RandomizeButton"
	rand_btn.custom_minimum_size = Vector2(150, 42)
	header.add_child(rand_btn)
	var reset_btn := UiKit.button("Reset", _on_reset)
	reset_btn.name = "ResetButton"
	reset_btn.custom_minimum_size = Vector2(110, 42)
	header.add_child(reset_btn)
	root_vb.add_child(header)

	# Main split: Left 3D mirror preview + presets, Right tabbed customization controls
	var body_hb := HBoxContainer.new()
	body_hb.add_theme_constant_override("separation", 18)
	body_hb.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root_vb.add_child(body_hb)

	body_hb.add_child(_build_preview_column())
	body_hb.add_child(_build_controls_column())

	# Footer
	var footer := HBoxContainer.new()
	footer.add_theme_constant_override("separation", 14)
	var back_btn := UiKit.button("Back" if is_new_game else "Cancel", _on_cancel)
	back_btn.name = "CancelButton"
	back_btn.custom_minimum_size = Vector2(160, 46)
	footer.add_child(back_btn)
	var f_space := Control.new()
	f_space.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	footer.add_child(f_space)
	var start_lbl := "Drift into the Veil" if is_new_game else "Apply Look"
	var confirm_btn := UiKit.button(start_lbl, _on_confirm)
	confirm_btn.name = "ConfirmButton"
	confirm_btn.custom_minimum_size = Vector2(240, 48)
	footer.add_child(confirm_btn)
	root_vb.add_child(footer)

	_select_tab(0)
	_refresh_preview()


func _build_preview_column() -> VBoxContainer:
	var col := VBoxContainer.new()
	col.custom_minimum_size = Vector2(390, 0)
	col.add_theme_constant_override("separation", 10)

	var frame := PanelContainer.new()
	var st := UiKit._box(Color(0.04, 0.03, 0.1, 0.95), UiKit.VIOLET.lightened(0.25), 3, 16)
	st.content_margin_left = 6
	st.content_margin_right = 6
	st.content_margin_top = 6
	st.content_margin_bottom = 6
	frame.add_theme_stylebox_override("panel", st)
	frame.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(frame)

	var svc := SubViewportContainer.new()
	svc.stretch = true
	svc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	svc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	svc.custom_minimum_size = Vector2(370, 340)
	svc.gui_input.connect(_on_preview_input)
	frame.add_child(svc)

	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.transparent_bg = false
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	vp.size = Vector2i(370, 340)
	svc.add_child(vp)

	var stage := Node3D.new()
	vp.add_child(stage)

	var env_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.05, 0.04, 0.13)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.38, 0.35, 0.62)
	env.ambient_light_energy = 1.0
	env.glow_enabled = true
	env.glow_intensity = 0.7
	env.glow_bloom = 0.15
	env_node.environment = env
	stage.add_child(env_node)

	var cam := Camera3D.new()
	cam.fov = 38.0
	cam.position = Vector3(0, 0.36, 1.38)
	cam.look_at_from_position(cam.position, Vector3(0, 0.31, 0), Vector3.UP)
	stage.add_child(cam)

	var key_light := DirectionalLight3D.new()
	key_light.light_color = Color(0.92, 0.95, 1.0)
	key_light.light_energy = 1.25
	key_light.rotation_degrees = Vector3(-28, 32, 0)
	stage.add_child(key_light)

	_preview_light = OmniLight3D.new()
	_preview_light.position = Vector3(0, 0.38, 0.45)
	_preview_light.light_energy = 0.85
	_preview_light.omni_range = 3.0
	stage.add_child(_preview_light)

	# Pedestal ring under the ghost
	var ped := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.32
	cyl.bottom_radius = 0.36
	cyl.height = 0.04
	ped.mesh = cyl
	ped.position = Vector3(0, -0.04, 0)
	var pm := StandardMaterial3D.new()
	pm.albedo_color = Color(0.22, 0.18, 0.38)
	pm.emission_enabled = true
	pm.emission = Color(0.36, 0.75, 1.0)
	pm.emission_energy_multiplier = 0.35
	ped.material_override = pm
	stage.add_child(ped)

	var ps := load("res://assets/characters/ghost.gltf") as PackedScene
	if ps:
		_preview_model = ps.instantiate()
		stage.add_child(_preview_model)
		var ap := Actors.find_prefix(_preview_model, "AnimationPlayer") as AnimationPlayer
		if ap:
			Actors.setup_loops(ap, Game.characters.get("ghost", {}))
			if ap.has_animation("idle_float"):
				ap.play("idle_float")
		var manifest_node := Actors.find_prefix(_preview_model, "MATERIAL_manifest") as Node3D
		if manifest_node:
			manifest_node.visible = false
		_preview_eyes = Actors.find_prefix(_preview_model, "ghost_eyes") as MeshInstance3D
		var body := Actors.find_prefix(_preview_model, "ghost_body") as MeshInstance3D
		_preview_sheet_mat = ShaderMaterial.new()
		_preview_sheet_mat.shader = load("res://shaders/ghost.gdshader")
		if body and body.mesh:
			for s in body.mesh.get_surface_count():
				body.set_surface_override_material(s, _preview_sheet_mat)

	var drag_hint := UiKit.label("Drag to spin · Presets below", 14, Color(0.75, 0.82, 0.96))
	drag_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(drag_hint)

	var preset_grid := GridContainer.new()
	preset_grid.columns = 2
	preset_grid.add_theme_constant_override("h_separation", 8)
	preset_grid.add_theme_constant_override("v_separation", 6)
	for i in GhostAppearance.PRESETS.size():
		var pr: Dictionary = GhostAppearance.PRESETS[i]
		var b := UiKit.button(String(pr["name"]), _apply_preset.bind(i))
		b.name = "Preset_%d" % i
		b.custom_minimum_size = Vector2(188, 36)
		b.add_theme_font_size_override("font_size", 16)
		preset_grid.add_child(b)
	col.add_child(preset_grid)
	return col


func _build_controls_column() -> VBoxContainer:
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_theme_constant_override("separation", 10)

	var tabs := HBoxContainer.new()
	tabs.add_theme_constant_override("separation", 8)
	var tab_names := ["Colors & Gradients", "Patterns & Shaders", "Eyes & Expressions", "Aura & FX"]
	_tab_buttons.clear()
	for i in tab_names.size():
		var b := UiKit.button(tab_names[i], _select_tab.bind(i))
		b.name = "Tab_%d" % i
		b.toggle_mode = true
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.custom_minimum_size = Vector2(150, 42)
		b.add_theme_font_size_override("font_size", 18)
		tabs.add_child(b)
		_tab_buttons.append(b)
	col.add_child(tabs)

	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(scroll)

	_controls_box = VBoxContainer.new()
	_controls_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_controls_box.add_theme_constant_override("separation", 10)
	scroll.add_child(_controls_box)
	return col


func _select_tab(idx: int) -> void:
	_tab = idx
	for i in _tab_buttons.size():
		_tab_buttons[i].button_pressed = (i == idx)
	for c in _controls_box.get_children():
		_controls_box.remove_child(c)
		c.queue_free()
	match idx:
		0:
			_build_tab_colors()
		1:
			_build_tab_patterns_shaders()
		2:
			_build_tab_eyes()
		3:
			_build_tab_fx()


func _build_tab_colors() -> void:
	_add_palette_picker("Sheet Color", "body_color", GhostAppearance.BODY_COLORS)
	_add_palette_picker("Rim Glow Color", "rim_color", GhostAppearance.RIM_COLORS)
	_add_option_chips("Gradient Style", "gradient_mode", GhostAppearance.GRADIENTS)
	_add_palette_picker("Gradient Secondary Color", "secondary_color", GhostAppearance.SECONDARY_COLORS)
	_add_slider_row("Gradient Blend", "gradient_strength", 0.0, 1.0, 0.05)
	_add_slider_row("Sheet Opacity", "alpha", 0.45, 0.96, 0.02)


func _build_tab_patterns_shaders() -> void:
	_add_option_chips("Sheet Pattern", "pattern_mode", GhostAppearance.PATTERNS)
	_add_palette_picker("Pattern Color", "pattern_color", GhostAppearance.PATTERN_COLORS)
	_add_slider_row("Pattern Scale", "pattern_scale", 0.5, 2.2, 0.1)
	_add_slider_row("Pattern Contrast", "pattern_strength", 0.0, 1.0, 0.05)
	_add_option_chips("Shader Finish", "finish_mode", GhostAppearance.FINISHES)
	_add_slider_row("Inner Radiance", "glow_boost", 0.0, 1.2, 0.05)
	_add_slider_row("Pulse Speed", "pulse_speed", 0.0, 2.6, 0.2)


func _build_tab_eyes() -> void:
	_add_option_chips("Eye Style", "eye_style", GhostAppearance.EYE_STYLES)
	_add_palette_picker("Eye Color", "eye_color", GhostAppearance.EYE_COLORS)
	_add_slider_row("Eye Glow", "eye_glow", 0.0, 2.4, 0.2)
	_add_option_chips("Resting Expression", "expression", GhostAppearance.EXPRESSIONS)


func _build_tab_fx() -> void:
	_add_option_chips("Spectral Aura FX", "fx", GhostAppearance.FX_AURAS)
	_add_palette_picker("Aura Tint", "fx_color", GhostAppearance.RIM_COLORS)


func _add_palette_picker(title: String, key: String, palette: Array) -> void:
	_controls_box.add_child(UiKit.heading(title, 20, UiKit.GOLD))
	var grid := GridContainer.new()
	grid.columns = 6
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	var cur := String(Game.appearance.get(key, "")).to_lower()
	for entry in palette:
		var hex := String(entry["color"]).to_lower()
		var col := Color(hex)
		var b := Button.new()
		b.custom_minimum_size = Vector2(106, 36)
		b.text = String(entry["name"]).split(" ")[-1]
		b.tooltip_text = String(entry["name"])
		b.add_theme_font_size_override("font_size", 14)
		var lum := col.r * 0.299 + col.g * 0.587 + col.b * 0.114
		var fg := Color(0.06, 0.04, 0.12) if lum > 0.58 else Color(0.98, 0.98, 1.0)
		b.add_theme_color_override("font_color", fg)
		b.add_theme_color_override("font_hover_color", fg)
		b.add_theme_color_override("font_pressed_color", fg)
		b.add_theme_color_override("font_focus_color", fg)
		var sel := (cur == hex)
		var border := UiKit.GOLD if sel else Color(1, 1, 1, 0.35)
		var bw := 3 if sel else 1
		var st := UiKit._box(col, border, bw, 8)
		var st_h := UiKit._box(col.lightened(0.12), UiKit.WHITE, 2, 8)
		for sname in ["normal", "pressed", "focus"]:
			b.add_theme_stylebox_override(sname, st)
		b.add_theme_stylebox_override("hover", st_h)
		b.pressed.connect(func() -> void:
			Sfx.ui("ui_click")
			Game.set_appearance_key(key, hex)
			_select_tab(_tab)
			_refresh_preview())
		grid.add_child(b)
	_controls_box.add_child(grid)


func _add_option_chips(title: String, key: String, options: Array) -> void:
	_controls_box.add_child(UiKit.heading(title, 20, UiKit.GOLD))
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	var cur: Variant = Game.appearance.get(key)
	for opt in options:
		var val: Variant = opt["id"]
		var b := UiKit.button(String(opt["name"]), func() -> void:
			Game.set_appearance_key(key, val)
			_select_tab(_tab)
			_refresh_preview())
		b.name = "%s_%s" % [key, str(val)]
		b.toggle_mode = true
		b.button_pressed = (str(cur) == str(val))
		b.custom_minimum_size = Vector2(210, 38)
		b.add_theme_font_size_override("font_size", 16)
		grid.add_child(b)
	_controls_box.add_child(grid)


func _add_slider_row(title: String, key: String, lo: float, hi: float, step: float) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var lbl := UiKit.label(title, 18, UiKit.WHITE)
	lbl.custom_minimum_size = Vector2(210, 0)
	row.add_child(lbl)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = float(Game.appearance.get(key, lo))
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.custom_minimum_size = Vector2(240, 28)
	var val_lbl := UiKit.label("%.2f" % s.value, 16, UiKit.GOLD)
	val_lbl.custom_minimum_size = Vector2(64, 0)
	val_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	s.value_changed.connect(func(v: float) -> void:
		val_lbl.text = "%.2f" % v
		Game.set_appearance_key(key, v)
		_refresh_preview())
	row.add_child(s)
	row.add_child(val_lbl)
	_controls_box.add_child(row)


func _refresh_preview() -> void:
	GhostAppearance.apply_to_materials(Game.appearance, _preview_sheet_mat, _preview_eyes, _preview_light, Game.trait_rank("haunting"))
	if _preview_fx and is_instance_valid(_preview_fx):
		_preview_fx.queue_free()
		_preview_fx = null
	if _preview_model:
		_preview_fx = GhostAppearance.build_fx_node(Game.appearance)
		if _preview_fx:
			_preview_model.add_child(_preview_fx)


func _on_preview_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
		_dragging = e.pressed
	elif e is InputEventMouseMotion and _dragging and _preview_model:
		_preview_yaw += e.relative.x * 0.012
		_preview_model.rotation.y = _preview_yaw


func _process(dt: float) -> void:
	if _preview_model and not _dragging:
		_preview_yaw = fmod(_preview_yaw + dt * 0.45, TAU)
		_preview_model.rotation.y = _preview_yaw


func _apply_preset(idx: int) -> void:
	var pr: Dictionary = GhostAppearance.PRESETS[clampi(idx, 0, GhostAppearance.PRESETS.size() - 1)]
	Game.set_appearance((pr["data"] as Dictionary).duplicate(true))
	_select_tab(_tab)
	_refresh_preview()


func _on_randomize() -> void:
	Game.set_appearance(GhostAppearance.randomize_appearance(Game.rng))
	_select_tab(_tab)
	_refresh_preview()


func _on_reset() -> void:
	Game.set_appearance(GhostAppearance.defaults())
	_select_tab(_tab)
	_refresh_preview()


func _on_confirm() -> void:
	confirmed.emit()


func _on_cancel() -> void:
	Game.set_appearance(_backup)
	cancelled.emit()


func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		_on_cancel()
