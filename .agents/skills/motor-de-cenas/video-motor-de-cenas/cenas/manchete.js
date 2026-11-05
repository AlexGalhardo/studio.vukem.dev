// manchete.js — recorte de notícia: veículo, data, manchete e linha fina. Nada imita a interface de um site real.
import { PARAMS_PALCO, montarPalco, montarCredito, htmlComGrifo, prepararGrifo } from './_comum.js';

export const meta = {
  nome: 'manchete',
  descricao: 'Recorte de notícia: veículo, data, manchete grande e linha fina, com grifo opcional.',
  dur_padrao: 4.5,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    manchete: { tipo: 'texto', obrigatorio: true, descricao: 'o título da notícia' },
    veiculo: { tipo: 'texto', padrao: null, descricao: 'nome do veículo (vai na tarja)' },
    data: { tipo: 'texto', padrao: null, descricao: 'data como ela deve aparecer (ex.: "12 de março de 2024")' },
    linha_fina: { tipo: 'texto', padrao: null, descricao: 'subtítulo da notícia' },
    grifo: { tipo: 'lista', padrao: [], itens: { tipo: 'texto' }, descricao: 'trechos da manchete a marcar' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;

  const bloco = ctx.el('div', 'mc-manchete');
  Object.assign(bloco.style, {
    position: 'absolute', left: '0', width: base.area.w + 'px',
    display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: ctx.px(0.02) + 'px',
  });
  base.conteudo.appendChild(bloco);

  // cabeçalho: veículo na tarja + data em "dados"
  const cab = ctx.el('div', 'mc-cabecalho');
  Object.assign(cab.style, { display: 'flex', alignItems: 'center', gap: ctx.px(0.02) + 'px', width: base.area.w + 'px' });
  bloco.appendChild(cab);
  let tarja = null;
  if (p.veiculo) {
    tarja = ctx.kit.tarja(p.veiculo, { tam: Math.min(ctx.px(ctx.DA.graficos.tarja.tamanho), ctx.tam('h3')) });
    cab.appendChild(tarja.el);
    tarja.medir();
  }
  let data = null;
  if (p.data) {
    data = ctx.texto('dados', p.data, { tam: ctx.tam('nota'), cor: 'texto_suave' });
    cab.appendChild(data);
    ctx.medir(data);
  }

  const filete = ctx.el('div', 'mc-filete');
  Object.assign(filete.style, {
    width: base.area.w + 'px', height: Math.max(1, ctx.traco).toFixed(1) + 'px',
    background: ctx.alfa('texto_suave', 0.5), transformOrigin: 'left center', flex: '0 0 auto',
  });
  bloco.appendChild(filete);

  const { html } = htmlComGrifo(ctx, p.manchete, p.grifo);
  const titulo = ctx.texto('titulo', '', { tam: ctx.tam('h1'), wrap: true, maxW: base.area.w, html });
  bloco.appendChild(titulo);
  const alturaMax = base.area.h * (p.linha_fina ? 0.52 : 0.68);
  ctx.ajustar_texto(titulo, base.area.w, { min: ctx.tam('h3'), alturaMax, maxLinhas: ctx.orientacao === 'vertical' ? 6 : 4 });
  ctx.sem_orfa(titulo, { min: ctx.tam('h3') });
  const grifo = prepararGrifo(ctx, titulo);

  let fina = null;
  if (p.linha_fina) {
    fina = ctx.texto('corpo', p.linha_fina, { tam: ctx.tam('corpo'), cor: 'texto_suave', wrap: true, maxW: base.area.w });
    bloco.appendChild(fina);
    ctx.ajustar_texto(fina, base.area.w, { min: ctx.minimo_legivel, maxLinhas: 4 });
    ctx.sem_orfa(fina, { min: ctx.minimo_legivel });
  }

  bloco.style.top = Math.round(Math.max(0, (base.area.h - bloco.offsetHeight) / 2)) + 'px';
  const credito = montarCredito(ctx, palco, p);

  const e = ctx.escalonamento;
  const tGrifo = Math.min(base.inicio_saida - ctx.dur('curta'), T0 + ctx.dur('longa') + e * 6);
  const T = ctx.tl().add('cabecalho', T0, ctx.dur('media'))
    .add('filete', T0 + e * 2, ctx.dur('media'), { curva: 'enfase' })
    .add('manchete', T0 + e * 4, ctx.dur('longa'), { tipo: 'texto' })
    .add('fina', T0 + e * 7, ctx.dur('media'))
    .add('grifo', tGrifo, ctx.dur('media'), { curva: 'enfase', tipo: 'enfase' })
    .add('credito', T0 + e * 7, ctx.dur('media'));

  Object.assign(S, { ctx, base, tarja, data, filete, titulo, fina, grifo, credito, T });
  return { ...base.layout(), bloco: ctx.rectDe(bloco), manchete: ctx.rectDe(titulo), linhas: ctx.medir(titulo).linhas, fim_entrada: +T.t1('manchete').toFixed(3) };
}

export function seek(t) {
  const { ctx, base, tarja, data, filete, titulo, fina, grifo, credito, T } = S;
  base.seek(t);
  const pc = T.p(t, 'cabecalho');
  if (tarja) tarja.seek(pc, T.p(t, 'cabecalho', 'suave'));
  if (data) ctx.entrada(data, pc, 'fade');
  const pf = T.p(t, 'filete');
  filete.style.opacity = pf > 0 ? '1' : '0';
  filete.style.transform = `scaleX(${ctx.clamp(pf, 0, 1).toFixed(4)})`;
  ctx.entrada(titulo, T.p(t, 'manchete'), ctx.DA.movimento.entrada_padrao, { origem: 'esquerda' });
  grifo.seek(T.p(t, 'grifo'));
  if (fina) ctx.entrada(fina, T.p(t, 'fina'), 'fade');
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  return t >= S.T.t1('grifo') + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  return S.base.ancoras().concat([
    { t: +S.T.t0('manchete').toFixed(3), nome: 'manchete', tipo: 'texto' },
    { t: +S.T.t0('grifo').toFixed(3), nome: 'grifo', tipo: 'enfase' },
  ]);
}
