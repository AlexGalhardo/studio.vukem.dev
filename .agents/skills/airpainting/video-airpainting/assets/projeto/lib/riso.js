// Kit do estilo "airpainting": objetos chapados com gradiente PONTILHADO de risografia sobre papel claro,
// profundidade de campo (objetos desfocados ao fundo), mão de cartoon com contorno de giz que ferve,
// selo violeta com letra laranja que troca de texto e infográfico de objetos empilhados.
// Depende de core.js e kit.js (K, onTick, cue, VIDEO). Tudo é função do tempo t: nada toca sozinho.
(function () {
  const RI = (window.RI = {});
  const f1 = (RI.f1 = v => +(+v).toFixed(1));

  // ── cores ──
  RI.PAPEL = '#f2efe9'; RI.TINTA = '#2a2440'; RI.CONTORNO = '#16121c';
  RI.SELO = { fundo: '#4a3df0', letra: '#ffb020' };
  // f: capa [claro, médio, mais escuro da base lisa, cor do pontilhado]; b: contracapa [claro, escuro, pontilhado]; deep: cor de texto/acento
  RI.CORES = {
    azul:  { f: ['#bdf3ee', '#a9e2f3', '#93b4f6', '#4a3ff0'], b: ['#8c84ff', '#5a4ff2', '#2f25c8'], deep: '#4a3ff0' },
    rosa:  { f: ['#f9c9e8', '#f3aedb', '#f08fb4', '#e8403f'], b: ['#ff8a96', '#ec4a55', '#b81f2e'], deep: '#e8403f' },
    ambar: { f: ['#ffeaa8', '#ffd98a', '#ffb466', '#ff5a24'], b: ['#ffa96a', '#f4692e', '#c8400c'], deep: '#f0561f' },
    verde: { f: ['#e2f8cf', '#c4efb6', '#93dcaa', '#0f9a5e'], b: ['#7fdba6', '#33b274', '#147a4a'], deep: '#0f8a54' },
    lilas: { f: ['#efe4ff', '#dccbff', '#b9a2ff', '#6a3df0'], b: ['#a993ff', '#7b5cf3', '#4b2cc0'], deep: '#6a3df0' },
    menta: { f: ['#dffbf6', '#b9f1ea', '#86dcd8', '#0a8f9a'], b: ['#7fd9d5', '#2fb2b4', '#0d7480'], deep: '#0a8090' },
  };
  // mãos: base lisa (2 cores) + sombra pontilhada + pontas dos dedos dobrados
  RI.MAOS = {
    amarela: { base: ['#ffe55a', '#ffc12e'], sombra: '#ff5a1e', ponta: '#ff6a2a' },
    rosa:    { base: ['#ffd6e4', '#ffb3cb'], sombra: '#e8405a', ponta: '#f0607a' },
    morena:  { base: ['#e6a77a', '#d08a5a'], sombra: '#8a3f22', ponta: '#a8522e' },
    azul:    { base: ['#bfe4ff', '#93c8ff'], sombra: '#3a3ff0', ponta: '#5a6af5' },
  };

  // ── utilidades de movimento ──
  RI.tf = (el, x, y, s = 1, r = 0, sy) => el.setAttribute('transform', `translate(${f1(x)} ${f1(y)}) rotate(${f1(r)}) scale(${(+s).toFixed(4)} ${(+(sy ?? s)).toFixed(4)})`);
  RI.show = (el, on) => el.setAttribute('display', on ? 'inline' : 'none');
  RI.E = (n, t, a, b) => K.ease(n, K.seg(t, a, b));
  const BO = gsap.parseEase('back.out(2)');
  RI.pop = (t, t0, d = .35) => t < t0 ? 0 : BO(K.seg(t, t0, t0 + d));
  RI.q = (t, qps = 12) => Math.floor(t * qps + 1e-6) / qps;       // tempo de stop-motion
  RI.passo = (t, lista, ini) => { let v = ini; for (const [a, x] of lista) if (t >= a) v = x; return v; };
  RI.bump = (t, tp, w = .07) => Math.max(0, 1 - Math.abs(t - tp) / w);  // pico triangular em tp

  // ── instalação: filtros, gradientes, estilos. Chame uma vez, no topo do script da página. ──
  let defs;
  RI.instalar = (o = {}) => {
    const st = K.$('#stage'); st.style.background = o.papel ?? RI.PAPEL;
    st.insertAdjacentHTML('afterbegin', `<svg width="0" height="0" style="position:absolute"><defs id="ri-defs">
      <filter id="ri-dither" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
       <feTurbulence type="fractalNoise" baseFrequency="${o.grao ?? .62}" numOctaves="2" seed="4" result="n"/>
       <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  2 0 0 0 -.5" result="na"/>
       <feComposite in="SourceAlpha" in2="na" operator="arithmetic" k1="0" k2="10" k3="-10" k4="0" result="m"/>
       <feComponentTransfer in="m" result="mb"><feFuncA type="discrete" tableValues="0 1"/></feComponentTransfer>
       <feComponentTransfer in="SourceGraphic" result="solid"><feFuncA type="discrete" tableValues="0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1"/></feComponentTransfer>
       <feComposite in="solid" in2="mb" operator="in"/></filter>
      <filter id="ri-rough" filterUnits="userSpaceOnUse" x="-800" y="-400" width="1600" height="1800"><feTurbulence id="ri-rturb" type="fractalNoise" baseFrequency=".09" numOctaves="2" seed="1" result="n"/>
       <feDisplacementMap in="SourceGraphic" in2="n" scale="${o.giz ?? 7}" xChannelSelector="R" yChannelSelector="G"/></filter>
    </defs></svg>`);
    defs = K.$('#ri-defs');
    const dg = (id, col, st) => `<linearGradient id="${id}" x1="1" y1="0" x2="0" y2="1">${st.map(([a, v]) => `<stop offset="${a}" stop-color="${col}" stop-opacity="${v}"/>`).join('')}</linearGradient>`;
    defs.insertAdjacentHTML('beforeend', Object.entries(RI.CORES).map(([k, c]) =>
      `<linearGradient id="ri-gf-${k}" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c.f[0]}"/><stop offset=".55" stop-color="${c.f[1]}"/><stop offset="1" stop-color="${c.f[2]}"/></linearGradient>${dg('ri-gdf-' + k, c.f[3], [[0, 0], [.28, 0], [.62, .5], [1, 1]])}
       <linearGradient id="ri-gb-${k}" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c.b[0]}"/><stop offset="1" stop-color="${c.b[1]}"/></linearGradient>${dg('ri-gdb-' + k, c.b[2], [[0, 0], [.4, .1], [1, .9]])}`).join('')
      + Object.entries(RI.MAOS).map(([k, m]) => `<linearGradient id="ri-gh-${k}" gradientUnits="userSpaceOnUse" x1="-300" y1="100" x2="160" y2="700"><stop offset="0" stop-color="${m.base[0]}"/><stop offset="1" stop-color="${m.base[1]}"/></linearGradient>
       <linearGradient id="ri-ghd-${k}" gradientUnits="userSpaceOnUse" x1="-260" y1="160" x2="200" y2="760"><stop offset="0" stop-color="${m.sombra}" stop-opacity="0"/><stop offset=".35" stop-color="${m.sombra}" stop-opacity=".05"/><stop offset=".75" stop-color="${m.sombra}" stop-opacity=".75"/><stop offset="1" stop-color="${m.sombra}" stop-opacity="1"/></linearGradient>`).join(''));
    document.head.insertAdjacentHTML('beforeend', `<style>
      .ri-full{position:absolute;left:0;top:0;width:${VIDEO.w}px;height:${VIDEO.h}px;overflow:visible}
      .ri-bg{position:absolute;overflow:visible}
      .ri-selo{position:absolute;background:${RI.SELO.fundo};border-radius:16px;display:grid;place-items:center;transform-origin:50% 60%}
      .ri-selo .tx{display:inline-block;font:800 44px/.92 'Unbounded';color:${RI.SELO.letra};text-align:center;letter-spacing:-.03em;white-space:nowrap}
      .ri-num{position:absolute;width:260px;text-align:center;font:800 64px/1 'Unbounded';letter-spacing:-.04em}
      .ri-nome{position:absolute;width:260px;text-align:center;font:600 38px/1 'Inter Tight';color:${RI.TINTA};letter-spacing:-.01em}
    </style>`);
    onTick(t => K.$('#ri-rturb').setAttribute('seed', 1 + Math.floor(t * 12 + 1e-6) % 9));   // contorno de giz ferve a 12 qps
  };
  let UID = 0;
  RI.defs = html => defs.insertAdjacentHTML('beforeend', html);
  RI.blur = () => { const id = 'ri-blur' + (++UID); RI.defs(`<filter id="${id}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="0"/></filter>`); return { id, el: K.$(`#${id} feGaussianBlur`) }; };

  // ── a técnica: base lisa + a mesma forma na cor escura, com opacidade em gradiente, passada pelo pontilhado ──
  RI.camada = (d, k, tipo = 'f', extra = '') => `<path d="${d}" fill="url(#ri-g${tipo}-${k})"${extra}/><path d="${d}" fill="url(#ri-gd${tipo}-${k})" filter="url(#ri-dither)"${extra}/>`;
  // formas prontas (centradas na base, origem em 0,0 = meio da base) para outros infográficos
  RI.ret = (w, h, r = 18) => `M${-w / 2 + r} ${-h}H${w / 2 - r}Q${w / 2} ${-h} ${w / 2} ${-h + r}V${-r}Q${w / 2} 0 ${w / 2 - r} 0H${-w / 2 + r}Q${-w / 2} 0 ${-w / 2} ${-r}V${-h + r}Q${-w / 2} ${-h} ${-w / 2 + r} ${-h}Z`;
  RI.circ = r => `M${-r} ${-r}A${r} ${r} 0 1 0 ${r} ${-r}A${r} ${r} 0 1 0 ${-r} ${-r}Z`;   // círculo apoiado na base (centro em 0,-r)
  RI.cartao = (k, w = 260, h = 170, r = 22) => RI.camada(RI.ret(w, h, r), k);
  RI.bola = (k, r = 90) => RI.camada(RI.circ(r), k);
  RI.folha = (w = 220, h = 290, linhas = 6) => `<path d="${RI.ret(w, h, 10)}" fill="#fbfaf7"/>` + Array.from({ length: linhas }, (_, i) => `<rect x="${-w / 2 + 28}" y="${-h + 50 + i * 34}" width="${(w - 56) * (i === linhas - 1 ? .55 : 1)}" height="10" rx="5" fill="#d9d5e6"/>`).join('');

  // qualquer forma "pintável": uma variante por cor; cada cor nova é revelada por um círculo que cresce a partir de o.origem
  // devolve pintar(i, raio) para i ≥ 1. (A pasta grande usa a mesma ideia na capa e na contracapa.)
  RI.pintavel = (g, d, cores, o = {}) => { const [ox, oy] = o.origem ?? [0, 0], id = 'ri-v' + (++UID), tipo = o.tipo ?? 'f';
    RI.defs(cores.slice(1).map((_, i) => `<clipPath id="${id}-c${i + 1}"><circle cx="${ox}" cy="${oy}" r="0"/></clipPath>`).join(''));
    g.insertAdjacentHTML('beforeend', cores.map((k, i) => `<g${i ? ` clip-path="url(#${id}-c${i})"` : ''}>${RI.camada(d, k, tipo)}</g>`).join(''));
    const circ = cores.slice(1).map((_, i) => K.$(`#${id}-c${i + 1} circle`));
    return (i, r) => circ[i - 1].setAttribute('r', f1(r)); };

  // pasta pequena fechada (fundo e infográfico)
  RI.mini = (k, w = 230, h = 170) => { const fr = `M${-w / 2} 0L${-w / 2} ${-h}L${-w * .3} ${-h}C${-w * .22} ${-h} ${-w * .2} ${-h + 12} ${-w * .12} ${-h + 12}L${w / 2} ${-h + 12}L${w / 2} 0Z`;
    return `<path d="M${-w / 2 + 8} -4L${-w / 2 + 8} ${-h + 10}L${-w * .18} ${-h + 10}L${-w * .14} ${-h - 6}L${w * .1} ${-h - 6}L${w * .14} ${-h + 10}L${w / 2 + 8} ${-h + 10}L${w / 2 + 8} -4Z" fill="url(#ri-gb-${k})"/><path d="${fr}" fill="url(#ri-gf-${k})"/><path d="${fr}" fill="url(#ri-gdf-${k})" filter="url(#ri-dither)"/>`; };

  // ── pasta grande que abre, recebe papéis e é "pintada" (cada cor nova se espalha num círculo a partir de um ponto) ──
  // o: { cores: ['azul','rosa',...], w: 700, h: 560, origem: [x,y] (local, ponto de onde a tinta se espalha) }
  RI.pasta = (g, o = {}) => { const W2 = (o.w ?? 700) / 2, H = o.h ?? 560, cores = o.cores ?? ['azul'], [ox, oy] = o.origem ?? [180, 100], id = 'ri-p' + (++UID);
    const FRONT = `M${-W2} 0L${-W2} ${-H}L${-W2 + 255} ${-H}C${-W2 + 280} ${-H} ${-W2 + 288} ${-H + 34} ${-W2 + 310} ${-H + 34}L${W2} ${-H + 34}L${W2} 0Z`;
    const BACK = `M${-W2 + 30} -6L${-W2 + 30} ${-H + 30}L${-W2 + 200} ${-H + 30}L${-W2 + 220} ${-H - 8}C${-W2 + 226} ${-H - 22} ${-W2 + 234} ${-H - 26} ${-W2 + 250} ${-H - 26}L${-W2 + 390} ${-H - 26}C${-W2 + 408} ${-H - 26} ${-W2 + 414} ${-H - 18} ${-W2 + 418} ${-H - 4}L${-W2 + 430} ${-H + 30}L${W2 + 26} ${-H + 30}L${W2 + 26} -6Z`;
    const PAPER = (dx, r, ticks) => `<g transform="translate(${dx} 0) rotate(${r})"><path d="M${-W2 + 50} -10L${-W2 + 50} ${-H + 10}L${W2 + 6} ${-H + 18}L${W2 + 6} -10Z" fill="#fbfaf7"/><path d="M${-W2 + 50} ${-H + 10}L${W2 + 6} ${-H + 18}L${W2 + 6} ${-H + 30}L${-W2 + 50} ${-H + 22}Z" fill="#e6e3ef"/>${ticks ? Array.from({ length: 7 }, (_, i) => `<rect x="${-120 + i * 34}" y="${-H + 2}" width="5" height="22" fill="${RI.TINTA}"/>`).join('') : ''}</g>`;
    RI.defs(cores.slice(1).map((_, i) => `<clipPath id="${id}-c${i + 1}"><circle cx="${ox}" cy="${oy}" r="0"/></clipPath>`).join(''));
    const vari = (d, tipo) => cores.map((k, i) => `<g${i ? ` clip-path="url(#${id}-c${i})"` : ''}>${RI.camada(d, k, tipo)}</g>`).join('');
    g.innerHTML = `<g class="pb">${vari(BACK, 'b')}</g><g class="pp">${PAPER(0, .6, 0)}<g class="pi">${PAPER(-6, -.8, 1)}${PAPER(8, 1.4, 1)}</g></g><g class="pf">${vari(FRONT, 'f')}</g>`;
    const [pb, pp, pi, pf] = ['.pb', '.pp', '.pi', '.pf'].map(s => K.$(s, g)), circ = cores.slice(1).map((_, i) => K.$(`#${id}-c${i + 1} circle`)), bl = RI.blur();
    return {
      pos: (x, y, s = 1, r = 0) => RI.tf(g, x, y, s, r),
      abrir: op => { pf.setAttribute('transform', `skewX(${f1(9 * op)}) scale(1 ${(1 - .05 * op).toFixed(4)})`); pb.setAttribute('transform', `skewX(${f1(-4 * op)})`); pp.setAttribute('transform', `skewX(${f1(2 * op)})`); },
      papeis: u => { RI.show(pi, u > 0); pi.setAttribute('transform', `translate(0 ${f1(-420 * (1 - K.ease('bounce.out', u)))})`); },  // u: 0 (fora) → 1 (dentro)
      pintar: (i, r) => circ[i - 1].setAttribute('r', f1(r)),        // i ≥ 1: raio da cor i
      foco: px => { if (px > .3) { g.setAttribute('filter', `url(#${bl.id})`); bl.el.setAttribute('stdDeviation', f1(px)); } else g.removeAttribute('filter'); },
    }; };

  // ── mão de cartoon apontando: ponta do dedo em (0,0), punho para baixo (sai da tela) ──
  RI.mao = (g, o = {}) => { const k = o.pele ?? 'amarela', m = RI.MAOS[k], C = RI.CONTORNO, id = 'ri-hm' + (++UID);
    const HS = mode => { const ex = mode === 1 ? 18 : 0, c = mode === 1 ? C : mode === 2 ? '#fff' : `url(#ri-gh-${k})`, st = mode === 1 ? ` stroke="${c}" stroke-width="18" stroke-linejoin="round"` : '';
      const cap = (x1, y1, x2, y2, w) => `<path d="M${x1} ${y1}L${x2} ${y2}" stroke="${c}" stroke-width="${w + ex}" stroke-linecap="round" fill="none"/>`;
      return cap(0, 52, 2, 300, 122) + `<ellipse cx="-55" cy="445" rx="220" ry="195" fill="${c}"${st}/>` + cap(-140, 352, -350, 372, 104) + `<path d="M-200 520L140 520L170 980L-230 980Z" fill="${c}"${st}/>`; };
    const CU = mode => { const ex = mode === 1 ? 14 : 0, c = mode === 1 ? C : `url(#ri-gh-${k})`, cap = (x1, y1, x2, y2, w) => `<path d="M${x1} ${y1}L${x2} ${y2}" stroke="${c}" stroke-width="${w + ex}" stroke-linecap="round" fill="none"/>`;
      return [cap(-178, 402, -10, 396, 98), cap(-168, 496, -22, 494, 94), cap(-140, 586, -40, 590, 86)]; };
    RI.defs(`<mask id="${id}" maskUnits="userSpaceOnUse" x="-500" y="-100" width="900" height="1200"><g>${HS(2)}</g></mask>`);
    g.innerHTML = `<g filter="url(#ri-rough)">${HS(1)}</g>${HS(0)}<rect x="-500" y="-60" width="900" height="1100" fill="url(#ri-ghd-${k})" filter="url(#ri-dither)" mask="url(#${id})"/>
      ${CU(0).map((f, i) => `<g filter="url(#ri-rough)">${CU(1)[i]}</g>${f}`).join('')}
      <g filter="url(#ri-rough)"><ellipse cx="-206" cy="404" rx="36" ry="30" fill="${m.ponta}"/><ellipse cx="-198" cy="494" rx="32" ry="28" fill="${m.ponta}"/><ellipse cx="-168" cy="583" rx="28" ry="26" fill="${m.ponta}"/>
       <path d="M-46 250C-18 264 26 264 54 248" fill="none" stroke="${C}" stroke-width="9" stroke-linecap="round"/>
       <ellipse cx="6" cy="40" rx="38" ry="46" fill="${C}" transform="rotate(4 6 40)"/><ellipse cx="-372" cy="368" rx="26" ry="32" fill="${C}" transform="rotate(-70 -372 368)"/></g>`;
    return { pos: (x, y, r = 6, s = 1) => RI.tf(g, x, y, s, r), show: on => RI.show(g, on) }; };
  // deslocamento vertical de toque: levanta ~.3 s antes e afunda no instante do toque
  RI.toqueDy = (t, toques, alto = 38, fundo = 16) => toques.reduce((a, tp) => a - (t < tp ? alto * Math.sin(Math.PI * K.seg(t, tp - .3, tp)) : 0) + fundo * RI.bump(t, tp), 0);
  // anel que se abre no toque. toques: [{t, x, y, cor}]
  RI.aneis = (g, toques) => t => { g.innerHTML = toques.map(a => { const u = K.seg(t, a.t, a.t + .45); if (u <= 0 || u >= 1) return '';
    return `<circle cx="${a.x}" cy="${a.y}" r="${f1(20 + 150 * K.ease('expo.out', u))}" fill="none" stroke="${a.cor}" stroke-width="${f1(14 * (1 - u))}" opacity="${f1(1 - u)}"/>`; }).join(''); };

  // ── selo: troca de texto com um "flip" (achata e volta), balanço de stop-motion; pode alargar no fim para virar a marca ──
  // textos: [[t, 'linha<br>linha'], ...]; o: { x, y (centro), lado: 200, final: { t, w: 560, h: 160 } }
  RI.selo = (parent, textos, o = {}) => { const el = K.html(parent, `<div class="ri-selo"><div class="tx"></div></div>`), tx = K.$('.tx', el), L = o.lado ?? 200, fim = o.final, cx = o.x ?? VIDEO.w / 2, cy = o.y ?? 400;
    return t => { const si = textos.reduce((a, [ts], i) => t >= ts ? i : a, 0), last = fim && si === textos.length - 1;
      if (tx.__i !== si) { tx.innerHTML = textos[si][1]; tx.__i = si; tx.style.fontSize = '44px'; const mw = last ? fim.w - 90 : L - 36; tx.style.fontSize = f1(Math.min(last ? 80 : 50, 44 * mw / tx.offsetWidth)) + 'px'; }
      const flip = textos.slice(1).reduce((m, [ts]) => Math.min(m, Math.abs(Math.cos(Math.PI * K.seg(t, ts - .08, ts + .08)))), 1);
      const p = RI.pop(t, o.t0 ?? .15, .4), fin = fim ? RI.E('back.out(1.6)', t, fim.t, fim.t + .35) : 0, w = L + ((fim?.w ?? L) - L) * fin, h = L + ((fim?.h ?? L) - L) * fin;
      Object.assign(el.style, { width: f1(w) + 'px', height: f1(h) + 'px', left: f1(cx - w / 2) + 'px', top: f1(cy - h / 2) + 'px', display: p > .001 ? 'grid' : 'none',
        transform: `translateY(${f1(Math.sin(RI.q(t, 8) * 5) * 3)}px) rotate(${f1(Math.sin(RI.q(t, 8) * 7) * 3 * (1 - fin) - 2 * fin)}deg) scale(${p.toFixed(3)},${(p * Math.max(.15, flip)).toFixed(3)})` }); }; };

  // ── objetos desfocados ao fundo (profundidade de campo), um por cor; mostram a cor do estado atual ──
  // itens: [[x, y, escala, desfoque px, velocidade de deriva], ...]; desenho: k => svg string (padrão: RI.mini)
  RI.fundo = (parent, itens, o = {}) => { const cores = o.cores ?? Object.keys(RI.CORES), des = o.desenho ?? (k => RI.mini(k));
    parent.insertAdjacentHTML('beforeend', itens.map(([x, y, s, b]) => `<svg class="ri-bg" width="400" height="320" viewBox="-200 -250 400 320" style="left:${x - 200}px;top:${y - 160}px;filter:blur(${b}px)">${cores.map(k => `<g data-k="${k}">${des(k)}</g>`).join('')}</svg>`).join(''));
    const els = [...parent.querySelectorAll('.ri-bg')].slice(-itens.length);
    return (t, cor, alfa = 1) => els.forEach((s, i) => { const [, , sc, , v] = itens[i]; s.style.opacity = f1(alfa * (.75 + .25 * Math.sin(i)));
      s.style.transform = `translate(${f1(Math.sin(t * .7 * v + i) * 18)}px,${f1(-t * 22 * v)}px) scale(${sc}) rotate(${f1(Math.sin(i * 3) * 10)}deg)`;
      for (const g of s.children) g.setAttribute('display', g.dataset.k === cor ? 'inline' : 'none'); }); };

  // ── infográfico: barras feitas de objetos empilhados, número contando em cima e nome embaixo ──
  // colunas: [{k, n, x, v, nome}]; o: { base, passo, t0, tNum, desenho, sufixo }
  RI.pilhas = (g, parent, colunas, o = {}) => { const base = o.base ?? 1520, passo = o.passo ?? 62, t0 = o.t0 ?? 3.05, tn = o.tNum ?? t0 + .25, des = o.desenho ?? (k => RI.mini(k)), alt = o.alturaObj ?? 170;
    g.innerHTML = colunas.map((c, ci) => Array.from({ length: c.n }, (_, i) => `<g data-c="${ci}" data-i="${i}">${des(c.k)}</g>`).join('')).join('');
    parent.insertAdjacentHTML('beforeend', colunas.map((c, ci) => `<div class="ri-num" style="left:${c.x - 130}px;top:${base - c.n * passo - alt - 92}px;color:${RI.CORES[c.k].deep}">0</div><div class="ri-nome" style="left:${c.x - 130}px;top:${base + 34}px">${c.nome}</div>`).join(''));
    const objs = [...g.children], nums = [...parent.querySelectorAll('.ri-num')].slice(-colunas.length), noms = [...parent.querySelectorAll('.ri-nome')].slice(-colunas.length);
    const quando = (ci, i) => t0 + i * .085 + ci * .05;
    const tick = t => { RI.show(g, t >= t0 - .05);
      objs.forEach(e => { const ci = +e.dataset.c, i = +e.dataset.i, c = colunas[ci], a = quando(ci, i), u = K.seg(t, a, a + .32); RI.show(e, t >= a);
        const sq = Math.max(0, 1 - Math.abs(u - .36) / .12); RI.tf(e, c.x + Math.sin(i * 2.3 + ci) * 6, base - i * passo - 520 * (1 - K.ease('bounce.out', u)), 1 + .06 * sq, Math.sin(i * 1.7 + ci * 2) * 3, 1 - .1 * sq); });
      colunas.forEach((c, ci) => { const a = K.seg(t, tn + ci * .05, tn + .15 + ci * .05); nums[ci].style.opacity = noms[ci].style.opacity = f1(a);
        nums[ci].textContent = Math.round(c.v * RI.E('power3.out', t, tn, tn + .7)) + (o.sufixo ?? ''); nums[ci].style.transform = noms[ci].style.transform = `translateY(${f1(20 * (1 - a))}px)`; }); };
    tick.sons = () => colunas.forEach((c, ci) => { for (let i = 0; i < c.n; i++) cue('pop', quando(ci, i) + .12, { f: 380 + i * 80 + ci * 40, gain: -9 }); for (let k = 0; k < 6; k++) if (ci === 0) cue('tick', tn + .05 + k * .1, { gain: -2 }); });
    return tick; };

  // sons de um toque com pintura
  RI.somToque = (tp, i = 0) => { cue('click', tp, { gain: 2 }); cue('bubble', tp + .04, { gain: -2 }); cue('sparkle', tp + .06, { gain: -10 }); cue('pop', tp - .08, { f: 760 + i * 120, gain: -8 }); };
})();
