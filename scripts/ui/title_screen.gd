## Title screen: the painted concept/ui/title_screen.png with invisible buttons over its menu
## (Continue, New Game, Settings, Quit).
class_name TitleScreen
extends Control

signal continue_pressed
signal new_game_pressed
signal settings_pressed
signal quit_pressed

const IMG_SIZE := Vector2(1672, 941)
# Menu buttons in image pixels (concept/ui/title_screen.png).
const BUTTONS := {
	"continue": Rect2(80, 396, 316, 76),
	"new_game": Rect2(82, 492, 310, 72),
	"settings": Rect2(82, 586, 310, 72),
	"quit": Rect2(82, 678, 310, 72),
}

var image: TextureRect
var _buttons: Dictionary = {}
var _glow: Dictionary = {}


func _ready() -> void:
	theme = UiKit.theme()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.05, 0.04, 0.12)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	image = TextureRect.new()
	image.texture = load("res://assets/ui/title_screen.png")
	image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	image.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(image)
	for key: String in BUTTONS:
		var b := Button.new()
		b.flat = true
		b.focus_mode = Control.FOCUS_ALL
		var empty := StyleBoxEmpty.new()
		for s in ["normal", "hover", "pressed", "focus", "disabled"]:
			b.add_theme_stylebox_override(s, empty)
		add_child(b)
		var glow := Panel.new()
		var st := StyleBoxFlat.new()
		st.bg_color = Color(0.4, 0.9, 1.0, 0.12)
		st.border_color = Color(0.5, 0.95, 1.0, 0.9)
		st.set_border_width_all(3)
		st.set_corner_radius_all(10)
		glow.add_theme_stylebox_override("panel", st)
		glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
		glow.visible = false
		add_child(glow)
		_glow[key] = glow
		b.mouse_entered.connect(func() -> void:
			glow.visible = true
			Sfx.ui("ui_hover"))
		b.mouse_exited.connect(func() -> void: glow.visible = false)
		b.focus_entered.connect(func() -> void: glow.visible = true)
		b.focus_exited.connect(func() -> void: glow.visible = false)
		b.pressed.connect(_on_pressed.bind(key))
		_buttons[key] = b
	var ver := UiKit.label("Vertical slice · run 1 · %s" % ProjectSettings.get_setting("application/config/version", "0.1"), 14, Color(1, 1, 1, 0.6))
	ver.name = "Version"
	add_child(ver)
	resized.connect(_layout)
	_layout()
	(_buttons["continue"] as Button).disabled = not Game.has_save()
	if not Game.has_save():
		(_buttons["continue"] as Button).modulate.a = 0.5
	Sfx.music("menu_music_box")
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


## Maps image pixels to screen with the same "keep aspect covered" fit as the TextureRect.
func image_to_screen(r: Rect2) -> Rect2:
	var s := size
	var k := maxf(s.x / IMG_SIZE.x, s.y / IMG_SIZE.y)
	var off := (s - IMG_SIZE * k) * 0.5
	return Rect2(off + r.position * k, r.size * k)


func _layout() -> void:
	var ver := get_node_or_null("Version") as Label
	if ver:
		ver.position = size - Vector2(330, 34)
	for key: String in BUTTONS:
		var r := image_to_screen(BUTTONS[key])
		(_buttons[key] as Button).position = r.position
		(_buttons[key] as Button).size = r.size
		(_glow[key] as Panel).position = r.position - Vector2(4, 4)
		(_glow[key] as Panel).size = r.size + Vector2(8, 8)


func _on_pressed(key: String) -> void:
	Sfx.ui("ui_click")
	match key:
		"continue":
			continue_pressed.emit()
		"new_game":
			new_game_pressed.emit()
		"settings":
			settings_pressed.emit()
		"quit":
			quit_pressed.emit()
