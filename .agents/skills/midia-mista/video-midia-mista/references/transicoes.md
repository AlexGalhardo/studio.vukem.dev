# Transições

Use uma transição **diferente** em cada corte. O exemplo usa cinco, nesta ordem, e essa variedade é metade do estilo.

## Zoom com desfoque (título → cena 2)

A cena que sai mergulha num ponto (o cursor) e desfoca; a próxima entra já perto e assenta.

```js
const z = E('expo.in', t, .98, 1.15);                       // saída: 0,17 s acelerando
c1.style.transform = `scale(${1 + 2.6 * z})`; c1.style.transformOrigin = `${cursorX}px 900px`; c1.style.filter = M.filtroBlur(16 * z);
// entrada da cena seguinte:
c2.style.transform = `scale(${1.3 - .3 * E('expo.out', t, 1.15, 1.5)})`;
```

Som: `whoosh_in` no início do zoom e `hit_soft` no corte.

## Chicote vertical ou horizontal (2 → 3, 6 → 7)

As duas cenas andam **juntas**, como uma câmera que vira rápido: a que sai vai para cima (ou para a esquerda) e a que entra vem de baixo (ou da direita), com desfoque de movimento no meio.

```js
const cv = M.chicote(t, 2.28, 2.48);                        // { u: 0→1 (power2.inOut), blur: pico de 10 px no meio }
c2.style.transform = `translateY(${-H * cv.u}px)`;  c2.style.filter = M.filtroBlur(cv.blur);
c3.style.transform = `translateY(${H * (1 - cv.u)}px)`; c3.style.filter = M.filtroBlur(cv.blur);
```

As janelas das duas cenas precisam se sobrepor durante o chicote (no exemplo, a cena 3 começa em 2,28 e a 2 acaba em 2,48). **A textura de fundo (`.bgimg`) tem que ficar dentro da `.cam`** nas duas cenas. Se ficar fora, o fundo da cena que entra aparece de uma vez, cobrindo a que ainda está saindo, e o chicote vira um corte seco. Som: `swoosh` no início.

## Chuva de adesivos (3 → 5)

Não é corte: a cena 4 é uma camada por cima. Os adesivos cobrem a cena que sai, a cena seguinte começa a ser desenhada por baixo, e os adesivos voam para fora revelando-a. Veja `M.adesivos` e a receita da cena 4 em `cenas.md`. Som: `M.somAdesivos(t0)` (10 bolhas + pop) e `whoosh_out` na saída.

## Caleidoscópio (5 → 6)

A foto da cena seguinte aparece em 3×3 ladrilhos espelhados (os pares e ímpares invertidos em X e Y, então as bordas casam), girando 30° e convergindo para o ladrilho do meio em 0,26 s. No fim, o ladrilho do meio é idêntico à foto em tela cheia, então a troca para o cartão é invisível. Som: `glitch` (.25 s) + `whoosh_in`, e `shutter` no momento da troca.

## Slap em 4 quadros (dentro das cenas)

Toda peça que **chega** (foto, fita, adesivo, peça principal) entra com `M.slap(t, t0, k)`: escala 1 + k → 1 em 4 degraus de 0,05 s, sem suavização. O "tranco" é o que imita stop-motion. `k` de .3 a .45 (maior para a peça mais importante). Mostre a peça só a partir de `t0` (`display:none` antes). Som: `paper` no mesmo instante (ou `tom` + `click` para algo pesado caindo na mão).

## Regras

- **Nenhuma transição passa de 0,26 s.** O estilo é rápido.
- **Nunca dois cortes iguais seguidos.**
- **A transição carrega movimento**, não fica num fade. Se precisar de uma sexta transição, use um "slide de papel": a cena nova entra como folha deslizando por cima, com sombra, girando 3–5°.
