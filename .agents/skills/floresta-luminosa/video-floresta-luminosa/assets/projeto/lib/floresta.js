// floresta.js — biblioteca do estilo "floresta luminosa" (three.js, módulo ES)
// Diorama noturno low-poly "desenhado a lápis de cor sobre papel preto": cada face é hachurada à mão numa direção
// própria, a água é a única luz fria (emissiva, com halo), câmera travada e micro-movimentos em laço a 10 qps.
// Uso na página:  import * as FL from '../../lib/floresta.js';  const S = FL.palco({...});
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
export { THREE, mergeGeometries };

// Cores em sRGB direto: sem gestão de cor e sem tone mapping, o hex da paleta é o hex do vídeo.
THREE.ColorManagement.enabled = false;

// ───────────────────────── paleta (amostrada da referência) ─────────────────────────
export const PAL = {
  papel: '#0e0a06',                                   // o preto quente que aparece entre os traços
  madeira: '#8a5432', madeiraEsc: '#5a3520', casca: '#6e4228',   // troncos, galhos
  copa: '#6a4a36', terra: '#5e4430', paredao: '#4a3426', barranco: '#3a2416',
  onca: '#c27a40', oncaClara: '#e3a568', ventre: '#c9a47c', mancha: '#1a0e07',
  agua: '#78c2f3', aguaMeio: '#4f86c0', aguaFunda: '#15283f', espuma: '#c8e8ff',
  ceu: '#3a4c66', ceuFundo: '#10151c', estrela: '#f6eedc',
  fundo: '#4a4943', musgo: '#4f5a48', folha: '#8a6a4c', folhaEsc: '#5a4a3a',
  pedra: '#8a78a6', pedraEsc: '#59413e', peixe: '#b9826a', olho: '#d6c68a', olhoNoite: '#eaf8a8',
  creme: '#f2dcae', azulTexto: '#bfe4ff',
};

// ───────────────────────── utilidades determinísticas ─────────────────────────
export function rng(seed = 1) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const suave = (a, b, v) => { const k = clamp((v - a) / (b - a)); return k * k * (3 - 2 * k); };
export const io = k => (k = clamp(k), k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
/** progresso 0→1 de t na janela [a,b] */
export const prog = (t, a, b) => clamp((t - a) / (b - a));
/** tempo quantizado (stop-motion): o estilo inteiro anda a 10 qps */
export const degrau = (t, fps = 10) => Math.floor(t * fps + 1e-6) / fps;
const PERM = (() => { const r = rng(1337), p = [...Array(256).keys()]; for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; } return Uint8Array.from([...p, ...p]); })();
/** ruído de valor 2D suave em [-1,1] */
export function ruido(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi, X = xi & 255, Y = yi & 255;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), h = (a, b) => PERM[PERM[a] + b] / 127.5 - 1;
  return lerp(lerp(h(X, Y), h(X + 1, Y), u), lerp(h(X, Y + 1), h(X + 1, Y + 1), u), v);
}

// ───────────────────────── uniforms globais ─────────────────────────
export const U = {
  tempo: { value: 0 },                                               // tempo QUANTIZADO (10 qps)
  sol: { value: new THREE.Vector3(-.45, .8, .42).normalize() },      // luz da lua (vinda de cima-esquerda-frente)
  pxK: { value: .001 },                                              // tamanho do pixel / profundidade (definido pelo palco)
  aneis: { value: [0, 1, 2, 3].map(() => new THREE.Vector4(0, 0, -99, 0)) },   // ondas quadradas na água: (x, z, t0, força)
};

// ───────────────────────── palco: renderer + bloom + acabamento ─────────────────────────
const ACABAMENTO = {
  uniforms: { tDiffuse: { value: null }, uVig: { value: .42 }, uLev: { value: .02 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uVig, uLev; varying vec2 vUv;
    float h(vec2 p){ p=fract(p*vec2(123.34,456.21)); p+=dot(p,p+45.32); return fract(p.x*p.y); }
    void main(){ vec2 c=(vUv-.5)*vec2(.62,1.); float d=length(c);
      vec3 col=texture2D(tDiffuse,vUv).rgb;
      col*=1.-uVig*smoothstep(.22,.62,d);
      col+=(h(floor(vUv*vec2(1080.,1920.)))-.5)*uLev;      // pó fixo do papel (não anima: o traço não ferve)
      gl_FragColor=vec4(max(col,0.),1.); }`,
};

/**
 * palco({ fov, cam:[x,y,z], alvo:[x,y,z], fundo, bloom:{forca,raio,limiar}, vinheta, fps })
 * Câmera travada (o estilo não mexe a câmera). S.update = (tq, t) => {...} recebe o tempo já quantizado.
 */
export function palco(o = {}) {
  const V = window.VIDEO;
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  renderer.toneMapping = THREE.NoToneMapping; renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.domElement.className = 'layer';
  document.getElementById('stage').prepend(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(o.fundo ?? PAL.papel);
  const camera = new THREE.PerspectiveCamera(o.fov ?? 32, V.w / V.h, .1, 300);
  camera.position.set(...(o.cam ?? [0, 1.6, 13.5])); camera.lookAt(new THREE.Vector3(...(o.alvo ?? [0, .3, -1])));
  camera.updateMatrixWorld();
  U.pxK.value = 2 * Math.tan(camera.fov * Math.PI / 360) / V.h;
  const rt = new THREE.WebGLRenderTarget(V.w, V.h, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, rt); composer.setPixelRatio(1); composer.setSize(V.w, V.h);
  composer.addPass(new RenderPass(scene, camera));
  const b = o.bloom || {};
  const bloom = new UnrealBloomPass(new THREE.Vector2(V.w / 2, V.h / 2), b.forca ?? .55, b.raio ?? .55, b.limiar ?? .58);
  composer.addPass(bloom);
  const fin = new ShaderPass(ACABAMENTO); fin.uniforms.uVig.value = o.vinheta ?? .42; composer.addPass(fin);
  const S = { THREE, renderer, scene, camera, composer, bloom, update: null, fps: o.fps ?? 10, tq: 0 };
  onTick(t => { const tq = degrau(t, S.fps); S.tq = tq; U.tempo.value = tq; if (S.update) S.update(tq, t); composer.render(); });
  return S;
}

/** profundidade (distância à câmera) do centro de um objeto — usada para o traço ter ~o mesmo tamanho em pixels */
export function profundidade(S, obj) {
  const box = new THREE.Box3().setFromObject(obj), c = box.getCenter(new THREE.Vector3());
  return c.applyMatrix4(S.camera.matrixWorldInverse).z * -1;
}
/** fixa a profundidade de referência do traço de cada malha (chame depois de montar a cena; não recalcula se já tiver) */
export function calibrar(S, raiz = S.scene) {
  S.scene.updateMatrixWorld(true);
  raiz.traverse(m => { if (m.isMesh && m.material?.uniforms?.uProf && m.material.uniforms.uProf.value <= 0) m.material.uniforms.uProf.value = Math.max(1, profundidade(S, m)); });
}

// ───────────────────────── material de lápis (o coração do estilo) ─────────────────────────
const VERT = `
attribute vec3 aN; attribute vec3 aD; attribute float aF;
varying vec3 vO; varying vec3 vW; varying vec3 vN; varying vec3 vNW; varying vec3 vD; varying float vF;
void main(){
  vO = position; vN = aN; vD = aD; vF = aF;
  vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz;
  vNW = normalize(mat3(modelMatrix) * aN);
  gl_Position = projectionMatrix * viewMatrix * w;
}`;
const FRAG = `
uniform vec3 uCor, uCor2, uPapel, uSol, uVentre, uMancha, uFundoCor;
uniform float uPx, uProf, uPxK, uDens, uLarg, uComp, uVar, uAmb, uDif, uBrilho, uTempo, uVel, uAlfa, uSeed, uReal, uFundoY, uRealce;
uniform float uLustro; uniform vec4 uManchas; uniform vec4 uGrad; uniform vec4 uAneis[4]; uniform float uAneisOn; uniform vec3 uAnelCor;
varying vec3 vO; varying vec3 vW; varying vec3 vN; varying vec3 vNW; varying vec3 vD; varying float vF;
float hs(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
vec3 h33(vec3 p){ p = fract(p*vec3(.1031,.1030,.0973)); p += dot(p, p.yxz+33.33); return fract((p.xxy+p.yxx)*p.zyx); }
// uma fileira de traços paralelos: linhas = uv.y inteiro; traços de comprimento variável ao longo de uv.x, levemente inclinados
vec2 linha(vec2 uv, float seed, float dens, float larg, float comp){
  float row = floor(uv.y);
  float r1 = hs(vec2(row, seed)), r2 = hs(vec2(row*.37 + 3.1, seed + 7.31));
  float L = comp * mix(.45, 1.9, r1);
  float x = uv.x / L + r2 * 13.;
  float sg = floor(x), fu = fract(x);
  float s1 = hs(vec2(sg + seed*.13, row + 1.7)), s2 = hs(vec2(sg*1.31 + .5, row*1.7 + seed)), s3 = hs(vec2(sg*.77 - 2.3, row - seed));
  float on = step(1. - dens, s1);
  float c = .5 + (s2 - .5)*.3 + (s3 - .5)*.5*(fu - .5) + .06*sin(uv.x*.5 + r1*6.28);
  float tip = smoothstep(0., .16, fu) * smoothstep(1., .78, fu);
  float w = larg * mix(.5, 1.3, s3) * .5 * mix(.25, 1., tip);
  float d = abs(fract(uv.y) - c);
  float aa = max(fwidth(uv.y), 1e-3) * .8;
  float ink = (1. - smoothstep(w - aa, w + aa, d)) * on * step(.06, fu) * step(fu, .95);
  return vec2(ink, mix(.5, 1.3, s2*.55 + s3*.45));
}
// duas fileiras intercaladas (meia linha de defasagem, comprimentos diferentes): quebra a cara de "tijolinho"
vec2 tracos(vec2 uv, float seed, float dens, float larg, float comp){
  vec2 a = linha(uv, seed, dens, larg, comp);
  vec2 b = linha(uv + vec2(31.7, .5), seed + 5.3, dens * .85, larg * .9, comp * 1.35);
  return a.x >= b.x ? a : b;
}
float manchas(vec3 p, vec3 T, vec3 B){
  vec3 q = p / uManchas.y; vec3 i = floor(q), f = fract(q);
  float best = 9.; vec3 bv = vec3(0.); vec3 bc = vec3(0.);
  for (int z=-1; z<=1; z++) for (int y=-1; y<=1; y++) for (int x=-1; x<=1; x++) {
    vec3 g = vec3(float(x), float(y), float(z)); vec3 o = h33(i + g) * .7 + .15; vec3 r = g + o - f; float d = dot(r, r);
    if (d < best) { best = d; bv = r; bc = i + g; }
  }
  float d = sqrt(best); vec3 hc = h33(bc + 5.);
  if (uManchas.x < 1.5) {                       // roseta: anel quebrado (às vezes com pinta no meio)
    float R = uManchas.z * mix(.8, 1.2, hc.x);
    float ring = 1. - smoothstep(.085, .11, abs(d - R));
    float ang = atan(dot(bv, T), dot(bv, B));
    float nb = floor(mix(3., 6., hc.z));
    float brk = step(mix(.22, .42, hc.x), fract(ang / 6.2832 * nb + hc.y + .15 * sin(ang * 3. + hc.z * 6.)));
    float mid = (1. - smoothstep(.06, .1, d)) * step(.55, hc.z);
    return clamp(ring * brk + mid, 0., 1.);
  }
  return 1. - smoothstep(uManchas.z * mix(.6, 1.15, hc.x) - .05, uManchas.z * mix(.6, 1.15, hc.x), d);   // pintas cheias
}
void main(){
  vec3 nW = normalize(vNW); if (!gl_FrontFacing) nW = -nW;
  float ndl = max(dot(nW, normalize(uSol)), 0.);
  float tone = 1. + (vF - .5) * uVar;
  float grad = uGrad.z == uGrad.w ? 1. : mix(uGrad.z, uGrad.w, smoothstep(uGrad.x, uGrad.y, vW.y));
  float lus = uLustro > 0. ? 1. + uLustro * (sin(dot(vW.xz, vec2(1.7, .9)) + vF * 6.28) * .5 - .2) : 1.;
  float L = (uAmb + uDif * ndl) * tone * uBrilho * grad * lus;
  float Lc = clamp(L, 0., 1.);
  vec3 T = normalize(vD), B = normalize(cross(vN, vD));
  float esp = uPx * uProf * uPxK;
  vec2 uv = vec2(dot(vO, T) - uTempo * uVel, dot(vO, B)) / esp + vF * 97.;
  vec2 A = tracos(uv, uSeed + floor(vF * 50.), mix(.32, .8, Lc) * uDens, mix(.3, .46, Lc) * uLarg, uComp);
  float cr = cos(.24), sr = sin(.24);
  vec2 uv2 = vec2(cr*uv.x - sr*uv.y, sr*uv.x + cr*uv.y) * vec2(1., 1.3) + 17.3;
  vec2 A2 = linha(uv2, uSeed + 11., .3 * uDens * mix(.4, 1., Lc), .34 * uLarg, uComp * .7);
  vec3 cor = uCor, cor2 = uCor2;
  if (uManchas.w > .5) { float vb = smoothstep(-.3, -.75, vN.y); cor = mix(cor, uVentre, vb); cor2 = mix(cor2, uVentre, vb); }
  if (uReal > .5) { float sub = 1. - smoothstep(uFundoY - .04, uFundoY + .04, vW.y); cor = mix(cor, uFundoCor, sub); cor2 = mix(cor2, uFundoCor * 1.3, sub); L *= mix(1., .8, sub); }
  vec3 col = uPapel * (.55 + .45 * Lc);
  col = mix(col, cor * A.y * (.28 + .82 * L), A.x);
  col = mix(col, cor2 * A2.y * (.32 + .8 * L), A2.x * .8 * uRealce);
  if (uManchas.x > .5) { float m = manchas(vO, T, B); col = mix(col, uMancha * (.7 + .5 * A.y), m * (.88 + .12 * A.x)); }
  float alfa = mix(uAlfa, 1., max(A.x, A2.x * .8 * uRealce));
  if (uAneisOn > .5) {
    for (int k = 0; k < 4; k++) {
      vec4 a = uAneis[k]; float age = uTempo - a.z;
      if (a.w <= 0. || age < 0. || age > 1.5) continue;
      vec2 dp = vW.xz - a.xy; float dch = max(abs(dp.x), abs(dp.y) * 1.15);
      for (int j = 0; j < 3; j++) {
        float r = (age - float(j) * .22) * .6; if (r < .015) continue;
        float w = .007 + .002 * float(j); float aa = fwidth(dch) * 1.2;
        float l = (1. - smoothstep(w, w + aa, abs(dch - r))) * a.w * (1. - age / 1.5) * .75;
        col = mix(col, uAnelCor, l);
        alfa = max(alfa, l);
      }
    }
  }
  gl_FragColor = vec4(col, alfa);
}`;

/**
 * lapis({ cor, cor2, papel, px, prof, dens, larg, comp, var, amb, dif, brilho, vel, alfa, semente,
 *         manchas:[tipo, celula, raio, ventre], ventre, mancha, grad:[y0,y1,k0,k1], fundo:{y, cor}, aneis, realce })
 * cor: cor dos traços · cor2: traços de realce (2ª camada girada) · px: distância entre traços em pixels
 * amb/dif: luz ambiente e da lua · vel: traços deslizando ao longo da direção (água) · emissivo = amb 1, dif 0.
 */
export function lapis(o = {}) {
  const C = v => new THREE.Color(v);
  const m = new THREE.ShaderMaterial({
    vertexShader: VERT, fragmentShader: FRAG, side: THREE.DoubleSide,
    transparent: (o.alfa ?? 1) < 1, depthWrite: (o.alfa ?? 1) >= 1,
    uniforms: {
      uTempo: U.tempo, uSol: U.sol, uPxK: U.pxK, uAneis: U.aneis,
      uCor: { value: C(o.cor ?? PAL.madeira) }, uCor2: { value: C(o.cor2 ?? o.cor ?? PAL.madeira) }, uPapel: { value: C(o.papel ?? PAL.papel) },
      uPx: { value: o.px ?? 4.4 }, uProf: { value: o.prof ?? 0 }, uDens: { value: o.dens ?? 1 }, uLarg: { value: o.larg ?? 1 }, uComp: { value: o.comp ?? 14 },
      uVar: { value: o.var ?? .45 }, uAmb: { value: o.amb ?? .42 }, uDif: { value: o.dif ?? .75 }, uBrilho: { value: o.brilho ?? 1 },
      uVel: { value: o.vel ?? 0 }, uAlfa: { value: o.alfa ?? 1 }, uSeed: { value: o.semente ?? 1 }, uRealce: { value: o.realce ?? 1 },
      uManchas: { value: new THREE.Vector4(...(o.manchas ?? [0, 1, .3, 0])) }, uVentre: { value: C(o.ventre ?? PAL.ventre) }, uMancha: { value: C(o.mancha ?? PAL.mancha) },
      uGrad: { value: new THREE.Vector4(...(o.grad ?? [0, 1, 1, 1])) }, uLustro: { value: o.lustro ?? 0 },
      uReal: { value: o.fundo ? 1 : 0 }, uFundoY: { value: o.fundo?.y ?? 0 }, uFundoCor: { value: C(o.fundo?.cor ?? PAL.fundo) },
      uAneisOn: { value: o.aneis ? 1 : 0 }, uAnelCor: { value: C(o.anelCor ?? '#b9defa') },
    },
  });
  m.isLapis = true;
  return m;
}
/** água luminosa: emissiva, traços claros deslizando no sentido da correnteza */
export const aguaMat = (o = {}) => lapis(Object.assign({ cor: PAL.aguaMeio, cor2: PAL.agua, papel: PAL.aguaFunda, amb: .95, dif: 0, var: 1.1, lustro: .55, comp: 16, px: 4.4, vel: .35, aneis: true, realce: .8 }, o));

// ───────────────────────── geometria facetada ─────────────────────────
/**
 * facetar(geo, { eixo:[x,y,z], jit, semente, porTriangulo, eixoFn(centro, normal) })
 * Deixa a malha "low-poly desenhada": cada face plana ganha a própria direção de traço (eixo projetado no plano,
 * girado ao acaso ±jit/2) e um tom (aF). Triângulos coplanares vizinhos ficam com a mesma direção.
 */
export function facetar(geo, o = {}) {
  const g = geo.index ? geo.toNonIndexed() : geo.clone();
  for (const k of Object.keys(g.attributes)) if (k !== 'position') g.deleteAttribute(k);
  g.clearGroups();
  const P = g.attributes.position, n = P.count / 3;
  const aN = new Float32Array(P.count * 3), aD = new Float32Array(P.count * 3), aF = new Float32Array(P.count);
  const R = rng(o.semente ?? 7), grupos = new Map(), eixo = new THREE.Vector3(...(o.eixo ?? [0, 1, 0])).normalize();
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), e1 = new THREE.Vector3(), nn = new THREE.Vector3(), t = new THREE.Vector3(), ce = new THREE.Vector3();
  const tol = o.tol ?? 60;
  for (let i = 0; i < n; i++) {
    a.fromBufferAttribute(P, 3 * i); b.fromBufferAttribute(P, 3 * i + 1); c.fromBufferAttribute(P, 3 * i + 2);
    nn.subVectors(b, a).cross(e1.subVectors(c, a));
    if (nn.lengthSq() < 1e-14) nn.set(0, 1, 0); nn.normalize();
    const key = o.porTriangulo ? i : [nn.x, nn.y, nn.z, nn.dot(a)].map(v => Math.round(v * tol)).join(',');
    let G = grupos.get(key);
    if (!G) {
      ce.copy(a).add(b).add(c).multiplyScalar(1 / 3);
      const ax = o.eixoFn ? o.eixoFn(ce, nn) : eixo;
      t.copy(ax).addScaledVector(nn, -ax.dot(nn));
      if (t.lengthSq() < .05) { t.set(1, 0, 0).addScaledVector(nn, -nn.x); if (t.lengthSq() < .05) t.set(0, 0, 1).addScaledVector(nn, -nn.z); }
      t.normalize().applyAxisAngle(nn, (R() - .5) * (o.jit ?? .9));
      G = { f: R(), t: t.clone() }; grupos.set(key, G);
    }
    for (let k = 0; k < 3; k++) { const j = 3 * i + k; aN[3 * j] = nn.x; aN[3 * j + 1] = nn.y; aN[3 * j + 2] = nn.z; aD[3 * j] = G.t.x; aD[3 * j + 1] = G.t.y; aD[3 * j + 2] = G.t.z; aF[j] = G.f; }
  }
  g.setAttribute('aN', new THREE.BufferAttribute(aN, 3)); g.setAttribute('aD', new THREE.BufferAttribute(aD, 3)); g.setAttribute('aF', new THREE.BufferAttribute(aF, 1));
  return g;
}
/** aplica uma matriz a uma geometria já facetada (posição + normal e direção do traço) */
export function transformar(g, M) {
  g.attributes.position.applyMatrix4(M);
  const R = new THREE.Matrix3().getNormalMatrix(M), v = new THREE.Vector3();
  for (const k of ['aN', 'aD']) { const A = g.attributes[k]; if (!A) continue; for (let i = 0; i < A.count; i++) { v.fromBufferAttribute(A, i).applyMatrix3(R).normalize(); A.setXYZ(i, v.x, v.y, v.z); } A.needsUpdate = true; }
  return g;
}
export const unir = gs => mergeGeometries(gs, false);
export const M4 = (pos = [0, 0, 0], rot = [0, 0, 0], esc = 1) => new THREE.Matrix4().compose(new THREE.Vector3(...pos), new THREE.Quaternion().setFromEuler(new THREE.Euler(...rot, 'YXZ')), new THREE.Vector3(...(Array.isArray(esc) ? esc : [esc, esc, esc])));
export function malha(geo, mat, pai) { const m = new THREE.Mesh(geo, mat); m.frustumCulled = false; if (pai) pai.add(m); return m; }

// seções para loft (lado, cima) em [-1,1]
export const FORMA = {
  caixa: [[-1, -1], [1, -1], [1, .4], [.55, 1], [-.55, 1], [-1, .4]],          // caixa chanfrada (corpo da onça)
  hex: [...Array(6)].map((_, i) => [Math.cos(i / 6 * Math.PI * 2 + .5), Math.sin(i / 6 * Math.PI * 2 + .5)]),
  pent: [...Array(5)].map((_, i) => [Math.cos(i / 5 * Math.PI * 2 + .3), Math.sin(i / 5 * Math.PI * 2 + .3)]),
  losango: [[0, -1], [1, 0], [0, 1], [-1, 0]],
};
/**
 * loft(secoes, { forma, cima, tampas, dir }) → BufferGeometry (sem facetar)
 * secoes: [{ p:[x,y,z], w, h, forma? }] ao longo de um caminho; cada seção fica perpendicular ao caminho
 * (ou a `dir`, se dada: use dir:[1,0,0] em cabeças e corpos, senão o anel inclina e a testa cobre os olhos).
 */
export function loft(secoes, o = {}) {
  const forma = o.forma ?? FORMA.hex, up0 = new THREE.Vector3(...(o.cima ?? [0, 1, 0]));
  const C = secoes.map(s => new THREE.Vector3(...s.p)), anel = [];
  for (let i = 0; i < secoes.length; i++) {
    const f = o.dir ? new THREE.Vector3(...o.dir).normalize() : new THREE.Vector3().subVectors(C[Math.min(i + 1, C.length - 1)], C[Math.max(i - 1, 0)]).normalize();
    let s = new THREE.Vector3().crossVectors(f, up0); if (s.lengthSq() < 1e-6) s.set(0, 0, 1); s.normalize();
    const u = new THREE.Vector3().crossVectors(s, f).normalize(), sec = secoes[i], fm = sec.forma ?? forma;
    anel.push(fm.map(([x, y]) => C[i].clone().addScaledVector(s, x * sec.w / 2).addScaledVector(u, y * sec.h / 2)));
  }
  const pos = [], push = (...vs) => vs.forEach(v => pos.push(v.x, v.y, v.z)), k = forma.length;
  for (let i = 0; i < anel.length - 1; i++) for (let j = 0; j < k; j++) {
    const a = anel[i][j], b = anel[i][(j + 1) % k], c = anel[i + 1][(j + 1) % k], d = anel[i + 1][j];
    push(a, c, b, a, d, c);                // normais para fora
  }
  if (o.tampas !== false) {
    for (const [r, inv] of [[anel[0], true], [anel[anel.length - 1], false]]) {
      const m = r.reduce((s, v) => s.add(v), new THREE.Vector3()).multiplyScalar(1 / k);
      for (let j = 0; j < k; j++) inv ? push(m, r[j], r[(j + 1) % k]) : push(m, r[(j + 1) % k], r[j]);
    }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); return g;
}
/** geometria a partir de uma lista de triângulos [[a,b,c], ...] */
export function tris(lista) { const pos = []; lista.forEach(t => t.forEach(v => pos.push(...v))); const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); return g; }
/** pedra low-poly: icosaedro amassado. o: {r, achatar, semente} */
export function pedraGeo(o = {}) {
  const g = new THREE.IcosahedronGeometry(o.r ?? .3, 0), P = g.attributes.position, R = rng(o.semente ?? 3);
  for (let i = 0; i < P.count; i++) P.setXYZ(i, P.getX(i) * (1 + (R() - .5) * .35), P.getY(i) * (o.achatar ?? .45), P.getZ(i) * (1 + (R() - .5) * .35));
  return g;
}

// ───────────────────────── cenário ─────────────────────────
/**
 * relevoRio({ centro(z), largura(z), poco(x), fundo, margem(x,z) }) → { altura(x,z), margem(x,z) }
 * O relevo-padrão do estilo: margens baixas com ruído, a vala do rio afundando até `fundo` e (opcional) um poço que
 * ocupa toda a frente a partir de z = poco(x) — é ele que vira o "corte de aquário" com peixes. Passe `altura` ao terreno.
 */
export function relevoRio(o = {}) {
  const margem = o.margem ?? ((x, z) => .12 + .12 * ruido(x * .7, z * .7) + .06 * ruido(x * 2.1 + 3, z * 1.7));
  const fundo = o.fundo ?? -1.8;
  const altura = (x, z) => {
    const d = Math.abs(x - o.centro(z)) / o.largura(z);
    const poco = o.poco ? suave(o.poco(x) - .15, o.poco(x) + .35, z) : 0;
    return lerp(fundo + .2 * ruido(x * 1.3, z * 1.1), margem(x, z), suave(.72, 1.05, d) * (1 - poco));
  };
  return { altura, margem };
}
/**
 * terreno(S, { x:[x0,x1], z:[z0,z1], nx, nz, altura(x,z), cor, cor2, fundo:{y, cor}, base, jit, semente, px })
 * Malha de alturas grossa (faces grandes = facetas) + parede de corte na frente (z1) descendo até `base`.
 * Devolve { mesh, parede, perfil:[[x,y]...] } — o perfil da frente serve para recortar o "vidro" d'água.
 */
export function terreno(S, o) {
  const R = rng(o.semente ?? 11), nx = o.nx ?? 16, nz = o.nz ?? 12, jit = o.jit ?? .32, G = [];
  for (let j = 0; j <= nz; j++) { const row = []; for (let i = 0; i <= nx; i++) {
    let x = lerp(o.x[0], o.x[1], i / nx), z = lerp(o.z[0], o.z[1], j / nz);
    const dx = (o.x[1] - o.x[0]) / nx, dz = (o.z[1] - o.z[0]) / nz;
    if (i > 0 && i < nx) x += (R() - .5) * jit * dx;
    if (j > 0 && j < nz) z += (R() - .5) * jit * dz;
    row.push([x, o.altura(x, z), z]); } G.push(row); }
  const T = [];
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const a = G[j][i], b = G[j][i + 1], c = G[j + 1][i + 1], d = G[j + 1][i];
    if ((i + j) % 2) T.push([a, d, b], [b, d, c]); else T.push([a, d, c], [a, c, b]);
  }
  const mat = lapis(Object.assign({ cor: o.cor ?? PAL.terra, cor2: o.cor2 ?? o.cor ?? PAL.terra, fundo: o.fundo, px: o.px ?? 4.4, comp: 15 }, o.mat || {}));
  const mesh = malha(facetar(tris(T), { eixo: [1, 0, .3], jit: 1.4, semente: o.semente ?? 11 }), mat, S.scene);
  const base = o.base ?? -4, fr = G[nz], W = [];
  for (let i = 0; i < nx; i++) { const a = fr[i], b = fr[i + 1]; W.push([a, [a[0], base, a[2]], b], [b, [a[0], base, a[2]], [b[0], base, b[2]]]); }
  const parede = malha(facetar(tris(W), { eixo: [.15, 1, 0], jit: .5, semente: 5 }), lapis(Object.assign({ cor: o.corParede ?? PAL.barranco, px: o.px ?? 4.4, comp: 12, amb: .5, dif: .35 }, o.matParede || {})), S.scene);
  return { mesh, parede, perfil: fr.map(p => [p[0], p[1], p[2]]), grade: G };
}
/** vidro d'água na frente do corte: polígono entre a superfície (y=0) e o perfil do terreno onde ele está abaixo d'água */
export function vidroAgua(S, perfil, o = {}) {
  const T = [], y0 = o.nivel ?? 0, z = perfil[0][2] + (o.frente ?? .004);
  for (let i = 0; i < perfil.length - 1; i++) {
    let [xa, ya] = perfil[i], [xb, yb] = perfil[i + 1];
    if (ya >= y0 && yb >= y0) continue;
    if (ya > y0) { const k = (y0 - ya) / (yb - ya); xa = lerp(xa, xb, k); ya = y0; }
    if (yb > y0) { const k = (y0 - ya) / (yb - ya); xb = lerp(xa, xb, k); yb = y0; }
    T.push([[xa, ya, z], [xb, yb, z], [xb, y0, z]], [[xa, ya, z], [xb, y0, z], [xa, y0, z]]);
  }
  const mat = lapis(Object.assign({ cor: '#3c5a5a', cor2: '#6f9a9a', papel: '#0b1212', alfa: .1, amb: .55, dif: 0, dens: .22, comp: 24, px: 5.7, var: .2, realce: .4 }, o.mat || {}));
  return malha(facetar(tris(T), { eixo: [1, 0, 0], jit: .25, semente: 4 }), mat, S.scene);
}
/** superfície da água: plano facetado em y=nivel (só aparece onde o terreno afunda). o: {x, z, nx, nz, fluxo:[x,y,z], ...mat} */
export function rio(S, o = {}) {
  const R = rng(o.semente ?? 21), nx = o.nx ?? 7, nz = o.nz ?? 9, T = [], G = [];
  for (let j = 0; j <= nz; j++) { const row = []; for (let i = 0; i <= nx; i++) {
    let x = lerp(o.x[0], o.x[1], i / nx), z = lerp(o.z[0], o.z[1], j / nz);
    if (i > 0 && i < nx) x += (R() - .5) * .7 * (o.x[1] - o.x[0]) / nx;
    if (j > 0 && j < nz) z += (R() - .5) * .7 * (o.z[1] - o.z[0]) / nz;
    row.push([x, o.nivel ?? 0, z]); } G.push(row); }
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const a = G[j][i], b = G[j][i + 1], c = G[j + 1][i + 1], d = G[j + 1][i];
    if (R() < .5) T.push([a, d, b], [b, d, c]); else T.push([a, d, c], [a, c, b]);
  }
  const fl = o.fluxo ?? [.08, 0, 1];
  return malha(facetar(tris(T), { eixo: fl, jit: .5, porTriangulo: true, semente: o.semente ?? 21 }), aguaMat(o.mat || {}), S.scene);
}
/** cachoeira: cortina de 3 facetas com riscos verticais descendo + faixa de espuma na base. o: {x, y0, y1, z, larg, vel} */
export function cachoeira(S, o = {}) {
  const g = new THREE.Group(); S.scene.add(g);
  const x = o.x ?? 0, z = o.z ?? -7, w = o.larg ?? 1.2, y0 = o.y0 ?? 0, y1 = o.y1 ?? 2, k = [-.5, -.18, .18, .5], dz = [0, .12, .12, 0], T = [];
  for (let i = 0; i < 3; i++) T.push(
    [[x + k[i] * w, y1, z + dz[i]], [x + k[i] * w, y0, z + dz[i] + .25], [x + k[i + 1] * w, y0, z + dz[i + 1] + .25]],
    [[x + k[i] * w, y1, z + dz[i]], [x + k[i + 1] * w, y0, z + dz[i + 1] + .25], [x + k[i + 1] * w, y1, z + dz[i + 1]]]);
  malha(facetar(tris(T), { eixo: [0, -1, 0], jit: .08, semente: 3 }),
    aguaMat(Object.assign({ cor: '#4a86c0', cor2: '#8cc6f5', papel: '#13304e', vel: o.vel ?? 1.1, comp: 24, px: 4, var: .25, aneis: false, larg: .8 }, o.mat || {})), g);
  // espuma: faixa baixa de riscos horizontais
  const F = [[[x - w * .62, y0 + .02, z + .3], [x + w * .62, y0 + .02, z + .3], [x + w * .62, y0 + .2, z + .26]], [[x - w * .62, y0 + .02, z + .3], [x + w * .62, y0 + .2, z + .26], [x - w * .62, y0 + .2, z + .26]]];
  malha(facetar(tris(F), { eixo: [1, 0, 0], jit: .05, semente: 9 }),
    aguaMat({ cor: '#6aa6dc', cor2: '#b4e0ff', papel: '#173a5c', vel: .12, comp: 14, px: 4, aneis: false, dens: .9 }), g);
  return g;
}
/** paredão de pedra/terra ao fundo, com entalhe para a cachoeira. o: {x:[x0,x1], z, base, topo(x), n, cor} */
export function paredao(S, o = {}) {
  const R = rng(o.semente ?? 31), n = o.n ?? 14, linhas = o.linhas ?? 3, T = [], G = [];
  for (let j = 0; j <= linhas; j++) { const row = []; for (let i = 0; i <= n; i++) {
    const x = lerp(o.x[0], o.x[1], i / n) + (i > 0 && i < n ? (R() - .5) * .5 : 0), top = o.topo(x);
    const y = lerp(o.base ?? 0, top, j / linhas) + (j > 0 && j < linhas ? (R() - .5) * .35 : 0);
    row.push([x, y, (o.z ?? -7.5) + (j < linhas ? (R() - .5) * .5 : -.25 + (R() - .5) * .2)]); } G.push(row); }
  for (let j = 0; j < linhas; j++) for (let i = 0; i < n; i++) {
    const a = G[j][i], b = G[j][i + 1], c = G[j + 1][i + 1], d = G[j + 1][i]; T.push([a, b, c], [a, c, d]);
  }
  // topo: faixa horizontal recuando
  const top = G[linhas];
  for (let i = 0; i < n; i++) { const a = top[i], b = top[i + 1]; T.push([a, b, [b[0], b[1] + .05, b[2] - 3]], [a, [b[0], b[1] + .05, b[2] - 3], [a[0], a[1] + .05, a[2] - 3]]); }
  return malha(facetar(tris(T), { eixo: [1, .15, 0], jit: .7, semente: o.semente ?? 31 }), lapis(Object.assign({ cor: o.cor ?? PAL.paredao, amb: .32, dif: .6, comp: 16 }, o.mat || {})), S.scene);
}
/** céu: plano grande atrás de tudo, riscos diagonais longos, mais claro no meio. o: {z, larg, alt, y} */
export function ceu(S, o = {}) {
  const z = o.z ?? -40, w = o.larg ?? 60, h = o.alt ?? 50, y = o.y ?? 8;
  const g = tris([[[-w / 2, y - h / 2, z], [w / 2, y - h / 2, z], [w / 2, y + h / 2, z]], [[-w / 2, y - h / 2, z], [w / 2, y + h / 2, z], [-w / 2, y + h / 2, z]]]);
  return malha(facetar(g, { eixo: [1, .55, 0], jit: 0, semente: 2 }), lapis(Object.assign({ cor: '#2e3d52', cor2: '#40546e', papel: '#0d1117', amb: .9, dif: 0, comp: 26, px: 5.1, var: 0, dens: .75, grad: [-6, 10, .45, 1.05] }, o.mat || {})), S.scene);
}
/** estrelas: pontinhos que piscam a 10 qps. o: {n, z, x:[a,b], y:[a,b], tam:[min,max] px, semente} */
export function estrelas(S, o = {}) {
  const R = rng(o.semente ?? 5), n = o.n ?? 90, pos = [], tam = [], id = [];
  for (let i = 0; i < n; i++) { pos.push(lerp(...(o.x ?? [-22, 22]), R()), lerp(...(o.y ?? [2, 30]), R()), o.z ?? -39); tam.push(lerp(...(o.tam ?? [3, 6.5]), R() ** 2)); id.push(R() * 100); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('aS', new THREE.Float32BufferAttribute(tam, 1)); g.setAttribute('aI', new THREE.Float32BufferAttribute(id, 1));
  const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, uniforms: { uTempo: U.tempo, uCor: { value: new THREE.Color(PAL.estrela) } },
    vertexShader: `attribute float aS; attribute float aI; uniform float uTempo; varying float vB;
      void main(){ gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.);
        float f = floor(uTempo*10.+.001); float h = fract(sin(aI*91.7 + f*13.13)*43758.5453); float h2 = fract(sin(aI*7.3)*1531.7);
        vB = h2 < .3 ? mix(.25, 1., h) : mix(.75, 1., h); gl_PointSize = aS; }`,
    fragmentShader: `uniform vec3 uCor; varying float vB; void main(){ float d = length(gl_PointCoord-.5); gl_FragColor = vec4(uCor*vB, smoothstep(.5,.18,d)*vB); }` });
  const p = new THREE.Points(g, m); p.frustumCulled = false; S.scene.add(p); return p;
}
/**
 * arvore(S, { x, z, y, alt, raio, camadas, cor, corCopa, semente, galhos })
 * Tronco facetado (riscos verticais) + copa em lajes empilhadas (terraços recortados), como madeira entalhada.
 */
export function arvore(S, o = {}) {
  const R = rng(o.semente ?? 41), g = new THREE.Group(); g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); S.scene.add(g);
  const alt = o.alt ?? 3.2, rr = o.tronco ?? .28, inc = o.inclina ?? 0, gs = [];
  const sec = []; for (let i = 0; i <= 5; i++) { const k = i / 5; sec.push({ p: [inc * k * k * alt + Math.sin(k * 3 + R()) * .06, k * alt, 0], w: rr * 2 * lerp(1.25, .7, k), h: rr * 2 * lerp(1.15, .65, k) }); }
  gs.push(facetar(loft(sec, { forma: FORMA.hex }), { eixo: [0, 1, 0], jit: .35, semente: o.semente ?? 41 }));
  for (const gl of o.galhos ?? [[-1, .62], [1, .78]]) {   // [lado, altura relativa]
    const y0 = gl[1] * alt, x0 = inc * gl[1] * gl[1] * alt, L = o.galho ?? .9;
    gs.push(facetar(loft([{ p: [x0, y0, 0], w: rr * 1.1, h: rr }, { p: [x0 + gl[0] * L * .55, y0 + L * .45, (R() - .5) * .3], w: rr * .8, h: rr * .7 }, { p: [x0 + gl[0] * L, y0 + L * .75, (R() - .5) * .4], w: rr * .55, h: rr * .5 }], { forma: FORMA.pent }), { eixo: [gl[0], 1, 0], jit: .3, semente: 7 + gl[0] }));
  }
  malha(unir(gs), lapis({ cor: o.cor ?? PAL.madeira, cor2: '#a86a42', comp: 16, px: o.px ?? 4.4 }), g);
  // copa: lajes de contorno recortado
  const cs = [], raio = o.raio ?? 1.6, n = o.camadas ?? 5, topo = alt + (o.copaY ?? .1);
  for (let i = 0; i < n; i++) {
    const k = i / Math.max(1, n - 1), r = raio * lerp(1, .5, k), pts = [], m = 22;
    for (let j = 0; j < m; j++) { const a = j / m * Math.PI * 2, rr2 = r * (1 + (R() - .5) * .5 + .16 * Math.sin(a * 3 + i * 1.7) + .1 * Math.sin(a * 5 + i)); pts.push(new THREE.Vector2(Math.cos(a) * rr2 * (o.alarga ?? 1.25), Math.sin(a) * rr2 * .8)); }
    const sh = new THREE.Shape(pts), e = new THREE.ExtrudeGeometry(sh, { depth: (o.espessura ?? .34) * (1 + (R() - .5) * .4), bevelEnabled: false, steps: 1 });
    const gm = facetar(e, { eixo: [1, 0, 0], jit: 1.6, semente: 50 + i + (o.semente ?? 0) });
    transformar(gm, M4([(R() - .5) * .5 + (o.copaX ?? 0), topo + i * (o.passo ?? .22) - (i === 0 ? .15 : 0), (R() - .5) * .35], [-Math.PI / 2 + (R() - .5) * .34, R() * 6, (R() - .5) * .3]));
    cs.push(gm);
  }
  malha(unir(cs), lapis({ cor: o.corCopa ?? PAL.copa, cor2: '#8a6448', comp: 12, px: o.px ?? 4.4, amb: .36, dif: .8 }), g);
  return g;
}
/**
 * roseta(S, { x, y, z, n, aneis, comp, larg, cor, semente, ergue }) — planta em roseta (bromélia/agave): folhas em losango dobrado
 * Devolve o grupo; para balançar, gire g.rotation.z/x de leve no update.
 */
export function roseta(S, o = {}) {
  const R = rng(o.semente ?? 61), g = new THREE.Group(); g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); (o.pai ?? S.scene).add(g);
  const gs = [], an = o.aneis ?? 2, n = o.n ?? 7, L0 = o.comp ?? .6, W0 = o.larg ?? .14;
  for (let r = 0; r < an; r++) for (let i = 0; i < n; i++) {
    const L = L0 * lerp(1, .62, r / Math.max(1, an - 1)) * (1 + (R() - .5) * .25), W = W0 * (1 + (R() - .5) * .3), H = W * .55;
    const f = tris([[[0, 0, 0], [L * .4, 0, -W], [L * .42, H, 0]], [[0, 0, 0], [L * .42, H, 0], [L * .4, 0, W]], [[L * .42, H, 0], [L * .4, 0, -W], [L, 0, 0]], [[L * .42, H, 0], [L, 0, 0], [L * .4, 0, W]]]);
    const gm = facetar(f, { eixo: [1, 0, 0], jit: .25, semente: 100 + r * 20 + i });
    const elev = lerp(o.ergue ?? .55, (o.ergue ?? .55) + .55, r / Math.max(1, an - 1)) + (R() - .5) * .2;
    transformar(gm, M4([0, r * .04, 0], [0, (i + r * .5) / n * Math.PI * 2 + R() * .3, elev]));
    gs.push(gm);
  }
  malha(unir(gs), lapis({ cor: o.cor ?? PAL.folha, cor2: o.cor2 ?? '#a88a66', comp: 10, px: o.px ?? 4.3, amb: .38, dif: .75, brilho: o.brilho ?? 1 }), g);
  return g;
}
/** capim: lâminas finas e compridas (folhas longas da frente). o: {x,y,z,n,alt,cor} */
export function capim(S, o = {}) {
  const R = rng(o.semente ?? 71), g = new THREE.Group(); g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); S.scene.add(g);
  const T = [];
  for (let i = 0; i < (o.n ?? 6); i++) {
    const a = (R() - .5) * 1.6, h = (o.alt ?? 1.2) * lerp(.6, 1.1, R()), w = .05 + R() * .03, x = (R() - .5) * .4, b = (R() - .5) * .5;
    const tip = [x + Math.sin(a) * h, Math.cos(a) * h, b * .3], mid = [x + Math.sin(a) * h * .5 + .05, Math.cos(a) * h * .55, 0];
    T.push([[x - w, 0, 0], [x + w, 0, 0], mid], [[x - w, 0, 0], mid, tip], [[x + w, 0, 0], tip, mid]);
  }
  malha(facetar(tris(T), { eixo: [0, 1, 0], jit: .2, semente: o.semente ?? 71 }), lapis({ cor: o.cor ?? PAL.musgo, cor2: '#7a8a6a', comp: 16, px: 4.3, amb: .35, dif: .7 }), g);
  return g;
}
/** pedra(s) facetadas. o: {x,y,z,r,achatar,cor,rot} */
export function pedra(S, o = {}) {
  const gm = facetar(pedraGeo(o), { eixo: [1, 0, .2], jit: 1.4, semente: o.semente ?? 3 });
  const m = malha(gm, lapis({ cor: o.cor ?? PAL.pedra, cor2: o.cor2 ?? '#b0a0c8', comp: 9, px: o.px ?? 4.3, amb: .45, dif: .7 }), o.pai ?? S.scene);
  m.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); m.rotation.y = o.rot ?? 0; return m;
}
/** peixe low-poly com olho claro grande. o: {x,y,z,tam,cor,rot,semente} → grupo com .rabo e .fase */
export function peixe(S, o = {}) {
  const s = o.tam ?? 1, g = new THREE.Group(); g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); g.rotation.y = o.rot ?? 0; S.scene.add(g);
  const corpo = loft([{ p: [-.17 * s, 0, 0], w: .02 * s, h: .04 * s }, { p: [-.05 * s, 0, 0], w: .08 * s, h: .15 * s }, { p: [.07 * s, .005 * s, 0], w: .075 * s, h: .13 * s }, { p: [.17 * s, -.01 * s, 0], w: .015 * s, h: .03 * s }], { forma: FORMA.losango, cima: [0, 1, 0] });
  const mat = lapis({ cor: o.cor ?? PAL.peixe, cor2: '#e0b8a0', comp: 7, px: 3.7, amb: .5, dif: .6, prof: o.prof ?? 0 });
  malha(facetar(corpo, { eixo: [1, 0, 0], jit: .5, semente: o.semente ?? 3 }), mat, g);
  const rabo = new THREE.Group(); rabo.position.set(-.16 * s, 0, 0); g.add(rabo);
  malha(facetar(tris([[[0, 0, 0], [-.12 * s, .08 * s, 0], [-.1 * s, 0, .005]], [[0, 0, 0], [-.1 * s, 0, .005], [-.12 * s, -.07 * s, 0]]]), { eixo: [1, 0, 0], jit: .4 }), mat, rabo);
  // olho: anel claro + pupila (dos dois lados)
  for (const lado of [1, -1]) {
    const olho = new THREE.Mesh(new THREE.CircleGeometry(.032 * s, 10), new THREE.MeshBasicMaterial({ color: '#cbbf96', side: THREE.DoubleSide }));
    olho.position.set(.085 * s, .018 * s, lado * .036 * s); olho.rotation.y = lado > 0 ? 0 : Math.PI; g.add(olho);
    const pu = new THREE.Mesh(new THREE.CircleGeometry(.014 * s, 8), new THREE.MeshBasicMaterial({ color: '#2a1a12', side: THREE.DoubleSide }));
    pu.position.set(.088 * s, .018 * s, lado * .039 * s); pu.rotation.y = olho.rotation.y; g.add(pu);
  }
  g.userData = { rabo, fase: (o.semente ?? 1) * 1.7, base: g.position.clone(), rot: g.rotation.y };
  return g;
}
/** balanço de peixe a 10 qps (parado no lugar, rabo batendo, deriva curta) */
export function nadar(p, t, k = 1) {
  const u = p.userData, f = u.fase;
  p.rotation.y = u.rot + Math.sin(t * 2.3 + f) * .14 * k;
  p.userData.rabo.rotation.y = Math.sin(t * 9 + f) * .5 * k;
  p.position.x = u.base.x + Math.sin(t * .9 + f) * .05 * k; p.position.y = u.base.y + Math.sin(t * 1.3 + f * 2) * .025 * k;
}

// ───────────────────────── a onça (rig simples por grupos) ─────────────────────────
/**
 * onca(S, { prof, cor, escala }) → { g, P (partes), pose(estado) }
 * Construída virada para +x, patas no chão em y=0. Partes: corpo, pescoco, cabeca, patas[4] {coxa, canela}, cauda[].
 * pose({ passo, andar(0..1), agachar(0..1), pescoco, cabecaY, cabecaX, piscar(0..1), cauda, brilhoOlho })
 */
export function onca(S, o = {}) {
  const s = o.escala ?? 1, g = new THREE.Group(); S.scene.add(g);
  const prof = o.prof ?? 0;
  const pele = (extra = {}) => lapis(Object.assign({ cor: o.cor ?? PAL.onca, cor2: PAL.oncaClara, comp: 5, px: o.px ?? 4.5, prof, amb: .5, dif: .85, manchas: [1, .17 * s, .33, 1], var: .35 }, extra));
  const mCorpo = pele(), mPata = pele({ manchas: [2, .08 * s, .27, 0] }), mCab = pele({ manchas: [2, .055 * s, .24, 1] }), mCauda = pele({ manchas: [2, .09 * s, .3, 0] });
  const mats = [mCorpo, mPata, mCab, mCauda];
  const raiz = new THREE.Group(); g.add(raiz);            // raiz: sobe/desce (balanço) e inclina (agachar)
  const corpo = new THREE.Group(); raiz.add(corpo);
  const S_ = v => v * s;
  // corpo: garupa → quadril → cintura recolhida → peito fundo → ombro alto → raiz do pescoço
  malha(facetar(loft([
    { p: [S_(-.6), S_(.66), 0], w: S_(.3), h: S_(.34) }, { p: [S_(-.47), S_(.67), 0], w: S_(.46), h: S_(.5) }, { p: [S_(-.12), S_(.63), 0], w: S_(.44), h: S_(.42) },
    { p: [S_(.24), S_(.6), 0], w: S_(.5), h: S_(.6) }, { p: [S_(.44), S_(.66), 0], w: S_(.46), h: S_(.58) }, { p: [S_(.57), S_(.76), 0], w: S_(.34), h: S_(.38) }], { forma: FORMA.caixa, dir: [1, 0, 0] }),
  { eixo: [1, 0, 0], jit: .5, semente: 3 }), mCorpo, corpo);
  // pescoço + cabeça
  const pescoco = new THREE.Group(); pescoco.position.set(S_(.52), S_(.8), 0); corpo.add(pescoco);
  malha(facetar(loft([{ p: [0, 0, 0], w: S_(.34), h: S_(.36) }, { p: [S_(.2), S_(.02), 0], w: S_(.3), h: S_(.32) }], { forma: FORMA.caixa }), { eixo: [1, 0, 0], jit: .5, semente: 4 }), mCorpo, pescoco);
  const cabeca = new THREE.Group(); cabeca.position.set(S_(.2), S_(.02), 0); pescoco.add(cabeca);
  const H = v => S_(v * 1.18);           // a cabeça é desenhada numa escala própria (cabeça grande, típica da onça)
  malha(facetar(unir([
    // crânio → bochecha → plano do rosto (onde ficam os olhos) → focinho que salta para a frente
    loft([{ p: [H(-.04), 0, 0], w: H(.3), h: H(.28) }, { p: [H(.1), 0, 0], w: H(.41), h: H(.32) }, { p: [H(.17), -H(.01), 0], w: H(.39), h: H(.29) },
      { p: [H(.185), -H(.045), 0], w: H(.22), h: H(.17) }, { p: [H(.25), -H(.055), 0], w: H(.19), h: H(.14) }, { p: [H(.285), -H(.065), 0], w: H(.12), h: H(.1) }], { forma: FORMA.caixa, dir: [1, 0, 0] }),
    // orelhas: pirâmides baixas e largas
    ...[1, -1].map(z => tris([[[H(.0), H(.12), z * H(.04)], [H(.12), H(.12), z * H(.16)], [H(.04), H(.27), z * H(.15)]], [[H(.0), H(.12), z * H(.04)], [H(.04), H(.27), z * H(.15)], [H(-.06), H(.11), z * H(.15)]], [[H(.12), H(.12), z * H(.16)], [H(-.06), H(.11), z * H(.15)], [H(.04), H(.27), z * H(.15)]]])),
  ]), { eixo: [1, 0, 0], jit: .6, semente: 5 }), mCab, cabeca);
  // focinho escuro + olhos (amêndoa clara com pupila) — olho brilha à noite (brilhoOlho)
  const nariz = new THREE.Mesh(tris([[[H(.292), -H(.03), -H(.045)], [H(.292), -H(.03), H(.045)], [H(.295), -H(.085), 0]]]), new THREE.MeshBasicMaterial({ color: '#2a140a', side: THREE.DoubleSide })); cabeca.add(nariz);
  const olhos = [];
  for (const z of [1, -1]) {
    const go = new THREE.Group(); go.position.set(H(.196), H(.045), z * H(.122)); go.rotation.y = z * -.2; cabeca.add(go);
    const am = new THREE.Mesh(tris([[[0, 0, -H(.035)], [0, H(.02), 0], [0, 0, H(.035)]], [[0, 0, -H(.035)], [0, 0, H(.035)], [0, -H(.017), 0]]]), new THREE.MeshBasicMaterial({ color: PAL.olho, side: THREE.DoubleSide }));
    const pu = new THREE.Mesh(tris([[[H(.002), -H(.015), -H(.006)], [H(.002), H(.017), 0], [H(.002), -H(.015), H(.006)]]]), new THREE.MeshBasicMaterial({ color: '#160b05', side: THREE.DoubleSide }));
    go.add(am, pu); olhos.push({ go, am });
  }
  // patas grossas: [x, z, traseira?]
  const patas = [];
  for (const [x, z, tras] of [[.4, .15, 0], [.4, -.15, 0], [-.44, .16, 1], [-.44, -.16, 1]]) {
    const coxa = new THREE.Group(); coxa.position.set(S_(x), S_(tras ? .62 : .54), S_(z)); corpo.add(coxa);
    const L1 = tras ? .3 : .27, L2 = tras ? .25 : .24;
    malha(facetar(loft(tras ? [{ p: [0, S_(.06), 0], w: S_(.2), h: S_(.36) }, { p: [S_(.05), -S_(L1 * .55), 0], w: S_(.18), h: S_(.26) }, { p: [S_(.04), -S_(L1), 0], w: S_(.13), h: S_(.15) }]
      : [{ p: [0, S_(.06), 0], w: S_(.19), h: S_(.27) }, { p: [0, -S_(L1), 0], w: S_(.15), h: S_(.17) }], { forma: FORMA.hex, cima: [1, 0, 0] }), { eixo: [0, 1, 0], jit: .4, semente: 9 }), mPata, coxa);
    const canela = new THREE.Group(); canela.position.set(S_(tras ? .04 : 0), -S_(L1), 0); coxa.add(canela);
    malha(facetar(unir([loft([{ p: [0, 0, 0], w: S_(.13), h: S_(.15) }, { p: [S_(tras ? -.03 : 0), -S_(L2), 0], w: S_(.12), h: S_(.13) }], { forma: FORMA.hex, cima: [1, 0, 0] }),
      loft([{ p: [S_(tras ? -.07 : -.06), -S_(L2 + .015), 0], w: S_(.15), h: S_(.08) }, { p: [S_(tras ? .08 : .1), -S_(L2 + .025), 0], w: S_(.15), h: S_(.065) }], { forma: FORMA.caixa })]),
    { eixo: [0, 1, 0], jit: .4, semente: 10 }), mPata, canela);
    patas.push({ coxa, canela, tras, lado: z > 0 ? 1 : -1 });
  }
  // cauda: corrente de segmentos (curva em S para cima)
  const cauda = []; let pai = corpo, px = S_(-.6), py = S_(.76);
  for (let i = 0; i < 9; i++) {
    const seg = new THREE.Group(); seg.position.set(px, py, 0); pai.add(seg);
    const r = S_(lerp(.075, .045, i / 8)), L = S_(.115);
    malha(facetar(loft([{ p: [0, 0, 0], w: r, h: r }, { p: [-L, 0, 0], w: r * .9, h: r * .9 }], { forma: FORMA.pent }), { eixo: [1, 0, 0], jit: .3, semente: 20 + i }), mCauda, seg);
    cauda.push(seg); pai = seg; px = -L; py = 0;
  }
  const P = { raiz, corpo, pescoco, cabeca, patas, cauda, olhos, mats };
  /** estado da pose (todas as chaves opcionais) */
  function pose(e = {}) {
    const ph = (e.passo ?? 0) * Math.PI * 2, an = e.andar ?? 0, ag = e.agachar ?? 0;
    raiz.position.y = S_(Math.abs(Math.sin(ph)) * .025 * an - .1 * ag);
    raiz.rotation.z = -.2 * ag + Math.sin(ph * 2) * .015 * an;
    // pernas: andar lateral (TE 0, DE .25, TD .5, DD .75)
    const off = [.25, .75, 0, .5];
    patas.forEach((p, i) => {
      const f = ph + off[i] * Math.PI * 2, sw = Math.sin(f), lift = Math.max(0, Math.cos(f));
      if (p.tras) { p.coxa.rotation.z = (sw * .42) * an + .18 * ag; p.canela.rotation.z = (-.15 - lift * .55) * an - .1 * ag; }
      else { p.coxa.rotation.z = (sw * .4) * an + .38 * ag; p.canela.rotation.z = (lift * .6) * an + -.42 * ag; }
      p.coxa.rotation.x = p.lado * .04 * ag;
    });
    pescoco.rotation.z = (e.pescoco ?? 0) + Math.sin(ph * 2) * .03 * an;
    cabeca.rotation.z = e.cabecaX ?? 0; cabeca.rotation.y = e.cabecaY ?? 0;
    const cb = e.cauda ?? 0;
    cauda.forEach((c, i) => { c.rotation.z = (i === 0 ? 1.0 : i < 4 ? -.3 : -.2 + (i > 6 ? -.25 : 0)) + Math.sin(ph + i * .6) * .06 * an + Math.sin((e.t ?? 0) * 1.6 + i * .7) * .05 + cb * (i > 3 ? .1 : 0); c.rotation.y = Math.sin((e.t ?? 0) * 1.1 + i * .5) * .05; });
    const pis = clamp(e.piscar ?? 0); olhos.forEach(ol => { ol.go.scale.y = Math.max(.08, 1 - pis); ol.am.material.color.set(e.brilhoOlho ? new THREE.Color(PAL.olho).lerp(new THREE.Color(PAL.olhoNoite).multiplyScalar(1.6), e.brilhoOlho) : PAL.olho); });
    for (const m of mats) m.uniforms.uBrilho.value = e.luz ?? 1;
  }
  pose({});
  return { g, P, pose };
}

// ───────────────────────── texto a lápis (camada 2D por cima) ─────────────────────────
/**
 * textoLapis({ texto, fonte, x, y, cor, sombra, ang, esp, comp:[a,b], larg, semente, w, h, base })
 * Letras preenchidas com o mesmo traço do 3D (hachura em ângulo sobre uma base mais escura), reveladas traço a traço.
 * Crie no SETUP (depois das fontes). Chame .desenhar(p) com p ∈ [0,1] (quantize o tempo antes!).
 */
export function textoLapis(o) {
  const W = o.w ?? 1000, H = o.h ?? 220, cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  Object.assign(cv.style, { position: 'absolute', left: (o.x - W / 2) + 'px', top: (o.y - H / 2) + 'px', pointerEvents: 'none' });
  (o.pai ?? document.getElementById('stage')).appendChild(cv);
  const ctx = cv.getContext('2d'), mk = document.createElement('canvas'); mk.width = W; mk.height = H;
  const m = mk.getContext('2d'); m.font = o.fonte; m.textAlign = 'center'; m.textBaseline = 'middle';
  if (o.espaco) m.letterSpacing = o.espaco + 'px';
  m.fillStyle = '#fff'; m.fillText(o.texto, W / 2, H / 2);
  const md = m.getImageData(0, 0, W, H).data, alfa = (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? 0 : md[(Math.floor(y) * W + Math.floor(x)) * 4 + 3];
  let x0 = W, x1 = 0; for (let y = 0; y < H; y += 2) for (let x = 0; x < W; x += 2) if (alfa(x, y) > 10) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); }
  const R = rng(o.semente ?? 3), ang = o.ang ?? -.42, ca = Math.cos(ang), sa = Math.sin(ang), esp = o.esp ?? 3.6, cmp = o.comp ?? [10, 30], diag = Math.hypot(W, H) / 2, tr = [];
  for (let v = -diag; v < diag; v += esp) {
    let u = -diag + R() * 12;
    while (u < diag) {
      const L = lerp(cmp[0], cmp[1], R()), gap = 1 + R() * 3.5, vv = v + (R() - .5) * esp * .35;
      const ax = W / 2 + ca * u - sa * vv, ay = H / 2 + sa * u + ca * vv, bx = W / 2 + ca * (u + L) - sa * vv, by = H / 2 + sa * (u + L) + ca * vv;
      if (alfa(ax, ay) + alfa((ax + bx) / 2, (ay + by) / 2) + alfa(bx, by) > 0) tr.push({ ax, ay, bx, by, b: lerp(.72, 1.12, R()), w: (o.larg ?? 2.1) * lerp(.7, 1.25, R()), r: ((ax + bx) / 2 - x0) / Math.max(1, x1 - x0) * .85 + R() * .15 });
      u += L + gap;
    }
  }
  const base = o.base ?? .55, cor = new THREE.Color(o.cor ?? PAL.creme), off = document.createElement('canvas'); off.width = W; off.height = H; const oc = off.getContext('2d');
  const rgb = k => `rgb(${Math.round(clamp(cor.r * k) * 255)},${Math.round(clamp(cor.g * k) * 255)},${Math.round(clamp(cor.b * k) * 255)})`;
  let ultimo = -1;
  function desenhar(p) {
    p = clamp(p); if (p === ultimo) return; ultimo = p;
    ctx.clearRect(0, 0, W, H); oc.clearRect(0, 0, W, H); if (p <= 0) return;
    const lim = x0 + (x1 - x0 + 40) * p - 20;
    // base escura (dá corpo à letra) revelada junto com os traços
    oc.save(); oc.beginPath(); oc.rect(0, 0, lim, H); oc.clip(); oc.globalAlpha = base; oc.drawImage(mk, 0, 0); oc.globalCompositeOperation = 'source-in'; oc.fillStyle = rgb(.55); oc.fillRect(0, 0, W, H); oc.restore();
    oc.lineCap = 'round';
    for (const t of tr) { if (t.r > p) continue; oc.strokeStyle = rgb(t.b); oc.lineWidth = t.w; oc.beginPath(); oc.moveTo(t.ax, t.ay); oc.lineTo(t.bx, t.by); oc.stroke(); }
    oc.globalCompositeOperation = 'destination-in'; oc.drawImage(mk, 0, 0); oc.globalCompositeOperation = 'source-over';
    if (o.sombra !== false) { ctx.save(); ctx.filter = `blur(${o.sombraBlur ?? 14}px)`; ctx.globalAlpha = .75 * p; ctx.drawImage(mk, 0, 4); ctx.globalCompositeOperation = 'source-in'; ctx.fillStyle = o.sombra ?? '#05070a'; ctx.fillRect(0, 0, W, H); ctx.restore(); }
    ctx.drawImage(off, 0, 0);
  }
  return { cv, desenhar, larg: x1 - x0 };
}

// ───────────────────────── ondas quadradas na água ─────────────────────────
/** dispara/atualiza a onda k (0–3): centro (x,z) no mundo, início t0 (s), força 0–1 */
export function anel(k, x, z, t0, forca = 1) { U.aneis.value[k].set(x, z, t0, forca); }
