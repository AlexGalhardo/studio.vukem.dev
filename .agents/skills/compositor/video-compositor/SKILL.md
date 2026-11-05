---
name: video-compositor
description: >
  Faz a música do vídeo e a mixagem final. A trilha é sintetizada do zero em numpy — contrabaixo,
  bateria e teclado Rhodes, em cinco climas e no bpm que você pedir — e sai em duas versões: a cheia e a
  "cama", aberta para a voz caber na frente. A mixagem põe a voz na frente (corte de graves, presença,
  de-esser, limiter), abaixa a música por ducking de sidechain exatamente quando ele fala, soma os
  efeitos sonoros e entrega −14 LUFS / −1 dBTP (ou −16 para peça curta), com stems para o editor. Use
  quando o usuário pedir trilha, música de fundo, "faz a mixagem", "deixa a voz mais clara", "a música
  está alta demais", "não escuto a voz", loudness, LUFS, normalizar o áudio para o YouTube, ou o
  mix_final.wav que entra no render. Irmã de video-efeitos-sonoros, que gera o som/efeitos.wav recebido
  aqui: nível e densidade dos efeitos são lá, não aqui.
---

# video-compositor

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

No fim da edição, quando a fala já está decupada e os efeitos prontos: é aqui que o vídeo ganha música e
sai no volume certo para a plataforma. Também serve sozinho, só para mixar (sem trilha) ou só para fazer
a música (sem mixar).

## 1. A trilha

```bash
python3 scripts/trilha.py --clima neutro --bpm 100 --dur 180 --saida som/
python3 scripts/trilha.py --climas          # lista os climas, com o bpm sugerido e a cara de cada um
```

Três instrumentos sintetizados nota por nota — contrabaixo dedilhado, bateria (bumbo afinado, caixa com
esteira, chimbal abafado) e um Rhodes por FM. Nada de amostra ou loop de terceiros: **não há o que
licenciar e o tema é seu**.

| clima | para quê |
|---|---|
| `tenso` | ré menor contido, 86 bpm: denúncia, investigação, suspense |
| `neutro` | ré maior sereno, 100 bpm: a cama padrão de vídeo falado |
| `claro` | dó maior aberto, 110 bpm: abertura, tutorial, boa notícia |
| `grave` | mi menor meio-tempo, 76 bpm: trecho pesado, quase só baixo e bumbo |
| `pulsante` | lá menor motor, 112 bpm: contagem, lista, montagem rápida |

Saem **dois** arquivos: `som/trilha.wav` (a música inteira, pico −3 dBFS) e `som/trilha_cama.wav` — a
mesma música com −6,5 dB entre 300 Hz e 3 kHz, teclado e chimbal mais baixos e um pouco mais escura. **É
a cama que entra na mixagem**; a cheia serve para abertura, encerramento e trecho sem fala.

`--semente` muda os detalhes do arranjo sem mudar a música. `--nome abertura` gera um segundo tema no
mesmo projeto.

## 2. A mixagem

```bash
python3 scripts/mixar.py som/voz.wav --trilha som/trilha_cama.wav --efeitos som/efeitos.wav \
    --saida som/mix_final.wav --stems som/stems --diagnostico --ajustar
```

A ordem é sempre esta:

1. **Voz.** Highpass em 70 Hz, −2 dB no abafado (250 Hz), +1,5 dB de presença (3,5 kHz), +1,2 dB de ar
   (5,2 kHz), de-esser e limiter leve. A MESMA voz tratada vira a chave do ducking.
2. **Efeitos.** Entram **a 0 dB**: o `som/efeitos.wav` da `video-efeitos-sonoros` já sai calibrado contra
   a sua voz. Não mexa no ganho dele aqui.
3. **Trilha.** Em laço a partir de `--inicio-trilha`, com ganho automático para ficar ~20 dB abaixo da
   fala **durante a fala**, e ducking por sidechain para abrir nos vãos. O sidechain tira cerca de
   8,6 dB enquanto ele fala; o que o `--diagnostico` mede é a música SUBINDO nos vãos, e esse número
   é menor (~6 dB numa fala corrida), porque o release de 450 ms não abre por completo em vão curto.
4. **Soma.** `amix` sem normalizar, limiter de barramento e loudnorm: mede (repetindo a medida se o
   ganho que falta não couber no pico), depois aplica com `linear=true` — ganho estático, que
   preserva a mixagem em vez de comprimi-la.

| opção | para quê |
|---|---|
| `--alvo -16 --tp -1.5` | peça curta (Reels, TikTok); o padrão −14/−1 é YouTube |
| `--inicio-trilha 72` | o trecho começa no segundo 72 da música (vídeo longo mixado por partes) |
| `--trilha-db -2` | ajuste fino sobre o ganho automático |
| `--diagnostico` | mede música × voz em janelas de 100 ms e **prova** o ducking |
| `--ajustar` | usa essa medida para corrigir a música e mixar de novo, uma vez |
| `--stems som/stems` | voz, efeitos, música e mix com o mesmo ganho, para o XML do editor |

## Regras e armadilhas

- **Use a cama, não a trilha cheia.** Com a cheia a voz some no meio da música e nenhum ducking salva.
- **Sem `--diagnostico` você não sabe se o ducking funcionou.** Ele mede o RMS da música nas janelas de
  fala e nas de vão; `ducking_db` é a diferença. Abaixo de 3 dB, a música não está abrindo.
- **O ganho da música é automático.** Só mexa em `--trilha-db` depois de ouvir; `--ajustar` já corrige
  sozinho o que a medida mostrar.
- **Se o aviso "o loudnorm caiu no modo dinâmico" aparecer**, a mixagem foi comprimida em vez de só
  receber ganho. O aviso diz a soma medida, o pico e o LRA: quase sempre é voz gravada baixa demais, e
  a saída é normalizar a voz antes de mixar.
- **O `LRA` do loudnorm é o ALVO de faixa dinâmica, não um teto de segurança.** Qualquer valor abaixo
  do LRA do próprio material faz o ffmpeg recusar o modo linear e comprimir. Por isso ele fica no
  máximo que o ffmpeg aceita: quem controla a dinâmica aqui é a cadeia de voz e o limiter.
- **O pico real é conferido no arquivo gravado**, não no que o loudnorm diz. Se passar do alvo, o teto do
  limiter de barramento desce exatamente a sobra e a mixagem é refeita uma vez.
- **Os stems são tirados antes do limiter de barramento**, então a soma dos três não é a mix ao pé da
  letra: o relatório mede a diferença (`resto_rms_db`, `pior_janela_400ms_db`). Resto alto = o limiter
  trabalhou muito, sinal de voz baixa na entrada.
- **Vídeo longo:** mixe por partes com `--inicio-trilha` para a música não recomeçar a cada bloco.
- O ffmpeg passa pela trava do kit de direção de arte quando ela existe (uma tarefa pesada por vez).

## Saídas

| arquivo | o que é |
|---|---|
| `som/trilha.wav` | a música inteira, pico −3 dBFS |
| `som/trilha_cama.wav` | a mesma música aberta para a voz — **é esta que vai para a mixagem** |
| `som/trilha.json` | clima, bpm, progressão, níveis, pico, RMS e correlação L/R |
| `som/mix_final.wav` | a mixagem, 48 kHz estéreo 16-bit, do tamanho exato da voz |
| `som/mix_final.json` | passadas do loudnorm, LUFS, pico real, LRA, prova do ducking e stems |
| `som/stems/{voz,efeitos,musica,mix}.wav` | os stems para o editor, no mesmo ganho da mix |
