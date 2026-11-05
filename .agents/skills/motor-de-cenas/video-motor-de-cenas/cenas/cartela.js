// cartela.js — elemento fixo: a cartela de troca de assunto. A cartela de título do kit + o contador de capítulo.
import { PARAMS_PALCO, montarPalco } from './_comum.js';

export const meta = {
  nome: 'cartela',
  descricao: 'Cartela de troca de assunto: sobretítulo, título, filete e contador de capítulo.',
  dur_padrao: 4,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    titulo: { tipo: 'texto', obrigatorio: true, descricao: 'o assunto que começa agora' },
    sobretitulo: { tipo: 'texto', padrao: null, descricao: 'texto curto acima (ex.: "Parte 2")' },
    subtitulo: { tipo: 'texto', padrao: null, descricao: 'linha de apoio' },
    capitulo: { tipo: 'inteiro', padrao: null, min: 1, descricao: 'número deste capítulo (acende no contador)' },
    de: { tipo: 'inteiro', padrao: null, min: 1, descricao: 'total de capítulos (desenha o contador inteiro)' },
    alinhar: { tipo: 'opcao', opcoes: ['esquerda', 'centro'], padrao: 'esquerda' },
    ...PARAMS_PALCO,
    palco: { ...PARAMS_PALCO.palco, padrao: 'cheia' },
  },
};

const S = {};

export async function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const camada = ctx.el('div', 'mc-camada');
  Object.assign(camada.style, { position: 'absolute', inset: '0' });
  base.mundo.appendChild(camada);

  const cart = await ctx.kit.cena('titulo', {
    titulo: p.titulo, sobretitulo: p.sobretitulo, subtitulo: p.subtitulo, alinhar: p.alinhar,
    plataforma: p.plataforma, reservar_legenda: p.reservar_legenda, assinatura: false,
  }, { palco: camada, dur: ctx.duracao, alfa: true });

  // contador de capítulos: um traço por capítulo, o atual em primaria
  let contador = null, pontos = [];
  const total = p.de || 0;
  if (total > 1 && p.capitulo) {
    contador = ctx.el('div', 'mc-contador');
    Object.assign(contador.style, { position: 'absolute', display: 'flex', gap: ctx.px(0.008) + 'px', alignItems: 'center' });
    base.mundo.appendChild(contador);
    const largura = Math.max(ctx.px(0.012), ctx.px(0.3) / total);
    for (let i = 0; i < total; i++) {
      const d = ctx.el('div');
      const atual = i === p.capitulo - 1;
      Object.assign(d.style, {
        width: (atual ? largura * 1.6 : largura).toFixed(1) + 'px', height: Math.max(2, ctx.traco * 2).toFixed(1) + 'px',
        background: ctx.cor(atual ? 'primaria' : 'texto_suave'), transformOrigin: 'left center',
      });
      contador.appendChild(d);
      pontos.push(d);
    }
    const gcEmbaixo = !ctx.DA.graficos.gc.posicao.startsWith('superior');
    contador.style.left = Math.round(base.area.x) + 'px';
    contador.style.top = Math.round(gcEmbaixo ? base.area.y : base.area.y1 - Math.max(2, ctx.traco * 2)) + 'px';
  }

  const T = ctx.tl().add('contador', base.t0_conteudo + ctx.escalonamento * 4, ctx.dur('media'));
  Object.assign(S, { ctx, base, cart, contador, pontos, T });
  return { ...base.layout(), titulo: cart.layout, capitulo: p.capitulo || null, de: total || null };
}

export function seek(t) {
  const { ctx, base, cart, contador, T } = S;
  base.seek(t);
  cart.seek(ctx.clamp(t, 0, ctx.duracao));
  if (contador) ctx.entrada(contador, T.p(t, 'contador'), 'fade');
}

export function key(t) {
  return null;
}

export function ancoras() {
  return S.base.ancoras();
}
