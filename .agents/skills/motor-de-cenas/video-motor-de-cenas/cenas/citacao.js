// citacao.js — a citação do kit (aspas, frase palavra a palavra, autor e crédito) com o carimbo de estado por cima.
import { PARAMS_PALCO, montarPalco, montarCarimbo, limitar } from './_comum.js';

export const meta = {
  nome: 'citacao',
  descricao: 'Citação na DA (aspas, autor, fonte) com carimbo de estado — "confirmado", "negou", "sem resposta".',
  dur_padrao: 6,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    texto: { tipo: 'texto', obrigatorio: true, descricao: 'a frase citada, sem aspas (o kit põe)' },
    autor: { tipo: 'texto', padrao: null, descricao: 'quem disse' },
    cargo: { tipo: 'texto', padrao: null, descricao: 'cargo ou contexto' },
    foto: { tipo: 'arquivo', padrao: null, descricao: 'foto do autor' },
    carimbo: { tipo: 'texto', padrao: null, descricao: 'texto do carimbo (curto, em caixa alta)' },
    cor_carimbo: { tipo: 'cor', padrao: 'negativo', descricao: 'token do carimbo' },
    carimbo_em: { tipo: 'numero', padrao: null, min: 0, descricao: 'segundos em que o carimbo bate; padrão: 62% da cena' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export async function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const camada = ctx.el('div', 'mc-camada');
  Object.assign(camada.style, { position: 'absolute', inset: '0' });
  base.mundo.appendChild(camada);

  const cit = await ctx.kit.cena('citacao', {
    texto: p.texto, autor: p.autor, cargo: p.cargo, fonte: p.fonte, foto: p.foto,
    plataforma: p.plataforma, reservar_legenda: p.reservar_legenda,
  }, { palco: camada, dur: ctx.duracao, alfa: true });

  let carimbo = null, tCarimbo = null;
  if (p.carimbo) {
    tCarimbo = limitar(p.carimbo_em == null ? ctx.duracao * 0.62 : p.carimbo_em, 0, Math.max(0, base.inicio_saida - ctx.dur('curta')));
    carimbo = montarCarimbo(ctx, base.mundo, p.carimbo, { cor: p.cor_carimbo || 'negativo' });
    const x = Math.round(base.area.x1 - carimbo.w - ctx.px(0.01));
    const y = Math.round(base.area.y1 - carimbo.h - ctx.px(0.01));
    carimbo.el.style.left = x + 'px';
    carimbo.el.style.top = y + 'px';
  }

  const T = ctx.tl();
  if (carimbo) T.add('carimbo', tCarimbo, ctx.dur('curta'), { curva: 'enfase', tipo: 'enfase' });
  Object.assign(S, { ctx, base, cit, carimbo, T, tCarimbo });
  return { ...base.layout(), citacao: cit.layout, carimbo: carimbo ? { t: +tCarimbo.toFixed(3), texto: p.carimbo } : null };
}

export function seek(t) {
  const { ctx, base, cit, carimbo, T } = S;
  base.seek(t);
  cit.seek(ctx.clamp(t, 0, ctx.duracao));
  if (carimbo) carimbo.seek(T.p(t, 'carimbo'));
}

export function key(t) {
  return null;
}

export function ancoras() {
  const a = S.base.ancoras();
  if (S.carimbo) a.push({ t: +S.tCarimbo.toFixed(3), nome: 'carimbo', tipo: 'enfase' });
  return a;
}
