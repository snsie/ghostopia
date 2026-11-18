## Regression checks for UiKit panels: ensures corner brackets stay completely removed from all
## UI containers and cannot silently return.
extends "res://tests/framework/test_case.gd"

const UiKitS := preload("res://scripts/ui/ui_kit.gd")
const HudS := preload("res://scripts/ui/hud.gd")
const MenusS := preload("res://scripts/ui/menus.gd")


func test_panel_has_no_overlay_children() -> void:
	var p := UiKitS.panel()
	add_to_tree(p)
	assert_true(p is PanelContainer, "UiKit.panel() returns a PanelContainer")
	assert_eq(p.get_child_count(), 0, "UiKit.panel() must not attach corner bracket or overlay children")


func test_uikit_source_has_no_brackets_class() -> void:
	var src := FileAccess.get_file_as_string("res://scripts/ui/ui_kit.gd")
	assert_false(src.contains("class Brackets"), "Brackets class must stay removed from UiKit")
	assert_false(src.contains("Brackets.new"), "UiKit must not instantiate Brackets")


func test_panel_style_is_clean_rounded_slate() -> void:
	var p := UiKitS.panel()
	add_to_tree(p)
	var st := p.get_theme_stylebox("panel") as StyleBoxFlat
	assert_not_null(st, "panel uses a StyleBoxFlat")
	assert_eq(st.corner_radius_top_left, 12, "rounded top-left corner")
	assert_eq(st.corner_radius_top_right, 12, "rounded top-right corner")
	assert_eq(st.corner_radius_bottom_left, 12, "rounded bottom-left corner")
	assert_eq(st.corner_radius_bottom_right, 12, "rounded bottom-right corner")
	assert_eq(st.border_width_left, 2, "clean 2px border")


func test_hud_and_pause_panels_contain_only_layout_children() -> void:
	var pause := MenusS.pause({"Resume": func() -> void: pass})
	add_to_tree(pause)
	_assert_no_overlay_children(pause)

	var hud := HudS.new()
	hud._build_status()
	hud._build_clock()
	hud._build_hotbar()
	hud._build_paths()
	hud._build_center()
	hud.toast("Test notification", "level")
	hud.overheard("Pip", "Did you hear that?")
	add_to_tree(hud)
	_assert_no_overlay_children(hud)


func _assert_no_overlay_children(root: Node) -> void:
	if root is PanelContainer:
		for ch in root.get_children():
			var cls := ch.get_class()
			assert_ne(cls, "Control", "PanelContainer must not have raw Control overlay child")
			assert_null(ch.get_script(), "PanelContainer content child should not be a custom bracket script")
	for ch in root.get_children():
		_assert_no_overlay_children(ch)


func test_ghost_appearance_options_and_materials() -> void:
	assert_true(GhostAppearance.BODY_COLORS.size() >= 10, "healthy body color palette")
	assert_true(GhostAppearance.RIM_COLORS.size() >= 8, "healthy rim color palette")
	assert_true(GhostAppearance.GRADIENTS.size() >= 5, "gradient options")
	assert_true(GhostAppearance.PATTERNS.size() >= 8, "pattern options")
	assert_true(GhostAppearance.FINISHES.size() >= 7, "shader finish options")
	assert_true(GhostAppearance.EYE_STYLES.size() >= 7, "eye style options")
	assert_true(GhostAppearance.EXPRESSIONS.size() >= 5, "expression options")
	assert_true(GhostAppearance.FX_AURAS.size() >= 7, "aura fx options")

	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/ghost.gdshader")
	var ghost_scene := (load("res://assets/characters/ghost.gltf") as PackedScene).instantiate()
	add_to_tree(ghost_scene)
	var eyes := Actors.find_prefix(ghost_scene, "ghost_eyes") as MeshInstance3D
	var light := OmniLight3D.new()
	add_to_tree(light)

	var custom := {
		"body_color": "#8cf5d2", "rim_color": "#b86bff", "secondary_color": "#1d1436",
		"pattern_color": "#ffd866", "gradient_mode": 2, "pattern_mode": 4, "finish_mode": 3,
		"eye_style": 2, "eye_color": "#ffcc33", "eye_glow": 1.4, "expression": "happy",
		"fx": "sparkles", "fx_color": "#ffd866",
	}
	GhostAppearance.apply_to_materials(custom, mat, eyes, light, 0)
	assert_eq(int(mat.get_shader_parameter("gradient_mode")), 2, "gradient uniform applied")
	assert_eq(int(mat.get_shader_parameter("pattern_mode")), 4, "pattern uniform applied")
	assert_eq(int(mat.get_shader_parameter("finish_mode")), 3, "finish uniform applied")
	assert_true(eyes.material_override is ShaderMaterial, "eye style uses ghost_eyes shader")
	var happy_idx := eyes.find_blend_shape_by_name("happy")
	assert_almost_eq(eyes.get_blend_shape_value(happy_idx), 1.0, 0.01, "happy blend shape applied")

	var fx_node := GhostAppearance.build_fx_node(custom)
	assert_not_null(fx_node, "sparkles fx node created")
	add_to_tree(fx_node)


func test_characterizer_screen_tabs_presets_and_cancel() -> void:
	Game.set_appearance(GhostAppearance.defaults())
	var scr := CharacterizerScreen.new()
	scr.is_new_game = true
	add_to_tree(scr)
	_assert_no_overlay_children(scr)

	# Switch through all 4 customization tabs
	for tab_i in 4:
		scr._select_tab(tab_i)
		assert_eq(scr._tab, tab_i, "switched to tab %d" % tab_i)
		assert_true(scr._controls_box.get_child_count() > 0, "tab %d populates controls" % tab_i)

	# Apply preset and verify Game.appearance updates
	scr._apply_preset(1)
	assert_eq(String(Game.appearance["fx"]), "sparkles", "preset 1 applies sparkles aura")
	assert_eq(int(Game.appearance["eye_style"]), 2, "preset 1 applies starry eyes")

	# Randomize produces valid sanitized dictionary
	scr._on_randomize()
	assert_true(Game.appearance.has("body_color") and Game.appearance.has("eye_style"), "randomized appearance valid")

	# Cancel restores backup from when screen opened
	var cancelled := [false]
	scr.cancelled.connect(func() -> void: cancelled[0] = true)
	scr._on_cancel()
	assert_true(cancelled[0], "cancelled signal emitted")
	assert_eq(String(Game.appearance["fx"]), "none", "cancel restores initial appearance")


func test_magic_mirror_placed_at_base() -> void:
	var lvl := Level.new()
	add_to_tree(lvl)
	lvl._place_magic_mirror()
	assert_not_null(lvl.magic_mirror, "Magic Mirror prop created at base")
	assert_true(lvl.mirror_pos().distance_to(Vector3(30.5, 28.0, 95.7)) < 1.0, "Magic Mirror sits in mausoleum yard")

