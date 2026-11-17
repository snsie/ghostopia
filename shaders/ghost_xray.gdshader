// Second pass of the ghost sheet: a faint ice-blue silhouette drawn through walls, so the ghost
// stays readable while phasing through blocks (stronger while phasing).
shader_type spatial;
render_mode unshaded, blend_add, depth_test_disabled, depth_draw_never, cull_back, shadows_disabled;

uniform float strength = 0.35;

void fragment() {
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 1.5);
	ALBEDO = vec3(0.45, 0.75, 1.0) * (0.15 + f * 0.6) * strength;
}
