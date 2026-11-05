# Áudio

As referências têm narração + trilha eletrônica discreta + cliques de interface quando rótulos e pinos aparecem. Sem narração, a trilha e os efeitos contam a história. Tudo é sintetizado em `audio/synth.py` (numpy, sem samples) e masterizado a −14 LUFS / −1,5 dBTP.

## Trilha

`VIDEO.music = { style: 'ambient_major', key: 'D', gain: -4 }` com `bpm: 100`: pads claros, arpejo vítreo e baixo; bumbo macio só a partir de `m:drop`.

```js
cue('m:intro', 0);        // pads e arpejo: apresentação
cue('m:drop', T.c3);      // entra o pulso quando a máquina liga
cue('m:main', T.c4);      // conclusão
cue('m:stop', T.fim - .25);   // acorde final com reverb
```

Para um tema mais tenso (segurança, falha, acidente): `style: 'ambient'` (menor) ou `'thriller'`.

## Efeitos por evento (os do exemplo)

| evento | cue | nível |
|---|---|---|
| chip aparece / troca | `ui_blip` (+ `swoosh` .06 s antes do corte) | padrão, −3 nas trocas |
| caixa de legenda aparece | `focus_tick` | muito baixo |
| rótulo estala | `tick` + `pop {f: 800–1100, gain: -8}` | baixo |
| corte varrendo a maquete | `whoosh_slow` + `cut` no fim | −2 / −4 |
| água correndo num cano | `agua {d}` | −16 (pico) |
| máquina ligando | `turbina {d}` (serra filtrada que sobe + batida das pás) | −15 |
| explosão de peças | `swoosh` + `click` quando assenta | −3 |
| energia gerada | `zap` + `sparkle` | −4 / −2 |
| rede elétrica / pulsos | `rede {d}` (zumbido de 60 Hz com estalos) + `zap` baixo | −22 |
| luzes acendendo | `lamp_click` em sequência, alternando pan ±.3 e caindo .5 dB | −6 … −8,5 |
| carimbo | `hit_soft` + `paper` + `chime {m: 86}` | −2 / padrão / −4 |
| corte seco entre capítulos | `whoosh_in` .05 s antes | padrão |

Princípios:
- Todo corte, rótulo, chip e mudança de estado tem um som no quadro.
- Dois iguais a menos de 60 ms viram "flam": espalhe.
- Sons contínuos (`agua`, `turbina`, `rede`) duram o capítulo (`d` = duração) e abrem/fecham sozinhos.
- A trilha fica embaixo; `synth.py` normaliza o total.

## Ordem

```bash
$N render.mjs <nn> --at=1                        # grava videos/<nn-nome>/cues.json
<PYTHON> audio/synth.py <nn>       # audio/<nn-nome>.wav
$N render.mjs <nn>                               # mp4 com áudio
```

## Som novo

Escreva `def fx_nome(d=…)` em `synth.py` (mono, 48 kHz, devolve um array numpy) e registre em `SFX = {'nome': (lambda p: fx_nome(p.get('d', 1)), pico_dBFS, abre_no_estereo)}`. Modelos: `fx_agua` (ruído rosa em banda com pulsação), `fx_turbina` (frequência que sobe com `cumsum`), `fx_rede` (soma de harmônicos de 60 Hz).
