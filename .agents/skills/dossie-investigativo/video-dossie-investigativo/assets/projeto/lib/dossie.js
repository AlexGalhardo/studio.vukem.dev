// dossie.js — estilo "dossiê investigativo" (global DS): papel de xerox, tarjas de censura, foto de ficha,
// impressão digital, ficha datilografada, anotação à mão, carimbo, painel de fios e câmera de mesa.
// Tudo é desenhado por código e é função de t (onTick). Nada de animação CSS, timers ou Math.random (use K.rng).
// MONTE AS PEÇAS DENTRO DE window.SETUP: várias medem texto ou desenham letras em canvas e precisam das fontes carregadas.
(function () {
  const DS = (window.DS = {});
  const W = () => VIDEO.w, H = () => VIDEO.h, TAU = Math.PI * 2;
  const css = document.createElement('style');
  css.textContent = `
:root{--ds-papel:#e4e3df;--ds-tinta:#111111;--ds-cinza:#6e6d68;--ds-acento:#111111;--ds-fio:#2c2c2a;--ds-caneta:#15151a;
  --ds-grot:'Inter Tight',Helvetica,Arial,sans-serif;--ds-mono:'Courier Prime','Courier New',monospace;--ds-serif:'Lora',Georgia,serif}
.ds-mundo{position:absolute;left:0;top:0;transform-origin:0 0;will-change:transform}
.ds-abs,.ds-papel,.ds-tarja,.ds-foto,.ds-foto>*,.ds-dig,.ds-ficha,.ds-cod,.ds-cols,.ds-carimbo,.ds-cartao,.ds-etq,.ds-pino,.ds-tit,.ds-txt,.ds-fita{position:absolute}
.ds-papel canvas,.ds-tarja canvas,.ds-dig canvas,.ds-carimbo canvas{display:block}
.ds-tarja,.ds-carimbo,.ds-dig,.ds-foto{transform-origin:50% 50%}
.ds-foto img{display:block;max-width:none;object-fit:cover}
.ds-ficha,.ds-cols,.ds-med .t,.ds-dig .r{font-family:var(--ds-mono);color:var(--ds-tinta);white-space:pre}
.ds-lin{position:relative}.ds-v.f{font-weight:700}
.ds-cod{font-family:var(--ds-grot);color:var(--ds-tinta);white-space:nowrap;line-height:1}
.ds-cod .r{font-family:var(--ds-mono);font-weight:700;letter-spacing:.2em;margin-bottom:.55em}
.ds-svg{position:absolute;left:0;top:0;overflow:visible;color:var(--ds-tinta)}
.ds-svg text{font:400 11px 'Courier Prime',monospace;fill:currentColor}
.ds-med{color:var(--ds-tinta)}.ds-med path{fill:none;stroke:currentColor;stroke-width:1.6}.ds-med .t{position:absolute;left:0;width:100%;text-align:center}
.ds-cartao{font-family:var(--ds-grot);color:var(--ds-tinta);box-shadow:3px 4px 0 rgba(0,0,0,.2),0 0 0 1px rgba(0,0,0,.14);transform-origin:50% 0}
.ds-c-sub{font-family:var(--ds-mono);font-weight:700;letter-spacing:.1em;color:var(--ds-cinza);margin-bottom:.35em}
.ds-c-tit{font-weight:800;letter-spacing:-.02em;line-height:1.02;margin-bottom:.3em}
.ds-c-txt{font-weight:500;color:var(--ds-texto,#3a3a37)}
.ds-w{display:inline-block}
.ds-tj{position:relative;display:inline-block;color:transparent;white-space:nowrap}
.ds-tj b{position:absolute;left:-.12em;right:-.12em;top:4%;bottom:0;background:var(--ds-tinta);transform-origin:0 50%}
.ds-etq{font-family:var(--ds-grot);color:var(--ds-papel);white-space:nowrap;line-height:1}
.ds-etq .s{font-weight:500;opacity:.86;margin-bottom:.22em}.ds-etq .t{font-weight:800;letter-spacing:-.02em}
.ds-etq .n{position:absolute;top:0;background:#f1f0ec;color:#111;font-weight:800;display:grid;place-items:center;box-shadow:0 0 0 1px rgba(0,0,0,.2)}
.ds-pino{border-radius:50%;background:radial-gradient(circle at 34% 30%,#fff 0 13%,#6a6a6a 16% 28%,#0c0c0c 56%);box-shadow:2px 3px 0 rgba(0,0,0,.3)}
.ds-tit{font-family:var(--ds-grot);color:var(--ds-tinta);white-space:nowrap}
.ds-txt{color:var(--ds-tinta)}
.ds-fita{background:rgba(246,245,238,.62);box-shadow:inset 0 0 0 1px rgba(0,0,0,.1),1px 2px 0 rgba(0,0,0,.08)}
.ds-rodape{position:absolute;left:0;right:0;bottom:26px;text-align:center;font:700 17px 'Courier Prime',monospace;letter-spacing:.14em;color:rgba(20,20,20,.62);z-index:60}`;
  document.head.appendChild(css);

  // ───────── utilitários ─────────
  const el = (tag, cls, pai, style = '') => { const e = document.createElement(tag); if (cls) e.className = cls; if (style) e.style.cssText = style; if (pai) pai.appendChild(e); return e; };
  const cv = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };
  const fb = (x, y) => K.noise(x, y) + .5 * K.noise(x * 2.03 + 17.1, y * 2.03 + 9.7) + .25 * K.noise(x * 4.1 + 3.3, y * 4.1 + 41.2);
  const vis = (e, on) => { e.style.visibility = on ? 'visible' : 'hidden'; };
  const f1 = v => (+v).toFixed(1);
  const tinta = pai => (pai && getComputedStyle(pai).getPropertyValue('--ds-tinta').trim()) || '#111111';
  const tinge = (c, cor) => { const g = c.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-in'; g.fillStyle = cor; g.fillRect(0, 0, c.width, c.height); g.globalCompositeOperation = 'source-over'; };
  DS.qps = 12;                                   // passo do "stop-motion" (tremor de registro, grão)
  DS.q = (t, q = DS.qps) => (q ? Math.floor(t * q + 1e-6) / q : t);
  DS.baques = [];                                // [t, força]: batidas (carimbo, fita, digital) que sacodem a câmera
  // som sem "flam": dois efeitos IGUAIS a menos de 55 ms viram um estalo só → empurra o segundo
  const usados = {};
  DS.som = (tipo, t, o = {}) => { const u = (usados[tipo] = usados[tipo] || []); let tt = Math.max(0, t); while (u.some(x => Math.abs(x - tt) < .055)) tt += .034; u.push(tt); return cue(tipo, tt, o); };

  // ───────── mundo, câmera de mesa, troca de página ─────────
  DS.mundo = (stage, { w = W(), h = H(), id } = {}) => { const m = el('div', 'ds-mundo', stage, `width:${w}px;height:${h}px`); if (id) m.id = id; return m; };
  // keys: [{t, x, y, z, r, ease, corte}] — (x, y) = ponto do mundo no centro da tela. `corte:true` = pula seco para esta chave.
  DS.camera = (mundo, keys, { tremor = 1.1, giro = .05, qps = DS.qps, seed = 1 } = {}) => {
    keys = keys.slice().sort((a, b) => a.t - b.t).map(k => Object.assign({ z: 1, r: 0 }, k));
    const em = t => {
      for (let i = keys.length - 1; i >= 0; i--) if (t >= keys[i].t) {
        const a = keys[i], b = keys[i + 1]; if (!b || b.corte) return a;
        const k = gsap.parseEase(b.ease || 'sine.inOut')(K.seg(t, a.t, b.t));
        return { x: K.lerp(a.x, b.x, k), y: K.lerp(a.y, b.y, k), z: a.z * Math.pow(b.z / a.z, k), r: K.lerp(a.r, b.r, k) };
      }
      return keys[0];
    };
    onTick(t => {
      const c = em(t), r = K.rng(Math.floor(t * qps + 1e-6) * 7919 + seed * 131);
      let dx = (r() - .5) * 2 * tremor, dy = (r() - .5) * 2 * tremor; const dr = (r() - .5) * 2 * giro;
      for (const [tb, f] of DS.baques) if (t >= tb && t < tb + .3) { const u = t - tb; dy += f * Math.exp(-u / .05) * Math.cos(u * 60); }
      mundo.style.transform = `translate(${(W() / 2 + dx).toFixed(2)}px,${(H() / 2 + dy).toFixed(2)}px) rotate(${(c.r + dr).toFixed(3)}deg) scale(${c.z.toFixed(5)}) translate(${(-c.x).toFixed(2)}px,${(-c.y).toFixed(2)}px)`;
    });
    return em;
  };
  // páginas: [[t0, mundo], [t1, mundo2], …] — cada uma fica visível até a próxima; a troca é um corte seco com 2 quadros em negativo
  DS.paginas = (lista, { flash = 'neg', quadros = 2, som = true } = {}) => {
    const dt = quadros / VIDEO.fps;
    if (som) lista.slice(1).forEach(([t]) => { DS.som('paper', t - .04, { gain: 3 }); DS.som('shutter', t, { gain: -3 }); });
    onTick(t => lista.forEach(([t0, m], i) => { const t1 = lista[i + 1] ? lista[i + 1][0] : 1e9, on = t >= t0 && t < t1; m.style.display = on ? '' : 'none'; m.style.filter = on && i && flash === 'neg' && t < t0 + dt ? 'invert(1)' : ''; }));
  };
  // passada de luz de scanner (faixa branca que atravessa a tela, com duas linhas finas de sombra)
  DS.scanner = (stage, { t0 = 0, d = .8, larg = 280, forca = .8, dir = 1, som = true, ease = 'sine.inOut', gain = -3 } = {}) => {
    const a = forca, b = el('div', 'ds-scan', stage, `position:absolute;left:0;top:0;width:100%;height:${larg}px;z-index:40;visibility:hidden;` +
      `background:linear-gradient(180deg,rgba(255,255,255,0) 0%,rgba(255,255,255,${a * .25}) 30%,rgba(0,0,0,.3) 37%,rgba(255,255,255,${a * .7}) 39%,#fff 50%,rgba(255,255,255,${a * .7}) 61%,rgba(0,0,0,.3) 63%,rgba(255,255,255,${a * .25}) 70%,rgba(255,255,255,0) 100%)`);
    const ez = gsap.parseEase(ease); if (som) DS.som('scanner', t0, { d, gain });
    onTick(t => { const on = t >= t0 && t <= t0 + d; vis(b, on); if (!on) return; const k = ez(K.seg(t, t0, t0 + d)); b.style.transform = `translateY(${(dir > 0 ? K.lerp(-larg, H(), k) : K.lerp(H(), -larg, k)).toFixed(1)}px)`; });
    return t0 + d;
  };
  // grão de xerox animado em degraus (12 qps) por cima de tudo
  DS.grao = (stage, { opacity = .2, qps = DS.qps, w = 720, blend = 'overlay' } = {}) => {
    const h = Math.round(w * H() / W()), c = cv(w, h); c.style.cssText = `position:absolute;inset:0;width:100%;height:100%;pointer-events:none;mix-blend-mode:${blend};opacity:${opacity};z-index:50`;
    stage.appendChild(c); const g = c.getContext('2d'), img = g.createImageData(w, h); let ult = -1;
    onTick(t => { const s = Math.floor(t * qps + 1e-6); if (s === ult) return; ult = s; const r = K.rng(s * 7919 + 1), d = img.data;
      for (let i = 0; i < d.length; i += 4) { d[i] = d[i + 1] = d[i + 2] = 128 + (r() + r() - 1) * 150; d[i + 3] = 255; } g.putImageData(img, 0, 0); });
    return c;
  };
  DS.vinheta = (stage, forca = .3) => el('div', '', stage, `position:absolute;inset:0;pointer-events:none;z-index:45;background:radial-gradient(ellipse 82% 78% at 50% 48%,rgba(0,0,0,0) 55%,rgba(0,0,0,${forca}) 100%)`);
  // linha fixa no rodapé da TELA (fonte dos dados, crédito da foto, aviso de ficção)
  DS.rodape = (stage, texto, { t0 = 0, cor } = {}) => { const e = el('div', 'ds-rodape', stage, cor ? `color:${cor}` : ''); e.textContent = texto; onTick(t => vis(e, t >= t0)); return e; };

  // ───────── 1. papel de xerox / arquivo ─────────
  DS.papel = (pai, o = {}) => {
    const { x = 0, y = 0, w = W(), h = H(), tom = 'claro', seed = 1, bandas = 1, manchas = 1, borda = 1, riscos = 1, grao = 1, furos = false, z = 0 } = o;
    const esc = tom === 'escuro', base = o.base ?? (esc ? 26 : 224), c = cv(w, h), g = c.getContext('2d'), r = K.rng(seed * 131 + 7);
    const tin = esc ? '255,255,255' : '0,0,0', luz = esc ? '0,0,0' : '255,255,255';
    g.fillStyle = `rgb(${base},${base},${base})`; g.fillRect(0, 0, w, h);
    // nuvens de toner (baixa resolução, ampliadas)
    const q = 8, lw = Math.ceil(w / q), lh = Math.ceil(h / q), lc = cv(lw, lh), lg = lc.getContext('2d'), li = lg.createImageData(lw, lh);
    for (let j = 0, p = 0; j < lh; j++) for (let i = 0; i < lw; i++, p += 4) {
      const n = fb(i * .011 + seed * 3.1, j * .05 - seed * 1.7) + .45 * K.noise(i * .19 + 40, j * .19 + seed);
      li.data[p] = li.data[p + 1] = li.data[p + 2] = n > 0 ? 255 : 0; li.data[p + 3] = Math.min(255, Math.abs(n) * 24 * manchas);
    }
    lg.putImageData(li, 0, 0); g.drawImage(lc, 0, 0, w, h);
    // bandas horizontais de scanner + linhas finas
    for (let yy = -40; yy < h;) { const bh = 30 + r() * r() * 460, a = (.015 + r() * .05) * bandas; g.fillStyle = r() < .55 ? `rgba(${tin},${a})` : `rgba(${luz},${a * 2.2})`; g.fillRect(0, yy, w, bh); yy += bh * (.5 + r()); }
    for (let i = 0; i < 6 * bandas; i++) { g.fillStyle = `rgba(${tin},${.03 + r() * .06})`; g.fillRect(0, r() * h, w, 1 + r() * 2.5); }
    if (bandas) { const y0 = h * (.15 + r() * .6), bh = h * (.08 + r() * .1), gr = g.createLinearGradient(0, y0, 0, y0 + bh); gr.addColorStop(0, `rgba(${tin},0)`); gr.addColorStop(.5, `rgba(${tin},${.07 * bandas})`); gr.addColorStop(1, `rgba(${tin},0)`); g.fillStyle = gr; g.fillRect(0, y0, w, bh); }
    // arrastos de toner (cilindro sujo) e um canto mais escuro
    for (let i = 0; i < 9 * manchas; i++) { g.fillStyle = `rgba(${tin},${.05 + r() * .09})`; g.fillRect(r() * w, r() * h, 80 + r() * 460, 1 + r() * 2.4); }
    if (manchas) { const kx = r() < .5 ? 0 : w, ky = r() < .5 ? 0 : h, gr = g.createRadialGradient(kx, ky, 0, kx, ky, Math.min(w, h) * .55); gr.addColorStop(0, `rgba(${tin},${.13 * manchas})`); gr.addColorStop(1, `rgba(${tin},0)`); g.fillStyle = gr; g.fillRect(0, 0, w, h); }
    // texto do verso vazando (linhas fantasma, como folha fina na fotocópia)
    if (o.verso) for (let yy = h * .06; yy < h * .96; yy += 34 + r() * 8) { if (r() < .18) { yy += 60; continue; } for (let xx = w * .1; xx < w * (.55 + r() * .35);) { const L = 18 + r() * 90; g.fillStyle = `rgba(${tin},${.022 + r() * .03})`; g.fillRect(xx, yy, L, 7 + r() * 3); xx += L + 10 + r() * 8; } }
    // riscos verticais de toner
    for (let i = 0; i < 6 * riscos; i++) { g.fillStyle = `rgba(${tin},${.025 + r() * .06})`; g.fillRect(r() * w, 0, .8 + r() * 1.6, h); }
    // vincos (frações da altura)
    [].concat(o.vinco === undefined ? [.5] : o.vinco || []).forEach(fv => { const vy = h * fv, gr = g.createLinearGradient(0, vy - 26, 0, vy + 26); gr.addColorStop(0, `rgba(${tin},0)`); gr.addColorStop(.47, `rgba(${tin},.08)`); gr.addColorStop(.5, `rgba(${luz},.34)`); gr.addColorStop(.55, `rgba(${tin},.11)`); gr.addColorStop(1, `rgba(${tin},0)`); g.fillStyle = gr; g.fillRect(0, vy - 26, w, 52); });
    // grão, pontinhos e borda de fotocópia (sombra irregular do vidro)
    const img = g.getImageData(0, 0, w, h), d = img.data, sg = esc ? 1 : -1, E = 70;
    const eL = new Float32Array(h), eR = new Float32Array(h), eT = new Float32Array(w), eB = new Float32Array(w);
    for (let j = 0; j < h; j++) { eL[j] = (K.noise(j * .006 + seed, 3.3) * 16 + K.noise(j * .07, seed + 9.1) * 3 + 2) * borda; eR[j] = (K.noise(j * .006 + seed * 2, 13.3) * 16 + K.noise(j * .07, seed + 29.1) * 3 + 1) * borda; }
    for (let i = 0; i < w; i++) { eT[i] = (K.noise(i * .006 + seed * 3, 23.3) * 14 + K.noise(i * .07, seed + 49.1) * 3 + 1) * borda; eB[i] = (K.noise(i * .006 + seed * 4, 33.3) * 18 + K.noise(i * .07, seed + 69.1) * 3 + 3) * borda; }
    for (let j = 0, p = 0; j < h; j++) for (let i = 0; i < w; i++, p += 4) {
      let v = d[p] + (r() + r() - 1) * 16 * grao;
      if (r() < .0028 * grao) v += sg * (40 + r() * 150);
      if (borda && (i < E || j < E || i > w - E || j > h - E)) {
        const m = Math.min(i - eL[j], w - 1 - i - eR[j], j - eT[i], h - 1 - j - eB[i]);
        v = m < 0 ? (esc ? 232 : 14) + r() * 16 : v + sg * 30 * Math.exp(-m / 16) * (.6 + r() * .8);
      }
      d[p] = v + (esc ? 0 : 1); d[p + 1] = v; d[p + 2] = v - (esc ? 0 : 2.5);
    }
    g.putImageData(img, 0, 0);
    // fiapos e poeira do vidro; furos de arquivo
    g.strokeStyle = `rgba(${tin},.42)`; g.lineWidth = .9;
    for (let i = 0; i < 5 * manchas; i++) { const hx = r() * w, hy = r() * h, a = r() * TAU, L = 14 + r() * 40; g.beginPath(); g.moveTo(hx, hy); g.quadraticCurveTo(hx + Math.cos(a) * L * .5 + (r() - .5) * 20, hy + Math.sin(a) * L * .5 + (r() - .5) * 20, hx + Math.cos(a) * L, hy + Math.sin(a) * L); g.stroke(); }
    for (let i = 0; i < 26 * manchas; i++) { g.fillStyle = `rgba(${tin},${.3 + r() * .5})`; g.beginPath(); g.arc(r() * w, r() * h, .6 + r() * r() * 3, 0, TAU); g.fill(); }
    if (furos) [.16, .5, .84].forEach(fv => { g.fillStyle = `rgba(${tin},.82)`; g.beginPath(); g.arc(36, h * fv, 13, 0, TAU); g.fill(); });
    const box = el('div', 'ds-papel', pai, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;z-index:${z}`); box.appendChild(c);
    if (esc) ['--ds-tinta:#eceae5', '--ds-papel:#151515', '--ds-fio:#c9c8c3', '--ds-caneta:#f1f0ea', '--ds-cinza:#a3a29c'].forEach(s => box.style.setProperty(...s.split(':')));
    return box;
  };

  // ───────── 2. tarja de censura ─────────
  // tipo 'marcador': risca da esquerda p/ a direita · tipo 'fita': bate de uma vez (olhos de foto)
  DS.tarja = (pai, o = {}) => {
    const { x, y, w, h = 44, t0 = 0, tipo = 'marcador', seed = 1, rot = 0, som = true, z = 3 } = o;
    const p = Math.ceil(h * .4), c = cv(w + 2 * p, h + 2 * p), g = c.getContext('2d'), r = K.rng(seed * 733 + 11);
    g.fillStyle = '#000';
    const forma = (y0, y1, amp, pontas) => {
      const n = Math.max(6, Math.round(w / 16)), top = [], bot = [];
      for (let i = 0; i <= n; i++) { const u = i / n, X = p + u * w + (i === 0 ? -r() * pontas : i === n ? r() * pontas : 0);
        top.push([X, y0 + (r() - .5) * amp + K.noise(u * 4 + seed, 1.7) * amp * 1.4]); bot.push([X + (r() - .5) * pontas * .6, y1 + (r() - .5) * amp + K.noise(u * 4 + seed, 9.2) * amp * 1.4]); }
      g.beginPath(); top.forEach((q, i) => (i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]))); bot.reverse().forEach(q => g.lineTo(q[0], q[1])); g.closePath(); g.fill();
    };
    if (tipo === 'fita') forma(p, p + h, 2.2, h * .1);
    else {
      const np = h > 34 ? 3 : 2;
      for (let k = 0; k < np; k++) { const hh = h * (.6 + r() * .16), yk = p + (h - hh) * (k / (np - 1)) + (r() - .5) * h * .1; forma(yk, yk + hh, h * .1, h * .28); }
      forma(p + h * .14, p + h * .86, h * .05, h * .08);
      g.globalCompositeOperation = 'destination-out';           // tinta seca nas pontas
      for (let i = 0; i < 12; i++) { const ini = r() < .4, L = 6 + r() * w * .16; g.fillStyle = `rgba(0,0,0,${.25 + r() * .5})`; g.fillRect(ini ? p - 8 : p + w - L + 8, p + r() * h, L, 1 + r() * 2.2); }
    }
    g.globalCompositeOperation = 'destination-out';             // erosão de fotocópia nas bordas
    for (let i = 0, n = w * h / 240; i < n; i++) { const k = r() * r() * h * .28; g.fillStyle = `rgba(0,0,0,${.4 + r() * .6})`; g.fillRect(p + r() * w, r() < .5 ? p + k : p + h - k, 1 + r() * 2.2, 1 + r() * 1.6); }
    tinge(c, o.cor || tinta(pai));
    const box = el('div', 'ds-tarja', pai, `left:${x - p}px;top:${y - p}px;width:${c.width}px;height:${c.height}px;z-index:${z}`); box.appendChild(c);
    const fita = tipo === 'fita', d = o.d ?? (fita ? .1 : Math.min(.5, .12 + w * .00045)), ez = gsap.parseEase(fita ? 'power3.in' : 'power1.inOut');
    if (som) DS.som(fita ? 'tape' : 'marker', t0, { gain: o.gain ?? (fita ? 0 : -6) });
    if (fita) DS.baques.push([t0 + d, 3]);
    onTick(t => {
      if (t < t0) return vis(box, false); vis(box, true); const k = ez(K.seg(t, t0, t0 + d));
      if (fita) box.style.transform = `rotate(${(rot + (1 - k) * 2.5).toFixed(2)}deg) scale(${(1 + (1 - k) * .16).toFixed(4)})`;
      else { box.style.transform = `rotate(${rot}deg)`; box.style.clipPath = `inset(0 ${((1 - k) * 100).toFixed(2)}% 0 0)`; }
    });
    return { el: box, fim: t0 + d };
  };

  // ───────── 3. foto de ficha ─────────
  // tratamento de xerox num canvas (o mesmo espírito do tools/dossie.py, para o retrato procedural)
  DS.xerox = (c, { contraste = 1.7, grao = .26, brilho = .02, riscos = 3, seed = 1, reticula = 0, limiar = 0 } = {}) => {
    const g = c.getContext('2d'), w = c.width, h = c.height, img = g.getImageData(0, 0, w, h), d = img.data, r = K.rng(seed * 269 + 3);
    const rx = Array.from({ length: riscos }, () => [Math.floor(r() * w), 1 + Math.floor(r() * 2), .1 + r() * .2]);
    for (let j = 0, p = 0; j < h; j++) { const bd = 1 + K.noise(j * .013 + seed, 7.7) * .1;
      for (let i = 0; i < w; i++, p += 4) {
        let v = ((d[p] * .3 + d[p + 1] * .59 + d[p + 2] * .11) / 255 - .5) * contraste + .5 + brilho; v *= bd;
        if (reticula) { const s = Math.PI / reticula, a = (i + j) * s * .7071, b = (i - j) * s * .7071; v = v + (Math.cos(a) * Math.cos(b)) * .32 > .5 ? .93 : .07; }
        if (limiar) v = K.lerp(v, v > .5 + (r() - .5) * .3 ? .96 : .04, limiar);
        v += (r() + r() - 1) * grao;
        for (const [x0, lw, a] of rx) if (i >= x0 && i < x0 + lw) v += a;
        d[p] = d[p + 1] = d[p + 2] = 14 + K.clamp(v) * 222;
      } }
    g.putImageData(img, 0, 0); return c;
  };
  // retrato procedural (ninguém de verdade): manchas borradas de cabeça, cabelo em tufos, pescoço e ombros, passadas no xerox.
  // cabelo: 'curto' | 'franja' | 'longo' | 'calvo' · roupa: 'terno' | 'camiseta' | 'camisa' · seed muda proporções e tons
  DS.retrato = (o = {}) => {
    const { w = 520, h = 660, seed = 1 } = o, r = K.rng(seed * 419 + 5), c = cv(w, h), g = c.getContext('2d'), G = (v, a = 1) => `rgba(${v | 0},${v | 0},${v | 0},${a})`;
    const cab = o.cabelo || ['curto', 'franja', 'longo', 'calvo'][Math.floor(r() * 4)], rou = o.roupa || ['terno', 'camiseta', 'camisa'][Math.floor(r() * 3)];
    const cx = w * (.5 + (r() - .5) * .03), hy = h * .4, rx = w * (.185 + r() * .02), ry = h * (.2 + r() * .015), pele = 164 + r() * 26, bg = o.fundo ?? 132 + r() * 40, pelo = G(10 + r() * 24), lado = r() < .5 ? -1 : 1;
    const elip = (x, y, a, b, cor) => { g.fillStyle = cor; g.beginPath(); g.ellipse(x, y, Math.abs(a), Math.abs(b), 0, 0, TAU); g.fill(); };
    const B = k => { g.filter = `blur(${(w * k).toFixed(1)}px)`; };
    let gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, G(bg + 18)); gr.addColorStop(1, G(bg - 30)); g.fillStyle = gr; g.fillRect(0, 0, w, h);
    B(.07); elip(cx, hy, w * .42, h * .4, G(bg + 46, .55));                                   // luz atrás da cabeça
    B(.012); if (cab === 'longo') elip(cx, hy + ry * .5, rx * 1.42, ry * 1.85, pelo);
    // ombros (um mais alto que o outro), pescoço, roupa
    const oy = h * (.715 + (r() - .5) * .02), dz = lado * h * .012;
    g.fillStyle = G(rou === 'camisa' ? 188 : rou === 'camiseta' ? 46 + r() * 30 : 26);
    g.beginPath(); g.moveTo(cx - w * .54, h); g.bezierCurveTo(cx - w * .52, h * .8 + dz, cx - w * .24, oy + h * .04 + dz, cx - w * .09, oy); g.lineTo(cx + w * .09, oy); g.bezierCurveTo(cx + w * .24, oy + h * .04 - dz, cx + w * .52, h * .8 - dz, cx + w * .54, h); g.closePath(); g.fill();
    g.fillStyle = G(pele - 38); g.beginPath(); g.moveTo(cx - rx * .56, hy + ry * .5); g.lineTo(cx - rx * .64, oy + h * .02); g.quadraticCurveTo(cx, oy + h * .085, cx + rx * .64, oy + h * .02); g.lineTo(cx + rx * .56, hy + ry * .5); g.closePath(); g.fill();
    if (rou === 'terno') {
      g.fillStyle = G(222); g.beginPath(); g.moveTo(cx - w * .085, oy + h * .01); g.quadraticCurveTo(cx, oy + h * .05, cx + w * .085, oy + h * .01); g.lineTo(cx + w * .03, h); g.lineTo(cx - w * .03, h); g.closePath(); g.fill();
      g.fillStyle = G(14); g.beginPath(); g.moveTo(cx - w * .02, oy + h * .065); g.lineTo(cx + w * .02, oy + h * .065); g.lineTo(cx + w * .036, h); g.lineTo(cx - w * .036, h); g.closePath(); g.fill();
      g.strokeStyle = G(6); g.lineWidth = w * .014; g.beginPath(); g.moveTo(cx - w * .095, oy + h * .005); g.lineTo(cx - w * .036, h); g.moveTo(cx + w * .095, oy + h * .005); g.lineTo(cx + w * .036, h); g.stroke();
    } else if (rou === 'camisa') { g.strokeStyle = G(96); g.lineWidth = w * .01; g.beginPath(); g.moveTo(cx - w * .11, oy); g.lineTo(cx, oy + h * .09); g.lineTo(cx + w * .11, oy); g.moveTo(cx, oy + h * .09); g.lineTo(cx, h); g.stroke(); }
    else elip(cx, oy + h * .028, rx * .74, h * .03, G(pele - 40));
    B(.022); elip(cx, hy + ry * 1.04, rx * .66, ry * .17, G(0, .62));                        // sombra do queixo
    // orelhas + cabeça (oval mais estreito no queixo)
    B(.006); elip(cx - rx * 1.0, hy + ry * .06, rx * .12, ry * .19, G(pele - 26)); elip(cx + rx * 1.0, hy + ry * .06, rx * .12, ry * .19, G(pele - 44));
    const cabeca = () => { g.beginPath(); g.moveTo(cx, hy - ry); g.bezierCurveTo(cx + rx * 1.14, hy - ry, cx + rx * 1.08, hy + ry * .36, cx + rx * .6, hy + ry * .8); g.quadraticCurveTo(cx, hy + ry * 1.2, cx - rx * .6, hy + ry * .8); g.bezierCurveTo(cx - rx * 1.08, hy + ry * .36, cx - rx * 1.14, hy - ry, cx, hy - ry); g.closePath(); };
    cabeca(); g.fillStyle = G(pele); g.fill();
    g.save(); cabeca(); g.clip();                                                                 // luz de um lado, sombra do outro
    B(.035); gr = g.createLinearGradient(cx - lado * rx, 0, cx + lado * rx * 1.1, 0); gr.addColorStop(.3, G(0, 0)); gr.addColorStop(1, G(0, .46)); g.fillStyle = gr; g.fillRect(cx - rx * 1.3, hy - ry * 1.3, rx * 2.6, ry * 2.8);
    B(.03); elip(cx - lado * rx * .25, hy - ry * .5, rx * .5, ry * .24, G(255, .4)); elip(cx - lado * rx * .5, hy + ry * .28, rx * .24, ry * .2, G(255, .26)); elip(cx - lado * rx * .06, hy + ry * .12, rx * .07, ry * .24, G(255, .3));
    B(.016);
    for (const sd of [-1, 1]) { elip(cx + sd * rx * .42, hy - ry * .05, rx * .27, ry * .09, G(0, .64)); elip(cx + sd * rx * .43, hy - ry * .21, rx * .31, ry * .036, G(0, .6)); }
    elip(cx + lado * rx * .12, hy + ry * .2, rx * .09, ry * .22, G(0, .36)); elip(cx, hy + ry * .41, rx * .2, ry * .036, G(0, .55));
    elip(cx, hy + ry * .63, rx * .34, ry * .028, G(0, .68)); elip(cx, hy + ry * .77, rx * .24, ry * .045, G(0, .26)); elip(cx, hy + ry * 1.05, rx * .7, ry * .13, G(0, .3));
    g.restore();
    // cabelo: tufos borrados ao longo do crânio (contorno irregular, sem "capacete")
    B(.009);
    const tufo = (ang, rad, sz) => elip(cx + Math.cos(ang) * rx * rad, hy + Math.sin(ang) * ry * rad, rx * sz, ry * sz * .82, pelo);
    if (cab === 'calvo') { for (const sd of [0, 1]) for (let i = 0; i < 5; i++) tufo(Math.PI * (sd ? 1.97 - i * .03 : 1.03 + i * .03), .97 + r() * .03, .07 + r() * .035); B(.03); elip(cx - lado * rx * .15, hy - ry * .78, rx * .4, ry * .14, G(255, .35)); }
    else {
      const a0 = cab === 'longo' ? 1.0 : 1.07, n = 26, risca = .35 + r() * .3;
      for (let i = 0; i <= n; i++) tufo(Math.PI * (a0 + (2 - 2 * (a0 - 1) - 1) * i / n), .9 + r() * .1, .2 + r() * .08);
      elip(cx, hy - ry * .97, rx * .8, ry * .24, pelo);
      for (let i = 0; i <= 10; i++) { const u = i / 10, alto = cab === 'franja' ? .42 + r() * .1 : .66 + Math.abs(u - risca) * .28 + r() * .06; elip(cx - rx * .8 + u * rx * 1.6, hy - ry * alto - ry * .1, rx * .18, ry * .13, pelo); }
      if (cab === 'longo') for (const sd of [-1, 1]) { elip(cx + sd * rx * 1.08, hy + ry * .45, rx * .28, ry * 1.15, pelo); elip(cx + sd * rx * 1.0, hy + ry * 1.3, rx * .34, ry * .5, pelo); }
    }
    // borrão geral (funde as formas) e xerox
    g.filter = 'none'; const tmp = cv(w, h); tmp.getContext('2d').drawImage(c, 0, 0); B(.005); g.drawImage(tmp, -8, -8, w + 16, h + 16); g.filter = 'none';
    return DS.xerox(c, Object.assign({ seed, contraste: 1.8, grao: .3, limiar: .24 }, o.xerox || {}));
  };
  // fita adesiva translúcida
  DS.fita = (pai, { x, y, w = 110, h = 36, rot = 0, t0 = 0, z = 5 } = {}) => { const e = el('div', 'ds-fita', pai, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;transform:rotate(${rot}deg);z-index:${z};clip-path:polygon(0 0,3% 22%,0 40%,4% 62%,0 82%,2% 100%,98% 100%,100% 78%,96% 58%,100% 36%,97% 18%,100% 0)`); onTick(t => vis(e, t >= t0)); return e; };
  // foto: src (foto do usuário tratada pelo tools/dossie.py) OU retrato procedural (seed/retrato:{cabelo,roupa}).
  // copias: [{dx, dy, op}] — xerox desbotado ao lado. Devolve {el, x, y, w, h, pino, olhos(), medida()}
  DS.foto = (pai, o = {}) => {
    const { x, y, w = 520, t0 = 0, rot = 0, seed = 1, copias = [], cruzes = true, fita = false, moldura = 0, som = true, z = 2 } = o, h = o.h ?? Math.round(w * 1.27);
    const src = o.src || DS.retrato(Object.assign({ w, h, seed }, o.retrato || {})).toDataURL('image/jpeg', .9);
    const box = el('div', 'ds-foto', pai, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;z-index:${z}`);
    const cs = copias.map((cp, i) => { const e = el('img', '', box, `left:${cp.dx ?? 0}px;top:${cp.dy ?? 0}px;width:${w}px;height:${h}px;opacity:${cp.op ?? .5};filter:contrast(${cp.contraste ?? .45}) brightness(${cp.brilho ?? 1.45}) blur(${cp.blur ?? .7}px)`); e.src = src; return [e, t0 + (cp.t ?? .12 * (i + 1))]; });
    const im = el('img', '', box, `left:0;top:0;width:${w}px;height:${h}px;box-shadow:0 0 0 ${moldura}px #f0efeb,0 0 0 ${moldura + 1}px rgba(0,0,0,.25)`); im.src = src;
    const xs = [];
    if (fita) xs.push(DS.fita(box, { x: w * .5 - 62, y: -20, w: 124, h: 38, rot: -2 + (seed % 5), t0 }));
    if (cruzes) [[-30, -30], [w + 30, -30], [-30, h + 30], [w + 30, h + 30]].forEach(([a, b], i) => DS.cruz(box, { x: a, y: b, s: 20, t0: t0 + .22 + i * .05 }));
    if (som) DS.som('paper', t0, { gain: 1 }); DS.baques.push([t0 + .12, 2]);
    onTick(t => { vis(box, t >= t0); if (t < t0) return; const k = K.seg(t, t0, t0 + .12); box.style.transform = `rotate(${(rot + (1 - k) * 3).toFixed(2)}deg) scale(${(1 + (1 - k) * .07).toFixed(4)})`; cs.forEach(([e, tc]) => vis(e, t >= tc)); });
    const F = { el: box, x, y, w, h, pino: [x + w / 2, y + 16], fim: t0 + .12 };
    F.olhos = (q = {}) => DS.tarja(box, Object.assign({ x: w * .15, y: h * .335, w: w * .7, h: h * .1, tipo: 'fita', t0: t0 + .6, seed: seed + 3, cor: '#0b0b0b', z: 4 }, q));
    F.medida = (texto, q = {}) => DS.medida(box, Object.assign({ x0: 0, y0: -58, x1: w, y1: -58, texto, t0: t0 + .35 }, q));
    return F;
  };

  // ───────── 4. impressão digital ─────────
  DS.digital = (pai, o = {}) => {
    const { x, y, w = 260, t0 = 0, seed = 1, rot = 0, rotulo, caixa = false, som = true, z = 2, cristas = 25 } = o, h = o.h ?? Math.round(w * 1.3);
    const c = cv(w, h), g = c.getContext('2d'), img = g.createImageData(w, h), d = img.data, r = K.rng(seed * 577 + 3), tp = o.tipo || ['laco', 'espiral', 'arco'][seed % 3];
    const cx = w * (.5 + (r() - .5) * .1), cy = h * (.45 + (r() - .5) * .06), per = w / cristas, inc = (r() - .5) * .5, F = .011 * 260 / w;
    for (let j = 0, p = 0; j < h; j++) for (let i = 0; i < w; i++, p += 4) {
      const ex = (i - w / 2) / (w * .46), ey = (j - h / 2) / (h * .48), bd = 1 - (ex * ex + ey * ey) + K.noise(i * F * 2.6 + seed, j * F * 2.6) * .24;
      if (bd <= 0) continue;
      let u = i - cx + fb(i * F + seed * 5.3, j * F + 1.1) * per * 2.8, v = j - cy + fb(i * F + 40.7, j * F + seed * 2.9) * per * 2.8; u += v * inc * .35;
      let ph;
      if (tp === 'espiral') ph = (Math.hypot(u, v * 1.14) + Math.atan2(v, u) / TAU * per) / per;
      else if (tp === 'arco') ph = (v + per * 7 * Math.exp(-(u * u) / (w * w * .05)) * K.clamp(1.2 - v / (h * .35))) / per;
      else ph = Math.hypot(v > 0 ? u * Math.exp(-v / (h * .17)) : u, v) / per;
      const tin = fb(i * F * 1.5 + seed * 9.1, j * F * 1.5 - seed * 4.3);         // carga de tinta: falha ↔ empasta
      let a = .5 + .5 * Math.cos(ph * TAU) > .5 - tin * .6 ? 1 : 0;
      if (tin < -.36 || (bd < .14 && r() > bd / .14) || r() < .1) a = 0;
      if (a) { d[p + 3] = 255 * (.72 + r() * .28); }
    }
    g.putImageData(img, 0, 0); tinge(c, o.cor || tinta(pai));
    const box = el('div', 'ds-dig', pai, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;z-index:${z}`); box.appendChild(c);
    let fr, lb;
    if (caixa) fr = el('div', 'ds-abs', pai, `left:${x - 18}px;top:${y - 16}px;width:${w + 36}px;height:${h + 32 + (rotulo ? 34 : 0)}px;border:1.5px solid var(--ds-tinta);opacity:.7;z-index:${z}`);
    if (rotulo) { lb = el('div', 'ds-ficha', pai, `left:${x - 18}px;width:${w + 36}px;top:${y + h + 12}px;text-align:center;font-size:${Math.max(14, w * .068)}px;letter-spacing:.12em;z-index:${z}`); lb.textContent = rotulo; }
    if (som) DS.som('ink', t0 + .07, { gain: 0 }); DS.baques.push([t0 + .1, 2.5]);
    onTick(t => { [fr, lb].forEach(e => e && vis(e, t >= (o.tCaixa ?? t0 - .25))); if (t < t0) return vis(box, false); vis(box, true); const k = K.seg(t, t0, t0 + .1);
      box.style.transform = `rotate(${rot}deg) scale(${(1 + (1 - k * k) * .22).toFixed(4)})`; box.style.opacity = (.5 + .5 * K.seg(t, t0 + .04, t0 + .14)).toFixed(3); });
    return { el: box, x, y, w, h, fim: t0 + .14 };
  };

  // ───────── 6. ficha datilografada ─────────
  // campos: [{r:'NOME', v:'…', tarja:true|'depois'|nCaracteres, forte:true}] — tarja:true = o valor nasce tarjado (nunca aparece)
  DS.ficha = (pai, o = {}) => {
    const { x, y, campos, fs = 36, t0 = 0, cps = 36, pausa = .1, som = true, seed = 1, z = 3 } = o, lh = o.lh ?? Math.round(fs * 1.75);
    const box = el('div', 'ds-ficha', pai, `left:${x}px;top:${y}px;font-size:${fs}px;line-height:${lh}px;z-index:${z}` + (o.cor ? `;color:${o.cor}` : '') + (o.peso ? `;font-weight:${o.peso}` : ''));
    let t = t0, ks = 0; const L = [];
    campos.forEach((c, i) => {
      const ln = el('div', 'ds-lin', box, `height:${lh}px`), a = el('span', 'ds-r', ln), b = el('span', 'ds-v' + (c.forte ? ' f' : ''), ln), rot = c.r ? c.r + ': ' : '';
      a.textContent = rot; b.textContent = c.v ?? ''; const wr = a.offsetWidth, wv = b.offsetWidth; a.textContent = b.textContent = '';
      const it = { a, b, rot, val: c.v ?? '', t, x: x + wr, y: y + i * lh, w: wv, h: lh };
      const tj = q => DS.tarja(box, Object.assign({ x: wr - fs * .08, y: i * lh + lh * .5 - fs * .58, w: it.w + fs * .16, h: fs * 1.08, seed: seed * 17 + i, som }, q));
      if (c.tarja && c.tarja !== 'depois') { it.w = typeof c.tarja === 'number' ? c.tarja * fs * .6 : Math.max(wv, fs * 3); it.val = ''; t += rot.length / cps; it.tarja = tj({ t0: t + .03 }); t = it.tarja.fim + pausa; }
      else { t += (rot.length + it.val.length) / cps; if (c.tarja) { it.tarja = tj({ t0: t + .12 }); t = it.tarja.fim; } t += pausa; }
      if (som) for (let n = 0, N = rot.length + it.val.length, ps = Math.max(2, Math.ceil(.066 * cps)); n < N; n += ps) DS.som('tecla', it.t + n / cps, { gain: -4 - (ks % 3), p: (ks++ * 37) % 7 });
      it.fim = t; L.push(it);
    });
    onTick(tt => L.forEach(it => { const n = Math.max(0, Math.floor((tt - it.t) * cps + 1e-6)); if (n === it.n) return; it.n = n; it.a.textContent = it.rot.slice(0, n); it.b.textContent = it.val.slice(0, Math.max(0, n - it.rot.length)); }));
    return { el: box, linhas: L, fim: t, lh, caixa: i => ({ x: L[i].x, y: L[i].y + (lh - fs * 1.1) / 2, w: L[i].w, h: fs * 1.1 }) };
  };
  DS.rotulo = (pai, texto, o = {}) => DS.ficha(pai, Object.assign({ fs: 20, cps: 60, som: false, campos: [].concat(texto).map(v => ({ v })) }, o));
  // código grande do arquivo ("RL-0417"): grotesca pesada, batida caractere a caractere
  DS.codigo = (pai, txt, { x, y, fs = 150, t0 = 0, passo = .05, rotulo, som = true, peso = 800, esp = .05, z = 3 } = {}) => {
    const box = el('div', 'ds-cod', pai, `left:${x}px;top:${y}px;z-index:${z}`); let lab;
    if (rotulo) { lab = el('div', 'r', box, `font-size:${Math.max(16, fs * .15)}px`); lab.textContent = rotulo; }
    const big = el('div', '', box, `font-size:${fs}px;letter-spacing:${esp}em;font-weight:${peso}`), ch = [...txt].map(s => { const sp = el('span', '', big); sp.textContent = s; return sp; });
    if (som) ch.forEach((s, i) => s.textContent.trim() && DS.som('key', t0 + i * passo, { gain: -1 }));
    onTick(t => { ch.forEach((s, i) => (s.style.opacity = t >= t0 + i * passo ? 1 : 0)); if (lab) lab.style.opacity = t >= t0 ? 1 : 0; });
    return { el: box, w: big.offsetWidth, h: box.offsetHeight, fim: t0 + ch.length * passo };
  };
  // colunas de números miúdos (textura de arquivo); itens: lista própria, senão códigos sem sentido gerados pela semente
  DS.colunas = (pai, { x, y, n = 12, cols = 1, fs = 15, t0 = 0, passo = .025, seed = 1, larg = 120, itens, cor, z = 2 } = {}) => {
    const r = K.rng(seed * 911 + 1), box = el('div', 'ds-cols', pai, `left:${x}px;top:${y}px;font-size:${fs}px;line-height:${Math.round(fs * 1.55)}px;z-index:${z}` + (cor ? `;color:${cor}` : ''));
    const num = () => { const k = r(); return k < .4 ? String(Math.floor(r() * 1000)).padStart(3, '0') : k < .75 ? `${Math.floor(r() * 90 + 10)}.${Math.floor(r() * 10)}` : `${'ABDKR'[Math.floor(r() * 5)]}-${Math.floor(r() * 90 + 10)}`; };
    const ls = [];
    for (let c = 0; c < cols; c++) { const col = el('div', '', box, `position:absolute;left:${c * larg}px;top:0`); for (let i = 0; i < n; i++) { const d = el('div', '', col); d.textContent = itens ? itens[(c * n + i) % itens.length] : num() + (r() < .35 ? '  ' + num() : ''); ls.push(d); } }
    onTick(t => ls.forEach((d, i) => vis(d, t >= t0 + i * passo)));
    return { el: box, fim: t0 + ls.length * passo };
  };
  // régua graduada que se desenha da esquerda p/ a direita
  DS.regua = (pai, { x, y, w, t0 = 0, d = .45, passo = 14, alt = 10, vertical = false, numeros = true, esp = 1.5, z = 2 } = {}) => {
    let s = `M0 0H${w}`, tx = ''; for (let i = 0, n = Math.floor(w / passo); i <= n; i++) { const X = i * passo; s += `M${X} 0V${f1(i % 10 === 0 ? alt * 1.8 : i % 5 === 0 ? alt * 1.3 : alt * .7)}`; if (numeros && i % 10 === 0) tx += `<text x="${X + 3}" y="${alt * 1.8 + 13}">${String(i).padStart(2, '0')}</text>`; }
    const box = el('div', 'ds-abs', pai, `left:${x}px;top:${y}px;width:${w}px;height:${alt * 2 + 20}px;transform-origin:0 0;z-index:${z}` + (vertical ? ';transform:rotate(90deg)' : ''));
    box.innerHTML = `<svg class="ds-svg" width="${w}" height="${alt * 2 + 20}"><path d="${s}" fill="none" stroke="currentColor" stroke-width="${esp}"/>${tx}</svg>`;
    const ez = gsap.parseEase('power2.out'); onTick(t => { vis(box, t >= t0); box.style.clipPath = `inset(-6px ${((1 - ez(K.seg(t, t0, t0 + d))) * 100).toFixed(2)}% -6px -6px)`; });
    return { el: box, fim: t0 + d };
  };
  // cruz de registro (pisca uma vez ao entrar)
  DS.cruz = (pai, { x, y, s = 22, t0 = 0, circulo = true, esp = 1.6, z = 4 } = {}) => {
    const box = el('div', 'ds-abs', pai, `left:${x - s}px;top:${y - s}px;width:${s * 2}px;height:${s * 2}px;z-index:${z}`);
    box.innerHTML = `<svg class="ds-svg" width="${s * 2}" height="${s * 2}"><path d="M0 ${s}H${s * 2}M${s} 0V${s * 2}" fill="none" stroke="currentColor" stroke-width="${esp}"/>${circulo ? `<circle cx="${s}" cy="${s}" r="${s * .48}" fill="none" stroke="currentColor" stroke-width="${esp}"/>` : ''}</svg>`;
    const q = 2 / VIDEO.fps; onTick(t => vis(box, t >= t0 && !(t >= t0 + q && t < t0 + 2 * q))); return box;
  };
  // linha de medida (tracejada, com batentes) + rótulo em mono
  DS.medida = (pai, { x0, y0, x1, y1, texto, t0 = 0, d = .35, traco = '10 8', fs = 20, lado = -1, z = 4 } = {}) => {
    const L = Math.hypot(x1 - x0, y1 - y0), ang = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI;
    const box = el('div', 'ds-abs ds-med', pai, `left:${x0}px;top:${y0}px;width:${L}px;height:0;transform-origin:0 0;transform:rotate(${ang}deg);z-index:${z}`);
    box.innerHTML = `<svg class="ds-svg" style="top:-12px" width="${L}" height="24"><path d="M0 12H${f1(L)}" stroke-dasharray="${traco}"/><path d="M0 3V21M${f1(L)} 3V21"/></svg>` + (texto ? `<div class="t" style="font-size:${fs}px;line-height:1;top:${lado < 0 ? -fs - 16 : 18}px">${texto}</div>` : '');
    const sv = box.firstChild, tx = box.querySelector('.t'), ez = gsap.parseEase('power2.out');
    onTick(t => { vis(box, t >= t0); sv.style.clipPath = `inset(-4px ${((1 - ez(K.seg(t, t0, t0 + d))) * 100).toFixed(2)}% -4px -4px)`; if (tx) vis(tx, t >= t0 + d * .8); });
    return { el: box, fim: t0 + d };
  };

  // ───────── 7. anotação à mão (caneta) ─────────
  const suave = pts => { let d = `M${f1(pts[0][0])} ${f1(pts[0][1])}`; for (let i = 0; i < pts.length - 1; i++) { const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    d += `C${f1(p1[0] + (p2[0] - p0[0]) / 6)} ${f1(p1[1] + (p2[1] - p0[1]) / 6)},${f1(p2[0] - (p3[0] - p1[0]) / 6)} ${f1(p2[1] - (p3[1] - p1[1]) / 6)},${f1(p2[0])} ${f1(p2[1])}`; } return d; };
  // cada subcaminho ("M…") vira um <path> próprio e eles se desenham EM SEQUÊNCIA (o tracejado do SVG recomeça a cada subcaminho)
  const caneta = (pai, dpath, { t0 = 0, d = .5, esp = 2.6, cor, z = 6, ease = 'power1.inOut', som = 'pen', gain = -5 } = {}) => {
    const s = el('div', 'ds-abs', pai, `left:0;top:0;width:0;height:0;z-index:${z}`), subs = String(dpath).split(/(?=M)/).filter(Boolean);
    s.innerHTML = `<svg class="ds-svg" width="10" height="10">${subs.map(q => `<path d="${q}" pathLength="1" fill="none" stroke="${cor || 'var(--ds-caneta)'}" stroke-width="${esp}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1 1" stroke-dashoffset="1"/>`).join('')}</svg>`;
    const ps = [...s.querySelectorAll('path')], Ls = ps.map(p => Math.max(1, p.getTotalLength())), tot = Ls.reduce((a, b) => a + b, 0), ez = gsap.parseEase(ease);
    let acc = 0; const fx = Ls.map(L => { const a = acc / tot; acc += L; return [a, acc / tot]; });
    if (som) for (let u = 0; u < d - .05; u += .2) DS.som(som, t0 + u, { gain });
    onTick(t => { const k = ez(K.seg(t, t0, t0 + d)); vis(s, k > 0); ps.forEach((p, i) => { const u = K.seg(k, fx[i][0], fx[i][1]); p.style.display = u > 0 ? '' : 'none'; p.setAttribute('stroke-dashoffset', (1 - u).toFixed(4)); }); });
    return { el: s, fim: t0 + d };
  };
  DS.traco = (pai, pts, o) => caneta(pai, suave(pts), o);                       // traço livre por pontos [[x,y],…]
  // garrancho: parece escrita cursiva e não diz nada (de propósito — a anotação é textura, não informação)
  DS.garrancho = (pai, { x, y, w = 300, alt = 16, linhas = 1, entre, seed = 1, sobe = -.04, ...q } = {}) => {
    const r = K.rng(seed * 311 + 17), eh = entre ?? alt * 2.7; let dd = '', np = 0;
    for (let l = 0; l < linhas; l++) {
      const by = y + l * eh, fim = x + w * (l === linhas - 1 && linhas > 1 ? .45 + r() * .4 : .86 + r() * .14); let px = x + r() * alt;
      while (px < fim) {
        const pts = [[px, by + (px - x) * sobe]];
        for (let i = 0, nl = 2 + Math.floor(r() * 6); i < nl && px < fim; i++) {
          const a = alt * (.7 + r() * .6), k = r(), yb = by + (px - x) * sobe;
          if (k < .34) pts.push([px + a * .3, yb - alt * (.7 + r() * .5)], [px + a * .62, yb + r() * 2]);
          else if (k < .56) pts.push([px + a * .5, yb - alt * .85], [px + a * .12, yb - alt * .5], [px + a * .62, yb]);
          else if (k < .72) pts.push([px + a * .45, yb - alt * (1.9 + r() * .5)], [px + a * .2, yb - alt * 1.2], [px + a * .6, yb]);
          else if (k < .86) pts.push([px + a * .4, yb - alt * .7], [px + a * .5, yb + alt * (1 + r() * .5)], [px + a * .05, yb + alt * .8], [px + a * .7, yb]);
          else pts.push([px + a * .8, yb - alt * .12 + r() * 3]);
          px += a * (.62 + r() * .3);
        }
        np += pts.length; dd += suave(pts.map(p => [p[0] + (by - p[1]) * .24, p[1]])); px += alt * (1 + r() * .8);
      }
    }
    return caneta(pai, dd, Object.assign({ d: K.clamp(np * .011, .3, 1.5), esp: Math.max(2.4, alt * .17) }, q));
  };
  DS.sublinhado = (pai, { x, y, w, seed = 1, duplo = false, d = .22, ...q } = {}) => { const r = K.rng(seed * 97 + 5), pts = [[x, y + r() * 3], [x + w * .35, y + (r() - .5) * 5], [x + w * .7, y + (r() - .5) * 5], [x + w, y - 2 + r() * 3]];
    if (duplo) pts.push([x + w * .96, y + 7], [x + w * .5, y + 8 + r() * 3], [x + w * .06, y + 9]); return caneta(pai, suave(pts), Object.assign({ d: d * (duplo ? 1.8 : 1) }, q)); };
  DS.circulo = (pai, { x, y, w, h, seed = 1, voltas = 1.14, d = .38, ...q } = {}) => { const r = K.rng(seed * 53 + 9), cx = x + w / 2, cy = y + h / 2, n = 22, pts = [], a0 = -2.4 + r() * .6;
    for (let i = 0; i <= n * voltas; i++) { const a = a0 + (i / n) * TAU, k = 1 + (r() - .5) * .07 + i / (n * voltas) * .07; pts.push([cx + Math.cos(a) * w / 2 * k * 1.12, cy + Math.sin(a) * h / 2 * k * 1.3]); } return caneta(pai, suave(pts), Object.assign({ d }, q)); };
  DS.seta = (pai, { x0, y0, x1, y1, curva = .25, cabeca = 18, d = .32, ...q } = {}) => { const mx = (x0 + x1) / 2 - (y1 - y0) * curva, my = (y0 + y1) / 2 + (x1 - x0) * curva, ang = Math.atan2(y1 - my, x1 - mx), hx = a => `${f1(x1 - Math.cos(ang + a) * cabeca)} ${f1(y1 - Math.sin(ang + a) * cabeca)}`;
    return caneta(pai, `M${f1(x0)} ${f1(y0)}Q${f1(mx)} ${f1(my)},${f1(x1)} ${f1(y1)}M${hx(.5)}L${f1(x1)} ${f1(y1)}L${hx(-.5)}`, Object.assign({ d }, q)); };
  DS.assinatura = (pai, { x, y, w = 260, h = 90, seed = 1, d = .7, ...q } = {}) => { const r = K.rng(seed * 761 + 3), by = y + h * .62, pts = [[x, by], [x + w * .1, y], [x + w * .03, y + h * .55], [x + w * .2, y + h * .1], [x + w * .16, by + h * .25], [x + w * .3, by - h * .2]];
    for (let px = x + w * .3; px < x + w * .82;) { const a = w * (.04 + r() * .05); pts.push([px + a * .5, by - h * (.25 + r() * .5)], [px + a, by + h * r() * .12]); px += a; }
    pts.push([x + w, by - h * .3], [x + w * .9, by + h * .3], [x + w * .1, by + h * .38], [x + w * 1.02, by + h * .2]); return caneta(pai, suave(pts), Object.assign({ d, esp: 2.8 }, q)); };

  // ───────── 8. carimbo ─────────
  // texto em caixa dupla, girado, com tinta falhada; x,y = canto (ou cx,cy = centro). cor: preto (padrão) ou o acento
  DS.carimbo = (pai, { texto, sub, x, y, cx, cy, fs = 64, rot = -8, t0 = 0, seed = 1, cor, falha = 1, som = true, z = 8, fonte = 'grot', borda = true } = {}) => {
    const fam = fonte === 'mono' ? `700 ${fs}px 'Courier Prime'` : `900 ${fs}px 'Inter Tight'`, m = cv(4, 4).getContext('2d'); m.font = fam; m.letterSpacing = fs * .06 + 'px';
    const tw = m.measureText(texto).width, px = fs * .42, py = fs * .3, bw = Math.ceil(tw + 2 * px), bh = Math.ceil(fs * 1.02 + 2 * py + (sub ? fs * .4 : 0)), pad = 8;
    const c = cv(bw + 2 * pad, bh + 2 * pad), g = c.getContext('2d'), r = K.rng(seed * 643 + 29); g.translate(pad, pad);
    if (borda) { g.lineWidth = fs * .085; g.strokeRect(g.lineWidth / 2, g.lineWidth / 2, bw - g.lineWidth, bh - g.lineWidth); g.lineWidth = fs * .026; const k = fs * .16; g.strokeRect(k, k, bw - 2 * k, bh - 2 * k); }
    g.font = fam; g.letterSpacing = fs * .06 + 'px'; g.fillText(texto, px, py + fs * .86);
    if (sub) { g.font = `700 ${fs * .3}px 'Courier Prime'`; g.letterSpacing = fs * .04 + 'px'; g.textAlign = 'center'; g.fillText(sub, bw / 2, bh - py * .78); }
    const img = g.getImageData(0, 0, c.width, c.height), d = img.data, dir = r() * TAU;
    for (let j = 0, p = 3; j < c.height; j++) for (let i = 0; i < c.width; i++, p += 4) { if (!d[p]) continue;
      const n = fb(i * .02 + seed * 7.7, j * .02 - seed * 3.1), lado = .5 + .5 * Math.sin(dir + i / c.width * 3 + j / c.height * 2);      // pressão desigual
      d[p] *= n * falha < -.22 - lado * .25 || r() < (.08 + (1 - lado) * .24) * falha ? 0 : .72 + r() * .28; }
    g.putImageData(img, 0, 0); tinge(c, cor || tinta(pai));
    if (cx !== undefined) { x = cx - c.width / 2; y = cy - c.height / 2; }
    const box = el('div', 'ds-carimbo', pai, `left:${x}px;top:${y}px;width:${c.width}px;height:${c.height}px;z-index:${z}`); box.appendChild(c);
    if (som) DS.som('stamp', t0 + .08, { gain: 0 }); DS.baques.push([t0 + .1, 7]);
    onTick(t => { if (t < t0) return vis(box, false); vis(box, true); const k = K.seg(t, t0, t0 + .1), e = k * k * k, rb = K.seg(t, t0 + .1, t0 + .22);
      box.style.opacity = (.4 + .6 * k).toFixed(3); box.style.transform = `rotate(${(rot - (1 - e) * 5).toFixed(2)}deg) scale(${(1 + (1 - e) * .55 - Math.sin(rb * Math.PI) * .025).toFixed(4)})`; });
    return { el: box, w: c.width, h: c.height, fim: t0 + .22 };
  };

  // ───────── texto com tarjas embutidas: "Trabalhou na [[Usina 3]] até o apagão." ─────────
  // o trecho entre [[ ]] NUNCA aparece (fica transparente sob a tarja): não há o que vazar
  const rico = (cont, txt, seed) => {
    const r = K.rng(seed * 389 + 1), toks = [];
    String(txt).split(/(\[\[.*?\]\]|\n|\s+)/).forEach(s => {
      if (!s) return; if (s === '\n') return cont.appendChild(document.createElement('br')); if (/^\s+$/.test(s)) return cont.appendChild(document.createTextNode(' '));
      const tj = s.startsWith('[['), sp = el('span', tj ? 'ds-tj' : 'ds-w', cont); sp.textContent = tj ? s.slice(2, -2) : s;
      if (tj) { const b = el('b', '', sp), n = 5, top = [], bot = []; for (let i = 0; i <= n; i++) { top.push(`${(i / n * 100).toFixed(0)}% ${(r() * 15).toFixed(0)}%`); bot.push(`${(100 - i / n * 100).toFixed(0)}% ${(100 - r() * 15).toFixed(0)}%`); } b.style.clipPath = `polygon(${top.concat(bot).join(',')})`; sp._b = b; }
      toks.push(sp);
    });
    return toks;
  };
  const anima = (toks, t0, { pps = 16, dTj = .14, som } = {}) => {
    const ez = gsap.parseEase('power1.inOut'); toks.forEach((sp, i) => { sp._t = t0 + i / pps; if (sp._b && som) DS.som('marker', sp._t, { gain: -10 }); });
    onTick(t => toks.forEach(sp => { if (sp._b) sp._b.style.transform = `scaleX(${ez(K.seg(t, sp._t, sp._t + dTj)).toFixed(4)})`; else vis(sp, t >= sp._t); }));
    return t0 + toks.length / pps + dTj;
  };
  // bloco de texto: fonte 'serif' (citação), 'mono' (ficha) ou 'grot' (título de apoio); entra palavra a palavra, seco
  DS.texto = (pai, txt, { x, y, w, fs = 34, fonte = 'serif', peso, italico = false, cor, t0 = 0, pps = 14, lh = 1.3, alinhar = 'left', seed = 1, som = true, z = 3 } = {}) => {
    const box = el('div', 'ds-txt', pai, `left:${x}px;top:${y}px;${w ? `width:${w}px;` : 'white-space:nowrap;'}font-family:var(--ds-${fonte});font-size:${fs}px;line-height:${lh};text-align:${alinhar};font-weight:${peso ?? (fonte === 'grot' ? 800 : fonte === 'serif' ? 500 : 400)};z-index:${z}` + (italico ? ';font-style:italic' : '') + (cor ? `;color:${cor}` : ''));
    const fim = anima(rico(box, txt, seed), t0, { pps, som }); return { el: box, fim, w: box.offsetWidth, h: box.offsetHeight };
  };
  // título em grotesca pesada, uma linha por batida (cabe em maxw se informado)
  DS.titulo = (pai, linhas, { x, y, fs = 150, t0 = 0, passo = .14, d = .14, cor, peso = 900, lh = .94, esp = -.025, alinhar = 'left', w, maxw, som = 'cut', gain = -4, z = 5 } = {}) => {
    const box = el('div', 'ds-tit', pai, `left:${x}px;top:${y}px;font-size:${fs}px;font-weight:${peso};line-height:${lh};letter-spacing:${esp}em;text-align:${alinhar};z-index:${z}` + (w ? `;width:${w}px` : '') + (cor ? `;color:${cor}` : ''));
    const ls = [].concat(linhas).map(s => { const l = el('div', '', box); l.textContent = s; return l; });
    if (maxw && box.offsetWidth > maxw) box.style.fontSize = (fs = fs * maxw / box.offsetWidth).toFixed(1) + 'px';
    const ez = gsap.parseEase('power3.out'); if (som) ls.forEach((l, i) => DS.som(som, t0 + i * passo, { gain }));
    onTick(t => ls.forEach((l, i) => { const ti = t0 + i * passo, k = ez(K.seg(t, ti, ti + d)); vis(l, t >= ti); l.style.transform = `translateY(${((1 - k) * fs * .2).toFixed(2)}px)`; l.style.clipPath = `inset(${((1 - k) * 100).toFixed(1)}% -5% -14% -5%)`; }));
    return { el: box, fim: t0 + (ls.length - 1) * passo + d, w: box.offsetWidth, h: box.offsetHeight, fs };
  };

  // ───────── 5. painel investigativo: cartões, etiquetas, alfinetes e fios ─────────
  DS.alfinete = (pai, { x, y, s = 20, t0 = 0, som = true, z = 9 } = {}) => {
    const p = el('div', 'ds-pino', pai, `left:${x - s / 2}px;top:${y - s / 2}px;width:${s}px;height:${s}px;z-index:${z}`); if (som) DS.som('pin', t0, { gain: -2 });
    onTick(t => { vis(p, t >= t0); p.style.transform = `scale(${(1 + (1 - K.seg(t, t0, t0 + .07)) * .8).toFixed(3)})`; }); return p;
  };
  // cartão de papel: sub (mono miúdo), título (grotesca) e linhas de texto com [[tarjas]]. Devolve {el, pino, w, h, fim}
  DS.cartao = (pai, { x, y, w = 420, titulo, sub, linhas = [], fs = 24, t0 = 0, rot = 0, alfinete = true, seed = 1, pps = 18, tom = 'claro', fundo, som = true, z = 2 } = {}) => {
    const esc = tom === 'escuro', box = el('div', 'ds-cartao', pai, `left:${x}px;top:${y}px;width:${w}px;z-index:${z};background:${fundo || (esc ? '#141414' : '#efeeea')};padding:${f1(fs * (alfinete ? 1.25 : .85))}px ${f1(fs * .9)}px ${fs}px`);
    if (esc) ['--ds-tinta:#eceae5', '--ds-cinza:#a3a29c', '--ds-texto:#cfcdc7'].forEach(v => box.style.setProperty(...v.split(':')));
    if (sub) el('div', 'ds-c-sub', box, `font-size:${f1(fs * .72)}px`).textContent = sub;
    if (titulo) el('div', 'ds-c-tit', box, `font-size:${f1(fs * 1.8)}px`).textContent = titulo;
    const corpo = el('div', 'ds-c-txt', box, `font-size:${fs}px;line-height:1.4`), fim = anima(rico(corpo, [].concat(linhas).join('\n'), seed), t0 + .18, { pps, som });
    if (alfinete) DS.alfinete(box, { x: w / 2, y: fs * .62, t0: t0 + .08, som });
    if (som) DS.som('paper', t0, { gain: -1 }); DS.baques.push([t0 + .1, 1.5]);
    onTick(t => { vis(box, t >= t0); const k = K.seg(t, t0, t0 + .1); box.style.transform = `rotate(${(rot + (1 - k) * 2.5).toFixed(2)}deg) scale(${(1 + (1 - k) * .06).toFixed(4)})`; });
    return { el: box, pino: [x + w / 2, y + fs * .62], x, y, w, h: box.offsetHeight, fim };
  };
  // etiqueta de nome: bloco chapado com texto vazado + número (como as etiquetas do painel de referência)
  DS.etiqueta = (pai, { x, y, texto, sub, n, fs = 46, t0 = 0, cor, d = .16, som = true, z = 5 } = {}) => {
    const box = el('div', 'ds-etq', pai, `left:${x}px;top:${y}px;z-index:${z};background:${cor || 'var(--ds-tinta)'};padding:${f1(fs * .2)}px ${f1(fs * .32)}px ${f1(fs * .17)}px`);
    if (sub) el('div', 's', box, `font-size:${f1(fs * .42)}px`).textContent = sub; el('div', 't', box, `font-size:${fs}px`).textContent = texto;
    const k = fs * .74, num = n === undefined ? null : el('div', 'n', box, `right:${-k}px;width:${k}px;height:${k}px;font-size:${f1(fs * .56)}px`); if (num) num.textContent = n;
    const ez = gsap.parseEase('power2.out'); if (som) DS.som('click', t0, { gain: 0 });
    onTick(t => { vis(box, t >= t0); box.style.clipPath = `inset(0 ${((1 - ez(K.seg(t, t0, t0 + d))) * 100).toFixed(2)}% 0 0)`; if (t >= t0 + d) box.style.clipPath = 'none'; if (num) vis(num, t >= t0 + d); });
    return { el: box, w: box.offsetWidth, h: box.offsetHeight, fim: t0 + d };
  };
  // fio entre dois pontos [x,y] (ou peças com .pino), desenhado no tempo. cor: 'var(--ds-acento)' para o fio que importa
  DS.fio = (pai, { de, para, t0 = 0, d, cor, esp = 2.2, queda = .03, som = true, z = 7, gain = -6 } = {}) => {
    const [x0, y0] = de.pino || de, [x1, y1] = para.pino || para, L = Math.hypot(x1 - x0, y1 - y0), s = el('div', 'ds-abs', pai, `left:0;top:0;width:0;height:0;z-index:${z}`);
    s.innerHTML = `<svg class="ds-svg" width="10" height="10"><path d="M${f1(x0)} ${f1(y0)}Q${f1((x0 + x1) / 2)} ${f1((y0 + y1) / 2 + L * queda)},${f1(x1)} ${f1(y1)}" pathLength="1" fill="none" stroke="${cor || 'var(--ds-fio)'}" stroke-width="${esp}" stroke-linecap="round" stroke-dasharray="1 1" stroke-dashoffset="1"/></svg>`;
    const p = s.querySelector('path'), dur = d ?? K.clamp(L / 1600, .22, .7), ez = gsap.parseEase('power2.inOut'); if (som) DS.som('thread', t0, { gain });
    onTick(t => { const k = ez(K.seg(t, t0, t0 + dur)); vis(s, k > 0); p.setAttribute('stroke-dashoffset', (1 - k).toFixed(4)); });
    return { el: s, fim: t0 + dur };
  };
})();
