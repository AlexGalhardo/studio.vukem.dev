# Receitas: como fazer cada peça

## Sumário
1. Fotos: a do usuário ou o retrato gerado por código
2. Página: esqueleto
3. API de `lib/dossie.js` (`DS`)
4. Trocar o caso do exemplo, passo a passo
5. Mais páginas, papel escuro e 16:9
6. Problemas comuns

## 1. Fotos

**Foto do usuário** (ou de domínio público/licença livre, com crédito no rodapé):

```bash
P=<o PYTHON= do projeto.py>; I=videos/02-caso/img; mkdir -p $I
$P tools/dossie.py xerox ~/foto.jpg $I/sujeito.png --largura 500                 # 3x4, xerox padrão
$P tools/dossie.py xerox ~/foto.jpg $I/sujeito.png --largura 500 --foco .5,.35 --contraste 2 --grao .3
$P tools/dossie.py xerox ~/foto.jpg $I/sujeito.png --modo meiotom --reticula 5    # retícula de jornal
```

- `--largura` = largura da foto na página (500 na ficha, 400–440 no mural). `--proporcao 3x4` recorta em volta de `--foco x,y` (fração da imagem; ponha no meio do rosto). `--proporcao livre` não recorta.
- `--contraste` 1,4–2,2; `--gama` < 1 clareia, > 1 escurece; `--toner` (0–0,5) empelota os meios-tons; `--borrao` amacia antes do contraste; `--modo limiar` dá preto e branco puros.
- Na página: `const F = DS.foto(pai, {src: 'img/sujeito.png', x, y, w: 500, h: 667, …})` e ajuste a tarja: `F.olhos({t0, y: F.h * .36, h: F.h * .1})` (a linha dos olhos muda de foto para foto; confira num `--at`).

**Sem foto** (padrão, e sempre em caso fictício): `DS.foto(pai, {seed: 7, retrato: {cabelo: 'curto', roupa: 'terno'}})`. `cabelo`: `curto`, `franja`, `longo`, `calvo`; `roupa`: `terno`, `camiseta`, `camisa`; `seed` muda proporções, tons e o lado da luz. É uma mancha de xerox, não um rosto: funciona com os olhos tarjados.

## 2. Página: esqueleto

```html
<script>VIDEO={w:1080,h:1920,fps:30,dur:11,bpm:90,music:{style:'dossie',key:'D',gain:0}}</script>
<script>LIBS=['dossie.js']</script>
<script src="../../lib/boot.js"></script>
<style>#stage{background:#0d0d0d;overflow:hidden} :root{--ds-acento:#d8481e}</style>
<div id="stage"></div>
<script>
const T = { /* tempos */ };
window.SETUP = () => {                               // TUDO aqui dentro (as fontes já carregaram)
  const S = document.querySelector('#stage');
  const m1 = DS.mundo(S, { w: 1080, h: 1920 });      // página 1: a folha
  DS.papel(m1, { x: -8, y: -8, w: 1096, h: 1936, seed: 4, furos: true, verso: true });
  /* peças da ficha … */  DS.camera(m1, [ /* chaves */ ]);
  const m2 = DS.mundo(S, { w: 2000, h: 3556 });      // página 2: o mural
  DS.papel(m2, { w: 2000, h: 3556, seed: 9, vinco: [.34, .68] });
  /* peças do painel … */  DS.camera(m2, [ /* chaves */ ], { seed: 2 });
  DS.paginas([[0, m1], [T.corte, m2]]);              // quem aparece quando (corte seco em negativo)
  DS.scanner(S, { t0: .05, d: .85 }); DS.grao(S, { opacity: .16 }); DS.vinheta(S, .3);
  DS.rodape(S, 'Fonte: … (ou: CASO FICTÍCIO · NOMES E FATOS INVENTADOS)');
  cue('m:ficha', 0); cue('m:painel', T.corte); cue('m:fim', T.tit); cue('m:stop', VIDEO.dur - .4);
};
</script>
```

A ordem importa: mundos primeiro (o segundo fica por cima), depois `paginas`, e por último as camadas de tela (scanner, grão, vinheta, rodapé).

## 3. API de `lib/dossie.js` (`DS`)

Todas as peças recebem `t0` (quando entram) e posição em px do **pai** (o mundo, ou outra peça). As que batem ou riscam marcam o próprio som.

**Palco e câmera**

| função | o que faz |
|---|---|
| `DS.mundo(stage, {w, h})` | plano onde as peças vivem (folha ou mural) |
| `DS.camera(mundo, [{t, x, y, z, ease, corte}], {tremor: 1.1, giro: .05, seed})` | câmera de mesa: ponto do mundo no centro da tela + zoom; tremor a 12 qps; sacode nas batidas |
| `DS.paginas([[t0, mundo], …], {flash: 'neg', quadros: 2})` | troca de página em corte seco, com 2 quadros em negativo |
| `DS.scanner(stage, {t0, d: .8, larg: 280, forca: .8, dir: 1})` | passada de luz (`dir: -1` sobe) |
| `DS.grao(stage, {opacity: .2})` · `DS.vinheta(stage, .3)` | grão animado em degraus · bordas escuras |
| `DS.rodape(stage, texto, {t0, cor})` | linha fixa no rodapé da tela: fonte, crédito ou aviso de ficção |

**1. Papel** — `DS.papel(pai, {x, y, w, h, tom: 'claro'|'escuro', seed, bandas: 1, manchas: 1, riscos: 1, grao: 1, borda: 1, vinco: [.5], furos, verso, base})`. Os multiplicadores aceitam 0 (desliga) a 2. `vinco` é uma lista de frações da altura (`false` tira). Devolve o elemento; peças postas **dentro** de um papel escuro saem em tinta clara.

**2. Tarja** — `DS.tarja(pai, {x, y, w, h: 44, t0, tipo: 'marcador'|'fita', seed, rot, d, cor})` → `{el, fim}`. Para texto, prefira as tarjas embutidas (abaixo); esta é para pôr à mão sobre qualquer coisa.

**3. Foto de ficha** — `DS.foto(pai, {x, y, w: 500, h, src | seed + retrato: {cabelo, roupa}, t0, rot, copias: [{dx, dy, op}], cruzes: true, fita: false, moldura: 0})` → `{el, x, y, w, h, pino, olhos(), medida()}`.
- `F.olhos({t0, tipo: 'fita', y, h, x, w})`: tarja sobre os olhos (padrão: `y = 33,5%` da altura, para o retrato procedural).
- `F.medida('REG. 3×4 — FRONTAL')`: linha tracejada com batentes e rótulo acima da foto.
- `DS.retrato({w, h, seed, cabelo, roupa})` devolve o canvas, se quiser usar o retrato em outro lugar.

**4. Digital** — `DS.digital(pai, {x, y, w: 260, seed, tipo: 'laco'|'espiral'|'arco', t0, rot, rotulo, caixa, cristas: 25})`.

**5. Painel**

| função | o que faz |
|---|---|
| `DS.cartao(pai, {x, y, w: 420, sub, titulo, linhas: ['… [[tarjado]] …'], fs: 24, t0, rot, alfinete: true, tom: 'claro'|'escuro', seed})` → `{el, pino, w, h, fim}` | cartão de papel com tarjas embutidas |
| `DS.etiqueta(pai, {x, y, texto, sub, n, fs: 46, t0, cor})` | etiqueta de nome (bloco chapado, texto vazado, número) |
| `DS.alfinete(pai, {x, y, t0})` | alfinete solto (o cartão já traz o dele; a foto não) |
| `DS.fio(pai, {de, para, t0, d, cor, esp: 2.2, queda: .03})` → `{fim}` | fio entre dois pontos `[x, y]` ou peças com `.pino` (foto, cartão) |

**6. Ficha**

| função | o que faz |
|---|---|
| `DS.ficha(pai, {x, y, fs: 36, lh, t0, cps: 36, campos: [{r, v, tarja, forte}]})` → `{linhas, fim, caixa(i)}` | campos datilografados; `tarja: true` = o valor nasce tarjado (largura do valor); `tarja: 8` = tarja de 8 caracteres; `tarja: 'depois'` = datilografa e risca; `caixa(i)` devolve o retângulo do valor (para circular ou sublinhar) |
| `DS.rotulo(pai, 'texto' | ['linha 1', 'linha 2'], {x, y, fs: 20, t0, peso})` | rótulo em mono, datilografado rápido e sem som |
| `DS.codigo(pai, 'RL-0417', {x, y, fs: 150, t0, rotulo: 'ID DO SUJEITO'})` | código grande, batido caractere a caractere |
| `DS.colunas(pai, {x, y, n: 12, cols: 1, larg: 120, fs: 15, t0, seed, itens})` | colunas de números miúdos (códigos sem sentido, a menos que você passe `itens`) |
| `DS.regua(pai, {x, y, w, t0, vertical, numeros})` · `DS.cruz(pai, {x, y, s: 22, t0})` · `DS.medida(pai, {x0, y0, x1, y1, texto, t0})` | régua graduada · cruz de registro · linha de medida |

**7. Anotação à mão** (todas aceitam `t0, d, esp, cor, seed`)

| função | o que desenha |
|---|---|
| `DS.garrancho(pai, {x, y, w: 300, alt: 16, linhas: 1})` | linhas de "escrita" ilegível; `alt` é a altura da letra |
| `DS.circulo(pai, {x, y, w, h})` | elipse de caneta em volta de um retângulo |
| `DS.sublinhado(pai, {x, y, w, duplo})` · `DS.seta(pai, {x0, y0, x1, y1, curva: .25})` | sublinhado · seta curva com ponta |
| `DS.assinatura(pai, {x, y, w: 260, h: 90})` · `DS.traco(pai, [[x, y], …])` | rubrica genérica · traço livre |

**8. Carimbo** — `DS.carimbo(pai, {texto, sub, cx, cy (ou x, y), fs: 64, rot: -8, t0, seed, falha: 1, fonte: 'grot'|'mono', cor})`. `falha` < 1 deixa mais legível; > 1, mais gasto.

**Texto** — `DS.titulo(pai, ['LINHA 1', 'LINHA 2'], {x, y, fs: 150, maxw, t0, passo: .14})` (grotesca pesada, uma linha por batida) e `DS.texto(pai, '“citação com [[trecho tarjado]]”', {x, y, w, fs: 34, fonte: 'serif'|'mono'|'grot', italico, t0, pps: 14})`.

Exemplos curtos:

```js
// ficha com um valor circulado à mão
const fi = DS.ficha(m1, { x: 84, y: 1195, fs: 36, lh: 62, t0: 1, cps: 50, campos: [
  { r: 'NOME', v: 'FULANO DE TAL', tarja: true }, { r: 'SITUAÇÃO', v: 'DESAPARECIDO', forte: true } ] });
const c = fi.caixa(1); DS.circulo(m1, { x: c.x - 10, y: c.y - 4, w: c.w + 20, h: c.h + 8, t0: fi.fim + .2 });

// foto no mural com alfinete, etiqueta e fio até um cartão
const f = DS.foto(m2, { x: 150, y: 420, w: 440, h: 560, seed: 7, t0: 5.1, rot: -1.2, cruzes: false, moldura: 10 });
DS.alfinete(m2, { x: f.pino[0], y: f.pino[1], t0: 5.2 });
DS.etiqueta(m2, { x: 150, y: 290, texto: 'Nome Sobrenome', sub: 'papel no caso', n: 1, fs: 60, t0: 5.3 });
const k = DS.cartao(m2, { x: 640, y: 300, w: 420, fs: 28, sub: 'LOCAL', titulo: 'Usina 3', linhas: ['Painel de [[controle]] aberto.'], t0: 5.4 });
DS.fio(m2, { de: f, para: k, t0: 5.7 });
```

## 4. Trocar o caso do exemplo, passo a passo

1. `cp -R videos/exemplo-arquivo-0417 videos/02-caso`.
2. **Página 1:** troque cabeçalho, código (`DS.codigo`), campos da ficha e carimbo. Cada linha de ficha a 50 cps leva `caracteres ÷ 50 + 0,1 s`; ajuste `T.dig`, `T.circ`, `T.carimbo` para depois de `fi.fim`.
3. **Fotos:** `src` tratado pelo `tools/dossie.py xerox`, ou outro `seed`/`retrato`.
4. **Página 2:** troque nomes, cartões e fios. Confira o estado final com `--at=10.5`, depois cada parada da câmera (`--at=5.8,7.0,8.1`).
5. **Título:** duas linhas curtas; `maxw` encolhe a letra para caber.
6. **Rodapé:** fonte do caso real ou aviso de ficção.
7. Som e render (`audio.md`).

## 5. Mais páginas, papel escuro e 16:9

- **Terceira página** (um documento, uma segunda ficha): outro `DS.mundo`, outra `DS.camera` e mais uma entrada em `DS.paginas([[0, m1], [5, m2], [10, m3]])`. Um `DS.scanner` curto depois de cada corte.
- **Negativo:** `DS.papel(m, {tom: 'escuro'})` e ponha as peças **dentro** do papel devolvido (`const folha = DS.papel(…); DS.ficha(folha, …)`), que elas saem claras. Cartão isolado: `DS.cartao(…, {tom: 'escuro'})`.
- **16:9:** `VIDEO={w:1920,h:1080,…}`; mundo da ficha 1920×1080 e mural deitado (por exemplo 3200×1800, zoom final 0,6). Nada muda na biblioteca.

## 6. Problemas comuns

- **Tarja ou carimbo com largura errada, texto amontoado:** a peça foi criada fora do `SETUP`.
- **Fundo preto aparecendo na borda:** a câmera saiu da folha; confira `x ≥ 540/z` e `y ≥ 960/z` (e o outro lado), ou dê 8 px de sangria ao papel (`x: -8, y: -8, w: 1096…`).
- **Garrancho desenhando vários pedaços ao mesmo tempo:** não acontece com as funções da biblioteca; se montar um traço à mão com vários `M`, use `DS.traco` uma vez por pedaço.
- **Etiqueta ou título estourando a tela no fim:** veja com `--at` no último segundo; no zoom final a tela mostra `1080 ÷ z` px do mundo.
- **Digital parecendo alvo:** troque `seed` ou use `tipo: 'laco'`/`'arco'`.
- **Render lento:** o papel é desenhado uma vez por página; o que pesa é mural muito maior que 2000×3556. Um render por vez.
