// diorama.js — biblioteca do estilo "diorama isométrico" (three.js, módulo ES)
// Bloco de terreno recortado sobre base técnica, câmera ortográfica parada, acabamento de HQ:
// cel-shading em faixas + hachura de gravura nas sombras + salpicos + contorno a nanquim (pós-processo).
// Uso na página:  import * as DI from '../../lib/diorama.js';  const S = DI.palco({...});
import * as THREE from 'three';
export { THREE };

// Cores em sRGB direto: sem gestão de cor e sem tone mapping, o hex da paleta é o hex do vídeo.
THREE.ColorManagement.enabled = false;

// ───────────────────────── paleta (amostrada da referência) ─────────────────────────
export const PAL = {
  tinta: '#241a33',
  chao: '#0a9d92', chaoClaro: '#60d19e', chaoSombra: '#55415b',
  salmao: '#ea9a6e', faceBaixo: '#d09983', faceSombra: '#8a2d57',
  rocha: '#7b0f27', rochaLuz: '#cd7455',
  base: '#3bb390', baseClaro: '#94cdad', trilho: '#4a63c8', lampada: '#ffe9a8', cabo: '#d0414f',
};

// Rampas de 5 tons (do mais escuro ao mais claro) + cor da sombra projetada (cs) + cor da hachura/salpico (hc)
export const RAMPAS = {
  areia: { c: ['#8a2d57', '#b0485a', '#d9795f', '#ea9a6e', '#f7bb8c'], cs: '#a3505f', hc: '#5a1d40' },
  rocha: { c: ['#4a0a22', '#661027', '#7b0f27', '#9c2238', '#d27050'] },
  face: { c: ['#8a2d57', '#9c3a5c', '#d9795f', '#f39f6f', '#f7bb8c'], cs: '#9a4a63', hc: '#561a3e' },
  chao: { c: ['#1f5a66', '#127f80', '#0a948c', '#0a9d92', '#2bb6a0'], cs: '#55415b', hc: '#2c2142' },
  base: { c: ['#215e66', '#1f7f74', '#2f9f86', '#3bb390', '#94cdad'], cs: '#4a3b5a', hc: '#22323f' },
  deck: { c: ['#2a6a6a', '#4b9c8c', '#79bea0', '#94cdad', '#bfe3c6'], cs: '#4f4560', hc: '#2a3540' },
  trilho: { c: ['#262f66', '#33407e', '#3d52a8', '#4a63c8', '#7d93e6'], cs: '#2a2550', hc: '#1c1a3a' },
  agua: { c: ['#334a73', '#4b6491', '#5f7fa6', '#7b9cbb', '#c9dde4'], cs: '#4f5680', hc: '#2c3358' },
  mata: { c: ['#3f4a66', '#4f7a78', '#78a88e', '#9cc79f', '#cfe8c4'], cs: '#55607a', hc: '#2c3346' },
  vermelho: { c: ['#4e0a20', '#7b0f27', '#a8233a', '#d0414f', '#ee7a6d'], cs: '#5a2340', hc: '#2c1428' },
  creme: { c: ['#7f5a6a', '#b98f85', '#e0c4ac', '#f2e3c6', '#fff6e4'], cs: '#a07e86', hc: '#4a3346' },
};

// ───────────────────────── ruído determinístico (JS) ─────────────────────────
export function rng(seed = 1) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const PERM = (() => { const r = rng(1337), p = [...Array(256).keys()]; for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; } return Uint8Array.from([...p, ...p]); })();
const GX = new Float32Array(256), GY = new Float32Array(256);
for (let i = 0; i < 256; i++) { const a = i / 256 * Math.PI * 2; GX[i] = Math.cos(a); GY[i] = Math.sin(a); }
/** ruído de gradiente 2D em [-1,1] */
export function ruido(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi, X = xi & 255, Y = yi & 255;
  const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10), v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
  const g = (h, dx, dy) => GX[h] * dx + GY[h] * dy;
  const a = PERM[PERM[X] + Y], b = PERM[PERM[X + 1] + Y], c = PERM[PERM[X] + Y + 1], d = PERM[PERM[X + 1] + Y + 1];
  const x1 = g(a, xf, yf) + u * (g(b, xf - 1, yf) - g(a, xf, yf)), x2 = g(c, xf, yf - 1) + u * (g(d, xf - 1, yf - 1) - g(c, xf, yf - 1));
  return (x1 + v * (x2 - x1)) * 1.41;
}
/** fbm: soma de oitavas (≈[-1,1]) */
export function fbm(x, y, oct = 4) { let s = 0, a = .5, f = 1, n = 0; for (let i = 0; i < oct; i++) { s += a * ruido(x * f + i * 17.3, y * f - i * 9.1); n += a; a *= .5; f *= 2.03; } return s / n; }
/** cristas: ruído "ridged" em [0,1] — penhascos e arestas de rocha */
export function cristas(x, y, oct = 4) { let s = 0, a = .5, f = 1, n = 0; for (let i = 0; i < oct; i++) { const r = 1 - Math.abs(ruido(x * f + i * 31.7, y * f + i * 5.3)); s += a * r * r; n += a; a *= .5; f *= 2.1; } return s / n; }
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const suave = (a, b, v) => { const k = clamp((v - a) / (b - a)); return k * k * (3 - 2 * k); };
/** máximo suave (une morros sem vinco) */
export const smax = (a, b, k = .4) => { const h = clamp(.5 + .5 * (a - b) / k); return lerp(b, a, h) + k * h * (1 - h); };
/** domo tipo "pão de açúcar": paredes íngremes e topo arredondado. o: {x,z,rx,rz,h,ang,pot,ombro} */
export function domo(x, z, o) {
  const c = Math.cos(o.ang || 0), s = Math.sin(o.ang || 0), dx = x - o.x, dz = z - o.z;
  const ur = dx * c - dz * s, u = ur / (ur < 0 && o.rx2 ? o.rx2 : o.rx), v = (dx * s + dz * c) / o.rz, q = Math.sqrt(u * u + v * v);
  // sulcos: o raio varia com o ângulo → caneluras verticais descendo a encosta
  const sq = o.sulcos ? q * (1 + o.sulcos * ruido(Math.cos(Math.atan2(v, u)) * (o.sulcosF ?? 2.2) + (o.semente || 0), Math.sin(Math.atan2(v, u)) * (o.sulcosF ?? 2.2))) : q;
  const p = o.pot ?? 2.4;
  // fora do raio o domo continua descendo (negativo): assim smax() com o resto do relevo não levanta o chão em volta
  // pe: talude suave no pé do paredão (onde a mata cresce)
  const pe = o.pe ? o.pe * o.h * Math.exp(-(((sq - 1) / (o.peLarg ?? .35)) ** 2)) : 0;
  if (sq >= 1) return -o.h * .5 * (sq - 1) + pe;
  return o.h * Math.pow(1 - Math.pow(sq, p), o.ombro ?? .45) + pe;
}
/** frente de onda: 0 → 1 quando a frente (progresso p ∈ [0,1]) passa pela coordenada u ∈ [0,1]. larg = largura da frente */
export const onda = (u, p, larg = .35) => suave(0, 1, (p * (1 + larg) - u) / larg);

// ───────────────────────── material de HQ (cel + hachura + salpico) ─────────────────────────
const TEMPO = { value: 0 }, SOL = { value: new THREE.Vector3(-.55, .68, 1).normalize() }, TINTA = { value: new THREE.Color(PAL.tinta) };
const GLSL = `
uniform vec3 uS[5]; uniform vec3 uR[5]; uniform vec4 uTh; uniform vec4 uThR; uniform float uRockOn; uniform vec3 uCS; uniform vec3 uHC; uniform vec3 uInk;
uniform vec4 uHatch; uniform vec3 uStreak; uniform vec3 uSpeck; uniform vec2 uRough; uniform vec3 uSun; uniform float uTime;
uniform vec3 uGradD; uniform vec2 uGradR; uniform vec3 uGradC; uniform float uGradA;
uniform sampler2D uMap; uniform float uMapOn; uniform vec2 uMapRep; uniform float uLevel; uniform vec3 uFoamC;
varying vec3 vW; varying vec3 vWN;
#ifdef DI_AGUA
varying float vH;
#endif
float diH(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float diN(vec2 p){ vec2 i=floor(p), f=fract(p); vec2 u=f*f*(3.-2.*f);
  return mix(mix(diH(i),diH(i+vec2(1.,0.)),u.x), mix(diH(i+vec2(0.,1.)),diH(i+vec2(1.,1.)),u.x), u.y); }
vec3 diRamp(vec3 a, vec3 b, vec3 c, vec3 d, vec3 e, vec4 th, float n){
  float aa = fwidth(n)*.75 + 1e-4;
  vec3 r = mix(a, b, smoothstep(th.x-aa, th.x+aa, n));
  r = mix(r, c, smoothstep(th.y-aa, th.y+aa, n));
  r = mix(r, d, smoothstep(th.z-aa, th.z+aa, n));
  return mix(r, e, smoothstep(th.w-aa, th.w+aa, n)); }
`;
const FRAG = `
  vec3 wn = normalize(vWN);
  vec3 Ls = normalize(uSun);
  float ndl = clamp(dot(wn, Ls), 0., 1.);
  float lit = reflectedLight.directDiffuse.r;             // = ndl * sombra (luz branca, intensidade PI, difuso branco)
  float shd = ndl > .04 ? clamp(lit / ndl, 0., 1.) : 1.;
  vec3 an = abs(wn);
  vec2 P = an.y > .6 ? vW.xz : (an.x > an.z ? vW.zy : vW.xy);
  float nn = ndl + (diN(P*uRough.y + vW.y*1.3) - .5) * uRough.x;
  vec3 col = diRamp(uS[0],uS[1],uS[2],uS[3],uS[4], uTh, nn);
  float steep = 1. - smoothstep(.5, .8, an.y);
  if (uRockOn > .5) {
    float rk = smoothstep(.8, .55, wn.y + (diN(P*2.3) - .5)*.3);
    col = mix(col, diRamp(uR[0],uR[1],uR[2],uR[3],uR[4], uThR, nn), rk);
    steep = rk;
  }
  float gq = clamp((dot(vW, uGradD) - uGradR.x) / (uGradR.y - uGradR.x), 0., 1.);
  col = mix(col, uGradC, gq * uGradA * smoothstep(.25, .45, ndl));
  // estrias verticais de gravura nos paredões
  if (uStreak.x > 0.) {
    vec2 hz = wn.xz; float lh = length(hz); hz = lh > 1e-3 ? hz/lh : vec2(1.,0.);
    float along = dot(vW.xz, vec2(-hz.y, hz.x));
    float s1 = diN(vec2(along*uStreak.y, vW.y*2.2));
    float s2 = diN(vec2(along*uStreak.y*2.7 + 13.1, vW.y*4.1));
    col = mix(col, uHC, smoothstep(.6, .8, s1) * steep * uStreak.x);
    col = mix(col, uRockOn > .5 ? uR[4] : uS[4], smoothstep(.74, .86, s2) * steep * uStreak.z * step(uTh.z, nn));
  }
  // sombra projetada dura
  float cs = (1. - smoothstep(.3, .7, shd)) * step(.04, ndl);
  col = mix(col, uCS, cs);
  // hachura de gravura: nas faixas escuras e na sombra projetada
  float sombra = clamp(1. - smoothstep(uTh.x, uTh.y, nn) + cs, 0., 1.);
  sombra = max(sombra, (1. - smoothstep(uTh.y, uTh.z, nn)) * .45);
  vec2 dv = vec2(cos(uHatch.w), sin(uHatch.w));
  float hc = dot(P, dv) * uHatch.y + (diN(P*2.1) - .5) * 1.5;
  float hw = fwidth(hc) * .8;
  float hl = 1. - smoothstep(uHatch.z*.5 - hw, uHatch.z*.5 + hw, abs(fract(hc) - .5));
  float br = smoothstep(.32, .55, diN(vec2(dot(P, vec2(-dv.y, dv.x)) * uHatch.y * .16, floor(hc) * .37)));
  col = mix(col, uHC, hl * br * sombra * uHatch.x);
  // salpicos (escuros e claros)
  vec2 sp = P * uSpeck.z; vec2 ci = floor(sp); vec2 fr = fract(sp) - .5;
  float hh = diH(ci); vec2 of = vec2(diH(ci + 3.7), diH(ci + 9.1)) - .5;
  float sz = .1 + .12 * diH(ci + 5.3), dd = length(fr - of * .5), sw = fwidth(sp.x) * .8;
  float dotm = 1. - smoothstep(sz - sw, sz + sw, dd);
  col = mix(col, uHC, dotm * step(1. - uSpeck.x, hh));
  col = mix(col, uS[4], dotm * step(hh, uSpeck.y));
#ifdef DI_AGUA
  float dep = uLevel - vH;
  float fn = (diN(vW.xz*5. + uTime*.7) - .5) * .09;
  col = mix(col, uS[3], (1. - smoothstep(0., .4, dep)) * .55);
  vec2 iso = vec2(dot(vW.xz, vec2(.7071, -.7071)), dot(vW.xz, vec2(.7071, .7071)));
  float fl = diN(vec2(iso.x*1.1 + uTime*.25, iso.y*16.));
  col = mix(col, uS[4], smoothstep(.76, .82, fl) * .75 * (1. - cs*.6));
  col = mix(col, uS[2], smoothstep(.2, .14, fl) * .5);
  col = mix(col, uFoamC, 1. - smoothstep(.03 + fn, .12 + fn, dep));
#endif
  // detalhe pintado (canvas): R multiplica, G = nanquim, B = brilho
  if (uMapOn > .5) { vec3 tx = texture2D(uMap, vUv * uMapRep).rgb; col *= tx.r; col = mix(col, uS[4], tx.b); col = mix(col, uInk, tx.g); }
  gl_FragColor = vec4(col, 1.);
`;
/**
 * Material do estilo. o: { rampa:'areia'|{c:[5],cs,hc}, rocha:'rocha'|null, faixas:[4 limiares de N·L],
 *   hachura:[intensidade, linhas/unidade, espessura(0-1), ângulo rad], estrias:[int, freq, brilho], salpico:[escuros, claros, células/unidade],
 *   aspereza:[amp, freq], grad:{dir:[x,y,z], de, ate, cor, forca}, mapa:Texture, rep:[u,v], agua:bool, espuma:'#hex' }
 */
export function material(o = {}) {
  const R = typeof o.rampa === 'string' ? RAMPAS[o.rampa] : (o.rampa || RAMPAS.areia);
  const Rr = o.rocha ? (typeof o.rocha === 'string' ? RAMPAS[o.rocha] : o.rocha) : R;
  const C = c => new THREE.Color(c), V3 = a => new THREE.Vector3(...a);
  const th = o.faixas || [.1, .25, .42, .86], h = o.hachura || [.85, 22, .38, .6], es = o.estrias || [0, 30, .5], sp = o.salpico || [.05, .015, 13], ru = o.aspereza || [.12, 3];
  const gr = o.grad || { dir: [0, 1, 0], de: 0, ate: 1, cor: '#ffffff', forca: 0 };
  const m = new THREE.MeshLambertMaterial({ color: 0xffffff });
  m.defines = { USE_UV: '' }; if (o.agua) m.defines.DI_AGUA = '';
  const u = m.userData.u = {
    uS: { value: R.c.map(C) }, uR: { value: Rr.c.map(C) }, uTh: { value: new THREE.Vector4(...th) }, uThR: { value: new THREE.Vector4(...(o.faixasRocha || [.14, .34, .6, .9])) }, uRockOn: { value: o.rocha ? 1 : 0 },
    uCS: { value: C(R.cs || R.c[0]) }, uHC: { value: C(R.hc || PAL.tinta) }, uInk: TINTA, uSun: SOL, uTime: TEMPO,
    uHatch: { value: new THREE.Vector4(...h) }, uStreak: { value: V3(es) }, uSpeck: { value: V3(sp) }, uRough: { value: new THREE.Vector2(...ru) },
    uGradD: { value: V3(gr.dir).normalize() }, uGradR: { value: new THREE.Vector2(gr.de, gr.ate) }, uGradC: { value: C(gr.cor) }, uGradA: { value: gr.forca },
    uMap: { value: o.mapa || null }, uMapOn: { value: o.mapa ? 1 : 0 }, uMapRep: { value: new THREE.Vector2(...(o.rep || [1, 1])) },
    uLevel: { value: 0 }, uFoamC: { value: C(o.espuma || '#eef4ef') },
  };
  m.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, u);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vW; varying vec3 vWN;\n#ifdef DI_AGUA\nattribute float aH; varying float vH;\n#endif')
      .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
  vec4 diW = vec4(transformed, 1.);
  #ifdef USE_INSTANCING
    diW = instanceMatrix * diW;
  #endif
  diW = modelMatrix * diW; vW = diW.xyz;
  vWN = normalize((vec4(transformedNormal, 0.) * viewMatrix).xyz);
  #ifdef DI_AGUA
    vH = aH;
  #endif`);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + GLSL).replace('#include <opaque_fragment>', FRAG);
  };
  return m;
}
/** material sem luz (lâmpadas, brilhos) */
export const brilho = cor => new THREE.MeshBasicMaterial({ color: new THREE.Color(cor) });

// ───────────────────────── texturas pintadas (canvas) ─────────────────────────
// Convenção de cores do canvas: BASE (não muda), TINTA (nanquim), FUNDO (rebaixo mais escuro), LUZ (brilho)
export const CV = { BASE: 'rgb(255,0,0)', TINTA: 'rgb(255,255,0)', FUNDO: 'rgb(196,0,0)', FUNDO2: 'rgb(160,0,0)', LUZ: 'rgb(255,0,255)' };
export function textura(w, h, desenhar) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d');
  x.fillStyle = CV.BASE; x.fillRect(0, 0, w, h); desenhar(x, w, h);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; t.colorSpace = THREE.NoColorSpace; return t;
}
/** painel técnico com janela hexagonal, parafusos e grade (a parede da base) */
export function texPainel(semente = 3) {
  return textura(512, 512, (x, w, h) => {
    const r = rng(semente); x.lineJoin = 'round';
    x.strokeStyle = CV.TINTA; x.lineWidth = 6; x.strokeRect(10, 14, w - 20, h - 28);
    x.lineWidth = 3; x.strokeRect(30, 34, w - 60, h - 68);
    const hex = (cx, cy, rx, ry) => { x.beginPath(); [[-.55, -1], [.55, -1], [1, -.35], [1, .35], [.55, 1], [-.55, 1], [-1, .35], [-1, -.35]].forEach(([a, b], i) => x[i ? 'lineTo' : 'moveTo'](cx + a * rx, cy + b * ry)); x.closePath(); };
    hex(w / 2, h / 2 + 6, 170, 165); x.fillStyle = CV.FUNDO; x.fill(); x.lineWidth = 7; x.stroke();
    hex(w / 2, h / 2 + 6, 140, 135); x.fillStyle = CV.FUNDO2; x.fill(); x.lineWidth = 3; x.stroke();
    x.strokeStyle = CV.LUZ; x.lineWidth = 5; x.beginPath(); x.moveTo(w / 2 - 70, h / 2 - 115); x.lineTo(w / 2 + 70, h / 2 - 115); x.stroke();
    x.strokeStyle = CV.TINTA; x.lineWidth = 3;
    for (let i = 0; i < 4; i++) { x.beginPath(); x.moveTo(w / 2 - 60 + i * 40, h / 2 + 40); x.lineTo(w / 2 - 60 + i * 40, h / 2 + 110); x.stroke(); }
    x.fillStyle = CV.TINTA; [[40, 44], [w - 40, 44], [40, h - 44], [w - 40, h - 44]].forEach(([a, b]) => { x.beginPath(); x.arc(a, b, 7, 0, 7); x.fill(); });
    if (r() < .5) { x.beginPath(); x.arc(w - 70, h / 2, 12, 0, 7); x.fill(); }
  });
}
/** chão de placas: juntas finas, riscos, marcas (repetir com rep) */
export function texChao(semente = 5) {
  return textura(2048, 2048, (x, w, h) => {
    const r = rng(semente); x.strokeStyle = CV.TINTA; x.lineCap = 'round';
    // juntas principais (2 por lado da textura) com interrupções
    for (let i = 0; i <= 2; i++) { const p = i * w / 2; x.lineWidth = 5;
      for (let k = 0; k < 8; k++) { const a = k * h / 8 + (r() < .2 ? 40 : 0), b = (k + 1) * h / 8 - (r() < .2 ? 50 : 0);
        x.beginPath(); x.moveTo(p, a); x.lineTo(p, b); x.stroke(); x.beginPath(); x.moveTo(a, p); x.lineTo(b, p); x.stroke(); } }
    // juntas finas secundárias e riscos
    x.lineWidth = 2.5;
    for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) {
      const x0 = i * w / 2, y0 = j * h / 2;
      if (r() < .7) { const yy = y0 + 200 + r() * 600; x.beginPath(); x.moveTo(x0, yy); x.lineTo(x0 + 1024, yy); x.stroke(); }
      for (let k = 0; k < 3; k++) if (r() < .6) { const yy = y0 + 60 + r() * 900, xx = x0 + 40 + r() * 600; x.beginPath(); x.moveTo(xx, yy); x.lineTo(xx + 80 + r() * 260, yy); x.stroke(); }
      for (let k = 0; k < 2; k++) if (r() < .5) { const xx = x0 + 60 + r() * 900, yy = y0 + 40 + r() * 600; x.beginPath(); x.moveTo(xx, yy); x.lineTo(xx, yy + 80 + r() * 200); x.stroke(); }
      if (r() < .5) { x.fillStyle = CV.FUNDO; const a = x0 + 80 + r() * 800, b = y0 + 80 + r() * 800; x.fillRect(a, b, 90, 30); x.strokeRect(a, b, 90, 30); }
      for (let k = 0; k < 6; k++) { x.fillStyle = CV.TINTA; x.beginPath(); x.arc(x0 + r() * 1024, y0 + r() * 1024, 3 + r() * 3, 0, 7); x.fill(); }
    }
  });
}
/** grelha de ventilação (furos em grade) */
export function texGrelha() {
  return textura(256, 128, (x, w, h) => {
    x.fillStyle = CV.FUNDO; x.fillRect(0, 0, w, h); x.fillStyle = CV.TINTA;
    for (let i = 0; i < 12; i++) for (let j = 0; j < 5; j++) { x.beginPath(); x.arc(16 + i * 20.5, 18 + j * 23, 6.5, 0, 7); x.fill(); }
    x.strokeStyle = CV.TINTA; x.lineWidth = 6; x.strokeRect(3, 3, w - 6, h - 6);
  });
}

// ───────────────────────── palco: renderer + câmera ortográfica + luz + nanquim ─────────────────────────
/**
 * o: { ss: superamostragem (2), meia: meia-largura visível em unidades (6.85), azimute (45°), elevacao (33°), alvo:[x,y,z],
 *      sol:[x,y,z] (direção PARA a luz), sombra:{tam, raio, mapa}, fundo:'#hex', traco: espessura do nanquim em px finais (1.3),
 *      kDepth, kNormal (limiares do contorno), grao }
 */
export function palco(o = {}) {
  const V = window.VIDEO, SS = o.ss ?? 2, W = V.w * SS, H = V.h * SS;
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap; renderer.shadowMap.autoUpdate = false;
  renderer.domElement.className = 'layer';
  (o.parent || document.getElementById('stage')).prepend(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(o.fundo || PAL.chao);
  const ar = V.w / V.h, meia = o.meia ?? 6.85;
  const camera = new THREE.OrthographicCamera(-meia, meia, meia / ar, -meia / ar, 1, 160);
  const az = (o.azimute ?? 45) * Math.PI / 180, el = (o.elevacao ?? 33) * Math.PI / 180, alvo = new THREE.Vector3(...(o.alvo || [0, 0, 0]));
  camera.position.set(alvo.x + Math.cos(el) * Math.sin(az) * 70, alvo.y + Math.sin(el) * 70, alvo.z + Math.cos(el) * Math.cos(az) * 70);
  camera.lookAt(alvo); camera.updateMatrixWorld();
  // sol: direcional com sombra dura
  SOL.value.set(...(o.sol || [-.55, .68, 1])).normalize();
  const sol = new THREE.DirectionalLight(0xffffff, Math.PI);
  const so = o.sombra || {};
  sol.position.copy(alvo).addScaledVector(SOL.value, 60); sol.target.position.copy(alvo);
  sol.castShadow = true; sol.shadow.mapSize.set(so.mapa ?? 4096, so.mapa ?? 4096);
  const R = so.tam ?? 16; Object.assign(sol.shadow.camera, { left: -R, right: R, top: R, bottom: -R, near: 1, far: 140 });
  sol.shadow.bias = so.bias ?? -.0004; sol.shadow.normalBias = so.normalBias ?? .03; sol.shadow.radius = so.raio ?? 1;
  scene.add(sol, sol.target);
  // alvos: cor (+profundidade) e normais, em superamostragem
  const dt = new THREE.DepthTexture(W, H); dt.type = THREE.UnsignedIntType;
  const rtC = new THREE.WebGLRenderTarget(W, H, { depthTexture: dt, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
  const rtN = new THREE.WebGLRenderTarget(W, H, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter });
  const nMat = new THREE.MeshNormalMaterial();
  const post = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
    uniforms: { tC: { value: rtC.texture }, tN: { value: rtN.texture }, tD: { value: dt }, uPx: { value: new THREE.Vector2(1 / W, 1 / H) },
      uLine: { value: (o.traco ?? 1.3) * SS * .5 }, uInk: TINTA, uRange: { value: camera.far - camera.near },
      uDK: { value: o.kDepth ?? .05 }, uNK: { value: o.kNormal ?? .32 }, uGrain: { value: o.grao ?? .022 }, uSeed: { value: 0 }, uSS: { value: SS } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }',
    fragmentShader: `uniform sampler2D tC, tN, tD; uniform vec2 uPx; uniform float uLine, uRange, uDK, uNK, uGrain, uSeed, uSS; uniform vec3 uInk; varying vec2 vUv;
      float D(vec2 p){ return texture2D(tD, p).r * uRange; }
      vec3 Nn(vec2 p){ return texture2D(tN, p).rgb * 2. - 1.; }
      float edge(vec2 p){ vec2 o = uPx * uLine; float c = D(p);
        float lap = abs(D(p - vec2(o.x, 0.)) + D(p + vec2(o.x, 0.)) - 2. * c) + abs(D(p - vec2(0., o.y)) + D(p + vec2(0., o.y)) - 2. * c);
        float ed = smoothstep(uDK, uDK * 2., lap);
        vec3 n = Nn(p);
        float nd = max(max(1. - dot(n, Nn(p + vec2(o.x, 0.))), 1. - dot(n, Nn(p - vec2(o.x, 0.)))), max(1. - dot(n, Nn(p + vec2(0., o.y))), 1. - dot(n, Nn(p - vec2(0., o.y)))));
        return max(ed, smoothstep(uNK, uNK * 1.6, nd)); }
      float hs(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      void main(){
        vec3 col = vec3(0.); vec2 h = uPx * .5; float e = 0.;
        for (int i = 0; i < 4; i++) { vec2 q = vUv + h * vec2(i == 0 || i == 2 ? -1. : 1., i < 2 ? -1. : 1.); col += texture2D(tC, q).rgb; e += edge(q); }
        col *= .25; e *= .25;
        col = mix(col, uInk, clamp(e, 0., 1.) * .95);
        col += (hs(gl_FragCoord.xy + uSeed) - .5) * uGrain;
        gl_FragColor = vec4(col, 1.); }`,
    depthTest: false, depthWrite: false,
  }));
  const postScene = new THREE.Scene(); postScene.add(post); const postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const S = { THREE, renderer, scene, camera, sol, SS, post, update: null, t: 0 };
  /** adiciona objetos já com sombra (projeta e recebe) */
  S.add = (...objs) => { objs.forEach(ob => { ob.traverse(m => { if (m.isMesh) { m.castShadow = m.userData.semSombra ? false : true; m.receiveShadow = true; } }); scene.add(ob); }); return objs[0]; };
  /** ponto 3D → pixel da tela (1080×1920) */
  S.tela = (x, y, z) => { const v = new THREE.Vector3(x, y, z).project(camera); return [(v.x + 1) / 2 * V.w, (1 - v.y) / 2 * V.h]; };
  onTick(t => {
    S.t = t; TEMPO.value = t; post.material.uniforms.uSeed.value = Math.floor(t * 12) * 7.13;
    if (S.update) S.update(t);
    renderer.shadowMap.needsUpdate = true;
    camera.layers.enableAll();
    renderer.setRenderTarget(rtC); renderer.render(scene, camera);
    // passe de normais (sem a camada 1: brilhos e halos não ganham contorno)
    const bg = scene.background; scene.background = null; scene.overrideMaterial = nMat; camera.layers.set(0);
    renderer.setClearColor(0x8080ff, 1); renderer.setRenderTarget(rtN); renderer.clear(); renderer.render(scene, camera);
    scene.overrideMaterial = null; scene.background = bg; camera.layers.enableAll();
    renderer.setRenderTarget(null); renderer.render(postScene, postCam);
  });
  return S;
}

// ───────────────────────── bloco de terreno recortado ─────────────────────────
/**
 * Malha de altura + 4 faces cortadas (a "seção de solo" do diorama).
 * o: { lx, lz, nx, nz, fundo (profundidade do bloco abaixo de y=0), mat (topo), matFace (faces) }
 * T.alturas(fn(i,x,z) → y) recalcula; T.altura(x,z) consulta (bilinear); T.X, T.Z, T.H: arrays por vértice.
 */
export function terreno(S, o = {}) {
  const lx = o.lx ?? 10, lz = o.lz ?? 8, nx = o.nx ?? 180, nz = o.nz ?? 144, F = o.fundo ?? 2.6, NV = (nx + 1) * (nz + 1);
  const X = new Float32Array(NV), Z = new Float32Array(NV), Hh = new Float32Array(NV);
  for (let iy = 0; iy <= nz; iy++) for (let ix = 0; ix <= nx; ix++) { const i = iy * (nx + 1) + ix; X[i] = -lx / 2 + ix * lx / nx; Z[i] = -lz / 2 + iy * lz / nz; }
  const g = new THREE.PlaneGeometry(lx, lz, nx, nz); g.rotateX(-Math.PI / 2);
  const topo = new THREE.Mesh(g, o.mat || material({ rampa: 'areia', rocha: 'rocha', estrias: [.8, 26, .6] })); topo.frustumCulled = false;
  const grupo = new THREE.Group(); grupo.add(topo);
  // faces: índices de borda em ordem "da esquerda para a direita" vista de fora (enrolamento anti-horário)
  const row = (iy, rev) => { const a = []; for (let ix = 0; ix <= nx; ix++) a.push(iy * (nx + 1) + ix); return rev ? a.reverse() : a; };
  const col = (ix, rev) => { const a = []; for (let iy = 0; iy <= nz; iy++) a.push(iy * (nx + 1) + ix); return rev ? a.reverse() : a; };
  const bordas = [[row(nz, false), [0, 0, 1]], [col(nx, true), [1, 0, 0]], [row(0, true), [0, 0, -1]], [col(0, false), [-1, 0, 0]]];
  const matFace = o.matFace || material({ rampa: 'face', grad: { dir: [0, -1, 0], de: -.2, ate: F, cor: PAL.faceBaixo, forca: .8 }, estrias: [0, 40, 0], hachura: [.8, 24, .36, 1.2], salpico: [.05, .02, 14] });
  const faces = bordas.map(([idx, n]) => {
    const m = idx.length, pos = new Float32Array(m * 6), nor = new Float32Array(m * 6), uv = new Float32Array(m * 4), ind = [];
    for (let k = 0; k < m; k++) {
      const i = idx[k]; pos.set([X[i], 0, Z[i], X[i], -F, Z[i]], k * 6); nor.set([...n, ...n], k * 6); uv.set([k / (m - 1), 1, k / (m - 1), 0], k * 4);
      if (k < m - 1) { const a = 2 * k, b = a + 1, c = a + 2, d = a + 3; ind.push(a, b, c, b, d, c); }
    }
    const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); gg.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    gg.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); gg.setIndex(ind);
    const me = new THREE.Mesh(gg, matFace); me.frustumCulled = false; grupo.add(me); return { me, idx };
  });
  const T = { grupo, topo, faces, X, Z, H: Hh, lx, lz, nx, nz, fundo: F, NV };
  T.alturas = fn => {
    const p = g.attributes.position.array;
    for (let i = 0; i < NV; i++) { const y = fn(i, X[i], Z[i]); Hh[i] = y; p[i * 3 + 1] = y; }
    g.attributes.position.needsUpdate = true; g.computeVertexNormals();
    for (const f of faces) { const a = f.me.geometry.attributes.position; for (let k = 0; k < f.idx.length; k++) a.array[k * 6 + 1] = Hh[f.idx[k]]; a.needsUpdate = true; }
  };
  T.altura = (x, z) => {
    const fx = clamp((x + lx / 2) / lx * nx, 0, nx - 1e-4), fz = clamp((z + lz / 2) / lz * nz, 0, nz - 1e-4), ix = Math.floor(fx), iz = Math.floor(fz), ax = fx - ix, az = fz - iz, i = iz * (nx + 1) + ix;
    return lerp(lerp(Hh[i], Hh[i + 1], ax), lerp(Hh[i + nx + 1], Hh[i + nx + 2], ax), az);
  };
  S.add(grupo);
  return T;
}

// ───────────────────────── água (nível que sobe dentro do bloco, com espuma na margem) ─────────────────────────
export function agua(S, T, o = {}) {
  const g = new THREE.PlaneGeometry(T.lx, T.lz, T.nx, T.nz); g.rotateX(-Math.PI / 2);
  const aH = new THREE.BufferAttribute(new Float32Array(T.NV), 1); g.setAttribute('aH', aH);
  const mat = o.mat || material({ rampa: 'agua', agua: true, hachura: [.5, 20, .3, .2], salpico: [.0, .02, 10] });
  const topo = new THREE.Mesh(g, mat); topo.frustumCulled = false; topo.userData.semSombra = true;
  const matLado = o.matLado || material({ rampa: 'agua', hachura: [.6, 22, .34, 1.2], estrias: [.25, 30, .6] });
  const ins = .004, lados = [[T.lx, [0, 0, T.lz / 2 - ins], 0], [T.lz, [T.lx / 2 - ins, 0, 0], Math.PI / 2], [T.lx, [0, 0, -T.lz / 2 + ins], Math.PI], [T.lz, [-T.lx / 2 + ins, 0, 0], -Math.PI / 2]]
    .map(([len, p, ry]) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(len, 1).translate(0, .5, 0), matLado); m.position.set(...p); m.rotation.y = ry; m.userData.semSombra = true; return m; });
  const grupo = new THREE.Group(); grupo.add(topo, ...lados); S.add(grupo);
  const A = { grupo, topo, lados, mat, nivel: -T.fundo };
  A.set = y => {
    A.nivel = y; const vis = y > -T.fundo + .01; grupo.visible = vis; if (!vis) return;
    topo.position.y = y; mat.userData.u.uLevel.value = y;
    for (const l of lados) { l.scale.y = y + T.fundo; l.position.y = -T.fundo; }
    aH.array.set(T.H); aH.needsUpdate = true;
  };
  return A;
}

// ───────────────────────── vegetação em tufos (instanciada) ─────────────────────────
/** lista: [{x,z,s,t0}] — cada tufo brota em t0 (escala com back.out) e fica pousado no terreno */
export function tufos(S, T, lista, o = {}) {
  const r = rng(o.semente ?? 9), geo = new THREE.IcosahedronGeometry(1, 1), p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) { const k = 1 + (r() - .5) * .45; p.setXYZ(i, p.getX(i) * k, p.getY(i) * k * .8, p.getZ(i) * k); }
  geo.computeVertexNormals();
  const mat = o.mat || material({ rampa: 'mata', faixas: [.12, .32, .55, .8], hachura: [.7, 26, .36, .9], salpico: [.12, .06, 18], aspereza: [.25, 7] });
  const im = new THREE.InstancedMesh(geo, mat, lista.length); im.frustumCulled = false; S.add(im);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), vs = new THREE.Vector3(), vp = new THREE.Vector3();
  const dur = o.dur ?? .4;
  const back = k => { const c = 1.9; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); };
  const F = { im, lista };
  F.update = t => {
    lista.forEach((f, i) => {
      const k = clamp((t - f.t0) / dur), s = k <= 0 ? 0 : back(k) * f.s;
      e.set(0, f.rot ?? i * 2.4, 0); q.setFromEuler(e); vs.set(s, s, s); vp.set(f.x, T.altura(f.x, f.z) + s * .45, f.z);
      m4.compose(vp, q, vs); im.setMatrixAt(i, m4);
    });
    im.instanceMatrix.needsUpdate = true;
  };
  return F;
}

// ───────────────────────── base técnica + chão ─────────────────────────
/**
 * o: { lx, lz, fundo, alt (altura do plinto), deck:{x0,x1,prof,alt}, cor: rampas }
 * Devolve { grupo, piso (y do chão) }
 */
export function base(S, o = {}) {
  const lx = o.lx ?? 10, lz = o.lz ?? 8, F = o.fundo ?? 2.6, alt = o.alt ?? 1, y0 = -F - alt, G = new THREE.Group();
  const tp = texPainel(3), mPlain = material({ rampa: 'base', hachura: [.9, 22, .38, .7], salpico: [.03, .01, 12] });
  const mX = material({ rampa: 'base', mapa: tp, rep: [lz / 1.1, 1], hachura: [.9, 22, .38, .7], salpico: [.03, .01, 12] });
  const mZ = material({ rampa: 'base', mapa: tp, rep: [lx / 1.1, 1], hachura: [.9, 22, .38, .7], salpico: [.03, .01, 12] });
  const pl = new THREE.Mesh(new THREE.BoxGeometry(lx - .16, alt, lz - .16), [mX, mPlain, mPlain, mPlain, mZ, mPlain]); pl.position.y = y0 + alt / 2; G.add(pl);
  // friso escuro logo abaixo do bloco
  const mFriso = material({ rampa: 'base', faixas: [.5, .6, .7, .9] });
  const fr = new THREE.Mesh(new THREE.BoxGeometry(lx - .02, .08, lz - .02), mFriso); fr.position.y = -F - .04; G.add(fr);
  // deck na frente-esquerda com rampa e tubos
  const d = Object.assign({ x0: -lx / 2 - .4, x1: -.6, prof: 1.7, alt: .22 }, o.deck || {});
  const mDeck = material({ rampa: 'deck', hachura: [.85, 22, .38, .7], salpico: [.06, .03, 14] });
  const dk = new THREE.Mesh(new THREE.BoxGeometry(d.x1 - d.x0, d.alt, d.prof), mDeck); dk.position.set((d.x0 + d.x1) / 2, y0 + d.alt / 2, lz / 2 - .08 + d.prof / 2); G.add(dk);
  const mTubo = material({ rampa: 'base', faixas: [.15, .35, .55, .8], hachura: [.9, 24, .4, .9] });
  [-1, 1].forEach((s, i) => {
    const xm = d.x0 + (d.x1 - d.x0) * (.32 + i * .3);
    const curva = new THREE.CatmullRomCurve3([[xm, .25, lz / 2 + .1], [xm + .05, .25, lz / 2 + .7], [xm + .35, .22, lz / 2 + 1.1], [xm + .4, .22, lz / 2 + d.prof - .15]].map(([a, b, c]) => new THREE.Vector3(a, y0 + d.alt + b, c)));
    G.add(new THREE.Mesh(new THREE.TubeGeometry(curva, 40, .16, 12), mTubo));
    const tampa = new THREE.Mesh(new THREE.SphereGeometry(.16, 14, 10), mTubo); tampa.position.copy(curva.getPoint(1)); G.add(tampa);
  });
  // cones/marcos no deck
  const mCone = material({ rampa: 'base', faixas: [.2, .4, .6, .85] });
  for (let i = 0; i < 4; i++) { const c = new THREE.Mesh(new THREE.ConeGeometry(.07, .16, 4), mCone); c.position.set(d.x0 + .3 + i * (d.x1 - d.x0 - .6) / 3, y0 + d.alt + .08, lz / 2 + d.prof * .78); G.add(c); }
  // trilho azul duplo em volta do bloco (lados visíveis) + postes com lâmpada
  const mTr = material({ rampa: 'trilho', faixas: [.15, .35, .55, .8], hachura: [.6, 24, .36, .3] });
  const off = .2;
  [[-F + .14], [-F + .34]].forEach(([y]) => {
    const a = new THREE.Mesh(new THREE.BoxGeometry(lx + off * 2, .045, .045), mTr); a.position.set(0, y, lz / 2 + off); G.add(a);
    const b = new THREE.Mesh(new THREE.BoxGeometry(.045, .045, lz + off * 2), mTr); b.position.set(lx / 2 + off, y, 0); G.add(b);
  });
  const lamp = brilho(PAL.lampada), mPoste = material({ rampa: 'base', faixas: [.2, .4, .6, .85] });
  const halos = [];
  [[lx / 2 + off, lz / 2 + off], [-lx / 2 - off, lz / 2 + off], [lx / 2 + off, -lz / 2 - off]].forEach(([x, z]) => {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(.035, .045, F * .32 + alt, 8), mPoste); p.position.set(x, y0 + (F * .32 + alt) / 2, z); G.add(p);
    const l = new THREE.Mesh(new THREE.CylinderGeometry(.05, .05, .16, 10), lamp); l.position.set(x, y0 + F * .32 + alt + .08, z); l.userData.semSombra = true; G.add(l);
    halos.push(l.position.clone());
  });
  S.add(G);
  return { grupo: G, piso: y0, halos };
}
/**
 * Chão infinito de placas com degradê para perto da câmera, grelhas e cabos vermelhos serpenteando.
 * o: { y, tam, grelhas:[[x,z,larg,prof,rotY]], cabos:[[[x,z],...]] }
 */
export function chao(S, o = {}) {
  const y = o.y ?? -3.6, tam = o.tam ?? 120, G = new THREE.Group();
  const m = material({ rampa: 'chao', mapa: texChao(5), rep: [tam / 18, tam / 18], hachura: [.95, 20, .42, .75], salpico: [.05, .02, 9],
    grad: { dir: [1, 0, 1], de: o.gradDe ?? -2, ate: o.gradAte ?? 12, cor: PAL.chaoClaro, forca: .85 } });
  const p = new THREE.Mesh(new THREE.PlaneGeometry(tam, tam), m); p.rotation.x = -Math.PI / 2; p.position.y = y; G.add(p);
  const tg = texGrelha(), mg = material({ rampa: 'base', mapa: tg, hachura: [.8, 22, .38, .7] });
  (o.grelhas || []).forEach(([x, z, w, d, r]) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, .06, d), mg); b.position.set(x, y + .03, z); b.rotation.y = r || 0; G.add(b); });
  const mc = material({ rampa: 'vermelho', faixas: [.12, .3, .5, .8], hachura: [.7, 26, .36, .3], salpico: [0, 0, 1] });
  (o.cabos || []).forEach(pts => {
    const c = new THREE.CatmullRomCurve3(pts.map(([x, z]) => new THREE.Vector3(x, y + .07, z)));
    G.add(new THREE.Mesh(new THREE.TubeGeometry(c, Math.max(60, pts.length * 20), .065, 8), mc));
  });
  S.add(G);
  return { grupo: G, mat: m };
}

// ───────────────────────── cabos e bondinho ─────────────────────────
/** cabo suspenso de A a B (catenária aproximada), que se desenha com .mostrar(k ∈ [0,1]) */
export function cabo(S, A, B, o = {}) {
  const flecha = o.flecha ?? .35, n = 80;
  const P = u => new THREE.Vector3(lerp(A[0], B[0], u), lerp(A[1], B[1], u) - flecha * 4 * u * (1 - u), lerp(A[2], B[2], u));
  const curva = new THREE.CatmullRomCurve3(Array.from({ length: n + 1 }, (_, i) => P(i / n)));
  const g = new THREE.TubeGeometry(curva, n * 2, o.raio ?? .018, 6);
  const me = new THREE.Mesh(g, o.mat || material({ rampa: { c: ['#241a33', '#2c2140', '#3a2c50', '#4a3a60', '#5a4a70'] }, hachura: [0, 1, 0, 0], salpico: [0, 0, 1] }));
  me.userData.semSombra = !!o.semSombra; S.add(me);
  const total = g.index.count;
  return { me, P, mostrar: k => { g.setDrawRange(0, Math.floor(clamp(k) * total / 6) * 6); me.visible = k > 0; } };
}
/** cabine do bondinho: caixa creme com faixa de janelas, teto e haste */
export function cabine(S, o = {}) {
  const G = new THREE.Group(), s = o.escala ?? 1;
  const tj = textura(256, 128, (x, w, h) => { x.fillStyle = CV.FUNDO2; x.fillRect(12, 26, w - 24, 52); x.strokeStyle = CV.TINTA; x.lineWidth = 6; x.strokeRect(12, 26, w - 24, 52);
    for (let i = 1; i < 4; i++) { x.beginPath(); x.moveTo(12 + i * (w - 24) / 4, 26); x.lineTo(12 + i * (w - 24) / 4, 78); x.stroke(); } x.fillStyle = CV.LUZ; x.fillRect(20, 32, 40, 8); });
  const mc = material({ rampa: o.rampa || 'creme', mapa: tj, hachura: [.7, 30, .36, .6], salpico: [0, 0, 1] });
  const caixa = new THREE.Mesh(new THREE.BoxGeometry(.42 * s, .3 * s, .3 * s), mc); G.add(caixa);
  const teto = new THREE.Mesh(new THREE.BoxGeometry(.46 * s, .06 * s, .34 * s), material({ rampa: 'vermelho', faixas: [.12, .3, .5, .8] })); teto.position.y = .18 * s; G.add(teto);
  const haste = new THREE.Mesh(new THREE.CylinderGeometry(.012 * s, .012 * s, .22 * s, 6), material({ rampa: { c: ['#241a33', '#2c2140', '#3a2c50', '#4a3a60', '#5a4a70'] } })); haste.position.y = .31 * s; G.add(haste);
  S.add(G); G.userData.alturaHaste = .42 * s;
  return G;
}

// ───────────────────────── etiquetas técnicas (HTML + fio de nanquim) ─────────────────────────
/** cria o SVG dos fios de chamada sobre o palco */
export function camadaFios(parent = document.getElementById('stage')) {
  const ns = 'http://www.w3.org/2000/svg', s = document.createElementNS(ns, 'svg');
  s.setAttribute('width', VIDEO.w); s.setAttribute('height', VIDEO.h); s.setAttribute('class', 'layer'); s.style.pointerEvents = 'none'; parent.appendChild(s);
  return s;
}

// ───────────────────────── curvas de tempo ─────────────────────────
export const io = k => k < .5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;          // quad in-out
export const saida = k => 1 - (1 - k) ** 2;                                        // quad out
export const backOut = (k, c = 1.7) => k <= 0 ? 0 : 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2;
export const prog = (t, [a, b]) => clamp((t - a) / (b - a));

// ───────────────────────── metamorfose do relevo (a marca do estilo) ─────────────────────────
/**
 * Relevo que vira outro relevo numa onda contínua que atravessa o bloco.
 * o.estados: [fn(x,z) → y, ...]  (n paisagens, calculadas UMA vez)
 * o.passos:  [{ t:[t0,t1], u: fn(x,z) → 0..1 (ordem em que a frente passa), larg: largura da frente (.4),
 *               crista: altura da "ondulação" que viaja com a frente (+ incha, − afunda), modo: 'onda' | 'inchar' }]  (n−1)
 *   'onda'   → a frente varre o bloco na ordem de u;   'inchar' → tudo sobe junto, quem tem u menor vai na frente.
 * Devolve { E (arrays por estado), update(t) }. Chame M.update(t) dentro de S.update.
 */
export function metamorfose(T, o) {
  const NV = T.NV, ease = o.ease || io;
  const E = o.estados.map(fn => { const a = new Float32Array(NV); for (let i = 0; i < NV; i++) a[i] = fn(T.X[i], T.Z[i]); return a; });
  const U = o.passos.map(p => { const a = new Float32Array(NV); for (let i = 0; i < NV; i++) a[i] = p.u ? clamp(p.u(T.X[i], T.Z[i])) : 0; return a; });
  const n = o.passos.length, w = new Float32Array(n);
  const M = { E, U };
  M.update = t => {
    const ps = o.passos.map(p => ease(prog(t, p.t)));
    T.alturas(i => {
      let h = E[0][i];
      for (let k = 0; k < n; k++) {
        const p = o.passos[k], L = p.larg ?? .4;
        w[k] = p.modo === 'inchar' ? suave(0, 1, ps[k] * (1 + L) - U[k][i] * L) : onda(U[k][i], ps[k], L);
        h = lerp(h, E[k + 1][i], w[k]);
      }
      // cristas que viajam com cada frente (somem quando a frente seguinte passa)
      let b = 0;
      for (let k = 0; k < n; k++) { let c = (o.passos[k].crista ?? 0) * Math.sin(Math.PI * w[k]); for (let j = k + 1; j < n; j++) c *= 1 - w[j]; b += c; }
      return h + b;
    });
  };
  return M;
}

// ───────────────────────── adereços: casinha/estação e barco ─────────────────────────
/** casinha creme com telhado vermelho e mastro (estação, farol, casa). o: {x,y,z, rot, larg, alt, prof, rampa, teto} */
export function casinha(S, o = {}) {
  const G = new THREE.Group(), L = o.larg ?? .5, A = o.alt ?? .32, P = o.prof ?? .42;
  const mc = o.mat || material({ rampa: o.rampa || 'creme', hachura: [.8, 28, .36, .6], salpico: [0, 0, 1] }), mt = o.matTeto || material({ rampa: o.teto || 'vermelho', faixas: [.12, .3, .5, .8] });
  const c = new THREE.Mesh(new THREE.BoxGeometry(L, A, P), mc); c.position.y = A / 2; G.add(c);
  const t = new THREE.Mesh(new THREE.BoxGeometry(L + .08, .07, P + .08), mt); t.position.y = A + .035; G.add(t);
  if (o.mastro !== false) { const m = new THREE.Mesh(new THREE.CylinderGeometry(.03, .03, .35, 6), mt); m.position.set(L * .36, A + .18, 0); G.add(m); }
  G.position.set(o.x || 0, o.y || 0, o.z || 0); G.rotation.y = o.rot ?? .6; S.add(G);
  return G;
}
/** veleiro: casco + vela triangular de frente para a câmera. o: {escala, rot} */
export function barco(S, o = {}) {
  const G = new THREE.Group();
  const casco = new THREE.Mesh(new THREE.BoxGeometry(.62, .14, .22), material({ rampa: 'creme', faixas: [.12, .3, .5, .8] })); casco.position.y = .05; G.add(casco);
  const vg = new THREE.BufferGeometry(); vg.setAttribute('position', new THREE.Float32BufferAttribute([-.22, .12, 0, .2, .12, 0, -.12, .72, 0], 3)); vg.computeVertexNormals();
  const mv = material({ rampa: 'creme', faixas: [.05, .2, .35, .8], hachura: [.6, 30, .36, .3] }); mv.side = THREE.DoubleSide;
  G.add(new THREE.Mesh(vg, mv)); G.rotation.y = o.rot ?? .6; G.userData.escala = o.escala ?? 1; S.add(G);
  return G;
}

// ───────────────────────── HUD: título, etiquetas técnicas com fio de nanquim, carimbo ─────────────────────────
/** injeta o CSS padrão do HUD (classes .di-*) — chame uma vez, antes do SETUP */
export function estiloHUD() {
  if (document.getElementById('di-hud-css')) return;
  const st = document.createElement('style'); st.id = 'di-hud-css';
  st.textContent = `
.di-hud{position:absolute;inset:0;pointer-events:none}
.di-fig{position:absolute;left:0;right:0;top:92px;text-align:center;font:600 27px/1 'Chakra Petch';letter-spacing:.24em;color:${PAL.tinta}}
.di-tit{position:absolute;left:0;right:0;top:150px;text-align:center;font:700 128px/1 'Chakra Petch';color:#f39f6f;white-space:nowrap;
  -webkit-text-stroke:8px ${PAL.tinta};paint-order:stroke fill;text-shadow:9px 9px 0 #3e2f46;letter-spacing:.01em}
.di-tit .ch{display:inline-block}
.di-sub{position:absolute;left:0;right:0;top:302px;text-align:center;font:600 40px/1 'Chakra Petch';color:${PAL.tinta}}
.di-tag{position:absolute;left:54px;top:436px;display:none;align-items:stretch;background:#f6e7cf;border:5px solid ${PAL.tinta};box-shadow:9px 9px 0 #3e2f46}
.di-tag b{display:grid;place-items:center;background:#7b0f27;color:#f6e7cf;font:700 46px/1 'Chakra Petch';padding:0 18px;border-right:5px solid ${PAL.tinta}}
.di-tag .tx{padding:13px 22px 14px}
.di-tag h2{font:700 41px/1.05 'Chakra Petch';color:${PAL.tinta};white-space:nowrap}
.di-tag p{font:500 31px/1.2 'Chakra Petch';color:#7b0f27;margin-top:5px;white-space:nowrap}
.di-fios{position:absolute;inset:0}
.di-escala{position:absolute;left:54px;top:1812px;font:600 25px/1 'Chakra Petch';letter-spacing:.14em;color:${PAL.tinta};display:flex;align-items:center;gap:16px}
.di-escala i{display:block;width:150px;height:14px;border:4px solid ${PAL.tinta};background:linear-gradient(90deg,${PAL.tinta} 0 25%,#f6e7cf 25% 50%,${PAL.tinta} 50% 75%,#f6e7cf 75%)}`;
  document.head.appendChild(st);
}
/** quebra o título em letras e reduz a fonte até caber em `largura` px (chame no SETUP, depois das fontes) */
export function titulo(sel, largura = 980) {
  const el = typeof sel === 'string' ? document.querySelector(sel) : sel;
  el.innerHTML = '<span class="di-titIn">' + [...el.textContent].map(c => c === ' ' ? ' ' : `<span class="ch">${c}</span>`).join('') + '</span>';
  const inn = el.querySelector('.di-titIn');
  for (let i = 0; i < 60 && inn.offsetWidth > largura; i++) el.style.fontSize = (parseFloat(getComputedStyle(el).fontSize) - 2) + 'px';
  return el.querySelectorAll('.ch');
}
/**
 * Etiquetas técnicas: caixa creme com número + fio de nanquim até um ponto 3D (que pode se mover).
 * lista: [{ el:'#id' (div.di-tag já no HTML), t:[entra, sai], alvo: () => [x,y,z] }]; svg: o <svg class="di-fios">.
 * Entrada: a caixa abre por máscara (.32 s, cúbica), o fio corre (.3 s) e o anel do alvo estoura (back.out). Saída: some para a direita.
 */
export function etiquetas(S, lista, svg) {
  const NS = 'http://www.w3.org/2000/svg', box = typeof svg === 'string' ? document.querySelector(svg) : svg, ink = PAL.tinta;
  lista.forEach(g => {
    g.e = typeof g.el === 'string' ? document.querySelector(g.el) : g.el;
    g.l = document.createElementNS(NS, 'line'); g.c = document.createElementNS(NS, 'circle'); g.c0 = document.createElementNS(NS, 'circle');
    g.l.setAttribute('stroke', ink); g.l.setAttribute('stroke-width', 5); g.l.setAttribute('stroke-linecap', 'round');
    [g.c, g.c0].forEach((c, k) => { c.setAttribute('r', k ? 9 : 18); c.setAttribute('fill', k ? ink : 'none'); c.setAttribute('stroke', k ? ink : '#f6e7cf'); c.setAttribute('stroke-width', k ? 5 : 6); });
    g.c.style.filter = `drop-shadow(0 0 0 ${ink}) drop-shadow(2px 2px 0 ${ink}) drop-shadow(-2px -2px 0 ${ink})`;
    box.append(g.l, g.c, g.c0);
  });
  onTick(t => {
    for (const g of lista) {
      const kin = clamp((t - g.t[0]) / .32), kout = clamp((t - g.t[1]) / .24), vis = t >= g.t[0] && kout < 1;
      g.e.style.display = vis ? 'flex' : 'none';
      const ein = 1 - (1 - kin) ** 3, eout = kout ** 2;
      g.e.style.clipPath = `inset(-20px ${(eout ? 0 : (1 - ein) * 100)}% -20px ${eout * 100}%)`;
      const ln = clamp((t - g.t[0] - .14) / .3) * (1 - clamp((t - g.t[1] + .05) / .18));
      const [ax, ay] = [g.e.offsetLeft + 44, g.e.offsetTop + g.e.offsetHeight + 4], [fx, fy] = S.tela(...g.alvo());
      const dist = Math.hypot(fx - ax, fy - ay), fim = Math.max(0, 1 - 20 / Math.max(dist, 1));
      const lk = (1 - (1 - ln) ** 2) * fim, ex = lerp(ax, fx, lk), ey = lerp(ay, fy, lk);
      [['x1', ax], ['y1', ay], ['x2', ex], ['y2', ey]].forEach(([k, v]) => g.l.setAttribute(k, v.toFixed(1)));
      g.l.style.display = g.c0.style.display = ln > 0 ? '' : 'none';
      g.c0.setAttribute('cx', ax); g.c0.setAttribute('cy', ay);
      const dk = backOut(clamp((t - g.t[0] - .4) / .25), 2.2) * (1 - clamp((t - g.t[1]) / .15));
      g.c.setAttribute('cx', fx.toFixed(1)); g.c.setAttribute('cy', fy.toFixed(1)); g.c.setAttribute('r', (18 * dk).toFixed(2)); g.c.style.display = dk > 0 ? '' : 'none';
    }
  });
  return lista;
}
/** carimbo que "bate" em degraus de stop-motion (escala 1.45 → 1 em `degraus` passos) e assenta */
export function carimbar(el, t, t0, o = {}) {
  const e = typeof el === 'string' ? document.querySelector(el) : el, k = clamp((t - t0) / (o.dur ?? .2)), d = o.degraus ?? 4;
  e.style.display = t >= t0 ? '' : 'none';
  const q = Math.floor(k * d) / d; e.style.transform = `rotate(${o.rot ?? -14}deg) scale(${(o.de ?? 1.45) - ((o.de ?? 1.45) - 1) * q})`; e.style.opacity = Math.min(1, .3 + q);
}
