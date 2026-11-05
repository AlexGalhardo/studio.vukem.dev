# Áudio: trilha e efeitos

O som do estilo é **sala de arquivo**: zumbido de reator, relógio seco, e cada peça que entra faz o barulho do objeto (tecla, carimbo, fita, caneta, alfinete). Tudo é sintetizado por `audio/synth.py` (sem samples) a partir dos `cue()` que a biblioteca e a página marcam.

## Trilha

```js
VIDEO = { …, bpm: 90, music: { style: 'dossie', key: 'D', gain: 0 } }
cue('m:ficha', 0);                 // qualquer nome serve para a seção calma
cue('m:painel', T.corte);          // relógio dobra de velocidade + cluster agudo inquieto
cue('m:fim', T.tit);               // nota grave de piano + impacto surdo na entrada do título
cue('m:stop', VIDEO.dur - .4);     // corta o drone; fica só a cauda
```

- `dossie`: zumbido de 60 Hz quase subliminar, drone grave que respira (presente desde o primeiro quadro), tique de relógio em cada tempo e uma nota grave de piano na entrada de cada seção. Sem bateria, sem melodia.
- Seções chamadas `painel`, `tension` ou `board` dobram o relógio e somam um cluster agudo de segunda menor. `fim` soma um impacto grave filtrado.
- `bpm` é a velocidade do relógio: 80–96. `key` muda a altura do drone (`D`, `C`, `E`).
- Alternativa mais dramática: `style: 'thriller'` (batimento cardíaco que acelera e pizzicato). `ambient` também existe; os estilos com bateria (`launch`) não combinam.

## Efeitos (onde caem)

| evento | efeito | ganho | quem marca |
|---|---|---|---|
| caractere do código grande | `key` (tecla pesada) | −1 dB | `DS.codigo` |
| datilografia da ficha | `tecla` (7 variações de martelo) | −4 a −6 dB | `DS.ficha`, uma a cada ~66 ms |
| tarja de marcador | `marker` | −6 dB (−10 nas embutidas) | `DS.tarja`, `DS.texto`, `DS.cartao` |
| tarja de fita | `tape` (rasgo + tapa) | 0 dB | `DS.tarja({tipo: 'fita'})`, `F.olhos` |
| foto ou cartão pousando | `paper` | +1 / −1 dB | `DS.foto`, `DS.cartao` |
| digital | `ink` (baque macio) | 0 dB | `DS.digital` |
| carimbo | `stamp` (madeira na mesa) | 0 dB | `DS.carimbo` |
| caneta | `pen` (arranhado) | −5 dB, a cada 0,2 s do traço | garrancho, círculo, seta, assinatura |
| alfinete | `pin` | −2 dB | `DS.alfinete`, `DS.cartao` |
| etiqueta | `click` | 0 dB | `DS.etiqueta` |
| fio | `thread` (corda esticando) | −6 dB | `DS.fio` |
| linha do título | `cut` (baque seco) | −4 dB | `DS.titulo` |
| scanner | `scanner` (motor + chiado, com a duração da passada) | −3 dB | `DS.scanner` |
| troca de página | `paper` + `shutter` | +3 / −3 dB | `DS.paginas` |

- Toda peça aceita `som: false`; as que têm um efeito só aceitam `gain`.
- Efeitos iguais a menos de 55 ms viram um estalo só: `DS.som(tipo, t, opções)` empurra o segundo alguns quadros. Use-o no lugar de `cue` para qualquer efeito repetido que você acrescentar.
- Vários fios ao mesmo tempo: deixe o som só no primeiro (`som: false` nos outros), como nos três fios de acento do exemplo.
- Outros efeitos úteis já no sintetizador: `carriage` (alavanca e campainha da máquina, no fim de uma ficha), `hit_soft`, `lamp_click`, `whoosh_slow`.

## Ordem dos comandos

```bash
$N render.mjs <nn> --at=1                  # grava videos/<nn-nome>/cues.json
$P audio/synth.py <nn>             # audio/<nn-nome>.wav, −14 LUFS / −1,5 dBTP
$N render.mjs <nn>                         # mp4 com o áudio
```

Mudou tempo ou peça na página: refaça os três passos (o `cues.json` é regravado a cada render).

Conferir: `ffmpeg -i out/<nn-nome>.mp4 -af ebur128=peak=true -f null -` → I ≈ −14 LUFS; o começo não pode ficar mudo (no exemplo, o primeiro segundo fica ~2 dB abaixo do resto) e as seções ficam a menos de 3 dB uma da outra.
