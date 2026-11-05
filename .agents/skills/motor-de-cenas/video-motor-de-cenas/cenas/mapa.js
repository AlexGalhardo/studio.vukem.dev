// mapa.js — mapa esquemático: malha, um contorno de território, pontos marcados e rotas entre eles.
// Nada é baixado: o contorno é o que o projeto passar (frações do quadro) ou a forma genérica do kit desta skill.
import { PARAMS_PALCO, montarPalco, montarChapeu, montarCredito, svgDe, limitar } from './_comum.js';

// contorno genérico (frações da caixa do mapa) — uma massa de terra qualquer, de propósito não reconhecível
const CONTORNO_PADRAO = [
  [0.14, 0.22], [0.31, 0.12], [0.49, 0.17], [0.62, 0.10], [0.78, 0.20], [0.86, 0.36],
  [0.80, 0.53], [0.84, 0.70], [0.68, 0.84], [0.50, 0.88], [0.33, 0.81], [0.22, 0.66], [0.10, 0.46],
];

export const meta = {
  nome: 'mapa',
  descricao: 'Mapa esquemático com malha, contorno, pontos marcados e rotas — sem nenhum dado baixado.',
  dur_padrao: 6,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    pontos: {
      tipo: 'lista', obrigatorio: true, min: 1, max: 8,
      itens: {
        tipo: 'objeto', campos: {
          nome: { tipo: 'texto', obrigatorio: true },
          x: { tipo: 'numero', obrigatorio: true, min: 0, max: 1, descricao: 'fração da largura do mapa' },
          y: { tipo: 'numero', obrigatorio: true, min: 0, max: 1, descricao: 'fração da altura do mapa' },
          destaque: { tipo: 'booleano', padrao: false },
        },
      },
    },
    rotas: {
      tipo: 'lista', padrao: [], max: 8,
      itens: { tipo: 'objeto', campos: { de: { tipo: 'inteiro', obrigatorio: true, min: 0 }, para: { tipo: 'inteiro', obrigatorio: true, min: 0 } } },
      descricao: 'rotas entre pontos, por índice',
    },
    contorno: { tipo: 'lista', padrao: null, min: 6, itens: { tipo: 'lista', min: 2, max: 2, itens: { tipo: 'numero' } }, descricao: 'polígono [[x, y], …] em frações; padrão: a forma genérica do kit' },
    titulo: { tipo: 'texto', padrao: null },
    ...PARAMS_PALCO,
  },
};

const S = {};

export function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;

  let topo = 0;
  const chapeu = montarChapeu(ctx, base.conteudo, p.chapeu);
  if (chapeu) { Object.assign(chapeu.el.style, { position: 'absolute', left: '0', top: '0' }); topo = chapeu.el.offsetHeight + ctx.px(0.025); }
  let titulo = null;
  if (p.titulo) {
    titulo = ctx.texto('titulo', p.titulo, { tam: ctx.tam('h2'), wrap: true, maxW: base.area.w });
    Object.assign(titulo.style, { position: 'absolute', left: '0', top: topo + 'px' });
    base.conteudo.appendChild(titulo);
    ctx.ajustar_texto(titulo, base.area.w, { min: ctx.tam('h3'), maxLinhas: 2 });
    topo += ctx.medir(titulo).h + ctx.px(0.03);
  }

  const caixa = { x: 0, y: topo, w: base.area.w, h: Math.max(ctx.px(0.15), base.area.h - topo) };
  const tela = svgDe(ctx, base.area.w, base.area.h);
  base.conteudo.appendChild(tela);
  const traco = Math.max(1, ctx.traco);

  // malha: linhas finas, só para dar escala
  const malha = ctx.svg('g', {});
  tela.appendChild(malha);
  const passoMalha = Math.max(ctx.px(0.05), caixa.w / 8);
  for (let x = caixa.x; x <= caixa.x + caixa.w + 0.5; x += passoMalha) {
    malha.appendChild(ctx.svg('line', { x1: x.toFixed(1), y1: caixa.y.toFixed(1), x2: x.toFixed(1), y2: (caixa.y + caixa.h).toFixed(1), stroke: ctx.alfa('texto_suave', 0.18), 'stroke-width': traco.toFixed(2) }));
  }
  for (let y = caixa.y; y <= caixa.y + caixa.h + 0.5; y += passoMalha) {
    malha.appendChild(ctx.svg('line', { x1: caixa.x.toFixed(1), y1: y.toFixed(1), x2: (caixa.x + caixa.w).toFixed(1), y2: y.toFixed(1), stroke: ctx.alfa('texto_suave', 0.18), 'stroke-width': traco.toFixed(2) }));
  }

  const pts = (p.contorno && p.contorno.length ? p.contorno : CONTORNO_PADRAO).map(([fx, fy]) => [caixa.x + fx * caixa.w, caixa.y + fy * caixa.h]);
  const territorio = ctx.svg('polygon', {
    points: pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' '),
    fill: ctx.alfa('secundaria', 0.95), stroke: ctx.alfa('texto_suave', 0.6), 'stroke-width': (traco * 1.5).toFixed(2), 'stroke-linejoin': 'round',
  });
  tela.appendChild(territorio);

  const lugar = (pt) => [caixa.x + limitar(pt.x, 0, 1) * caixa.w, caixa.y + limitar(pt.y, 0, 1) * caixa.h];
  const rotas = [];
  for (const r of p.rotas || []) {
    const a = p.pontos[r.de], b = p.pontos[r.para];
    if (!a || !b || a === b) continue;
    const [x0, y0] = lugar(a), [x1, y1] = lugar(b);
    const dist = Math.hypot(x1 - x0, y1 - y0) || 1;
    const arco = ctx.svg('path', {
      d: `M ${x0.toFixed(1)} ${y0.toFixed(1)} Q ${((x0 + x1) / 2).toFixed(1)} ${((y0 + y1) / 2 - dist * 0.22).toFixed(1)} ${x1.toFixed(1)} ${y1.toFixed(1)}`,
      fill: 'none', stroke: ctx.alfa('primaria', 0.85), 'stroke-width': (traco * 2).toFixed(2), 'stroke-linecap': 'round',
    });
    tela.appendChild(arco);
    const comp = dist * 1.15;
    rotas.push({ el: arco, comp });
  }

  const marcas = [];
  const raio = Math.max(ctx.px(0.008), traco * 3);
  for (let i = 0; i < p.pontos.length; i++) {
    const pt = p.pontos[i];
    const [x, y] = lugar(pt);
    const cor = pt.destaque ? 'primaria' : 'texto';
    const g = ctx.el('div', 'mc-marca');
    Object.assign(g.style, { position: 'absolute', left: Math.round(x) + 'px', top: Math.round(y) + 'px', display: 'flex', alignItems: 'center', gap: ctx.px(0.008) + 'px', transform: 'translate(0, -50%)' });
    base.conteudo.appendChild(g);
    const disco = ctx.el('div');
    Object.assign(disco.style, { width: raio * 2 + 'px', height: raio * 2 + 'px', borderRadius: '50%', background: ctx.cor(cor), flex: '0 0 auto', marginLeft: -raio + 'px' });
    g.appendChild(disco);
    const nome = ctx.texto('dados', pt.nome, { tam: ctx.tam('nota'), cor });
    Object.assign(nome.style, { background: ctx.alfa('fundo', 0.8), padding: `${ctx.px(0.003).toFixed(1)}px ${ctx.px(0.006).toFixed(1)}px` });
    g.appendChild(nome);
    ctx.medir(nome);
    if (x + ctx.medir(nome).w + raio * 3 > caixa.x + caixa.w) { g.style.flexDirection = 'row-reverse'; g.style.transform = 'translate(-100%, -50%)'; disco.style.marginLeft = '0'; disco.style.marginRight = -raio + 'px'; }
    marcas.push({ el: g, destaque: !!pt.destaque });
  }

  const credito = montarCredito(ctx, palco, p);
  const e = ctx.escalonamento;
  const T = ctx.tl().add('chapeu', T0, ctx.dur('media')).add('titulo', T0 + e, ctx.dur('media'))
    .add('mapa', T0 + e * 2, ctx.dur('longa'), { curva: 'suave' });
  const t1 = T0 + e * 2 + ctx.dur('longa') * 0.5;
  const passo = limitar((base.inicio_saida - t1 - ctx.dur('media')) / Math.max(1, marcas.length + rotas.length), e, ctx.dur('curta'));
  T.escalonar(marcas.map((_, i) => 'p' + i), t1, ctx.dur('curta'), { passo, tipo: 'texto' });
  const tRotas = t1 + passo * marcas.length;
  rotas.forEach((_, i) => T.add('r' + i, tRotas + i * passo, ctx.dur('media'), { curva: 'suave', tipo: 'enfase' }));
  T.add('credito', t1, ctx.dur('media'));

  Object.assign(S, { ctx, base, chapeu, titulo, malha, territorio, marcas, rotas, credito, T, tRotas, t1, passo });
  return { ...base.layout(), mapa: { x: Math.round(caixa.x + base.area.x), y: Math.round(caixa.y + base.area.y), w: Math.round(caixa.w), h: Math.round(caixa.h) }, pontos: marcas.length, rotas: rotas.length, fim_entrada: +(tRotas + ctx.dur('media')).toFixed(3) };
}

export function seek(t) {
  const { ctx, base, chapeu, titulo, malha, territorio, marcas, rotas, credito, T } = S;
  base.seek(t);
  if (chapeu) chapeu.seek(T.p(t, 'chapeu'), T.p(t, 'chapeu', 'suave'));
  if (titulo) ctx.entrada(titulo, T.p(t, 'titulo'), ctx.DA.movimento.entrada_padrao, { origem: 'esquerda' });
  const pm = T.p(t, 'mapa');
  malha.style.opacity = (pm * 0.9).toFixed(3);
  territorio.style.opacity = pm.toFixed(3);
  marcas.forEach((m, i) => ctx.entrada(m.el, T.p(t, 'p' + i), 'fade'));
  rotas.forEach((r, i) => {
    const q = T.p(t, 'r' + i);
    r.el.setAttribute('stroke-dasharray', `${r.comp.toFixed(1)} ${r.comp.toFixed(1)}`);
    r.el.setAttribute('stroke-dashoffset', (r.comp * (1 - q)).toFixed(1));
    r.el.style.opacity = q > 0 ? '1' : '0';
  });
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  const fim = S.tRotas + S.rotas.length * S.passo + S.ctx.dur('media');
  return t >= fim + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  const a = S.base.ancoras().concat([{ t: +S.t1.toFixed(3), nome: 'pontos', tipo: 'texto' }]);
  if (S.rotas.length) a.push({ t: +S.tRotas.toFixed(3), nome: 'rotas', tipo: 'enfase' });
  return a;
}
