// maquete.js — biblioteca do estilo "maquete 3D semi-realista" (three.js, módulo ES)
// Um BLOCO de diorama (estratos de terra cortados nas laterais) flutuando num estúdio creme infinito,
// visto de cima em 3/4 com perspectiva leve; materiais PBR procedurais (ladrilho, azulejo, madeira, inox,
// vidro, água), bonecos de maquete semi-realistas com ações animadas, luz de estúdio + AO + sombra macia,
// órbita lenta de câmera e HUD editorial (versalete, título serifado em itálico, painel claro, dados em mono).
// Uso na página:  import * as M from '../../lib/maquete.js';  window.SETUP = async () => { const S = M.palco({...}); ... }
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
export { THREE };

// ───────────────────────── paleta (amostrada da referência + Brasil) ─────────────────────────
export const PAL = {
  estudio: '#ECEAE4', estudio2: '#E2DFD8',                 // fundo creme (topo → base)
  tinta: '#1f1d1a', tinta2: '#5f5b54', tinta3: '#8f8a80', fio: '#d9d5cb', papel: '#f7f6f2', acento: '#c2502e',
  corte: '#3b3631',                                          // topo das paredes cortadas (poché)
  concreto: '#cfcac0', contrapiso: '#b8b0a3', terra: '#9a4a2e', argila: '#c26d3d', areia: '#d9bb8b', brita: '#8e8982', rocha: '#4b4039',
  madeira: '#9c6b43', madeiraClara: '#c89c6d', inox: '#c9cdd1', ferro: '#2c2b2a', branco: '#f3f2ee',
  verdeAgua: '#9ccfbf', amareloBR: '#f2c53d', verdeBR: '#2f8f5b', azulBR: '#2f6db3', vermelho: '#c3372c', terracota: '#b5533c',
  asfalto: '#4a4a4c', guia: '#bdb8ae',
};
/** tons de pele (claro → escuro) e cabelos */
export const PELE = ['#f2cba9', '#e3b089', '#c98f66', '#a86e48', '#7f4c2f', '#5b3622'];
export const CABELO = ['#17120f', '#3a2517', '#6a4427', '#a37a4c', '#b9b0a4'];

// ───────────────────────── utilidades determinísticas ─────────────────────────
export function rng(seed = 1) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const PERM = (() => { const r = rng(1337), p = [...Array(256).keys()]; for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; } return Uint8Array.from([...p, ...p]); })();
const GX = new Float32Array(256), GY = new Float32Array(256);
for (let i = 0; i < 256; i++) { const a = i / 256 * Math.PI * 2; GX[i] = Math.cos(a); GY[i] = Math.sin(a); }
/** ruído de gradiente 2D em ~[-1,1] */
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
/** progresso 0→1 de t na janela [t0,t1] com ease do GSAP */
export const fase = (t, t0, t1, ease = 'none') => gsap.parseEase(ease)(clamp((t - t0) / (t1 - t0)));
/** ângulo de um ciclo de período T (use períodos que dividem a duração → loop perfeito) */
export const ciclo = (t, T, f = 0) => 2 * Math.PI * (t / T + f);
const h2 = (x, y) => { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); };
const V3 = a => (a && a.isVector3) ? a.clone() : new THREE.Vector3(...a);
export const v3 = V3;
const SRGB = THREE.SRGBColorSpace;

// ───────────────────────── palco: renderer + estúdio + AO + sombra macia ─────────────────────────
const QUAD_VERT = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
const ACAB_FRAG = `uniform sampler2D tDiffuse; uniform float uTime, uGrain, uVig; uniform vec2 uRes; varying vec2 vUv;
float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void main(){ vec2 c = vUv - .5; c.x *= uRes.x / uRes.y; float d = length(c);
  vec3 col = texture2D(tDiffuse, vUv).rgb;
  col *= 1. - uVig * smoothstep(.35, 1.05, d);
  col += (h(vUv * uRes + fract(uTime * 7.13) * 100.) - .5) * uGrain;
  gl_FragColor = vec4(col, 1.); }`;

// Neutral tone mapping (o mesmo do three) — usado para achar a cor linear que sai EXATAMENTE no creme do fundo
function neutral(c) {
  const x = Math.min(...c), off = x < .08 ? x - 6.25 * x * x : .04; c = c.map(v => v - off);
  const peak = Math.max(...c), sc = .76; if (peak < sc) return c;
  const d = 1 - sc, np = 1 - d * d / (peak + d - sc); c = c.map(v => v * np / peak);
  const g = 1 - 1 / (.15 * (peak - np) + 1); return c.map(v => lerp(v, np, g));
}
function inverterTom(hex, expo = 1) {
  const alvo = new THREE.Color(hex); const T = [alvo.r, alvo.g, alvo.b]; let L = [...T];
  for (let i = 0; i < 80; i++) { const o = neutral(L.map(v => v * expo)); L = L.map((v, k) => Math.max(0, v + (T[k] - o[k]) * 1.3)); }
  return L;
}
/** fundo de estúdio: gradiente vertical em cor linear pré-compensada (sai igual ao hex depois do tone mapping) */
function fundoEstudio(cores, expo) {
  const n = 256, data = new Float32Array(n * 4), L = cores.map(c => inverterTom(c, expo));
  for (let i = 0; i < n; i++) {
    const k = i / (n - 1) * (L.length - 1), a = Math.floor(Math.min(k, L.length - 2)), f = k - a;     // i=0 → base da tela
    const c = L[L.length - 1 - a].map((v, j) => lerp(v, L[L.length - 2 - a][j], f));
    data.set([...c, 1], i * 4);
  }
  const tx = new THREE.DataTexture(data, 1, n, THREE.RGBAFormat, THREE.FloatType); tx.magFilter = tx.minFilter = THREE.LinearFilter; tx.needsUpdate = true; return tx;
}

/**
 * Palco do estilo. o: {fundo:[topo, base], exposicao, fov, ambiente (força do IBL), sol:{dir,forca,cor,raio},
 *   chao (y do chão infinito), sombraChao (opacidade), ao:{raio, forca}, grao, vinheta, raioSombra}
 * Devolve S = {scene, camera, renderer, composer, sol, ao, update(t) (você define), hud:[], sombra(centro, raio)}.
 */
export function palco(o = {}) {
  const V = window.VIDEO;
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  const expo = o.exposicao ?? 1;
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = expo;
  renderer.outputColorSpace = SRGB;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.VSMShadowMap;
  renderer.domElement.className = 'layer';
  (o.parent || document.getElementById('stage')).prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = fundoEstudio(o.fundo || [PAL.estudio, PAL.estudio2], expo);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture; scene.environmentIntensity = o.ambiente ?? .85;
  const camera = new THREE.PerspectiveCamera(o.fov ?? 28, V.w / V.h, .5, 300);

  // luz de estúdio: IBL (sala branca) + sol com sombra VSM macia + preenchimento quente
  const sol = new THREE.DirectionalLight(o.sol?.cor || '#fff4e6', o.sol?.forca ?? 2.1);
  sol.castShadow = true; sol.shadow.mapSize.set(2048, 2048); sol.shadow.radius = o.sol?.raio ?? 9; sol.shadow.blurSamples = 16;
  sol.shadow.bias = -.0006; sol.shadow.normalBias = .015;
  scene.add(sol, sol.target);
  const hemi = new THREE.HemisphereLight('#fffaf3', '#cfc6b8', o.hemi ?? .35); scene.add(hemi);
  const dirSol = V3(o.sol?.dir || [-.55, 1, .5]).normalize();

  // chão infinito: só recebe sombra (o creme é o próprio fundo)
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.ShadowMaterial({ color: '#3b3024', opacity: o.sombraChao ?? .32 }));
  chao.rotation.x = -Math.PI / 2; chao.position.y = o.chao ?? -2; chao.receiveShadow = true; chao.userData.ao = true; scene.add(chao);

  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(V.w, V.h, { type: THREE.HalfFloatType, samples: 4 }));
  composer.setPixelRatio(1); composer.setSize(V.w, V.h);
  composer.addPass(new RenderPass(scene, camera));
  const mr = Math.random; Math.random = rng(77);                        // GTAO sorteia o ruído do denoise: fixa a semente
  const ao = new GTAOPass(scene, camera, V.w, V.h); Math.random = mr;
  ao.updateGtaoMaterial({ radius: o.ao?.raio ?? .35, distanceExponent: 1.4, thickness: 1, scale: 1, samples: 16, distanceFallOff: 1 });
  ao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
  ao.blendIntensity = o.ao?.forca ?? .9;
  // AO só nas superfícies opacas: sprites (vapor), vidro e água ficam fora (senão viram quadrados escuros)
  ao._overrideVisibility = function () { scene.traverse(x => { if ((x.isPoints || x.isLine || x.isSprite || (x.isMesh && x.material?.transparent && !x.userData.ao)) && x.visible) { x.visible = false; this._visibilityCache.push(x); } }); };
  composer.addPass(ao);
  composer.addPass(new OutputPass());
  const acab = new ShaderPass({ uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: o.grao ?? .012 }, uVig: { value: o.vinheta ?? .1 }, uRes: { value: new THREE.Vector2(V.w, V.h) } }, vertexShader: QUAD_VERT, fragmentShader: ACAB_FRAG });
  composer.addPass(acab);

  const S = {
    THREE, renderer, scene, camera, composer, sol, hemi, chao, ao, acab, update: null, hud: [], anima: [],
    /** move o sol (e a caixa de sombra) para cobrir a área de interesse */
    sombra(centro, raio = 10) {
      const c = V3(centro); sol.target.position.copy(c); sol.position.copy(c).addScaledVector(dirSol, raio * 3);
      const sc = sol.shadow.camera; sc.left = sc.bottom = -raio; sc.right = sc.top = raio; sc.near = .5; sc.far = raio * 7; sc.updateProjectionMatrix();
    },
    /** registra fn(t) chamada todo quadro (antes do S.update) — peças animadas se registram aqui */
    cada(fn) { S.anima.push(fn); return fn; },
  };
  S.sombra([0, 0, 0], o.raioSombra ?? 10);
  onTick(t => {
    acab.uniforms.uTime.value = t;
    for (const f of S.anima) f(t);
    if (S.update) S.update(t);
    camera.updateMatrixWorld();
    for (const h of S.hud) h(t);
    composer.render();
  });
  return S;
}

// ───────────────────────── texturas procedurais (canvas) ─────────────────────────
const TX = new Map();
export function tela2d(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); return c; }
/** CanvasTexture pronta: repetição, sRGB, anisotropia */
export function textura(c, o = {}) {
  const t = new THREE.CanvasTexture(c); t.colorSpace = o.cor === false ? THREE.NoColorSpace : SRGB;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...(o.rep || [1, 1])); t.anisotropy = 8; return t;
}
/** clona uma textura com outra repetição (mesma imagem) */
export function repetir(tx, rx, ry) { const t = tx.clone(); t.repeat.set(rx, ry); t.needsUpdate = true; return t; }
function cache(k, f) { if (!TX.has(k)) TX.set(k, f()); return TX.get(k); }
/** mancha (variação de tom) por pixel: amp ~.06–.2, esc = tamanho da mancha em px */
export function manchar(g, w, h, amp = .1, esc = 40, seed = 1) {
  const im = g.getImageData(0, 0, w, h), d = im.data, r = rng(seed);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4, k = 1 + amp * fbm(x / esc + seed, y / esc) + (r() - .5) * amp * .5;
    d[i] = clamp(d[i] * k, 0, 255); d[i + 1] = clamp(d[i + 1] * k, 0, 255); d[i + 2] = clamp(d[i + 2] * k, 0, 255);
  }
  g.putImageData(im, 0, 0);
}
const tom = (hex, k) => { const c = new THREE.Color(hex); c.multiplyScalar(k); return '#' + c.getHexString(); };

export const tex = {
  /** ladrilho hidráulico (padrão de flor terracota + verde sobre creme). lado = tamanho da peça em m */
  ladrilho(o = {}) {
    const k = JSON.stringify(o); return cache('lad' + k, () => {
      const s = 128, n = 4, c1 = o.fundo || '#ebe0c8', c2 = o.cor1 || PAL.terracota, c3 = o.cor2 || '#2f4a40';
      const c = tela2d(s * n, s * n, (g) => {
        for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
          const x = i * s, y = j * s; g.save(); g.beginPath(); g.rect(x, y, s, s); g.clip();
          g.fillStyle = c1; g.fillRect(x, y, s, s);
          for (const [cx, cy] of [[x, y], [x + s, y], [x, y + s], [x + s, y + s]]) {
            g.fillStyle = c2; g.beginPath(); g.arc(cx, cy, s * .4, 0, 7); g.fill();
            g.fillStyle = c1; g.beginPath(); g.arc(cx, cy, s * .27, 0, 7); g.fill();
            g.fillStyle = c3; g.beginPath(); g.arc(cx, cy, s * .13, 0, 7); g.fill();
          }
          g.fillStyle = c3; g.translate(x + s / 2, y + s / 2);
          for (let a = 0; a < 4; a++) { g.rotate(Math.PI / 2); g.beginPath(); g.ellipse(0, -s * .17, s * .07, s * .17, 0, 0, 7); g.fill(); }
          g.fillStyle = c2; g.beginPath(); g.arc(0, 0, s * .06, 0, 7); g.fill();
          g.restore();
          g.strokeStyle = 'rgba(90,80,70,.55)'; g.lineWidth = 2; g.strokeRect(x + 1, y + 1, s - 2, s - 2);
        }
        manchar(g, s * n, s * n, .08, 60, 3);
      });
      return textura(c);
    });
  },
  /** piso/azulejo quadriculado: cor, rejunte, n peças por textura, faixa:{linha, cor} opcional */
  azulejo(o = {}) {
    const k = JSON.stringify(o); return cache('azu' + k, () => {
      const n = o.n ?? 8, s = 64, r = rng(o.seed ?? 5);
      const c = tela2d(s * n, s * (o.linhas ?? n), (g, w, h) => {
        g.fillStyle = o.rejunte || '#b9b6ae'; g.fillRect(0, 0, w, h);
        for (let i = 0; i < n; i++) for (let j = 0; j < (o.linhas ?? n); j++) {
          const linha = (o.linhas ?? n) - 1 - j, faixa = o.faixa && o.faixa.linhas.includes(linha);
          g.fillStyle = tom(faixa ? o.faixa.cor : (o.cor || '#f1f0eb'), .96 + r() * .06); g.fillRect(i * s + 2, j * s + 2, s - 4, s - 4);
        }
        manchar(g, w, h, .05, 30, 9);
      });
      return textura(c);
    });
  },
  /** pedra portuguesa em ondas (calçadão): faixa = largura da onda em m, px/m */
  pedraPortuguesa(o = {}) {
    return cache('pp' + JSON.stringify(o), () => {
      const W = 1024, pm = o.pxm ?? 256, faixa = o.faixa ?? .32, pedra = o.pedra ?? .05, cp = o.claro || '#ece8df', ce = o.escuro || '#2a2a2b';
      const c = tela2d(W, W, (g) => {
        const im = g.createImageData(W, W), d = im.data, A = new THREE.Color(cp), B = new THREE.Color(ce), R = new THREE.Color('#8d877c');
        const per = W / pm;                                                      // metros por textura (para a onda fechar no repeat)
        for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
          const u = x / pm, v = y / pm, cx = Math.floor(u / pedra + .5 * (Math.floor(v / pedra) % 2)), cy = Math.floor(v / pedra);
          const fx = u / pedra + .5 * (Math.floor(v / pedra) % 2) - cx, fy = v / pedra - cy;
          const jit = h2(cx, cy), borda = Math.min(fx, 1 - fx, fy, 1 - fy) < .09 + jit * .05;
          const uc = (cx + .5) * pedra, vc = (cy + .5) * pedra;
          const onda = Math.floor((vc + faixa * .55 * Math.sin(uc / per * Math.PI * 2 * Math.round(per / 1.1))) / faixa);
          const base = ((onda % 2) + 2) % 2 ? B : A, kk = .9 + jit * .16, col = borda ? R : base;
          const i = (y * W + x) * 4; d[i] = col.r * 255 * kk; d[i + 1] = col.g * 255 * kk; d[i + 2] = col.b * 255 * kk; d[i + 3] = 255;
        }
        g.putImageData(im, 0, 0);
      });
      return textura(c);
    });
  },
  /** asfalto com grão; faixa amarela/branca opcional */
  asfalto(o = {}) {
    return cache('asf' + JSON.stringify(o), () => {
      const c = tela2d(512, 512, (g, w, h) => {
        g.fillStyle = o.cor || PAL.asfalto; g.fillRect(0, 0, w, h);
        const r = rng(4); for (let i = 0; i < 9000; i++) { g.fillStyle = r() > .5 ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.12)'; g.fillRect(r() * w, r() * h, 1.5, 1.5); }
        manchar(g, w, h, .12, 70, 2);
      });
      return textura(c);
    });
  },
  /** madeira com veios (cor base) */
  madeira(o = {}) {
    return cache('mad' + JSON.stringify(o), () => {
      const c = tela2d(256, 256, (g, w, h) => {
        const im = g.createImageData(w, h), d = im.data, C = new THREE.Color(o.cor || PAL.madeira);
        for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
          const v = Math.sin((y / h * 18 + 2.2 * fbm(x / 90, y / 25, 2)) * Math.PI), k = .86 + .12 * v * v + .05 * ruido(x / 6, y / 2);
          const i = (y * w + x) * 4; d[i] = C.r * 255 * k; d[i + 1] = C.g * 255 * k; d[i + 2] = C.b * 255 * k; d[i + 3] = 255;
        }
        g.putImageData(im, 0, 0);
      });
      return textura(c);
    });
  },
  /** toalha xadrez (vichy) */
  xadrez(o = {}) {
    return cache('xad' + JSON.stringify(o), () => {
      const n = o.n ?? 8, s = 32, cor = new THREE.Color(o.cor || PAL.vermelho);
      const c = tela2d(n * s, n * s, (g, w, h) => {
        g.fillStyle = '#f4f1ea'; g.fillRect(0, 0, w, h);
        g.fillStyle = `rgba(${cor.r * 255 | 0},${cor.g * 255 | 0},${cor.b * 255 | 0},.55)`;
        for (let i = 0; i < n; i += 2) { g.fillRect(i * s, 0, s, h); g.fillRect(0, i * s, w, s); }
        manchar(g, w, h, .04, 20, 6);
      });
      return textura(c);
    });
  },
  /** parede pintada (cor) com rodapé; alt em m e px/m para o rodapé cair certo */
  pintura(o = {}) {
    return cache('pin' + JSON.stringify(o), () => {
      const pm = 128, H = Math.round((o.alt ?? 2.8) * pm), W = 256;
      const c = tela2d(W, H, (g) => {
        g.fillStyle = o.cor || PAL.verdeAgua; g.fillRect(0, 0, W, H);
        if (o.barra) { g.fillStyle = o.barra.cor; g.fillRect(0, H - o.barra.alt * pm, W, o.barra.alt * pm); g.fillStyle = 'rgba(0,0,0,.12)'; g.fillRect(0, H - o.barra.alt * pm, W, 2); }
        g.fillStyle = o.rodape || '#6c655c'; g.fillRect(0, H - .1 * pm, W, .1 * pm);
        manchar(g, W, H, .05, 50, 8);
      });
      return textura(c);
    });
  },
  /** quadro de giz com linhas de texto [{txt, tam (px), cor}] (precisa das fontes carregadas: chame dentro do SETUP) */
  giz(linhas, o = {}) {
    const W = o.w ?? 512, H = o.h ?? 384;
    const c = tela2d(W, H, (g) => {
      g.fillStyle = o.fundo || '#26302b'; g.fillRect(0, 0, W, H);
      manchar(g, W, H, .18, 40, 12);
      g.textAlign = 'center'; g.textBaseline = 'middle';
      let y = o.topo ?? H * .17;
      for (const l of linhas) {
        g.font = `${l.peso ?? 700} ${l.tam}px ${l.fonte || "'Geist'"}`; g.fillStyle = l.cor || 'rgba(245,242,232,.92)';
        g.save(); g.translate(W / 2, y); g.rotate(l.rot ?? -.015); g.fillText(l.txt, 0, 0); g.restore();
        y += l.tam * (l.esp ?? 1.32);
      }
      // grão de giz: apaga pontinhos
      const r = rng(31); g.globalCompositeOperation = 'destination-out';
      for (let i = 0; i < 2600; i++) { g.fillStyle = `rgba(0,0,0,${.25 + r() * .5})`; g.fillRect(r() * W, r() * H, 1.4, 1.4); }
      g.globalCompositeOperation = 'destination-over'; g.fillStyle = o.fundo || '#26302b'; g.fillRect(0, 0, W, H);
      g.globalCompositeOperation = 'source-over';
      if (o.moldura !== false) { g.strokeStyle = o.moldura || '#8a5a35'; g.lineWidth = W * .035; g.strokeRect(0, 0, W, H); }
    });
    return textura(c);
  },
  /** letreiro / placa: fundo, linhas de texto centralizadas */
  placa(linhas, o = {}) {
    const W = o.w ?? 1024, H = o.h ?? 256;
    const c = tela2d(W, H, (g) => {
      g.fillStyle = o.fundo || PAL.amareloBR; g.fillRect(0, 0, W, H);
      if (o.borda) { g.strokeStyle = o.borda; g.lineWidth = H * .06; g.strokeRect(H * .05, H * .05, W - H * .1, H - H * .1); }
      g.textAlign = 'center'; g.textBaseline = 'middle';
      for (const l of linhas) { g.font = `${l.estilo || ''} ${l.peso ?? 800} ${l.tam}px ${l.fonte || "'Geist'"}`; g.fillStyle = l.cor || PAL.vermelho; g.fillText(l.txt, W / 2, l.y * H); }
      manchar(g, W, H, .04, 60, 2);
    });
    return textura(c);
  },
  /** listras (toldo): cores alternadas */
  listras(cores, o = {}) {
    return cache('lis' + cores.join() + JSON.stringify(o), () => {
      const n = o.n ?? 8, s = 32;
      const c = tela2d(n * s, 64, (g, w, h) => { for (let i = 0; i < n; i++) { g.fillStyle = cores[i % cores.length]; g.fillRect(i * s, 0, s, h); } manchar(g, w, h, .05, 20, 4); });
      return textura(c);
    });
  },
  /** mancha macia radial (vapor, fumaça, sombra de contato) */
  macia(o = {}) {
    return cache('mac' + JSON.stringify(o), () => {
      const c = tela2d(128, 128, (g) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, `rgba(255,255,255,${o.a ?? 1})`); gr.addColorStop(.5, `rgba(255,255,255,${(o.a ?? 1) * .45})`); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); });
      return textura(c, { cor: false });
    });
  },
  /**
   * lateral de um estrato. tipo: 'concreto'|'contrapiso'|'terra'|'argila'|'areia'|'brita'|'rocha'|'asfalto'
   * larg/alt em m; o: {cor, corCima, canos:[{u (0–1), v (m a partir do topo do estrato), r, cor}], raizes, seed}
   */
  estrato(tipo, larg, alt, o = {}) {
    const pm = 150, W = Math.min(2048, Math.round(larg * pm)), H = Math.max(16, Math.round(alt * pm)), r = rng(o.seed ?? 7);
    const cor = o.cor || PAL[tipo] || '#a99';
    const c = tela2d(W, H, (g) => {
      g.fillStyle = cor; g.fillRect(0, 0, W, H);
      manchar(g, W, H, tipo === 'areia' ? .07 : .16, tipo === 'terra' ? 26 : 40, (o.seed ?? 7) + 3);
      const pedras = { concreto: [700, 1, 3, '#9b968e', '#e2ddd3'], contrapiso: [300, 1, 2.5, '#8f887d', '#d4cec4'], terra: [130, 2, 7, '#5c2c1b', '#b56a48'], argila: [80, 2, 6, '#8a4423', '#d98a58'], areia: [3000, .6, 1.3, '#a88b5f', '#efd9b0'], brita: [900, 2.5, 7, '#5e5953', '#b8b3ab'], rocha: [160, 4, 12, '#2f2723', '#6a5d55'], asfalto: [900, .8, 2, '#262627', '#77777a'] }[tipo];
      if (pedras) {
        const n = Math.round(pedras[0] * W * H / 60000);
        for (let i = 0; i < n; i++) {
          const x = r() * W, y = r() * H, s = lerp(pedras[1], pedras[2], r() ** 2);
          g.fillStyle = r() > .5 ? pedras[3] : pedras[4]; g.globalAlpha = .55 + r() * .45;
          g.beginPath(); g.ellipse(x, y, s * (1 + r() * .6), s, r() * 3, 0, 7); g.fill();
        }
        g.globalAlpha = 1;
      }
      if (o.raizes) {
        g.strokeStyle = 'rgba(70,40,25,.55)'; g.lineWidth = 1.4;
        for (let i = 0; i < o.raizes; i++) { let x = r() * W, y = 0; g.beginPath(); g.moveTo(x, y); for (let k = 0; k < 12; k++) { x += (r() - .5) * 14; y += r() * H * .09; g.lineTo(x, y); } g.stroke(); }
      }
      if (o.corCima) {                                                     // contato ondulado com a camada de cima
        g.fillStyle = o.corCima; g.beginPath(); g.moveTo(0, 0);
        for (let x = 0; x <= W; x += 6) g.lineTo(x, H * .06 + 3 + 5 * fbm(x / 45 + (o.seed ?? 7), 0, 2) + 2 * Math.sin(x / 17));
        g.lineTo(W, 0); g.fill();
      }
      for (const cn of o.canos || []) {                                   // seção de cano (esgoto, água, gás, conduíte)
        const x = cn.u * W, y = cn.v * pm, R = cn.r * pm;
        g.fillStyle = 'rgba(0,0,0,.25)'; g.beginPath(); g.arc(x + R * .12, y + R * .14, R * 1.08, 0, 7); g.fill();
        g.fillStyle = cn.cor || '#e7dcc3'; g.beginPath(); g.arc(x, y, R, 0, 7); g.fill();
        g.fillStyle = cn.dentro || '#2a2320'; g.beginPath(); g.arc(x, y, R * .74, 0, 7); g.fill();
        if (cn.agua) { g.fillStyle = 'rgba(80,150,210,.85)'; g.beginPath(); g.arc(x, y, R * .74, .25, Math.PI - .25); g.fill(); }
      }
    });
    return textura(c);
  },
};

// ───────────────────────── materiais PBR (cache por chave) ─────────────────────────
const MC = new Map();
/** material padrão: o: {rug, metal, mapa (textura), env, opac, lados, emis, emisForca, plano} */
export function mat(cor, o = {}) {
  const k = cor + JSON.stringify(o, (kk, v) => (v && v.isTexture) ? v.uuid : v); if (MC.has(k)) return MC.get(k);
  const m = new THREE.MeshStandardMaterial({
    color: cor, roughness: o.rug ?? .7, metalness: o.metal ?? 0, map: o.mapa || null, flatShading: o.plano ?? false,
    emissive: o.emis || '#000000', emissiveIntensity: o.emisForca ?? 1, envMapIntensity: o.env ?? 1,
    transparent: o.opac !== undefined && o.opac < 1, opacity: o.opac ?? 1, side: o.lados ? THREE.DoubleSide : THREE.FrontSide,
  });
  if (o.opac !== undefined && o.opac < 1) m.depthWrite = false;
  MC.set(k, m); return m;
}
const M = {
  pele: c => mat(c, { rug: .55 }),
  tecido: c => mat(c, { rug: .9 }),
  cabelo: c => mat(c, { rug: .55 }),
  plastico: c => mat(c, { rug: .35 }),
  ceramica: (c = '#f6f5f1') => mat(c, { rug: .18, env: 1.2 }),
  inox: (c = PAL.inox) => mat(c, { rug: .32, metal: .85, env: 1.3 }),
  aluminio: () => mat('#b9bcc0', { rug: .45, metal: .8, env: 1.2 }),
  ferro: () => mat(PAL.ferro, { rug: .6, metal: .5 }),
  madeira: (c = PAL.madeira) => mat('#ffffff', { rug: .62, mapa: tex.madeira({ cor: c }) }),
  vidro: (c = '#dfeff0', opac = .22) => { const k = 'vidro' + c + opac; if (MC.has(k)) return MC.get(k); const m = new THREE.MeshPhysicalMaterial({ color: c, roughness: .04, metalness: 0, transparent: true, opacity: opac, envMapIntensity: 1.6, depthWrite: false, side: THREE.DoubleSide }); MC.set(k, m); return m; },
  luz: (c, f = 1.6) => { const m = new THREE.MeshBasicMaterial({ color: new THREE.Color(c).multiplyScalar(f) }); return m; },
  corte: () => mat(PAL.corte, { rug: .9 }),
};
/** materiais prontos (pele, tecido, cabelo, plástico, cerâmica, inox, alumínio, ferro, madeira, vidro, luz, corte) */
export const MAT = M;
/** água com ondulação animada: devolve material com .atualizar(t) (já registrado se passar S) */
export function agua(S, o = {}) {
  const nm = cache('normAgua', () => {
    const W = 256, c = tela2d(W, W, (g) => {
      const im = g.createImageData(W, W), d = im.data; const f = (x, y) => fbm(x / 26, y / 26, 3);
      for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
        const dx = f(x + 1, y) - f(x - 1, y), dy = f(x, y + 1) - f(x, y - 1), i = (y * W + x) * 4;
        d[i] = 128 + dx * 500; d[i + 1] = 128 + dy * 500; d[i + 2] = 255; d[i + 3] = 255;
      }
      g.putImageData(im, 0, 0);
    });
    return textura(c, { cor: false });
  });
  const n1 = repetir(nm, o.rep ?? 2, o.rep ?? 2);
  const m = new THREE.MeshPhysicalMaterial({ color: o.cor || '#4f9fd6', roughness: .06, metalness: 0, transparent: true, opacity: o.opac ?? .7, normalMap: n1, normalScale: new THREE.Vector2(.6, .6), envMapIntensity: 1.5, depthWrite: false });
  m.atualizar = t => { n1.offset.set(t * .05 * (o.vel ?? 1), t * .033 * (o.vel ?? 1)); };
  if (S) S.cada(m.atualizar);
  return m;
}

// ───────────────────────── primitivas ─────────────────────────
export function malha(geo, material, o = {}) { const m = new THREE.Mesh(geo, material); m.castShadow = o.sombra ?? true; m.receiveShadow = o.recebe ?? true; return m; }
export function grupo(pai, x = 0, y = 0, z = 0) { const g = new THREE.Group(); g.position.set(x, y, z); if (pai) pai.add(g); return g; }
const matDe = (cor, o) => (cor && (cor.isMaterial || Array.isArray(cor))) ? cor : mat(cor || '#ccc', o?.mat);
/** caixa com chanfro leve. pos = centro da BASE [x,y,z] */
export function caixa(w, h, d, cor, o = {}) {
  const ch = o.chanfro ?? Math.min(w, h, d) * .06;
  const g = ch > 0 ? new RoundedBoxGeometry(w, h, d, 2, ch) : new THREE.BoxGeometry(w, h, d);
  const m = malha(g, matDe(cor, o), o);
  if (o.pos) m.position.set(o.pos[0], o.pos[1] + h / 2, o.pos[2]);
  return m;
}
/** caixa com mapa em metros (uv proporcional ao tamanho): tx = textura base, tam = tamanho da textura em m */
export function caixaTex(w, h, d, tx, tam = 1, o = {}) {
  const geo = new THREE.BoxGeometry(w, h, d), uv = geo.attributes.uv, nrm = geo.attributes.normal;
  for (let i = 0; i < uv.count; i++) {
    const nx = Math.abs(nrm.getX(i)), ny = Math.abs(nrm.getY(i));
    const [a, b] = nx > .5 ? [d, h] : ny > .5 ? [w, d] : [w, h];
    uv.setXY(i, uv.getX(i) * a / tam, uv.getY(i) * b / tam);
  }
  const m = malha(geo, o.material || mat('#ffffff', { mapa: tx, rug: o.rug ?? .6, env: o.env ?? 1 }), o);
  if (o.pos) m.position.set(o.pos[0], o.pos[1] + h / 2, o.pos[2]);
  return m;
}
export function cilindro(r, h, cor, o = {}) {
  const g = new THREE.CylinderGeometry(o.r2 ?? r, r, h, o.seg ?? 24, 1, o.aberto ?? false);
  const m = malha(g, matDe(cor, o), o); if (o.pos) m.position.set(o.pos[0], o.pos[1] + h / 2, o.pos[2]); return m;
}
export function bola(r, cor, o = {}) { const m = malha(new THREE.SphereGeometry(r, o.seg ?? 20, Math.round((o.seg ?? 20) * .7)), matDe(cor, o), o); if (o.pos) m.position.set(...o.pos); if (o.esc) m.scale.set(...o.esc); return m; }
/** placa plana com textura (letreiro, quadro, tela). Normal em +z */
export function plano(w, h, mapaOuMat, o = {}) {
  const m = malha(new THREE.PlaneGeometry(w, h), mapaOuMat.isMaterial ? mapaOuMat : mat('#ffffff', { mapa: mapaOuMat, rug: o.rug ?? .8, lados: o.lados }), { sombra: o.sombra ?? false, recebe: true });
  if (o.pos) m.position.set(...o.pos); if (o.rotY !== undefined) m.rotation.y = o.rotY; return m;
}

// ───────────────────────── o BLOCO de diorama ─────────────────────────
/**
 * Bloco com estratos cortados nas laterais. Topo em y = 0.
 * o: {x:[x0,x1], z:[z0,z1], estratos:[{h, tipo, cor, canos:{frente:[...], lado:[...]}, raizes}], seed}
 * Os estratos vão de cima para baixo. Canos: {u (0–1 ao longo da face), v (m abaixo do topo do estrato), r, cor, agua}.
 * Devolve Group com userData.base (y da base).
 */
export function bloco(o) {
  const [x0, x1] = o.x, [z0, z1] = o.z, w = x1 - x0, d = z1 - z0, g = new THREE.Group();
  let y = 0, ant = null;
  for (const [i, e] of o.estratos.entries()) {
    const cor = e.cor || PAL[e.tipo] || '#aaa', seed = (o.seed ?? 1) * 10 + i;
    const opZ = { cor, corCima: ant, seed, canos: e.canos?.frente, raizes: e.raizes }, opX = { cor, corCima: ant, seed: seed + 5, canos: e.canos?.lado, raizes: e.raizes };
    const tZ = tex.estrato(e.tipo, w, e.h, opZ), tX = tex.estrato(e.tipo, d, e.h, opX);
    const lat = (t) => mat('#ffffff', { mapa: t, rug: .92, env: .7 });
    const topo = mat(cor, { rug: .9 });
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, e.h, d), [lat(tX), lat(tX), topo, topo, lat(tZ), lat(tZ)]);
    m.position.set((x0 + x1) / 2, y - e.h / 2, (z0 + z1) / 2); m.castShadow = true; m.receiveShadow = true; g.add(m);
    y -= e.h; ant = cor;
  }
  g.userData.base = y;
  return g;
}

/** piso (placa fina) com textura em metros. regiao = [x0,z0,x1,z1], tam = metros por textura */
export function piso(regiao, tx, o = {}) {
  const [x0, z0, x1, z1] = regiao, h = o.h ?? .04;
  return caixaTex(x1 - x0, h, z1 - z0, tx, o.tam ?? 1, { pos: [(x0 + x1) / 2, o.y ?? 0, (z0 + z1) / 2], rug: o.rug ?? .55, env: o.env, sombra: false });
}
/**
 * parede reta de [xa,za] a [xb,zb]. o: {h, esp, dentro (material ou textura da face +normal), fora, tam (m/textura), corte (cor do topo)}
 * A face "dentro" fica à DIREITA de quem anda de a para b. Topo pintado com a cor de corte (poché).
 */
export function parede(a, b, o = {}) {
  const h = o.h ?? 2.8, e = o.esp ?? .15, dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz);
  const geo = new THREE.BoxGeometry(L, h, e), uv = geo.attributes.uv, nrm = geo.attributes.normal, tam = o.tam ?? 1;
  for (let i = 0; i < uv.count; i++) { const nx = Math.abs(nrm.getX(i)); if (Math.abs(nrm.getZ(i)) > .5) uv.setXY(i, uv.getX(i) * L / tam, uv.getY(i)); else if (nx > .5) uv.setXY(i, uv.getX(i) * e / tam, uv.getY(i)); }
  const fm = v => !v ? mat(PAL.branco, { rug: .85 }) : v.isMaterial ? v : mat('#ffffff', { mapa: v, rug: .8 });
  const lado = mat(o.lado || '#d9d4ca', { rug: .85 });
  const m = new THREE.Mesh(geo, [lado, lado, mat(o.corte || PAL.corte, { rug: .9 }), lado, fm(o.dentro), fm(o.fora)]);
  m.castShadow = m.receiveShadow = true;
  m.position.set((a[0] + b[0]) / 2, (o.y ?? 0) + h / 2, (a[1] + b[1]) / 2); m.rotation.y = -Math.atan2(dz, dx);
  return m;
}

// ───────────────────────── móveis e objetos do restaurante ─────────────────────────
/** mesa quadrada; toalha xadrez opcional. o: {lado, alt, toalha (cor), madeira} */
export function mesa(o = {}) {
  const g = new THREE.Group(), L = o.lado ?? .8, A = o.alt ?? .75;
  if (o.toalha) {
    const t = tex.xadrez({ cor: o.toalha }); const mt = mat('#ffffff', { mapa: t, rug: .9 });
    g.add(caixa(L + .04, .02, L + .04, mt, { pos: [0, A - .02, 0], chanfro: .008 }));
    const saia = mat('#ffffff', { mapa: repetir(t, 1, .25), rug: .9 });
    for (const [x, z, w, d] of [[0, L / 2 + .02, L + .06, .012], [0, -L / 2 - .02, L + .06, .012], [L / 2 + .02, 0, .012, L + .06], [-L / 2 - .02, 0, .012, L + .06]]) g.add(caixa(w, .16, d, saia, { pos: [x, A - .17, z], chanfro: 0 }));
  } else g.add(caixa(L, .04, L, M.madeira(o.madeira), { pos: [0, A - .04, 0], chanfro: .01 }));
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) g.add(cilindro(.02, A - .04, M.ferro(), { pos: [sx * (L / 2 - .07), 0, sz * (L / 2 - .07)], seg: 8 }));
  return g;
}
/** cadeira (madeira ou plástico). Frente em +z (a pessoa senta olhando +z) */
export function cadeira(o = {}) {
  const g = new THREE.Group(), m = o.plastico ? M.plastico(o.cor || PAL.vermelho) : M.madeira(o.cor || PAL.madeiraClara);
  g.add(caixa(.42, .04, .42, m, { pos: [0, .44, 0], chanfro: .012 }));
  g.add(caixa(.42, .42, .035, m, { pos: [0, .48, -.2], chanfro: .012 }));
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) g.add(caixa(.035, .44, .035, m, { pos: [sx * .18, 0, sz * .18], chanfro: .006 }));
  return g;
}
/** prato feito: arroz, feijão, bife, salada, fritas (sobre prato branco) */
export function pf(o = {}) {
  const g = new THREE.Group(), r = o.r ?? .12;
  g.add(cilindro(r, .014, M.ceramica(), { pos: [0, 0, 0], r2: r * 1.05, seg: 28 }));
  g.add(bola(r * .42, mat('#f4f1e6', { rug: .9 }), { pos: [-r * .35, .014, -r * .2], esc: [1, .38, 1] }));                 // arroz
  g.add(bola(r * .36, mat('#4a2a1c', { rug: .4 }), { pos: [r * .1, .014, -r * .42], esc: [1, .3, 1] }));                    // feijão
  g.add(bola(r * .38, mat('#7b4426', { rug: .6 }), { pos: [r * .3, .02, r * .22], esc: [1.25, .28, .85] }));                // bife
  g.add(bola(r * .22, mat('#5f9a3a', { rug: .8 }), { pos: [-r * .32, .016, r * .4], esc: [1, .5, 1] }));                    // salada
  g.add(bola(r * .1, mat('#d03a2a', { rug: .5 }), { pos: [-r * .2, .03, r * .52] }));                                        // tomate
  for (let i = 0; i < 4; i++) { const b = caixa(.012, .012, r * .45, mat('#e8b84a', { rug: .7 }), { chanfro: 0 }); b.position.set(r * (.05 + i * .06), .03, r * .52); b.rotation.y = .5 + i * .2; g.add(b); }
  return g;
}
/** copo americano (vidro) com bebida */
export function copo(cor = '#c97a2b') { const g = new THREE.Group(); g.add(cilindro(.026, .08, M.vidro('#e8f2f2', .35), { pos: [0, 0, 0], r2: .03, seg: 12 })); g.add(cilindro(.023, .055, mat(cor, { rug: .2 }), { pos: [0, .004, 0], r2: .026, seg: 12, sombra: false })); return g; }
/** garrafa (refrigerante/cerveja genérica) */
export function garrafa(cor = '#3f6b2f', o = {}) { const g = new THREE.Group(), h = o.h ?? .26; g.add(cilindro(.035, h * .62, mat(cor, { rug: .15, opac: o.opac }), { pos: [0, 0, 0], seg: 12 })); g.add(cilindro(.035, h * .38, mat(cor, { rug: .15 }), { pos: [0, h * .62, 0], r2: .013, seg: 12 })); g.add(cilindro(.015, .02, mat(o.tampa || '#d6c35a', { rug: .4, metal: .5 }), { pos: [0, h, 0], seg: 8 })); return g; }
/** salgados: 'coxinha' | 'pastel' | 'paoDeQueijo' | 'esfiha' */
export function salgado(tipo = 'coxinha') {
  const dour = mat('#c4843d', { rug: .75 });
  if (tipo === 'coxinha') { const g = new THREE.Group(); const b = bola(.035, dour, { pos: [0, .032, 0], esc: [1, .95, 1] }); const c = malha(new THREE.ConeGeometry(.03, .06, 14), dour); c.position.y = .085; g.add(b, c); return g; }
  if (tipo === 'pastel') { const m = malha(new THREE.CylinderGeometry(.06, .06, .018, 20, 1, false, 0, Math.PI), mat('#e2b35c', { rug: .7 })); m.position.y = .01; const g = new THREE.Group(); g.add(m); return g; }
  if (tipo === 'esfiha') { const g = new THREE.Group(); g.add(cilindro(.04, .02, mat('#d9a456', { rug: .8 }), { pos: [0, 0, 0] })); g.add(cilindro(.032, .006, mat('#9a3b22', { rug: .7 }), { pos: [0, .02, 0] })); return g; }
  const g = new THREE.Group(); g.add(bola(.025, mat('#e7c27a', { rug: .8 }), { pos: [0, .022, 0], esc: [1, .85, 1] })); return g;
}
/** balcão expositor de vidro com salgados. Comprimento em x, frente em +z */
export function balcaoVidro(o = {}) {
  const g = new THREE.Group(), L = o.comp ?? 1.8, P = o.prof ?? .6;
  g.add(caixaTex(L, .9, P, tex.madeira({ cor: o.madeira || '#8a5a35' }), .6, { pos: [0, 0, 0] }));
  g.add(caixa(L + .04, .03, P + .04, M.inox(), { pos: [0, .9, 0], chanfro: .01 }));
  const vid = M.vidro();
  g.add(caixa(L, .36, .012, vid, { pos: [0, .93, P / 2 - .03], chanfro: 0, sombra: false }));
  g.add(caixa(L, .012, P - .06, vid, { pos: [0, 1.29, 0], chanfro: 0, sombra: false }));
  for (const sx of [-1, 1]) g.add(caixa(.012, .36, P - .06, vid, { pos: [sx * L / 2, .93, 0], chanfro: 0, sombra: false }));
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) g.add(caixa(.02, .37, .02, M.inox(), { pos: [sx * (L / 2), .93, sz * (P / 2 - .03)], chanfro: 0 }));
  const tipos = o.salgados || ['coxinha', 'pastel', 'paoDeQueijo', 'esfiha'], nb = tipos.length, bw = (L - .16) / nb;
  tipos.forEach((tp, i) => {
    const x = -L / 2 + .08 + bw * (i + .5);
    g.add(caixa(bw - .04, .015, P - .2, M.inox('#d9dcdf'), { pos: [x, .94, 0], chanfro: .004 }));
    for (let a = 0; a < 3; a++) for (let b = 0; b < 2; b++) { const s = salgado(tp); s.position.set(x - bw * .28 + a * bw * .28, .955, -.08 + b * .15); s.rotation.y = a + b; g.add(s); }
  });
  return g;
}
/** geladeira expositora (porta de vidro com garrafas). Frente em +z */
export function geladeira(o = {}) {
  const g = new THREE.Group(), W = o.larg ?? .75, H = o.alt ?? 1.95, P = .65, corp = mat(o.cor || '#f1f0ec', { rug: .3 });
  g.add(caixa(W, H, P, corp, { pos: [0, 0, 0], chanfro: .03 }));
  g.add(caixa(W - .08, H - .42, .02, mat('#1c2a33', { rug: .2 }), { pos: [0, .14, P / 2], chanfro: 0 }));
  g.add(plano(W - .04, .2, tex.placa([{ txt: o.texto || 'BEBIDAS GELADAS', tam: 64, y: .5, cor: '#ffffff' }], { fundo: o.faixa || PAL.vermelho, w: 512, h: 128 }), { pos: [0, H - .14, P / 2 + .012] }));
  const cores = o.cores || ['#3f6b2f', '#7a3a1b', '#c33b2c', '#e9a93a', '#2f6db3', '#d9d4c4'], r = rng(o.seed ?? 3);
  for (let p = 0; p < 4; p++) {
    const y = .2 + p * .36; g.add(caixa(W - .12, .012, P - .15, mat('#c9d2d6', { rug: .3 }), { pos: [0, y, -.02], chanfro: 0, sombra: false }));
    for (let i = 0; i < 6; i++) { const b = garrafa(cores[Math.floor(r() * cores.length)], { h: .24 + r() * .06 }); b.position.set(-W / 2 + .1 + i * (W - .2) / 5, y + .012, .1); b.scale.setScalar(.95); g.add(b); }
  }
  g.add(caixa(W - .08, H - .42, .012, M.vidro('#dff3ff', .18), { pos: [0, .14, P / 2 + .02], chanfro: 0, sombra: false }));
  g.add(caixa(.025, .5, .03, M.inox(), { pos: [W / 2 - .08, .9, P / 2 + .04], chanfro: .008 }));
  const luz = plano(W - .14, .03, M.luz('#f4fbff', 1.4), { pos: [0, H - .32, P / 2 - .02] }); g.add(luz);
  return g;
}
/** fogão industrial de N bocas (2 fileiras), com chamas. Frente em +z. Devolve g com userData.bocas (posições locais do topo) */
export function fogao(S, o = {}) {
  const g = new THREE.Group(), n = o.bocas ?? 6, L = o.comp ?? 1.5, P = .75, A = .82;
  g.add(caixa(L, A, P, M.inox(), { pos: [0, 0, 0], chanfro: .02 }));
  g.add(caixa(L - .06, .03, P - .06, M.ferro(), { pos: [0, A, 0], chanfro: .006 }));
  for (let i = 0; i < 5; i++) { const b = cilindro(.022, .03, M.ferro(), { seg: 10 }); b.rotation.x = Math.PI / 2; b.position.set(-L / 2 + .2 + i * (L - .4) / 4, A - .25, P / 2 + .015); g.add(b); }
  const bocas = [], chamas = [], cols = n / 2;
  for (let i = 0; i < cols; i++) for (let j = 0; j < 2; j++) {
    const x = -L / 2 + L / cols * (i + .5), z = j ? .17 : -.17; bocas.push(new THREE.Vector3(x, A + .03, z));
    const anel = malha(new THREE.TorusGeometry(.09, .012, 6, 18), M.ferro()); anel.rotation.x = Math.PI / 2; anel.position.set(x, A + .035, z); g.add(anel);
    for (let k = 0; k < 4; k++) { const b = caixa(.2, .012, .015, M.ferro(), { chanfro: 0 }); b.position.set(x, A + .04, z); b.rotation.y = k * Math.PI / 4; g.add(b); }
    const ch = malha(new THREE.CylinderGeometry(.095, .06, .035, 18, 1, true), new THREE.MeshBasicMaterial({ color: new THREE.Color('#4f8dff').multiplyScalar(1.6), transparent: true, opacity: .75, side: THREE.DoubleSide, depthWrite: false }), { sombra: false });
    ch.position.set(x, A + .05, z); g.add(ch); chamas.push(ch);
  }
  if (S) S.cada(t => chamas.forEach((c, i) => { c.scale.y = .8 + .35 * Math.abs(Math.sin(t * 23 + i * 1.7)); }));
  g.userData.bocas = bocas; return g;
}
/** panelão de alumínio com conteúdo ('feijao'|'arroz'|'agua'|cor) */
export function panela(o = {}) {
  const g = new THREE.Group(), r = o.r ?? .2, h = o.alt ?? .26;
  g.add(cilindro(r, h, M.aluminio(), { pos: [0, 0, 0], aberto: true, seg: 28, mat: {} }));
  g.children[0].material = mat('#b9bcc0', { rug: .4, metal: .8, lados: true, env: 1.2 });
  g.add(cilindro(r, .01, M.aluminio(), { pos: [0, 0, 0], seg: 28 }));
  const cont = { feijao: '#3d2116', arroz: '#f2efe4', agua: '#a9c7cf', molho: '#a8341f' }[o.conteudo] || o.conteudo || '#3d2116';
  g.add(cilindro(r * .97, .01, mat(cont, { rug: o.conteudo === 'arroz' ? .9 : .25 }), { pos: [0, h * .78, 0], seg: 28 }));
  for (const s of [-1, 1]) { const al = malha(new THREE.TorusGeometry(.04, .01, 6, 12, Math.PI), M.aluminio()); al.position.set(s * (r + .01), h * .82, 0); al.rotation.set(0, s > 0 ? -Math.PI / 2 : Math.PI / 2, 0); al.rotation.x = 0; g.add(al); }
  return g;
}
/** chapa (bifeteira) com bifes e ovos. Frente em +z. userData.bifes */
export function chapa(o = {}) {
  const g = new THREE.Group(), L = o.comp ?? 1.1, P = .7, A = .82;
  g.add(caixa(L, A, P, M.inox(), { pos: [0, 0, 0], chanfro: .02 }));
  g.add(caixa(L - .08, .04, P - .12, mat('#2b2927', { rug: .35, metal: .6 }), { pos: [0, A, -.02], chanfro: .005 }));
  const bifes = [];
  for (let i = 0; i < (o.bifes ?? 4); i++) { const b = bola(.07, mat('#6e3a20', { rug: .55 }), { esc: [1.2, .22, .9] }); b.position.set(-L / 2 + .2 + i * .17, A + .055, -.08 + (i % 2) * .14); g.add(b); bifes.push(b); }
  for (let i = 0; i < (o.ovos ?? 2); i++) { const e = new THREE.Group(); e.add(bola(.065, mat('#f6f3ea', { rug: .3 }), { esc: [1, .12, 1] })); e.add(bola(.025, mat('#f2a91c', { rug: .2 }), { pos: [0, .008, 0], esc: [1, .6, 1] })); e.position.set(L / 2 - .2 - i * .16, A + .045, .12 - i * .12); g.add(e); }
  g.userData.bifes = bifes; g.userData.topo = A + .04; return g;
}
/** pia de inox com cuba e torneira (água animada se passar S). Frente em +z */
export function pia(S, o = {}) {
  const g = new THREE.Group(), L = o.comp ?? 1.2, P = .65, A = .88;
  g.add(caixa(L, A - .04, P, mat('#e6e3dc', { rug: .6 }), { pos: [0, 0, 0], chanfro: .015 }));
  g.add(caixa(L + .02, .04, P + .02, M.inox(), { pos: [0, A - .04, 0], chanfro: .01 }));
  g.add(caixa(L * .5, .012, P * .6, mat('#6d7277', { rug: .3, metal: .7 }), { pos: [-L * .12, A + .001, 0], chanfro: 0, sombra: false }));
  const tor = new THREE.Group(); tor.position.set(-L * .12, A, -P / 2 + .07); g.add(tor);
  tor.add(cilindro(.018, .3, M.inox(), { pos: [0, 0, 0], seg: 10 }));
  const bico = caixa(.03, .03, .2, M.inox(), { chanfro: .01 }); bico.position.set(0, .3, .09); tor.add(bico);
  const jato = cilindro(.011, .29, agua(S, { opac: .55, rep: 1, vel: 6 }), { pos: [0, 0, .18], seg: 10, sombra: false }); jato.position.y = .01; tor.add(jato);
  for (let i = 0; i < (o.pratos ?? 6); i++) g.add(cilindro(.11, .012, M.ceramica(), { pos: [L * .33, A + i * .016, .02], seg: 22 }));
  return g;
}
/** caixa registradora + maquininha */
export function caixaRegistradora() {
  const g = new THREE.Group();
  g.add(caixa(.34, .1, .32, mat('#3d4146', { rug: .5 }), { pos: [0, 0, 0], chanfro: .015 }));
  const tec = caixa(.3, .05, .18, mat('#565b61', { rug: .5 }), { pos: [0, .08, .05], chanfro: .01 }); tec.rotation.x = .25; g.add(tec);
  const vis = caixa(.18, .1, .03, mat('#2b2f33', { rug: .4 }), { pos: [0, .1, -.1], chanfro: .008 }); g.add(vis);
  g.add(plano(.15, .06, M.luz('#7fe0a0', 1.1), { pos: [0, .15, -.084] }));
  const maq = caixa(.07, .02, .13, mat('#1d1f22', { rug: .4 }), { pos: [.26, 0, .06], chanfro: .008 }); g.add(maq);
  return g;
}
/** quadro de giz de parede (tx = tex.giz). Normal em +z */
export function quadro(w, h, tx) { const g = new THREE.Group(); g.add(caixa(w + .06, h + .06, .03, M.madeira('#7a4b2a'), { pos: [0, -.03 - h / 2, 0], chanfro: .01 })); g.add(plano(w, h, tx, { pos: [0, 0, .017] })); return g; }
/** cavalete de calçada (A) com quadro dos dois lados */
export function cavalete(tx, o = {}) {
  const g = new THREE.Group(), w = o.larg ?? .5, h = o.alt ?? .8, ab = .2;
  for (const s of [-1, 1]) {
    const p = new THREE.Group(); p.position.set(0, h, 0); p.rotation.x = -s * ab; g.add(p);
    const tab = caixa(w, h, .025, M.madeira('#8a5a35'), { chanfro: .008 }); tab.position.set(0, -h / 2, s * .02); p.add(tab);
    const q = plano(w - .07, h - .1, tx, { pos: [0, -h / 2 - .01, s * .034] }); if (s < 0) q.rotation.y = Math.PI; p.add(q);
  }
  return g;
}
/** toldo listrado inclinado com sanefa recortada. comp ao longo de x, projeta para +z */
export function toldo(o = {}) {
  const g = new THREE.Group(), L = o.comp ?? 3, P = o.proj ?? .9, cair = o.cair ?? .35;
  const tx = repetir(tex.listras(o.cores || ['#f3efe6', PAL.verdeBR]), L / (o.listra ?? .25) / 8, 1);
  const m = mat('#ffffff', { mapa: tx, rug: .85, lados: true });
  const lona = malha(new THREE.PlaneGeometry(L, Math.hypot(P, cair)), m); lona.rotation.x = -Math.PI / 2 + Math.atan2(cair, P); lona.position.set(0, -cair / 2, P / 2); g.add(lona);
  const n = Math.round(L / .25), sanefa = new THREE.Shape(); sanefa.moveTo(-L / 2, 0); sanefa.lineTo(L / 2, 0); sanefa.lineTo(L / 2, -.14);
  for (let i = n; i > 0; i--) { const x = -L / 2 + i * L / n; sanefa.quadraticCurveTo(x - L / n / 2, -.26, x - L / n, -.14); }
  sanefa.lineTo(-L / 2, 0);
  const sg = new THREE.ShapeGeometry(sanefa); const uv = sg.attributes.uv, p = sg.attributes.position; for (let i = 0; i < uv.count; i++) uv.setXY(i, (p.getX(i) + L / 2) / L, p.getY(i) + .5);
  const sm = malha(sg, m); sm.position.set(0, -cair, P); g.add(sm);
  for (const s of [-1, 1]) { const br = cilindro(.012, Math.hypot(P, cair), M.ferro(), { seg: 6 }); br.geometry.translate(0, Math.hypot(P, cair) / 2, 0); br.position.set(s * (L / 2 - .05), 0, 0); br.rotation.x = Math.PI / 2 + Math.atan2(cair, P); g.add(br); }
  return g;
}
/** ventilador de parede que oscila (S para animar). Montado em -z (parede), sopra +z */
export function ventilador(S, o = {}) {
  const g = new THREE.Group(), cor = o.cor || '#f0eee8';
  g.add(caixa(.1, .14, .05, mat(cor, { rug: .4 }), { pos: [0, -.07, 0], chanfro: .015 }));
  const braco = cilindro(.015, .14, M.inox(), { seg: 8 }); braco.rotation.x = Math.PI / 2; braco.position.set(0, 0, .09); g.add(braco);
  const cab = grupo(g, 0, 0, .16);
  cab.add(bola(.05, mat(cor, { rug: .4 }), { esc: [1, 1, 1.2] }));
  const grade = malha(new THREE.TorusGeometry(.17, .006, 6, 32), M.inox()); grade.position.z = .09; cab.add(grade);
  const grade2 = grade.clone(); grade2.position.z = .03; cab.add(grade2);
  const pas = grupo(cab, 0, 0, .06);
  for (let i = 0; i < 3; i++) { const p = bola(.07, mat(o.pas || '#5fa6c9', { rug: .3, opac: .85 }), { esc: [.55, 1.15, .1] }); p.position.set(Math.sin(i * 2.094) * .085, Math.cos(i * 2.094) * .085, 0); p.rotation.z = -i * 2.094; pas.add(p); }
  if (S) S.cada(t => { pas.rotation.z = -t * 31; cab.rotation.y = .6 * Math.sin(ciclo(t, 5)); });
  return g;
}
/** TV de parede com futebol animado (canvas). Normal em +z */
export function tv(S, o = {}) {
  const g = new THREE.Group(), W = o.larg ?? .9, H = W * .5625;
  g.add(caixa(W + .04, H + .04, .05, mat('#151618', { rug: .3 }), { pos: [0, -(H + .04) / 2, 0], chanfro: .01 }));
  const cv = tela2d(320, 180, () => {}), tx = textura(cv), g2 = cv.getContext('2d');
  const tela = plano(W, H, new THREE.MeshBasicMaterial({ map: tx, toneMapped: true }), { pos: [0, 0, .027] }); g.add(tela);
  const desenha = t => {
    for (let i = 0; i < 8; i++) { g2.fillStyle = i % 2 ? '#2f8a3e' : '#34963f'; g2.fillRect(i * 40, 0, 40, 180); }
    g2.strokeStyle = 'rgba(255,255,255,.8)'; g2.lineWidth = 2; g2.strokeRect(10, 14, 300, 156); g2.beginPath(); g2.moveTo(160, 14); g2.lineTo(160, 170); g2.stroke(); g2.beginPath(); g2.arc(160, 92, 22, 0, 7); g2.stroke();
    const bx = 160 + 90 * Math.sin(ciclo(t, 5)), by = 92 + 40 * Math.sin(ciclo(t, 2.5) + 1);
    for (let i = 0; i < 6; i++) { const a = i * 1.1; g2.fillStyle = i < 3 ? '#f2c53d' : '#2a58c9'; g2.beginPath(); g2.arc(bx + 40 * Math.sin(a + ciclo(t, 5)) - (i < 3 ? 15 : -15), by + 30 * Math.cos(a * 1.7 + ciclo(t, 2.5)), 4.5, 0, 7); g2.fill(); }
    g2.fillStyle = '#fff'; g2.beginPath(); g2.arc(bx, by, 3, 0, 7); g2.fill();
    g2.fillStyle = 'rgba(10,12,20,.85)'; g2.fillRect(8, 6, 118, 22); g2.fillStyle = '#fff'; g2.font = "700 15px 'Geist'"; g2.textBaseline = 'middle'; g2.fillText(o.placar || 'CASA 1 x 0 VIS', 14, 17.5);
    tx.needsUpdate = true;
  };
  if (S) S.cada(desenha); else desenha(0);
  return g;
}
/** vaso com espada-de-são-jorge */
export function planta(o = {}) {
  const g = new THREE.Group(), r = rng(o.seed ?? 2);
  g.add(cilindro(.12, .3, mat(o.vaso || '#a5532f', { rug: .8 }), { pos: [0, 0, 0], r2: .15, seg: 18 }));
  g.add(cilindro(.135, .01, mat('#3b2a1f'), { pos: [0, .29, 0], seg: 18 }));
  for (let i = 0; i < 9; i++) { const f = malha(new THREE.ConeGeometry(.035, .5 + r() * .35, 4), mat(i % 2 ? '#3f7a3a' : '#567f3a', { rug: .6 })); f.scale.z = .25; f.position.set((r() - .5) * .14, .3 + .25, (r() - .5) * .14); f.rotation.set((r() - .5) * .3, r() * 3, (r() - .5) * .3); f.geometry.translate(0, .1, 0); g.add(f); }
  return g;
}
/** orelhão (telefone público): concha laranja em poste */
export function orelhao() {
  const g = new THREE.Group();
  g.add(cilindro(.035, 1.6, M.ferro(), { pos: [0, 0, 0], seg: 10 }));
  const conc = malha(new THREE.SphereGeometry(.34, 28, 18, 0, Math.PI * 2, 0, Math.PI * .5), mat('#e8862f', { rug: .3, lados: true }));
  conc.scale.set(1, 1.35, 1); conc.position.set(0, 1.55, .12); conc.rotation.x = .55; g.add(conc);
  g.add(caixa(.17, .28, .1, mat('#c8c8c4', { rug: .4 }), { pos: [0, 1.15, .12], chanfro: .02 }));
  return g;
}
/** árvore de calçada (copa de bolas + tronco) com canteiro */
export function arvore(o = {}) {
  const g = new THREE.Group(), r = rng(o.seed ?? 4), h = o.alt ?? 2.4;
  g.add(caixa(.7, .06, .7, mat('#6b4a33', { rug: 1 }), { pos: [0, 0, 0], chanfro: .01 }));
  g.add(cilindro(.06, h * .6, M.madeira('#6f4d33'), { pos: [0, 0, 0], r2: .045, seg: 10 }));
  for (let i = 0; i < 7; i++) g.add(bola(.32 + r() * .2, mat(['#4f8a3f', '#5f9a45', '#3f7a38'][i % 3], { rug: .8 }), { pos: [(r() - .5) * .7, h * .62 + r() * .55, (r() - .5) * .7], seg: 12 }));
  return g;
}
/** vira-lata caramelo deitado (abana o rabo se passar S). Frente em +z */
export function cachorro(S, o = {}) {
  const g = new THREE.Group(), c = mat(o.cor || '#c98d4b', { rug: .85 }), cl = mat('#e9c9a0', { rug: .85 });
  g.add(bola(.15, c, { pos: [0, .12, 0], esc: [1, .75, 1.9] }));
  g.add(bola(.1, c, { pos: [0, .2, .3], esc: [1, .95, 1.05] }));
  g.add(bola(.055, cl, { pos: [0, .17, .4], esc: [1, .8, 1.3] }));
  g.add(bola(.018, mat('#1d1512', { rug: .3 }), { pos: [0, .19, .47] }));
  for (const s of [-1, 1]) { g.add(bola(.045, c, { pos: [s * .07, .29, .27], esc: [.7, 1.1, .4] })); g.add(bola(.04, cl, { pos: [s * .08, .05, .26], esc: [.8, .5, 1.6] })); }
  const rabo = grupo(g, 0, .14, -.27); const rb = cilindro(.022, .2, c, { seg: 8 }); rb.geometry.translate(0, .1, 0); rb.rotation.x = -1.1; rabo.add(rb);
  if (S) S.cada(t => { rabo.rotation.y = .6 * Math.sin(ciclo(t, .5)); });
  return g;
}

// ───────────────────────── vapor e fumaça (sprites em ciclo → loop perfeito) ─────────────────────────
/** coluna de vapor/fumaça. o: {pos, n, T (período, divida a duração), alt, larg, cor, opac, tam} */
export function vapor(S, o = {}) {
  const g = new THREE.Group(), n = o.n ?? 14, T = o.T ?? 2.5, r = rng(o.seed ?? 5), ps = [];
  g.position.set(...(o.pos || [0, 0, 0]));
  for (let i = 0; i < n; i++) {
    const m = new THREE.SpriteMaterial({ map: tex.macia(), color: o.cor || '#ffffff', transparent: true, opacity: 0, depthWrite: false });
    const s = new THREE.Sprite(m); g.add(s); ps.push({ s, f: i / n, a: r() * 6.28, d: .4 + r() * .6 });
  }
  S.cada(t => {
    for (const p of ps) {
      const u = ((t / T + p.f) % 1 + 1) % 1, alt = (o.alt ?? .9) * u;
      p.s.position.set(Math.sin(p.a + u * 3) * (o.larg ?? .12) * (.4 + u), alt, Math.cos(p.a * 1.3 + u * 2) * (o.larg ?? .12) * .6 * u);
      const sc = (o.tam ?? .16) * (.5 + 1.6 * u) * p.d; p.s.scale.set(sc, sc, sc);
      p.s.material.opacity = (o.opac ?? .45) * Math.sin(Math.PI * u) ** 1.5;
    }
  });
  return g;
}

// ───────────────────────── boneco de maquete semi-realista ─────────────────────────
const lathe = (pts, mat_, seg = 20, phi0 = 0, phiL = Math.PI * 2) => malha(new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), seg, phi0, phiL), mat_);
const cilM = (r1, r2, h, m_, seg = 14) => { const x = malha(new THREE.CylinderGeometry(r1, r2, h, seg), m_); x.position.y = -h / 2; return x; };
/**
 * Pessoa em escala de maquete (≈1,7 m), proporção realista, sem rosto. Frente em +z. "D" = direita (−x), "E" = esquerda (+x).
 * o: {altura, corpo:'h'|'m', pele, cabelo, penteado:'curto'|'coque'|'rabo'|'black'|'careca'|'longo',
 *     camisa, manga:'curta'|'longa'|'regata', calca, bermuda, sapato, chinelo, avental (cor), touca (cor), bone (cor),
 *     colete (cor), gravata (cor, borboleta), cracha, luvas (cor)}
 * Devolve p = {root, quadril, tronco, cabeca, ombro:{D,E}, cotovelo:{D,E}, mao:{D,E}, coxa:{D,E}, joelho:{D,E}}. Anime com pose()/ACAO.
 */
export function pessoa(o = {}) {
  const k = (o.altura ?? 1.72) / 1.72, fem = o.corpo === 'm';
  const pele = M.pele(o.pele || PELE[2]), camisa = M.tecido(o.camisa || '#f2f1ec'), calca = M.tecido(o.calca || '#2c3140');
  const sapato = mat(o.chinelo ? '#d9d4c7' : (o.sapato || '#1f1c1a'), { rug: .5 }), cab = M.cabelo(o.cabelo || CABELO[0]);
  const root = new THREE.Group(), q = grupo(root, 0, .92, 0); root.scale.setScalar(k);
  const p = { root, quadril: q, ombro: {}, cotovelo: {}, mao: {}, coxa: {}, joelho: {}, base: .92 };
  // pelve (calça/bermuda)
  const pel = lathe(fem ? [[0, -.07], [.135, -.07], [.158, .0], [.15, .1], [.13, .15], [0, .15]] : [[0, -.07], [.13, -.07], [.148, 0], [.142, .1], [.135, .15], [0, .15]], calca); pel.scale.z = .68; q.add(pel);
  for (const [lado, s] of [['D', -1], ['E', 1]]) {
    const cx = grupo(q, s * .083, -.03, 0); p.coxa[lado] = cx;
    cx.add(bola(.07, calca, { seg: 12 }));
    cx.add(cilM(.07, .056, .43, o.bermuda ? calca : calca));
    if (o.bermuda) { const pe = cilM(.05, .045, .17, pele); pe.position.y = -.345; cx.add(pe); }
    const jo = grupo(cx, 0, -.43, 0); p.joelho[lado] = jo;
    jo.add(bola(.054, o.bermuda ? pele : calca, { seg: 12 }));
    jo.add(cilM(.054, .04, .42, o.bermuda ? pele : calca));
    const pe = caixa(.085, .06, .22, sapato, { chanfro: .025 }); pe.position.set(0, -.44, .045); jo.add(pe);
  }
  // tronco
  const tr = grupo(q, 0, .06, 0); p.tronco = tr;
  const perfil = fem ? [[0, 0], [.135, 0], [.142, .06], [.122, .19], [.15, .32], [.152, .4], [.14, .45], [.1, .49], [.045, .52], [0, .525]]
    : [[0, 0], [.138, 0], [.142, .06], [.138, .18], [.158, .32], [.168, .4], [.158, .455], [.11, .49], [.05, .52], [0, .525]];
  const torso = lathe(perfil, camisa, 22); torso.scale.z = .66; tr.add(torso);
  if (o.colete) { const ve = lathe(perfil.map(([r, y]) => [r * 1.04 + .002, y]).filter(([, y]) => y < .47), M.tecido(o.colete), 22, .42, Math.PI * 2 - .84); ve.scale.z = .68; tr.add(ve); }
  if (o.avental) {
    const av = malha(new THREE.CylinderGeometry(.152, .175, .78, 18, 1, true, -1.05, 2.1), mat(o.avental, { rug: .85, lados: true }));
    av.scale.z = .74; av.position.y = .03; tr.add(av);
    const al = malha(new THREE.TorusGeometry(.075, .008, 4, 16, Math.PI), mat(o.avental, { rug: .85 })); al.position.set(0, .43, .02); al.rotation.x = -.3; tr.add(al);
  }
  if (o.cracha) tr.add(caixa(.05, .035, .01, mat('#ffffff', { rug: .4 }), { pos: [.07, .34, .1], chanfro: .003 }));
  if (o.gravata) { const gb = bola(.022, mat(o.gravata, { rug: .5 }), { pos: [0, .5, .07], esc: [1.8, .8, .6] }); tr.add(gb); }
  const pesc = cilM(.042, .046, .1, pele); pesc.position.y = .57; tr.add(pesc);
  // cabeça
  const ca = grupo(tr, 0, .56, 0); p.cabeca = ca;
  ca.add(bola(.098, pele, { pos: [0, .11, .005], esc: [.9, 1.12, 1], seg: 24 }));
  ca.add(bola(.016, pele, { pos: [0, .105, .095], esc: [.8, 1, 1] }));
  for (const s of [-1, 1]) ca.add(bola(.018, pele, { pos: [s * .088, .11, 0], esc: [.5, 1, .8] }));
  const cobre = (r, f, m_) => { const h = malha(new THREE.SphereGeometry(r, 24, 14, 0, Math.PI * 2, 0, Math.PI * f), m_); h.position.y = .115; h.scale.set(.93, 1.08, 1.03); h.rotation.x = -.35; ca.add(h); return h; };
  const pt = o.penteado || 'curto';
  if (o.touca) { const tc = cobre(.112, .52, mat(o.touca, { rug: .95 })); tc.rotation.x = -.2; ca.add(bola(.1, mat(o.touca, { rug: .95 }), { pos: [0, .19, -.01], esc: [1.05, .55, 1.05] })); }
  else if (pt !== 'careca') {
    cobre(pt === 'black' ? .125 : .104, pt === 'black' ? .6 : .52, cab);
    if (pt === 'coque') ca.add(bola(.05, cab, { pos: [0, .2, -.08] }));
    if (pt === 'rabo') { const rb = cilM(.03, .02, .18, cab); rb.position.set(0, .14, -.1); rb.rotation.x = .3; ca.add(rb); }
    if (pt === 'longo') { const lg = malha(new THREE.CylinderGeometry(.095, .1, .2, 18, 1, true, Math.PI * .6, Math.PI * .8), mat(o.cabelo || CABELO[0], { rug: .55, lados: true })); lg.position.y = .04; ca.add(lg); }
  }
  if (o.bone) { cobre(.106, .5, M.tecido(o.bone)); const ab = caixa(.12, .01, .1, M.tecido(o.bone), { chanfro: .004 }); ab.position.set(0, .17, .1); ab.rotation.x = .12; ca.add(ab); }
  // braços
  for (const [lado, s] of [['D', -1], ['E', 1]]) {
    const om = grupo(tr, s * .182, .44, 0); p.ombro[lado] = om;
    const mangaCor = o.manga === 'regata' ? pele : camisa;
    om.add(bola(.05, mangaCor, { seg: 12 }));
    om.add(cilM(.047, .04, .29, o.manga === 'longa' ? camisa : pele));
    if (o.manga !== 'longa' && o.manga !== 'regata') { const mg = cilM(.056, .052, .13, camisa); om.add(mg); }
    const co = grupo(om, 0, -.29, 0); p.cotovelo[lado] = co;
    const luva = o.luvas ? M.plastico(o.luvas) : null;
    co.add(bola(.04, luva || (o.manga === 'longa' ? camisa : pele), { seg: 10 }));
    co.add(cilM(.039, .032, .25, luva || (o.manga === 'longa' ? camisa : pele)));
    const ma = grupo(co, 0, -.25, 0); p.mao[lado] = ma;
    ma.add(bola(.042, luva || pele, { pos: [0, -.04, 0], esc: [.75, 1.2, .5], seg: 12 }));
  }
  root.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
  pose(p, {});
  return p;
}
const JUNTAS = ['tronco', 'cabeca'];
/** aplica uma pose (ângulos em rad). P: {tronco:[x,y,z], cabeca, ombroD:[x,y,z], ombroE, cotoveloD (n), cotoveloE, maoD:[x,y,z], maoE,
 *  coxaD:[x,y,z], coxaE, joelhoD (n), joelhoE, altura (desloca o quadril)}. Ombro x<0 = braço p/ frente; tronco x>0 = inclina p/ frente. */
export function pose(p, P) {
  const set = (obj, v, d = [0, 0, 0]) => { const a = v ?? d; obj.rotation.set(a[0] ?? 0, a[1] ?? 0, a[2] ?? 0); };
  set(p.tronco, P.tronco); set(p.cabeca, P.cabeca);
  set(p.ombro.D, P.ombroD, [.04, 0, -.09]); set(p.ombro.E, P.ombroE, [.04, 0, .09]);
  p.cotovelo.D.rotation.set(P.cotoveloD ?? -.2, 0, 0); p.cotovelo.E.rotation.set(P.cotoveloE ?? -.2, 0, 0);
  set(p.mao.D, P.maoD); set(p.mao.E, P.maoE);
  set(p.coxa.D, P.coxaD); set(p.coxa.E, P.coxaE);
  p.joelho.D.rotation.set(P.joelhoD ?? 0, 0, 0); p.joelho.E.rotation.set(P.joelhoE ?? 0, 0, 0);
  p.quadril.position.y = p.base + (P.altura ?? 0);
}
/** prende um objeto na mão (lado 'D'|'E') com deslocamento/rotação locais */
export function segurar(p, lado, obj, pos = [0, -.06, .02], rot = [0, 0, 0]) { obj.position.set(...pos); obj.rotation.set(...rot); p.mao[lado].add(obj); return obj; }

const sen = Math.sin, cos = Math.cos;
/** sentado numa cadeira de assento ~.46 m (mescle com ...SENTADO) */
export const SENTADO = { coxaD: [-1.5, 0, -.05], coxaE: [-1.5, 0, .05], joelhoD: 1.5, joelhoE: 1.5, altura: -.42 };
/**
 * Ações animadas: ACAO.nome(p, t, o) → aplica a pose do quadro t. Todas são cíclicas; use períodos T que dividem a duração
 * do vídeo (5 s: 5, 2.5, 1.25, 1, .625, .5) para o vídeo fechar em loop.
 */
export const ACAO = {
  parado: (p, t, o = {}) => { const w = ciclo(t, o.T ?? 5, o.f ?? 0); pose(p, { tronco: [.02, .03 * sen(w), 0], cabeca: [.05, .15 * sen(w * 2), 0], ...o.extra }); },
  mexer: (p, t, o = {}) => { const w = ciclo(t, o.T ?? 1.25, o.f ?? 0); pose(p, { tronco: [.16, .07 * sen(w), 0], cabeca: [.42, .05 * sen(w), 0], ombroD: [-.85 + .12 * sen(w), .18 * cos(w), -.16 + .1 * cos(w)], cotoveloD: -.95 + .14 * sen(w + 1), maoD: [.25, 0, 0], ombroE: [-.5, 0, .3], cotoveloE: -1.05, ...o.extra }); },
  chapear: (p, t, o = {}) => { const w = ciclo(t, o.T ?? 1.25, o.f ?? 0), fl = Math.max(0, sen(w)) ** 3; pose(p, { tronco: [.14, -.06 * sen(w), 0], cabeca: [.45, -.1 * sen(w), 0], ombroD: [-.75 - .3 * fl, .1, -.12], cotoveloD: -.75 - .45 * fl, maoD: [-.7 * fl, 0, 0], ombroE: [-.55, 0, .22], cotoveloE: -.95, ...o.extra }); },
  lavar: (p, t, o = {}) => { const w = ciclo(t, o.T ?? .625, o.f ?? 0); pose(p, { tronco: [.22, .03 * sen(w), 0], cabeca: [.5, 0, 0], ombroD: [-.72 + .09 * sen(w), .14 * cos(w), -.1], cotoveloD: -.85 + .1 * cos(w), ombroE: [-.8, 0, .14], cotoveloE: -.95, maoE: [0, 0, .4], ...o.extra }); },
  varrer: (p, t, o = {}) => { const w = ciclo(t, o.T ?? 1.25, o.f ?? 0), s = sen(w); pose(p, { tronco: [.28, .32 * s, 0], cabeca: [.45, -.12 * s, 0], ombroD: [-.5 + .1 * s, .2 * s, -.12], cotoveloD: -.45, ombroE: [-.95, 0, .28], cotoveloE: -.6, coxaD: [0, 0, -.1], coxaE: [-.15, 0, .12], joelhoE: .12, ...o.extra }); },
  digitar: (p, t, o = {}) => { const w = ciclo(t, o.T ?? .5, o.f ?? 0), ol = suave(.15, .5, .5 - .5 * cos(ciclo(t, o.Tolhar ?? 2.5, o.f ?? 0))); pose(p, { tronco: [.1, 0, 0], cabeca: [lerp(.48, .02, ol), .25 * ol, 0], ombroD: [-.4, 0, -.14], cotoveloD: -1.1 + .1 * Math.max(0, sen(w)), ombroE: [-.4, 0, .14], cotoveloE: -1.1 + .1 * Math.max(0, -sen(w)), ...o.extra }); },
  comer: (p, t, o = {}) => { const u = t / (o.T ?? 2.5) + (o.f ?? 0), m = (.5 - .5 * cos(2 * Math.PI * u)) ** 2; pose(p, { ...SENTADO, tronco: [.16 - .06 * m, 0, 0], cabeca: [.32 - .28 * m, 0, 0], ombroD: [-.45 - .3 * m, 0, -.22 + .06 * m], cotoveloD: -1.0 - 1.15 * m, ombroE: [-.35, 0, .22], cotoveloE: -1.15, ...o.extra }); },
  conversar: (p, t, o = {}) => { const w = ciclo(t, o.T ?? 2.5, o.f ?? 0); pose(p, { ...(o.sentado ? SENTADO : {}), tronco: [.06, .1 * sen(w), 0], cabeca: [.05 + .08 * sen(w * 2), .35 * sen(w), 0], ombroE: [-.45 + .18 * sen(w * 2), 0, .25], cotoveloE: -1.3 + .25 * sen(w * 2 + 1), maoE: [0, .4 * sen(w * 2), 0], ombroD: [-.35, 0, -.2], cotoveloD: -1.1, ...o.extra }); },
  pagar: (p, t, o = {}) => { const w = ciclo(t, o.T ?? 2.5, o.f ?? 0), k = .5 - .5 * cos(w); pose(p, { tronco: [.05, 0, 0], cabeca: [.2 + .15 * k, 0, 0], ombroD: [-.6 - .35 * k, 0, -.1], cotoveloD: -.9 + .4 * k, ombroE: [.05, 0, .1], ...o.extra }); },
  /** andar no lugar (combine com caminho()). bandeja: braço E dobrado segurando à altura do ombro */
  andar: (p, t, o = {}) => {
    const w = ciclo(t, o.T ?? 1, o.f ?? 0), s = sen(w);
    pose(p, { tronco: [.05, .07 * s, 0], cabeca: [.08, -.05 * s, 0], coxaD: [-.42 * s, 0, 0], coxaE: [.42 * s, 0, 0], joelhoD: .08 + .65 * Math.max(0, cos(w)) ** 1.5, joelhoE: .08 + .65 * Math.max(0, -cos(w)) ** 1.5,
      ombroD: [.32 * s, 0, -.1], cotoveloD: -.3, ombroE: o.bandeja ? [-.2, 0, .5] : [-.32 * s, 0, .1], cotoveloE: o.bandeja ? -1.6 : -.3, maoE: o.bandeja ? [0, 0, -.4] : [0, 0, 0], altura: .022 * cos(2 * w), ...o.extra });
  },
};
/** percorre uma curva fechada (CatmullRom) em T segundos, olhando para a frente. Use com ACAO.andar(T = T/nPassos) */
export function caminho(p, curva, t, T, f = 0) {
  const u = ((t / T + f) % 1 + 1) % 1, P = curva.getPointAt(u), D = curva.getTangentAt(u);
  p.root.position.set(P.x, P.y, P.z); p.root.rotation.y = Math.atan2(D.x, D.z); return u;
}
/** objetos de mão */
export const OBJ = {
  colher: () => { const g = new THREE.Group(); const c = cilindro(.008, .42, M.madeira('#b88553'), { seg: 6 }); c.position.y = -.25; g.add(c); g.add(bola(.025, M.madeira('#b88553'), { pos: [0, -.45, 0], esc: [1, 1.4, .4] })); return g; },
  espatula: () => { const g = new THREE.Group(); const c = cilindro(.008, .22, M.ferro(), { seg: 6 }); c.position.y = -.12; g.add(c); g.add(caixa(.08, .1, .006, M.inox(), { pos: [0, -.3, 0], chanfro: 0 })); return g; },
  prato: () => cilindro(.1, .012, M.ceramica(), { seg: 20 }),
  bandeja: (itens = 2) => { const g = new THREE.Group(); g.add(cilindro(.2, .012, M.inox('#d9dcdf'), { seg: 28 })); for (let i = 0; i < itens; i++) { const f = pf({ r: .085 }); f.position.set((i - (itens - 1) / 2) * .17, .012, 0); g.add(f); } const c = copo('#e98a2a'); c.position.set(0, .012, .12); g.add(c); return g; },
  vassoura: () => { const g = new THREE.Group(); const c = cilindro(.012, 1.25, M.madeira('#c79a6b'), { seg: 6 }); c.position.y = -.62; g.add(c); const cb = caixa(.32, .05, .06, M.plastico('#2f6db3'), { pos: [0, -1.3, 0], chanfro: .01 }); g.add(cb); g.add(caixa(.3, .07, .05, mat('#d9b44a', { rug: .9 }), { pos: [0, -1.37, 0], chanfro: 0 })); return g; },
  cartao: () => caixa(.085, .055, .004, M.plastico('#2f6db3'), { chanfro: 0 }),
  garfo: () => { const g = new THREE.Group(); const c = caixa(.008, .14, .004, M.inox(), { chanfro: 0 }); c.position.y = -.07; g.add(c); return g; },
};

// ───────────────────────── câmera: órbita lenta + leve aproximação ─────────────────────────
/** o: {alvo, raio:[r0,r1], azim:[a0,a1] (graus, 0 = +z, 90 = +x), elev:[e0,e1] (graus), fov:[f0,f1], t0, t1, ease} → fn(t) */
export function orbita(S, o) {
  const A = V3(o.alvo || [0, 0, 0]), ar = x => Array.isArray(x) ? x : [x, x];
  const [r0, r1] = ar(o.raio), [a0, a1] = ar(o.azim), [e0, e1] = ar(o.elev), [f0, f1] = ar(o.fov ?? 28);
  return t => {
    const k = fase(t, o.t0 ?? 0, o.t1 ?? window.VIDEO.dur, o.ease ?? 'sine.inOut');
    const r = lerp(r0, r1, k), az = lerp(a0, a1, k) * Math.PI / 180, el = lerp(e0, e1, k) * Math.PI / 180;
    S.camera.position.set(A.x + r * cos(el) * sen(az), A.y + r * sen(el), A.z + r * cos(el) * cos(az)); S.camera.lookAt(A);
    const f = lerp(f0, f1, k); if (S.camera.fov !== f) { S.camera.fov = f; S.camera.updateProjectionMatrix(); }
  };
}

// ───────────────────────── HUD editorial (HTML sobre o 3D) ─────────────────────────
const CSS = `
.mq-hud{position:absolute;inset:0;pointer-events:none;z-index:5;color:${PAL.tinta};font-family:'Geist',sans-serif}
.mq-rot{position:absolute;font:600 21px/1 'Geist',sans-serif;letter-spacing:.24em;text-transform:uppercase;color:${PAL.tinta2};white-space:nowrap}
.mq-tit{position:absolute;font:italic 400 var(--tam,168px)/.86 'Lora',Georgia,serif;letter-spacing:-.025em;white-space:nowrap}
.mq-tit div:nth-child(2){padding-left:.42em}
.mq-tit b{font-weight:400;color:${PAL.acento}}
.mq-sub{position:absolute;font:italic 400 36px/1.28 'Lora',Georgia,serif;color:#3f3c37;white-space:nowrap}
.mq-traco{position:absolute;height:1.5px;background:${PAL.tinta};opacity:.5}
.mq-selo{position:absolute;display:flex;align-items:center;gap:12px;padding:10px 18px;border:1.5px solid ${PAL.fio};border-radius:8px;background:rgba(250,249,246,.75);font:500 18px/1 'JetBrains Mono',monospace;letter-spacing:.16em;text-transform:uppercase;color:${PAL.tinta2};white-space:nowrap}
.mq-selo i{width:11px;height:11px;border-radius:50%;background:#3aa76d;display:inline-block}
.mq-pain{position:absolute;background:rgba(250,249,246,.94);border:1.5px solid ${PAL.fio};border-radius:10px;padding:22px 22px 18px;box-shadow:0 10px 30px rgba(60,50,40,.08)}
.mq-pain .cab{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:16px}
.mq-pain .cab span{font:600 17px/1 'Geist',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:${PAL.tinta2}}
.mq-pain .cab em{font:italic 400 22px/1 'Lora',Georgia,serif;color:${PAL.tinta3}}
.mq-pain .sec{font:600 15px/1 'Geist',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:${PAL.tinta3};margin:16px 0 10px}
.mq-pain .lin{height:1px;background:${PAL.fio};margin:14px 0 0}
.mq-bts{display:flex;gap:8px}
.mq-bt{flex:1;height:52px;border-radius:6px;border:1.5px solid #cfcac0;display:flex;align-items:center;justify-content:center;gap:8px;font:600 18px/1.05 'Geist',sans-serif;color:${PAL.tinta};text-align:center;background:#fbfaf7}
.mq-bt.on{background:${PAL.tinta};color:#fff;border-color:${PAL.tinta}}
.mq-bt.pr{box-shadow:inset 0 0 0 2px ${PAL.tinta}}
.mq-bt i{width:14px;height:14px;border-radius:50%;display:inline-block;box-shadow:inset 0 -2px 3px rgba(0,0,0,.25)}
.mq-chips{display:flex;gap:10px}
.mq-chip{flex:1;border:1.5px solid #d8d3c9;border-radius:6px;padding:10px 6px 9px;display:flex;flex-direction:column;align-items:center;gap:8px;font:italic 400 19px/1 'Lora',Georgia,serif;color:${PAL.tinta2};background:#fbfaf7}
.mq-chip.on{border-color:${PAL.tinta};box-shadow:inset 0 0 0 1px ${PAL.tinta};color:${PAL.tinta}}
.mq-chip i{width:20px;height:20px;border-radius:50%;display:block;box-shadow:inset 0 -3px 4px rgba(0,0,0,.25)}
.mq-stats{display:flex;justify-content:space-between;font:400 17px/1 'Geist',sans-serif;color:${PAL.tinta2};margin-top:14px}
.mq-stats b{font:600 17px/1 'JetBrains Mono',monospace;color:${PAL.tinta}}
.mq-sl{margin-top:4px}
.mq-sl .t{display:flex;justify-content:space-between;font:600 15px/1 'Geist',sans-serif;letter-spacing:.2em;text-transform:uppercase;color:${PAL.tinta3}}
.mq-sl .t b{font:500 15px/1 'JetBrains Mono',monospace;letter-spacing:.04em;color:${PAL.tinta2}}
.mq-sl .tr{position:relative;height:2px;background:#cfcac0;margin:14px 2px 10px}
.mq-sl .tr i{position:absolute;top:50%;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;background:#fbfaf7;border:1.5px solid ${PAL.tinta2}}
.mq-sl .e{display:flex;justify-content:space-between;font:italic 400 16px/1 'Lora',Georgia,serif;color:${PAL.tinta3}}
.mq-rod{position:absolute}
.mq-rod .c{font:600 16px/1 'Geist',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:${PAL.tinta3}}
.mq-rod .f{font:italic 400 30px/1.25 'Lora',Georgia,serif;color:${PAL.tinta};margin:10px 0 18px;white-space:nowrap}
.mq-rod .d{display:flex;border-top:1.5px solid ${PAL.fio};padding-top:14px}
.mq-rod .d div{padding:0 22px 0 0;margin-right:22px;border-right:1.5px solid ${PAL.fio}}
.mq-rod .d div:last-child{border-right:0}
.mq-rod .d span{display:block;font:600 14px/1 'Geist',sans-serif;letter-spacing:.2em;text-transform:uppercase;color:${PAL.tinta3};margin-bottom:9px}
.mq-rod .d b{font:500 30px/1 'JetBrains Mono',monospace;color:${PAL.tinta};white-space:nowrap}
.mq-rod .d small{font:400 15px/1 'Geist',sans-serif;color:${PAL.tinta3};margin-left:5px}
.mq-rod .n{font:400 14px/1.35 'Geist',sans-serif;color:${PAL.tinta3};margin-top:14px;white-space:nowrap}
`;
let HUD = null;
export function hud() {
  if (HUD) return HUD;
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  const el = document.createElement('div'); el.className = 'mq-hud'; document.getElementById('stage').appendChild(el);
  HUD = { el }; return HUD;
}
const div = (cls, html = '', css = {}) => { const e = document.createElement('div'); e.className = cls; e.innerHTML = html; Object.assign(e.style, css); hud().el.appendChild(e); return e; };
const px = v => typeof v === 'number' ? v + 'px' : v;
const posCss = o => ({ left: px(o.x ?? 60), top: o.y !== undefined ? px(o.y) : undefined, right: o.direita !== undefined ? px(o.direita) : undefined, bottom: o.base !== undefined ? px(o.base) : undefined, width: o.w ? px(o.w) : undefined });
const valor = (v, t) => typeof v === 'function' ? v(t) : v;

/** cabeçalho editorial: rótulo em versalete, título serifado em itálico (ponto final no acento), traço e subtítulo.
 *  o: {x, y, rotulo, titulo:['Restaurante.'] (linhas; o último '.' vira acento), tam, sub:['linha', 'linha'], entrada (s; 0 = já na tela)} */
export function cabecalho(S, o) {
  const x = o.x ?? 60, y = o.y ?? 150, tam = o.tam ?? 168;
  const r = div('mq-rot', o.rotulo, { left: px(x), top: px(y) });
  const tit = div('mq-tit', o.titulo.map(l => `<div>${l.replace(/\.$/, '<b>.</b>')}</div>`).join(''), { left: px(x - 6), top: px(y + 40), '--tam': px(tam) });
  const yS = y + 40 + tam * .86 * o.titulo.length + 34;
  const tr = div('mq-traco', '', { left: px(x), top: px(yS), width: '64px' });
  const sub = div('mq-sub', (o.sub || []).join('<br>'), { left: px(x), top: px(yS + 22) });
  const ent = o.entrada ?? 0;
  S.hud.push(t => { [r, tit, tr, sub].forEach((e, i) => { const k = ent ? fase(t, i * .08, ent + i * .08, 'power3.out') : 1; e.style.opacity = k; e.style.transform = `translateY(${(1 - k) * 18}px)`; }); });
  return { r, tit, sub };
}
/** selo "● AO VIVO · 11:58" no canto (relógio que anda com t). o: {txt, relogio:[h,m,s] , direita, y} */
export function selo(S, o = {}) {
  const e = div('mq-selo', '<i></i><span></span>', { right: px(o.direita ?? 60), top: px(o.y ?? 146) }), sp = e.querySelector('span'), dot = e.querySelector('i');
  S.hud.push(t => {
    let tx = o.txt || 'AO VIVO';
    if (o.relogio) { const [h, m, s] = o.relogio, tot = h * 3600 + m * 60 + s + Math.floor(t); tx += ` · ${String(Math.floor(tot / 3600) % 24).padStart(2, '0')}:${String(Math.floor(tot / 60) % 60).padStart(2, '0')}:${String(tot % 60).padStart(2, '0')}`; }
    if (sp.textContent !== tx) sp.textContent = tx; dot.style.opacity = .55 + .45 * Math.cos(ciclo(t, 1));
  });
  return e;
}
/**
 * painel claro de controles (como o da referência). o: {x, y, w, titulo, fig, blocos:[
 *   {tipo:'botoes', itens:[{txt, on, cor}]}, {tipo:'chips', rot, itens:[{txt, cor}], ativo (índice ou fn(t))},
 *   {tipo:'stats', itens:[[rot, valor|fn(t)]]}, {tipo:'slider', rot, val:fn(t)|n (0–1), txt:fn(t)|str, de, ate}, {tipo:'linha'}]}
 */
export function painel(S, o) {
  const e = div('mq-pain', '', { ...posCss(o) }), upd = [];
  e.innerHTML = `<div class="cab"><span>${o.titulo}</span>${o.fig ? `<em>${o.fig}</em>` : ''}</div>`;
  for (const b of o.blocos) {
    if (b.rot) e.insertAdjacentHTML('beforeend', `<div class="sec">${b.rot}</div>`);
    if (b.tipo === 'linha') e.insertAdjacentHTML('beforeend', '<div class="lin"></div>');
    if (b.tipo === 'botoes') {
      const w = document.createElement('div'); w.className = 'mq-bts'; e.appendChild(w);
      const bts = b.itens.map(it => { const x = document.createElement('div'); x.className = 'mq-bt' + (it.on ? ' on' : ''); x.innerHTML = (it.cor ? `<i style="background:${it.cor}"></i>` : '') + it.txt; w.appendChild(x); return x; });
      if (b.pulso) upd.push(t => { const i = valor(b.pulso, t); bts.forEach((x, j) => x.classList.toggle('pr', j === i)); });
    }
    if (b.tipo === 'chips') {
      const w = document.createElement('div'); w.className = 'mq-chips'; e.appendChild(w);
      const cs = b.itens.map(it => { const x = document.createElement('div'); x.className = 'mq-chip'; x.innerHTML = `<i style="background:${it.cor}"></i>${it.txt}`; w.appendChild(x); return x; });
      upd.push(t => { const a = valor(b.ativo, t); cs.forEach((x, j) => x.classList.toggle('on', j === a)); });
    }
    if (b.tipo === 'stats') {
      const w = document.createElement('div'); w.className = 'mq-stats'; e.appendChild(w);
      const vs = b.itens.map(([r]) => { const x = document.createElement('div'); x.innerHTML = `${r} <b></b>`; w.appendChild(x); return x.querySelector('b'); });
      upd.push(t => b.itens.forEach(([, v], j) => { const s = String(valor(v, t)); if (vs[j].textContent !== s) vs[j].textContent = s; }));
    }
    if (b.tipo === 'slider') {
      const w = document.createElement('div'); w.className = 'mq-sl'; e.appendChild(w);
      w.innerHTML = `<div class="t">${b.titulo || ''}<b></b></div><div class="tr"><i></i></div><div class="e"><span>${b.de || ''}</span><span>${b.ate || ''}</span></div>`;
      const th = w.querySelector('i'), bv = w.querySelector('b');
      upd.push(t => { th.style.left = (100 * clamp(valor(b.val, t))) + '%'; const s = valor(b.txt, t) ?? ''; if (bv.textContent !== s) bv.textContent = s; });
    }
  }
  S.hud.push(t => upd.forEach(f => f(t)));
  return e;
}
/** rodapé: cabeça em versalete, frase em itálico, linha de dados em mono e nota miúda.
 *  o: {x, y, cab, frase, dados:[{rot, val|fn(t), uni}], nota} */
export function rodape(S, o) {
  const e = div('mq-rod', '', posCss(o));
  e.innerHTML = `<div class="c">${o.cab || ''}</div><div class="f">${o.frase || ''}</div><div class="d">${o.dados.map(d => `<div><span>${d.rot}</span><b></b>${d.uni ? `<small>${d.uni}</small>` : ''}</div>`).join('')}</div>${o.nota ? `<div class="n">${o.nota}</div>` : ''}`;
  const bs = [...e.querySelectorAll('.d b')];
  S.hud.push(t => o.dados.forEach((d, j) => { const s = String(valor(d.val, t)); if (bs[j].textContent !== s) bs[j].textContent = s; }));
  return e;
}
/** projeta um ponto 3D em px da tela */
export function tela(S, alvo, saida = new THREE.Vector3()) {
  if (alvo.isObject3D) alvo.getWorldPosition(saida); else saida.copy(alvo.isVector3 ? alvo : V3(alvo));
  saida.project(S.camera); return { x: (saida.x + 1) / 2 * window.VIDEO.w, y: (1 - saida.y) / 2 * window.VIDEO.h, atras: saida.z > 1 };
}
