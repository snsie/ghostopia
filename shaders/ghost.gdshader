// The ghost's sheet: translucent white with an ice-blue fresnel rim; `manifest` makes it opaque and
// bright (the living can see it), `phase` adds a shimmer while inside a wall, `hurt` flashes it.
// Supports appearance customization: gradients, procedural patterns, shader finishes, and pulse FX.
shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, diffuse_toon, specular_toon;

uniform vec3 body : source_color = vec3(0.84, 0.89, 0.98);
uniform vec3 rim : source_color = vec3(0.62, 0.88, 1.0);
uniform vec3 secondary : source_color = vec3(0.45, 0.35, 0.85);
uniform vec3 pattern_col : source_color = vec3(0.95, 0.85, 1.0);
uniform float alpha = 0.78;
uniform float manifest = 0.0;
uniform float phase = 0.0;
uniform float hurt = 0.0;
uniform float scatter = 0.0;

uniform int gradient_mode = 0;      // 0 none, 1 bottom_up, 2 top_down, 3 core_radial, 4 split_band, 5 horizon_glow
uniform float gradient_strength = 0.65;
uniform int pattern_mode = 0;       // 0 none, 1 stripes, 2 rings, 3 polka, 4 stars, 5 swirls, 6 stitches, 7 runes, 8 checker
uniform float pattern_scale = 1.0;
uniform float pattern_strength = 0.45;
uniform int finish_mode = 0;        // 0 classic, 1 holographic, 2 phantom_glitch, 3 starfield, 4 plasma, 5 embers, 6 crystalline, 7 shadow_ink
uniform float pulse_speed = 0.0;
uniform float glow_boost = 0.0;

uniform float drift_rank = 0.0;
uniform float resilience_rank = 0.0;
varying float height;
varying vec3 local_pos;

float hash21(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

vec3 hsv2rgb(vec3 c) {
	vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
	vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
	return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void vertex() {
	height = VERTEX.y;
	local_pos = VERTEX;
	float tail = 1.0 - smoothstep(0.02, 0.32, height);
	VERTEX.z += 0.045 * drift_rank * tail;
	if (finish_mode == 2) {
		float glitch = step(0.92, sin(TIME * 19.0 + height * 28.0));
		VERTEX.x += glitch * 0.018 * sin(TIME * 43.0);
	}
}

void fragment() {
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.0);
	float h_norm = clamp(height / 0.6, 0.0, 1.0);
	float ang = atan(local_pos.x, local_pos.z);

	// 1. Base & Gradient
	vec3 base_c = body;
	if (gradient_mode == 1) {
		base_c = mix(secondary, body, smoothstep(0.05, 0.85, h_norm) * gradient_strength + (1.0 - gradient_strength));
	} else if (gradient_mode == 2) {
		base_c = mix(body, secondary, smoothstep(0.15, 0.9, h_norm) * gradient_strength);
	} else if (gradient_mode == 3) {
		base_c = mix(secondary, body, clamp(f * 1.5, 0.0, 1.0) * gradient_strength + (1.0 - gradient_strength));
	} else if (gradient_mode == 4) {
		float band = smoothstep(0.32, 0.36, h_norm) - smoothstep(0.56, 0.60, h_norm);
		base_c = mix(body, secondary, band * gradient_strength);
	} else if (gradient_mode == 5) {
		float wave = 0.5 + 0.5 * sin(h_norm * 9.0 - TIME * 2.0 + ang * 2.0);
		base_c = mix(body, secondary, wave * gradient_strength);
	}

	// 2. Procedural Pattern
	float pat = 0.0;
	float sc = max(0.25, pattern_scale);
	if (pattern_mode == 1) {
		pat = smoothstep(0.3, 0.5, 0.5 + 0.5 * sin(ang * floor(8.0 * sc)));
	} else if (pattern_mode == 2) {
		pat = smoothstep(0.35, 0.55, 0.5 + 0.5 * sin(h_norm * 28.0 * sc));
	} else if (pattern_mode == 3) {
		vec2 uv_p = vec2(ang * 2.2 * sc, h_norm * 7.0 * sc);
		vec2 gv = fract(uv_p) - 0.5;
		pat = 1.0 - smoothstep(0.22, 0.28, length(gv));
	} else if (pattern_mode == 4) {
		vec2 uv_s = vec2(ang * 2.6 * sc, h_norm * 8.0 * sc);
		vec2 id = floor(uv_s);
		vec2 gv = fract(uv_s) - 0.5;
		float rnd = hash21(id);
		if (rnd > 0.35) {
			float d1 = abs(gv.x) + abs(gv.y);
			float d2 = length(gv);
			pat = (1.0 - smoothstep(0.18, 0.24, d1)) * (0.65 + 0.35 * sin(TIME * 3.5 + rnd * 12.0));
			pat = max(pat, 1.0 - smoothstep(0.07, 0.11, d2));
		}
	} else if (pattern_mode == 5) {
		pat = smoothstep(0.35, 0.65, 0.5 + 0.5 * sin(ang * 4.0 + h_norm * 18.0 * sc - TIME * 1.5));
	} else if (pattern_mode == 6) {
		float seam = 1.0 - smoothstep(0.03, 0.055, abs(sin(ang * 2.0 + h_norm * 1.5)));
		float cross_tick = step(0.55, fract(h_norm * 18.0 * sc)) * (1.0 - smoothstep(0.11, 0.14, abs(sin(ang * 2.0 + h_norm * 1.5))));
		pat = clamp(seam + cross_tick, 0.0, 1.0);
	} else if (pattern_mode == 7) {
		vec2 uv_r = vec2(ang * 3.0 * sc, h_norm * 9.0 * sc);
		vec2 gv = abs(fract(uv_r) - 0.5);
		float ring = smoothstep(0.16, 0.2, max(gv.x, gv.y)) - smoothstep(0.24, 0.28, max(gv.x, gv.y));
		float core = 1.0 - smoothstep(0.06, 0.09, length(gv));
		pat = clamp(ring + core, 0.0, 1.0);
	} else if (pattern_mode == 8) {
		vec2 uv_c = floor(vec2(ang * 2.5 * sc, h_norm * 7.5 * sc));
		pat = mod(uv_c.x + uv_c.y, 2.0);
	}
	base_c = mix(base_c, pattern_col, pat * pattern_strength);

	// 3. Rim & Shader Finish
	vec3 c = mix(base_c, rim, f * 0.6);
	float extra_emit = glow_boost;
	float rough = 0.35;
	if (finish_mode == 1) {
		vec3 holo = hsv2rgb(vec3(fract(f * 1.3 + h_norm * 0.7 + TIME * 0.18), 0.55, 1.0));
		c = mix(c, holo, 0.42);
		extra_emit += 0.25;
		rough = 0.15;
	} else if (finish_mode == 2) {
		float scan = 0.5 + 0.5 * sin(FRAGCOORD.y * 0.6 + TIME * 16.0);
		c = mix(c, rim, scan * 0.32);
		extra_emit += scan * 0.35;
	} else if (finish_mode == 3) {
		vec2 st_uv = FRAGCOORD.xy * 0.045 + vec2(0.0, TIME * 0.35);
		float st = pow(hash21(floor(st_uv)), 18.0);
		c = mix(c * 0.55, vec3(1.0, 0.98, 0.9), st);
		extra_emit += st * 1.4;
	} else if (finish_mode == 4) {
		float pl = 0.5 + 0.5 * sin(h_norm * 14.0 - TIME * 4.5 + sin(ang * 3.0 + TIME * 2.0));
		c = mix(c, rim, pl * 0.45);
		extra_emit += pl * 0.45;
	} else if (finish_mode == 5) {
		float ember = (1.0 - smoothstep(0.0, 0.48, h_norm)) * (0.6 + 0.4 * sin(TIME * 6.0 + ang * 5.0));
		c = mix(c, vec3(1.0, 0.42, 0.12), ember * 0.75);
		extra_emit += ember * 0.85;
	} else if (finish_mode == 6) {
		float facet = floor(f * 5.0) / 5.0;
		c = mix(base_c, rim, facet * 0.85);
		rough = 0.08;
		extra_emit += facet * 0.3;
	} else if (finish_mode == 7) {
		float ink = smoothstep(0.32, 0.62, f);
		c = mix(base_c, vec3(0.05, 0.03, 0.12), ink * 0.82);
		rough = 0.65;
	}

	// 4. Gameplay overlays (hurt, evolution traits, phase, manifest, scatter)
	c = mix(c, vec3(1.0, 0.45, 0.35), hurt * 0.6);
	float tail = (1.0 - smoothstep(0.02, 0.32, height)) * clamp(drift_rank * 0.22, 0.0, 0.85);
	float mantle = smoothstep(0.28, 0.56, height) * clamp(resilience_rank * 0.25, 0.0, 0.9);
	c = mix(c, vec3(0.19, 0.88, 1.0), tail);
	c = mix(c, vec3(1.0, 0.64, 0.24), mantle);
	ALBEDO = c;
	float shimmer = phase * (0.5 + 0.5 * sin(TIME * 12.0 + FRAGCOORD.y * 0.15));
	float pulse = 1.0 + (pulse_speed > 0.01 ? 0.28 * sin(TIME * pulse_speed * 3.0) : 0.0);
	ALPHA = clamp(mix(alpha, 1.0, manifest) - shimmer * 0.35 - scatter, 0.0, 1.0);
	EMISSION = (rim * (0.08 + f * 0.9 + manifest * 0.9) + c * extra_emit) * pulse + vec3(0.6, 0.4, 1.0) * shimmer * 0.4;
	EMISSION += c * (tail + mantle) * 0.5;
	ROUGHNESS = rough;
}

