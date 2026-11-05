# Estilo — pintura em camadas

## As 3 marcas (tudo serve a elas)

1. **A obra no lugar, e a câmera atravessa a moldura.** O vídeo começa no museu: a obra inteira, emoldurada, numa parede escura com um foco de luz quente e uma placa. A câmera já está andando. Sem corte, a moldura passa pela câmera (cresce mais rápido que a pintura e sai pelas bordas) e a parede se dissolve. O que estava "atrás" da moldura é a própria pintura, estendida.
2. **Camadas de profundidade com parallax real.** A obra é separada em 4–6 planos (fundo, terreno, grupo principal, grupos do meio, primeiro plano). A câmera faz um dolly contínuo: o primeiro plano cresce até ~1,5× mais que o plano de foco e escorrega para fora; o céu quase não se mexe. Atrás de cada recorte há pintura refeita, então o parallax nunca mostra buraco.
3. **Profundidade de campo e luz de museu.** A figura principal fica nítida no centro; o primeiro plano desfoca até ~9–11 px; o fundo desfoca um pouco (2–3 px). Vinheta quente, cantos escuros, véu de luz suave por cima. Termina PARADO na figura principal.

## Paleta

A paleta é a da obra. O que o estilo acrescenta:

| uso | cor |
|---|---|
| parede do museu (centro → canto) | `#4a1d16` → `#2a0f0b` → `#120605` (bordô quase preto; a referência tem `#321410`/`#180a09` nos cantos da sala) |
| dourado da moldura (perfil) | `#2a1a08` `#7a5a22` `#e6c776` `#9a7330` `#6b4a1a` `#d9b55e` `#f6e3a0` `#b48a3a` `#5a3c14` `#c9a24f` `#f0d68c` `#8a6526` `#24170a` |
| placa do museu | papel `#f1e8d4` → `#e4d8bd`, texto `#2a1d12`, autor `#6b4a24` |
| título final | creme `#f6ead2`, sobrelinha ouro `#e9c987`, sombra `rgba(10,4,0,.85)` |
| céu estendido (topo) | `ceu=(112,142,172)` em `camadas.py estender` — um azul acinzentado que combina com tela envelhecida |

Correção de cor do palco: `contrast(1.05) saturate(1.06)` (opção `grade` do `PC.palco`). Não sature mais que isso: é pintura a óleo, não foto.

## Tipografia

- **Placa do museu** (na parede, mesma escala da moldura): autor em Inter Tight 600 caixa-alta espaçada (.24em), título da obra em Playfair Display itálico 600, linha técnica em Inter Tight 400 (ano · técnica · acervo).
- **Título final** (tela, centrado no terço de baixo, sobre o primeiro plano desfocado): sobrelinha Inter Tight 600 27 px caixa-alta .34em ouro; nome Playfair Display itálico 700 84 px creme; fio dourado que abre; linha de baixo Playfair 31 px.
- **Crédito**: Inter Tight 15 px, creme a 62%, no rodapé.
- A referência não tem texto nenhum. Use o mínimo: a placa (que faz parte do museu) e um título discreto no fim.

## Camadas: como dividir uma obra

| camada | K (fim do dolly) | desfoque | o que vai nela |
|---|---|---|---|
| fundo | 0,75–0,85 | ~7 px | céu, arquitetura distante; é a obra inteira, limpa (inpainting) e estendida |
| terreno / meio | 0,9–0,95 | ~2 px | chão, colinas, casas, figuras distantes |
| **foco** | **1,0** | 0 | a figura/grupo principal + o chão logo abaixo dela (polígono esfumado) |
| grupos do meio | 0,95–1,1 | ~1–3 px | figuras próximas do foco (ex.: guarda que galopa até D. Pedro) |
| primeiro plano | 1,4–1,6 | ~9–11 px | figuras grandes na borda de baixo, margem, vegetação, água |

- O desfoque padrão é `dof × |1 − 1/K|` (`dof` = 30 px no exemplo). Fixe por camada com `blur` no `camadas.json` se quiser.
- Grupos que interagem (alguém aponta para o foco, ergue a espada para ele) ficam em K próximos: diferença grande separa mãos de espadas.
- Figuras que tocam a borda de baixo da obra precisam de `estender_baixo` (o vertical mostra abaixo da obra): `reflexo` para água, `esticar` para chão/mato.

## Composição 9:16

- **Começo (museu):** a obra a ~87% da largura (940 de 1080 px), um pouco acima do meio; foco de luz em cone vindo de cima; placa centrada abaixo da moldura; parede ocupa o resto.
- **Fim:** a obra a ~0,95 px de tela por px da imagem (resolução nativa no plano de foco), a figura principal no terço central, o primeiro plano desfocado ocupando o terço de baixo (onde vai o título), um pouco de céu em cima.
- Obra larga (1,8:1 ou mais) nunca enche a altura antes do fim: por isso a extensão (céu em cima, reflexo/mato embaixo) e a moldura que voa (cobre a transição).

## Materiais e acabamento

- **Moldura dourada**: gerada em canvas (`PC.moldura`): perfil de 13 faixas, cantos em meia-esquadria, luz de cima (cima 1,18 · esquerda 1 · direita .86 · baixo .7), contas e folhas em relevo, rosetas nos cantos, douramento gasto. Sombra na parede para baixo; sombra interna na tela; brilho que corre no dourado enquanto a câmera anda.
- **Parede**: gradiente radial a partir do alto da obra (o spot). **Facho**: cone suave `screen` com desfoque de 30 px.
- **Poeira**: 60 partículas suaves com profundidade (as perto crescem mais rápido); a 100% no museu, 45% dentro da tela.
- **Acabamento**: vinheta radial quente (.42), véu de luz `soft-light` no alto (.3), grão `overlay` (.06).
- **Tela estendida**: a extensão carrega o grão da tela (alta frequência da pintura) e pinceladas de ruído, para não parecer "digital".
