// blocos.js — biblioteca do estilo "peças de montar — montando e desmontando" (three.js, módulo ES)
// Um objeto inteiro feito de MILHARES de peças pequenas com pinos (tijolos, placas, lisos, telhas, redondos),
// modelado em grade de voxels, que se MONTA voando em arco a partir de montes de peças soltas sobre uma placa-base
// verde cheia de pinos e depois se DESMONTA de cima para baixo, voltando aos montes (loop perfeito).
// Cenário de maquete de brinquedo: rua de asfalto, chão cinza-claro, prédios pastel low-poly, céu com nuvens em blocos.
// Uso:  import * as B from '../../lib/blocos.js';  window.SETUP = async () => { const S = B.palco({...}); ... }
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
export { THREE };

// ───────────────────────── medidas (1 unid. = 1 passo de pino) ─────────────────────────
export const H_TIJOLO = 1.2, H_PLACA = 0.4;
const PINO_R = .3, PINO_H = .18, FOLGA = .03, CHANFRO = .055;

// ───────────────────────── paleta de plástico ABS ─────────────────────────
export const COR = {
  vermelho: '#c8231b', branco: '#f3f2ee', preto: '#1c1d20', grafite: '#4f5459', cinza: '#9ea4aa', prata: '#c8cdd2',
  azulPerua: '#7db3de', azul: '#1f5fae', marinho: '#1c2d52', amarelo: '#f5c52e', laranja: '#f08a24', bege: '#dcc597',
  marrom: '#7a4a2c', verde: '#2f9a4b', verdeClaro: '#79c159', ceramica: '#c25a2c', kraft: '#cfb98f', madeira: '#b98a55',
  jeans: '#3d5e8e', vidro: '#4a6272', luz: '#fff3d2', rosa: '#e98aa6',
  pele: ['#f1c9a5', '#dba57d', '#b47b52', '#8a5636', '#5e3a24'],
};
// cenário: cores-BASE calibradas para que o render (com a luz do palco) dê os valores medidos na referência
// (chão ≈ 207,208,204 · asfalto ≈ 77,86,91 · placa ≈ 55,140,87 · prédios pastel dessaturados e enevoados)
export const CENA = {
  placa: '#368454', chao: '#acada8', asfalto: '#2b3236', faixa: '#e9e9e6', calcada: '#a6a7a3',
  ceu: '#7fb7e6', horizonte: '#dde7ee', predios: ['#8d9cab', '#ae979e', '#b5a090', '#9c95a8', '#99aaa1', '#b7ad91'],
};

// ───────────────────────── utilidades de tempo e acaso (tudo determinístico) ─────────────────────────
export function rng(seed = 1) { let s = seed >>> 0 || 1; return () => { s = (s + 0x6d2b79f5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const suave = k => { k = clamp(k); return k * k * (3 - 2 * k); };
/** progresso 0→1 entre t0 e t1 */
export const fase = (t, t0, t1) => clamp((t - t0) / (t1 - t0));
/** envelope 0→1→0 (sobe em [a,b], desce em [c,d]) */
export const janela = (t, a, b, c, d) => suave(fase(t, a, b)) * (1 - suave(fase(t, c, d)));
const V3 = v => (v?.isVector3 ? v.clone() : new THREE.Vector3(...(v || [0, 0, 0])));

// ───────────────────────── palco: renderer + luz de dia de estúdio + AO ─────────────────────────
const QUAD_VERT = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
const ACAB_FRAG = `uniform sampler2D tDiffuse; uniform float uTime, uGrain, uVig; uniform vec2 uRes; varying vec2 vUv;
float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void main(){ vec2 c = vUv - .5; c.x *= uRes.x / uRes.y; float d = length(c);
  vec3 col = texture2D(tDiffuse, vUv).rgb;
  col *= 1. - uVig * smoothstep(.45, 1.1, d);
  col += (h(vUv * uRes + fract(uTime * 7.13) * 100.) - .5) * uGrain;
  gl_FragColor = vec4(col, 1.); }`;

/**
 * Palco. o: {fov, exposicao, sol:{dir, forca, cor}, hemi, ambiente (IBL), ao:{raio, forca}, grao, vinheta, raioSombra, centroSombra}
 * Devolve S = {scene, camera, renderer, composer, sol, mats, rigs, cada(fn), update(t) (você define), hud:[], sombra(c, r)}.
 */
export function palco(o = {}) {
  const V = window.VIDEO;
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = o.exposicao ?? 1;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.domElement.className = 'layer';
  (o.parent || document.getElementById('stage')).prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), .04).texture; scene.environmentIntensity = o.ambiente ?? .55;
  const camera = new THREE.PerspectiveCamera(o.fov ?? 36, V.w / V.h, 1, 4000);

  const sol = new THREE.DirectionalLight(o.sol?.cor || '#fff6ea', o.sol?.forca ?? 2.4);
  sol.castShadow = true; sol.shadow.mapSize.set(4096, 4096); sol.shadow.radius = o.sol?.raio ?? 3;
  sol.shadow.bias = -.0004; sol.shadow.normalBias = .03;
  scene.add(sol, sol.target);
  const hemi = new THREE.HemisphereLight('#e4f0ff', '#bdb6a8', o.hemi ?? .7); scene.add(hemi);
  const dirSol = V3(o.sol?.dir || [-.45, 1, .55]).normalize();

  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(V.w, V.h, { type: THREE.HalfFloatType, samples: 4 }));
  composer.setPixelRatio(1); composer.setSize(V.w, V.h);
  composer.addPass(new RenderPass(scene, camera));
  const mr = Math.random; Math.random = rng(77);                       // o GTAO sorteia o ruído do denoise: fixa a semente
  const ao = new GTAOPass(scene, camera, V.w, V.h); Math.random = mr;
  ao.updateGtaoMaterial({ radius: o.ao?.raio ?? 1.1, distanceExponent: 1.5, thickness: 1.2, scale: 1, samples: 16, distanceFallOff: 1 });
  ao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 5, rings: 2, samples: 16 });
  ao.blendIntensity = o.ao?.forca ?? .85;
  ao._overrideVisibility = function () { scene.traverse(x => { if ((x.isPoints || x.isLine || x.isSprite || x.userData.semAO || (x.isMesh && x.material?.transparent && !x.userData.ao)) && x.visible) { x.visible = false; this._visibilityCache.push(x); } }); };
  composer.addPass(ao);
  composer.addPass(new OutputPass());
  const acab = new ShaderPass({ uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uGrain: { value: o.grao ?? .006 }, uVig: { value: o.vinheta ?? .08 }, uRes: { value: new THREE.Vector2(V.w, V.h) } }, vertexShader: QUAD_VERT, fragmentShader: ACAB_FRAG });
  composer.addPass(acab);

  const S = {
    THREE, renderer, scene, camera, composer, sol, hemi, ao, acab, update: null, hud: [], anima: [], rigs: [], rig: {}, mats: {}, pecas: [],
    sombra(centro, raio = 50) {
      const c = V3(centro); sol.target.position.copy(c); sol.position.copy(c).addScaledVector(dirSol, raio * 3);
      const sc = sol.shadow.camera; sc.left = sc.bottom = -raio; sc.right = sc.top = raio; sc.near = 1; sc.far = raio * 7; sc.updateProjectionMatrix();
    },
    cada(fn) { S.anima.push(fn); return fn; },
  };
  for (const f of ['abs', 'vidro', 'luz', 'borracha', 'metal']) S.mats[f] = matFam(f);
  S.sombra(o.centroSombra || [0, 0, 0], o.raioSombra ?? 50);
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

/** materiais por família: abs (plástico brilhante), vidro (translúcido fumê), luz (emissivo), borracha, metal */
function matFam(fam) {
  if (fam === 'vidro') return new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: .05, metalness: 0, transparent: true, opacity: .74, depthWrite: false, clearcoat: 1, clearcoatRoughness: .04 });
  if (fam === 'luz') return new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: .12, clearcoat: 1, emissive: '#ffe7b0', emissiveIntensity: 0 });
  if (fam === 'borracha') return new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: .72, metalness: 0 });
  if (fam === 'metal') return new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: .25, metalness: .7, clearcoat: .6 });
  return new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: .3, metalness: 0, clearcoat: .5, clearcoatRoughness: .25 });
}

// ───────────────────────── geometria das peças (com pinos e chanfro) ─────────────────────────
const GEO = new Map();
function geoPino(r = PINO_R) {
  const p = [[0, 0], [r, 0], [r, PINO_H - .045], [r - .03, PINO_H - .01], [r - .07, PINO_H], [0, PINO_H]].map(([x, y]) => new THREE.Vector2(x, y));
  return new THREE.LatheGeometry(p, 14);
}
function juntar(gs) {
  const ni = gs.some(g => !g.index); if (ni) gs = gs.map(g => (g.index ? g.toNonIndexed() : g));
  for (const g of gs) { for (const k of Object.keys(g.attributes)) if (!['position', 'normal'].includes(k)) g.deleteAttribute(k); }
  return mergeGeometries(gs);
}
// Sem pino no topo: o pino cilindrico e a assinatura registrada de um sistema de blocos conhecido.
// As pecas ficam chanfradas e se leem como bloco de montar generico. A funcao continua existindo
// para nao quebrar quem a chama.
function pinos() { return []; }
/**
 * Geometria de uma peça pelo nome:  tijolo-MxN · placa-MxN · liso-MxN (sem pino) · redondo-NxN · botao-NxN (placa redonda)
 * · telha-1xN (rampa 45°, desce para +x) · pneu · aro.  M = largura (eixo z), N = comprimento (eixo x).
 * Origem: centro da base (pneu/aro: centro da roda, eixo em y).
 */
export function geoPeca(tipo) {
  if (GEO.has(tipo)) return GEO.get(tipo);
  const [kind, dim = '1x1'] = tipo.split('-'), [m, n] = dim.split('x').map(Number);
  const w = n - FOLGA, d = m - FOLGA;
  let g;
  if (kind === 'tijolo' || kind === 'placa' || kind === 'liso') {
    const h = (kind === 'tijolo' ? H_TIJOLO : H_PLACA) - .01;
    const box = new RoundedBoxGeometry(w, h, d, 2, CHANFRO).translate(0, h / 2, 0);
    g = juntar([box, ...(kind === 'liso' ? [] : pinos(n, m, h, PINO_R))]);
  } else if (kind === 'redondo' || kind === 'botao') {
    const h = (kind === 'redondo' ? H_TIJOLO : H_PLACA) - .01, r = n / 2 - .03;
    const p = [[0, 0], [r - .05, 0], [r, .05], [r, h - .05], [r - .05, h], [0, h]].map(([x, y]) => new THREE.Vector2(x, y));
    g = juntar([new THREE.LatheGeometry(p, 28), ...pinos(1, 1, h - .005, n > 1 ? .55 : PINO_R)]);
  } else if (kind === 'telha') {
    const h = H_TIJOLO - .01, L = n - FOLGA, s = new THREE.Shape();
    s.moveTo(-L / 2, 0); s.lineTo(L / 2, 0); s.lineTo(L / 2, .3); s.lineTo(-L / 2 + 1, h); s.lineTo(-L / 2, h); s.closePath();
    const ex = new THREE.ExtrudeGeometry(s, { depth: d - .06, bevelEnabled: true, bevelThickness: .03, bevelSize: .03, bevelSegments: 1 }).translate(0, 0, -(d - .06) / 2);
    ex.computeVertexNormals();
    g = juntar([ex, ...pinos(1, m, h, PINO_R).map(p => p.translate(-L / 2 + .5 + (n - 1) / 2 - (n - 1) / 2, 0, 0))]);
  } else if (kind === 'pneu') {
    const R = n || 2.6, W = 1, p = [[R * .58, -W], [R * .88, -W], [R * .97, -W * .85], [R, -W * .5], [R, W * .5], [R * .97, W * .85], [R * .88, W], [R * .58, W]];
    g = juntar([new THREE.LatheGeometry(p.map(([x, y]) => new THREE.Vector2(x, y)), 40)]);
  } else if (kind === 'aro') {
    const R = n || 1.55, p = [[0, -1.02], [R - .05, -1.02], [R, -.95], [R, .9], [R - .08, 1.02], [R * .62, 1.04], [R * .48, 1.16], [R * .3, 1.22], [0, 1.24]];
    g = juntar([new THREE.LatheGeometry(p.map(([x, y]) => new THREE.Vector2(x, y)), 32)]);
  } else throw new Error('peça desconhecida: ' + tipo);
  g.computeBoundingSphere();
  GEO.set(tipo, g); return g;
}

// ───────────────────────── peças, modelos por voxels e "rigs" (articulações) ─────────────────────────
/**
 * Uma peça. o: {tipo, cor, fam, pos:[x,y,z] (no espaço do rig), rot:[rx,ry,rz] | rotY, grupo, rig, obj (Object3D em vez de instância),
 *   esc: escala da peça (número ou [sx,sy,sz]; ex. 1/1.4 para peças menores que o passo da placa-base)}
 * Sem montes/programa ela fica fixa no lugar (cenário feito de peças).
 */
export function peca(o) {
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(...(o.rot || [0, o.rotY || 0, 0])));
  return { tipo: o.tipo, cor: o.cor, fam: o.fam || 'abs', P: V3(o.pos), qP: q, grupo: o.grupo || 'modelo', rig: o.rig || null, obj: o.obj || null, chave: o.chave || o.cor, tam: o.tam ?? tamDe(o.tipo), esc: o.esc ?? 1 };
}
const tamDe = tipo => { const m = /(\d+)x(\d+)/.exec(tipo || ''); return m ? +m[1] * +m[2] : 4; };
const escMedia = e => (Array.isArray(e) ? (e[0] + e[1] + e[2]) / 3 : e ?? 1);

/**
 * Modelo a partir de uma grade de voxels (1 voxel = 1×1 pino × 1 camada).
 * o: {dim:[X,Y,Z], forma:(x,y,z)=>chave|null, cores:{chave: '#hex' | {cor, fam, tipo:'redondo'|'liso'|'placa'}},
 *     alturas:[altura de cada camada] (padrão 1,2 = tijolo; 0,4 = placa), origem:[x,y,z] (centro do voxel 0 em x/z, base em y),
 *     oco:true (só a casca visível), grupo:(x,y,z,chave)=>nome, rig:nome | (x,y,z,chave)=>nome, max:4 (peça mais longa),
 *     escala: 1 (tamanho de cada peça e do passo da grade; 1/1.4 = grade 1,4× mais fina com o objeto do mesmo tamanho no mundo)}
 * Cobre cada camada com 1x1/1x2/1x3/1x4 na direção da sequência mais longa e desencontra as juntas em camadas ímpares.
 */
export function modelo(o) {
  const [X, Y, Z] = o.dim, alt = o.alturas || [], hy = y => alt[y] ?? H_TIJOLO, [ox, oy, oz] = o.origem || [0, 0, 0], sE = o.escala ?? 1;
  const y0s = []; let acc = 0; for (let y = 0; y < Y; y++) { y0s.push(acc); acc += hy(y); }
  const id = (x, y, z) => (y * Z + z) * X + x, dentro = (x, y, z) => x >= 0 && y >= 0 && z >= 0 && x < X && y < Y && z < Z;
  const G = new Array(X * Y * Z).fill(null);
  for (let y = 0; y < Y; y++) for (let z = 0; z < Z; z++) for (let x = 0; x < X; x++) G[id(x, y, z)] = o.forma(x, y, z) || null;
  const get = (x, y, z) => (dentro(x, y, z) ? G[id(x, y, z)] : null);
  const info = k => { const c = o.cores?.[k] ?? COR[k] ?? k; return typeof c === 'object' ? c : { cor: c }; };
  const transp = k => !!k && info(k).fam === 'vidro';
  const opaco = (x, y, z) => { const k = get(x, y, z); return !!k && !transp(k); };
  const gr = (x, y, z, k) => (o.grupo ? o.grupo(x, y, z, k) : 'modelo');
  const rg = (x, y, z, k) => (typeof o.rig === 'function' ? o.rig(x, y, z, k) : o.rig || null);
  const keep = new Uint8Array(X * Y * Z), used = new Uint8Array(X * Y * Z);
  for (let y = 0; y < Y; y++) for (let z = 0; z < Z; z++) for (let x = 0; x < X; x++) {
    const k = G[id(x, y, z)]; if (!k) continue;
    keep[id(x, y, z)] = o.oco === false || transp(k) || !opaco(x + 1, y, z) || !opaco(x - 1, y, z) || !opaco(x, y + 1, z) || !opaco(x, y - 1, z) || !opaco(x, y, z + 1) || !opaco(x, y, z - 1) ? 1 : 0;
  }
  const pecas = [];
  for (let y = 0; y < Y; y++) for (let z = 0; z < Z; z++) for (let x = 0; x < X; x++) {
    const i = id(x, y, z), k = G[i]; if (!k || !keep[i] || used[i]) continue;
    const inf = info(k), g = gr(x, y, z, k), r = rg(x, y, z, k);
    const igual = (a, b, c) => dentro(a, b, c) && G[id(a, b, c)] === k && keep[id(a, b, c)] && !used[id(a, b, c)] && gr(a, b, c, k) === g && rg(a, b, c, k) === r;
    let n = 1, dir = 'x';
    if (inf.tipo !== 'redondo' && inf.tipo !== 'botao') {
      let rx = 1; while (igual(x + rx, y, z)) rx++;
      let rz = 1; while (igual(x, y, z + rz)) rz++;
      dir = rx > rz ? 'x' : rz > rx ? 'z' : (y % 2 ? 'z' : 'x');
      const run = dir === 'x' ? rx : rz, ant = dir === 'x' ? get(x - 1, y, z) : get(x, y, z - 1);
      let cap = o.max ?? 4; if (ant !== k && y % 2) cap = Math.min(cap, 2);
      n = Math.min(run, cap);
    }
    for (let s = 0; s < n; s++) used[dir === 'x' ? id(x + s, y, z) : id(x, y, z + s)] = 1;
    const kind = inf.tipo || (hy(y) < .8 ? 'placa' : 'tijolo');
    const cx = ox + (x + (dir === 'x' ? (n - 1) / 2 : 0)) * sE, cz = oz + (z + (dir === 'z' ? (n - 1) / 2 : 0)) * sE;
    pecas.push(peca({ tipo: `${kind}-1x${n}`, cor: inf.cor, fam: inf.fam, pos: [cx, oy + y0s[y] * sE, cz], rotY: dir === 'z' ? Math.PI / 2 : 0, grupo: g, rig: r, chave: k, esc: sE }));
  }
  return pecas;
}

/**
 * Forma a partir de CAMADAS EM TEXTO (para modelos pequenos desenhados à mão).
 * lista[y] = texto com uma linha por z e um caractere por x; legenda {'R': 'vermelho', 'W': 'branco', ...}; '.' ou espaço = vazio.
 * Devolve {dim, forma} para espalhar em modelo({...camadas(lista, legenda), cores, origem, ...}).
 */
export function camadas(lista, legenda) {
  const L = lista.map(s => s.split('\n').map(r => r.replace(/\s+$/, '')).filter(r => r.length));
  const dim = [Math.max(...L.flat().map(r => r.length)), L.length, Math.max(...L.map(c => c.length))];
  return { dim, forma: (x, y, z) => { const ch = L[y]?.[z]?.[x]; return ch && ch !== '.' && ch !== ' ' ? legenda[ch] ?? null : null; } };
}

/**
 * Articulação (rig): as peças com p.rig = nome seguem a matriz dele.  o: {pai, pos:[...], pivo:[...], fn: t => ({pos, rot})}
 * Mundo = pai · T(pos) · T(pivo) · R(rot) · T(-pivo).  Ex.: rig('onibus', {pos:[0,0,0]}); rig('carroceria', {pai:'onibus', fn: t => ({pos:[0, sobe(t), 0]})})
 */
export function rig(S, nome, o = {}) {
  const r = { nome, pai: o.pai ? S.rig[o.pai] : null, base: V3(o.pos), pivo: V3(o.pivo), rotBase: o.rot || [0, 0, 0], fn: o.fn || null, local: new THREE.Matrix4(), world: new THREE.Matrix4(), q: new THREE.Quaternion() };
  S.rig[nome] = r; S.rigs.push(r); return r;
}
const _e = new THREE.Euler(), _mA = new THREE.Matrix4(), _mB = new THREE.Matrix4(), _vS = new THREE.Vector3(), _vP = new THREE.Vector3();
function avaliarRigs(S, t) {
  for (const r of S.rigs) {
    const f = r.fn ? r.fn(t) : {}, p = f.pos || [0, 0, 0], ro = f.rot || [0, 0, 0];
    r.local.makeTranslation(r.base.x + p[0] + r.pivo.x, r.base.y + p[1] + r.pivo.y, r.base.z + p[2] + r.pivo.z);
    _e.set(r.rotBase[0] + ro[0], r.rotBase[1] + ro[1], r.rotBase[2] + ro[2]); _mA.makeRotationFromEuler(_e); r.local.multiply(_mA);
    _mB.makeTranslation(-r.pivo.x, -r.pivo.y, -r.pivo.z); r.local.multiply(_mB);
    if (r.pai) r.world.multiplyMatrices(r.pai.world, r.local); else r.world.copy(r.local);
    r.world.decompose(_vP, r.q, _vS);
  }
}

// ───────────────────────── linha do tempo: montar e desmontar ─────────────────────────
/**
 * Programa a montagem por subconjuntos e a desmontagem (ordem inversa exata → os montes voltam iguais ao quadro 0).
 * o: {grupos: {nome: [t0, t1], ...} (janela de PARTIDA de cada subconjunto, na ordem de quem monta),
 *     voo: [min, max] (s), desmonta: [t0, t1] (janela de partida da volta), vooVolta: [min, max], seed, mistura: .8 (camadas misturadas)}
 * fimMontagem/fimDesmontagem são calculados na hora (montes({voo}) re-cronometra os voos pela distância).
 */
export function programar(pecas, o) {
  const R = rng(o.seed ?? 5), [v0, v1] = o.voo || [.45, .6], [w0, w1] = o.vooVolta || [.42, .55];
  for (const [nome, [t0, t1]] of Object.entries(o.grupos)) {
    const L = pecas.filter(p => p.grupo === nome && !p.fixa);
    L.forEach(p => (p._k = p.P.y + R() * (o.mistura ?? .8) * H_TIJOLO * escMedia(p.esc) + p.P.x * .002));
    L.sort((a, b) => a._k - b._k);
    L.forEach((p, i) => { p.a0 = lerp(t0, t1, L.length > 1 ? i / (L.length - 1) : 0) + (R() - .5) * .03; p.a1 = p.a0 + lerp(v0, v1, R()); });
  }
  const todas = pecas.filter(p => p.a0 !== undefined).sort((a, b) => a.a0 - b.a0), N = todas.length, [d0, d1] = o.desmonta;
  todas.forEach((p, i) => { p.ordem = i; p.b0 = lerp(d0, d1, N > 1 ? (N - 1 - i) / (N - 1) : 0); p.b1 = p.b0 + lerp(w0, w1, R()); });
  return { total: N, get fimMontagem() { return Math.max(...todas.map(p => p.a1)); }, get fimDesmontagem() { return Math.max(...todas.map(p => p.b1)); } };
}

/**
 * Montes de origem sobre a placa-base. defs: [{x, z, chaves:[...], raio?, pilha?:true (empilhado, ex. pneus), rot?:[..] (pose fixa), resto?:true}]
 * Cada peça programada vai para o monte mais próximo que aceita a chave dela; quem sai primeiro fica no topo,
 * então o monte vai baixando durante a montagem e cresce de volta na desmontagem. o.sobra = fração de peças extras que nunca saem.
 * o.voo / o.vooVolta: [min, max] → a duração de cada voo passa a ser proporcional à distância horizontal até o monte
 * (velocidade parecida → as peças que saem do mesmo monte formam uma fita contínua, não uma nuvem).
 * Devolve as peças extras (adicione-as à lista antes de instanciar).
 */
export function montes(pecas, defs, o = {}) {
  const R = rng(o.seed ?? 11), extras = [], sobra = o.sobra ?? .12;
  const lista = defs.map(d => ({ ...d, pecas: [] }));
  for (const p of pecas) {
    if (p.a0 === undefined) continue;
    const ok = lista.filter(d => d.chaves?.includes(p.chave)), cand = ok.length ? ok : lista.filter(d => d.resto);
    if (!cand.length) throw new Error('sem monte para a chave ' + p.chave);
    let best = cand[0], bd = Infinity; for (const d of cand) { const dd = (d.x - p.P.x) ** 2 + (d.z - p.P.z) ** 2; if (dd < bd) { bd = dd; best = d; } }
    best.pecas.push(p);
  }
  for (const d of lista) {
    const L = d.pecas.sort((a, b) => a.a0 - b.a0), nEx = d.pilha ? 0 : Math.round(L.length * (d.sobra ?? sobra));
    for (let i = 0; i < nEx; i++) { const m = L[Math.floor(R() * L.length)]; const e = { ...m, P: m.P.clone(), qP: m.qP.clone(), a0: undefined, a1: undefined, b0: undefined, b1: undefined, obj: null, extra: true }; extras.push(e); }
    const sm = L.length ? L.reduce((a, p) => a + escMedia(p.esc), 0) / L.length : 1;
    const tot = L.length + nEx, Rr = d.raio ?? (1.05 * Math.cbrt(tot) + 1.2) * sm, hmax = Rr * (d.altura ?? .6);
    let pos;
    if (d.pilha) pos = L.map((_, i) => [d.x + (R() - .5) * .3, (L.length - 1 - i) * (d.passo ?? 2.05) + (d.y0 ?? 0), d.z + (R() - .5) * .3]);
    else {
      // pontos dentro de um cone; "nível" λ = r/R + y/h: tirar primeiro os de λ maior deixa sempre um cone menor (o monte encolhe sem virar anel)
      pos = [];
      for (let i = 0; i < tot; i++) {
        const r = Rr * Math.sqrt(R()), a = R() * Math.PI * 2, y = hmax * (1 - r / Rr) * R();
        pos.push([d.x + r * Math.cos(a), y, d.z + r * Math.sin(a), r / Rr + y / hmax]);
      }
      pos.sort((a, b) => b[3] - a[3]);
    }
    const todos = [...L, ...extras.slice(extras.length - nEx)];
    todos.forEach((p, i) => {
      p.H = new THREE.Vector3(...pos[i]);
      p.qH = new THREE.Quaternion().setFromEuler(new THREE.Euler(...(d.rot || (d.pilha ? [0, R() * 6.28, 0] : [(R() - .5) * 1.3, R() * 6.28, (R() - .5) * 1.3]))));
    });
  }
  if (o.voo || o.vooVolta) {                                             // voo proporcional à distância (fita contínua)
    const L = pecas.filter(p => p.H && p.a0 !== undefined), dh = p => Math.hypot(p.H.x - p.P.x, p.H.z - p.P.z);
    const ds = L.map(dh), d0 = Math.min(...ds), d1 = Math.max(...ds);
    L.forEach((p, i) => {
      const k = d1 > d0 ? (ds[i] - d0) / (d1 - d0) : .5, j = (R() - .5) * .04;
      if (o.voo) p.a1 = p.a0 + lerp(o.voo[0], o.voo[1], k) + j;
      if (o.vooVolta) p.b1 = p.b0 + lerp(o.vooVolta[0], o.vooVolta[1], k) + j;
    });
  }
  return extras;
}

// ───────────────────────── instanciar: InstancedMesh por tipo/família + atualização por quadro ─────────────────────────
const _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _qs = new THREE.Quaternion(), _m = new THREE.Matrix4(), _one = new THREE.Vector3(1, 1, 1), _sc = new THREE.Vector3();
const _tp = new THREE.Vector3(), _tq = new THREE.Quaternion(), _b1 = new THREE.Vector3(), _b2 = new THREE.Vector3();
/**
 * Cria as malhas instanciadas (uma por tipo × família, com cor por instância) e registra a animação.
 * o: {centro:[x,y,z] (centro do objeto, para o "estouro" da desmontagem), seed, quique:.3, variacao:.035 (variação de tom por peça),
 *     arco:.7 (altura do arco de ida = arco × distância horizontal monte→lugar; arcos altos = fita que passa POR CIMA do objeto)}
 */
export function instanciar(S, pecas, o = {}) {
  const R = rng(o.seed ?? 23), centro = V3(o.centro || [0, 5, 0]);
  S.pecas = pecas;
  avaliarRigs(S, 0);
  const grupos = new Map();
  for (const p of pecas) { if (p.obj) { S.scene.add(p.obj); continue; } const k = p.tipo + '|' + p.fam; if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(p); }
  const cor = new THREE.Color(), malhas = [];
  for (const [k, L] of grupos) {
    const [tipo, fam] = k.split('|');
    const mesh = new THREE.InstancedMesh(geoPeca(tipo), S.mats[fam], L.length);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.castShadow = fam !== 'vidro'; mesh.receiveShadow = true; mesh.frustumCulled = false;
    L.forEach((p, i) => { p.mesh = mesh; p.idx = i; cor.set(p.cor); const v = 1 + (R() - .5) * 2 * (o.variacao ?? .035); cor.multiplyScalar(v); mesh.setColorAt(i, cor); });
    mesh.instanceColor.needsUpdate = true; S.scene.add(mesh); malhas.push(mesh);
  }
  // parâmetros de voo de cada peça (arco, giro, estouro)
  for (const p of pecas) {
    if (!p.H || p.a0 === undefined) continue;
    _tp.copy(p.P); if (p.rig) _tp.applyMatrix4(S.rig[p.rig].world);
    const dist = p.H.distanceTo(_tp), dh = Math.hypot(p.H.x - _tp.x, p.H.z - _tp.z);
    p.arco = 2 + (o.arco ?? .7) * dh + Math.max(0, _tp.y - p.H.y) * .3 + R() * 2.5;
    p.arco2 = 3 + .3 * dist + R() * 4;
    p.eixo = new THREE.Vector3(R() - .5, R() - .5, R() - .5).normalize(); p.giro = (1.2 + R() * 2.4) * Math.PI * (R() < .5 ? -1 : 1);
    const out = new THREE.Vector3(_tp.x - centro.x, 0, _tp.z - centro.z); if (out.lengthSq() < .01) out.set(R() - .5, 0, R() - .5);
    out.normalize().multiplyScalar(2 + R() * 5); out.y = 3 + R() * 5 + Math.max(0, _tp.y - centro.y) * .3; p.estouro = out;
  }
  for (const p of pecas) { const e = p.esc ?? 1; p._s = Array.isArray(e) ? new THREE.Vector3(...e) : new THREE.Vector3(e, e, e); if (p.obj) p.obj.scale.copy(p._s); }
  const Q = o.quique ?? .3;
  S.cada(t => {
    avaliarRigs(S, t);
    for (const p of pecas) {
      const r = p.rig ? S.rig[p.rig] : null;
      const alvo = () => { _tp.copy(p.P); _tq.copy(p.qP); if (r) { _tp.applyMatrix4(r.world); _tq.premultiply(r.q); } };
      if (!p.H) { alvo(); _p.copy(_tp); _q.copy(_tq); }
      else if (p.a0 === undefined || t < p.a0 || t >= p.b1) {
        _p.copy(p.H); _q.copy(p.qH);
        if (p.b1 !== undefined && t >= p.b1 && t - p.b1 < .2) { const s = t - p.b1; _p.y += Q * .5 * Math.exp(-s * 30) * Math.abs(Math.sin(s * 40)); }
      } else if (t < p.a1) {                                           // voo de ida: arco + giro, chega de cima
        alvo(); const k = (t - p.a0) / (p.a1 - p.a0), e = 1 - (1 - k) * (1 - k);
        _p.lerpVectors(p.H, _tp, e); _p.y += p.arco * 4 * e * (1 - e);
        _q.slerpQuaternions(p.qH, _tq, suave(k)); _qs.setFromAxisAngle(p.eixo, p.giro * Math.sin(Math.PI * k)); _q.multiply(_qs);
      } else if (t < p.b0) {                                           // no lugar (com o "assentar" do encaixe)
        alvo(); _p.copy(_tp); _q.copy(_tq); const s = t - p.a1; if (s < .25) _p.y += Q * Math.exp(-s * 26) * Math.abs(Math.sin(s * 36));
      } else {                                                         // volta: estoura para fora e para cima, cai no monte
        alvo(); const k = (t - p.b0) / (p.b1 - p.b0), e = Math.pow(k, 1.15), u = 1 - e;
        _b1.copy(_tp).add(p.estouro); _b2.copy(p.H); _b2.y += p.arco2;
        _p.copy(_tp).multiplyScalar(u * u * u).addScaledVector(_b1, 3 * u * u * e).addScaledVector(_b2, 3 * u * e * e).addScaledVector(p.H, e * e * e);
        _q.slerpQuaternions(_tq, p.qH, suave(k)); _qs.setFromAxisAngle(p.eixo, -p.giro * Math.sin(Math.PI * k)); _q.multiply(_qs);
      }
      if (p.obj) { p.obj.position.copy(_p); p.obj.quaternion.copy(_q); }
      else { _m.compose(_p, _q, p._s || _one); p.mesh.setMatrixAt(p.idx, _m); }
    }
    for (const m of malhas) m.instanceMatrix.needsUpdate = true;
  });
  return malhas;
}

/** contador de peças: sobe quando a peça encaixa no modelo e desce quando ela POUSA de volta no monte (chega a 0 com a nuvem já no chão) */
export function contar(pecas) {
  const ch = pecas.filter(p => p.a1 !== undefined).map(p => p.a1).sort((a, b) => a - b), sa = pecas.filter(p => p.b1 !== undefined).map(p => p.b1).sort((a, b) => a - b);
  const ate = (L, t) => { let lo = 0, hi = L.length; while (lo < hi) { const m = (lo + hi) >> 1; if (L[m] <= t) lo = m + 1; else hi = m; } return lo; };
  return t => ate(ch, t) - ate(sa, t);
}

/**
 * Marca o som de cada peça (o synth.py lê de cues.json): 'sai' ao decolar do monte, 'clique' ao encaixar, 'solta' ao soltar, 'cai' ao voltar ao monte.
 * proj(t, v) → x de tela em [-1, 1] (para o pan). Peças grandes soam mais graves; vidro mais agudo; borracha abafada.
 */
export function sons(S, pecas, proj) {
  const v = new THREE.Vector3();
  for (const p of pecas) {
    if (p.a1 === undefined) continue;
    v.copy(p.P); if (p.rig) v.applyMatrix4(S.rig[p.rig].world);
    const pan = +clamp(proj(p.a1, v) * .8, -.9, .9).toFixed(2), panV = +clamp(proj(p.b1, p.H) * .8, -.9, .9).toFixed(2);
    const base = { tam: p.tam, mat: p.fam };
    if (p.H) cue('sai', +p.a0.toFixed(3), { ...base, pan: +clamp(proj(p.a0, p.H) * .8, -.9, .9).toFixed(2), g: .5 });
    cue('clique', +p.a1.toFixed(3), { ...base, pan, g: 1 });
    cue('solta', +p.b0.toFixed(3), { ...base, pan, g: .5 });
    cue('cai', +p.b1.toFixed(3), { ...base, pan: panV, g: .55 });
  }
}

// ───────────────────────── peças especiais e personagem ─────────────────────────
/** adesivo impresso (decalque) desenhado em canvas: plano w×h unidades, face para +z. draw(ctx, W, H) */
export function adesivo(w, h, draw, o = {}) {
  const W = o.res ?? 1024, Hh = Math.round(W * h / w), c = document.createElement('canvas'); c.width = W; c.height = Hh;
  draw(c.getContext('2d'), W, Hh);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; tx.anisotropy = 8;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshPhysicalMaterial({ map: tx, transparent: true, roughness: .35, clearcoat: .6, polygonOffset: true, polygonOffsetFactor: -2 }));
  const verso = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ color: o.verso || '#eeece6', roughness: .8, transparent: true, opacity: .97 }));
  verso.rotation.y = Math.PI; verso.position.z = -.01; m.add(verso);                 // verso de papel (o texto não aparece espelhado ao girar)
  m.userData.ao = false; m.castShadow = false; m.receiveShadow = true; return m;
}

/**
 * Cola um objeto (adesivo, placa, letreiro) NO LUGAR, sem voar: escala 0→1 com sobra e um flash, e descola (1→0) na desmontagem.
 * Use para o que fica na face externa de um objeto já fechado (voando, o decalque atravessaria a carroceria).
 * o: {rig, pos:[x,y,z] (no espaço do rig), rot:[...], entra: t, dur: .16, sai: t, flash: 1.2}. Chame DEPOIS de instanciar().
 */
export function colar(S, obj, o = {}) {
  const P = V3(o.pos), q0 = new THREE.Quaternion().setFromEuler(new THREE.Euler(...(o.rot || [0, 0, 0]))), dur = o.dur ?? .16;
  const mats = []; obj.traverse(m => { if (m.material?.emissive) mats.push(m.material); });
  for (const m of mats) m.emissive.set('#ffffff');
  S.scene.add(obj);
  const sobra = k => { const c = 2.2; return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2; };   // ease-out-back
  S.cada(t => {
    avaliarRigs(S, t);
    const r = o.rig ? S.rig[o.rig] : null; obj.position.copy(P); obj.quaternion.copy(q0);
    if (r) { obj.position.applyMatrix4(r.world); obj.quaternion.premultiply(r.q); }
    const ki = fase(t, o.entra, o.entra + dur), ko = o.sai !== undefined ? fase(t, o.sai, o.sai + .1) : 0;
    const s = ki <= 0 ? 0 : sobra(ki) * (1 - suave(ko));
    obj.visible = s > .002; obj.scale.setScalar(Math.max(s, .001));
    const fl = (o.flash ?? 1.2) * janela(t, o.entra + dur * .4, o.entra + dur * .7, o.entra + dur * .9, o.entra + dur + .3);
    for (const m of mats) m.emissiveIntensity = fl;
  });
  return obj;
}

/** roda = pneu + aro (2 peças). lado: +1 (calota para +z) ou -1. o: {raio, aro, cor, rig, grupo, esc} */
export function roda(pos, lado = 1, o = {}) {
  const rot = [lado * Math.PI / 2, 0, 0];
  return [
    peca({ tipo: `pneu-1x${o.raio ?? 2.6}`, cor: o.pneu || COR.preto, fam: 'borracha', pos, rot, grupo: o.grupo || 'rodas', rig: o.rig, chave: 'pneu', tam: 30, esc: o.esc }),
    peca({ tipo: `aro-1x${o.aro ?? 1.55}`, cor: o.cor || COR.branco, fam: o.fam || 'abs', pos, rot, grupo: o.grupo || 'rodas', rig: o.rig, chave: 'aro', tam: 12, esc: o.esc }),
  ];
}

/**
 * Bonequinho feito de peças (NÃO é a minifigura oficial: corpo de tijolos 4×2, cabeça quadrada, capacete de placa).
 * o: {nome, pos:[x,0,z], rotY, pele, camisa, colete, calca, botina, capacete, bigode:true}
 * Cria os rigs  nome, nome.cabeca, nome.bracoE, nome.bracoD  (anime com S.rig['nome.bracoD'].fn = t => ({rot:[...]}))
 */
export function boneco(S, o = {}) {
  const n = o.nome || 'boneco', c = { pele: o.pele || COR.pele[2], camisa: o.camisa || '#e9e6df', colete: o.colete || COR.laranja, faixa: '#dfe3e6', calca: o.calca || COR.jeans, botina: o.botina || '#3a2a20', capacete: o.capacete || COR.amarelo, cinto: '#5b3b24' };
  rig(S, n, { pos: o.pos || [0, 0, 0], rot: [0, o.rotY || 0, 0], fn: o.fn });
  const yOmbro = 6 * H_TIJOLO;
  rig(S, n + '.cabeca', { pai: n, pivo: [2.5, yOmbro, 1.5] });
  rig(S, n + '.bracoE', { pai: n, pivo: [0, yOmbro - .3, 1.5] });
  rig(S, n + '.bracoD', { pai: n, pivo: [5, yOmbro - .3, 1.5] });
  const alturas = [1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, .4, 1.2];
  const forma = (x, y, z) => {
    const bx = x - 1, bz = z - 1, corpo = bx >= 0 && bx <= 3 && bz >= 0 && bz <= 1, braco = (x === 0 || x === 5) && bz >= 0 && bz <= 1;
    if (y === 0) return corpo ? 'botina' : null;
    if (y <= 2) return corpo ? 'calca' : null;
    if (y === 3) return corpo ? 'cinto' : braco && bz === 1 ? 'pele' : braco ? 'camisa' : null;
    if (y === 4) return corpo ? (bz === 1 && (bx === 1 || bx === 2) ? 'camisa' : 'faixa') : braco ? 'camisa' : null;
    if (y === 5) return corpo ? (bz === 1 && (bx === 1 || bx === 2) ? 'camisa' : 'colete') : braco ? 'colete' : null;
    if (y === 6 || y === 7) return corpo ? 'pele' : null;
    if (y === 8) return x >= 0 && x <= 5 && z >= 0 && z <= 3 ? 'capacete' : null;
    if (y === 9) return corpo ? 'capacete' : null;
    return null;
  };
  const pc = modelo({ dim: [6, 10, 4], alturas, forma, cores: c, origem: [0, 0, 0], max: 4, oco: false, grupo: () => 'boneco',
    rig: (x, y) => (y >= 6 ? n + '.cabeca' : (x === 0 && y >= 3 && y <= 5) ? n + '.bracoE' : (x === 5 && y >= 3 && y <= 5) ? n + '.bracoD' : n) });
  const yC = 6 * H_TIJOLO, frente = 2.5 + .02, rx = [Math.PI / 2, 0, 0];
  for (const ex of [1.72, 3.28]) {                                       // olhos: placa redonda branca + pupila pequena + sobrancelha
    pc.push(peca({ tipo: 'botao-1x1', cor: '#fbfaf6', pos: [ex, yC + 1.42, frente], rot: rx, rig: n + '.cabeca', grupo: 'boneco', esc: .82 }));
    pc.push(peca({ tipo: 'botao-1x1', cor: COR.preto, pos: [ex + (ex < 2.5 ? .08 : -.08), yC + 1.36, frente + .3], rot: rx, rig: n + '.cabeca', grupo: 'boneco', esc: [.4, .5, .4] }));
    pc.push(peca({ tipo: 'liso-1x1', cor: '#2a1d16', pos: [ex, yC + 2.18, frente - .02], rot: [Math.PI / 2, ex < 2.5 ? .1 : -.1, 0], rig: n + '.cabeca', grupo: 'boneco', esc: [.9, .6, .26] }));
  }
  if (o.bigode !== false) pc.push(peca({ tipo: 'liso-1x2', cor: '#2a1d16', pos: [2.5, yC + .62, frente - .03], rot: rx, rig: n + '.cabeca', grupo: 'boneco' }));
  pc.push(peca({ tipo: 'liso-1x2', cor: '#c94a3a', pos: [2.5, yC + .22, frente - .08], rot: rx, rig: n + '.cabeca', grupo: 'boneco' }));
  return pc;
}

// ───────────────────────── cenário: placa-base, rua, cidade pastel, céu ─────────────────────────
function tela2d(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); return c; }
function texJanelas(parede, vidro = '#bcd3e6') {
  const c = tela2d(64, 64, (g, w, h) => {
    g.fillStyle = parede; g.fillRect(0, 0, w, h);
    g.fillStyle = 'rgba(0,0,0,.06)'; g.fillRect(0, 56, w, 8);
    g.fillStyle = '#f7f5ef'; g.fillRect(15, 13, 34, 32);
    g.fillStyle = vidro; g.fillRect(18, 16, 28, 26);
    g.fillStyle = 'rgba(40,60,90,.18)'; g.fillRect(18, 30, 28, 12);
    g.fillStyle = '#f7f5ef'; g.fillRect(31, 16, 2, 26);
  });
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.magFilter = THREE.LinearFilter; t.anisotropy = 4; return t;
}
/** placa-base verde cheia de pinos com o topo em y = 0. o: {w, d (em pinos), cor, x, z, escala (passo do pino; use a mesma das peças)} */
export function placaBase(S, o = {}) {
  const e = o.escala ?? 1, w = o.w ?? 84, d = o.d ?? 60, cor = o.cor || CENA.placa, g = new THREE.Group();
  const mat = new THREE.MeshPhysicalMaterial({ color: cor, roughness: .38, clearcoat: .35, clearcoatRoughness: .3 });
  const base = new THREE.Mesh(new RoundedBoxGeometry(w * e, .5, d * e, 2, .1), mat); base.position.y = -.25; base.receiveShadow = true; base.castShadow = true; g.add(base);
  // No lugar do campo de pinos, um sulco de grade bem discreto: dá a leitura de placa modular
  // sem copiar o relevo registrado.
  const gc = document.createElement('canvas'); gc.width = gc.height = 64;
  const gg = gc.getContext('2d');
  gg.fillStyle = '#ffffff'; gg.fillRect(0, 0, 64, 64);
  gg.strokeStyle = 'rgba(0,0,0,.055)'; gg.lineWidth = 2;
  gg.strokeRect(1, 1, 62, 62);
  const gt = new THREE.CanvasTexture(gc); gt.wrapS = gt.wrapT = THREE.RepeatWrapping;
  gt.repeat.set(w, d); gt.anisotropy = 4;
  base.material = new THREE.MeshPhysicalMaterial({ color: cor, map: gt, roughness: .42,
    clearcoat: .3, clearcoatRoughness: .35 });
  g.position.set(o.x ?? 0, 0, o.z ?? 0); S.scene.add(g); return g;
}
/**
 * Cidade de brinquedo em volta: chão cinza-claro, rua de asfalto com faixas, calçadas, postes, prédios pastel low-poly
 * com janelinhas e caixas-d'água, céu azul-claro com nuvens em blocos e névoa clara de distância.
 * o: {rua:{z, largura}, ruas:[...], seed, nevoa:[perto, longe] (padrão 140–600), predios:{z0, n}, cores:{chao, asfalto, predios:[...], ...} (sobrepõe CENA)}
 */
const CENA_BASE = CENA;
export function cidade(S, o = {}) {
  const R = rng(o.seed ?? 31), sc = S.scene, nev = o.nevoa || [140, 600], CENA = { ...CENA_BASE, ...(o.cores || {}) };
  sc.fog = new THREE.Fog(CENA.horizonte, nev[0], nev[1]);
  const lam = (cor, ex = {}) => new THREE.MeshStandardMaterial({ color: cor, roughness: .92, metalness: 0, ...ex });
  const plano = (w, d, cor, y, x = 0, z = 0) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), typeof cor === 'string' ? lam(cor) : cor); m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); m.receiveShadow = true; sc.add(m); return m; };
  plano(5000, 5000, CENA.chao, -.5);
  // ruas (eixo x) + faixas + calçadas: a principal (o.rua) e outras paralelas (o.ruas)
  const rz = o.rua?.z ?? 50, rl = o.rua?.largura ?? 26, calc = lam(CENA.calcada);
  for (const r of [{ z: rz, largura: rl }, ...(o.ruas || [])]) {
    const z = r.z, l = r.largura ?? rl;
    plano(5000, l, CENA.asfalto, -.46, 0, z);
    plano(5000, .9, CENA.faixa, -.44, 0, z - l / 2 + 1.4); plano(5000, .9, CENA.faixa, -.44, 0, z + l / 2 - 1.4);
    for (let x = -400; x < 400; x += 12) plano(6, .9, CENA.faixa, -.44, x, z);
    for (const s of [-1, 1]) { const c = new THREE.Mesh(new THREE.BoxGeometry(5000, .5, 4), calc); c.position.set(0, -.3, z + s * (l / 2 + 2)); c.receiveShadow = true; sc.add(c); }
  }
  // rua transversal
  if (o.transversal !== false) { const tx = o.transversalX ?? 150; plano(rl, 5000, CENA.asfalto, -.455, tx, 0); for (let z = -600; z < rz - rl; z += 12) plano(.9, 6, CENA.faixa, -.435, tx, z); }
  // postes ao longo da rua
  const poste = lam('#8d949a', { roughness: .6, metalness: .3 });
  for (let x = -260; x <= 260; x += 52) {
    if (Math.abs(x) < (o.semPostes ?? 60)) continue;
    const g = new THREE.Group(), h = 22;
    const p = new THREE.Mesh(new THREE.CylinderGeometry(.35, .45, h, 8), poste); p.position.y = h / 2; g.add(p);
    const b = new THREE.Mesh(new THREE.BoxGeometry(.5, .5, 5), poste); b.position.set(0, h - .3, 2.3); g.add(b);
    const l = new THREE.Mesh(new THREE.BoxGeometry(1.4, .5, 2), lam('#e9ecee')); l.position.set(0, h - .6, 4.5); g.add(l);
    g.position.set(x, 0, rz + rl / 2 + 3); g.rotation.y = Math.PI; g.traverse(m => (m.castShadow = true)); sc.add(g);
  }
  // prédios pastel com janelinhas (fora de um retângulo livre em volta da cena)
  const livre = o.livre || { x: [-95, 95], z: [-80, rz + rl / 2 + 10] };
  const nP = o.predios?.n ?? 70, cores = CENA.predios, texs = cores.map(c => texJanelas(c));
  const topo = cores.map(c => lam(new THREE.Color(c).multiplyScalar(.93)));
  for (let i = 0, tent = 0; i < nP && tent < 2000; tent++) {
    const x = (R() - .5) * 1000, z = -(o.predios?.z0 ?? 110) - R() * 560, w = 28 + R() * 40, d = 26 + R() * 30, h = 34 + R() * 95;
    if (x + w / 2 > livre.x[0] && x - w / 2 < livre.x[1] && z + d / 2 > livre.z[0] && z - d / 2 < livre.z[1]) continue;
    if (Math.abs(x - (o.transversalX ?? 150)) < w / 2 + rl / 2 + 4) continue;
    const ci = Math.floor(R() * cores.length), tx = texs[ci];
    const mk = (rx, ry) => { const t = tx.clone(); t.repeat.set(Math.max(1, Math.round(rx / 6.5)), Math.max(1, Math.round(ry / 7))); t.needsUpdate = true; return lam('#ffffff', { map: t }); };
    const mats = [mk(d, h), mk(d, h), topo[ci], topo[ci], mk(w, h), mk(w, h)];
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mats); b.position.set(x, h / 2 - .5, z); b.receiveShadow = true; sc.add(b);
    const cor = new THREE.Mesh(new THREE.BoxGeometry(w + 1, 1.6, d + 1), topo[ci]); cor.position.set(x, h - .5, z); sc.add(cor);
    if (R() < .7) { const cx = new THREE.Mesh(new THREE.CylinderGeometry(3, 3.4, 4, 10), lam('#5f8fc4', { roughness: .5 })); cx.position.set(x + (R() - .5) * w * .5, h + 2, z + (R() - .5) * d * .5); sc.add(cx); }
    if (R() < .5) { const ca = new THREE.Mesh(new THREE.BoxGeometry(6 + R() * 6, 4, 6 + R() * 5), lam('#e7e4dd')); ca.position.set(x - (R() - .5) * w * .4, h + 2, z + (R() - .5) * d * .4); sc.add(ca); }
    i++;
  }
  // céu: domo em gradiente (horizonte = cor da névoa) + nuvens em blocos
  const ceu = new THREE.Mesh(new THREE.SphereGeometry(3000, 32, 16), new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { cA: { value: new THREE.Color(CENA.ceu) }, cH: { value: new THREE.Color(CENA.horizonte) } },
    vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
    fragmentShader: 'uniform vec3 cA, cH; varying vec3 vP; void main(){ float k = smoothstep(.0, .32, vP.y); gl_FragColor = vec4(mix(cH, cA, k), 1.); }' }));
  ceu.userData.semAO = true; sc.add(ceu);
  const nuv = new THREE.MeshStandardMaterial({ color: '#ffffff', emissive: '#ffffff', emissiveIntensity: .55, roughness: 1, fog: false });
  for (let i = 0; i < (o.nuvens ?? 12); i++) {
    const g = new THREE.Group(), a = -Math.PI / 2 + (R() - .5) * 2.4, dist = 1300 + R() * 600;
    const n = 3 + Math.floor(R() * 4);
    for (let k = 0; k < n; k++) { const b = new THREE.Mesh(new THREE.BoxGeometry(60 + R() * 90, 26 + R() * 30, 40 + R() * 40), nuv); b.position.set((k - n / 2) * 55 + R() * 20, R() * 22, R() * 20); g.add(b); }
    g.position.set(Math.cos(a) * dist, 260 + R() * 320, Math.sin(a) * dist); g.lookAt(0, g.position.y, 0); g.userData.semAO = true; g.traverse(m => (m.userData.semAO = true)); sc.add(g);
  }
}

// ───────────────────────── câmera: órbita 3/4 em balanço (fecha o loop) ─────────────────────────
/**
 * o: {alvo, raio:[longe, perto], azim:[centro, amplitude, fase], elev:[centro, amplitude], fov, perto: t do ponto mais próximo, T: período}
 * Azimute 0 = câmera em +z olhando para -z; positivo gira para +x. Tudo periódico em T → loop perfeito.
 */
export function orbita(S, o) {
  const A = V3(o.alvo || [0, 0, 0]), T = o.T ?? window.VIDEO.dur, [r0, r1] = o.raio, [ac, aa, af = 0] = o.azim, [ec, ea = 0] = o.elev, tp = o.perto ?? T * .6;
  const f = t => {
    const k = .5 + .5 * Math.cos(2 * Math.PI * (t - tp) / T);                  // 1 no ponto mais próximo
    const r = lerp(r0, r1, k), az = (ac + aa * Math.sin(2 * Math.PI * t / T + af)) * Math.PI / 180, el = (ec + ea * (k - .5) * 2) * Math.PI / 180;
    S.camera.position.set(A.x + r * Math.cos(el) * Math.sin(az), A.y + r * Math.sin(el), A.z + r * Math.cos(el) * Math.cos(az)); S.camera.lookAt(A);
    if (o.fov && S.camera.fov !== o.fov) { S.camera.fov = o.fov; S.camera.updateProjectionMatrix(); }
    S.camera.updateMatrixWorld();
  };
  return f;
}
/** x de tela em [-1, 1] de um ponto do mundo no instante t (usa a função de câmera) */
export function projetor(S, cam) { const v = new THREE.Vector3(); return (t, p) => { cam(t); S.camera.updateMatrixWorld(); v.copy(p).project(S.camera); return v.x; }; }

/** brilho aditivo (sprite) para faróis e lâmpadas; ajuste .material.opacity por quadro */
export function brilho(cor = '#fff1c8', tam = 6) {
  const c = tela2d(128, 128, (g, w, h) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.25, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
  const t = new THREE.CanvasTexture(c);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, color: cor, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  s.scale.set(tam, tam, 1); return s;
}

// ───────────────────────── rótulo discreto (HUD) ─────────────────────────
const CSS = `
.bm-rot{position:absolute;display:flex;align-items:center;gap:22px;padding:20px 28px 20px 22px;border-radius:22px;background:rgba(255,255,255,.9);
  box-shadow:0 10px 30px rgba(30,40,60,.14);font-family:'Geist',sans-serif;color:#1d2433;z-index:5;white-space:nowrap}
.bm-ico{width:58px;height:44px;border-radius:7px;background:var(--c);position:relative;box-shadow:inset 0 -6px 0 rgba(0,0,0,.18)}
.bm-ico i{position:absolute;top:-9px;width:18px;height:11px;border-radius:5px 5px 2px 2px;background:var(--c);box-shadow:inset 0 -3px 0 rgba(0,0,0,.15)}
.bm-ico i:nth-child(1){left:7px}.bm-ico i:nth-child(2){left:33px}
.bm-l1{font:700 22px/1 'Geist',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#56607a}
.bm-l2{display:flex;align-items:baseline;gap:12px;margin-top:9px}
.bm-n{font:600 46px/1 'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;color:#1d2433}
.bm-t{font:500 24px/1 'Geist',sans-serif;color:#56607a}
.bm-e{font:700 18px/1 'Geist',sans-serif;letter-spacing:.16em;text-transform:uppercase;padding:7px 11px;border-radius:8px;color:#fff;background:var(--c);margin-left:6px}
`;
const milhar = n => String(Math.max(0, Math.round(n))).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
/**
 * o: {x, y, linha:'O Futuro é Glorioso Tour · ônibus', total, contador: t => n, estado: t => ['montando', '#cor'], cor}
 */
export function rotulo(S, o) {
  if (!document.getElementById('bm-css')) { const st = document.createElement('style'); st.id = 'bm-css'; st.textContent = CSS; document.head.appendChild(st); }
  const el = document.createElement('div'); el.className = 'bm-rot'; el.style.left = o.x + 'px'; el.style.top = o.y + 'px'; el.style.setProperty('--c', o.cor || COR.vermelho);
  // Cabecalho sem icone de tijolo e sem contagem de pecas: as duas coisas faziam a tela parecer
  // o cartao de uma caixa de brinquedo. Fica a linha do projeto e o estado da montagem.
  el.innerHTML = `<div><div class="bm-l1">${o.linha}</div><div class="bm-l2"><span class="bm-e"></span></div></div>`;
  document.getElementById('stage').appendChild(el);
  const eEl = el.querySelector('.bm-e');
  S.hud.push(t => { const [txt, c] = o.estado(t); eEl.textContent = txt; eEl.style.background = c; });
  return el;
}
