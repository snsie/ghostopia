## The heart of the slice: turns the ghost's acts into villager Unease (who hears a creak, who sees
## a light go out), lands or botches the BOO and grades it, pays Fright / Remembrance / Heat,
## runs town memory (charms, salt lines, legend, tavern rumors, Pip the witness), overheard
## muttering, and Remembrance decay.
class_name ScareDirector
extends Node

signal graded(result: Dictionary)
signal fear_discovered(villager_id: String)
signal legend_grew(name: String)

var gw: Node
var _now := 0.0
var _overhear_cd: Dictionary = {}   # villager -> time
var _mutter_i: Dictionary = {}
var _rumor_cd := 0.0
var _rem_cd := 0.0
var last_result: Dictionary = {}
var last_act: Dictionary = {}


func setup(p_gw: Node) -> void:
	gw = p_gw


func _sc() -> Dictionary:
	return Game.tuning.d("scare")


# ---------------------------------------------------------------- acts

## The ghost haunts `h` with `action`. Returns a status string ("ok" or why not).
func haunt(h: Hauntable, action: String) -> String:
	var t := Game.tuning
	var ability := h.ability()
	if action == "":
		return "no action"
	if not Game.ability_unlocked(ability):
		var lvl := int(h.data.get("level", 1))
		gw.hud.hint("%s needs Haunting level %d" % [ability.capitalize(), lvl])
		return "locked"
	if Game.town.is_unhauntable(h.id):
		gw.hud.hint("A charm hangs here. It won't answer you for a while.")
		return "charmed"
	if h.on_cooldown(_now):
		return "cooldown"
	if not h.can_act(action):
		gw.hud.hint("It's already out")
		return "unlit"
	var cost := t.f("haunting.ecto_cost.%s" % action, 5.0)
	if Game.ecto < cost:
		gw.hud.hint("Not enough Ectoplasm")
		return "ecto"
	Game.ecto -= cost
	h.act(action, _now)
	gw.player._play_clip("haunt_cast", 0.6)
	gw.player.set_expression("happy", 1.0)
	# A trick counts for town memory only once it was part of a finished scare (see _remember_tricks);
	# using it again in a later scare doubles suspicion.
	var same_twice := Game.town.used_before(h.id, ability)
	var base_u := float(h.data.get("unease", {}).get(action, 8.0))
	if action == "rock_wildly":
		base_u = 26.0
	elif action == "tilt_portrait":
		base_u = 23.0
	var hearers := _affected(h, action)
	last_act = {"object": h.id, "action": action, "hearers": hearers.map(func(e: Array) -> String: return (e[0] as Npc).id)}
	for e in hearers:
		var n: Npc = e[0]
		var factor: float = e[1]
		if n.asleep and not n.now_awake():
			if h.kind in ["door", "floorboard"]:
				n.wake(t.f("scare.wake_unease_fraction", 0.45))
			continue
		var mult := factor * (1.0 + 0.05 * Game.trait_rank("haunting"))
		var res := n.mind.apply_act({"object": h.id, "kind": h.kind, "ability": ability, "action": action,
			"unease": base_u, "fears": h.data.get("fears", []), "same_trick_twice": same_twice, "mult": mult,
			"pos": h.world_pos()}, _now, _sc())
		n.react_stage(String(res["stage_before"]), String(res["stage_after"]))
		if h.is_light() and action == "snuff":
			n.notice_snuffed(h, t.f("haunting.relight_delay_s", 7.0))
		for r in res["new_reactions"]:
			_suspicious(n, r, h)
		if res["bolted"]:
			_bolt(n)
		else:
			n.investigate(h.world_pos())
	return "ok"


## After a break or bolt: every object used in the scare is remembered; one used in an earlier scare
## within the window gets the scared villager's charm (town memory `repeat_trick`).
func _remember_tricks(n: Npc, chain: Array) -> void:
	var t := Game.tuning
	var seen := {}
	for c in chain:
		var key := "%s|%s" % [c["object"], c["ability"]]
		if seen.has(key):
			continue
		seen[key] = true
		var repeat := Game.town.record_act(String(c["object"]), String(c["ability"]),
			t.i("town_memory.repeat_within_nights", 2), t.i("town_memory.repeat_same_object_count", 2))
		var h: Hauntable = gw.level.hauntables.get(String(c["object"]))
		if repeat and h and h.data.get("source") != "carried":
			_hang_charm(n, h)


## Villagers reached by an act: [[npc, factor]]. Noise carries `noise_radius_m`; a light act reaches
## whoever is near the light; a carried light only its carrier.
func _affected(h: Hauntable, action: String) -> Array:
	var out: Array = []
	var p := h.world_pos()
	var sc := _sc()
	if h.data.get("source") == "carried":
		var n: Npc = gw.npc_by_id(String(h.data.get("carried_by", "")))
		if n:
			out.append([n, 1.0])
		return out
	for n: Npc in gw.npcs:
		if not n.visible:
			continue
		var d := n.global_position.distance_to(p)
		if h.is_light():
			var r := float(sc.get("light_act_radius_m", 7.0))
			if d <= r:
				out.append([n, 1.0])
		else:
			var radius := float(h.data.get("noise_radius_m", 8.0))
			if action == "drift_open":
				radius *= 0.8
			var f := ScareMath.noise_factor(d, radius, float(sc.get("noise_falloff", 0.5)))
			if f > 0.0:
				out.append([n, f])
	return out


func _suspicious(n: Npc, r: Dictionary, h: Hauntable) -> void:
	n.suspicious(r)
	var eff: Dictionary = r.get("effect", {})
	match String(r.get("action", "")):
		"light_more_candles":
			n.mind.flicker_mult = float(eff.get("flicker_unease_mult", 0.6))
			for id: String in gw.level.hauntables:
				var hh: Hauntable = gw.level.hauntables[id]
				if hh.is_light() and not hh.lit and hh.world_pos().distance_to(n.global_position) < 10.0:
					hh.set_lit(true)
		"hang_charm", "turn_doll_to_wall":
			var target := String(r.get("target", "last_haunted_object"))
			if target == "last_haunted_object":
				target = h.id
			var nights := int(eff.get("nights", eff.get("unhauntable_nights", Game.tuning.i("town_memory.charm_unhauntable_nights", 3))))
			Game.town.hang_charm(target, String(r.get("charm_prop", n.data.get("charm", {}).get("kind", "garlic_lavender"))), nights, n.id)
			gw.level.show_charm(target, String(Game.town.charms[target]["charm"]))
			Game.toast.emit("%s hung a charm. That one's off limits for %d nights." % [n.data["name"], nights], "memory")
		"scatter_salt":
			var door := String(eff.get("salt_line", r.get("target", "")))
			_salt(door, int(eff.get("nights", 2)), n)
		"investigate":
			n.mind.unease_mult_after = float(eff.get("unease_mult_after", 0.5))
			n.mind.unease_mult_until = _now + float(eff.get("seconds", 30))
		"search_with_pitchfork":
			var pl: Node3D = gw.player
			if pl.global_position.distance_to(n.global_position) < float(eff.get("searches_hiding_spots_radius_m", 6)) \
					and Game.rng.randf() < float(eff.get("spot_chance", 0.25)):
				n.say("THERE! I saw something!", 3.0)
				Game.town.heat += 2.0
	Game.toast.emit("%s is getting suspicious" % n.data["name"], "memory")


func _hang_charm(n: Npc, h: Hauntable) -> void:
	var nights := Game.tuning.i("town_memory.charm_unhauntable_nights", 3)
	var charm := String(n.data.get("charm", {}).get("kind", "garlic_lavender"))
	Game.town.hang_charm(h.id, charm, nights, n.id)
	gw.level.show_charm(h.id, charm)
	var lines: Array = []
	for rule in Game.population.get("town_memory", {}).get("rules", []):
		if rule["id"] == "repeat_trick":
			lines = rule.get("lines", [])
	n.say(String(lines[Game.rng.randi() % lines.size()]) if not lines.is_empty() else "A charm on it.", 4.0)
	n.play_clip("hang_charm", 0.0, "")
	Game.toast.emit("Same trick twice: %s hung a charm on the %s" % [n.data["name"], h.kind.replace("_", " ")], "memory")


func _salt(door: String, nights: int, n: Npc) -> void:
	if door == "" or not Game.markers_by_id.has(door):
		door = _nearest_door(n.global_position)
	if door == "":
		return
	Game.town.add_salt(door, nights, n.id)
	gw.level.show_salt(door)
	Game.toast.emit("%s salted a doorway. You can't pass it for %d nights." % [n.data["name"], nights], "memory")


func _nearest_door(p: Vector3) -> String:
	var best := ""
	var bd := 1e9
	for id: String in Game.markers_by_id:
		var m: Dictionary = Game.markers_by_id[id]
		if m["kind"] != "door" or String(m.get("owner", "")) == "mausoleum":
			continue
		var mp: Array = m["pos"]
		var d := p.distance_to(Vector3(mp[0], mp[1], mp[2]))
		if d < bd:
			bd = d
			best = id
	return best


func _bolt(n: Npc) -> void:
	var chain := n.mind.chain.duplicate()
	var res := n.mind.bolt(_sc())
	_remember_tricks(n, chain)
	n.bolt()
	_pay(res, n, false)
	_botch_memory(n)
	Game.stats["bolts"] += 1
	res["villager"] = n.id
	res["villager_name"] = n.data["name"]
	last_result = res
	graded.emit(res)


# ---------------------------------------------------------------- the break

## BOO: picks the best villager in the scare radius and lands (or botches) the break.
func boo(player: Node3D) -> Dictionary:
	var sc := _sc()
	var radius := float(Game.presence_level().get("scare_radius_m", 4.0))
	var target: Npc = null
	var best := -1.0
	for n: Npc in gw.npcs:
		if not n.visible or not n.is_target() or not n.is_awake():
			continue
		var d := n.global_position.distance_to(player.global_position)
		if d > radius:
			continue
		var score := n.mind.frac() * 2.0 - d / radius
		if score > best:
			best = score
			target = n
	if target == null:
		gw.hud.hint("Nobody close enough to scare")
		return {"outcome": "none"}
	var to_ghost := player.global_position - target.global_position
	var vul: Dictionary = sc.get("vulnerable", {})
	var alone := true
	for o: Npc in gw.npcs:
		if o != target and o.visible and o.is_awake() and o.global_position.distance_to(target.global_position) < float(vul.get("alone_radius_m", 10.0)):
			alone = false
	var back := ScareMath.is_back_turned(target.forward, to_ghost, float(vul.get("facing_away_deg", 100.0)))
	var door := target.mind.last_door_act()
	var doorway := not door.is_empty() and (door["pos"] as Vector3).distance_to(target.global_position) < float(vul.get("doorway_radius_m", 2.2))
	var needs := ScareMath.stage_from(String(sc.get("boo", {}).get("needs_stage", "primed")), sc.get("stages", []))
	var sees := ScareMath.can_see(target.forward, to_ghost, float(sc.get("boo", {}).get("spotted_cone_deg", 70.0)), float(sc.get("boo", {}).get("spotted_range_m", 7.0)))
	var seen := sees and target.mind.frac() < needs
	var chain := target.mind.chain.duplicate()
	var res := target.mind.boo({"alone": alone, "back_turned": back, "rigged_doorway": doorway, "seen": seen}, _now, sc)
	res["villager"] = target.id
	res["villager_name"] = target.data["name"]
	res["alone"] = alone
	res["back_turned"] = back
	res["doorway"] = doorway
	var outcome := String(res.get("outcome", "none"))
	if outcome == "botch":
		target.botch(String(res.get("reason", "too_early")))
		_botch_memory(target)
		Game.town.heat = minf(Game.tuning.f("heat.max", 100.0), Game.town.heat + float(sc.get("payout", {}).get("heat", {}).get("botch", 3.0)))
		Game.stats["botches"] += 1
		for r in res.get("new_reactions", []):
			_suspicious(target, r, null)
		Sfx.play("laugh", -6.0)
	elif outcome in ["spooked", "terrified", "legendary"]:
		target.break_scare(outcome)
		_pay(res, target, true)
		_remember_tricks(target, chain)
		Game.stats["scares"] += 1
		Game.stats[outcome] = int(Game.stats.get(outcome, 0)) + 1
		if outcome == "legendary":
			gw.player._play_clip("celebrate", 0.0)
			gw.player.set_expression("happy", 2.5)
		gw.slowmo(float(sc.get("boo", {}).get("slowmo_s", 0.6)), float(sc.get("boo", {}).get("slowmo_scale", 0.3)))
		gw.player.punch_in(float(sc.get("boo", {}).get("punch_in_s", 1.0)))
	last_result = res
	Game.scares_log.append({"villager": res["villager_name"], "outcome": outcome, "score": res.get("score", 0),
		"night": Game.nights, "hour": Game.hour_at(Game.cycle_t)})
	while Game.scares_log.size() > 20:
		Game.scares_log.pop_front()
	graded.emit(res)
	return res


func _pay(res: Dictionary, n: Npc, is_break: bool) -> void:
	var sc := _sc()
	var t := Game.tuning
	var outcome := String(res.get("outcome", "bolt"))
	var fright := float(res.get("fright", 0.0))
	Game.add_fright(fright, ["haunting"])
	var rem_mult := float(n.data.get("on_break", {}).get("remembrance", 1.0)) if is_break else 1.0
	if res.get("made_believer", false):
		rem_mult *= t.f("remembrance.believer_mult", 3.0)
	var area := String(Game.area_at(n.global_position).get("id", "millbrook_square"))
	Game.town.add_remembrance(area, ScareMath.remembrance_for(outcome, sc.get("payout", {}), rem_mult))
	Game.town.heat = minf(t.f("heat.max", 100.0), Game.town.heat + float(sc.get("payout", {}).get("heat", {}).get(outcome, 1.0)))
	if not is_break:
		return
	# legend: points, epithet from the kinds used, rumors, Pip the witness
	var pts := 0.0
	var lp := t.d("town_memory.legend_points")
	if outcome == "legendary":
		pts += float(lp.get("legendary", 2))
	elif outcome == "terrified":
		pts += float(lp.get("terrified", 1))
	if res.get("made_believer", false):
		pts += float(lp.get("believer", 3))
		Game.town.add_remembrance(area, 0.1)
	if outcome in ["terrified", "legendary"] and not last_act.is_empty():
		var h: Hauntable = gw.level.hauntables.get(last_act.get("object", ""))
		if h:
			Game.town.count_epithet(h.kind, String(last_act.get("action", "")))
	var witnessed := _pip_sees(n)
	if witnessed:
		pts *= t.f("town_memory.witness_mult", 3.0)
		pts = maxf(pts, 1.0)
		res["witnessed"] = true
	var add_rumor := outcome == "legendary" or witnessed or (outcome == "terrified" and Game.rng.randf() < t.f("town_memory.terrified_rumor_chance", 0.35))
	if add_rumor:
		_make_rumor(n, witnessed)
	if pts > 0.0 and Game.town.add_legend(pts):
		var nm := Game.town.legend_name()
		var bonus := Game.town.stage_remembrance_bonus()
		for k: String in Game.town.remembrance:
			Game.town.add_remembrance(k, bonus)
		legend_grew.emit(nm)
		Game.toast.emit("Millbrook whispers of %s" % nm, "legend")


func _pip_sees(n: Npc) -> bool:
	var pip: Npc = gw.npc_by_id("pip")
	if pip == null or not pip.visible or not pip.is_awake() or pip == n:
		return false
	if pip.global_position.distance_to(n.global_position) > Game.tuning.f("town_memory.witness_radius_m", 18.0):
		return false
	var w: Dictionary = pip.data.get("witness", {})
	var r: Dictionary = w.get("reaction", {})
	pip.say(String(r.get("line", "Did you SEE that?!")), 4.0)
	pip.play_clip(String(r.get("animation", "startle")), 0.0, "")
	return true


func _make_rumor(n: Npc, witnessed: bool) -> void:
	var temps := Game.town.rumor_templates()
	if temps.is_empty():
		return
	var h: Hauntable = gw.level.hauntables.get(last_act.get("object", ""))
	var place := String(Game.area_at(n.global_position).get("name", "the village"))
	var tagged: Dictionary = Game.population.get("town_memory", {}).get("rumors", {}).get("tagged", {})
	var tmpl := String(temps[Game.rng.randi() % temps.size()])
	if witnessed and tagged.has("witness"):
		tmpl = String(tagged["witness"])
	elif n.mind.believer and n.mind.skeptic and tagged.has("skeptic"):
		tmpl = String(tagged["skeptic"])
	var hour := Game.hour_at(Game.cycle_t)
	var text := Game.town.make_rumor(tmpl, {"victim": String(n.data["name"]).get_slice(" ", String(n.data["name"]).get_slice_count(" ") - 1),
		"pronouns": n.data.get("pronouns", {}), "object": h.kind.replace("_", " ") if h else "door", "place": place,
		"action": String(last_act.get("action", "creak")), "hour": "%d o'clock" % (int(hour) % 12 if int(hour) % 12 != 0 else 12)})
	Game.town.add_rumor(text, "pip" if witnessed else "tavern", Game.tuning.i("town_memory.max_rumors", 6))


func _botch_memory(n: Npc) -> void:
	var door := _nearest_door(n.global_position)
	if door != "" and not Game.town.salt_lines.has(door):
		_salt(door, Game.tuning.i("town_memory.salt_line_nights", 2), n)


# ---------------------------------------------------------------- per frame

func tick(dt: float, now: float) -> void:
	_now = now
	var sc := _sc()
	for k: String in Game.minds:
		(Game.minds[k] as VillagerMind).tick(dt, now, sc)
	_overhear(now)
	_rumors(dt)
	var t := Game.tuning
	Game.town.decay_remembrance(dt, t.f("remembrance.decay_per_s", 0.00012), t.f("remembrance.min", 0.0))
	Game.town.heat = maxf(0.0, Game.town.heat - t.f("heat.decay_per_s", 0.01) * dt)
	_rem_cd -= dt
	if _rem_cd <= 0.0:
		_rem_cd = 2.0
		gw.world.set_remembrance(Game.areas, Game.town.remembrance, t.f("remembrance.fading_below", 0.4), t.f("remembrance.fully_faded_at", 0.1))


func _overhear(now: float) -> void:
	var t := Game.tuning
	var pl: Player = gw.player
	if pl.manifest_left > 0.0:
		return
	for n: Npc in gw.npcs:
		if not n.visible or not n.is_awake():
			continue
		if n.global_position.distance_to(pl.global_position) > t.f("overhear.radius_m", 4.0):
			continue
		if ScareMath.stage_index(n.mind.frac(), t.a("scare.stages")) >= 2:
			continue
		if now < float(_overhear_cd.get(n.id, -100.0)):
			continue
		var lines: Array = n.data.get("mutters", {}).get("lines", [])
		if lines.is_empty():
			continue
		var i := int(_mutter_i.get(n.id, Game.rng.randi() % lines.size())) % lines.size()
		_mutter_i[n.id] = i + 1
		_overhear_cd[n.id] = now + t.f("overhear.cooldown_s", 14.0)
		n.say(String(lines[i]), t.f("overhear.bubble_s", 4.5))
		gw.hud.overheard(String(n.data["name"]), String(lines[i]))
		if n.mind.hear_line(i, t.i("overhear.lines_to_reveal_fear", 3)) and n.is_target():
			var fear := String(n.mind.fear).replace("_", " ")
			Game.toast.emit("Fear discovered: %s is afraid of %s" % [n.data["name"], fear], "fear")
			fear_discovered.emit(n.id)


func _rumors(dt: float) -> void:
	_rumor_cd -= dt
	if _rumor_cd > 0.0:
		return
	_rumor_cd = 1.0
	var pl: Player = gw.player
	if String(Game.area_at(pl.global_position).get("id", "")) != "tavern" or Game.town.rumors.is_empty():
		return
	for n: Npc in gw.npcs:
		if n.visible and n.is_awake() and n.global_position.distance_to(pl.global_position) < Game.tuning.f("town_memory.rumor_heard_within_m", 6.0):
			var r: Dictionary = Game.town.rumors[Game.rng.randi() % Game.town.rumors.size()]
			n.say(String(r["text"]), 5.5)
			gw.hud.overheard(String(n.data["name"]) + " (rumor)", String(r["text"]))
			_rumor_cd = Game.tuning.f("town_memory.rumor_cooldown_s", 20.0)
			return


## A new night: town memory ages, suspicion fades, charms and salt lines that expired come down.
func new_night() -> void:
	Game.town.new_night()
	for k: String in Game.minds:
		(Game.minds[k] as VillagerMind).new_night(_sc())
	gw.level.clear_charms_not_in(Game.town.charms)
	gw.level.clear_salt_not_in(Game.town.salt_lines)
	for id: String in gw.level.hauntables:
		var h: Hauntable = gw.level.hauntables[id]
		if h.is_light() and not h.lit:
			h.set_lit(true)


func restore_memory_visuals() -> void:
	for k: String in Game.town.charms:
		gw.level.show_charm(k, String(Game.town.charms[k]["charm"]))
	for k: String in Game.town.salt_lines:
		gw.level.show_salt(k)
