# Som: trilha e efeitos

Todo o áudio é sintetizado (numpy e scipy, sem samples) por `audio/synth.py`, a partir das marcações `cue()` feitas na página. O render grava as marcações em `videos/<nome>/cues.json`, junto com a duração, o bpm e o objeto `music`.

```bash
node render.mjs <nome> --preview=6               # (re)escreve cues.json
audio/.venv/bin/python audio/synth.py <nome>     # → audio/<nome>.wav, masterizado em −14 LUFS / −1,5 dBTP
node render.mjs <nome>                           # → out/<nome>.mp4 com o áudio junto
```

Sempre que mexer em tempos na página, refaça os três passos nessa ordem.

## Trilha

```js
VIDEO = { w: 1080, h: 1920, fps: 60, dur: 5, bpm: 112, music: { style: 'launch_bright', key: 'D', gain: -4 } }
```

- **Estilo:** `launch_bright`, um pop eletrônico leve em tom maior. Combina com o papel claro e as cores pastel.
- **Seções:** `cue('m:intro', 0); cue('m:main', .05)` faz a trilha já começar cheia (vídeos de 5 s não têm tempo para introdução). `cue('m:stop', dur - .3)` encerra com um acorde.
- **Volume:** `gain: -4`. A trilha fica bem atrás: quem conta a história são os cliques, as bolhas e os pops.
- **Alternativas:** `ambient_major` deixa mais calmo e fofo; `launch` deixa mais sério e "tech".

## Efeitos do estilo

Formato: `cue(tipo, t, { gain, pan, f })`.

| momento | cues (no exemplo) |
|---|---|
| foco do objeto (0 s) | `whoosh_slow` −8 |
| selo entrando | `pop` f 520 |
| objeto abrindo | `paper` −4 |
| mão subindo | `whoosh_in` −6 |
| **toque** (`RI.somToque(tp, i)`) | `pop` agudo 0,08 s antes (f 760 + 120·i, −8), `click` +2 no toque, `bubble` −2 (+0,04 s), `sparkle` −10 (+0,06 s) |
| mão descendo | `whoosh_out` −6 |
| papéis caindo | `paper` ×2 e `pop` f 640 |
| objeto saindo | `swoosh` −4 |
| pilhas (`pilhas.sons()`) | um `pop` por objeto ao pousar (f sobe com a altura) e 6 `tick` na contagem |
| marca | `chime` −6 + `pop` f 900 |
| frase final | `ui_blip` −6 |

Outros disponíveis: `whoosh_slow`, `riser`, `impact`, `hit_soft`, `boom`, `sub_drop`, `ding`, `coin`, `zap`, `snap`, `type`, `marker`, `scratch`, `shutter`, `glitch`, `squeak`, `boing`, `cut`, `reverse`, `tape_stop`.

Princípios:

- **Sincronia:** use o mesmo `t` da animação no `cue()`. O clique cai **no quadro** em que a mão afunda.
- **Antecipação:** o pop agudo antes do toque acompanha o "levantar" da mão e prepara o ouvido.
- **Intervalo mínimo:** nunca dois efeitos iguais a menos de 60 ms um do outro.
- **Hierarquia:** clique e chime são os mais altos; bolha e pop, médios; brilho e tick, baixos.

## Criar um efeito novo

Escreva uma função `fx_nome(...)` em `audio/synth.py` que devolva um array mono a 48 kHz e registre no dicionário `SFX`:

```python
def fx_spray(d=.35):  # spray de tinta: ruído agudo filtrado com ataque rápido
    t = tt(d); return bp(noise(d), 3000, 11000) * np.clip(t / .01, 0, 1) * np.exp(-t / .12)
SFX['spray'] = (lambda p: fx_spray(p.get('d', .35)), -16, True)   # (função, pico alvo em dBFS, abre no estéreo?)
```

As ferramentas disponíveis no topo do arquivo são `osc`, `noise`, `lp`, `hp`, `bp`, `peq`, `sat`, `reverb`, `env` e `tt`.
