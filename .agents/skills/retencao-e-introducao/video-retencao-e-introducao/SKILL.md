---
name: video-retencao-e-introducao
description: Monta a introdução do vídeo - feita POR ÚLTIMO, com as melhores mídias do vídeo pronto - como uma rajada que troca a cada 1 ou 2 segundos no ritmo da fala e da música, com chicotes, flashes brancos e zooms entre as tomadas, renderizada no formato da direção de arte. Entrega o plano, o MP4, os eventos de som em som/eventos_intro.json e um checklist de retenção em qa/retencao-intro.md (ritmo medido, transições, mídia repetida, licença de tudo que entrou). Use quando o usuário disser "faz a intro", "a abertura do vídeo", "os primeiros segundos", "aquela rajada do começo", "monta o gancho", "o vídeo está perdendo gente no começo", "checklist de retenção" ou "o que colocar antes da vinheta". Difere das irmãs - video-montagem cuida da timeline inteira, video-efeitos-sonoros sintetiza os sons que os eventos daqui pedem, video-motion-graphics desenha cena, não corta mídia.
---

# video-retencao-e-introducao

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

**No fim.** A intro é a última coisa montada, porque ela é feita com o melhor do vídeo já pronto: as tomadas
que ficaram boas, os motions que funcionaram, as imagens mais fortes. Fazer a intro antes é escolher no escuro.

A dinâmica é sempre a mesma: tomada curta atrás de tomada curta, **troca a cada 1–2 s**, no ritmo da fala e da
música, com chicote, flash branco e zoom entre elas. No vídeo de referência foram 1 min 52 s com 120 mídias.

## Fluxo

```bash
# 1. planejar (não renderiza)
python3 <skills>/video-retencao-e-introducao/scripts/intro.py planejar \
    --midias broll/tratado --fala transcricao/palavras.json --t0 0 --t1 112 --bpm 120 --min 1 --max 2

# 2. renderizar
python3 .../intro.py montar [--previa] [--refazer]

# 3. checklist de retenção
python3 .../intro.py checklist --medir render/intro.mp4
```

- `--midias` aceita uma **pasta**, um **arquivo de lista** (um caminho por linha) ou uma mídia; sem ele, procura
  em `broll/tratado`, `broll/bruto` e `bruto`. As mídias entram em rodízio, na ordem da lista.
- `--fala` dá o ritmo da narração: cada corte encosta na palavra ou na **pausa** mais próxima.
- `--bpm` põe as trocas na batida (`--compasso` diz quantas batidas tem o compasso; a batida forte pesa mais).
- `--semente` torna o plano reprodutível: o mesmo número dá o mesmo corte.
- `--previa` renderiza em metade do lado para olhar rápido antes do render bom.

**Mostre a prévia ao usuário antes do render definitivo.** Intro é a parte mais subjetiva do vídeo.

## O que sai

| arquivo | o que é |
|---|---|
| `animacoes/intro/plano.json` | cada tomada: mídia, trecho, duração, transição de entrada, folga e zoom |
| `render/intro.mp4` | a intro renderizada no formato da DA, carimbada |
| `som/eventos_intro.json` | `[{"t": 3.2, "som": "whoosh", "db": -18}]` — o que a video-efeitos-sonoros sonoriza |
| `qa/retencao-intro.md` | o checklist: ritmo medido, transições, mídia repetida, licença de tudo |
| `animacoes/intro/_trab/c###.mp4` | os clipes intermediários (apague à vontade; `--refazer` os refaz) |

## As transições

| nome | xfade | duração | som |
|---|---|---|---|
| `corte` | corte seco (1 quadro) | — | — |
| `chicote` / `chicote_dir` | `smoothleft` / `smoothright` | 0,22 s | `whoosh` −18 dB |
| `branco` (flash) | `fadewhite` | 0,30 s | `impacto` −16 dB |
| `zoom` | `circleopen` | 0,36 s | `zoom_in` −20 dB |

O plano escolhe sozinho: flash onde a fala **pausa**, chicote na batida forte, zoom de vez em quando, corte
seco no resto. O `zoom` usa `circleopen`, e não `zoomin`: saindo de footage, o `zoomin` amplia tanto no meio da
transição que o quadro vira uma mancha chapada de uma cor só (medido no quadro do meio: desvio padrão 0,3 e 5
tons distintos, contra 40,6 e 242 tons com o `circleopen`). O `zoomin` ficou em `zoom_duro`, que só presta
saindo de peça gráfica — e, mesmo escrito à mão no `plano.json`, `montar` troca o `zoomin` por `circleopen`
quando o clipe que **sai** não é peça gráfica (campo `grafico` da tomada). Mexer à mão no `plano.json` e rodar
`montar` de novo é o caminho normal de refino.

## Regras que custaram caro

- **A folga no fim de cada clipe e o corte no fim da cadeia.** Cada clipe entra no `xfade` com
  `tpad=stop_mode=clone:stop_duration=0.15` e a cadeia toda termina em `trim=duration=<total>`. Sem a folga,
  um corte de 1 quadro encerra a cadeia antes da hora e a intro sai curta; sem o `trim`, sobra o rabo da
  última folga. Este par custou um dia de depuração — não mexa.
- **Cada clipe é renderizado com `dur + folga`**: a folga de uma tomada é a duração da transição da
  **próxima**. Se o clipe tiver só `dur`, o `xfade` come o fim dela.
- **O offset do `xfade` acumula a duração LÍQUIDA** (`dur`), nunca `dur + folga`. Somar a folga empurra tudo.
- **Nada de começar a tomada no primeiro quadro da mídia**: é ali que mora o pior enquadramento. O plano entra
  no miolo (`dentro`).
- **Tomada parada mais de ~2,5 s mata a retenção** — o checklist reprova e diz qual é.
- **A intro é peça do vídeo**: sem direção de arte ela não sai (código 2). Formato, fps e carimbo vêm da DA.
- **Mídia repetida em sequência** é o erro mais visível de uma rajada montada por script: o checklist conta.

## Códigos de saída

`0` ok · `1` falhou (o ffmpeg diz o porquê) · `2` projeto sem direção de arte · `64` erro de uso.
