---
name: video-roteiro-e-estilo-de-fala
description: Mede o jeito de falar de um apresentador a partir de várias transcrições (palavras por minuto, tamanho de frase, pausas, muletas, bordões, aberturas e fechos → roteiro/estilo-de-fala.json e .md) e escreve o roteiro nesse estilo, em 2 arquivos — narração (só as falas, na ordem do vídeo) e edição (o que entra na tela em cada subseção e onde buscar cada mídia) — mais roteiro/edicao.json para as skills seguintes. Divide o vídeo longo em partes, uma por agente roteirista, e junta as partes conferindo a emenda. Use quando o usuário disser "escreve o roteiro", "roteiro do vídeo", "no meu jeito de falar", "igual aos meus outros vídeos", "mede como eu falo", "quantas palavras cabem em 10 minutos", "divide o roteiro entre agentes", "monta o roteiro de edição". Difere das irmãs: video-pesquisa-ia verifica os fatos que entram aqui; video-pauta-midia lê um roteiro JÁ escrito e vira pauta de mídia; video-broll busca a mídia; gerar-roteiro faz peça curta de rede social, não vídeo longo.

---

# Roteiro e estilo de fala

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Os dois scripts só usam a biblioteca padrão: qualquer `python3` 3.10+ serve.

## O que esta skill entrega

1. **A ficha de estilo de fala** — como a pessoa fala, medido, não achado: `roteiro/estilo-de-fala.json` e `.md`.
2. **O roteiro em 2 arquivos** — `roteiro/roteiro-fala.md` (só a narração, na ordem do vídeo) e `roteiro/roteiro-edicao.md`
   (o que entra na tela em cada subseção e onde buscar cada mídia), mais `roteiro/edicao.json` para as skills seguintes.

Os dois arquivos existem por um motivo prático: quem grava lê **só** o de narração, sem nenhuma marcação atrapalhando;
quem edita abre o de edição e já sabe o que cada frase precisa mostrar, sem reler o roteiro inteiro.

## Passo 1 — Medir o jeito de falar

Junte de 3 a 10 transcrições de vídeos antigos da pessoa (quanto mais fala, melhor a medida; 20 minutos no total já dá
um número estável). Transcreva com a skill `video-transcricao`, ou use `.palavras.json` que o projeto já tenha:

```bash
python3 ~/.claude/skills/video-roteiro-e-estilo-de-fala/scripts/estilo.py \
    transcricao/*.palavras.json --saida roteiro/ --nome "Apresentador"
```

Entra: `.palavras.json` (`[{"w","t0","t1","p"}]`, também aceita o formato antigo `a`/`b`), `segmentos.json`
(`[{"t0","t1","texto"}]`, com o tempo repartido entre as palavras), `.txt`/`.md` (só texto: conta frase e vocabulário,
não conta ritmo) ou uma pasta com qualquer um deles. `--min-repeticoes N` (padrão 3) é quantas vezes uma sequência
precisa aparecer para virar bordão.

Sai `roteiro/estilo-de-fala.md`, que é o que o roteirista lê, com:

- **Palavras por minuto**, corridas e sem as pausas, e o **orçamento de palavras** por duração (15 s, 30 s, 1 min, 5 min, 10 min).
- **Tamanho de frase**: média, mediana, a curta (p10), a longa (p90) e a maior.
- **Ritmo das pausas**: quantas pausas de 0,6 s e de 1,2 s por minuto, a mediana e a maior.
- **Muletas** (`né`, `tipo`, `então`, `sabe`…) com quantas vezes e por mil palavras; **viradas** (`só que`, `o problema é que`, `agora`); **bordões** (sequências de 3 a 6 palavras que ele repete, e em quantos vídeos diferentes).
- **Aberturas e fechos** reais, um por transcrição, e os **começos de frase** que ele repete.
- Perguntas por 100 frases, números por mil palavras e variedade de vocabulário.

Mostre a ficha ao usuário antes de escrever. **Ela mede COMO ele fala, não O QUE ele diz**: nenhum número daí
autoriza uma afirmação no roteiro — isso é a ficha de fatos da `video-pesquisa-ia`.

## Passo 2 — Do material de pesquisa ao esqueleto

Antes de escrever uma linha, feche com o usuário:

1. **A tese**, em uma frase. Se o vídeo não cabe numa frase, tem ideia demais.
2. **A duração alvo** → converta em palavras pelo orçamento da ficha (num vídeo de 40 min a 160 ppm são ~6400 palavras).
3. **As partes**, na ordem do vídeo: de 4 a 10 blocos, cada um com um título, as subseções dentro dele e qual pedaço da
   pesquisa sustenta cada subseção. Esta lista é o contrato entre os agentes roteiristas.
4. **O que NÃO entra** (o material que ficou de fora e por quê) — é o que impede dois agentes de escreverem a mesma coisa.

## Passo 3 — Um agente roteirista por parte

Uma parte por agente, todos em paralelo. Cada agente recebe, e só isso:

- `roteiro/estilo-de-fala.md` inteiro e `references/escrita.md` desta skill;
- a tese do vídeo, o orçamento de palavras **da parte dele** e o título das partes vizinhas;
- **o último parágrafo da parte anterior e o primeiro da seguinte** (quando já existirem) — é a emenda;
- o pedaço da pesquisa da parte dele, com os `fato_id` disponíveis;
- a lista do que não entra.

Cada agente grava **dois arquivos com o mesmo prefixo** em `roteiro/partes/`:

```
roteiro/partes/03-regua-de-prova.fala.md       # `# Título da parte`, `## subseção`, parágrafos de fala
roteiro/partes/03-regua-de-prova.edicao.json   # lista de blocos (contrato em references/formato-dos-roteiros.md)
```

Regras do pedido que evitam os três erros clássicos: **cada parte só pode usar o material dela** (senão duas partes
contam o mesmo caso); **nenhuma parte abre se apresentando de novo** ("como eu disse", "neste vídeo") — quem abre é a
parte 01; e **o campo `fala` de cada bloco é um trecho literal da narração**, copiado e colado, porque é por ele que a
montagem acha o ponto depois da gravação.

## Passo 4 — Juntar e conferir a emenda

```bash
python3 ~/.claude/skills/video-roteiro-e-estilo-de-fala/scripts/juntar.py           # grava os 3 arquivos
python3 ~/.claude/skills/video-roteiro-e-estilo-de-fala/scripts/juntar.py --so-conferir
```

Grava `roteiro/roteiro-fala.md`, `roteiro/roteiro-edicao.md` e `roteiro/edicao.json`, e **reprova (código 1)**:
parte faltando ou numerada duas vezes, parte com um arquivo só, subseção sem nenhum bloco de edição, bloco apontando
para uma subseção que não existe, `fala` de bloco que não aparece na narração, **frase de 8 palavras ou mais repetida
em duas partes** (o erro mais comum de roteiro escrito por vários agentes) e marcador de seção dentro da fala.
Avisa (não reprova): vocabulário banido, fechamento "não é X, é Y", número por extenso, código de tela desconhecido e
bloco de mídia de fora sem dizer onde buscar. No fim imprime a duração estimada do vídeo pelo ppm da ficha de estilo.

Os códigos de tela são os de `references/formato-dos-roteiros.md`; para usar outros, grave `roteiro/telas.json`
(`{"CODIGO": "o que é na tela"}`) e eles entram na legenda.

Depois de juntar: leia o `roteiro-fala.md` inteiro em voz alta (ou peça a um agente revisor) contra o checklist de
`references/escrita.md`, e só então mande gravar.

## O que vai para as skills seguintes

| Arquivo | Quem usa |
|---|---|
| `roteiro/roteiro-fala.md` | quem grava; a `video-transcricao` usa os nomes próprios daqui no `--nomes` |
| `roteiro/roteiro-edicao.md` | o usuário e o editor humano |
| `roteiro/edicao.json` | `video-pauta-midia` (vira pauta), `video-broll` (o que buscar), as skills de animação (o que desenhar), `video-montagem` (onde cada tela entra) |
| `roteiro/estilo-de-fala.json` | esta skill, quando o roteiro for revisado, e qualquer agente que reescreva um trecho |

Fatos: todo número, data, nome e citação do roteiro precisa de `fato_id` na `pesquisa/fatos.json` da `video-pesquisa-ia`.
O bloco de edição carrega esses ids em `fatos`, e é por ali que o crédito na tela é conferido.

## Armadilhas que custaram caro

- **Transcrição curta mente sobre o ritmo.** Com 20 segundos de fala o ppm saiu 219, e com 75 s, 186 — a mesma pessoa.
  Abaixo de ~10 minutos somados, trate o número como estimativa e diga isso ao usuário.
- **Sem pontuação, "frase média" vira o vídeo inteiro.** Transcrição sem ponto final dá uma frase só; o `estilo.py`
  percebe (menos de uma frase a cada 45 palavras) e passa a dividir pelas pausas de 1,2 s — confira a coluna
  "frases divididas por" antes de acreditar no tamanho de frase.
- **Tirar todas as muletas deixa a fala com cara de IA.** A ficha mostra quantas ele usa por mil palavras; mantenha as
  duas ou três mais frequentes, nas viradas, e nunca duas na mesma frase.
- **Bordão é tempero, não molho.** Sequência que aparece em mais de um vídeo é marca registrada: 1 ou 2 por vídeo.
  Repetida em toda parte, o vídeo fica com cara de paródia — e cada agente repete a dele sem saber dos outros.
- **Agente roteirista sem a lista do que não entra reescreve a parte do vizinho.** Foi exatamente o que o `juntar.py`
  pegou no teste: a mesma frase de 20 palavras em duas partes, escrita por dois agentes que receberam a mesma pesquisa.
- **O `fala` do bloco tem de ser literal.** Resumo ("quando ele fala do tanque") não casa com a transcrição depois da
  gravação, e a montagem não acha o ponto. Copie e cole da narração.
- **Marcação de tela dentro da narração atrapalha a gravação.** `[0-3s]`, `HOOK`, `CTA` e `B-ROLL:` no meio da fala
  acabam lidos em voz alta. A narração é só o que sai da boca.
- **Número por extenso soa fraco e atrapalha a conferência.** `6 etapas` vence `seis etapas`, e o número em algarismo é
  o que a ficha de fatos consegue casar.
- **Duração estimada é estimativa.** Ela usa o ppm da ficha; leitura de documento na tela, pausa de respiração e
  regravação mudam o resultado para mais. Deixe de 10 a 15 % de folga.
