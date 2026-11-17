## Inventory and crafting (concept/ui/inventory.png): the ghost's spectral tools and tiers on the
## left (cosmetic slots are run 2), the item grid in the middle (click to put a block in the
## selected hotbar slot), and the Spectral Workbench recipes on the right (only at the workbench).
class_name InventoryScreen
extends Control

signal closed

var at_workbench := false
var _grid: GridContainer
var _recipes: VBoxContainer
var _tools: VBoxContainer


func _ready() -> void:
	theme = UiKit.theme()
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(UiKit.dim(0.55))
	var p := UiKit.panel()
	p.custom_minimum_size = Vector2(1180, 640)
	add_child(UiKit.centered(p))
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 12)
	p.add_child(vb)
	var top := HBoxContainer.new()
	top.add_child(UiKit.heading("Inventory", 32, UiKit.GOLD))
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(sp)
	top.add_child(UiKit.button("Close", func() -> void: closed.emit()))
	vb.add_child(top)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 18)
	hb.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vb.add_child(hb)
	_tools = VBoxContainer.new()
	_tools.custom_minimum_size = Vector2(260, 0)
	hb.add_child(_tools)
	var mid := VBoxContainer.new()
	mid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hb.add_child(mid)
	mid.add_child(UiKit.heading("Items", 22))
	mid.add_child(UiKit.label("Click a block to put it in the selected hotbar slot.", 15, Color(0.8, 0.85, 1.0)))
	_grid = GridContainer.new()
	_grid.columns = 6
	_grid.add_theme_constant_override("h_separation", 8)
	_grid.add_theme_constant_override("v_separation", 8)
	mid.add_child(_grid)
	var right := VBoxContainer.new()
	right.custom_minimum_size = Vector2(360, 0)
	hb.add_child(right)
	right.add_child(UiKit.heading("Spectral Workbench", 22, UiKit.GOLD))
	_recipes = VBoxContainer.new()
	_recipes.add_theme_constant_override("separation", 8)
	right.add_child(_recipes)
	Game.inventory.changed.connect(_refresh)
	_refresh()


func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("inventory") or e.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		closed.emit()


func _refresh() -> void:
	if not is_inside_tree():
		return
	for box in [_grid, _recipes, _tools]:
		for c in box.get_children():
			c.queue_free()
	_tools.add_child(UiKit.heading("Basic Ghost", 22))
	_tools.add_child(UiKit.label("HP %d · Spectral" % int(Game.max_hp()), 16))
	for t in Inventory.TOOLS:
		var row := HBoxContainer.new()
		var ic := TextureRect.new()
		ic.texture = UiKit.icon_for(t)
		ic.custom_minimum_size = Vector2(56, 56)
		ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		row.add_child(ic)
		row.add_child(UiKit.label(UiKit.item_name(t), 18))
		_tools.add_child(row)
	_tools.add_child(UiKit.label("Cosmetics: masks, hats, gloves (run 2)", 14, Color(0.7, 0.7, 0.8)))
	var inv := Game.inventory
	var keys := inv.items.keys()
	keys.sort()
	for k: String in keys:
		var b := Button.new()
		b.custom_minimum_size = Vector2(92, 92)
		b.icon = UiKit.icon_for(k)
		b.expand_icon = true
		b.tooltip_text = "%s ×%d" % [UiKit.item_name(k), inv.count(k)]
		b.text = str(inv.count(k))
		b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
		b.add_theme_font_size_override("font_size", 16)
		b.pressed.connect(func() -> void:
			if inv.block_for(k) != "":
				var old := inv.hotbar.find(k)
				if old >= 0:
					inv.hotbar[old] = ""
				inv.hotbar[inv.selected] = k
				Sfx.ui("ui_click")
				inv.changed.emit())
		_grid.add_child(b)
	if keys.is_empty():
		_grid.add_child(UiKit.label("Empty. Gather with your tools.", 16))
	if not at_workbench:
		_recipes.add_child(UiKit.label("Go to the workbench beside the mausoleum to craft.", 16, Color(0.8, 0.8, 0.9)))
	for r in Game.tuning.a("recipes"):
		var box := UiKit.panel()
		var v := VBoxContainer.new()
		box.add_child(v)
		var have_txt: Array[String] = []
		for k: String in r["needs"]:
			have_txt.append("%s %d/%d" % [UiKit.item_name(k), inv.count(k), int(r["needs"][k])])
		v.add_child(UiKit.heading(String(r["name"]), 18))
		v.add_child(UiKit.label(", ".join(have_txt), 14, Color(0.85, 0.9, 1.0)))
		var ok := at_workbench and inv.can_craft(r)
		var done: bool = r.has("tool") and inv.tool_tier(String(r["tool"])) >= int(r.get("tier", 1))
		var btn := UiKit.button("Owned" if done else "Craft", func() -> void:
			if inv.craft(r):
				Sfx.play("craft")
				Game.toast.emit("Crafted %s" % r["name"], "level"))
		btn.disabled = not ok
		btn.custom_minimum_size = Vector2(120, 36)
		v.add_child(btn)
		_recipes.add_child(box)
