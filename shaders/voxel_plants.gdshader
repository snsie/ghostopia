shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley;
#include "res://shaders/voxel_common.gdshaderinc"

uniform sampler2DArray albedo_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform float sway = 0.07;

varying float layer;
varying vec3 wpos;

void vertex() {
	layer = UV2.x;
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float t = TIME * 1.4 + wpos.x * 0.35 + wpos.z * 0.27;
	VERTEX.x += sin(t) * sway * COLOR.a;
	VERTEX.z += cos(t * 0.8) * sway * 0.6 * COLOR.a;
}

void fragment() {
	vec4 a = texture(albedo_tex, vec3(UV, layer));
	if (a.a < 0.45) { discard; }
	float f = fade_amount(wpos);
	ALBEDO = desaturate(a.rgb * COLOR.rgb, f * 0.85);
	ROUGHNESS = 0.95;
	SPECULAR = 0.1;
	BACKLIGHT = vec3(0.25);
}
