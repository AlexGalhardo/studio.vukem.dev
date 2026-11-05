# Áudio — pintura em camadas

A referência é muda. O som do estilo conta a mesma passagem que a imagem: **sala de museu (silêncio, passos) → atravessar a moldura (sopro) → dentro da cena (vento, a ação da obra) → chegada na figura principal (rufo, tímpano, acorde maior)**.

## Trilha `museu` (`VIDEO.music = {style:'museu', key:'D', gain:-3}`)

| seção | cue | o que toca |
|---|---|---|
| `intro` | `m:intro` 0 | cordas sustentadas em menor com 9ª, baixinhas (sala) |
| `build` | `m:build` (`entra + .3`) | crescendo das cordas + ostinato nos graves em ritmo de galope (curto-curto-longo, ciclo .42 s) |
| `drop` | `m:drop` (`para`) | chegada: acorde MAIOR (cordas + metais + baixo), cauda longa |
| `stop` | `m:stop` (`fim − .2`) | fim |

Para obras sem cavalaria, o ostinato ainda funciona como pulso; para algo calmo (paisagem, retrato), troque por `ambient` / `ambient_major` e tire o `galope` (`PC.som(T, {cena: null})`).

## Efeitos do estilo (em `audio/synth.py`)

| cue | som | nível (pico) |
|---|---|---|
| `sala` (`d`) | rumor rosa grave de sala grande, respira | −30 dBFS |
| `passo` | passo em piso de madeira: baque + salto + cauda do salão | −21 |
| `passagem` (`d`) | sopro de ar simétrico + pressão grave (atravessar a moldura) | −14 |
| `vento` (`d`) | vento de campo aberto em banda, rajadas lentas | −25 |
| `galope` (`d`, `n`) | cavalaria chegando: 4 cavalos, compasso de 4 batidas, terra; cresce | −15 |
| `rufo` (`d`, `f`) | rufo de tímpano em crescendo | −12 |
| `timpano` (`f`) | golpe de tímpano + taiko com sala | −6 |

## Cues do exemplo (`PC.som({entra: 1.9, para: 6.4, fim: 7.5})`)

```
0      m:intro · sala (d = entra + 1)
.10 .63 1.16  passo (pan ±.15, cada um 1,5 dB mais baixo)
1.7    passagem (d 1.7)            ← a moldura começa a voar em 1.9
2.15   vento (d até o fim)
2.2    m:build
2.45   galope (até o 'para')
5.45   rufo (.95 s)
6.4    m:drop · timpano            ← a câmera para
7.3    m:stop
```

Fluxo: `$N render.mjs <nn> --at=1` (grava `cues.json`) → `audio/.venv/bin/python audio/synth.py <nn>` → `$N render.mjs <nn>`. O master sai a −14 LUFS / −1,5 dBTP.

## Princípios

- O museu é quase silêncio: só ar e passos. O contraste com a cena é o que dá a sensação de "entrar".
- O sopro da `passagem` começa ~.2 s ANTES da moldura voar e termina com a parede já sumindo.
- O som da cena é o que a obra mostra (cavalos → galope; mar → ondas: `fx_mar` não existe, crie como `fx_vento` com banda mais grave e ciclo de 6 s).
- A chegada cai no quadro em que a câmera para (`T.para`), não no título.
- Som novo: `def fx_nome(...)` (numpy, mono, 48 kHz) e registre em `SFX = {'nome': (lambda p: fx_nome(), pico_dBFS, abre_no_estereo)}`.
