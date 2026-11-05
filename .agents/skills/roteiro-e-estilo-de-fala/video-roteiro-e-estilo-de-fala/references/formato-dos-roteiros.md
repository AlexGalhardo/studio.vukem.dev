# Formato dos dois roteiros

Contrato dos arquivos que os agentes roteiristas escrevem e dos três que o `juntar.py` grava.

## 1. O que cada agente entrega

Dois arquivos com o **mesmo prefixo** `<nn>-<slug>` em `roteiro/partes/`. O número manda na ordem do vídeo.

### `<nn>-<slug>.fala.md` — narração

```markdown
# A régua de prova

## Por que uma régua

A gente combinou uma régua antes de escrever qualquer linha, porque sem ela todo item parece ter o mesmo peso.

São 4 notas. A primeira é decisão documentada. A segunda é investigação em andamento.

## O que a régua muda na tela

Cada nota ganhou uma cor, e a cor aparece em toda ficha que entra no vídeo.
```

- `#` é o título da parte (o `Parte 03 —` da frente, se houver, é descartado).
- `##` (ou `###`) é uma **subseção**: é a unidade com que o resto do processo trabalha.
- Parágrafos são fala, e só fala. Nada de `[0-3s]`, `HOOK`, `CTA`, `B-ROLL:` ou nome de arquivo aqui.
- Linha começando com `>`, `|`, `-` ou `*` é ignorada: use para recado ao revisor, não para fala.

### `<nn>-<slug>.edicao.json` — o que entra na tela

Uma lista de blocos. Um bloco por entrada de tela, na ordem em que entram.

```json
[
 {"tela": "MOTION",
  "subsecao": "Por que uma régua",
  "fala": "São 4 notas",
  "midia": "As 4 notas acendendo uma a uma, cada uma na sua cor",
  "buscar": {"onde": "animação própria", "skill": "video-animacao-explicativa", "termo": null},
  "fatos": ["F031"],
  "status": "pendente",
  "notas": ""}
]
```

| campo | obrigatório | o que é |
|---|---|---|
| `subsecao` | sim | **igual** ao texto do `##` na narração (é a chave que liga os dois arquivos) |
| `fala` | sim | trecho **literal** da narração daquela subseção, copiado e colado — é por ele que a montagem acha o ponto |
| `tela` | sim | um código da legenda (abaixo) |
| `midia` | recomendado | o que aparece, em uma frase; `—` quando é só o apresentador |
| `buscar` | se a mídia vem de fora | `{"onde", "skill", "termo"}`: onde procurar, qual skill atende, que termo usar |
| `fatos` | quando há dado na tela | ids da `pesquisa/fatos.json` que sustentam o que aparece |
| `id` | não | o `juntar.py` numera (`03-01`, `03-02`…) se você não der |
| `status` | não | `pendente` (padrão), `aprovado`, `pronto` |
| `notas` | não | recado para quem edita |

## 2. Códigos de tela

| Código | O que é na tela |
|---|---|
| `CAM` | apresentador em tela cheia |
| `CAM+` | apresentador com cartões e rótulos entrando |
| `VERT` | apresentador na moldura, conteúdo ao lado |
| `MOTION` | animação em tela cheia |
| `INSERT` | mídia de terceiro ou peça pronta num cartão |
| `DOC` | documento, print ou manchete na tela |
| `CARTELA` | abertura de bloco em cor chapada |
| `GC` | gerador de caracteres sobre o que estiver na tela |
| `BROLL` | imagem de cobertura de banco livre |

Para trocar ou acrescentar, grave `roteiro/telas.json` com `{"CODIGO": "o que é na tela"}`: o `juntar.py` junta com
estes e usa a legenda inteira no `roteiro-edicao.md`. A **aparência** de cada código é da `video-direcao-de-arte`;
aqui só se diz qual é o tipo de tela.

## 3. O que o `juntar.py` grava

- **`roteiro/roteiro-fala.md`** — as partes em ordem, com `## NN · Título` e as subseções em `###`. Só fala.
- **`roteiro/roteiro-edicao.md`** — a legenda e, por subseção, uma tabela `id · Tela · Fala · Mídia · Onde buscar`.
- **`roteiro/edicao.json`**:

```json
{"versao": 1,
 "telas": {"CAM": "apresentador em tela cheia"},
 "partes": [{"prefixo": "03-regua-de-prova", "numero": 3, "titulo": "A régua de prova",
             "palavras": 820, "duracao_estimada_s": 255.3, "subsecoes": ["Por que uma régua"]}],
 "blocos": [{"id": "03-01", "parte": "03-regua-de-prova", "subsecao": "Por que uma régua",
             "tela": "MOTION", "fala": "São 4 notas", "midia": "As 4 notas acendendo",
             "buscar": {"onde": "animação própria", "skill": "video-animacao-explicativa"},
             "fatos": ["F031"], "skill": "video-animacao-explicativa",
             "status": "pendente", "notas": ""}]}
```

`duracao_estimada_s` só existe quando há `roteiro/estilo-de-fala.json` na mesma pasta (palavras ÷ ppm × 60).

## 4. Depois da gravação

O `fala` de cada bloco é o que amarra o roteiro à gravação: procure o trecho no `transcricao/palavras.json` e você
tem o segundo em que a tela entra. É assim que a `video-montagem` transforma `edicao.json` numa EDL, e é por isso
que o `fala` precisa ser literal, nunca um resumo.
