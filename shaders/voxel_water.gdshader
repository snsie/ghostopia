shader_type spatial;
render_mode blend_mix, depth_draw_always, cull_back, diffuse_burley, specular_schlick_ggx;
#include "res://shaders/voxel_common.gdshaderinc"

uniform sampler2DArray albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform vec3 tint : source_color = vec3(0.35, 0.65, 0.95);
uniform float flow_speed = 0.35;

varying float layer;
varying vec3 wpos;

void vertex() {
	layer = UV2.x;
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = UV + vec2(0.0, -TIME * flow_speed);
	vec2 uv2 = UV * 1.3 + vec2(0.17, -TIME * flow_speed * 0.6);
	vec3 a = texture(albedo_tex, vec3(fract(uv), layer)).rgb;
	vec3 b = texture(albedo_tex, vec3(fract(uv2), layer)).rgb;
	vec3 c = mix(a, b, 0.5) * mix(vec3(1.0), tint, 0.35);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	float f = fade_amount(wpos);
	ALBEDO = desaturate(c, f * 0.8);
	ALPHA = mix(0.72, 0.92, fres);
	ROUGHNESS = 0.08;
	SPECULAR = 0.6;
	float spark = pow(max(b.b - 0.6, 0.0) * 2.5, 3.0);
	EMISSION = tint * (0.12 + spark * 0.8);
}
