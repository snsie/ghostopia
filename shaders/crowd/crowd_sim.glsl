#[compute]
#version 450

// GPU crowd sim for the battle prototype. One shader, three passes chosen by pc.mode:
//   0 clear: zero the spatial-hash counts, the per-frame summary entries and the nearby-band counters
//   1 bin:   put every live unit into its spatial-hash cell (fixed capacity per cell)
//   2 step:  one unit per thread, the same rules in the same order as scripts/battle/crowd_sim_cpu.gd
//            (keep them in sync), writing the next state, the clan's MultiMesh instance, the summary
//            and the nearby list around the ghost.
// Unit layout: scripts/battle/crowd_layout.gd (STRIDE 20 floats).

layout(local_size_x = 64, local_size_y = 1, local_size_z = 1) in;

#define STRIDE 20
#define PX 0
#define PZ 1
#define VX 2
#define VZ 3
#define FORM 4
#define RESOLVE 5
#define CLAN 6
#define STATE 7
#define ATTACK_CD 8
#define ANIM_T 9
#define YAW 10
#define PY 11
#define TARGET 12
#define STATE_T 13
#define FLASH 14
#define SEED 15
#define CLIP 16
#define STRIKE 17
#define ACTOR 19
#define PENDING_T 18
#define PENDING_MAX 90.0

#define S_FIGHT 0
#define S_ROUT 1
#define S_SCATTERED 2
#define S_LEFT 3

#define CLIP_IDLE 0
#define CLIP_WALK 1
#define CLIP_ATTACK 2
#define CLIP_FLEE 3

#define T_BLOCKED 1
#define T_WATER 2
#define T_HOME0 8

#define SPHERE_STRIDE 12
#define SPH_SCARE 1
#define MM_STRIDE 16

#define MAX_CLANS 4
#define SUM_STATE 0
#define SUM_ROUTS 20
#define SUM_SCATTERS 24
#define SUM_FLANK 28
#define SUM_FLANK_RES 36
#define SUM_ENGAGED 44
#define SUM_FRONT 48
#define SUM_SIZE 72

#define NEAR_BANDS 8
#define NEAR_BAND_M 1.5
#define NEAR_BAND_CAP 40
#define NEAR_ENTRY 21

#define DMG_FIXED 256.0
#define PI 3.14159265358979
#define TAU 6.28318530717959

layout(set = 0, binding = 0, std430) restrict readonly buffer UnitsIn { float d[]; } uin;
layout(set = 0, binding = 1, std430) restrict writeonly buffer UnitsOut { float d[]; } uout;
layout(set = 0, binding = 2, std430) restrict buffer AccRead { uint d[]; } acc_read;
layout(set = 0, binding = 3, std430) restrict buffer AccWrite { uint d[]; } acc_write;
layout(set = 0, binding = 4, std430) restrict buffer GridCount { uint d[]; } grid_count;
layout(set = 0, binding = 5, std430) restrict buffer GridItems { uint d[]; } grid_items;
layout(set = 0, binding = 6, std430) restrict readonly buffer Heights { float d[]; } heights;
layout(set = 0, binding = 7, std430) restrict readonly buffer Flags { int d[]; } flags;
layout(set = 0, binding = 8, std430) restrict readonly buffer Flow { float d[]; } flow;
// [0, 32) CrowdParams.pack(), [32, 64) 8 floats per clan
layout(set = 0, binding = 9, std430) restrict readonly buffer Consts { float d[]; } k;
layout(set = 0, binding = 10, std430) restrict readonly buffer Spheres { float d[]; } sph;
// [0, SUM_SIZE) summary, [SUM_SIZE, SUM_SIZE + NEAR_BANDS) nearby band counts
layout(set = 0, binding = 11, std430) restrict buffer Summary { uint d[]; } summary;
layout(set = 0, binding = 12, std430) restrict writeonly buffer Nearby { float d[]; } nearby;
layout(set = 0, binding = 13, std430) restrict writeonly buffer MM0 { float d[]; } mm0;
layout(set = 0, binding = 14, std430) restrict writeonly buffer MM1 { float d[]; } mm1;
// promotion requests from the near tier: [count, index...]. A requested unit that is still fighting or
// routing is frozen as "pending" (ACTOR 0.5) so the CPU builds its actor from an exact record.
layout(set = 0, binding = 15, std430) restrict readonly buffer Requests { uint d[]; } req;

layout(push_constant, std430) uniform PC {
	uint mode;
	uint n;
	uint grid_w;
	uint grid_h;
	float dt;
	float ghost_x;
	float ghost_z;
	float near_r;
	uint terr_w;
	uint terr_h;
	uint sphere_count;
	uint frame;
	uint start0;
	uint start1;
	uint cells;
	uint clans;
	float mid_x;
	float pad0;
	float pad1;
	float pad2;
} pc;

// CrowdParams.pack() order
#define P_FORM k.d[0]
#define P_RESOLVE k.d[1]
#define P_SPEED k.d[2]
#define P_FLEE_SPEED k.d[3]
#define P_ACCEL k.d[4]
#define P_SEP_RADIUS k.d[5]
#define P_SEP_STRENGTH k.d[6]
#define P_ENGAGE k.d[7]
#define P_REACH k.d[8]
#define P_ATTACK_CD k.d[9]
#define P_ATTACK_DMG k.d[10]
#define P_STRIKE_AT k.d[11]
#define P_HIT_RESOLVE_K k.d[12]
#define P_SHAKEN_BELOW k.d[13]
#define P_SHAKEN_MULT k.d[14]
#define P_FEAR_RADIUS k.d[15]
#define P_ROUT_DRAIN k.d[16]
#define P_ROUT_SHOCK k.d[17]
#define P_SCATTER_SHOCK k.d[18]
#define P_REGEN k.d[19]
#define P_DISSOLVE k.d[20]
#define P_WADE_MULT k.d[21]
#define P_WADE_SINK k.d[22]
#define P_CELL_M k.d[23]
#define P_CELL_CAP uint(k.d[24])
#define P_ATTACK_CLIP k.d[25]
#define P_PRESS_FREE k.d[26]
#define P_PRESS_K k.d[27]

float u_in(uint i, int f) {
	return uin.d[i * STRIDE + f];
}

int terr_cell(float x, float z) {
	int cx = clamp(int(floor(x)), 0, int(pc.terr_w) - 1);
	int cz = clamp(int(floor(z)), 0, int(pc.terr_h) - 1);
	return cx + int(pc.terr_w) * cz;
}

bool passable_at(float x, float z, int clan) {
	if (x < 0.0 || z < 0.0 || x >= float(pc.terr_w) || z >= float(pc.terr_h)) {
		return false;
	}
	int f = flags.d[terr_cell(x, z)];
	if ((f & T_BLOCKED) != 0) {
		return false;
	}
	if ((f & T_WATER) != 0 && k.d[32 + clan * 8 + 4] < 0.5) {
		return false;
	}
	return true;
}

// Godot's fmod / lerp_angle / wrapf, so both sims turn the same way
float fmod_g(float x, float y) {
	return x - y * trunc(x / y);
}

float lerp_angle_g(float from, float to, float w) {
	float diff = fmod_g(to - from, TAU);
	float dist = fmod_g(2.0 * diff, TAU) - diff;
	return from + dist * w;
}

float wrap_pi(float v) {
	return v - TAU * floor((v + PI) / TAU);
}

uint grid_cell(float x, float z) {
	uint gx = uint(clamp(int(x / P_CELL_M), 0, int(pc.grid_w) - 1));
	uint gz = uint(clamp(int(z / P_CELL_M), 0, int(pc.grid_h) - 1));
	return gx + pc.grid_w * gz;
}

void write_mm(uint i, int clan, float px, float py, float pz, float yaw, float scl, float clip, float anim_t, float code, float flash) {
	float cs = cos(yaw) * scl;
	float sn = sin(yaw) * scl;
	uint m;
	if (clan == 0) {
		m = (i - pc.start0) * MM_STRIDE;
		mm0.d[m + 0] = cs; mm0.d[m + 1] = 0.0; mm0.d[m + 2] = sn; mm0.d[m + 3] = px;
		mm0.d[m + 4] = 0.0; mm0.d[m + 5] = scl; mm0.d[m + 6] = 0.0; mm0.d[m + 7] = py;
		mm0.d[m + 8] = -sn; mm0.d[m + 9] = 0.0; mm0.d[m + 10] = cs; mm0.d[m + 11] = pz;
		mm0.d[m + 12] = clip; mm0.d[m + 13] = anim_t; mm0.d[m + 14] = code; mm0.d[m + 15] = flash;
	} else {
		m = (i - pc.start1) * MM_STRIDE;
		mm1.d[m + 0] = cs; mm1.d[m + 1] = 0.0; mm1.d[m + 2] = sn; mm1.d[m + 3] = px;
		mm1.d[m + 4] = 0.0; mm1.d[m + 5] = scl; mm1.d[m + 6] = 0.0; mm1.d[m + 7] = py;
		mm1.d[m + 8] = -sn; mm1.d[m + 9] = 0.0; mm1.d[m + 10] = cs; mm1.d[m + 11] = pz;
		mm1.d[m + 12] = clip; mm1.d[m + 13] = anim_t; mm1.d[m + 14] = code; mm1.d[m + 15] = flash;
	}
}

void copy_unit(uint i) {
	for (int f = 0; f < STRIDE; f++) {
		uout.d[i * STRIDE + f] = uin.d[i * STRIDE + f];
	}
}

void pass_clear(uint gid) {
	if (gid < pc.cells) {
		grid_count.d[gid] = 0u;
	}
	if (gid < SUM_SIZE) {
		if (gid < SUM_ROUTS || gid >= SUM_FLANK) {
			summary.d[gid] = 0u;
		}
	}
	if (gid < NEAR_BANDS) {
		summary.d[SUM_SIZE + gid] = 0u;
	}
}

void pass_bin(uint i) {
	if (i >= pc.n) {
		return;
	}
	int st = int(u_in(i, STATE));
	if (st == S_LEFT) {
		return;
	}
	if (st == S_SCATTERED && u_in(i, STATE_T) > 0.0) {
		return;
	}
	uint gc = grid_cell(u_in(i, PX), u_in(i, PZ));
	uint slot = atomicAdd(grid_count.d[gc], 1u);
	if (slot < P_CELL_CAP) {
		grid_items.d[gc * P_CELL_CAP + slot] = i;
	}
}

void pass_step(uint i) {
	if (i >= pc.n) {
		return;
	}
	uint o = i * STRIDE;
	int state = int(uin.d[o + STATE]);
	int clan = int(uin.d[o + CLAN]);
	float px = uin.d[o + PX];
	float pz = uin.d[o + PZ];
	float dt = pc.dt;

	float act = uin.d[o + ACTOR];
	bool is_actor = act > 0.75;
	bool pending = act > 0.25 && !is_actor;
	bool accept = false;
	if (!is_actor && !pending && (state == S_FIGHT || state == S_ROUT)) {
		uint nreq = min(req.d[0], 64u);
		for (uint r = 0u; r < nreq; r++) {
			if (req.d[1u + r] == i) {
				accept = true;
				pending = true;
			}
		}
	}
	atomicAdd(summary.d[SUM_STATE + state * MAX_CLANS + clan], 1u);
	if ((state == S_FIGHT || state == S_ROUT) && !is_actor) {
		float gd = length(vec2(px - pc.ghost_x, pz - pc.ghost_z));
		if (gd < pc.near_r) {
			uint band = min(uint(gd / NEAR_BAND_M), uint(NEAR_BANDS - 1));
			uint slot = atomicAdd(summary.d[SUM_SIZE + band], 1u);
			if (slot < NEAR_BAND_CAP) {
				uint e = (band * NEAR_BAND_CAP + slot) * NEAR_ENTRY;
				nearby.d[e] = float(i);
				for (int f = 0; f < STRIDE; f++) {
					nearby.d[e + 1 + f] = uin.d[o + f];
				}
			}
		}
	}

	if (pending) {
		// waiting for the near tier: frozen, still drawn, released again if the CPU never takes it
		acc_read.d[i] = 0u;
		copy_unit(i);
		float waited = accept ? 0.0 : uin.d[o + PENDING_T] + 1.0;
		uout.d[o + PENDING_T] = waited;
		uout.d[o + ACTOR] = waited > PENDING_MAX ? 0.0 : 0.5;
		write_mm(i, clan, px, uin.d[o + PY], pz, uin.d[o + YAW], 1.0, uin.d[o + CLIP], uin.d[o + ANIM_T],
			state == S_ROUT ? 0.5 : 0.0, uin.d[o + FLASH]);
		return;
	}
	if (state == S_LEFT || is_actor || state == S_SCATTERED) {
		acc_read.d[i] = 0u;
		copy_unit(i);
		float st_t = uin.d[o + STATE_T];
		int new_st = state;
		if (state == S_SCATTERED && !is_actor) {
			st_t += dt;
			uout.d[o + STATE_T] = st_t;
			if (st_t >= P_DISSOLVE) {
				new_st = S_LEFT;
				uout.d[o + STATE] = float(S_LEFT);
			}
		}
		float scl = 0.0;
		float code = 0.0;
		if (new_st == S_SCATTERED && !is_actor) {
			float kk = st_t / P_DISSOLVE;
			scl = 1.0 + 0.35 * kk;
			code = 1.0 + clamp(kk, 0.0, 1.0);
		}
		write_mm(i, clan, px, uin.d[o + PY], pz, uin.d[o + YAW], scl, uin.d[o + CLIP], uin.d[o + ANIM_T], code, uin.d[o + FLASH]);
		return;
	}

	int cpo = 32 + clan * 8;
	float c_speed = k.d[cpo];
	float c_regen = k.d[cpo + 1];
	float c_fear = k.d[cpo + 2];
	float c_dmg = k.d[cpo + 3];
	float c_spread = k.d[cpo + 5];
	float form = uin.d[o + FORM];
	float resolve = uin.d[o + RESOLVE];
	float flash = max(0.0, uin.d[o + FLASH] - dt * 4.0);

	// incoming melee (struck last frame)
	float dmg = float(acc_read.d[i]) / DMG_FIXED;
	acc_read.d[i] = 0u;
	float shaken = resolve < P_SHAKEN_BELOW ? P_SHAKEN_MULT : 1.0;
	if (dmg > 0.0) {
		form -= dmg * shaken;
		resolve -= dmg * P_HIT_RESOLVE_K;
		flash = 1.0;
	}

	// hit spheres
	for (uint s = 0u; s < pc.sphere_count; s++) {
		uint so = s * SPHERE_STRIDE;
		int tgt = int(sph.d[so + 7]);
		if (tgt >= 0 && uint(tgt) != i) {
			continue;
		}
		if ((int(sph.d[so + 6]) & (1 << clan)) == 0) {
			continue;
		}
		float dx = px - sph.d[so];
		float dz = pz - sph.d[so + 2];
		float r = sph.d[so + 3];
		float d = sqrt(dx * dx + dz * dz);
		if (d > r) {
			continue;
		}
		float kk = 1.0 - sph.d[so + 8] * d / max(r, 0.001);
		float fm = (int(sph.d[so + 9]) & SPH_SCARE) != 0 ? c_fear : 1.0;
		float fd = sph.d[so + 4] * kk;
		if (fd > 0.0) {
			form -= fd * shaken;
			resolve -= fd * P_HIT_RESOLVE_K;
			flash = 1.0;
		}
		resolve -= sph.d[so + 5] * kk * fm;
	}

	// neighbours
	float sep_r = P_SEP_RADIUS;
	float sep2 = sep_r * sep_r;
	float fear2 = P_FEAR_RADIUS * P_FEAR_RADIUS;
	float sepx = 0.0;
	float sepz = 0.0;
	int best = -1;
	float best_d2 = P_ENGAGE * P_ENGAGE;
	int n_rout = 0;
	int n_new_rout = 0;
	int n_new_scatter = 0;
	int n_allies = 0;
	int n_close = 0;
	int gcx = clamp(int(px / P_CELL_M), 0, int(pc.grid_w) - 1);
	int gcz = clamp(int(pz / P_CELL_M), 0, int(pc.grid_h) - 1);
	uint cap = P_CELL_CAP;
	for (int cz = max(0, gcz - 1); cz < min(int(pc.grid_h), gcz + 2); cz++) {
		for (int cx = max(0, gcx - 1); cx < min(int(pc.grid_w), gcx + 2); cx++) {
			uint gc = uint(cx) + pc.grid_w * uint(cz);
			uint cnt = min(grid_count.d[gc], cap);
			for (uint k2 = 0u; k2 < cnt; k2++) {
				uint j = grid_items.d[gc * cap + k2];
				if (j == i) {
					continue;
				}
				uint oj = j * STRIDE;
				int sj = int(uin.d[oj + STATE]);
				float dx2 = px - uin.d[oj + PX];
				float dz2 = pz - uin.d[oj + PZ];
				float d2 = dx2 * dx2 + dz2 * dz2;
				if (sj != S_SCATTERED && d2 < sep2) {
					n_close += 1;
					if (d2 > 1e-6) {
						float dd = sqrt(d2);
						float push = (sep_r - dd) / sep_r / dd;
						sepx += dx2 * push;
						sepz += dz2 * push;
					} else {
						float a = (uin.d[o + SEED] - uin.d[oj + SEED]) * 40.0;
						sepx += cos(a);
						sepz += sin(a);
					}
				}
				if (int(uin.d[oj + CLAN]) != clan) {
					if (sj == S_FIGHT && d2 < best_d2) {
						best_d2 = d2;
						best = int(j);
					}
				} else if (d2 < fear2) {
					if (sj == S_ROUT) {
						n_rout += 1;
						n_allies += 1;
						if (uin.d[oj + STATE_T] == 0.0) {
							n_new_rout += 1;
						}
					} else if (sj == S_SCATTERED) {
						if (uin.d[oj + STATE_T] == 0.0) {
							n_new_scatter += 1;
							n_allies += 1;
						}
					} else {
						n_allies += 1;
					}
				}
			}
		}
	}

	float inv_allies = 1.0 / max(1.0, float(n_allies));
	float fear_hit = (float(n_rout) * P_ROUT_DRAIN * dt + float(n_new_rout) * P_ROUT_SHOCK + float(n_new_scatter) * P_SCATTER_SHOCK) * inv_allies * c_spread;
	resolve -= fear_hit;
	if (n_rout == 0 && dmg <= 0.0 && fear_hit <= 0.0 && best < 0) {
		resolve = min(P_RESOLVE, resolve + (P_REGEN + c_regen) * dt);
	}
	int new_state = state;
	float state_t = uin.d[o + STATE_T] + dt;
	if (form <= 0.0) {
		form = 0.0;
		new_state = S_SCATTERED;
		state_t = 0.0;
		atomicAdd(summary.d[SUM_SCATTERS + clan], 1u);
	} else if (resolve <= 0.0 && state == S_FIGHT) {
		resolve = 0.0;
		new_state = S_ROUT;
		state_t = 0.0;
		atomicAdd(summary.d[SUM_ROUTS + clan], 1u);
	}
	resolve = max(resolve, 0.0);

	// movement
	float vx = uin.d[o + VX];
	float vz = uin.d[o + VZ];
	float yaw = uin.d[o + YAW];
	float attack_cd = uin.d[o + ATTACK_CD] - dt;
	float anim_t = uin.d[o + ANIM_T];
	int clip = int(uin.d[o + CLIP]);
	int strike = int(uin.d[o + STRIKE]);
	int target = -1;
	float want_x = 0.0;
	float want_z = 0.0;
	float face_x = 0.0;
	float face_z = 0.0;
	int c = terr_cell(px, pz);
	bool in_water = (flags.d[c] & T_WATER) != 0;
	uint cells = pc.terr_w * pc.terr_h;
	if (new_state == S_FIGHT) {
		if (best >= 0) {
			uint ob = uint(best) * STRIDE;
			float tx = uin.d[ob + PX] - px;
			float tz = uin.d[ob + PZ] - pz;
			float td = sqrt(tx * tx + tz * tz);
			target = best;
			face_x = tx;
			face_z = tz;
			if (td <= P_REACH) {
				if (attack_cd <= 0.0 && strike == 0) {
					attack_cd = P_ATTACK_CD * (0.8 + 0.4 * uin.d[o + SEED]);
					strike = best + 1;
					clip = CLIP_ATTACK;
					anim_t = 0.0;
				}
			} else {
				float sp = P_SPEED * c_speed;
				want_x = tx / td * sp;
				want_z = tz / td * sp;
			}
		} else {
			uint fo = (uint(clan * 2) * cells + uint(c)) * 2u;
			float sp2 = P_SPEED * c_speed;
			want_x = flow.d[fo] * sp2;
			want_z = flow.d[fo + 1u] * sp2;
		}
	} else if (new_state == S_ROUT) {
		uint fo = (uint(clan * 2 + 1) * cells + uint(c)) * 2u;
		want_x = flow.d[fo] * P_FLEE_SPEED;
		want_z = flow.d[fo + 1u] * P_FLEE_SPEED;
		strike = 0;
	} else {
		strike = 0;
	}
	// the pending blow lands at the strike point of the attack clip
	if (strike > 0 && clip == CLIP_ATTACK && anim_t + dt >= P_STRIKE_AT && anim_t < P_STRIKE_AT) {
		uint tj = uint(strike - 1);
		uint otj = tj * STRIDE;
		float sx = uin.d[otj + PX] - px;
		float sz = uin.d[otj + PZ] - pz;
		int st = int(uin.d[otj + STATE]);
		float rr = P_REACH * 1.3;
		if (st == S_FIGHT && sx * sx + sz * sz <= rr * rr) {
			atomicAdd(acc_write.d[tj], uint(P_ATTACK_DMG * c_dmg * DMG_FIXED + 0.5));
		}
		strike = 0;
	}
	if (clip == CLIP_ATTACK && anim_t >= P_ATTACK_CLIP) {
		strike = 0;
	}
	// crowd pressure: a packed unit stops pushing forward instead of crushing into the ones ahead
	float press = clamp(1.0 - max(0.0, float(n_close) - P_PRESS_FREE) * P_PRESS_K, 0.15, 1.0);
	want_x *= press;
	want_z *= press;
	float mult = in_water ? P_WADE_MULT : 1.0;
	float tvx = (want_x + sepx * P_SEP_STRENGTH) * mult;
	float tvz = (want_z + sepz * P_SEP_STRENGTH) * mult;
	float a2 = min(1.0, P_ACCEL * dt);
	vx += (tvx - vx) * a2;
	vz += (tvz - vz) * a2;
	float nx = px + vx * dt;
	float nz = pz + vz * dt;
	if (!passable_at(nx, nz, clan)) {
		if (passable_at(nx, pz, clan)) {
			nz = pz;
			vz = 0.0;
		} else if (passable_at(px, nz, clan)) {
			nx = px;
			vx = 0.0;
		} else {
			nx = px;
			nz = pz;
			vx = 0.0;
			vz = 0.0;
		}
	}
	int nc = terr_cell(nx, nz);
	float py = heights.d[nc];
	if ((flags.d[nc] & T_WATER) != 0) {
		py -= P_WADE_SINK;
	}
	if (new_state == S_ROUT && (flags.d[nc] & (T_HOME0 << clan)) != 0) {
		new_state = S_LEFT;
	}
	// facing and animation
	float spd = sqrt(vx * vx + vz * vz);
	if (face_x != 0.0 || face_z != 0.0) {
		yaw = lerp_angle_g(yaw, atan(face_x, face_z), min(1.0, dt * 10.0));
	} else if (spd > 0.2) {
		yaw = lerp_angle_g(yaw, atan(vx, vz), min(1.0, dt * 8.0));
	}
	if (new_state == S_ROUT) {
		if (clip != CLIP_FLEE) {
			clip = CLIP_FLEE;
			anim_t = 0.0;
		}
		anim_t += dt * max(0.6, spd / P_FLEE_SPEED);
	} else if (clip == CLIP_ATTACK && anim_t < P_ATTACK_CLIP) {
		anim_t += dt;
	} else {
		int want_clip = spd > 0.35 ? CLIP_WALK : CLIP_IDLE;
		if (want_clip != clip) {
			clip = want_clip;
			anim_t = uin.d[o + SEED];
		}
		anim_t += dt * (clip == CLIP_WALK ? max(0.5, spd / P_SPEED) : 1.0);
	}
	yaw = wrap_pi(yaw);
	uout.d[o + PX] = nx;
	uout.d[o + PZ] = nz;
	uout.d[o + VX] = vx;
	uout.d[o + VZ] = vz;
	uout.d[o + FORM] = form;
	uout.d[o + RESOLVE] = resolve;
	uout.d[o + CLAN] = float(clan);
	uout.d[o + STATE] = float(new_state);
	uout.d[o + ATTACK_CD] = max(attack_cd, -1.0);
	uout.d[o + ANIM_T] = anim_t;
	uout.d[o + YAW] = yaw;
	uout.d[o + PY] = py;
	uout.d[o + TARGET] = float(target);
	uout.d[o + STATE_T] = state_t;
	uout.d[o + FLASH] = flash;
	uout.d[o + SEED] = uin.d[o + SEED];
	uout.d[o + CLIP] = float(clip);
	uout.d[o + STRIKE] = float(strike);
	uout.d[o + 18] = uin.d[o + 18];
	uout.d[o + 19] = uin.d[o + 19];

	if (new_state == S_FIGHT) {
		uint fl = nx < pc.mid_x ? 0u : 1u;
		atomicAdd(summary.d[SUM_FLANK + clan * 2 + int(fl)], 1u);
		atomicAdd(summary.d[SUM_FLANK_RES + clan * 2 + int(fl)], uint(resolve * 16.0));
		if (target >= 0 && best_d2 <= P_REACH * P_REACH * 1.2) {
			atomicAdd(summary.d[SUM_ENGAGED + clan], 1u);
			int fo = SUM_FRONT + (clan * 2 + int(fl)) * 3;
			atomicAdd(summary.d[fo], 1u);
			atomicAdd(summary.d[fo + 1], uint(nx * 4.0));
			atomicAdd(summary.d[fo + 2], uint(nz * 4.0));
		}
	}
	float scl = 1.0;
	float code = 0.0;
	if (new_state == S_LEFT) {
		scl = 0.0;
	} else if (new_state == S_SCATTERED) {
		scl = 1.0;
		code = 1.0;
	} else if (new_state == S_ROUT) {
		code = 0.5;
	}
	write_mm(i, clan, nx, py, nz, yaw, scl, float(clip), anim_t, code, flash);
}

void main() {
	uint gid = gl_GlobalInvocationID.x;
	if (pc.mode == 0u) {
		pass_clear(gid);
	} else if (pc.mode == 1u) {
		pass_bin(gid);
	} else {
		pass_step(gid);
	}
}
