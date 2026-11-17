// Cute-spooky sky: three-colour gradient (top, horizon, void below), stars and a huge soft moon
// disc at night (moon direction from the moon DirectionalLight).
shader_type sky;

uniform vec3 top_color : source_color = vec3(0.04, 0.04, 0.16);
uniform vec3 horizon_color : source_color = vec3(0.24, 0.23, 0.49);
uniform vec3 void_color : source_color = vec3(0.08, 0.04, 0.16);
uniform float stars = 1.0;
uniform float moon = 1.0;
uniform vec3 moon_dir = vec3(0.5, 0.6, -0.6);

float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

void sky() {
	vec3 d = normalize(EYEDIR);
	float h = d.y;
	vec3 c = h > 0.0 ? mix(horizon_color, top_color, pow(clamp(h, 0.0, 1.0), 0.55)) : mix(horizon_color, void_color, clamp(-h * 3.0, 0.0, 1.0));
	if (stars > 0.0 && h > 0.0) {
		vec3 g = floor(d * 180.0);
		float s = hash(g);
		float tw = 0.6 + 0.4 * sin(TIME * (1.0 + s * 3.0) + s * 40.0);
		c += vec3(0.9, 0.92, 1.0) * step(0.9965, s) * tw * stars * smoothstep(0.0, 0.25, h);
	}
	if (moon > 0.0) {
		float a = dot(d, normalize(moon_dir));
		float disc = smoothstep(0.9965, 0.9975, a);
		float halo = pow(max(a, 0.0), 60.0) * 0.5 + pow(max(a, 0.0), 8.0) * 0.12;
		vec3 mc = vec3(0.86, 0.9, 1.0);
		float crater = 0.85 + 0.15 * hash(floor(d * 900.0));
		c = mix(c, mc * crater * 1.6, disc * moon);
		c += vec3(0.55, 0.6, 1.0) * halo * moon;
	}
	COLOR = c;
}
