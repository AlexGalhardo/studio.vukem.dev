# Áudio do estilo

A referência é muda; o som do estilo foi criado para a maquete "soar" física: terra, pedra, água, folhas e máquina, sobre uma trilha ambiente calma. Tudo é sintetizado em `audio/synth.py` (sem samples) e masterizado a −14 LUFS / −1,5 dBTP.

## Trilha

`VIDEO.music = { style: 'ambient', key: 'D', gain: -4 }`, `bpm: 84`. Seções:

```js
cue('m:intro', 0);      // só pads
cue('m:build', 1.7);    // entra arpejo vítreo + baixo (quando o relevo começa a mudar de verdade)
cue('m:main', 5.0);     // pulso suave (chegada do bondinho / do "presente")
cue('m:stop', VIDEO.dur - .25);
```

Para um tema mais leve/alegre, use `style: 'ambient_major'`.

## Efeitos do estilo (novos neste synth.py)

| cue | quando | parâmetros |
|---|---|---|
| `ronco` | relevo sobe ou desaba (cada passo da metamorfose) | `d` = duração do passo (1,8–2,2) |
| `cascalho` | erosão, desmoronamento | `d` 1,4–1,8 |
| `mar` | água subindo/entrando | `d` = duração da subida |
| `folhas` | mata brotando | `d` ~1,4 (fica baixo de propósito) |
| `bonde` | objeto mecânico viajando (bondinho, trem, barco a motor) | `d` = duração da viagem |

## Efeitos da casa usados no exemplo

- HUD: `ui_blip` na entrada de cada etiqueta, `tick` quando o anel estoura (+.42 s), `whoosh_out` (−9 dB) na saída.
- Título: `swoosh` em 0.
- Adereços: `pop` com `f` subindo (520, 660, 800) para estações em sequência; `thread` quando um cabo se desenha.
- Fecho: `hit_soft` + `paper` + `chime` (`m: 86`) no carimbo.

## Regras

- O ronco dura o passo inteiro: ele É o movimento. Os efeitos curtos marcam o HUD.
- Dois efeitos iguais a menos de 60 ms viram "flam": espalhe.
- Ruído largo (folhas, mar) fica baixo: confira o espectrograma (`ffmpeg -i out/v.mp4 -lavfi showspectrumpic=s=1400x300 esp.png`) e baixe se aparecer um bloco claro dominando.
- Ordem: `render --at=1` (grava cues.json) → `synth.py` → `render`.
