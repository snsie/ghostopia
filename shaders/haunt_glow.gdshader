// Haunt glow on HAUNT_* shells: additive fresnel rim, violet -> ice-blue, gently pulsing.
shader_type spatial;
render_mode blend_add, unshaded, cull_back, depth_draw_never, shadows_disabled;

uniform vec3 inner : source_color = vec3(0.62, 0.38, 1.0);
uniform vec3 outer : source_color = vec3(0.62, 0.92, 1.0);
uniform float strength = 1.6;

void fragment() {
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.2);
	float pulse = 0.75 + 0.25 * sin(TIME * 5.0);
	ALBEDO = mix(inner, outer, f) * (0.25 + f * 1.4) * strength * pulse;
}
