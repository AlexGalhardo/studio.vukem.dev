# Gramática de movimento

O estilo junta **duas velocidades**:

- **Pulos e cortes rápidos**, que dão energia: pop elástico, chicote, troca seca de fundo.
- **Gestos em stop-motion a 12 qps**, que dão personalidade: rebolar, abanar, piscar, olhar.

Nada desliza devagar, exceto o zoom do campo de ícones. Os valores abaixo são os do exemplo e estão calibrados contra a referência original.

## Roteiro-tipo (15 s)

| trecho | tempo | o que acontece |
|---|---|---|
| abertura | 0–0,5 | tela preta; um **pontinho** cresce acelerando (`expo.in`) até virar o herói |
| estouro | 0,5–1,15 | 6 **estrelas concêntricas** (lima, magenta, violeta, vermelho, lima, preto) nascem a cada 0,065 s e crescem até cobrir a tela. A última, preta, "limpa" o quadro. A câmera treme. |
| herói | 1,0–1,55 | o herói sozinho no preto; respira (bob de 3 px em 12 qps), gira um detalhe |
| campo | 1,55–4,3 | **zoom-out**: escala 3,2 → 1 (`power2.inOut` até 2,95) → 0,82 (`sine.inOut`), com giro de 0 → −14°. Os ícones **brotam do centro para fora**, pela distância. |
| mergulho | 4,3–4,78 | os ícones **somem de fora para dentro**, o herói cresce ×33 (`power3.in`) e a cor dele **vira o fundo** da cena seguinte |
| objetos | 1,2–1,3 s cada | 3 a 6 cenas: **pop → detalhes em sequência → gesto → rótulo → chicote** |
| estouro final | ~0,5 + 0,7 | um objeto treme cada vez mais (24 qps) e estoura numa estrela de outra cor, com confete. O **mascote** nasce dentro da estrela. |
| mascote | ~1,6 | olha para um lado e para o outro (em degraus), pisca, mostra a língua |
| wordmark | ~1,5 | digitado a 0,04 s por letra, sublinhado desenhado em 0,35 s, confetinho na ponta |
| fim | 0,3 | corte para o preto |

**Versões curtas:**

- **5 s:** pontinho + estouro (0–1,1) → 2 objetos de 1,2 s → wordmark (1,4 s).
- **8 s:** abertura + campo curto (zoom 0,9 s) → 3 objetos → mascote rápido → wordmark.

O campo e o mascote são as primeiras coisas a cortar quando falta tempo.

## Vocabulário (com o código)

| movimento | como | valores |
|---|---|---|
| **pop (entrada)** | `s = TR.pop(t, t0, .3)`; rotação `(1 - Math.min(1, s)) * 12` | `back.out(2.3)`: passa de 1,15 e assenta em 0,3 s. Entra torto (±12–14°) e endireita. |
| **chicote (saída)** | `TR.whip(t, tCorte)` somado ao x ou ao y do grupo **e do rótulo** | 1400 px em 0,17 s, `power3.in`. **O corte acontece no meio do chicote**: o próximo fundo entra com o objeto ainda saindo. Alterne a direção (esq., cima, dir., esq., baixo). |
| **corte de fundo** | `TR.fundos(S.bg, [[t, cor], ...])` | instantâneo, no mesmo quadro em que o objeto seguinte começa o pop |
| **sumir encolhendo** | `TR.popOut(t, t0, .14)` | `back.in(2)`: estica um pouco antes de sumir |
| **gesto stop-motion** | `Math.sin(TR.q12(t) * 2π * f) * amp` | 12 qps, f de 2 a 5 Hz, amp de 8 a 14°. Rebolar, abanar rabo, língua, orelha. |
| **sequência que brota** | `TR.pop(t, t0 + i * .07, .2)` em cada peça | intervalo de 0,065 a 0,075 s; pop com tom subindo a cada peça (pintas, pompons, ícones) |
| **olhar / inclinar** | `TR.passo(t, [[t1, v1], [t2, v2]], v0)` ou soma de `E('back.out(3)', t, a, a + .1)` | movimentos em degraus de 0,1 s com sobra elástica, nunca uma rotação contínua |
| **piscar** | escalaY do olho 1 → 0,08 → 1, ou a altura da pálpebra | ~0,12 s no total, depois de o personagem "assentar" |
| **pulinho** | y −120·sin(π·u) em 0,24 s; na chegada escX 1,1 e escY 0,86 por ~0,07 s | squash e stretch só na chegada |
| **esticar (corpo)** | frente com `power3.out` em 0,4 s; traseira com `back.out(1.25)` em 0,78 s | o comprimento é a diferença entre as pontas (veja o dachshund) |
| **tremer antes de estourar** | alterna ±k a 24 qps, amplitude crescendo de 0 a 1 | rot ±5°, x ±6 px, escala ±5% (cruzada em X e Y) |
| **estouro** | estrela 0,18 → 1,28 em 0,22 s (`expo.out`); some com `back.in` em 0,26 s; `TR.confete` + `TR.tremer` | a câmera treme 34 px por ~0,25 s |
| **rótulo** | `TR.rotulo` + `TR.rotuloTick(L, t, t0, t1, ox, oy)` | entra ~0,3 s depois do objeto, a 0,05 s por letra. Cada letra nasce com escala 1,45 por 1/20 s. Sai junto com o chicote. |

## Ritmo

- **Algo acontece a cada ≤ 0,3 s:** um pop, uma letra, uma pinta, um gesto. Se uma cena tem 0,5 s parada, falta detalhe para brotar.
- **Cena de objeto de 1,2–1,3 s:**

| instante | o que acontece |
|---|---|
| 0 | pop |
| 0,2–0,9 | os detalhes brotam |
| 0,3 | o rótulo começa |
| 0,3–1,0 | gesto principal |
| últimos 0,17 s | chicote |

- **Lisura:** o movimento do objeto (pop, chicote, zoom) é liso a 60 qps, enquanto o **gesto** e a **fervura** são em degraus de 12 qps. Essa mistura é o que dá o "feito à mão" sem ficar travado.
- **Câmera:** só existe no campo (zoom e giro) e na tremida dos estouros. Fora isso a câmera é fixa: quem se mexe é o objeto.

## Peças de assinatura prontas em `TR`

```js
const estrelas = TR.estrelas(gEstrelas, { t0: .5 });   // no tick: estrelas(t)
const campo = TR.campo(gCampo, { icones: [['bone', [P.W]], ...], t0: 1.55, tSaida: 4.3 });   // no tick: campo.tick(t). A escala e o giro do gCampo são seus.
const confete = TR.confete(gConfete, { n: 10 });       // no tick: confete(t, tEstouro, cx, cy)
TR.tremer(S.cam, [.5, 11.55]);                          // tremida nos estouros
```
