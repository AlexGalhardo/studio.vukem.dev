// documento.js — página de documento com trechos grifados e carimbo. Não imita a interface de nenhum produto.
import { PARAMS_PALCO, montarPalco, montarCredito, montarCarimbo, htmlComGrifo, prepararGrifo, limitar } from './_comum.js';

export const meta = {
  nome: 'documento',
  descricao: 'Página de documento: cabeçalho, linhas em monoespaçada, trecho grifado e carimbo.',
  dur_padrao: 6,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    linhas: { tipo: 'lista', obrigatorio: true, min: 1, max: 12, itens: { tipo: 'texto' }, descricao: 'as linhas do documento, na ordem' },
    titulo: { tipo: 'texto', padrao: null, descricao: 'cabeçalho do documento' },
    sub: { tipo: 'texto', padrao: null, descricao: 'linha de identificação (processo, data, origem)' },
    grifo: { tipo: 'lista', padrao: [], itens: { tipo: 'texto' }, descricao: 'trechos a marcar (procurados em todas as linhas)' },
    carimbo: { tipo: 'texto', padrao: null, descricao: 'texto do carimbo' },
    cor_carimbo: { tipo: 'cor', padrao: 'negativo' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;

  // a folha: um painel em `fundo` sobre o cartão em `superficie` (dois degraus da DA, nunca papel inventado)
  const folha = ctx.el('div', 'mc-folha');
  const padL = ctx.px(0.03), padT = ctx.px(0.028);
  Object.assign(folha.style, {
    position: 'absolute', left: '0', top: '0', width: base.area.w + 'px', height: base.area.h + 'px',
    boxSizing: 'border-box', background: ctx.cor('fundo'), borderRadius: (ctx.raio * 0.5).toFixed(1) + 'px',
    borderStyle: 'solid', borderWidth: Math.max(1, ctx.traco) + 'px', borderColor: ctx.alfa('texto_suave', 0.35),
    padding: `${padT.toFixed(1)}px ${padL.toFixed(1)}px`, overflow: 'hidden',
  });
  base.conteudo.appendChild(folha);
  const larguraUtil = base.area.w - padL * 2;

  const pilha = ctx.el('div', 'mc-pilha');
  Object.assign(pilha.style, { position: 'relative', display: 'flex', flexDirection: 'column', gap: ctx.px(0.012) + 'px' });
  folha.appendChild(pilha);

  let titulo = null, sub = null, regua = null;
  if (p.titulo) {
    titulo = ctx.texto('subtitulo', p.titulo, { tam: ctx.tam('h3'), wrap: true, maxW: larguraUtil });
    pilha.appendChild(titulo);
    ctx.ajustar_texto(titulo, larguraUtil, { min: ctx.minimo_legivel, maxLinhas: 2 });
  }
  if (p.sub) {
    sub = ctx.texto('dados', p.sub, { tam: ctx.tam('nota'), cor: 'texto_suave', wrap: true, maxW: larguraUtil });
    pilha.appendChild(sub);
    ctx.ajustar_texto(sub, larguraUtil, { min: ctx.minimo_legivel, maxLinhas: 2 });
  }
  if (titulo || sub) {
    regua = ctx.el('div', 'mc-regua');
    Object.assign(regua.style, { width: larguraUtil + 'px', height: Math.max(1, ctx.traco) + 'px', background: ctx.alfa('texto_suave', 0.45), transformOrigin: 'left center', margin: `${ctx.px(0.008).toFixed(1)}px 0` });
    pilha.appendChild(regua);
  }

  const alturaLinhas = Math.max(ctx.px(0.08), base.area.h - padT * 2 - pilha.offsetHeight);
  const tamLinha = limitar(alturaLinhas / (p.linhas.length * 1.9), ctx.minimo_legivel, ctx.tam('corpo'));
  const linhas = [];
  for (const texto of p.linhas) {
    const { html, grifou } = htmlComGrifo(ctx, texto, p.grifo);
    const el = ctx.texto('corpo', '', { tam: tamLinha, wrap: true, maxW: larguraUtil, html, cor: grifou ? 'texto' : 'texto_suave' });
    pilha.appendChild(el);
    ctx.ajustar_texto(el, larguraUtil, { min: ctx.minimo_legivel, maxLinhas: 3 });
    linhas.push({ el, grifo: prepararGrifo(ctx, el), temGrifo: grifou > 0 });
  }

  let carimbo = null, tCarimbo = null;
  if (p.carimbo) {
    carimbo = montarCarimbo(ctx, base.mundo, p.carimbo, { cor: p.cor_carimbo || 'negativo' });
    carimbo.el.style.left = Math.round(base.area.x1 - carimbo.w - ctx.px(0.02)) + 'px';
    carimbo.el.style.top = Math.round(base.area.y1 - carimbo.h - ctx.px(0.02)) + 'px';
  }

  const credito = montarCredito(ctx, palco, p);
  const e = ctx.escalonamento;
  const T = ctx.tl().add('folha', T0, ctx.dur('media'), { curva: 'suave' }).add('cabecalho', T0 + e * 2, ctx.dur('media'));
  const t1 = T0 + e * 3;
  const passo = Math.max(e, Math.min(e * 2.2, (base.inicio_saida - t1 - ctx.dur('longa')) / Math.max(1, linhas.length)));
  T.escalonar(linhas.map((_, i) => 'l' + i), t1, ctx.dur('curta'), { passo, tipo: 'texto' });
  const tGrifo = Math.min(base.inicio_saida - ctx.dur('media'), t1 + passo * linhas.length + ctx.dur('curta'));
  T.add('grifo', tGrifo, ctx.dur('media'), { curva: 'enfase', tipo: 'enfase' });
  tCarimbo = Math.min(base.inicio_saida - ctx.dur('curta'), tGrifo + ctx.dur('media'));
  if (carimbo) T.add('carimbo', tCarimbo, ctx.dur('curta'), { curva: 'enfase', tipo: 'enfase' });
  T.add('credito', t1, ctx.dur('media'));

  Object.assign(S, { ctx, base, folha, titulo, sub, regua, linhas, carimbo, credito, T, tGrifo, tCarimbo });
  return { ...base.layout(), folha: ctx.rectDe(folha), linhas: linhas.length, grifos: linhas.filter((l) => l.temGrifo).length, fim_entrada: +(tGrifo + ctx.dur('media')).toFixed(3) };
}

export function seek(t) {
  const { ctx, base, folha, titulo, sub, regua, linhas, carimbo, credito, T } = S;
  base.seek(t);
  ctx.entrada(folha, T.p(t, 'folha'), 'fade');
  const pc = T.p(t, 'cabecalho');
  if (titulo) ctx.entrada(titulo, pc, 'fade');
  if (sub) ctx.entrada(sub, pc, 'fade');
  if (regua) { regua.style.opacity = pc > 0 ? '1' : '0'; regua.style.transform = `scaleX(${pc.toFixed(4)})`; }
  linhas.forEach((l, i) => { ctx.entrada(l.el, T.p(t, 'l' + i), 'fade'); l.grifo.seek(T.p(t, 'grifo')); });
  if (carimbo) carimbo.seek(T.p(t, 'carimbo'));
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  const fim = S.carimbo ? S.tCarimbo + S.ctx.dur('curta') : S.tGrifo + S.ctx.dur('media');
  return t >= fim + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  const a = S.base.ancoras().concat([{ t: +S.tGrifo.toFixed(3), nome: 'grifo', tipo: 'enfase' }]);
  if (S.carimbo) a.push({ t: +S.tCarimbo.toFixed(3), nome: 'carimbo', tipo: 'enfase' });
  return a;
}
