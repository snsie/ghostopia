// Screen-space ink outline from depth discontinuities (props and characters get the hand-inked look
// the voxel tiles already bake). Drawn on a full-screen quad in front of the camera.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, depth_test_disabled, cull_disabled, fog_disabled;

uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform vec3 ink : source_color = vec3(0.06, 0.04, 0.12);
uniform float strength = 0.75;
uniform float max_dist = 45.0;

void vertex() {
	POSITION = vec4(VERTEX.xy * 2.0, 1.0, 1.0);
}

float lin(vec2 uv, mat4 inv_proj) {
	float d = texture(depth_tex, uv).r;
	vec4 v = inv_proj * vec4(uv * 2.0 - 1.0, d, 1.0);
	return -v.z / v.w;
}

void fragment() {
	vec2 px = 1.0 / VIEWPORT_SIZE;
	float c = lin(SCREEN_UV, INV_PROJECTION_MATRIX);
	float e = 0.0;
	float l = lin(SCREEN_UV + vec2(-px.x, 0.0), INV_PROJECTION_MATRIX);
	float r = lin(SCREEN_UV + vec2(px.x, 0.0), INV_PROJECTION_MATRIX);
	float u = lin(SCREEN_UV + vec2(0.0, -px.y), INV_PROJECTION_MATRIX);
	float d = lin(SCREEN_UV + vec2(0.0, px.y), INV_PROJECTION_MATRIX);
	float lap = abs(l + r + u + d - 4.0 * c);
	e = smoothstep(0.04 * c, 0.16 * c, lap);
	e *= 1.0 - smoothstep(max_dist * 0.5, max_dist, c);
	ALBEDO = ink;
	ALPHA = e * strength;
}
