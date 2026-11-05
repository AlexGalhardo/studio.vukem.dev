# Áudio: floresta luminosa

A referência é muda. O som do estilo é **contemplativo e noturno**: a mata e a água fazem a cama, uma caixinha de música esparsa dá o ar mágico, e os efeitos são pequenos e próximos (pata, lambida, brilho). Nada de whoosh nem impacto: o vídeo não tem cortes.

## Trilha `noturno`

```js
VIDEO = { …, bpm: 72, music: { style: 'noturno', key: 'D', gain: -3 } }
cue('m:intro', 0); cue('m:main', 1.3); cue('m:stop', 7.8);
```

- **Água correndo:** ruído rosa em banda (220–1800 Hz), estéreo largo, ondulando devagar. Baixa (ganho .11): se subir, vira chiado e engole os efeitos.
- **Grilos:** duas vozes (4,7 e 5,3 kHz), trincas de pulsos a cada ~1 s, laterais.
- **Sapos:** 3 coaxadas esparsas com reverb.
- **Pad quente:** acorde dórico, ataque lento, filtrado em 1,3 kHz.
- **Caixinha de música:** glock + marimba em notas soltas da pentatônica, a partir de `m:main`, alternando lados. Em `m:stop`, acorde final longo.

## Efeitos do estilo

| cue | quando | pico (dBFS) | parâmetros |
|---|---|---|---|
| `brilho` | olhos acendem / olhar final | −16 | `gain` |
| `passo` | cada passo da caminhada (~3/s), alternando ganho | −15 | `gain`, `pan` |
| `folhas` | o bicho passa pela moita | −22 | `d` (s) |
| `lapis` | texto sendo desenhado | −19 | `d` = duração do desenho |
| `lambida` | 20 ms antes do focinho tocar a água | −11 | — |

Também servem do motor: `bubble`, `bird`, `chime`, `sparkle` (com ganho baixo).

## Regras

- O som cai no quadro do movimento (o tempo é quantizado a 10 qps: use os mesmos instantes do `T`).
- Passos: espalhe por igual na janela da caminhada e alterne −4/−6 dB de ganho; nunca dois a menos de 60 ms.
- As lambidas são o pico do vídeo (~8 dB acima da cama). Se não aparecerem, baixe a água, não suba a lambida.
- Master: loudnorm em duas passadas para −14 LUFS / −1,5 dBTP (automático no `synth.py`).

## Ordem

```bash
$N render.mjs <nn> --at=1                 # grava videos/<nn-nome>/cues.json
<PYTHON> audio/synth.py <nn>                 # audio/<nn-nome>.wav
$N render.mjs <nn>                         # mp4 com áudio
```
