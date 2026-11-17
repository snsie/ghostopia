shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;
#include "res://shaders/voxel_common.gdshaderinc"

uniform sampler2DArray albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2DArray emission_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float emission_strength = 1.0;
uniform float normal_strength = 0.7;

varying float layer;
varying float emissive;
varying vec3 wpos;

void vertex() {
	layer = UV2.x;
	emissive = UV2.y;
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec4 a = texture(albedo_tex, vec3(UV, layer));
	if (a.a < 0.5) { discard; }
	vec3 col = a.rgb * COLOR.rgb;
	float f = fade_amount(wpos);
	vec3 emis = vec3(0.0);
	if (emissive > 0.5) {
		emis = texture(emission_tex, vec3(UV, layer)).rgb * emission_strength * 2.0;
	}
	if (f > 0.0) {
		col = desaturate(col, f * 0.85) * (1.0 - 0.25 * f);
		vec2 e = abs(UV - 0.5) * 2.0;
		float edge = smoothstep(0.78, 0.98, max(e.x, e.y));
		vec3 cell = floor(wpos - NORMAL * 0.01);
		float flick = step(0.55, fract(hash13(cell) * 7.0 + TIME * (0.6 + hash13(cell + 3.0))));
		emis += vec3(0.55, 0.35, 1.0) * edge * flick * f * 0.9;
		col *= 1.0 - edge * f * 0.5;
	}
	ALBEDO = col;
	ROUGHNESS = 0.92;
	SPECULAR = 0.2;
	NORMAL_MAP = texture(normal_tex, vec3(UV, layer)).rgb;
	NORMAL_MAP_DEPTH = normal_strength;
	EMISSION = emis;
}
