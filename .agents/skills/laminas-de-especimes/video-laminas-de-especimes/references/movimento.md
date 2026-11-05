# Movimento — ritmo e tempos

## Sumário
1. O que foi medido na referência
2. Conta do ritmo (exemplares × compassos × duração)
3. Roteiro-tipo do exemplo
4. Ordem dos exemplares
5. Variações seguras

## 1. O que foi medido na referência

`analisar.py ler` achou só 5 "planos" (o fundo nunca muda). A medida certa é a diferença quadro a quadro com limiar baixo:

| medida | valor |
|---|---|
| trocas | 121 em 13,4 s → **9 por segundo** |
| hold (60 qps) | 6 ×45, 8 ×25, 7 ×22, 4 ×12, 9 ×10 — padrão 6-6-8 = 20 quadros a cada 3 exemplares |
| movimento dentro do hold | nenhum (diferença média 0,0) |
| transição | corte seco |
| fim | os primeiros exemplares voltam: laço |

Para medir outra referência parecida:

```bash
ffmpeg -i ref.mp4 -vf "scale=180:135,format=gray" -f rawvideo - > gray.raw
# diferença média entre quadros > ~2 (0–255) = troca; conte os quadros entre trocas
```

## 2. Conta do ritmo

| ritmo | bpm em que 1 exemplar = 1 semicolcheia | 1 compasso (4/4) |
|---|---|---|
| **9/s** (padrão, a referência) | **135** | 16 exemplares = 1,78 s |
| 8/s | 120 | 16 exemplares = 2,0 s |
| 10/s | 150 | 16 exemplares = 1,6 s |

| exemplares | compassos a 135 bpm | duração |
|---|---|---|
| 48 | 3 | 5,33 s |
| 64 | 4 | **7,11 s** (exemplo) |
| 72 | 4,5 | 8,0 s (laço da música não fecha — evite) |

Regras: `VIDEO.dur = n / LA.RITMO`; `VIDEO.bpm = LA.RITMO * 15`; n múltiplo de 16 para a trilha `gabinete` emendar no laço. A 60 qps a cadência sai 7-7-6 quadros (o motor arredonda `floor(t·9)`).

## 3. Roteiro-tipo do exemplo (64 exemplares, 7,11 s)

| t (s) | exemplares | gaveta / etiqueta | som |
|---|---|---|---|
| 0,00 | nº 001 *Eumolpus ignitus* | BESOUROS · COLEOPTERA | `madeira` (gaveta encosta) + 1º tempo da trilha |
| 0,00–1,11 | 001–010 redondos (crisomelídeos, besouros-tartaruga) | | `flip` a cada troca, acento a cada 4 |
| 1,11–2,44 | 011–022 escaravelhos e rola-bostas | | |
| 2,44–5,33 | 023–048 alongados (tec-tecs, buprestídeos, serra-paus) | | |
| 5,33 | nº 049 *Morpho menelaus* | BORBOLETAS E MARIPOSAS · LEPIDOPTERA | `gaveta` (desliza 0,3 s antes e bate no corte) |
| 5,33–6,44 | 049–058 borboletas | | |
| 6,44–7,11 | 059–064 mariposas → emenda no nº 001 | | |

O grupo troca **no compasso** (5,33 s = início do 4º compasso): a gaveta cai no "1".

## 4. Ordem dos exemplares

- Blocos por forma (como a referência: joaninhas/tartarugas → escaravelhos → alongados), dentro do bloco **alternando** claro/escuro e quente/frio.
- Nunca 3 escuros seguidos. Se a coleção tiver muitos escuros, espalhe-os ou troque.
- O 1º quadro é a capa do reels: comece com o exemplar mais impressionante (iridescente, metálico).
- O último exemplar deve contrastar com o 1º (o laço também é uma troca).
- `LA.alternar(ids, cores, primeiro)` faz uma ordem gulosa de contraste máximo se você tiver as cores Lab de cada id (o `especime.py` não as grava; a ordem do exemplo foi feita à mão olhando a folha).

## 5. Variações seguras

- **Mais devagar** (público que precisa ler o nome): 6/s a 90 bpm (`ritmo: 6`, `bpm: 90`), 48 exemplares = 8 s.
- **Pouso final** (vídeo que não é laço, termina num exemplar com título): use `laco:false` em `LA.colecao`, deixe o último exemplar até o fim e anime só o texto; a trilha `gabinete` aceita `laco:false` no `music` (aí o fim leva o fade de 50 ms).
- **Várias gavetas curtas**: cada grupo com 16 exemplares (1 compasso) — a etiqueta troca a cada 1,78 s.
