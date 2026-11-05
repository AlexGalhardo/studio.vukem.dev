---
name: video-mapa-de-fala
description: Transforma a transcrição no mapa mecânico do que foi dito — blocos de contexto, pessoas citadas (casando um banco de nomes por som, o que acha o nome que o Whisper escreveu errado), objetos, provas e lugares, números e datas com o tempo, o relógio das palavras (palavras por minuto por trecho), repetições, gaguejos, retomadas, muletas e silêncios, e fala × roteiro (improviso e o que não foi dito). Grava transcricao/mapa/*.json e mapa.md, tudo com mm:ss. Use quando o usuário disser "o que ele falou nesse vídeo", "quem ele cita", "onde ele fala números", "o que ele improvisou", "ele seguiu o roteiro?", "aqui ele falou rápido demais", ou quando for decupar, montar pauta de mídia ou checar fatos e faltar o inventário da fala. O script só mede, conta e casa; a leitura — quem importa, o que a prova prova, o que entra no vídeo — é do Claude. Difere das irmãs: video-transcricao produz os tempos lidos aqui; video-checagem compara a fala com a pesquisa e os documentos; video-montagem usa os tempos na timeline.
---

# Mapa de fala: o inventário do que foi dito

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Depende da skill `video-transcricao` (o `transcricao/palavras.json` e o módulo do formato vêm de lá). Só
biblioteca padrão; nada de rede.

**Regra nº 1: o script é mecânico, a leitura é sua.** Tudo que sai daqui é **candidato**: um nome que casou por
som, uma palavra do léxico de provas, um número, um trecho que não bateu com o roteiro. O script não sabe quem
é importante, se a prova prova alguma coisa, se o improviso ficou melhor que o roteiro nem o que entra no vídeo.
Isso se decide lendo os arquivos — é o seu trabalho, não o dele. Não apresente a saída bruta ao usuário como se
fosse conclusão.

```bash
MF=~/.claude/skills/video-mapa-de-fala/scripts
PY=python3                       # o da linha PYTHON= do preparar.py
cd "/caminho/do projeto"
```

Códigos de saída: **0** ok · **1** falhou · **2** falta insumo (sem transcrição).

## 1. Banco de nomes (antes do mapa)

```bash
"$PY" "$MF/nomes.py" --projeto .            # lê roteiro/ e pesquisa/fatos.json → roteiro/nomes.json
"$PY" "$MF/nomes.py" --transcricao          # inclui os nomes que o Whisper já escreveu
```

Sai `roteiro/nomes.json`:

```json
{"versao": 1,
 "pessoas": [{"nome": "Marina Vasconcelos", "papel": "repórter", "variantes": ["Marina"]}],
 "organizacoes": [{"nome": "Instituto Farol", "papel": "", "variantes": []}],
 "lugares": [{"nome": "Vila Esperança", "papel": "", "variantes": []}], "outros": []}
```

A separação entre pessoa, organização e lugar é um chute por palavra-chave. **Abra o arquivo, conserte a
separação e preencha `papel` e `variantes`** (apelido, só o primeiro nome, a sigla) antes de rodar o mapa:
é a variante que faz a skill achar a citação curta, e é o banco inteiro que faz o casamento fonético valer.
Rodar o `nomes.py` de novo não apaga nada — só acrescenta o que faltava.

## 2. O mapa

```bash
"$PY" "$MF/mapa.py" --projeto .
"$PY" "$MF/mapa.py" --palavras transcricao/palavras.json --roteiro roteiro/roteiro.md --nomes roteiro/nomes.json
```

Grava em `transcricao/mapa/`:

| arquivo | o que traz |
|---|---|
| `blocos.json` | blocos de contexto (`B001`…): quebram na pausa ≥ 1,2 s, em 45 s ou em 130 palavras. Cada um com `t0`, `t1`, `mmss`, `palavras`, `ppm` e o texto. É o endereço que todos os outros arquivos usam. |
| `pessoas.json` | cada pessoa do banco: quantas vezes foi citada, em que blocos, e **cada ocorrência** com `como_foi_dito`, `tipo` (`exato` ou `parecido`) e `semelhanca`. Pessoa do banco com `vezes: 0` não foi citada. |
| `coisas.json` | `citados` (palavra de prova ou de lugar com as 6 palavras em volta), `organizacoes`, `lugares` e `nomes_fora_do_banco` (nome próprio dito que o banco não conhece). |
| `numeros.json` | número, dinheiro, percentual, data, ano e hora, com o tempo e o trecho. O tipo sai da vizinhança: "3 milhões de reais" é dinheiro, "março de 2019" é data. |
| `relogio.json` | palavras por minuto por bloco e por minuto do vídeo, com `ritmo`: `corrido`, `no ritmo` ou `arrastado` em relação à mediana do próprio vídeo. |
| `tropecos.json` | `repeticoes` (palavra repetida, gaguejo, retomada do trecho inteiro), `silencios` ≥ 1,5 s e `muletas` com quantas vezes e quando. |
| `roteiro.json` | fala × roteiro: `casadas` (frase do roteiro → tempo e `como_foi_dito`), `nao_faladas` (ficou no papel) e `improvisos` (fala que não veio do roteiro), mais a `cobertura_das_palavras`. |
| `mapa.md` | tudo isso em texto, com `mm:ss`, para ler de uma vez. |

Sem `roteiro/nomes.json` o mapa roda do mesmo jeito, mas sem a seção de pessoas (e sem achar nome escrito
errado). Sem roteiro, sem a seção fala × roteiro.

## 3. O que fazer com o mapa (a parte do Claude)

1. **Leia o `mapa.md` inteiro** antes de falar qualquer coisa ao usuário.
2. **Pessoas**: junte as grafias (`grafias` traz o que o Whisper escreveu); decida quem é figura central e quem
   é citação de passagem; devolva ao `nomes.json` a variante que faltava. Nome com `semelhanca` abaixo de ~0,88
   merece conferência: pode ser coincidência de som.
3. **Provas e objetos**: o léxico acha a palavra, não o fato. "o documento mostra" pode ser um documento que o
   vídeo nunca exibe — isso vira pedido de mídia (skill `video-pauta-midia`), não prova.
4. **Números e datas** são a entrada da checagem: passe-os à skill `video-checagem` com a pesquisa.
5. **Relógio**: trecho `corrido` costuma precisar de respiro na montagem; `arrastado`, de corte. Compare com o
   resto do próprio vídeo, nunca com um número absoluto.
6. **Tropeços**: é matéria-prima da decupagem (qual tentativa fica), não erro a corrigir no texto.
7. **Improvisos**: leia um por um. Improviso bom entra no roteiro final; improviso que inventa fato vai para a
   checagem. Frase `nao_falada` é decisão de direção: ficou de fora de propósito ou foi esquecida?

## Armadilhas

- **Mapa não é decupagem.** Aqui ninguém decide o que fica no corte; isso é da skill de decupagem, que usa estes
  mesmos tempos.
- **O casamento fonético acha parecido, não igual.** Sobrenome curto e nome comum casam com qualquer coisa: o
  limiar é 0,82 e nomes de menos de três letras são ignorados de propósito. Confira antes de corrigir a
  transcrição com base nele.
- **Banco de nomes ruim, mapa ruim.** Se o `nomes.json` saiu do roteiro mas o vídeo cita gente que não estava
  lá, essas pessoas aparecem em `nomes_fora_do_banco` — leia essa lista sempre; é lá que mora o que o roteiro
  não previu.
- **A cobertura do roteiro não mede qualidade.** 75% de cobertura num vídeo lido é problema; num vídeo de
  conversa é o normal. Use junto com os `improvisos`.
- **Bloco não é parágrafo.** Fala corrida sem pausa vira bloco de 45 s; isso não quer dizer que seja um assunto
  só. Para assunto, leia o texto.
- **Transcrição velha.** Se o áudio foi decupado depois da transcrição, os tempos do mapa apontam para o lugar
  errado. Transcreva de novo o material montado antes de mapear.
