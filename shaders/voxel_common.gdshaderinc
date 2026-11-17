// Shared by the voxel shaders: per-area Remembrance fading (desaturate + flickering block edges).
uniform sampler2D remembrance_tex : filter_linear, repeat_disable;
uniform vec2 world_size = vec2(192.0, 192.0);
uniform float fading_below = 0.4;
uniform float faded_at = 0.1;

float fade_amount(vec3 wp) {
	float r = texture(remembrance_tex, wp.xz / world_size).r;
	return clamp((fading_below - r) / max(fading_below - faded_at, 0.001), 0.0, 1.0);
}

vec3 desaturate(vec3 c, float k) {
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	return mix(c, vec3(l) * vec3(0.92, 0.92, 1.0), k);
}

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}
