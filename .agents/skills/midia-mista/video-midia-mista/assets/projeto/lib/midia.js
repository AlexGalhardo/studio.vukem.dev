// Kit do estilo "mídia mista": vídeo explicativo de colagem com FOTOS REAIS recortadas sobre texturas (papel cinza,
// tecido escuro, madeira, mesa de desenho), fita amarela rasgada com letra à mão, marcador (laço, seta, X de marca-texto,
// círculo vermelho), texto datilografado, chuva de adesivos, objeto explodido em 3D, caleidoscópio, foto em cartão com
// legenda e lousa final. Depende de core.js e kit.js (K, onTick, cue, VIDEO). Tudo é função do tempo t.
(function () {
  const M = (window.M = {});
  const f1 = (M.f1 = v => +(+v).toFixed(1));
  M.$ = s => K.$(s); M.$$ = s => K.$$(s); M.seg = K.seg; M.cl = K.clamp;
  M.E = (n, t, a, b) => K.ease(n, K.seg(t, a, b));
  const BO = gsap.parseEase('back.out(2.2)');
  M.pop = (t, t0, d = .3) => t < t0 ? 0 : BO(K.seg(t, t0, t0 + d));
  // degraus de stop-motion: 0 → 1 em n saltos dentro de d segundos
  M.steps = (t, t0, d, n) => t < t0 ? 0 : Math.min(1, Math.ceil(K.seg(t, t0, t0 + d) * n - 1e-6) / n);
  // "slap": peça batida na mesa — escala 1+k → 1 em 4 quadros (0 antes de t0)
  M.slap = (t, t0, k = .3) => t < t0 ? 0 : 1 + k * (1 - M.steps(t, t0, .2, 4));
  // mostra a cena #id só dentro de [a, b)
  M.vis = (id, a, b, t) => { const v = t >= a && t < b; K.$('#' + id).style.display = v ? 'block' : 'none'; return v; };
  M.digitar = (el, txt, t, t0, t1) => { el.textContent = txt.slice(0, Math.round(txt.length * K.seg(t, t0, t1))); };

  // ── estilos base (dimensões relativas ao VIDEO) ──
  document.head.insertAdjacentHTML('beforeend', `<style>
    #all{position:absolute;inset:0}
    .sc{position:absolute;inset:0;overflow:hidden;display:none}
    .cam{position:absolute;inset:0;transform-origin:50% 50%}
    .bgimg{position:absolute;left:-7.4%;top:-7.4%;width:114.8%;height:114.8%;max-width:none;object-fit:cover}
    .pic{position:absolute;display:block;max-width:none;transform-origin:50% 50%}
    .sh{filter:drop-shadow(12px 18px 12px rgba(20,8,0,.55))}
    .sh2{filter:drop-shadow(10px 16px 8px rgba(0,0,0,.75))}
    .stk{filter:drop-shadow(10px 0 0 #fff) drop-shadow(-10px 0 0 #fff) drop-shadow(0 10px 0 #fff) drop-shadow(0 -10px 0 #fff) drop-shadow(10px 16px 12px rgba(0,0,0,.45))}
    .tape{position:absolute;background:#f0cd1c;padding:12px 44px 18px 40px;font:700 62px/1 'Kalam';color:#fff;white-space:nowrap;text-shadow:0 2px 0 rgba(110,80,0,.35);transform-origin:50% 50%}
    .tag{position:absolute;background:#f7f6f2;padding:14px 34px 16px;font:700 54px/1 'Kalam';color:#1d1b1a;white-space:nowrap;box-shadow:6px 9px 14px rgba(0,0,0,.22);transform-origin:20% 50%}
    .hand{position:absolute;font:700 64px/1 'Kalam';color:#2a2826;white-space:nowrap}
    .ann{position:absolute;left:0;top:0;width:${VIDEO.w}px;height:${VIDEO.h}px;overflow:visible;pointer-events:none}
    .ann path{fill:none;stroke-linecap:round;stroke-linejoin:round;visibility:hidden}
    .vig{position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse 75% 62% at 50% 48%,transparent 50%,rgba(12,8,4,.46) 100%)}
    .ttl{position:absolute;font:italic 600 172px/1.1 'Playfair Display';color:#2e2c2a;white-space:nowrap;letter-spacing:-.012em}
    .ttl i{display:inline-block;width:8px;height:.87em;background:#e4c02a;margin-left:14px;vertical-align:-.08em}
  </style>`);

  // ── marcador: filtro de borda tremida (aplique filter="url(#mk)" no <svg class="ann">) ──
  M.marcador = (o = {}) => { K.$('#stage').insertAdjacentHTML('afterbegin', `<svg width="0" height="0" style="position:absolute"><filter id="mk" filterUnits="userSpaceOnUse" x="-300" y="-300" width="${VIDEO.w + 600}" height="${VIDEO.h + 600}"><feTurbulence id="mkt" type="fractalNoise" baseFrequency="${o.freq ?? .035}" numOctaves="2" seed="2" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="${o.forca ?? 5}" xChannelSelector="R" yChannelSelector="G"/></filter></svg>`);
    onTick(t => K.$('#mkt').setAttribute('seed', 2 + Math.floor(t * 12) % 4)); };
  // traço que se desenha: u de 0 a 1
  M.ink = (el, u) => { if (!el.__L) { el.__L = el.getTotalLength() + 4; el.style.strokeDasharray = el.__L; } el.style.strokeDashoffset = f1(el.__L * (1 - K.clamp(u))); el.style.visibility = u > 0 ? 'visible' : 'hidden'; };
  M.reink = el => { el.__L = 0; };   // chame depois de trocar o "d" de um path animado
  // curva aberta suave por pontos (Catmull-Rom)
  M.curva = p => { let d = `M${f1(p[0][0])} ${f1(p[0][1])}`; for (let i = 0; i < p.length - 1; i++) { const p0 = p[Math.max(0, i - 1)], p1 = p[i], p2 = p[i + 1], p3 = p[Math.min(p.length - 1, i + 2)];
    d += `C${f1(p1[0] + (p2[0] - p0[0]) / 6)} ${f1(p1[1] + (p2[1] - p0[1]) / 6)} ${f1(p2[0] - (p3[0] - p1[0]) / 6)} ${f1(p2[1] - (p3[1] - p1[1]) / 6)} ${f1(p2[0])} ${f1(p2[1])}`; } return d; };
  // laço feito à mão (passa um pouco do ponto de partida, como caneta de verdade)
  M.laco = (cx, cy, rx, ry, rot = 0, seed = 1) => { const r = K.rng(seed), p = [], a0 = -2.3 + r() * .5, c = Math.cos(rot * Math.PI / 180), s = Math.sin(rot * Math.PI / 180);
    for (let i = 0; i <= 30; i++) { const a = a0 + i / 30 * Math.PI * 2.18, k = 1 + (r() - .5) * .04 + i / 30 * .07, x = Math.cos(a) * rx * k, y = Math.sin(a) * ry * k; p.push([cx + x * c - y * s, cy + x * s + y * c]); }
    return M.curva(p); };
  // seta: haste curva por pontos + ponta (dois riscos) calculada pela direção final
  M.seta = (pts, tam = 36) => { const [a, b] = [pts[pts.length - 2], pts[pts.length - 1]], ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    const p1 = [b[0] - Math.cos(ang - .5) * tam, b[1] - Math.sin(ang - .5) * tam], p2 = [b[0] - Math.cos(ang + .5) * tam, b[1] - Math.sin(ang + .5) * tam];
    return { haste: M.curva(pts), ponta: `M${f1(p1[0])} ${f1(p1[1])}L${f1(b[0])} ${f1(b[1])}L${f1(p2[0])} ${f1(p2[1])}` }; };
  // fita/etiqueta rasgada: bordas esquerda e direita em zigue-zague (clip-path)
  M.rasgar = (el, seed, dente = 3) => { const r = K.rng(seed), L = [], R = []; for (let i = 0; i <= 10; i++) { L.push(`${f1(r() * dente)}% ${i * 10}%`); R.push(`${f1(100 - r() * dente)}% ${100 - i * 10}%`); } el.style.clipPath = `polygon(${[...L, ...R].join(',')})`; };
  M.rasgarTudo = () => { K.$$('.tape').forEach((e, i) => M.rasgar(e, 10 + i)); K.$$('.tag').forEach((e, i) => M.rasgar(e, 40 + i)); };
  // escreve letra a letra com cada letra levemente torta
  M.letras = (el, txt, n) => { el.innerHTML = [...txt].map((ch, i) => `<span style="display:inline-block;transform:translateY(${i % 2 ? 4 : -4}px) rotate(${i % 3 - 1}deg)${i >= n ? ';visibility:hidden' : ''}">${ch === ' ' ? '&nbsp;' : ch}</span>`).join(''); };

  // ── acabamento de filme: vinheta, grão e tremor de projetor (exige <div id="all"> envolvendo as cenas) ──
  M.acabamento = (o = {}) => { const all = K.$('#all'); all.insertAdjacentHTML('beforeend', '<div class="vig"></div>');
    K.grain(K.$('#stage'), { opacity: o.grao ?? .16, w: 360 });
    if (o.tremor !== false) onTick(t => { const r = K.rng(Math.floor(t * 15) + 11); all.style.transform = `translate(${f1((r() - .5) * 3)}px,${f1((r() - .5) * 3)}px)`; }); };

  // ── transições ──
  // chicote: as duas cenas andam juntas (a que sai e a que entra), com desfoque no meio. Devolve u (0→1) e o desfoque.
  M.chicote = (t, t0, t1) => { const u = M.E('power2.inOut', t, t0, t1); return { u, blur: u > .05 && u < .95 ? 10 * Math.sin(Math.PI * u) : 0 }; };
  M.filtroBlur = px => px > .2 ? `blur(${f1(px)}px)` : '';

  // ── texto datilografado com a câmera seguindo o cursor ──
  // o: { t0, passo (s por letra), x0 (onde a linha começa), xCursor (até onde o cursor anda antes de a linha rolar) }
  M.datilografia = (box, txt, o = {}) => { box.classList.add('ttl'); box.innerHTML = '<span></span><i></i>'; const sp = K.$('span', box), car = K.$('i', box), t0 = o.t0 ?? .1, pa = o.passo ?? .034, x0 = o.x0 ?? 110, xc = o.xCursor ?? 830; let W = [];
    box.style.left = x0 + 'px';
    return {
      medir: () => { const sc = box.closest('.sc'), d = sc && sc.style.display; if (sc) sc.style.display = 'block'; W = Array.from({ length: txt.length + 1 }, (_, i) => { sp.textContent = txt.slice(0, i); return sp.offsetWidth; }); if (sc) sc.style.display = d; },
      fim: t0 + txt.length * pa,
      cursorX: t => { const nf = K.clamp((t - t0) / pa, 0, txt.length), i = Math.floor(nf); return x0 + K.lerp(W[i], W[Math.min(txt.length, i + 1)], nf - i); },
      tick: t => { const n = K.clamp(Math.floor((t - t0) / pa + 1e-6) + 1, 0, txt.length), nf = K.clamp((t - t0) / pa, 0, txt.length), i = Math.floor(nf);
        sp.textContent = txt.slice(0, n); car.style.opacity = (n >= txt.length && Math.floor(t * 4) % 2) ? 0 : 1;
        const w = K.lerp(W[i], W[Math.min(txt.length, i + 1)], nf - i); box.style.transform = `translateX(${f1(Math.min(0, xc - (x0 + w)))}px)`; },
      sons: (g = -6) => { for (let i = 0; i < txt.length; i += 2) cue('key', t0 + i * pa, { gain: g }); },
    }; };

  // ── padrão de recortes repetidos em grade diagonal (brotam do centro para fora em stop-motion) ──
  // o: { imgs: [src...], t0, dur (espalhamento), altura, dx, dy, inclX, inclY, rot, cx, cy, sombra }
  M.padrao = (box, o) => { const r = K.rng(o.seed ?? 5), P = [], W = VIDEO.w, H = VIDEO.h, dx = o.dx ?? 250, dy = o.dy ?? 196, ix = o.inclX ?? 72, iy = o.inclY ?? -62, cx = o.cx ?? W * .44, cy = o.cy ?? H * .45;
    for (let row = -4; row < Math.ceil(H / dy) + 4; row++) for (let col = -4; col < Math.ceil(W / dx) + 3; col++) { const x = col * dx + row * ix + (r() - .5) * 30, y = row * dy + col * iy + (r() - .5) * 30;
      if (x < -240 || x > W + 120 || y < -320 || y > H + 140) continue; P.push({ x, y, k: Math.abs(row + col) % o.imgs.length, rot: (o.rot ?? -18) + (r() - .5) * 16, s: .8 + r() * .12, d: Math.hypot(x - cx, y - cy) }); }
    box.innerHTML = P.map(p => `<img class="pic ${o.sombra ?? 'sh2'}" src="${o.imgs[p.k]}" style="left:${f1(p.x)}px;top:${f1(p.y)}px;height:${o.altura ?? 270}px;display:none">`).join('');
    const els = [...box.children], t0 = o.t0 ?? 0, dur = o.dur ?? .35;
    return t => els.forEach((e, i) => { const p = P[i], a = t0 + p.d / 1500 * dur, s = M.steps(t, a, .12, 3); e.style.display = s > 0 ? 'block' : 'none'; e.style.transform = `rotate(${f1(p.rot)}deg) scale(${(p.s * s).toFixed(3)})`; }); };

  // ── chuva de adesivos (borda branca): brotam do centro para fora cobrindo a tela e depois voam para fora ──
  // o: { imgs, t0, tSaida, fim, linhas, colunas, w, centro: src (adesivo maior no meio) }
  M.adesivos = (box, o) => { const r = K.rng(o.seed ?? 9), S = [], W = VIDEO.w, H = VIDEO.h, cols = o.colunas ?? 4, rows = o.linhas ?? 8, cw = W / (cols - .4), rh = H / (rows - .9);
    for (let row = 0; row < rows; row++) for (let col = 0; col < cols; col++) { const x = col * cw - 60 + (row & 1) * cw * .45 + (r() - .5) * 80, y = row * rh - 120 + (r() - .5) * 70, w = (o.w ?? 330) + r() * 90;
      S.push({ x, y, w, src: o.imgs[Math.floor(r() * o.imgs.length)], rot: (r() - .5) * 50, d: Math.hypot(x + w / 2 - W / 2, y + w * .4 - H / 2), a: Math.atan2(y + w * .4 - H / 2, x + w / 2 - W / 2) }); }
    if (o.centro) S.push({ x: W / 2 - 210, y: H / 2 - 140, w: 420, src: o.centro, rot: -8, d: 0, a: 0 });
    box.innerHTML = S.map(s => `<img class="pic stk" src="${s.src}" style="left:${f1(s.x)}px;top:${f1(s.y)}px;width:${f1(s.w)}px;display:none">`).join('');
    const els = [...box.children], t0 = o.t0, ts = o.tSaida, fim = o.fim ?? ts + .26;
    return t => els.forEach((e, i) => { const s = S[i], a = t0 + s.d / 1100 * .3, out = M.E('expo.in', t, ts + s.d / 1100 * .08, fim), sc = t < a ? 0 : 1 + .25 * (1 - M.steps(t, a, .12, 3));
      e.style.display = sc > 0 && out < .99 ? 'block' : 'none';
      e.style.transform = `translate(${f1(Math.cos(s.a) * 1100 * out)}px,${f1(Math.sin(s.a) * 1100 * out)}px) rotate(${f1(s.rot + 30 * out)}deg) scale(${(sc * (1 - .3 * out)).toFixed(3)})`; }); };
  M.somAdesivos = (t0, n = 10) => { for (let k = 0; k < n; k++) cue('bubble', t0 + k * .034, { gain: -6 }); cue('pop', t0 + .02, { f: 520 }); };

  // ── caleidoscópio: 3×3 ladrilhos espelhados de uma foto que convergem para o ladrilho do meio ──
  // box: div vazia; url: imagem; pos: background-position. tick(t, t0, t1, zoomInterno)
  M.caleidoscopio = (box, url, pos = '50% 50%') => { const W = VIDEO.w, H = VIDEO.h; Object.assign(box.style, { position: 'absolute', left: W / 2 + 'px', top: H / 2 + 'px', width: 0, height: 0 });
    box.innerHTML = [0, 1, 2].flatMap(r => [0, 1, 2].map(c => `<div style="position:absolute;left:${(c - 1) * W - W / 2}px;top:${(r - 1) * H - H / 2}px;width:${W}px;height:${H}px;overflow:hidden;transform:scale(${c === 1 ? 1 : -1},${r === 1 ? 1 : -1})"><div class="kin" style="position:absolute;inset:0;background:url(${url}) ${pos}/cover"></div></div>`)).join('');
    const kins = K.$$('.kin', box);
    return (t, t0, t1, kin = 1) => { const on = t >= t0 - .001 && t < t1; box.style.display = on ? 'block' : 'none'; if (!on) return;
      const kz = M.E('power3.in', t, t0, t1); box.style.transform = `scale(${(1 / 3 + (2 / 3) * kz).toFixed(4)}) rotate(${f1(30 * (1 - M.E('power2.out', t, t0, t1)))}deg)`;
      kins.forEach(e => (e.style.transform = `scale(${kin.toFixed(4)})`)); }; };
  // posição de um ponto da foto (X,Y em px da imagem original) dentro de um quadro com background "cover" + zoom interno
  M.mapaCapa = (cw, ch, iw, ih, px = .5, py = .5, kin = 1) => { const s0 = Math.max(cw / iw, ch / ih);
    return (X, Y) => [cw / 2 + ((cw - iw * s0) * px + X * s0 - cw / 2) * kin, ch / 2 + ((ch - ih * s0) * py + Y * s0 - ch / 2) * kin]; };

  // ── objeto explodido em 3D (camadas que se separam em Z numa vista isométrica) ──
  // camadas: [{ src, w, h, z0, z1, css }], o: { x, y, rx (inclinação), rz0→rz1 (giro), perspectiva }
  M.explodido = (box, camadas, o = {}) => { Object.assign(box.style, { position: 'absolute', left: (o.x ?? VIDEO.w / 2) + 'px', top: (o.y ?? VIDEO.h * .52) + 'px', width: 0, height: 0, perspective: (o.perspectiva ?? 2400) + 'px' });
    box.innerHTML = `<div style="position:absolute;transform-style:preserve-3d">${camadas.map(c => `<img src="${c.src}" style="position:absolute;width:${c.w}px;left:${-c.w / 2}px;top:${-(c.h ?? c.w) / 2}px;max-width:none;${c.css ?? ''}">`).join('')}</div>`;
    const iso = box.firstChild, els = [...iso.children];
    return (t, ex, giro = 0, bob = 0) => { box.style.transform = `translateY(${f1(bob)}px)`; iso.style.transform = `rotateX(${o.rx ?? 56}deg) rotateZ(${f1((o.rz0 ?? -40) + ((o.rz1 ?? -30) - (o.rz0 ?? -40)) * giro)}deg)`;
      els.forEach((e, i) => (e.style.transform = `translateZ(${f1(camadas[i].z0 + (camadas[i].z1 - camadas[i].z0) * ex)}px)`)); }; };
})();
