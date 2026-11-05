# Movimento — ilustração explicativa

Medido quadro a quadro na referência (24 qps, 19,9 s, 3 planos) e comprimido no exemplo (30 qps, 8 s).

## Sumário
1. Estrutura e proporção
2. Tabela T do exemplo
3. Entradas, saídas e eases
4. Câmera do plano contínuo
5. Stop-motion e fervura
6. Transições
7. Ritmo

## 1. Estrutura e proporção

| cena | fundo | % da duração | conteúdo |
|---|---|---|---|
| 1 | rosa | 26% | 4 fotos P&B entram e se reorganizam; rachaduras crescem; coroas fervem |
| 2 | creme | 54% | plano contínuo: personagens + objeto central → câmera sobe → ação de cima → câmera desce → ação de baixo |
| 3 | rosa | 20% | banco de nuvens com rótulo → varrida → título (+ subtítulo, crédito) |

Para 6 s: 1,55 / 3,25 / 1,2. Para 8 s: 2,05 / 4,35 / 1,6.

## 2. Tabela T do exemplo (8 s)

```js
const T = { c2: 2.05, c3: 6.40, fim: 8.0,
  f2: .45, f3: .95, f4: 1.40,                                   // fotos 2, 3, 4 (a 1 já está no centro)
  excl: 2.14, vapor: 2.12, rio: 2.30, olho: 2.75,               // cena 2a: "!" salta, vapor sobe, fluxo se desenha, lupa pisca
  sobe: 3.22, bracos: 3.26, inclina: 3.80, rega: 3.92, apaga: 4.22, saem: 4.28,   // 2b: câmera sobe, braços entram, regam, fogo apaga
  desce: 4.78, funil: 4.86, armarios: 4.92, pessoa: 5.00, cano: 5.10, torneira: 5.52, copo: 5.60,   // 2c
  varre: 6.52, titulo: 6.92, sub: 7.12, chuva: 7.18, cred: 7.28 };                                    // 3
```

## 3. Entradas, saídas e eases

| peça | entrada | duração | ease |
|---|---|---|---|
| foto nova | desliza de fora (direita, baixo ou baixo-direita) com giro 10–14° assentando em 2–3° | .24 s (7 quadros) | `expo.out` |
| fotos que já estavam | abrem espaço (1 central → 2 lado a lado → grade) | .38 s | `power2.inOut` |
| foto 1 no quadro 0 | já no centro, terminando de assentar (escala 1,18 → 1,34) | começa em −.14 s | `expo.out` |
| rachaduras | troncos um a um (atraso .1 s), ramos depois | 1,6 s cada | `power1.out` em degraus de 12 qps |
| "!" | pop | .3 s | `back.out(2)` |
| fluxo no globo (rio voador) | desenha da origem à ponta, com seta | .75 s | `power2.inOut` (degraus de 15 qps) |
| braços do alto | descem dos cantos (−420, −620 px) | .55 s | `expo.out` |
| regador inclina | 0 → 56° em volta do punho | .32 s | `back.out(1.6)` |
| labareda apaga | escala 1 → .78 → .55 → .34 → .15 → 0 | 5 degraus de .12 s | degraus |
| personagens que saem | afundam 760 px | .42 s | `power2.in` |
| armários | deslizam da esquerda (−760 px) | .5 s | `expo.out` |
| pessoa | sobe do pé do quadro (+700 px) | .5 s | `expo.out` |
| funil | pop | .3 s | `back.out(2)` |
| água no cano | enche da boca do funil à torneira | .42 s | `power1.inOut` |
| varrida (rede/guarda-chuva) | arco de Bézier de baixo-esquerda até sair no alto-direita | .62 s | `power1.inOut` |
| bolha varrida | encolhe para 16% e cai (gravidade 2600 px/s², deriva lateral 320 px/s) | .16 s + queda | `power3.out` |
| título | aparece já atrás das nuvens, escala .9 → 1 | .35 s | `back.out(2)` |
| subtítulo | sobe 40 px e acende | .45 s | `expo.out` |

## 4. Câmera do plano contínuo

Um `#mundo` de 1080×3400 com `translateY(-camY)`. Use `IL.chaves`:

```js
const camY = IL.chaves([[T.c2, 640], [T.sobe, 610, 'none'], [T.sobe + .58, -50, 'power2.inOut'],
  [T.desce, -110, 'none'], [T.desce + .62, 1150, 'power2.inOut'], [T.c3, 1190, 'none']]);
```

- Entre os movimentos, a câmera nunca para: deriva 30–60 px (`'none'`).
- Tilts de .55–.65 s com `power2.inOut`. A referência faz o mesmo: o objeto central (globo) fica no quadro e o resto entra/sai pelas bordas.

## 5. Stop-motion e fervura

- Gestos de braço, balanço do corpo, giro das fotos, regadores: tempo quantizado `IL.q(t, 12)` (12 qps, "em dois").
- Labareda, coroas, "!": forma nova a cada `IL.quadro(t, 8)` (8 qps), jitter de 4–5 px nos vértices.
- Bolhas de vapor/água sobem em 12 qps com oscilação lateral.
- Câmera, deslizes, varrida e quedas: lisos (30 qps).

## 6. Transições

- Cortes secos entre fundos diferentes (rosa → creme → rosa), com som de `cut`.
- Dentro da cena 2, a câmera é a transição.
- Na cena 3, a varrida é a transição para o título.

## 7. Ritmo

Sempre algo novo a cada .4–.6 s; nenhuma cena parada. Respiro só depois do título (~.9 s com chuva fina e nuvens respirando).
