# Estilo: diorama isométrico

## Sumário
1. As 3 marcas
2. Paleta (hex)
3. Materiais e acabamento
4. Composição 9:16
5. Tipografia e HUD
6. O que NÃO fazer

## 1. As 3 marcas

1. **Diorama de terreno recortado** — um bloco retangular de solo (topo com relevo, 4 faces cortadas retas) sobre uma base técnica verde-água (plinto com painéis de janela hexagonal, trilho azul duplo, postes com lâmpada, deck com tubos), no meio de um chão infinito de placas. Câmera ortográfica quase isométrica (azimute 45°, elevação ~35°), **parada**.
2. **Acabamento de HQ** — luz em 5 faixas chapadas (sem degradê de luz), contorno a nanquim roxo-escuro (~1,3 px) em silhuetas e vincos, hachura de gravura (linhas quebradas) nas faixas escuras e na sombra projetada, salpicos escuros e claros espalhados, sombra projetada dura e **roxa** caindo para a direita e um pouco para trás.
3. **Relevo que se metamorfoseia** — sem cortes: uma paisagem vira a próxima numa onda que atravessa o bloco (ou incha a partir de um centro), com uma crista que viaja com a frente. As faces cortadas acompanham o perfil, e a água aparece como faixa azul na face.

## 2. Paleta (hex, amostrada da referência)

| papel | hex |
|---|---|
| chão (topo da tela → perto da câmera) | `#0a9d92` → `#60d19e` |
| sombra no chão | `#55415b` (hachura `#2c2142`) |
| topo de areia (luz) | `#ea9a6e`, realce `#f7bb8c` |
| face cortada iluminada | `#f39f6f` → `#d09983` embaixo |
| face cortada na sombra | `#8a2d57` |
| rocha (meio → luz) | `#7b0f27` → `#9c2238` → `#d27050` |
| base técnica | `#3bb390`, claro `#94cdad` |
| trilho | `#4a63c8` |
| água | `#7b9cbb`, espuma `#eef4ef` |
| mata | `#9cc79f` / `#78a88e` / sombra `#4f7a78` |
| nanquim | `#241a33` |
| papel das etiquetas | `#f6e7cf`, número em `#7b0f27` |

As rampas completas (5 tons + cor da sombra projetada `cs` + cor da hachura `hc`) estão em `DI.RAMPAS`: `areia`, `rocha`, `face`, `chao`, `base`, `deck`, `trilho`, `agua`, `mata`, `vermelho`, `creme`.

## 3. Materiais e acabamento

Todo objeto usa `DI.material({...})` (Lambert por baixo, saída trocada por rampa):

- **faixas** `[a,b,c,d]`: limiares de N·L entre os 5 tons. Padrão `[.1, .25, .42, .86]`: topo e face esquerda caem no tom 4 (salmão), face direita no tom 1 (magenta).
- **rocha**: segunda rampa usada onde o terreno é íngreme (normal.y < ~.7) — é isso que faz paredões carmim sobre planície salmão.
- **hachura** `[intensidade, linhas/unidade, espessura, ângulo]`: só aparece nas faixas escuras e na sombra projetada.
- **estrias** `[int, freq, brilho]`: riscos verticais de gravura nos paredões.
- **salpico** `[escuros, claros, células/unidade]`: pintinhas como as da referência.
- **grad**: degradê por posição (chão clareia para perto da câmera; face cortada rosa embaixo).
- **mapa**: textura de canvas com convenção de canais (R multiplica, G = nanquim, B = brilho) — painéis, grelhas, juntas. Use `DI.textura(w,h,desenhar)` e as cores `DI.CV`.
- **Contorno a nanquim**: pós-processo no `DI.palco` (laplaciano de profundidade + diferença de normais, em superamostragem 2×). Objetos na camada 1 (`obj.layers.set(1)`) ficam sem contorno.
- **Grão** leve no pós (`grao`, padrão .022), sem vinheta e sem bloom.

## 4. Composição 9:16

- Bloco de 10 × 8 unidades ocupando ~95% da largura, centro do topo em ~55% da altura (`meia: 6.6`, `alvo: [0, 1.2, 0]`).
- Profundidade do bloco ~2,3 e plinto ~1,5 (a base técnica é parte do visual: não esconda).
- Morros altos ficam **atrás** (canto −x −z) e sobem para a área livre de cima; terra, mata e casinhas na frente/esquerda; água à direita (aparece na face +x como faixa azul).
- Terço de cima: título + etiquetas. Rodapé: nota técnica ("ESCALA VERTICAL EXAGERADA") ou créditos.
- Sombra do bloco grande à direita (luz `sol: [-.55, .68, 1]`, ~30° de elevação).

## 5. Tipografia e HUD

- **Chakra Petch** (técnica, quadrada): título 700 em salmão `#f39f6f` com contorno nanquim 8 px e sombra dura `9px 9px 0 #3e2f46` (a mesma sombra roxa do diorama); linha "FIG. 01 — LUGAR" 600 espaçada; subtítulo 600 em nanquim.
- **Etiquetas técnicas** (`.di-tag`): caixa creme, borda nanquim 5 px, sombra dura roxa, número em caixa carmim, título 700 + linha 500 carmim; fio de nanquim do canto da etiqueta até um anel no ponto 3D (que acompanha o relevo ou um objeto em movimento).
- Uma etiqueta por estado, no mesmo lugar (y ≈ 436). Texto curto: título ≤ 30 caracteres, linha ≤ 36.
- Fecho opcional: carimbo postal/selo que bate em 4 degraus.

## 6. O que NÃO fazer

- Mexer a câmera, cortar de plano ou dar zoom: quebra a leitura de maquete.
- Degradê suave de luz, bloom, reflexo, céu: o estilo é chapado e de papel.
- Sombra preta ou cinza: a sombra é roxa e hachurada.
- Relevo liso demais: sem `cristas` o morro vira "plástico"; sem `sulcos` o domo vira bala.
- Inventar dados no HUD. Escala vertical exagerada? Diga isso na tela.
