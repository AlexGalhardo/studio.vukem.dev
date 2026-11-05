// laminas.js — estilo "lâminas de espécimes": coleção de museu folheada em ritmo de semicolcheia.
// Um exemplar recortado (vista dorsal, cabeça para cima) por vez, centrado pelo corpo, sobre creme
// liso, sem sombra, sem movimento: corte seco a cada 1/9 s. Etiqueta de coleção embaixo, discreta.
// Uso: <script>LIBS=['laminas.js']</script> antes do boot.js; dados de tools/especime.py (especimes.js).
(function () {
  const LA = (window.LA = {});
  LA.FUNDO = '#e9ecd9';        // creme-sálvia medido na referência (232,236,216 → e9ecd9 depois do H.264)
  LA.TINTA = '#2a2c22';        // texto principal (nanquim esverdeado)
  LA.APAGADO = '#7c7f6d';      // texto secundário
  LA.RITMO = 9;                // exemplares por segundo = semicolcheia a 135 bpm
  LA.GRUPOS = {
    besouros: { nome: 'Besouros', ordem: 'Coleoptera' },
    lepidopteros: { nome: 'Borboletas e mariposas', ordem: 'Lepidoptera' },
    borboletas: { nome: 'Borboletas', ordem: 'Lepidoptera' },
    mariposas: { nome: 'Mariposas', ordem: 'Lepidoptera' },
    cigarras: { nome: 'Cigarras', ordem: 'Hemiptera' },
    percevejos: { nome: 'Percevejos', ordem: 'Hemiptera' },
    abelhas: { nome: 'Abelhas e vespas', ordem: 'Hymenoptera' },
    libelulas: { nome: 'Libélulas', ordem: 'Odonata' },
    gafanhotos: { nome: 'Gafanhotos', ordem: 'Orthoptera' },
  };

  const css = `
  .la-palco{background:var(--la-fundo)}
  .la-col{position:absolute;inset:0}
  .la-col img{position:absolute;display:none;image-rendering:auto;user-select:none;filter:var(--la-realce,none)}
  .la-col img.on{display:block}
  .la-cab{position:absolute;left:0;right:0;display:flex;align-items:center;justify-content:center;gap:26px;
    font:500 23px/1 'Inter Tight',sans-serif;letter-spacing:.42em;text-transform:uppercase;color:var(--la-apagado)}
  .la-cab i{display:block;width:70px;height:1.5px;background:currentColor;opacity:.55}
  .la-cab span{margin-right:-.42em}
  .la-eti{position:absolute;left:0;right:0;text-align:center;color:var(--la-tinta)}
  .la-eti .g{font:500 23px/1 'Inter Tight',sans-serif;letter-spacing:.34em;text-transform:uppercase;color:var(--la-apagado)}
  .la-eti .g b{font-weight:500;color:var(--la-tinta)}
  .la-eti .n{font:italic 400 54px/1.1 'Libre Caslon Text',serif;margin-top:20px;white-space:nowrap}
  .la-eti .c{font:400 25px/1 'Courier Prime',monospace;margin-top:20px;color:var(--la-apagado);letter-spacing:.06em}
  .la-cred{position:absolute;left:60px;right:60px;text-align:center;font:400 15px/1.45 'Inter Tight',sans-serif;color:#8f927f}`;

  // Palco creme liso. Cores podem ser trocadas (fundo, tinta, apagado).
  LA.palco = (o = {}) => {
    const st = document.getElementById('stage');
    const fundo = o.fundo || LA.FUNDO;
    st.classList.add('la-palco');
    st.style.setProperty('--la-fundo', fundo);
    st.style.setProperty('--la-tinta', o.tinta || LA.TINTA);
    st.style.setProperty('--la-apagado', o.apagado || LA.APAGADO);
    if (!document.getElementById('la-css')) { const s = document.createElement('style'); s.id = 'la-css'; s.textContent = css; document.head.appendChild(s); }
    return st;
  };

  // Ordena a lista de exemplares por uma lista de ids (o que não estiver na ordem fica de fora).
  LA.ordenar = (lista, ids) => { const m = new Map(lista.map(e => [e.id, e])); return ids.map(i => { if (!m.has(i)) throw new Error('exemplar ausente: ' + i); return m.get(i); }); };

  // Coleção folheada: um <img> por exemplar, posicionado para o CENTRO DO CORPO (cx,cy) cair em (x,y).
  // o = {x, y, t0 (início), ritmo (por segundo), escala, pai, faixa:[topo, base]}
  // faixa: antena ou perna comprida nunca passa do topo/base (o exemplar desliza só o necessário).
  LA.colecao = (itens, o = {}) => {
    const x = o.x ?? 540, y = o.y ?? 880, esc = o.escala ?? 1, ritmo = o.ritmo ?? LA.RITMO, t0 = o.t0 ?? 0;
    const el = document.createElement('div'); el.className = 'la-col'; (o.pai || document.getElementById('stage')).appendChild(el);
    // realce: a referência tem cor de foto de catálogo "puxada" (saturação e contraste um pouco acima do natural)
    const re = o.realce === false ? null : Object.assign({ sat: 1.12, con: 1.04, luz: 1.0 }, o.realce || {});
    if (re) el.style.setProperty('--la-realce', `saturate(${re.sat}) contrast(${re.con}) brightness(${re.luz})`);
    const [fy0, fy1] = o.faixa || [-1e9, 1e9];
    const imgs = itens.map(e => {
      const im = new Image(); im.decoding = 'sync'; im.src = (o.base || '') + e.src; im.alt = e.nome;
      let top = y - e.cy * esc; const h = e.h * esc;
      if (h > fy1 - fy0) top = (fy0 + fy1 - h) / 2; else if (top < fy0) top = fy0; else if (top + h > fy1) top = fy1 - h;
      Object.assign(im.style, { left: (x - e.cx * esc) + 'px', top: top + 'px', width: (e.w * esc) + 'px', height: h + 'px' });
      el.appendChild(im); return im;
    });
    const n = itens.length;
    const C = {
      el, imgs, itens, n, ritmo, t0, dur: n / ritmo,
      // índice do exemplar no instante t (laço: depois do último volta ao primeiro)
      idx: t => { const k = Math.floor((t - t0) * ritmo + 1e-6); return o.laco === false ? Math.max(0, Math.min(n - 1, k)) : ((k % n) + n) % n; },
      tempo: k => t0 + k / ritmo,
      pronto: () => Promise.all(imgs.map(im => im.decode().catch(() => { throw new Error('não carregou ' + im.src); }))),
    };
    let atual = -1;
    onTick(t => {
      const k = t < t0 ? -1 : C.idx(t);
      if (k === atual) return;
      if (atual >= 0) imgs[atual].classList.remove('on');
      if (k >= 0) imgs[k].classList.add('on');
      atual = k; if (C.aoTrocar) C.aoTrocar(k, t);
    });
    return C;
  };

  // Cabeçalho pequeno em versal espaçada, com fios dos dois lados.
  LA.cabecalho = (txt, o = {}) => {
    const d = document.createElement('div'); d.className = 'la-cab'; d.style.top = (o.y ?? 150) + 'px';
    d.innerHTML = `<i></i><span>${txt}</span><i></i>`; document.getElementById('stage').appendChild(d); return d;
  };

  // Etiqueta de coleção: GRUPO · ORDEM / nome científico em itálico / nº do exemplar (datilografado).
  LA.etiqueta = (col, o = {}) => {
    const d = document.createElement('div'); d.className = 'la-eti'; d.style.top = (o.y ?? 1500) + 'px';
    d.innerHTML = `<div class="g"></div><div class="n"></div><div class="c"></div>`; document.getElementById('stage').appendChild(d);
    const [g, nm, c] = d.children, tot = String(col.n).padStart(3, '0'), grupos = Object.assign({}, LA.GRUPOS, o.grupos || {});
    const maxW = o.largura ?? 960;
    const set = k => {
      const e = col.itens[k], G = grupos[e.g] || { nome: e.g, ordem: '' };
      g.innerHTML = `<b>${G.nome}</b>${G.ordem ? ' · ' + G.ordem : ''}`;
      nm.textContent = e.nome; nm.style.fontSize = '';
      if (nm.scrollWidth > maxW) nm.style.fontSize = (54 * maxW / nm.scrollWidth).toFixed(1) + 'px';   // nome comprido encolhe
      c.textContent = (o.prefixo ?? 'nº ') + String(k + 1).padStart(3, '0') + ' / ' + tot;
    };
    const prev = col.aoTrocar; col.aoTrocar = (k, t) => { prev && prev(k, t); if (k >= 0) set(k); };
    return d;
  };

  // Linha de créditos das fotos (obrigatória para CC BY / BY-SA), pequena no rodapé.
  LA.creditos = (txt, o = {}) => {
    const d = document.createElement('div'); d.className = 'la-cred'; d.style.top = (o.y ?? 1822) + 'px';
    // cada "Autor (licença)" fica inteiro na mesma linha: a quebra só acontece entre créditos
    const partes = txt.split(' · ');
    partes.forEach((p, i) => { const sp = document.createElement('span'); sp.style.whiteSpace = 'nowrap'; sp.textContent = p + (i < partes.length - 1 ? ' ·' : ''); d.appendChild(sp); d.appendChild(document.createTextNode(' ')); });
    document.getElementById('stage').appendChild(d); return d;
  };

  // Som: 'flip' a cada troca (acento nos tempos), 'gaveta' quando muda o grupo, 'madeira' no início.
  LA.sons = (col, o = {}) => {
    const ac = o.acento ?? 4;
    for (let k = 0; k < col.n; k++) {
      const t = col.tempo(k), e = col.itens[k], ant = col.itens[(k - 1 + col.n) % col.n];
      if (k === 0) cue('madeira', t, { gain: o.ganhoMadeira ?? -2 });
      else if (e.g !== ant.g) cue('gaveta', Math.max(0, t - .3), { gain: o.ganhoGaveta ?? 0 });
      cue('flip', t, { gain: (k % ac === 0 ? 0 : -4) + (o.ganhoFlip ?? 0), pan: ((k * 7) % 5 - 2) * .06 });
    }
  };

  // Ordem que alterna cores (contraste máximo entre vizinhos), útil para montar a sequência.
  // cores = {id: [L,a,b]}; devolve ids.
  LA.alternar = (ids, cores, primeiro) => {
    const r = ids.slice(), s = [primeiro ?? r[0]]; r.splice(r.indexOf(s[0]), 1);
    const dist = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
    while (r.length) {
      const a = cores[s[s.length - 1]], b = cores[s[s.length - 2] ?? s[s.length - 1]];
      let best = 0, bv = -1; r.forEach((id, i) => { const v = dist(cores[id], a) + .5 * dist(cores[id], b); if (v > bv) { bv = v; best = i; } });
      s.push(r.splice(best, 1)[0]);
    }
    return s;
  };
})();
