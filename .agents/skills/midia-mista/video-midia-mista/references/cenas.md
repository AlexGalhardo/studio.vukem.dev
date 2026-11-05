# Receitas de cena (tempos do exemplo de 7,9 s, 30 fps)

Todos os tempos abaixo são do `videos/exemplo-microchips/index.html`. As janelas de cena se **sobrepõem** nas transições (a cena que sai e a que entra ficam visíveis juntas):

```js
const S = { s1: [0, 1.15], s2: [1.15, 2.48], s3: [2.28, 4.16], s4: [3.66, 4.44], s5: [4.14, 5.84], s6: [5.8, 6.82], s7: [6.62, 7.9] };
```

Cada cena é um `<div class="sc" id="sN">` com um `<div class="cam" id="cN">` por dentro (a câmera), e a textura `.bgimg` como primeiro filho da câmera. Assim o fundo anda junto nos chicotes e no empurrão. No `onTick`, `if (M.vis('sN', ...S.sN, t)) { ... }` mostra a cena e anima só o que está nela.

Ritmo: **1,1–1,7 s por cena**, com a primeira peça entrando nos primeiros 0,1 s e a última anotação terminando ~0,15 s antes da transição. Se o vídeo precisar de mais tempo, alongue as cenas 3, 5 e 7 (as que têm mais leitura), não o título.

## 1 · Título datilografado (0 – 1,15)

```js
const titulo = M.datilografia($('#ttl'), 'Do tamanho de uma sala…', { t0: .1, passo: .034, x0: 110, xCursor: 830 });
// SETUP: titulo.medir(); titulo.sons();
// tick:
titulo.tick(t); const z = E('expo.in', t, .98, 1.15);
$('#c1').style.transform = `scale(${1 + .07 * seg(t, 0, 1) + 2.6 * z}) rotate(${-1 + seg(t, 0, 1.1)}deg)`;
$('#c1').style.transformOrigin = `${Math.min(830, titulo.cursorX(t))}px 900px`;   // o zoom final mergulha no cursor
$('#c1').style.filter = M.filtroBlur(16 * z);
```

- **Texto:** de 18 a 26 letras, terminando em reticências (é uma pergunta ou meia frase que a cena 2 completa). Com `passo .034`, 23 letras levam 0,8 s.
- **Câmera:** a linha rola para a esquerda quando o cursor passa de x = 830. Por isso a frase pode ser maior que a tela.

## 2 · Padrão + foto + fitas + X (1,15 – 2,48)

```js
const valvulas = M.padrao($('#grid2'), { imgs: ['img/valvula_s.png', 'img/valvula2_s.png'], t0: 1.15, dur: .35 });
```

| t | o quê |
|---|---|
| 1,15 | câmera entra de 1,3× para 1× (`expo.out`, .35 s); recortes brotam do centro para fora em 3 saltos |
| 1,24 | foto impressa batida (`slap` k .35), giro −5° |
| 1,40 / 1,50 | fita principal e fita secundária (menor) batidas |
| 1,60–1,86 | laço branco em volta das fitas (`power1.inOut`) |
| 1,70–1,98 | duas setinhas brancas vindo das bordas, cada uma com a ponta logo depois |
| 1,92–2,06 / 2,08–2,22 | os dois traços do **X** de marca-texto (`power2.in`, largura 118 px), por cima da foto e por baixo das fitas |
| 2,28–2,48 | chicote vertical para a cena 3 |

O padrão deve ser algo **do passado ou do problema** (válvulas, fitas VHS, disquetes, cartas…). A foto do meio é o "documento" histórico.

## 3 · Mesa vista de cima com mãos de passagem (2,28 – 4,16)

| t | o quê |
|---|---|
| 2,28–2,48 | entra subindo (chicote) |
| 2,42–2,95 | mão esquerda desfocada entra e sai pela esquerda (`sin(π·u)`), ajeitando a caneta |
| 2,52–3,08 | mão direita desfocada entra e sai pela direita |
| 2,76 | a peça principal aparece batida (`slap` k .4) — como se a mão direita a soltasse |
| 2,92 | fita amarela batida |
| 3,05–3,30 | laço branco na fita |
| 3,22–3,50 | seta branca da fita até a peça |
| 3,40–3,68 | círculo vermelho grosso (16 px) na peça |

Objetos de contexto ficam parados desde o início (3 a 4 itens nas bordas, girados). As mãos são o mesmo `mao_blur.png` espelhado, com `rotate` de ±55°: o desfoque pesado é o que as faz parecerem passar rápido na frente da lente.

## 4 · Chuva de adesivos (3,66 – 4,44)

```js
const adesivos = M.adesivos($('#st4'), { imgs: [...5 recortes], centro: 'img/chip_ouro_s.png', t0: 3.66, tSaida: 4.14, fim: 4.4 });
// som: M.somAdesivos(3.66)
```

Brotam em 0,3 s do centro para fora e cobrem a cena 3 inteira (mantenha a cena 3 visível até 4,16 para não aparecer preto entre os adesivos). Às 4,14 voam radialmente para fora e revelam a cena 5, que já está visível por baixo.

## 5 · Objeto explodido sobre faixa amarela (4,14 – 5,84)

```js
const cpu = M.explodido($('#iso'), [
  { src: 'img/cpu_baixo_cut.png', w: 520, h: 626, z0: 0,  z1: -150 },
  { src: 'img/die_q.jpg',         w: 290,          z0: 10, z1: 30, css: 'box-shadow:0 0 0 4px #1c1c22' },
  { src: 'img/cpu_topo_cut.png',  w: 520, h: 624, z0: 22, z1: 212 }], { x: 540, y: 1010, rx: 56, rz0: -40, rz1: -30 });
// tick: cpu(t, E('back.out(1.7)', t, 4.42, 4.95), seg(t, 4.14, 5.84), Math.sin(t * 2.4) * 10);
```

| t | o quê |
|---|---|
| 4,14 | câmera assenta de 1,06× (`expo.out`) |
| 4,42–4,95 | camadas se separam (`back.out(1.7)`); sombra elíptica embaixo cresce e clareia |
| 4,62 | etiqueta de papel abre (`scaleX` com `back.out(2)`), texto datilografado até 5,22 |
| 4,92 | palavra à mão revelada em 7 saltos; laço vermelho 5,12–5,36; linha fina até a camada 5,28–5,44 |
| 5,05 | ícone em círculo preto (pop) |
| 5,20 | parágrafo cinza pequeno sobe e aparece |

Camadas: use fotos de frente e verso do objeto (ou foto + uma imagem do "miolo"). Para objetos sem camadas, explode por **partes** (tampa, corpo, peça interna) ou por **estágios** (matéria-prima, peça, produto).

## 6 · Caleidoscópio → foto em cartão (5,8 – 6,82)

```js
const kal = M.caleidoscopio($('#kal'), 'img/sala_limpa.jpg', '52% 50%');
// tick: const kin = 1.22 - .12 * seg(t, 5.8, 6.82); kal(t, 5.8, 6.06, kin); $('#cin').style.transform = `scale(${kin})`;
```

| t | o quê |
|---|---|
| 5,80–6,06 | 3×3 ladrilhos espelhados giram de 30° a 0° e convergem no do meio (`power3.in`) |
| 6,06 | troca para o cartão `#card` em tela cheia (mesma foto, mesmo zoom interno: o corte é invisível) |
| 6,08–6,36 | o cartão encolhe para margens de 70 × 230 px com cantos de 44 px e sombra (`back.out(1.4)`) |
| 6,24 | legenda branca sobre faixa preta, embaixo |
| 6,32–6,56 | laço branco num detalhe da foto; rótulo à mão revelado 6,42–6,68 |
| 6,62–6,82 | chicote horizontal para a cena 7 |

Para circular um detalhe da foto num cartão que muda de tamanho, use `M.mapaCapa(cw, ch, larguraFoto, alturaFoto, posX, posY, zoom)(X, Y)` e redesenhe o laço a cada quadro (`M.reink`).

## 7 · Lousa final (6,62 – 7,9)

| t | o quê |
|---|---|
| 6,62–6,82 | entra da direita (chicote) |
| 6,86–7,16 | palavra-chave vermelha letra a letra, cada letra torta (`M.letras`) |
| 7,12–7,38 | laço vermelho em volta |
| 7,30–7,58 | frase à mão branca digitada embaixo |
| 7,52 | fita amarela batida na borda de baixo da lousa (`slap` k .45) |
| 7,52–7,90 | segura parado (com o empurrão lento) para quem pausar; créditos no rodapé |
