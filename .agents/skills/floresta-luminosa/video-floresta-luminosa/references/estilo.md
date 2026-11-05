# Estilo: floresta luminosa

Referência de origem: animação noturna quadrada (720×720, 12,8 s, 10 qps, muda) — felino bebendo água num rio, cachoeira azul ao fundo, árvores nas laterais, corte "de aquário" com peixes. Plano único em laço de ~2 s.

## As 3 marcas

1. **Low-poly desenhado a lápis sobre preto.** Formas 3D facetadas, sombreamento chapado por face, e cada face preenchida por riscos finos e densos numa direção própria (a direção muda de face para face). Entre os riscos aparece o papel preto. Nada de contorno: a silhueta é a borda dos polígonos.
2. **Noite quente com água fria que brilha.** Tudo o que é madeira, terra e bicho fica em marrons e ocre; o céu é marinho com estrelas pontuais; a única luz "viva" e fria é a água (cachoeira, rio facetado, corte de aquário), com halo leve.
3. **Diorama parado em laço lento a 10 qps.** Câmera travada; só micro-movimentos cíclicos em degraus de 0,1 s.

Se uma decisão não serve a uma dessas três, corte.

## Paleta (medida na referência)

| uso | hex | na lib |
|---|---|---|
| papel (entre os traços) | `#0e0a06` | `PAL.papel` |
| tronco / galho (traço) | `#8a5432` (luz `#a86a42`) | `PAL.madeira` |
| copa | `#6a4a36` | `PAL.copa` |
| terra da margem | `#5e4430` | `PAL.terra` |
| paredão | `#4a3426` | `PAL.paredao` |
| barranco do corte | `#3a2416` | `PAL.barranco` |
| onça | `#c27a40` · claro `#e3a568` · barriga `#c9a47c` · pinta `#1a0e07` | `PAL.onca…` |
| água (traço / realce / fundo) | `#4f86c0` / `#78c2f3` / `#15283f` | `PAL.aguaMeio/agua/aguaFunda` |
| céu | traço `#2e3d52`, papel `#0d1117` | `ceu()` |
| estrela | `#f6eedc` | `PAL.estrela` |
| fundo d'água (sob o nível) | `#323c38` | `terreno({fundo})` |
| pedra lilás (acento) | `#8a78a6` | `PAL.pedra` |
| roseta clara / escura | `#8f7a64` / `#4f5a48` | `PAL.folha`, `PAL.musgo` |
| peixe | `#b9826a`, olho `#cbbf96` | `PAL.peixe` |
| texto | creme `#f2dcae`, azul `#bfe4ff` | `PAL.creme`, `PAL.azulTexto` |

A média da imagem é escura (medianas de #18 a #6e). A coisa mais clara da tela deve ser sempre a água (e os olhos).

## O traço (material `FL.lapis`)

- Espaçamento ~4,4 px por fileira (duas fileiras intercaladas → ~2,2 px efetivos), largura 1–2,5 px, comprimento 15–60 px, brilho variando de risco a risco (0,5–1,3×).
- Faces iluminadas: riscos mais densos, largos e claros. Faces na sombra: ralos e escuros (o preto domina).
- 2ª camada de realce, girada ~14°, mais rala e mais clara (`cor2`).
- Cada face plana tem tom próprio (`var`) — é o que faz o low-poly ler mesmo sem contorno.
- O traço NÃO ferve: o que está parado fica idêntico entre quadros. Só a água anda (riscos deslizando ao longo da direção, `vel`).

## Objetos típicos

- **Árvores:** tronco hexagonal com riscos verticais, 2 galhos, copa em lajes empilhadas de contorno recortado (terraços, como madeira entalhada).
- **Paredão:** parede facetada atrás de tudo, com entalhe onde desce a cachoeira; serra ao longe em verde-acinzentado.
- **Água:** cachoeira em 3 facetas com riscos verticais descendo; faixa de espuma com riscos horizontais na base; rio facetado (triângulos grandes com tons diferentes e um lustro interno); poço na frente que vira o corte de aquário.
- **Corte de aquário:** a frente do diorama é cortada; vê-se debaixo d'água o fundo escuro, seixos e peixes de olho grande e claro.
- **Plantas:** rosetas (bromélia/agave) de folhas em losango dobrado, capim de lâminas longas na frente.
- **Pedras:** icosaedros amassados; lilás junto da água.
- **Bicho:** low-poly de caixa chanfrada, patas em colunas grossas, cauda em corrente, cabeça curta com plano de rosto, olhos em amêndoa clara com pupila. Pintas como rosetas quebradas e pontos (procedurais, no espaço do objeto).

## Tipografia

A referência não tem texto. Padrão do estilo: **Fraunces** (serifa macia, OFL), minúscula, título ~138 px (600) em creme e subtítulo ~60 px (500) em azul-claro, preenchidos com o mesmo traço de lápis (`FL.textoLapis`) e revelados traço a traço da esquerda para a direita, a 10 qps. Sombra difusa escura por baixo para ler sobre o céu.

## Composição 9:16

| faixa (de cima) | conteúdo |
|---|---|
| 0–25 % | céu com estrelas entre as copas; título e subtítulo |
| 15–40 % | paredão com a cachoeira (esquerda), troncos nas laterais |
| 35–70 % | margens e rio facetado; o bicho no terço central, ~40 % da largura |
| 70–100 % | corte de aquário: fundo escuro, peixes, seixos |

Câmera do exemplo: `fov 32, cam [0, 3.7, 11], alvo [0, .5, -1.2]`.

## Acabamento

Bloom contido (força .55, raio .55, limiar .58) só na água e nos olhos; vinheta .42 oval; pó fixo de papel (não anima). Sem grão de filme.
