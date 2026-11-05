---
name: engenharia-do-projeto
description: Conduz um projeto de software do papel à produção, em qualquer stack, para quem nunca programou e para dev experiente. Descobre onde o projeto está e leva ao próximo passo com especificação, stack e arquitetura com registro de decisões (ADR), dados e permissões antes das telas, fases com critério de pronto, testes em camadas, CI, revisão por lentes, ida a produção com simulação e memória entre sessões. Use sempre que o usuário quiser criar um app, site, API ou sistema, tirar uma ideia do papel, organizar ou assumir um projeto existente ou herdado, planejar fase ou funcionalidade, escolher stack, modelar o banco, montar testes ou CI, revisar ou publicar, ou disser "por onde eu começo", "em que pé estamos", "posso subir" ou "continua de onde paramos", mesmo sem falar em método. Vale para toda mudança em banco, login, permissão, pagamento, segredo ou produção. Não use para correção de uma linha fora dessas áreas, dúvida de sintaxe ou script descartável.
---

# Engenharia do projeto

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Funciona no Windows, no macOS e no Linux. No Windows, onde estiver `python3` use `py -3`.

Este arquivo é um painel: volte ao §1 ao mudar de situação ou quando o fio se perder. `<skill>` é a
pasta onde ele está; `<projeto>`, a raiz do projeto do dono.

- **Uma casa para cada fato.** Os outros documentos apontam; fato em dois lugares diverge.
- **Regra que importa vira verificação**, na camada mais barata que a enxerga.
- **O peso acompanha o risco.** Quanto processo a mudança pede sai do que ela toca.
- **Rodou ou inferiu.** O relato separa, com números copiados da saída.
- **O dono decide o produto, a produção e o dinheiro.** O agente carrega a engenharia.

Funciona porque o estado do método mora no projeto, em documentos de casa fixa: a décima sessão
começa como a primeira. O teste antes de agir: sei em que situação estou, o que prova que terminei
e de quem é a decisão? O dono conseguiria conferir?

Documento novo parte de `assets/modelos/`; ao escrever um, abra só o arquivo correspondente de
`assets/exemplo/`, que calibra tamanho e tom.

## 1. Descubra a situação (sempre o primeiro passo)

Pasta vazia, ou sessão fora de uma pasta de projeto (a pasta pessoal, uma pasta com outras coisas):
é A. Não rode nada ali: com quem nunca programou, o primeiro ato não pode ser pedir permissão para
rodar script. A pasta se combina com o dono no passo 2 do §3. No resto:

```bash
python3 <skill>/scripts/situacao.py <projeto>     # → o que existe, o que está em curso, "situação provável", "leia"
```

"Provável" é literal: cruze com o pedido. Sem Python, responda à mão: há código? Quais existem:
especificação, instruções, decisões, roteiro, estado? Que fase está em andamento? O estado é mais
velho que o último commit? O que `git status` mostra?

| | Situação | Sinais | Próximo passo | Leia |
| --- | --- | --- | --- | --- |
| A | Do zero | sem código nem documentos; "por onde eu começo" | a ordem do §3 | `references/entrevista.md` até a §2; trecho 1 de `assets/exemplo/conversa.md` |
| B | Adotar projeto existente | há código e falta `metodo.ini`, instruções ou estado; "assumi", "herdei" | levantamento só de leitura; oferecer o mínimo (§5); depois, C | `references/adocao.md` |
| C | Conduzir fase ou mudança | documentos presentes; pedido de funcionalidade, correção ou fase | o ciclo do §4 | a ficha do passo |
| D | Ir a produção | commits a enviar no ramo que implanta; "pode subir", "publica" | portões, a lista ao dono, banco, dados, código, conferência | `references/producao.md`, antes de qualquer comando |
| E | Retomar | estado mais velho que o código; "em que pé estamos", "continua de onde paramos" | ler o estado do disco, reconferir o que tem data, relatar | `references/retomada.md` |

**Fora do método:** correção que cabe em um arquivo, não toca zona sensível e não decide nada novo;
dúvida de sintaxe; script descartável. Faça direto, sem ficha: em projeto que usa o método, vale só
o portão do commit (§4). Peso leve é outra coisa: lê "O mínimo" da ficha.

- **Duas situações ao mesmo tempo:** o pedido manda; da outra, só "O mínimo" da ficha.
- **O diagnóstico e o pedido discordam:** vale o pedido. Diga ao dono o fato que muda o que será
  feito (arquivo fora do commit, verificação vencida), nunca a letra da situação.
- **Pedido pequeno em zona sensível:** é C com peso médio, mesmo que caiba em uma linha. A zona se
  decide pelo que a mudança toca; os caminhos de `[zonas]` são a rede.

## 2. Prepare o projeto (uma vez por projeto)

**Quando:** em A, no passo 2 do §3. Em B, depois do levantamento e do sim do dono. Em C, D e E, só
se o diagnóstico acusar documento faltando. Nunca na primeira resposta.

```bash
python3 <skill>/scripts/montar.py <projeto> --simular     # → o que seria criado; nada é gravado
python3 <skill>/scripts/montar.py <projeto>               # → cria só o que falta
```

Entre os dois, diga ao dono em uma frase o que será criado: seis documentos em pasta sem código; em
projeto com código, só `metodo.ini`, registro de decisões vazio, estado e, se faltar, o arquivo de
instruções.

- **Requisitos:** macOS ou Linux (no Windows, WSL), Python 3.8 ou mais novo e git. Se um deles
  pedir instalação, não instale sem o dono pedir: siga à mão.
- **Onde rodar:** todos os comandos partem da raiz do projeto. Sem repositório, `git init` antes do
  primeiro commit.
- **Projeto existente:** nada é sobrescrito nem alterado; o que existe é mapeado em `metodo.ini`.
- **Sem Python:** copie os modelos à mão; cada script traz no cabeçalho o bloco "à mão:". As recusas
  automáticas deixam de existir: diga isso ao dono.
- **Scripts no projeto:** `--com-ferramentas` copia os seis para `ferramentas/metodo/`. É
  obrigatório quando um degrau da escada ou o CI chama um deles: ali só vale o caminho do projeto.

## 3. Do zero: a ordem

1. **Entrevistar**, sem código nem escolha de ferramenta, em até duas rodadas:
   `references/entrevista.md`.
2. **Preparar (§2) e escrever a especificação.** Mostre o resumo de uma tela e pare até o
   "aprovado": `references/especificacao.md`.
3. **Decidir stack e arquitetura**, um registro por escolha: `references/stack.md` e
   `references/decisoes.md` §2. Se não é aplicação web com banco, antes
   `references/tipos-de-projeto.md`.
4. **Escrever o arquivo de instruções:** `references/instrucoes.md` §2 e §3.
5. **Dividir em fases** no roteiro; mostre o plano das fases de fundação e espere o ok:
   `references/fases.md` §1 e §2.
6. **Fase de base**, em três partes: (a) projeto que abre no ambiente local e arquivos de ambiente,
   `references/ambientes.md` §1; (b) degraus 0 a 2 com comando e `[zonas]` com os caminhos reais,
   `references/testes.md` §8; (c) primeiro estágio do CI quando o dono criar a conta e o
   repositório remoto, que são passos dele, `references/ci.md` §1 e §2.

Daí em diante, o ciclo do §4, com dados e permissões antes das telas (`references/dados.md`).

## 4. O ciclo de toda mudança

| Passo | Pergunte-se | Leia | Sai do passo com |
| --- | --- | --- | --- |
| 1. Mapear | O que já existe e o que já foi decidido? | `references/decisoes.md` ("O mínimo") | `decisoes.py titulos` lido; a lista do que a mudança toca |
| 2. Combinar | O que prova que terminei? Que peso o risco pede? | `references/fases.md` §2. `references/pesos.md` se há zona sensível ou dúvida. `references/fase-grande.md` só no peso pesado | "Pronto quando" escrito; o peso dito |
| 3. Implementar no ambiente local, com os testes junto | Que camada de teste enxerga esta regra? | `references/testes.md`, na seção da camada. `references/dados.md` só se muda esquema, permissão ou dado de exemplo. `references/fronteiras.md` só se há dado restrito ou regra "só X pode Y". `references/stack.md` §5 só se liga serviço externo. Variante, só se a stack ou a tarefa é a dela | código e teste na mesma mudança |
| 4. Subir a escada | Até que degrau subi? O que não rodou? | `references/testes.md` §1; se falhou, a §9 | a linha `escada:` de `escada.py --exigido` |
| 5. Revisar | O que nenhum teste pergunta? | `references/revisao.md` | achados com decisão; se corrigiu, a escada de novo |
| 6. Fechar | Que documento muda junto? Isto é decisão? | `references/fechar.md` | commit pelo portão; estado com data; relato e os três blocos |

**Peso.** **Leve:** horas, poucos arquivos, nenhuma zona sensível. **Médio:** dias numa área, ou
qualquer mudança em zona sensível. **Pesado:** dado restrito exposto ao público, plataforma que o
agente não conhece ou vários contratos entre partes. O que cada peso pede: `references/pesos.md` §4.

```bash
python3 <skill>/scripts/escada.py --ate 2 && git commit -m "<o que muda no comportamento>"   # portão do commit
python3 <skill>/scripts/escada.py --exigido     # fim da mudança: até o degrau que as zonas tocadas pedem
```

- **Código 3 no portão do commit:** há degrau 0, 1 ou 2 sem comando. Preencha em `metodo.ini` (o
  comando que o projeto já tem, ou `n/a: <motivo>` se o degrau não existe na stack) e rode de novo.
  Código não é commitado com um dos três pendente.
- **Código 3 em `--exigido`:** o degrau exigido ainda não existe. Não trava o commit; obriga a dizer
  o degrau em "Não rodei" e a abrir item datado em "Ficou para depois".
- **Commit só de documentos do método** (os de `[documentos]` e o `metodo.ini`) sai sem a escada:
  não há o que verificar, como nos primeiros commits de um projeto.

**O piso**, que nenhum peso corta:

1. Degraus 0 a 2 verdes antes de todo commit que toque código, ligados a ele por `&&`.
2. Segredo fora da conversa, do git e dos documentos.
3. Havendo dado restrito ou área restrita: teste de permissão por persona, teste de vazamento e a
   guarda conferida pela resposta crua.
4. Ambiente remoto: só a lista que o dono autorizou, com a conferência prévia de cada escrita lida.
5. Relato com "Rodei e vi", "Inferi" e "Não rodei".
6. O que foi cortado ou adiado fica escrito em `docs/ESTADO.md`, com data.

"O mínimo" de uma ficha são as 30 primeiras linhas: abra com esse limite e só passe dele quando o
passo pedir uma seção. No peso leve, "O mínimo" basta. Com vários agentes:
`assets/modelos/papeis.md` e `references/revisao.md` §7.

## 5. Quem decide

- **Pergunte antes**, já com a decisão padrão: escrever no ambiente remoto ou enviar ao ramo que
  implanta; mexer no que já está em produção; gravar os documentos do método em projeto que já
  existe; criar o que custa dinheiro; dependência grande; mudar o escopo; apagar dado; ação sem
  volta; desfazer decisão registrada; abrir exceção a regra inegociável.
- **Só o dono faz**, com o passo escrito para ele seguir sem o agente: painéis de serviços, contas,
  credenciais, textos legais, preço e marca. É o que o agente não alcança ou não deve alcançar.
  Aplicar migração, carregar dados e enviar código é do agente, com a lista autorizada.
- **Decida e registre** todo o resto, e declare em "Decidi sem perguntar".

Para o ambiente remoto, a pergunta é uma **lista**: o que será feito, na ordem. O sim autoriza só a
lista; pare no primeiro resultado fora do previsto, e o que não está nela pede outro pedido. Nas
fases de fundação (base e dados), mostre um plano curto e espere o ok: são as mais caras de
desfazer. Se o dono pedir algo contra a recomendação, avise uma vez, com a alternativa, cumpra e
registre quem decidiu (`references/dono.md` §4).

## 6. Regras inegociáveis

1. **Leia antes de propor.** Busque sem limite de profundidade; leia os títulos do registro de
   decisões e a documentação da versão instalada. Se não, refaz-se o que já existe.
2. **Estado com data se reconfere na fonte antes de agir.** Releia `docs/ESTADO.md` do disco e
   confira contra o ambiente. Se não, age-se sobre o que era verdade ontem.
3. **Verificação e ação seguinte se ligam com `&&`**, como no portão do commit (§4). Com `;`, o
   commit ou o envio sai com teste falhando.
4. **O relato separa o que rodou do que foi inferido**, com números copiados da saída. Se não,
   alegação vira fato e o dono decide em cima dela.
5. **Segredo não se repete.** Colado na conversa: não repita, peça a troca, use valor de teste. Não
   vai ao git nem a documento. Se não, vaza pelo histórico.
6. **Ambiente remoto é só leitura até o dono autorizar uma lista, e a autorização vale só para
   ela.** Enviar ao ramo que implanta é ir a produção. Se não, o dono perde o controle do que está
   no ar.
7. **Nada sem volta sem a conferência prévia lida.** Escreva antes o que pode sobrar na saída e pare
   se sobrar outra coisa. Onde não há simulação, o relato diz "sem simulação; conferi X".
8. **Decisão registrada não se desfaz em silêncio, e regra não se afrouxa por plano nem por
   revisão.** O que parece erro pode ser escolha: leve ao dono em "Para decidir"
   (`references/dono.md` §5). Se não, o mesmo problema é resolvido duas vezes, uma para cada lado.

## 7. Se acontecer no meio

- **O dono colou uma chave ou senha.** O valor já está no histórico. Não repita, peça a troca e use
  valor de teste. Não guarde "só por enquanto" (`references/ambientes.md` §2).
- **A permissão da sessão barrou uma ação.** A recusa é decisão de quem configurou. Pare, diga o que
  ia fazer e entregue o comando ao dono. Não tente outro caminho para o mesmo efeito
  (`references/producao.md` §9).
- **Um degrau falhou ou o CI ficou vermelho.** Rodar de novo esconde a causa. Relate com a saída e
  diagnostique antes de repetir (`references/testes.md` §9).
- **Documento e código dizem coisas diferentes.** Documento que descreve (por assunto, leia-me,
  mapa): o código manda, corrija o documento. Documento que manda (regra, registro, especificação):
  é achado; não mexa em nenhum dos dois sem o dono (`references/decisoes.md` §5).
- **Bug em produção, e o dono pede para enviar já.** A pressa convida a pular a verificação.
  Reproduza no ambiente local, envie só a correção, pelo portão, e confira como visitante. O piso
  não encolhe (`references/producao.md` §1).
- **O contexto foi resumido ou o fio se perdeu.** O que se lembra pode não ser o que está no disco.
  Rode o diagnóstico de novo e volte ao §1.

Não se encaixa em nenhum: procure pelo sintoma em `references/armadilhas.md`.

## 8. Como falar com o dono

- Linguagem comum primeiro; termo técnico entre parênteses na primeira vez. Arquivo novo se
  apresenta em uma frase, com o que o dono faz com ele.
- Letra de situação, peso, piso, zona, evidência e ficha são vocabulário do agente: ao dono, diga o
  efeito. "Escada" e "degrau" podem ir a ele, explicados uma vez.
- Até cinco perguntas por rodada, cada uma com o padrão que será adotado.
- Toda entrega fecha com os três blocos (**Decidi sem perguntar**, **Preciso de você**, **Como
  conferir**); os textos estão em `assets/modelos/mensagens-ao-dono.md`.
- O perfil padrão é o de quem nunca programou. Troque para o perfil dev quando o dono usar o
  vocabulário técnico ou pedir para ir direto, e anote em `docs/ESTADO.md`. O perfil muda a
  explicação, não o método.
- Decisão, autorização, validação ou termo novo para quem nunca programou: `references/dono.md`.

## Arquivos

Scripts, todos com `--ajuda` e a última linha `não conferi:`:

- `scripts/situacao.py`: o diagnóstico; o que existe, o que está em curso, a situação provável.
- `scripts/montar.py`: cria os documentos do método que faltam, sem sobrescrever.
- `scripts/escada.py`: sobe a escada, para no primeiro degrau que falhar, grava a evidência.
- `scripts/decisoes.py`: índice, próximo número e conferência do registro de decisões.
- `scripts/envio.py`: confere o que sairia no próximo envio: segredo, arquivo proibido, posição.
- `scripts/fronteiras.py`: regras de fronteira lidas como texto; diz o que não entende.

Modelos, exemplo e moldes:

- `assets/modelos/`: 17 modelos com lacunas; todo documento novo parte daqui.
- `assets/exemplo/`: um projeto fictício preenchido; `conversa.md` é a régua de tom com o dono.
- `assets/variante-web/`: moldes de código, chamados por `references/variante-web.md` §12.

Fichas. O momento de ler cada uma está no §1, §3, §4 e §7 (`references/dono.md`: §5 e §8):

- `references/entrevista.md`: perguntas ao dono, em linguagem comum, com padrões.
- `references/especificacao.md`: as onze seções, onde apertar, aprovação.
- `references/instrucoes.md`: arquivo de instruções; regra com verificador.
- `references/stack.md`: critérios, medir em vez de supor, serviço externo.
- `references/decisoes.md`: o que registrar, o registro, rever sem apagar.
- `references/adocao.md`: o mínimo do método num projeto existente.
- `references/pesos.md`: casos classificados, zonas sensíveis, modo enxuto.
- `references/fases.md`: cortar fases, "Pronto quando", plano de uma página.
- `references/fase-grande.md`: levantamento, plano-contrato e pacotes.
- `references/dados.md`: matriz de permissões, migrações, dados de exemplo.
- `references/testes.md`: a escada, as camadas, teste instável.
- `references/fronteiras.md`: teste que lê o código; teste de vazamento.
- `references/ci.md`: três estágios que crescem com as fases.
- `references/revisao.md`: lentes, achados, conferir antes de corrigir.
- `references/fechar.md`: documentos, commit e relato da mudança.
- `references/producao.md`: portões, a lista, banco, dados, código, conferência.
- `references/ambientes.md`: arquivos de ambiente, segredo colado, máquina do dono.
- `references/dono.md`: perguntar, validar, avisar; glossário para quem nunca programou.
- `references/retomada.md`: chegar numa sessão, o estado, notas de memória.
- `references/armadilhas.md`: índice por sintoma.
- `references/tipos-de-projeto.md`: biblioteca, CLI, API, aplicativo móvel, dados, site estático.
- `references/variante-web.md`: SQL e código para web com PostgreSQL. Só se a stack é essa.
- `references/variante-interface.md`: briefing visual, estados de tela. Antes de telas ou redesenho.
