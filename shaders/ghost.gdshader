// The ghost's sheet: translucent white with an ice-blue fresnel rim; `manifest` makes it opaque and
// bright (the living can see it), `phase` adds a shimmer while inside a wall, `hurt` flashes it.
shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, diffuse_toon, specular_toon;

uniform vec3 body : source_color = vec3(0.84, 0.89, 0.98);
uniform vec3 rim : source_color = vec3(0.62, 0.88, 1.0);
uniform float alpha = 0.78;
uniform float manifest = 0.0;
uniform float phase = 0.0;
uniform float hurt = 0.0;
uniform float scatter = 0.0;

void fragment() {
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.0);
	vec3 c = mix(body, rim, f * 0.6);
	c = mix(c, vec3(1.0, 0.45, 0.35), hurt * 0.6);
	ALBEDO = c;
	float shimmer = phase * (0.5 + 0.5 * sin(TIME * 12.0 + FRAGCOORD.y * 0.15));
	ALPHA = clamp(mix(alpha, 1.0, manifest) - shimmer * 0.35 - scatter, 0.0, 1.0);
	EMISSION = rim * (0.08 + f * 0.9 + manifest * 0.9) + vec3(0.6, 0.4, 1.0) * shimmer * 0.4;
	ROUGHNESS = 0.35;
}
