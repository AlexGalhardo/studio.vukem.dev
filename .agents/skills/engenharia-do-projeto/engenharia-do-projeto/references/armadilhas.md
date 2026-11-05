# Armadilhas: algo deu errado, em que ficha está a saída?

Leia quando: as interrupções do `SKILL.md` §7 não resolveram.
Não é aqui: a causa e a saída de cada armadilha. Elas moram na ficha do assunto, na seção indicada
e em "O que evitar"; cada linha daqui só aponta.

## O mínimo

- Relate com a saída do comando, não com "deu erro".
- Não rode de novo esperando outro resultado: repetir esconde a causa.
- Ache o sintoma numa das cinco tabelas e abra a ficha na seção indicada.
- Se foi o dono que disse "não funcionou", faça três perguntas antes de mexer: o que ele abriu, o
  que esperava, o que apareceu.
- Sintoma que não está aqui: abra a ficha do assunto e, no relato, separe o que foi medido do que
  é hipótese.

Conteúdo: 1. O teste passa e não prova 2. Passou aqui e falha lá 3. Fui a produção e não apareceu
4. Os documentos se contradizem 5. Fiz o que não devia

## 1. O teste passa e não prova

| Sintoma, como aparece | Onde está a saída |
| --- | --- |
| A verificação de fronteiras está verde, e descobre-se que ela não leu arquivo nenhum | `references/fronteiras.md` §5 |
| A regra continua verde depois que o arquivo que ela protegia mudou de nome | `references/fronteiras.md` §5 |
| O teste de permissão passa para toda persona, inclusive a que devia ser barrada | `references/testes.md` §6 |
| O teste de vazamento passa, e o dado restrito está na resposta crua | `references/fronteiras.md` §6 |
| O teste da área restrita passa, e a página abre para quem não devia entrar | `references/fronteiras.md` §7 |
| O item de "Pronto quando" passa com a página ainda vazia, ou só na primeira execução | `references/fases.md` §2 |
| A regra é trocada no código, e o teste dela continua verde | `references/testes.md` §4 |
| A escada diz que passou, e há degrau sem comando (código 3) | `SKILL.md` §4 |
| Um documento diz que a ferramenta bloqueia algo, e ela não bloqueia | `references/instrucoes.md` §4 |
| Um registro garante uma proteção que nenhum teste prova | `references/decisoes.md` §4 |

## 2. Passou aqui e falha lá

| Sintoma, como aparece | Onde está a saída |
| --- | --- |
| O degrau do banco passa num dia e falha no outro, sem mudança de código | `references/testes.md` §9 |
| A ponta a ponta falha ao acaso depois de horas com o servidor de desenvolvimento aberto | `references/testes.md` §9 |
| O teste passa sozinho e falha quando roda com os outros | `references/testes.md` §9 |
| Passa na máquina e falha no CI, que reclama de variável ou de serviço ausente | `references/testes.md` §8 |
| O build passa na máquina e quebra no CI ao consultar o banco | `references/ci.md` §1 |
| O artefato gerado na máquina difere do que o CI gera | `references/ci.md` §4 |
| O CI está vermelho "desde sempre", e ninguém mais olha | `references/ci.md` §5 |
| Funciona no ambiente local e falha em produção, com o mesmo código | `references/producao.md` §7 |
| Os testes de banco passam no banco de teste e falham no banco da plataforma | `references/variante-web.md` §6 |
| O comando ou a função que o agente lembra não existe na versão instalada | `references/instrucoes.md` §8 |

## 3. Fui a produção e não apareceu

| Sintoma, como aparece | Onde está a saída |
| --- | --- |
| O endereço da hospedagem mostra o novo, e o endereço que o dono usa mostra o antigo | `references/producao.md` §6 |
| A carga de dados terminou sem erro, e o site continua igual | `references/producao.md` §6 |
| O envio saiu, e a página não mudou | `references/producao.md` §5 |
| O CI ficou vermelho depois de um envio que implanta | `references/producao.md` §5 |
| O build novo falha, ou gera página incompleta, logo depois do envio | `references/producao.md` §2 |
| O histórico de migrações do ambiente remoto não bate com os arquivos | `references/producao.md` §3 |
| A migração de dado rodou em produção e não mudou nada, sem avisar | `references/dados.md` §8 |
| Ninguém consegue entrar como administrador em produção | `references/producao.md` §7 |
| O commit foi feito, e nada chegou ao ambiente remoto | `references/fechar.md` §4 |
| A permissão da sessão barrou um passo no meio da lista | `references/producao.md` §9 |

## 4. Os documentos se contradizem

| Sintoma, como aparece | Onde está a saída |
| --- | --- |
| O documento por assunto ou o leia-me descreve uma coisa, e o código faz outra | `references/decisoes.md` §5 |
| Uma regra, um registro ou a especificação manda uma coisa, e o código faz outra | `references/decisoes.md` §5 |
| Um registro antigo diz o contrário de um mais novo | `references/decisoes.md` §5 |
| Dois registros têm o mesmo número, ou o código cita um número que não existe | `references/decisoes.md` §7 |
| A especificação aprovada descreve um produto que já mudou | `references/especificacao.md` §7 |
| O estado diz que falta o que já foi feito | `references/retomada.md` §3 |
| O estado do ambiente remoto aparece em dois documentos, com datas diferentes | `references/retomada.md` §3 |
| Uma contagem escrita em prosa (testes, arquivos, itens) não bate com a saída de hoje | `references/retomada.md` §6 |
| Um trecho do plano contradiz a errata, ou o roteiro contradiz uma decisão posterior | `references/fases.md` §8 |
| Num projeto adotado, os documentos e o código se desmentem em vários pontos | `references/adocao.md` §6 |

## 5. Fiz o que não devia

Erro próprio se admite ao dono com a saída, se corrige e vira regra. O destino da regra está em
`references/retomada.md` §4.

| Sintoma, como aparece | Onde está a saída |
| --- | --- |
| O commit ou o envio saiu com um degrau falhando | `SKILL.md` §6, regra 3 |
| A busca não achou arquivos que existiam, e algo foi refeito | `SKILL.md` §6, regra 1 |
| O relato disse "passou" sobre o que não foi rodado | `SKILL.md` §6, regra 4 |
| O valor de uma chave colada pelo dono foi repetido ou gravado | `references/ambientes.md` §2 |
| Um comando rodou contra o ambiente remoto, e a intenção era o ambiente local | `references/ambientes.md` §1 |
| O banco local foi recriado, e o dono perdeu o que tinha cadastrado | `references/ambientes.md` §4 |
| Dados de exemplo, ou um arquivo que não devia, foram ao git ou ao ambiente remoto | `references/ambientes.md` §3 |
| Uma migração já aplicada fora do ambiente local foi editada | `references/dados.md` §8 |
| Uma decisão registrada foi desfeita ao "corrigir" um achado | `references/dono.md` §5 |
| Foi feito no ambiente remoto algo que não estava na lista | `references/dono.md` §7 |

Volte ao `SKILL.md`, §7.
