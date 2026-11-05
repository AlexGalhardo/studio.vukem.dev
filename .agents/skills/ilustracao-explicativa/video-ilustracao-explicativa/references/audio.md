# Áudio — ilustração explicativa

Sem narração: a trilha é leve e os **efeitos contam a história**. Todo som é sintetizado (`audio/synth.py`), masterizado a −14 LUFS / −1,5 dBTP.

## Trilha

```js
VIDEO = { …, bpm: 112, music: { style: 'explicador', key: 'F', gain: -8 } }
cue('m:main', 0); cue('m:break', T.c3); cue('m:main', T.titulo); cue('m:stop', T.fim - .25);
```

- `explicador` (feita para este estilo): marimba em acordes no contratempo, baixo pizzicato nos tempos 1 e 3, glockenspiel com um motivo a cada 2 compassos, shaker em colcheias, bumbo macio e palma leve. Tom maior, clima de explainer de ONG/ciência.
- Seções: `m:intro` (só marimba + shaker), `m:main` (tudo), `m:break` (sem baixo e bumbo — use no corte para as nuvens), `m:outro`, `m:stop` (acorde final de marimba + glock com reverb).
- `gain: -8` deixa a trilha embaixo. Se os efeitos sumirem, desça para −10.

## Efeitos por evento

| evento | cue | ganho típico |
|---|---|---|
| foto desliza | `IL.somFoto(t)` = `whoosh_in` + `paper` | −9 / −8 |
| rachaduras crescem | `scratch` (2–4 ao longo da cena, pan alternado) | −18 |
| corte seco de fundo | `cut` | −5 a −6 |
| "!" ou objeto que salta | `pop` com `f` 500–900 | −9 a −12 |
| bolhas de vapor/água | `bubble` em sequência irregular (.14–.18 s) | −13 a −14 |
| fluxo/seta se desenha | `marker` + `swoosh` | −10 / −14 |
| lupa pisca | `ui_blip` | −12 |
| câmera sobe/desce | `whoosh_slow` | −8 |
| braços/armários entram | `swoosh` com pan para o lado de onde vêm | −10 a −11 |
| regador derrama, cano enche, torneira | `agua` com `d` = duração | −9 a −16 |
| fogo apaga | `sizzle` | −12 |
| torneira abre | `squeak` com `f: 1500` | −20 |
| varrida das nuvens | `whoosh_in` + 4–5 `pop` graves descendo (420 → 260 Hz) | −6 / −9 |
| título | `impact` | −9 |
| chuva fina no fim | `chuva` com `d` até o fim | −12 |

Efeitos novos deste estilo em `synth.py`: `agua` (chiado filtrado com rajadas e bolhinhas que sobem de tom), `chuva` (ruído rosa agudo + pinguinhos), `sizzle` (chiado de fogo apagando).

## Princípios

- Todo corte, entrada e impacto tem som, no quadro do movimento.
- Dois sons iguais a menos de 60 ms viram "flam": espalhe.
- Sequência de pops/bolhas: tons e intervalos diferentes, nunca metrônomo.
- Ordem: preview (grava `cues.json`) → `synth.py` → render.
