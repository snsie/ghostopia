## Items, tool tiers, the 9-slot hotbar and Spectral Workbench crafting. Pure state.
class_name Inventory
extends RefCounted

signal changed

const HOTBAR_SIZE := 9
const TOOLS := ["scythe", "shovel", "sledgehammer"]

var items: Dictionary = {}          # item id -> count
var tools: Dictionary = {}          # tool -> tier (the ghost holds only spectral tools)
var hotbar: Array[String] = []      # item or tool ids, "" = empty
var selected: int = 0


func setup(start: Dictionary) -> void:
	items = (start.get("inventory", {}) as Dictionary).duplicate()
	tools = (start.get("tools", {}) as Dictionary).duplicate()
	hotbar.clear()
	for s in start.get("hotbar", []):
		hotbar.append(String(s))
	while hotbar.size() < HOTBAR_SIZE:
		hotbar.append("")
	for k: String in items:
		_auto_slot(k)


func count(item: String) -> int:
	return int(items.get(item, 0))


func add(item: String, n: int = 1) -> void:
	if n <= 0:
		return
	items[item] = count(item) + n
	_auto_slot(item)
	changed.emit()


func remove(item: String, n: int = 1) -> bool:
	if count(item) < n:
		return false
	items[item] = count(item) - n
	if int(items[item]) <= 0:
		items.erase(item)
	changed.emit()
	return true


func tool_tier(tool: String) -> int:
	return int(tools.get(tool, 0))


func selected_id() -> String:
	return hotbar[selected] if selected < hotbar.size() else ""


func is_tool(id: String) -> bool:
	return TOOLS.has(id)


## Placeable blocks get a hotbar slot automatically (the first free one).
func _auto_slot(item: String) -> void:
	if not _placeable.has(item) or hotbar.has(item):
		return
	for i in hotbar.size():
		if hotbar[i] == "":
			hotbar[i] = item
			return


var _placeable: Dictionary = {}     # item id -> block id (set by the game from tuning items)


func set_placeable(map: Dictionary) -> void:
	_placeable = map


func block_for(item: String) -> String:
	return String(_placeable.get(item, ""))


func can_craft(recipe: Dictionary) -> bool:
	if recipe.has("tool") and tool_tier(String(recipe["tool"])) >= int(recipe.get("tier", 1)):
		return false
	var needs: Dictionary = recipe.get("needs", {})
	for k: String in needs:
		if count(k) < int(needs[k]):
			return false
	return true


func missing_for(recipe: Dictionary) -> Dictionary:
	var out := {}
	var needs: Dictionary = recipe.get("needs", {})
	for k: String in needs:
		var m := int(needs[k]) - count(k)
		if m > 0:
			out[k] = m
	return out


func craft(recipe: Dictionary) -> bool:
	if not can_craft(recipe):
		return false
	var needs: Dictionary = recipe.get("needs", {})
	for k: String in needs:
		items[k] = count(k) - int(needs[k])
		if int(items[k]) <= 0:
			items.erase(k)
	if recipe.has("tool"):
		tools[String(recipe["tool"])] = int(recipe.get("tier", 1))
	elif recipe.has("item"):
		add(String(recipe["item"]), int(recipe.get("count", 1)))
	changed.emit()
	return true


func to_save() -> Dictionary:
	return {"items": items, "tools": tools, "hotbar": hotbar, "selected": selected}


func from_save(d: Dictionary) -> void:
	items = {}
	for k: String in d.get("items", {}):
		items[k] = int(d["items"][k])
	tools = {}
	for k: String in d.get("tools", {}):
		tools[k] = int(d["tools"][k])
	hotbar.clear()
	for s in d.get("hotbar", []):
		hotbar.append(String(s))
	while hotbar.size() < HOTBAR_SIZE:
		hotbar.append("")
	selected = int(d.get("selected", 0))
	changed.emit()
