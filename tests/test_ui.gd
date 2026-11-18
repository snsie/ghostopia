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
