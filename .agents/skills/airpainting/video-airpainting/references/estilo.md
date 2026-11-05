# Estilo: o que faz parecer "airpainting"

O visual tem cinco ingredientes:

1. **Papel claro e quente** de fundo, liso e quase vazio.
2. **Objetos chapados com gradiente pontilhado de risografia.** É a assinatura do estilo.
3. **Profundidade de campo:** cópias pequenas e desfocadas do objeto flutuam ao fundo.
4. **Uma mão de cartoon** com contorno de giz que treme, apontando e tocando.
5. **Um selo** (sticker) violeta com letra laranja grossa, que troca de texto.

Se faltar um deles, vira "flat design genérico". Se os cinco estiverem lá, lê como a referência.

## Papel

- **Cor:** `#f2efe9` (`RI.PAPEL`). É quente e levemente acinzentado; branco puro mata o estilo. Mude com `RI.instalar({ papel: '#...' })`.
- **Textura:** nenhuma no fundo. O grão vive **dentro** dos objetos.
- **Texto corrido:** `#2a2440` (`RI.TINTA`), um violeta quase preto. Nunca `#000`.

## O pontilhado de risografia (a técnica)

Um gradiente liso parece "app genérico". Espalhar o gradiente com ruído (displacement) **não funciona**: a cor muda pouco em poucos pixels e o grão some.

O que funciona é o **pontilhado por limiar**, como numa impressão risográfica de duas tintas. Cada forma tem duas camadas:

1. **Base lisa:** a forma preenchida com um gradiente suave **claro → médio** (`ri-gf-<cor>`), sem a cor escura.
2. **Camada escura:** a mesma forma, na **cor escura chapada**, com **opacidade em gradiente** (0 no canto claro → 1 no canto escuro), passada pelo filtro `ri-dither`. O filtro compara a opacidade de cada pixel com um ruído fino:
   - opacidade maior que o ruído → o pixel vira **um ponto 100% opaco**;
   - opacidade menor → transparente.

O resultado são pontos sólidos cada vez mais densos rumo ao canto escuro, com borda nítida. É exatamente a transição granulada da referência.

```js
RI.camada(d, 'azul')        // → <path base lisa/> + <path camada escura com filter="url(#ri-dither)"/>
RI.camada(d, 'azul', 'b')   // versão "contracapa" (mais escura), para a parte de trás ou a lateral de um objeto
```

Detalhes que importam (já resolvidos no `riso.js`):

- **Ruído:** `feTurbulence` com `baseFrequency .62` e 2 oitavas. O vermelho dele é esticado (`2R − .5`) para cobrir 0–1 sem acumular nos extremos. Com o mapeamento antigo (`3,2R − 1,1`), muitos pixels caíam em 0 e aparecia uma **linha reta** onde o pontilhado começava.
- **Dureza:** a comparação usa ganho 10 (`k2=10 k3=-10`) e depois um degrau (`feFuncA discrete "0 1"`). Os pontos ficam binários, sem meio-tom.
- **Cor do ponto:** vem da própria camada, com o alfa forçado a 1 (outro `discrete`). Por isso um único filtro serve para todas as cores.
- **Direção:** todo gradiente vai do **canto superior direito** (claro) ao **inferior esquerdo** (escuro): `x1=1 y1=0 → x2=0 y2=1`, em `objectBoundingBox`. A luz vem sempre do mesmo lado em todos os objetos.
- **Região do filtro:** `objectBoundingBox` com 0–100% funciona para formas com área. Para um **traço** (path só com `stroke`, como uma linha horizontal), a caixa tem altura ~0 e o filtro corta tudo. Nesse caso use `filterUnits="userSpaceOnUse"` com uma região fixa, como o `ri-rough` faz.
- **Tamanho do grão:** é fixo em pixels de tela. Objetos pequenos (as pastinhas do gráfico) têm o mesmo grão que os grandes, como numa impressão.

## Cores

Cada cor em `RI.CORES` tem:

- `f` (capa): `[claro, médio, base escura, cor do pontilhado]`;
- `b` (contracapa ou lateral): `[claro, escuro, pontilhado]`;
- `deep`: a cor de acento para números e anéis.

| nome | claro → escuro | uso típico |
|---|---|---|
| `azul` | ciano-gelo → violeta-azul `#4a3ff0` | a cor-mãe do estilo; abre e fecha o vídeo |
| `rosa` | rosa-chiclete → vermelho-coral | 1ª troca de cor, "emoção" |
| `ambar` | creme → laranja-queimado | 2ª troca, "calor", destaque |
| `verde` | menta-clara → verde-bandeira | dinheiro, ok, crescimento |
| `lilas` | lavanda → violeta | celular e telas |
| `menta` | água → petróleo | dados, ciência |

Regras:

- **No máximo 3 cores de objeto por vídeo.** A referência usa azul + rosa; o exemplo usa azul, rosa e âmbar.
- **O azul é a cor de casa.** Comece nela e use-a na barra mais alta do infográfico.
- **Cor nova:** escolha um tom bem claro (quase pastel), um médio e um escuro **saturado** para o pontilhado. Se o escuro for acinzentado, o grão vira sujeira. Use `tools/referencia.py` para tirar os tons de uma referência.

## Profundidade de campo

- **Foco:** o objeto principal é o **único nítido** e fica grande no centro (~65% da largura).
- **Fundo:** 6 a 8 cópias pequenas (`escala .45–1`) e **desfocadas** (`blur` 7–14 px) espalhadas pelas bordas. Nunca ponha uma atrás do objeto principal. Elas sobem devagar (22 px/s × velocidade) e balançam de lado. Isso é `RI.fundo`.
- **Cor:** as cópias **mudam junto** com o objeto principal, logo depois de cada toque. Esse eco vende a ideia de "pintar".
- **Entrada:** o objeto principal entra **desfocado** (26 px) e foca em 0,4 s, como uma lente procurando foco (`pasta.foco(px)`).

## A mão

A mão é cartoon, propositalmente diferente dos objetos:

- **Contorno:** preto grosso (`#16121c`, ~9 px visíveis), com **borda de giz** que ferve a 12 qps (`ri-rough`: turbulência `.09`, deslocamento 7 px, semente trocada a cada 1/12 s).
- **Pele:** amarela por padrão. É uma base lisa amarelo-claro → amarelo-gema, mais **sombra laranja pontilhada** no lado de baixo/direito (a mesma técnica, mascarada pela silhueta). Outras peles: `rosa`, `morena`, `azul` (`RI.MAOS`).
- **Unhas:** pretas, uma no indicador e outra no polegar. Dão o charme da referência.
- **Dedos dobrados:** três rolos com contorno próprio e a ponta em laranja.
- **Pose:** indicador para cima, levemente inclinado para a direita (+6°). O polegar aponta para a esquerda.
- **Tamanho:** grande. A mão ocupa ~55% da largura e sai pela borda de baixo; o punho nunca aparece.

## O selo

- **Forma:** quadrado de 200 px, cantos de 16 px, violeta `#4a3df0`, sem sombra.
- **Texto:** Unbounded 800, laranja `#ffb020`, minúsculas, 2 a 3 linhas curtas centradas, entrelinha .92, tracking −.03em. O tamanho se ajusta à linha mais longa (máx. 50 px).
- **Posição:** centralizado, **acima** do objeto principal (centro em y≈400 numa tela de 1920).
- **Final:** alarga para virar a **marca** (560×160) com uma palavra só, até 80 px.
- **Textos:** 1 a 3 palavras por troca. São os "passos" da explicação: o que é → o que você faz → o resultado → a marca.

## Composição 9:16 (1080×1920)

| faixa (y) | o que fica |
|---|---|
| 300–500 | selo |
| 590–1200 | objeto principal (base em y=1200) |
| 1250–1920 | mão (ponta do dedo em ~1290, logo abaixo do objeto) |
| 880–1560 | infográfico (números em cima, nomes em 1554) |
| 1715 | frase final em Inter Tight 600 de 42 px, com o trecho-chave em violeta 800 |

**Para 1:1 ou 16:9:** mantenha o selo acima e o objeto no centro. A mão entra pela borda de baixo à direita e o infográfico ocupa a largura toda. Recomponha as posições em vez de escalar o vídeo inteiro.

## Tipografia

- **Unbounded 800:** selo e números. Larga, redonda e pesada.
- **Inter Tight 600:** nomes das colunas e frase final.
- **Disponíveis no projeto:** Dela Gothic One, Rubik Mono One, Bricolage Grotesque e Caveat (anotação à mão).

Nada de texto grande além do selo, dos números e da frase final. O estilo explica com **objetos**, não com parágrafos.

## O que evitar

- Gradiente liso sem pontilhado: vira app genérico.
- Sombra projetada nos objetos: a profundidade vem só do desfoque.
- Contorno nos objetos: só a mão tem contorno.
- Mais de 3 cores de objeto, ou fundo colorido.
- Fundo branco puro ou texto preto puro.
- Ícones pequenos e detalhados: os objetos são grandes e simples.
- Mão realista, ou mão sem as unhas pretas.
