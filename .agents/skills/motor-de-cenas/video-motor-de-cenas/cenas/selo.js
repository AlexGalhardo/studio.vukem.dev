// selo.js — elemento fixo: o selo que muda de estado (ex.: APURANDO → CONFIRMADO). Overlay com alfa.
import { montarCarimbo, limitar } from './_comum.js';

export const meta = {
  nome: 'selo',
  descricao: 'Selo de estado no canto da zona segura, que troca de texto e de cor no tempo da fala.',
  dur_padrao: 5,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: true,
  grao: false,
  params: {
    estados: {
      tipo: 'lista', obrigatorio: true, min: 1, max: 4,
      itens: {
        tipo: 'objeto', campos: {
          texto: { tipo: 'texto', obrigatorio: true, descricao: 'curto, 1 a 3 palavras' },
          cor: { tipo: 'cor', padrao: 'primaria' },
          em: { tipo: 'numero', padrao: null, min: 0, descricao: 'segundos da peça em que este estado entra; padrão: distribuído' },
        },
      },
    },
    canto: { tipo: 'opcao', opcoes: ['superior_esquerda', 'superior_direita', 'inferior_esquerda', 'inferior_direita'], padrao: 'superior_direita' },
    inclinacao: { tipo: 'numero', padrao: -7, min: -15, max: 15 },
    plataforma: { tipo: 'plataforma', padrao: null, descricao: 'zona segura a respeitar' },
    reservar_legenda: { tipo: 'booleano', padrao: null, descricao: 'deixa livre a faixa da legenda queimada' },
  },
};

const S = {};

export function build(palco, p, ctx) {
  const area = ctx.area_livre(p.plataforma || undefined, { legenda: p.reservar_legenda });
  const n = p.estados.length;
  const fimSaida = ctx.fim_saida();
  const janela = Math.max(ctx.dur('media'), (fimSaida - ctx.dur('curta')) / Math.max(1, n));

  const selos = p.estados.map((est, i) => {
    const em = est.em == null ? (i === 0 ? 0 : limitar(janela * i, 0, fimSaida)) : limitar(est.em, 0, fimSaida);
    const c = montarCarimbo(ctx, palco, est.texto, { cor: est.cor || 'primaria', inclinacao: p.inclinacao, tam: ctx.tam('h3') });
    Object.assign(c.el.style, { background: ctx.alfa('fundo', 0.82) });
    const alto = p.canto.startsWith('superior');
    const esq = p.canto.endsWith('esquerda');
    const folga = ctx.px(0.012);                       // a inclinação joga os cantos para fora: sobra uma folga
    c.el.style.left = Math.round(esq ? area.x + folga : area.x1 - c.w - folga) + 'px';
    c.el.style.top = Math.round(alto ? area.y + folga : area.y1 - c.h - folga) + 'px';
    return { c, em: +em.toFixed(3), texto: est.texto };
  }).sort((a, b) => a.em - b.em);

  Object.assign(S, { ctx, selos, fimSaida });
  return {
    estados: selos.map((s) => ({ t: s.em, texto: s.texto, caixa: { x: parseFloat(s.c.el.style.left), y: parseFloat(s.c.el.style.top), w: s.c.w, h: s.c.h } })),
    zona: area.plataforma, reservou_legenda: !!area.reservou,
    fim_entrada: +(selos[0].em + ctx.dur('curta')).toFixed(3), inicio_saida: +fimSaida.toFixed(3),
  };
}

export function seek(t) {
  const { ctx, selos, fimSaida } = S;
  const saindo = t >= fimSaida;
  const ps = saindo ? ctx.prog(t, fimSaida, ctx.dur('curta'), 'saida') : 0;
  selos.forEach((s, i) => {
    const prox = selos[i + 1];
    const dentro = t >= s.em - 1e-9 && (!prox || t < prox.em);
    if (!dentro) { s.c.el.style.opacity = '0'; s.c.el.style.transform = `rotate(0deg) scale(1)`; return; }
    s.c.seek(ctx.prog(t, s.em, ctx.dur('curta'), 'enfase'));
    if (saindo) s.c.el.style.opacity = (1 - ps).toFixed(3);
  });
}

export function key(t) {
  return null;
}

export function ancoras() {
  return S.selos.map((s, i) => ({ t: s.em, nome: 'selo' + i, tipo: i === 0 ? 'entrada' : 'enfase' }));
}
