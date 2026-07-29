import{u as Y,a as A,j as t,d as H,w as F,y as J,A as Z,q as U,C as N}from"./r3f-BotC7k8I.js";import{a as n}from"./vendor-COGkcq7C.js";import{g as I,X as q,Y as O,Z as $,t as K,C as B,r as Q,H as L,I as w,_ as ee,$ as S,a0 as te,h as W,J as oe,e as ne,a1 as se}from"./three-y8ac1Ddt.js";import{u as C}from"./index-DPBYpb39.js";function re(){const{camera:e}=Y(),o=n.useRef(0),c=n.useRef(0),i=n.useRef(new I(0,0,0)),s=n.useRef(new I),r=n.useRef(null),a=n.useRef(0),u=n.useRef(0);return A(({gl:g},d)=>{const l=g.domElement,v=(f,G,V,X)=>{if(V)r.current={x:f,y:G};else if(X)r.current=null;else if(r.current){const _=(f-r.current.x)*.005,k=(G-r.current.y)*.005;a.current+=_,u.current+=k,r.current={x:f,y:G}}},m=f=>v(f.clientX,f.clientY,!0,!1),h=f=>v(f.clientX,f.clientY,!1,!1),y=()=>v(0,0,!1,!0),M=f=>{f.touches.length===1&&v(f.touches[0].clientX,f.touches[0].clientY,!0,!1)},x=f=>{f.touches.length===1&&v(f.touches[0].clientX,f.touches[0].clientY,!1,!1)},p=()=>v(0,0,!1,!0);l.addEventListener("mousedown",m),l.addEventListener("mousemove",h),l.addEventListener("mouseup",y),l.addEventListener("mouseleave",y),l.addEventListener("touchstart",M,{passive:!0}),l.addEventListener("touchmove",x,{passive:!0}),l.addEventListener("touchend",p,{passive:!0});const E=d*.06,j=d*.02;o.current+=E,c.current+=j;const b=o.current+a.current,R=c.current+u.current,T=10+Math.sin(R*.3)*1.5,D=Math.sin(b)*T,P=Math.cos(b)*T,z=1.5+Math.sin(R*.5)*.8;return e.position.lerp(s.current.set(D,z,P),d*.8),e.lookAt(i.current),()=>{l.removeEventListener("mousedown",m),l.removeEventListener("mousemove",h),l.removeEventListener("mouseup",y),l.removeEventListener("mouseleave",y),l.removeEventListener("touchstart",M),l.removeEventListener("touchmove",x),l.removeEventListener("touchend",p)}}),null}function ae(){const e=n.useRef(null),o=n.useRef(null),c=n.useRef(null),i=n.useRef(null),s=n.useRef(null);return A(({clock:r})=>{const a=r.getElapsedTime();e.current.position.x=Math.sin(a*.1)*5,e.current.position.y=6+Math.sin(a*.15)*2,o.current.position.x=Math.cos(a*.08)*4,c.current.position.z=Math.sin(a*.12)*3,s.current.position.x=Math.sin(a*.2)*3,s.current.position.z=Math.cos(a*.18)*3}),t.jsxs(t.Fragment,{children:[t.jsx("ambientLight",{ref:i,intensity:.2,color:"#4466ff"}),t.jsx("directionalLight",{ref:e,position:[5,8,5],intensity:2,color:"#4488ff",castShadow:!1}),t.jsx("directionalLight",{ref:o,position:[-4,3,2],intensity:.8,color:"#ff66aa"}),t.jsx("directionalLight",{ref:c,position:[0,-2,-6],intensity:1.2,color:"#66ccff"}),t.jsx("pointLight",{ref:s,position:[2,1,2],intensity:.5,color:"#00aaff",distance:20}),t.jsx("hemisphereLight",{args:["#4488ff","#001133",.3]})]})}function ie(){n.useRef(null);const e=new q(30,60,4491519,2245802);return e.material.transparent=!0,e.material.opacity=.15,e.position.y=-3.5,A(({clock:o})=>{const c=o.getElapsedTime();e.position.z=c*.3%1,e.material.opacity=.1+Math.sin(c*.5)*.05}),t.jsx("primitive",{object:e})}function ue(){const e=n.useRef(null);A(({clock:c})=>{const i=c.getElapsedTime();e.current.rotation.x=Math.sin(i*.1)*.1,e.current.rotation.y=i*.05,e.current.rotation.z=Math.cos(i*.08)*.05});const o=Array.from({length:3},(c,i)=>{const s=6+i*1.5,r=new O(s-.02,s,80),a=new $({color:new B().setHSL(.6+i*.05,.8,.3+i*.1),transparent:!0,opacity:.08+i*.02,side:K,depthWrite:!1}),u=new Q(r,a);return u.rotation.x=Math.PI/3+i*.2,t.jsx("primitive",{object:u},i)});return t.jsx("group",{ref:e,children:o})}function ce(){const o=new Float32Array(600),c=new Float32Array(200);for(let a=0;a<200;a++)o[a*3]=(Math.random()-.5)*40,o[a*3+1]=(Math.random()-.5)*20,o[a*3+2]=(Math.random()-.5)*40-5,c[a]=Math.random()*2+.5;const i=new L;i.setAttribute("position",new w(o,3)),i.setAttribute("size",new w(c,1));const s=new ee({color:"#4488ff",size:.03,transparent:!0,opacity:.3,blending:S,depthWrite:!1,sizeAttenuation:!0}),r=new te(i,s);return A(({clock:a})=>{const u=a.getElapsedTime(),g=r.geometry.attributes.position.array;for(let d=0;d<200;d++)g[d*3+1]+=Math.sin(u*.1+d)*.001;r.geometry.attributes.position.needsUpdate=!0}),t.jsx("primitive",{object:r})}function le(){return t.jsxs(t.Fragment,{children:[t.jsx("fog",{attach:"fog",args:["#000811",15,35]}),t.jsx("color",{attach:"background",args:["#000811"]}),t.jsx(ie,{}),t.jsx(ue,{}),t.jsx(ce,{})]})}function me(){const e=C(o=>o.brainActivity);return t.jsxs(H,{multisampling:0,children:[t.jsx(F,{intensity:.8+e*.6,luminanceThreshold:.2,luminanceSmoothing:.9,mipmapBlur:!0}),t.jsx(F,{intensity:.4,luminanceThreshold:.8,luminanceSmoothing:.5,mipmapBlur:!0}),t.jsx(J,{offset:[.001,5e-4]}),t.jsx(Z,{opacity:.02}),t.jsx(U,{eskil:!1,offset:.3,darkness:.6})]})}const fe=`
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
`,ve=`
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
`,he=`
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
`,de=`
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
`;function pe({count:e=8e3,activity:o,mouseStateRef:c}){const i=n.useRef(null),s=n.useRef(null),[r,a,u,g,d]=n.useMemo(()=>{const m=new Float32Array(e*3),h=new Float32Array(e*3),y=new Float32Array(e),M=new Float32Array(e),x=new Float32Array(e);for(let p=0;p<e;p++){const E=Math.random()*Math.PI*2,j=Math.acos(2*Math.random()-1),b=2.8+(Math.random()-.5)*.8,R=2+(Math.random()-.5)*.6,T=1.8+(Math.random()-.5)*.7,P=Math.pow(Math.random(),.5);m[p*3]=Math.sin(j)*Math.cos(E)*b*P,m[p*3+1]=Math.cos(j)*R*P,m[p*3+2]=Math.sin(j)*Math.sin(E)*T*P;const z=.58+m[p*3+1]/R*.15,f=new B().setHSL(z,.9,.5);h[p*3]=f.r,h[p*3+1]=f.g,h[p*3+2]=f.b,y[p]=.02+Math.random()*.06,M[p]=Math.random(),x[p]=.3+Math.random()*.7}return[m,h,y,M,x]},[e]);A(({clock:m})=>{if(s.current){const h=c.current;s.current.uniforms.uTime.value=m.getElapsedTime(),s.current.uniforms.uActivity.value=o,s.current.uniforms.uMouse.value.x=h.x,s.current.uniforms.uMouse.value.y=h.y,s.current.uniforms.uMouseActive.value=h.down?1:.5}});const l=n.useMemo(()=>({uTime:{value:0},uActivity:{value:o},uPulsePhase:{value:Math.random()*Math.PI*2},uMouse:{value:new W(0,0)},uMouseActive:{value:0}}),[]),v=n.useMemo(()=>{const m=new L;return m.setAttribute("position",new w(r,3)),m.setAttribute("aColor",new w(a,3)),m.setAttribute("aSize",new w(u,1)),m.setAttribute("aRandom",new w(g,1)),m.setAttribute("aEnergy",new w(d,1)),m},[r,a,u,g,d]);return t.jsx("points",{ref:i,geometry:v,children:t.jsx("shaderMaterial",{ref:s,uniforms:l,vertexShader:fe,fragmentShader:ve,transparent:!0,depthWrite:!1,blending:S})})}function ge(){const e=n.useRef(null),o=n.useRef(new Array(4).fill(0)),c=n.useMemo(()=>({uTime:{value:0},uAmplitude:{value:0},uAmps:{value:new oe(0,0,0,0)}}),[]),i=n.useMemo(()=>Array.from({length:4},(s,r)=>{const a=3.8+r*.8,u=48+r*12,g=[],d=[];for(let m=0;m<=u;m++){const h=m/u*Math.PI*2;g.push(Math.cos(h)*a,0,Math.sin(h)*a),d.push(h)}const l=new L;l.setAttribute("position",new w(new Float32Array(g),3)),l.setAttribute("aAngle",new w(new Float32Array(d),1));const v=new ne({uniforms:c,vertexShader:ye,fragmentShader:Me,transparent:!0,depthWrite:!1,blending:S});return new se(l,v)}),[]);return n.useEffect(()=>()=>{i.forEach(s=>{s.geometry.dispose(),s.material.dispose()})},[i]),A(({clock:s})=>{const r=C.getState().audioAmplitude,a=s.getElapsedTime();for(let u=0;u<4;u++){const g=u===0?r:o.current[u-1];o.current[u]+=(g-o.current[u])*.1}c.uTime.value=a,c.uAmplitude.value=r,c.uAmps.value.set(o.current[0],o.current[1],o.current[2],o.current[3]),e.current&&(e.current.rotation.y=a*.15,e.current.rotation.x=Math.sin(a*.1)*.05)}),t.jsx("group",{ref:e,children:i.map((s,r)=>t.jsx("primitive",{object:s},r))})}const ye=`
uniform float uTime;
uniform float uAmplitude;
uniform vec4 uAmps;

attribute float aAngle;

varying float vGlow;

void main() {
  vec3 pos = position;

  // Map ring radius (stored in XZ length) to a ring index 0-3
  float radius = length(pos.xz);
  float ringIdx = clamp(floor((radius - 3.5) / 0.8), 0.0, 3.0);
  float amp = uAmps[int(ringIdx)];

  // Three wave frequencies for organic motion
  float wave  = sin(aAngle * 6.0 - uTime * 3.0) * amp * 0.6;
  float wave2 = sin(aAngle * 12.0 + uTime * 2.0) * amp * 0.3;
  float wave3 = cos(aAngle * 8.0 - uTime * 4.0) * amp * 0.4;
  pos.y = (wave + wave2 + wave3) * 0.5;

  // Radial pulse — ring expands/contracts with beat
  float pulse = 1.0 + sin(aAngle * 4.0 + uTime * 2.0) * amp * 0.08;
  pos.x *= pulse;
  pos.z *= pulse;

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  vGlow = amp * (0.5 + 0.5 * sin(uTime * 2.0 + aAngle * 3.0));
}
`,Me=`
uniform float uAmplitude;

varying float vGlow;

void main() {
  float intensity = 0.15 + vGlow * 0.85;
  vec3 color = mix(
    vec3(0.08, 0.25, 0.7),    // deep blue
    vec3(0.4, 0.85, 1.0),     // bright cyan
    intensity
  );

  float alpha = intensity * 0.45;
  float hdr = 1.0 + intensity * 2.5;

  gl_FragColor = vec4(color * hdr, alpha);
}
`;function xe({count:e=600,activity:o,mouseStateRef:c}){const i=n.useRef(null),s=n.useRef(null),[r,a,u]=n.useMemo(()=>{const l=[],v=[],m=[];for(let h=0;h<e;h++){const y=Math.random()*Math.PI*2,M=Math.acos(2*Math.random()-1),x=Math.pow(Math.random(),.4),p=y+(Math.random()-.5)*.8,E=M+(Math.random()-.5)*.8,j=2.8,b=2,R=1.8;l.push(Math.sin(M)*Math.cos(y)*j*x,Math.cos(M)*b*x,Math.sin(M)*Math.sin(y)*R*x,Math.sin(E)*Math.cos(p)*j*x,Math.cos(E)*b*x,Math.sin(E)*Math.sin(p)*R*x);const T=.3+Math.random()*.7;v.push(T,T),m.push(Math.random(),Math.random())}return[new Float32Array(l),new Float32Array(v),new Float32Array(m)]},[e]);A(({clock:l})=>{if(s.current){const v=c.current;s.current.uniforms.uTime.value=l.getElapsedTime(),s.current.uniforms.uActivity.value=o,s.current.uniforms.uMouse.value.x=v.x,s.current.uniforms.uMouse.value.y=v.y,s.current.uniforms.uMouseActive.value=v.down?1:.5}});const g=n.useMemo(()=>{const l=new L;return l.setAttribute("position",new w(r,3)),l.setAttribute("aEnergy",new w(a,1)),l.setAttribute("aRandom",new w(u,1)),l},[r,a,u]),d=n.useMemo(()=>({uTime:{value:0},uActivity:{value:o},uPulsePhase:{value:Math.random()*Math.PI*2},uMouse:{value:new W(0,0)},uMouseActive:{value:0}}),[]);return t.jsx("lineSegments",{ref:i,geometry:g,children:t.jsx("shaderMaterial",{ref:s,uniforms:d,vertexShader:he,fragmentShader:de,transparent:!0,depthWrite:!1,blending:S})})}function we(){const e=n.useRef(null);return A(({clock:o})=>{e.current&&(e.current.rotation.x=Math.sin(o.getElapsedTime()*.1)*.05,e.current.rotation.y=o.getElapsedTime()*.03)}),t.jsxs("mesh",{ref:e,children:[t.jsx("sphereGeometry",{args:[3.2,32,32]}),t.jsx("meshBasicMaterial",{color:"#4488ff",transparent:!0,opacity:.04,wireframe:!0,depthWrite:!1})]})}function Ae(){const e=n.useRef(null);return A(({clock:o})=>{if(e.current){const c=1+Math.sin(o.getElapsedTime()*.5)*.02;e.current.scale.setScalar(c)}}),t.jsxs("mesh",{ref:e,children:[t.jsx("sphereGeometry",{args:[.8,16,16]}),t.jsx("meshBasicMaterial",{color:"#88ccff",transparent:!0,opacity:.3,blending:S})]})}function Ee({activity:e,mouseStateRef:o}){return t.jsxs("group",{children:[t.jsx(pe,{count:8e3,activity:e,mouseStateRef:o}),t.jsx(xe,{count:600,activity:e,mouseStateRef:o}),t.jsx(we,{}),t.jsx(Ae,{}),t.jsx(ge,{})]})}function je(){const e=n.useRef({x:0,y:0,down:!1,velocityX:0,velocityY:0}),o=n.useRef(0),c=n.useRef(0),i=n.useRef(null),s=r=>{i.current=r};return n.useEffect(()=>{const r=(m,h)=>{const y=m/window.innerWidth*2-1,M=-(h/window.innerHeight)*2+1;e.current.velocityX=y-o.current,e.current.velocityY=M-c.current,e.current.x=y,e.current.y=M,o.current=y,c.current=M,i.current?.(e.current)},a=m=>r(m.clientX,m.clientY),u=()=>{e.current.down=!0},g=()=>{e.current.down=!1},d=m=>{m.touches.length>0&&r(m.touches[0].clientX,m.touches[0].clientY)},l=()=>{e.current.down=!0},v=()=>{e.current.down=!1};return document.addEventListener("mousemove",a,{passive:!0}),document.addEventListener("mousedown",u,{passive:!0}),document.addEventListener("mouseup",g,{passive:!0}),document.addEventListener("touchmove",d,{passive:!0}),document.addEventListener("touchstart",l,{passive:!0}),document.addEventListener("touchend",v,{passive:!0}),()=>{document.removeEventListener("mousemove",a),document.removeEventListener("mousedown",u),document.removeEventListener("mouseup",g),document.removeEventListener("touchmove",d),document.removeEventListener("touchstart",l),document.removeEventListener("touchend",v)}},[]),{state:e,on:s}}function Re(){const[e,o]=n.useState("");return n.useEffect(()=>{const c=setInterval(()=>{o(i=>i.length>=3?"":i+".")},500);return()=>clearInterval(c)},[]),t.jsxs("div",{style:{position:"fixed",inset:0,display:"flex",alignItems:"center",justifyContent:"center",background:"#000811",color:"#4488ff",fontFamily:"'JetBrains Mono', monospace",flexDirection:"column",gap:16,zIndex:1},children:[t.jsx("div",{style:{fontSize:32,opacity:.6},children:"◈"}),t.jsxs("div",{style:{fontSize:11,letterSpacing:4,opacity:.4,textTransform:"uppercase"},children:["Inicializando",e]})]})}function Le(){const e=C(u=>u.brainActivity),[o,c]=n.useState(!1),[i,s]=n.useState(!1),r=n.useRef(!0),a=je();return n.useEffect(()=>{const u=setTimeout(()=>{!i&&r.current&&(console.warn("[JARVIS] Canvas initialization timeout"),c(!0))},1e4);return()=>{clearTimeout(u),r.current=!1}},[i]),o?t.jsxs("div",{style:{position:"fixed",inset:0,display:"flex",alignItems:"center",justifyContent:"center",background:"#000811",color:"#4488ff",fontFamily:"'JetBrains Mono', monospace",flexDirection:"column",gap:12,zIndex:1},children:[t.jsx("div",{style:{fontSize:40},children:"⚠"}),t.jsx("div",{style:{fontSize:12,letterSpacing:2,opacity:.5},children:"3D RENDER OFFLINE"}),t.jsxs("div",{style:{fontSize:10,opacity:.3,maxWidth:400,textAlign:"center"},children:["WebGL não disponível ou ocorreu um erro na renderização 3D.",t.jsx("br",{}),"A interface HUD ainda está funcional."]})]}):t.jsxs(t.Fragment,{children:[!i&&t.jsx(Re,{}),t.jsxs(N,{gl:{antialias:!0,alpha:!1,powerPreference:"high-performance",stencil:!1,depth:!0,failIfMajorPerformanceCaveat:!1},camera:{position:[0,0,12],fov:45,near:.1,far:100},dpr:[1,2],performance:{min:.5},onCreated:u=>{u.gl.capabilities.isWebGL2||console.warn("[JARVIS] WebGL2 not available, falling back to WebGL1"),r.current&&s(!0)},onError:u=>{console.error("[JARVIS] Canvas error:",u),r.current&&c(!0)},style:{position:"fixed",top:0,left:0,width:"100%",height:"100%",opacity:i?1:0,transition:"opacity 0.5s ease-in"},children:[t.jsx(re,{}),t.jsx(ae,{}),t.jsx(le,{}),t.jsx(Ee,{activity:e,mouseStateRef:a.state}),t.jsx(me,{})]})]})}export{Le as Scene};
