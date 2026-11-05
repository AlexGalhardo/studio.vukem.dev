// Kit do estilo "traço simples": formas chapadas recortadas à mão (sem contorno, sem sombra, sem gradiente),
// borda que ferve a 12 qps, paleta curta, entradas elásticas, saídas em chicote, fundo que troca seco.
// Depende de core.js e kit.js (K, onTick, VIDEO). Tudo é função do tempo t: nada toca sozinho.
(function () {
  const TR = (window.TR = {});

  // ── paletas (6 cores + preto). P é a padrão; troque com TR.usarPaleta('pastel') ANTES de desenhar ──
  TR.PALETAS = {
    neon:   { k: '#000', L: '#d3f76f', R: '#e04a50', V: '#655af6', M: '#cd3bda', G: '#5fc697', W: '#f6f3ec' },
    pastel: { k: '#1d1a2b', L: '#ffe48a', R: '#ff8a7a', V: '#8fa2ff', M: '#f7a8d8', G: '#8fdcb4', W: '#fffaf0' },
    terra:  { k: '#1f1712', L: '#f2c14e', R: '#d1495b', V: '#2e5e8c', M: '#ed7d3a', G: '#5b8c5a', W: '#f4ead5' },
    mar:    { k: '#06141f', L: '#ffd23f', R: '#ff5d5d', V: '#3a86ff', M: '#00b4d8', G: '#2ec4b6', W: '#f1faee' },
  };
  TR.P = Object.assign({}, TR.PALETAS.neon);
  TR.usarPaleta = nome => Object.assign(TR.P, TR.PALETAS[nome] || nome);

  const f1 = (TR.f1 = v => +(+v).toFixed(1));

  // ── primitivas de desenho (devolvem string SVG) ──
  // Catmull-Rom fechado → Bézier: contorno macio, levemente irregular
  TR.curve = pts => { const n = pts.length, g = i => pts[(i + n) % n]; let d = `M${f1(pts[0][0])} ${f1(pts[0][1])}`;
    for (let i = 0; i < n; i++) { const p0 = g(i - 1), p1 = g(i), p2 = g(i + 1), p3 = g(i + 2);
      d += `C${f1(p1[0] + (p2[0] - p0[0]) / 6)} ${f1(p1[1] + (p2[1] - p0[1]) / 6)} ${f1(p2[0] - (p3[0] - p1[0]) / 6)} ${f1(p2[1] - (p3[1] - p1[1]) / 6)} ${f1(p2[0])} ${f1(p2[1])}`; }
    return d + 'Z'; };
  let SEED = 7; TR.semente = s => (SEED = s);
  // bolha: círculo/elipse "recortado à mão". o: { n: nº de pontos (8–12), j: irregularidade (.03 lisa … .1 torta), rot: graus, seed }
  TR.blob = (cx, cy, rx, ry, fill, o = {}) => { const n = o.n ?? 11, j = o.j ?? .05, r = K.rng(o.seed ?? SEED++), rot = (o.rot ?? 0) * Math.PI / 180, pts = [];
    for (let i = 0; i < n; i++) { const a = (i + (r() - .5) * .3) / n * Math.PI * 2, k = 1 + (r() - .5) * 2 * j, x = Math.cos(a) * rx * k, y = Math.sin(a) * ry * k;
      pts.push([cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot)]); }
    return `<path d="${TR.curve(pts)}" fill="${fill}"/>`; };
  // polígono de arestas retas com vértices levemente tortos (o.j em px; 0 = exato)
  TR.poly = (pts, fill, o = {}) => { const r = K.rng(o.seed ?? SEED++), j = o.j ?? 3;
    return `<path d="M${pts.map(p => `${f1(p[0] + (r() - .5) * 2 * j)} ${f1(p[1] + (r() - .5) * 2 * j)}`).join('L')}Z" fill="${fill}"/>`; };
  TR.starPts = (n, ro, ri, seed, j = .12) => { const r = K.rng(seed), pts = []; for (let i = 0; i < n * 2; i++) { const a = i / (n * 2) * Math.PI * 2 - Math.PI / 2, R = (i % 2 ? ri : ro) * (1 + (r() - .5) * 2 * j); pts.push([Math.cos(a) * R, Math.sin(a) * R]); } return pts; };
  TR.star = (cx, cy, n, ro, ri, fill, o = {}) => TR.poly(TR.starPts(n, ro, ri, o.seed ?? SEED++, o.j ?? .12).map(p => [p[0] + cx, p[1] + cy]), fill, { j: 0 });
  // retângulo de cantos arredondados, levemente torto (telas, pastas, cartões, botões). x,y = canto superior esquerdo
  TR.caixa = (x, y, w, h, r, fill, o = {}) => { const j = o.j ?? 3, rr = K.rng(o.seed ?? SEED++), J = () => (rr() - .5) * 2 * j;
    const pts = [[x + r, y], [x + w - r, y], [x + w, y + r], [x + w, y + h - r], [x + w - r, y + h], [x + r, y + h], [x, y + h - r], [x, y + r]].map(([a, b]) => [a + J(), b + J()]);
    return `<path d="${TR.curve(pts)}" fill="${fill}"/>`; };
  // gota / pino de mapa: bola em cima, ponta em baixo (cx,cy = centro da bola)
  TR.gota = (cx, cy, r, fill) => `<path d="M${f1(cx)} ${f1(cy + 1.75 * r)}C${f1(cx - .55 * r)} ${f1(cy + 1.05 * r)} ${f1(cx - r)} ${f1(cy + .6 * r)} ${f1(cx - r)} ${f1(cy)}A${f1(r)} ${f1(r)} 0 1 1 ${f1(cx + r)} ${f1(cy)}C${f1(cx + r)} ${f1(cy + .6 * r)} ${f1(cx + .55 * r)} ${f1(cy + 1.05 * r)} ${f1(cx)} ${f1(cy + 1.75 * r)}Z" fill="${fill}"/>`;
  // traço grosso de ponta redonda (boca, rugas, costura, coleira, alça)
  TR.line = (d, col, w) => `<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
  TR.G = (id, inner, attr = '') => `<g${id ? ` id="${id}"` : ''}${attr ? ' ' + attr : ''}>${inner}</g>`;
  // olho padrão: bola preta + brilho branco no alto (o brilho dá vida; sem ele vira buraco)
  TR.olho = (x, y, r, o = {}) => TR.blob(x, y, r, r * 1.06, o.cor ?? TR.P.k, { n: 8 }) + TR.blob(x + (o.bx ?? .3) * r, y - .35 * r, r * .3, r * .3, o.brilho ?? TR.P.W, { n: 6 });

  // ── movimento ──
  TR.tf = (el, x, y, s = 1, r = 0, sy) => el.setAttribute('transform', `translate(${f1(x)} ${f1(y)}) rotate(${f1(r)}) scale(${(+s).toFixed(4)} ${(+(sy ?? s)).toFixed(4)})`);
  TR.show = (el, on) => el.setAttribute('display', on ? 'inline' : 'none');
  TR.E = (nome, t, a, b) => K.ease(nome, K.seg(t, a, b));
  const BO = (TR.BO = gsap.parseEase('back.out(2.3)')), BI = (TR.BI = gsap.parseEase('back.in(2)'));
  TR.pop = (t, t0, d = .3) => t < t0 ? 0 : BO(K.seg(t, t0, t0 + d));            // 0 → ~1.15 → 1 (entrada elástica)
  TR.popOut = (t, t0, d = .14) => 1 - BI(K.seg(t, t0, t0 + d));                     // 1 → 0 (saída que encolhe)
  TR.q12 = (t, qps = 12) => Math.floor(t * qps + 1e-6) / qps;                        // tempo de stop-motion
  TR.whip = (t, t1, dist = 1400, d = .17) => dist * TR.E('power3.in', t, t1 - d, t1); // saída em chicote que termina no corte
  TR.passo = (t, lista, ini) => { let v = ini; for (const [a, x] of lista) if (t >= a) v = x; return v; };  // valor em degraus [[t, v], ...]
  TR.janela = (t, a, b) => t >= a && t < b;

  // ── palco: #stage > #art (com a borda que ferve) > #bg + #cam > (#svg + #labs) ──
  TR.palco = () => { const st = K.$('#stage'), W = VIDEO.w, H = VIDEO.h; st.style.background = '#000';
    st.insertAdjacentHTML('afterbegin', `<div id="art" style="position:absolute;left:-40px;top:-40px;width:${W + 80}px;height:${H + 80}px"><div id="bg" style="position:absolute;inset:0;background:#000"></div><div id="cam" style="position:absolute;left:40px;top:40px;width:${W}px;height:${H}px"><svg id="svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="position:absolute;left:0;top:0;overflow:visible"></svg><div id="labs"></div></div></div>`);
    return { art: K.$('#art'), bg: K.$('#bg'), cam: K.$('#cam'), svg: K.$('#svg'), labs: K.$('#labs') }; };

  // borda que ferve: um ruído deslocando tudo, trocado a cada 1/12 s. o: { forca (px, 6–12), freq (.008–.016), qps }
  TR.ferver = (alvo, o = {}) => {
    document.body.insertAdjacentHTML('beforeend', `<svg width="0" height="0" style="position:absolute"><filter id="tr-boil" x="-3%" y="-3%" width="106%" height="106%" color-interpolation-filters="sRGB"><feTurbulence type="fractalNoise" baseFrequency="${o.freq ?? .011}" numOctaves="2" seed="1" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="${o.forca ?? 9}" xChannelSelector="R" yChannelSelector="G"/></filter></svg>`);
    const turb = document.querySelector('#tr-boil feTurbulence'); alvo.style.filter = 'url(#tr-boil)';
    onTick(t => turb.setAttribute('seed', 1 + Math.floor(t * (o.qps ?? 12) + 1e-6) % 11)); };

  // fundo que troca seco: [[t, cor], ...]
  TR.fundos = (el, lista) => onTick(t => { el.style.background = TR.passo(t, lista, lista[0][1]); });
  // tremida de câmera em volta de instantes: [t1, t2, ...]
  TR.tremer = (el, instantes, o = {}) => onTick(t => { let sh = 0; for (const a of instantes) sh = Math.max(sh, 1 - Math.abs(t - a - .08) / (o.dur ?? .24));
    const r = K.rng(Math.floor(t * 24) + 3), A = (o.amp ?? 34) * sh; el.style.transform = sh > 0 ? `translate(${f1((r() - .5) * A)}px,${f1((r() - .5) * A)}px)` : ''; });

  // ── rótulo digitado letra a letra, cada letra levemente torta (como letreiro feito à mão) ──
  document.head.insertAdjacentHTML('beforeend', `<style>.tr-lab{position:absolute;left:0;right:0;text-align:center;font:400 132px/1 'Anton';letter-spacing:.03em;white-space:pre;display:none}.tr-lab span{display:inline-block;transform-origin:50% 70%}</style>`);
  TR.rotulo = (parent, txt, cor, o = {}) => { const el = K.html(parent, `<div class="tr-lab" style="top:${o.top ?? Math.round(VIDEO.h * .693)}px;color:${cor};${o.css ?? ''}">${[...txt].map(c => `<span>${c === ' ' ? '&nbsp;' : c}</span>`).join('')}</div>`);
    const r = K.rng(o.seed ?? txt.length * 31 + 5), spans = K.$$('span', el); return { el, spans, rot: spans.map(() => (r() - .5) * (o.torto ?? 9)), dy: spans.map(() => (r() - .5) * 14) }; };
  TR.rotuloTick = (L, t, t0, t1, ox = 0, oy = 0, passo = .05) => { const on = t >= t0 && t < t1; L.el.style.display = on ? 'block' : 'none'; if (!on) return;
    L.spans.forEach((s, i) => { const ti = t0 + i * passo; s.style.visibility = t >= ti ? 'visible' : 'hidden'; s.style.transform = `translateY(${L.dy[i]}px) rotate(${L.rot[i]}deg) scale(${t - ti < 1 / 20 ? 1.45 : 1})`; });
    L.el.style.transform = `translate(${f1(ox)}px,${f1(oy)}px)`; };
  TR.somDigitar = (t0, n, passo = .05, gain = -2) => { for (let i = 0; i < n; i++) cue('type', t0 + i * passo, { gain }); };

  // ── peças de assinatura ──
  // estouro: estrelas concêntricas que crescem uma atrás da outra até cobrir a tela (a última, da cor do fundo seguinte, "limpa")
  TR.estrelas = (g, o = {}) => { const P = TR.P, cores = o.cores ?? [P.L, P.M, P.V, P.R, P.L, P.k], t0 = o.t0 ?? .5, gap = o.gap ?? .065, dur = o.dur ?? .32,
      cx = o.cx ?? VIDEO.w / 2, cy = o.cy ?? VIDEO.h / 2, esc = o.escala ?? Math.hypot(VIDEO.w, VIDEO.h) / 2 / 168 * 1.1;
    g.innerHTML = cores.map((c, i) => `<g>${TR.poly(TR.starPts(9 + (i % 3), 260, 168, (o.seed ?? 40) + i, .14), c, { j: 0 })}</g>`).join('');
    const kids = [...g.children], fim = t0 + (cores.length - 1) * gap + dur + .03;
    return t => { const on = t >= t0 && t < fim; TR.show(g, on); if (!on) return;
      kids.forEach((k, i) => { const a = t0 + i * gap, u = K.seg(t, a, a + dur); TR.show(k, t >= a); TR.tf(k, cx, cy, .02 + esc * K.ease('power1.in', u), (i % 2 ? 1 : -1) * 18 * u + i * 9); }); }; };

  // campo de ícones em grade com jitter (centro vazio para o herói). Os ícones brotam do centro para fora e somem de fora para dentro.
  // o: { icones: [[fn|nomeEmTR.IC, cores], ...], t0, tSaida, dx, dy, colunas, linhas, vazio, tam, vel, seed }. A câmera (escala/giro) é do chamador.
  TR.campo = (g, o) => { const r = K.rng(o.seed ?? 21), dx = o.dx ?? 240, dy = o.dy ?? 215, itens = [];
    for (let j = -(o.linhas ?? 8); j <= (o.linhas ?? 8); j++) for (let i = -(o.colunas ?? 5); i <= (o.colunas ?? 5); i++) {
      const x = i * dx + (j & 1 ? dx / 2 : 0) + (r() - .5) * 80, y = j * dy + (r() - .5) * 70, d = Math.hypot(x, y);
      if (d < (o.vazio ?? 175)) continue; const [fn, cores] = o.icones[Math.floor(r() * o.icones.length)];
      itens.push({ x, y, d, rot: (r() - .5) * 50, s: (o.tam ?? 1.4) + r() * .4, ph: r() * 6.28, html: (typeof fn === 'string' ? TR.IC[fn] : fn)(cores),
        tp: o.t0 + d / (o.vel ?? 1300) * 1.6 + (r() - .5) * .08, to: o.tSaida + (1 - Math.min(1, d / 2000)) * .3 });
    }
    g.insertAdjacentHTML('afterbegin', itens.map(it => `<g>${it.html}</g>`).join('')); [...g.children].slice(0, itens.length).forEach((el, i) => (itens[i].el = el));
    return { itens, tick: t => { for (const f of itens) { let s = t < f.tp ? 0 : BO(K.seg(t, f.tp, f.tp + .28)); if (t >= f.to) s *= TR.popOut(t, f.to);
      if (s <= .002) { TR.show(f.el, false); continue; } TR.show(f.el, true); TR.tf(f.el, f.x, f.y, s * f.s, f.rot + Math.sin(TR.q12(t) * 2.3 + f.ph) * 5); } } }; };

  // confete de triângulos que voa em leque e encolhe. devolve tick(t, t0, cx, cy)
  TR.confete = (g, o = {}) => { const P = TR.P, n = o.n ?? 10, cores = o.cores ?? [P.M, P.V, P.R];
    const C = Array.from({ length: n }, (_, i) => { const r = K.rng((o.seed ?? 300) + i); return { a: (o.a0 ?? 0) + i / n * (o.arco ?? 6.283) + (r() - .5) * .4, d: (o.dist ?? 300) + r() * (o.var ?? 260), s: (o.tam ?? 1) * (.6 + r() * .6), rot: (r() - .5) * 720, c: cores[i % cores.length] }; });
    g.innerHTML = C.map(c => `<g>${TR.poly([[-26, 20], [30, 14], [0, -32]], c.c, { j: 3 })}</g>`).join(''); const kids = [...g.children], vida = o.vida ?? .9;
    return (t, t0, cx, cy) => { const on = t >= t0 && t < t0 + vida; TR.show(g, on); if (!on) return;
      kids.forEach((k, i) => { const c = C[i], u = TR.E('expo.out', t, t0, t0 + vida * .6), rr = (o.r0 ?? 120) + c.d * u; TR.tf(k, cx + Math.cos(c.a) * rr, cy + Math.sin(c.a) * rr, c.s * (1 - K.seg(t, t0 + vida * .6, t0 + vida)), c.rot * u); }); }; };

  // ── biblioteca de ícones (centrados em 0,0, ~±70 px). Cada um recebe um array de cores. Use como modelo para os seus. ──
  const P = TR.P, blob = TR.blob, poly = TR.poly, star = TR.star, line = TR.line;
  TR.IC = {
    // genéricos
    heart: c => `<path d="M0 46C-30 22-62 4-58-24C-54-50-18-54 0-26C18-54 54-50 58-24C62 4 30 22 0 46Z" fill="${c[0]}"/>` + blob(-28, -24, 9, 11, P.W, { n: 7 }),
    star8: c => star(0, 0, 8, 56, 30, c[0]) + blob(0, 0, 14, 14, c[1] ?? P.W, { n: 8 }),
    aster: c => star(0, 0, 7, 58, 14, c[0], { j: .08 }),
    tri: c => poly([[-40, 30], [44, 22], [0, -46]], c[0], { j: 4 }),
    dots: c => [[-24, -22], [0, -22], [24, -22], [-12, 0], [12, 0], [0, 22]].map(([x, y], i) => blob(x, y, 12, 12, c[i % c.length], { n: 7 })).join(''),
    rosette: c => poly([[-26, 20], [-6, 20], [-14, 78], [-30, 64]], c[2]) + poly([[6, 20], [26, 20], [30, 64], [14, 78]], c[2]) + star(0, 0, 14, 50, 40, c[0], { j: .04 }) + blob(0, 0, 28, 28, c[1], { n: 10 }),
    house: c => poly([[-52, -4], [52, -4], [52, 62], [-52, 62]], c[0]) + poly([[-74, 6], [0, -66], [74, 6]], c[1]) + poly([[-18, 62], [-18, 26], [18, 26], [18, 62]], P.k, { j: 1 }) + blob(0, 26, 18, 18, P.k, { n: 8 }),
    sock: c => poly([[-24, -60], [22, -60], [22, 20], [48, 30], [48, 58], [-10, 58], [-24, 40]], c[0]) + poly([[-24, -48], [22, -48], [22, -34], [-24, -34]], c[1], { j: 1.5 }) + poly([[-24, -24], [22, -24], [22, -10], [-24, -10]], c[1], { j: 1.5 }),
    ball: c => blob(0, 0, 48, 48, c[0], { n: 12, j: .03 }) + line('M-34 -32C-12 -12 -12 14 -34 34', c[1] ?? P.W, 7) + line('M34 -32C12 -12 12 14 34 34', c[1] ?? P.W, 7),
    disc: c => blob(0, 0, 64, 30, c[0], { n: 12, j: .03 }) + blob(0, -2, 40, 17, c[1], { n: 10, j: .04 }),
    // universo cachorro (do exemplo)
    bone: c => poly([[-52, -15], [52, -15], [52, 15], [-52, 15]], c[0], { j: 2 }) + [[-56, -17], [-56, 17], [56, -17], [56, 17]].map(([x, y]) => blob(x, y, 21, 21, c[0], { n: 8 })).join(''),
    paw: c => blob(0, 22, 36, 29, c[0]) + [[-40, -12], [-15, -38], [15, -38], [40, -12]].map(([x, y]) => blob(x, y, 14, 17, c[0], { n: 8 })).join(''),
    bowl: c => blob(0, -6, 50, 24, c[1]) + [[-22, -24], [4, -30], [26, -18]].map(([x, y], i) => blob(x, y, 11, 10, [P.R, P.W, P.V][i], { n: 7 })).join('') + poly([[-64, -4], [64, -4], [48, 46], [-48, 46]], c[0]),
    hydrant: c => blob(0, -36, 32, 26, c[0]) + poly([[-8, -70], [8, -70], [8, -54], [-8, -54]], c[0]) + poly([[-28, -36], [28, -36], [28, 58], [-28, 58]], c[0]) + poly([[-48, -4], [-26, -4], [-26, 18], [-48, 18]], c[1]) + poly([[26, -4], [48, -4], [48, 18], [26, 18]], c[1]) + poly([[-40, 52], [40, 52], [40, 68], [-40, 68]], c[1]) + blob(0, 8, 9, 9, c[1], { n: 7 }),
    collar: c => line('M-30 -40 A50 50 0 1 0 30 -40', c[0], 18) + blob(0, 56, 19, 19, c[1], { n: 9 }) + blob(0, 52, 4, 4, P.k, { n: 6 }),
    mutt: c => blob(-44, -6, 22, 42, c[1], { rot: 20 }) + blob(44, -6, 22, 42, c[1], { rot: -20 }) + blob(0, 0, 46, 42, c[0]) + blob(-15, -8, 6, 6, P.k, { n: 6 }) + blob(15, -8, 6, 6, P.k, { n: 6 }) + blob(0, 14, 11, 8, P.k, { n: 7 }),
    sausage: c => `<g transform="rotate(-20)">${blob(0, 0, 66, 22, c[0], { n: 12, j: .03 })}${blob(-20, -8, 16, 5, P.W, { n: 7 })}</g>`,
    leash: c => line('M-50 50C-20 0 20 40 30-10', c[0], 12) + line('M30-10C20-50 70-60 60-20C55 0 35-2 30-10', c[0], 12) + blob(-50, 50, 12, 12, c[1], { n: 7 }),
  };
})();
