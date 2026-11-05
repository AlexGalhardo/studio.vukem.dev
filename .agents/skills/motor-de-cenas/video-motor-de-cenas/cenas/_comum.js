// _comum.js — peças compartilhadas pelas cenas do motor (tudo pelo ctx: nenhuma cor, fonte, curva ou duração literal).
//
// Padrão da casa (aprovado): POUCO EFEITO. Um movimento por vez, câmera calma (1,5% em toda a cena)
// e uma só troca grande — o cartão que vira tela cheia, ou o contrário. Motion denso é "espalhafatoso".
//
// O palco é igual em todas as cenas: um cartão (a zona segura com uma folga) sobre o fundo, o conteúdo
// SEMPRE na área livre da DA (zona segura menos a faixa da legenda). Nos modos `abre`/`fecha` só o
// cartão cresce ou encolhe: o conteúdo não se mexe, então nenhum texto reflui nem sai do quadro.

export const PARAMS_PALCO = {
  palco: {
    tipo: 'opcao', opcoes: ['cartao', 'cheia', 'abre', 'fecha'], padrao: 'cartao',
    descricao: 'cartao = painel na zona segura · cheia = tela cheia · abre = cartão que vira tela cheia · fecha = tela cheia que vira cartão',
  },
  camera: {
    tipo: 'opcao', opcoes: ['parada', 'aproxima', 'afasta'], padrao: 'aproxima',
    descricao: 'deriva lenta da câmera em toda a cena (1,5%); "parada" desliga',
  },
  chapeu: { tipo: 'texto', padrao: null, descricao: 'etiqueta curta no alto, na tarja da DA' },
  fonte: { tipo: 'texto', padrao: null, descricao: 'crédito da fonte (o prefixo da DA é posto pelo kit)' },
  plataforma: { tipo: 'plataforma', padrao: null, descricao: 'zona segura a respeitar (vertical: reels, tiktok, shorts, uniao)' },
  reservar_legenda: { tipo: 'booleano', padrao: null, descricao: 'deixa livre a faixa da legenda queimada; padrão: conforme legenda.reservar_em da DA' },
};

const DERIVA = 0.015;          // quanto a câmera anda em TODA a cena (fração) — calma de propósito

export const limitar = (v, a, b) => Math.max(a, Math.min(b, v));

/** Interpola dois retângulos {x, y, x1, y1}. */
function entreRects(a, b, p) {
  return { x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, x1: a.x1 + (b.x1 - a.x1) * p, y1: a.y1 + (b.y1 - a.y1) * p };
}

function porRect(el, r, raio) {
  el.style.left = r.x.toFixed(1) + 'px';
  el.style.top = r.y.toFixed(1) + 'px';
  el.style.width = Math.max(0, r.x1 - r.x).toFixed(1) + 'px';
  el.style.height = Math.max(0, r.y1 - r.y).toFixed(1) + 'px';
  el.style.borderRadius = Math.max(0, raio).toFixed(1) + 'px';
}

/**
 * Monta o palco da cena. Devolve { mundo, cartao, conteudo, area, T, t0_conteudo, inicio_saida, seek(t), layout(), ancoras() }.
 * `conteudo` é onde a cena pendura o que desenha; `area` é o retângulo dele em px do quadro.
 */
export function montarPalco(ctx, palco, p) {
  const livre = ctx.area_livre(p.plataforma || undefined, { legenda: p.reservar_legenda });
  const folga = ctx.px(0.03);
  const rCartao = {
    x: limitar(livre.x - folga, 0, ctx.L), y: limitar(livre.y - folga, 0, ctx.A),
    x1: limitar(livre.x1 + folga, 0, ctx.L), y1: limitar(livre.y1 + folga, 0, ctx.A),
  };
  const rCheia = { x: 0, y: 0, x1: ctx.L, y1: ctx.A };

  const grupo = ctx.el('div', 'mc-grupo');
  Object.assign(grupo.style, { position: 'absolute', inset: '0' });
  palco.appendChild(grupo);

  const mundo = ctx.el('div', 'mc-mundo');
  Object.assign(mundo.style, { position: 'absolute', inset: '0', transformOrigin: '50% 50%' });
  grupo.appendChild(mundo);

  const cartao = ctx.el('div', 'mc-cartao');
  Object.assign(cartao.style, {
    position: 'absolute', boxSizing: 'border-box', background: ctx.cor('superficie'),
    borderStyle: 'solid', borderWidth: Math.max(1, ctx.traco) + 'px', borderColor: ctx.alfa('primaria', 0.3),
  });
  mundo.appendChild(cartao);

  const conteudo = ctx.el('div', 'mc-conteudo');
  Object.assign(conteudo.style, { position: 'absolute', left: livre.x + 'px', top: livre.y + 'px', width: livre.w + 'px', height: livre.h + 'px' });
  mundo.appendChild(conteudo);

  const modo = p.palco || 'cartao';
  const dTroca = ctx.dur('longa');
  const tTroca = modo === 'fecha' ? ctx.duracao * 0.58 : ctx.duracao * 0.42;
  const T = ctx.tl().add('palco', 0, ctx.dur('media'), { curva: 'suave' });
  if (modo === 'abre' || modo === 'fecha') T.add('troca', tTroca, dTroca, { curva: 'suave', tipo: 'enfase' });
  const t0Conteudo = +(ctx.dur('curta')).toFixed(3);
  const inicioSaida = ctx.fim_saida();
  const deriva = p.camera === 'aproxima' ? DERIVA : p.camera === 'afasta' ? -DERIVA : 0;

  const estado = {
    mundo, cartao, conteudo, T, modo, tTroca, dTroca, inicioSaida, deriva,
    area: { x: livre.x, y: livre.y, w: livre.w, h: livre.h, x1: livre.x1, y1: livre.y1 },
    livre, rect_cartao: rCartao, rect_cheia: rCheia, t0_conteudo: t0Conteudo, inicio_saida: inicioSaida, grupo,

    seek(t) {
      // 1. câmera: deriva linear, sempre o mesmo valor para o mesmo t (função pura)
      const pc = ctx.lin(t, 0, Math.max(0.5, ctx.duracao));
      const esc = deriva >= 0 ? 1 + deriva * pc : 1 - deriva * (1 - pc);
      mundo.style.transform = `scale(${esc.toFixed(5)})`;
      // 2. geometria do cartão: cartão → tela cheia (ou o contrário) em uma troca só
      let q = modo === 'cheia' ? 1 : 0;
      if (modo === 'abre') q = ctx.prog(t, tTroca, dTroca, 'suave');
      else if (modo === 'fecha') q = 1 - ctx.prog(t, tTroca, dTroca, 'suave');
      const r = entreRects(rCartao, rCheia, q);
      porRect(cartao, r, ctx.raio * (1 - q));
      cartao.style.borderColor = ctx.alfa('primaria', 0.3 * (1 - q));
      // 3. entrada e saída do conjunto — o estado COMPLETO em todo t, inclusive na janela de saída:
      //    pular a entrada do cartão aqui deixa o cartão como o seek anterior o largou (cena impura)
      ctx.entrada(cartao, T.p(t, 'palco'), 'fade');
      if (t >= inicioSaida) ctx.saida(grupo, ctx.prog(t, inicioSaida, ctx.dur('curta'), 'saida'));
      else ctx.entrada(grupo, 1, 'fade');
    },

    layout() {
      return {
        palco: modo, camera: p.camera || 'parada',
        cartao: { x: +rCartao.x.toFixed(1), y: +rCartao.y.toFixed(1), w: +(rCartao.x1 - rCartao.x).toFixed(1), h: +(rCartao.y1 - rCartao.y).toFixed(1) },
        area: { x: livre.x, y: livre.y, w: livre.w, h: livre.h },
        reservou_legenda: !!livre.reservou, faixa_legenda: livre.faixa_legenda || null,
        troca: modo === 'abre' || modo === 'fecha' ? +tTroca.toFixed(3) : null,
        fim_entrada: +(t0Conteudo + ctx.dur('media')).toFixed(3), inicio_saida: +inicioSaida.toFixed(3),
      };
    },

    ancoras() {
      const a = [{ t: 0, nome: 'cena', tipo: 'entrada' }];
      if (modo === 'abre' || modo === 'fecha') a.push({ t: +tTroca.toFixed(3), nome: 'palco_' + modo, tipo: 'enfase' });
      return a;
    },
  };
  return estado;
}

/** Tarja (chapéu) do kit, pendurada em `destino`. Devolve null quando não há texto. */
export function montarChapeu(ctx, destino, texto) {
  if (!texto) return null;
  const t = ctx.kit.tarja(texto, { tam: Math.min(ctx.px(ctx.DA.graficos.tarja.tamanho), ctx.tam('h3')) });
  destino.appendChild(t.el);
  t.medir();
  return t;
}

/**
 * Crédito da fonte do kit (graficos.citacao_fonte), fora da câmera para não derivar com ela.
 * `sobre_midia`: o crédito cai em cima de foto ou footage — ganha um apoio no fundo da DA para continuar legível
 * (graficos.citacao_fonte não tem token de proteção, ao contrário do GC).
 */
export function montarCredito(ctx, palco, p, { sobre_midia = false } = {}) {
  if (!p.fonte) return null;
  const c = ctx.kit.credito(p.fonte, { plataforma: p.plataforma || undefined, reservar_legenda: p.reservar_legenda });
  if (sobre_midia) {
    Object.assign(c.el.style, {
      background: ctx.alfa('fundo', 0.78), padding: `${ctx.px(0.005).toFixed(1)}px ${ctx.px(0.009).toFixed(1)}px`,
      borderRadius: (ctx.raio * 0.3).toFixed(1) + 'px',
    });
  }
  palco.appendChild(c.el);
  c.posicionar();
  return c;
}

/** `<img>` de foto/captura: o único escape do auditor, sempre declarado. `url` já vem como file:// do motor. */
export function imagem(ctx, url, motivo = 'foto fornecida pelo projeto') {
  const img = ctx.el('img');
  img.setAttribute('data-da-livre', motivo);
  img.src = url;
  Object.assign(img.style, { display: 'block', width: '100%', height: '100%', objectFit: 'cover' });
  return img;
}

/** Espera as imagens decodificarem: sem isso a primeira amostra do auditor pega a foto em branco. */
export async function esperarImagens(raiz) {
  await Promise.all(Array.from(raiz.querySelectorAll('img')).map((i) => (i.decode ? i.decode().catch(() => null) : null)));
}

// ─────────────────────────────────────────────────────────────────── texto ──

/** Minúsculas sem acento, com o índice de cada caractere no texto original. */
export function normalizar(s) {
  let saida = '';
  const idx = [];
  const str = String(s || '');
  for (let i = 0; i < str.length; i++) {
    const c = str[i].normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    for (let k = 0; k < c.length; k++) { saida += c[k]; idx.push(i); }
  }
  return { texto: saida, idx };
}

/** Marcação do texto com <span class="mc-grifo"> nos trechos pedidos (sem cor na string: a cor vem depois, por token). */
export function htmlComGrifo(ctx, texto, grifos) {
  const n = normalizar(texto);
  const faixas = [];
  for (const g of grifos || []) {
    const alvo = normalizar(g).texto.trim();
    if (!alvo) continue;
    const i = n.texto.indexOf(alvo);
    if (i < 0) continue;
    faixas.push([n.idx[i], n.idx[i + alvo.length - 1] + 1]);
  }
  faixas.sort((a, b) => a[0] - b[0]);
  let html = '', pos = 0;
  for (const [a, b] of faixas) {
    if (a < pos) continue;
    html += ctx.esc(texto.slice(pos, a)) + `<span class="mc-grifo">${ctx.esc(texto.slice(a, b))}</span>`;
    pos = b;
  }
  html += ctx.esc(texto.slice(pos));
  return { html, grifou: faixas.length };
}

/**
 * Marca-texto da DA: uma faixa em `primaria` que corre POR BAIXO das letras, da esquerda para a direita.
 * Fica abaixo da linha de base de propósito — marca-texto por cima do glifo derruba o contraste do
 * próprio texto que ele quer destacar (medido: texto sobre primaria dá 1,3:1). Devolve { spans, seek(p) }.
 */
export function prepararGrifo(ctx, el, { cor = 'primaria' } = {}) {
  const spans = Array.from(el.querySelectorAll('.mc-grifo'));
  const faixa = ctx.alfa(cor, 0.92);
  for (const s of spans) {
    Object.assign(s.style, {
      backgroundImage: `linear-gradient(${faixa}, ${faixa})`, backgroundRepeat: 'no-repeat',
      backgroundPosition: '0 97%', backgroundSize: '0% 20%', boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone',
    });
  }
  return {
    spans,
    seek(p) {
      const q = ctx.clamp(p, 0, 1);
      for (const s of spans) s.style.backgroundSize = (q * 100).toFixed(1) + '% 20%';
    },
  };
}

/**
 * Carimbo: etiqueta inclinada com borda, que bate e assenta (um movimento só). Devolve { el, w, h, seek(p) }.
 * O `destino` precisa estar no DOM antes da chamada — a medida é feita aqui.
 */
export function montarCarimbo(ctx, destino, texto, { cor = 'negativo', inclinacao = -7, tam = null } = {}) {
  const el = ctx.texto('subtitulo', texto, { tam: tam ?? ctx.tam('h3'), cor });
  Object.assign(el.style, {
    position: 'absolute', boxSizing: 'content-box',
    padding: `${ctx.px(0.009).toFixed(1)}px ${ctx.px(0.018).toFixed(1)}px`,
    borderStyle: 'solid', borderWidth: Math.max(2, ctx.traco * 2).toFixed(1) + 'px', borderColor: ctx.alfa(cor, 0.9),
    borderRadius: (ctx.raio * 0.4).toFixed(1) + 'px', transformOrigin: '50% 50%',
  });
  destino.appendChild(el);
  ctx.medir(el);
  return {
    el, w: el.offsetWidth, h: el.offsetHeight,
    seek(p) {
      const q = ctx.clamp(p, 0, 1);
      const s = 1 + 0.45 * (1 - q) * (1 - q);
      el.style.opacity = q.toFixed(3);
      el.style.transform = `rotate(${inclinacao}deg) scale(${s.toFixed(4)})`;
    },
  };
}

/** Número no padrão pt-BR, sem depender de Intl (que o auditor vigia quando formata "agora"). */
export function formatarNumero(v, { casas = 0, prefixo = '', sufixo = '', milhar = '.', decimal = ',' } = {}) {
  const neg = v < 0;
  const partes = Math.abs(Number(v) || 0).toFixed(casas).split('.');
  const inteiro = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, milhar);
  return (neg ? '−' : '') + (prefixo || '') + inteiro + (partes[1] ? decimal + partes[1] : '') + (sufixo || '');
}

// ──────────────────────────────────────────────────────────────────── svg ──

/** <svg> do tamanho da caixa, para fios, linhas e marcas. */
export function svgDe(ctx, w, h) {
  const s = ctx.svg('svg', { width: String(Math.round(w)), height: String(Math.round(h)), viewBox: `0 0 ${Math.round(w)} ${Math.round(h)}` });
  Object.assign(s.style, { position: 'absolute', left: '0', top: '0', overflow: 'visible' });
  return s;
}

/** Linha que se desenha: devolve { el, seek(p) } (stroke-dashoffset é só estilo, continua puro em t). */
export function fio(ctx, svg, x0, y0, x1, y1, { cor = 'primaria', alfa = 0.8, largura = null, tracejado = false } = {}) {
  const L = Math.hypot(x1 - x0, y1 - y0) || 1;
  const w = largura ?? Math.max(1, ctx.traco);
  const el = ctx.svg('line', {
    x1: x0.toFixed(1), y1: y0.toFixed(1), x2: x1.toFixed(1), y2: y1.toFixed(1),
    stroke: ctx.alfa(cor, alfa), 'stroke-width': w.toFixed(2), 'stroke-linecap': 'round',
  });
  if (tracejado) el.setAttribute('stroke-dasharray', `${(w * 3).toFixed(1)} ${(w * 3).toFixed(1)}`);
  svg.appendChild(el);
  return {
    el,
    seek(p) {
      const q = ctx.clamp(p, 0, 1);
      if (!tracejado) {
        el.setAttribute('stroke-dasharray', `${L.toFixed(1)} ${L.toFixed(1)}`);
        el.setAttribute('stroke-dashoffset', (L * (1 - q)).toFixed(1));
      }
      el.style.opacity = q.toFixed(3);
    },
  };
}
