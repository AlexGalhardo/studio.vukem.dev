# Gramática visual da mídia mista

O estilo é um explicativo de colagem feito à mão: **fotos reais recortadas** colocadas sobre **superfícies reais** (papel, tecido, madeira, mesa de desenho) e anotadas com **material de papelaria** (fita amarela, marcador branco e vermelho, marca-texto, etiqueta de papel). A câmera nunca para e as cenas mudam a cada 1–1,5 s. O que dá a cara de "feito à mão" é a mistura de dois tempos:

- **Stop-motion para o que chega.** Peça batida na mesa em 4 quadros (`M.slap`), recortes que brotam em 3 saltos (`M.steps`), letra à mão que se revela aos trancos.
- **Movimento liso para a câmera.** Empurrão lento (escala 1 → 1,06 ao longo da cena), leve giro de 1–2°, transições em chicote e zoom.

## Os 7 tipos de cena

Monte o vídeo combinando estes tipos (o exemplo usa os 7, em ~7,9 s). Cada um tem uma superfície e um "gesto" principal.

| # | Cena | Superfície | Gesto principal | Exemplo |
|---|---|---|---|---|
| 1 | **Título datilografado** | papel cinza com vinheta | texto em serifa itálica digitado letra a letra, cursor amarelo, câmera seguindo o cursor | "Do tamanho de uma sala…" |
| 2 | **Padrão + etiqueta** | tecido escuro | o mesmo recorte repetido numa grade diagonal; no meio, uma foto impressa (borda branca), fitas amarelas, laço branco, setinhas e um **X grande de marca-texto** | válvulas + ENIAC |
| 3 | **Mesa vista de cima** | madeira escura | objetos reais espalhados, **mãos desfocadas de passagem** colocando a peça principal, fita amarela, seta branca, círculo vermelho | chip na palma da mão |
| 4 | **Chuva de adesivos** | (por cima da cena anterior) | dezenas de recortes com borda branca brotam do centro para fora, cobrem a tela e voam para fora | chips, CPUs, wafers |
| 5 | **Objeto explodido** | papel cinza + faixa amarela vertical | camadas do objeto se separam em 3D isométrico, flutuando com sombra; etiqueta de papel datilografada, palavra à mão circulada em vermelho, ícone em círculo preto, parágrafo pequeno cinza | CPU: dissipador, die, substrato |
| 6 | **Foto em cartão** | papel cinza | entra por um **caleidoscópio** espelhado, vira foto em tela cheia e encolhe para um cartão de cantos redondos com legenda tipo documentário; um detalhe da foto é circulado e nomeado | sala limpa, "wafer de silício" |
| 7 | **Lousa final** | mesa de desenho clara com folhas, lápis, régua, objetos | lousa preta com moldura clara: palavra-chave em vermelho letra a letra, laço vermelho, frase à mão em branco, **fita amarela batida** por cima | "MICROCHIPS" + "do ENIAC ao seu bolso" |

Para um tema novo, pense em cada cena como uma pergunta: o que é **antigo/grande** (cena 2, riscado com X), o que é **pequeno/próximo** (cena 3, na mão), o que tem **dentro** (cena 5, explodido), **onde é feito ou usado** (cena 6, foto real), e qual é a **frase final** (cena 7).

## Materiais (classes do `midia.js`)

| Material | Como fazer | Classe/função |
|---|---|---|
| Recorte com sombra de mesa | PNG com alfa do Vision + sombra quente | `.pic.sh` |
| Recorte sobre tecido escuro | sombra mais dura e escura | `.pic.sh2` |
| Adesivo | contorno branco de 10 px (4 `drop-shadow`) + sombra | `.pic.stk` |
| Foto impressa | `<img>` com `border:16px solid #f1eee6; border-bottom-width:64px` e sombra | inline |
| Fita amarela rasgada | `.tape` + `M.rasgarTudo()` (bordas em zigue-zague) | `.tape` |
| Etiqueta de papel | `.tag` (papel branco, letra preta, sombra) | `.tag` |
| Letra à mão solta | `.hand` (Kalam 700) | `.hand` |
| Marcador (laço, seta, X, círculo) | `<path>` dentro de `<svg class="ann" filter="url(#mk)">`, revelado com `M.ink` | `M.laco`, `M.seta` |
| Faixa amarela | `div` de 480 px de largura, altura da tela + 120, `#f1cc1c` | inline |
| Lousa | `div` com fundo `tecido_escuro.jpg`, `border:18px solid #ebe7dd`, giro −2° | inline |
| Lápis, régua, folhas | SVG ou `div` simples com sombra — adereço pequeno não precisa de foto | inline |

## Cores

- **Amarelo** da fita: `#f0cd1c` (faixa `#f1cc1c`; X de marca-texto `#f3e46d` com opacidade .93; cursor `#e4c02a`).
- **Vermelho** do marcador: `#e53327` (lousa `#ec3a2b` com contorno `#4a0f08`).
- **Branco** do marcador: `#fff`; papel das bordas e etiquetas: `#f1eee6` / `#f7f6f2`.
- **Tinta** de texto: `#2e2c2a` (título), `#2a2826` (à mão), `#7f7e7a` (parágrafo).
- Superfícies: papel `#e2e2df`, tecido `#181716`, mesa `#c4c9cc`, madeira nogueira (ver `fotos.md`).

Fora isso, a cor vem **das fotos**. Não pinte nada de roxo, azul neon ou gradiente: o estilo é material, não digital.

## Tipografia

| Uso | Fonte | Tamanho em 1080×1920 |
|---|---|---|
| Título datilografado | Playfair Display itálico 600 | 172 px, `letter-spacing:-.012em` |
| Fita amarela | Kalam 700, branca com sombra marrom | 62 px (segunda linha 46 px) |
| Etiqueta de papel, palavra à mão | Kalam 700 | 54–64 px |
| Palavra da lousa | Dela Gothic One, vermelha com contorno escuro | 86 px (ajuste à largura) |
| Frase à mão na lousa | Kalam 400, branca | 60 px |
| Legenda de foto, parágrafo, créditos | Inter Tight 500 | 38 / 25 / 15 px |

Fontes extras disponíveis em `lib/fonts.css`: DM Serif Display, Permanent Marker, Caveat.

## Acabamento (sempre)

`M.acabamento({ grao: .16 })` no fim do script: **vinheta** radial escura nas bordas, **grão** de filme (opacidade .16) e **tremor de projetor** (±1,5 px a 15 qps). Junto com `M.marcador()` (o traço de marcador treme de leve a 12 qps), é o que tira a cara de "slide".

## Composição em 9:16

Todos os vídeos são verticais (1080×1920). Regras práticas:

- **Uma ideia por tela.** O texto principal de cada cena fica entre y = 400 e 1400; a faixa de baixo (1500–1920) é para objetos, sombra e créditos.
- **Objetos sangram a borda.** Mão, madeira, válvulas e adesivos saem para fora da tela; nada fica "centralizado num vazio".
- **Texto grande.** Fita a partir de 46 px; nada menor que 25 px, exceto os créditos.
- **Sobreposição.** Fita sobre foto, laço sobre fita, X por cima da foto e por baixo das fitas. A ordem das camadas no HTML é a ordem na mesa.
- **Folga das texturas.** O fundo `.bgimg` tem 114,8% do quadro (−7,4% de margem), para o empurrão de câmera não mostrar borda.
