## One UI kit for every screen (matches concept/ui): translucent dark slate panels with thin cyan
## frames and glowing corner brackets, white and gold rounded headings (Fredoka), green and cyan
## bars, square item slots, parchment pages for the journal and the Scattered screen.
class_name UiKit
extends RefCounted

const SLATE := Color(0.06, 0.08, 0.15, 0.84)
const SLATE_LIGHT := Color(0.12, 0.15, 0.26, 0.9)
const CYAN := Color(0.36, 0.88, 1.0)
const GOLD := Color(1.0, 0.8, 0.28)
const WHITE := Color(0.96, 0.97, 1.0)
const GREEN := Color(0.45, 0.92, 0.38)
const ECTO := Color(0.35, 0.85, 1.0)
const VIOLET := Color(0.66, 0.42, 1.0)
const PARCHMENT := Color(0.93, 0.86, 0.7)
const INK := Color(0.2, 0.14, 0.1)
const RED := Color(1.0, 0.36, 0.3)

static var _font: FontFile
static var _heavy: FontVariation
static var _body: FontVariation
static var _theme: Theme


static func font_heavy() -> Font:
	_load_fonts()
	return _heavy


static func font_body() -> Font:
	_load_fonts()
	return _body


static func _load_fonts() -> void:
	if _heavy != null:
		return
	_font = load("res://assets/ui/fonts/Fredoka.ttf")
	_heavy = FontVariation.new()
	_heavy.base_font = _font
	_heavy.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): 650}
	_body = FontVariation.new()
	_body.base_font = _font
	_body.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): 450}


static func theme() -> Theme:
	if _theme:
		return _theme
	_load_fonts()
	var t := Theme.new()
	t.default_font = _body
	t.default_font_size = 20
	t.set_color("font_color", "Label", WHITE)
	t.set_color("font_outline_color", "Label", Color(0.03, 0.02, 0.08, 0.9))
	t.set_constant("outline_size", "Label", 4)
	var b := _box(SLATE_LIGHT, CYAN * Color(1, 1, 1, 0.55), 2, 10)
	var bh := _box(Color(0.16, 0.24, 0.36, 0.95), CYAN, 2, 10)
	var bp := _box(Color(0.1, 0.32, 0.42, 0.95), CYAN, 3, 10)
	var bd := _box(Color(0.1, 0.1, 0.14, 0.7), Color(0.4, 0.4, 0.5, 0.4), 2, 10)
	for s in [["normal", b], ["hover", bh], ["pressed", bp], ["focus", bh], ["disabled", bd]]:
		t.set_stylebox(s[0], "Button", s[1])
	t.set_font("font", "Button", _heavy)
	t.set_font_size("font_size", "Button", 22)
	t.set_color("font_color", "Button", WHITE)
	t.set_color("font_hover_color", "Button", GOLD)
	t.set_color("font_disabled_color", "Button", Color(0.6, 0.6, 0.7))
	var grab := _box(CYAN, CYAN, 0, 8)
	t.set_stylebox("slider", "HSlider", _box(Color(0.1, 0.12, 0.2), CYAN * Color(1, 1, 1, 0.5), 1, 4))
	t.set_stylebox("grabber_area", "HSlider", _box(CYAN * Color(1, 1, 1, 0.6), CYAN, 0, 4))
	t.set_stylebox("grabber_area_highlight", "HSlider", grab)
	t.set_stylebox("panel", "PanelContainer", panel_style())
	t.set_stylebox("panel", "TooltipPanel", panel_style())
	t.set_color("font_color", "CheckBox", WHITE)
	t.set_font("font", "CheckBox", _body)
	_theme = t
	return t


static func _box(bg: Color, border: Color, bw: int, radius: int) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(bw)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 14
	s.content_margin_right = 14
	s.content_margin_top = 8
	s.content_margin_bottom = 8
	s.anti_aliasing = true
	return s


static func panel_style() -> StyleBoxFlat:
	var s := _box(SLATE, CYAN * Color(1, 1, 1, 0.45), 2, 12)
	s.shadow_color = Color(0.2, 0.7, 1.0, 0.18)
	s.shadow_size = 8
	s.content_margin_left = 18
	s.content_margin_right = 18
	s.content_margin_top = 14
	s.content_margin_bottom = 14
	return s


static func parchment_style() -> StyleBoxFlat:
	var s := _box(PARCHMENT, Color(0.55, 0.38, 0.2), 3, 10)
	s.shadow_color = Color(0, 0, 0, 0.4)
	s.shadow_size = 10
	s.content_margin_left = 26
	s.content_margin_right = 26
	s.content_margin_top = 20
	s.content_margin_bottom = 20
	return s


## A slate panel with cyan corner brackets.
static func panel() -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", panel_style())
	var br := Brackets.new()
	br.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	br.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(br)
	return p


static func parchment() -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", parchment_style())
	return p


static func heading(text: String, size: int = 30, color: Color = WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font_heavy())
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_constant_override("outline_size", 8)
	l.add_theme_color_override("font_outline_color", Color(0.04, 0.03, 0.1, 0.95))
	return l


static func label(text: String, size: int = 20, color: Color = WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


static func ink_label(text: String, size: int = 20) -> Label:
	var l := label(text, size, INK)
	l.add_theme_constant_override("outline_size", 0)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


static func button(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(220, 48)
	b.pressed.connect(func() -> void:
		Sfx.ui("ui_click")
		cb.call())
	b.mouse_entered.connect(func() -> void: Sfx.ui("ui_hover"))
	return b


static func bar(color: Color, width: float = 220.0, height: float = 16.0) -> ProgressBar:
	var pb := ProgressBar.new()
	pb.custom_minimum_size = Vector2(width, height)
	pb.show_percentage = false
	var bg := _box(Color(0.03, 0.04, 0.09, 0.85), CYAN * Color(1, 1, 1, 0.35), 1, int(height / 2))
	bg.content_margin_top = 0
	bg.content_margin_bottom = 0
	var fg := _box(color, color.lightened(0.3), 0, int(height / 2))
	fg.content_margin_top = 0
	fg.content_margin_bottom = 0
	pb.add_theme_stylebox_override("background", bg)
	pb.add_theme_stylebox_override("fill", fg)
	return pb


static func icon_for(item: String) -> Texture2D:
	if Inventory.TOOLS.has(item):
		var tier := maxi(1, Game.inventory.tool_tier(item))
		item = "%s_t%d" % [item, tier]
	var p := "res://assets/ui/icons/%s.png" % item
	return load(p) if ResourceLoader.exists(p) else null


static func item_name(item: String) -> String:
	var it: Variant = Game.tuning.d("items").get(item, {})
	var nm := String(it.get("name", item.capitalize())) if it is Dictionary else item.capitalize()
	if Inventory.TOOLS.has(item):
		nm += " " + ["", "I", "II", "III", "IV"][clampi(Game.inventory.tool_tier(item), 0, 4)]
	return nm


## Wraps `c` in a full-screen CenterContainer (screens are centred panels).
static func centered(c: Control) -> CenterContainer:
	var cc := CenterContainer.new()
	cc.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cc.add_child(c)
	return cc


## Full-screen dim layer.
static func dim(alpha: float = 0.55) -> ColorRect:
	var c := ColorRect.new()
	c.color = Color(0.02, 0.01, 0.06, alpha)
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return c


class Brackets:
	extends Control
	func _draw() -> void:
		var s := size
		var l := minf(22.0, minf(s.x, s.y) * 0.3)
		var c := UiKit.CYAN
		var w := 3.0
		for corner: Vector2 in [Vector2(0, 0), Vector2(s.x, 0), Vector2(0, s.y), Vector2(s.x, s.y)]:
			var dx := 1.0 if corner.x == 0 else -1.0
			var dy := 1.0 if corner.y == 0 else -1.0
			var p := corner + Vector2(dx * -2, dy * -2)
			draw_line(p, p + Vector2(dx * l, 0), Color(c, 0.25), w + 4)
			draw_line(p, p + Vector2(0, dy * l), Color(c, 0.25), w + 4)
			draw_line(p, p + Vector2(dx * l, 0), c, w)
			draw_line(p, p + Vector2(0, dy * l), c, w)
	func _notification(what: int) -> void:
		if what == NOTIFICATION_RESIZED:
			queue_redraw()
