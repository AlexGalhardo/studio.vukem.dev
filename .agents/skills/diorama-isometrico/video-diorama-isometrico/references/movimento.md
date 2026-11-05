# Movimento: tempos, transformações e ritmo

## Sumário
1. O que a referência faz (medido)
2. Roteiro-tipo de 8 s
3. As transformações (metamorfose)
4. Eventos secundários
5. HUD: entradas e saídas
6. Regras de ritmo

## 1. O que a referência faz (medido)

- 1 plano contínuo; loop perfeito de **10,0 s** (diferença entre t e t+10 s ≈ 1,8/255). Câmera 100% parada.
- ~4 paisagens por loop (≈2,5 s cada): pico alto → rio corta o bloco da direita para a esquerda e a vegetação acompanha → paredão + cânion → pico central → vários picos → volta.
- A mudança é uma **frente suave** que atravessa o bloco: nada pula, nada tem overshoot elástico; a velocidade é constante dentro de cada transição (ease in-out leve).
- Um objeto flutua o tempo todo (nave) com balanço leve e sombra própria — no exemplo vira o bondinho e o barco.

## 2. Roteiro-tipo de 8 s (o exemplo)

| t (s) | 3D | HUD | som |
|---|---|---|---|
| −0,35 → 1,75 | planície **incha** a partir do centro (maciço) | título letra a letra (0–0,6), etiqueta 01 (0,35) | `swoosh`, `ronco` |
| 1,65 → 3,6 | **erosão**: frente vem do canto do mar e deixa só os domos | etiqueta 02 (1,8) | `ronco`, `cascalho` |
| 2,15 → 4,6 | água sobe de −1,5 a 0 (enche o fundo cavado) | etiqueta 03 (3,55) aponta para a água | `mar` |
| 3,9 → 5,3 | mata brota da praia para cima | — | `folhas` |
| 4,6 → 5,65 | estações estouram, cabos se desenham | etiqueta 04 (5,0) | `pop`×3, `thread`×2 |
| 5,5 → 7,9 | bondinhos cruzam os cabos; barco desliza | fio da etiqueta segue o bondinho | `bonde` |
| 6,35 | — | carimbo bate (4 degraus) | `hit_soft`, `paper`, `chime` |

Comece o primeiro passo **antes de 0** (−0,35 s) para o quadro 0 já ter movimento.

## 3. As transformações (`DI.metamorfose`)

- `modo: 'inchar'` — tudo sobe junto e quem tem `u` menor vai na frente: `w = suave(0,1, p·(1+larg) − u·larg)`. Use para soerguimento, "nascer" de montanha. Evita o pico em forma de espinha.
- `modo: 'onda'` — uma frente varre o bloco na ordem de `u`: `w = onda(u, p, larg)`. Use para erosão, rio que entra, mar que avança.
- `u(x,z)`: a ordem da frente (0 = primeiro). Distância a um centro (`hypot(x−cx, z−cz)/7`) para inchar; projeção numa direção (`(1 − (x/5 + z/4)/2)/2`) para varrer do canto +x+z ao −x−z. Some `.08·fbm` para a frente ficar irregular.
- `larg`: .35–.45. `crista`: +.2 (incha na frente) ou −.15 (afunda na frente).
- Ease de cada passo: `io` (quad in-out). Duração: 1,8–2,1 s por passo; sobreponha ~0,1 s entre passos.

## 4. Eventos secundários

- **Água**: `A.set(lerp(-1.5, 0, saida(prog(t, T.mar))))`. Comece junto com a erosão.
- **Mata**: `t0` de cada tufo = início + `suave(.1, 2.2, altura)·.95` + acaso·.3 → brota da beira d'água para cima, em ~1,4 s. Entrada `back.out(1.9)` em .4 s.
- **Adereços** (casinhas, estações): `backOut` em .35 s, escalonados .12 s.
- **Cabos**: `cabo.mostrar(io(...))` em .5 s, o segundo .2 s depois.
- **Objeto que viaja** (bondinho, barco): `io(prog(t, [5.5, 7.9]))` ao longo de `cabo.P(u)`; balanço `.02·sin(5t)`.

## 5. HUD: entradas e saídas

- Título: letras `yPercent 70 → 0`, `scale .6 → 1`, `back.out(2.2)`, .38 s, `stagger .028`.
- Linha FIG: abre do centro (`clip-path inset 50% → 0`), .4 s `power3.out`. Subtítulo: máscara em `steps(16)` (.5 s), cara de digitação.
- Etiqueta (`DI.etiquetas`): abre por máscara da esquerda .32 s (cúbica), fio corre .3 s (+.14 s), anel do alvo estoura `back.out(2.2)` .25 s (+.4 s). Saída: máscara para a direita .24 s.
- Carimbo: `DI.carimbar` — escala 1,45 → 1 em 4 degraus (.2 s), rotação −14°.

## 6. Regras de ritmo

- Sempre há pelo menos 2 coisas se mexendo: relevo/água + HUD, ou bondinho + barco + ondulação da água (`uTime` já anima a água).
- Uma etiqueta nova a cada ~1,6 s; a última fica até o fim.
- Termine com 1,5–2 s de "respiro" com movimento lento (objetos viajando), não com tudo parado.
