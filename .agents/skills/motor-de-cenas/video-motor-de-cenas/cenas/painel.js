// painel.js — pessoas (ou entidades) ligadas por fios: quem conhece quem. Até 6 nós.
import { PARAMS_PALCO, montarPalco, montarChapeu, montarCredito, imagem, esperarImagens, svgDe, fio, limitar } from './_comum.js';

export const meta = {
  nome: 'painel',
  descricao: 'Painel de pessoas ou entidades ligadas por fios, com rótulo nas ligações.',
  dur_padrao: 6,
  formatos: ['horizontal', 'vertical', 'quadrado'],
  alfa_padrao: false,
  grao: true,
  params: {
    pessoas: {
      tipo: 'lista', obrigatorio: true, min: 2, max: 6,
      itens: {
        tipo: 'objeto', campos: {
          nome: { tipo: 'texto', obrigatorio: true },
          cargo: { tipo: 'texto', padrao: null },
          foto: { tipo: 'arquivo', padrao: null },
          destaque: { tipo: 'booleano', padrao: false },
        },
      },
      descricao: 'de 2 a 6 nós do painel',
    },
    ligacoes: {
      tipo: 'lista', padrao: [], max: 10,
      itens: {
        tipo: 'objeto', campos: {
          de: { tipo: 'inteiro', obrigatorio: true, min: 0 },
          para: { tipo: 'inteiro', obrigatorio: true, min: 0 },
          rotulo: { tipo: 'texto', padrao: null },
        },
      },
      descricao: 'fios entre os nós, por índice (0 = o primeiro)',
    },
    titulo: { tipo: 'texto', padrao: null, descricao: 'título acima do painel' },
    ...PARAMS_PALCO,
  },
};

const S = {};

export async function build(palco, p, ctx) {
  const base = montarPalco(ctx, palco, p);
  const T0 = base.t0_conteudo;
  const n = p.pessoas.length;

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

  // grade dos nós: uma fileira até 3, duas acima disso
  const colunas = n <= 3 ? n : Math.ceil(n / 2);
  const fileiras = n <= 3 ? 1 : 2;
  const campo = { x: 0, y: topo, w: base.area.w, h: Math.max(ctx.px(0.1), base.area.h - topo) };
  const celulaL = campo.w / colunas, celulaA = campo.h / fileiras;
  const diam = Math.round(limitar(Math.min(celulaL * 0.52, celulaA * 0.46), ctx.px(0.06), ctx.px(0.17)));

  const tela = svgDe(ctx, base.area.w, base.area.h);
  base.conteudo.appendChild(tela);

  const nos = [];
  for (let i = 0; i < n; i++) {
    const pessoa = p.pessoas[i];
    const col = i % colunas, lin = Math.floor(i / colunas);
    const cx = campo.x + celulaL * (col + 0.5);
    const cy = campo.y + celulaA * (lin + 0.42);

    const no = ctx.el('div', 'mc-no');
    Object.assign(no.style, { position: 'absolute', left: Math.round(cx - celulaL / 2) + 'px', top: Math.round(cy - diam / 2) + 'px', width: Math.round(celulaL) + 'px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: ctx.px(0.012) + 'px' });
    base.conteudo.appendChild(no);

    const disco = ctx.el('div', 'mc-disco');
    Object.assign(disco.style, {
      width: diam + 'px', height: diam + 'px', borderRadius: '50%', overflow: 'hidden', boxSizing: 'border-box',
      background: ctx.cor('fundo'), borderStyle: 'solid', borderWidth: Math.max(2, ctx.traco * 2).toFixed(1) + 'px',
      borderColor: ctx.cor(pessoa.destaque ? 'primaria' : 'texto_suave'),
      display: 'flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto',
    });
    no.appendChild(disco);
    if (pessoa.foto) {
      disco.appendChild(imagem(ctx, pessoa.foto, `foto de ${pessoa.nome}`));
    } else {
      const sigla = ctx.texto('dados', iniciais(pessoa.nome), { tam: diam * 0.34, cor: pessoa.destaque ? 'primaria' : 'texto_suave' });
      disco.appendChild(sigla);
    }

    const nome = ctx.texto('subtitulo', pessoa.nome, { tam: ctx.tam('nota'), wrap: true, maxW: celulaL * 0.92, alinhar: 'centro', cor: 'texto' });
    no.appendChild(nome);
    ctx.ajustar_texto(nome, celulaL * 0.92, { min: ctx.minimo_legivel, maxLinhas: 2 });
    let cargo = null;
    if (pessoa.cargo) {
      cargo = ctx.texto('corpo', pessoa.cargo, { tam: ctx.tam('nota') * 0.88, cor: 'texto_suave', wrap: true, maxW: celulaL * 0.92, alinhar: 'centro' });
      no.appendChild(cargo);
      ctx.ajustar_texto(cargo, celulaL * 0.92, { min: ctx.minimo_legivel, maxLinhas: 2 });
    }
    nos.push({ el: no, cx, cy, destaque: !!pessoa.destaque });
  }
  await esperarImagens(base.conteudo);

  const fios = [];
  for (const lig of p.ligacoes || []) {
    const a = nos[lig.de], b = nos[lig.para];
    if (!a || !b || a === b) continue;
    const f = fio(ctx, tela, a.cx, a.cy, b.cx, b.cy, { cor: 'primaria', alfa: 0.75 });
    let rot = null;
    if (lig.rotulo) {
      rot = ctx.texto('dados', lig.rotulo, { tam: ctx.tam('nota') * 0.85, cor: 'texto_suave' });
      Object.assign(rot.style, { position: 'absolute', background: ctx.cor('fundo'), padding: `${ctx.px(0.004).toFixed(1)}px ${ctx.px(0.008).toFixed(1)}px` });
      base.conteudo.appendChild(rot);
      const m = ctx.medir(rot);
      rot.style.left = Math.round((a.cx + b.cx) / 2 - m.w / 2) + 'px';
      rot.style.top = Math.round((a.cy + b.cy) / 2 - m.h / 2) + 'px';
    }
    fios.push({ f, rot });
  }

  const credito = montarCredito(ctx, palco, p);
  const e = ctx.escalonamento;
  const T = ctx.tl().add('chapeu', T0, ctx.dur('media')).add('titulo', T0 + e, ctx.dur('media'));
  T.escalonar(nos.map((_, i) => 'no' + i), T0 + e * 3, ctx.dur('media'), { passo: e * 1.6 });
  const tFios = T0 + e * 3 + e * 1.6 * n + ctx.dur('curta');
  T.escalonar(fios.map((_, i) => 'fio' + i), tFios, ctx.dur('media'), { passo: e * 2, tipo: 'enfase' });
  T.add('credito', tFios, ctx.dur('media'));

  Object.assign(S, { ctx, base, chapeu, titulo, nos, fios, credito, T, tFios });
  return {
    ...base.layout(), nos: nos.map((no) => ({ cx: Math.round(no.cx), cy: Math.round(no.cy) })), diametro: diam,
    ligacoes: fios.length, fim_entrada: +(tFios + ctx.dur('media')).toFixed(3),
  };
}

function iniciais(nome) {
  return String(nome).trim().split(/\s+/).filter((w) => w.length > 2 || /^[A-ZÁÉÍÓÚÂÊÔÃÕÇ]/.test(w)).slice(0, 2).map((w) => w[0]).join('').toUpperCase() || String(nome)[0].toUpperCase();
}

export function seek(t) {
  const { ctx, base, chapeu, titulo, nos, fios, credito, T } = S;
  base.seek(t);
  if (chapeu) chapeu.seek(T.p(t, 'chapeu'), T.p(t, 'chapeu', 'suave'));
  if (titulo) ctx.entrada(titulo, T.p(t, 'titulo'), ctx.DA.movimento.entrada_padrao, { origem: 'esquerda' });
  nos.forEach((no, i) => ctx.entrada(no.el, T.p(t, 'no' + i), 'fade'));
  fios.forEach((f, i) => {
    const p = T.p(t, 'fio' + i, 'suave');
    f.f.seek(p);
    if (f.rot) ctx.entrada(f.rot, ctx.clamp((p - 0.6) / 0.4, 0, 1), 'fade');
  });
  if (credito) credito.seek(T.p(t, 'credito'));
}

export function key(t) {
  const fim = S.tFios + S.ctx.dur('media') + S.ctx.escalonamento * 2 * S.fios.length;
  return t >= fim + 0.05 && t < S.base.inicio_saida ? 'parado' : null;
}

export function ancoras() {
  return S.base.ancoras().concat(S.fios.length ? [{ t: +S.tFios.toFixed(3), nome: 'fios', tipo: 'enfase' }] : []);
}
