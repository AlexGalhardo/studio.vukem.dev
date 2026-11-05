// numero.js — um número que conta até o valor, com rótulo e linha de apoio. Um dado por tela.
import { PARAMS_PALCO, montarPalco, montarChapeu, montarCredito, formatarNumero } from './_comum.js';

export const meta = {
  nome: 'numero',
  descricao: 'Um número grande que conta até o valor, com rótulo, apoio e crédito da fonte.',
  dur_padrao: 4,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    valor: { tipo: 'numero', obrigatorio: true, descricao: 'o valor final' },
    rotulo: { tipo: 'texto', obrigatorio: true, descricao: 'o que o número é (uma linha)' },
    apoio: { tipo: 'texto', padrao: null, descricao: 'linha curta de contexto abaixo do rótulo' },
    prefixo: { tipo: 'texto', padrao: '', descricao: 'ex.: "R$ "' },
    sufixo: { tipo: 'texto', padrao: '', descricao: 'ex.: "%" ou " mil"' },
    casas: { tipo: 'inteiro', padrao: 0, min: 0, max: 4, descricao: 'casas decimais' },
    de: { tipo: 'numero', padrao: 0, descricao: 'valor inicial da contagem' },
    cor: { tipo: 'cor', padrao: 'primaria', descricao: 'token do número' },
    alinhar: { tipo: 'opcao', opcoes: ['esquerda', 'centro'], padrao: 'centro' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;
  const centro = p.alinhar === 'centro';
  const alinhar = centro ? 'centro' : 'esquerda';

  const bloco = ctx.el('div', 'mc-numero');
  Object.assign(bloco.style, {
    position: 'absolute', left: '0', width: base.area.w + 'px', display: 'flex', flexDirection: 'column',
    alignItems: centro ? 'center' : 'flex-start', gap: ctx.px(0.018) + 'px',
  });
  base.conteudo.appendChild(bloco);

  const chapeu = montarChapeu(ctx, bloco, p.chapeu);
  const fmt = { casas: p.casas || 0, prefixo: p.prefixo || '', sufixo: p.sufixo || '' };
  const cheio = formatarNumero(p.valor, fmt);
  const numero = ctx.texto('dados', cheio, { tam: ctx.tam('display'), cor: p.cor, alinhar });
  bloco.appendChild(numero);
  ctx.ajustar_texto(numero, base.area.w, { min: ctx.tam('h2') });
  numero.style.width = base.area.w + 'px';
  numero._inner.style.display = 'block';
  numero._inner.style.textAlign = centro ? 'center' : 'left';

  const rotulo = ctx.texto('titulo', p.rotulo, { tam: ctx.tam('h3'), wrap: true, maxW: base.area.w, alinhar });
  bloco.appendChild(rotulo);
  ctx.ajustar_texto(rotulo, base.area.w, { min: ctx.minimo_legivel, maxLinhas: 3 });
  ctx.sem_orfa(rotulo, { min: ctx.minimo_legivel });

  let apoio = null;
  if (p.apoio) {
    apoio = ctx.texto('corpo', p.apoio, { tam: ctx.tam('corpo'), cor: 'texto_suave', wrap: true, maxW: base.area.w, alinhar });
    bloco.appendChild(apoio);
    ctx.ajustar_texto(apoio, base.area.w, { min: ctx.minimo_legivel, maxLinhas: 3 });
  }

  const h = bloco.offsetHeight;
  bloco.style.top = Math.round(Math.max(0, (base.area.h - h) / 2)) + 'px';

  const credito = montarCredito(ctx, palco, p);
  const dConta = Math.min(ctx.dur('longa') * 1.6, Math.max(ctx.dur('media'), base.inicio_saida - T0 - ctx.dur('curta')));
  const T = ctx.tl().add('chapeu', T0, ctx.dur('media'))
    .add('numero', T0 + ctx.escalonamento, dConta, { curva: 'suave', tipo: 'enfase' })
    .add('rotulo', T0 + ctx.escalonamento * 3, ctx.dur('media'))
    .add('apoio', T0 + ctx.escalonamento * 5, ctx.dur('media'))
    .add('credito', T0 + ctx.escalonamento * 5, ctx.dur('media'));

  Object.assign(S, { ctx, base, chapeu, numero, rotulo, apoio, credito, T, p, fmt });
  return { ...base.layout(), bloco: ctx.rectDe(bloco), numero: ctx.rectDe(numero), valor: p.valor, fim_entrada: +T.t1('numero').toFixed(3) };
}

export function seek(t) {
  const { ctx, base, chapeu, numero, rotulo, apoio, credito, T, p, fmt } = S;
  base.seek(t);
  if (chapeu) chapeu.seek(T.p(t, 'chapeu'), T.p(t, 'chapeu', 'suave'));
  const pn = T.p(t, 'numero');
  const de = p.de || 0;
  numero._inner.textContent = formatarNumero(de + (p.valor - de) * pn, fmt);
  ctx.entrada(numero, Math.min(1, ctx.lin(t, T.t0('numero'), ctx.dur('curta'))), 'fade');
  ctx.entrada(rotulo, T.p(t, 'rotulo'), ctx.DA.movimento.entrada_padrao);
  if (apoio) ctx.entrada(apoio, T.p(t, 'apoio'), 'fade');
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  return t >= S.T.t1('numero') + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  return S.base.ancoras().concat([{ t: +S.T.t0('numero').toFixed(3), nome: 'numero', tipo: 'enfase' }]);
}
