# Movimento: tempos, entradas e câmera

As referências são imagens paradas; o movimento foi desenhado para parecer **mesa de arquivo filmada**: as coisas são postas, batidas, riscadas e datilografadas, nunca deslizam com suavidade. Entradas duram de 2 a 4 quadros; o que é lento é a câmera.

## Estrutura (duas páginas e um corte seco)

| fase | exemplo (11 s) | % |
|---|---|---|
| página 1: código, foto, tarja nos olhos | 0,0–1,2 | 11% |
| página 1: ficha datilografada (câmera desce) | 0,95–3,75 | 25% |
| página 1: digitais, anotação, carimbo (câmera abre; começa com a ficha ainda batendo) | 3,15–5,0 | 17% |
| corte seco + página 2: peças e fios (câmera segue o fio) | 5,0–8,1 | 28% |
| página 2: câmera abre, fios de acento, título | 8,1–9,05 | 9% |
| carimbo final, assinatura e respiro | 9,4–11,0 | 15% |

Tabela `T` do exemplo:

```js
const T = { cod: 0, regua: .3, foto: .2, ficha: .95, olhos: .8, dig: [3.15, 3.38], circ: 3.62, nota: 3.78, carimbo: 4.3, corte: 5.0,
  f1: 5.08, usina: 5.36, linha: 5.5, f2: 6.55, vila: 7.5, f3: 7.8, dig3: 8.2, conv: 8.42, tit: 8.72, arq: 9.4, ass: 9.6 };
// dur 11 s, 30 qps
```

Para outra duração, mude o espaço entre as entradas, não a duração de cada uma. Vídeo de 20 a 30 s: três ou quatro páginas (`DS.paginas`), cada uma com 5 a 8 s.

## Tremor de registro (o quadro nunca fica parado)

- `DS.camera` soma a cada **1/12 s** um deslocamento de ±1,1 px e um giro de ±0,05°, sorteados pela semente. É o tremor de stop-motion; não use valores maiores, vira terremoto.
- `DS.grao` troca o grão também 12 vezes por segundo.
- Toda batida (carimbo 7 px, fita 3 px, digital 2,5 px, foto 2 px, cartão 1,5 px) empurra a câmera para baixo e some em ~0,15 s (`DS.baques`).

## Entradas (o que a biblioteca faz)

| peça | entrada | duração | som |
|---|---|---|---|
| código (`DS.codigo`) | um caractere a cada 0,05 s, seco | 0,35 s para 7 caracteres | `key` por caractere |
| ficha (`DS.ficha`) | letra a letra, 36–50 caracteres por segundo; pausa de 0,1 s entre linhas | ~2,8 s para 5 linhas a 50 cps, com duas tarjas | `tecla` a cada ~66 ms |
| tarja marcador | revela da esquerda p/ a direita, `power1.inOut` | 0,12 s + 0,45 ms por px (máx. 0,5 s) | `marker` |
| tarja fita | aparece 16% maior e girada 2,5°, assenta com `power3.in` | 0,10 s | `tape` + baque |
| foto | aparece 7% maior e girada 3°, assenta; cópias a +0,12 e +0,24 s; cruzes piscam a partir de +0,22 s; medida a +0,35 s | 0,12 s | `paper` |
| digital | aparece 22% maior, assenta; a tinta escurece nos 3 quadros seguintes | 0,10 s | `ink` + baque |
| carimbo | desce de 155% para 100% com `t³`, girando 5°; ricochete de 2,5% | 0,10 + 0,12 s | `stamp` + baque forte |
| caneta (garrancho, círculo, seta, assinatura) | traço desenhado na ordem da escrita, `power1.inOut` | círculo 0,38 s; seta 0,32 s; garrancho 0,3–1,5 s | `pen` a cada 0,2 s |
| régua, medida | reveladas da esquerda p/ a direita, `power2.out` | 0,45 s / 0,35 s | — |
| cartão | aparece 6% maior e girado 2,5°, assenta; alfinete a +0,08 s; texto palavra a palavra (18 por segundo) a partir de +0,18 s | 0,10 s | `paper`, `pin`, `marker` nas tarjas |
| etiqueta | bloco preto revela da esquerda, `power2.out`; o número entra no fim | 0,16 s | `click` |
| fio | desenha de uma ponta à outra, `power2.inOut` | comprimento ÷ 1600 px/s (0,22–0,7 s) | `thread` |
| título | cada linha sobe 20% da altura da letra saindo de uma máscara, `power3.out`; 0,14 s entre linhas | 0,14 s por linha | `cut` |
| texto (`DS.texto`) | palavra a palavra, seco, 14–22 por segundo; a tarja embutida risca no lugar da palavra | — | `marker` baixo |

Regras de ritmo:

- **Tarja nos olhos até 0,6 s depois da foto** (no exemplo: 0,24 a 0,6 s). Antes disso o rosto fica exposto demais.
- Entre duas batidas (carimbo, fita, digital), pelo menos 0,2 s.
- O fio sai da peça antiga **antes** de a peça nova entrar: a câmera viaja junto com o fio e a peça cai quando ele chega.
- Depois de um corte, três peças no primeiro meio segundo.

## Câmera de mesa (`DS.camera`)

Chaves `{t, x, y, z}`: `(x, y)` é o ponto do mundo no centro da tela e `z` o zoom. Entre duas chaves a interpolação é `sine.inOut` (ou o `ease` da chave de chegada); o zoom interpola em escala geométrica.

```js
// página 1: fecha no alto, desce com a datilografia, abre para a folha inteira
DS.camera(m1, [
  { t: 0,   x: 440, y: 742,  z: 1.3 },
  { t: .9,  x: 452, y: 760,  z: 1.29 },                         // deriva lenta
  { t: 3.0, x: 472, y: 1150, z: 1.26, ease: 'power1.inOut' },   // acompanha a ficha
  { t: 4.5, x: 540, y: 960,  z: 1.012, ease: 'power2.inOut' },  // abre
  { t: 5.0, x: 540, y: 960,  z: 1.0 } ]);
// página 2: peça 1 → segue o fio até a peça 2 → peça 3 → abre o mural inteiro
DS.camera(m2, [
  { t: 5.0,  x: 602,  y: 904,  z: 1.12 },
  { t: 6.0,  x: 640,  y: 990,  z: 1.04 },
  { t: 6.85, x: 1440, y: 1120, z: 1.0,  ease: 'power2.inOut' },
  { t: 7.15, x: 1436, y: 1140, z: 1.0 },
  { t: 7.95, x: 722,  y: 2060, z: .9,   ease: 'power2.inOut' },
  { t: 8.1,  x: 726,  y: 2066, z: .9 },
  { t: 9.05, x: 1000, y: 1778, z: .548, ease: 'power2.inOut' },
  { t: 11,   x: 1000, y: 1778, z: .56 } ]);                     // respiro: empurra 2%
```

- **Parada nunca é parada:** entre duas viagens, ponha um par de chaves com 10 a 30 px de deriva.
- **Viagem** de peça a peça: 0,8 a 0,9 s, `power2.inOut`. **Abertura final:** ~1 s, terminando 1,3 a 1,5 s antes do fim.
- **Não mostre fora da folha:** a tela vê `1080/z × 1920/z`; mantenha `x ≥ 540/z`, `y ≥ 960/z` e o equivalente do outro lado. O zoom mínimo é `1080 ÷ largura do mundo`.
- `corte: true` numa chave faz a câmera pular seco para ela (dentro da mesma página).

## Troca de página e scanner

- `DS.paginas([[0, m1], [5.0, m2]])`: no instante da troca a página nova entra **em negativo por 2 quadros** e normaliza. É o corte seco do estilo; não use fade nem transição deslizante.
- `DS.scanner(stage, {t0, d})`: faixa de luz de 280 px que desce a tela. Uma passada de 0,85 s na abertura (a folha "sendo copiada") e uma de 0,55 s logo depois de cada corte.

## Saída

Não há saída: o vídeo termina com o mural inteiro, o carimbo batido e 1,2 a 1,6 s de respiro (a câmera ainda empurra 2% e o papel continua tremendo).
