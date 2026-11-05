// foto.js — uma foto na moldura da DA, com rótulo e crédito. A foto é o único elemento `data-da-livre` da cena.
import { PARAMS_PALCO, montarPalco, montarCredito, imagem, esperarImagens } from './_comum.js';

export const meta = {
  nome: 'foto',
  descricao: 'Foto na moldura da DA (rótulo + crédito), em cartão ou em tela cheia.',
  dur_padrao: 4,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    arquivo: { tipo: 'arquivo', obrigatorio: true, descricao: 'imagem (jpg/png); nada de GIF — o auditor reprova imagem animada' },
    rotulo: { tipo: 'texto', padrao: null, descricao: 'rótulo da moldura (quem é, de quando é)' },
    sub: { tipo: 'texto', padrao: null, descricao: 'segunda linha do rótulo (ex.: "Reprodução")' },
    encaixe: { tipo: 'opcao', opcoes: ['cobrir', 'inteira'], padrao: 'cobrir', descricao: 'cobrir recorta para preencher a janela; inteira mostra a foto toda' },
    estilo: { tipo: 'opcao', opcoes: ['nenhuma', 'borda', 'cantoneiras', 'janela', 'polaroid'], padrao: null, descricao: 'estilo da moldura; padrão: tratamento.moldura da DA' },
    area: { tipo: 'lista', padrao: null, min: 4, max: 4, itens: { tipo: 'numero' }, descricao: '[x, y, l, a] em frações do quadro; padrão: a área livre inteira' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export async function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;

  const m = ctx.kit.moldura({
    rotulo: p.rotulo, sub: p.sub, area: p.area || undefined, estilo: p.estilo || undefined,
    plataforma: p.plataforma || undefined, reservar_legenda: p.reservar_legenda,
  });
  base.mundo.appendChild(m.el);

  const j = m.layout.janela;
  const g = m.layout.janela_girada || null;
  const quadro = ctx.el('div', 'mc-foto');
  Object.assign(quadro.style, {
    position: 'absolute', left: j.x + 'px', top: j.y + 'px', width: j.w + 'px', height: j.h + 'px',
    overflow: 'hidden', background: ctx.cor('fundo'), zIndex: '0',
    transform: g && g.angulo ? `rotate(${g.angulo}deg)` : 'none', transformOrigin: '50% 50%',
  });
  const img = imagem(ctx, p.arquivo, p.rotulo ? `foto: ${p.rotulo}` : 'foto do projeto');
  img.style.objectFit = p.encaixe === 'inteira' ? 'contain' : 'cover';
  img.style.transformOrigin = '50% 50%';
  quadro.appendChild(img);
  base.mundo.insertBefore(quadro, m.el);
  await esperarImagens(quadro);

  const credito = montarCredito(ctx, palco, p, { sobre_midia: true });
  const T = ctx.tl().add('foto', T0, ctx.dur('longa'), { curva: 'suave' }).add('credito', T0 + ctx.escalonamento * 3, ctx.dur('media'));
  const zoom = p.camera === 'parada' ? 0 : 0.03;

  Object.assign(S, { ctx, base, m, quadro, img, credito, T, zoom });
  return { ...base.layout(), janela: j, janela_girada: g, moldura: m.layout.estilo || null, fim_entrada: +T.t1('foto').toFixed(3) };
}

export function seek(t) {
  const { ctx, base, m, quadro, img, credito, T, zoom } = S;
  base.seek(t);
  m.seek(t);
  ctx.entrada(quadro, T.p(t, 'foto'), 'mascara', { origem: 'esquerda' });
  const pz = ctx.lin(t, 0, Math.max(0.5, ctx.duracao));
  img.style.transform = `scale(${(1 + zoom * pz).toFixed(5)})`;
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  return null;                                     // a foto respira o tempo todo: nenhum quadro se repete
}

export function ancoras() {
  return S.base.ancoras().concat([{ t: +S.T.t0('foto').toFixed(3), nome: 'foto', tipo: 'entrada' }]);
}
