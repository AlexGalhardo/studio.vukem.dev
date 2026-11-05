// texto.js — frase datilografada com marca-texto: o texto aparece letra a letra e um trecho é grifado depois.
import { PARAMS_PALCO, montarPalco, montarChapeu, montarCredito, htmlComGrifo, prepararGrifo, limitar } from './_comum.js';

export const meta = {
  nome: 'texto',
  descricao: 'Frase datilografada na tipografia da DA, com um trecho grifado a marca-texto no fim.',
  dur_padrao: 5,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    texto: { tipo: 'texto', obrigatorio: true, descricao: 'a frase (até ~30 palavras; encolhe para caber)' },
    grifo: { tipo: 'lista', padrao: [], itens: { tipo: 'texto' }, descricao: 'trechos exatos da frase a marcar (acento e caixa não importam)' },
    papel: { tipo: 'opcao', opcoes: ['titulo', 'subtitulo', 'corpo'], padrao: 'corpo', descricao: 'papel tipográfico da frase' },
    escala: { tipo: 'opcao', opcoes: ['h1', 'h2', 'h3', 'corpo'], padrao: 'h2', descricao: 'degrau da escala da DA' },
    alinhar: { tipo: 'opcao', opcoes: ['esquerda', 'centro'], padrao: 'esquerda' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const centro = p.alinhar === 'centro';
  const T0 = base.t0_conteudo;

  const chapeu = montarChapeu(ctx, base.conteudo, p.chapeu);
  if (chapeu) Object.assign(chapeu.el.style, { position: 'absolute', left: '0', top: '0' });
  const alturaChapeu = chapeu ? chapeu.el.offsetHeight + ctx.px(0.03) : 0;

  const { html } = htmlComGrifo(ctx, p.texto, p.grifo);
  const frase = ctx.texto(p.papel, '', { tam: ctx.tam(p.escala), wrap: true, maxW: base.area.w, alinhar: p.alinhar, html });
  frase.style.position = 'absolute';
  base.conteudo.appendChild(frase);
  ctx.ajustar_texto(frase, base.area.w, { min: ctx.minimo_legivel, alturaMax: base.area.h - alturaChapeu, maxLinhas: ctx.orientacao === 'vertical' ? 8 : 5 });
  ctx.sem_orfa(frase, { min: ctx.minimo_legivel });
  const m = ctx.medir(frase);
  frase.style.left = Math.round(centro ? (base.area.w - m.w) / 2 : 0) + 'px';
  frase.style.top = Math.round(alturaChapeu + Math.max(0, (base.area.h - alturaChapeu - m.h) / 2)) + 'px';

  const grifo = prepararGrifo(ctx, frase);
  const credito = montarCredito(ctx, palco, p);

  // tempo: a digitação cresce com o texto, mas nunca invade a saída
  const sobra = Math.max(ctx.dur('curta'), base.inicio_saida - T0 - ctx.dur('media'));
  const dTexto = Math.min(sobra, ctx.dur('longa') * limitar(p.texto.length / 42, 1, 2.6));
  const tGrifo = Math.min(base.inicio_saida - ctx.dur('curta'), T0 + dTexto + ctx.escalonamento * 2);
  const T = ctx.tl().add('chapeu', T0, ctx.dur('media')).add('texto', T0 + ctx.escalonamento * 2, dTexto, { curva: 'linear', tipo: 'texto' })
    .add('grifo', tGrifo, ctx.dur('media'), { curva: 'enfase', tipo: 'enfase' }).add('credito', T0, ctx.dur('media'));

  Object.assign(S, { ctx, base, chapeu, frase, grifo, credito, T });
  return { ...base.layout(), frase: ctx.rectDe(frase), linhas: m.linhas, grifos: grifo.spans.length, fim_entrada: +T.t1('texto').toFixed(3) };
}

export function seek(t) {
  const { ctx, base, chapeu, frase, grifo, credito, T } = S;
  base.seek(t);
  if (chapeu) chapeu.seek(T.p(t, 'chapeu'), T.p(t, 'chapeu', 'suave'));
  ctx.entrada(frase, T.p(t, 'texto'), 'digita');
  grifo.seek(T.p(t, 'grifo'));
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  return t >= S.T.t1('grifo') + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  return S.base.ancoras().concat(S.T.ancoras().filter((a) => a.nome === 'texto' || a.nome === 'grifo'));
}
