---
name: video-transcricao
description: Transcreve áudio e vídeo palavra a palavra, com tempo, instalando o Whisper sozinho — corta o silêncio do começo antes de transcrever, usa os nomes próprios do roteiro no --prompt, corrige pela energia do áudio o atraso de 1 a 2 décimos do Whisper e grava transcricao/palavras.json, segmentos.json, texto.txt e qa.json. Vídeo de uma hora vai em blocos com sobreposição, costurados pelo texto repetido da emenda, sem palavra duplicada nem pulada. Também acha termo, frase ou nome escrito errado dentro da transcrição, com o minuto. Use quando o usuário pedir transcrição, decupagem, legenda em texto, "o que ele fala nesse áudio", "transcreve esse vídeo inteiro", "acha onde ele fala sobre X", ou quando outra tarefa precisar dos tempos palavra a palavra. Difere das irmãs: video-mapa-de-fala lê esta transcrição e monta o mapa do que foi dito; video-checagem compara a fala com a pesquisa; video-montagem usa estes tempos na EDL e no XML; video-mixagem e video-efeitos-sonoros tratam som, não texto.
---

# Transcrição palavra a palavra, com tempo

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

No Mac o motor é o `whisper-cli` (whisper.cpp) com o modelo `ggml-large-v3-turbo.bin`; em Linux e Windows é o
`faster-whisper`. O instalador resolve o que faltar; o seu código é o mesmo nos dois caminhos.

**Regra nº 1: o tempo que sai daqui é o tempo da mídia original.** Tudo que vem depois (legenda, EDL, motion,
efeito sonoro) é ancorado nestes segundos. Nunca "ajuste a olho" um tempo deste arquivo: refaça a transcrição
sobre o áudio certo.

```bash
TR=~/.claude/skills/video-transcricao/scripts
PY=python3                      # troque pelo caminho da linha PYTHON= do preparar.py
cd "/caminho/do projeto"
"$PY" "$TR/transcrever.py" --help     # também buscar.py e afinar.py, cada um com --help em PT-BR
```

Códigos de saída: **0** ok · **1** falhou · **2** falta insumo (mídia, ffmpeg ou Whisper).

## 1. Transcrever

```bash
"$PY" "$TR/transcrever.py" bruto/entrevista.mp4 --saida transcricao/ --nomes-de roteiro/roteiro.md
"$PY" "$TR/transcrever.py" bruto/entrevista.mp4 --saida transcricao/ --nomes "Marina Vasconcelos, Instituto Farol"
```

O que ele faz, nesta ordem:

1. **Extrai o áudio** em WAV 16 kHz mono (a entrada canônica do Whisper) em `transcricao/_trabalho/`.
2. **Mede a fala por RMS** e, se houver mais de 1 s de silêncio na frente, **corta antes de transcrever** e soma o
   corte de volta nos tempos. Sem isso o Whisper ancora a primeira palavra em 0,0 e a legenda vai adiantando até
   mais de um segundo no fim de um vídeo longo.
3. **Monta o `--prompt`** com os nomes próprios (`--nomes` e/ou `--nomes-de`, que aceita arquivo ou pasta e lê
   `.md` e `.txt`). Sem prompt o Whisper escreve nome próprio de ouvido. O prompt para em 600 caracteres: o limite
   do modelo é 224 tokens.
4. **Corta em blocos** de `--bloco` segundos (padrão 600) com `--sobreposicao` segundos repetidos (padrão 12) e
   transcreve um por vez. Cada bloco pronto fica em `_trabalho/`: se o processo morrer, rodar de novo continua de
   onde parou (`--refazer` ignora o que estava pronto).
5. **Costura** os blocos casando o texto repetido da emenda (veja «A costura», abaixo).
6. **Afina o início das palavras** pela energia do áudio (`--sem-afinar` desliga).
7. Grava `palavras.json`, `segmentos.json`, `texto.txt` e `qa.json`.

Opções que importam: `--idioma pt` (padrão; nunca deixe em automático, o Whisper troca de idioma no meio),
`--duas-passadas` (roda também a passada por segmento, para um texto de leitura com pontuação melhor — dobra o
tempo), `--sem-corte` (não mexe no silêncio inicial, quando o tempo precisa casar com outro arquivo).

## 2. Buscar dentro da transcrição

```bash
"$PY" "$TR/buscar.py" transcricao/palavras.json "orçamento"
"$PY" "$TR/buscar.py" transcricao/ "a denúncia tem muito mais peso"      # frase: aceita erro no meio
"$PY" "$TR/buscar.py" . "absolvição" --parecido                          # acha "absorvição", como o Whisper escreveu
"$PY" "$TR/buscar.py" . "investiga|denunc" --regex --json
```

Sai o `mm:ss` de cada ocorrência com o contexto em volta. Ignora acento, caixa e pontuação. Frase inteira
raramente casa palavra por palavra (o reconhecimento erra alguma no meio), por isso o padrão aceita 80% das
palavras em ordem — ajuste com `--minimo`. `--parecido` casa pela pronúncia e é o jeito de achar nome próprio
que saiu escrito errado. Códigos: 0 achou · 1 não achou · 2 falta insumo.

## 3. Afinar de novo, quando o áudio mudou

```bash
"$PY" "$TR/afinar.py" transcricao/palavras.json render/mix_final.wav
```

Depois de uma decupagem ou de uma remixagem, os tempos da transcrição não valem mais para o áudio novo. Se o
TEXTO continua o mesmo e só o áudio foi retocado, `afinar.py` reencaixa os inícios. Se o áudio foi CORTADO
(trechos removidos), transcreva de novo: afinar não inventa o que sumiu.

## Os arquivos que saem

- `transcricao/palavras.json` — `[{"w": "palavra", "t0": 1.23, "t1": 1.51, "p": 0.93}]`, segundos, `p` =
  confiança de 0 a 1. É o contrato da casa: quem lê aceita também `a`/`b` no lugar de `t0`/`t1`.
- `transcricao/segmentos.json` — `[{"t0", "t1", "texto"}]`, frases agrupadas a partir das mesmas palavras
  (quebra na pontuação, na pausa maior que 0,8 s e no comprimento). Mesmos tempos do `palavras.json`.
- `transcricao/texto.txt` — só o texto, uma frase por linha, para ler e colar.
- `transcricao/qa.json` — duração, começo e fim da fala por RMS, palavras por minuto, confiança mediana, a lista
  das palavras abaixo de 0,75, buracos de mais de 5 s sem palavra, os blocos, o diário da costura, o prompt
  usado, a estatística do afinamento e os avisos.
- `transcricao/_trabalho/` — WAV 16 kHz e os blocos já transcritos. Intermediário: pode apagar.

Outras skills importam o módulo do formato em vez de reimplementar a leitura:

```python
import sys; from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/video-transcricao/scripts"))
import palavras as P
pal = P.carregar(P.achar_palavras())        # sobe as pastas até achar transcricao/palavras.json
P.frases(pal); P.mmss(12.5); P.normalizar(s); P.fonetica(s); P.parecido(a, b)
P.nomes_do_texto(texto); P.ocorrencias_aproximadas(nome, pal)
```

## A costura dos blocos

Na emenda, os dois blocos transcreveram o **mesmo** trecho. Cortar por tempo com um limiar duplica palavra;
cortar por índice fixo pula palavra — foi o bug que custou caro. O que funciona: casar o texto repetido dos dois
lados (`difflib` sobre as palavras normalizadas, exigindo 2 palavras seguidas iguais e menos de 1 s de diferença
no tempo) e emendar exatamente no fim do casamento. Sem texto reconhecível na sobreposição (silêncio, música), cai
para o meio da sobreposição, que nunca duplica nem pula mais de uma palavra. O `qa.json` registra, em `costura`,
o método usado em cada emenda e quantas palavras foram descartadas — **leia isso** antes de confiar num arquivo
longo.

Sobreposição menor que ~6 s deixa pouco texto para casar. Em bloco curto o Whisper também tem menos contexto e
erra mais palavra: não diminua `--bloco` sem motivo.

## Armadilhas que custaram caro

- **A legenda entra certa e vai ficando adiantada.** Silêncio no começo do arquivo. É o passo 2; não pule.
- **Nome próprio sai de ouvido.** Passe `--nomes-de roteiro/roteiro.md`. Depois procure com
  `buscar.py --parecido` cada nome que importa: o que o prompt não pegou aparece ali.
- **Confiança baixa nem sempre é erro.** Num caso real, de quatro palavras abaixo de 0,75 só uma estava errada.
  Ouça o trecho antes de corrigir; nunca troque palavra isolada de uso comum por regra automática.
- **Corrigir texto estraga o tempo.** Se for corrigir o texto, troque **trechos com 2 ou 3 palavras de contexto**
  e reparta o intervalo de tempo do trecho antigo entre as palavras novas. `da ⇒ até` casa em todo "da" da fala.
- **Duas passadas, dois textos.** Com `--duas-passadas`, o `segmentos.json` vem da passada por segmento e pode
  não bater palavra por palavra com o `palavras.json`. Para karaokê e EDL use sempre o `palavras.json`.
- **A verificação circular.** Conferir a legenda contra o próprio JSON do Whisper só prova consistência interna.
  A validação de verdade é contra o áudio: compare `primeira_palavra_s` com `fala_ini_s` no `qa.json` (devem
  bater em centésimos) e ouça o começo e o fim.
- **Máquina pequena.** O modelo ocupa 1,6 GB; não rode duas transcrições ao mesmo tempo. Os scripts já passam o
  ffmpeg e o Whisper pela trava do kit de direção de arte quando ela existe (fora do Windows).
- **Entrada vazia e item começando com `[`** são controle do Whisper (`[_BEG_]`, `[Música]`): já são filtrados
  aqui, mas se você ler o JSON do Whisper na mão, filtre.
