# Estilo visual: traço simples

O visual parece papel colorido recortado com tesoura e colado num fundo liso, filmado quadro a quadro.

- **Formas:** tudo é forma chapada, de uma cor só. Não tem contorno, sombra, gradiente, textura nem 3D.
- **Volume:** quem dá volume é a sobreposição de formas e um brilho branco pequeno.
- **Bordas:** são levemente irregulares e "fervem", ou seja, tremem um pouquinho a cada 1/12 s, como animação desenhada à mão.

Um bom teste é se o quadro parado funcionaria como adesivo. Se precisasse de sombra ou de linha para ser entendido, a forma está complicada demais.

## Paleta

São 6 cores saturadas, mais preto e um branco quente. `TR.P` começa com a paleta `neon` (amostrada da referência original):

| chave | neon | papel |
|---|---|---|
| `k` | `#000` | fundo de abertura e de encerramento; olhos, narizes, portas, máscaras |
| `L` | `#d3f76f` lima | o fundo "da marca"; pompons, bolinha |
| `R` | `#e04a50` vermelho | corpos, coleiras, corações |
| `V` | `#655af6` violeta | fundo; orelhas, patas, telhados |
| `M` | `#cd3bda` magenta | fundo; detalhes internos (orelha por dentro, língua, facetas) e o sublinhado |
| `G` | `#5fc697` menta | fundo; corpo secundário, o estouro final |
| `W` | `#f6f3ec` branco quente | partes claras (dálmata, poodle) e brilhos |

Também há as paletas prontas `pastel`, `terra` e `mar` em `TR.PALETAS`, e você pode passar o seu próprio objeto. Para casar com a referência do usuário, rode `tools/referencia.py` e copie as cores que ele lista.

**Troque a paleta antes de desenhar**, porque os desenhos leem `TR.P` na hora em que são criados:

```js
TR.usarPaleta('pastel');
TR.usarPaleta({ L: '#ffd23f', ... });
```

Regras de cor:

- **Fundo:** cada cena tem um fundo de **uma** cor da paleta, e ele troca seco a cada objeto. A sequência do exemplo é preto → lima → violeta → menta → magenta → vermelho → lima → preto. Não repita a mesma cor em duas cenas seguidas.
- **Objeto:** usa 2 ou 3 cores da paleta, **nenhuma igual à do fundo**. Pares que funcionam bem:
  - lima com vermelho, violeta, magenta ou preto;
  - violeta com branco, preto ou lima;
  - menta com vermelho, violeta ou preto;
  - magenta com lima ou branco;
  - vermelho com menta, branco ou preto.
- **Detalhes:** preto vai em olhos, narizes e aberturas (porta, boca). Branco vai em brilhos e manchas claras. O objeto pode ter cor "errada", como pug verde-menta ou poodle lima. O estilo é gráfico, não realista: **a forma diz o que é, a cor só precisa contrastar.**

## Forma

- **`TR.blob(cx, cy, rx, ry, cor, {n, j, rot})`:** a forma redonda "cortada à mão".
  - `n` de 8 a 12 pontos (menos pontos dá forma mais tosca);
  - `j` é a irregularidade: .03 para quase lisa (cabeças grandes, bolas), .05 é o padrão, .09 a .1 para pompom, mancha ou nuvem.
- **`TR.poly(pontos, cor, {j})`:** arestas retas com os vértices tortos `j` px (2 a 4). Use para casas, pernas, telhados, triângulos e facetas.
- **`TR.star(...)`:** estrelas de pontas irregulares, para estouros, selos e brilhos.
- **`TR.line(d, cor, largura)`:** **só** para boca, ruga, costura, coleira, alça ou rabo fino. Use largura de 6 a 20 px com ponta redonda. Nunca use traço fino (menos de 5 px): a fervura come.
- **Círculos e retângulos perfeitos** (`<circle>`, `<rect>`) só aparecem escondidos, como a pálpebra que é um retângulo preto sobre um olho preto.
- **Tamanho mínimo:** nenhum detalhe com menos de ~12 px de raio em 1080 de largura. O deslocamento da fervura é de ±4,5 px, então coisa menor vira borrão.

## Borda que ferve

```js
TR.ferver(S.art);   // padrão: freq .011, forca 9, qps 12
```

- **`forca`:** é a amplitude em px. 6 é sutil e elegante; 9 é o padrão da referência; 12 a 14 dá jeito bem "feito à mão". Acima de 14 o texto fica ilegível.
- **`freq`:** é o tamanho da ondulação. .008 dá ondas largas, como papel; .016 deixa a borda mais nervosa.
- **`qps`:** 12 é animação "nos dois" a 24 qps, o clássico. 8 fica mais tosco e 24 vira vibração.

A fervura vale para **tudo** que está dentro de `#art`, inclusive o texto. Isso é intencional, porque o letreiro também parece recortado.

## Composição 9:16 (1080×1920)

| elemento | tamanho / lugar |
|---|---|
| objeto principal | 40–50% da largura (430–560 px), centro em y ≈ 860–960 (um pouco acima do meio) |
| rótulo | Anton 132 px, centralizado, topo em y ≈ 1330 (69%) |
| mascote | ~270 px de largura, centro em y ≈ 945 |
| wordmark | Anton 100–110 px, no máximo 85% da largura, y ≈ 890 |
| margem segura | 80 px nas laterais; nada importante abaixo de y 1650 (interface do app) |

- **Um objeto por vez**, centralizado. A única cena cheia é o campo de ícones. Ali o quadro fica **lotado**: ícones de ~180 px a cada ~200 px, quase encostando, em vários ângulos.
- **Fundo vazio:** é o fundo liso que deixa o objeto "saltar". Não ponha nada atrás.
- **Para 1:1 ou 16:9:** mude `VIDEO.w` e `VIDEO.h`, recentralize (`540, 960` vira `w/2, h/2`) e reduza o objeto para ~55% da **altura** no 16:9.

## Tipografia

- **Anton** em caixa alta é o padrão: condensada e pesada, parece letreiro recortado.
  - Cada letra tem rotação fixa de ±4,5° e deslocamento vertical de ±7 px (`TR.rotulo` sorteia uma vez).
  - A palavra entra digitada letra a letra.
- **Cor do texto:** preto sobre lima, menta e branco; branco sobre violeta, vermelho, magenta e preto.
- **Alternativas incluídas:**
  - `Bebas Neue`: mais fina, elegante;
  - `Rubik Mono One`: larga e geométrica, divertida;
  - `Dela Gothic One`: bem pesada;
  - `Permanent Marker`: pincel, para anotação;
  - `Unbounded`: redonda e moderna;
  - `Inter Tight`: neutra, só para créditos.
- **Quantidade de texto:** uma palavra ou um nome curto por cena. Frase só no wordmark final, e de até ~20 caracteres.

## O que evitar

- **Fora do estilo:** gradiente, sombra, contorno, brilho difuso, textura, grão, foto, 3D, desfoque. Tudo isso quebra o recorte.
- **Cor:** cor fora da paleta, ou objeto da mesma cor do fundo.
- **Movimento liso demais:** câmera passeando, fade-in e fade-out, ease suave em tudo. O estilo pede pulo elástico, chicote e corte seco (veja `movimento.md`).
- **Detalhe miúdo:** dedos, fios, cílios, texturas de pelo. Simplifique até virar 2 a 6 formas.
- **Texto longo** ou legenda corrida.
