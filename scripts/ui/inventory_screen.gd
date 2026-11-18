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
var _slots: HBoxContainer


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
	mid.add_child(UiKit.label("Choose a slot, then a tool or block.", 15, Color(0.8, 0.85, 1.0)))
	_slots = HBoxContainer.new()
	mid.add_child(_slots)
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
	for slot in Inventory.HOTBAR_SIZE:
		if e.is_action_pressed("slot_%d" % (slot + 1)):
			get_viewport().set_input_as_handled()
			_select_slot(slot)
			return
	if e.is_action_pressed("inventory") or e.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		closed.emit()


func _refresh() -> void:
	if not is_inside_tree():
		return
	for box in [_grid, _recipes, _tools, _slots]:
		for c in box.get_children():
			box.remove_child(c)
			c.queue_free()
	_tools.add_child(UiKit.heading("Ghost Traits", 22))
	_tools.add_child(UiKit.label("HP %d · Spectral" % int(Game.max_hp()), 16))
	_tools.add_child(UiKit.label("Unspent trait picks: %d" % Game.pending_traits(), 16))
	for id: String in ["haunting", "drift", "resilience"]:
		var benefit: String = {"haunting": "+5% Unease", "drift": "+5% speed", "resilience": "+2 max HP"}[id]
		var trait_button := UiKit.button("%s %d  ·  %s" % [id.capitalize(), Game.trait_rank(id), benefit],
			func() -> void:
				Game.choose_trait(id)
				_refresh())
		trait_button.disabled = Game.pending_traits() == 0
		_tools.add_child(trait_button)
	var inv := Game.inventory
	for tool: String in Inventory.TOOLS:
		var button := UiKit.button(UiKit.item_name(tool), _assign.bind(tool))
		button.icon = UiKit.icon_for(tool)
		button.expand_icon = true
		button.custom_minimum_size.y = 52
		button.disabled = inv.tool_tier(tool) <= 0
		_tools.add_child(button)
	for slot in Inventory.HOTBAR_SIZE:
		var button := UiKit.button(str(slot + 1), _select_slot.bind(slot))
		button.toggle_mode = true
		button.button_pressed = slot == inv.selected
		button.custom_minimum_size = Vector2(42, 38)
		var item := inv.hotbar[slot]
		button.tooltip_text = UiKit.item_name(item) if item != "" else "Empty slot"
		button.icon = UiKit.icon_for(item) if item != "" else null
		button.expand_icon = true
		_slots.add_child(button)
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
		b.disabled = inv.block_for(k) == ""
		b.pressed.connect(_assign.bind(k))
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


func _select_slot(slot: int) -> void:
	Game.inventory.selected = slot
	Game.inventory.changed.emit()


func _assign(item: String) -> void:
	if Game.inventory.assign_selected(item):
		Sfx.ui("ui_click")
