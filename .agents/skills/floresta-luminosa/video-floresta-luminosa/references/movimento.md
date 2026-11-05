# Movimento: floresta luminosa

## Cadência

- **10 qps em degraus.** Medido na referência: o vídeo inteiro anda a 10 qps (cada pose fica 0,1 s). O render sai a 30 qps (cada pose repete 3×), mas todo cálculo usa o tempo quantizado `tq` que o palco entrega. Não misture movimento liso com degraus: fica "quebrado".
- **Câmera travada.** Nenhum empurrão, nenhum pan. O vídeo é um plano só.
- **Laço de ~2 s.** Na referência, a cada 20 quadros o ciclo recomeça (pisca → abaixa → lambe → anéis). Use eventos espaçados de 0,8–2 s.

## O laço ambiente (sempre ligado, por baixo de tudo)

| o quê | como | valores |
|---|---|---|
| cachoeira | riscos verticais descendo | `vel` 1,1 u/s |
| rio | riscos deslizando no sentido da correnteza | `vel` .35 u/s, eixo `fluxo` |
| estrelas | brilho novo a cada quadro de 10 qps; 30 % delas piscam forte | `FL.estrelas` |
| peixes | giro ±.14 rad (2,3 rad/s), rabo ±.5 rad (9 rad/s), deriva ±.05 u | `FL.nadar(p, tq)` |
| cauda do bicho | ondulação lenta por segmento | dentro de `pose({t})` |
| moita | balança ±.04 rad quando o bicho passa | `rotation.z` |

## Coreografia do exemplo (8 s)

| t (s) | evento | detalhe |
|---|---|---|
| 0,35 | olhos acendem na moita | bicho atrás da moita com `luz` .1; `brilhoOlho` 1 (bloom); som `brilho` |
| 1,0 / 2,15 | piscadas | 0,2 s (2 quadros) com `piscar` 1 |
| 1,3–4,35 | sai da mata e caminha até a beira | `P0 → P1` com `io` (ease in-out), `passo` = (t−1,3)·1,45 ciclos/s, `andar` sobe/desce em .3 s |
| 1,5–3,2 | sai da sombra | `luz` .1 → 1 (`suave`) e `brilhoOlho` 1 → 0 até 3,4 |
| 1,75–2,75 | título desenhado a lápis | progresso quantizado em décimos |
| 3,85–4,95 | vira para a água e agacha | `RUMO → RUMO_BEBE`, `agachar` 0 → 1, `pescoco` → −.62 |
| 5,15 / 5,95 / 6,75 | lambidas | cabeça desce −.12 rad por .45 s; anel quadrado nasce no focinho (`FL.anel`) |
| 5,2–6,1 | subtítulo desenhado | |
| 7,0–7,6 | ergue a cabeça e encara a câmera | `pescoco` +.55, `cabecaY` +.62, `brilhoOlho` .25 |
| 7,4 | piscada final | e segura olhando até o fim |

## Anéis quadrados (marca da referência)

Três anéis concêntricos por lambida, em distância de Chebyshev (quadrados no plano da água), defasados .22 s, crescendo .6 u/s, finos (.007–.011 u) e somem em 1,5 s. Até 4 fontes ao mesmo tempo (`FL.anel(k, x, z, t0, força)`).

## Caminhada (rig da onça)

- Passo lateral (traseira esq. 0, dianteira esq. .25, traseira dir. .5, dianteira dir. .75 do ciclo).
- Coxas ±.4 rad, canela dobra só na fase de subida (`max(0, cos)`), corpo sobe ±.025 e balança .015 rad.
- Velocidade de ~0,8 u/s com 1,45 ciclos/s não escorrega visivelmente com a escala 1,25.

## Ritmo e duração

6–8 s. Um evento novo a cada 1,5–2 s; o texto entra quando o bicho já está visível (não compete com os olhos no escuro). Termine num quadro "de pôster": bicho parado olhando, água correndo.
