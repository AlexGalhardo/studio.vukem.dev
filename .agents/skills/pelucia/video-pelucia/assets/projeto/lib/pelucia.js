// pelucia.js — biblioteca do estilo "pelúcia" (three.js, módulo ES)
// Bonecos e objetos de PELÚCIA flutuando num estúdio creme: pelo curto de verdade (cascas/shells com fios),
// feltro, botão plástico, costura, sombra enorme e desfocada no chão e HUD editorial de "estudo de material".
// Uso na página:  import * as PL from '../../lib/pelucia.js';  const S = PL.palco({...});
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
export { THREE };

// ───────────────────────── paleta (amostrada da referência + marca fictícia) ─────────────────────────
export const PAL = {
  fundo: '#e1ddd8', fundoClaro: '#e9e6e1', sombra: '#5f564b', tinta: '#1d1b18', texto: '#57524b', fio: '#b5afa6',
  bronze: '#857860', bronzeVentre: '#ece5d6', laguna: '#1f8791', lagunaClaro: '#5fb8bf', porDoSol: '#e0603a', porDoSolClaro: '#f39a6c',
  creme: '#f1ebe0', kraft: '#b08e62', carvao: '#3a3734', inox: '#9a9ea0',
  pele: ['#4f3223', '#7a4b31', '#b07a52', '#d8a47c', '#ecc3a0'], cabelo: ['#17110e', '#2f2119', '#5a3d27', '#8a6440'],
  linha: '#2a2420', rosa: '#e7907c', boca: '#8e2a2a',
};

// ───────────────────────── utilidades ─────────────────────────
export function rng(seed = 1) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const suave = (a, b, v) => { const k = clamp((v - a) / (b - a)); return k * k * (3 - 2 * k); };
export const fase = (t, t0, t1, ease = 'none') => gsap.parseEase(ease)(clamp((t - t0) / (t1 - t0)));
const V3 = a => (a && a.isVector3 ? a.clone() : new THREE.Vector3(...(a || [0, 0, 0])));
export const v3 = V3;
/** onda periódica: sen(2π(t/periodo + desloc)). Use períodos que dividem a duração → loop perfeito */
export const onda = (t, periodo, desloc = 0) => Math.sin(2 * Math.PI * (t / periodo + desloc));
/** quadros-chave periódicos: lista [[t, v], ...] (v número ou array), interpolação com ease; `per` fecha o loop */
export function chaves(t, lista, o = {}) {
  const per = o.per, ease = gsap.parseEase(o.ease || 'sine.inOut');
  if (per) t = ((t % per) + per) % per;
  let a = lista[0], b = lista[lista.length - 1];
  if (t <= a[0]) return a[1]; if (t >= b[0]) return b[1];
  for (let i = 0; i < lista.length - 1; i++) if (t >= lista[i][0] && t <= lista[i + 1][0]) { a = lista[i]; b = lista[i + 1]; break; }
  const k = ease((t - a[0]) / Math.max(1e-6, b[0] - a[0]));
  return Array.isArray(a[1]) ? a[1].map((x, i) => lerp(x, b[1][i], k)) : lerp(a[1], b[1], k);
}

// ───────────────────────── palco: renderer + DOF suave + acabamento ─────────────────────────
const QUAD_VERT = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
const DOF_FRAG = `
uniform sampler2D tCor, tProf; uniform float uFoco, uAbert, uMax, uNear, uFar; uniform vec2 uRes; varying vec2 vUv;
float lin(float d){ float z = d * 2. - 1.; return 2. * uNear * uFar / (uFar + uNear - z * (uFar - uNear)); }
float coc(float z){ if (z > uFar * .95) return 0.; return clamp(abs(z - uFoco) / z * uAbert * uRes.y, 0., uMax); }  // fundo liso não desfoca (evita halo)
void main(){
  float zC = lin(texture2D(tProf, vUv).r), cC = coc(zC);
  vec3 cor = texture2D(tCor, vUv).rgb; float tot = 1.; float r = 1.5; float ang = 0.;
  for (int i = 0; i < 160; i++) {
    if (r >= uMax) break;
    vec2 uv = vUv + vec2(cos(ang), sin(ang)) * r / uRes;
    vec3 c = texture2D(tCor, uv).rgb; float z = lin(texture2D(tProf, uv).r); float cs = coc(z);
    if (z > zC) cs = clamp(cs, 0., cC * 2.);
    float m = smoothstep(r - .5, r + .5, cs);
    cor += mix(cor / tot, c, m); tot += 1.; ang += 2.39996323; r += 2.4 / r;
  }
  gl_FragColor = vec4(cor / tot, 1.);
}`;
class PassDOF extends Pass {
  constructor(scene, camera, w, h) {
    super(); this.scene = scene; this.camera = camera;
    this.rt = new THREE.WebGLRenderTarget(w, h, { type: THREE.HalfFloatType, samples: 4, depthTexture: new THREE.DepthTexture(w, h) });
    this.mat = new THREE.ShaderMaterial({ uniforms: { tCor: { value: this.rt.texture }, tProf: { value: this.rt.depthTexture }, uFoco: { value: 10 }, uAbert: { value: .02 }, uMax: { value: 10 }, uNear: { value: .1 }, uFar: { value: 200 }, uRes: { value: new THREE.Vector2(w, h) } }, vertexShader: QUAD_VERT, fragmentShader: DOF_FRAG, depthTest: false, depthWrite: false });
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
  vec3 col = texture2D(tDiffuse, vUv).rgb; col *= 1. - uVig * smoothstep(.25, 1., d);
  col += (h(vUv * uRes + fract(uTime * 7.13) * 100.) - .5) * uGrain; gl_FragColor = vec4(col, 1.); }`;

/** fundo de estúdio: gradiente vertical + mancha de luz radial (textura de tela) */
export function fundoEstudio(cores = ['#e6e2dc', '#e1ddd8', '#dcd7d1'], luz = { x: .55, y: .38, r: .65, forca: .05 }) {
  const c = document.createElement('canvas'); c.width = 270; c.height = 480; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, c.height); cores.forEach((k, i) => gr.addColorStop(i / (cores.length - 1), k)); g.fillStyle = gr; g.fillRect(0, 0, c.width, c.height);
  const rg = g.createRadialGradient(c.width * luz.x, c.height * luz.y, 0, c.width * luz.x, c.height * luz.y, c.height * luz.r);
  rg.addColorStop(0, `rgba(255,252,246,${luz.forca})`); rg.addColorStop(1, 'rgba(255,252,246,0)'); g.fillStyle = rg; g.fillRect(0, 0, c.width, c.height);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; return tx;
}

// luz compartilhada entre os materiais de pelo (uniforms únicos → mudar aqui muda em todos)
const LUZ = {
  uKeyDir: { value: new THREE.Vector3(-.45, .85, .55).normalize() }, uKeyCor: { value: new THREE.Color('#fff4e6').multiplyScalar(1.15) },
  uRimDir: { value: new THREE.Vector3(.5, .4, -.9).normalize() }, uRimCor: { value: new THREE.Color('#fff8ee').multiplyScalar(.9) },
  uCeu: { value: new THREE.Color('#f4efe8').multiplyScalar(.62) }, uChao: { value: new THREE.Color('#bdb3a6').multiplyScalar(.42) },
  uRot: { value: new THREE.Matrix3() }, uRot2: { value: new THREE.Matrix3() },
};
{ const m = new THREE.Matrix4().makeRotationAxis(new THREE.Vector3(1, 1, 1).normalize(), .71); LUZ.uRot.value.setFromMatrix4(m);
  const m2 = new THREE.Matrix4().makeRotationAxis(new THREE.Vector3(-1, 2, .5).normalize(), 1.37); LUZ.uRot2.value.setFromMatrix4(m2); }

/**
 * Palco do estilo. o: {fundo:[cores], luzFundo, fov, exposicao, dof:{abertura,max}, grao, vinheta,
 *   luz:{key:[x,y,z], keyForca, rim:[x,y,z], rimForca, ceu, chao, amb}, ambiente (intensidade do RoomEnvironment p/ feltro e plástico)}
 * Devolve S = {scene, camera, renderer, composer, dof, update(t) (você define), antes:[fn(t)], hud:[fn(t)]}.
 */
export function palco(o = {}) {
  const V = window.VIDEO;
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = o.exposicao ?? 1;
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.domElement.className = 'layer';
  (o.parent || document.getElementById('stage')).prepend(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = fundoEstudio(o.fundo, o.luzFundo);
  const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture; scene.environmentIntensity = o.ambiente ?? .55;
  const camera = new THREE.PerspectiveCamera(o.fov ?? 24, V.w / V.h, .1, 200);

  // luz: chave quente do alto à esquerda, contraluz por trás à direita (dá o "veludo" na borda), céu/chão de estúdio
  const L = o.luz || {};
  if (L.key) LUZ.uKeyDir.value.set(...L.key).normalize(); if (L.rim) LUZ.uRimDir.value.set(...L.rim).normalize();
  LUZ.uKeyCor.value.set(L.keyCor || '#fff4e6').multiplyScalar(L.keyForca ?? 1.15); LUZ.uRimCor.value.set(L.rimCor || '#fff8ee').multiplyScalar(L.rimForca ?? .9);
  LUZ.uCeu.value.set(L.ceu || '#f4efe8').multiplyScalar(L.amb ?? .62); LUZ.uChao.value.set(L.chao || '#bdb3a6').multiplyScalar((L.amb ?? .62) * .68);
  const key = new THREE.DirectionalLight(L.keyCor || '#fff4e6', (L.keyForca ?? 1.15) * Math.PI * .8); key.position.copy(LUZ.uKeyDir.value).multiplyScalar(20); scene.add(key);
  const rim = new THREE.DirectionalLight(L.rimCor || '#fff8ee', (L.rimForca ?? .9) * Math.PI * .5); rim.position.copy(LUZ.uRimDir.value).multiplyScalar(20); scene.add(rim);
  const hemi = new THREE.HemisphereLight(L.ceu || '#f4efe8', L.chao || '#bdb3a6', (L.amb ?? .62) * Math.PI * .5); scene.add(hemi);

  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(V.w, V.h, { type: THREE.HalfFloatType }));
  composer.setPixelRatio(1); composer.setSize(V.w, V.h);
  const dofPass = new PassDOF(scene, camera, V.w, V.h); composer.addPass(dofPass);
  composer.addPass(new OutputPass());
  const acab = new ShaderPass({ uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: o.grao ?? .018 }, uVig: { value: o.vinheta ?? .1 }, uRes: { value: new THREE.Vector2(V.w, V.h) } }, vertexShader: QUAD_VERT, fragmentShader: ACAB_FRAG });
  composer.addPass(acab);
  const dof = { foco: 16, abertura: o.dof?.abertura ?? .02, max: o.dof?.max ?? 9 };
  const S = { THREE, renderer, scene, camera, composer, key, rim, hemi, dof, acab, update: null, antes: [], hud: [] };
  onTick(t => {
    acab.uniforms.uTime.value = t;
    if (S.update) S.update(t);
    scene.updateMatrixWorld(); camera.updateMatrixWorld();
    for (const f of S.antes) f(t);
    const u = dofPass.mat.uniforms; u.uFoco.value = dof.foco; u.uAbert.value = dof.abertura; u.uMax.value = Math.max(2, dof.max);
    for (const h of S.hud) h(t);
    composer.render();
  });
  return S;
}

/** câmera com deriva leve e periódica (loop perfeito): orbita ±giro graus e sobe/desce ±alt em `periodo` s */
export function derivaCamera(S, o = {}) {
  const alvo = V3(o.alvo || [0, .4, 0]), dist = o.dist ?? 16, elev = (o.elev ?? 20) * Math.PI / 180, az0 = (o.az ?? 0) * Math.PI / 180;
  const giro = (o.giro ?? 3) * Math.PI / 180, alt = o.alt ?? .12, per = o.periodo ?? window.VIDEO.dur;
  S.camera.fov = o.fov ?? S.camera.fov; S.camera.updateProjectionMatrix();
  return t => {
    const az = az0 + giro * onda(t, per), el = elev + alt * .02 * onda(t, per, .25);
    S.camera.position.set(alvo.x + dist * Math.cos(el) * Math.sin(az), alvo.y + dist * Math.sin(el) + alt * onda(t, per, .25), alvo.z + dist * Math.cos(el) * Math.cos(az));
    S.camera.lookAt(alvo);
    S.dof.foco = S.camera.position.distanceTo(alvo) + (o.foco ?? 0);
  };
}

// ───────────────────────── PELO por cascas (shells) ─────────────────────────
const PELO_VERT = `
uniform float uLen, uN, uDobra; uniform vec3 uPente, uGrav;
varying vec3 vP0, vNw, vPw, vTw, vNo; varying float vH;
void main(){
#ifdef USE_INSTANCING
  float h = float(gl_InstanceID + 1) / uN;
#else
  float h = 0.;
#endif
  vec3 n = normalize(normal);
  vec3 pt = uPente - n * dot(uPente, n);                 // direção do penteado no plano da superfície
  vec3 p = position + n * h * uLen + pt * uDobra * h * h * uLen;
  vec4 wp = modelMatrix * vec4(p, 1.);
  wp.xyz += uGrav * h * h * uLen;                        // gravidade / inércia (mundo)
  vPw = wp.xyz; vP0 = position; vH = h; vNo = n;
  vNw = normalize(mat3(modelMatrix) * n);
  vTw = normalize(mat3(modelMatrix) * (n + pt * uDobra * 2. * h) + uGrav * 2. * h);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;
const PELO_FRAG = `
uniform vec3 uCor, uCorVentre, uVentreEixo, uPontas, uKeyDir, uKeyCor, uRimDir, uRimCor, uCeu, uChao;
uniform float uVentreLim, uVentreSuave, uDens, uAO, uVeludo, uBrilho, uVar, uManchas, uRedem, uSemente, uFio, uNap, uTufo, uTufoFreq;
uniform mat3 uRot, uRot2;
varying vec3 vP0, vNw, vPw, vTw, vNo; varying float vH;
float h31(vec3 p){ p = fract(p * .1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
vec3 h33(vec3 p){ p = fract(p * vec3(.1031, .1030, .0973)); p += dot(p, p.yxz + 33.33); return fract((p.xxy + p.yxx) * p.zyx); }
float vn(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(mix(h31(i), h31(i + vec3(1,0,0)), f.x), mix(h31(i + vec3(0,1,0)), h31(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(h31(i + vec3(0,0,1)), h31(i + vec3(1,0,1)), f.x), mix(h31(i + vec3(0,1,1)), h31(i + vec3(1,1,1)), f.x), f.y), f.z); }
float fio(vec3 q, float h, float lm, out float rnd){
  vec3 c = floor(q), f = fract(q);
  vec3 j = h33(c) * .56 + .22; rnd = h31(c + 17.17);
  float L = mix(.45, 1., rnd * rnd * .4 + rnd * .6) * lm;
  if (h > L) return 0.;
  float rad = uFio * (1. - .5 * h / L);
  float d = length(f - j); float aa = max(fwidth(d), 1e-3) * .9;
  return 1. - smoothstep(rad - aa, rad + aa, d);
}
void main(){
  float h = vH; float alpha = 1.; float rnd = .5;
  vec3 p0 = vP0 + uSemente;
  if (h > 0.) {
    float r1, r2;
    float tf = vn(p0 * uTufoFreq) * .7 + vn(p0 * uTufoFreq * 2.3 + 7.) * .3;           // tufos
    float lm = mix(1., mix(.55, 1.12, smoothstep(.25, .75, tf)), uTufo);
    float a1 = fio(uRot * p0 * uDens, h, lm, r1);
    float a2 = fio(uRot2 * p0 * uDens * 1.27 + 5.3, h, lm, r2);
    alpha = max(a1, a2); rnd = a1 > a2 ? r1 : r2;
    if (alpha < .03) discard;
  }
  vec3 base = uCor;
  float vm = smoothstep(uVentreLim - uVentreSuave, uVentreLim + uVentreSuave, dot(vNo, uVentreEixo));
  base = mix(base, uCorVentre, vm);
  float m = vn(vP0 * 7. + uSemente) * .65 + vn(vP0 * 19. - uSemente) * .35;
  base *= 1. + (m - .5) * uManchas;
  base *= 1. + (rnd - .5) * uVar;
  base = mix(base, base * uPontas, h * h);
  float ao = mix(uAO, 1., pow(h, .7));
  vec3 N = normalize(vNw), V = normalize(cameraPosition - vPw), T = normalize(vTw);
  vec3 sw = (vec3(vn(vP0 * 5. + 1.), vn(vP0 * 5. + 9.), vn(vP0 * 5. + 17.)) - .5) * uRedem;
  T = normalize(T + sw);
  vec3 Lk = normalize(uKeyDir);
  float wrap = max(0., (dot(N, Lk) + .4) / 1.4);
  float tl = dot(T, Lk); float kk = sqrt(max(0., 1. - tl * tl));
  float dif = wrap * mix(1., kk, .35);
  vec3 H = normalize(Lk + V); float th = dot(T, H); float spec = pow(sqrt(max(0., 1. - th * th)), 48.) * wrap;
  vec3 amb = mix(uChao, uCeu, N.y * .5 + .5);
  vec3 col = base * (amb + uKeyCor * dif) * ao;
  col += uKeyCor * spec * uBrilho * h * (base * .7 + .12);
  float fres = pow(1. - max(dot(N, V), 0.), 2.5);
  float rl = max(0., dot(N, normalize(uRimDir))) * .6 + .4;
  col += (base * .55 + .45) * uRimCor * fres * uVeludo * (.35 + .65 * h) * rl;
  vec3 tp = T - N * dot(T, N); float lt = length(tp);
  float nap = lt > 1e-3 ? dot(tp / lt, V) : 0.;
  col *= 1. + uNap * nap * h;
  gl_FragColor = vec4(col, alpha);
}`;
const corLin = c => new THREE.Color(c);
/**
 * Material de pelúcia por cascas. o: {cor, ventre:{cor, eixo:[x,y,z], lim, suave}, pontas (multiplica a cor nas pontas, 1.15),
 *  comp (comprimento do pelo em unid., .03), dens (fios por unid., 150), fio (espessura 0–.5, .42), pente:[x,y,z] (direção do penteado),
 *  dobra (quanto o pelo deita, .8), redemoinho (.6), veludo (brilho de borda, .55), brilho (especular, .35), ao (escuro na raiz, .45),
 *  var (variação por fio, .22), manchas (manchas de pelo amassado, .22), nap (claro/escuro conforme a direção, .25), semente, camadas}
 */
export function materialPelo(o = {}) {
  const ve = o.ventre || {};
  const m = new THREE.ShaderMaterial({
    uniforms: {
      uLen: { value: o.comp ?? .03 }, uN: { value: o.camadas ?? 26 }, uDobra: { value: o.dobra ?? .8 },
      uPente: { value: V3(o.pente || [0, -1, .2]).normalize() }, uGrav: { value: V3(o.grav || [0, -.25, 0]) },
      uCor: { value: corLin(o.cor || PAL.bronze) }, uCorVentre: { value: corLin(ve.cor || o.cor || PAL.bronze) }, uVentreEixo: { value: V3(ve.eixo || [0, -1, 0]).normalize() },
      uVentreLim: { value: ve.lim ?? .35 }, uVentreSuave: { value: ve.suave ?? .18 }, uPontas: { value: new THREE.Vector3().setScalar(o.pontas ?? 1.06) },
      uDens: { value: o.dens ?? 150 }, uAO: { value: o.ao ?? .55 }, uVeludo: { value: o.veludo ?? .35 }, uBrilho: { value: o.brilho ?? .35 },
      uVar: { value: o.var ?? .22 }, uManchas: { value: o.manchas ?? .22 }, uRedem: { value: o.redemoinho ?? .6 }, uSemente: { value: (o.semente ?? 1) * 3.17 },
      uFio: { value: o.fio ?? .5 }, uNap: { value: o.nap ?? .25 }, uTufo: { value: o.tufo ?? .8 }, uTufoFreq: { value: o.tufoFreq ?? 22 }, ...LUZ,
    },
    vertexShader: PELO_VERT, fragmentShader: PELO_FRAG,
  });
  m.alphaToCoverage = true;
  return m;
}
/** malha de pelúcia: base opaca + (camadas-1) cascas instanciadas. geo em unidades finais (sem escala na malha) */
export function pelucia(geo, o = {}) {
  if (!geo.attributes.normal) geo.computeVertexNormals();
  const mat = o.material || materialPelo(o); const n = o.camadas ?? 26; mat.uniforms.uN.value = n;
  const g = new THREE.Group();
  const base = new THREE.Mesh(geo, mat); g.add(base);
  const cascas = new THREE.InstancedMesh(geo, mat, n); cascas.userData.semSombra = true; cascas.frustumCulled = false; g.add(cascas);
  g.userData.pelo = mat; g.material = mat; return g;
}

// ───────────────────────── geometrias macias ─────────────────────────
/** perfil [[raio, y], ...] suavizado e girado (corpo, pão, copo...) */
export function torno(perfil, o = {}) {
  const c = new THREE.SplineCurve(perfil.map(p => new THREE.Vector2(p[0], p[1])));
  const pts = c.getPoints(o.pontos ?? 40).map(p => new THREE.Vector2(Math.max(0, p.x), p.y));
  const g = new THREE.LatheGeometry(pts, o.seg ?? 64, o.fi0 ?? 0, o.fi ?? Math.PI * 2); g.computeVertexNormals(); return g;
}
export function esfera(r, esc = [1, 1, 1], o = {}) { const g = new THREE.SphereGeometry(r, o.seg ?? 64, o.anel ?? 40, o.fi0 ?? 0, o.fi ?? Math.PI * 2, o.te0 ?? 0, o.te ?? Math.PI); g.scale(...esc); return g; }
export function capsula(r, comp, o = {}) { return new THREE.CapsuleGeometry(r, comp, 10, o.seg ?? 32, 4); }
export function caixaMacia(w, h, d, raio = .04, seg = 4) { return new RoundedBoxGeometry(w, h, d, seg, raio); }
/** "amassa" a geometria: empurra os vértices pela normal com ruído suave (tecido enchido, copa de boné) */
export function amassar(geo, amp = .01, seed = 1) {
  geo.computeVertexNormals(); const p = geo.attributes.position, n = geo.attributes.normal, f = 9;
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const k = Math.sin(x * f + seed) * Math.sin(y * f * 1.3 + seed * 2.1) * Math.sin(z * f * .9 + seed * .7) + .5 * Math.sin((x + z) * f * 2.1 + seed);
    p.setXYZ(i, x + n.getX(i) * k * amp, y + n.getY(i) * k * amp, z + n.getZ(i) * k * amp); }
  geo.computeVertexNormals(); return geo;
}

// ───────────────────────── feltro, plástico, costura ─────────────────────────
let _bump = null;
/** textura de fibras (bump) do feltro — gerada uma vez, determinística */
export function texturaFeltro() {
  if (_bump) return _bump;
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d'); const r = rng(77);
  g.fillStyle = '#808080'; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i++) {
    const x = r() * 512, y = r() * 512, a = r() * Math.PI * 2, l = 3 + r() * 11, v = Math.floor(90 + r() * 90);
    g.strokeStyle = `rgba(${v},${v},${v},.35)`; g.lineWidth = .6 + r() * .9; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a + .6) * l * .5, y + Math.sin(a + .6) * l * .5, x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
  }
  _bump = new THREE.CanvasTexture(c); _bump.wrapS = _bump.wrapT = THREE.RepeatWrapping; _bump.repeat.set(3, 3); return _bump;
}
const CACHE = new Map();
/** feltro fosco com fibras e brilho de veludo. o: {map (textura de desenho), rep (repetição das fibras), bump, sheen, opac, lados} */
export function feltro(cor, o = {}) {
  const k = cor + JSON.stringify({ ...o, map: o.map ? o.map.uuid : 0 }); if (CACHE.has(k) && !o.unico) return CACHE.get(k);
  const b = texturaFeltro();
  const m = new THREE.MeshPhysicalMaterial({
    color: o.map ? '#ffffff' : cor, map: o.map || null, roughness: o.rug ?? .92, metalness: 0, bumpMap: b, bumpScale: o.bump ?? 1.2,
    sheen: o.sheen ?? .8, sheenRoughness: .55, sheenColor: new THREE.Color(cor).lerp(new THREE.Color('#ffffff'), .45),
    transparent: o.opac !== undefined, opacity: o.opac ?? 1, side: o.lados ? THREE.DoubleSide : THREE.FrontSide, depthWrite: o.opac === undefined,
  });
  if (!o.unico) CACHE.set(k, m); return m;
}
/** plástico brilhante (olho de botão, tampa, canudo) */
export function plastico(cor = '#0d0c0c', o = {}) {
  return new THREE.MeshPhysicalMaterial({ color: cor, roughness: o.rug ?? .18, metalness: 0, clearcoat: 1, clearcoatRoughness: o.verniz ?? .06, envMapIntensity: o.reflexo ?? 1.6 });
}
export function malha(geo, mat, o = {}) { const m = new THREE.Mesh(geo, mat); if (o.pos) m.position.set(...o.pos); if (o.rot) m.rotation.set(...o.rot); if (o.esc) m.scale.set(...(Array.isArray(o.esc) ? o.esc : [o.esc, o.esc, o.esc])); return m; }
/** olho de botão: disco de plástico preto com aro e dois furinhos de linha. Aponta para +z do grupo */
export function botao(r = .055, cor = '#0e0d0d') {
  const g = new THREE.Group();
  g.add(malha(esfera(r, [1, 1, .42], { seg: 32, anel: 20 }), plastico(cor)));
  const aro = new THREE.Mesh(new THREE.TorusGeometry(r * .93, r * .12, 10, 40), plastico(cor, { rug: .3 })); aro.position.z = r * .12; g.add(aro);
  return g;
}
/** costura: pontinhos de linha ao longo de uma curva (Curve3 ou lista de pontos). o: {passo, raio, cor, cheio (0–1 do passo com linha)} */
export function costura(curva, o = {}) {
  if (Array.isArray(curva)) curva = new THREE.CatmullRomCurve3(curva.map(V3));
  const L = curva.getLength(), passo = o.passo ?? .03, n = Math.max(1, Math.round(L / passo)), dl = L / n * (o.cheio ?? .62), r = o.raio ?? .006;
  const geo = new THREE.CapsuleGeometry(r, Math.max(1e-4, dl - 2 * r), 3, 6);
  const im = new THREE.InstancedMesh(geo, new THREE.MeshStandardMaterial({ color: o.cor || PAL.linha, roughness: .75 }), n);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), Y = new THREE.Vector3(0, 1, 0), S1 = new THREE.Vector3(1, 1, 1);
  for (let i = 0; i < n; i++) { const u = (i + .5) / n; Q.setFromUnitVectors(Y, curva.getTangentAt(u)); M.compose(curva.getPointAt(u), Q, S1); im.setMatrixAt(i, M); }
  return im;
}
/** ponto na superfície de um elipsoide (centro c, raio r, escala esc): lat (rad, + p/ cima), lon (rad, 0 = frente +z, + p/ esquerda do boneco = +x) */
export function naSuperficie(c, r, esc, lat, lon) {
  return new THREE.Vector3(c[0] + r * esc[0] * Math.cos(lat) * Math.sin(lon), c[1] + r * esc[1] * Math.sin(lat), c[2] + r * esc[2] * Math.cos(lat) * Math.cos(lon));
}
/** posiciona obj na superfície do elipsoide olhando para fora */
export function colar(obj, c, r, esc, lat, lon, saliencia = 0) {
  const p = naSuperficie(c, r + saliencia, esc, lat, lon); obj.position.copy(p);
  const n = new THREE.Vector3((p.x - c[0]) / (esc[0] ** 2), (p.y - c[1]) / (esc[1] ** 2), (p.z - c[2]) / (esc[2] ** 2)).normalize();
  obj.lookAt(p.clone().add(n)); return obj;
}

// ───────────────────────── etiquetas de feltro (texto/marca desenhados em canvas) ─────────────────────────
/** textura de canvas com fundo de feltro: desenhar(g, w, h). Devolve CanvasTexture sRGB */
export function etiqueta(desenhar, w = 512, h = 256, fundo = '#ffffff') {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d');
  g.fillStyle = fundo; g.fillRect(0, 0, w, h); desenhar(g, w, h);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; tx.anisotropy = 8; return tx;
}
/** marca fictícia: chama + nome em arco (ex.: "BRASA BURGER"). o: {fundo, cor, acento, nome, sub} */
export function logoMarca(o = {}) {
  const nome = o.nome || 'BRASA', sub = o.sub || 'BURGER';
  return etiqueta((g, w, h) => {
    g.fillStyle = o.fundo || PAL.creme; g.beginPath(); g.arc(w / 2, h / 2, w * .47, 0, 7); g.fill();
    g.strokeStyle = o.acento || PAL.porDoSol; g.lineWidth = w * .035; g.beginPath(); g.arc(w / 2, h / 2, w * .41, 0, 7); g.stroke();
    // chama
    g.fillStyle = o.acento || PAL.porDoSol; g.beginPath(); const cx = w / 2, cy = h * .4, s = w * .15;
    g.moveTo(cx, cy - s * 1.3); g.bezierCurveTo(cx + s * 1.1, cy - s * .2, cx + s * .9, cy + s, cx, cy + s); g.bezierCurveTo(cx - s * .9, cy + s, cx - s * 1.1, cy - s * .1, cx - s * .2, cy - s * .7);
    g.bezierCurveTo(cx - s * .1, cy - s * .2, cx + s * .1, cy, cx, cy - s * 1.3); g.fill();
    g.fillStyle = o.cor || PAL.tinta; g.textAlign = 'center'; g.font = `900 ${w * .15}px Geist, sans-serif`; g.fillText(nome, w / 2, h * .74);
    g.font = `700 ${w * .075}px Geist, sans-serif`; g.fillText(sub.split('').join(' '), w / 2, h * .85);
  }, 512, 512, o.fundo || PAL.creme);
}
/** remendo redondo de feltro com a marca (para boné, sacola, copo...) */
export function remendo(r = .08, o = {}) {
  const g = new THREE.Group();
  const tx = o.tex || logoMarca(o);
  const disco = new THREE.Mesh(new THREE.CylinderGeometry(r, r, .008, 40), feltro(o.fundo || PAL.creme)); disco.rotation.x = Math.PI / 2; g.add(disco);
  const face = new THREE.Mesh(new THREE.CircleGeometry(r * .985, 40), feltro('#fff', { map: tx, bump: .5 })); face.position.z = .0042; g.add(face);
  const borda = costura(new THREE.EllipseCurve(0, 0, r * .86, r * .86).getPoints(40).map(p => [p.x, p.y, .006]), { passo: r * .18, raio: r * .03, cor: o.linha || PAL.porDoSol });
  g.add(borda); return g;
}

// ───────────────────────── sombra enorme e desfocada no chão ─────────────────────────
const BLUR_FRAG = `uniform sampler2D t; uniform vec2 dir; varying vec2 vUv;
void main(){ float w[5]; w[0]=.227; w[1]=.194; w[2]=.121; w[3]=.054; w[4]=.016;
  float s = texture2D(t, vUv).r * w[0];
  for (int i = 1; i < 5; i++) { s += texture2D(t, vUv + dir * float(i)).r * w[i]; s += texture2D(t, vUv - dir * float(i)).r * w[i]; }
  gl_FragColor = vec4(s, s, s, 1.); }`;
/**
 * Sombra de estúdio: silhueta de tudo que flutua, projetada pela luz no chão e MUITO desfocada.
 * o: {y (altura do chão), dir:[x,y,z] (de onde vem a luz), centro:[x,z], tam (área coberta), res, desfoque (px de textura), passes, cor, opac}
 */
export function sombraChao(S, o = {}) {
  const res = o.res ?? 256, tam = o.tam ?? 9, y = o.y ?? -1.6, R = S.renderer;
  const dir = V3(o.dir || [.5, 1, -.12]).normalize(), c = V3([o.centro?.[0] ?? 0, y, o.centro?.[1] ?? 0]);
  const cam = new THREE.OrthographicCamera(-tam / 2, tam / 2, tam / 2, -tam / 2, .1, 80);
  cam.position.copy(c).addScaledVector(dir, 30); cam.up.set(0, 0, -1); cam.lookAt(c); cam.layers.set(1); cam.updateMatrixWorld();
  const mk = () => new THREE.WebGLRenderTarget(res, res, { type: THREE.HalfFloatType });
  const A = mk(), B = mk();
  const branco = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const blur = new THREE.ShaderMaterial({ uniforms: { t: { value: null }, dir: { value: new THREE.Vector2() } }, vertexShader: QUAD_VERT, fragmentShader: BLUR_FRAG, depthTest: false, depthWrite: false });
  const quad = new FullScreenQuad(blur);
  const uM = new THREE.Matrix4();
  const mat = new THREE.ShaderMaterial({
    uniforms: { tS: { value: A.texture }, uM: { value: uM }, uCor: { value: new THREE.Color(o.cor || PAL.sombra) }, uOpac: { value: o.opac ?? .5 } },
    vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform sampler2D tS; uniform mat4 uM; uniform vec3 uCor; uniform float uOpac; varying vec3 vW;
      void main(){ vec4 c = uM * vec4(vW, 1.); vec2 uv = c.xy / c.w * .5 + .5;
        float e = smoothstep(0., .1, uv.x) * smoothstep(1., .9, uv.x) * smoothstep(0., .1, uv.y) * smoothstep(1., .9, uv.y);
        float s = texture2D(tS, uv).r; gl_FragColor = vec4(uCor, clamp(s, 0., 1.) * uOpac * e); }`,
    transparent: true, depthWrite: false,
  });
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), mat); chao.rotation.x = -Math.PI / 2; chao.position.y = y; chao.userData.semSombra = true; chao.renderOrder = -1;
  S.scene.add(chao);
  const cc = new THREE.Color(); const passos = o.passes ?? 3, des = o.desfoque ?? 2.2;
  const sombra = { chao, cam, mat, opac: mat.uniforms.uOpac };
  S.antes.push(() => {
    S.scene.traverse(m => { if (m.isMesh && !m.userData.semSombra && m !== chao) m.layers.enable(1); });
    const bg = S.scene.background, env = S.scene.environment, ca = R.getClearAlpha(); R.getClearColor(cc);
    S.scene.background = null; S.scene.overrideMaterial = branco;
    R.setRenderTarget(A); R.setClearColor(0x000000, 1); R.clear(); R.render(S.scene, cam);
    S.scene.overrideMaterial = null; S.scene.background = bg; S.scene.environment = env;
    for (let i = 0; i < passos; i++) {
      const k = des * (1 + i * 1.2) / res;
      blur.uniforms.t.value = A.texture; blur.uniforms.dir.value.set(k, 0); R.setRenderTarget(B); quad.render(R);
      blur.uniforms.t.value = B.texture; blur.uniforms.dir.value.set(0, k); R.setRenderTarget(A); quad.render(R);
    }
    R.setRenderTarget(null); R.setClearColor(cc, ca);
    uM.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);
  });
  return sombra;
}

// ───────────────────────── boneco de pelúcia paramétrico ─────────────────────────
/**
 * Boneco de pelúcia (corpo de feijão enchido, cabeção, braços e pernas curtos, olhos de botão, sorriso costurado).
 * o: {pele, cabelo, cabeloTipo:'curto'|'coque'|'black'|'nenhum', camisa, calca, sapato, avental (cor|null), chapeu:'bone'|'viseira'|null,
 *     corChapeu, cracha:'NOME'|null, bigode (cor|null), boca:'costura'|'aberta', bochechas (bool), pelo:{comp, dens}, semente}
 * Devolve B = {raiz, corpo, cabeca, bracoE, bracoD, maoE, maoD, pernaE, pernaD, balancar(t, o), bracos({e:[x,y,z], d:[x,y,z]})}
 * (E = esquerda DO BONECO = +x local; o boneco olha para +z)
 */
export function boneco(o = {}) {
  const sem = o.semente ?? 1, pel = o.pelo || {}, comp = pel.comp ?? .036, dens = pel.dens ?? 105;
  const P = (cor, extra = {}) => ({ cor, comp, dens, semente: sem + (extra.s ?? 0), ...extra });
  const raiz = new THREE.Group(), corpo = new THREE.Group(); raiz.add(corpo);
  // tronco: feijão enchido
  const tronco = pelucia(torno([[0, -.33], [.24, -.315], [.37, -.2], [.4, -.02], [.38, .16], [.31, .32], [.17, .42], [0, .45]]), P(o.camisa || PAL.porDoSol, { pente: [0, -1, .1], s: 1 }));
  corpo.add(tronco);
  // pernas curtinhas + sapatos de feltro
  const perna = lado => {
    const g = new THREE.Group(); g.position.set(lado * .16, -.27, 0);
    const pz = pelucia(capsula(.12, .12), P(o.calca || PAL.carvao, { s: 2 + lado })); pz.position.y = -.12; g.add(pz);
    g.add(malha(esfera(.13, [1, .62, 1.3], { seg: 32, anel: 20 }), feltro(o.sapato || '#2b2725'), { pos: [0, -.27, .05] }));
    corpo.add(g); return g;
  };
  const pernaE = perna(1), pernaD = perna(-1);
  // braços: manga de pelo + mão (luva) de pelo na cor da pele
  const braco = lado => {
    const g = new THREE.Group(); g.position.set(lado * .34, .25, 0);
    const manga = pelucia(capsula(.115, .14), P(o.camisa || PAL.porDoSol, { pente: [0, -1, 0], s: 4 + lado })); manga.position.y = -.12; g.add(manga);
    const mao = new THREE.Group(); mao.position.y = -.31; g.add(mao);
    mao.add(pelucia(esfera(.1, [1, .95, .9], { seg: 40, anel: 28 }), P(o.pele || PAL.pele[2], { comp: comp * .8, s: 6 + lado, pente: [0, -1, 0], tufo: .5 })));
    corpo.add(g); g.userData.mao = mao; return g;
  };
  const bracoE = braco(1), bracoD = braco(-1);
  // cabeça
  const cabeca = new THREE.Group(); cabeca.position.y = .8; corpo.add(cabeca);
  const RC = .39, EC = [1, .93, .96];
  cabeca.add(pelucia(esfera(RC, EC), P(o.pele || PAL.pele[2], { comp: comp * .85, pente: [0, -1, .35], s: 9, dobra: .75, tufo: .55 })));
  for (const l of [1, -1]) { const or = pelucia(esfera(.085, [.6, 1, .9], { seg: 32, anel: 20 }), P(o.pele || PAL.pele[2], { comp: comp * .75, s: 10 + l })); colar(or, [0, 0, 0], RC, EC, .02, l * Math.PI / 2, -.02); cabeca.add(or); }
  // rosto: olhos de botão, nariz de feltro, bochechas, boca
  const olhos = [];
  for (const l of [1, -1]) {
    const b = botao(.05); colar(b, [0, 0, 0], RC, EC, -.02, l * .34, comp * .62); cabeca.add(b); olhos.push(b);
    if (o.aroOlho !== false) { const a = malha(new THREE.CircleGeometry(.068, 32), feltro(o.aroOlho || '#f6f1e8')); colar(a, [0, 0, 0], RC, EC, -.02, l * .34, comp * .5); cabeca.add(a); }
  }
  const nariz = malha(esfera(.04, [1.2, .85, .8], { seg: 24, anel: 16 }), feltro(new THREE.Color(o.pele || PAL.pele[2]).multiplyScalar(.82).getStyle()));
  colar(nariz, [0, 0, 0], RC, EC, -.17, 0, comp * .5); cabeca.add(nariz);
  if (o.bochechas !== false) for (const l of [1, -1]) { const b = malha(new THREE.CircleGeometry(.055, 28), feltro(PAL.rosa, { opac: .75 })); colar(b, [0, 0, 0], RC, EC, -.2, l * .55, comp * .9); cabeca.add(b); }
  if (o.boca === 'aberta') {
    const sh = new THREE.Shape(); sh.absarc(0, 0, .07, Math.PI, 2 * Math.PI, false); sh.lineTo(-.07, 0);
    const bc = malha(new THREE.ExtrudeGeometry(sh, { depth: .01, bevelEnabled: true, bevelThickness: .004, bevelSize: .004, bevelSegments: 2 }), feltro(PAL.boca));
    colar(bc, [0, 0, 0], RC, EC, -.3, 0, comp * .45); cabeca.add(bc);
  } else {
    const pts = []; for (let i = 0; i <= 12; i++) { const u = i / 12; pts.push(naSuperficie([0, 0, 0], RC + comp * .55, EC, -.31 - .07 * Math.sin(Math.PI * u), (u - .5) * .5)); }
    cabeca.add(costura(pts, { passo: .022, raio: .0065 }));
  }
  if (o.bigode) { const bg = pelucia(esfera(.075, [1.5, .45, .6], { seg: 32, anel: 16 }), P(o.bigode, { comp: comp * .9, s: 12, pente: [0, -1, 0] })); colar(bg, [0, 0, 0], RC, EC, -.24, 0, comp * .2); cabeca.add(bg); }
  // cabelo
  const cab = o.cabelo || PAL.cabelo[0], tipo = o.cabeloTipo || 'curto';
  if (tipo !== 'nenhum') {
    const capa = pelucia(esfera(RC + .012, [EC[0] * 1.02, EC[1], EC[2] * 1.02], { te: Math.PI * (tipo === 'black' ? .62 : .5) }), P(cab, { comp: comp * (tipo === 'black' ? 2.2 : 1.1), s: 13, pente: [0, -.4, -1], manchas: .3 }));
    capa.rotation.x = -.42; cabeca.add(capa);
    if (tipo === 'coque') { const cq = pelucia(esfera(.15, [1, .9, 1], { seg: 40, anel: 28 }), P(cab, { comp: comp * 1.1, s: 14 })); cq.position.set(0, .2, -.34); cabeca.add(cq); }
    if (tipo === 'black') { const bl = pelucia(esfera(RC * 1.18, [1, .9, 1], { te: Math.PI * .58 }), P(cab, { comp: comp * 2.4, s: 15, dobra: .2, redemoinho: 1.4 })); bl.rotation.x = -.5; bl.position.y = .04; cabeca.add(bl); }
  }
  // chapéu
  const corCh = o.corChapeu || PAL.laguna;
  if (o.chapeu === 'bone' || o.chapeu === 'viseira') {
    const ch = new THREE.Group(); ch.rotation.x = -.18; cabeca.add(ch);
    if (o.chapeu === 'bone') {
      const EB = [1.05, .98, 1.07], RB = RC + comp * .95 + .012, CB = .013;
      ch.add(pelucia(amassar(esfera(RB, EB, { te: Math.PI * .5 }), .012, 7 + sem), P(corCh, { comp: CB, dens: 210, s: 16, pente: [0, -1, 0], dobra: .5, tufo: .3, manchas: .32, veludo: .25 })));
      ch.add(pelucia(esfera(.03, [1, .6, 1], { seg: 16, anel: 10 }), P(corCh, { comp: .008, dens: 260, s: 17 })).translateY(RB * EB[1] + .004));
      for (const lon of [0, Math.PI * .5, -Math.PI * .5, Math.PI * .25, -Math.PI * .25]) ch.add(costura(Array.from({ length: 13 }, (_, i) => naSuperficie([0, 0, 0], RB + CB * .8, EB, Math.PI / 2 * (.05 + .9 * i / 12), lon)), { passo: .028, raio: .0065, cor: new THREE.Color(corCh).multiplyScalar(.62).getStyle() }));
      const rm = remendo(.08, { acento: o.corMarca || PAL.porDoSol, linha: o.corMarca || PAL.porDoSol }); colar(rm, [0, 0, 0], RB + CB * .7, EB, .42, 0, .004); ch.add(rm);
    } else {
      const fx = pelucia(amassar(torno([[RC * .96 + comp, .065], [RC * .99 + comp + .012, .12], [RC * 1.0 + comp, .175]], { seg: 72 }), .006, 5 + sem), P(corCh, { comp: .012, dens: 210, s: 18, pente: [0, -1, 0], dobra: .4, tufo: .3, veludo: .25 }));
      ch.add(fx);
      for (const y of [.078, .162]) ch.add(costura(new THREE.EllipseCurve(0, 0, RC * .98 + comp + .024, RC * .98 + comp + .024).getPoints(60).map(p => [p.x, y, p.y]), { passo: .028, raio: .0055, cor: new THREE.Color(corCh).multiplyScalar(.62).getStyle() }));
      const rm = remendo(.045, { acento: o.corMarca || PAL.porDoSol, linha: o.corMarca || PAL.porDoSol }); rm.position.set(0, .12, RC * 1.0 + comp + .03); ch.add(rm);
    }
    // aba: meia-lente macia de pelo curto (cantos redondos) com duas linhas de costura em relevo
    const aba = pelucia(esfera(.3, [1, .075, .82], { fi0: 0, fi: Math.PI, seg: 64, anel: 32 }), P(corCh, { comp: .01, dens: 230, s: 19, pente: [0, 0, 1], dobra: .5, tufo: .25, veludo: .25 }));
    aba.rotation.x = .12; aba.position.set(0, o.chapeu === 'bone' ? .095 : .08, RC * .74); ch.add(aba);
    for (const rr of [.9, .74]) ch.add(costura(Array.from({ length: 25 }, (_, i) => { const a = Math.PI * (.08 + .84 * i / 24);
      return new THREE.Vector3(.3 * rr * Math.cos(a), .3 * .075 * Math.sqrt(1 - rr * rr) + .011, .246 * rr * Math.sin(a)).applyEuler(aba.rotation).add(aba.position); }),
      { passo: .025, raio: .006, cor: new THREE.Color(corCh).multiplyScalar(.62).getStyle() }));
  }
  // avental de feltro com bolso costurado
  if (o.avental) {
    const av = malha(torno([[.375, -.3], [.405, -.02], [.385, .16], [.33, .3]], { fi0: -.95, fi: 1.9, seg: 32 }), feltro(o.avental, { lados: true }));
    const ka = 1 + comp * 3; av.geometry.scale(ka, 1, ka); corpo.add(av);
    const rr = y => (.405 - .55 * (y + .02) ** 2) * ka + .006, bolso = [];
    for (let i = 0; i <= 4; i++) { const y = -.07 - .13 * i / 4; bolso.push([Math.sin(-.26) * rr(y), y, Math.cos(-.26) * rr(y)]); }
    for (let i = 1; i <= 8; i++) { const a = -.26 + .52 * i / 8; bolso.push([Math.sin(a) * rr(-.2), -.2, Math.cos(a) * rr(-.2)]); }
    for (let i = 1; i <= 4; i++) { const y = -.2 + .13 * i / 4; bolso.push([Math.sin(.26) * rr(y), y, Math.cos(.26) * rr(y)]); }
    corpo.add(costura(bolso, { passo: .028, raio: .006, cor: PAL.creme }));
  }
  // crachá
  if (o.cracha) {
    const tx = etiqueta((g, w, h) => {
      g.fillStyle = o.corMarca || PAL.porDoSol; g.fillRect(0, 0, w, h * .28); g.fillStyle = '#fff'; g.font = `800 ${h * .17}px Geist, sans-serif`; g.textAlign = 'center'; g.fillText('BRASA BURGER', w / 2, h * .2);
      g.fillStyle = PAL.tinta; g.font = `800 ${h * .44}px Geist, sans-serif`; g.fillText(o.cracha, w / 2, h * .8);
    }, 512, 256, '#f7f3ea');
    const cr = malha(caixaMacia(.17, .085, .014, .006, 2), [feltro('#f7f3ea'), feltro('#f7f3ea'), feltro('#f7f3ea'), feltro('#f7f3ea'), feltro('#fff', { map: tx, bump: .4 }), feltro('#f7f3ea')]);
    const lado = o.crachaLado ?? 1; colar(cr, [0, .17, 0], o.avental ? .44 : .395 + comp * 1.1, [1, 1, 1], 0, lado * .4, 0); corpo.add(cr);
  }
  const B = {
    raiz, corpo, cabeca, bracoE, bracoD, maoE: bracoE.userData.mao, maoD: bracoD.userData.mao, pernaE, pernaD, olhos,
    /** balanço macio de pelúcia: flutua, gira de leve, enche/esvazia, cabeça e pernas atrasadas. o: {periodo, desloc, amp} */
    balancar(t, q = {}) {
      const per = q.periodo ?? 2.5, d = q.desloc ?? 0, a = q.amp ?? 1;
      corpo.position.y = .05 * a * onda(t, per, d);
      corpo.rotation.z = .045 * a * onda(t, per * 2, d + .1); corpo.rotation.x = .03 * a * onda(t, per, d + .3);
      const s = .022 * a * onda(t, per / 2, d + .15); corpo.scale.set(1 + s, 1 - s, 1 + s);
      cabeca.rotation.z = .06 * a * onda(t, per * 2, d - .05); cabeca.rotation.x = .04 * a * onda(t, per, d + .05);
      pernaE.rotation.x = .22 * a * onda(t, per, d + .2); pernaD.rotation.x = -.22 * a * onda(t, per, d + .35);
    },
    /** braços: rotação [x,y,z] de cada ombro (x<0 levanta para a frente; z>0 abre o braço esquerdo, z<0 abre o direito) */
    bracos(q) { if (q.e) bracoE.rotation.set(...q.e); if (q.d) bracoD.rotation.set(...q.d); },
  };
  return B;
}

// ───────────────────────── comidas de pelúcia e feltro ─────────────────────────
/** hambúrguer de pelúcia: pão de pelo (ventre mais claro) com gergelim de feltro, carne de pelo, queijo, alface e tomate de feltro */
export function hamburguer(o = {}) {
  const r = o.raio ?? .13, g = new THREE.Group(), sem = o.semente ?? 30;
  const pao = o.pao || '#c98a45', pc = { comp: .012, dens: 260, fio: .4, semente: sem, pente: [0, 1, 0], dobra: .3, ventre: { cor: '#efd3a0', eixo: [0, -1, 0], lim: -.1, suave: .25 } };
  g.add(pelucia(torno([[0, 0], [r * .92, .005], [r, r * .2], [r * .9, r * .36], [0, r * .4]], { seg: 48 }), { cor: pao, ...pc }));
  const carne = pelucia(torno([[0, 0], [r * 1.02, .0], [r * 1.07, r * .17], [r * 1.0, r * .33], [0, r * .33]], { seg: 48 }), { cor: '#5a3524', comp: .014, dens: 240, semente: sem + 1, manchas: .4 });
  carne.position.y = r * .38; g.add(carne);
  // queijo com cantos caídos
  const q = caixaMacia(r * 1.75, .012, r * 1.75, .006, 2); const pq = q.attributes.position;
  for (let i = 0; i < pq.count; i++) { const x = pq.getX(i), z = pq.getZ(i); const d = Math.max(Math.abs(x), Math.abs(z)) / (r * .87); pq.setY(i, pq.getY(i) - Math.max(0, d - .55) ** 2 * r * .9); }
  q.computeVertexNormals(); const queijo = malha(q, feltro('#f1b53a')); queijo.position.y = r * .74; queijo.rotation.y = .4; g.add(queijo);
  // alface ondulada
  const al = new THREE.CylinderGeometry(r * 1.12, r * 1.12, .014, 64, 1); const pa = al.attributes.position;
  for (let i = 0; i < pa.count; i++) { const x = pa.getX(i), z = pa.getZ(i), a = Math.atan2(z, x), d = Math.hypot(x, z) / (r * 1.12); pa.setY(i, pa.getY(i) + Math.sin(a * 9) * .014 * d * d); }
  al.computeVertexNormals(); g.add(malha(al, feltro('#79ad4c'), { pos: [0, r * .8, 0] }));
  g.add(malha(new THREE.CylinderGeometry(r * .8, r * .8, .02, 40), feltro('#d8462e'), { pos: [0, r * .87, 0] }));
  const topo = pelucia(torno([[0, 0], [r * 1.0, 0], [r * 1.06, r * .25], [r * .85, r * .62], [r * .45, r * .82], [0, r * .86]], { seg: 56 }), { cor: pao, ...pc, semente: sem + 2 });
  topo.position.y = r * .92; g.add(topo);
  // gergelim
  const R = rng(sem), gs = new THREE.InstancedMesh(esfera(.011, [1, .55, .6], { seg: 10, anel: 6 }), feltro('#f6ead0'), 14), M = new THREE.Matrix4();
  for (let i = 0; i < 14; i++) { const a = R() * 6.28, rr = Math.sqrt(R()) * r * .7, y = r * .92 + r * .86 * Math.sqrt(Math.max(0, 1 - (rr / (r * 1.02)) ** 2)) + .012; const ob = new THREE.Object3D(); ob.position.set(Math.cos(a) * rr, y, Math.sin(a) * rr); ob.rotation.set(R() * .5, R() * 6, 0); ob.updateMatrix(); gs.setMatrixAt(i, ob.matrix); }
  g.add(gs); return g;
}
/** hambúrguer cru/na chapa: só o disco de carne (de pelúcia) */
export function carne(o = {}) { const r = o.raio ?? .12; return pelucia(torno([[0, 0], [r * 1.0, 0], [r * 1.06, r * .17], [r * .98, r * .32], [0, r * .33]], { seg: 48 }), { cor: o.cor || '#5a3524', comp: .014, dens: 240, semente: o.semente ?? 40, manchas: .4 }); }
/** batata frita: caixinha de feltro com a marca + palitos de feltro */
export function batata(o = {}) {
  const g = new THREE.Group(), cor = o.cor || PAL.porDoSol;
  const cx = caixaMacia(.15, .16, .08, .02, 3); const p = cx.attributes.position;
  for (let i = 0; i < p.count; i++) { const k = 1 + (p.getY(i) / .16) * .5; p.setX(i, p.getX(i) * k); }
  cx.computeVertexNormals();
  const tx = etiqueta((c, w, h) => { c.fillStyle = cor; c.fillRect(0, 0, w, h); c.fillStyle = '#fff'; c.font = `900 ${h * .3}px Geist, sans-serif`; c.textAlign = 'center'; c.fillText('BRASA', w / 2, h * .62); }, 256, 256, cor);
  const caixa = malha(cx, [feltro(cor), feltro(cor), feltro(cor), feltro(cor), feltro('#fff', { map: tx }), feltro(cor)]); caixa.position.y = .08; g.add(caixa);
  const R = rng(o.semente ?? 50), pal = caixaMacia(.022, .17, .022, .008, 2), mt = feltro('#f3c64f');
  for (let i = 0; i < 11; i++) { const m = malha(pal, mt); m.position.set((R() - .5) * .15, .17 + R() * .04, (R() - .5) * .05); m.rotation.set((R() - .5) * .4, R() * 3, (R() - .5) * .5); g.add(m); }
  return g;
}
/** copo de refri de feltro com tampa e canudo. o: {cor, faixa, texto} */
export function refri(o = {}) {
  const g = new THREE.Group(), cor = o.cor || PAL.creme, fx = o.faixa || PAL.porDoSol;
  const tx = etiqueta((c, w, h) => { c.fillStyle = cor; c.fillRect(0, 0, w, h); c.fillStyle = fx; c.fillRect(0, h * .3, w, h * .4); c.fillStyle = '#fff'; c.font = `900 ${h * .2}px Geist, sans-serif`; c.textAlign = 'center'; for (const x of [.25, .75]) c.fillText(o.texto || 'GUARANÁ', w * x, h * .57); }, 1024, 256, cor);
  tx.wrapS = THREE.RepeatWrapping;
  const copo = malha(new THREE.CylinderGeometry(.075, .058, .2, 48, 1, false), [feltro('#fff', { map: tx }), feltro(cor), feltro(cor)]); copo.position.y = .1; g.add(copo);
  g.add(malha(esfera(.08, [1, .25, 1], { te: Math.PI / 2, seg: 40, anel: 12 }), feltro('#f4f1ea'), { pos: [0, .2, 0] }));
  const can = malha(new THREE.CylinderGeometry(.009, .009, .16, 12), plastico(o.canudo || PAL.laguna, { rug: .35 })); can.position.set(.02, .27, 0); can.rotation.z = -.2; g.add(can);
  return g;
}
/** bandeja de feltro com papel forrado e o pedido montado (hambúrguer, batata, refri) */
export function bandeja(o = {}) {
  const g = new THREE.Group(), cor = o.cor || PAL.laguna;
  g.add(malha(caixaMacia(.62, .035, .42, .016, 3), feltro(cor)));
  const papel = etiqueta((c, w, h) => { c.fillStyle = '#f3ecdf'; c.fillRect(0, 0, w, h); c.fillStyle = 'rgba(224,96,58,.55)'; c.font = `800 ${h * .07}px Geist, sans-serif`;
    for (let y = 0; y < 8; y++) for (let x = 0; x < 4; x++) c.fillText(((x + y) % 2 ? 'BRASA' : 'BURGER'), x * w * .28 + (y % 2) * 30 - 20, y * h * .14 + 30); }, 512, 384, '#f3ecdf');
  g.add(malha(new THREE.PlaneGeometry(.5, .33), feltro('#fff', { map: papel, bump: .5 }), { pos: [0, .019, 0], rot: [-Math.PI / 2, 0, .12] }));
  const borda = costura(new THREE.EllipseCurve(0, 0, .29, .19).getPoints(40).map(p => [p.x, .019, p.y]), { passo: .03, raio: .005, cor: PAL.creme });
  g.add(borda);
  const h = hamburguer({ semente: o.semente ?? 31 }); h.position.set(-.1, .02, .02); h.rotation.y = .5; g.add(h);
  const b = batata({ semente: (o.semente ?? 31) + 3 }); b.position.set(.13, .02, -.08); b.rotation.y = -.25; g.add(b);
  const r = refri(); r.position.set(.17, .02, .1); g.add(r);
  g.userData.itens = { hamburguer: h, batata: b, refri: r }; return g;
}
/** sacola de entrega de feltro (kraft) aberta em cima, com a marca e alças. altura ~.5 */
export function sacola(o = {}) {
  const g = new THREE.Group(), cor = o.cor || PAL.kraft, w = o.larg ?? .5, h = o.alt ?? .48, d = o.prof ?? .3, e = .02;
  const m = feltro(cor);
  g.add(malha(caixaMacia(w, e, d, .008, 2), m, { pos: [0, -h / 2, 0] }));
  g.add(malha(caixaMacia(w, h, e, .008, 2), m, { pos: [0, 0, -d / 2] }));
  g.add(malha(caixaMacia(e, h, d, .008, 2), m, { pos: [-w / 2, 0, 0] }), malha(caixaMacia(e, h, d, .008, 2), m, { pos: [w / 2, 0, 0] }));
  g.add(malha(caixaMacia(w, h, e, .008, 2), m, { pos: [0, 0, d / 2] }));
  const lg = remendo(.12, { acento: PAL.porDoSol, linha: PAL.porDoSol }); lg.position.set(0, .02, d / 2 + .016); g.add(lg);
  for (const z of [-1, 1]) g.add(malha(caixaMacia(w + .01, .05, .012, .006, 2), feltro(PAL.laguna), { pos: [0, h / 2 - .06, z * (d / 2 + .008)] }));
  for (const z of [-1, 1]) { const al = new THREE.Mesh(new THREE.TorusGeometry(.11, .014, 8, 32, Math.PI), feltro(PAL.porDoSol)); al.position.set(0, h / 2, z * d * .5); g.add(al); }
  g.add(costura([[-w / 2 + .03, h / 2 - .02, d / 2 + .012], [w / 2 - .03, h / 2 - .02, d / 2 + .012]], { passo: .03, raio: .005, cor: PAL.creme }));
  g.userData.boca = new THREE.Vector3(0, h / 2, 0); return g;
}
/** chapa de lanchonete de feltro (corpo laranja, tampo "inox", botões) */
export function chapa(o = {}) {
  const g = new THREE.Group(), w = o.larg ?? .7, d = o.prof ?? .42;
  g.add(malha(caixaMacia(w, .16, d, .035, 3), feltro(o.cor || PAL.carvao), { pos: [0, -.08, 0] }));
  g.add(malha(caixaMacia(w * .94, .03, d * .9, .012, 2), feltro(PAL.inox, { sheen: .3, rug: .7 }), { pos: [0, .012, 0] }));
  const fr = malha(caixaMacia(w * .9, .08, .02, .01, 2), feltro(PAL.porDoSol), { pos: [0, -.08, d / 2] }); g.add(fr);
  for (const x of [-.2, 0, .2]) g.add(malha(new THREE.CylinderGeometry(.022, .022, .03, 20), plastico('#1b1a19'), { pos: [x * w / .7, -.08, d / 2 + .02], rot: [Math.PI / 2, 0, 0] }));
  g.add(costura([[-w * .45, .03, d * .45], [w * .45, .03, d * .45], [w * .45, .03, -d * .45], [-w * .45, .03, -d * .45], [-w * .45, .03, d * .45]], { passo: .03, raio: .005, cor: '#d8d4cc' }));
  return g;
}
/** espátula de feltro: cabo de madeira + lâmina inox. Cresce para +z a partir da mão */
export function espatula() {
  const g = new THREE.Group();
  g.add(malha(new THREE.CylinderGeometry(.018, .02, .2, 16), feltro('#7b5232'), { pos: [0, 0, .1], rot: [Math.PI / 2, 0, 0] }));
  g.add(malha(caixaMacia(.12, .012, .14, .01, 2), feltro(PAL.inox, { sheen: .3 }), { pos: [0, -.02, .26], rot: [.25, 0, 0] }));
  return g;
}
/** fumacinhas de feltro que sobem e somem (loop): devolve {grupo, update(t)} */
export function fumaca(o = {}) {
  const g = new THREE.Group(), n = o.n ?? 3, per = o.periodo ?? 1.25, alt = o.alt ?? .5, R = rng(o.semente ?? 9);
  const it = Array.from({ length: n }, (_, i) => { const m = malha(esfera(.045, [1, .8, 1], { seg: 20, anel: 12 }), feltro('#fbf8f2', { opac: .5, unico: true, sheen: 1 })); m.userData.semSombra = true; g.add(m); return { m, d: i / n, x: (R() - .5) * .2, z: (R() - .5) * .1 }; });
  return { grupo: g, update(t) { for (const q of it) { const k = ((t / per + q.d) % 1 + 1) % 1; q.m.position.set(q.x + .05 * Math.sin(k * 6 + q.d * 9), k * alt, q.z); q.m.scale.setScalar(.4 + k * 1.4); q.m.material.opacity = .3 * Math.sin(Math.PI * k) ** 1.5; } } };
}

// ───────────────────────── HUD editorial (HTML sobre o 3D) ─────────────────────────
const CSS = `
.pl-hud{position:absolute;inset:0;pointer-events:none;z-index:5;color:${PAL.tinta};font-family:'Geist',sans-serif}
.pl-rot{position:absolute;left:58px;top:112px;font:500 21px/1 'Geist',sans-serif;letter-spacing:.2em;color:#6f6a62;text-transform:uppercase;white-space:nowrap}
.pl-tit{position:absolute;left:50px;top:150px;font:400 172px/.96 'Lora',serif;font-style:italic;letter-spacing:-.025em;color:${PAL.tinta};white-space:nowrap}
.pl-tit .l2{display:block;padding-left:96px}
.pl-txt{position:absolute;left:58px;top:520px;font:400 30px/1.32 'Lora',serif;font-style:italic;color:#4a463f;white-space:nowrap}
.pl-selo{position:absolute;right:50px;top:100px;border:1.5px solid #c9c3ba;border-radius:5px;padding:9px 14px 8px;font:600 16px/1 'JetBrains Mono',monospace;letter-spacing:.14em;color:#55514b;text-transform:uppercase;display:flex;gap:10px;align-items:center}
.pl-selo i{width:9px;height:9px;border-radius:50%;background:#3d9a63;display:inline-block}
.pl-pn{position:absolute;right:40px;width:340px;background:rgba(236,233,228,.86);border:1.5px solid #d3cec6;border-radius:6px;padding:20px 20px 18px;box-shadow:0 2px 0 rgba(0,0,0,.02)}
.pl-pn .hd{display:flex;justify-content:space-between;align-items:baseline;padding-bottom:13px;border-bottom:1.5px solid #d9d4cc;margin-bottom:14px}
.pl-pn .cap{font:600 16px/1 'Geist',sans-serif;letter-spacing:.17em;color:#55514b;text-transform:uppercase}
.pl-pn .fig{font:400 19px/1 'Lora',serif;font-style:italic;color:#8a847a}
.pl-pn .sec{margin:4px 0 12px}
.pl-pn .sw{display:flex;gap:12px;margin:12px 0 14px}
.pl-pn .sw div{flex:1;border:1.5px solid transparent;border-radius:4px;padding:6px 6px 5px;text-align:center}
.pl-pn .sw div.on{border-color:#bdb6ab;background:rgba(255,255,255,.3)}
.pl-pn .sw b{display:block;height:26px;border-radius:2px;border-bottom:9px solid #f3efe8;margin-bottom:6px}
.pl-pn .sw span{font:400 17px/1 'Lora',serif;font-style:italic;color:#4a463f}
.pl-pn .sl{margin:9px 0 2px}
.pl-pn .sl .top{display:flex;justify-content:space-between;align-items:baseline}
.pl-pn .sl .v{font:500 17px/1 'JetBrains Mono',monospace;color:#2e2b27}
.pl-pn .sl .tr{position:relative;height:22px;margin:4px 0 0}
.pl-pn .sl .tr:before{content:'';position:absolute;left:0;right:0;top:11px;height:1.5px;background:#b3ada3}
.pl-pn .sl .k{position:absolute;top:3px;width:16px;height:16px;margin-left:-8px;border-radius:50%;border:1.8px solid #3b3833;background:#efebe5}
.pl-pn .sl .ext{display:flex;justify-content:space-between;font:400 16px/1 'Lora',serif;font-style:italic;color:#8a847a}
.pl-pn .bt{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px;padding-top:13px;border-top:1.5px solid #d9d4cc}
.pl-pn .bt div{border:1.5px solid #b9b3aa;border-radius:3px;height:40px;display:flex;align-items:center;justify-content:center;font:500 19px/1 'Geist',sans-serif;color:#2e2b27;background:rgba(255,255,255,.22)}
.pl-pn .bt div.on{background:${PAL.tinta};border-color:${PAL.tinta};color:#f4f1ec}
.pl-pn .ck{display:flex;gap:16px;margin-top:13px;font:500 16px/1 'Geist',sans-serif;color:#4a463f;align-items:center}
.pl-pn .ck i{display:inline-block;width:13px;height:13px;border:1.5px solid #6b665e;margin-right:6px;vertical-align:-2px;position:relative}
.pl-pn .ck i.on:after{content:'';position:absolute;inset:2px;background:#2e2b27}
.pl-rd{position:absolute;left:58px;bottom:70px;width:520px}
.pl-rd .dica{font:400 24px/1.3 'Lora',serif;font-style:italic;color:#3f3b35;margin-bottom:20px;min-height:94px}
.pl-rd .dica b{font:600 15px/1 'Geist',sans-serif;font-style:normal;letter-spacing:.16em;color:#6f6a62;margin-right:10px;vertical-align:2px}
.pl-rd .dd{display:flex;border-top:1.5px solid #d3cec6;padding-top:12px}
.pl-rd .dd div{padding:0 22px 0 0;margin-right:20px;border-right:1.5px solid #d3cec6}
.pl-rd .dd div:last-child{border-right:0}
.pl-rd .dd .r{font:600 14px/1 'Geist',sans-serif;letter-spacing:.16em;color:#6f6a62;text-transform:uppercase;margin-bottom:9px}
.pl-rd .dd .v{font:500 29px/1 'JetBrains Mono',monospace;color:${PAL.tinta};white-space:nowrap}
.pl-rd .dd .v small{font:400 15px/1 'Geist',sans-serif;color:#77726a;margin-left:5px}
.pl-rd .nota{margin-top:14px;font:400 14px/1.35 'Geist',sans-serif;color:#8d877e}
.pl-canto{position:absolute;right:40px;bottom:70px;border:1.5px solid #d3cec6;border-radius:4px;padding:12px 16px;font:600 14px/1 'Geist',sans-serif;letter-spacing:.16em;color:#55514b;display:flex;gap:40px}
`;
let HUD = null;
export function hud() {
  if (HUD) return HUD;
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  const el = document.createElement('div'); el.className = 'pl-hud'; document.getElementById('stage').appendChild(el);
  HUD = { el }; return HUD;
}
const div = (cls, html = '') => { const e = document.createElement('div'); e.className = cls; e.innerHTML = html; hud().el.appendChild(e); return e; };
/** cabeçalho editorial: rótulo pequeno, título enorme em serifa itálica (2 linhas, a 2ª recuada) e texto itálico curto */
export function cabecalhoEditorial(S, o) {
  div('pl-rot', o.rotulo);
  div('pl-tit', `<span>${o.titulo[0]}</span><span class="l2">${o.titulo[1]}</span>`);
  if (o.texto) div('pl-txt', o.texto.join('<br>'));
  if (o.selo) div('pl-selo', `<i></i>${o.selo}`);
}
/**
 * Painel do espécime. o: {titulo, fig, top, pelos:[{nome, cor}], pelo (índice ativo), sliders:[{nome, valor(t)|txt, k(t)|n, min, max}],
 *  acoes:[nomes], ativa(t) → índice, checks:[[txt, on]]}
 */
export function painel(S, o) {
  const p = div('pl-pn'); p.style.top = (o.top ?? 1130) + 'px';
  let h = `<div class="hd"><span class="cap">${o.titulo}</span><span class="fig">${o.fig || ''}</span></div>`;
  if (o.pelos) h += `<div class="cap">${o.rotuloPelo || 'Pelo'}</div><div class="sw">${o.pelos.map((q, i) => `<div class="${i === (o.pelo ?? 0) ? 'on' : ''}"><b style="background:${q.cor}"></b><span>${q.nome}</span></div>`).join('')}</div>`;
  h += (o.sliders || []).map(s => `<div class="sl"><div class="top"><span class="cap">${s.nome}</span><span class="v"></span></div><div class="tr"><span class="k"></span></div><div class="ext"><span>${s.min}</span><span>${s.max}</span></div></div>`).join('');
  if (o.acoes) h += `<div class="bt">${o.acoes.map(a => `<div>${a}</div>`).join('')}</div>`;
  if (o.checks) h += `<div class="ck">${o.checks.map(([t, on]) => `<span><i class="${on ? 'on' : ''}"></i>${t}</span>`).join('')}</div>`;
  p.innerHTML = h;
  const sls = [...p.querySelectorAll('.sl')], bts = [...p.querySelectorAll('.bt div')];
  S.hud.push(t => {
    (o.sliders || []).forEach((s, i) => { const k = typeof s.k === 'function' ? s.k(t) : s.k; sls[i].querySelector('.k').style.left = (clamp(k) * 100) + '%'; sls[i].querySelector('.v').textContent = typeof s.valor === 'function' ? s.valor(t) : s.valor; });
    const a = o.ativa ? o.ativa(t) : -1; bts.forEach((b, i) => b.classList.toggle('on', i === a));
  });
  return p;
}
/** rodapé: dica itálica (muda com a ação), dados em mono e nota de escala. o: {dica(t) → [rótulo, texto], dados:[{r, v(t)|txt, u}], nota} */
export function rodape(S, o) {
  const r = div('pl-rd', `<div class="dica"></div><div class="dd">${o.dados.map(d => `<div><div class="r">${d.r}</div><div class="v"><span></span><small>${d.u || ''}</small></div></div>`).join('')}</div>${o.nota ? `<div class="nota">${o.nota}</div>` : ''}`);
  const dica = r.querySelector('.dica'), vs = [...r.querySelectorAll('.dd .v span')]; let ult = '';
  S.hud.push(t => {
    const d = o.dica ? o.dica(t) : null; const k = d ? d.join('|') : ''; if (k !== ult) { dica.innerHTML = d ? `<b>${d[0]}</b>${d[1]}` : ''; ult = k; }
    o.dados.forEach((q, i) => { vs[i].textContent = typeof q.v === 'function' ? q.v(t) : q.v; });
  });
  return r;
}
export function canto(S, txt) { return div('pl-canto', `<span>${txt}</span><span>+</span>`); }
