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
VIDEO = { w: 1080, h: 1920, fps: 60, dur: 15, bpm: 124, music: { style: 'launch_bright', key: 'F', gain: -1 } }
```

- **Estilo:** `launch_bright` é o padrão deste estilo: pop eletrônico em tom maior, com bumbo, palmas e arpejo, que combina com cores saturadas e cortes secos.
  - `launch` é a versão menor, mais séria.
  - `ambient_major` funciona para algo calmo e fofo.
- **Seções:** são marcadas por cues `m:*`. O exemplo usa:
  - `m:intro` em 0 (só pad e arpejo);
  - `m:build` quando o campo abre (caixa crescendo);
  - `m:drop` no corte para o primeiro objeto (entra o bumbo cheio);
  - `m:outro` no wordmark;
  - `m:stop` ~0,05 s antes do fim, que encerra com um acorde.
- **Volume:** a trilha é normalizada e fica **atrás** dos efeitos. Neste estilo os efeitos são metade da graça.

## Efeitos

Formato: `cue(tipo, t, { gain, pan, f, n, d })`.

| tipo | onde (no exemplo) | parâmetros |
|---|---|---|
| `pop` | cada coisa que brota (ícone, pinta, objeto entrando) | `f`: tom (380–1300). Suba o tom numa sequência. |
| `squeak` | brinquedo de apertar: pompons, rebolado, língua | `f`: 1100–1600 |
| `boing` | mola: pulinho, inclinação de cabeça, objeto pulando no lugar | |
| `bark` | latido estilizado | `f`: 560 é cachorro médio, 760 é pequeno; `n: 2` dá "au-au" |
| `type` | cada letra do rótulo (`TR.somDigitar(t0, n, passo)`) | |
| `swoosh` | cada chicote de saída, em `tCorte - .17` | |
| `whoosh_in` / `whoosh_out` | entrada correndo, mergulho | |
| `whoosh_slow` | início do zoom-out do campo | |
| `reverse` | o "sugar" antes do mergulho | `d`: duração |
| `riser` | antes de um estouro | `d` |
| `boom` | estouro de estrelas e estouro final | |
| `sparkle` | confete | |
| `tick` / `click` | passos curtos, degraus do olhar, piscada | |
| `marker` | sublinhado sendo desenhado | |
| `cut` | corte seco importante (entrada do primeiro objeto, fim) | |

Outros disponíveis: `whoosh_slow`, `impact`, `hit_soft`, `sub_drop`, `ui_blip`, `chime`, `ding`, `coin`, `bubble`, `zap`, `snap`, `tom`, `heart`, `paper`, `scratch`, `shutter`, `glitch`, `tape_stop`, `bird`.

Princípios:

- **Sincronia:** o som cai **no quadro** do movimento. O jeito mais seguro é fazer o `cue()` com o mesmo `t` da animação.
- **Intervalo mínimo:** nunca dois efeitos iguais a menos de 60 ms um do outro. No campo de ícones, sonorize 1 a cada ~6 ícones, não todos.
- **Hierarquia:** estouro e corte são altos; pop, squeak e type são médios; tick e click são baixos (`gain` −2 a −9).

## Criar um efeito novo

Escreva uma função `fx_nome(...)` em `audio/synth.py` que devolva um array mono a 48 kHz e registre no dicionário `SFX`:

```python
def fx_miado(f0=700):
    d = .45; t = tt(d); f = f0 * (1 + .5 * np.sin(np.pi * t / d))   # sobe e desce
    ph = 2 * np.pi * np.cumsum(f) / SR; x = sum(np.sin(h * ph) / h for h in range(1, 8))
    return peq(bp(x, 400, 5000), 1800, 6, 1.2) * np.sin(np.pi * t / d) ** .7
SFX['miado'] = (lambda p: fx_miado(p.get('f', 700)), -12, False)   # (função, pico alvo em dBFS, abre no estéreo?)
```

As ferramentas disponíveis no topo do arquivo são `osc`, `noise`, `lp`, `hp`, `bp`, `peq`, `sat`, `reverb`, `env` e `tt`. Os modelos `fx_bark`, `fx_boing` e `fx_squeak` mostram as receitas: pulso harmônico com formantes, senoide com vibrato que morre e assobio que sobe e desce.
