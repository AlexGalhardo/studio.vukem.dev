# CI: o que o job de ponta a ponta sobe, em que ordem, e o que ele guarda quando falha?

Leia quando: for pôr a suíte no CI ou entender um vermelho que só acontece lá (passo 8 do fluxo).
Não é aqui: rodar na máquina e diagnosticar teste instável (`references/rodar-e-diagnosticar.md`).

## O mínimo

- O job sobe o banco local com as migrations e os dados de exemplo, faz o build, sobe o servidor de
  produção e roda a suíte no desktop e no celular.
- Nenhum segredo do repositório: o endereço e as chaves são os da stack local, lidos dela.
- No CI, `.only` é proibido, a repetição vai até 2, o rastro é gravado na primeira repetição e o
  relatório é guardado só quando falha.
- É o job mais caro. Ele roda ao lado de um job rápido (lint, tipos, testes de unidade), não no
  lugar dele.

Conteúdo: 1. Os passos 2. Nenhum segredo 3. O que muda no CI 4. Quando fica vermelho 5. Onde o job
se encaixa 6. Outro serviço de CI

## 1. Os passos, na ordem

Molde: `assets/moldes/ci-ponta-a-ponta.yml`, para o GitHub Actions.

| Passo | Por quê | Se faltar |
| --- | --- | --- |
| Código, linguagem na versão escrita no arquivo do projeto, dependências com o arquivo de trava congelado | a mesma versão da máquina e da produção | "passa na minha máquina" |
| Banco local, com as migrations do zero e os dados de exemplo | as personas vêm dos dados de exemplo, e o banco tem de nascer só do repositório | o preparo para em "sem código para…" e nenhum teste roda |
| Variáveis lidas da stack que subiu | o aplicativo, o preparo e o build leem os mesmos nomes | a trava para em "faltam URL_DO_BANCO…" |
| Navegador, com as bibliotecas do sistema | só o que os projetos usam (no molde, o Chromium) | o Playwright para pedindo a instalação |
| Build de produção, em passo próprio | build quebrado aparece como "Build", não como teste que estourou o tempo | o servidor de produção não sobe |
| Ponta a ponta | com `CI=true` a configuração sobe o servidor de produção e não faz o build de novo | |
| Relatório, só quando falha, por 7 dias | o rastro e o relatório em HTML são o que há para olhar depois | o vermelho vira "roda de novo para ver" |

O job tem limite de 30 minutos: um servidor que não sobe não segura a fila.

Não tire a caixa de e-mail local da stack: o teste de login lê o código nela.

## 2. Nenhum segredo do repositório

- As chaves da stack local nascem com ela. O job as lê do comando de status e as grava em dois
  lugares: no ambiente do job e no arquivo de ambiente que a configuração do Playwright carrega.
- O `tee` do molde grava sem imprimir no registro. O `test -n` falha o passo se a stack não
  devolveu o endereço, em vez de deixar o erro aparecer três passos depois.
- Chave de serviço externo (pagamento, envio de e-mail) não entra no job. Os testes afirmam o aviso
  tratado que aparece sem ela (`references/personas-e-sessoes.md` §5).
- "Põe a chave de produção nos segredos para testar de verdade": não. As travas recusam endereço
  remoto, e a suíte cria contas e dados.

## 3. O que muda no CI

A configuração lê `CI`, que o GitHub Actions já define como `true`; o molde repete a variável no
passo para deixar a dependência à vista.

| Opção | Na máquina | No CI | Por quê |
| --- | --- | --- | --- |
| `forbidOnly` | desligado | ligado | um `.only` esquecido roda um teste e pinta o job de verde |
| `retries` | 0 | 2 | a instabilidade aparece para quem escreve; no CI ela não trava o envio |
| `trace` | `on-first-retry` | `on-first-retry` | só grava quando repete: toda falha repetida deixa um rastro |
| `reporter` | `list` | `github` e `html` | anotações no pedido de merge e o relatório que o job guarda |
| Comando do servidor | build e servidor | só o servidor | o build já rodou no passo dele |

Quantos processos o Playwright abre por padrão num executor de CI: a conferir na documentação do
Playwright. Se o job ficar instável por falta de memória, fixe `workers` na configuração e anote o
motivo no comentário.

## 4. Quando fica vermelho

1. Baixe o artefato do job. Abra o relatório com `npx playwright show-report <pasta>` e o rastro
   com `npx playwright show-trace <trace.zip>`.
2. Siga o procedimento de `references/rodar-e-diagnosticar.md` §4: primeiro separe falha de
   asserção de conexão derrubada e de tempo estourado.
3. **Todos falharam de uma vez:** olhe o preparo. Banco que não subiu, dados de exemplo que
   mudaram ou variável vazia derrubam a geração das sessões.
4. **Passou só na repetição:** o relatório marca o teste como instável. Ele entra na lista de
   consertos. Quem quer tolerância zero acrescenta `--fail-on-flaky-tests` ao comando.
5. **Vermelho "que sempre foi assim"** ensina a ignorar o sinal. Conserte, ou tire o teste com o
   motivo registrado.

## 5. Onde o job se encaixa

No sistema de origem o workflow tem três jobs em paralelo:

| Job | Roda | Limite |
| --- | --- | --- |
| Rápido | lint, formatação, tipos e testes de unidade | 15 min |
| Banco | migrations do zero, dados de exemplo e testes de banco | 15 min |
| Ponta a ponta | o molde desta skill | 30 min |

- **Retorno rápido:** erro de tipo aparece sem esperar contêiner nem navegador.
- **Diagnóstico pelo nome do job:** vermelho no banco é migration ou permissão; vermelho no ponta a
  ponta é comportamento.
- **O build mora onde há banco.** Se o build consulta o banco para montar páginas, ele só funciona
  no job que sobe a stack. Se não consulta, rode-o também no job rápido.
- **O CI cresce com o projeto.** Este job entra quando existe tela para testar, não no primeiro
  dia.
- **Cancele a execução anterior da mesma branch** com o grupo de concorrência do cabeçalho do
  molde: dois envios seguidos não disputam a fila.

## 6. Outro serviço de CI

A ordem é a mesma. Muda a sintaxe de três coisas: como subir o banco (contêiner de serviço ou
comando), como passar variável de um passo para o seguinte, e como guardar um arquivo quando o job
falha. O molde só rodou, na forma de origem, no GitHub Actions.

## O que evitar

- Ponta a ponta contra o servidor de desenvolvimento no CI: esconde erro de build e é lento.
- Guardar o relatório sempre: gasta armazenamento, e ninguém abre relatório de job verde.
- Aumentar `retries` até o job ficar verde.
- Instalar todos os navegadores quando os projetos usam um.

## Pronto quando

- Um envio com `.only` num teste deixa o job vermelho.
- Um teste quebrado de propósito deixa o relatório para baixar, e o rastro abre.
- O workflow não cita `secrets.` em nenhum passo deste job.
