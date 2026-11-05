# Estilo — ilustração explicativa

## Sumário
1. As 3 marcas
2. Paleta
3. Traço e materiais
4. Personagens
5. Objetos de explainer
6. Fotos
7. Tipografia
8. Composição em 9:16
9. Acabamento

## 1. As 3 marcas

| marca | o que é | onde está na lib |
|---|---|---|
| ilustração plana com contorno fino | personagens sem rosto + objetos chapados, fundos rosa/creme com grão | `IL.boneco`, `IL.mao`, `IL.globo`, `IL.regador`, `IL.lupa`, `IL.fogoD`, `IL.grao` |
| fotos P&B em cantoneiras ciano | deslizam, se reorganizam em grade, rachaduras crescem, coroas fervem | `IL.foto`, `IL.coreografia`, `IL.rachaduras`, `IL.crescer`, `IL.coroa` |
| nuvens pretas com rótulo químico + título largo | banco de bolhas "H₂O/CO₂" varrido por mão com rede/guarda-chuva | `IL.nuvens`, `IL.rede`, `IL.guardaChuva`, `IL.varredor`, `IL.cabe` |

Se o vídeo novo perder uma delas, deixa de parecer a referência. Tudo o mais (tema, metáfora, objetos) muda livremente.

## 2. Paleta (`IL.P`, medida na referência)

| nome | hex | uso |
|---|---|---|
| `rosa` | `#f06aa6` | fundo das cenas de foto e de título; tronco estampado; selos; contorno da labareda; continentes "quentes" |
| `creme` | `#f3ece0` | fundo da cena de ilustração; jaleco; 2ª linha do título; rótulos "H₂O"; continentes "frios" |
| `k` | `#231f20` | contorno, calça, globo, nuvens, 1ª linha do título (nunca preto puro) |
| `azulc` | `#b4dcec` | cabeça/pele clara, braço claro, água, bolhas, rio voador, guarda-chuva |
| `royal` | `#2b3db6` | braço escuro que entra pela borda |
| `azulm` | `#5b8fe6` | cabeça/luva azul média, mão que varre |
| `amarelo` | `#f9d02a` | labareda, coroas, prancheta, pasta, tronco amarelo, cabo da lupa |
| `cinza` / `cinzaE` / `cinzaC` | `#bdbcba` / `#a3a2a0` / `#d6d5d2` | regador, funil, torneira (sem contorno, com sombra chapada) |
| `ciano` | `#7fd0f0` | cantoneiras das fotos |
| `vidro` | `#86d4f1` | vidros de armário/janela |
| `branco` | `#fbf8f2` | estampa, brilho de copo, traços que correm dentro do fluxo |

Regra: no máximo 5 cores fortes por quadro. Rosa e creme se alternam por cena (corte seco), nunca no mesmo fundo.

## 3. Traço e materiais

- Contorno `#231f20` uniforme, `IL.LW = 5` px (4,5 nos bonecos, 3,5 em detalhes pequenos), `stroke-linejoin: round`.
- Preenchimentos chapados, sem gradiente, sem sombra projetada. "Volume" só com uma faixa de cor vizinha chapada (lado claro do regador).
- Membros e canos são **tubos**: traço preto largo por baixo + traço colorido por cima (`IL.tubo`). Ponta redonda.
- Rachaduras/rios: linha preta fina (3,5 px), segmentos retos com ângulo vivo (`miter`), ramos curtos.
- Labareda: polígono amarelo com contorno rosa fino (3 px); picos só para o lado de cima (`IL.fogoD`), ferve a 8 qps; faíscas em losango laranja com contorno rosa.
- Bolhas: só contorno azul-claro (4 px), sem preenchimento.

## 4. Personagens (`IL.boneco`)

- Cabeça = círculo (raio 40 na escala 1) **sem olhos nem boca**. O bico triangular fino (rosa ou amarelo) indica para onde olha (`dir`).
- Cabelo: `curto` (capacete preto no alto e atrás) ou `coque` (cacho de bolinhas pretas atrás).
- Cabeça flutua ~1 raio acima do tronco; tronco, cabeça e calça são peças soltas.
- Tronco: pílula larga (sem jaleco) ou retângulo de cantos redondos dentro do jaleco aberto; estampa `zigue` (zigue-zagues brancos e triângulos) ou `rabisco` (ondinhas azuis).
- Calça: Π preto chapado, sem contorno.
- Jaleco: creme com contorno, ombros arredondados, lapelas que deixam ver tronco e calça.
- Braços: tubos de 38 (pele) ou 46 (manga) com contorno; mão = luva arredondada (`luva`, `punho`, `aponta`).
- Escala em 9:16: **1,5–1,6**, cortados na coxa pelo quadro.

## 5. Objetos de explainer

Globo preto com continentes em linha fina (rosa enquanto "quente", creme depois), regador cinza com selo rosa e ícone preto (`arvore`, `vento`, `gota`, `sol`), lupa com olho, prancheta, "!" torto que ferve, funil/cano/torneira, copo de contorno com nível azul, armários com vidro azul e itens em linha. Todo objeto novo segue: chapado + contorno 5 px, ou chapado cinza sem contorno se for metal.

## 6. Fotos

- P&B com leve sépia e contraste baixo: `tools/ilustra.py foto` (duotone `#221e1a → #ece6da`).
- Retângulo 3:2 sem borda, 4 cantoneiras triangulares ciano (lado ≈ 7% da largura, saindo 28% para fora).
- Giro de 2–4°, balanço lento "em dois".
- 4 fotos, assuntos do mundo real (paisagem, fenômeno, cidade). Nada de pessoas identificáveis em close.

## 7. Tipografia

- **Archivo** variável (OFL) — única família.
- Título: `font-stretch:125%; font-weight:900`, caixa alta, 2 linhas empilhadas com entrelinha .92–.96: **1ª preta, 2ª creme**. Largura ~73% do quadro (`IL.cabe(el, 790)`).
- Rótulos químicos: mesma fonte, 46 px, creme, giro ±12°; subscrito com `<tspan dy="12" font-size="30">` (`IL.H2O`, `IL.CO2`).
- Subtítulo: `112% / 800`, ~58 px, preto, 2 linhas, minúsculas.
- Crédito: `100% / 500`, 17 px, preto 72%.

## 8. Composição em 9:16 (referência era 16:9)

- **Fotos:** grade 2×2 de 480×320 centrada (colunas em x 285/795, linhas em y 770/1130); rios pretos ocupam todo o rosa em volta; coroas de 210×270 nos cantos de baixo, a base fora do quadro.
- **Plano contínuo:** um mundo SVG de 1080×3400 que a câmera percorre na vertical. Globo (r 290) no terço de cima; personagens grandes embaixo, cortados na coxa; braços com regadores entram pelos cantos de cima; a cozinha fica abaixo do globo, à esquerda (armários) com a pessoa à direita.
- **Título:** faixa de nuvens no alto (até y≈380), colunas finas (~100 px) nas laterais até y≈1300; janela rosa no meio com o título em y≈585–950 e subtítulo logo abaixo; rodapé rosa com chuva e crédito.

## 9. Acabamento

Só grão fino (`IL.grao`, opacidade .2, overlay, treme a 12 qps). Sem vinheta, sem brilho, sem desfoque, sem aberração. Tudo plano.
