// hd2d.js — biblioteca do estilo "pixel art HD-2D" (three.js, módulo ES)
// Mundo 3D de verdade (blocos, telhados, muros, chão de pedra, árvores em volumes) vestido com texturas de PIXEL ART
// de baixa resolução (filtro nearest, rampas de cor com matiz deslocado), personagens como SPRITES 2D em billboard,
// câmera alta em 3/4 com FOV estreito, tilt-shift forte, bloom quente, névoa, raios de luz, partículas e gradação dourada.
// Uso:  import * as HD from '../../lib/hd2d.js';  const S = HD.palco({...});  S.update = t => {...}
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
export { THREE };

/** densidade de pixels: texels por metro no cenário (ppu) e pixels por metro nos sprites (ppuSprite) */
export const CFG = { ppu: 24, ppuSprite: 20 };

// ───────────────────────── utilidades determinísticas ─────────────────────────
export function rng(seed = 1) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const PERM = (() => { const r = rng(1337), p = [...Array(256).keys()]; for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; } return Uint8Array.from([...p, ...p]); })();
const GX = new Float32Array(256), GY = new Float32Array(256);
(() => { const r = rng(7); for (let i = 0; i < 256; i++) { const a = r() * Math.PI * 2; GX[i] = Math.cos(a); GY[i] = Math.sin(a); } })();
/** ruído de gradiente 2D em ~[-1,1] */
export function ruido(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi, X = xi & 255, Y = yi & 255;
  const g = (i, j, dx, dy) => { const h = PERM[PERM[X + i] + Y + j]; return GX[h] * dx + GY[h] * dy; };
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = g(0, 0, xf, yf) + u * (g(1, 0, xf - 1, yf) - g(0, 0, xf, yf));
  const b = g(0, 1, xf, yf - 1) + u * (g(1, 1, xf - 1, yf - 1) - g(0, 1, xf, yf - 1));
  return (a + v * (b - a)) * 1.4;
}
export function fbm(x, y, oct = 3) { let s = 0, a = .5, f = 1, n = 0; for (let i = 0; i < oct; i++) { s += a * ruido(x * f + i * 17.3, y * f - i * 9.1); n += a; a *= .5; f *= 2.03; } return s / n; }
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const suave = (a, b, v) => { const k = clamp((v - a) / (b - a)); return k * k * (3 - 2 * k); };
/** 0..1 entre t0 e t1 com ease do GSAP — o "relógio" de tudo */
export const fase = (t, t0, t1, ease = 'none') => gsap.parseEase(ease)(clamp((t - t0) / (t1 - t0)));
export const v3 = a => (a && a.isVector3) ? a.clone() : new THREE.Vector3(...a);
/** hash inteiro → [0,1) */
export const hash = (x, y, s = 0) => { let h = (Math.floor(x) * 374761393 + Math.floor(y) * 668265263 + s * 1442695041) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + .5) / 16);
/** limiar de pontilhado ordenado (Bayer 4x4) — o "dither" da pixel art */
export const dither = (x, y) => BAYER[((Math.floor(y) & 3) << 2) + (Math.floor(x) & 3)];

// ───────────────────────── cor e rampas (paleta de pixel art) ─────────────────────────
const CC = new Map();
/** '#rrggbb' → [r,g,b] (sRGB 0..255) */
export function cor(c) { if (Array.isArray(c)) return c; let v = CC.get(c); if (!v) { const n = parseInt(c.slice(1), 16); v = [n >> 16 & 255, n >> 8 & 255, n & 255]; CC.set(c, v); } return v; }
function rgb2hsl([r, g, b]) { r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2; if (mx === mn) return [0, 0, l]; const d = mx - mn, s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn); let h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return [h / 6, s, l]; }
function hsl2rgb(h, s, l) { const f = (p, q, t) => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < .5 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; }; if (!s) return [l * 255, l * 255, l * 255].map(Math.round); const q = l < .5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q; return [f(p, q, h + 1 / 3), f(p, q, h), f(p, q, h - 1 / 3)].map(v => Math.round(v * 255)); }
const lerpMatiz = (a, b, k) => { let d = b - a; if (d > .5) d -= 1; if (d < -.5) d += 1; return (a + d * k + 1) % 1; };
/** mistura de duas cores → [r,g,b] */
export const misturar = (a, b, k) => { a = cor(a); b = cor(b); return [0, 1, 2].map(i => Math.round(lerp(a[i], b[i], k))); };
/**
 * Rampa de pixel art: n tons do escuro ao claro, com matiz deslocado (sombras puxam p/ azul-violeta, luzes p/ amarelo).
 * o: {contraste:.32, matiz:.08}
 */
export function rampa(c, n = 5, o = {}) {
  const [h, s, l] = rgb2hsl(cor(c)), sp = o.contraste ?? .32, hs = o.matiz ?? .08;
  return Array.from({ length: n }, (_, i) => {
    const k = n === 1 ? 0 : i / (n - 1) - .5;
    const ll = clamp(l + k * sp * 2 * (k < 0 ? 1 : .8), .03, .97);
    const hh = k < 0 ? lerpMatiz(h, .7, -k * hs * 2) : lerpMatiz(h, .13, k * hs * 2);
    const ss = clamp(s * (k < 0 ? 1 - k * .25 : 1 - k * .4));
    return hsl2rgb(hh, ss, ll);
  });
}
/** cor sRGB → linear (para shaders próprios) */
export const linear = c => cor(c).map(v => Math.pow(v / 255, 2.2));

// ───────────────────────── Pixels: o pincel de pixel art ─────────────────────────
/** Tela de pixels com mapa de altura (para o normal map). Coordenadas inteiras, y para baixo. */
export class Pixels {
  constructor(w, h) { this.w = w; this.h = h; this.d = new Uint8ClampedArray(w * h * 4); this.alt = new Float32Array(w * h); this.rep = false; this.ox = 0; this.oy = 0; this.clip = null; }
  _i(x, y) {
    x = Math.floor(x + this.ox); y = Math.floor(y + this.oy);
    if (this.clip && (x < this.clip[0] || y < this.clip[1] || x >= this.clip[2] || y >= this.clip[3])) return -1;
    if (this.rep) { x = ((x % this.w) + this.w) % this.w; y = ((y % this.h) + this.h) % this.h; } else if (x < 0 || y < 0 || x >= this.w || y >= this.h) return -1;
    return y * this.w + x;
  }
  px(x, y, c, a = 255) {
    const i = this._i(x, y); if (i < 0) return this; const d = this.d, j = i * 4;
    if (c == null) { d[j + 3] = 0; return this; }
    const k = cor(c);
    if (a >= 255) { d[j] = k[0]; d[j + 1] = k[1]; d[j + 2] = k[2]; d[j + 3] = 255; }
    else { const f = a / 255; d[j] += (k[0] - d[j]) * f; d[j + 1] += (k[1] - d[j + 1]) * f; d[j + 2] += (k[2] - d[j + 2]) * f; d[j + 3] = Math.max(d[j + 3], a); }
    return this;
  }
  le(x, y) { const i = this._i(x, y); if (i < 0) return null; const j = i * 4; return this.d[j + 3] ? [this.d[j], this.d[j + 1], this.d[j + 2]] : null; }
  alfa(x, y) { const i = this._i(x, y); return i < 0 ? 0 : this.d[i * 4 + 3]; }
  a(x, y, v) { const i = this._i(x, y); if (i >= 0) this.alt[i] = v; return this; }
  rect(x, y, w, h, c, al) { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.px(x + i, y + j, c, al); return this; }
  disc(cx, cy, r, c, al) { for (let y = Math.floor(cy - r - 1); y <= cy + r + 1; y++) for (let x = Math.floor(cx - r - 1); x <= cx + r + 1; x++) if ((x - cx) ** 2 + (y - cy) ** 2 <= r * r + r * .6) this.px(x, y, c, al); return this; }
  elipse(cx, cy, rx, ry, c, al) { for (let y = Math.floor(cy - ry - 1); y <= cy + ry + 1; y++) for (let x = Math.floor(cx - rx - 1); x <= cx + rx + 1; x++) if (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.05) this.px(x, y, c, al); return this; }
  linha(x0, y0, x1, y1, c, al) {
    x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let e = dx + dy;
    for (; ;) { this.px(x0, y0, c, al); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) { e += dy; x0 += sx; } if (e2 <= dx) { e += dx; y0 += sy; } }
    return this;
  }
  poli(pts, c, al) {
    const ys = pts.map(p => p[1]), y0 = Math.floor(Math.min(...ys)), y1 = Math.ceil(Math.max(...ys));
    for (let y = y0; y <= y1; y++) {
      const yc = y + .5, xs = [];
      for (let i = 0; i < pts.length; i++) { const [ax, ay] = pts[i], [bx, by] = pts[(i + 1) % pts.length]; if ((ay <= yc && by > yc) || (by <= yc && ay > yc)) xs.push(ax + (yc - ay) / (by - ay) * (bx - ax)); }
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) for (let x = Math.round(xs[k]); x < Math.round(xs[k + 1]); x++) this.px(x, y, c, al);
    }
    return this;
  }
  /** desenha um mapa de caracteres: linhas = ['..ab', ...], pal = {a:'#hex'} */
  mapa(x, y, linhas, pal) { linhas.forEach((l, j) => [...l].forEach((ch, i) => { if (pal[ch]) this.px(x + i, y + j, pal[ch]); })); return this; }
  /** contorno de 1 px em volta dos pixels opacos (dentro da região x0,y0,x1,y1) */
  contorno(c, x0 = 0, y0 = 0, x1 = this.w, y1 = this.h, diag = false) {
    const ox = this.ox, oy = this.oy, cl = this.clip; this.ox = this.oy = 0; this.clip = null;
    const op = (x, y) => x >= x0 && y >= y0 && x < x1 && y < y1 && this.d[(y * this.w + x) * 4 + 3] > 0;
    const marca = [];
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      if (op(x, y)) continue;
      if (op(x - 1, y) || op(x + 1, y) || op(x, y - 1) || op(x, y + 1) || (diag && (op(x - 1, y - 1) || op(x + 1, y - 1) || op(x - 1, y + 1) || op(x + 1, y + 1)))) marca.push([x, y]);
    }
    for (const [x, y] of marca) this.px(x, y, c);
    this.ox = ox; this.oy = oy; this.clip = cl; return this;
  }
  canvas() { const c = document.createElement('canvas'); c.width = this.w; c.height = this.h; c.getContext('2d').putImageData(new ImageData(this.d, this.w, this.h), 0, 0); return c; }
  /** textura nearest. o.texel (padrão true): repeat = 1/w para UV em texels (geometria da biblioteca) */
  textura(o = {}) { const t = new THREE.CanvasTexture(this.canvas()); conf(t, this, o); t.colorSpace = THREE.SRGBColorSpace; return t; }
  /** normal map a partir do mapa de altura (pixelado, um normal por texel) */
  normais(forca = 2, o = {}) {
    const { w, h } = this, A = this.alt, d = new Uint8ClampedArray(w * h * 4), rep = o.repetir !== false;
    const H = (x, y) => { if (rep) { x = (x + w) % w; y = (y + h) % h; } else { x = clamp(x, 0, w - 1); y = clamp(y, 0, h - 1); } return A[y * w + x]; };
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let nx = -(H(x + 1, y) - H(x - 1, y)) * .5 * forca, ny = (H(x, y + 1) - H(x, y - 1)) * .5 * forca, nz = 1; const l = Math.hypot(nx, ny, nz);
      const j = (y * w + x) * 4; d[j] = (nx / l * .5 + .5) * 255; d[j + 1] = (ny / l * .5 + .5) * 255; d[j + 2] = (nz / l * .5 + .5) * 255; d[j + 3] = 255;
    }
    const c = document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d').putImageData(new ImageData(d, w, h), 0, 0);
    const t = new THREE.CanvasTexture(c); conf(t, this, o); t.colorSpace = THREE.NoColorSpace; return t;
  }
}
function conf(t, P, o) {
  t.magFilter = THREE.NearestFilter; t.minFilter = o.mip === false ? THREE.NearestFilter : THREE.LinearMipmapLinearFilter; t.generateMipmaps = o.mip !== false;
  t.wrapS = t.wrapT = o.repetir === false ? THREE.ClampToEdgeWrapping : THREE.RepeatWrapping; t.anisotropy = 4;
  if (o.texel !== false) t.repeat.set(1 / P.w, 1 / P.h);
}
const TX = new Map();
const cache = (k, fn) => { if (!TX.has(k)) TX.set(k, fn()); return TX.get(k); };
const pacote = (P, forca = 2, E = null) => ({ map: P.textura(), normalMap: P.normais(forca), emissiveMap: E ? E.textura() : null, w: P.w, h: P.h, P });

// ───────────────────────── fonte bitmap 5x7 (desenhada em código, com acentos do pt-BR) ─────────────────────────
const GL = {
  A: '.###.|#...#|#...#|#####|#...#|#...#|#...#', B: '####.|#...#|#...#|####.|#...#|#...#|####.', C: '.###.|#...#|#....|#....|#....|#...#|.###.',
  D: '####.|#...#|#...#|#...#|#...#|#...#|####.', E: '#####|#....|#....|####.|#....|#....|#####', F: '#####|#....|#....|####.|#....|#....|#....',
  G: '.###.|#...#|#....|#.###|#...#|#...#|.####', H: '#...#|#...#|#...#|#####|#...#|#...#|#...#', I: '###|.#.|.#.|.#.|.#.|.#.|###',
  J: '..###|...#.|...#.|...#.|...#.|#..#.|.##..', K: '#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#', L: '#....|#....|#....|#....|#....|#....|#####',
  M: '#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#', N: '#...#|#...#|##..#|#.#.#|#..##|#...#|#...#', O: '.###.|#...#|#...#|#...#|#...#|#...#|.###.',
  P: '####.|#...#|#...#|####.|#....|#....|#....', Q: '.###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#', R: '####.|#...#|#...#|####.|#.#..|#..#.|#...#',
  S: '.####|#....|#....|.###.|....#|....#|####.', T: '#####|..#..|..#..|..#..|..#..|..#..|..#..', U: '#...#|#...#|#...#|#...#|#...#|#...#|.###.',
  V: '#...#|#...#|#...#|#...#|#...#|.#.#.|..#..', W: '#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.', X: '#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#',
  Y: '#...#|#...#|.#.#.|..#..|..#..|..#..|..#..', Z: '#####|....#|...#.|..#..|.#...|#....|#####',
  0: '.###.|#...#|#..##|#.#.#|##..#|#...#|.###.', 1: '..#..|.##..|..#..|..#..|..#..|..#..|.###.', 2: '.###.|#...#|....#|...#.|..#..|.#...|#####',
  3: '#####|...#.|..#..|...#.|....#|#...#|.###.', 4: '...#.|..##.|.#.#.|#..#.|#####|...#.|...#.', 5: '#####|#....|####.|....#|....#|#...#|.###.',
  6: '..##.|.#...|#....|####.|#...#|#...#|.###.', 7: '#####|....#|...#.|..#..|.#...|.#...|.#...', 8: '.###.|#...#|#...#|.###.|#...#|#...#|.###.',
  9: '.###.|#...#|#...#|.####|....#|...#.|.##..', h: '#....|#....|#.##.|##..#|#...#|#...#|#...#',
  '·': '.|.|.|#|.|.|.', '.': '.|.|.|.|.|.|#', ':': '.|.|#|.|.|#|.', '!': '#|#|#|#|#|.|#', '?': '.###.|#...#|....#|...#.|..#..|.....|..#..',
  '-': '...|...|...|###|...|...|...', ',': '..|..|..|..|..|.#|#.', "'": '#|#|.|.|.|.|.', '/': '....#|...#.|...#.|..#..|.#...|.#...|#....',
  'º': '.##|#.#|.##|...|###|...|...', '$': '..#..|.####|#.#..|.###.|..#.#|####.|..#..', '+': '.....|..#..|..#..|#####|..#..|..#..|.....',
};
const ACENTO = { agudo: ['...#.', '..#..'], grave: ['.#...', '..#..'], circ: ['..#..', '.#.#.'], til: ['.##.#', '#..#.'] };
const COMP = { Á: ['A', 'agudo'], À: ['A', 'grave'], Â: ['A', 'circ'], Ã: ['A', 'til'], É: ['E', 'agudo'], Ê: ['E', 'circ'], Í: ['I', 'agudo'], Ó: ['O', 'agudo'], Ô: ['O', 'circ'], Õ: ['O', 'til'], Ú: ['U', 'agudo'], Ç: ['C', 'cedilha'] };
function glifo(ch) {
  if (ch !== 'h' && ch.toUpperCase() !== ch) ch = ch.toUpperCase();
  const c = COMP[ch], base = GL[c ? c[0] : ch] || GL['?'], rows = base.split('|');
  return { w: rows[0].length, rows, acento: c ? c[1] : null };
}
/** largura em pixels de um texto na fonte 5x7 (esp = espaço entre letras) */
export function medirPx(s, esp = 1) { let w = 0; for (const ch of s) w += (ch === ' ' ? 3 : glifo(ch).w) + esp; return Math.max(0, w - esp); }
/** escreve texto pixel na tela P a partir de (x, y = topo da maiúscula). esc = tamanho do pixel. Acentos usam 2 linhas acima. */
export function textoPx(P, s, x, y, c, o = {}) {
  const esc = o.escala ?? 1, esp = o.esp ?? 1;
  for (const ch of s) {
    if (ch === ' ') { x += (3 + esp) * esc; continue; }
    const g = glifo(ch), dot = (i, j) => P.rect(x + i * esc, y + j * esc, esc, esc, c);
    g.rows.forEach((r, j) => [...r].forEach((b, i) => { if (b === '#') dot(i, j); }));
    if (g.acento === 'cedilha') { dot(2, 7); dot(1, 8); dot(2, 8); }
    else if (g.acento) { const off = Math.floor((g.w - 5) / 2); ACENTO[g.acento].forEach((r, j) => [...r].forEach((b, i) => { if (b === '#') dot(i + off, j - 2); })); }
    x += (g.w + esp) * esc;
  }
  return x;
}

// ───────────────────────── texturas procedurais de pixel art ─────────────────────────
/** Todas devolvem {map, normalMap, emissiveMap?, w, h, P}; UV da biblioteca é em texels (repeat = 1/w). */
export const tex = {
  /** paralelepípedo de granito (rua) */
  paralelepipedo(o = {}) {
    return cache('par' + JSON.stringify(o), () => {
      const W = 96, H = 96, P = new Pixels(W, H), r = rng(o.seed ?? 3); P.rep = true;
      const R = rampa(o.cor || '#8f877c', 7, { contraste: .3 }), J = rampa('#3d3431', 3, { contraste: .2 });
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { P.px(x, y, J[hash(x, y, 2) < .2 ? 0 : 1]); P.a(x, y, 0); }
      const bh = 5, rows = H / (bh + 1);
      for (let row = 0; row < rows; row++) {
        const y0 = row * (bh + 1), xs = Math.floor(r() * 8); let x = xs;
        while (x < xs + W - 3) {
          let bw = 6 + Math.floor(r() * 4); if (xs + W - (x + bw + 1) < 5) bw = xs + W - x - 1;
          const base = r() < .15 ? 2 : r() < .8 ? 3 : 4;
          for (let j = 0; j < bh; j++) for (let i = 0; i < bw; i++) {
            const cx = x + i, cy = y0 + j, canto = (i === 0 || i === bw - 1) && (j === 0 || j === bh - 1);
            if (canto && hash(cx, cy, 9) < .75) continue;
            const n = ruido(cx * .55, cy * .55);
            let k = base + (n > .35 ? 1 : n < -.35 ? -1 : 0);
            if (j === 0) k += 1; if (i === 0 && j < bh - 1) k += 1; if (j === bh - 1 || i === bw - 1) k -= 1;
            const m = fbm(cx * .035 + 5, cy * .035, 2); if (m > .15 && dither(cx, cy) < (m - .15) * 2.5) k -= 1;
            P.px(cx, cy, R[clamp(k, 0, 6)]); P.a(cx, cy, (j === 0 || j === bh - 1 || i === 0 || i === bw - 1) ? .55 : .85 + n * .1);
          }
          x += bw + 1;
        }
      }
      for (let i = 0; i < 70; i++) { const x = Math.floor(r() * W), y = Math.floor(r() * H); if (P.alt[y * W + x] === 0) P.px(x, y, r() < .5 ? '#56763a' : '#7a9846'); }
      return pacote(P, 2.4);
    });
  },
  /** pedra portuguesa: mosaico preto e branco em ondas (calçadão) */
  pedraPortuguesa(o = {}) {
    return cache('pp' + JSON.stringify(o), () => {
      const W = 96, H = 48, P = new Pixels(W, H); P.rep = true;
      const B = rampa(o.claro || '#e7dcc4', 4, { contraste: .16 }), N = rampa(o.escuro || '#37302d', 3, { contraste: .22 }), J = cor('#a29682');
      const lam = o.lambda ?? 48, A = o.amp ?? 6, Py = 24, banda = o.banda ?? 9;
      for (let y = 0; y < H; y++) {
        const jx = Math.floor(hash(0, y >> 1, 7) * 2);
        for (let x = 0; x < W; x++) {
          const cx = (x + jx) >> 1, cy = y >> 1, px = cx * 2 - jx + 1, py = cy * 2 + 1;
          const grout = (((x + jx) & 1) === 0 && hash(cx, cy, 3) < .3) || ((y & 1) === 0 && hash(cx, cy, 4) < .22);
          const yy = (((py + A * Math.sin(2 * Math.PI * px / lam)) % Py) + Py) % Py, preto = yy < banda;
          const hv = hash(cx, cy, 11);
          if (grout) { P.px(x, y, J); P.a(x, y, .25); }
          else { P.px(x, y, preto ? N[hv < .3 ? 0 : hv < .85 ? 1 : 2] : B[hv < .15 ? 0 : hv < .55 ? 1 : hv < .9 ? 2 : 3]); P.a(x, y, .7 + hv * .25); }
        }
      }
      return pacote(P, 1.6);
    });
  },
  /** reboco liso repetível (laterais de casas, muros) */
  rebocoTile(c = '#e8dcc0', o = {}) {
    return cache('rt' + c + JSON.stringify(o), () => {
      const W = 48, H = 48, P = new Pixels(W, H), R = rampa(c, 7, { contraste: .26 }); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const n = fbm(x * .13, y * .13, 2) * .7 + ruido(x * .6, y * .6) * .3, d = (dither(x, y) - .5) * .35;
        P.px(x, y, R[3 + (n + d > .2 ? 1 : n + d < -.22 ? -1 : 0)]); P.a(x, y, .6 + n * .25);
      }
      return pacote(P, 1.2);
    });
  },
  /** detalhe liso de 8x8 (molduras, metal pintado, plástico) */
  liso(c, o = {}) {
    return cache('li' + c + JSON.stringify(o), () => {
      const P = new Pixels(8, 8), R = rampa(c, 5, { contraste: o.contraste ?? .16 }); P.rep = true;
      for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) { const h = hash(x, y, c.length); P.px(x, y, R[h < .2 ? 1 : h < .85 ? 2 : 3]); P.a(x, y, .5 + h * .1); }
      return pacote(P, .6);
    });
  },
  concreto(c = '#a7a39b') {
    return cache('co' + c, () => {
      const W = 32, H = 32, P = new Pixels(W, H), R = rampa(c, 6, { contraste: .22 }); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const n = fbm(x * .2, y * .2, 2), h = hash(x, y, 5); P.px(x, y, R[2 + (n > .2 ? 1 : n < -.2 ? -1 : 0) + (h > .93 ? 1 : h < .06 ? -1 : 0)]); P.a(x, y, .5 + n * .2); }
      return pacote(P, 1);
    });
  },
  tijolo(o = {}) {
    return cache('tj' + JSON.stringify(o), () => {
      const W = 40, H = 32, P = new Pixels(W, H), R = rampa(o.cor || '#b4542f', 6, { contraste: .3 }), J = rampa(o.junta || '#a69b8b', 3); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const row = Math.floor(y / 4), xx = x + (row % 2) * 5, bi = Math.floor(xx / 10);
        if (y % 4 === 3 || xx % 10 === 9) { P.px(x, y, J[1]); P.a(x, y, .2); continue; }
        const t = hash(bi, row, 3), k = (t < .2 ? 1 : t < .75 ? 2 : 3) + (y % 4 === 0 ? 1 : 0) - (y % 4 === 2 && hash(x, y) < .4 ? 1 : 0);
        P.px(x, y, R[clamp(k, 0, 5)]); P.a(x, y, .8);
      }
      return pacote(P, 2);
    });
  },
  /** telha colonial (capa e canal), linhas descendo o caimento */
  telha(o = {}) {
    return cache('te' + JSON.stringify(o), () => {
      const W = 48, H = 48, P = new Pixels(W, H), R = rampa(o.cor || '#b9583a', 7, { contraste: .36 }); P.rep = true;
      const capa = [2, 4, 4, 3, 2, 1], canal = [1, 2, 2, 2, 1, 0], hc = [.4, .9, 1, .9, .6, .3], hn = [.3, .15, .1, .15, .3, .4];
      for (let c = 0; c < 8; c++) for (let rr = 0; rr < 6; rr++) {
        const t = hash(c, rr, 21), tint = t < .12 ? -1 : t > .85 ? 1 : 0, ehCapa = c % 2 === 0;
        for (let j = 0; j < 8; j++) for (let i = 0; i < 6; i++) {
          const x = c * 6 + i, y = rr * 8 + j;
          let k = (ehCapa ? capa[i] + 1 : canal[i] + 1) + tint;
          if (j === 0) k -= 2; else if (j === 1) k -= 1; if (j === 7 && ehCapa) k += 1;
          if (!ehCapa && hash(x, y, 4) < .06) { P.px(x, y, hash(x, y, 5) < .5 ? '#5f7440' : '#7d8a4a'); P.a(x, y, .3); continue; }
          P.px(x, y, R[clamp(k, 0, 6)]); P.a(x, y, (ehCapa ? hc[i] : hn[i]) - (j === 0 ? .25 : 0));
        }
      }
      return pacote(P, 3);
    });
  },
  madeira(c = '#8a5a34', o = {}) {
    return cache('ma' + c + JSON.stringify(o), () => {
      const W = 30, H = 48, P = new Pixels(W, H), R = rampa(c, 6, { contraste: .3 }); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const pl = Math.floor(x / 6), t = hash(pl, 0, 8);
        if (x % 6 === 5) { P.px(x, y, R[0]); P.a(x, y, .2); continue; }
        const g = ruido(x * 1.1 + pl * 7, y * .08 + pl * 3);
        let k = (t < .3 ? 2 : 3) + (g > .35 ? -1 : g < -.4 ? 1 : 0) + (x % 6 === 0 ? 1 : 0);
        P.px(x, y, R[clamp(k, 0, 5)]); P.a(x, y, .75 + g * .1);
      }
      return pacote(P, 1.5);
    });
  },
  /** folhagem de copa: tufos de folhas com brilho (ipê = '#f2c12e', mangueira = '#3f7a34') */
  folhagem(c = '#4f8a3a', o = {}) {
    return cache('fo' + c + JSON.stringify(o), () => {
      const W = 48, H = 48, P = new Pixels(W, H), R = rampa(c, 7, { contraste: .42, matiz: .1 }), r = rng(o.seed ?? 4); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { P.px(x, y, R[hash(x, y, 1) < .5 ? 0 : 1]); P.a(x, y, .1); }
      for (let i = 0; i < (o.n ?? 380); i++) {
        const x = Math.floor(r() * W), y = Math.floor(r() * H), k = 2 + Math.floor(r() * 3) + (r() < .12 ? 1 : 0), v = r() < .5;
        const forma = v ? [[0, 0], [0, 1], [1, 1], [0, 2]] : [[0, 0], [1, 0], [1, 1], [2, 1]];
        for (const [dx, dy] of forma) { P.px(x + dx, y + dy, R[clamp(k + (dy === 0 ? 1 : 0), 0, 6)]); P.a(x + dx, y + dy, .6 + k * .08); }
        if (o.flores && r() < o.flores) { P.px(x + 1, y - 1, o.corFlor || '#fff1b0'); P.a(x + 1, y - 1, 1); }
      }
      return pacote(P, 2.2);
    });
  },
  grama(c = '#5c8f3a') {
    return cache('gr' + c, () => {
      const W = 32, H = 32, P = new Pixels(W, H), R = rampa(c, 6, { contraste: .36, matiz: .1 }), r = rng(12); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { P.px(x, y, R[2 + (fbm(x * .2, y * .2, 2) > .15 ? 1 : 0) - (dither(x, y) < .2 ? 1 : 0)]); P.a(x, y, .3); }
      for (let i = 0; i < 150; i++) { const x = Math.floor(r() * W), y = Math.floor(r() * H), k = 3 + Math.floor(r() * 3); P.px(x, y, R[clamp(k, 0, 5)]).px(x, y + 1, R[k - 1]).px(x, y + 2, R[1]); P.a(x, y, .8).a(x, y + 1, .6); }
      for (let i = 0; i < 6; i++) { const x = Math.floor(r() * W), y = Math.floor(r() * H); P.px(x, y, i % 2 ? '#f4e9a0' : '#e98aa8'); }
      return pacote(P, 1.6);
    });
  },
  terra(c = '#8a6142') {
    return cache('tr' + c, () => {
      const W = 32, H = 32, P = new Pixels(W, H), R = rampa(c, 5, { contraste: .25 }); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const n = fbm(x * .25, y * .25, 2), h = hash(x, y, 2); P.px(x, y, R[2 + (n > .2 ? 1 : n < -.25 ? -1 : 0) + (h > .95 ? 1 : 0)]); P.a(x, y, .5 + n * .3); }
      return pacote(P, 1.4);
    });
  },
  casca(c = '#5b4030') {
    return cache('ca' + c, () => {
      const W = 16, H = 32, P = new Pixels(W, H), R = rampa(c, 5, { contraste: .3 }); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const g = ruido(x * .9, y * .12); P.px(x, y, R[2 + (g > .3 ? -1 : g < -.3 ? 1 : 0)]); P.a(x, y, .6 - Math.abs(g) * .3); }
      return pacote(P, 2);
    });
  },
  /** azulejo português azul e branco (2x2 peças de 12 px) */
  azulejo(o = {}) {
    return cache('az' + JSON.stringify(o), () => {
      const W = 24, H = 24, P = new Pixels(W, H), B = rampa(o.fundo || '#eef0ee', 3, { contraste: .1 }), A = rampa(o.cor || '#2f5fae', 3, { contraste: .3 }); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const i = x % 12, j = y % 12; let c = B[1], h = .8;
        if (i === 11 || j === 11) { c = '#b9bdbd'; h = .2; }
        else { const dc = Math.min(Math.hypot(i, j), Math.hypot(i - 11, j), Math.hypot(i, j - 11), Math.hypot(i - 11, j - 11)); const dm = Math.abs(i - 5) + Math.abs(j - 5);
          if (dc < 4 && dc > 2) c = A[1]; else if (dm <= 2) c = dm === 0 ? B[2] : A[2]; else if (dm === 4 && (i === 5 || j === 5)) c = A[0]; if (i === 0 || j === 0) c = B[2]; }
        P.px(x, y, c); P.a(x, y, h);
      }
      return pacote(P, 1.2);
    });
  },
  /** listras do toldo (listras correm ao longo do caimento) */
  toldo(cores = ['#d8302b', '#f3ece0']) {
    return cache('to' + cores.join(), () => {
      const L = 6, W = L * cores.length, H = 12, P = new Pixels(W, H); P.rep = true;
      const rs = cores.map(c => rampa(c, 4, { contraste: .2 }));
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const R = rs[Math.floor(x / L)]; P.px(x, y, R[2 - (x % L === L - 1 ? 1 : 0) + (x % L === 0 ? 1 : 0) - (hash(x, y) < .08 ? 1 : 0)]); P.a(x, y, .6 + Math.sin((x % L) / L * Math.PI) * .3); }
      return pacote(P, 1.2);
    });
  },
  /** saia recortada do toldo (alfa) */
  toldoSaia(cores = ['#d8302b', '#f3ece0']) {
    return cache('ts' + cores.join(), () => {
      const L = 6, W = L * cores.length, H = 6, P = new Pixels(W, H); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const i = x % L, c = cores[Math.floor(x / L)], R = rampa(c, 4, { contraste: .2 }); if (y >= 3 && Math.hypot(i - 2.5, y - 2.2) > 3.2) continue; P.px(x, y, R[y === 0 ? 3 : y > 3 ? 1 : 2]); }
      return pacote(P, .5);
    });
  },
  /** chapa corrugada / portão de enrolar (listras horizontais) */
  chapa(c = '#7c8796', o = {}) {
    return cache('ch' + c + JSON.stringify(o), () => {
      const W = 16, H = 8, P = new Pixels(W, H), R = rampa(c, 5, { contraste: .3 }), pr = [3, 2, 2, 1]; P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const k = o.vertical ? pr[x % 4] : pr[y % 4]; P.px(x, y, R[k - (hash(x, y) < .06 ? 1 : 0)]); P.a(x, y, k * .25); }
      return pacote(P, 1.5);
    });
  },
  /** grade de ferro (alfa): barras verticais com lanças */
  grade(c = '#2a2830', o = {}) {
    return cache('ga' + c + JSON.stringify(o), () => {
      const W = 8, H = 24, P = new Pixels(W, H), R = rampa(c, 3, { contraste: .3 }); P.rep = true;
      for (let y = 0; y < H; y++) { P.px(3, y, R[1]).px(4, y, R[0]); }
      for (let x = 0; x < W; x++) { P.px(x, 2, R[2]).px(x, H - 3, R[1]); if (o.meio) P.px(x, 12, R[1]); }
      P.px(3, 0, R[2]).px(2, 1, R[1]).px(4, 1, R[1]);
      return pacote(P, .8);
    });
  },
  veneziana(c = '#3d7a5a') {
    return cache('ve' + c, () => {
      const W = 12, H = 12, P = new Pixels(W, H), R = rampa(c, 4, { contraste: .3 }); P.rep = true;
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const k = y % 3 === 0 ? 3 : y % 3 === 1 ? 2 : 0; P.px(x, y, R[x === 0 || x === W - 1 ? 1 : k]); P.a(x, y, (y % 3) * .3); }
      return pacote(P, 1.4);
    });
  },
  /** janela pintada (vidro + caixilho); acesa → luz quente com cortina e emissiveMap */
  janela(o = {}) {
    return cache('ja' + JSON.stringify(o), () => {
      const W = o.w ?? 20, H = o.h ?? 26, P = new Pixels(W, H), E = new Pixels(W, H), M = rampa(o.moldura || '#efe6d2', 3, { contraste: .3 });
      const meio = Math.floor(W / 2), trav = Math.round(H * .36);
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (o.acesa) {
          const L = rampa(o.luz || '#ffc45e', 5, { contraste: .34 }), k = y < H * .3 ? 4 : y < H * .65 ? 3 : 2, c = L[clamp(k - (dither(x, y) < .25 && y > H * .5 ? 1 : 0), 0, 4)];
          P.px(x, y, c); E.px(x, y, c);
          const cw = Math.max(2, Math.round(W * .22));
          if (o.cortina !== false && (x < cw || x >= W - cw)) { const C = rampa(o.cortina || '#c8553d', 4); const cc = C[(x % 2) + 1]; P.px(x, y, cc); E.px(x, y, misturar('#000000', cc, .5)); }
        } else {
          const vv = rampa('#3a4a66', 4, { contraste: .3 }), refl = ((x + y * .8) % 11) < 2;
          P.px(x, y, refl ? vv[3] : vv[y < H * .5 ? 2 : 1]);
        }
      }
      if (o.tipo !== 'vitrine') {
        for (let y = 0; y < H; y++) { P.px(meio, y, M[1]); E.px(meio, y, '#000000'); }
        for (let x = 0; x < W; x++) { P.px(x, trav, M[1]); E.px(x, trav, '#000000'); }
      }
      if (o.planta && o.acesa) { for (let i = 0; i < 5; i++) P.px(3 + i, H - 3 - (i % 2), '#3f7a34'); P.rect(4, H - 2, 3, 2, '#9a5532'); }
      for (let x = 0; x < W; x++) { P.px(x, 0, M[0]); P.px(x, H - 1, M[0]); E.px(x, 0, '#000000'); }
      for (let y = 0; y < H; y++) { P.px(0, y, M[0]); P.px(W - 1, y, M[0]); }
      return { map: P.textura(), emissiveMap: E.textura(), normalMap: null, w: W, h: H, P };
    });
  },
  /** porta: 'madeira' (tábuas) ou 'ferro' (ferro com vidro canelado, bem brasileira) */
  porta(o = {}) {
    return cache('po' + JSON.stringify(o), () => {
      const W = o.w ?? 22, H = o.h ?? 50, P = new Pixels(W, H), E = new Pixels(W, H), R = rampa(o.cor || '#7a4a2a', 5, { contraste: .3 });
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (o.tipo === 'ferro') {
          const bx = x % 7 === 0 || x === W - 1, by = y % 10 === 0 || y === H - 1 || (y > H * .62 && y < H * .66);
          if (bx || by) { P.px(x, y, R[x % 7 === 0 ? 3 : 2]); P.a(x, y, .9); }
          else { const V = rampa(o.vidro || '#d9cfa8', 4, { contraste: .2 }); const c = V[(x + (y >> 1)) % 3 === 0 ? 3 : 2]; P.px(x, y, c); P.a(x, y, .5); if (o.acesa) E.px(x, y, misturar('#000000', '#ffc070', .55)); }
        } else {
          const pl = x % 6 === 5, k = pl ? 0 : 2 + (ruido(x * 1.2, y * .1) > .3 ? -1 : 0) + (x % 6 === 0 ? 1 : 0);
          P.px(x, y, R[k]); P.a(x, y, pl ? .3 : .8);
        }
      }
      P.rect(W - 5, Math.round(H * .5), 2, 2, '#d8c27a');
      return { map: P.textura(), normalMap: P.normais(1.2), emissiveMap: E.textura(), w: W, h: H, P };
    });
  },
  /** revistas expostas (banca) */
  revistas(o = {}) {
    return cache('rv' + JSON.stringify(o), () => {
      const W = 48, H = 24, P = new Pixels(W, H), r = rng(o.seed ?? 31), cs = ['#e2362f', '#f2c12e', '#2f7fd8', '#e86fa8', '#3bb273', '#ffffff', '#ff8a2a', '#7a4fd0', '#20c4d0'];
      P.rect(0, 0, W, H, '#2a2e2a');
      for (let j = 0; j < 3; j++) for (let i = 0; i < 8; i++) {
        const x = i * 6, y = j * 8, c = cs[Math.floor(r() * cs.length)], R = rampa(c, 4);
        P.rect(x, y, 5, 7, R[2]); P.rect(x, y, 5, 2, '#f4f1ea'); P.rect(x + 1, y + 3 + Math.floor(r() * 2), 3, 2, R[r() < .5 ? 0 : 3]); P.px(x + 4, y + 6, R[1]);
      }
      for (let x = 0; x < W; x++) { P.px(x, 7, '#151815'); P.px(x, 15, '#151815'); }
      return pacote(P, .8);
    });
  },
  /** fronde de palmeira (alfa) */
  fronde(c = '#4f8a3a') {
    return cache('fr' + c, () => {
      const W = 24, H = 72, P = new Pixels(W, H), R = rampa(c, 5, { contraste: .36, matiz: .1 }), m = W / 2;
      for (let y = 2; y < H; y += 2) {
        const k = 1 - y / H, L = Math.round(2 + 9 * Math.sin(Math.PI * Math.min(1, (y + 8) / H)) * (.4 + k * .6));
        for (let s of [-1, 1]) for (let i = 1; i <= L; i++) { const xx = m + s * i, yy = y + Math.floor(i * .55); P.px(xx, yy, R[i < L * .4 ? 3 : i < L * .8 ? 2 : 1]); if (i % 3 === 0) P.px(xx, yy + 1, R[1]); }
      }
      for (let y = 0; y < H; y++) { P.px(m, y, '#8a7a3a'); P.px(m - 1, y, R[3]); }
      return pacote(P, .8);
    });
  },
};

// ───────────────────────── fachada pintada (reboco com sujeira, rachaduras, reboco caído) ─────────────────────────
/**
 * Pinta a fachada inteira (W×H texels) e devolve {P, E, pronto()} — P = cor, E = emissivo (vitrines acesas).
 * o: {seed, sujeira (m), rachaduras, descascado, aberturas:[{x,y,w,h} texels, y do topo], barra:{cor,h(m)}}
 */
export function fachada(W, H, c, o = {}) {
  const P = new Pixels(W, H), E = new Pixels(W, H), r = rng(o.seed ?? 1), s = (o.seed ?? 1) * 13.7, PPU = CFG.ppu;
  const R = rampa(c, 7, { contraste: o.contraste ?? .36 });
  E.rect(0, 0, W, H, '#000000');
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const n = fbm(x * .06 + s, y * .06, 3) + ruido(x * .5, y * .5 + s) * .3, d = (dither(x, y) - .5) * .42;
    let k = 3 + (n + d > .18 ? 1 : n + d < -.2 ? -1 : 0);
    const yb = (H - 1 - y) / PPU, suj = o.sujeira ?? .55;
    if (yb < suj) { const q = 1 - yb / suj; if (dither(x, y) < q * .8) k--; if (dither(x + 2, y + 1) < q * .3) k--; }
    if (y < 2) k--;
    if (y > 2 && y < 2 + (o.topoClaro ?? 0)) k++;
    P.px(x, y, R[clamp(k, 0, 6)]); P.a(x, y, .6 + n * .2);
  }
  if (o.barra) {
    const hb = Math.round(o.barra.h * PPU), B = o.barra.azulejo ? null : rampa(o.barra.cor, 5, { contraste: .25 });
    const az = o.barra.azulejo ? tex.azulejo(o.barra.azulejo === true ? {} : o.barra.azulejo).P : null;
    for (let y = H - hb; y < H; y++) for (let x = 0; x < W; x++) {
      if (az) { const j = ((x % 24) + ((y - (H - hb)) % 24) * 24) * 4; P.px(x, y, [az.d[j], az.d[j + 1], az.d[j + 2]]); P.a(x, y, .7); }
      else { const yb = (H - 1 - y) / PPU; P.px(x, y, B[2 - (dither(x, y) < (1 - yb / o.barra.h) * .5 ? 1 : 0) + (y === H - hb ? 2 : 0)]); }
    }
    for (let x = 0; x < W; x++) P.px(x, H - hb - 1, R[1]);
  }
  for (let i = 0; i < (o.rachaduras ?? 2); i++) { let x = r() * W, y = r() * H * .6; for (let j = 0; j < 12 + r() * 18; j++) { P.px(x, y, R[1]); P.a(x, y, .3); x += r() < .45 ? (r() < .5 ? -1 : 1) : 0; y += 1; } }
  for (let i = 0; i < (o.descascado ?? 1); i++) {
    const cx = r() * W, cy = H * (.25 + r() * .5), rx = 3 + r() * 5, ry = 2 + r() * 3;
    for (let y = Math.floor(cy - ry - 2); y <= cy + ry + 2; y++) for (let x = Math.floor(cx - rx - 2); x <= cx + rx + 2; x++) {
      const e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ruido(x * .7, y * .7) * .4;
      if (e < 1) { const jt = (y % 3 === 0) || ((x + (Math.floor(y / 3) % 2) * 3) % 6 === 0); P.px(x, y, jt ? '#8e7d6c' : (hash(x >> 1, y, 5) < .5 ? '#a8553a' : '#94472f')); P.a(x, y, .35); }
      else if (e < 1.4) { P.px(x, y, R[5]); P.a(x, y, .75); }
    }
  }
  for (const a of o.aberturas || []) {
    for (let x = a.x - 1; x <= a.x + a.w; x++) { P.px(x, a.y - 1, R[2]); }
    for (let y = a.y; y < a.y + a.h; y++) { P.px(a.x + a.w, y, R[2]); }
    if (a.escorrido !== false) for (let x = a.x; x < a.x + a.w; x++) { const L = Math.floor(hash(x, a.y, 3) * 10 * (a.escorrido ?? 1)); for (let j = 1; j < L; j++) if (dither(x, a.y + a.h + j) < .55 - j * .04) P.px(x, a.y + a.h + 1 + j, R[2]); }
  }
  return { P, E, R, pronto(forca = 1.6) { return { map: P.textura(), normalMap: P.normais(forca), emissiveMap: E.textura(), w: W, h: H }; } };
}

/** pinta uma loja aberta (padaria): fundo quente, prateleiras com pães, balcão-vitrine e luz (emissivo) */
export function pintarLoja(F, L) {
  const { P, E } = F, PPU = CFG.ppu, x0 = Math.round(L.x * PPU), w = Math.round(L.w * PPU), h = Math.round(L.h * PPU), y0 = P.h - Math.round((L.y ?? .15) * PPU) - h;
  const fundo = rampa(L.cor || '#7a4a2c', 5, { contraste: .3 }), luz = rampa('#ffc977', 5, { contraste: .3 }), pao = rampa('#d48a3a', 4, { contraste: .3 }), r = rng(L.seed ?? 5);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const dx = (x - w / 2) / (w / 2), dy = y / h, k = clamp(1 - dx * dx * .6 - dy * .5 + (dither(x, y) - .5) * .25);
    const c = k > .75 ? luz[1] : k > .55 ? fundo[4] : k > .35 ? fundo[3] : fundo[2];
    P.px(x0 + x, y0 + y, c); E.px(x0 + x, y0 + y, misturar('#000000', c, .35 + k * .35));
  }
  for (let x = 0; x < w; x++) for (let j = 0; j < 3; j++) { const c = rampa('#8b9097', 4)[j === 1 ? 1 : 2]; P.px(x0 + x, y0 + j, c); E.px(x0 + x, y0 + j, '#000000'); }
  for (const fy of [.3, .5]) {
    const yy = y0 + Math.round(h * fy);
    for (let x = 2; x < w - 2; x++) { P.px(x0 + x, yy, '#4a2c1a'); E.px(x0 + x, yy, '#140a04'); }
    for (let x = 3; x < w - 4; x += 3 + Math.floor(r() * 2)) { const c = pao[1 + Math.floor(r() * 3)]; P.rect(x0 + x, yy - 2, 2, 2, c).px(x0 + x, yy - 2, pao[3]); E.rect(x0 + x, yy - 2, 2, 2, misturar('#000000', c, .7)); }
  }
  const bc = y0 + Math.round(h * .62);
  for (let y = bc; y < y0 + h; y++) for (let x = 1; x < w - 1; x++) {
    const vid = y < bc + Math.round(h * .2), c = y === bc ? '#d8d2c4' : vid ? (hash(x, y, 2) < .1 ? '#fff6dd' : misturar('#ffd99a', '#c9a46a', (y - bc) / (h * .2))) : rampa('#9d5a33', 4)[(x % 4 === 0) ? 1 : 2];
    P.px(x0 + x, y, c); E.px(x0 + x, y, vid ? misturar('#000000', c, .8) : '#000000');
    if (vid && y > bc + 2 && x % 4 === 1) { P.rect(x0 + x, y, 2, 1, pao[2]); }
  }
  for (const lx of [.25, .75]) { const x = x0 + Math.round(w * lx); P.rect(x - 1, y0 + 3, 3, 2, '#fff4cf'); E.rect(x - 1, y0 + 3, 3, 2, '#fff4cf'); }
  return F;
}
/** pinta um portão de enrolar fechado com pichação discreta */
export function pintarPortao(F, G) {
  const { P } = F, PPU = CFG.ppu, x0 = Math.round(G.x * PPU), w = Math.round(G.w * PPU), h = Math.round(G.h * PPU), y0 = P.h - Math.round((G.y ?? .15) * PPU) - h;
  const R = rampa(G.cor || '#7f8a98', 5, { contraste: .3 }), r = rng(G.seed ?? 8);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { P.px(x0 + x, y0 + y, R[[3, 2, 2, 1][y % 4] - (y > h - 4 && dither(x, y) < .5 ? 1 : 0)]); P.a(x0 + x, y0 + y, [.8, .6, .5, .2][y % 4]); }
  P.rect(x0 + Math.round(w / 2) - 2, y0 + h - 4, 4, 1, '#2b2b30');
  if (G.pixo !== false) { const cs = ['#1d1b22', '#d8302b', '#2f7fd8']; for (let k = 0; k < 3; k++) { let x = x0 + 4 + r() * (w - 14), y = y0 + h * .35 + r() * h * .3; for (let i = 0; i < 10; i++) { P.px(x, y, cs[k]); P.px(x + 1, y, cs[k]); x += 1; y += Math.round((r() - .5) * 3); } } }
  return F;
}

// ───────────────────────── materiais e geometria com UV em texels ─────────────────────────
/** material padrão do estilo a partir de um pacote de textura. o: {cor (multiplica), relevo, rug, metal, emissivo, brilho, alpha, lados} */
export function matTex(t, o = {}) {
  const m = new THREE.MeshStandardMaterial({ map: t.map || null, normalMap: t.normalMap || null, roughness: o.rug ?? .92, metalness: o.metal ?? 0, color: o.cor ?? 0xffffff, side: o.lados ? THREE.DoubleSide : THREE.FrontSide });
  if (t.normalMap) m.normalScale.set(o.relevo ?? 1, o.relevo ?? 1);
  if (t.emissiveMap && (o.brilho ?? 1) > 0) { m.emissiveMap = t.emissiveMap; m.emissive = new THREE.Color(o.emissivo || '#ffffff'); m.emissiveIntensity = o.brilho ?? 1; }
  if (o.alpha) { m.alphaTest = .5; m.side = THREE.DoubleSide; }
  return m;
}
const MC = new Map();
/** material de cor com micro-textura pixelada (peças pequenas) */
export const matCor = (c, o = {}) => { const k = c + JSON.stringify(o); if (!MC.has(k)) MC.set(k, matTex(tex.liso(c, o), o)); return MC.get(k); };
/** material que brilha (lâmpadas, letreiros) — passa do limiar do bloom */
export const brilho = (c, f = 3) => new THREE.MeshBasicMaterial({ color: new THREE.Color(c).multiplyScalar(f), toneMapped: true });
const sombrear = (m, s = true) => { m.castShadow = s; m.receiveShadow = true; return m; };
/** caixa com UV em texels por face. mat pode ser array [+x,-x,+y,-y,+z,-z]. o: {pos:[x,y,z], sombra} */
export function caixa(w, h, d, mat, o = {}) {
  const g = new THREE.BoxGeometry(w, h, d), uv = g.attributes.uv, P = CFG.ppu, dims = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
  for (let f = 0; f < 6; f++) for (let k = 0; k < 4; k++) { const i = f * 4 + k; uv.setXY(i, uv.getX(i) * dims[f][0] * P, uv.getY(i) * dims[f][1] * P); }
  const m = sombrear(new THREE.Mesh(g, mat), o.sombra ?? true); if (o.pos) m.position.set(...o.pos); return m;
}
/** plano vertical (de frente para +z) com UV em texels */
export function plano(w, h, mat, o = {}) {
  const g = new THREE.PlaneGeometry(w, h), uv = g.attributes.uv, P = CFG.ppu;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w * P, uv.getY(i) * h * P);
  const m = sombrear(new THREE.Mesh(g, mat), o.sombra ?? false); if (o.pos) m.position.set(...o.pos); return m;
}
/** chão horizontal entre x0..x1, z0..z1 na altura y, UV pelo mundo; o.variacao escurece manchas grandes (quebra a repetição) */
export function chao(x0, x1, z0, z1, y, mat, o = {}) {
  const sx = Math.max(1, Math.round((x1 - x0) / 1.5)), sz = Math.max(1, Math.round((z1 - z0) / 1.5));
  const g = new THREE.PlaneGeometry(x1 - x0, z1 - z0, sx, sz); g.rotateX(-Math.PI / 2); g.translate((x0 + x1) / 2, y, (z0 + z1) / 2);
  const p = g.attributes.position, uv = g.attributes.uv, P = CFG.ppu, cols = [];
  for (let i = 0; i < p.count; i++) { uv.setXY(i, p.getX(i) * P, -p.getZ(i) * P); const v = 1 - (o.variacao ?? 0) * clamp(fbm(p.getX(i) * .12 + 3, p.getZ(i) * .12, 2) + .5); cols.push(v, v * .99, v * .97); }
  if (o.variacao) { g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3)); mat = mat.clone(); mat.vertexColors = true; }
  const m = new THREE.Mesh(g, mat); m.receiveShadow = true; return m;
}
/** cilindro com UV em texels (seg = lados; 4 = poste quadrado) */
export function cilindro(rt, rb, h, mat, o = {}) {
  const seg = o.seg ?? 8, g = new THREE.CylinderGeometry(rt, rb, h, seg, o.segV ?? 1, o.aberto ?? false), uv = g.attributes.uv, P = CFG.ppu, per = Math.PI * (rt + rb);
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * per * P, uv.getY(i) * h * P);
  if (o.base) g.translate(0, h / 2, 0);
  if (seg === 4) g.rotateY(Math.PI / 4);
  const m = sombrear(new THREE.Mesh(g, mat), o.sombra ?? true); if (o.pos) m.position.set(...o.pos); return m;
}
/** bolha irregular (copa de árvore, arbusto) com UV em texels */
export function bolha(rb, mat, seed = 1, o = {}) {
  const g = new THREE.SphereGeometry(rb, o.seg ?? 14, o.segV ?? 10), p = g.attributes.position, uv = g.attributes.uv, P = CFG.ppu;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i), n = 1 + ruido(x / rb * 1.6 + seed * 3.1, (y + z * .7) / rb * 1.6 - seed) * (o.irregular ?? .16);
    p.setXYZ(i, x * n, (y < 0 ? y * (o.achata ?? .7) : y) * n, z * n);
    uv.setXY(i, uv.getX(i) * 2 * Math.PI * rb * P, uv.getY(i) * Math.PI * rb * P);
  }
  g.computeVertexNormals();
  return sombrear(new THREE.Mesh(g, mat), true);
}

// ───────────────────────── peças do cenário (rua de bairro brasileiro) ─────────────────────────
/** rua de paralelepípedo + meio-fio + calçadas de pedra portuguesa. Devolve Group com userData {zr, zl, zp} */
export function rua(o = {}) {
  const { x0 = -40, x1 = 40, larg = 7, calcLonge = 2.8, calcPerto = 2.8, mf = .16 } = o, zr = larg / 2, g = new THREE.Group();
  g.add(chao(x0, x1, -zr, zr, 0, matTex(tex.paralelepipedo(o.paralelepipedo), { relevo: 1.2 }), { variacao: .28 }));
  const mp = matTex(tex.pedraPortuguesa(o.pedra), { relevo: .9 });
  g.add(chao(x0, x1, -zr - calcLonge, -zr, mf, mp, { variacao: .18 }));
  g.add(chao(x0, x1, zr, zr + calcPerto, mf, mp, { variacao: .18 }));
  const mc = matTex(tex.concreto('#b9b3a6'));
  g.add(caixa(x1 - x0, mf, .16, mc, { pos: [(x0 + x1) / 2, mf / 2, -zr - .08] }), caixa(x1 - x0, mf, .16, mc, { pos: [(x0 + x1) / 2, mf / 2, zr + .08] }));
  const sarj = matCor('#5f5650'); g.add(chao(x0, x1, -zr, -zr + .25, .004, sarj), chao(x0, x1, zr - .25, zr, .004, sarj));
  g.userData = { zr, zl: -zr - calcLonge, zp: zr + calcPerto, mf };
  return g;
}

/** caixa d'água azul de fibra (no alto das lajes) */
export function caixaDagua(o = {}) {
  const g = new THREE.Group(), m = matCor(o.cor || '#2f74c0', { contraste: .3 });
  g.add(cilindro(.5, .42, .75, m, { seg: 10, base: true }), cilindro(.56, .56, .1, matCor('#24599a'), { seg: 10, pos: [0, .8, 0] }));
  return g;
}

/** janela 3D: vidro pintado (aceso = emissivo) + moldura, peitoril, venezianas, grade, floreira */
export function janela3D(g, a, o = {}) {
  const P = CFG.ppu, w = a.w, h = a.h, e = .09;
  const tj = tex.janela({ w: Math.round(w * P), h: Math.round(h * P), acesa: !!a.acesa, cortina: a.cortina ?? o.cortina, moldura: a.moldura ?? o.moldura, tipo: a.tipo, planta: a.planta });
  g.add(plano(w, h, matTex(tj, { emissivo: '#ffb35c', brilho: a.acesa ? (o.brilhoJanela ?? 2.4) : 0, rug: .5 }), { pos: [a.x, a.y + h / 2, .015] }));
  const mc = matCor(a.moldura ?? o.moldura ?? '#efe6d2');
  g.add(caixa(w + 2 * e, e, .1, mc, { pos: [a.x, a.y + h + e / 2, .05] }), caixa(e, h, .1, mc, { pos: [a.x - w / 2 - e / 2, a.y + h / 2, .05] }), caixa(e, h, .1, mc, { pos: [a.x + w / 2 + e / 2, a.y + h / 2, .05] }));
  g.add(caixa(w + 2 * e + .14, .08, .2, mc, { pos: [a.x, a.y - .04, .1] }));
  if (a.veneziana) { const mv = matTex(tex.veneziana(a.veneziana)); for (const s of [-1, 1]) { const v = caixa(w / 2, h, .04, mv, { pos: [a.x + s * (w * .75 + e + .02), a.y + h / 2, .07] }); v.rotation.y = s * -.3; g.add(v); } }
  if (a.grade) g.add(plano(w + .1, h, matTex(tex.grade(), { alpha: true }), { pos: [a.x, a.y + h / 2, .11], sombra: true }));
  if (a.floreira) { g.add(caixa(w * .9, .18, .18, matCor('#8a4a2a'), { pos: [a.x, a.y - .17, .2] })); const b = bolha(.22, matTex(tex.folhagem('#4a8a3a', { flores: .5, corFlor: a.floreira === true ? '#ff7aa8' : a.floreira })), a.x * 7, { irregular: .3 }); b.scale.set(w * 2, .9, .9); b.position.set(a.x, a.y - .02, .22); g.add(b); }
}
/** porta 3D com moldura e degrau */
export function porta3D(g, a, o = {}) {
  const P = CFG.ppu, tp = tex.porta({ w: Math.round(a.w * P), h: Math.round(a.h * P), cor: a.cor, tipo: a.tipo, acesa: a.acesa });
  g.add(plano(a.w, a.h, matTex(tp, { emissivo: '#ffb35c', brilho: a.acesa ? 2 : 0 }), { pos: [a.x, a.y + a.h / 2, .02] }));
  const mc = matCor(a.moldura ?? o.moldura ?? '#efe6d2'), e = .1;
  g.add(caixa(a.w + 2 * e, e, .1, mc, { pos: [a.x, a.y + a.h + e / 2, .05] }), caixa(e, a.h, .1, mc, { pos: [a.x - a.w / 2 - e / 2, a.y + a.h / 2, .05] }), caixa(e, a.h, .1, mc, { pos: [a.x + a.w / 2 + e / 2, a.y + a.h / 2, .05] }));
  g.add(caixa(a.w + .3, .12, .35, matTex(tex.concreto('#b7ab98')), { pos: [a.x, .06 + (a.y - .15), .17] }));
}
/** toldo listrado inclinado com saia recortada */
export function toldo(g, a) {
  const cores = a.cores || ['#d8302b', '#f3ece0'], prof = a.prof ?? 1.3, ang = a.ang ?? .32, w = a.w;
  const t = caixa(w, .04, prof, [matCor(cores[0]), matCor(cores[0]), matTex(tex.toldo(cores)), matTex(tex.toldo(cores)), matCor(cores[0]), matCor(cores[0])]);
  const piv = new THREE.Group(); piv.position.set(a.x, a.y, .05); piv.rotation.x = ang; t.position.z = prof / 2; piv.add(t); g.add(piv);
  const saia = plano(w, .26, matTex(tex.toldoSaia(cores), { alpha: true }), { sombra: true }); saia.position.set(0, -.13, prof); piv.add(saia);
  return piv;
}
/** letreiro pixelado: linhas [{texto, escala, cor}], fundo, borda; brilho > 0 acende as letras */
export function letreiro(o) {
  const linhas = o.linhas, pad = o.pad ?? 3, esp = 2;
  const ws = linhas.map(l => medirPx(l.texto) * (l.escala ?? 1)), hs = linhas.map(l => (7 + (/[ÁÀÂÃÉÊÍÓÔÕÚ]/.test(l.texto) ? 2 : 0) + (/Ç/.test(l.texto) ? 2 : 0)) * (l.escala ?? 1));
  const W = Math.max(...ws) + pad * 2 + 2, H = hs.reduce((a, b) => a + b, 0) + esp * (linhas.length - 1) + pad * 2 + 2;
  const P = new Pixels(W, H), E = new Pixels(W, H), F = rampa(o.fundo || '#1f3b6e', 4, { contraste: .2 }), B = rampa(o.borda || '#f2d27a', 3);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const bd = x === 0 || y === 0 || x === W - 1 || y === H - 1; P.px(x, y, bd ? B[x === 0 || y === 0 ? 2 : 0] : F[1 + (dither(x, y) < .15 ? 1 : 0)]); E.px(x, y, '#000000'); }
  let y = pad + 1;
  linhas.forEach((l, i) => {
    const e = l.escala ?? 1, acima = /[ÁÀÂÃÉÊÍÓÔÕÚ]/.test(l.texto) ? 2 * e : 0, x = Math.round((W - ws[i]) / 2), c = l.cor || '#fff2c4';
    textoPx(P, l.texto, x + e, y + acima + e, misturar('#000000', F[0], .5), { escala: e });
    textoPx(P, l.texto, x, y + acima, c, { escala: e }); textoPx(E, l.texto, x, y + acima, c, { escala: e });
    y += hs[i] + esp;
  });
  const t = { map: P.textura(), normalMap: null, emissiveMap: E.textura() };
  const PPU = CFG.ppu * (o.densidade ?? 1), m = plano(W / CFG.ppu / (o.densidade ?? 1), H / CFG.ppu / (o.densidade ?? 1), matTex(t, { emissivo: '#ffffff', brilho: o.brilho ?? 1.6, rug: .6 }));
  m.geometry.attributes.uv.array.forEach((v, i, arr) => { arr[i] = v * (o.densidade ?? 1); });
  m.userData = { W: W / PPU, H: H / PPU };
  return m;
}

/**
 * Casa/sobrado brasileiro. Origem: canto esquerdo da fachada no chão (x→direita, fachada em z=0, fundo em -prof).
 * o: {x,z,larg,prof,andares,pe,cor,corLado,telhado:'colonial'|'platibanda'|'laje', corTelha, plat, seed,
 *     janelas:[{x,y,w,h,acesa,veneziana,grade,floreira,cortina}], portas:[{x,y,w,h,cor,tipo}], loja:{x,w,h}, portao:{x,w,h},
 *     barra:{cor|azulejo,h}, toldo:{x,y,w,prof,cores}, letreiro:{linhas,...,x,y}, sacada:{x,w,y}, muro:{recuo,altura,cor,portao:{x,w}},
 *     caixaDagua, ferragens, numero, descascado, rachaduras, moldura, tijoloAndar (2º andar de tijolo aparente)}
 */
export function casa(o = {}) {
  const P = CFG.ppu, r = rng(o.seed ?? 1), g = new THREE.Group(), f = new THREE.Group();
  const larg = o.larg ?? 6, prof = o.prof ?? 8, andares = o.andares ?? 1, pe = o.pe ?? 3.1, tT = o.telhado ?? 'colonial';
  const plat = tT === 'platibanda' ? (o.plat ?? 1.1) : tT === 'laje' ? .35 : .2, hP = andares * pe + plat + .15, recuo = o.muro?.recuo ?? 0;
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); f.position.z = -recuo; g.add(f);
  const jan = o.janelas ?? [], portas = o.portas ?? [];
  const W = Math.round(larg * P), H = Math.round(hP * P), rect = a => ({ x: Math.round((a.x - a.w / 2) * P), y: H - Math.round((a.y + a.h) * P), w: Math.round(a.w * P), h: Math.round(a.h * P) });
  const F = fachada(W, H, o.cor ?? '#e9cf8a', { seed: o.seed, aberturas: [...jan, ...portas].map(rect), descascado: o.descascado ?? 1, rachaduras: o.rachaduras ?? 2, barra: o.barra, topoClaro: tT === 'platibanda' ? 2 : 0 });
  if (o.tijoloAndar) { const tj = tex.tijolo().P, y1 = H - Math.round((.15 + pe) * P); for (let y = 0; y < y1; y++) for (let x = 0; x < W; x++) { const j = ((x % 40) + (y % 32) * 40) * 4; F.P.px(x, y, [tj.d[j], tj.d[j + 1], tj.d[j + 2]]); F.P.a(x, y, tj.alt[(x % 40) + (y % 32) * 40]); } }
  if (o.loja) pintarLoja(F, { ...o.loja, x: o.loja.x - o.loja.w / 2 });
  if (o.portao) pintarPortao(F, { ...o.portao, x: o.portao.x - o.portao.w / 2 });
  const matF = matTex(F.pronto(), { emissivo: '#ffffff', brilho: o.loja ? (o.brilhoLoja ?? 2.2) : 0 });
  const matL = matTex(tex.rebocoTile(o.corLado ?? o.cor ?? '#e9cf8a')), matT = matTex(tex.concreto('#9c958a'));
  f.add(caixa(larg, hP, prof, [matL, matL, matT, matT, matF, matL], { pos: [larg / 2, hP / 2, -prof / 2] }));
  for (const a of jan) janela3D(f, a, o);
  for (const a of portas) porta3D(f, a, o);
  if (o.toldo) toldo(f, o.toldo);
  if (o.letreiro) { const L = letreiro(o.letreiro); L.position.set(o.letreiro.x ?? larg / 2, o.letreiro.y ?? (hP - plat / 2 - .05), .07); f.add(L); }
  if (o.sacada) { const s = o.sacada, mc = matTex(tex.concreto('#c9c0b0')); f.add(caixa(s.w, .14, .9, mc, { pos: [s.x, s.y, .45] })); const gr = matTex(tex.grade('#2a2830', { meio: true }), { alpha: true }); f.add(plano(s.w, 1, gr, { pos: [s.x, s.y + .57, .9], sombra: true })); for (const sg of [-1, 1]) { const p = plano(.9, 1, gr, { pos: [s.x + sg * s.w / 2, s.y + .57, .45], sombra: true }); p.rotation.y = Math.PI / 2; f.add(p); } }
  const mc = matCor(o.moldura ?? '#efe6d2');
  if (tT === 'platibanda' || tT === 'laje') {
    f.add(caixa(larg + .12, .16, .32, mc, { pos: [larg / 2, hP - .08, .06] }), caixa(larg + .04, .07, .22, mc, { pos: [larg / 2, hP - .3, .02] }));
    if (tT === 'platibanda' && o.telhaEscondida !== false) { const tl = telhadoColonial(larg - .5, prof - .6, Math.min(1.6, prof * .2), { cor: o.corTelha, beiral: 0, beiralLado: 0, parede: matL }); tl.position.set(larg / 2, hP - plat + .25, -.4); f.add(tl); }
    if (o.caixaDagua) { const c = caixaDagua(); c.position.set(larg * (o.caixaDagua.x ?? .7), hP - plat + .2, -prof * .4); f.add(c); }
    if (o.ferragens) for (const fx of [.15, larg - .15]) for (let k = 0; k < 3; k++) f.add(cilindro(.012, .012, .7 + k * .12, matCor('#4a3a34'), { seg: 3, pos: [fx + (k - 1) * .06, hP + .35, -.1 - k * .05] }));
  } else {
    const tl = telhadoColonial(larg, prof, o.alturaTelhado ?? Math.min(2.2, prof * .28), { cor: o.corTelha, beiral: .5, parede: matL });
    tl.position.set(larg / 2, hP, 0); f.add(tl);
  }
  if (o.numero) { const n = letreiro({ linhas: [{ texto: String(o.numero), cor: '#1f3b6e' }], fundo: '#f1f3f0', borda: '#2f5fae', brilho: 0, pad: 2 }); n.position.set(o.numeroX ?? larg - .6, 2.1, .03); f.add(n); }
  if (recuo > 0) {
    const m = o.muro, alt = m.altura ?? 1.5, mm = matTex(tex.rebocoTile(m.cor ?? o.cor ?? '#e9cf8a'));
    g.add(chao(0, larg, -recuo, 0, .16, matTex(tex.concreto('#b8ad9c')), { variacao: .2 }));
    const px = m.portao?.x ?? larg / 2, pw = m.portao?.w ?? 1.2;
    const seg = (a, b) => { if (b - a > .01) g.add(caixa(b - a, alt, .2, mm, { pos: [(a + b) / 2, alt / 2, -.1] }), caixa(b - a + .06, .08, .28, mc, { pos: [(a + b) / 2, alt + .04, -.1] })); };
    seg(0, px - pw / 2); seg(px + pw / 2, larg);
    const gr = plano(pw, alt + .3, matTex(tex.grade('#2b2a33', { meio: true }), { alpha: true }), { pos: [px, (alt + .3) / 2, -.1], sombra: true }); g.add(gr); g.userData.portao = gr;
    for (const s of [-1, 1]) g.add(caixa(.24, alt + .4, .24, mm, { pos: [px + s * (pw / 2 + .12), (alt + .4) / 2, -.1] }));
    if (m.plantas !== false) for (let i = 0; i < 3; i++) { const b = bolha(.45 + r() * .2, matTex(tex.folhagem(['#3f7a34', '#4f8f3a', '#5a8a2e'][i], { flores: i === 1 ? .3 : 0, corFlor: '#ff6f91' })), i + (o.seed ?? 1), { irregular: .25 }); b.position.set(.7 + i * (larg - 1.4) / 2 + (i === 1 ? (px > larg / 2 ? -1.2 : 1.2) : 0), .5, -recuo * .55); if (Math.abs(b.position.x - px) > pw * .7) g.add(b); }
  }
  g.userData.altura = hP; g.userData.f = f;
  return g;
}

/** telhado colonial de duas águas (cumeeira paralela à rua). Origem: centro da fachada no topo da parede. */
export function telhadoColonial(larg, prof, alt, o = {}) {
  const g = new THREE.Group(), b = o.beiral ?? .5, bl = o.beiralLado ?? .3, P = CFG.ppu, X = larg / 2 + bl, zm = -prof / 2, z0 = b, z1 = -prof - b, y0 = -.18;
  const L0 = Math.hypot(z0 - zm, alt - y0), L1 = Math.hypot(zm - z1, alt - y0);
  const pos = [], uv = [];
  const quad = (a, bq, c, d, ua, ub, uc, ud) => { pos.push(...a, ...bq, ...c, ...a, ...c, ...d); uv.push(...ua, ...ub, ...uc, ...ua, ...uc, ...ud); };
  quad([-X, y0, z0], [X, y0, z0], [X, alt, zm], [-X, alt, zm], [-X * P, 0], [X * P, 0], [X * P, L0 * P], [-X * P, L0 * P]);
  quad([X, y0, z1], [-X, y0, z1], [-X, alt, zm], [X, alt, zm], [X * P, 0], [-X * P, 0], [-X * P, L1 * P], [X * P, L1 * P]);
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); geo.computeVertexNormals();
  g.add(sombrear(new THREE.Mesh(geo, matTex(tex.telha({ cor: o.cor }), { relevo: 1.3, lados: true })), true));
  const tri = [], tuv = [];
  for (const s of [-1, 1]) { const x = s * larg / 2; const pts = s > 0 ? [[x, 0, 0], [x, 0, -prof], [x, alt - .1, zm]] : [[x, 0, -prof], [x, 0, 0], [x, alt - .1, zm]]; for (const p of pts) { tri.push(...p); tuv.push(-p[2] * P, p[1] * P); } }
  const tg = new THREE.BufferGeometry(); tg.setAttribute('position', new THREE.Float32BufferAttribute(tri, 3)); tg.setAttribute('uv', new THREE.Float32BufferAttribute(tuv, 2)); tg.computeVertexNormals();
  g.add(sombrear(new THREE.Mesh(tg, o.parede || matCor('#e9cf8a')), true));
  const cum = cilindro(.13, .13, 2 * X + .05, matTex(tex.telha({ cor: o.cor }), { cor: '#c9b8a8' }), { seg: 6 }); cum.rotation.z = Math.PI / 2; cum.position.set(0, alt + .03, zm); g.add(cum);
  g.add(caixa(2 * X, .12, .06, matCor('#5a3a26'), { pos: [0, y0 - .02, z0 + .02] }));
  return g;
}

/** poste de concreto com cruzeta, isoladores, transformador opcional e luminária (luz de sódio). Devolve Group com userData.fios (pontos de amarração, locais) */
export function poste(o = {}) {
  const g = new THREE.Group(), h = o.altura ?? 9, mc = matTex(tex.concreto('#a39e94'));
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0);
  g.add(cilindro(.1, .17, h, mc, { seg: 4, base: true }));
  g.add(caixa(.12, .12, 1.9, matTex(tex.madeira('#6a4a30')), { pos: [0, h - .35, 0] }));
  const iso = matCor('#d9dcd6');
  for (const z of [-.8, 0, .8]) g.add(cilindro(.04, .05, .14, iso, { seg: 6, pos: [0, h - .22, z] }));
  if (o.trafo) { const t = cilindro(.32, .32, .85, matCor('#8d949a', { contraste: .3 }), { seg: 10, pos: [0, h - 1.7, -.42] }); g.add(t); g.add(cilindro(.36, .36, .06, matCor('#6d747a'), { seg: 10, pos: [0, h - 1.25, -.42] })); }
  const lado = o.lado ?? 1, braco = caixa(.07, .07, 1.5, matCor('#5d636b'), { pos: [0, h - 1.15, lado * .75] }); braco.rotation.x = -lado * .18; g.add(braco);
  const cab = caixa(.26, .14, .55, matCor('#4b5058'), { pos: [0, h - 1.0, lado * 1.5] }); g.add(cab);
  const lamp = new THREE.Mesh(new THREE.PlaneGeometry(.2, .45), brilho(o.corLuz || '#ffc070', o.brilhoLampada ?? 3.2)); lamp.rotation.x = Math.PI / 2; lamp.position.set(0, h - 1.08, lado * 1.5); g.add(lamp);
  if (o.luz !== false) { const L = new THREE.PointLight(o.corLuz || '#ffb062', o.forcaLuz ?? 26, o.alcance ?? 11, 1.6); L.position.set(0, h - 1.4, lado * 1.5); g.add(L); g.userData.luz = L; }
  g.userData.fios = { alta: [[0, h - .15, -.8], [0, h - .15, 0], [0, h - .15, .8]], baixa: [[.12, h - 2.4, 0], [.12, h - 2.7, 0], [.12, h - 3.0, 0]], tv: [[-.14, h - 3.4, 0], [-.14, h - 3.6, 0]] };
  return g;
}
/** fio em catenária entre dois pontos do mundo (queda em metros) */
export function fio(a, b, o = {}) {
  const A = v3(a), B = v3(b), M = A.clone().add(B).multiplyScalar(.5); M.y -= (o.queda ?? .35) * 2;
  const c = new THREE.QuadraticBezierCurve3(A, M, B);
  return sombrear(new THREE.Mesh(new THREE.TubeGeometry(c, o.seg ?? 24, o.raio ?? .022, 4, false), matCor(o.cor || '#1c1a20')), true);
}
/** emaranhado de fios entre postes (e ramais para as casas). postes: Groups de poste(); ramais: [[pontoPoste(idx,'baixa'), pontoCasa]] */
export function emaranhado(postes, o = {}) {
  const g = new THREE.Group(), r = rng(o.seed ?? 4), W = (p, k, i) => { const v = v3(p.userData.fios[k][i]); return v.add(p.position); };
  for (let i = 0; i + 1 < postes.length; i++) {
    const a = postes[i], b = postes[i + 1], d = a.position.distanceTo(b.position);
    for (let k = 0; k < 3; k++) g.add(fio(W(a, 'alta', k), W(b, 'alta', k), { queda: d * .018 + r() * .05, raio: .018 }));
    for (let k = 0; k < 3; k++) g.add(fio(W(a, 'baixa', k), W(b, 'baixa', k), { queda: d * .03 + r() * .15, raio: .022 + r() * .01 }));
    for (let k = 0; k < 2; k++) for (let m = 0; m < 3; m++) g.add(fio(W(a, 'tv', k).add(new THREE.Vector3(0, -m * .07, 0)), W(b, 'tv', k).add(new THREE.Vector3(0, -m * .09, 0)), { queda: d * .045 + m * .12 + r() * .2, raio: .02 + r() * .015, cor: m === 2 ? '#2b2b30' : '#18171c' }));
  }
  for (const [p, alvo] of o.ramais || []) g.add(fio(p, alvo, { queda: .25 + r() * .2, raio: .016 }));
  return g;
}
/** orelhão (o telefone público brasileiro): concha laranja sobre um pé */
export function orelhao(o = {}) {
  const g = new THREE.Group(), c = o.cor || '#f28a1a', mc = matCor(c, { contraste: .2, rug: .45 });
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); g.rotation.y = o.giro ?? 0; g.scale.setScalar(o.escala ?? 1.15);
  g.add(cilindro(.05, .06, 2.0, matCor('#566573'), { seg: 6, base: true }));
  const casca = new THREE.Group(); casca.position.y = 1.55; casca.scale.set(1, 1.35, .95);
  const topo = new THREE.SphereGeometry(.55, 16, 6, 0, Math.PI * 2, 0, Math.PI * .3);
  const lado = new THREE.SphereGeometry(.55, 16, 8, Math.PI * .85, Math.PI * 1.3, Math.PI * .3, Math.PI * .34);
  for (const geo of [topo, lado]) { const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 80, uv.getY(i) * 40); const m = new THREE.Mesh(geo, mc.clone()); m.material.side = THREE.DoubleSide; sombrear(m, true); casca.add(m); }
  g.add(casca);
  g.add(caixa(.22, .32, .12, matCor('#9aa3ad'), { pos: [0, 1.35, -.2] }), caixa(.06, .2, .07, matCor('#2a2c33'), { pos: [-.08, 1.36, -.12] }));
  return g;
}
/** banca de jornal verde com revistas e letreiro */
export function banca(o = {}) {
  const g = new THREE.Group(), w = o.larg ?? 2.2, h = o.altura ?? 2.2, d = o.prof ?? 1.4, mv = matTex(tex.chapa(o.cor || '#2f7a4c', { vertical: true }));
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0);
  const fr = matTex(tex.revistas({ seed: o.seed ?? 3 }));
  g.add(caixa(w, h, d, [mv, mv, mv, mv, fr, mv], { pos: [0, h / 2, 0] }));
  g.add(caixa(w + .3, .1, d + .5, matCor('#e8e2d2'), { pos: [0, h + .05, .15] }));
  const L = letreiro({ linhas: [{ texto: o.texto || 'BANCA', cor: '#fff6d8' }], fundo: o.cor || '#2f7a4c', borda: '#f2d27a', brilho: 1.4, pad: 2 }); L.position.set(0, h + .35, d / 2 + .05); g.add(L);
  g.add(caixa(.9, .65, .45, matCor('#5a3a26'), { pos: [w * .2, .33, d / 2 + .3] }));
  const jor = matCor('#e8e4da'); for (let i = 0; i < 3; i++) g.add(caixa(.38, .05, .28, jor, { pos: [w * .2 - .25 + i * .25, .68 + i * .02, d / 2 + .3] }));
  return g;
}
/** árvore em volumes: tipo 'ipe' (amarelo), 'mangueira' (verde-escura, copa enorme) ou cor própria */
export function arvore(o = {}) {
  const r = rng(o.seed ?? 5), g = new THREE.Group(), alt = o.altura ?? 6, raio = o.raio ?? 2.4, tipo = o.tipo ?? 'mangueira';
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0);
  const corF = o.cor ?? (tipo === 'ipe' ? '#f0bf2a' : tipo === 'mangueira' ? '#3a7331' : '#5d9a3e');
  const mt = matTex(tex.casca());
  g.add(cilindro(.16, .26, alt * .62, mt, { seg: 7, base: true }));
  const mf = matTex(tex.folhagem(corF, tipo === 'ipe' ? { flores: .25, corFlor: '#fff3b0', n: 420 } : { n: 420 }), { relevo: 1.5, cor: o.tinta ?? 0xffffff });
  const n = o.bolhas ?? 9;
  for (let i = 0; i < n; i++) {
    const a = i / n * Math.PI * 2 + r(), d = (i === 0 ? 0 : .35 + r() * .5) * raio * .65, y = alt * .66 + (i === 0 ? raio * .35 : r() * raio * .5);
    const rb = raio * (i === 0 ? .62 : .4 + r() * .22), b = bolha(rb, mf, (o.seed ?? 5) * 10 + i, { irregular: .2 });
    b.position.set(Math.cos(a) * d, y, Math.sin(a) * d * .85); g.add(b);
    if (i > 0 && i < 5) { const gal = cilindro(.05, .09, d + .4, mt, { seg: 5 }); gal.position.set(Math.cos(a) * d * .5, alt * .6 + (y - alt * .6) * .5, Math.sin(a) * d * .42); gal.lookAt(g.position.clone().add(new THREE.Vector3(Math.cos(a) * d, y, Math.sin(a) * d * .85))); gal.rotateX(Math.PI / 2); g.add(gal); }
  }
  g.userData.copa = { y: alt * .66 + raio * .3, raio };
  return g;
}
/** palmeira imperial: tronco anelado + frondes em alfa curvadas */
export function palmeira(o = {}) {
  const g = new THREE.Group(), alt = o.altura ?? 12, r = rng(o.seed ?? 2);
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0);
  g.add(cilindro(.2, .3, alt, matTex(tex.concreto('#9c958a')), { seg: 8, base: true }));
  g.add(cilindro(.24, .22, 1.6, matCor('#5d8a3a'), { seg: 8, pos: [0, alt + .7, 0] }));
  const mf = matTex(tex.fronde(o.cor || '#4f8a3a'), { alpha: true, relevo: .6 }), n = o.frondes ?? 11;
  for (let i = 0; i < n; i++) {
    const comp = 3.2 + r() * .8, geo = new THREE.PlaneGeometry(1, comp, 1, 8), p = geo.attributes.position, uv = geo.attributes.uv, lift = .35 + r() * .7;
    for (let k = 0; k < p.count; k++) { const s = p.getY(k) / comp + .5, x = p.getX(k); p.setXYZ(k, x, s * comp * Math.sin(lift) - 1.4 * s * s * comp * .35, s * comp * Math.cos(lift)); uv.setXY(k, uv.getX(k) * 24, uv.getY(k) * 72); }
    geo.computeVertexNormals();
    const m = sombrear(new THREE.Mesh(geo, mf), true); const piv = new THREE.Group(); piv.position.y = alt + 1.4; piv.rotation.y = i / n * Math.PI * 2 + r() * .3; piv.add(m); g.add(piv);
  }
  return g;
}
/** carro estacionado 3D com texturas pixeladas. tipo 'seda' | 'kombi' */
export function carro(o = {}) {
  const g = new THREE.Group(), tipo = o.tipo ?? 'seda', c = o.cor || '#c23b2e', R = rampa(c, 5, { contraste: .3 }), P = CFG.ppu;
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); g.rotation.y = o.giro ?? 0;
  const L = tipo === 'kombi' ? 4.2 : 4.1, Wd = tipo === 'kombi' ? 1.75 : 1.7, hb = tipo === 'kombi' ? 1.55 : .62, y0 = .28;
  const lado = (ehK) => { const W = Math.round(L * P), H = Math.round(hb * P), Pp = new Pixels(W, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const topo = ehK && y < H * .55, k = topo ? 3 : (y < 2 ? 3 : y > H - 3 ? 1 : 2);
      let col = topo ? rampa(o.cor2 || '#efe9dc', 4)[k - (dither(x, y) < .1 ? 1 : 0)] : R[k];
      if (ehK && topo && y > 3 && y < H * .45 && x % Math.round(W / 4) > 3 && x > 6 && x < W - 4) col = ((x + y) % 9 < 2) ? '#7f9cc0' : '#2c3a52';
      if (!topo && (x === Math.round(W * .48) || (!ehK && x === Math.round(W * .72))) && y > 2 && y < H - 3) col = R[0];
      Pp.px(x, y, col);
    }
    for (const fx of [.2, .8]) { const cx = W * fx, cy = H + 1, rr = .38 * P; for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (Math.hypot(x - cx, y - cy) < rr) Pp.px(x, y, '#1a181d'); }
    Pp.rect(0, H - 4, W, 1, '#c8ccd0');
    return { map: Pp.textura(), normalMap: null };
  };
  const frente = (tras) => { const W = Math.round(Wd * P), H = Math.round(hb * P), Pp = new Pixels(W, H); for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) Pp.px(x, y, R[y < 3 ? 3 : 2]); Pp.rect(0, H - 4, W, 3, tras ? '#2a2a2e' : '#bfc5ca');
    const lc = tras ? '#e0322b' : '#fff3c4', ly = Math.round(H * (tipo === 'kombi' ? .62 : .3)); Pp.rect(2, ly, 6, 3, lc); Pp.rect(W - 8, ly, 6, 3, lc);
    if (tras) { Pp.rect(Math.round(W / 2) - 5, H - 8, 10, 4, '#f4f4f0'); Pp.rect(Math.round(W / 2) - 5, H - 8, 10, 1, '#2f5fae'); } else if (tipo !== 'kombi') Pp.rect(10, ly, W - 20, 3, '#2a2c33');
    if (tipo === 'kombi' && !tras) { Pp.linha(4, 2, Math.round(W / 2), Math.round(H * .5), '#efe9dc'); Pp.linha(W - 4, 2, Math.round(W / 2), Math.round(H * .5), '#efe9dc'); Pp.rect(4, 3, W - 8, Math.round(H * .3), '#2c3a52'); }
    return { map: Pp.textura(), normalMap: null }; };
  const mTopo = matCor(tipo === 'kombi' ? (o.cor2 || '#efe9dc') : c, { rug: .5 });
  const corpo = caixa(L, hb, Wd, [matTex(frente(false), { rug: .45 }), matTex(frente(true), { rug: .45 }), mTopo, mTopo, matTex(lado(tipo === 'kombi'), { rug: .45 }), matTex(lado(tipo === 'kombi'), { rug: .45 })], { pos: [0, y0 + hb / 2, 0] });
  g.add(corpo);
  if (tipo !== 'kombi') {
    const Wv = Math.round(2.1 * P), Hv = Math.round(.5 * P), Pv = new Pixels(Wv, Hv);
    for (let y = 0; y < Hv; y++) for (let x = 0; x < Wv; x++) { const col = (x < 3 || x > Wv - 4 || x === Math.round(Wv / 2)) ? R[2] : ((x + y) % 10 < 2 ? '#86a3c4' : y < 3 ? '#3b4c68' : '#283447'); Pv.px(x, y, col); }
    const mv = matTex({ map: Pv.textura() }, { rug: .3 });
    g.add(caixa(2.1, .5, Wd - .14, [mv, mv, matCor(c, { rug: .5 }), mv, mv, mv], { pos: [-.15, y0 + hb + .25, 0] }));
  }
  const mr = matCor('#1b1a1f'), mcalota = matCor('#aab2ba');
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const rd = cilindro(.3, .3, .2, mr, { seg: 10, pos: [sx * L * .3, .3, sz * (Wd / 2 - .06)] }); rd.rotation.x = Math.PI / 2; g.add(rd); const cl = cilindro(.15, .15, .03, mcalota, { seg: 8, pos: [sx * L * .3, .3, sz * (Wd / 2 + .05)] }); cl.rotation.x = Math.PI / 2; g.add(cl); }
  return g;
}
/** mesa e cadeiras de plástico de boteco */
export function mesaBoteco(o = {}) {
  const g = new THREE.Group(), m = matCor(o.cor || '#d8302b', { rug: .5 });
  g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0);
  g.add(caixa(.75, .05, .75, m, { pos: [0, .72, 0] })); for (const sx of [-1, 1]) for (const sz of [-1, 1]) g.add(caixa(.05, .7, .05, m, { pos: [sx * .32, .35, sz * .32] }));
  for (const [cx, cz, rot] of o.cadeiras ?? [[-.65, 0, Math.PI / 2], [.65, 0, -Math.PI / 2]]) { const c = new THREE.Group(); c.position.set(cx, 0, cz); c.rotation.y = rot; c.add(caixa(.45, .05, .45, m, { pos: [0, .44, 0] }), caixa(.45, .45, .05, m, { pos: [0, .68, -.2] })); for (const sx of [-1, 1]) for (const sz of [-1, 1]) c.add(caixa(.04, .44, .04, m, { pos: [sx * .19, .22, sz * .19] })); g.add(c); }
  if (o.garrafa !== false) { g.add(cilindro(.04, .045, .28, matCor('#5a3a1a', { rug: .3 }), { seg: 6, pos: [.1, .89, .05] })); g.add(cilindro(.035, .03, .1, matCor('#f2e6c8'), { seg: 6, pos: [-.12, .8, -.08] })); }
  return g;
}
/** vaso de barro com planta (flores opcionais) */
export function vaso(o = {}) {
  const g = new THREE.Group(), s = o.tam ?? 1; g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0);
  g.add(cilindro(.2 * s, .14 * s, .32 * s, matCor(o.corVaso || '#a8553a', { contraste: .3 }), { seg: 8, base: true }));
  const b = bolha(.3 * s, matTex(tex.folhagem(o.cor || '#4a8a3a', o.flor ? { flores: .45, corFlor: o.flor } : {}), { relevo: 1.3 }), (o.x ?? 0) * 3.7 + (o.z ?? 0), { irregular: .3, seg: 10, segV: 7 });
  b.position.y = .45 * s; b.scale.set(1, o.alto ?? 1, 1); g.add(b); return g;
}
/** engradado de cerveja (plástico amarelo) com gargalos */
export function engradado(o = {}) {
  const g = new THREE.Group(); g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0); g.rotation.y = o.giro ?? 0;
  const n = o.pilha ?? 2, m = matTex(tex.chapa(o.cor || '#f2c12e', { vertical: true }), { rug: .6 }), gm = matCor('#5a3a1a', { rug: .3 });
  for (let i = 0; i < n; i++) { g.add(caixa(.55, .3, .38, m, { pos: [0, .15 + i * .31, 0] })); }
  for (let i = 0; i < 6; i++) g.add(cilindro(.03, .03, .1, gm, { seg: 5, pos: [-.18 + (i % 3) * .18, n * .31 + .03, -.09 + Math.floor(i / 3) * .18] }));
  return g;
}
/** canteiro baixo com arbustos floridos (bom de primeiro plano desfocado) */
export function canteiro(o = {}) {
  const g = new THREE.Group(), r = rng(o.seed ?? 3), w = o.larg ?? 3, d = o.prof ?? 1.1; g.position.set(o.x ?? 0, o.y ?? 0, o.z ?? 0);
  g.add(caixa(w, .35, d, matTex(tex.tijolo({ cor: '#b06a48' })), { pos: [0, .175, 0] }));
  const flores = o.flores ?? ['#ff6f91', '#ffd23a', '#ffffff', '#c86bff'];
  for (let i = 0; i < Math.round(w / .7); i++) { const b = bolha(.42 + r() * .25, matTex(tex.folhagem(r() < .5 ? '#3f7a34' : '#5a9a3a', { flores: .5, corFlor: flores[Math.floor(r() * flores.length)] }), { relevo: 1.3 }), i + (o.seed ?? 3) * 9, { irregular: .3, seg: 10, segV: 7 }); b.position.set(-w / 2 + .4 + i * (w - .8) / Math.max(1, Math.round(w / .7) - 1), .55 + r() * .2, (r() - .5) * d * .4); g.add(b); }
  return g;
}

/** morro de fundo com casinhas coloridas, lajes, caixas d'água e janelas acesas (fica desfocado) */
export function bairroFundo(o = {}) {
  const r = rng(o.seed ?? 9), g = new THREE.Group(), cores = o.cores ?? ['#e7a3a0', '#a6d6c6', '#efd27e', '#9fc1e6', '#efa66a', '#ece2cf', '#cfa4d6', '#b9d78c', '#d98b6a'];
  const mJ = brilho('#ffbe6a', 2.6), mJo = matCor('#2b3346'), mT = matTex(tex.terra('#7a5a3e'));
  const base = matTex(tex.rebocoTile('#f2ece0'));
  for (let f = 0; f < (o.fileiras ?? 3); f++) {
    const passo = o.passo ?? 7, z = (o.z0 ?? -16) - f * passo, y = f * (o.subida ?? 2.4); let x = (o.x0 ?? -30) + r() * 2;
    g.add(caixa((o.x1 ?? 30) - (o.x0 ?? -30) + 10, y + 3, passo, mT, { pos: [((o.x0 ?? -30) + (o.x1 ?? 30)) / 2, y / 2 - 1.5, z - passo / 2], sombra: false }));
    while (x < (o.x1 ?? 30)) {
      const w = 3.2 + r() * 3, and = 1 + Math.floor(r() * 2.2), h = and * 2.8 + .3, c = cores[Math.floor(r() * cores.length)], d = 4.5 + r() * 2;
      const mat = base.clone(); mat.color = new THREE.Color(c);
      g.add(caixa(w - .25, h, d, mat, { pos: [x + w / 2, y + h / 2, z - d / 2 - r() * .8] }));
      const nj = w > 4.4 ? 2 : 1;
      for (let a = 0; a < and; a++) for (let j = 0; j < nj; j++) g.add(plano(.85, .95, r() < (o.acesas ?? .55) ? mJ : mJo, { pos: [x + (j + .5) * w / nj, y + a * 2.8 + 1.4, z + .02] }));
      if (r() < .55) { const cd = caixaDagua(); cd.position.set(x + w * (.3 + r() * .4), y + h, z - d * .5); g.add(cd); }
      else if (r() < .7) { const t = telhadoColonial(w - .25, d, 1.2, { beiral: .3, beiralLado: .15, parede: mat }); t.position.set(x + w / 2, y + h, z); g.add(t); }
      x += w + (r() < .2 ? 1.2 : 0);
    }
  }
  return g;
}

// ───────────────────────── sprites 2D em billboard ─────────────────────────
/** folha de sprite: n quadros de w×h px; desenhar(P, i) pinta o quadro i em coordenadas locais (0..w, 0..h). Contorno escuro automático. */
export function folhaSprite(w, h, n, desenhar, o = {}) {
  const P = new Pixels(w * n, h);
  for (let i = 0; i < n; i++) { P.ox = i * w; P.oy = 0; P.clip = [i * w, 0, (i + 1) * w, h]; desenhar(P, i); P.ox = 0; P.clip = null; if (o.contorno !== false) P.contorno(o.contorno || '#1b1424', i * w, 0, (i + 1) * w, h); }
  const tex = P.textura({ texel: false, repetir: false, mip: false });
  return { tex, w, h, n, P };
}
let BLOB = null;
function blobMat() {
  if (BLOB) return BLOB;
  const P = new Pixels(16, 8); for (let y = 0; y < 8; y++) for (let x = 0; x < 16; x++) { const e = ((x - 7.5) / 8) ** 2 + ((y - 3.5) / 4) ** 2; if (e < 1) P.px(x, y, '#000000', e < .45 ? 150 : 80); }
  const t = P.textura({ texel: false, repetir: false, mip: false });
  return (BLOB = new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, color: '#1a0f20' }));
}
/**
 * Sprite em billboard (vira para a câmera; inclina parte do pitch). o: {pos:[x,y,z], ppu, ancora:[.5,0], inclina:.35, sombraReal:true, blob:1, tinta}
 * Devolve {g, plano, quadro(i), flip, pos} — mova spr.g.position; troque quadro com spr.quadro(i).
 */
export function sprite(S, folha, o = {}) {
  const ppu = o.ppu ?? CFG.ppuSprite, W = folha.w / ppu, H = folha.h / ppu, an = o.ancora ?? [.5, 0];
  const tx = folha.tex.clone(); tx.repeat.set(1 / folha.n, 1); tx.needsUpdate = true;
  const mat = new THREE.MeshBasicMaterial({ map: tx, alphaTest: .5, side: THREE.DoubleSide, color: new THREE.Color(o.tinta ?? S.tintaSprite ?? '#ffffff') });
  const geo = new THREE.PlaneGeometry(W, H); geo.translate((.5 - an[0]) * W, H / 2 - an[1] * H, 0);
  const pl = new THREE.Mesh(geo, mat); pl.castShadow = o.sombraReal ?? true;
  const g = new THREE.Group(); g.add(pl); if (o.pos) g.position.set(...o.pos);
  if (o.blob !== false) { const b = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), blobMat()); b.rotation.x = -Math.PI / 2; const k = o.blob ?? 1; b.scale.set(W * .8 * k, Math.min(W * .8, .7) * .55 * k, 1); b.position.y = .015; g.add(b); g.userData.blob = b; }
  (o.pai || S.scene).add(g);
  const spr = { g, plano: pl, tex: tx, folha, flip: false, inclina: o.inclina ?? .35, q: 0,
    quadro(i) { i = ((Math.floor(i) % folha.n) + folha.n) % folha.n; spr.q = i; tx.offset.x = (spr.flip ? i + 1 : i) / folha.n; tx.repeat.x = (spr.flip ? -1 : 1) / folha.n; return spr; },
    visivel(v) { g.visible = v; return spr; } };
  spr.quadro(0); S.sprites.push(spr);
  return spr;
}
const _cp = new THREE.Vector3(), _sp = new THREE.Vector3();
function billboard(S, spr) {
  if (!spr.g.visible) return;
  S.camera.getWorldPosition(_cp); spr.g.getWorldPosition(_sp);
  const dx = _cp.x - _sp.x, dz = _cp.z - _sp.z, yaw = Math.atan2(dx, dz), pitch = Math.atan2(_cp.y - _sp.y, Math.hypot(dx, dz));
  spr.plano.rotation.set(-pitch * spr.inclina, yaw, 0, 'YXZ');
}

/** paletas de pele (tons diversos) */
export const PELE = { clara: '#f0c7a2', media: '#d29a6c', parda: '#b77a4f', morena: '#8f5a3a', negra: '#5e3a26' };
const OUT = '#1b1424';
/**
 * Pessoa (vista de frente, cabeçuda como nos RPGs): o: {pele, cabelo:{cor, estilo:'curto'|'crespo'|'longo'|'coque'|'careca'}, camisa, calca, sapato,
 *  extra:'touca'|'bone'|'avental'|'colete'|'sacola'|'bandeja' (ou lista), corBone, acao:'parado'|'andar'|'acenar'|'varrer'|'arrumar'}
 * Quadros: parado 2 · andar 4 · acenar 2 · varrer 4 · arrumar 2 (todos na mesma folha: 0-1 parado, 2-5 andar, 6-7 acenar, 8-11 varrer, 12-13 arrumar)
 */
export function folhaPessoa(o = {}) {
  const PE = rampa(o.pele || PELE.parda, 4, { contraste: .26 }), CA = rampa(o.cabelo?.cor || '#2a1d18', 3, { contraste: .3 }), CM = rampa(o.camisa || '#3b7dd8', 4, { contraste: .3 });
  const CL = rampa(o.calca || '#34405a', 3, { contraste: .3 }), SA = rampa(o.sapato || '#2a2222', 2), est = o.cabelo?.estilo || 'curto', EX = [].concat(o.extra || []), tem = k => EX.includes(k);
  return folhaSprite(20, 34, 14, (P, i) => {
    const acao = i < 2 ? 'parado' : i < 6 ? 'andar' : i < 8 ? 'acenar' : i < 12 ? 'varrer' : 'arrumar', k = i < 2 ? i : i < 6 ? i - 2 : i < 8 ? i - 6 : i < 12 ? i - 8 : i - 12;
    const bob = acao === 'parado' ? k : acao === 'andar' ? (k % 2) : 0, by = 2 + bob;
    const pernaE = acao === 'andar' && k === 1 ? -1 : 0, pernaD = acao === 'andar' && k === 3 ? -1 : 0;
    P.rect(6, 31 + pernaE, 4, 2, SA[0]).rect(11, 31 + pernaD, 4, 2, SA[0]).px(6, 31 + pernaE, SA[1]).px(11, 31 + pernaD, SA[1]);
    P.rect(7, 25 + by - 2, 3, 6 - bob + pernaE, CL[1]).rect(11, 25 + by - 2, 3, 6 - bob + pernaD, CL[1]).px(7, 25 + by - 2, CL[2]).px(11, 25 + by - 2, CL[2]);
    const tor = (x, y, w, h) => { P.rect(x, y, w, h, CM[2]); P.rect(x, y, 1, h, CM[3]); P.rect(x + w - 2, y, 2, h, CM[1]); };
    tor(6, 15 + by, 9, 9);
    if (tem('colete')) { P.rect(6, 19 + by, 9, 1, '#e8eef2'); P.rect(7, 26 + by - 2, 3, 1, '#e8eef2').rect(11, 26 + by - 2, 3, 1, '#e8eef2'); }
    if (tem('avental')) { P.rect(7, 18 + by, 7, 9 - by + 2, '#f4f1ea').rect(7, 18 + by, 1, 9 - by + 2, '#ffffff').rect(13, 18 + by, 1, 9 - by + 2, '#cfcac0'); }
    const mao = PE[2];
    if (acao === 'acenar') { const ax = 15 + k; P.rect(4, 16 + by, 2, 6, CM[3]).rect(4, 22 + by, 2, 1, mao); P.rect(ax, 9 + by, 2, 6, CM[1]).rect(ax, 7 + by, 2, 2, mao); }
    else if (acao === 'varrer') { const dx = [-2, 0, 2, 0][k]; P.rect(4, 16 + by, 2, 5, CM[3]).rect(15, 16 + by, 2, 5, CM[1]); P.linha(16, 15 + by, 6 + dx, 30, '#8a6a3a'); P.rect(2 + dx, 30, 8, 2, '#d9b45a').rect(2 + dx, 32, 8, 1, '#a8862e'); P.rect(15, 21 + by, 2, 1, mao).rect(10 + dx / 2, 24 + by, 2, 1, mao); }
    else if (acao === 'arrumar' || tem('bandeja')) { const up = acao === 'arrumar' ? k : 0; P.rect(5, 17 + by - up, 3, 2, CM[3]).rect(13, 17 + by + up - 1, 3, 2, CM[1]).rect(7, 18 + by - up, 2, 2, mao).rect(12, 18 + by + up - 1, 2, 2, mao);
      if (tem('bandeja')) { P.rect(3, 17 + by - up, 15, 1, '#b8c0c6'); for (let b = 0; b < 4; b++) P.rect(4 + b * 3, 15 + by - up, 3, 2, b % 2 ? '#d48a3a' : '#e8a74e').px(5 + b * 3, 15 + by - up, '#f6cf7e'); } }
    else { const sw = acao === 'andar' ? [0, 1, 0, -1][k] : 0; P.rect(4, 16 + by + sw, 2, 6, CM[3]).rect(4, 22 + by + sw, 2, 1, mao); P.rect(15, 16 + by - sw, 2, 6, CM[1]).rect(15, 22 + by - sw, 2, 1, mao);
      if (tem('sacola')) { P.rect(15, 23 + by - sw, 3, 1, '#e8e8e8').rect(14, 24 + by - sw, 5, 5, '#f4f4f0').rect(17, 24 + by - sw, 2, 5, '#d4d4d0').px(15, 25 + by - sw, '#d8302b'); } }
    P.rect(9, 14 + by, 3, 1, PE[1]);
    const hy = 3 + by;
    if (est === 'crespo') { P.disc(10.5, hy + 3.5, 6.6, CA[1]); P.disc(8, hy + 1, 2.5, CA[2]); }
    P.rect(5, hy + 1, 11, 10, PE[2]).rect(5, hy + 1, 1, 10, PE[3]).rect(14, hy + 2, 2, 9, PE[1]).rect(6, hy + 10, 9, 1, PE[1]);
    P.rect(7, hy + 6, 1, 2, OUT).rect(12, hy + 6, 1, 2, OUT).px(7, hy + 6, '#ffffff'); P.rect(9, hy + 9, 2, 1, PE[0]);
    const cab = (x, y, w, h) => P.rect(x, y, w, h, CA[1]);
    if (est === 'curto') { cab(5, hy, 11, 4); cab(5, hy + 4, 1, 3); cab(15, hy + 4, 1, 3); P.rect(6, hy, 5, 1, CA[2]); }
    else if (est === 'crespo') { P.rect(5, hy, 11, 3, CA[1]); P.px(5, hy + 3, CA[1]).px(15, hy + 3, CA[1]); }
    else if (est === 'longo') { cab(4, hy, 13, 4); cab(4, hy + 4, 2, 12); cab(15, hy + 4, 2, 12); P.rect(6, hy, 6, 1, CA[2]); }
    else if (est === 'coque') { cab(5, hy, 11, 4); P.disc(10.5, hy - 2, 2.5, CA[1]); cab(5, hy + 4, 1, 2); cab(15, hy + 4, 1, 2); }
    else if (est === 'careca') { P.rect(5, hy + 4, 1, 3, CA[1]).rect(15, hy + 4, 1, 3, CA[1]); P.rect(7, hy + 1, 3, 1, PE[3]); }
    if (tem('touca')) { P.rect(5, hy - 4, 11, 6, '#f6f4ee').rect(5, hy - 4, 2, 6, '#ffffff').rect(13, hy - 4, 3, 6, '#d6d2c8').rect(4, hy + 1, 13, 2, '#e8e4da'); }
    if (tem('bone') || tem('colete')) { const B = rampa(o.corBone || '#e8722a', 3); P.rect(5, hy - 1, 11, 4, B[1]).rect(5, hy - 1, 4, 1, B[2]).rect(3, hy + 3, 15, 1, B[0]); }
  });
}
/** motoboy de lado (indo para a direita): quadros 0-3 andando (roda gira, balanço no paralelepípedo), 4-5 parado (motor ligado) */
export function folhaMotoboy(o = {}) {
  const V = rampa(o.moto || '#d22b2b', 4, { contraste: .3 }), BA = rampa(o.bau || '#13b3a5', 4, { contraste: .32 }), JA = rampa(o.jaqueta || '#30343f', 4, { contraste: .3 });
  const JE = rampa(o.calca || '#3f5f96', 4, { contraste: .3 }), CP = rampa(o.capacete || '#eef0f4', 4, { contraste: .3 }), RA = o.raio || '#ffd23a';
  return folhaSprite(54, 42, 6, (P, i) => {
    const anda = i < 4, ang = anda ? i * (Math.PI * 2 / 3) / 4 : 0, bob = anda ? [0, 1, 0, 0][i] : (i === 5 ? 1 : 0), dy = 1 + bob;
    const roda = (cx, cy) => {
      for (let y = -8; y <= 8; y++) for (let x = -8; x <= 8; x++) { const d = Math.hypot(x, y); if (d <= 7.4) P.px(cx + x, cy + y, d > 5.6 ? (d > 6.6 ? '#1c1b22' : (x + y < -4 ? '#3a3944' : '#2b2a33')) : d > 4.6 ? (x + y < 0 ? '#c9d0d8' : '#8d96a2') : null); }
      for (let s = 0; s < 3; s++) { const a = ang + s * Math.PI * 2 / 3; P.linha(cx, cy, cx + Math.cos(a) * 4.6, cy + Math.sin(a) * 4.6, '#7e8794'); }
      P.rect(cx - 1, cy - 1, 2, 2, '#e6ebf0');
    };
    roda(12, 33); roda(42, 33);
    P.linha(12, 33, 25, 29, '#6d7682').linha(12, 32, 25, 28, '#8d96a2');
    P.rect(5, 28, 13, 3, '#c5ccd4').rect(5, 28, 13, 1, '#eef2f6').rect(5, 30, 13, 1, '#7e8792').rect(3, 28, 2, 2, '#2a2a2e').linha(17, 30, 25, 31, '#7e8792');
    for (let x = 7; x <= 17; x++) P.px(x, 24 - (x > 9 && x < 15 ? 1 : 0), V[2]);
    P.rect(3, 23, 2, 2, '#ff3b30').rect(2, 22, 16, 1, '#5d636b');
    // baú
    P.rect(1, 8 + dy, 16, 14, BA[2]).rect(1, 8 + dy, 16, 2, BA[3]).rect(1, 10 + dy, 16, 1, BA[1]).rect(14, 11 + dy, 3, 11, BA[1]).rect(1, 20 + dy, 16, 1, BA[0]);
    P.mapa(6, 12 + dy, ['...##', '..##.', '.##..', '#####', '..##.', '.##..', '##...'], { '#': RA });
    P.rect(1, 18 + dy, 13, 1, '#e8f0f6');
    // garfo, para-lama e farol
    P.linha(42, 33, 37, 17, '#c5ccd4').linha(43, 33, 38, 17, '#7e8792');
    for (let x = 37; x <= 47; x++) P.px(x, 24 - (x > 39 && x < 45 ? 1 : 0), V[2]);
    P.rect(39, 15 + bob, 4, 3, '#fff4b8').px(42, 15 + bob, '#ffffff').rect(37, 15 + bob, 2, 3, '#4b5058');
    P.linha(34, 13 + bob, 38, 15 + bob, '#3b3f49');
    // motor, quadro, tanque, banco
    P.rect(21, 26, 10, 6, '#3b3f49'); for (let y = 27; y < 32; y += 2) P.rect(21, y, 10, 1, '#555b67'); P.rect(22, 31, 7, 2, '#555b67');
    P.linha(37, 18, 29, 26, V[0]).linha(36, 18, 28, 26, V[1]);
    P.poli([[24, 19 + bob], [35, 18 + bob], [36, 22 + bob], [34, 25], [25, 25], [23, 22 + bob]], V[2]); P.rect(26, 19 + bob, 7, 1, V[3]).rect(25, 24, 9, 1, V[1]);
    P.rect(17, 23, 6, 3, V[1]);
    P.rect(13, 21 + bob, 12, 3, '#232129').rect(13, 21 + bob, 12, 1, '#3d3a45');
    // piloto
    P.poli([[19, 19 + dy], [28, 20 + dy], [28, 23 + dy], [19, 23 + dy]], JE[2]); P.rect(19, 19 + dy, 9, 1, JE[3]);
    P.poli([[26, 21 + dy], [29, 21 + dy], [29, 29], [26, 29]], JE[1]); P.rect(25, 29, 6, 2, '#5b3a24').px(30, 30, '#5b3a24').rect(25, 29, 6, 1, '#7a5236');
    P.poli([[17, 9 + dy], [24, 10 + dy], [25, 21 + dy], [17, 21 + dy]], JA[2]); P.rect(17, 9 + dy, 1, 12, JA[3]).rect(23, 11 + dy, 2, 10, JA[1]); P.rect(17, 15 + dy, 8, 1, '#e8f0f6');
    P.poli([[20, 11 + dy], [24, 11 + dy], [35, 13 + bob], [35, 15 + bob], [31, 15 + bob], [20, 14 + dy]], JA[3]); P.rect(33, 13 + bob, 3, 2, '#1e1d22');
    const hy = 5 + dy;
    P.disc(21, hy, 4.8, CP[2]); P.rect(18, hy - 3, 3, 1, CP[3]).px(17, hy - 2, CP[3]); P.rect(20, hy + 3, 5, 2, CP[1]);
    P.rect(22, hy - 2, 4, 3, '#26314d').px(23, hy - 2, '#9fc2ff').px(25, hy, '#3d4e78'); P.rect(24, hy + 2, 2, 2, CP[1]);
  });
}
/** vira-lata caramelo de lado (olhando para a esquerda): 0-1 abanando o rabo, 2-3 latindo */
export function folhaCachorro(o = {}) {
  const C = rampa(o.cor || '#d08a3c', 4, { contraste: .3 });
  return folhaSprite(26, 18, 4, (P, i) => {
    const late = i >= 2, rabo = i % 2;
    P.elipse(14, 10, 7, 3.4, C[2]); P.rect(9, 7, 10, 1, C[3]); P.rect(8, 9, 3, 4, '#f4ead8');
    for (const [x, d] of [[9, 0], [11, 1], [17, 0], [19, 1]]) P.rect(x, 12, 2, 5, d ? C[1] : C[2]).px(x, 16, '#f4ead8');
    if (rabo) P.linha(20, 9, 23, 5, C[2]).px(23, 4, C[3]); else P.linha(20, 9, 24, 8, C[2]).px(24, 7, C[3]);
    const hy = late ? 5 : 6;
    P.disc(6, hy, 3.2, C[2]); P.rect(1, hy + 1, 4, 2, C[3]).px(0, hy + 1, OUT); P.px(4, hy - 1, OUT); P.rect(7, hy - 3, 2, 3, C[0]);
    if (late) P.rect(1, hy + 3, 3, 1, '#7a2a2a').px(1, hy + 4, C[2]);
  });
}
/** balão de fala pixelado (com rabinho) — um quadro; texto em pt-BR com acentos */
export function folhaBalao(texto, o = {}) {
  const tw = medirPx(texto), acento = /[ÁÀÂÃÉÊÍÓÔÕÚ]/.test(texto) ? 2 : 0, W = tw + 8, H = 7 + 6 + acento + 4;
  return folhaSprite(W, H, 1, P => {
    const bh = H - 4;
    P.rect(1, 0, W - 2, bh, '#fffaf0').rect(0, 1, W, bh - 2, '#fffaf0').rect(1, bh - 2, W - 2, 1, '#e3dccb');
    P.poli([[4, bh - 1], [9, bh - 1], [3, H]], '#fffaf0');
    textoPx(P, texto, 4, 3 + acento, o.cor || '#d8262e');
  }, { contorno: o.contorno || '#1b1424' });
}

// ───────────────────────── partículas (pixels quadrados ou discos pixelados) ─────────────────────────
const PART_V = `attribute float tam; attribute vec4 cor; uniform float uEsc; varying vec4 vCor;
void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.); gl_Position = projectionMatrix * mv; gl_PointSize = tam * uEsc / max(.1, -mv.z); vCor = cor; }`;
const PART_F = `uniform float uForma; varying vec4 vCor;
void main(){ if (vCor.a < .004) discard;
  if (uForma > .5) { vec2 q = (floor(gl_PointCoord * 6.) + .5) / 6. - .5; if (dot(q, q) > .22) discard; }
  gl_FragColor = vCor; }`;
/** sistema de partículas: update(t, P) escreve P.set(i, x,y,z, tam(m), [r,g,b] linear, alfa). o: {aditivo, forma:'quadrado'|'disco'} */
export function particulas(S, n, update, o = {}) {
  const geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), tam = new Float32Array(n), corA = new Float32Array(n * 4);
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('tam', new THREE.BufferAttribute(tam, 1)); geo.setAttribute('cor', new THREE.BufferAttribute(corA, 4));
  const mat = new THREE.ShaderMaterial({ uniforms: { uEsc: { value: 1000 }, uForma: { value: o.forma === 'disco' ? 1 : 0 } }, vertexShader: PART_V, fragmentShader: PART_F, transparent: true, depthWrite: false, blending: o.aditivo ? THREE.AdditiveBlending : THREE.NormalBlending });
  const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; pts.renderOrder = o.ordem ?? 5; S.scene.add(pts);
  const Pt = { n, pts, mat, update,
    set(i, x, y, z, s, c, a) { pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z; tam[i] = s; corA[i * 4] = c[0]; corA[i * 4 + 1] = c[1]; corA[i * 4 + 2] = c[2]; corA[i * 4 + 3] = a; },
    _tick(t) { corA.fill(0); update(t, Pt); geo.attributes.position.needsUpdate = geo.attributes.tam.needsUpdate = geo.attributes.cor.needsUpdate = true; mat.uniforms.uEsc.value = S.V.h / (2 * Math.tan(S.camera.fov * Math.PI / 360)); } };
  S.particulas.push(Pt); return Pt;
}
/** poeira dourada flutuando na luz. o: {caixa:[x0,x1,y0,y1,z0,z1], n, cor, forca} */
export function poeira(S, o = {}) {
  const [x0, x1, y0, y1, z0, z1] = o.caixa || [-10, 10, .3, 6, -6, 6], n = o.n ?? 240, r = rng(o.seed ?? 21), c = linear(o.cor || '#ffd58a').map(v => v * (o.forca ?? 3));
  const B = Array.from({ length: n }, () => [r(), r(), r(), r() * 6.28, .3 + r() * .7, r()]);
  return particulas(S, n, (t, P) => B.forEach((b, i) => {
    const x = x0 + (((b[0] + t * .012 * (b[4] - .5)) % 1 + 1) % 1) * (x1 - x0), y = y0 + (((b[1] + t * .02 * b[4]) % 1 + 1) % 1) * (y1 - y0), z = z0 + b[2] * (z1 - z0);
    const tw = Math.max(0, Math.sin(t * (1.5 + b[4] * 2) + b[3])) ** 2;
    P.set(i, x + Math.sin(t * .7 + b[3]) * .25, y, z, (o.tam ?? .05) * (b[5] < .15 ? 1.8 : 1), c, .25 + .75 * tw);
  }), { aditivo: true });
}
/** pétalas/folhas caindo de uma copa. o: {centro:[x,y,z], raio, n, cor, chao, vento} */
export function petalas(S, o = {}) {
  const [cx, cy, cz] = o.centro || [0, 5, 0], R = o.raio ?? 2.5, n = o.n ?? 50, r = rng(o.seed ?? 33), cs = (o.cores || ['#ffd23a', '#f2b51e', '#ffe680']).map(linear), ch = o.chao ?? .17;
  const B = Array.from({ length: n }, () => [r() * 6.28, Math.sqrt(r()) * R, r(), 2.5 + r() * 2.5, r() * 6.28, Math.floor(r() * cs.length)]);
  return particulas(S, n, (t, P) => B.forEach((b, i) => {
    const p = ((t / b[3] + b[2]) % 1), y = cy - p * (cy - ch + .3), sw = Math.sin(t * 2.2 + b[4]) * .35;
    const x = cx + Math.cos(b[0]) * b[1] + sw + p * (o.vento ?? 1.2), z = cz + Math.sin(b[0]) * b[1] * .8;
    P.set(i, x, Math.max(ch, y), z, o.tam ?? .09, cs[b[5]], y < ch ? 0 : Math.min(1, p * 6) * (1 - suave(.92, 1, p)));
  }), { forma: 'quadrado' });
}
/** fumaça em baforadas a partir de uma fonte móvel: fonte(t) → [x,y,z] ou null. o: {intervalo, vida, deriva:[dx,dy,dz], cor, tam} */
export function fumaca(S, fonte, o = {}) {
  const dt = o.intervalo ?? .09, vida = o.vida ?? .9, N = Math.ceil(vida / dt) + 1, c = linear(o.cor || '#d9d4cc'), dr = o.deriva || [-.5, .55, .1];
  return particulas(S, N, (t, P) => {
    for (let k = 0; k < N; k++) {
      const nasc = (Math.floor(t / dt) - k) * dt, age = t - nasc; if (nasc < -10 || age > vida) continue;
      const p = fonte(nasc); if (!p) continue; const a = age / vida, f = o.forca ? o.forca(nasc) : 1; if (f <= 0) continue;
      const j = hash(Math.round(nasc * 100), 3, 9); P.set(k, p[0] + dr[0] * age + (j - .5) * .25 * age, p[1] + dr[1] * age * (.7 + j * .6), p[2] + dr[2] * age, (o.tam ?? .16) * (.7 + j * .6) * (1 + a * 2.4) * f, c, (1 - a) ** 1.5 * (o.alfa ?? .75) * f);
    }
  }, { forma: 'disco', ordem: 6 });
}
/** gotas de respingo (água): eventos [{t0, x, z, n}] */
export function respingos(S, eventos, o = {}) {
  const tot = eventos.reduce((s, e) => s + (e.n ?? 14), 0), r = rng(o.seed ?? 77), c = linear(o.cor || '#cfe6ff').map(v => v * 1.6);
  const G = []; eventos.forEach(e => { for (let i = 0; i < (e.n ?? 14); i++) { const a = r() * Math.PI * 2, v = 1 + r() * 1.6; G.push([e, Math.cos(a) * v * .7 + (e.vx ?? 0), 2 + r() * 2, Math.sin(a) * v * .5]); } });
  return particulas(S, tot, (t, P) => G.forEach(([e, vx, vy, vz], i) => { const age = t - e.t0; if (age < 0 || age > .6) return; const y = .05 + vy * age - 9.8 * age * age / 2; if (y < 0) return; P.set(i, e.x + vx * age, y, e.z + vz * age, .06, c, 1 - age / .6); }), { forma: 'quadrado', aditivo: false });
}
/** vagalumes piscando (aditivos, fazem bloom) */
export function vagalumes(S, o = {}) {
  const [x0, x1, y0, y1, z0, z1] = o.caixa || [-5, 5, .5, 3, -2, 2], n = o.n ?? 16, r = rng(o.seed ?? 5), c = linear(o.cor || '#d8ff7a').map(v => v * 6);
  const B = Array.from({ length: n }, () => [r(), r(), r(), r() * 6.28, .5 + r()]);
  return particulas(S, n, (t, P) => B.forEach((b, i) => P.set(i, x0 + (x1 - x0) * b[0] + Math.sin(t * .6 * b[4] + b[3]) * .5, y0 + (y1 - y0) * b[1] + Math.sin(t * .9 + b[3] * 2) * .25, z0 + (z1 - z0) * b[2], .07, c, Math.max(0, Math.sin(t * 2.4 * b[4] + b[3])) ** 3)), { aditivo: true });
}

// ───────────────────────── luz: raios (cortinas aditivas) e poça d'água ─────────────────────────
const QUAD_V = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
const RAIO_F = `uniform float uT, uForca, uSeed; uniform vec3 uCor; varying vec2 vUv;
void main(){ float a = smoothstep(0., .3, vUv.y) * smoothstep(1., .45, vUv.y); float w = pow(sin(3.14159 * vUv.x), 2.);
  float f = .7 + .3 * sin(uT * .8 + uSeed * 6.3) * sin(uT * .37 + uSeed * 2.1); gl_FragColor = vec4(uCor * a * w * uForca * f, 1.); }`;
/** raios de luz: faixas aditivas na direção dir (do céu para o chão), sempre de frente para a câmera. o: {pontos:[[x,y,z]...] (topo), dir, comp, larg, cor, forca} */
export function raios(S, o = {}) {
  const dir = v3(o.dir || [.55, -.75, .2]).normalize(), c = new THREE.Color(o.cor || '#ffc98a'), out = [];
  (o.pontos || []).forEach((p, i) => {
    const comp = Array.isArray(o.comp) ? o.comp[i % o.comp.length] : (o.comp ?? 14), larg = Array.isArray(o.larg) ? o.larg[i % o.larg.length] : (o.larg ?? 1.6);
    const mat = new THREE.ShaderMaterial({ uniforms: { uT: { value: 0 }, uForca: { value: o.forca ?? .12 }, uSeed: { value: i * .37 }, uCor: { value: c } }, vertexShader: QUAD_V, fragmentShader: RAIO_F, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(larg, comp), mat); m.renderOrder = 4; S.scene.add(m);
    const ini = v3(p), centro = ini.clone().addScaledVector(dir, comp / 2);
    out.push({ m, centro, mat });
  });
  const R = { lista: out, dir, _tick(t) {
    for (const { m, centro, mat } of out) {
      mat.uniforms.uT.value = t; const toCam = S.camera.position.clone().sub(centro).normalize();
      const dx = new THREE.Vector3().crossVectors(dir, toCam).normalize(), nz = new THREE.Vector3().crossVectors(dx, dir).normalize();
      m.matrixAutoUpdate = false; m.matrix.makeBasis(dx, dir.clone().negate(), nz).setPosition(centro); m.matrixWorldNeedsUpdate = true;
    } } };
  S.raios.push(R); return R;
}
const AGUA_F = `uniform float uT, uPPU; uniform vec3 uA, uB, uLuz; uniform vec2 uC, uR; uniform vec4 uOnda[4]; varying vec3 vW;
float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void main(){ vec2 p = (floor(vW.xz * uPPU) + .5) / uPPU; vec2 q = (p - uC) / uR;
  float e = length(q) + .12 * sin(atan(q.y, q.x) * 3. + 1.3) + .06 * sin(atan(q.y, q.x) * 7.); if (e > 1.) discard;
  vec3 c = mix(uA, uB, clamp(.5 + q.y * .6, 0., 1.));
  float w = sin(p.x * 9. + uT * 2.3) * sin(p.y * 13. - uT * 1.7); float brilho = step(.82, w) * .7;
  for (int i = 0; i < 4; i++) { float age = uT - uOnda[i].z; if (age > 0. && age < 2.) { float d = length(p - uOnda[i].xy); brilho += step(abs(d - age * 1.1), .045) * exp(-age * 1.6) * uOnda[i].w; } }
  brilho += step(.985, h(floor(p * 3.) + floor(uT * 6.))) * .8;
  c = mix(c, uLuz, clamp(brilho, 0., 1.)); c *= mix(1., .7, smoothstep(.8, 1., e));
  gl_FragColor = vec4(c, mix(.92, .6, smoothstep(.75, 1., e))); }`;
/** poça d'água animada (pixelada): reflete o céu dourado, cintila e faz ondas em anel. o: {x,z,rx,rz, ondas:[{x,z,t0,forca}]} */
export function poca(S, o = {}) {
  const rx = o.rx ?? 1.2, rz = o.rz ?? .7, ondas = (o.ondas || []).slice(0, 4);
  const u = { uT: { value: 0 }, uPPU: { value: CFG.ppu }, uA: { value: new THREE.Color(o.corA || '#ffcf8a') }, uB: { value: new THREE.Color(o.corB || '#6d86b8') }, uLuz: { value: new THREE.Color(o.luz || '#fff3d0').multiplyScalar(1.6) }, uC: { value: new THREE.Vector2(o.x ?? 0, o.z ?? 0) }, uR: { value: new THREE.Vector2(rx, rz) }, uOnda: { value: Array.from({ length: 4 }, (_, i) => ondas[i] ? new THREE.Vector4(ondas[i].x, ondas[i].z, ondas[i].t0, ondas[i].forca ?? 1) : new THREE.Vector4(0, 0, -99, 0)) } };
  const mat = new THREE.ShaderMaterial({ uniforms: u, vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`, fragmentShader: AGUA_F, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4 });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(rx * 2.6, rz * 2.6), mat); m.rotation.x = -Math.PI / 2; m.position.set(o.x ?? 0, (o.y ?? 0) + .012, o.z ?? 0); m.renderOrder = 2; S.scene.add(m);
  S.agua.push(u); return m;
}

// ───────────────────────── palco: renderer + pós-processo HD-2D ─────────────────────────
const HD2D_F = `
uniform sampler2D tCor, tProf; uniform float uFoco, uFaixa, uAbert, uMax, uNear, uFar; uniform vec2 uRes;
uniform float uTelaC, uTelaF, uTelaS, uTelaMax; uniform vec3 uNevA, uNevB; uniform float uNevIni, uNevFim, uNevMax;
varying vec2 vUv;
float lin(float d){ float z = d * 2. - 1.; return 2. * uNear * uFar / (uFar + uNear - z * (uFar - uNear)); }
float coc(float z, vec2 uv){ float dz = max(0., abs(z - uFoco) - uFaixa); float c = dz / z * uAbert * uRes.y;
  float s = smoothstep(uTelaF, uTelaF + uTelaS, abs(uv.y - uTelaC)) * uTelaMax; return clamp(max(c, s), 0., uMax); }
vec3 nev(vec3 c, float z, vec2 uv){ float k = clamp((z - uNevIni) / (uNevFim - uNevIni), 0., 1.) * uNevMax; return mix(c, mix(uNevB, uNevA, uv.y), k); }
void main(){
  float zC = lin(texture2D(tProf, vUv).r), cC = coc(zC, vUv);
  vec3 cor = nev(texture2D(tCor, vUv).rgb, zC, vUv); float tot = 1., r = 1.5, ang = 0.;
  for (int i = 0; i < 320; i++) {
    if (r >= uMax) break;
    vec2 uv = vUv + vec2(cos(ang), sin(ang)) * r / uRes;
    float z = lin(texture2D(tProf, uv).r); vec3 c = nev(texture2D(tCor, uv).rgb, z, uv); float cs = coc(z, uv);
    if (z > zC) cs = clamp(cs, 0., cC * 2.);
    float m = smoothstep(r - .5, r + .5, cs);
    cor += mix(cor / tot, c, m); tot += 1.; ang += 2.39996323; r += 2.4 / r;
  }
  gl_FragColor = vec4(cor / tot, 1.);
}`;
class PassHD2D extends Pass {
  constructor(scene, camera, w, h) {
    super(); this.scene = scene; this.camera = camera;
    this.rt = new THREE.WebGLRenderTarget(w, h, { type: THREE.HalfFloatType, samples: 4, depthTexture: new THREE.DepthTexture(w, h) });
    this.mat = new THREE.ShaderMaterial({ uniforms: {
      tCor: { value: this.rt.texture }, tProf: { value: this.rt.depthTexture }, uFoco: { value: 30 }, uFaixa: { value: 3 }, uAbert: { value: .03 }, uMax: { value: 30 }, uNear: { value: 1 }, uFar: { value: 300 }, uRes: { value: new THREE.Vector2(w, h) },
      uTelaC: { value: .5 }, uTelaF: { value: .3 }, uTelaS: { value: .2 }, uTelaMax: { value: 0 }, uNevA: { value: new THREE.Color('#ffd9a0') }, uNevB: { value: new THREE.Color('#c9a07a') }, uNevIni: { value: 40 }, uNevFim: { value: 90 }, uNevMax: { value: .5 } },
      vertexShader: QUAD_V, fragmentShader: HD2D_F, depthTest: false, depthWrite: false });
    this.quad = new FullScreenQuad(this.mat);
  }
  render(renderer, writeBuffer) {
    renderer.setRenderTarget(this.rt); renderer.clear(); renderer.render(this.scene, this.camera);
    const u = this.mat.uniforms; u.uNear.value = this.camera.near; u.uFar.value = this.camera.far;
    renderer.setRenderTarget(this.renderToScreen ? null : writeBuffer); this.quad.render(renderer);
  }
}
const GRADE_F = `uniform sampler2D tDiffuse; uniform vec2 uRes, uSolUV; uniform float uT, uGrao, uVin, uSat, uCont, uSolForca; uniform vec3 uSombra, uLuz, uSolCor; varying vec2 vUv;
float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void main(){ vec3 c = texture2D(tDiffuse, vUv).rgb; float l = dot(c, vec3(.2126, .7152, .0722));
  c *= mix(uSombra, vec3(1.), smoothstep(.0, .55, l)) * mix(vec3(1.), uLuz, smoothstep(.35, 1., l));
  c = clamp(c, 0., 1.); c = mix(c, c * c * (3. - 2. * c), uCont);
  l = dot(c, vec3(.2126, .7152, .0722)); c = mix(vec3(l), c, uSat);
  vec2 d = (vUv - uSolUV) * vec2(uRes.x / uRes.y, 1.); c += uSolCor * uSolForca * exp(-dot(d, d) * 2.5);
  vec2 v = vUv - .5; v.x *= uRes.x / uRes.y * 1.2; c *= 1. - uVin * smoothstep(.22, .82, length(v));
  c += (h(vUv * uRes + fract(uT * 7.13) * 100.) - .5) * uGrao;
  gl_FragColor = vec4(c, 1.); }`;
/**
 * Palco HD-2D. o: {fov, exposicao, ceu:[cores fundo], hemi:{ceu,chao,forca}, sol:{cor,forca,dir}, sombraCaixa:[cx,cz,raio],
 *   tilt:{foco,faixa,abertura,max, tela:{centro,faixa,suave,max}}, nevoa:{cima,baixo,ini,fim,max},
 *   bloom:{forca,raio,limiar}, grade:{sombra,luz,sat,contraste,vinheta,grao, sol:{uv,cor,forca}}, tintaSprite}
 * Devolve S = {scene, camera, renderer, sol, hemi, tilt, sprites, particulas, raios, update(t)}.
 */
export function palco(o = {}) {
  const V = window.VIDEO;
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(V.w, V.h, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = o.exposicao ?? 1;
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.domElement.className = 'layer'; (o.parent || document.getElementById('stage')).prepend(renderer.domElement);
  const scene = new THREE.Scene();
  const cv = document.createElement('canvas'); cv.width = 4; cv.height = 256; const cg = cv.getContext('2d'), gr = cg.createLinearGradient(0, 0, 0, 256);
  (o.ceu || ['#f7c98a', '#f0a868', '#c98a72']).forEach((k, i, a) => gr.addColorStop(i / (a.length - 1), k)); cg.fillStyle = gr; cg.fillRect(0, 0, 4, 256);
  scene.background = new THREE.CanvasTexture(cv); scene.background.colorSpace = THREE.SRGBColorSpace;
  const camera = new THREE.PerspectiveCamera(o.fov ?? 30, V.w / V.h, o.perto ?? 1, o.longe ?? 300);
  const hemi = new THREE.HemisphereLight(o.hemi?.ceu ?? '#9fb0d8', o.hemi?.chao ?? '#6a4a3a', o.hemi?.forca ?? 1.1); scene.add(hemi);
  const sol = new THREE.DirectionalLight(o.sol?.cor ?? '#ffc27a', o.sol?.forca ?? 3); sol.castShadow = true;
  sol.shadow.mapSize.set(4096, 4096); sol.shadow.bias = -.0003; sol.shadow.normalBias = .03; sol.shadow.radius = o.sol?.suave ?? 3;
  scene.add(sol, sol.target);
  const dirSol = v3(o.sol?.dir || [-.62, .42, .66]).normalize();
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(V.w, V.h, { type: THREE.HalfFloatType })); composer.setPixelRatio(1); composer.setSize(V.w, V.h);
  const hd = new PassHD2D(scene, camera, V.w, V.h); composer.addPass(hd);
  const b = o.bloom || {}; const bloom = new UnrealBloomPass(new THREE.Vector2(V.w, V.h), b.forca ?? .55, b.raio ?? .6, b.limiar ?? .9); composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const gd = o.grade || {}, C = (c, d) => new THREE.Color(c ?? d);
  const grade = new ShaderPass({ uniforms: { tDiffuse: { value: null }, uRes: { value: new THREE.Vector2(V.w, V.h) }, uT: { value: 0 }, uGrao: { value: gd.grao ?? .025 }, uVin: { value: gd.vinheta ?? .5 }, uSat: { value: gd.sat ?? 1.12 }, uCont: { value: gd.contraste ?? .25 },
    uSombra: { value: C(gd.sombra, '#c9d4f0') }, uLuz: { value: C(gd.luz, '#fff0d6') }, uSolUV: { value: new THREE.Vector2(...(gd.sol?.uv ?? [.05, .95])) }, uSolCor: { value: C(gd.sol?.cor, '#ffb661') }, uSolForca: { value: gd.sol?.forca ?? .22 } }, vertexShader: QUAD_V, fragmentShader: GRADE_F });
  composer.addPass(grade);
  const tl = o.tilt || {}, nv = o.nevoa || {};
  const S = { THREE, V, renderer, scene, camera, composer, sol, hemi, bloom, grade, hd, sprites: [], particulas: [], raios: [], agua: [], update: null, tintaSprite: o.tintaSprite ?? '#fff1de',
    tilt: { foco: tl.foco ?? 30, faixa: tl.faixa ?? 3, abertura: tl.abertura ?? .03, max: tl.max ?? 30, tela: { centro: .5, faixa: .3, suave: .2, max: 0, ...(tl.tela || {}) } },
    nevoa: { cima: nv.cima ?? '#ffd9a0', baixo: nv.baixo ?? '#d8a878', ini: nv.ini ?? 40, fim: nv.fim ?? 90, max: nv.max ?? .5 },
    /** caixa de sombra do sol: centro [x,z] e raio (m) */
    sombra(cx, cz, raio = 22) { const c = new THREE.Vector3(cx, 0, cz); sol.target.position.copy(c); sol.position.copy(c).addScaledVector(dirSol, raio * 2.5); const sc = sol.shadow.camera; sc.left = sc.bottom = -raio; sc.right = sc.top = raio; sc.near = 1; sc.far = raio * 6; sc.updateProjectionMatrix(); } };
  const sc = o.sombraCaixa || [0, -2, 22]; S.sombra(...sc);
  onTick(t => {
    S.t = t; grade.uniforms.uT.value = t;
    if (S.update) S.update(t);
    camera.updateMatrixWorld();
    for (const s of S.sprites) billboard(S, s);
    for (const p of S.particulas) p._tick(t);
    for (const r of S.raios) r._tick(t);
    for (const a of S.agua) a.uT.value = t;
    const u = hd.mat.uniforms, T = S.tilt, N = S.nevoa;
    u.uFoco.value = T.foco; u.uFaixa.value = T.faixa; u.uAbert.value = T.abertura; u.uMax.value = Math.max(2, T.max);
    u.uTelaC.value = T.tela.centro; u.uTelaF.value = T.tela.faixa; u.uTelaS.value = T.tela.suave; u.uTelaMax.value = T.tela.max;
    u.uNevA.value.set(N.cima); u.uNevB.value.set(N.baixo); u.uNevIni.value = N.ini; u.uNevFim.value = N.fim; u.uNevMax.value = N.max;
    for (const h of S.hud || []) h(t);
    composer.render();
  });
  return S;
}

/**
 * Câmera de travelling HD-2D: alto em 3/4, FOV estreito, desliza do alvo `de` ao alvo `ate`.
 * o: {de:[x,y,z], ate:[x,y,z], dist (m), pitch (graus p/ baixo), yaw (graus), fov, t0, t1, ease, focoExtra}. dist/pitch/yaw/fov aceitam [ini, fim].
 */
export function travelling(S, o) {
  const val = (x, k) => Array.isArray(x) ? lerp(x[0], x[1], k) : x, A = new THREE.Vector3(), D = Math.PI / 180;
  return t => {
    const k = fase(t, o.t0 ?? 0, o.t1 ?? S.V.dur, o.ease ?? 'none');
    A.copy(v3(o.de)).lerp(v3(o.ate), k);
    const d = val(o.dist ?? 34, k), p = val(o.pitch ?? 38, k) * D, y = val(o.yaw ?? 8, k) * D;
    S.camera.position.set(A.x + d * Math.cos(p) * Math.sin(y), A.y + d * Math.sin(p), A.z + d * Math.cos(p) * Math.cos(y)); S.camera.lookAt(A);
    const fov = val(o.fov ?? 30, k); if (S.camera.fov !== fov) { S.camera.fov = fov; S.camera.updateProjectionMatrix(); }
    S.tilt.foco = d + (o.focoExtra ?? 0);
    return A;
  };
}

// ───────────────────────── HUD: placa de local (estilo "Saltwind Harbor") ─────────────────────────
let HUDC = null;
function hudCanvas(S) {
  if (HUDC) return HUDC;
  const c = document.createElement('canvas'); c.width = S.V.w; c.height = S.V.h; c.className = 'layer'; c.style.zIndex = 5; document.getElementById('stage').appendChild(c);
  const ctx = c.getContext('2d'); ctx.imageSmoothingEnabled = false; S.hud = S.hud || []; S.hud.unshift(() => ctx.clearRect(0, 0, c.width, c.height));
  return (HUDC = { c, ctx });
}
/** placa de local pixelada: título (e subtítulo) numa placa escura com moldura dourada e ramos. o: {sub, t0, t1, y (px do centro), escala} */
export function placaLocal(S, texto, o = {}) {
  const { ctx } = hudCanvas(S), esc = o.escala ?? 5, sub = o.sub, padX = 7, tw = medirPx(texto), sw = sub ? medirPx(sub) : 0;
  const W = Math.max(tw, sw) + padX * 2, H = sub ? 27 : 17, orn = o.ramo ?? 22;
  const P = new Pixels(W, H), Q = new Pixels(orn * 2 + W, 9);
  const D = rampa('#d9b25e', 4, { contraste: .3 });
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const cant = (x < 2 || x >= W - 2) && (y < 2 || y >= H - 2); if (cant && (x === 0 || x === W - 1) && (y === 0 || y === H - 1)) continue; const bd = x === 0 || y === 0 || x === W - 1 || y === H - 1, bi = x === 2 || y === 2 || x === W - 3 || y === H - 3; P.px(x, y, bd ? '#120e18' : bi ? (y === 2 ? D[3] : y === H - 3 ? D[1] : D[2]) : (x === 1 || y === 1 || x === W - 2 || y === H - 2) ? '#2a2034' : '#1f1a2c', bd ? 255 : 236); }
  for (const [x, y] of [[2, 2], [W - 3, 2], [2, H - 3], [W - 3, H - 3]]) P.px(x, y, D[3]);
  textoPx(P, texto, Math.round((W - tw) / 2) + 1, 6, '#07050a'); textoPx(P, texto, Math.round((W - tw) / 2), 5, '#f7ecd0');
  if (sub) { const sx = Math.round((W - sw) / 2); textoPx(P, sub, sx + 1, 17, '#07050a'); textoPx(P, sub, sx, 16, D[3]); P.rect(5, 14, W - 10, 1, D[0]); }
  const my = 4;
  for (let x = 0; x < orn; x++) for (const s of [0, 1]) { const xx = s ? orn + W + x : orn - 1 - x; Q.px(xx, my, x > orn - 3 ? D[3] : D[2]); if (x % 5 === 2) { Q.px(xx, my - 1 - (x % 10 === 2 ? 1 : 0), '#9ab04a'); Q.px(xx + (s ? 1 : -1), my - 2 + (x % 10 === 2 ? 0 : 3), '#6f8a3a'); } }
  for (const s of [0, 1]) { const ex = s ? orn * 2 + W - 2 : 1; Q.px(ex, my - 1, D[3]).px(ex, my + 1, D[3]).px(ex - 1, my, D[3]).px(ex + 1, my, D[3]).px(ex, my, '#fff3c0'); }
  const cP = P.canvas(), cQ = Q.canvas(), t0 = o.t0 ?? .4, t1 = o.t1 ?? 3.2, cx = S.V.w / 2, cy = o.y ?? S.V.h * .17;
  S.hud.push(t => {
    if (t < t0 || t > t1 + .5) return;
    const kin = fase(t, t0, t0 + .45, 'power2.out'), kout = 1 - fase(t, t1, t1 + .4, 'power1.in'), a = Math.min(kin, kout);
    const g = fase(t, t0 + .1, t0 + .7, 'power3.out') * kout;
    ctx.save(); ctx.imageSmoothingEnabled = false;
    const ow = Math.round(orn * g), qy = Math.round(cy - 4.5 * esc + (H - 9) / 2 * 0);
    if (ow > 0) { ctx.globalAlpha = a; ctx.drawImage(cQ, orn - ow, 0, ow, 9, Math.round(cx - (W / 2 + ow) * esc), Math.round(cy - 4.5 * esc), ow * esc, 9 * esc); ctx.drawImage(cQ, orn + W, 0, ow, 9, Math.round(cx + W / 2 * esc), Math.round(cy - 4.5 * esc), ow * esc, 9 * esc); }
    const step = Math.round((1 - kin) * 3) * esc;
    ctx.globalAlpha = a; ctx.drawImage(cP, Math.round(cx - W / 2 * esc), Math.round(cy - H / 2 * esc) + step, W * esc, H * esc);
    ctx.restore();
  });
}
