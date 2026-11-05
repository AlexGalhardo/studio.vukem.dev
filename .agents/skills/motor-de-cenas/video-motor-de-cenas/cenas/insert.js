// insert.js — moldura vazia com alfa: a janela fica transparente para o ffmpeg encaixar o VÍDEO.
// Footage nunca entra na página (o auditor reprova mídia tocando); o vídeo entra depois, numa passada:
//   layout = da.ler_carimbo("animacoes/insert.webm")["parametros"]["layout"]
//   video.encaixar_em_janela("render/_fundo.mp4", "broll/tratado/x.mp4", "render/insert.mp4", layout,
//                            moldura="animacoes/insert.webm", da_obj=d)
import { montarCredito } from './_comum.js';

export const meta = {
  nome: 'insert',
  descricao: 'Moldura de insert com a janela transparente: o vídeo é encaixado pelo ffmpeg depois.',
  dur_padrao: 4,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: true,
  grao: false,
  params: {
    rotulo: { tipo: 'texto', padrao: null, descricao: 'rótulo da moldura (o que é o vídeo, de quando é)' },
    sub: { tipo: 'texto', padrao: null, descricao: 'segunda linha do rótulo (ex.: "Reprodução")' },
    area: { tipo: 'lista', padrao: null, min: 4, max: 4, itens: { tipo: 'numero' }, descricao: '[x, y, l, a] em frações do quadro; padrão: a área livre inteira' },
    estilo: { tipo: 'opcao', opcoes: ['nenhuma', 'borda', 'cantoneiras', 'janela', 'polaroid'], padrao: null, descricao: 'padrão: tratamento.moldura da DA' },
    inclinacao: { tipo: 'numero', padrao: null, min: -15, max: 15, descricao: 'graus (só em polaroid)' },
    fonte: { tipo: 'texto', padrao: null, descricao: 'crédito da fonte' },
    plataforma: { tipo: 'plataforma', padrao: null, descricao: 'zona segura a respeitar' },
    reservar_legenda: { tipo: 'booleano', padrao: null, descricao: 'deixa livre a faixa da legenda queimada' },
  },
};

const S = {};

export function build(palco, p, ctx) {
  const m = ctx.kit.moldura({
    rotulo: p.rotulo, sub: p.sub, area: p.area || undefined, estilo: p.estilo || undefined,
    inclinacao: p.inclinacao == null ? undefined : p.inclinacao,
    plataforma: p.plataforma || undefined, reservar_legenda: p.reservar_legenda,
  });
  palco.appendChild(m.el);
  const credito = montarCredito(ctx, palco, p, { sobre_midia: true });
  const T = ctx.tl().add('credito', ctx.dur('curta') + ctx.escalonamento * 3, ctx.dur('media'));
  Object.assign(S, { ctx, m, credito, T });
  return { ...m.layout, fim_entrada: m.layout.fim_entrada ?? null, inicio_saida: m.layout.inicio_saida ?? +ctx.fim_saida().toFixed(3) };
}

export function seek(t) {
  const { m, credito, T } = S;
  m.seek(t);
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  return S.m.key ? S.m.key(t) : null;
}

export function ancoras() {
  const a = (S.m.ancoras ? S.m.ancoras() : []) || [];
  return a.length ? a : [{ t: 0, nome: 'insert', tipo: 'entrada' }];
}
