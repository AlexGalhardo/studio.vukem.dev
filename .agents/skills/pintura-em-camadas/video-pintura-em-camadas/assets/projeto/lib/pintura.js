// pintura.js — estilo "pintura em camadas": uma obra clássica pendurada no museu; a câmera atravessa a
// moldura e passeia DENTRO da pintura, que foi separada em camadas de profundidade (parallax 2.5D),
// com profundidade de campo (frente desfocada, figura principal nítida) e luz quente de museu.
// Global: window.PC. Depende de core.js/kit.js (onTick, K). Tudo é função de t.
(function () {
  const PC = (window.PC = {});
  const W = () => VIDEO.w, H = () => VIDEO.h;

  // ---------- carregar as camadas (saída de tools/camadas.py montar) ----------
  // plano = { pintura:[w,h], extensao:{cima,baixo,lados}, camadas:[{nome,K,arquivo,x,y,w,h,blur?}] }
  PC.carregar = async (url = 'img/camadas-out.json', pasta = 'img/') => {
    const P = await (await fetch(url)).json();
    await Promise.all(P.camadas.map(c => new Promise((ok, erro) => {
      const im = new Image(); im.onload = () => im.decode().then(ok, ok); im.onerror = erro; im.src = pasta + c.arquivo; c.img = im;
    })));
    return P;
  };

  // ---------- curvas de câmera ----------
  // chaves monotônicas: [[t, v], …] → f(t), interpolação cúbica de Fritsch–Carlson (nunca passa do ponto,
  // derivada zero nas pontas). Serve para log da escala, pan e qualquer parâmetro que só vai num sentido.
  PC.chaves = (ks) => {
    const n = ks.length, x = ks.map(k => k[0]), y = ks.map(k => k[1]);
    const d = []; for (let i = 0; i < n - 1; i++) d.push((y[i + 1] - y[i]) / (x[i + 1] - x[i]));
    const m = [0]; for (let i = 1; i < n - 1; i++) m.push(d[i - 1] * d[i] <= 0 ? 0 : (2 * d[i - 1] * d[i]) / (d[i - 1] + d[i])); m.push(0);
    return t => {
      if (t <= x[0]) return y[0]; if (t >= x[n - 1]) return y[n - 1];
      let i = 0; while (t > x[i + 1]) i++;
      const h = x[i + 1] - x[i], s = (t - x[i]) / h, s2 = s * s, s3 = s2 * s;
      return (2 * s3 - 3 * s2 + 1) * y[i] + (s3 - 2 * s2 + s) * h * m[i] + (-2 * s3 + 3 * s2) * y[i + 1] + (s3 - s2) * h * m[i + 1];
    };
  };

  // câmera = { S (px de tela por px da pintura no plano de foco), ax, ay (ponto da pintura no centro da tela),
  //            p (0→1: quanto as camadas já se separaram em profundidade), kw (1→: a moldura voando para fora),
  //            sala (opacidade da parede/moldura) }
  // o.S: [[t, S]…]  o.A: [[t, x, y]…]  o.sep: [t0, t1]  o.atravessa: [t0, t1]  o.voo  o.dissolve: [t0, t1]
  PC.camera = (o) => {
    const lS = PC.chaves(o.S.map(([t, v]) => [t, Math.log(v)]));
    const ax = PC.chaves(o.A.map(([t, x]) => [t, x])), ay = PC.chaves(o.A.map(([t, , y]) => [t, y]));
    const [p0, p1] = o.sep ?? [2, 6.4], [w0, w1] = o.atravessa ?? [1.9, 3], [d0, d1] = o.dissolve ?? [2, 2.9];
    return t => ({
      S: Math.exp(lS(t)), ax: ax(t), ay: ay(t),
      p: K.ease(o.sepEase ?? 'power1.in', K.seg(t, p0, p1)),
      kw: 1 + (o.voo ?? 1.6) * Math.pow(K.smooth(K.seg(t, w0, w1)), 1.6),
      sala: 1 - K.smooth(K.seg(t, d0, d1)),
    });
  };

  // ---------- palco: canvas onde as camadas são desenhadas a cada quadro ----------
  // o = { dof: desfoque máximo (px de tela) por unidade de |1-1/K|, foco: K do plano nítido (1) }
  PC.palco = (stage, P, o = {}) => {
    const cv = document.createElement('canvas'); cv.width = W(); cv.height = H(); cv.className = 'pc-mundo'; stage.appendChild(cv);
    cv.style.cssText = `position:absolute;left:0;top:0;filter:${o.grade ?? 'contrast(1.05) saturate(1.06)'}`;   // leve correção de cor
    const x = cv.getContext('2d');
    x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
    const dof = o.dof ?? 30, foco = o.foco ?? 1;
    const desenha = (c, cam) => {
      const k = Math.pow(c.K / foco, cam.p);
      const sc = cam.S * k;
      const tx = W() / 2 + (c.x - cam.ax) * sc + (c.dx || 0), ty = H() / 2 + (c.y - cam.ay) * sc + (c.dy || 0);
      const bl = (c.blur ?? dof * Math.abs(1 - foco / c.K)) * cam.p + (c.blurExtra || 0);
      // o filtro do canvas age em px de tela: o raio NÃO é multiplicado pela escala
      x.filter = bl > .35 ? `blur(${bl.toFixed(2)}px)` : 'none';
      x.globalAlpha = c.alpha ?? 1;
      x.drawImage(c.img, tx, ty, c.w * sc, c.h * sc);
      x.filter = 'none'; x.globalAlpha = 1;
      return { sc, tx, ty, bl };
    };
    return {
      el: cv, ctx: x,
      // desenha todas as camadas (de trás para a frente) e devolve o estado de cada uma
      quadro(cam, antes) { x.setTransform(1, 0, 0, 1, 0, 0); x.clearRect(0, 0, W(), H()); return P.camadas.map(c => { antes && antes(c, cam); return desenha(c, cam); }); },
      // converte um ponto da pintura no plano de profundidade K para a tela
      tela(px, py, cam, Kc = foco) { const sc = cam.S * Math.pow(Kc / foco, cam.p); return [W() / 2 + (px - cam.ax) * sc, H() / 2 + (py - cam.ay) * sc, sc]; },
    };
  };

  // ---------- moldura dourada (gerada em canvas, cantos em meia-esquadria, luz de cima) ----------
  // devolve um canvas do tamanho (w+2b) × (h+2b) em "px de pintura" × res, com o vão transparente
  PC.moldura = (w, h, b, o = {}) => {
    const res = o.res ?? .5, r = K.rng(o.seed ?? 5);
    const cw = Math.round((w + 2 * b) * res), ch = Math.round((h + 2 * b) * res), B = b * res;
    const c = document.createElement('canvas'); c.width = cw; c.height = ch; const x = c.getContext('2d');
    // perfil: fração da largura da moldura → cor base (do lado de fora para o vão)
    const perfil = o.perfil || [
      [0, .00, '#2a1a08'], [.03, .06, '#7a5a22'], [.06, .14, '#e6c776'], [.14, .2, '#9a7330'], [.2, .34, '#6b4a1a'],
      [.34, .44, '#d9b55e'], [.44, .5, '#f6e3a0'], [.5, .62, '#b48a3a'], [.62, .74, '#5a3c14'], [.74, .84, '#c9a24f'],
      [.84, .9, '#f0d68c'], [.9, .96, '#8a6526'], [.96, 1, '#24170a']];
    // luz de cada lado (cima clara, baixo escura)
    const luz = { cima: 1.18, esq: 1.0, dir: .86, baixo: .7 };
    const lados = [
      ['cima', [[0, 0], [cw, 0], [cw - B, B], [B, B]], (f) => [0, f * B, cw, f * B]],
      ['baixo', [[0, ch], [cw, ch], [cw - B, ch - B], [B, ch - B]], (f) => [0, ch - f * B, cw, ch - f * B]],
      ['esq', [[0, 0], [B, B], [B, ch - B], [0, ch]], (f) => [f * B, 0, f * B, ch]],
      ['dir', [[cw, 0], [cw - B, B], [cw - B, ch - B], [cw, ch]], (f) => [cw - f * B, 0, cw - f * B, ch]],
    ];
    const tom = (hex, k) => { const n = parseInt(hex.slice(1), 16); const f = v => Math.max(0, Math.min(255, Math.round(v * k))); return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`; };
    for (const [nome, poly, linha] of lados) {
      x.save(); x.beginPath(); poly.forEach(([a, b2], i) => (i ? x.lineTo(a, b2) : x.moveTo(a, b2))); x.closePath(); x.clip();
      const [x0, y0] = linha(0), [x1, y1] = linha(1);
      const g = x.createLinearGradient(nome === 'esq' || nome === 'dir' ? x0 : 0, nome === 'cima' || nome === 'baixo' ? y0 : 0, nome === 'esq' || nome === 'dir' ? x1 : 0, nome === 'cima' || nome === 'baixo' ? y1 : 0);
      for (const [a, z, cor] of perfil) { g.addColorStop(a, tom(cor, luz[nome])); g.addColorStop(Math.min(1, z), tom(cor, luz[nome] * .96)); }
      x.fillStyle = g; x.fillRect(0, 0, cw, ch);
      // ornamento: contas (pérolas) na faixa .44–.5 e folhas na faixa .74–.84
      const horiz = nome === 'cima' || nome === 'baixo';
      const L = horiz ? cw : ch, passo = Math.max(6, B * .09);
      for (let s = 0; s < L; s += passo) {
        const f = .47, q = horiz ? [s, nome === 'cima' ? f * B : ch - f * B] : [nome === 'esq' ? f * B : cw - f * B, s];
        const rr = B * .028; const gg = x.createRadialGradient(q[0] - rr * .3, q[1] - rr * .4, rr * .1, q[0], q[1], rr);
        gg.addColorStop(0, tom('#fff2bf', luz[nome])); gg.addColorStop(.6, tom('#c99d45', luz[nome])); gg.addColorStop(1, tom('#4a3210', luz[nome]));
        x.fillStyle = gg; x.beginPath(); x.arc(q[0], q[1], rr, 0, 7); x.fill();
      }
      for (let s = 0; s < L; s += passo * 2.2) {
        const f = .79, q = horiz ? [s, nome === 'cima' ? f * B : ch - f * B] : [nome === 'esq' ? f * B : cw - f * B, s];
        x.save(); x.translate(q[0], q[1]); if (!horiz) x.rotate(Math.PI / 2);
        x.fillStyle = tom('#f3db92', luz[nome]); x.beginPath(); x.ellipse(0, 0, passo * .9, B * .035, 0, 0, 7); x.fill();
        x.fillStyle = tom('#6b4a18', luz[nome]); x.beginPath(); x.ellipse(passo * .2, B * .012, passo * .5, B * .012, 0, 0, 7); x.fill();
        x.restore();
      }
      x.restore();
    }
    // cantos: rosetas
    for (const [a, b2] of [[B / 2, B / 2], [cw - B / 2, B / 2], [B / 2, ch - B / 2], [cw - B / 2, ch - B / 2]]) {
      const g = x.createRadialGradient(a - B * .06, b2 - B * .08, B * .02, a, b2, B * .3);
      g.addColorStop(0, '#fff0b8'); g.addColorStop(.35, '#d4ab55'); g.addColorStop(.75, '#7a561e'); g.addColorStop(1, 'rgba(60,40,10,0)');
      x.fillStyle = g; x.beginPath(); x.arc(a, b2, B * .3, 0, 7); x.fill();
    }
    // douramento gasto: pintinhas claras/escuras + manchas largas
    x.save(); x.beginPath(); x.rect(0, 0, cw, ch); x.rect(B, B, cw - 2 * B, ch - 2 * B); x.clip('evenodd');
    for (let i = 0; i < cw * ch / 900; i++) { const v = r(); x.fillStyle = v < .5 ? `rgba(40,25,5,${r() * .18})` : `rgba(255,240,190,${r() * .16})`; x.fillRect(r() * cw, r() * ch, 1 + r() * 2, 1 + r() * 2); }
    for (let i = 0; i < 40; i++) { const a = r() * cw, b2 = r() * ch, rr = B * (.2 + r() * .6); const g = x.createRadialGradient(a, b2, 0, a, b2, rr); g.addColorStop(0, `rgba(50,30,8,${.08 + r() * .1})`); g.addColorStop(1, 'rgba(50,30,8,0)'); x.fillStyle = g; x.fillRect(a - rr, b2 - rr, rr * 2, rr * 2); }
    x.restore();
    // sombra interna da moldura sobre a tela (o vão fica transparente; a sombra é desenhada pelo palco)
    return { canvas: c, res, b };
  };

  // ---------- sala de museu: parede com vão (a pintura aparece por trás), moldura, foco de luz ----------
  // desenhada no MESMO canvas do palco, por cima das camadas, com a escala da moldura (S·kw) e opacidade cam.sala
  PC.sala = (palco, P, o = {}) => {
    const [pw, ph] = P.pintura, b = o.borda ?? 170;
    const mold = PC.moldura(pw, ph, b, o.moldura || {});
    const parede = o.parede ?? ['#4a1d16', '#2a0f0b', '#120605'];
    return (cam, t = 0) => {
      if (cam.sala <= 0.002) return;
      const x = palco.ctx, sc = cam.S * cam.kw;
      const X = v => W() / 2 + (v - cam.ax) * sc, Y = v => H() / 2 + (v - cam.ay) * sc;
      x.save(); x.globalAlpha = cam.sala;
      // parede com o vão da obra
      const cx = X(pw / 2), cy = Y(ph * .2);
      const g = x.createRadialGradient(cx, cy, 10, cx, cy, Math.max(W(), H()) * 1.1 * Math.max(1, cam.kw * .8));
      g.addColorStop(0, parede[0]); g.addColorStop(.45, parede[1]); g.addColorStop(1, parede[2]);
      x.fillStyle = g; x.beginPath(); x.rect(-10, -10, W() + 20, H() + 20); x.rect(X(-2), Y(-2), (pw + 4) * sc, (ph + 4) * sc); x.fill('evenodd');
      // sombra da moldura na parede (luz de cima → sombra para baixo)
      x.shadowColor = 'rgba(0,0,0,.55)'; x.shadowBlur = 38 * sc / .25; x.shadowOffsetY = 26 * sc / .25;
      x.drawImage(mold.canvas, X(-b), Y(-b), (pw + 2 * b) * sc, (ph + 2 * b) * sc);
      x.shadowColor = 'transparent';
      // brilho que corre no dourado conforme a câmera anda (reflexo do spot na moldura)
      if (o.brilho) {
        const u = K.seg(t, o.brilho[0], o.brilho[1]), gx = X(-b) + (pw + 2 * b) * sc * (-.3 + 1.6 * u);
        x.save(); x.beginPath(); x.rect(X(-b), Y(-b), (pw + 2 * b) * sc, (ph + 2 * b) * sc); x.rect(X(0), Y(0), pw * sc, ph * sc); x.clip('evenodd');
        const lg = x.createLinearGradient(gx - 260, Y(-b), gx + 260, Y(ph + b));
        lg.addColorStop(0, 'rgba(255,240,200,0)'); lg.addColorStop(.5, `rgba(255,240,200,${o.brilhoA ?? .45})`); lg.addColorStop(1, 'rgba(255,240,200,0)');
        x.globalCompositeOperation = 'lighter'; x.fillStyle = lg; x.fillRect(X(-b), Y(-b), (pw + 2 * b) * sc, (ph + 2 * b) * sc); x.restore();
      }
      // sombra interna: a moldura projeta uma faixa escura sobre a tela, mais forte no alto
      const si = x.createLinearGradient(0, Y(0), 0, Y(ph * .12));
      si.addColorStop(0, 'rgba(20,10,3,.55)'); si.addColorStop(1, 'rgba(20,10,3,0)');
      x.fillStyle = si; x.fillRect(X(0), Y(0), pw * sc, ph * .12 * sc);
      // luz de museu sobre a tela: mais clara no alto/centro, cantos de baixo apagados
      const lz = x.createRadialGradient(X(pw / 2), Y(-ph * .15), 0, X(pw / 2), Y(-ph * .15), ph * 1.45 * sc);
      lz.addColorStop(0, 'rgba(255,225,170,.0)'); lz.addColorStop(.55, 'rgba(30,15,5,0)'); lz.addColorStop(1, 'rgba(30,15,5,.42)');
      x.fillStyle = lz; x.fillRect(X(0), Y(0), pw * sc, ph * sc);
      x.restore();
    };
  };

  // ---------- poeira no facho de luz / no ar da cena (bokeh suave, com profundidade) ----------
  PC.poeira = (stage, o = {}) => {
    const c = document.createElement('canvas'); c.width = W(); c.height = H(); c.className = 'pc-poeira'; stage.appendChild(c);
    c.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none';
    const x = c.getContext('2d'), r = K.rng(o.seed ?? 21), n = o.n ?? 70;
    const ps = Array.from({ length: n }, () => ({ x: r() * 1.6 - .3, y: r() * 1.4 - .2, z: .35 + r() * 1.6, f: r() * 6.28, v: .5 + r() }));
    return (t, cam, z0 = 1) => {
      x.clearRect(0, 0, W(), H());
      const Z = cam.S / (o.S0 ?? cam.S);                                   // quanto a câmera já entrou
      for (const p of ps) {
        const k = Math.pow(Z, 1 / p.z * .9);                               // perto (z pequeno) cresce mais rápido
        let px = .5 + (p.x - .5) * k + Math.sin(t * .35 * p.v + p.f) * .012, py = .5 + (p.y - .5) * k - t * .006 * p.v + Math.cos(t * .3 + p.f) * .008;
        if (px < -.1 || px > 1.1 || py < -.1 || py > 1.1) continue;
        const rad = (o.r ?? 2.2) * k / p.z * (p.z < .7 ? 3 : 1), a = (o.a ?? .35) * Math.min(1, .5 / Math.abs(p.z - z0) + .2) * (p.z < .7 ? .35 : 1);
        const g = x.createRadialGradient(px * W(), py * H(), 0, px * W(), py * H(), rad);
        g.addColorStop(0, `rgba(255,236,196,${a})`); g.addColorStop(1, 'rgba(255,236,196,0)');
        x.fillStyle = g; x.fillRect(px * W() - rad, py * H() - rad, rad * 2, rad * 2);
      }
    };
  };

  // ---------- placa de museu presa na parede (mesma escala e opacidade da sala) ----------
  // el: <div> com o texto da placa; pos: {x, y} em px da pintura (canto sup. esquerdo da placa)
  PC.placa = (el, pos) => (cam) => {
    const sc = cam.S * cam.kw;
    el.style.transformOrigin = '0 0';
    el.style.transform = `translate(${(W() / 2 + (pos.x - cam.ax) * sc).toFixed(2)}px,${(H() / 2 + (pos.y - cam.ay) * sc).toFixed(2)}px) scale(${sc.toFixed(5)})`;
    el.style.opacity = cam.sala;
  };

  // ---------- título final: sobrelinha que fecha o espaçamento, nome que desfoca para nítido, fio que abre ----------
  // root contém .sobre .nome .fio .sob (todas opcionais)
  PC.titulo = (root, t0, o = {}) => {
    const q = s => root.querySelector(s);
    if (q('.sobre')) TL.fromTo(q('.sobre'), { opacity: 0, letterSpacing: o.de ?? '.6em' }, { opacity: 1, letterSpacing: o.ate ?? '.34em', duration: .7, ease: 'power3.out', immediateRender: true }, t0);
    if (q('.nome')) TL.fromTo(q('.nome'), { opacity: 0, y: 26, filter: 'blur(10px)' }, { opacity: 1, y: 0, filter: 'blur(0px)', duration: .75, ease: 'power3.out', immediateRender: true }, t0 + .1);
    if (q('.fio')) TL.fromTo(q('.fio'), { width: 0 }, { width: o.fio ?? 420, duration: .7, ease: 'power2.inOut', immediateRender: true }, t0 + .3);
    if (q('.sob')) TL.fromTo(q('.sob'), { opacity: 0 }, { opacity: 1, duration: .5, ease: 'power1.out', immediateRender: true }, t0 + .45);
  };

  // ---------- som do estilo: sala de museu → atravessa a moldura → dentro da cena → chegada ----------
  // T = { entra (a moldura começa a voar), para (a câmera para), fim (dur do vídeo) }
  // o.cena: 'galope' | 'vento' | null — o que se ouve dentro da tela (além do vento)
  PC.som = (T, o = {}) => {
    cue('m:intro', 0); cue('m:build', T.entra + .3); cue('m:drop', T.para); cue('m:stop', T.fim - .2);
    cue('sala', 0, { d: T.entra + 1 });
    [.1, .63, 1.16].filter(t => t < T.entra - .3).forEach((t, i) => cue('passo', t, { pan: i % 2 ? .15 : -.15, gain: -1.5 * i }));
    cue('passagem', T.entra - .2, { d: 1.7 });
    cue('vento', T.entra + .25, { d: T.fim - T.entra - .2 });
    if ((o.cena ?? 'galope') === 'galope') cue('galope', T.entra + .55, { d: T.para - T.entra - .55 });
    cue('rufo', T.para - .95, { d: .95 }); cue('timpano', T.para);
  };

  // ---------- acabamento de museu: vinheta quente, véu de luz, grão ----------
  PC.acabamento = (stage, o = {}) => {
    const v = document.createElement('div'); v.className = 'pc-vinheta'; stage.appendChild(v);
    v.style.cssText = `position:absolute;inset:0;pointer-events:none;background:radial-gradient(120% 85% at 50% 42%, rgba(0,0,0,0) 55%, rgba(18,8,3,${o.vinheta ?? .55}) 100%)`;
    const l = document.createElement('div'); l.className = 'pc-luz'; stage.appendChild(l);
    l.style.cssText = `position:absolute;inset:0;pointer-events:none;mix-blend-mode:soft-light;background:radial-gradient(90% 60% at 50% 30%, rgba(255,214,150,${o.luz ?? .35}), rgba(255,214,150,0) 70%)`;
    if (o.grao !== 0) K.grain(stage, { opacity: o.grao ?? .07, w: 540, blend: 'overlay' });
    return { vinheta: v, luz: l };
  };

  // ---------- facho de luz do museu (cone suave vindo de cima) ----------
  PC.facho = (stage) => {
    const f = document.createElement('div'); f.className = 'pc-facho'; stage.appendChild(f);
    f.style.cssText = 'position:absolute;left:-20%;width:140%;top:-10%;height:80%;pointer-events:none;mix-blend-mode:screen;transform-origin:50% 0;' +
      'background:radial-gradient(40% 100% at 50% 0%, rgba(255,214,160,.22), rgba(255,214,160,0) 100%);clip-path:polygon(38% 0,62% 0,92% 100%,8% 100%);filter:blur(30px)';
    return f;
  };
})();
