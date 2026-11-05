// Kit do estilo "ilustração explicativa": explainer de ilustração plana com contorno preto fino,
// personagens sem rosto (cabeça-círculo + bico triangular), fundos rosa-chiclete/creme com grão,
// fotos P&B em cantoneiras ciano, rachaduras que crescem, coroas/labaredas amarelas que fervem,
// globo projetado com contornos de continentes, regadores, bolhas, banco de nuvens pretas com rótulo químico.
// Depende de core.js e kit.js (K, TL, onTick, VIDEO). Tudo é função do tempo t: nada toca sozinho.
(function () {
  const IL = (window.IL = {});

  // ── paleta medida na referência ──
  IL.P = {
    rosa: '#f06aa6', creme: '#f3ece0', k: '#231f20', azulc: '#b4dcec', royal: '#2b3db6', azulm: '#5b8fe6',
    amarelo: '#f9d02a', cinza: '#bdbcba', cinzaE: '#a3a2a0', cinzaC: '#d6d5d2', ciano: '#7fd0f0', vidro: '#86d4f1', branco: '#fbf8f2',
  };
  IL.LW = 5;                                    // contorno padrão (px a 1080 de largura)
  const f1 = (IL.f1 = v => +(+v).toFixed(1));
  const NS = 'http://www.w3.org/2000/svg';

  // ── tempo ──
  IL.E = (nome, t, a, b) => K.ease(nome, K.seg(t, a, b));
  IL.q = (t, qps = 12) => Math.floor(t * qps + 1e-6) / qps;              // tempo de stop-motion ("em dois")
  IL.quadro = (t, qps = 8) => Math.floor(t * qps + 1e-6);                 // índice do quadro de fervura
  IL.passo = (t, lista, ini) => { let v = ini; for (const [a, x] of lista) if (t >= a) v = x; return v; };
  IL.janela = (t, a, b) => t >= a && t < b;
  const BO = gsap.parseEase('back.out(2)'), EXO = gsap.parseEase('expo.out');
  IL.pop = (t, t0, d = .32) => t < t0 ? 0 : BO(K.seg(t, t0, t0 + d));    // 0 → ~1.1 → 1

  // ── DOM/SVG ──
  // insere HTML/SVG no fim de parent (em <svg>/<g> os nós nascem no namespace SVG) e devolve o 1º nó novo
  IL.add = (parent, s) => { const n0 = parent.children.length; parent.insertAdjacentHTML('beforeend', s.trim()); const novos = [...parent.children].slice(n0); return novos.length === 1 ? novos[0] : novos; };
  IL.tf = (el, x, y, s = 1, r = 0, sy) => el.setAttribute('transform', `translate(${f1(x)} ${f1(y)}) rotate(${f1(r)}) scale(${(+s).toFixed(4)} ${(+(sy ?? s)).toFixed(4)})`);
  IL.show = (el, on) => { if (el instanceof SVGElement) el.setAttribute('display', on ? 'inline' : 'none'); else el.style.display = on ? '' : 'none'; };
  IL.svg = (parent, w, h, cls = '') => IL.add(parent, `<svg class="${cls}" xmlns="${NS}" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="position:absolute;left:0;top:0;overflow:visible"></svg>`);

  // ── caminhos ──
  IL.poli = (pts, fechado) => 'M' + pts.map(p => `${f1(p[0])} ${f1(p[1])}`).join('L') + (fechado ? 'Z' : '');
  // Catmull-Rom → Bézier (aberto ou fechado): curva macia passando pelos pontos
  IL.cm = (pts, fechado) => {
    const n = pts.length; if (n < 3) return IL.poli(pts, fechado);
    const g = i => fechado ? pts[(i + n) % n] : pts[Math.max(0, Math.min(n - 1, i))];
    let d = `M${f1(pts[0][0])} ${f1(pts[0][1])}`; const m = fechado ? n : n - 1;
    for (let i = 0; i < m; i++) { const p0 = g(i - 1), p1 = g(i), p2 = g(i + 1), p3 = g(i + 2);
      d += `C${f1(p1[0] + (p2[0] - p0[0]) / 6)} ${f1(p1[1] + (p2[1] - p0[1]) / 6)} ${f1(p2[0] - (p3[0] - p1[0]) / 6)} ${f1(p2[1] - (p3[1] - p1[1]) / 6)} ${f1(p2[0])} ${f1(p2[1])}`; }
    return d + (fechado ? 'Z' : '');
  };
  // ── primitivas com contorno (devolvem string SVG) ──
  const lw = o => o.lw ?? IL.LW;
  IL.forma = (d, fill, o = {}) => `<path d="${d}" fill="${fill}" stroke="${o.cor ?? IL.P.k}" stroke-width="${lw(o)}" stroke-linejoin="round" stroke-linecap="round"${o.attr ? ' ' + o.attr : ''}/>`;
  IL.linha = (d, cor, w, o = {}) => `<path d="${d}" fill="none" stroke="${cor}" stroke-width="${w}" stroke-linecap="${o.cap ?? 'round'}" stroke-linejoin="round"${o.attr ? ' ' + o.attr : ''}/>`;
  IL.circ = (x, y, r, fill, o = {}) => `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}" fill="${fill}"${o.sem ? '' : ` stroke="${o.cor ?? IL.P.k}" stroke-width="${lw(o)}"`}${o.attr ? ' ' + o.attr : ''}/>`;
  IL.elipse = (x, y, rx, ry, fill, o = {}) => `<ellipse cx="${f1(x)}" cy="${f1(y)}" rx="${f1(rx)}" ry="${f1(ry)}" fill="${fill}"${o.sem ? '' : ` stroke="${o.cor ?? IL.P.k}" stroke-width="${lw(o)}"`}${o.rot ? ` transform="rotate(${o.rot} ${f1(x)} ${f1(y)})"` : ''}/>`;
  // tubo com contorno: braço, manga, perna, cano — traço preto largo por baixo + traço colorido por cima
  IL.tubo = (d, w, fill, o = {}) => `<g class="tubo">${IL.linha(d, o.cor ?? IL.P.k, w + 2 * lw(o), { cap: o.cap })}${IL.linha(d, fill, w, { cap: o.cap })}</g>`;
  // atualiza um tubo já inserido (para braços animados)
  IL.setTubo = (g, d) => g.querySelectorAll('path').forEach(p => p.setAttribute('d', d));
  // pílula (tronco dos bonecos)
  IL.pilula = (x, y, w, h, fill, o = {}) => `<rect x="${f1(x)}" y="${f1(y)}" width="${f1(w)}" height="${f1(h)}" rx="${f1(o.r ?? Math.min(w, h) / 2)}" fill="${fill}"${o.sem ? '' : ` stroke="${o.cor ?? IL.P.k}" stroke-width="${lw(o)}"`}/>`;

  // ── fundo chapado + grão fino ──
  IL.fundo = (parent, cor, cls = '') => IL.add(parent, `<div class="il-fundo ${cls}" style="position:absolute;inset:0;background:${cor}"></div>`);
  // grão estático de 1 px que "treme" (deslocado) a qps quadros por segundo — o da referência é fino e quase parado
  IL.grao = (parent, o = {}) => {
    const W = VIDEO.w + 64, H = VIDEO.h + 64, c = document.createElement('canvas'); c.width = W; c.height = H;
    const x = c.getContext('2d'), img = x.createImageData(W, H), r = K.rng(o.seed ?? 77), d = img.data, a = o.amp ?? 70;
    for (let i = 0; i < d.length; i += 4) { const v = 128 + (r() + r() - 1) * a; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255; }
    x.putImageData(img, 0, 0);
    c.style.cssText = `position:absolute;left:-32px;top:-32px;width:${W}px;height:${H}px;pointer-events:none;mix-blend-mode:${o.blend ?? 'overlay'};opacity:${o.op ?? .16};z-index:${o.z ?? 50}`;
    parent.appendChild(c);
    onTick(t => { const rr = K.rng(IL.quadro(t, o.qps ?? 12) * 131 + 7); c.style.transform = `translate(${Math.round((rr() - .5) * 60)}px,${Math.round((rr() - .5) * 60)}px)`; });
    return c;
  };

  // ── foto P&B em cantoneiras ciano (prepare a imagem com tools/ilustra.py foto) ──
  IL.foto = (parent, src, w, h, o = {}) => {
    const c = o.canto ?? Math.round(w * .07), cor = o.cor ?? IL.P.ciano;
    const tri = (pos, poly) => `<div style="position:absolute;${pos};width:${c}px;height:${c}px;background:${cor};clip-path:polygon(${poly})"></div>`;
    const el = IL.add(parent, `<div class="il-foto" style="position:absolute;left:0;top:0;width:${w}px;height:${h}px;margin:${-h / 2}px 0 0 ${-w / 2}px;will-change:transform">
      <img src="${src}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block">
      ${tri(`left:${-c * .28}px;top:${-c * .28}px`, '0 0,100% 0,0 100%')}${tri(`right:${-c * .28}px;top:${-c * .28}px`, '0 0,100% 0,100% 100%')}
      ${tri(`left:${-c * .28}px;bottom:${-c * .28}px`, '0 0,0 100%,100% 100%')}${tri(`right:${-c * .28}px;bottom:${-c * .28}px`, '100% 0,100% 100%,0 100%')}</div>`);
    return el;
  };
  IL.posFoto = (el, x, y, s = 1, r = 0) => (el.style.transform = `translate(${f1(x)}px,${f1(y)}px) rotate(${f1(r)}deg) scale(${(+s).toFixed(4)})`);
  // coreografia "deslizar e reorganizar": cada foto tem uma lista de poses [t, x, y, s, r]; a primeira pose
  // fora da tela é a entrada. Entre poses: deslize curto e seco (expo.out) na entrada, power2.inOut no rearranjo.
  IL.coreografia = (el, poses, o = {}) => onTick(t => {
    if (t < poses[0][0]) { IL.show(el, false); return; }
    IL.show(el, true);
    let i = 0; while (i < poses.length - 1 && t >= poses[i + 1][0]) i++;
    const cur = poses[i], prev = poses[i - 1];
    let p = cur.slice(1, 5);
    if (prev) { const k = K.ease(cur[6] ?? 'power2.inOut', K.seg(t, cur[0], cur[0] + (cur[5] ?? .35))); p = [1, 2, 3, 4].map(j => K.lerp(prev[j], cur[j], k)); }
    const f = o.fase ?? 0, tq = IL.q(t, 12), wob = o.balanco ?? .6;          // balanço lento, "em dois"
    IL.posFoto(el, p[0] + Math.sin(tq * 2.1 + f) * 3, p[1] + Math.cos(tq * 1.7 + f) * 3, p[2], p[3] + Math.sin(tq * 2.6 + f) * wob);
  });

  // ── rachaduras / rios ramificados que crescem em degraus ──
  // o: { seed, n (troncos), w, h, lw, cor, seg:[min,max] px, passos:[min,max], ramo: prob., bordas:'tblr' }
  IL.rachaduras = (svg, o = {}) => {
    const r = K.rng(o.seed ?? 5), W = o.w ?? VIDEO.w, H = o.h ?? VIDEO.h, out = [], bordas = o.bordas ?? 'tblr';
    const seg = o.seg ?? [50, 120], ps = o.passos ?? [6, 11];
    const anda = (x, y, ang, n, prof) => { const pts = [[x, y]];
      for (let i = 0; i < n; i++) { ang += (r() - .5) * 1.7; const L = K.lerp(seg[0], seg[1], r()) * (prof ? .7 : 1); x += Math.cos(ang) * L; y += Math.sin(ang) * L; pts.push([x, y]);
        if (!prof && i > 0 && r() < (o.ramo ?? .4)) out.push({ pts: anda(x, y, ang + (r() < .5 ? 1 : -1) * (.7 + r() * .6), 2 + Math.floor(r() * 3), 1), ramo: i / n }); }
      return pts; };
    for (let k = 0; k < (o.n ?? 8); k++) {
      const b = bordas[Math.floor(r() * bordas.length)]; let x, y, a;
      if (b === 't') { x = r() * W; y = -10; a = Math.PI / 2; } else if (b === 'b') { x = r() * W; y = H + 10; a = -Math.PI / 2; }
      else if (b === 'l') { x = -10; y = r() * H; a = 0; } else { x = W + 10; y = r() * H; a = Math.PI; }
      out.push({ pts: anda(x, y, a + (r() - .5) * .8, K.lerp(ps[0], ps[1], r()) | 0, 0), ramo: 0, tronco: k });
    }
    return out.map((c, i) => { const el = IL.add(svg, IL.linha(IL.poli(c.pts), o.cor ?? IL.P.k, o.lw ?? 3.5, { cap: 'butt', attr: 'stroke-linejoin="miter"' }));
      const len = el.getTotalLength(); el.style.strokeDasharray = `${len} ${len + 10}`; el.style.strokeDashoffset = len; return Object.assign(c, { el, len, i }); });
  };
  // cresce cada linha conforme t (em degraus de stop-motion); t0/dur por linha, ramos entram depois do tronco
  IL.crescer = (lista, t, o = {}) => { const tq = IL.q(t, o.qps ?? 12);
    for (const c of lista) { const t0 = (o.t0 ?? 0) + (c.tronco !== undefined ? c.tronco * (o.atraso ?? .12) : (o.atraso ?? .12) * 3 + c.ramo * (o.dur ?? 1.6) * .8 + (c.i % 5) * .05), d = c.tronco !== undefined ? (o.dur ?? 1.6) : (o.dur ?? 1.6) * .45;
      const p = K.ease('power1.out', K.seg(tq, t0, t0 + d)); c.el.style.strokeDashoffset = c.len * (1 - p); } };

  // ── coroa amarela (o "M" que ferve nos cantos) ──
  // contorno grosso amarelo em zigue-zague: polígono externo + interno (evenodd); vértices tremem por quadro
  IL.coroaD = (w, h, seed, frame, o = {}) => {
    const r = K.rng(seed * 1000 + frame * 17), J = (o.j ?? 4), j = () => (r() - .5) * 2 * J, esp = o.esp ?? w * .16, n = o.picos ?? 3;
    const ext = [[0, h]], int = [];
    for (let i = 0; i <= n * 2; i++) { const x = (i / (n * 2)) * w, alto = i % 2 === 0; const y = alto ? (i === 0 || i === n * 2 ? h * .2 : h * (.02 + r() * .1)) : h * (.3 + r() * .1);
      ext.push([x + j(), y + j()]); }
    ext.push([w, h]);
    // interno: mesmo zigue-zague deslocado para baixo/para dentro
    for (let i = ext.length - 2; i >= 1; i--) { const [x, y] = ext[i]; int.push([K.clamp(x, esp, w - esp) + j() * .4, y + esp * 1.25 + j() * .4]); }
    const intPts = [[w - esp, h + 2], ...int, [esp, h + 2]];
    return IL.poli(ext, true) + IL.poli(intPts, true);
  };
  IL.coroa = (svg, x, y, w, h, o = {}) => {
    const g = IL.add(svg, `<g transform="translate(${x} ${y})${o.espelho ? ` scale(-1 1) translate(${-w} 0)` : ''}"><path fill="${o.cor ?? IL.P.amarelo}" fill-rule="evenodd"/></g>`), p = g.firstElementChild;
    const fa = IL.add(g, `<g></g>`);
    const fais = Array.from({ length: o.faiscas ?? 3 }, (_, i) => IL.add(fa, `<path d="M0 -9 L5 0 L0 9 L-5 0Z" fill="${o.cor ?? IL.P.amarelo}"/>`));
    onTick(t => { const fr = IL.quadro(t, o.qps ?? 8); p.setAttribute('d', IL.coroaD(w, h, o.seed ?? 3, fr, o));
      fais.forEach((f, i) => { const per = 1.1, u = ((IL.q(t, 8) + i * per / fais.length) % per) / per, rr = K.rng(i * 9 + Math.floor((IL.q(t, 8) + i * per / fais.length) / per) * 31);
        IL.tf(f, w * (.15 + rr() * .7), -10 - u * h * .7, (1 - u) * (.6 + rr() * .6), rr() * 40); f.setAttribute('opacity', u < .85 ? 1 : 0); }); });
    return g;
  };
  // ── labareda / explosão radial com contorno (sol, fogo, estouro) ──
  IL.labaredaD = (cx, cy, r, n, seed, frame, o = {}) => {
    const rr = K.rng(seed * 1000 + frame * 13), pts = [], a0 = (o.giro ?? 0) * Math.PI / 180, dir = o.dir ?? null;
    for (let i = 0; i < n * 2; i++) { const a = a0 + i / (n * 2) * Math.PI * 2 + (rr() - .5) * .12;
      let R = i % 2 ? r * (o.vale ?? .78) : r * (1 + (rr() - .3) * (o.var ?? .35));
      if (dir !== null) { const c = Math.cos(a - dir * Math.PI / 180); R *= 1 + Math.max(0, c) * (o.puxa ?? .6) * (i % 2 ? .5 : 1); }
      pts.push([cx + Math.cos(a) * R, cy + Math.sin(a) * R]); }
    return IL.poli(pts, true);
  };

  // bola de fogo: abraça o círculo por baixo e solta picos longos para o lado de 'dir' (graus; -90 = para cima)
  IL.fogoD = (cx, cy, r, seed, frame, o = {}) => {
    const rr = K.rng(seed * 1000 + frame * 13), n = o.picos ?? 6, dir = (o.dir ?? -70) * Math.PI / 180, ab = (o.abertura ?? 150) * Math.PI / 180, pts = [];
    const base = o.base ?? 1.08, alto = o.alto ?? .75;
    for (let i = 0; i < 40; i++) { const a = dir + Math.PI + (i / 40) * Math.PI * 2 - Math.PI; const da = Math.atan2(Math.sin(a - dir), Math.cos(a - dir));
      if (Math.abs(da) > ab / 2) pts.push([cx + Math.cos(a) * r * (base + (rr() - .5) * .03), cy + Math.sin(a) * r * (base + (rr() - .5) * .03)]); }
    // picos: de um lado da abertura ao outro
    const seq = []; for (let i = 0; i <= n * 2; i++) { const a = dir + ab / 2 - (i / (n * 2)) * ab, k = 1 - Math.abs((i / (n * 2)) * 2 - 1);
      const R = i % 2 ? r * (base + .06 + rr() * .06) : r * (base + .12 + alto * (.35 + .65 * k) * (.8 + rr() * .4)); seq.push([cx + Math.cos(a) * R, cy + Math.sin(a) * R]); }
    // ordena: arco de baixo (no sentido do relógio a partir do fim da abertura) + picos
    const baixo = pts.sort((p, q) => { const ap = (Math.atan2(p[1] - cy, p[0] - cx) - (dir + ab / 2) + 6 * Math.PI) % (2 * Math.PI), aq = (Math.atan2(q[1] - cy, q[0] - cx) - (dir + ab / 2) + 6 * Math.PI) % (2 * Math.PI); return aq - ap; });
    return IL.poli([...baixo, ...seq], true);
  };

  // ── bolhas de contorno azul (vapor, água) ──
  IL.bolha = (x, y, r, o = {}) => `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}" fill="none" stroke="${o.cor ?? IL.P.azulc}" stroke-width="${o.lw ?? 4}"/>`;
  // campo de bolhas que sobem de uma área: devolve atualizador (t) → posiciona n bolhas
  IL.bolhas = (svg, o = {}) => {
    const r = K.rng(o.seed ?? 11), n = o.n ?? 12, g = IL.add(svg, `<g></g>`), bs = [];
    for (let i = 0; i < n; i++) bs.push({ el: IL.add(g, IL.bolha(0, 0, 1, o)), x: o.x + (r() - .5) * (o.larg ?? 120), t0: (o.t0 ?? 0) + r() * (o.dur ?? 1), v: (o.sobe ?? 260) * (.6 + r() * .7), rad: (o.r ?? 14) * (.5 + r() * .9), osc: r() * 6 });
    onTick(t => { const tq = IL.q(t, 12); for (const b of bs) { const u = tq - b.t0, vida = o.vida ?? .9; if (u < 0 || u > vida) { b.el.setAttribute('display', 'none'); continue; }
      b.el.setAttribute('display', 'inline'); const k = u / vida; b.el.setAttribute('cx', f1(b.x + Math.sin(u * 7 + b.osc) * 10)); b.el.setAttribute('cy', f1(o.y - u * b.v));
      b.el.setAttribute('r', f1(b.rad * (k < .15 ? k / .15 : k > .8 ? 1 - (k - .8) / .2 * .6 : 1))); } });
    return g;
  };

  // ── globo: círculo preto + contornos de continentes (window.TERRA, de tools/ilustra.py terra) ──
  // o: { cx, cy, r, lon0, lat0, cor, lw, fundo, pais (cor do contorno do país destacado) }
  IL.globo = (svg, o = {}) => {
    const g = IL.add(svg, `<g class="il-globo"></g>`), D = Math.PI / 180;
    const st = { cx: o.cx ?? 0, cy: o.cy ?? 0, r: o.r ?? 300, lon0: o.lon0 ?? -55, lat0: o.lat0 ?? -15 };
    const disco = IL.add(g, IL.circ(st.cx, st.cy, st.r, o.fundo ?? IL.P.k, { sem: true }));
    const terra = IL.add(g, `<path fill="none" stroke="${o.cor ?? IL.P.rosa}" stroke-width="${o.lw ?? 2.6}" stroke-linejoin="round" stroke-linecap="round"/>`);
    const pais = o.pais ? IL.add(g, `<path fill="${o.paisFill ?? 'none'}" stroke="${o.pais}" stroke-width="${o.paisLw ?? 3.5}" stroke-linejoin="round"/>`) : null;
    const proj = (lon, lat) => { const l = (lon - st.lon0) * D, p = lat * D, p0 = st.lat0 * D;
      const x = Math.cos(p) * Math.sin(l), y = Math.cos(p0) * Math.sin(p) - Math.sin(p0) * Math.cos(p) * Math.cos(l), c = Math.sin(p0) * Math.sin(p) + Math.cos(p0) * Math.cos(p) * Math.cos(l);
      return [st.cx + x * st.r, st.cy - y * st.r, c]; };
    const aneis = rings => { let d = ''; for (const ring of rings) { let run = []; const flush = () => { if (run.length > 1) d += IL.poli(run); run = []; };
      for (const [lon, lat] of ring) { const [x, y, c] = proj(lon, lat); if (c > 0.02) run.push([x, y]); else flush(); } flush(); } return d; };
    const desenha = () => { disco.setAttribute('cx', st.cx); disco.setAttribute('cy', st.cy); disco.setAttribute('r', st.r);
      terra.setAttribute('d', aneis(window.TERRA.land)); if (pais) pais.setAttribute('d', aneis(window.TERRA.pais || [])); };
    desenha();
    return { g, disco, terra, pais, proj, st, desenha, caminho: (lls, suave = true) => (suave ? IL.cm : IL.poli)(lls.map(([lo, la]) => proj(lo, la).slice(0, 2))) };
  };

  // ── fluxo: tubo com contorno que se desenha + traços brancos correndo dentro (rio voador, cano com água) ──
  IL.fluxo = (svg, d, o = {}) => {
    const w = o.w ?? 26, g = IL.add(svg, `<g class="il-fluxo">${IL.linha(d, o.borda ?? IL.P.k, w + 2 * (o.lw ?? IL.LW))}${IL.linha(d, o.cor ?? IL.P.azulc, w)}${IL.linha(d, o.traco ?? IL.P.branco, o.tw ?? 5, { attr: 'class="corre"' })}</g>`);
    const ps = [...g.querySelectorAll('path')], len = ps[0].getTotalLength(), dash = o.dash ?? [26, 34];
    const ponta = o.ponta ? IL.add(g, `<path d="M0 -${w * 1.05} L${w * 1.5} 0 L0 ${w * 1.05}Z" fill="${o.cor ?? IL.P.azulc}" stroke="${o.borda ?? IL.P.k}" stroke-width="${o.lw ?? IL.LW}" stroke-linejoin="round"/>`) : null;
    const set = (p, fase = 0) => { p = K.clamp(p); const L = len * p, per = dash[0] + dash[1], fim = L - w * .5;
      ps[0].style.strokeDasharray = ps[1].style.strokeDasharray = `${f1(L)} ${f1(len + 99)}`;
      // traços brancos que correm (fase em px) só no trecho já desenhado
      const arr = [0]; let pos = 0;
      for (let a = ((fase % per) + per) % per - per; a < fim; a += per) { const s0 = Math.max(0, a), s1 = Math.min(fim, a + dash[0]);
        if (s1 > s0) { arr.push(f1(s0 - pos), f1(s1 - s0)); pos = s1; } }
      arr.push(f1(len + 99)); ps[2].style.strokeDasharray = arr.join(' '); ps[2].setAttribute('opacity', fim > 0 ? 1 : 0);
      if (ponta) { const q = ps[0].getPointAtLength(Math.max(0, L)), q0 = ps[0].getPointAtLength(Math.max(0, L - 6)); IL.tf(ponta, q.x, q.y, K.clamp(p * 25), Math.atan2(q.y - q0.y, q.x - q0.x) * 180 / Math.PI); }
    };
    set(0); return { g, len, set, path: ps[0] };
  };

  // ── mãos (luvas arredondadas com contorno), em coordenadas locais apontando para +x ──
  // tipo: 'luva' (mão aberta/mitene) · 'punho' (segurando alça) · 'aponta' (indicador esticado)
  IL.mao = (x, y, ang, cor, o = {}) => {
    const s = o.s ?? 1, tipo = o.tipo ?? 'luva', k = IL.P.k, L = lw(o);
    let inner = '';
    if (tipo === 'punho') inner = IL.forma('M-4 -26 C24 -34 46 -26 48 -6 C50 16 34 30 10 28 C-8 27 -14 12 -12 -2 Z', cor, { lw: L }) +
      IL.linha('M22 -20 C34 -18 40 -10 40 -4 M24 -4 C34 -2 40 4 39 10 M20 11 C30 13 34 18 32 23', k, L * .8);
    else if (tipo === 'aponta') inner = IL.forma('M-6 -22 C14 -30 30 -24 34 -16 L70 -16 C80 -16 80 -4 70 -4 L40 -4 C46 6 42 22 22 26 C2 30 -12 18 -10 0 Z', cor, { lw: L }) +
      IL.forma('M8 -20 C2 -32 18 -42 26 -30 C30 -24 28 -18 24 -14', cor, { lw: L });
    else inner = IL.forma('M-8 -22 C10 -34 40 -30 48 -12 C56 6 44 26 20 27 C0 28 -14 16 -12 0 Z', cor, { lw: L }) +
      IL.forma('M14 -24 C10 -40 26 -48 34 -36 C38 -30 36 -24 32 -20', cor, { lw: L });
    return `<g transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(ang)}) scale(${s} ${o.espelho ? -s : s})">${inner}</g>`;
  };

  // ── boneco sem rosto: cabeça-círculo + bico, tronco-pílula, calça em Π, braços-tubo; opcional jaleco ──
  // coordenadas locais: (0,0) = topo do tronco no centro; unidade = cabeça de raio 40 (use s para escalar)
  // o: { x, y, s, dir (-1 olha p/ esquerda, 1 direita), pele, blusa, estampa:'zigue'|'rabisco'|null, corEstampa,
  //      cabelo:'curto'|'coque'|null, bico, jaleco:bool, maos (cor), calca }
  IL.boneco = (svg, o = {}) => {
    const P = IL.P, dir = o.dir ?? -1, k = P.k, L = o.lw ?? 4.5;
    const g = IL.add(svg, `<g class="il-boneco"></g>`), nivel = n => IL.add(g, `<g class="${n}"></g>`);
    const atras = nivel('atras'), corpo = nivel('corpo'), frente = nivel('frente');
    const larg = o.jaleco ? 84 : 122, alt = o.jaleco ? 150 : 142;
    // braço de trás (desenhado antes) e braço da frente (depois): cada um é um tubo + mão
    const bracos = {};
    const mkBraco = (lado, par) => { const gb = IL.add(par, `<g class="braco-${lado}">${IL.tubo('M0 0', o.jaleco ? 46 : 38, o.jaleco ? P.creme : (o.pele ?? P.azulc), { lw: L })}<g class="mao"></g></g>`);
      bracos[lado] = { g: gb, tubo: gb.querySelector('.tubo'), mao: gb.querySelector('.mao') }; };
    mkBraco('tras', atras);
    if (o.jaleco) IL.add(corpo, IL.forma(`M${-larg - 22} 34 C${-larg - 22} 6 ${-larg} -4 ${-larg + 26} -6 L${larg - 26} -6 C${larg} -4 ${larg + 22} 6 ${larg + 22} 34 L${larg + 34} 900 L${-larg - 34} 900 Z`, P.creme, { lw: L }));
    // calça em Π (preta chapada)
    const cy0 = o.jaleco ? 196 : 182, cw = o.jaleco ? 70 : 105;
    IL.add(corpo, `<path d="M${-cw} ${cy0 + 30} Q${-cw} ${cy0} ${-cw + 30} ${cy0} L${cw - 30} ${cy0} Q${cw} ${cy0} ${cw} ${cy0 + 30} L${cw - 4} 900 L22 900 L20 ${cy0 + 80} L-20 ${cy0 + 80} L-22 900 L${-cw + 4} 900 Z" fill="${o.calca ?? k}"/>`);
    // tronco
    const tr = IL.add(corpo, `<g class="tronco">${IL.pilula(-larg, 0, larg * 2, alt, o.blusa ?? P.rosa, { lw: L, r: o.jaleco ? 40 : alt / 2 })}</g>`);
    if (o.estampa) { const r = K.rng(o.seedEstampa ?? 4), ce = o.corEstampa ?? P.branco; let s = '';
      const cols = o.jaleco ? 3 : 4, rows = 3, pos = [];
      for (let a = 0; a < cols; a++) for (let b = 0; b < rows; b++) pos.push([-larg + (a + .5) * (larg * 2 / cols) + (r() - .5) * 26, (b + .5) * (alt / rows) + (r() - .5) * 22]);
      for (const [x, y] of pos) { const a = r() * 360;
        s += o.estampa === 'zigue' ? `<path d="M-14 6 L-4 -8 L4 6 L14 -8" transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(a)})" fill="none" stroke="${ce}" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="miter"/>`
          : `<path d="M-16 0 C-10 -12 -2 12 6 0 S16 -8 18 2" transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(a)})" fill="none" stroke="${ce}" stroke-width="3.6" stroke-linecap="round"/>`; }
      if (o.estampa === 'zigue') for (let i = 0; i < 2; i++) s += `<path d="M0 -7 L7 5 L-7 5Z" transform="translate(${f1(-larg + 40 + r() * (larg * 2 - 80))} ${f1(30 + r() * (alt - 60))}) rotate(${f1(r() * 360)})" fill="${ce}"/>`;
      const id = 'ilc' + (IL._id = (IL._id || 0) + 1);
      IL.add(tr, `<clipPath id="${id}"><rect x="${-larg}" y="0" width="${larg * 2}" height="${alt}" rx="${o.jaleco ? 40 : alt / 2}"/></clipPath>`);
      IL.add(tr, `<g clip-path="url(#${id})">${s}</g>`); }
    // lapelas do jaleco por cima do tronco e da calça
    if (o.jaleco) { IL.add(corpo, IL.forma(`M${-larg - 22} 34 C${-larg - 22} 6 ${-larg} -4 ${-larg + 26} -6 L${-larg + 52} -6 C${-larg + 64} 60 ${-56} 150 -40 300 L-34 900 L${-larg - 34} 900 Z`, P.creme, { lw: L }));
      IL.add(corpo, IL.forma(`M${larg + 22} 34 C${larg + 22} 6 ${larg} -4 ${larg - 26} -6 L${larg - 52} -6 C${larg - 64} 60 56 150 40 300 L34 900 L${larg + 34} 900 Z`, P.creme, { lw: L })); }
    // cabeça
    const hx = o.hx ?? 0, hy = -78, R = 40, cab = IL.add(corpo, `<g class="cabeca"></g>`);
    if (o.cabelo === 'coque') IL.add(cab, [[-dir * 26, -26, 22], [-dir * 6, -38, 20], [-dir * 34, -4, 18], [-dir * 16, -50, 15], [-dir * 40, -30, 15]].map(([a, b, rr]) => IL.circ(hx + a, hy + b, rr, k, { sem: true })).join(''));
    IL.add(cab, IL.circ(hx, hy, R, o.pele ?? P.azulc, { lw: L }));
    if (o.cabelo === 'curto') IL.add(cab, `<path d="M${hx - dir * 42} ${hy + 6} C${hx - dir * 46} ${hy - 34} ${hx - dir * 10} ${hy - 52} ${hx + dir * 18} ${hy - 40} C${hx + dir * 30} ${hy - 34} ${hx + dir * 34} ${hy - 26} ${hx + dir * 30} ${hy - 20} C${hx + dir * 4} ${hy - 26} ${hx - dir * 14} ${hy - 6} ${hx - dir * 18} ${hy + 22} Z" fill="${k}"/>`);
    IL.add(cab, `<path d="M${hx + dir * 34} ${hy + 6} L${hx + dir * 82} ${hy + 2} L${hx + dir * 36} ${hy + 20} Z" fill="${o.bico ?? P.rosa}"/>`);
    mkBraco('frente', frente);
    const B = { g, bracos, cab, tronco: tr, dir,
      // braço por pontos [ombro, cotovelo, pulso] em coordenadas locais; mão no pulso com ângulo e tipo
      braco: (lado, pts, m = {}) => { const b = bracos[lado]; IL.setTubo(b.tubo, IL.cm(pts));
        const [a, c] = [pts[pts.length - 2], pts[pts.length - 1]], ang = m.ang ?? Math.atan2(c[1] - a[1], c[0] - a[0]) * 180 / Math.PI;
        b.mao.innerHTML = m.sem ? '' : IL.mao(c[0], c[1], ang, m.cor ?? o.maos ?? P.azulm, { tipo: m.tipo, s: m.s ?? 1, espelho: m.espelho, lw: L }); },
      pos: (x, y, s = o.s ?? 1, r = 0) => IL.tf(g, x, y, s, r) };
    B.pos(o.x ?? 0, o.y ?? 0, o.s ?? 1);
    return B;
  };

  // ── objetos de explainer (strings SVG em coordenadas locais) ──
  // regador cinza chapado (sem contorno, como na referência), selo rosa com ícone; bico aponta para +x
  IL.regador = (o = {}) => { const P = IL.P, c = o.cor ?? P.cinza, e = o.escuro ?? P.cinzaE, cl = o.claro ?? P.cinzaC;
    return `<g class="il-regador">
      <path d="M-70 -78 C-70 -128 70 -128 70 -78" fill="none" stroke="${e}" stroke-width="13" stroke-linecap="round"/>
      <path d="M60 10 L200 -70 L206 -58 L74 44 Z" fill="${c}"/>
      <path d="M190 -92 L224 -40 L232 -46 L200 -98 Z" fill="${e}"/>
      <path d="M-82 -80 L82 -80 L72 86 C40 96 -40 96 -72 86 Z" fill="${c}"/>
      <path d="M-82 -80 L-64 -80 L-56 90 C-62 89 -67 88 -72 86 Z" fill="${cl}"/>
      <ellipse cx="0" cy="-80" rx="82" ry="17" fill="${e}"/><ellipse cx="0" cy="-80" rx="70" ry="11" fill="${cl}"/>
      <path d="M-82 -40 C-128 -40 -132 40 -78 46" fill="none" stroke="${e}" stroke-width="13" stroke-linecap="round"/>
      ${IL.circ(4, 12, 46, o.selo ?? P.rosa, { sem: true })}${o.icone ? IL.icone(o.icone, 4, 12, 1) : ''}</g>`; };
  // ícones pretos de traço (para selos): arvore, vento, gota, sol, reciclar
  IL.icone = (nome, x, y, s = 1, cor = IL.P.k) => { const L = 5.5; let d = '';
    if (nome === 'arvore') d = IL.linha('M0 26 L0 2 M0 12 L-10 2 M0 8 L9 -1', cor, L) + `<path d="M-20 4 C-32 2 -32 -16 -20 -18 C-22 -32 -4 -36 0 -26 C6 -36 24 -30 20 -16 C32 -14 30 6 18 4 Z" fill="none" stroke="${cor}" stroke-width="${L}" stroke-linejoin="round"/>`;
    else if (nome === 'vento') d = IL.linha('M-26 -12 L10 -12 C22 -12 22 -26 12 -26 C6 -26 4 -20 6 -18 M-26 0 L20 0 C34 0 34 18 22 18 C16 18 13 12 15 9 M-26 12 L0 12', cor, L);
    else if (nome === 'gota') d = `<path d="M0 -26 C10 -10 18 0 18 10 C18 22 -18 22 -18 10 C-18 0 -10 -10 0 -26Z" fill="none" stroke="${cor}" stroke-width="${L}" stroke-linejoin="round"/>`;
    else if (nome === 'sol') d = IL.circ(0, 0, 11, 'none', { cor, lw: L }) + IL.linha([0, 1, 2, 3, 4, 5, 6, 7].map(i => { const a = i * Math.PI / 4; return `M${f1(Math.cos(a) * 18)} ${f1(Math.sin(a) * 18)}L${f1(Math.cos(a) * 27)} ${f1(Math.sin(a) * 27)}`; }).join(''), cor, L);
    return `<g transform="translate(${f1(x)} ${f1(y)}) scale(${s})">${d}</g>`; };
  // lupa: aro rosa, lente azul-clara com olho, cabo amarelo
  IL.lupa = (o = {}) => { const P = IL.P; return `<g class="il-lupa">
      ${IL.pilula(-11, 40, 22, 74, P.amarelo, { r: 9 })}${IL.circ(0, 0, 50, P.rosa)}${IL.circ(0, 0, 34, P.azulc)}
      <path d="M-22 0 C-12 -14 12 -14 22 0 C12 14 -12 14 -22 0Z" fill="${P.branco}" stroke="${P.k}" stroke-width="4"/>${IL.circ(o.olhoX ?? 3, 0, 9, P.k, { sem: true })}
      <rect class="palpebra" x="-36" y="-36" width="72" height="0" fill="${P.azulc}"/></g>`; };
  // prancheta amarela com prendedor preto
  IL.prancheta = (o = {}) => { const P = IL.P; return `<g class="il-prancheta">${IL.forma('M-58 -78 L58 -78 L58 78 L-58 78 Z', P.amarelo)}<rect x="-24" y="-90" width="48" height="22" rx="6" fill="${P.k}"/>${IL.linha('M-34 -36 L30 -36 M-34 -12 L18 -12', P.k, 4)}</g>`; };
  // "!" preto torto (ferve)
  IL.exclamaD = (frame, seed = 1) => { const r = K.rng(seed * 100 + frame * 7), j = () => (r() - .5) * 4;
    return IL.poli([[-14 + j(), -64 + j()], [16 + j(), -60 + j()], [8 + j(), 6 + j()], [-8 + j(), 4 + j()]], true) + IL.poli([[-10 + j(), 18 + j()], [10 + j(), 18 + j()], [9 + j(), 38 + j()], [-11 + j(), 37 + j()]], true); };

  // ── banco de nuvens pretas (bolhas) com rótulo químico ──
  // devolve {g, puffs:[{el, x, y, r, rotulo?}]}; o.rotulo: texto (ex. 'H₂O'); o.fonte
  IL.puff = (g, x, y, r, o = {}) => { const el = IL.add(g, `<g transform="translate(${f1(x)} ${f1(y)})"><circle r="${f1(r)}" fill="${o.cor ?? IL.P.k}"/></g>`); return { el, x, y, r }; };
  IL.rotulo = (g, x, y, txt, o = {}) => IL.add(g, `<text x="${f1(x)}" y="${f1(y)}" transform="rotate(${f1(o.rot ?? 0)} ${f1(x)} ${f1(y)})" text-anchor="middle" dominant-baseline="central" fill="${o.cor ?? IL.P.creme}" style="font-family:'Archivo';font-stretch:125%;font-weight:900;font-size:${o.fs ?? 48}px">${txt}</text>`);

  // ── câmera/valor por chaves: [[t, v], [t, v, ease], …] — entre duas chaves interpola com o ease da 2ª ──
  IL.chaves = lista => t => { if (t <= lista[0][0]) return lista[0][1];
    for (let i = 1; i < lista.length; i++) { const [ta, va] = lista[i - 1], [tb, vb, e] = lista[i]; if (t < tb) return K.lerp(va, vb, K.ease(e ?? 'power2.inOut', K.seg(t, ta, tb))); }
    return lista[lista.length - 1][1]; };
  // curva de Bézier cúbica (caminho de varrida, de mão que entra em arco)
  IL.bezier3 = (a, b, c, d) => u => { const m = 1 - u; return [0, 1].map(k => m * m * m * a[k] + 3 * m * m * u * b[k] + 3 * m * u * u * c[k] + u * u * u * d[k]); };
  // título que cabe: mede o <span> interno (o bloco tem left/right 0) e devolve o font-size para a largura pedida
  IL.cabe = (el, largura, base = 100) => { el.style.fontSize = base + 'px'; const sp = el.querySelector('span') || el; return Math.floor(base * largura / sp.offsetWidth); };

  // ── banco de nuvens pretas com rótulo químico (a 3ª marca do estilo) ──
  // moldura (faixa no alto + colunas laterais, fica) + miolo (bolhas grandes sobre o título, é varrido).
  // o: { seed, w, h, topo (y da borda de baixo da faixa), lado (largura das colunas), fundoCol (y onde as colunas acabam),
  //      miolo: [[x, y, r], …], rotulo (HTML do texto), rotMold: [[x, y, giro], …], fs, cor }
  IL.H2O = 'H<tspan dy="12" font-size="30">2</tspan><tspan dy="-12">O</tspan>';
  IL.CO2 = 'CO<tspan dy="12" font-size="30">2</tspan>';
  IL.nuvens = (svg, o = {}) => {
    const W = o.w ?? VIDEO.w, topo = o.topo ?? 330, lado = o.lado ?? 104, fim = o.fundoCol ?? 1230, cor = o.cor ?? IL.P.k, rot = o.rotulo ?? IL.H2O;
    const nv = IL.add(svg, `<g></g>`), nvMi = IL.add(svg, `<g></g>`), rotMi = IL.add(svg, `<g></g>`), rotG = IL.add(svg, `<g></g>`);
    const r3 = K.rng(o.seed ?? 42), moldura = [], miolo = [];
    IL.add(nv, `<rect x="-40" y="-40" width="${W + 80}" height="${topo}" fill="${cor}"/><rect x="-40" y="-40" width="${lado}" height="${fim + 30}" fill="${cor}"/><rect x="${W - lado + 40}" y="-40" width="${lado}" height="${fim + 50}" fill="${cor}"/>`);
    for (let x = 90; x < W - 20; x += 92) moldura.push(IL.puff(nv, x + (r3() - .5) * 24, topo - 30 + (r3() - .5) * 36, 62 + r3() * 24, { cor }));
    for (let y = topo; y < fim; y += 84) { moldura.push(IL.puff(nv, lado - 40 + (r3() - .5) * 24, y, 50 + r3() * 18, { cor })); moldura.push(IL.puff(nv, W - lado + 40 + (r3() - .5) * 24, y + 30, 50 + r3() * 18, { cor })); }
    moldura.push(IL.puff(nv, 40, fim + 30, 86, { cor }), IL.puff(nv, W - 40, fim + 70, 92, { cor }), IL.puff(nv, 150, fim - 30, 60, { cor }), IL.puff(nv, W - 150, fim + 10, 64, { cor }));
    (o.miolo ?? IL.MIOLO).forEach(([x, y, r]) => miolo.push(IL.puff(nvMi, x, y, r * (o.escalaMiolo ?? 1.14), { cor })));
    const rotMold = (o.rotMold ?? IL.ROTMOLD).map(([x, y, a]) => IL.rotulo(rotG, x, y, rot, { rot: a, fs: x < 80 || x > W - 80 ? (o.fs ?? 46) * .74 : (o.fs ?? 46) }));
    miolo.forEach((m, i) => { if (i % 2 === 0 || i > 12) m.rot = IL.rotulo(m.lab = IL.add(rotMi, `<g></g>`), 0, 0, rot, { rot: (r3() - .5) * 26, fs: o.fs ?? 46 }); });
    const N = { moldura, miolo, rotMold, cx: W / 2,
      // varrida: caminho u→[x,y] (da mão), t0, duração; cada bolha do miolo é "pega" quando a copa/aro passa mais perto
      varrer: (caminho, t0, d, alcance = 260) => { N.caminho = caminho; N.t0 = t0; N.d = d;
        miolo.forEach(m => { let best = 1e9, bu = 0; for (let u = 0; u <= 1; u += .01) { const [x, y] = caminho(u), dd = Math.hypot(x - m.x, y - alcance - m.y); if (dd < best) { best = dd; bu = u; } }
          m.tPega = t0 + bu * d - .04 + (m.x > W / 2 ? .05 : 0); m.dir = m.x < W / 2 ? -1 : 1; }); },
      update: t => { const tq = IL.q(t, 12);
        moldura.forEach((m, i) => m.el.firstElementChild.setAttribute('r', (m.r * (1 + Math.sin(tq * 4 + i) * .035)).toFixed(1)));   // respiram em dois
        rotMold.forEach((r, i) => r.style.translate = `0 ${(Math.sin(tq * 3 + i) * 4).toFixed(1)}px`);
        miolo.forEach((m, i) => { const v = m.tPega === undefined ? -1 : t - m.tPega; let x = m.x, y = m.y, s = 1 + Math.sin(tq * 4 + i) * .03;
          if (v > 0) { s = K.lerp(1, .16, IL.E('power3.out', v, 0, .16)); x += m.dir * (60 + 320 * v); y += 2600 * v * v - 260 * v; }   // encolhe e cai como bolinha
          m.el.setAttribute('transform', `translate(${x.toFixed(1)} ${y.toFixed(1)}) scale(${s.toFixed(3)})`); IL.show(m.el, y < VIDEO.h + 180);
          if (m.lab) { m.lab.setAttribute('transform', m.el.getAttribute('transform')); IL.show(m.lab, y < VIDEO.h + 180); } }); } };
    return N;
  };
  IL.MIOLO = [[300, 430, 150], [520, 400, 140], [760, 440, 150], [240, 640, 160], [470, 640, 170], [720, 650, 165], [880, 560, 120], [300, 860, 165], [540, 880, 170], [790, 860, 160],
    [210, 1060, 140], [420, 1080, 150], [650, 1090, 155], [870, 1060, 140], [330, 1220, 120], [560, 1240, 130], [780, 1230, 120],
    [150, 470, 110], [930, 420, 110], [140, 830, 120], [940, 760, 120], [160, 1180, 110], [920, 1180, 110]];
  IL.ROTMOLD = [[90, 120, -12], [330, 90, 8], [560, 150, -6], [800, 100, 10], [1000, 190, -10], [50, 520, -14], [1030, 640, 12], [48, 900, 10], [1032, 1000, -12], [70, 1260, 8], [1030, 1300, -12], [220, 240, 6], [700, 250, -8]];
  // mão + ferramenta que varre, em coordenadas locais (mão na origem, ferramenta para cima, braço para baixo)
  IL.guardaChuva = (o = {}) => { const P = IL.P; return `<g class="il-guarda-chuva">
    ${IL.tubo('M60 700 L0 40', 70, o.braco ?? P.azulm, { lw: 5 })}${IL.tubo('M0 30 L0 -300', 9, P.creme, { lw: 4 })}
    ${IL.forma('M-200 -300 C-190 -440 190 -440 200 -300 C170 -330 140 -330 100 -300 C70 -330 30 -330 0 -300 C-30 -330 -70 -330 -100 -300 C-140 -330 -170 -330 -200 -300 Z', o.copa ?? P.azulc, { lw: 5 })}
    ${IL.linha('M0 -428 C-30 -400 -80 -340 -100 -300 M0 -428 C30 -400 80 -340 100 -300 M0 -428 L0 -300', P.k, 4)}${IL.linha('M0 -428 L0 -452', P.k, 9)}
    ${IL.linha('M0 30 L0 70 C0 100 -40 100 -40 70', P.k, 9)}${IL.mao(0, 20, -90, o.braco ?? P.azulm, { tipo: 'punho', s: 1.3, lw: 5 })}</g>`; };
  // rede de borboleta (a ferramenta da referência): cabo azul-claro, aro, malha branca quadriculada
  IL.rede = (o = {}) => { const P = IL.P, id = 'ilr' + (IL._id = (IL._id || 0) + 1); let malha = '';
    for (let i = -150; i <= 150; i += 26) malha += `M${i} -560 L${i} -240 M-150 ${-560 + (i + 150)} L150 ${-560 + (i + 150)} `;
    return `<g class="il-rede">${IL.tubo('M60 700 L0 40', 70, o.braco ?? P.azulm, { lw: 5 })}${IL.tubo('M0 40 L0 -250', 16, o.cabo ?? P.azulc, { lw: 4 })}
      <clipPath id="${id}"><path d="M-130 -300 C-170 -420 -120 -560 0 -560 C120 -560 170 -420 130 -300 C90 -230 -90 -230 -130 -300Z"/></clipPath>
      <path d="M-130 -300 C-170 -420 -120 -560 0 -560 C120 -560 170 -420 130 -300 C90 -230 -90 -230 -130 -300Z" fill="${P.branco}"/>
      <path d="${malha}" stroke="${P.k}" stroke-width="2.5" fill="none" clip-path="url(#${id})"/>
      <ellipse cx="0" cy="-300" rx="134" ry="44" fill="none" stroke="${P.k}" stroke-width="22"/><ellipse cx="0" cy="-300" rx="134" ry="44" fill="none" stroke="${o.cabo ?? P.azulc}" stroke-width="12"/>
      ${IL.mao(0, 20, -90, o.braco ?? P.azulm, { tipo: 'punho', s: 1.3, lw: 5 })}</g>`; };
  // anima a ferramenta ao longo do caminho (gira acompanhando a tangente)
  IL.varredor = (el, caminho, t0, d, o = {}) => onTick(t => { const u = IL.E(o.ease ?? 'power1.inOut', t, t0, t0 + d), [x, y] = caminho(u), [x2, y2] = caminho(Math.min(1, u + .01));
    IL.tf(el, x, y, o.s ?? 1.1, (Math.atan2(y2 - y, x2 - x) * 180 / Math.PI + 90) * (o.giro ?? .75)); IL.show(el, t > t0 && u < 1 && (!o.cena || o.cena(t))); });
  // chuva fina: traços azuis inclinados que caem de faixas de origem (x0,x1,y0,y1), a 15 qps
  IL.chuva = (g, o = {}) => { const gs = Array.from({ length: o.n ?? 46 }, (_, i) => { const r = K.rng(i * 13 + (o.seed ?? 5)), fx = o.faixas ?? [[120, 240, 1180, 1300], [840, 960, 1180, 1300], [120, 960, 330, 370]];
      const f = fx[Math.floor(r() * fx.length)]; return { x: K.lerp(f[0], f[1], r()), y0: K.lerp(f[2], f[3], r()), t0: (o.t0 ?? 0) + r() * (o.espalha ?? 1), v: 1500 + r() * 500, l: 26 + r() * 18 }; });
    return t => { let s = ''; for (const c of gs) { const v = IL.q(t, 15) - c.t0; if (v < 0) continue; const y = c.y0 + v * c.v; if (y > VIDEO.h + 40) continue;
      s += IL.linha(`M${c.x.toFixed(1)} ${y.toFixed(1)} l-6 ${c.l.toFixed(1)}`, o.cor ?? IL.P.azulc, o.lw ?? 6); } g.innerHTML = s; }; };

  // ── som (helpers) ──
  IL.somFoto = t => (cue('whoosh_in', t - .04, { gain: -9 }), cue('paper', t + .12, { gain: -8 }));
  IL.somPop = (t, f = 700, g = -10) => cue('pop', t, { f, gain: g });
})();
