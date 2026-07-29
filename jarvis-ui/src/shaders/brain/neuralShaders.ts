/* Inline GLSL shaders — avoids vite-plugin-glsl incompatibility with Vite 6 */

export const neuralVert = `
uniform float uTime;
uniform float uActivity;
uniform float uPulsePhase;
uniform vec2 uMouse;
uniform float uMouseActive;

attribute float aSize;
attribute float aRandom;
attribute vec3 aColor;
attribute float aEnergy;

varying vec3 vColor;
varying float vEnergy;
varying float vAlpha;
varying float vMouseDist;

void main() {
  vec3 pos = position;

  float pulse = sin(uTime * 0.8 + uPulsePhase + aRandom * 6.28) * 0.5 + 0.5;
  float expand = 1.0 + pulse * 0.15 * uActivity;
  pos *= expand;

  float oscX = sin(uTime * 2.0 + aRandom * 100.0) * 0.02;
  float oscY = cos(uTime * 1.7 + aRandom * 80.0) * 0.02;
  float oscZ = sin(uTime * 1.3 + aRandom * 60.0) * 0.02;
  pos += vec3(oscX, oscY, oscZ);

  // Mouse interaction: push particles away from cursor ray
  float mouseInfluence = uMouseActive * (1.0 - pulse);
  vec3 mouseDir = normalize(vec3(uMouse.x * 6.0, uMouse.y * 4.0, 0.0) - pos);
  float mouseDist = length(vec3(uMouse.x * 6.0, uMouse.y * 4.0, 0.0) - pos);
  float mouseAttract = exp(-mouseDist * 0.8) * mouseInfluence * 0.3;
  pos += mouseDir * mouseAttract;

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_PointSize = aSize * (300.0 / -mvPosition.z);
  gl_PointSize *= (0.8 + 0.4 * sin(uTime * 2.0 + aRandom * 50.0));
  gl_PointSize *= (1.0 + mouseAttract * 3.0);
  gl_Position = projectionMatrix * mvPosition;

  vColor = aColor;
  vEnergy = aEnergy;
  vAlpha = 0.4 + 0.6 * (0.5 + 0.5 * sin(uTime * 1.5 + aRandom * 30.0));
  vMouseDist = mouseDist;
}
`

export const neuralFrag = `
uniform float uTime;
uniform float uMouseActive;

varying vec3 vColor;
varying float vEnergy;
varying float vAlpha;
varying float vMouseDist;

void main() {
  vec2 center = gl_PointCoord - 0.5;
  float dist = length(center);

  float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
  alpha *= alpha;

  float core = exp(-dist * 12.0);
  float glow = exp(-dist * 4.0) * 0.6;

  // Mouse proximity boosts brightness
  float mouseGlow = exp(-vMouseDist * 0.6) * uMouseActive;
  float energyBoost = vEnergy + mouseGlow * 0.5;

  vec3 color = vColor * (1.0 + core * 2.0 + glow * 0.5 + mouseGlow);
  color *= (0.8 + 0.4 * energyBoost);

  float hdr = 1.0 + core * 3.0 + glow + mouseGlow * 2.0;
  gl_FragColor = vec4(color * hdr, alpha * vAlpha * (0.8 + mouseGlow * 0.4));
}
`

export const connectionVert = `
uniform float uTime;
uniform float uActivity;
uniform float uPulsePhase;
uniform vec2 uMouse;
uniform float uMouseActive;

attribute float aEnergy;
attribute float aRandom;

varying float vEnergy;
varying float vRandom;
varying float vPulse;
varying float vAlpha;
varying float vMouseDist;

void main() {
  vec3 pos = position;

  float oscStrength = 0.015 + uActivity * 0.02;
  float oscX = sin(uTime * 1.2 + aRandom * 100.0 + pos.y * 2.0) * oscStrength;
  float oscY = cos(uTime * 0.9 + aRandom * 80.0 + pos.x * 2.0) * oscStrength;
  float oscZ = sin(uTime * 1.1 + aRandom * 60.0 + pos.z * 2.0) * oscStrength;
  pos += vec3(oscX, oscY, oscZ);

  // Mouse interaction: brightness proximity
  float mouseDist = length(vec3(uMouse.x * 6.0, uMouse.y * 4.0, 0.0) - pos);

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  float wave = sin(uTime * 2.0 + position.x * 3.0 + position.y * 2.0 + position.z * 1.5) * 0.5 + 0.5;
  float pulse = sin(uTime * 0.8 + uPulsePhase + aRandom * 6.28) * 0.5 + 0.5;

  float mouseBoost = exp(-mouseDist * 0.5) * uMouseActive;
  vEnergy = aEnergy * (0.6 + 0.4 * wave) + mouseBoost * 0.4;
  vRandom = aRandom;
  vPulse = pulse;
  vAlpha = (0.3 + 0.7 * uActivity) * (0.7 + 0.3 * wave) + mouseBoost * 0.3;
  vMouseDist = mouseDist;
}
`

export const connectionFrag = `
uniform float uTime;
uniform float uActivity;
uniform float uMouseActive;

varying float vEnergy;
varying float vRandom;
varying float vPulse;
varying float vAlpha;
varying float vMouseDist;

void main() {
  float hue = 0.58 + vEnergy * 0.12 + vPulse * 0.05;
  float saturation = 0.7 + vEnergy * 0.3;
  float lightness = 0.3 + vEnergy * 0.5 + vPulse * 0.2;

  // Mouse proximity shifts color toward white-hot
  float mouseGlow = exp(-vMouseDist * 0.4) * uMouseActive;
  hue += mouseGlow * 0.05;
  lightness += mouseGlow * 0.4;
  saturation -= mouseGlow * 0.3;

  vec3 color;
  float c = (1.0 - abs(2.0 * lightness - 1.0)) * saturation;
  float x = c * (1.0 - abs(mod(hue * 6.0, 2.0) - 1.0));
  float m = lightness - c * 0.5;

  if (hue < 0.167) color = vec3(c, x, 0.0);
  else if (hue < 0.333) color = vec3(x, c, 0.0);
  else if (hue < 0.5) color = vec3(0.0, c, x);
  else if (hue < 0.667) color = vec3(0.0, x, c);
  else if (hue < 0.833) color = vec3(x, 0.0, c);
  else color = vec3(c, 0.0, x);
  color += m;

  float hdrIntensity = 1.0 + vEnergy * 2.0 + vPulse * 1.5 + mouseGlow * 3.0;
  float energyWave = pow(vEnergy, 4.0);
  vec3 energyGlow = vec3(0.3, 0.6, 1.0) * energyWave * 3.0;
  energyGlow += vec3(0.5, 0.8, 1.0) * mouseGlow * 4.0;

  vec3 finalColor = color * hdrIntensity + energyGlow;
  float hdrSpike = step(0.8, vEnergy) * vEnergy * 2.0 + mouseGlow * 2.0;
  finalColor += vec3(0.5, 0.8, 1.0) * hdrSpike;

  float alpha = vAlpha * (0.6 + 0.4 * (vEnergy + vPulse * 0.3 + mouseGlow));
  gl_FragColor = vec4(finalColor, alpha);
}
`
