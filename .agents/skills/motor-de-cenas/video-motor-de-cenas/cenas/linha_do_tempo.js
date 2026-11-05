// linha_do_tempo.js — trilho com marcos datados, que cresce e acende um marco de cada vez.
import { PARAMS_PALCO, montarPalco, montarChapeu, montarCredito, limitar } from './_comum.js';

export const meta = {
  nome: 'linha_do_tempo',
  descricao: 'Linha do tempo: trilho que cresce e marcos datados que acendem em ordem.',
  dur_padrao: 7,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    marcos: {
      tipo: 'lista', obrigatorio: true, min: 2, max: 7,
      itens: {
        tipo: 'objeto', campos: {
          data: { tipo: 'texto', obrigatorio: true, descricao: 'como a data deve aparecer' },
          texto: { tipo: 'texto', padrao: null, descricao: 'o que aconteceu (curto)' },
          destaque: { tipo: 'booleano', padrao: false },
        },
      },
    },
    titulo: { tipo: 'texto', padrao: null },
    sentido: { tipo: 'opcao', opcoes: ['auto', 'deitado', 'empe'], padrao: 'auto', descricao: 'auto segue a orientação do quadro' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;
  const n = p.marcos.length;
  const deitado = p.sentido === 'deitado' || (p.sentido === 'auto' && ctx.orientacao !== 'vertical');

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

  const campo = { x: 0, y: topo, w: base.area.w, h: Math.max(ctx.px(0.12), base.area.h - topo) };
  const espessura = Math.max(2, ctx.traco * 1.6);
  const bolinha = Math.max(ctx.px(0.012), espessura * 3);

  const trilho = ctx.el('div', 'mc-trilho');
  Object.assign(trilho.style, { position: 'absolute', background: ctx.alfa('texto_suave', 0.45) });
  base.conteudo.appendChild(trilho);

  const marcos = [];
  for (let i = 0; i < n; i++) {
    const mk = p.marcos[i];
    const cor = mk.destaque ? 'primaria' : 'texto';
    const item = ctx.el('div', 'mc-marco');
    Object.assign(item.style, { position: 'absolute', display: 'flex', gap: ctx.px(0.01) + 'px' });
    base.conteudo.appendChild(item);

    const ponto = ctx.el('div', 'mc-ponto');
    Object.assign(ponto.style, {
      width: bolinha + 'px', height: bolinha + 'px', borderRadius: '50%', flex: '0 0 auto',
      background: ctx.cor(cor), boxSizing: 'border-box',
    });
    const texto = ctx.el('div', 'mc-marco-texto');
    Object.assign(texto.style, { display: 'flex', flexDirection: 'column', gap: ctx.px(0.004) + 'px' });

    const largura = deitado ? limitar(campo.w / n - ctx.px(0.02), ctx.px(0.1), campo.w) : campo.w - bolinha - ctx.px(0.03);
    const data = ctx.texto('dados', mk.data, { tam: ctx.tam('corpo'), cor, wrap: true, maxW: largura });
    texto.appendChild(data);
    let corpo = null;
    if (mk.texto) {
      corpo = ctx.texto('corpo', mk.texto, { tam: ctx.tam('nota'), cor: 'texto_suave', wrap: true, maxW: largura });
      texto.appendChild(corpo);
    }
    if (deitado) { item.style.flexDirection = 'column'; item.style.alignItems = 'flex-start'; item.appendChild(ponto); item.appendChild(texto); }
    else { item.appendChild(ponto); item.appendChild(texto); }
    ctx.ajustar_texto(data, largura, { min: ctx.minimo_legivel, maxLinhas: 2 });
    if (corpo) ctx.ajustar_texto(corpo, largura, { min: ctx.minimo_legivel, maxLinhas: 3 });
    marcos.push({ el: item, ponto, largura });
  }

  // posiciona o trilho e os marcos
  let passo;
  if (deitado) {
    const y = Math.round(campo.y + campo.h * 0.40);
    Object.assign(trilho.style, { left: '0px', top: y + 'px', width: campo.w + 'px', height: espessura + 'px', transformOrigin: 'left center' });
    passo = n > 1 ? (campo.w - marcos[n - 1].largura) / (n - 1) : 0;
    marcos.forEach((m, i) => { m.el.style.left = Math.round(i * passo) + 'px'; m.el.style.top = Math.round(y - bolinha / 2) + 'px'; m.el.style.width = Math.round(m.largura) + 'px'; });
  } else {
    const x = Math.round(bolinha / 2 - espessura / 2);
    Object.assign(trilho.style, { left: x + 'px', top: campo.y + 'px', width: espessura + 'px', height: campo.h + 'px', transformOrigin: 'center top' });
    const alturas = marcos.map((m) => m.el.offsetHeight);
    const soma = alturas.reduce((a, b) => a + b, 0);
    const vao = n > 1 ? Math.max(ctx.px(0.012), (campo.h - soma) / (n - 1)) : 0;
    let y = campo.y;
    marcos.forEach((m, i) => { m.el.style.left = '0px'; m.el.style.top = Math.round(y) + 'px'; y += alturas[i] + vao; });
  }

  const credito = montarCredito(ctx, palco, p);
  const e = ctx.escalonamento;
  const dTrilho = ctx.dur('longa');
  const T = ctx.tl().add('chapeu', T0, ctx.dur('media')).add('titulo', T0 + e, ctx.dur('media'))
    .add('trilho', T0 + e * 2, dTrilho, { curva: 'suave' });
  const t1 = T0 + e * 2 + dTrilho * 0.35;
  const passoMarco = Math.max(e * 2, Math.min(ctx.dur('media'), (base.inicio_saida - t1 - ctx.dur('media')) / Math.max(1, n - 1)));
  T.escalonar(marcos.map((_, i) => 'm' + i), t1, ctx.dur('media'), { passo: passoMarco, tipo: 'texto' });
  T.add('credito', t1, ctx.dur('media'));

  Object.assign(S, { ctx, base, chapeu, titulo, trilho, marcos, credito, T, deitado, t1, passoMarco, n });
  return { ...base.layout(), marcos: marcos.map((m) => ({ x: parseFloat(m.el.style.left), y: parseFloat(m.el.style.top) })), sentido: deitado ? 'deitado' : 'empe', fim_entrada: +(t1 + passoMarco * (n - 1) + ctx.dur('media')).toFixed(3) };
}

export function seek(t) {
  const { ctx, base, chapeu, titulo, trilho, marcos, credito, T, deitado } = S;
  base.seek(t);
  if (chapeu) chapeu.seek(T.p(t, 'chapeu'), T.p(t, 'chapeu', 'suave'));
  if (titulo) ctx.entrada(titulo, T.p(t, 'titulo'), ctx.DA.movimento.entrada_padrao, { origem: 'esquerda' });
  const pt = T.p(t, 'trilho');
  trilho.style.opacity = pt > 0 ? '1' : '0';
  trilho.style.transform = deitado ? `scaleX(${pt.toFixed(4)})` : `scaleY(${pt.toFixed(4)})`;
  marcos.forEach((m, i) => ctx.entrada(m.el, T.p(t, 'm' + i), 'fade'));
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  const fim = S.t1 + S.passoMarco * (S.n - 1) + S.ctx.dur('media');
  return t >= fim + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  return S.base.ancoras().concat(S.marcos.map((_, i) => ({ t: +(S.t1 + S.passoMarco * i).toFixed(3), nome: 'marco' + i, tipo: 'texto' })));
}
