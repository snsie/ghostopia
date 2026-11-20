## Feel numbers for the crowd sim, read from tuning.json `battle`, shared by the CPU sim and packed
## into the GPU's params buffer (same order as `Params` in shaders/crowd/crowd_common.glsl).
class_name CrowdParams
extends RefCounted

var form := 100.0
var resolve := 100.0
var speed := 1.7               # walk speed, m/s
var flee_speed := 2.6
var accel := 6.0
var sep_radius := 0.85         # units push apart inside this distance
var sep_strength := 2.6
var engage := 2.4              # a fighting unit turns on the nearest enemy inside this
var reach := 1.15              # melee reach
var attack_cd := 1.5           # seconds between swings (x 0.8-1.2 per unit)
var attack_dmg := 2.5
var strike_at := 0.33          # seconds into the attack clip when the blow lands
var hit_resolve_k := 0.4       # Resolve lost per point of Form damage
var shaken_below := 40.0       # Resolve under this: unit is shaken
var shaken_mult := 1.5         # shaken units take extra damage
var fear_radius := 2.4         # routing allies inside this lower Resolve
var rout_drain := 15.0         # Resolve per second when every ally nearby is routing (scaled by their share)
var rout_shock := 40.0         # Resolve lost once if every ally nearby broke at once (scaled by their share)
var scatter_shock := 20.0      # the same for allies scattered nearby
var regen := 0.5               # Resolve per second when calm (plus the clan's bonus)
var dissolve_s := 0.8
var wade_mult := 0.6           # speed in running water (water walkers)
var wade_sink := 0.45
var cell_m := 2.5              # spatial hash cell size (>= engage and fear radius)
var cell_cap := 48
var attack_clip_s := 0.667
var press_free := 3.0          # neighbours inside sep_radius before crowd pressure slows a unit
var press_k := 0.2             # speed lost per extra neighbour (down to 15 %)
var water_cost := 4.0          # flow-field cost of a metre of running water for water walkers (not on the GPU)


static func from_tuning(t: Dictionary) -> CrowdParams:
	var p := CrowdParams.new()
	for k: String in t:
		if k in p:
			p.set(k, float(t[k]) if k != "cell_cap" else int(t[k]))
	return p


## 32 floats in the order of the GLSL Params block.
func pack() -> PackedFloat32Array:
	return PackedFloat32Array([
		form, resolve, speed, flee_speed,
		accel, sep_radius, sep_strength, engage,
		reach, attack_cd, attack_dmg, strike_at,
		hit_resolve_k, shaken_below, shaken_mult, fear_radius,
		rout_drain, rout_shock, scatter_shock, regen,
		dissolve_s, wade_mult, wade_sink, cell_m,
		float(cell_cap), attack_clip_s, press_free, press_k,
		0.0, 0.0, 0.0, 0.0,
	])


## Per-clan live modifiers: 8 floats each (speed mult, extra regen, scare mult (scare spheres),
## damage mult, water walker, contagion mult (fear spreading from breaking allies), unused x2).
## Bells and other clan fears change these.
static func clan_block(speed_mult: float, regen_bonus: float, fear_mult: float, dmg_mult: float, water_walker: bool,
		contagion_mult: float = -1.0) -> PackedFloat32Array:
	var cm := fear_mult if contagion_mult < 0.0 else contagion_mult
	return PackedFloat32Array([speed_mult, regen_bonus, fear_mult, dmg_mult, 1.0 if water_walker else 0.0, cm, 0.0, 0.0])
