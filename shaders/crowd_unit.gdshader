// Battle prototype undead: plays a baked vertex-animation texture (blender/scripts/build_battle_units.py).
// Crowd units read (clip, time, state code, hit flash) from the MultiMesh custom data the crowd sim
// writes; near actors pass the same four values through the `actor_anim` instance uniform.
// State code: 0 fighting, 0.5 routing (pale, ghostly), 1..2 scattering (bursting into wisps).
// Vertex colour alpha 0 marks glowing parts (eyes, candle flames).
shader_type spatial;
render_mode cull_back, depth_draw_opaque;

uniform sampler2D vat : filter_nearest, repeat_disable;
uniform int frames = 1;
uniform vec4 clips[4];
uniform vec3 tint : source_color = vec3(1.0);
uniform bool use_instance_custom = true;
uniform vec3 rout_color : source_color = vec3(0.72, 0.86, 1.0);
uniform vec3 wisp_color : source_color = vec3(0.70, 0.90, 1.0);
uniform float glow_energy = 2.6;
instance uniform vec4 actor_anim = vec4(0.0, 0.0, 0.0, 0.0);

varying float v_code;
varying float v_flash;
varying vec3 v_local;

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

void vertex() {
	vec4 a = use_instance_custom ? INSTANCE_CUSTOM : actor_anim;
	int clip = clamp(int(a.x + 0.5), 0, 3);
	vec4 c = clips[clip];
	float fc = max(c.y, 1.0);
	float f = a.y * c.z;
	float f0;
	float f1;
	if (c.w > 0.5) {
		f = mod(f, fc);
		f0 = floor(f);
		f1 = mod(f0 + 1.0, fc);
	} else {
		f = clamp(f, 0.0, fc - 1.0);
		f0 = floor(f);
		f1 = min(f0 + 1.0, fc - 1.0);
	}
	float fr = f - f0;
	int r0 = int(c.x + f0);
	int r1 = int(c.x + f1);
	vec3 p0 = texelFetch(vat, ivec2(VERTEX_ID, r0), 0).xyz;
	vec3 p1 = texelFetch(vat, ivec2(VERTEX_ID, r1), 0).xyz;
	vec3 n0 = texelFetch(vat, ivec2(VERTEX_ID, frames + r0), 0).xyz;
	vec3 n1 = texelFetch(vat, ivec2(VERTEX_ID, frames + r1), 0).xyz;
	VERTEX = mix(p0, p1, fr);
	NORMAL = normalize(mix(n0, n1, fr));
	v_code = a.z;
	v_flash = a.w;
	v_local = VERTEX;
	if (v_code >= 1.0) {
		// scattering: drift upward and swell as it comes apart
		float k = v_code - 1.0;
		VERTEX.y += k * k * 0.6;
	}
}

void fragment() {
	vec3 base = COLOR.rgb * tint;
	float glow = 1.0 - COLOR.a;
	vec3 emit = base * glow * glow_energy;
	if (v_code >= 1.0) {
		float k = v_code - 1.0;
		float n = hash13(floor(v_local * 9.0) + 7.0);
		if (n < k * 1.15) {
			discard;
		}
		base = mix(base, wisp_color, 0.6 + 0.4 * k);
		emit += wisp_color * (0.8 + 1.6 * k);
	} else if (v_code > 0.25) {
		// routing: the colour drains out of them
		float l = dot(base, vec3(0.3, 0.59, 0.11));
		base = mix(vec3(l), rout_color, 0.6) * 1.1;
		emit += rout_color * 0.25;
	}
	emit += vec3(1.0, 0.95, 0.85) * v_flash * 0.9;
	ALBEDO = base;
	EMISSION = emit;
	ROUGHNESS = 0.85;
	RIM = 0.22;
	RIM_TINT = 0.3;
}
