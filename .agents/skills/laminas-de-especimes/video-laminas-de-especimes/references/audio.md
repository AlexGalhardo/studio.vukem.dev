# Áudio — trilha `gabinete` e efeitos de coleção

## Sumário
1. Ideia
2. Trilha `gabinete`
3. Efeitos (`flip`, `gaveta`, `madeira`)
4. Passo a passo e conferência

## 1. Ideia

A referência tem só música: uma batida leve, com sinos/caixinha e grave cheio (≈86/172 bpm), sem efeitos. Aqui a música é sintetizada no **mesmo andamento do folhear**: a 135 bpm cada semicolcheia dura 1/9 s, então cada exemplar cai numa semicolcheia, e 16 exemplares = 1 compasso. Por cima, um estalo de cartão por troca faz o "folhear" soar.

Equilíbrio medido (Welch, mono) para não ficar só grave: 20–150 Hz ≈ −30 dB · 150–500 ≈ −30 · 500–2000 ≈ −29 · 2–6 k ≈ −42. A referência: −30 / −24 / −26 / −37.

## 2. Trilha `gabinete`

```js
VIDEO = { …, bpm: 135, music: { style: 'gabinete', key: 'F', gain: -1, laco: true } }
```

| camada | o que toca |
|---|---|
| piano elétrico | acorde I – vi – IV – V (um por compasso), no 1, no "e" do 2 e no 4; mais um pad triangular macio |
| baixo 808 | segue o bumbo (semicolcheias 0, 6 e 10), decai em ~0,3 s |
| caixinha de música | `glock` em colcheias, motivo de 4 compassos na escala maior |
| marimba | arpejo em semicolcheias, bem baixo (o "folhear" musical) |
| bateria | meio-tempo: bumbo 0/6/10, palma+caixa no 3, chimbal em colcheias, chimbal aberto no fim do compasso |

- `laco: true` (padrão): a duração vira um número inteiro de compassos e as caudas de reverb que passam do fim são somadas no começo — o mp4 em loop não tem emenda. Sem fade no fim.
- `laco: false`: compassos até cobrir a duração, sem dobra, com fade de 50 ms no fim.
- `key`: qualquer nota (`'F'`, `'G'`, `'Bb'`…). `gain` em dB relativo (−1 no exemplo).

As outras trilhas do motor (`ambient_major`, `launch_bright`…) também funcionam, mas não amarram o folhear ao tempo.

## 3. Efeitos

| cue | som | pico | quando |
|---|---|---|---|
| `flip` | estalo de cartão: ruído 1,8–7,5 kHz com ataque de 0,6 ms + segunda camada aos 16 ms + toque grave curto | −22 dBFS | toda troca; `LA.sons` põe 0 dB nos tempos e −4 dB nas outras semicolcheias |
| `gaveta` | atrito de gaveta (ruído 250–1600 Hz modulado) por `d` s que termina na batida de madeira | −12 dBFS | 0,3 s antes da troca de grupo (a batida cai no corte) |
| `madeira` | batida de madeira: modos de 182, 437 e 1130 Hz + ataque | −13 dBFS | no 1º exemplar (abre o vídeo e marca a emenda do laço) |

Todos estão em `audio/synth.py` (`fx_flip`, `fx_gaveta`, `fx_madeira`). Ajuste por cue com `gain` (dB) ou em `LA.sons(col, {ganhoFlip:-3})`.

## 4. Passo a passo e conferência

```
$P tools/render.py <nn> --at=0                       # grava videos/<nn>/cues.json (cues + VIDEO.music)
$P audio/synth.py <nn>      # audio/<nn>.wav, −14 LUFS, −1,5 dBTP
$P tools/render.py <nn>                              # mp4 com o áudio
ffmpeg -hide_banner -nostats -i out/<nn>.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):"
ffmpeg -i audio/<nn>.wav -lavfi "showspectrumpic=s=1600x500:fscale=log" espectro.png   # o grave não pode engolir tudo
```

No espectrograma: blocos de grave nos bumbos, faixas tonais no meio e **linhas verticais finas a 9/s** nos agudos (os `flip`). Se as linhas sumirem, suba `ganhoFlip`; se o grave virar um bloco contínuo, baixe o 808 em `st_gabinete`.
