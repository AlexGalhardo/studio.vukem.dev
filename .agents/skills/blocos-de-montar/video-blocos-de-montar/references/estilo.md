# Estilo "peças de montar — montando e desmontando"

O que se aprendeu olhando a referência (carro esportivo vermelho nº 23 de milhares de peças, que se monta sobre uma placa-base verde numa cidade pastel) e o que a biblioteca reproduz.

## As marcas

1. **Objeto de MILHARES de peças pequenas** (menores que o pino da placa: a demo usa 1/1,4 → ~2.400 peças num objeto de 40 de comprimento, aparência de mosaico). Tijolos 1x1, 1x2 (e 1x3/1x4 quando o desenho pede), placas, lisos, telhas, redondos. Cada peça tem **pinos cilíndricos** em cima, **chanfro** suave nas arestas (a junta escura entre peças é o que faz ler "peça") e **plástico ABS brilhante** com especular macio (clearcoat). As juntas são **desencontradas** como alvenaria (direção alternada por camada e peça mais curta no início das camadas ímpares).
2. **Voxels de tijolo.** O contorno sai em degraus: planta arredondada por camada, para-lamas recortados, teto recuado. Não tente suavizar — os degraus SÃO o estilo.
3. **Montagem em enxame por subconjuntos**, na ordem de quem monta de verdade (chassi escuro → rodas → mecânica/bancos → carroceria em cor → listras/detalhes → vidros → aerofólio/acessórios). Centenas de peças no ar ao mesmo tempo, cada uma em **arco** (parábola) com **giro** que zera na chegada, chegando **de cima** e dando um **quique** curto ao encaixar.
4. **Montes de origem por cor** espalhados na placa-base, que **encolhem** à medida que o objeto cresce (as peças saem do topo; o monte vira um cone menor, nunca um anel). Pneus empilhados.
5. **Desmontagem** de cima para baixo: cada peça estoura para fora e para cima e cai de volta no seu monte, que cresce de novo — fecha o loop.
6. **Cidade de brinquedo**: placa-base verde cheia de pinos, rua de asfalto escuro com faixas brancas e calçadas, chão CINZA (não creme — o teto branco do objeto precisa se destacar), prédios low-poly pastel DESSATURADOS (azul-acinzentado, rosa-velho, areia, lilás, menta, palha) com grade de janelinhas e caixas-d'água, céu azul-claro (#7fb7e6) com nuvens em blocos e **névoa clara** (#dde7ee, 140–600) que os deixa azul-acinzentados. Valores medidos no RENDER da referência: chão ≈ 207,208,204 · asfalto ≈ 77,86,91 · placa ≈ 55,140,87 · prédio ≈ 179,195,202. As cores-BASE em `CENA` (chão #acada8, asfalto #2b3236, placa #368454) já compensam a luz do palco.

## Paleta de peças (COR)

Cores saturadas de brinquedo, sem preto puro: vermelho #c8231b, branco #f3f2ee, preto #1c1d20, grafite #4f5459, cinza #9ea4aa, prata (metal) #c8cdd2, azul-perua #7db3de, azul #1f5fae, amarelo #f5c52e, laranja #f08a24, bege #dcc597, marrom #7a4a2c, cerâmica #c25a2c, kraft #cfb98f, madeira #b98a55, jeans #3d5e8e, vidro fumê #4a6272 (opacidade .74), luz #fff3d2 (emissiva). Cada instância varia ±3,5% de tom (lotes de plástico), o que ajuda a ler peça por peça.

## Materiais

- **abs**: MeshPhysical, rugosidade .3, clearcoat .5 (brilho de plástico injetado).
- **vidro**: translúcido fumê, sem escrita de profundidade, fora do AO.
- **luz**: como abs, com emissivo que você controla (`S.mats.luz.emissiveIntensity`) + `brilho()` aditivo na frente.
- **borracha** (pneus): fosca .72. **metal** (para-choque, aros cromados): metálico .7.

## Luz e pós

Dia de estúdio: IBL de sala branca (.5) + hemisférica céu/chão (.75) + sol branco-quente (2,5) vindo da frente-esquerda-alto com sombra PCF 4096 cobrindo a placa; GTAO (raio ~1,1 pino) escurece juntas e cantos; tone mapping Neutral (mantém o vermelho e o azul saturados); vinheta e grão quase nulos (a referência é CG limpo).

## Câmera e composição (9:16)

- 3/4 alta (elevação 22–30°), lente média (`fov` 44 vertical no 9:16), **órbita em balanço periódico** (azimute 36° → 60° → 36°, `azim: [48, 12, -2.33]`) que chega à FRENTE em 3/4 no instante "pronto", com aproximação forte (raio 121 → 82: o objeto ~80–85% da largura, a frente ~45% dele) e elevação mais baixa (o objeto vira herói e os prédios sobem no fundo). `alvo` [5, 7,5, 1]: um pouco à frente e acima do centro.
- Faixas do quadro: prédios enevoados no topo, placa-base com os montes de trás, objeto no meio, montes da frente e bonequinho embaixo (o bonequinho fica na faixa estreita diante do nariz, visível em todo o balanço). A 16:9 funciona com `fov` 30, raio [118, 94], `alvo` [6, 6, 9] (o bonequinho pode cortar no pé no "perto").
- Rótulo discreto no canto superior esquerdo, em y ≥ 260 px no 9:16 (fora da interface do Reels/TikTok): ícone de tijolo, "Nº 01 · NOME", contador mono que sobe no encaixe e desce no pouso, selo de estado (montando/pronta/desmontando).

## Tempo (5 s, 30 fps)

0–2,45 s montagem (partidas de 0 a 1,76 s, voo 0,55–0,72 s proporcional à distância, arco 0,7× a distância → fitas altas saindo dos montes a ~30 do centro; o adesivo cola em 2,3 s) · 2,45–3,7 s pronta, 1,25 s (suspensão amortecida, faróis piscam e acendem, motor, buzina, bonequinho comemora, tremor de antecipação) · 3,7–4,8 s desmontagem (partidas de 3,7 a 4,3 s, voo 0,38–0,5 s) · 4,8–5,0 s repouso igual ao quadro 0.

## Som

Chacoalhar baixinho na decolagem de cada peça (o começo não fica mudo), um clique de plástico por encaixe (transiente curto + ressonância 2–4 kHz; peça maior = mais grave; vidro mais agudo; borracha abafada), estalo menor ao soltar, chocalhar abafado ao cair no monte — a densidade acompanha o enxame sozinha. Por cima: whoosh no início de cada lote e no estouro, motor ligado durante o "pronta", buzina, interruptor de farol, marimba pentatônica e ambiente de rua. Tudo em loop, −14 LUFS (BS.1770) com limitador de pico verdadeiro (≤ −2 dBTP antes do AAC).
