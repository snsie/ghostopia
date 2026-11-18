// Custom eye shader for the ghost: supports eye styles (classic, hollow, star, heart, slit, spiral,
// glowing, button) without changing the underlying mesh, while keeping blend shape expressions intact.
shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, diffuse_toon, specular_toon;

uniform vec3 eye_col : source_color = vec3(0.10, 0.06, 0.15);
uniform float eye_glow = 0.0;
uniform int eye_style = 0; // 0 classic, 1 hollow, 2 star, 3 heart, 4 slit, 5 spiral, 6 glowing, 7 button
varying vec3 local_p;

void vertex() {
	local_p = VERTEX;
}

void fragment() {
	// Left and right eyes sit near x = +-0.046, y = 0.44 in character space
	float cx = local_p.x >= 0.0 ? 0.046 : -0.046;
	vec2 uv = vec2((local_p.x - cx) / 0.022, (local_p.y - 0.44) / 0.032);
	float r = length(uv);
	float a = atan(uv.y, uv.x);

	vec3 col = eye_col;
	float emit = eye_glow;
	vec3 dark = vec3(0.05, 0.03, 0.09);
	vec3 bright = mix(eye_col, vec3(1.0, 0.98, 0.95), 0.45);

	if (eye_style == 1) {
		// Hollow Ring
		float ring = smoothstep(0.32, 0.48, r);
		col = mix(dark, bright, ring);
		emit = max(emit, ring * 1.4);
	} else if (eye_style == 2) {
		// Starry Sparkle
		float star = 1.0 - smoothstep(0.28, 0.48, abs(uv.x) * 1.1 + abs(uv.y) * 0.85);
		star = max(star, 1.0 - smoothstep(0.14, 0.24, r));
		col = mix(dark, bright, star);
		emit = max(emit, star * 1.6);
	} else if (eye_style == 3) {
		// Heart Pupil
		vec2 p = vec2(uv.x * 1.35, (uv.y - 0.12) * 1.35);
		p.y -= sqrt(max(abs(p.x), 0.001)) * 0.55;
		float heart = 1.0 - smoothstep(0.38, 0.52, length(p));
		col = mix(dark, bright, heart);
		emit = max(emit, heart * 1.5);
	} else if (eye_style == 4) {
		// Cat Slit
		float slit = 1.0 - smoothstep(0.16, 0.28, abs(uv.x) + abs(uv.y) * 0.22);
		col = mix(bright * 0.7, dark, slit);
		emit = max(emit, (1.0 - slit) * 1.3);
	} else if (eye_style == 5) {
		// Hypno Spiral
		float sp = 0.5 + 0.5 * sin(r * 18.0 - a * 2.0 - TIME * 4.0);
		float mask = smoothstep(0.35, 0.65, sp);
		col = mix(dark, bright, mask);
		emit = max(emit, mask * 1.3);
	} else if (eye_style == 6) {
		// Radiant Orbs
		float core = 1.0 - smoothstep(0.0, 0.85, r);
		col = mix(eye_col, vec3(1.0), core * 0.55);
		emit = max(emit, 1.5 + core * 1.2);
	} else if (eye_style == 7) {
		// Stitched Button
		float rim_ring = smoothstep(0.58, 0.68, r) - smoothstep(0.78, 0.88, r);
		float cross_x = (1.0 - smoothstep(0.07, 0.12, abs(uv.x - uv.y))) + (1.0 - smoothstep(0.07, 0.12, abs(uv.x + uv.y)));
		cross_x *= 1.0 - smoothstep(0.38, 0.45, r);
		float m = clamp(rim_ring + cross_x, 0.0, 1.0);
		col = mix(dark * 1.2, bright, m);
		emit = max(emit, m * 1.1);
	}

	ALBEDO = col;
	EMISSION = col * emit;
	ROUGHNESS = 0.15;
}
