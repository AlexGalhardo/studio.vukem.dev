# Som

Todo o áudio é sintetizado por `audio/synth.py` (numpy + scipy, sem samples) a partir das marcações `cue()` feitas na página. O estilo **não tem narração**: quem conta a história é a trilha com os ruídos de papelaria e máquina de escrever, cada um no quadro exato do movimento.

```bash
node render.mjs <nome> --preview=6               # (re)escreve videos/<nome>/cues.json
audio/.venv/bin/python audio/synth.py <nome>     # → audio/<nome>.wav (−14 LUFS / −1,5 dBTP)
node render.mjs <nome>                           # → out/<nome>.mp4 com o áudio junto
```

Sempre que mexer em tempos, refaça os três passos nessa ordem.

## Trilha

```js
VIDEO = { w: 1080, h: 1920, fps: 30, dur: 7.9, bpm: 100, music: { style: 'launch', key: 'A', gain: -3 } }
cue('m:intro', 0); cue('m:build', 1.15); cue('m:drop', 2.48); cue('m:stop', 7.62);
```

- `launch` (menor, pulso eletrônico limpo) é o padrão do estilo; `launch_bright` para temas leves.
- A batida entra com `m:drop` na **primeira cena de mesa** (depois do título e do padrão). `m:stop` uns 0,3 s antes do fim encerra com um acorde.
- `gain: -3` deixa a trilha um pouco abaixo dos efeitos.

## Efeitos usados no exemplo

Formato: `cue(tipo, t, { gain, f, d })`.

| tipo | onde |
|---|---|
| `key` | teclas do título, uma a cada 2 letras (`titulo.sons()`), e da palavra da lousa |
| `type` | etiqueta datilografada, frase à mão |
| `whoosh_in` / `whoosh_out` / `whoosh_slow` | zoom do título, entrada do caleidoscópio / saída dos adesivos / entrada da mesa |
| `swoosh` | início de cada chicote |
| `hit_soft` | corte do título para a cena 2; chegada do objeto explodido |
| `pop` | recortes do padrão (6 pops, `f` subindo de 300 a 600), ícone em círculo |
| `paper` | cada `slap` (foto, fita, etiqueta) |
| `marker` | cada laço, seta e círculo |
| `scratch` | cada traço do X de marca-texto |
| `tom` + `click` | peça caindo na mão (`tom` com `f:140`) |
| `bubble` | chuva de adesivos (`M.somAdesivos`) |
| `riser` | 0,1 s antes da explosão do objeto |
| `glitch` | caleidoscópio |
| `shutter` | foto virando cartão |
| `ui_blip` | legenda da foto aparecendo |
| `impact` | fita final batida (bem baixo, `gain:-10`) |

Outros disponíveis: `boom`, `sub_drop`, `ding`, `chime`, `sparkle`, `coin`, `snap`, `heart`, `zap`, `tape_stop`, `reverse`, `carriage` (campainha de máquina de escrever, boa para fechar um título), `thread`, `lamp_click`, `bark`, `boing`, `squeak`.

## Princípios

- **Um som por gesto.** Se a peça bate, `paper`; se o marcador risca, `marker`. Não há som "de fundo" além da trilha.
- **Intervalo mínimo** de ~60 ms entre dois efeitos iguais (abaixo disso vira um "flam").
- Efeitos repetidos (teclas, pops, bolhas) ficam 6–12 dB abaixo do padrão.
