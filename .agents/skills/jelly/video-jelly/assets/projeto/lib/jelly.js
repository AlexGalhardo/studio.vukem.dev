// jelly.js — biblioteca do estilo "Jelly Bear" (gelatina / bala de goma), three.js módulo ES.
// Criaturas de GELATINA translúcida (transmissão + atenuação + verniz + bolhas internas) que BALANÇAM com
// molas determinísticas (squash & stretch, cisalhamento, ondas que sobem pelo corpo), sombra colorida
// translúcida, prato de porcelana num estúdio creme e HUD editorial (serifa itálica + painel de "espécime").
// Uso:  import * as JL from '../../lib/jelly.js';  const S = JL.palco({...});  S.update = t => {...}
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { MarchingCubes } from 'three/addons/objects/MarchingCubes.js';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
export { THREE, RoundedBoxGeometry };

// ───────────────────────── utilidades (tudo determinístico) ─────────────────────────
export const V3 = (a = 0, b = 0, c = 0) => Array.isArray(a) ? new THREE.Vector3(...a) : new THREE.Vector3(a, b, c);
export function rng(seed = 1) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const suave = (a, b, v) => { const k = clamp((v - a) / (b - a)); return k * k * (3 - 2 * k); };
export const fase = (t, t0, t1, ease = 'none') => gsap.parseEase(ease)(clamp((t - t0) / (t1 - t0)));
/** t dentro do loop (0..dur) */
export const ciclo = (t, per, off = 0) => (((t - off) % per) + per) % per;

// ───────────────────────── sabores (paleta de bala) ─────────────────────────
// cor = tinta da transmissão · fundo = atenuação (parte grossa) · miolo = brilho interno · borda = silhueta densa
export const SABORES = {
  morango:   { nome: 'Morango',        cor: '#ff5c68', fundo: '#ff1835', miolo: '#ff7a80', borda: '#c4001f' },
  limao:     { nome: 'Limão',          cor: '#b4f55a', fundo: '#62c800', miolo: '#d8ff8a', borda: '#3a8a00' },
  laranja:   { nome: 'Laranja',        cor: '#ffad4a', fundo: '#ff7a00', miolo: '#ffc47a', borda: '#d05000' },
  uva:       { nome: 'Uva',            cor: '#b882ff', fundo: '#7a2cff', miolo: '#d0a8ff', borda: '#5214c0' },
  abacaxi:   { nome: 'Abacaxi',        cor: '#ffe45a', fundo: '#ffb800', miolo: '#fff29a', borda: '#d89000' },
  framboesa: { nome: 'Framboesa azul', cor: '#5aa0ff', fundo: '#1a62ff', miolo: '#9cc8ff', borda: '#0a40c0' },
  tijolo:    { nome: 'Tijolo',         cor: '#ffb070', fundo: '#ff7420', miolo: '#ffc890', borda: '#d0500c' },
};
export const sabor = s => (typeof s === 'string' ? SABORES[s] || { nome: s, cor: s, fundo: s, miolo: s, borda: s } : s);

/** ajuste global (os sliders do HUD): firmeza multiplica a frequência das molas, amortecimento o fator de amortecimento */
export const AJUSTE = { firmeza: 1, amortecimento: 1, balanco: 1 };

// ───────────────────────── molas (respostas analíticas, seekáveis) ─────────────────────────
/** mola amortecida guiada por pulsos: em(t) = Σ a·e^(−ζωτ)·sin(ω_d τ). loop = dur → os pulsos do ciclo anterior
 *  continuam reverberando no começo (o vídeo fecha em loop sem salto). */
export function mola(o = {}) {
  return {
    freq: o.freq ?? 3.2, amort: o.amort ?? .14, loop: o.loop ?? (window.VIDEO?.dur || 0), pulsos: [],
    pulso(t, a = 1) { this.pulsos.push([t, a]); return this; },
    em(t) {
      const w = 2 * Math.PI * this.freq * AJUSTE.firmeza, z = clamp(this.amort * AJUSTE.amortecimento, .02, .9), wd = w * Math.sqrt(1 - z * z);
      let s = 0;
      for (const [t0, a] of this.pulsos) for (const sh of this.loop ? [0, this.loop] : [0]) {
        const tau = t - t0 + sh; if (tau > 0 && tau < 7 / (z * w)) s += a * Math.exp(-z * w * tau) * Math.sin(wd * tau);
      }
      return s * AJUSTE.balanco;
    },
  };
}

// ───────────────────────── jiggle (deformação no vertex shader, espaço do mundo) ─────────────────────────
// Um jiggle = um "corpo" que balança junto (ursinho + o que ele segura, parede inteira, carrinho…).
// Deforma em torno da base (jOrig) até a altura jAlt: squash (y encolhe, xz incha), cisalhamento ∝ h² na direção
// frente/lado e uma onda radial que sobe pelo corpo depois de cada impacto.
let JID = 0;
export function jiggle(o = {}) {
  const f = o.freq ?? 3.4, a = o.amort ?? .13;
  const J = {
    id: ++JID,
    u: { jOrig: { value: new THREE.Vector3() }, jFrente: { value: new THREE.Vector2(0, 1) }, jAlt: { value: o.altura ?? .5 },
      jSquash: { value: 0 }, jShear: { value: new THREE.Vector2() }, jRipA: { value: 0 }, jRipF: { value: 0 }, jOnda: { value: o.onda ?? 1.3 } },
    squash: mola({ freq: f, amort: a }), frente: mola({ freq: f * .78, amort: a }), lado: mola({ freq: f * .86, amort: a }),
    ondas: [], extra: { squash: 0, frente: 0, lado: 0 }, decai: o.decai ?? 4.5, fOnda: o.fOnda ?? 2.6,
    /** impacto no instante t: a = força (≈1 passo firme, 2 martelada), dir = [frente, lado] empurra o topo */
    impacto(t, a = 1, dir = [0, 0]) {
      this.squash.pulso(t, .11 * a); this.frente.pulso(t, dir[0] * .22 * a); this.lado.pulso(t, dir[1] * .22 * a);
      this.ondas.push([t, a]); return this;
    },
    /** quanto está balançando agora (0..~1) — bom para números do HUD */
    energia: 0,
    atualizar(t, obj) {
      if (obj) {
        obj.updateWorldMatrix(true, false);
        const e = obj.matrixWorld.elements; this.u.jOrig.value.set(e[12], e[13], e[14]);
        const fx = e[8], fz = e[10], n = Math.hypot(fx, fz) || 1; this.u.jFrente.value.set(fx / n, fz / n);
      }
      const sq = this.squash.em(t), sf = this.frente.em(t), sl = this.lado.em(t);
      this.u.jSquash.value = sq + this.extra.squash;
      this.u.jShear.value.set(sf + this.extra.frente, sl + this.extra.lado);
      let ra = 0, rf = 0, loop = window.VIDEO?.dur || 0;
      for (const [t0, a] of this.ondas) for (const sh of loop ? [0, loop] : [0]) {
        const tau = t - t0 + sh; if (tau <= 0) continue;
        const amp = .055 * a * Math.exp(-tau * this.decai / AJUSTE.amortecimento) * AJUSTE.balanco;
        if (amp > ra) { ra = amp; rf = 2 * Math.PI * this.fOnda * AJUSTE.firmeza * tau; }
      }
      this.u.jRipA.value = ra; this.u.jRipF.value = rf;
      this.energia = Math.min(1, Math.abs(sq) * 6 + Math.hypot(sf, sl) * 3 + ra * 8);
    },
  };
  return J;
}
/** jiggle neutro (objetos parados) */
export const PARADO = jiggle();

const JIG_GLSL = /* glsl */`
uniform vec3 jOrig; uniform vec2 jFrente; uniform float jAlt, jSquash, jRipA, jRipF, jOnda; uniform vec2 jShear;
vec3 jelly(vec3 p) {
  vec3 d = p - jOrig; float h = clamp(d.y / jAlt, 0., 1.6);
  d.y *= 1. - jSquash; d.xz *= 1. + .5 * jSquash * smoothstep(0., .5, h);
  vec2 lado = vec2(jFrente.y, -jFrente.x);
  d.xz += (jFrente * jShear.x + lado * jShear.y) * jAlt * h * h;
  d.xz *= 1. + jRipA * sin(6.2831853 * jOnda * h - jRipF) * smoothstep(0., .3, h);
  d.y += jAlt * jRipA * .35 * sin(6.2831853 * jOnda * h - jRipF - 1.2) * smoothstep(0., .3, h);
  return jOrig + d;
}`;
function injetarJiggle(sh, J) {
  Object.assign(sh.uniforms, J.u);
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\n' + JIG_GLSL)
    .replace('#include <project_vertex>', `vec4 jW = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
  jW = batchingMatrix * jW;
#endif
#ifdef USE_INSTANCING
  jW = instanceMatrix * jW;
#endif
jW = modelMatrix * jW; jW.xyz = jelly( jW.xyz );
vec4 mvPosition = viewMatrix * jW;
gl_Position = projectionMatrix * mvPosition;`)
    .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
  worldPosition.xyz = jelly( worldPosition.xyz );
#endif`);
}
/** liga o jiggle J a qualquer material (MeshStandard/Physical/Basic). extra(sh) permite injetar mais coisas. */
export function comJiggle(m, J = PARADO, extra) {
  m.onBeforeCompile = sh => { injetarJiggle(sh, J); if (extra) extra(sh); };
  m.customProgramCacheKey = () => 'jelly|' + (m.userData.chave || '');
  return m;
}

// ───────────────────────── materiais ─────────────────────────
const CACHE = new Map();
/** gelatina translúcida. o: {espessura, atenuacao, rug, brilho (miolo), borda, ior} */
export function gelatina(sab, J = PARADO, o = {}) {
  const S = sabor(sab), k = JSON.stringify([S.cor, J.id, o]);
  if (CACHE.has(k)) return CACHE.get(k);
  const m = new THREE.MeshPhysicalMaterial({
    color: S.cor, transmission: 1, thickness: o.espessura ?? .3, ior: o.ior ?? 1.36,
    attenuationColor: new THREE.Color(S.fundo), attenuationDistance: o.atenuacao ?? .5,
    roughness: o.rug ?? .2, clearcoat: 1, clearcoatRoughness: .03, specularIntensity: 1, envMapIntensity: o.env ?? 1.35,
  });
  const u = { jMiolo: { value: new THREE.Color(S.miolo) }, jBorda: { value: new THREE.Color(S.borda) }, jBrilho: { value: o.brilho ?? .22 }, jRim: { value: o.borda ?? .38 } };
  m.userData.chave = 'gel'; m.userData.u = u;
  comJiggle(m, J, sh => {
    Object.assign(sh.uniforms, u);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform vec3 jMiolo, jBorda; uniform float jBrilho, jRim;')
      .replace('#include <opaque_fragment>', `{ float ndv = saturate( dot( normal, geometryViewDir ) );
  outgoingLight += jMiolo * jBrilho * pow( ndv, 1.6 );                       // miolo luminoso
  outgoingLight = mix( outgoingLight, jBorda * .55, pow( 1. - ndv, 2.2 ) * jRim );  // borda mais densa
}
#include <opaque_fragment>`);
  });
  CACHE.set(k, m); return m;
}
/** plástico/verniz opaco (capacete, cabo), com jiggle opcional */
export function plastico(cor, J = PARADO, o = {}) {
  const m = new THREE.MeshPhysicalMaterial({ color: cor, roughness: o.rug ?? .32, metalness: o.metal ?? 0, clearcoat: o.verniz ?? .7, clearcoatRoughness: .12, envMapIntensity: o.env ?? 1 });
  return comJiggle(m, J);
}
export function fosco(cor, J = PARADO, o = {}) {
  const m = new THREE.MeshStandardMaterial({ color: cor, roughness: o.rug ?? .85, metalness: o.metal ?? 0, map: o.map || null, envMapIntensity: o.env ?? .8 });
  return comJiggle(m, J);
}
export function metal(cor = '#c9cdd2', J = PARADO, o = {}) {
  return comJiggle(new THREE.MeshPhysicalMaterial({ color: cor, roughness: o.rug ?? .28, metalness: 1, clearcoat: o.verniz ?? 0, envMapIntensity: 1.2 }), J);
}

// ───────────────────────── SDF → malha (marching cubes) ─────────────────────────
export const sdf = {
  elip(p, c, r) { const x = (p[0] - c[0]) / r[0], y = (p[1] - c[1]) / r[1], z = (p[2] - c[2]) / r[2]; const k0 = Math.hypot(x, y, z), k1 = Math.hypot(x / r[0], y / r[1], z / r[2]); return k1 < 1e-9 ? -Math.min(...r) : k0 * (k0 - 1) / k1; },
  bola(p, c, r) { return Math.hypot(p[0] - c[0], p[1] - c[1], p[2] - c[2]) - r; },
  capsula(p, a, b, r) { const pa = [p[0] - a[0], p[1] - a[1], p[2] - a[2]], ba = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]; const h = clamp((pa[0] * ba[0] + pa[1] * ba[1] + pa[2] * ba[2]) / (ba[0] ** 2 + ba[1] ** 2 + ba[2] ** 2)); return Math.hypot(pa[0] - ba[0] * h, pa[1] - ba[1] * h, pa[2] - ba[2] * h) - r; },
  caixa(p, c, b, r = 0) { const q = [Math.abs(p[0] - c[0]) - b[0] + r, Math.abs(p[1] - c[1]) - b[1] + r, Math.abs(p[2] - c[2]) - b[2] + r]; return Math.hypot(Math.max(q[0], 0), Math.max(q[1], 0), Math.max(q[2], 0)) + Math.min(Math.max(q[0], q[1], q[2]), 0) - r; },
  uniao(a, b, k) { if (k <= 0) return Math.min(a, b); const h = clamp(.5 + .5 * (b - a) / k); return lerp(b, a, h) - k * h * (1 - h); },
  menos(a, b, k = 0) { if (k <= 0) return Math.max(a, -b); const h = clamp(.5 - .5 * (a + b) / k); return lerp(a, -b, h) + k * h * (1 - h); },
};
/** malha suave de uma função distância f([x,y,z]) dentro da caixa [min,max]. res ~48–96. */
export function malhaSDF(f, min, max, res = 64) {
  const c = [0, 1, 2].map(i => (min[i] + max[i]) / 2), half = Math.max(...[0, 1, 2].map(i => max[i] - min[i])) / 2 * 1.12;
  const mc = new MarchingCubes(res, new THREE.MeshBasicMaterial(), false, false, 400000);
  mc.isolation = 0; const F = mc.field, hs = mc.halfsize, p = [0, 0, 0];
  for (let z = 0; z < res; z++) for (let y = 0; y < res; y++) for (let x = 0; x < res; x++) {
    p[0] = c[0] + (x - hs) / hs * half; p[1] = c[1] + (y - hs) / hs * half; p[2] = c[2] + (z - hs) / hs * half;
    F[x + y * res + z * res * res] = -f(p);
  }
  mc.update();
  const n = mc.count, src = mc.geometry.attributes.position.array, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) for (let j = 0; j < 3; j++) pos[i * 3 + j] = c[j] + src[i * 3 + j] * half;
  let g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g = mergeVertices(g, 1e-5); g.computeVertexNormals(); g.computeBoundingSphere();
  mc.geometry.dispose(); return g;
}
/** pontos dentro do volume (d < -margem), para bolhas e pontinhos */
export function pontosDentro(f, min, max, n, seed = 7, margem = .02) {
  const r = rng(seed), out = []; let guard = 0;
  while (out.length < n && guard++ < n * 400) { const p = [lerp(min[0], max[0], r()), lerp(min[1], max[1], r()), lerp(min[2], max[2], r())]; if (f(p) < -margem) out.push(p); }
  return out;
}

// ───────────────────────── bolhas e pontinhos suspensos ─────────────────────────
const GEO_BOLHA = new THREE.IcosahedronGeometry(1, 2);
/** InstancedMesh de pontinhos escuros + bolhas claras nas posições dadas (coordenadas locais do pai) */
export function bolhas(pts, sab, J = PARADO, o = {}) {
  const S = sabor(sab), r = rng(o.seed ?? 3), g = new THREE.Group();
  const escuro = new THREE.Color(S.borda).multiplyScalar(.25);
  const mE = comJiggle(new THREE.MeshStandardMaterial({ color: escuro, roughness: .5 }), J);
  const mC = comJiggle(new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: .08, clearcoat: 1, emissive: new THREE.Color(S.miolo).lerp(new THREE.Color('#fff'), .6), emissiveIntensity: .55 }), J);
  const fr = o.claras ?? .3, es = o.escala ?? 1;
  const nC = Math.round(pts.length * fr), nE = pts.length - nC;
  const iE = new THREE.InstancedMesh(GEO_BOLHA, mE, Math.max(1, nE)), iC = new THREE.InstancedMesh(GEO_BOLHA, mC, Math.max(1, nC));
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler();
  let a = 0, b = 0;
  pts.forEach((p, i) => {
    const clara = i < nC; E.set(r() * 6, r() * 6, r() * 6); Q.setFromEuler(E);
    const s = (clara ? lerp(.008, .022, r() ** 2) : lerp(.006, .013, r())) * es;
    M.compose(V3(p), Q, V3(s, s * (clara ? 1 : .7), s)); (clara ? iC : iE).setMatrixAt(clara ? b++ : a++, M);
  });
  iE.count = nE; iC.count = nC; iE.frustumCulled = iC.frustumCulled = false;
  g.add(iE, iC); return g;
}

// ───────────────────────── ursinho de goma paramétrico (malha única suave + esqueleto) ─────────────────────────
// Coordenadas locais com altura ~1 (pés em y=0, olha para +z). Ossos: raiz, tronco, cabeca, bracoE, bracoD, pernaE, pernaD.
const UP = {
  tronco: p => sdf.elip(p, [0, .40, 0], [.255, .285, .19]),
  cabeca: p => { const x = Math.abs(p[0]); let d = sdf.elip(p, [0, .80, 0], [.235, .205, .182]); d = sdf.uniao(d, sdf.elip(p, [0, .755, .13], [.105, .08, .09]), .05); return sdf.uniao(d, sdf.elip([x, p[1], p[2]], [.168, .962, -.01], [.078, .074, .05]), .035); },
  bracoE: p => sdf.capsula(p, [.19, .57, .02], [.31, .40, .11], .07),
  bracoD: p => sdf.capsula(p, [-.19, .57, .02], [-.31, .40, .11], .07),
  pernaE: p => sdf.capsula(p, [.13, .23, 0], [.15, .085, .05], .088),
  pernaD: p => sdf.capsula(p, [-.13, .23, 0], [-.15, .085, .05], .088),
};
const PARTES = ['tronco', 'cabeca', 'bracoE', 'bracoD', 'pernaE', 'pernaD'];
const PIVO = { raiz: [0, 0, 0], tronco: [0, .24, 0], cabeca: [0, .63, 0], bracoE: [.19, .57, .02], bracoD: [-.19, .57, .02], pernaE: [.13, .24, 0], pernaD: [-.13, .24, 0] };
const PAI = { tronco: 'raiz', cabeca: 'tronco', bracoE: 'tronco', bracoD: 'tronco', pernaE: 'raiz', pernaD: 'raiz' };
export const MAO = { bracoE: [.12, -.17, .09], bracoD: [-.12, -.17, .09] }; // ponta do braço no espaço do osso
const sdUrso = p => { const t = UP.tronco(p), c = UP.cabeca(p); let d = sdf.uniao(t, c, .045); d = sdf.uniao(d, Math.min(UP.bracoE(p), UP.bracoD(p)), .028); return sdf.uniao(d, Math.min(UP.pernaE(p), UP.pernaD(p)), .04); };
let GEO_URSO = null;
function geoUrso(res = 84) {
  if (GEO_URSO) return GEO_URSO;
  const g = malhaSDF(sdUrso, [-.42, -.02, -.24], [.42, 1.06, .3], res);
  const P = g.attributes.position, n = P.count, si = new Uint16Array(n * 4), sw = new Float32Array(n * 4), p = [0, 0, 0];
  for (let i = 0; i < n; i++) {
    p[0] = P.getX(i); p[1] = P.getY(i); p[2] = P.getZ(i);
    const d = PARTES.map(k => UP[k](p)), dm = Math.min(...d);
    const w = d.map((x, j) => [j + 1, Math.exp(-(x - dm) / .022)]).sort((a, b) => b[1] - a[1]).slice(0, 4);
    const s = w.reduce((a, x) => a + x[1], 0);
    w.forEach(([j, x], k) => { si[i * 4 + k] = j; sw[i * 4 + k] = x / s; });
  }
  g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4)); g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4));
  return (GEO_URSO = g);
}
let GEO_COLETE = null;
function geoColete() {
  if (GEO_COLETE) return GEO_COLETE;
  const f = p => {
    const d0 = UP.tronco(p); let d = Math.max(d0 - .03, -d0 - .004);
    d = Math.max(d, .27 - p[1], p[1] - .585);
    d = sdf.menos(d, Math.min(UP.bracoE(p), UP.bracoD(p)) - .022, .01);
    d = Math.max(d, -sdf.caixa(p, [0, .5, .2], [.022, .12, .12]));               // abertura do zíper
    return d;
  };
  return (GEO_COLETE = malhaSDF(f, [-.33, .24, -.25], [.33, .62, .25], 72));
}
function geoCapacete() {
  const g = new THREE.Group(), R = .168;
  const pts = []; for (let i = 0; i <= 24; i++) { const a = (i / 24) * Math.PI / 2; pts.push(new THREE.Vector2(Math.sin(a) * R, Math.cos(a) * R * .86)); }
  pts.push(new THREE.Vector2(R + .016, -.004), new THREE.Vector2(R + .018, -.016), new THREE.Vector2(R - .004, -.012));
  const casco = new THREE.LatheGeometry(pts.reverse(), 48);
  const crista = new THREE.TorusGeometry(R * .93, .013, 8, 40, Math.PI); crista.rotateY(Math.PI / 2); crista.scale(1, .9, 1);
  const aba = new THREE.CylinderGeometry(R * 1.02, R * 1.02, .012, 40, 1, false, -Math.PI * .42, Math.PI * .84); aba.scale(1, 1, 1.45); aba.translate(0, -.008, .012);
  return { casco, crista, aba };
}
/**
 * Ursinho de goma. o: {sabor, altura (0.6), capacete: cor|false, colete: cor|false, listra, olhos (true), seed}
 * Retorna U = {grupo, ossos, jig, mao:{E,D}, pose(p), atualizar(t), sombra}.
 */
export function ursinho(o = {}) {
  const S = sabor(o.sabor || 'morango'), H = o.altura ?? .6, J = jiggle({ altura: H * 1.05, freq: o.freq ?? 3.3, amort: o.amort ?? .12 });
  const grupo = new THREE.Group(), corpo = new THREE.Group(); corpo.scale.setScalar(H); grupo.add(corpo);
  const mat = gelatina(S, J, o.gel);
  const malha = new THREE.SkinnedMesh(geoUrso(), mat); malha.frustumCulled = false; corpo.add(malha);
  const ossos = {}, lista = [];
  for (const k of ['raiz', 'tronco', 'cabeca', 'bracoE', 'bracoD', 'pernaE', 'pernaD']) {
    const b = new THREE.Bone(); b.name = k; const pv = PIVO[k], pp = PAI[k] ? PIVO[PAI[k]] : [0, 0, 0];
    b.position.set(pv[0] - pp[0], pv[1] - pp[1], pv[2] - pp[2]); ossos[k] = b; lista.push(b);
    if (PAI[k]) ossos[PAI[k]].add(b);
  }
  malha.add(ossos.raiz); malha.bind(new THREE.Skeleton(lista));
  // bolhas por osso (seguem o esqueleto)
  const r = rng(o.seed ?? 11), pts = pontosDentro(sdUrso, [-.4, 0, -.22], [.4, 1.02, .28], o.bolhas ?? 340, o.seed ?? 11, .022);
  const porOsso = {};
  for (const p of pts) { const d = PARTES.map(k => UP[k](p)); const k = PARTES[d.indexOf(Math.min(...d))]; (porOsso[k] ||= []).push([p[0] - PIVO[k][0], p[1] - PIVO[k][1], p[2] - PIVO[k][2]]); }
  for (const k in porOsso) ossos[k].add(bolhas(porOsso[k], S, J, { seed: r() * 1e6 | 0, escala: 1 / 1 }));
  // olhos e nariz (opacos, brilhantes)
  if (o.olhos !== false) {
    const mo = comJiggle(new THREE.MeshPhysicalMaterial({ color: '#160b0b', roughness: .06, clearcoat: 1, clearcoatRoughness: .02 }), J);
    for (const s of [-1, 1]) { const e = new THREE.Mesh(GEO_BOLHA, mo); e.scale.set(.03, .034, .022); e.position.set(s * .082 - PIVO.cabeca[0], .835 - PIVO.cabeca[1], .163); ossos.cabeca.add(e); }
    const nz = new THREE.Mesh(GEO_BOLHA, gelatina({ ...S, cor: S.borda, fundo: S.borda }, J)); nz.scale.set(.03, .022, .02); nz.position.set(0, .79 - PIVO.cabeca[1], .212); ossos.cabeca.add(nz);
  }
  // capacete de obra (plástico) e colete com faixa refletiva
  if (o.capacete) {
    const G = geoCapacete(), mc = plastico(o.capacete, J, { rug: .28, verniz: .8 }), cap = new THREE.Group();
    for (const k of ['casco', 'crista', 'aba']) cap.add(new THREE.Mesh(G[k], mc));
    cap.position.set(0, .935 - PIVO.cabeca[1], -.012); cap.rotation.x = -.12; ossos.cabeca.add(cap);
  }
  if (o.colete) {
    const m = new THREE.MeshStandardMaterial({ color: o.colete, roughness: .8 });
    m.userData.chave = 'colete';
    const fx = new THREE.Color(o.listra || '#e9eef2');
    comJiggle(m, J, sh => {
      sh.uniforms.cListra = { value: fx };
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying float vLy;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvLy = position.y;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vLy; uniform vec3 cListra;')
        .replace('#include <metalnessmap_fragment>', `#include <metalnessmap_fragment>
float lst = smoothstep(.003,0.,abs(vLy-.40)-.022) + smoothstep(.003,0.,abs(vLy-.50)-.016);
diffuseColor.rgb = mix(diffuseColor.rgb, cListra, lst); roughnessFactor = mix(roughnessFactor, .3, lst); metalnessFactor = mix(metalnessFactor, .55, lst);`);
    });
    const v = new THREE.Mesh(geoColete(), m); v.position.set(-PIVO.tronco[0], -PIVO.tronco[1], -PIVO.tronco[2]); ossos.tronco.add(v);
  }
  // mãos (pontos de engate para ferramentas)
  const mao = {};
  for (const [k, lado] of [['bracoE', 'E'], ['bracoD', 'D']]) { const m = new THREE.Object3D(); m.position.set(...MAO[k]); ossos[k].add(m); mao[lado] = m; }
  // sombra colorida
  const sombra = sombraColorida({ cor: S.cor, miolo: S.miolo, raio: H * .42 });
  const U = {
    grupo, corpo, malha, ossos, jig: J, mao, sombra, H, sabor: S, mat,
    /** p: {tronco:[x,y,z], cabeca, bracoE, bracoD, pernaE, pernaD, sobe} (radianos; sobe em unidades de altura) */
    pose(p = {}) {
      for (const k of PARTES) { const v = p[k] || [0, 0, 0]; ossos[k].rotation.set(v[0], v[1], v[2]); }
      ossos.raiz.position.y = (p.sobe || 0);
    },
    atualizar(t) {
      J.atualizar(t, grupo);
      sombra.posicionar(J.u.jOrig.value, 1 + J.u.jSquash.value * .8);
    },
  };
  return U;
}
/** passo de caminhada: t, período de um passo (s), amplitude → pose parcial + instante do pé no chão */
export function andar(t, passo = .32, amp = 1, off = 0) {
  const ph = ((t - off) / passo) * Math.PI, s = Math.sin(ph), c = Math.cos(ph);
  return {
    pernaE: [.5 * s * amp, 0, 0], pernaD: [-.5 * s * amp, 0, 0],
    tronco: [.04 * amp, 0, .05 * s * amp], cabeca: [0, 0, -.04 * s * amp],
    bracoE: [-.35 * s * amp, 0, 0], bracoD: [.35 * s * amp, 0, 0],
    sobe: .022 * Math.abs(c) * amp,
  };
}
/** instantes em que o pé toca o chão numa caminhada (para registrar impactos) */
export const pisadas = (t0, t1, passo = .32, off = 0) => { const out = []; for (let k = Math.ceil((t0 - off) / passo - .5); off + (k + .5) * passo <= t1; k++) out.push(off + (k + .5) * passo); return out; };
/** mistura duas poses */
export function mistura(a, b, k) {
  const o = {}; for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
    const x = a[key] ?? (key === 'sobe' ? 0 : [0, 0, 0]), y = b[key] ?? (key === 'sobe' ? 0 : [0, 0, 0]);
    o[key] = Array.isArray(x) ? x.map((v, i) => lerp(v, y[i], k)) : lerp(x, y, k);
  } return o;
}

// ───────────────────────── sombra colorida (luz atravessa a goma e tinge o prato) ─────────────────────────
let LUZ_DIR = new THREE.Vector3(.55, 1, -.45).normalize(), PISO = .03;
const TEX_SOMBRA = new Map();
function texSombra(cor, miolo) {
  const k = cor + miolo; if (TEX_SOMBRA.has(k)) return TEX_SOMBRA.get(k);
  const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d');
  const tint = new THREE.Color(cor).lerp(new THREE.Color('#fff'), .05), hsl = {}; tint.getHSL(hsl); tint.setHSL(hsl.h, Math.min(1, hsl.s * 1.1), Math.min(.62, hsl.l));
  const g = x.createRadialGradient(128, 128, 0, 128, 128, 128);
  const css = (col, a) => { const cc = new THREE.Color('#fff').lerp(col, a); return '#' + cc.getHexString(); };
  g.addColorStop(0, css(tint, .62)); g.addColorStop(.35, css(tint, .5)); g.addColorStop(.7, css(tint, .18)); g.addColorStop(1, '#ffffff');
  x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; TEX_SOMBRA.set(k, t); return t;
}
let TEX_CAUSTICA = null;
function texCaustica() {
  if (TEX_CAUSTICA) return TEX_CAUSTICA;
  const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d');
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.4, 'rgba(255,255,255,.45)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 128, 128); return (TEX_CAUSTICA = new THREE.CanvasTexture(c));
}
/** o: {cor, miolo, raio, alonga (1.5), altura (para deslocar com a luz), forma: [sx, sz] (retângulo suave)} */
export function sombraColorida(o = {}) {
  const g = new THREE.Group(), R = o.raio ?? .2, al = o.alonga ?? 1.55, alt = o.altura ?? R * 1.6;
  const m = new THREE.MeshBasicMaterial({ map: texSombra(o.cor || '#f33', o.miolo || '#f88'), blending: THREE.MultiplyBlending, transparent: true, premultipliedAlpha: true, depthWrite: false, toneMapped: false });
  const geo = new THREE.PlaneGeometry(1, 1); geo.rotateX(-Math.PI / 2);
  const sb = new THREE.Mesh(geo, m); sb.renderOrder = 2; g.add(sb);
  const cm = new THREE.MeshBasicMaterial({ map: texCaustica(), color: new THREE.Color(o.miolo || '#fff').lerp(new THREE.Color('#fff'), .35), blending: THREE.AdditiveBlending, transparent: true, opacity: o.caustica ?? .28, depthWrite: false, toneMapped: false });
  const cs = new THREE.Mesh(geo, cm); cs.renderOrder = 3; g.add(cs);
  const ct = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: texSombra('#555', '#555'), blending: THREE.MultiplyBlending, transparent: true, premultipliedAlpha: true, depthWrite: false, toneMapped: false, opacity: .5 })); ct.renderOrder = 2; g.add(ct);
  const fx = o.forma ? o.forma[0] : 1, fz = o.forma ? o.forma[1] : 1;
  const ang = Math.atan2(-LUZ_DIR.x, -LUZ_DIR.z), off = alt / LUZ_DIR.y * .45;
  g.posicionar = (p, k = 1) => {
    const dx = -LUZ_DIR.x / Math.hypot(LUZ_DIR.x, LUZ_DIR.z), dz = -LUZ_DIR.z / Math.hypot(LUZ_DIR.x, LUZ_DIR.z);
    g.position.set(p.x, PISO + .002, p.z);
    sb.position.set(dx * off * .55, 0, dz * off * .55); sb.rotation.y = ang; sb.scale.set(R * 2.3 * fx * k, 1, R * 2.3 * al * fz * k);
    cs.position.set(dx * off * .35, .001, dz * off * .35); cs.rotation.y = ang; cs.scale.set(R * 1.1 * fx, 1, R * 1.3 * fz);
    ct.position.set(0, -.0005, 0); ct.scale.set(R * 1.7 * fx, 1, R * 1.5 * fz);
  };
  g.posicionar(V3(...(o.pos || [0, 0, 0])));
  return g;
}

// ───────────────────────── estúdio creme + prato de porcelana ─────────────────────────
function gradienteFundo(cores) {
  const c = document.createElement('canvas'); c.width = 4; c.height = 512; const x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 0, 512); cores.forEach((k, i) => g.addColorStop(i / (cores.length - 1), k)); x.fillStyle = g; x.fillRect(0, 0, 4, 512);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
/**
 * Palco: renderer + cena + luz de estúdio suave lateral + ambiente (reflexos nítidos) + chão creme infinito.
 * o: {fov, fundo:[topo, base], chao, luz:{dir, forca}, ambiente, exposicao, piso}
 */
export function palco(o = {}) {
  const V = window.VIDEO;
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = o.exposicao ?? 1;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.transmissionResolutionScale = o.resTransmissao ?? 1;
  renderer.domElement.className = 'layer';
  document.getElementById('stage').prepend(renderer.domElement);
  const vin = document.createElement('div'); vin.className = 'layer'; vin.style.cssText = `background:radial-gradient(ellipse 85% 70% at 50% 58%,rgba(0,0,0,0) 55%,rgba(60,52,44,${o.vinheta ?? .12}) 100%);pointer-events:none`;
  renderer.domElement.after(vin);
  const scene = new THREE.Scene();
  const fundo = o.fundo || ['#e6e4e0', '#ebe9e5', '#dedbd6'];
  scene.background = gradienteFundo(fundo);
  scene.fog = new THREE.Fog(o.neblina || '#e6e4e0', o.neblinaPerto ?? 8, o.neblinaLonge ?? 16);
  const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), .03).texture; scene.environmentIntensity = o.ambiente ?? .75;
  const camera = new THREE.PerspectiveCamera(o.fov ?? 30, V.w / V.h, .05, 80);
  PISO = o.piso ?? PISO;
  if (o.luz?.dir) LUZ_DIR = V3(o.luz.dir).normalize();
  const hemi = new THREE.HemisphereLight('#fffaf2', '#d8d0c4', o.hemi ?? .9); scene.add(hemi);
  const sol = new THREE.DirectionalLight('#fff6ea', o.luz?.forca ?? 2.4);
  sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048); sol.shadow.bias = -.0004; sol.shadow.normalBias = .02; sol.shadow.radius = 6; sol.shadow.blurSamples = 16;
  scene.add(sol, sol.target);
  const preenche = new THREE.DirectionalLight('#f4f0ff', o.preenche ?? 1.1); scene.add(preenche, preenche.target);
  const chao = new THREE.Mesh(new THREE.CircleGeometry(40, 64).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: o.chao || '#dcd9d4', roughness: .95 }));
  chao.receiveShadow = true; scene.add(chao);
  const S = {
    THREE, renderer, scene, camera, sol, hemi, preenche, chao, update: null, hud: [],
    /** aponta a luz principal (e a caixa de sombra) para a área */
    luz(centro = [0, 0, 0], raio = 2.2) {
      const c = V3(centro); sol.target.position.copy(c); sol.position.copy(c).addScaledVector(LUZ_DIR, raio * 3);
      preenche.target.position.copy(c); preenche.position.copy(c).add(V3(-1, .6, 1).multiplyScalar(raio * 2));
      const sc = sol.shadow.camera; sc.left = sc.bottom = -raio; sc.right = sc.top = raio; sc.near = .1; sc.far = raio * 7; sc.updateProjectionMatrix();
    },
    /** câmera orbital: alvo, distância, azimute (graus, 0 = de frente), elevação (graus) */
    orbita(alvo, dist, az, el, fov) {
      const a = az * Math.PI / 180, e = el * Math.PI / 180, A = V3(alvo);
      camera.position.set(A.x + dist * Math.cos(e) * Math.sin(a), A.y + dist * Math.sin(e), A.z + dist * Math.cos(e) * Math.cos(a));
      camera.lookAt(A); if (fov) { camera.fov = fov; } camera.updateProjectionMatrix();
    },
  };
  S.luz([0, 0, 0], o.raioLuz ?? 2.2);
  onTick(t => {
    if (S.update) S.update(t);
    for (const h of S.hud) h(t);
    renderer.render(scene, camera);
  });
  return S;
}
/** prato de porcelana branca (torno). o: {raio, fundo (y do piso), cor} → mesh; PISO = o.piso */
export function prato(o = {}) {
  const R = o.raio ?? 1.2, f = o.fundo ?? .03, pts = [];
  const add = (r, y) => pts.push(new THREE.Vector2(r, y));
  add(0, .004); add(R * .6, .004); add(R * .62, 0); add(R * .66, 0); add(R * .7, .012);
  for (let i = 0; i <= 10; i++) { const k = i / 10; add(lerp(R * .74, R * 1.0, k), lerp(.018, .07, k * k)); }
  add(R * 1.012, .082); add(R * 1.016, .092); add(R * 1.008, .1); add(R * .995, .1);
  for (let i = 0; i <= 12; i++) { const k = i / 12; add(lerp(R * .985, R * .74, k), lerp(.096, f, Math.sqrt(k))); }
  add(R * .7, f); add(0, f);
  const geo = new THREE.LatheGeometry(pts, 160);
  const m = new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({ color: o.cor || '#fbfaf7', roughness: .2, clearcoat: 1, clearcoatRoughness: .05, envMapIntensity: .9, side: THREE.DoubleSide }));
  m.castShadow = m.receiveShadow = true; PISO = f;
  const sp = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: texSombra('#6a645c', '#6a645c'), blending: THREE.MultiplyBlending, transparent: true, premultipliedAlpha: true, depthWrite: false, toneMapped: false }));
  sp.scale.set(R * 2.55, 1, R * 2.55); sp.position.set(-LUZ_DIR.x * .08, .0015, -LUZ_DIR.z * .08 + .03); sp.renderOrder = 1; m.add(sp);
  return m;
}
export const piso = () => PISO;

// ───────────────────────── peças de obra (goma + plástico + madeira) ─────────────────────────
/** tijolo baiano de goma (8 furos aparentes na face da frente). Dimensões ~ [.2, .09, .1] na escala 1. */
let GEO_TIJOLO = null;
export const TIJOLO = [.2, .09, .1];
export function geoTijolo() {
  if (GEO_TIJOLO) return GEO_TIJOLO;
  const [L, A, P] = TIJOLO.map(x => x / 2);
  const f = p => {
    let d = sdf.caixa(p, [0, 0, 0], [L, A, P], .012);
    for (const x of [-.0675, -.0225, .0225, .0675]) for (const y of [-.0185, .0185]) d = Math.max(d, -sdf.caixa(p, [x, y, 0], [.0165, .013, P + .02], .004));
    for (const x of [-.09, .09]) d = Math.max(d, -sdf.caixa(p, [x * 1.08, 0, P], [.004, A * .7, .003], .001));
    return d;
  };
  return (GEO_TIJOLO = malhaSDF(f, [-L, -A, -P], [L, A, P], 96));
}
export function tijolo(J = PARADO, o = {}) {
  const m = new THREE.Mesh(geoTijolo(), gelatina(o.sabor || 'tijolo', J, { espessura: .14, atenuacao: .42, brilho: .16, ...(o.gel || {}) }));
  return m;
}
/** argamassa (cinza fosco, levemente irregular) */
export function argamassa(w, h, d, J = PARADO, seed = 1) {
  const g = new RoundedBoxGeometry(w, h, d, 2, Math.min(h, d) * .45), P = g.attributes.position, r = rng(seed);
  for (let i = 0; i < P.count; i++) P.setY(i, P.getY(i) * (1 + (r() - .5) * .5));
  g.computeVertexNormals();
  return new THREE.Mesh(g, fosco('#c4beb4', J, { rug: .95 }));
}
/** parede de tijolos meia-subida (cursos desencontrados, juntas de argamassa).
 *  o: {cursos (nº de cursos completos, 2), porCurso (4), ultimo (tijolos no curso de cima, 2), alinhar ('esq'|'dir'), J, gel} → {grupo, topo:[tijolos de cima], alt, cursos:[[tijolos]]} */
export function parede(o = {}) {
  const g = new THREE.Group(), J = o.J || PARADO, [L, A, P] = TIJOLO, jt = .012, n = o.porCurso ?? 4, cursos = o.cursos ?? 2, passo = L + jt;
  const linhas = [];
  for (let c = 0; c <= cursos; c++) {
    const y = PISO + jt + c * (A + jt) + A / 2, desl = c % 2 ? passo / 2 : 0, qtd = c === cursos ? (o.ultimo ?? 2) : n, linha = [];
    const i0 = c === cursos && o.alinhar === 'dir' ? n - qtd : 0;
    const xs = Array.from({ length: qtd }, (_, i) => (i + i0 - (n - 1) / 2) * passo + desl);
    xs.forEach((x, i) => {
      const tj = tijolo(J, { gel: o.gel }); tj.position.set(x, y, 0); g.add(tj); linha.push(tj);
      if (i < qtd - 1) { const v = argamassa(jt * 1.25, A * .95, P * .88, J, c * 10 + i); v.position.set(x + passo / 2, y, 0); g.add(v); }
    });
    const ag = argamassa(qtd * passo + .004, jt * 1.25, P * 1.05, J, c + 50); ag.position.set((xs[0] + xs[qtd - 1]) / 2, y - A / 2 - jt / 2, 0); g.add(ag);
    linhas.push(linha);
  }
  return { grupo: g, topo: linhas[cursos], cursos: linhas, alt: PISO + (cursos + 1) * (A + jt) };
}
/** martelo (cabo de madeira + cabeça de aço). Origem na empunhadura, cabo ao longo de +y local,
 *  cabeça ao longo de z (face de bater em +z, unha em −z) — gire em x para alinhar ao plano do golpe. */
export function martelo(J = PARADO, o = {}) {
  const g = new THREE.Group(), c = o.cabo ?? .24;
  const cabo = new THREE.Mesh(new THREE.CylinderGeometry(.013, .016, c, 12).translate(0, c * .38, 0), plastico('#b77a45', J, { rug: .55, verniz: .25 }));
  const cab = new THREE.Mesh(new RoundedBoxGeometry(.042, .042, .1, 2, .01).translate(0, c * .86, .01), metal('#b9bec4', J, { rug: .22 }));
  const face = new THREE.Mesh(new THREE.CylinderGeometry(.026, .026, .03, 16).rotateX(Math.PI / 2).translate(0, c * .86, .07), metal('#d5d9dd', J, { rug: .18 }));
  const unha = new THREE.Mesh(new THREE.CylinderGeometry(.006, .02, .06, 12).rotateX(-Math.PI / 2 - .5).translate(0, c * .86 - .012, -.06), metal('#9aa0a7', J));
  g.add(cabo, cab, face, unha); g.cabeca = face; return g;
}
/** enxada (cabo longo + lâmina). Origem na mão de cima, cabo ao longo de -y local. */
export function enxada(J = PARADO, o = {}) {
  const g = new THREE.Group(), c = o.cabo ?? .62;
  g.add(new THREE.Mesh(new THREE.CylinderGeometry(.011, .011, c, 10).translate(0, -c / 2 + .05, 0), plastico('#c08850', J, { rug: .6, verniz: .1 })));
  const lam = new THREE.Mesh(new RoundedBoxGeometry(.13, .075, .008, 2, .003).translate(0, -.03, .028), metal('#8e949b', J, { rug: .4 }));
  lam.position.y = -c + .05; lam.rotation.x = .9; g.add(lam); g.lamina = lam; return g;
}
/** carrinho de mão: caçamba de goma (framboesa azul), roda de alcaçuz, chassi metálico, massa cinza dentro.
 *  Origem no eixo da roda no chão; os cabos apontam para -z (o ursinho fica atrás). */
export function carrinho(J = PARADO, o = {}) {
  const g = new THREE.Group(), rr = .07;
  const cac = p => {
    const k = clamp((p[1] - .16) / .13), hx = .13 + .05 * k, hz = .17 + .06 * k;
    const out = sdf.caixa([p[0], p[1], p[2] + .02 * k], [0, .225, -.25], [hx, .065, hz], .03);
    const kin = clamp((p[1] - .17) / .13), inn = sdf.caixa([p[0], p[1], p[2] + .02 * kin], [0, .25, -.25], [.13 + .05 * kin - .016, .065, .17 + .06 * kin - .016], .02);
    return Math.max(out, -inn);
  };
  const cacamba = new THREE.Mesh(malhaSDF(cac, [-.2, .14, -.5], [.2, .3, -.0], 72), gelatina(o.sabor || 'framboesa', J, { espessura: .1, atenuacao: .2 }));
  g.add(cacamba);
  const mg = new THREE.SphereGeometry(.15, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2), MP = mg.attributes.position;
  for (let i = 0; i < MP.count; i++) { const x = MP.getX(i), y = MP.getY(i), z = MP.getZ(i), k = 1 + .09 * Math.sin(x * 61 + z * 23) * Math.cos(z * 47 - x * 19) + .05 * Math.sin(y * 90 + x * 40); MP.setXYZ(i, x * k, y * k, z * k); }
  mg.computeVertexNormals(); mg.scale(1.02, .62, 1.32).translate(0, .215, -.255);
  const massa = new THREE.Mesh(mg, fosco('#8f8a84', J, { rug: 1 }));
  g.add(massa);
  const roda = new THREE.Group(); roda.position.set(0, rr, 0);
  const pneu = new THREE.Mesh(new THREE.TorusGeometry(rr - .022, .022, 14, 36).rotateY(Math.PI / 2), plastico('#211514', J, { rug: .35, verniz: .6 }));
  const cubo = new THREE.Mesh(new THREE.CylinderGeometry(.022, .022, .05, 16).rotateZ(Math.PI / 2), metal('#c7cbd0', J));
  roda.add(pneu, cubo); g.add(roda);
  const mt = metal('#5a6068', J, { rug: .35 });
  for (const s of [-1, 1]) {
    const tubo = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([V3(s * .03, rr, 0), V3(s * .09, .15, -.15), V3(s * .14, .16, -.4), V3(s * .17, .2, -.62)]), 24, .0085, 8), mt);
    const pe = new THREE.Mesh(new THREE.CylinderGeometry(.008, .008, .13, 8).translate(s * .12, .085, -.38), mt);
    const pega = new THREE.Mesh(new THREE.CylinderGeometry(.013, .013, .07, 10).rotateX(Math.PI / 2 - .2).translate(s * .17, .2, -.62), plastico('#1d1d1d', J, { rug: .6 }));
    g.add(tubo, pe, pega);
  }
  g.roda = roda; g.raioRoda = rr; g.pega = V3(0, .2, -.62);
  g.traverse(m => { if (m.isMesh && m !== cacamba) m.castShadow = true; });
  return g;
}
/** masseira de madeira com massa cinza. o: {w, d} */
export function masseira(o = {}) {
  const g = new THREE.Group(), w = o.w ?? .46, d = o.d ?? .3, h = .075, e = .014;
  const tex = texMadeira(), mm = new THREE.MeshStandardMaterial({ color: '#d9a873', map: tex, roughness: .8 });
  const tab = (sx, sy, sz, x, y, z) => { const m = new THREE.Mesh(new RoundedBoxGeometry(sx, sy, sz, 1, .003), mm); m.position.set(x, PISO + y, z); m.castShadow = m.receiveShadow = true; g.add(m); };
  tab(w, e, d, 0, e / 2, 0); tab(w, h, e, 0, h / 2, d / 2 - e / 2); tab(w, h, e, 0, h / 2, -d / 2 + e / 2); tab(e, h, d, w / 2 - e / 2, h / 2, 0); tab(e, h, d, -w / 2 + e / 2, h / 2, 0);
  const pg = new THREE.PlaneGeometry(w - 2 * e, d - 2 * e, 48, 32).rotateX(-Math.PI / 2), P = pg.attributes.position;
  for (let i = 0; i < P.count; i++) { const x = P.getX(i), z = P.getZ(i); let y = 0; for (const [fx, fz, f, a] of [[31, 17, 1.3, .006], [-23, 41, 4.1, .005], [57, -29, 2.2, .004], [-71, -63, 5.7, .003], [113, 89, .7, .002]]) y += a * Math.sin(x * fx + z * fz + f) * Math.cos(x * fz * .6 - z * fx * .4 + f * 2); P.setY(i, y + .01 * Math.exp(-((x + w * .15) ** 2 + z * z) * 40)); }
  pg.computeVertexNormals();
  const massa = new THREE.Mesh(pg, new THREE.MeshStandardMaterial({ color: '#94908a', roughness: .97 })); massa.position.y = PISO + h * .72; massa.receiveShadow = true; g.add(massa);
  g.massa = massa; return g;
}
function texMadeira(seed = 4) {
  const c = document.createElement('canvas'); c.width = 256; c.height = 64; const x = c.getContext('2d'), r = rng(seed);
  x.fillStyle = '#d6a46c'; x.fillRect(0, 0, 256, 64);
  for (let i = 0; i < 40; i++) { x.strokeStyle = `rgba(${120 + r() * 40},${70 + r() * 30},${30 + r() * 20},${.15 + r() * .2})`; x.lineWidth = .5 + r() * 1.5; x.beginPath(); const y = r() * 64; x.moveTo(0, y); for (let k = 0; k <= 8; k++) x.lineTo(k * 32, y + Math.sin(k + r() * 2) * 2.5); x.stroke(); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}
/** placa de obra em canvas (marca SEMPRE fictícia). linhas: [{txt, tam, cor, peso, fundo}] */
export function placa(linhas, o = {}) {
  const W = 1024, Hh = Math.round(W * (o.prop ?? .56)), c = document.createElement('canvas'); c.width = W; c.height = Hh; const x = c.getContext('2d');
  x.fillStyle = o.fundo || '#f7f4ec'; x.fillRect(0, 0, W, Hh);
  let y = 0;
  for (const l of linhas) {
    const h = Hh * (l.alt ?? .25);
    if (l.fundo) { x.fillStyle = l.fundo; x.fillRect(0, y, W, h); }
    x.fillStyle = l.cor || '#1d2a24'; x.font = `${l.peso || 800} ${h * (l.tam ?? .62)}px ${l.fonte || 'Geist, Helvetica, sans-serif'}`; x.textAlign = 'center'; x.textBaseline = 'middle';
    if (l.esp) x.letterSpacing = l.esp + 'px';
    x.fillText(l.txt, W / 2, y + h / 2); x.letterSpacing = '0px'; y += h;
  }
  x.strokeStyle = '#2a3a33'; x.lineWidth = 10; x.strokeRect(5, 5, W - 10, Hh - 10);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  const w = o.largura ?? .5, h = w * Hh / W, g = new THREE.Group();
  const quadro = new THREE.Mesh(new THREE.BoxGeometry(w, h, .012), [fosco('#e8e2d6'), fosco('#e8e2d6'), fosco('#e8e2d6'), fosco('#e8e2d6'), new THREE.MeshStandardMaterial({ map: t, roughness: .6 }), fosco('#d8d2c6')]);
  quadro.position.y = PISO + (o.alturaPostes ?? .22) + h / 2; quadro.castShadow = true; g.add(quadro);
  const mp = new THREE.MeshStandardMaterial({ color: '#c39563', map: texMadeira(9), roughness: .8 });
  for (const s of [-1, 1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(.022, quadro.position.y + h / 2 - PISO, .022), mp); p.position.set(s * (w / 2 - .05), PISO + (quadro.position.y + h / 2 - PISO) / 2, -.018); p.castShadow = true; g.add(p); }
  return g;
}
/** marmita de alumínio com tampa e alça */
export function marmita(o = {}) {
  const g = new THREE.Group(), al = new THREE.MeshPhysicalMaterial({ color: '#d4d7db', metalness: 1, roughness: .32, envMapIntensity: 1.3 });
  const shape = new THREE.Shape(); const w = .1, d = .065, r = .03;
  shape.moveTo(-w + r, -d); shape.lineTo(w - r, -d); shape.quadraticCurveTo(w, -d, w, -d + r); shape.lineTo(w, d - r); shape.quadraticCurveTo(w, d, w - r, d); shape.lineTo(-w + r, d); shape.quadraticCurveTo(-w, d, -w, d - r); shape.lineTo(-w, -d + r); shape.quadraticCurveTo(-w, -d, -w + r, -d);
  const corpo = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: .07, bevelEnabled: true, bevelSize: .006, bevelThickness: .006, bevelSegments: 3, curveSegments: 10 }).rotateX(-Math.PI / 2), al);
  corpo.position.y = PISO + .006; const tampa = corpo.clone(); tampa.scale.set(1.03, .18, 1.04); tampa.position.y = PISO + .075;
  const alca = new THREE.Mesh(new THREE.TorusGeometry(.05, .005, 6, 24, Math.PI), al); alca.position.set(0, PISO + .09, 0); alca.rotation.x = -.6;
  for (const m of [corpo, tampa, alca]) { m.castShadow = true; g.add(m); }
  return g;
}
/** monte de areia (grãos instanciados, tipo o açúcar da referência) */
export function monte(o = {}) {
  const n = o.n ?? 2600, R = o.raio ?? .22, H = o.alt ?? .09, r = rng(o.seed ?? 5);
  const geo = new THREE.BoxGeometry(1, 1, 1), m = new THREE.MeshStandardMaterial({ color: o.cor || '#d9b27a', roughness: .7 });
  const im = new THREE.InstancedMesh(geo, m, n), M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), C = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const a = r() * Math.PI * 2, d = Math.sqrt(r()) * R, h = H * Math.max(0, 1 - (d / R) ** 1.6) * (.85 + .3 * r());
    E.set(r() * 6, r() * 6, r() * 6); Q.setFromEuler(E); const s = lerp(.006, .011, r());
    M.compose(V3(Math.cos(a) * d, PISO + h * r() ** .3, Math.sin(a) * d * (o.achata ?? .8)), Q, V3(s, s, s)); im.setMatrixAt(i, M);
    im.setColorAt(i, C.set(o.cor || '#d9b27a').offsetHSL(0, (r() - .5) * .1, (r() - .5) * .14));
  }
  im.castShadow = false; im.receiveShadow = true; return im;
}

// ───────────────────────── HUD editorial ─────────────────────────
const CSS = `
.jl-hud{position:absolute;inset:0;pointer-events:none;color:#26221e;font-family:Geist,Helvetica,sans-serif}
.jl-rot{position:absolute;font:500 19px/1 Geist,sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#6e675f;padding-bottom:14px;border-bottom:1.5px solid #cfc8bd}
.jl-tit{position:absolute;font-family:'Lora',serif;font-style:italic;font-weight:400;letter-spacing:-.035em;color:#26221e;line-height:.84}
.jl-tit i{font-style:normal;display:inline-block;width:.13em;height:.13em;border-radius:50%;margin-left:.015em;vertical-align:baseline}
.jl-sub{position:absolute;font-family:'Lora',serif;font-style:italic;color:#5c554d;line-height:1.28}
.jl-pill{position:absolute;white-space:nowrap;display:flex;align-items:center;gap:10px;padding:10px 18px;border:1.5px solid #d6cfc4;border-radius:40px;background:rgba(250,248,244,.7);font:500 17px/1 Geist,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:#8a8279}
.jl-pill b{color:#3a342e;font-weight:600}
.jl-pill .p{width:10px;height:10px;border-radius:50%;background:#3fae5a;box-shadow:0 0 0 4px rgba(63,174,90,.18)}
.jl-pan{position:absolute;background:rgba(251,249,246,.86);border:1.5px solid #e2dcd2;border-radius:6px;padding:18px 20px 16px;box-shadow:0 10px 40px rgba(80,60,40,.07)}
.jl-pan .hd{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:13px}
.jl-pan .lb{font:600 15px/1 Geist,sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#4a443d}
.jl-pan .vl{font-family:'Lora',serif;font-style:italic;font-size:21px;color:#6a625a}
.jl-pan .sec{font:500 13.5px/1 Geist,sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#8d857b}
.jl-bts{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:14px}
.jl-bt{border:1.5px solid #ddd6cb;border-radius:4px;padding:8px 10px 7px;background:#fdfcfa}
.jl-bt .n{font-family:'Lora',serif;font-style:italic;font-size:22px;color:#2f2a25;line-height:1}
.jl-bt .k{font:500 10.5px/1 Geist,sans-serif;letter-spacing:.18em;color:#a69e93;margin-top:6px}
.jl-bt.on{background:#efe9df;border-color:#b9b0a3}
.jl-sab{display:grid;gap:7px;margin:10px 0 14px}
.jl-sab div{border:1.5px solid #ddd6cb;border-radius:4px;padding:8px 2px 7px;text-align:center;font:500 12.5px/1.15 Geist,sans-serif;color:#4a443d;background:#fdfcfa}
.jl-sab div.on{border-color:#8f877c;background:#efe9df}
.jl-sab span{display:block;width:24px;height:24px;border-radius:50%;margin:0 auto 7px}
.jl-sl{margin-bottom:10px}
.jl-sl .tr{position:relative;height:18px;margin:6px 0 3px}
.jl-sl .tr:before{content:'';position:absolute;left:0;right:0;top:8px;height:1.5px;background:#cdc6bb}
.jl-sl .kn{position:absolute;top:0;width:18px;height:18px;margin-left:-9px;border-radius:50%;border:1.5px solid #4a443d;background:#fbf9f6}
.jl-sl .ex{display:flex;justify-content:space-between;font:400 11.5px/1 Geist,sans-serif;color:#a69e93}
.jl-row{display:flex;gap:8px}
.jl-row div{flex:1;border:1.5px solid #ddd6cb;border-radius:4px;padding:9px 0;text-align:center;font:500 15px/1 Geist,sans-serif;color:#3a342e;background:#fdfcfa}
.jl-dados{position:absolute}
.jl-dados .ins{font:400 18px/1.45 Geist,sans-serif;color:#5c554d;padding-bottom:16px;border-bottom:1.5px solid #d6cfc4;margin-bottom:16px}
.jl-dados .ins b{color:#26221e;font-weight:600}
.jl-dados .gr{display:flex}
.jl-dados .c{padding:0 22px;border-left:1.5px solid #d6cfc4}
.jl-dados .c:first-child{padding-left:0;border-left:0}
.jl-dados .c .l{font:500 12.5px/1 'JetBrains Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#8d857b;margin-bottom:9px}
.jl-dados .c .v{font-family:'Lora',serif;font-style:italic;font-size:34px;color:#26221e;line-height:1;white-space:nowrap}
.jl-dados .c .v small{font:400 13px 'JetBrains Mono',monospace;color:#a69e93;margin-left:4px;font-style:normal}
.jl-dados .nota{font:400 12.5px/1.5 'JetBrains Mono',monospace;color:#a39b90;margin-top:14px}
.jl-rod{position:absolute;display:flex;justify-content:space-between;font:600 15px/1 Geist,sans-serif;letter-spacing:.2em;text-transform:uppercase;color:#4a443d;padding-top:14px;border-top:1.5px solid #d6cfc4}
`;
let HUDEL = null;
function hudEl() {
  if (HUDEL) return HUDEL;
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  HUDEL = document.createElement('div'); HUDEL.className = 'jl-hud'; document.getElementById('stage').appendChild(HUDEL); return HUDEL;
}
const el = (cls, html, css = {}) => { const e = document.createElement('div'); e.className = cls; e.innerHTML = html; Object.assign(e.style, css); hudEl().appendChild(e); return e; };
const px = v => typeof v === 'number' ? v + 'px' : v;
/** rótulo versalete + título serifa itálica com ponto colorido + subtítulo. o: {rotulo, titulo:[linhas], tam, sub:[linhas], x, y, ponto: cor | fn(t)} */
export function titulo(S, o) {
  const x = o.x ?? 64, y = o.y ?? 110, tam = o.tam ?? 200;
  el('jl-rot', o.rotulo, { left: px(x), top: px(y) });
  const tl = o.titulo.map((l, i) => i === o.titulo.length - 1 ? `${l}<i></i>` : l).join('<br>');
  const T = el('jl-tit', tl, { left: px(x - tam * .04), top: px(y + 46), fontSize: px(tam) });
  const dot = T.querySelector('i');
  const sub = el('jl-sub', o.sub.join('<br>'), { left: px(x), top: px(y + 46 + tam * .84 * o.titulo.length + 34), fontSize: px(o.tamSub ?? 34) });
  S.hud.push(t => { dot.style.background = typeof o.ponto === 'function' ? o.ponto(t) : (o.ponto || '#e8233a'); });
  return { T, sub };
}
/** pílula "● AO VIVO · ESTADO". estado: fn(t) → texto */
export function pilula(S, o) {
  const e = el('jl-pill', '<span class="p"></span><span>AO VIVO ·</span><b></b>', { right: px(o.x ?? 48), top: px(o.y ?? 96) }), b = e.querySelector('b');
  S.hud.push(t => { b.textContent = o.estado(t); });
  return e;
}
/**
 * painel "O ESPÉCIME" (aqui "O CANTEIRO"): o: {titulo, x, y, w, acoes:[{n,k}], ativa: fn(t)→idx, sabores:[chaves], sabor: fn(t)→idx,
 *   sliders:[{n, v: fn(t)→0..1, txt: fn(t)→str, ex:[esq, (meio), dir]}], botoes:[...]}
 */
export function painel(S, o) {
  const sabs = o.sabores.map(sabor);
  const html = `<div class="hd"><span class="lb">${o.titulo}</span><span class="vl" data-sab></span></div>
  <div class="jl-bts">${o.acoes.map((a, i) => `<div class="jl-bt" data-a="${i}"${a.larga ? ' style="grid-column:span ' + a.larga + '"' : ''}><div class="n">${a.n}</div><div class="k">${a.k}</div></div>`).join('')}</div>
  <div class="hd" style="margin-bottom:0"><span class="sec">${o.rotSabor || 'Sabor'}</span><span class="vl" data-sab2></span></div>
  <div class="jl-sab" style="grid-template-columns:repeat(${sabs.length},1fr)">${sabs.map((s, i) => `<div data-s="${i}"><span style="background:radial-gradient(circle at 35% 30%,#fff 0 8%,${s.cor} 30%,${s.borda} 100%)"></span>${s.nome}</div>`).join('')}</div>
  ${o.sliders.map((s, i) => `<div class="jl-sl"><div class="hd" style="margin-bottom:0"><span class="sec">${s.n}</span><span class="vl" data-st="${i}"></span></div><div class="tr"><div class="kn" data-k="${i}"></div></div><div class="ex">${s.ex.map(x => `<span>${x}</span>`).join('')}</div></div>`).join('')}
  <div class="jl-row">${o.botoes.map(b => `<div>${b}</div>`).join('')}</div>`;
  const P = el('jl-pan', html, { left: px(o.x), top: px(o.y), width: px(o.w ?? 400) });
  const bts = [...P.querySelectorAll('[data-a]')], sb = [...P.querySelectorAll('[data-s]')], kn = [...P.querySelectorAll('[data-k]')], st = [...P.querySelectorAll('[data-st]')];
  const v1 = P.querySelector('[data-sab]'), v2 = P.querySelector('[data-sab2]');
  S.hud.push(t => {
    const a = o.ativa ? o.ativa(t) : -1; bts.forEach((b, i) => b.classList.toggle('on', i === a));
    const s = o.sabor ? o.sabor(t) : 0; sb.forEach((b, i) => b.classList.toggle('on', i === s)); v1.textContent = v2.textContent = sabs[s]?.nome || '';
    o.sliders.forEach((sl, i) => { kn[i].style.left = (clamp(sl.v(t)) * 100).toFixed(2) + '%'; st[i].textContent = sl.txt(t); });
  });
  return P;
}
/** dados embaixo: o: {x, y (base), w, instrucao (html), campos:[{l, v: fn(t)→str, u}], nota} */
export function dados(S, o) {
  const html = `<div class="ins">${o.instrucao}</div><div class="gr">${o.campos.map((c, i) => `<div class="c"><div class="l">${c.l}</div><div class="v"><span data-v="${i}"></span><small>${c.u || ''}</small></div></div>`).join('')}</div>${o.nota ? `<div class="nota">${o.nota}</div>` : ''}`;
  const D = el('jl-dados', html, { left: px(o.x ?? 64), bottom: px(o.base ?? 70), width: px(o.w ?? 560) });
  const vs = [...D.querySelectorAll('[data-v]')];
  S.hud.push(t => o.campos.forEach((c, i) => { vs[i].textContent = c.v(t); }));
  return D;
}
/** linha de rodapé "DENTRO DO EXPERIMENTO  +" */
export function rodape(S, o) { return el('jl-rod', `<span>${o.txt}</span><span>+</span>`, { left: px(o.x), bottom: px(o.base ?? 64), width: px(o.w ?? 400) }); }
/** projeta um ponto 3D em px da tela */
export function tela(S, alvo, saida = new THREE.Vector3()) {
  if (alvo.isObject3D) alvo.getWorldPosition(saida); else saida.copy(alvo.isVector3 ? alvo : V3(alvo));
  saida.project(S.camera); return { x: (saida.x + 1) / 2 * window.VIDEO.w, y: (1 - saida.y) / 2 * window.VIDEO.h };
}
/** formata número pt-BR */
export const num = (v, d = 1) => v.toFixed(d).replace('.', ',');
