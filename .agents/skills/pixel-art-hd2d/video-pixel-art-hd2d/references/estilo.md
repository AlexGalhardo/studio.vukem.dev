# O estilo pixel art HD-2D

Estudado na referência "HD-2D game without a single imported art" (vila com feira e chafariz, floresta com raios de luz,
passagem nevada, porto "Saltwind Harbor", cânion de deserto). O que define o visual, em ordem de importância:

## 1. Mundo 3D, pele de pixel art

- A geometria é 3D de verdade e simples: blocos de casa, telhados de duas águas com beiral, muros, degraus, pedras do chão
  com relevo, troncos cilíndricos, copas feitas de várias bolhas. Volume e sombra projetada vêm do 3D.
- Toda superfície é pixel art: textura de baixa resolução (aqui 24 texels/m), filtro **nearest** na ampliação, pixel
  grande e nítido. Nada de gradiente liso: o sombreado é feito com **rampas** de 4–7 tons e **pontilhado ordenado** (Bayer 4x4).
- **Rampa com matiz deslocado** (regra da pixel art): sombra puxa para azul-violeta, luz puxa para amarelo; a saturação cai
  nas luzes. `HD.rampa(cor, n)` faz isso.
- **Normal map pixelado** gerado do mapa de altura da própria textura: cada pedra, telha, tijolo e tufo de folha pega luz do
  sol separadamente — é o que dá o "relevo pixelado" do chão de pedras da referência.
- Densidade constante: todas as peças usam UV em texels, então o pixel tem o mesmo tamanho na rua, na parede e no toldo.
- Detalhe de pixel artist pintado na textura: sujeira subindo do rodapé, escorrido sob a janela, rachadura, reboco caído
  mostrando tijolo, contorno escuro (AO) em volta das aberturas, musgo nas juntas, brilho de 1 px na borda de cima.

## 2. Personagens = sprites 2D

- Sprites com ~30–42 px de altura (20 px/m), cabeça grande (≈1/3 do corpo), contorno escuro de 1 px (`#1b1424`),
  luz pintada de cima-esquerda (coluna esquerda clara, direita escura), olhos de 1×2 px com brilho.
- Billboard: o sprite gira para a câmera em torno do eixo vertical e inclina ~35% do ângulo dela; projeta sombra real
  (alphaTest) + uma "bolha" escura pixelada no chão.
- Animação por quadros em ritmo de joguinho (6–14 quadros/s): respirar (1 px), andar (4), acenar (2), varrer (4),
  arrumar (2); veículo: roda com 3 raios girando em 4 quadros, balanço de 1 px no paralelepípedo, fumaça em baforadas.
- Balões de fala e placa de local em **fonte bitmap 5×7** com contorno — o texto nunca é fonte vetorial.

## 3. Câmera

- Alta, em 3/4: pitch 31–38° para baixo, yaw 5–10° (levemente de lado), FOV estreito (22–30°) e distância grande (35–42 m)
  — perspectiva "teleobjetiva" de diorama.
- Movimento: travelling lateral lento acompanhando o herói (≈1,2–1,6 m/s), sem cortes; o herói pode andar mais rápido que
  a câmera e "chegar" ao centro do quadro.
- Em 9:16: o campo horizontal é estreito (~11 m na rua). Casas de lote brasileiro (4–7 m de frente) cabem 1,5–2 por quadro;
  use sobrados de 2 andares para encher a faixa das fachadas.

## 4. Luz e pós ("miniatura dourada")

- Sol baixo de fim de tarde (`#ffc27a`, elevação ~25°) vindo da frente-esquerda: fachadas quentes, sombras longas
  para a direita e para trás. Céu/hemisfério azulado (`#a9b8e0`) enche as sombras de azul — o contraste quente/frio é o estilo.
- **Tilt-shift forte**: desfoque por profundidade com faixa nítida (±3 m em volta do foco) + desfoque extra por altura de
  tela; topo (telhados, morro) e base (calçada de cá, canteiros) bem borrados.
- **Bloom quente** só em emissivos: lâmpada de sódio, janelas acesas com cortina, vitrine, letreiro.
- **Névoa dourada** por profundidade (`#ffd7a0` em cima, `#e3ab7c` embaixo), **raios de luz** aditivos diagonais, poeira
  dourada piscando, pétalas/folhas caindo, vagalumes; brilho de sol no canto de cima.
- Gradação: sombras multiplicadas por azul-lavanda (`#c6d0ee`), luzes por creme (`#fff0d4`), saturação 1,12, curva em S,
  vinheta forte (0,55) e grão leve.

## 5. Paleta da rua brasileira (demo)

| uso | cores |
| --- | --- |
| fachadas | rosa `#e7a3a0`, creme `#f2dcae`, azul `#9fc7e6`, verde-água `#a6d6c6`, laranja `#efa66a`, amarelo `#efd27e`, lilás `#cfa4d6` |
| telhas e tijolo | `#b9583a`, `#a94f34`, tijolo `#b4542f` |
| chão | paralelepípedo `#a69886`, pedra portuguesa `#ddcfb3` / `#37302d`, sarjeta `#5f5650` |
| acentos | toldo `#d8302b`/`#f3ece0`, banca `#2f7a4c`, orelhão `#ffb52a`, caixa d'água `#2f74c0`, ipê `#f0bf2a`, mangueira `#3a7331` |
| luz | sódio `#ffc070`, janela `#ffc45e`, sol `#ffc27a`, névoa `#ffd7a0` |
| pele (sprites) | `#f0c7a2`, `#d29a6c`, `#b77a4f`, `#8f5a3a`, `#5e3a26` |

## 6. Composição 9:16

- Faixas: telhados+morro (0–25%) · fachadas (25–55%) · calçada de lá + rua com o herói (55–85%) · primeiro plano (85–100%).
- Placa de local no topo (~15% da altura), escala 6 px por pixel da fonte; some antes do clímax.
- Sempre algo em cada camada: fios e pipa no alto, figurantes na calçada, herói na rua, canteiros desfocados embaixo.
- Brasilidade: pedra portuguesa em ondas, paralelepípedo, platibanda, telha colonial, caixa d'água azul, grade nas janelas,
  porta de ferro com vidro canelado, azulejo azul e branco, toldo listrado, mesa de plástico, engradado amarelo,
  orelhão, banca, poste de concreto com emaranhado de fios, pipa enroscada, ipê amarelo, palmeiras imperiais, vira-lata caramelo.
