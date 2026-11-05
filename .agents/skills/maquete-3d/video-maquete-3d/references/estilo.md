# Estilo — maquete 3D semi-realista

Aprendido da referência "Harbor Jelly" (metade de baixo do vídeo Vib3Coded "Claude Opus 5.5 vs …", 1080×1368, 17 s): um porto inteiro num bloco de "gelatina" com estratos, flutuando num estúdio creme, com HUD de estudo de material. A skill troca o porto por qualquer lugar de trabalho e mantém a linguagem.

## As marcas (o que o olho julga primeiro)

1. **Objeto único flutuando no estúdio.** Um bloco retangular (não uma ilha orgânica), com arestas retas e limpas, a ~0,1 m acima do chão infinito. Fundo creme quase liso (`#ECEAE4` no topo → `#E2DFD8` na base), sem horizonte, sem textura, vinheta mínima. Sombra macia e quente (`#3b3024` a ~30%) caindo para trás/direita.
2. **Corte de terreno nas laterais.** Faixas horizontais com contato ondulado entre elas, de cima para baixo: concreto/contrapiso (cinza claro, agregado) → terra vermelha (latossolo, raízes finas, canos cortados: esgoto creme, água azul, gás amarelo) → argila laranja → areia bege granulada → brita cinza → rocha escura. Espessura total ≈ 1/6 da largura do bloco. As duas faces que a câmera vê são as que contam.
3. **Miniatura limpa e semi-realista.** Proporções reais (pessoas de 1,7 m, mesas de 0,75 m, paredes de 2,8 m), sem exagero cartoon. Materiais PBR foscos com textura procedural discreta; metais (inox, alumínio) refletem o estúdio; vidro quase invisível; cores saturadas porém suaves. Chanfros pequenos em tudo (pega luz na aresta).
4. **Casa de bonecas de arquiteto.** Telhado removido. Paredes do fundo e de um lado inteiras (são o "cenário": azulejo, pintura com barra, quadros, prateleiras); paredes de perto cortadas baixas (~0,95 m). Todo topo cortado é pintado de `#3b3631` (poché de maquete).
5. **Gente trabalhando ao mesmo tempo.** Cada boneco faz UMA ação legível pela silhueta, em loop; ninguém parado. Bonecos sem rosto (só nariz e orelhas como volume), tons de pele variados, uniformes que dizem a função (touca, avental, colete + gravata-borboleta, boné, luva amarela, crachá, regata + bermuda + chinelo).
6. **HUD editorial claro** (ver abaixo), fino, muito espaço em branco.

## Paleta

- Estúdio `#ECEAE4`/`#E2DFD8` · tinta `#1f1d1a` · cinzas `#5f5b54`, `#8f8a80` · fios `#d9d5cb` · papel `#f7f6f2` · **acento terracota `#c2502e`** (só o ponto do título e detalhes).
- Estratos: concreto `#cfcac0`, terra `#9a4a2e`, argila `#c26d3d`, areia `#d9bb8b`, brita `#8e8982`, rocha `#4b4039`.
- Brasil sem clichê de bandeira: amarelo `#f2c53d`, verde `#2f8f5b`, azul `#2f6db3`, vermelho `#c3372c`, terracota `#b5533c`, verde-água de parede `#a7d3c3` com barra `#5f9f8a`, fachada ocre `#ecc25e` com barra `#c75b3c`.
- Peles `PELE[0..5]` de `#f2cba9` a `#5b3622`; cabelos `CABELO[0..4]` (preto → grisalho).

## Materiais (todos em `MAT` / `tex`)

| superfície | receita |
|---|---|
| piso de salão | `tex.ladrilho()` (ladrilho hidráulico creme/terracota/verde), `tam` 1,2 m |
| cozinha, banheiro | `tex.azulejo({linhas, faixa:{linhas:[7], cor: azul}})` — faixa azul na altura certa |
| calçada | `tex.pedraPortuguesa()` (ondas preto/branco tipo Copacabana), `tam` 4 m |
| rua | `tex.asfalto()` + faixas brancas em caixas finas; meio-fio `PAL.guia` |
| parede pintada | `tex.pintura({cor, alt, barra:{alt,cor}, rodape})` — a textura é feita para a altura da parede |
| mesa de restaurante | `tex.xadrez({cor})` (toalha vichy) |
| madeira | `MAT.madeira(cor)` (veios procedurais) |
| metal | `MAT.inox()`, `MAT.aluminio()`, `MAT.ferro()` (rug .3–.6, metal .5–.85, env alto) |
| vidro | `MAT.vidro()` (transparente .2, sem escrever profundidade, fora do AO) |
| água | `M.agua(S, {cor, opac, vel})` — normal map animado |
| luz/tela | `MAT.luz(cor, força)` (MeshBasic, sem sombra) |

## Luz e pós

- IBL de `RoomEnvironment` (sala branca) com `environmentIntensity` ~.85 → reflexos de estúdio no inox e no vidro.
- Sol direcional quente `#fff4e6` força ~2,1, de cima-frente-esquerda (`dir [-.5, 1, .55]`), sombra VSM 2048 com `radius` 9 (macia, sem serrilhado).
- Hemisférica fraca (céu creme, chão bege) para levantar as sombras.
- GTAO (raio .35 m, força .9) dá o contato entre peças — é o que faz parecer maquete fotografada.
- Neutral tone mapping, exposição 1; MSAA 4×; grão .012 e vinheta .1 (quase nada). Sem bloom, sem DOF (a referência é nítida).

## Câmera e composição

- Lente longa: `fov` 26 a ~55 m (9:16) ou ~38 m (16:9) para um bloco de 10 × 9 m → perspectiva leve, quase isométrica.
- Ângulo de 3/4 vindo da frente-direita: azimute 24°→42°, elevação 37°→35°, raio −6% (leve aproximação), `sine.inOut` em toda a duração.
- 9:16: título no terço de cima (y 150–480), bloco no meio (y ~500–1350), painel à direita embaixo (y ~1400) e rodapé à esquerda (y ~1660). 16:9: título à esquerda em cima, painel à direita em cima, rodapé à esquerda embaixo, bloco ao centro.
- A fachada com letreiro e toldo fica na lateral que a câmera vê de viés (texto em letras grandes para aguentar o escorço).

## HUD (CSS da biblioteca)

- Rótulo: Geist 600, 21 px, `letter-spacing .24em`, caixa-alta, cinza `#5f5b54`. Ex.: "ESTUDOS DE MAQUETE · Nº 01".
- Título: Baskerville itálico 156 px (9:16) / 112 px (16:9), entrelinha .86, ponto final em terracota. Segunda linha recuada (.42 em) quando houver duas.
- Traço curto (64 px) + subtítulo itálico 36 px em 2 linhas.
- Selo: pílula com borda fina, ponto verde pulsando, mono espaçado ("AO VIVO · 11:42:07", relógio anda com `t`).
- Painel: cartão `rgba(250,249,246,.94)`, borda `#d9d5cb`, raio 10; cabeçalho em versalete + "fig. 01" em itálico; botões pretos; estatísticas com número em mono; chips com bolinha colorida e nome em itálico; sliders com trilho fino, polegar branco e extremos em itálico.
- Rodapé: versalete pequeno + frase itálica + linha de dados em mono separada por fios verticais + nota miúda ("Restaurante fictício · maquete ilustrativa").
- Movimento do HUD: só detalhes vivos (relógio, contadores que sobem devagar, polegar que respira, ponto pulsando). Sem entrada animada (o vídeo precisa funcionar em loop).

## Som

Ambiente curto em loop, nível ~ −17 LUFS: violão de bossa (ii-V) bem baixo + murmúrio do lugar + 2–3 ruídos de trabalho específicos (chapa, panela, louça, caixa). Adapte as camadas em `audio/synth.py` (outro lugar → outros ruídos: serra e martelo na obra, máquina de costura no ateliê, bipe de leitor no mercado).
