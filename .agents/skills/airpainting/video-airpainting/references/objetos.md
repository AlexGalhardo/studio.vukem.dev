# Objetos: API do `RI` e como trocar a pasta por outra coisa

A pasta é só o objeto do exemplo. O estilo funciona com qualquer objeto **grande, simples e de silhueta clara**: cartão de crédito, celular, documento, caixa, pizza, xícara, cadeado, envelope, nuvem, frasco, etc. Todos seguem a mesma receita da pasta.

Para testar um objeto novo parado, ao lado dos prontos:

```bash
node render.mjs folha --at=0.5     # → previews/folha-de-objetos/00.jpg
```

Edite `videos/folha-de-objetos/index.html` até o objeto ler bem e só então leve para o vídeo.

## Coordenadas

Todo construtor desenha com a **origem no meio da base** do objeto (0,0), crescendo para cima (y negativo). Para posicionar, use `RI.tf(g, x, y, escala, rotação)`: (x, y) é onde a base do objeto pousa na tela. Assim os objetos "assentam" no chão e empilham naturalmente.

## API

### Instalação e utilidades

| chamada | o que faz |
|---|---|
| `RI.instalar({ papel, grao, giz })` | papel de fundo, filtros `ri-dither` (pontilhado) e `ri-rough` (giz), gradientes de todas as cores e mãos, estilos. **Chame primeiro.** |
| `RI.tf(el, x, y, s, r, sy)` | transform de um `<g>`: translate, rotate e scale (`sy` opcional para achatar) |
| `RI.show(el, on)` | liga ou desliga um `<g>` |
| `RI.E(ease, t, a, b)` | ease por nome entre `a` e `b` (0 → 1) |
| `RI.pop(t, t0, d)` | entrada elástica 0 → ~1,1 → 1 (`back.out(2)`) |
| `RI.bump(t, tp, w)` | pico triangular em `tp` com meia-largura `w` (toques, apertos) |
| `RI.q(t, qps)` | tempo em degraus (stop-motion) |
| `RI.passo(t, [[t, v], ...], ini)` | valor em degraus no tempo |
| `RI.defs(html)` | acrescenta `<defs>` (gradientes, clipPaths, máscaras) |
| `RI.blur()` | cria um filtro de desfoque animável: `{ id, el }`; mude `el.setAttribute('stdDeviation', px)` |

### Formas e técnica

| chamada | devolve |
|---|---|
| `RI.camada(d, cor, 'f'\|'b')` | o path `d` em base lisa + camada pontilhada (`'b'` é a versão de contracapa, mais escura) |
| `RI.ret(w, h, r)` | path de retângulo arredondado apoiado na base |
| `RI.circ(r)` | path de círculo apoiado na base (centro em 0,−r) |
| `RI.cartao(cor, w, h, r)` | cartão pontilhado |
| `RI.bola(cor, r)` | bola pontilhada |
| `RI.folha(w, h, linhas)` | folha de papel branca com linhas de texto cinza (sem pontilhado: papel é liso) |
| `RI.mini(cor, w, h)` | pasta fechada pequena (fundo e infográfico) |

### Peças com estado (devolvem controles)

| chamada | controles |
|---|---|
| `RI.pasta(g, { cores, w, h, origem })` | `pos(x,y,s,r)`, `abrir(0..1)`, `papeis(0..1)`, `pintar(i, raio)`, `foco(px)` |
| `RI.pintavel(g, d, cores, { origem, tipo })` | devolve `pintar(i, raio)`: qualquer forma com troca de cor por círculo |
| `RI.mao(g, { pele })` | `pos(x, y, rot=6, escala=1)`, `show(on)`. A ponta do dedo é (0,0). |
| `RI.toqueDy(t, toques, alto, fundo)` | deslocamento vertical da mão (levanta antes, afunda no toque) |
| `RI.aneis(g, [{t,x,y,cor}])` | devolve `tick(t)`: anéis de toque |
| `RI.selo(parent, [[t, html]], { x, y, lado, t0, final:{t,w,h} })` | devolve `tick(t)` |
| `RI.fundo(parent, itens, { cores, desenho })` | devolve `tick(t, corAtual, alfa)`; `desenho: k => svg` troca a pastinha por outro objeto |
| `RI.pilhas(g, parent, colunas, { base, passo, t0, tNum, desenho, alturaObj, sufixo })` | devolve `tick(t)`; `tick.sons()` marca os pops e ticks |
| `RI.somToque(tp, i)` | cues de um toque (clique, bolha, brilho, pop) |

## Receitas de objetos (testadas na folha)

```js
// celular: corpo lilás arredondado + reflexo de tela
RI.camada(RI.ret(170, 300, 30), 'lilas') + `<rect x="-60" y="-280" width="120" height="14" rx="7" fill="#fff" opacity=".7"/>`

// caixa em 3/4: frente (capa) + tampa (contracapa, mais escura)
RI.camada('M-120 0V-150L0 -200L120 -150V0Z', 'ambar') + RI.camada('M-120 -150L0 -100L120 -150L0 -200Z', 'ambar', 'b')

// gráfico de pizza: uma fatia + o resto, em cores diferentes
RI.camada('M0 -130L0 -260A130 130 0 0 1 112.6 -65Z', 'rosa') + RI.camada('M0 -130L112.6 -65A130 130 0 1 1 0 -260Z', 'menta')

// cartão de crédito: cartão + chip + faixa
RI.cartao('azul', 420, 260, 26) + `<rect x="-170" y="-200" width="70" height="52" rx="10" fill="#ffd27a"/><rect x="-170" y="-80" width="200" height="16" rx="8" fill="#fff" opacity=".6"/>`
```

Regras para desenhar um objeto novo:

1. **Silhueta primeiro.** Se o objeto não se reconhece só pela silhueta preenchida de uma cor, simplifique.
2. **Uma ou duas camadas pontilhadas** por objeto: a face principal (`'f'`) e, se houver, uma lateral ou tampa (`'b'`). Detalhes (chip, botão, tela) vão **lisos**, em branco translúcido ou numa cor clara.
3. **Papel é liso.** Folhas, notas e etiquetas ficam em `#fbfaf7`, sem pontilhado, para contrastar com o objeto.
4. **Tamanho:** o objeto principal ocupa ~65% da largura (700 px em 1080). Os objetos do fundo e do infográfico têm 170–260 px.
5. **Perspectiva:** no máximo uma inclinação simples (`skewX` de 4–9°) para sugerir "abrir". Nada de 3D.

## Trocar a pasta por outro objeto no exemplo

1. Troque `RI.pasta(...)` por um `<g>` com `RI.pintavel(g, d, cores, { origem })`.
   - A **origem** é a ponta do dedo em coordenadas do objeto: `(dedoX − objetoX, dedoY − objetoY)`.
   - O raio vai até ~1000 (`power2.out`, 0,48 s), como na pasta.
2. O gesto de "abrir" tem equivalentes: um celular **acende** (retângulo branco na tela com opacidade 0 → .6), uma caixa **abre a tampa** (rotação da tampa) e um cartão **vira** (`scaleX` 1 → 0 → 1 trocando a face no meio).
3. No fundo e nas pilhas, passe `desenho: k => RI.cartao(k, 230, 150)` (ou o seu objeto) para `RI.fundo` e `RI.pilhas`. Se mudar a altura do objeto das pilhas, ajuste `alturaObj`.
4. Os papéis que caem dentro viram o conteúdo do objeto: notificações que surgem no celular, moedas que caem na caixa, etc.

## Outras poses de mão

- **Apontando para a esquerda:** a mesma mão girada, com `mao.pos(x, y, -84)`. O polegar passa a apontar para baixo. Ela entra pela borda direita: anime `x` em vez de `y`.
- **Tocando de cima:** `mao.pos(x, y, 174)` faz a mão descer do topo, de cabeça para baixo, apontando para baixo.
- **Punho:** ele termina num corte reto a **980 px × escala** da ponta do dedo. Posicione a mão para que esse corte fique **fora da tela**, na borda por onde ela entra. A sombra pontilhada gira junto com a mão, o que é aceitável.
- **Pose nova** (mão aberta, polegar para cima, pinça): copie `RI.mao` e troque as formas, mantendo as três camadas.
  - **Contorno:** as mesmas formas, 18 px mais grossas, em `#16121c`, num `<g filter="url(#ri-rough)">`. Fica **por baixo**.
  - **Preenchimento:** as formas com o gradiente da pele, por cima.
  - **Sombra pontilhada:** um retângulo com o gradiente `ri-ghd-<pele>`, passado pelo `ri-dither` e mascarado pela silhueta (`<mask>` com as formas em branco).

  Dedos são cápsulas: um `<path>` de dois pontos com `stroke-linecap="round"` e `stroke-width` igual à grossura. A palma é uma elipse. Unhas pretas na ponta de cada dedo esticado.
