---
name: video-prancha-de-referencia
description: Transforma o roteiro na prancha de referência do vídeo. Primeiro a decupagem em UNIDADES numeradas (U001, U002…) - cada uma com tipo de tela, as palavras daquela unidade (as DITAS, quando há transcrição), as mídias necessárias já com a orientação da direção de arte, uma linha de roteiro de edição legível e, no fim, as falas que fugiram do roteiro (improviso) com o tempo. Depois as FOLHAS DE CONTATO numeradas, com o código ligado à unidade (U045-3) e a licença embaixo de cada miniatura - o usuário escolhe os números e só então se baixa. Use quando o usuário disser "decupa o roteiro", "divide em unidades", "o que cada trecho precisa de imagem", "monta a prancha", "folha de contato", "me mostra as opções numeradas", "o que ele falou fora do roteiro" ou "roteiro de edição". Difere das irmãs - video-broll busca e baixa, video-garimpo-de-midia escolhe as fontes, video-pauta-midia lê os comentários do documento.
---

# video-prancha-de-referencia

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## Quando usar

Depois que há roteiro (e, melhor ainda, transcrição do que foi gravado) e antes de sair comprando imagem. A
prancha é o documento de onde o editor trabalha: **o que entra em cada pedaço do vídeo e de onde vem**.

São duas partes, uma por script:

- `decupar.py` — o roteiro vira unidades numeradas;
- `folha.py` — cada unidade ganha uma folha de contato numerada, e a escolha do usuário vira comando de download.

## Parte (a) — decupagem em unidades

```bash
python3 <skills>/video-prancha-de-referencia/scripts/decupar.py roteiro/roteiro-de-edicao.md
python3 .../decupar.py roteiro/roteiro-de-edicao.md --palavras transcricao/palavras.json
python3 .../decupar.py --auto roteiro/roteiro.md --alvo 10        # roteiro sem marcação
python3 .../decupar.py --listar --so-midias
```

Formato que ele lê (tudo opcional menos a linha `**U**`):

```markdown
## Bloco 1 — Abertura
### 1. O item que abre
**U** · 8 s · apresentador em tela cheia
- Fala: o texto que vai ser falado
- Tela: o que aparece
- Mídia: foto de um telescópio em observatório · imagem · en: observatory telescope
- Nota: observação para o editor
```

`**U**` numera sozinho (U001, U002…); `**U007**` fixa o número. O tipo de tela vira um **modo**:
`apresentador`, `ilustrado` (100% cobertura, ele não aparece), `misto` (janela/insert), `cartela`, `passagem`.

Com `--palavras`, cada unidade é **achada na fala** por casamento aproximado (o apresentador parafraseia):
a unidade ganha `t0`, `t1`, confiança e **as palavras ditas**. O que foi dito e não estava escrito vira
`roteiro/fora-do-roteiro.md`, com tempo e número de palavras — é o improviso.

Sai em `roteiro/unidades.json`, `roteiro/roteiro-de-edicao.md` e `roteiro/fora-do-roteiro.md`.

## Parte (b) — folhas de contato numeradas

```bash
python3 .../folha.py montar U045 [--colunas 4] [--por-fonte 4] [--pausa 2]
python3 .../folha.py montar U045 --sem-busca        # só redesenha, sem consultar ninguém
python3 .../folha.py escolher U045-3 U045-7
python3 .../folha.py listar
```

`montar` roda a busca da `video-broll` para **cada mídia pedida pela unidade**, com pausa entre os pedidos,
numera tudo na folha daquela unidade (`U045-1`, `U045-2`, …) e desenha
`broll/prancha/U045.png`: miniatura, **código em cima** e **licença embaixo**, com o sinal de cor
(verde = crédito opcional · âmbar = crédito obrigatório ou origem a conferir · vermelho = recusada).

**Mostre a folha ao usuário e espere.** `escolher` registra os códigos em `broll/prancha/escolhas.json` e
imprime o comando de download da `video-broll` — que ainda exige `--confirmar`. Nada é baixado antes disso;
`montar` baixa só as miniaturas.

## O que sai

| arquivo | o que é |
|---|---|
| `roteiro/unidades.json` | as unidades: modo, tempo, palavras ditas, mídias com código e orientação da DA |
| `roteiro/roteiro-de-edicao.md` | o roteiro de edição legível, bloco a bloco, com timecode |
| `roteiro/fora-do-roteiro.md` | as falas que fugiram do roteiro, com tempo |
| `broll/prancha/U045.png` | a folha de contato numerada da unidade |
| `broll/prancha/U045.candidatos.json` | o mapa código → busca → candidato (é o que `escolher` lê) |
| `broll/prancha/escolhas.json` | o que o usuário escolheu, por unidade |

## Regras que custaram caro

- **O código da folha é da unidade, não da busca.** `U045-3` é o que o usuário fala em voz alta; o número
  interno da busca fica no JSON. Nunca mostre dois conjuntos de números para a mesma folha.
- **Refazer a busca troca os números.** Se a folha for remontada, mostre a folha nova antes de pedir a escolha.
- **A licença vai embaixo da miniatura, sempre.** Folha sem licença leva alguém a escolher o que não pode usar.
- **A folha é ferramenta de trabalho, não peça do vídeo**: ela usa os tokens da DA quando há DA e um visual
  neutro quando não há (`--sem-da`). Mas **buscar** mídia exige DA — é ela que diz orientação e lado mínimo.
- **Unidade que não foi achada na fala** sai com `t0` nulo e um aviso no roteiro de edição: ou o trecho foi
  cortado, ou foi reescrito na gravação. Não invente tempo.
- **Improviso não é erro.** `fora-do-roteiro.md` existe para decidir o que fica — e o que fica precisa de
  cobertura que ninguém planejou.

## Códigos de saída

`0` ok · `1` falhou · `2` projeto sem direção de arte (ao buscar) · `64` erro de uso.
