---
name: video-motor-de-cenas
description: Motor de telas animadas sincronizadas com a fala. Você descreve cada cena ancorada por um TRECHO DO QUE A PESSOA DIZ; a skill resolve a âncora contra transcricao/palavras.json, vira tempo, renderiza na direção de arte do projeto e escreve os eventos de som. Traz 13 cenas prontas: foto, texto datilografado com grifo, número que conta, manchete, citação com carimbo, painel de pessoas ligadas por fios, linha do tempo, documento, infográfico, mapa, insert, cartela e selo. Use quando o usuário disser "anima essa parte", "põe uma tela com esse número", "card dessa citação", "cartela de troca de assunto", "linha do tempo na tela", "sincroniza a animação com a fala", "faz os motions do vídeo" ou mandar um roteiro com telas marcadas. Difere das irmãs: video-direcao-de-arte define o visual e é quem renderiza; video-animacao-audio faz legenda karaokê; video-broll trata footage; video-efeitos-sonoros sintetiza os sons que esta aponta; video-montagem encaixa os arquivos na timeline.
---

# Motor de cenas

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## O que este motor é

Uma **tela animada por vez, colada na fala**. Você não escreve tempo: escreve o trecho que a pessoa diz e a
cena entra ali. O desenho não é seu nem meu — vem do `da/da.json` do projeto (cor, tipo, escala, curvas,
durações, margens seguras). Por isso a mesma `cenas.json` serve ao horizontal e ao vertical.

**O padrão aprovado é pouco efeito.** Um movimento por vez, câmera que anda 1,5% na cena inteira e uma só
troca grande (o cartão que vira tela cheia, ou o contrário). Animação cheia de efeito fica
espalhafatosa e tira a atenção do que está sendo dito: não acrescente movimento por conta própria.

Precisa de duas coisas no projeto: `da/da.json` (skill `video-direcao-de-arte`) e `transcricao/palavras.json`
(skill `video-transcricao`). Sem DA, os comandos param com código 2.

## O fluxo, em quatro passos

Abaixo, `$M` é `~/.claude/skills/video-motor-de-cenas/scripts` e `$P` é o Python da linha `PYTHON=`.

### 1. Veja que cenas existem e o que cada uma pede

```bash
"$P" "$M/catalogo.py"                 # tabela das 13 cenas
"$P" "$M/catalogo.py" numero citacao  # todos os parâmetros dessas duas
```

### 2. Escreva `animacoes/cenas.json`

```json
{
 "formato": "horizontal",
 "cenas": [
  {"id": "c01", "tipo": "cartela",
   "ancora": "vamos para a segunda parte", "ate": "o primeiro documento",
   "params": {"sobretitulo": "Parte 2", "titulo": "O peso da acusação", "capitulo": 2, "de": 5}},

  {"id": "c02", "tipo": "numero", "ancora": "sete vezes mais alcance", "dur": 4,
   "params": {"valor": 7.4, "casas": 1, "sufixo": "x", "rotulo": "mais alcance que o desmentido",
              "apoio": "média de 120 casos", "chapeu": "Dado", "fonte": "Base aberta"}},

  {"id": "c03", "tipo": "selo", "desde": 0, "ancora": "a apuração começa aqui", "dur": 11,
   "params": {"canto": "superior_direita", "estados": [
      {"texto": "EM APURAÇÃO", "cor": "primaria", "em": 0},
      {"texto": "ARQUIVADO", "cor": "negativo", "em": "@mesmo que não dê em nada"}]}}
 ]
}
```

Campos de cada cena:

| campo | o que é |
|---|---|
| `id` | nome curto e único (vira o nome do arquivo). Sem ele, `c01`, `c02`… |
| `tipo` | a cena da biblioteca (`catalogo.py` lista) |
| `ancora` | **o trecho que a pessoa FALA**, 4 a 8 palavras seguidas — não o texto da tela |
| `em` | `"inicio"` (padrão) ou `"fim"`: a cena entra no começo ou no fim da âncora |
| `folga` | segundos a somar (negativo adianta) |
| `dur` | duração; sem ela, a duração padrão da cena |
| `ate` | outro trecho da fala: a cena dura até ali (em vez de `dur`) |
| `t0` | tempo absoluto, quando não houver âncora nenhuma |
| `desde` | segundo a partir do qual procurar a âncora (`0` volta ao começo) |
| `formato`, `alfa` | sobrescrevem o geral |
| `params` | os parâmetros da cena |
| `som` | troca o som de um tipo de âncora: `{"entrada": "zoom", "db": -22}`; `"nenhum"` cala aquele tipo |

**Âncora dentro de um parâmetro.** Onde a cena pede um número de tempo (o `em` de cada estado do selo),
`"@trecho da fala"` vira o segundo certo, contado a partir do começo da cena.

As âncoras são procuradas **em ordem**: cada uma começa a busca onde a anterior terminou, então uma frase
repetida casa na ocorrência certa. `"desde": 0` recomeça a busca do zero (é o que o selo do exemplo faz).

### 3. Resolva e OLHE as prévias antes de renderizar

```bash
"$P" "$M/motor.py" resolver "<pasta do projeto>"
"$P" "$M/motor.py" prova    "<pasta do projeto>"
```

`resolver` grava `animacoes/cenas.resolvidas.json` e imprime a tabela `id · cena · entra · dur · o que casou
na fala`. Confira essa tabela com o usuário: é a sincronia inteira em dez linhas.

`prova` renderiza **1 PNG por cena** em `qa/_prova-<id>-<cena>.png`, na metade da resolução. **Abra cada um e
mande no chat** antes de gastar um render de vídeo — é regra da casa.

### 4. Renderize e gere os eventos de som

```bash
"$P" "$M/motor.py" render  "<pasta do projeto>"      # só o que mudou; --refazer força tudo
"$P" "$M/motor.py" eventos "<pasta do projeto>"
"$P" "$M/motor.py" tudo    "<pasta do projeto>"      # os três de uma vez
```

Sai:

- `animacoes/<id>-<cena>.mp4` — cena opaca (h264, cor marcada bt709), com `<arquivo>.da.json` ao lado (o carimbo).
- `animacoes/<id>-<cena>.mov` — cena com alfa (ProRes 4444, para o Premiere): `selo` e `insert`.
- `som/eventos_motor.json` — `[{"t": 3.2, "som": "whoosh", "db": -18}]`, em tempo do vídeo. É o que a skill
  `video-efeitos-sonoros` sintetiza e mede. Só entram as âncoras de entrada e de ênfase (som discreto, poucos);
  `--todos-os-sons` inclui digitação e números. Dois eventos a menos de 0,15 s um do outro viram um.

Outras opções: `--so c03,c07` (só essas cenas), `--escala 0.5` (prévia em meia resolução), `--cenas <arquivo>`
(outro roteiro), `--formato vertical`.

## As 13 cenas

`foto` · `texto` (datilografado, com marca-texto) · `numero` (conta até o valor) · `manchete` (recorte de
notícia) · `citacao` (com carimbo de estado) · `painel` (pessoas ligadas por fios) · `linha_do_tempo` ·
`documento` (página com trecho grifado) · `infografico` (blocos ou etapas) · `mapa` (esquemático, nada baixado)
· `insert` (moldura com janela transparente) · `cartela` (troca de assunto) · `selo` (estado que muda).

Todas aceitam, além dos próprios: `palco` (`cartao` · `cheia` · `abre` · `fecha`), `camera`
(`parada` · `aproxima` · `afasta`), `chapeu`, `fonte` (o crédito), `plataforma` e `reservar_legenda`.
Parâmetro por parâmetro: `catalogo.py <nome>`, ou `references/catalogo-de-cenas.md`.

## Regras que custaram caro

- **A âncora é o que se FALA.** Copiá-la do texto que vai na tela é o erro número um: não casa, ou casa no
  lugar errado. Leia `transcricao/texto.txt` e copie de lá.
- **Casou por aproximação (`~0,8`) é aviso, não erro.** O Whisper erra nome próprio e a pessoa gagueja. O
  comando mostra o que casou: confira na tabela antes de renderizar.
- **Duas cenas opacas sobrepostas** viram aviso: é erro de roteiro. Overlay com alfa (selo, insert) pode
  conviver com qualquer coisa.
- **Nada de WebGL, GIF, vídeo tocando, `Math.random`, `Date.now` ou `setTimeout` numa cena.** O motor do kit é
  Canvas 2D e o auditor reprova relógio e sorteio: a cena é função pura do tempo.
- **Footage não entra na página.** Para encaixar vídeo, use a cena `insert` (janela transparente) e componha
  depois com `video.encaixar_em_janela` do kit, lendo `layout.janela` do carimbo.
- **Nenhuma cor nem fonte literal.** Tudo vem dos tokens da DA. Mudou a DA, renderize de novo: o carimbo
  guarda o sha256 e a conferência final reprova peça velha.
- **Máquina pequena.** O render entra na fila da trava do kit: uma coisa pesada por vez. Peça `prova` antes,
  não o vídeo inteiro.
- **Cena nova** é um módulo ES com `meta`, `build(palco, p, ctx)`, `seek(t)` puro, `key(t)` e `ancoras()`.
  Copie uma de `cenas/` e leia `references/kit-api.md` da skill `video-direcao-de-arte` (§9 e §10).
