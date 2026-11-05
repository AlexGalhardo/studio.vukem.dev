// lowpoly.js — biblioteca do estilo "low-poly explicativo" (three.js, módulo ES)
// Maquete 3D de massinha low-poly (branco/cinza + 1 acento) sobre fundo azul-noite com poeira em bokeh,
// desfoque de profundidade forte, vista em corte, peças que explodem, fluxos animados e HUD "COMO FUNCIONA".
// Uso na página:  import * as LP from '../../lib/lowpoly.js';  const S = LP.palco({...});
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
export { THREE };

// ───────────────────────── paleta (amostrada das referências) ─────────────────────────
export const PAL = {
  noite: '#1d222c', noite2: '#0c0f15',                                  // fundo: gradiente vertical
  branco: '#e8ebf0', gelo: '#c9cfd8', cinza: '#9aa1ab', grafite: '#424852', carvao: '#272b33',
  laranja: '#ff6a2a', verde: '#3ccf8e', azul: '#4f8cff', amarelo: '#ffc94a', vermelho: '#ff4d4d', cobre: '#d9844a',
  agua: '#3f8fdc', aguaClara: '#8fd0ff', aguaFunda: '#25507e',
  grama: '#86b26a', grama2: '#6f9e58', grama3: '#9cc27a', terra: '#b98a5e', rocha: '#8f949c',
  folha: '#5f9c56', folha2: '#7fb35f', folha3: '#4c8a4f', tronco: '#80614a',
  texto: '#ffffff', apagado: '#7b818b', mono: '#8b9099', caixa: 'rgba(20,23,29,.9)',
};

// ───────────────────────── utilidades determinísticas ─────────────────────────
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
export function fbm(x, y, oct = 3) { let s = 0, a = .5, f = 1, n = 0; for (let i = 0; i < oct; i++) { s += a * ruido(x * f + i * 17.3, y * f - i * 9.1); n += a; a *= .5; f *= 2.03; } return s / n; }
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const suave = (a, b, v) => { const k = clamp((v - a) / (b - a)); return k * k * (3 - 2 * k); };
/** progresso 0→1 de t na janela [t0,t1] com ease do GSAP ('power2.out', 'back.out(1.6)'…) */
export const fase = (t, t0, t1, ease = 'none') => gsap.parseEase(ease)(clamp((t - t0) / (t1 - t0)));
const V3 = a => (a && a.isVector3) ? a.clone() : new THREE.Vector3(...a);
export const v3 = V3;

// ───────────────────────── palco: renderer + desfoque de profundidade + acabamento ─────────────────────────
const DOF_FRAG = `
uniform sampler2D tCor, tProf; uniform float uFoco, uAbert, uMax, uNear, uFar; uniform vec2 uRes; varying vec2 vUv;
float lin(float d){ float z = d * 2. - 1.; return 2. * uNear * uFar / (uFar + uNear - z * (uFar - uNear)); }
float coc(float z){ return clamp(abs(z - uFoco) / z * uAbert * uRes.y, 0., uMax); }
void main(){
  float zC = lin(texture2D(tProf, vUv).r), cC = coc(zC);
  vec3 cor = texture2D(tCor, vUv).rgb; float tot = 1.;
  float r = 1.5; float ang = 0.;
  for (int i = 0; i < 260; i++) {
    if (r >= uMax) break;
    vec2 uv = vUv + vec2(cos(ang), sin(ang)) * r / uRes;
    vec3 c = texture2D(tCor, uv).rgb; float z = lin(texture2D(tProf, uv).r); float cs = coc(z);
    if (z > zC) cs = clamp(cs, 0., cC * 2.);           // fundo não vaza sobre o que está em foco
    float m = smoothstep(r - .5, r + .5, cs);
    cor += mix(cor / tot, c, m); tot += 1.;
    ang += 2.39996323; r += 2.4 / r;
  }
  gl_FragColor = vec4(cor / tot, 1.);
}`;
const QUAD_VERT = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
class PassDOF extends Pass {
  constructor(scene, camera, w, h) {
    super();
    this.scene = scene; this.camera = camera;
    this.rt = new THREE.WebGLRenderTarget(w, h, { type: THREE.HalfFloatType, samples: 4, depthTexture: new THREE.DepthTexture(w, h) });
    this.mat = new THREE.ShaderMaterial({
      uniforms: { tCor: { value: this.rt.texture }, tProf: { value: this.rt.depthTexture }, uFoco: { value: 10 }, uAbert: { value: .02 }, uMax: { value: 34 }, uNear: { value: .1 }, uFar: { value: 400 }, uRes: { value: new THREE.Vector2(w, h) } },
      vertexShader: QUAD_VERT, fragmentShader: DOF_FRAG, depthTest: false, depthWrite: false,
    });
    this.quad = new FullScreenQuad(this.mat);
  }
  render(renderer, writeBuffer) {
    renderer.setRenderTarget(this.rt); renderer.clear(); renderer.render(this.scene, this.camera);
    const u = this.mat.uniforms; u.uNear.value = this.camera.near; u.uFar.value = this.camera.far;
    renderer.setRenderTarget(this.renderToScreen ? null : writeBuffer); this.quad.render(renderer);
  }
}
const ACAB_FRAG = `uniform sampler2D tDiffuse; uniform float uTime, uGrain, uVig; uniform vec2 uRes; varying vec2 vUv;
float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void main(){ vec2 c = vUv - .5; c.x *= uRes.x / uRes.y; float d = length(c);
  vec3 col = texture2D(tDiffuse, vUv).rgb;
  col *= 1. - uVig * smoothstep(.3, .95, d);
  col += (h(vUv * uRes + fract(uTime * 7.13) * 100.) - .5) * uGrain;
  gl_FragColor = vec4(col, 1.); }`;

/** gradiente vertical (cores de cima → baixo) como textura de fundo */
export function gradiente(cores) {
  const c = document.createElement('canvas'); c.width = 4; c.height = 512; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 512); cores.forEach((k, i) => gr.addColorStop(i / (cores.length - 1), k));
  g.fillStyle = gr; g.fillRect(0, 0, 4, 512);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; return tx;
}

/**
 * Palco 3D do estilo. o: {fundo:[cores], fov, exposicao, dof:{abertura,max}, bloom:{forca,raio,limiar}, grao, vinheta, sol:{cor,forca,dir}, ceu, chao}
 * Devolve S = {scene, camera, renderer, composer, sol, hemi, borda, dof, update(t) (você define), sombra(centro, raio)}.
 */
export function palco(o = {}) {
  const V = window.VIDEO;
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = o.exposicao ?? 1;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.localClippingEnabled = true;
  renderer.domElement.className = 'layer';
  (o.parent || document.getElementById('stage')).prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = gradiente(o.fundo || [PAL.noite, PAL.noite2]);
  const camera = new THREE.PerspectiveCamera(o.fov ?? 30, V.w / V.h, .1, o.longe ?? 400);

  // luz de estúdio: céu suave + sol com sombra macia + borda azulada por trás
  const hemi = new THREE.HemisphereLight(o.ceu || '#e4ebff', o.chao || '#2b3039', o.hemi ?? 1.5); scene.add(hemi);
  const sol = new THREE.DirectionalLight(o.sol?.cor || '#fff2e0', o.sol?.forca ?? 2.4);
  sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048); sol.shadow.bias = -.0005; sol.shadow.normalBias = .03;
  scene.add(sol, sol.target);
  const borda = new THREE.DirectionalLight('#9fb8ff', o.borda ?? 1.0); scene.add(borda, borda.target);
  const dirSol = V3(o.sol?.dir || [-.55, 1, .65]).normalize(), dirBorda = new THREE.Vector3(.6, .5, -1).normalize();

  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(V.w, V.h, { type: THREE.HalfFloatType }));
  composer.setPixelRatio(1); composer.setSize(V.w, V.h);
  const dofPass = new PassDOF(scene, camera, V.w, V.h); composer.addPass(dofPass);
  const b = o.bloom || {};
  const bloom = new UnrealBloomPass(new THREE.Vector2(V.w, V.h), b.forca ?? .45, b.raio ?? .5, b.limiar ?? .92); composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const acab = new ShaderPass({ uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: o.grao ?? .03 }, uVig: { value: o.vinheta ?? .35 }, uRes: { value: new THREE.Vector2(V.w, V.h) } }, vertexShader: QUAD_VERT, fragmentShader: ACAB_FRAG });
  composer.addPass(acab);

  const dof = { foco: 10, abertura: o.dof?.abertura ?? .018, max: o.dof?.max ?? 34 };
  const S = {
    THREE, renderer, scene, camera, composer, sol, hemi, borda, bloom, dof, acab, update: null, hud: [],
    /** move o sol (e a caixa de sombra) para cobrir a área de interesse */
    sombra(centro, raio = 12) {
      const c = V3(centro); sol.target.position.copy(c); sol.position.copy(c).addScaledVector(dirSol, raio * 2.5);
      borda.target.position.copy(c); borda.position.copy(c).addScaledVector(dirBorda, raio * 2);
      const sc = sol.shadow.camera; sc.left = sc.bottom = -raio; sc.right = sc.top = raio; sc.near = .5; sc.far = raio * 6; sc.updateProjectionMatrix();
    },
  };
  S.sombra([0, 0, 0], o.raioSombra ?? 12);
  onTick(t => {
    acab.uniforms.uTime.value = t;
    if (S.update) S.update(t);
    camera.updateMatrixWorld();
    const u = dofPass.mat.uniforms; u.uFoco.value = dof.foco; u.uAbert.value = dof.abertura; u.uMax.value = Math.max(2, dof.max);
    for (const h of S.hud) h(t);
    composer.render();
  });
  return S;
}

// ───────────────────────── materiais (massinha fosca, low-poly) ─────────────────────────
const CACHE = new Map();
/** material fosco de massinha. o: {plano (flatShading, padrão true), rug, metal, emis, emisForca, opac, lados} */
export function mat(cor, o = {}) {
  const k = cor + JSON.stringify(o); if (CACHE.has(k)) return CACHE.get(k);
  const m = new THREE.MeshStandardMaterial({
    color: cor, roughness: o.rug ?? .82, metalness: o.metal ?? 0, flatShading: o.plano ?? true,
    emissive: o.emis || '#000000', emissiveIntensity: o.emisForca ?? 1,
    transparent: o.opac !== undefined && o.opac < 1, opacity: o.opac ?? 1, side: o.lados ? THREE.DoubleSide : THREE.FrontSide,
  });
  if (o.opac !== undefined && o.opac < 1) m.depthWrite = o.depthWrite ?? true;
  CACHE.set(k, m); return m;
}
/** material que brilha (bloom): cor * forca > 1 passa do limiar */
export function brilho(cor, forca = 2.5) { const m = new THREE.MeshBasicMaterial({ color: new THREE.Color(cor).multiplyScalar(forca), toneMapped: false }); return m; }
/** prepara malha: sombra projetada e recebida */
export function malha(geo, material, o = {}) {
  const m = new THREE.Mesh(geo, material); m.castShadow = o.sombra ?? true; m.receiveShadow = o.recebe ?? true; return m;
}
/** "torna low-poly": tira índices (cada face com a própria normal) e sacode vértices de leve */
export function facetar(geo, amp = 0, seed = 1) {
  let g = geo.index ? geo.toNonIndexed() : geo;
  if (amp > 0) {
    const r = rng(seed), p = g.attributes.position, mapa = new Map();
    for (let i = 0; i < p.count; i++) {
      const key = `${p.getX(i).toFixed(3)},${p.getY(i).toFixed(3)},${p.getZ(i).toFixed(3)}`;
      if (!mapa.has(key)) mapa.set(key, [(r() - .5) * amp, (r() - .5) * amp, (r() - .5) * amp]);
      const d = mapa.get(key); p.setXYZ(i, p.getX(i) + d[0], p.getY(i) + d[1], p.getZ(i) + d[2]);
    }
  }
  g.computeVertexNormals(); return g;
}

// ───────────────────────── primitivas ─────────────────────────
/** caixa chanfrada (o "tijolo" do estilo). pos opcional [x,y,z] = centro da BASE */
export function caixa(w, h, d, cor, o = {}) {
  const ch = o.chanfro ?? Math.min(w, h, d) * .12;
  const g = ch > 0 ? new RoundedBoxGeometry(w, h, d, 1, ch) : new THREE.BoxGeometry(w, h, d);
  const m = malha(g, o.material || mat(cor, { plano: o.plano ?? false, ...o.mat }));
  if (o.pos) m.position.set(o.pos[0], o.pos[1] + h / 2, o.pos[2]);
  return m;
}
/** cilindro low-poly (lados = facetas). pos = centro da base */
export function cilindro(r, h, cor, o = {}) {
  const g = new THREE.CylinderGeometry(o.rTopo ?? r, r, h, o.lados ?? 10, 1, !!o.aberto);
  const m = malha(g, o.material || mat(cor, o.mat));
  if (o.pos) m.position.set(o.pos[0], o.pos[1] + h / 2, o.pos[2]);
  return m;
}
/** esfera facetada (icosaedro) */
export function bola(r, cor, o = {}) { return malha(facetar(new THREE.IcosahedronGeometry(r, o.det ?? 1), o.sacode ?? 0, o.seed ?? 1), o.material || mat(cor, o.mat)); }

/** árvore low-poly: tronco + copa de icosaedro sacudido (tipo 'redonda') ou cones empilhados ('pinheiro') */
export function arvore(o = {}) {
  const r = rng(o.seed ?? 1), h = o.h ?? 1, g = new THREE.Group();
  const cores = o.cores || [PAL.folha, PAL.folha2, PAL.folha3];
  const tr = cilindro(.07 * h, .45 * h, PAL.tronco, { lados: 5, pos: [0, 0, 0] }); g.add(tr);
  if (o.tipo === 'pinheiro') {
    for (let i = 0; i < 3; i++) {
      const c = malha(facetar(new THREE.ConeGeometry((.42 - i * .1) * h, .55 * h, 6), .03 * h, (o.seed ?? 1) + i), mat(cores[i % cores.length]));
      c.position.y = (.5 + i * .3) * h; c.rotation.y = r() * 3; g.add(c);
    }
  } else {
    const c = bola(.38 * h, cores[Math.floor(r() * cores.length)], { det: 0, sacode: .12 * h, seed: (o.seed ?? 1) * 7 });
    c.position.y = .7 * h; c.scale.set(1, .9 + r() * .3, 1); c.rotation.set(r() * 3, r() * 3, 0); g.add(c);
  }
  g.rotation.y = r() * 6.28; g.userData.alt = h;
  return g;
}
/** espalha árvores: area(r) → [x,z] ou null; chao(x,z) → y; filtro(x,z) → bool */
export function floresta(o) {
  const r = rng(o.seed ?? 7), g = new THREE.Group(); let n = 0, tent = 0;
  while (n < o.n && tent++ < o.n * 40) {
    const p = o.area(r); if (!p) continue; const [x, z] = p;
    if (o.filtro && !o.filtro(x, z)) continue;
    const a = arvore({ h: (o.h ?? 1) * (.7 + r() * .6), seed: Math.floor(r() * 1e6), tipo: r() < (o.pinheiros ?? .25) ? 'pinheiro' : 'redonda', cores: o.cores });
    a.position.set(x, o.chao(x, z) - .05, z); g.add(a); n++;
  }
  return g;
}

/**
 * Terreno-bloco (maquete): topo facetado por função de altura + saia de terra + fundo (sólido fechado → corte funciona).
 * o: {x:[x0,x1], z:[z0,z1], seg:[nx,nz], altura:(x,z)→y, cor:(x,y,z,inclinacao)→hex, base:-1.5, corSaia}
 */
export function terreno(o) {
  const [x0, x1] = o.x, [z0, z1] = o.z, [nx, nz] = o.seg || [60, 60], base = o.base ?? -1.6;
  const H = o.altura, P = [], C = [], col = new THREE.Color(), tmp = new THREE.Vector3();
  const X = i => lerp(x0, x1, i / nx), Z = j => lerp(z0, z1, j / nz);
  const tri = (a, b, c, cor) => { P.push(...a, ...b, ...c); col.set(cor); for (let k = 0; k < 3; k++) C.push(col.r, col.g, col.b); };
  const corDe = (a, b, c) => {
    const ab = new THREE.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]), ac = new THREE.Vector3(c[0] - a[0], c[1] - a[1], c[2] - a[2]);
    tmp.crossVectors(ab, ac).normalize(); const inc = 1 - Math.abs(tmp.y);
    return o.cor ? o.cor((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3, inc) : PAL.grama;
  };
  const v = (i, j) => [X(i), H(X(i), Z(j)), Z(j)];
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const a = v(i, j), b = v(i + 1, j), c = v(i, j + 1), d = v(i + 1, j + 1);
    if ((i + j) % 2) { tri(a, c, b, corDe(a, c, b)); tri(b, c, d, corDe(b, c, d)); }
    else { tri(a, c, d, corDe(a, c, d)); tri(a, d, b, corDe(a, d, b)); }
  }
  // saia (4 lados) e fundo
  const saia = o.corSaia || '#7a5a44';
  const lado = (pts) => { for (let k = 0; k < pts.length - 1; k++) { const a = pts[k], b = pts[k + 1]; const a0 = [a[0], base, a[2]], b0 = [b[0], base, b[2]]; tri(a, a0, b, saia); tri(b, a0, b0, saia); } };
  lado([...Array(nx + 1).keys()].map(i => v(i, 0)).reverse());       // z0 (normal −z)
  lado([...Array(nx + 1).keys()].map(i => v(i, nz)));                 // z1
  lado([...Array(nz + 1).keys()].map(j => v(0, j)));                  // x0
  lado([...Array(nz + 1).keys()].map(j => v(nx, j)).reverse());       // x1
  tri([x0, base, z0], [x1, base, z0], [x0, base, z1], saia); tri([x1, base, z0], [x1, base, z1], [x0, base, z1], saia);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(C, 3)); g.computeVertexNormals();
  const m = malha(g, new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: .9 }));
  m.userData.altura = H; return m;
}

/**
 * Água low-poly: lâmina facetada que ondula (update(t)) + volume translúcido até o fundo (o corte mostra a seção azul).
 * o: {x:[a,b], z:[a,b], nivel, fundo, seg, cor, onda}
 */
export function agua(o) {
  const [x0, x1] = o.x, [z0, z1] = o.z, w = x1 - x0, d = z1 - z0, nv = o.nivel, fd = o.fundo ?? nv - 2, sg = o.seg || [Math.ceil(w * 1.6), Math.ceil(d * 1.6)];
  const g = new THREE.Group();
  const geo = new THREE.PlaneGeometry(w, d, sg[0], sg[1]).toNonIndexed(); geo.rotateX(-Math.PI / 2); geo.translate((x0 + x1) / 2, nv, (z0 + z1) / 2);
  const base = geo.attributes.position.array.slice();
  const lam = malha(geo, new THREE.MeshStandardMaterial({ color: o.cor || PAL.agua, roughness: .25, metalness: .05, flatShading: true, transparent: true, opacity: o.opac ?? .92 }), { sombra: false });
  g.add(lam);
  const vol = malha(new THREE.BoxGeometry(w - .02, nv - fd - .04, d - .02), new THREE.MeshStandardMaterial({ color: o.corFundo || PAL.aguaFunda, roughness: .4, transparent: true, opacity: .55, depthWrite: false }), { sombra: false });
  vol.position.set((x0 + x1) / 2, (nv + fd) / 2 - .03, (z0 + z1) / 2); if (o.volume !== false) g.add(vol);
  const amp = o.onda ?? .05;
  g.userData.update = t => {
    const p = geo.attributes.position.array;
    for (let i = 0; i < p.length; i += 3) p[i + 1] = base[i + 1] + amp * (Math.sin(base[i] * 1.7 + t * 1.9) * .6 + Math.sin(base[i + 2] * 2.3 - t * 1.4) * .4 + ruido(base[i] * .9 + t * .3, base[i + 2] * .9) * .5);
    geo.attributes.position.needsUpdate = true; geo.computeVertexNormals();
  };
  g.userData.lamina = lam; g.userData.volume = vol;
  return g;
}
/** fita de água seguindo uma curva (rio, canal de fuga). o: {largura, seg, cor, onda} */
export function rio(curva, o = {}) {
  const n = o.seg ?? 80, L = o.largura ?? 1.2, P = [], up = new THREE.Vector3(0, 1, 0);
  const pts = [];
  for (let i = 0; i <= n; i++) { const u = i / n, p = curva.getPointAt(u), tg = curva.getTangentAt(u), s = new THREE.Vector3().crossVectors(tg, up).normalize().multiplyScalar(L / 2); pts.push([p.clone().add(s), p.clone().sub(s)]); }
  for (let i = 0; i < n; i++) { const [a, b] = pts[i], [c, d] = pts[i + 1]; P.push(...a.toArray(), ...c.toArray(), ...b.toArray(), ...b.toArray(), ...c.toArray(), ...d.toArray()); }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); geo.computeVertexNormals();
  const base = geo.attributes.position.array.slice(), amp = o.onda ?? .03;
  const m = malha(geo, new THREE.MeshStandardMaterial({ color: o.cor || PAL.agua, roughness: .25, flatShading: true }), { sombra: false });
  m.userData.update = t => { const p = geo.attributes.position.array; for (let i = 0; i < p.length; i += 3) p[i + 1] = base[i + 1] + amp * Math.sin(base[i] * 2.1 + base[i + 2] * 1.3 - t * 2.4); geo.attributes.position.needsUpdate = true; geo.computeVertexNormals(); };
  return m;
}

/** cano/conduto ao longo de uma curva (com interior escuro para cortes) */
export function cano(curva, o = {}) {
  const g = new THREE.Group(), geo = new THREE.TubeGeometry(curva, o.seg ?? 64, o.raio ?? .3, o.lados ?? 10, false);
  g.add(malha(geo, mat(o.cor || PAL.grafite, { plano: o.plano ?? true })));
  g.add(malha(geo, new THREE.MeshStandardMaterial({ color: o.interior || PAL.carvao, side: THREE.BackSide, roughness: .9 }), { sombra: false }));
  return g;
}

/** engrenagem extrudada. o: {r, dentes, esp, furo, cor} */
export function engrenagem(o = {}) {
  const r = o.r ?? 1, n = o.dentes ?? 12, h = r * .18, s = new THREE.Shape();
  for (let i = 0; i < n; i++) {
    const a = i / n * Math.PI * 2, da = Math.PI / n;
    const pts = [[r, a - da * .55], [r + h, a - da * .3], [r + h, a + da * .3], [r, a + da * .55], [r, a + da * 1.45]];
    pts.forEach(([rr, aa], k) => (i === 0 && k === 0 ? s.moveTo : s.lineTo).call(s, rr * Math.cos(aa), rr * Math.sin(aa)));
  }
  const furo = new THREE.Path(); furo.absarc(0, 0, o.furo ?? r * .25, 0, Math.PI * 2, true); s.holes.push(furo);
  const geo = new THREE.ExtrudeGeometry(s, { depth: o.esp ?? r * .3, bevelEnabled: false, curveSegments: 6 }); geo.translate(0, 0, -(o.esp ?? r * .3) / 2); geo.rotateX(Math.PI / 2);
  return malha(geo, mat(o.cor || PAL.laranja));
}

/** pino de localização (haste + bolinha), estilo das refs: estala com escala */
export function pino(cor = PAL.verde, o = {}) {
  const g = new THREE.Group(), h = o.h ?? .6;
  g.add(cilindro(.015, h, '#e8ebf0', { lados: 4, pos: [0, 0, 0], mat: { plano: true } }));
  const b = malha(new THREE.IcosahedronGeometry(o.r ?? .09, 2), brilho(cor, o.forca ?? 1.6)); b.position.y = h; g.add(b);
  return g;
}

/** boneco de massinha (refs: overbooking / batimento). o: {cor, h} → grupo com .bracos .pernas para posar */
export function boneco(o = {}) {
  const c = o.cor || PAL.branco, h = o.h ?? 1.7, g = new THREE.Group(), M = mat(c, { plano: false, rug: .7 });
  const cap = (r, l) => malha(new THREE.CapsuleGeometry(r, l, 6, 12), M);
  const tronco = cap(.17 * h, .28 * h); tronco.position.y = .62 * h; g.add(tronco);
  const cab = malha(new THREE.SphereGeometry(.12 * h, 20, 14), M); cab.position.y = .92 * h; g.add(cab);
  const membro = (x, y, r, l) => { const p = new THREE.Group(); p.position.set(x, y, 0); const m = cap(r, l); m.position.y = -l / 2 - r * .5; p.add(m); g.add(p); return p; };
  g.userData.bracos = [membro(-.21 * h, .76 * h, .05 * h, .3 * h), membro(.21 * h, .76 * h, .05 * h, .3 * h)];
  g.userData.pernas = [membro(-.08 * h, .42 * h, .065 * h, .32 * h), membro(.08 * h, .42 * h, .065 * h, .32 * h)];
  return g;
}


/** carro de brinquedo (refs: Waze): carroceria chanfrada, cabine, rodas, faróis. Frente em +z. o: {cor, comp} → g.userData.rodas */
export function carro(o = {}) {
  const c = o.comp ?? 1, g = new THREE.Group(), cor = o.cor || PAL.branco;
  g.add(caixa(.56 * c, .3 * c, c, cor, { pos: [0, .1 * c, 0], chanfro: .07 * c, mat: { plano: false } }));
  g.add(caixa(.5 * c, .24 * c, .52 * c, o.corCabine || cor, { pos: [0, .38 * c, -.08 * c], chanfro: .06 * c, mat: { plano: false } }));
  g.add(caixa(.51 * c, .15 * c, .4 * c, '#2a2f37', { pos: [0, .43 * c, -.08 * c], chanfro: .03 * c }));            // vidros
  const rodas = [];
  [[-1, 1], [1, 1], [-1, -1], [1, -1]].forEach(([sx, sz]) => { const r = cilindro(.13 * c, .1 * c, '#22262d', { lados: 12 }); r.rotation.z = Math.PI / 2; r.position.set(sx * .27 * c, .13 * c, sz * .32 * c); g.add(r); rodas.push(r); });
  [-1, 1].forEach(sx => { const f = malha(new THREE.BoxGeometry(.1 * c, .05 * c, .02 * c), brilho('#fff4d6', 1.4)); f.position.set(sx * .18 * c, .27 * c, .5 * c + .01); g.add(f);
    const l = malha(new THREE.BoxGeometry(.11 * c, .05 * c, .02 * c), brilho(PAL.vermelho, 1.6)); l.position.set(sx * .18 * c, .27 * c, -.5 * c - .01); g.add(l); });
  g.userData.rodas = rodas; return g;
}
/** casinha com telhado de duas águas. o: {w, d, h, cor, telhado} */
export function casa(o = {}) {
  const w = o.w ?? 1, d = o.d ?? 1, h = o.h ?? .7, g = new THREE.Group();
  g.add(caixa(w, h, d, o.cor || PAL.branco, { pos: [0, 0, 0], chanfro: .02, plano: true }));
  const tri = new THREE.Shape([new THREE.Vector2(-w / 2 - .06, 0), new THREE.Vector2(w / 2 + .06, 0), new THREE.Vector2(0, h * .6)]);
  const tg = new THREE.ExtrudeGeometry(tri, { depth: d + .12, bevelEnabled: false }); tg.translate(0, h, -d / 2 - .06);
  g.add(malha(tg, mat(o.telhado || PAL.laranja)));
  g.add(caixa(w * .2, h * .5, .03, '#5a4636', { pos: [0, 0, d / 2], chanfro: 0 }));
  g.add(caixa(w * .2, h * .22, .03, '#2b3038', { pos: [w * .28, h * .4, d / 2], chanfro: 0 }));
  return g;
}
/** nuvem low-poly (bolhas de icosaedro com base achatada). o: {tam, cor, seed} */
export function nuvem(o = {}) {
  const r = rng(o.seed ?? 4), t = o.tam ?? 1, g = new THREE.Group();
  for (let i = 0; i < 5; i++) { const b = bola(t * (.35 + r() * .25), o.cor || '#f4f6fa', { det: 0, sacode: .06 * t, seed: i + 1 }); b.position.set((i - 2) * .32 * t, (r() * .15 + (i % 2 ? .12 : 0)) * t, (r() - .5) * .3 * t); b.castShadow = false; g.add(b); }
  return g;
}

// ───────────────────────── peças de máquinas e energia ─────────────────────────
/** rotor de turbina (tipo Francis): coroa, cubo e pás curvas. Girar: obj.rotation.y */
export function turbina(o = {}) {
  const r = o.r ?? 1, n = o.pas ?? 13, g = new THREE.Group(), cor = o.cor || PAL.laranja;
  const coroa = cilindro(r * .5, r * .12, cor, { rTopo: r * .34, lados: 20, pos: [0, r * .62, 0] }); g.add(coroa);
  const cubo = malha(new THREE.ConeGeometry(r * .3, r * .5, 12), mat(o.corCubo || PAL.grafite)); cubo.rotation.x = Math.PI; cubo.position.y = r * .38; g.add(cubo);
  const anel = malha(new THREE.CylinderGeometry(r * .92, r * .8, r * .16, 26, 1, true), mat(cor, { lados: true })); anel.position.y = r * .1; g.add(anel);
  for (let i = 0; i < n; i++) {
    const p = new THREE.Group(); p.rotation.y = i / n * Math.PI * 2;
    const pa = malha(new THREE.BoxGeometry(r * .05, r * .5, r * .5), mat(o.corPa || PAL.branco));
    pa.position.set(r * .62, r * .38, 0); pa.rotation.set(0, .7, -.25); p.add(pa); g.add(p);
  }
  return g;
}
/** gerador explodível: tampa, estator (anel + bobinas de cobre), rotor (polos alternados), eixo. Partes em g.userData.partes */
export function gerador(o = {}) {
  const r = o.r ?? 1.2, g = new THREE.Group(), P = {};
  // estator: anel com bobinas por dentro
  const est = new THREE.Group();
  const anelS = new THREE.Shape(); anelS.absarc(0, 0, r, 0, Math.PI * 2, false); const fu = new THREE.Path(); fu.absarc(0, 0, r * .78, 0, Math.PI * 2, true); anelS.holes.push(fu);
  const anelG = new THREE.ExtrudeGeometry(anelS, { depth: r * .55, bevelEnabled: false, curveSegments: 14 }); anelG.rotateX(-Math.PI / 2);
  est.add(malha(anelG, mat(o.corEstator || PAL.branco)));
  const nb = o.bobinas ?? 12; est.userData.bobinas = [];
  for (let i = 0; i < nb; i++) {
    const a = i / nb * Math.PI * 2, b = malha(new THREE.BoxGeometry(r * .14, r * .45, r * .22), mat(PAL.cobre, { emis: PAL.laranja, emisForca: 0 }).clone());
    b.position.set(Math.cos(a) * r * .72, r * .275, Math.sin(a) * r * .72); b.rotation.y = -a; est.add(b); est.userData.bobinas.push(b);
  }
  P.estator = est; g.add(est);
  // rotor: cilindro com polos (ímãs) alternados
  const rot = new THREE.Group();
  rot.add(cilindro(r * .5, r * .5, PAL.grafite, { lados: 16, pos: [0, r * .025, 0] }));
  const np = o.polos ?? 8;
  for (let i = 0; i < np; i++) { const a = i / np * Math.PI * 2, m = malha(new THREE.BoxGeometry(r * .1, r * .46, r * .26), mat(i % 2 ? PAL.vermelho : PAL.azul)); m.position.set(Math.cos(a) * r * .55, r * .27, Math.sin(a) * r * .55); m.rotation.y = -a; rot.add(m); }
  P.rotor = rot; g.add(rot);
  // tampa
  const tampa = new THREE.Group(); tampa.add(cilindro(r * 1.02, r * .14, o.corTampa || PAL.gelo, { lados: 24, pos: [0, r * .58, 0] })); tampa.add(cilindro(r * .2, r * .22, PAL.grafite, { lados: 10, pos: [0, r * .72, 0] }));
  P.tampa = tampa; g.add(tampa);
  g.userData.partes = P;
  return g;
}
/** torre de transmissão treliçada low-poly. o: {h, cor} → grupo; g.userData.pontas = posições locais dos isoladores */
export function torre(o = {}) {
  const h = o.h ?? 3, g = new THREE.Group(), cor = o.cor || PAL.gelo, M = mat(cor), b = h * .17, tp = h * .05;
  const viga = (a, c, e = .025 * h) => { const A = V3(a), C = V3(c), L = A.distanceTo(C); const m = malha(new THREE.BoxGeometry(e, L, e), M); m.position.copy(A).add(C).multiplyScalar(.5); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), C.clone().sub(A).normalize()); g.add(m); return m; };
  const cantos = [[1, 1], [1, -1], [-1, -1], [-1, 1]];
  cantos.forEach(([sx, sz]) => viga([sx * b, 0, sz * b], [sx * tp, h, sz * tp]));
  for (let k = 0; k < 4; k++) {           // travessas em X
    const y0 = h * k / 4, y1 = h * (k + 1) / 4, w0 = lerp(b, tp, k / 4), w1 = lerp(b, tp, (k + 1) / 4);
    viga([-w0, y0, w0], [w1, y1, w1], .015 * h); viga([w0, y0, -w0], [-w1, y1, -w1], .015 * h);
    viga([w0, y0, w0], [w1, y1, -w1], .015 * h); viga([-w0, y0, -w0], [-w1, y1, w1], .015 * h);
  }
  const bracos = [h * .8, h * .97], pontas = [];
  bracos.forEach((y, i) => { const L = h * (i ? .22 : .32); viga([-L, y, 0], [L, y, 0], .03 * h); [-L, L].forEach(x => { const iso = cilindro(.025 * h, .07 * h, PAL.grafite, { lados: 6, pos: [x, y - .07 * h, 0] }); g.add(iso); pontas.push(new THREE.Vector3(x, y - .07 * h, 0)); }); });
  g.userData.pontas = pontas; return g;
}
/** curva de cabo pendurado entre dois pontos (catenária aproximada) */
export function catenaria(a, b, caida = .4) { const A = V3(a), B = V3(b), M = A.clone().add(B).multiplyScalar(.5); M.y -= caida * 2; return new THREE.QuadraticBezierCurve3(A, M, B); }
/** cabo fino ao longo de curva */
export function cabo(curva, o = {}) { return malha(new THREE.TubeGeometry(curva, o.seg ?? 24, o.raio ?? .018, 4, false), mat(o.cor || PAL.carvao), { sombra: false }); }

/** prédio low-poly com janelas acendíveis. o: {w,d,andares,altAndar,cor,seed} → g.userData.janelas = [{malha, ordem}] */
export function predio(o = {}) {
  const w = o.w ?? 1, d = o.d ?? 1, n = o.andares ?? 4, ha = o.altAndar ?? .32, h = n * ha + .1, g = new THREE.Group();
  g.add(caixa(w, h, d, o.cor || PAL.branco, { pos: [0, 0, 0], chanfro: .03, plano: true }));
  g.add(caixa(w * .9, .06, d * .9, PAL.gelo, { pos: [0, h, 0], chanfro: .01 }));
  const jan = []; const r = rng(o.seed ?? 3);
  const cols = Math.max(1, Math.round(w / .26)), colsD = Math.max(1, Math.round(d / .26));
  const face = (nc, largura, fn) => { for (let a = 0; a < n; a++) for (let c = 0; c < nc; c++) { const u = (c + .5) / nc - .5; jan.push(fn(u * largura, .12 + a * ha + ha * .45, r())); } };
  face(cols, w, (x, y, k) => ({ p: [x, y, d / 2 + .006], ry: 0, k }));
  face(cols, w, (x, y, k) => ({ p: [x, y, -d / 2 - .006], ry: Math.PI, k }));
  face(colsD, d, (z, y, k) => ({ p: [w / 2 + .006, y, z], ry: Math.PI / 2, k }));
  face(colsD, d, (z, y, k) => ({ p: [-w / 2 - .006, y, z], ry: -Math.PI / 2, k }));
  g.userData.janelas = jan; g.userData.alt = h; return g;
}
/** cidade: muitos prédios + janelas numa InstancedMesh só. o: {lotes:[{x,z,w,d,andares,cor}], acesa:'#ffd27a'} → cid.acender(fn(janela)→0..1) */
export function cidade(o) {
  const g = new THREE.Group(), lista = [];
  o.lotes.forEach((l, i) => {
    const p = predio({ ...l, seed: i * 13 + 5 }); p.position.set(l.x, l.y ?? 0, l.z); p.rotation.y = l.ry ?? 0; g.add(p);
    p.updateMatrixWorld(true);
    p.userData.janelas.forEach(j => lista.push({ ...j, mundo: new THREE.Vector3(...j.p).applyMatrix4(p.matrixWorld), ry: j.ry + (l.ry ?? 0), predio: i }));
  });
  const im = new THREE.InstancedMesh(new THREE.PlaneGeometry(.13, .15), new THREE.MeshBasicMaterial({ color: '#ffffff', toneMapped: false }), lista.length);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(1, 1, 1);
  lista.forEach((j, i) => { q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), j.ry); m4.compose(j.mundo.clone().sub(g.position), q, sc); im.setMatrixAt(i, m4); im.setColorAt(i, new THREE.Color(o.apagada || '#353a43')); });
  g.add(im);
  const off = new THREE.Color(o.apagada || '#353a43'), on = new THREE.Color(o.acesa || '#ffd27a').multiplyScalar(o.forca ?? 2.6), c = new THREE.Color();
  g.userData.janelas = lista;
  /** fn(janela) → 0..1 (quanto está acesa) */
  g.userData.acender = fn => { lista.forEach((j, i) => { im.setColorAt(i, c.copy(off).lerp(on, clamp(fn(j)))); }); im.instanceColor.needsUpdate = true; };
  return g;
}

// ───────────────────────── fluxos, setas e partículas ─────────────────────────
/**
 * Partículas que andam por uma curva (água no cano, energia no cabo, ar, sangue…).
 * o: {n, forma:'bola'|'seta'|'capsula', tam, cor, forca (brilho), vel (voltas/s), espalha (desvio lateral)}
 * f.update(t, quantidade 0..1) — quantidade controla quantas aparecem (o fluxo "liga").
 */
export function fluxo(curva, o = {}) {
  const n = o.n ?? 40, tam = o.tam ?? .08;
  let geo;
  if (o.forma === 'seta') { const s = new THREE.Shape(); s.moveTo(0, tam * 1.2); s.lineTo(tam * .9, -tam * .5); s.lineTo(0, -tam * .1); s.lineTo(-tam * .9, -tam * .5); s.closePath(); geo = new THREE.ExtrudeGeometry(s, { depth: tam * .35, bevelEnabled: false }); geo.translate(0, 0, -tam * .17); geo.rotateX(Math.PI / 2); }
  else if (o.forma === 'capsula') { geo = new THREE.CapsuleGeometry(tam * .45, tam * 1.6, 3, 6); geo.rotateX(Math.PI / 2); }
  else geo = new THREE.IcosahedronGeometry(tam * .6, 1);
  const material = o.material || (o.forca ? brilho(o.cor || PAL.aguaClara, o.forca) : mat(o.cor || PAL.aguaClara, { plano: false }));
  const im = new THREE.InstancedMesh(geo, material, n); im.frustumCulled = false; im.castShadow = false;
  const r = rng(o.seed ?? 11), fases = [...Array(n)].map((_, i) => (i + r() * .6) / n), des = [...Array(n)].map(() => [(r() - .5) * 2, (r() - .5) * 2]);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3(), Z = new THREE.Vector3(0, 0, 1), up = new THREE.Vector3(0, 1, 0), lado = new THREE.Vector3(), cima = new THREE.Vector3();
  im.userData.update = (t, qt = 1, vel = o.vel ?? .35) => {
    for (let i = 0; i < n; i++) {
      const u = ((fases[i] + t * vel) % 1 + 1) % 1, vis = (i / n) < qt ? 1 : 0;
      curva.getPointAt(u, p); const tg = curva.getTangentAt(u);
      if (o.espalha) { lado.crossVectors(tg, up).normalize(); if (lado.lengthSq() < .01) lado.set(1, 0, 0); cima.crossVectors(lado, tg).normalize(); p.addScaledVector(lado, des[i][0] * o.espalha).addScaledVector(cima, des[i][1] * o.espalha); }
      q.setFromUnitVectors(Z, tg); const k = vis * Math.min(1, u * 12, (1 - u) * 12); s.set(k, k, k);
      m4.compose(p, q, s); im.setMatrixAt(i, m4);
    }
    im.instanceMatrix.needsUpdate = true;
  };
  return im;
}
/** trilha que se desenha ao longo da curva (tubo luminoso; t.progresso(0..1)) */
export function trilha(curva, o = {}) {
  const geo = new THREE.TubeGeometry(curva, o.seg ?? 120, o.raio ?? .05, 6, false);
  const m = malha(geo, o.forca ? brilho(o.cor || PAL.verde, o.forca) : mat(o.cor || PAL.verde), { sombra: false });
  const total = geo.index.count; m.userData.progresso = k => geo.setDrawRange(0, Math.floor(clamp(k) * total / 6) * 6);
  m.userData.progresso(0); return m;
}
/** seta 3D chata (fita + ponta) ao longo de uma curva, desenhada por progresso. o: {largura, cor, altura} */
export function seta(curva, o = {}) {
  const n = 60, L = o.largura ?? .25, up = new THREE.Vector3(0, 1, 0), P = [];
  const pts = []; for (let i = 0; i <= n; i++) { const u = i / n * .86, p = curva.getPointAt(u), tg = curva.getTangentAt(u), s = new THREE.Vector3().crossVectors(tg, o.normal ? V3(o.normal) : up).normalize().multiplyScalar(L / 2); pts.push([p.clone().add(s), p.clone().sub(s)]); }
  for (let i = 0; i < n; i++) { const [a, b] = pts[i], [c, d] = pts[i + 1]; P.push(...a.toArray(), ...c.toArray(), ...b.toArray(), ...b.toArray(), ...c.toArray(), ...d.toArray()); }
  const pf = curva.getPointAt(.86), pt = curva.getPointAt(1), tgf = curva.getTangentAt(.86), sf = new THREE.Vector3().crossVectors(tgf, o.normal ? V3(o.normal) : up).normalize().multiplyScalar(L * 1.1);
  P.push(...pf.clone().add(sf).toArray(), ...pt.toArray(), ...pf.clone().sub(sf).toArray());
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); geo.computeVertexNormals();
  const m = malha(geo, o.forca ? brilho(o.cor || PAL.laranja, o.forca) : mat(o.cor || PAL.laranja, { lados: true }), { sombra: false });
  const tot = P.length / 3; m.userData.progresso = k => geo.setDrawRange(0, k >= 1 ? tot : Math.floor(clamp(k / .9) * (tot - 3) / 3) * 3);
  m.userData.progresso(0); return m;
}
/** poeira/estrelas flutuando no fundo (bokeh com o DOF). o: {n, centro, raio:[rx,ry,rz], cores, tam} */
export function poeira(o = {}) {
  const n = o.n ?? 160, r = rng(o.seed ?? 5), c = V3(o.centro || [0, 0, 0]), R = o.raio || [20, 12, 20];
  const cores = o.cores || ['#ffffff', '#ffffff', '#ffffff', '#ffffff', PAL.laranja, '#8fb0ff'];
  const g = new THREE.Group(), geo = new THREE.IcosahedronGeometry(o.tam ?? .05, 1), base = [];
  const mats = cores.map(k => brilho(k, 1.15));
  for (let i = 0; i < n; i++) {
    const m = new THREE.Mesh(geo, mats[Math.floor(r() * mats.length)]); const p = [c.x + (r() - .5) * 2 * R[0], c.y + (r() - .5) * 2 * R[1], c.z + (r() - .5) * 2 * R[2]];
    m.position.set(...p); const s = .4 + r() * 1.2; m.scale.setScalar(s); base.push({ p, f: r() * 6.28, v: .1 + r() * .25 }); g.add(m);
  }
  g.userData.update = t => g.children.forEach((m, i) => { const b = base[i]; m.position.set(b.p[0] + Math.sin(t * b.v + b.f) * .25, b.p[1] + t * b.v * .35 + Math.sin(t * .7 + b.f) * .12, b.p[2] + Math.cos(t * b.v * .8 + b.f) * .25); });
  return g;
}

// ───────────────────────── corte e explosão ─────────────────────────
/**
 * Vista em corte. Um plano que corta tudo o que você aplicar; a face cortada aparece como "seção" chapada
 * (truque: as faces de trás do sólido, desenhadas sem luz na cor da seção). Funciona com malhas FECHADAS.
 * const c = LP.corte([-1,0,0]);  c.aplicar(obj, {secao:'#b07a52', faixas:[[y,cor],...]});  c.pos(0)  (mantém o lado x ≤ 0)
 */
export function corte(normal = [-1, 0, 0], pos = 100) {
  const n = V3(normal).normalize(), plano = new THREE.Plane(n, pos), clones = new Map();
  const secaoMat = (cor, faixas, hach) => {
    const m = new THREE.MeshBasicMaterial({ color: cor, side: THREE.BackSide, clippingPlanes: [plano], toneMapped: true });
    faixas = faixas || [];
    if (faixas.length || hach) {
      m.onBeforeCompile = sh => {
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vMundo;').replace('#include <project_vertex>', '#include <project_vertex>\nvMundo = (modelMatrix * vec4(transformed,1.)).xyz;');
        const decl = faixas.map((f, i) => `uniform float uY${i}; uniform vec3 uC${i};`).join('\n');
        faixas.forEach(([y, c], i) => { sh.uniforms['uY' + i] = { value: y }; sh.uniforms['uC' + i] = { value: new THREE.Color(c) }; });
        sh.uniforms.uHc = { value: new THREE.Color(hach ? hach[0] : '#000') }; sh.uniforms.uHe = { value: hach ? hach[1] ?? .35 : 1 };
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vMundo; uniform vec3 uHc; uniform float uHe;\n' + decl)
          .replace('vec4 diffuseColor = vec4( diffuse, opacity );', `vec3 dc = diffuse;\n${faixas.map((f, i) => `if (vMundo.y < uY${i}) { dc = uC${i}; }`).join(' else ')}\n${hach ? 'if (fract((vMundo.y + vMundo.z + vMundo.x) / uHe) < .22) dc = uHc;' : ''}\nvec4 diffuseColor = vec4( dc, opacity );`);
      };
      m.customProgramCacheKey = () => 'faixas' + faixas.map(f => f.join()).join('|') + (hach ? 'h' + hach.join() : '');
    }
    return m;
  };
  return {
    plano,
    /** constante do plano: com normal (−1,0,0), pos(c) mantém x ≤ c */
    pos(c) { plano.constant = c; },
    /** aplica a todas as malhas de obj. o: {secao: cor | null (sem tampa), faixas} */
    aplicar(obj, o = {}) { // o: {secao: cor, faixas: [[y, cor]…] (de baixo p/ cima), hachura: [cor, espaçamento]}
      const alvo = []; obj.traverse(m => { if (m.isMesh && !m.isInstancedMesh) alvo.push(m); });
      alvo.forEach(m => {
        const troca = mm => { if (!clones.has(mm)) { const c = mm.clone(); c.clippingPlanes = [plano]; c.clipShadows = true; clones.set(mm, c); } return clones.get(mm); };
        m.material = Array.isArray(m.material) ? m.material.map(troca) : troca(m.material);
        if (o.secao && m.material.side !== THREE.BackSide) {
          const t = new THREE.Mesh(m.geometry, secaoMat(o.secao, o.faixas, o.hachura)); t.castShadow = false; t.receiveShadow = false; t.renderOrder = -1; m.add(t);
        }
      });
      return obj;
    },
  };
}
/**
 * Seção de água num corte em x (o truque das faces de trás falha quando há terreno dentro do volume):
 * perfil chapado entre o nível e o chão, refeito a cada pos(c). o: {z:[z0,z1], nivel, fundo, chao:(x,z)→y, cor, n}
 */
export function secaoAgua(o) {
  const n = o.n ?? 90, geo = new THREE.BufferGeometry(), P = new Float32Array(n * 18);
  geo.setAttribute('position', new THREE.BufferAttribute(P, 3));
  const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: o.cor || '#4a8fd6', side: THREE.DoubleSide })); m.frustumCulled = false;
  m.userData.pos = c => {
    let k = 0; const [z0, z1] = o.z, b = z => Math.max(o.chao(c, z), o.fundo ?? -99);
    for (let i = 0; i < n; i++) {
      const za = lerp(z0, z1, i / n), zb = lerp(z0, z1, (i + 1) / n), ba = Math.min(b(za), o.nivel), bb = Math.min(b(zb), o.nivel), x = c - .004;
      P.set([x, ba, za, x, o.nivel, za, x, bb, zb, x, bb, zb, x, o.nivel, za, x, o.nivel, zb], k); k += 18;
    }
    geo.attributes.position.needsUpdate = true; geo.computeBoundingSphere(); m.visible = c < 50;
  };
  return m;
}
/**
 * Vista explodida: cada parte guarda a posição de origem e um deslocamento; explodir(partes, k) leva de 0 (montado) a 1 (explodido).
 * LP.prepararExplosao(parte, [dx,dy,dz], giro?)
 */
export function prepararExplosao(obj, desl, giro = [0, 0, 0]) { obj.userData.ex = { base: obj.position.clone(), rbase: obj.rotation.clone(), d: V3(desl), g: giro }; return obj; }
export function explodir(partes, k) {
  partes.forEach((p, i) => { const e = p.userData.ex; if (!e) return; const kk = clamp(k); p.position.copy(e.base).addScaledVector(e.d, kk); p.rotation.set(e.rbase.x + e.g[0] * kk, e.rbase.y + e.g[1] * kk, e.rbase.z + e.g[2] * kk); });
}
/** "brotar": escala 0 → 1 com back.out (peças entrando na maquete). Use com fase() */
export function brotar(obj, k, eixo = 'xyz') { const s = Math.max(1e-4, k); obj.visible = k > .001; obj.scale.set(eixo.includes('x') ? s : 1, eixo.includes('y') ? s : 1, eixo.includes('z') ? s : 1); }

// ───────────────────────── câmera por capítulos ─────────────────────────
/**
 * Roteiro de câmera: planos com janela [t0,t1), posição/alvo inicial→final e ease. Cada plano começa com "rack focus"
 * (tudo desfocado → nítido em `rack` s), a marca das referências. Opções por plano:
 *  {t0,t1, de:{pos,alvo}, ate:{pos,alvo}, ease:'sine.inOut', arco:true (interpola em órbita ao redor do alvo),
 *   fov, foco:(distância extra além do alvo), abertura, rack:.45, sombra:[cx,cy,cz,raio], antes(t,k), exposicao}
 * Devolve fn(t) para chamar no S.update.
 */
export function roteiroCamera(S, planos) {
  const P = new THREE.Vector3(), A = new THREE.Vector3();
  const sph = (pos, alvo) => { const d = V3(pos).sub(V3(alvo)); const r = d.length(); return { r, th: Math.atan2(d.x, d.z), ph: Math.acos(clamp(d.y / r, -1, 1)) }; };
  let ultimo = null;
  return t => {
    const p = planos.find(q => t >= q.t0 && t < q.t1) || (t < planos[0].t0 ? planos[0] : planos[planos.length - 1]);
    const k = fase(t, p.t0, p.t1, p.ease || 'sine.inOut');
    const de = p.de, ate = p.ate || p.de;
    A.copy(V3(de.alvo)).lerp(V3(ate.alvo), k);
    if (p.arco) {
      const s0 = sph(de.pos, de.alvo), s1 = sph(ate.pos, ate.alvo); let dth = s1.th - s0.th; if (dth > Math.PI) dth -= 2 * Math.PI; if (dth < -Math.PI) dth += 2 * Math.PI;
      const r = lerp(s0.r, s1.r, k), th = s0.th + dth * k, ph = lerp(s0.ph, s1.ph, k);
      P.set(A.x + r * Math.sin(ph) * Math.sin(th), A.y + r * Math.cos(ph), A.z + r * Math.sin(ph) * Math.cos(th));
    } else P.copy(V3(de.pos)).lerp(V3(ate.pos), k);
    S.camera.position.copy(P); S.camera.lookAt(A);
    if (p.rolagem) S.camera.rotateZ(lerp(p.rolagem[0], p.rolagem[1] ?? p.rolagem[0], k));
    const fov = Array.isArray(p.fov) ? lerp(p.fov[0], p.fov[1], k) : (p.fov ?? 30);
    if (S.camera.fov !== fov) { S.camera.fov = fov; S.camera.updateProjectionMatrix(); }
    // foco no alvo (+ ajuste), com rack focus na entrada do plano
    const rack = p.rack ?? .45, kr = fase(t, p.t0, p.t0 + rack, 'power2.out');
    const dist = P.distanceTo(A) + (p.foco ?? 0);
    S.dof.foco = lerp(dist * (p.rackDe ?? 3.2), dist, kr);
    S.dof.abertura = (p.abertura ?? .018) * lerp(p.rackMais ?? 1.6, 1, kr);
    if (p.sombra && ultimo !== p) S.sombra(p.sombra.slice(0, 3), p.sombra[3]);
    if (p.exposicao !== undefined) S.renderer.toneMappingExposure = Array.isArray(p.exposicao) ? lerp(p.exposicao[0], p.exposicao[1], k) : p.exposicao;
    ultimo = p;
    return p;
  };
}

// ───────────────────────── HUD (HTML sobre o 3D) ─────────────────────────
const CSS = `
.lp-hud{position:absolute;inset:0;pointer-events:none;z-index:5;font-family:'Geist',sans-serif;color:#fff}
.lp-serie{position:absolute;left:69px;top:285px;font:500 23px/1 'JetBrains Mono',monospace;letter-spacing:.26em;color:${PAL.mono};text-transform:uppercase;white-space:nowrap;text-shadow:0 1px 8px rgba(0,0,0,.6)}
.lp-chip{position:absolute;left:62px;top:330px;height:70px;border-radius:35px;background:rgba(24,27,34,.86);border:1.5px solid rgba(255,255,255,.12);display:flex;align-items:center;padding:0 30px 0 17px;gap:15px;overflow:hidden;white-space:nowrap;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.lp-chip .bol{width:37px;height:37px;border-radius:50%;background:#eef0f4;flex:none}
.lp-chip .pt{width:10px;height:10px;border-radius:50%;background:${PAL.laranja};flex:none}
.lp-chip .tx{font:700 31px/1 'JetBrains Mono',monospace;letter-spacing:.17em;text-transform:uppercase}
.lp-leg{position:absolute;left:50%;top:1480px;transform:translate(-50%,-50%);width:max-content;max-width:860px;padding:22px 34px 24px;border-radius:20px;background:${PAL.caixa};font:700 49px/1.18 'Geist',sans-serif;letter-spacing:-.012em;text-align:center;white-space:normal;box-shadow:0 10px 30px rgba(0,0,0,.25)}
.lp-leg span{color:${PAL.apagado}} .lp-leg span.on{color:#fff}
.lp-rot{position:absolute;left:0;top:0;padding:14px 20px 15px 20px;border-radius:12px;background:rgba(20,23,29,.9);border:1.5px solid rgba(255,255,255,.1);white-space:nowrap;transform-origin:0 50%}
.lp-rot .t{font:700 33px/1.05 'Geist',sans-serif;display:flex;align-items:center;gap:12px}
.lp-rot .t i{width:11px;height:11px;border-radius:50%;border:2.5px solid #fff;display:inline-block;flex:none}
.lp-rot .s{font:500 20px/1 'JetBrains Mono',monospace;letter-spacing:.14em;color:${PAL.mono};text-transform:uppercase;margin-top:9px;padding-left:25px}
.lp-tag{position:absolute;left:50%;top:0;transform:translate(-50%,-50%);padding:16px 30px;border-radius:12px;background:${PAL.laranja};color:#1a1410;font:800 46px/1 'JetBrains Mono',monospace;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap;box-shadow:0 8px 26px rgba(255,106,42,.3)}
.lp-pain{position:absolute;left:62px;right:62px;top:440px;border-radius:18px;background:rgba(20,23,29,.9);border:1.5px solid rgba(255,255,255,.1);padding:22px 30px 20px}
.lp-pain .h{font:500 20px/1 'JetBrains Mono',monospace;letter-spacing:.16em;color:${PAL.mono};text-transform:uppercase;margin-bottom:16px}
.lp-pain .l{display:flex;justify-content:space-between;align-items:center;font:700 36px/1.35 'Geist',sans-serif}
.lp-pain .l b{font:800 38px/1 'Geist',sans-serif;color:${PAL.laranja}}
.lp-plac{position:absolute;left:62px;right:62px;top:430px;border-radius:18px;background:rgba(20,23,29,.9);border:1.5px solid rgba(255,255,255,.1);padding:20px 30px 18px;display:flex;justify-content:space-between}
.lp-plac .c{display:flex;flex-direction:column;gap:10px} .lp-plac .c.d{align-items:flex-end}
.lp-plac .r{font:500 20px/1 'JetBrains Mono',monospace;letter-spacing:.14em;color:${PAL.mono};text-transform:uppercase}
.lp-plac .v{font:800 84px/1 'Geist',sans-serif;letter-spacing:-.02em}
.lp-num{position:absolute;left:0;right:0;top:0;display:flex;flex-direction:column;align-items:center;gap:6px;transform-origin:50% 50%}
.lp-num .n{font:800 320px/.9 'Geist',sans-serif;-webkit-text-stroke:10px #fff;paint-order:stroke fill;letter-spacing:-.04em}
.lp-num .w{font:800 52px/1 'JetBrains Mono',monospace;letter-spacing:.06em;text-transform:uppercase;color:#1a1d23;-webkit-text-stroke:6px #fff;paint-order:stroke fill}
.lp-fios{position:absolute;inset:0;overflow:visible}
.lp-cota{font:600 21px/1 'JetBrains Mono',monospace;letter-spacing:.14em;fill:#fff;text-transform:uppercase}
`;
let HUD = null;
/** cria (uma vez) a camada do HUD e o SVG dos fios */
export function hud() {
  if (HUD) return HUD;
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  const el = document.createElement('div'); el.className = 'lp-hud'; document.getElementById('stage').appendChild(el);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'lp-fios'); svg.setAttribute('width', window.VIDEO.w); svg.setAttribute('height', window.VIDEO.h); el.appendChild(svg);
  HUD = { el, svg }; return HUD;
}
const svgEl = (nome, at = {}) => { const e = document.createElementNS('http://www.w3.org/2000/svg', nome); for (const k in at) e.setAttribute(k, at[k]); hud().svg.appendChild(e); return e; };
const div = (cls, html = '') => { const e = document.createElement('div'); e.className = cls; e.innerHTML = html; hud().el.appendChild(e); return e; };
/** projeta um ponto 3D (Vector3 ou Object3D) em px da tela */
export function tela(S, alvo, saida = new THREE.Vector3()) {
  if (alvo.isObject3D) alvo.getWorldPosition(saida); else saida.copy(alvo.isVector3 ? alvo : V3(alvo));
  saida.project(S.camera); return { x: (saida.x + 1) / 2 * window.VIDEO.w, y: (1 - saida.y) / 2 * window.VIDEO.h, atras: saida.z > 1 };
}

/** cabeçalho "COMO FUNCIONA · TEMA" + chip de capítulo. caps = [{t, txt}]. Troca: some (.12 s) e digita o novo (~45 letras/s) */
export function cabecalho(S, serie, caps, o = {}) {
  const se = div('lp-serie', serie); const chip = div('lp-chip', '<span class="bol"></span><span class="pt"></span><span class="tx"></span>');
  const tx = chip.querySelector('.tx'), pt = chip.querySelector('.pt');
  const t0 = o.t0 ?? .1;
  // larguras medidas no SETUP (depois das fontes)
  let larg = null;
  const medir = () => { larg = caps.map(c => { tx.textContent = c.txt; return chip.offsetWidth; }); tx.textContent = ''; };
  S.hud.push(t => {
    if (!larg) medir();
    const ap = fase(t, t0, t0 + .35, 'power3.out'); se.style.opacity = chip.style.opacity = ap; chip.style.transform = `translateY(${(1 - ap) * -14}px)`;
    let i = -1; caps.forEach((c, k) => { if (t >= c.t) i = k; }); if (i < 0) { tx.textContent = ''; return; }
    const c = caps[i], prev = caps[i - 1], dt = t - c.t;
    const n = Math.floor(dt * 45), txt = dt < .1 && prev ? prev.txt : c.txt.slice(0, Math.max(0, n - 4));
    tx.textContent = txt; tx.style.opacity = dt < .1 && prev ? 1 - dt / .1 : 1;
    const w0 = prev ? larg[i - 1] : 140, w = lerp(w0, larg[i], fase(t, c.t + .05, c.t + .3, 'power3.out'));
    chip.style.width = w + 'px';
    const pulso = Math.max(0, 1 - dt / .3); pt.style.transform = `scale(${1 + pulso * 1.2})`;
  });
  return { serie: se, chip };
}

/**
 * Legenda karaokê: frases [{t0, t1, txt}] — palavra acende (cinza → branca) no tempo; caixa entra com leve escala.
 * As palavras dividem a janela [t0, t1 − .35] proporcional ao tamanho. o: {y}
 */
export function legenda(S, frases, o = {}) {
  const box = div('lp-leg'); if (o.y) box.style.top = o.y + 'px';
  const F = frases.map(f => { const ws = f.txt.split(' '); const pesos = ws.map(w => w.length + 2), tot = pesos.reduce((a, b) => a + b, 0); let acc = 0; const fim = f.fala ?? (f.t1 - f.t0) * .78; return { ...f, ws, ts: pesos.map(p => { const v = f.t0 + acc / tot * fim; acc += p; return v; }) }; });
  let atual = null, spans = [];
  S.hud.push(t => {
    const f = F.find(q => t >= q.t0 && t < q.t1);
    if (!f) { box.style.opacity = 0; return; }
    if (atual !== f) { atual = f; box.innerHTML = f.ws.map(w => `<span>${w}</span>`).join(' '); spans = [...box.children]; }
    spans.forEach((s, i) => s.classList.toggle('on', t >= f.ts[i]));
    const a = fase(t, f.t0 - .02, f.t0 + .12, 'power2.out'), z = fase(t, f.t1 - .1, f.t1, 'power2.in');
    box.style.opacity = a * (1 - z); box.style.transform = `translate(-50%,-50%) scale(${.94 + .06 * a})`;
  });
  return box;
}

/**
 * Rótulo que acompanha um objeto 3D: cartão escuro (título + subtítulo mono) ligado por um fio fino a um ponto no objeto.
 * o: {alvo: Object3D|[x,y,z], titulo, sub, t0, t1, dx, dy (px do cartão em relação ao ponto), lado:'dir'|'esq'}
 */
export function rotulo(S, o) {
  const card = div('lp-rot', `<div class="t"><i></i>${o.titulo}</div>${o.sub ? `<div class="s">${o.sub}</div>` : ''}`);
  const fio = svgEl('line', { stroke: 'rgba(255,255,255,.85)', 'stroke-width': 2.2 }), ponto = svgEl('circle', { r: 7, fill: '#fff' }), anel = svgEl('circle', { r: 14, fill: 'none', stroke: 'rgba(255,255,255,.55)', 'stroke-width': 2 });
  let w = null, h = null; const alvo = o.alvo.isObject3D ? o.alvo : V3(o.alvo);
  S.hud.push(t => {
    if (w === null) { w = card.offsetWidth; h = card.offsetHeight; }
    const a = fase(t, o.t0, o.t0 + .3, 'power3.out'), z = o.t1 ? fase(t, o.t1 - .18, o.t1, 'power2.in') : 0, vis = a * (1 - z);
    const p = tela(S, alvo); const on = vis > .001 && !p.atras;
    [card, fio, ponto, anel].forEach(e => e.style.display = on ? '' : 'none'); if (!on) return;
    const esq = (o.lado || 'dir') === 'esq';
    const mg = o.margem ?? 36, cx = clamp(p.x + (o.dx ?? (esq ? -90 : 90)) - (esq ? w : 0), mg, window.VIDEO.w - mg - w), cy = clamp(p.y + (o.dy ?? -110) - h / 2, mg, window.VIDEO.h - mg - h);   // cartão nunca sai da tela
    const k = fase(t, o.t0, o.t0 + .25, 'back.out(1.7)');
    card.style.transform = `translate(${cx}px,${cy}px) scale(${.6 + .4 * k})`; card.style.opacity = vis;
    card.style.transformOrigin = esq ? '100% 50%' : '0 50%';
    const ex = p.x < cx ? cx : p.x > cx + w ? cx + w : (esq ? cx + w : cx), ey = cy + h / 2;
    const kf = fase(t, o.t0, o.t0 + .22, 'power2.out');
    fio.setAttribute('x1', p.x); fio.setAttribute('y1', p.y); fio.setAttribute('x2', lerp(p.x, ex, kf)); fio.setAttribute('y2', lerp(p.y, ey, kf)); fio.style.opacity = vis;
    ponto.setAttribute('cx', p.x); ponto.setAttribute('cy', p.y); ponto.setAttribute('r', 7 * fase(t, o.t0, o.t0 + .2, 'back.out(3)')); ponto.style.opacity = vis;
    const pul = fase(t, o.t0, o.t0 + .7, 'power2.out'); anel.setAttribute('cx', p.x); anel.setAttribute('cy', p.y); anel.setAttribute('r', 8 + 26 * pul); anel.style.opacity = vis * (1 - pul);
  });
  return card;
}

/** carimbo laranja inclinado (destaque de uma palavra). o: {t0, t1, y, giro} — entra com batida (escala 1.6 → 1 em 4 degraus) */
export function carimbo(S, txt, o = {}) {
  const e = div('lp-tag', txt); e.style.top = (o.y ?? 760) + 'px';
  S.hud.push(t => {
    const a = clamp((t - o.t0) / .12), z = o.t1 ? fase(t, o.t1 - .15, o.t1) : 0;
    if (t < o.t0 || (o.t1 && t > o.t1)) { e.style.display = 'none'; return; } e.style.display = '';
    const s = 1 + .6 * (1 - Math.floor(a * 4) / 4); e.style.transform = `translate(-50%,-50%) rotate(${o.giro ?? -6}deg) scale(${s})`; e.style.opacity = (a > 0 ? 1 : 0) * (1 - z);
  });
  return e;
}

/** painel de dados/etapas: linhas [{t, txt, val}] que acendem; o: {titulo, t0, t1, top} */
export function painel(S, linhas, o = {}) {
  const e = div('lp-pain', `<div class="h">${o.titulo || ''}</div>` + linhas.map(l => `<div class="l"><span>${l.txt}</span><b>${l.val ?? ''}</b></div>`).join(''));
  if (o.top) e.style.top = o.top + 'px';
  const L = [...e.querySelectorAll('.l')];
  S.hud.push(t => {
    const a = fase(t, o.t0, o.t0 + .3, 'power3.out'), z = o.t1 ? fase(t, o.t1 - .2, o.t1, 'power2.in') : 0;
    e.style.opacity = a * (1 - z); e.style.transform = `translateY(${(1 - a) * -20}px)`; e.style.display = a * (1 - z) > 0 ? '' : 'none';
    L.forEach((l, i) => { const k = fase(t, linhas[i].t, linhas[i].t + .25, 'power2.out'); l.style.opacity = .22 + .78 * k; l.style.transform = `translateX(${(1 - k) * 18}px)`; l.querySelector('b').style.opacity = k; });
  });
  return e;
}


/** placar de 2 números (ref. overbooking: "ASSENTOS 180 | VENDIDAS 183"). o: {esq:{rot,val}, dir:{rot,de,para,cor}, conta:[t0,t1], t0, t1, top} */
export function placar(S, o) {
  const e = div('lp-plac', `<div class="c"><span class="r">${o.esq.rot}</span><span class="v">${o.esq.val}</span></div><div class="c d"><span class="r">${o.dir.rot}</span><span class="v" style="color:${o.dir.cor || PAL.laranja}"></span></div>`);
  if (o.top) e.style.top = o.top + 'px';
  const v = e.querySelector('.d .v'), [c0, c1] = o.conta || [o.t0, o.t0];
  S.hud.push(t => {
    const a = fase(t, o.t0, o.t0 + .3, 'power3.out'), z = o.t1 ? fase(t, o.t1 - .2, o.t1, 'power2.in') : 0;
    e.style.display = a * (1 - z) > 0 ? '' : 'none'; e.style.opacity = a * (1 - z); e.style.transform = `translateY(${(1 - a) * -20}px)`;
    v.textContent = Math.round(lerp(o.dir.de ?? 0, o.dir.para, fase(t, c0, c1, 'power1.inOut'))).toLocaleString('pt-BR');
  });
  return e;
}
/** título de capítulo com numeral gigante (ref. elevador: "1 CABOS"). o: {n, txt, cor, t0, t1, y} */
export function tituloCapitulo(S, o) {
  const e = div('lp-num', `<span class="n" style="color:${o.cor || PAL.laranja}">${o.n}</span><span class="w">${o.txt}</span>`); e.style.top = (o.y ?? 640) + 'px';
  S.hud.push(t => {
    const a = fase(t, o.t0, o.t0 + .35, 'back.out(2)'), z = fase(t, o.t1 - .2, o.t1, 'power2.in'), vis = t >= o.t0 && t < o.t1;
    e.style.display = vis ? '' : 'none'; if (!vis) return;
    e.style.opacity = Math.min(1, a * 3) * (1 - z); e.style.transform = `scale(${.5 + .5 * a + .15 * z})`;
  });
  return e;
}

/** cota (linha de medida com tracinhos nas pontas e texto) entre dois pontos 3D. o: {t0, t1, texto, lado(px de afastamento)} */
export function cota(S, a, b, o = {}) {
  const ln = svgEl('line', { stroke: '#fff', 'stroke-width': 2.4, 'stroke-dasharray': '10 7' }), t1 = svgEl('line', { stroke: '#fff', 'stroke-width': 3 }), t2 = svgEl('line', { stroke: '#fff', 'stroke-width': 3 });
  const tx = svgEl('text', { class: 'lp-cota', 'text-anchor': 'middle' }); tx.textContent = o.texto || '';
  const A = V3(a), B = V3(b);
  S.hud.push(t => {
    const k = fase(t, o.t0, o.t0 + .45, 'power3.out'), z = o.t1 ? fase(t, o.t1 - .2, o.t1) : 0, vis = (t >= o.t0 ? 1 : 0) * (1 - z);
    [ln, t1, t2, tx].forEach(e => e.style.opacity = vis); if (!vis) return;
    const p = tela(S, A), q0 = tela(S, B), q = { x: lerp(p.x, q0.x, k), y: lerp(p.y, q0.y, k) };
    const dx = q0.x - p.x, dy = q0.y - p.y, L = Math.hypot(dx, dy) || 1, nx = -dy / L * 16, ny = dx / L * 16;
    ln.setAttribute('x1', p.x); ln.setAttribute('y1', p.y); ln.setAttribute('x2', q.x); ln.setAttribute('y2', q.y);
    t1.setAttribute('x1', p.x - nx); t1.setAttribute('y1', p.y - ny); t1.setAttribute('x2', p.x + nx); t1.setAttribute('y2', p.y + ny);
    t2.setAttribute('x1', q.x - nx); t2.setAttribute('y1', q.y - ny); t2.setAttribute('x2', q.x + nx); t2.setAttribute('y2', q.y + ny); t2.style.opacity = vis * (k > .95 ? 1 : 0);
    const mx = (p.x + q.x) / 2 + (o.lado ?? 0), my = (p.y + q.y) / 2; tx.setAttribute('x', mx); tx.setAttribute('y', my + 7); tx.style.opacity = vis * fase(t, o.t0 + .3, o.t0 + .5);
  });
}
