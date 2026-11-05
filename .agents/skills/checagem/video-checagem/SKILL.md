---
name: video-checagem
description: Cruza o que foi DITO no vídeo com a pesquisa e os documentos do projeto e aponta, com mm:ss e a evidência ao lado, número que não bate com a fonte, citação entre aspas que não existe na fonte, dado que na fonte é de outro caso, atribuição trocada (o dado é de X e foi dito de Y), afirmação sem apoio nenhum e fato que a ficha de pesquisa marca como não confirmado ou vencido; marca «sensível» todo trecho que junta pessoa com acusação. Lê transcricao/palavras.json, pesquisa/fatos.json e .md/.txt/.pdf; grava qa/checagem.json e .md. Use quando o usuário disser "confere se o que eu falei está certo", "esse número bate com a fonte?", "ele disse isso mesmo?", "checagem antes de publicar", "o que eu falei tem fonte?" ou "tem alguma coisa errada no que eu gravei". Difere das irmãs: video-pesquisa-ia levanta e valida as fontes, video-mapa-de-fala inventaria a fala; aqui só se cruza fala × fonte, e nada é corrigido sozinho.
---

# Checagem: a fala contra a pesquisa e os documentos

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Depende da skill `video-transcricao` (daí vêm os tempos e o módulo do formato). `pypdf` é usado para ler PDF;
sem ele a skill tenta o `pdftotext` do sistema e, se não achar nenhum dos dois, **avisa qual PDF ficou de fora**
em vez de fingir que leu. Nada de rede.

## Regra nº 1: isto é uma peneira, não um veredito

Tudo que sai daqui é **suspeita com a evidência ao lado**, para alguém abrir a fonte e decidir. O script compara
números, nomes e palavras; ele não entende o assunto, não sabe o que é notícia velha nem quem está certo.
**Nenhum item vira correção automática** no roteiro, na transcrição ou no vídeo. Não leia a saída bruta ao
usuário como se fosse conclusão: abra a fonte citada em cada item antes de propor qualquer mudança.

## O que ela precisa

| insumo | de onde vem | obrigatório |
|---|---|---|
| `transcricao/palavras.json` | skill `video-transcricao` | sim |
| `pesquisa/fatos.json` | skill `video-pesquisa-ia` (contrato da casa) | pelo menos um dos dois |
| documentos `.md`, `.txt`, `.markdown`, `.csv`, `.json`, `.pdf` | `pesquisa/` e `documentos/` do projeto | pelo menos um dos dois |

Arquivo cujo nome começa com `_` é intermediário e é ignorado.

## Rodar

```bash
CH=~/.claude/skills/video-checagem/scripts
PY=python3                       # o da linha PYTHON= do preparar.py
cd "/caminho/do projeto"

"$PY" "$CH/checar.py"                                         # acha o projeto sozinho; usa pesquisa/ e documentos/
"$PY" "$CH/checar.py" --projeto . --documentos pesquisa/ docs/laudo.pdf
"$PY" "$CH/checar.py" --fatos pesquisa/fatos.json --palavras transcricao/palavras.json --saida qa/
"$PY" "$CH/checar.py" --hoje 2026-11-20                       # simula a data de PUBLICAÇÃO (o que terá vencido lá?)
```

Códigos de saída: **0** nada a apontar · **1** há itens para resolver · **2** falta insumo (sem transcrição, ou
sem ficha e sem documento nenhum).

## O que sai

`qa/checagem.json` (para script) e `qa/checagem.md` (para ler), os dois com `mm:ss`, a frase como foi falada, o
trecho da fonte e o que fazer. No `.md` os itens vêm em ordem de gravidade.

| tipo | o que é | gravidade |
|---|---|---|
| `numero_divergente` | o número falado e o da fonte são do mesmo tipo e não batem | alta |
| `citacao_nao_encontrada` | o que está entre aspas (ou atribuído com «disse», «segundo») não aparece em fonte nenhuma | alta |
| `citacao_diferente` | a citação existe, mas não palavra por palavra | média |
| `atribuicao_trocada` | o número confere, mas na fonte ele é de outra pessoa | alta |
| `fato_de_outro_caso` | a frase é quase a da fonte, só que lá o assunto é outra pessoa | alta |
| `sem_apoio` | o número falado não existe na pesquisa nem nos documentos | média |
| `fato_nao_confirmado` | a ficha tem o fato, com `status` diferente de `confirmado` | alta |
| `fato_vencido` | o fato da ficha caducou (`caduca_em` antes de hoje ou de `--hoje`) | média |
| `pessoa_com_acusacao` | pessoa + palavra de acusação no mesmo trecho, sem nada apontado antes | média |

Todo item tem `sensivel: true/false`. **Sensível** é todo trecho que junta nome de pessoa com acusação
(fraude, desvio, propina, condenado, assédio…), tenha ou não outro problema: não vai ao ar sem fonte conferida
e sem a resposta de quem está sendo acusado. É o único rótulo da skill que vale mesmo quando o resto está certo.

Formato de cada item: `{"id": "C001", "tipo", "gravidade", "sensivel", "t0", "t1", "mmss", "falado",
"valor_falado", "na_fonte", "citado", "semelhanca", "de_quem_na_fonte", "na_fonte_sobre", "status_na_ficha",
"caduca_em", "fonte": {"origem": "fatos"|"documento", "ref": "F003"|"laudo.pdf:12", "titulo", "url"},
"trecho_da_fonte", "pessoas_no_trecho", "acusacoes_no_trecho", "o_que_fazer"}`. O `resumo` traz as contagens,
os documentos lidos e **os que não consegui ler** — leia essa lista antes de confiar no resultado.

## O que o Claude faz com a saída

1. **Leia o `checagem.md` inteiro** antes de dizer qualquer coisa ao usuário.
2. **Abra a fonte de cada item de gravidade alta.** O `trecho_da_fonte` é um pedaço: a decisão é na fonte.
3. **Ordene por consequência, não por contagem.** Um `atribuicao_trocada` sobre uma pessoa viva vale mais que
   dez `sem_apoio` de número redondo.
4. **Separe o que se resolve na edição do que exige regravação.** Número errado dito uma vez costuma sair com
   um corte; tese errada, não.
5. **Sensível é conversa com o usuário**, não decisão sua: mostre o trecho, a fonte que existe (ou a falta dela)
   e pergunte se há a resposta do outro lado.
6. **Devolva o que ficou provado.** Fato que a checagem confirmou com uma fonte nova entra na ficha pela skill
   `video-pesquisa-ia` (`fatos adicionar` / `fatos atualizar`), não num bloco de notas solto.

## Armadilhas

- **Transcrição literal não é texto limpo.** O Whisper escreve "trezentos e vinte mil" e a fonte escreve
  "320.000": a skill já casa os dois (número por extenso, "mil/milhão/bilhão", `1.234,56`), mas erra quando a
  fala é truncada ou o nome saiu grafado errado. Rode a `video-mapa-de-fala` antes para consertar os nomes.
- **"cerca de" muda a tolerância.** Sem aproximação, 0,5% de diferença já é divergência; com "cerca de",
  "quase", "uns", a tolerância vira 10%. Um número exato falado como aproximado esconde erro de verdade.
- **Documento que não entra, não checa.** Um PDF escaneado (imagem) não tem texto: ele aparece em
  `documentos_nao_lidos` e tudo que dependia dele vira `sem_apoio`. Confira essa lista sempre.
- **`sem_apoio` quase nunca é mentira.** Na maior parte das vezes é pesquisa que falta, ou o dado está num
  documento que ninguém pôs na pasta. Trate como pergunta, não como acusação.
- **A ficha manda na data.** `fato_vencido` usa `caduca_em` da `video-pesquisa-ia`. Antes de publicar, rode com
  `--hoje <data da publicação>`: o que vence na semana que vem é problema hoje.
- **O léxico de acusação é bruto de propósito.** Ele marca "esquema", "crime", "preso" em qualquer contexto —
  inclusive numa frase inocente. Falso positivo aqui custa um minuto de leitura; falso negativo custa processo.
- **Checagem depois da decupagem.** Se o material foi cortado depois da transcrição, os `mm:ss` apontam para o
  lugar errado: transcreva o corte novo antes de checar.
- **Ela não busca nada na internet.** Só compara com o que já está no projeto. Para levantar fonte nova, é a
  `video-pesquisa-ia`.
