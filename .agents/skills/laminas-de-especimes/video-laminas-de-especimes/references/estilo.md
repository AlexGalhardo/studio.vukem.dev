# Estilo — lâminas de espécimes

## Sumário
1. As 3 marcas
2. Paleta
3. Tipografia
4. Exemplares (materiais e recorte)
5. Composição 9:16
6. O que NÃO fazer

## 1. As 3 marcas

| marca | como se reconhece | onde mora no código |
|---|---|---|
| Espécime sozinho no creme liso | foto macro real, vista de cima, sem sombra, centrada pelo corpo, cabeça para cima | `tools/especime.py` (recorte, giro, centro do corpo) + `LA.colecao` |
| Folhear a 9 por segundo | corte seco a cada 1/9 s, nada se mexe entre cortes, laço | `LA.RITMO = 9`, `fps: 60`, `dur: n/9` |
| Desfile de cor | cada vizinho contrasta; blocos por forma | a `ORDEM` no `index.html` (ou `LA.alternar`) |

A referência (Klickpin, 4:3, 13,5 s) tem **121 trocas em 13,4 s**, holds de 6-6-8 quadros a 60 qps (média 6,67 = 1/9 s) e diferença **zero** dentro de cada hold. Os primeiros besouros voltam no fim: é um laço.

## 2. Paleta

| papel | cor | nota |
|---|---|---|
| fundo | `#e9ecd9` | medido na referência (232,236,216 no quadro decodificado; o render sai 233,237,217) |
| tinta (grupo, nome) | `#2a2c22` | nanquim esverdeado, combina com o creme |
| tinta apagada (ordem, nº, cabeçalho) | `#7c7f6d` | |
| créditos | `#8f927f` | 15 px, legível mas discreto |

As cores fortes vêm **só** dos exemplares. Nada de fundo colorido, moldura, faixa ou sombra.

Realce de cor dos exemplares (`LA.colecao`, opção `realce`): `saturate(1.12) contrast(1.04)` — a referência tem cor de catálogo "puxada". Desligue com `realce:false` para fotos já saturadas demais.

## 3. Tipografia

A referência não tem texto. Quando houver rótulos (pedido comum), eles imitam a **etiqueta de gaveta de museu**, pequenos e fora do exemplar:

| peça | fonte | tamanho | caixa / espaço |
|---|---|---|---|
| cabeçalho (`LA.cabecalho`) | Inter Tight 500 | 23 px | versal, +0,42 em, com fios de 70 px dos dois lados |
| grupo · ordem (`LA.etiqueta`) | Inter Tight 500 | 23 px | versal, +0,34 em; grupo em tinta, ordem apagada |
| nome científico | Libre Caslon Text itálico | 54 px (encolhe se passar de 960 px) | como no arquivo: *Gênero espécie* |
| número | Courier Prime | 25 px | `nº 017 / 064`, datilografado |

Tudo em pt-BR, exceto o nome científico e a ordem em latim. Nada de fato inventado: a etiqueta só leva grupo, ordem/família e nome.

## 4. Exemplares (materiais e recorte)

- **Fonte boa:** fotos de exemplar de museu em fundo liso (branco, cinza claro ou preto), foco empilhado, vista dorsal, de preferência um por foto (ou dois lado a lado: `lado`). No Commons: Udo Schmidt (CC BY-SA, besouros do mundo todo, fundo branco), Ben Sale (CC BY, besouros neotropicais em pares), Didier Descouens / MHNT (CC BY-SA, borboletas "… MHNT dos.jpg" e mariposas "MHNT CUT … dorsal" em fundo preto).
- **Recorte:** por distância de cor ao fundo (mediana da borda), suave entre `t0` e `t1` → preserva antena e tarso finos, que o Vision perde. Buracos do corpo (manchas claras) são preenchidos; buraco grande com cor de fundo (antena em laço) continua transparente. Halo do fundo antigo é removido (`C = (I − (1−α)·fundo)/α`).
- **Tamanho:** raiz da área do exemplar = `alvo` px (560 no exemplo), limitado à `caixa` [900, 1150]. Assim um besouro redondo e um serra-pau de antenas longas parecem do mesmo "peso".
- **Centro:** o centro de massa do corpo (abertura morfológica tira pernas e antenas), não o centro da caixa.

## 5. Composição 9:16

```
y 168   ── COLEÇÃO ENTOMOLÓGICA ──           cabeçalho
y 235   ┐
        │  exemplar: corpo centrado em (540, 860), faixa vertical [235, 1475]
y 1475  ┘
y 1530  BESOUROS · COLEOPTERA                 etiqueta
        Gênero espécie
        nº 017 / 064
y 1818  créditos (2 linhas, 15 px)
```

- Corpo vertical, cabeça para cima: no 4:3 da referência o corpo ia na horizontal (lado maior); no 9:16 o lado maior é a altura.
- Exemplares de asas abertas (borboletas, mariposas, libélulas) ficam naturalmente horizontais e ocupam ~75–85% da largura.
- Ocupação: besouro ~60–75% da largura com pernas, ~50–60% da altura.

## 6. O que NÃO fazer

- Sombra projetada, moldura, cartão, alfinete desenhado, textura de papel: o creme é liso.
- Fade, zoom, flutuação, "respiração" do exemplar ou transição entre exemplares.
- Fotos de bicho vivo na natureza (fundo de folha, luz de flash): quebra a marca 1.
- Um exemplar por mais de 1/9 s (exceto se o usuário pedir um "pouso" final; ver `receitas.md`).
