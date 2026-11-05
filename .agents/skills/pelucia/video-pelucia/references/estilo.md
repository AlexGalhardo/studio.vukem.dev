# Estilo pelúcia — o que define o visual

Aprendido da referência "Claude Opus 5.5 / Plush Hammerhead" (estudo de material: um tubarão-martelo de pelúcia nadando num estúdio creme, com HUD editorial). O usuário julga o estilo por três coisas: o PELO parecer pelo, o objeto FLUTUAR num estúdio limpo e o HUD parecer página de revista/laboratório.

## 1. Material

**Pelúcia de pelo curto (≈5 mm na escala do brinquedo).**
- Feito por cascas (shells): a mesma malha repetida 24–28 vezes, cada uma empurrada ao longo da normal; em cada casca só sobra o pixel que cai dentro de um fio (ruído celular 3D em espaço do objeto). Resultado: fios de verdade na silhueta contra o fundo, não uma borda lisa.
- Raiz escura, ponta clara (`ao` .55, `pontas` 1.06): olhando de frente o pelo parece mais escuro e saturado; na borda aparecem só as pontas, mais claras — o "veludo".
- Brilho de veludo na borda (`veludo` .35, contraluz por trás) e especular anisotrópico fraco ao longo do fio (Kajiya-Kay, `brilho` .35).
- O pelo deita numa direção (`pente`, `dobra`) e tem redemoinhos (`redemoinho`): a mesma cor fica mais clara a favor e mais escura contra o pelo, com manchas de pelo amassado (`manchas` .22). Isso é o que tira a cara de "plástico com ruído".
- Ventre mais claro (o tubarão tem barriga creme): máscara pela normal em espaço do objeto (`ventre: {cor, eixo:[0,-1,0], lim, suave}`). No pão do hambúrguer a base é mais clara.
- Pelos diferentes por peça: pele/rosto mais curto (×0,7), cabelo mais longo (×1,1; black power ×2,2), comida bem curta (.012–.014) e densa (240–260).

**Feltro** para tudo que não é pelo: bonés, aventais, queijo, alface, tomate, caixinha de batata, copo, bandeja, sacola, crachá. Fosco (rugosidade .92), fibras em bump procedural, `sheen` para a borda aveludada. Desenhos e letras vêm de canvas (`etiqueta`) aplicados como `map`.

**Botão plástico** para olhos (preto, verniz brilhante, reflexo do RoomEnvironment) com um aro creme de feltro atrás. **Costura**: pontinhos de linha (capsulinhas instanciadas) ao longo de curvas — sorriso, bolso, aba do boné, bordas.

## 2. Estúdio e luz

- Fundo creme quase liso: #e1ddd8 (amostrado), gradiente vertical de ±2% e uma mancha de luz suave. Sem horizonte, sem paredes.
- Chão invisível: só a sombra existe. Ela é enorme, macia, deslocada pela luz (vem do alto à direita, um pouco de frente) e fica BEM abaixo dos objetos — é ela que diz "está flutuando". Cor #5f564b, opacidade ~.5.
- Luz: chave quente do alto à esquerda, contraluz por trás à direita (acende o veludo), céu/chão de estúdio para o preenchimento; RoomEnvironment fraco (.55) para o feltro e o plástico.
- Tone mapping Neutral, grão .016, vinheta .1. Sem bloom.

## 3. Câmera e composição (9:16)

- Lente longa: fov 22, distância ~19–21, elevação ~24°. Quase ortográfico, cara de foto de produto; a elevação mostra o chão o bastante para a sombra ter forma.
- Deriva leve e periódica (±3° de órbita, ±.08 de altura no período do vídeo). Nada de cortes.
- DOF quase nulo; o fundo nunca desfoca.
- Faixas (1080×1920): rótulo y≈112 · título 150–470 · texto itálico 520–610 · ELENCO 620–1380 · sombras 1380–1600 (à esquerda, pela luz) · painel à direita 1300–1800 · rodapé à esquerda (dica + dados + nota) até y≈1850.

## 4. HUD editorial

- Rótulo: Geist 500, 21 px, espaçamento .2em, cinza #6f6a62, caixa-alta — "ESTUDOS DE MATERIAL | Nº 028".
- Título: serifa itálica (Baskerville) 172 px, entrelinha .96, 2 linhas com a 2ª recuada ~96 px, terminando em ponto final ("Equipe / Pelúcia.").
- Texto: itálico 30 px, 3 linhas curtas, tom de legenda de museu.
- Selo no canto: mono 16 px em pílula fina — "● WEBGL · AO VIVO".
- Painel do espécime (340 px, creme translúcido, borda 1,5 px #d3cec6): cabeçalho em caixa-alta + "fig. 28" itálico; amostras de pelo (barra colorida sobre base creme, nome em itálico, a escolhida com moldura); sliders com nome em caixa-alta, valor em mono à direita, trilho fino, bolinha vazada e extremos em itálico ("frouxo/firme"); botões de ação em grade de 2 (o ativo fica preto — sincronize com a ação na tela); checkboxes miúdos.
- Rodapé: dica itálica com rótulo em caixa-alta (troca com a ação), dados em mono 29 px com rótulos miúdos e divisórias, nota de escala em letra de 14 px.

## 5. Paleta

| papel | cor |
|---|---|
| fundo | #e1ddd8 (claro #e9e6e1) |
| tinta / texto | #1d1b18 / #57524b |
| Bronze (pelo) | #857860 · ventre #ece5d6 |
| Laguna | #1f8791 |
| Pôr do sol | #e0603a |
| creme / kraft | #f1ebe0 / #b08e62 |
| peles | #4f3223 · #7a4b31 · #b07a52 · #d8a47c · #ecc3a0 |
| sombra | #5f564b |

## 6. Movimento

- Referência: nado em "S" lento, cauda batendo, pelo que acompanha o corpo. Para bonecos: flutua (±.07), balança (roll ±.045), enche/esvazia (squash ±2%), cabeça e pernas defasadas, braços com poses em quadros-chave suaves (`sine.inOut`).
- Interações sempre "de pelúcia": objetos passam em arco macio, a sacola "engole" o pedido (squash), a carne pula e vira devagar.
- Tudo periódico no período do vídeo → loop de rede social sem emenda.
