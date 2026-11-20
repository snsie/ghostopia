## GPU crowd sim: runs shaders/crowd/crowd_sim.glsl on the main RenderingDevice (Forward+: Vulkan on
## Windows, Metal on macOS). Unit state ping-pongs between two storage buffers; the step pass writes
## every unit's instance straight into its clan's MultiMesh buffer, so the CPU never touches positions.
## The CPU only uploads small things each frame (hit spheres, promoted units, clan modifiers) and reads
## back a small summary plus the nearby list around the ghost a few times a second, asynchronously.
## Same interface as CrowdSimCpu; `summary` and `nearby` lag a few frames behind.
class_name CrowdSimGpu
extends RefCounted

const L := preload("res://scripts/battle/crowd_layout.gd")
const SHADER := "res://shaders/crowd/crowd_sim.glsl"
const PC_SIZE := 80

var n := 0
var p: CrowdParams
var terrain: BattleTerrain
var clans := 0
var clan_start := PackedInt32Array()
var clan_size := PackedInt32Array()
var summary := PackedInt32Array()
var nearby: Array[PackedFloat32Array] = []
var ghost := Vector3(-1000, 0, -1000)
var frame := 0
var readback_every := 4
var readbacks := 0                  # completed summary readbacks (for tests and the bench)
var ok := false
var error := ""

var _rd: RenderingDevice
var _shader := RID()
var _pipeline := RID()
var _units: Array[RID] = []
var _acc: Array[RID] = []
var _count := RID()
var _items := RID()
var _heights := RID()
var _flags := RID()
var _flow := RID()
var _consts := RID()
var _spheres := RID()
var _summary := RID()
var _nearby := RID()
var _req := RID()
var _requests := PackedInt32Array()     # promotion requests for the next step
var _sets: Array[RID] = []
var _cur := 0                       # render thread: which unit buffer is the input this frame
var _gx := 0
var _gz := 0
var _cells := 0
var _consts_data := PackedFloat32Array()
var _consts_dirty := false
var _sphere_data := PackedFloat32Array()
var _writes: Dictionary = {}        # unit index -> PackedFloat32Array record
var _rb_inflight := false
var _since_rb := 0
var _mm_rids: Array[RID] = []


static func available() -> bool:
	return RenderingServer.get_rendering_device() != null


## `multimeshes`: one MultiMesh per clan (TRANSFORM_3D, custom data, no colours), instance_count = clan size.
func setup(p_terrain: BattleTerrain, params: CrowdParams, starts: PackedInt32Array, sizes: PackedInt32Array,
		init_units: PackedFloat32Array, clan_params: PackedFloat32Array, multimeshes: Array[RID]) -> void:
	terrain = p_terrain
	p = params
	clan_start = starts
	clan_size = sizes
	clans = starts.size()
	n = init_units.size() / L.STRIDE
	summary.resize(L.SUM_SIZE)
	_mm_rids = multimeshes
	_gx = ceili(terrain.w / p.cell_m)
	_gz = ceili(terrain.h / p.cell_m)
	_cells = _gx * _gz
	_consts_data = p.pack()
	var cp := clan_params.duplicate()
	cp.resize(L.MAX_CLANS * 8)
	_consts_data.append_array(cp)
	# lambdas capture `me` strongly, so a queued render-thread call never runs on a freed object
	var me := self
	var h := terrain.heights
	var f := terrain.flags
	var fl := terrain.packed_fields()
	RenderingServer.call_on_render_thread(func() -> void: me._rt_setup(init_units, h, f, fl))


func set_clan(c: int, block: PackedFloat32Array) -> void:
	for k in 8:
		_consts_data[32 + c * 8 + k] = block[k]
	_consts_dirty = true


func add_sphere(center: Vector3, radius: float, form_dmg: float, resolve_dmg: float, clan_mask: int,
		target: int = -1, falloff: float = 0.6, flags: int = 0) -> void:
	if _sphere_data.size() >= L.SPHERE_MAX * L.SPHERE_STRIDE:
		return
	_sphere_data.append_array(PackedFloat32Array([center.x, center.y, center.z, radius,
		form_dmg, resolve_dmg, float(clan_mask), float(target), falloff, float(flags), 0.0, 0.0]))


## Asks the GPU to hand unit i to the near tier. It is frozen as pending (ACTOR 0.5) if still alive, and
## shows up that way in the next nearby readback with its exact record (no resurrecting a unit that died
## since the last snapshot).
func request_promotion(i: int) -> void:
	if _requests.size() < 64:
		_requests.append(i)


## Overwrites unit i before the next step (promotion, demotion, near actors' per-frame state).
func write_unit(i: int, rec: PackedFloat32Array) -> void:
	_writes[i] = rec


func step(dt: float) -> void:
	if not ok and error != "":
		return
	var pcs: Array[PackedByteArray] = []
	for mode in 3:
		pcs.append(_push_constants(mode, dt))
	var spheres := _sphere_data
	_sphere_data = PackedFloat32Array()
	var writes := _writes
	_writes = {}
	var reqs := _requests
	_requests = PackedInt32Array()
	var consts := PackedFloat32Array()
	if _consts_dirty:
		consts = _consts_data.duplicate()
		_consts_dirty = false
	_since_rb += 1
	var rb := false
	if _since_rb >= readback_every and not _rb_inflight:
		rb = true
		_rb_inflight = true
		_since_rb = 0
	var me := self
	RenderingServer.call_on_render_thread(func() -> void: me._rt_step(pcs, spheres, writes, consts, rb, reqs))
	frame += 1


func _push_constants(mode: int, dt: float) -> PackedByteArray:
	var b := PackedByteArray()
	b.resize(PC_SIZE)
	b.encode_u32(0, mode)
	b.encode_u32(4, n)
	b.encode_u32(8, _gx)
	b.encode_u32(12, _gz)
	b.encode_float(16, dt)
	b.encode_float(20, ghost.x)
	b.encode_float(24, ghost.z)
	b.encode_float(28, L.NEAR_BANDS * L.NEAR_BAND_M)
	b.encode_u32(32, terrain.w)
	b.encode_u32(36, terrain.h)
	b.encode_u32(40, 0)   # sphere count: set on the render thread
	b.encode_u32(44, frame)
	b.encode_u32(48, clan_start[0])
	b.encode_u32(52, clan_start[mini(1, clans - 1)])
	b.encode_u32(56, _cells)
	b.encode_u32(60, clans)
	b.encode_float(64, terrain.mid_x)
	return b


## Frees the GPU buffers (restart / quit to title). Not needed at app exit: the device goes away whole.
func free_gpu() -> void:
	if ok:
		var me := self
		RenderingServer.call_on_render_thread(func() -> void: me._rt_free())
	ok = false


# ---------------------------------------------------------------- render thread

func _storage(bytes: PackedByteArray) -> RID:
	return _rd.storage_buffer_create(bytes.size(), bytes)


func _zeros(count: int) -> PackedByteArray:
	var b := PackedByteArray()
	b.resize(maxi(4, count * 4))
	return b


func _rt_setup(init_units: PackedFloat32Array, heights: PackedFloat32Array, flags: PackedInt32Array, flow: PackedFloat32Array) -> void:
	_rd = RenderingServer.get_rendering_device()
	if _rd == null:
		error = "no RenderingDevice"
		return
	var sf := load(SHADER) as RDShaderFile
	if sf == null:
		error = "missing %s" % SHADER
		return
	var spirv := sf.get_spirv()
	if spirv.compile_error_compute != "":
		error = spirv.compile_error_compute
		push_error("crowd shader: " + error)
		return
	_shader = _rd.shader_create_from_spirv(spirv, "crowd_sim")
	_pipeline = _rd.compute_pipeline_create(_shader)
	var ub := init_units.to_byte_array()
	_units = [_storage(ub), _storage(ub)]
	_acc = [_storage(_zeros(n)), _storage(_zeros(n))]
	_count = _storage(_zeros(_cells))
	_items = _storage(_zeros(_cells * p.cell_cap))
	_heights = _storage(heights.to_byte_array())
	_flags = _storage(flags.to_byte_array())
	_flow = _storage(flow.to_byte_array())
	_consts = _storage(_consts_data.to_byte_array())
	_spheres = _storage(_zeros(L.SPHERE_MAX * L.SPHERE_STRIDE))
	_summary = _storage(_zeros(L.SUM_SIZE + L.NEAR_BANDS))
	_nearby = _storage(_zeros(L.NEAR_BANDS * L.NEAR_BAND_CAP * L.NEAR_ENTRY))
	_req = _storage(_zeros(65))
	var mm0 := RenderingServer.multimesh_get_buffer_rd_rid(_mm_rids[0])
	var mm1 := RenderingServer.multimesh_get_buffer_rd_rid(_mm_rids[mini(1, _mm_rids.size() - 1)])
	if not mm0.is_valid() or not mm1.is_valid():
		error = "MultiMesh has no RenderingDevice buffer"
		push_error("crowd: " + error)
		return
	for k in 2:
		var bufs: Array[RID] = [_units[k], _units[1 - k], _acc[k], _acc[1 - k], _count, _items, _heights, _flags,
			_flow, _consts, _spheres, _summary, _nearby, mm0, mm1, _req]
		var uniforms: Array[RDUniform] = []
		for b in bufs.size():
			var u := RDUniform.new()
			u.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
			u.binding = b
			u.add_id(bufs[b])
			uniforms.append(u)
		_sets.append(_rd.uniform_set_create(uniforms, _shader, 0))
	ok = true


func _rt_step(pcs: Array[PackedByteArray], spheres: PackedFloat32Array, writes: Dictionary, consts: PackedFloat32Array, rb: bool,
		reqs: PackedInt32Array) -> void:
	if not ok or _rd == null:
		return
	var rq := PackedInt32Array([reqs.size()])
	rq.append_array(reqs)
	_rd.buffer_update(_req, 0, rq.size() * 4, rq.to_byte_array())
	for i: int in writes:
		var rec: PackedFloat32Array = writes[i]
		_rd.buffer_update(_units[_cur], i * L.STRIDE * 4, L.STRIDE * 4, rec.to_byte_array())
	if not consts.is_empty():
		_rd.buffer_update(_consts, 0, consts.size() * 4, consts.to_byte_array())
	var nsph := spheres.size() / L.SPHERE_STRIDE
	if nsph > 0:
		_rd.buffer_update(_spheres, 0, spheres.size() * 4, spheres.to_byte_array())
	var step_pc := pcs[2]
	step_pc.encode_u32(40, nsph)
	var cl := _rd.compute_list_begin()
	_rd.compute_list_bind_compute_pipeline(cl, _pipeline)
	_rd.compute_list_bind_uniform_set(cl, _sets[_cur], 0)
	var groups_clear := ceili(maxf(_cells, L.SUM_SIZE + L.NEAR_BANDS) / 64.0)
	var groups_units := ceili(n / 64.0)
	_rd.compute_list_set_push_constant(cl, pcs[0], PC_SIZE)
	_rd.compute_list_dispatch(cl, groups_clear, 1, 1)
	_rd.compute_list_add_barrier(cl)
	_rd.compute_list_set_push_constant(cl, pcs[1], PC_SIZE)
	_rd.compute_list_dispatch(cl, groups_units, 1, 1)
	_rd.compute_list_add_barrier(cl)
	_rd.compute_list_set_push_constant(cl, step_pc, PC_SIZE)
	_rd.compute_list_dispatch(cl, groups_units, 1, 1)
	_rd.compute_list_end()
	_cur = 1 - _cur
	if rb:
		if _rd.has_method("buffer_get_data_async"):
			var me := self
			_rd.buffer_get_data_async(_summary, func(d: PackedByteArray) -> void: me._rt_on_summary(d))
			_rd.buffer_get_data_async(_nearby, func(d: PackedByteArray) -> void: me._rt_on_nearby(d))
		else:
			_rt_on_summary(_rd.buffer_get_data(_summary))
			_rt_on_nearby(_rd.buffer_get_data(_nearby))


var _pending_summary := PackedByteArray()


func _rt_on_summary(data: PackedByteArray) -> void:
	_pending_summary = data


func _rt_on_nearby(data: PackedByteArray) -> void:
	_apply_readback.call_deferred(_pending_summary, data)


func _apply_readback(sum_bytes: PackedByteArray, near_bytes: PackedByteArray) -> void:
	_rb_inflight = false
	if sum_bytes.size() < (L.SUM_SIZE + L.NEAR_BANDS) * 4:
		return
	var all := sum_bytes.to_int32_array()
	summary = all.slice(0, L.SUM_SIZE)
	var nf := near_bytes.to_float32_array()
	var out: Array[PackedFloat32Array] = []
	for b in L.NEAR_BANDS:
		var cnt := mini(all[L.SUM_SIZE + b], L.NEAR_BAND_CAP)
		for s in cnt:
			var e := (b * L.NEAR_BAND_CAP + s) * L.NEAR_ENTRY
			out.append(nf.slice(e, e + L.NEAR_ENTRY))
	nearby = out
	readbacks += 1


func _rt_free() -> void:
	if _rd == null:
		return
	for r: RID in _sets:
		if r.is_valid() and _rd.uniform_set_is_valid(r):
			_rd.free_rid(r)
	_sets.clear()
	for r: RID in _units + _acc + [_count, _items, _heights, _flags, _flow, _consts, _spheres, _summary, _nearby, _req]:
		if r.is_valid():
			_rd.free_rid(r)
	if _pipeline.is_valid():
		_rd.free_rid(_pipeline)
	if _shader.is_valid():
		_rd.free_rid(_shader)
	_rd = null
