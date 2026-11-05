---
name: video-efeitos-sonoros
description: >
  Sintetiza efeitos sonoros do zero em numpy puro — whoosh, zoom, impacto, riser, tick, blip, clique,
  carimbo, papel, caneta, fogo, datilografia suave — num timbre elegante e sem estridência, posiciona os
  eventos nas âncoras da fala e calibra o nível pelo PICO ABSOLUTO em dBFS contra o RMS da sua voz,
  gravando som/efeitos.wav. O perfil padrão é "discreto", a regra da casa para vídeo longo: poucos
  efeitos, baixos, agudo macio; efeito perto demais de outro cai fora ou desce 3 dB. Use quando o
  usuário pedir efeitos sonoros, SFX, whoosh, "som de entrada", "som das animações", "sonoriza essas
  cenas", ou reclamar que os efeitos estão altos, baixos ou estridentes demais. Irmã de video-compositor,
  que faz a trilha e a mixagem final e recebe este efeitos.wav como uma das entradas: se o pedido for
  sobre o volume da voz, da música ou o loudness final, é lá, não aqui.
---

# video-efeitos-sonoros

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

Quando o vídeo já tem fala e cenas e falta o som que amarra as duas coisas: a entrada de um cartão, o
impacto de uma palavra-chave, a página virando, o número correndo. Não serve para trilha musical nem para
o loudness final — isso é `video-compositor`.

## O princípio: o efeito é detalhe

Em vídeo longo, efeito demais cansa em cinco minutos. O perfil **`discreto`** é o padrão e é o que o
usuário aprovou: **−5 dB em tudo, teto de −26 dBFS de pico, respiro de 0,35 s e no máximo 8 efeitos por
minuto**. Só mude para `normal` ou `marcante` se o pedido for explicitamente uma abertura, um corte
vertical ou uma intro.

A biblioteca inteira é sintetizada: ataques em cosseno de 2 a 8 ms (nunca clique), energia entre 150 Hz e
3 kHz, nada de chiado acima de 6 kHz, efeitos tonais afinados no mesmo tom da trilha e uma sala pequena
comum a todos, para soarem como uma família. Não há amostra de terceiros, então não há o que licenciar.

## Fluxo

### 1. Escolha os sons (opcional: veja o catálogo)

```bash
python3 scripts/sfx_lib.py --listar
```

34 efeitos, cada um com classe (`alta`, `media`, `baixa`), pico de referência e para que serve. Há
apelidos: `whoosh`, `zoom`, `boom`, `hit`, `click`, `ding`, `brilho`, `print`, `digitacao`, `pagina`,
`marcador`, `stamp`, `synth`.

### 2. Escreva os eventos

Dois caminhos. O direto, em segundos, no formato comum das skills de vídeo:

```json
[{"t": 3.2, "som": "whoosh", "db": -18}]
```

`t` em segundos, `som` é o nome ou apelido, `db` (opcional) é o pico absoluto desejado em dBFS dentro da
mix final. Sem `db`, vale o pico que a biblioteca traz. Também aceita `ganho_db` (nuance de ±3 dB),
`inverter` (troca o lado) e `nota`. `python3 scripts/posicionar.py --exemplo som/eventos.json` grava um
modelo.

O melhor caminho é ancorar pelo **texto falado**, não pelo segundo: assim a sonorização sobrevive a um
recorte novo da montagem.

```json
[{"texto": "primeira parte", "som": "impacto", "db": -26},
 {"texto": "e agora", "som": "riser", "alinhar": "termina"},
 {"texto": "o documento", "som": "papel", "onde": "fim", "atraso": 0.05, "ocorrencia": 2}]
```

```bash
python3 scripts/ancorar.py som/ancoras.json --palavras transcricao/palavras.json --saida som/eventos.json
```

A busca ignora acento e pontuação. `onde`: `inicio` (padrão) ou `fim`. `alinhar: "termina"` faz o GESTO do efeito
**acabar** na âncora — a cauda da sala continua soando por cima, que é o que o riser precisa para
desaguar no corte. (No teste: âncora em 8,38 s, riser de gesto 1,0 s posicionado em 7,38 s.) `ocorrencia`: 1 é a primeira, −1 é a
última. Âncora que não casa com nada é listada no stderr e o script sai com código 1: conserte o texto, não
ignore. Sem `transcricao/palavras.json`, sai com código 2 — rode antes a `video-transcricao`.

### 3. Posicione e calibre

```bash
python3 scripts/posicionar.py som/eventos.json --voz som/voz.wav --saida som/efeitos.wav
```

**Passe sempre `--voz`.** É isso que torna o nível correto: a biblioteca é calibrada para uma fala com RMS
mediano de −16,4 dBFS; o script mede o RMS real da sua voz e desloca a biblioteca inteira pela diferença.
Sem `--voz`, use `--dur` e aceite que o nível é nominal.

Sai `som/efeitos.wav` (48 kHz, estéreo, 16-bit, do tamanho exato da voz) e `som/efeitos.json`, que diz,
evento por evento, o pico alvo, o pico medido, se desceu 3 dB e por quê — e lista o que ficou de fora.

### 4. Entregue ao compositor

`som/efeitos.wav` entra **a 0 dB** na mixagem (`video-compositor`): ele já está calibrado contra a sua voz.

## Opções que importam

| opção | para quê |
|---|---|
| `--perfil discreto\|normal\|marcante` | densidade e nível; `discreto` é o padrão |
| `--respiro 0.35` | segundos mínimos entre dois efeitos (sobrepõe o perfil) |
| `--por-minuto 8` | teto de densidade; `0` desliga |
| `--tom A` | afina os efeitos tonais no tom da sua trilha (padrão `D`) |
| `--sfx pasta/` | onde ficam os WAV da biblioteca (padrão `<saída>/../sfx`) |

## Regras e armadilhas

- **Respiro.** Dois efeitos a menos de `--respiro` segundos: o mais importante fica e desce 3 dB, o outro
  cai fora. Classe `alta` > `media` > `baixa`. Empate: cai o segundo. Tudo volta explicado no JSON.
- **Densidade.** `--por-minuto` é contado por minuto CHEIO da linha do tempo, não em média: num
  trecho de 20 s, 7 efeitos passam no teto de 8/min, e o `por_minuto_medio` do relatório (20,6)
  sai acima do teto sem que nada tenha sido derrubado. O teto só morde em vídeo de minutos.
- **Nunca normalize o efeitos.wav.** O pico de cada evento É a informação. Normalizar destrói a calibração.
- **Se o barramento passar de −3 dBFS**, o script baixa tudo junto e avisa: é sinal de efeito demais
  empilhado, não de ganho errado. Tire eventos ou vá para o perfil discreto.
- **Riser e efeito longo ancoram pelo fim.** `alinhar: "termina"` existe por isso. Ancorar o riser pelo
  começo faz ele subir depois do corte, que é o erro clássico.
- **Tom.** Se a trilha não estiver em Ré, passe `--tom` igual ao da trilha, senão os efeitos tonais
  (`blip`, `sparkle`, `zoom`, `impacto`) brigam com a música. Mudar o tom refaz a biblioteca inteira, de
  propósito: a família tem de continuar afinada.
- **Efeito novo.** Escreva um `.py` no projeto que comece com `from sfx_lib import *` e defina
  `EXTRA = {"nome": (receita, pico_dbfs, classe, uso)}`; passe `--extra <arquivo>`. A receita é uma
  função **sem argumentos** que devolve um sinal estéreo e usa as ferramentas da biblioteca:
  `env(t, ataque, tau)`, `lp`, `banda`, `mono2`, `com_sala`, `ar`, `thock`, `malho`, `SR` e as notas
  (`D5`, `A4`…). O pico que você declarar é o destino: o `finalizar` ajusta o ganho até ele.
- **Máquina apertada.** A biblioteca inteira leva cerca de 3 s e cabe em memória; não precisa de trava.
  O ffmpeg, quando aparece (mídia que não é WAV), passa pela trava do kit de direção de arte se ela existir.

## Saídas

| arquivo | o que é |
|---|---|
| `som/sfx/*.wav` | a biblioteca sintetizada, 48 kHz estéreo 16-bit |
| `som/sfx/manifest.json` | pico, duração, centroide, energia acima de 6 kHz e uso de cada efeito |
| `som/sfx/_amostra.wav` | todos em sequência, +10 dB, para ouvir a biblioteca sozinha |
| `som/eventos.json` | os eventos resolvidos, no formato comum |
| `som/efeitos.wav` | o barramento posicionado e calibrado, do tamanho da voz |
| `som/efeitos.json` | o relatório: nível por evento, o que desceu, o que caiu fora e por quê |
