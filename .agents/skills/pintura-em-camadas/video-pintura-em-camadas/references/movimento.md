# Movimento — pintura em camadas

## O que a referência faz (medido)

Plano único de 12 s (Escola de Atenas), medido com ORB + RANSAC quadro a quadro:

- **Escala do plano de foco 1,00 → 1,54 e do primeiro plano 1,00 → 2,39 em 10 s.** A razão bate com um dolly de verdade (câmera andando em z a velocidade constante): `s(t) = z / (z − v·t)`; a frente está a ~0,6 da distância do foco.
- **A escala acelera de leve** (velocidade constante em z), sem ease-in-out teatral.
- **Deriva lateral pequena** (a câmera desce e vira um pouco): parallax também de lado.
- **Para seco** aos 10 s e segura 2 s parado.
- **Dissolução da sala** entre 2,5 e 4 s (25–33% da duração), enquanto anda.

## Roteiro-tipo (7,5 s, 30 qps)

| t (s) | fase | câmera | camadas | sala |
|---|---|---|---|---|
| 0,0–1,9 | museu | já andando; S × 1,32 no 1º segundo, acelerando | coplanares (p = 0) | parede, moldura, placa, facho, poeira |
| 1,9–3,0 | atravessa | S chega a ~0,58 em 2,6 s | começam a separar (p sobe) | moldura voa (kw 1 → 2,6), parede dissolve (2,0–2,9) |
| 3,0–6,4 | dolly | S 0,58 → 0,95, pan até a figura principal | p → 1 (`power1.in`: a frente acelera) | — |
| 6,4–7,5 | parado | para (derivada zero na última chave) | — | título em 6,55; crédito em 7,05 |

Proporção da referência: ~25% sala, ~15% dissolução, ~45% dolly, ~15% parado. Mantenha-a em outras durações (6–8 s).

## A câmera (`PC.camera`)

```js
const cam = PC.camera({
  S: [[0, S0], [1.0, S0 * 1.32], [2.6, .58], [5.9, .93], [6.4, .95]],   // px de tela por px da obra (plano de foco)
  A: [[0, pw / 2, 900], [2.6, 1790, 760], [6.4, 1690, 860]],             // ponto da obra no centro da tela
  sep: [1.9, 6.4],          // janela em que as camadas se separam (p: 0 → 1, power1.in)
  atravessa: [1.9, 3.0], voo: 1.6,   // a moldura cresce até 1 + voo vezes mais que a obra
  dissolve: [2.0, 2.9] });           // a parede e a moldura somem
```

- `S` e `A` são **chaves monotônicas** (`PC.chaves`, Fritsch–Carlson): nunca passam do ponto e param com derivada zero na última chave — é o "para seco" da referência, sem tranco.
- `S` é interpolado em **log** (zoom com velocidade perceptual constante).
- Cada camada é desenhada com escala `S · K^p` em torno do centro da tela: com `p = 0` a obra é plana; com `p = 1` a frente (K > 1) está K× maior que o foco. Mover `A` desloca mais as camadas da frente: é o parallax lateral.
- **S0** = largura da obra no museu / largura da imagem (940 / 3824 no exemplo).
- **S final** ≈ 0,9–1,0: a obra em resolução nativa no foco. Mais que 1,1 amolece (a imagem do Commons tem 3840 px).

### Regras que evitam área vazia (obra larga em 9:16)

- Quando a parede some (`dissolve[1]`), o céu estendido tem de cobrir o alto e as camadas da frente (com `estender_baixo`) o pé da tela. Confira `--at` em `dissolve[1]` e logo depois.
- Por isso o museu aproxima mais rápido (S × ~2,4 em 2,6 s) e o dolly dentro da tela é lento (S × ~1,6 em 3,8 s, como a referência).
- O `A.y` do meio do caminho fica mais alto que o do fim (o céu sobra em cima, onde é fácil estender).

## Parâmetros do exemplo

| parâmetro | valor | por quê |
|---|---|---|
| `dof` | 30 px | frente K 1,45 → ~9 px; carro K 1,55 → ~11 px; céu K 0,8 → ~7 px |
| `voo` | 1,6 | a moldura sai da tela em ~1 s sem parecer "explodir" |
| `sepEase` | `power1.in` | a separação acelera junto com o dolly, como a frente da referência |
| brilho da moldura | 0 → 2,6 s, .4 | um reflexo de spot atravessa o dourado enquanto a câmera anda |
| título | `PC.titulo` em `para + .15` | sobrelinha fecha o espaçamento .6 → .34em (.7 s), nome desfoca → nítido (.75 s), fio abre (.7 s) |

## O que NÃO fazer

- Cortes, zooms de soco, chicotes: o estilo é um plano só e lento.
- Ease-in-out longo no fim: a referência para quase seco; as chaves já param suave o bastante.
- Girar a câmera: só translação e dolly.
- Separar camadas no museu (p > 0 com a parede inteira): parece uma janela, não um quadro.
