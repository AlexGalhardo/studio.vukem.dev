# Gramática de movimento

O estilo é **macio com toques secos**:

- O objeto e o fundo se movem com eases `back.out` suaves (overshoot pequeno), e o fundo deriva devagar.
- Os **toques** são secos: a mão levanta, afunda, um anel se abre e a cor nova **se espalha num círculo** a partir da ponta do dedo.
- Detalhes vivos em **stop-motion a 8–12 qps**: o contorno de giz da mão ferve, o selo balança e o objeto respira em degraus.

Os valores abaixo são os do exemplo (`videos/exemplo-airpainting/index.html`) e foram calibrados contra a referência.

## Roteiro-tipo (5 s)

| tempo | o que acontece | código |
|---|---|---|
| 0–0,4 | objeto principal entra **desfocado** (26 px) e um pouco maior (1,06), e foca | `pasta.foco(26*(1-E('power2.out',t,0,.4)))` |
| 0,15 | **selo** pula (pop .4 s) com o 1º texto: o que é | `RI.selo(..., {t0:.15})` |
| 0,35–0,7 | o objeto **se abre** (capa inclina 9°, contracapa −4°) | `pasta.abrir(E('back.out(2.2)',t,.35,.7))` |
| 0,72–1,08 | **mão sobe** da borda de baixo | `E('back.out(1.4)',t,.72,1.08)`, 820 px |
| 1,15 | **toque 1**: anel + tinta nova + selo troca ("pinte no ar") | ver "toque" abaixo |
| 1,8 | **toque 2**: outra cor + selo ("uma cor por tema") | |
| 2,3–2,7 | mão desce | `E('power3.in',t,2.3,2.7)` |
| 2,4–2,75 | **papéis caem** dentro do objeto (bounce) e o selo vira o resultado ("tudo no lugar") | `pasta.papeis(K.seg(t,2.4,2.75))` |
| 2,5–2,85 | objeto **fecha** e assenta 30 px para baixo | `back.out(2)` |
| 2,85–3,25 | fundo desfocado some | |
| 2,95–3,28 | objeto **encolhe e sai** | `back.in(1.6)` |
| 3,05–3,7 | **infográfico**: objetos pequenos caem e empilham por cor | `RI.pilhas` |
| 3,3–4,0 | números **contam** até o valor; nomes sobem | `power3.out`, .7 s |
| 3,95–4,3 | selo **alarga e vira a marca** | `back.out(1.6)`, .35 s |
| 4,2–4,5 | frase final sobe e aparece | `back.out(2)` |
| 4,5–5 | quadro final parado e completo | |

Ritmo: **algo novo a cada ~0,35–0,65 s**. O selo troca 4 vezes em 5 s.

**Versões:**

- **7–8 s:** três toques e três cores, um segundo objeto entrando depois do primeiro (cartão, celular), e o infográfico com 4 colunas.
- **3–4 s:** foco → um toque → infográfico curto → marca.

## O toque (o coração do estilo)

```js
RI.toqueDy(t, TAP)                                           // deslocamento vertical da mão
pasta.pintar(i + 1, 1000 * E('power2.out', t, tp + .02, tp + .5))   // raio do círculo da cor nova
RI.aneis(g, [{ t: tp, x, y, cor }])                          // anel na ponta do dedo
```

1. **Levanta:** 0,3 s antes, a mão sobe até 38 px num arco senoidal ("tomando impulso").
2. **Afunda:** no instante do toque, desce 16 px num pico triangular de ±0,07 s.
3. **Aperto:** o objeto encolhe 1,5% por 0,09 s.
4. **Anel:** um círculo na cor nova abre de 20 → 170 px em 0,45 s (`expo.out`). O traço afina de 14 → 0 e some.
5. **Tinta:** a cor nova cobre o objeto num **círculo centrado na ponta do dedo**. O raio vai de 0 → 1000 px em 0,48 s (`power2.out`), via `clipPath` em cada variante de cor (`pasta.pintar`). A origem fica **fora** do objeto, logo abaixo dele, então a borda curva da tinta sobe pelo objeto.
6. **Selo:** troca de texto **exatamente** no toque.
7. **Fundo:** as cópias desfocadas trocam de cor 0,15 s depois.

Para outros objetos, faça cada variante de cor num grupo com `clip-path` de um círculo e anime o raio. O `RI.pasta` mostra como fazer.

## Selo

- **Pop de entrada:** `back.out(2)` em 0,4 s.
- **Troca:** um **flip**, que achata em Y até 15% e volta, em ±0,08 s em volta do instante. O texto troca no meio, quando está achatado.
- **Balanço:** ±3 px em Y e ±3° de rotação em degraus de 8 qps.
- **Final:** alarga de 200×200 para 560×160 em 0,35 s (`back.out(1.6)`), endireita para −2° e para de balançar.

## Infográfico de pilhas

- Cada objeto cai 520 px com `bounce.out` em 0,32 s.
- **Intervalos:** 0,085 s entre objetos da mesma pilha e 0,05 s entre pilhas, então as pilhas crescem juntas.
- **Achatamento** no impacto: escala 1,06 × 0,9 por ±0,04 s.
- **Torto:** cada objeto tem ±6 px e ±3° fixos, como uma pilha de verdade.
- **Altura:** 62 px por objeto. O número fica ~90 px acima do topo da pilha, conta até o valor em 0,7 s e sobe 20 px ao aparecer.
- **Proporção:** a quantidade de objetos por pilha é **proporcional** ao valor, arredondada. A pilha mais alta tem 5 a 6.

## Fundo desfocado

- Opacidade de .5 a 1 (varia por item).
- **Deriva:** sobe `22 px/s × v` e balança `±18 px` em X (`sin(t·.7·v + i)`).
- **Rotação:** fixa em ±10°, nunca gira.
- Aparece em 0,4 s no começo e some em 0,4 s antes do infográfico.

## Microdetalhes que vendem

- O objeto principal **respira**: ±3 px em Y em degraus de 12 qps, com ±0,8° em 8 qps.
- A mão **oscila** ±6 px em X (`sin(t·3.1)`) e ±1,5° em 8 qps enquanto espera.
- O contorno de giz **ferve** sempre, mesmo com a mão parada.
- Nada para totalmente até o último 0,5 s.

## Regras do motor

Tudo é função de `t` dentro de `onTick`. Use as eases por nome com `RI.E(nome, t, a, b)`, picos com `RI.bump(t, tp, w)` e degraus com `RI.q(t, qps)`. Nada de `Math.random()`: use `K.rng(seed)` se precisar de variação.
