// infografico.js — blocos ou etapas com rótulo, valor e nota. Para barra quantitativa use a cena `barras` do kit.
import { PARAMS_PALCO, montarPalco, montarChapeu, montarCredito, formatarNumero, svgDe, fio, limitar } from './_comum.js';

export const meta = {
  nome: 'infografico',
  descricao: 'Infográfico simples: blocos lado a lado ou etapas numeradas ligadas, com valor e nota.',
  dur_padrao: 6,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    itens: {
      tipo: 'lista', obrigatorio: true, min: 2, max: 6,
      itens: {
        tipo: 'objeto', campos: {
          rotulo: { tipo: 'texto', obrigatorio: true },
          valor: { tipo: 'numero', padrao: null },
          nota: { tipo: 'texto', padrao: null },
        },
      },
    },
    modo: { tipo: 'opcao', opcoes: ['blocos', 'etapas'], padrao: 'blocos' },
    titulo: { tipo: 'texto', padrao: null },
    prefixo: { tipo: 'texto', padrao: '' },
    sufixo: { tipo: 'texto', padrao: '' },
    casas: { tipo: 'inteiro', padrao: 0, min: 0, max: 4 },
    destaque: { tipo: 'inteiro', padrao: null, min: 0, descricao: 'índice do item em destaque' },
    cores: { tipo: 'opcao', opcoes: ['serie', 'primaria'], padrao: 'serie', descricao: 'série de cor.dados ou tudo na primária' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;
  const n = p.itens.length;
  const etapas = p.modo === 'etapas';

  let topo = 0;
  const chapeu = montarChapeu(ctx, base.conteudo, p.chapeu);
  if (chapeu) { Object.assign(chapeu.el.style, { position: 'absolute', left: '0', top: '0' }); topo = chapeu.el.offsetHeight + ctx.px(0.025); }
  let titulo = null;
  if (p.titulo) {
    titulo = ctx.texto('titulo', p.titulo, { tam: ctx.tam('h2'), wrap: true, maxW: base.area.w });
    Object.assign(titulo.style, { position: 'absolute', left: '0', top: topo + 'px' });
    base.conteudo.appendChild(titulo);
    ctx.ajustar_texto(titulo, base.area.w, { min: ctx.tam('h3'), maxLinhas: 2 });
    topo += ctx.medir(titulo).h + ctx.px(0.035);
  }

  const emLinha = ctx.orientacao !== 'vertical' && n <= 4;
  const campo = { y: topo, w: base.area.w, h: Math.max(ctx.px(0.12), base.area.h - topo) };
  const vao = ctx.px(0.02);
  const larguraItem = emLinha ? (campo.w - vao * (n - 1)) / n : campo.w;
  const alturaItem = emLinha ? campo.h : (campo.h - vao * (n - 1)) / n;

  const tela = svgDe(ctx, base.area.w, base.area.h);
  base.conteudo.appendChild(tela);
  const itens = [], fios = [];

  for (let i = 0; i < n; i++) {
    const it = p.itens[i];
    const destacado = p.destaque === i;
    const cor = p.cores === 'primaria' || destacado ? 'primaria' : `dado-${(i % 6) + 1}`;
    const x = emLinha ? i * (larguraItem + vao) : 0;

    const caixa = ctx.el('div', 'mc-item');
    Object.assign(caixa.style, {
      position: 'absolute', left: Math.round(x) + 'px', top: '0px',
      width: Math.round(larguraItem) + 'px', boxSizing: 'border-box',
      background: ctx.alfa('texto', 0.04), borderRadius: (ctx.raio * 0.5).toFixed(1) + 'px',
      borderLeftStyle: 'solid', borderLeftWidth: Math.max(2, ctx.traco * 2.5).toFixed(1) + 'px', borderLeftColor: ctx.cor(cor),
      padding: `${ctx.px(0.018).toFixed(1)}px ${ctx.px(0.016).toFixed(1)}px`,
      display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: ctx.px(0.008) + 'px', overflow: 'hidden',
    });
    base.conteudo.appendChild(caixa);
    const larguraTexto = larguraItem - ctx.px(0.034);

    if (etapas) {
      const num = ctx.texto('dados', String(i + 1), { tam: ctx.tam('h3'), cor });
      caixa.appendChild(num);
    }
    if (it.valor != null) {
      const v = ctx.texto('dados', formatarNumero(it.valor, { casas: p.casas || 0, prefixo: p.prefixo || '', sufixo: p.sufixo || '' }), { tam: ctx.tam('h2'), cor });
      caixa.appendChild(v);
      ctx.ajustar_texto(v, larguraTexto, { min: ctx.tam('corpo') });
    }
    const rot = ctx.texto('subtitulo', it.rotulo, { tam: ctx.tam('corpo'), wrap: true, maxW: larguraTexto });
    caixa.appendChild(rot);
    ctx.ajustar_texto(rot, larguraTexto, { min: ctx.minimo_legivel, maxLinhas: 3 });
    if (it.nota) {
      const nt = ctx.texto('corpo', it.nota, { tam: ctx.tam('nota'), cor: 'texto_suave', wrap: true, maxW: larguraTexto });
      caixa.appendChild(nt);
      ctx.ajustar_texto(nt, larguraTexto, { min: ctx.minimo_legivel, maxLinhas: 3 });
    }
    itens.push({ el: caixa, x, w: larguraItem });
  }

  // a caixa tem a altura do que cabe dentro dela, e o conjunto fica centrado no campo (nada esticado à toa)
  if (emLinha) {
    const hMax = Math.min(campo.h, Math.max(...itens.map((i) => i.el.offsetHeight)));
    const y = campo.y + Math.max(0, (campo.h - hMax) / 2);
    for (const it of itens) { it.el.style.height = Math.round(hMax) + 'px'; it.el.style.top = Math.round(y) + 'px'; it.y = y; it.h = hMax; }
  } else {
    const alturas = itens.map((i) => Math.min(alturaItem, i.el.offsetHeight));
    const soma = alturas.reduce((a, b) => a + b, 0) + vao * (n - 1);
    let y = campo.y + Math.max(0, (campo.h - soma) / 2);
    itens.forEach((it, i) => { it.el.style.height = Math.round(alturas[i]) + 'px'; it.el.style.top = Math.round(y) + 'px'; it.y = y; it.h = alturas[i]; y += alturas[i] + vao; });
  }

  if (etapas) {
    for (let i = 0; i + 1 < n; i++) {
      const a = itens[i], b = itens[i + 1];
      const ponto = emLinha
        ? [a.x + a.w, a.y + a.h / 2, b.x, b.y + b.h / 2]
        : [a.x + a.w / 2, a.y + a.h, b.x + b.w / 2, b.y];
      fios.push(fio(ctx, tela, ponto[0], ponto[1], ponto[2], ponto[3], { cor: 'texto_suave', alfa: 0.7, largura: Math.max(2, ctx.traco * 1.4) }));
    }
  }

  const credito = montarCredito(ctx, palco, p);
  const e = ctx.escalonamento;
  const T = ctx.tl().add('chapeu', T0, ctx.dur('media')).add('titulo', T0 + e, ctx.dur('media'));
  const t1 = T0 + e * 3;
  const passo = limitar((base.inicio_saida - t1 - ctx.dur('media')) / Math.max(1, n), e * 1.5, ctx.dur('media'));
  T.escalonar(itens.map((_, i) => 'i' + i), t1, ctx.dur('media'), { passo, tipo: 'texto' });
  fios.forEach((_, i) => T.add('f' + i, t1 + passo * (i + 0.7), ctx.dur('curta'), { curva: 'suave' }));
  T.add('credito', t1, ctx.dur('media'));

  Object.assign(S, { ctx, base, chapeu, titulo, itens, fios, credito, T, t1, passo, n });
  return { ...base.layout(), modo: p.modo, itens: itens.map((i) => ({ x: Math.round(i.x), y: Math.round(i.y), w: Math.round(i.w), h: Math.round(i.h) })), fim_entrada: +(t1 + passo * n + ctx.dur('media')).toFixed(3) };
}

export function seek(t) {
  const { ctx, base, chapeu, titulo, itens, fios, credito, T } = S;
  base.seek(t);
  if (chapeu) chapeu.seek(T.p(t, 'chapeu'), T.p(t, 'chapeu', 'suave'));
  if (titulo) ctx.entrada(titulo, T.p(t, 'titulo'), ctx.DA.movimento.entrada_padrao, { origem: 'esquerda' });
  itens.forEach((it, i) => ctx.entrada(it.el, T.p(t, 'i' + i), ctx.DA.movimento.entrada_padrao, { origem: 'esquerda' }));
  fios.forEach((f, i) => f.seek(T.p(t, 'f' + i)));
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  const fim = S.t1 + S.passo * S.n + S.ctx.dur('media');
  return t >= fim + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  return S.base.ancoras().concat(S.itens.map((_, i) => ({ t: +(S.t1 + S.passo * i).toFixed(3), nome: 'item' + i, tipo: 'texto' })));
}
