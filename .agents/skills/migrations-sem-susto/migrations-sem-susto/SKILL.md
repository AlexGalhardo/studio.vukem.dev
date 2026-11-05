---
name: migrations-sem-susto
description: Muda o banco de dados de um sistema que já está no ar sem quebrar produção, em qualquer banco relacional com migrations versionadas. Escreve a migration que só acrescenta, com cabeçalho que diz o porquê; separa expandir e usar (valor de enum, coluna obrigatória, renomear e remover em etapas); redefine função e política repetindo as proteções; monta a subida na ordem banco, dados, código; simula antes de escrever dados; confere o banco depois e diz o que não tem volta. Traz moldes em Postgres, roteiro de subida e um conferidor que só lê a pasta de migrations e o git. Use sempre que o usuário disser "preciso mudar o banco", "adiciona uma coluna", "cria uma migration", "quero renomear essa coluna", "posso apagar essa tabela?", "em que ordem eu subo isso?", "o deploy quebrou depois da migration", "dá para desfazer?" ou "aplica em produção", mesmo sem dizer migration. Não use para desenhar o modelo do zero, cópia de segurança, troca de banco, nem para o que é próprio do Supabase (skill irmã app-com-supabase).
---

# Migrations sem susto

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do projeto do dono; `<migrations>`, a pasta
onde o projeto guarda as migrations.

- **Só acrescentar.** Toda mudança de banco é um arquivo versionado novo, com um cabeçalho que diz
  o porquê. Arquivo que já saiu da máquina não muda.
- **Expandir primeiro, usar depois.** A estrutura que o código novo exige chega ao banco num passo
  anterior, que o código antigo aguenta.
- **Banco, dados, código.** Nessa ordem, com duas perguntas respondidas antes: o código novo
  funciona com o banco antigo? O código antigo funciona com o banco novo?
- **Simular e ler antes de escrever dados.** O que pode sobrar na simulação é escrito antes de
  rodar. Apareceu outra coisa: parar.
- **Aplicar em produção é decisão do dono.** O agente prepara, simula e confere. Só aplica com o
  pedido explícito dele, para aquela lista de passos.

Funciona porque, entre um passo e o seguinte, o sistema fica no ar com metade da mudança: cada
passo precisa deixar o conjunto funcionando sozinho. O teste antes de agir: sei o que está aplicado
em produção, o que este passo muda e o que acontece se eu parar logo depois dele?

Saiu de um sistema em produção com Postgres e 11 migrations, que só acrescentou: par de enum,
colunas opcionais, função e política redefinidas, subida em três passos com simulação. Os moldes
de `assets/moldes/` rodaram em ordem, do zero, num Postgres 17.11 descartável, e o que as fichas
marcam "medido" foi medido nele. O que o sistema de origem não fez (renomear, trocar tipo, remover,
preencher tabela grande, voltar atrás) é receita marcada "a conferir": ensaie antes. Em outro
banco, copie a ordem das decisões e confira a sintaxe: `references/expandir-e-usar.md` §7. O que é
próprio do Supabase está na skill irmã `app-com-supabase`.

## Preparar

1. Leia o que o projeto já tem: a ferramenta de migrations e a pasta dela, o comando que recria o
   banco do zero, os testes de banco e o documento que diz o que está aplicado em cada ambiente.
   Sem esse documento, escreva a linha de estado antes de mexer: `references/producao.md` §6.
2. Rode o conferidor, que só lê a pasta e o git:

   ```bash
   python3 <skill>/scripts/conferir.py <migrations> --base <ref do que já foi aplicado>
   # → "acusa:", "aviso:", "ok:", "não conferi:". Saída 0 limpo, 1 acusou, 2 uso, 3 incompleto
   ```

3. Pergunte ao dono o que o código não diz (seção "Pare e pergunte ao dono").

- **Requisitos:** Python 3.8 ou mais novo e git, só para o conferidor (rodou em macOS, Python 3.14).
- **`--base`** é o ref do git que corresponde a produção: o ramo que implanta, uma tag, um commit.
  Sem ele, o conferidor acusa todo arquivo mexido depois do commit em que entrou.

## Que mudança é esta

| Mudança | Em quantos passos | Leia |
| --- | --- | --- |
| Tabela, índice ou coluna opcional novos | 1 migration | `references/escrever.md` |
| Valor novo de enum | 2 migrations: uma cria, a seguinte usa | `references/expandir-e-usar.md` §1 |
| Coluna obrigatória | 3 migrations e 1 envio de código no meio | a mesma ficha, §2 |
| Renomear coluna ou tabela; trocar tipo | 3 a 4 migrations e 2 a 3 envios, ou não renomear | §3 e §4 |
| Remover coluna, tabela ou dado | código primeiro, banco depois, com o dono | §5 |
| Redefinir função, política ou visão | 1 migration com a definição inteira | `references/escrever.md` §4 |
| Dado que produção precisa para funcionar | 1 migration própria, que avisa | `references/escrever.md` §5 |
| Levar o que está pronto a produção | o roteiro, na ordem | `references/producao.md` |
| Algo quebrou depois de aplicar | não edite: outra migration | `references/testes-e-volta.md` §6 |

## Fluxo

### 1. Classifique a mudança e diga o tamanho dela

Ache a linha na tabela acima. Antes de escrever, diga ao dono quantas migrations e quantos envios
de código a mudança pede, o que não tem volta e o que só ele decide.
**Confira:** o estado de produção foi lido agora, do arquivo no disco, e não da memória da sessão.
**Pronto quando:** a lista de passos está escrita, e cada passo deixa o sistema funcionando.

### 2. Escreva a migration

Crie o arquivo pela ferramenta do projeto, que põe a versão no nome. Parta do molde da mudança,
em `assets/moldes/` (tabela "Arquivos"), e siga `references/escrever.md`.
**Confira:** `conferir.py` sai com 0, ou cada "acusa:" tem a resposta escrita no cabeçalho.
**Pronto quando:** o cabeçalho diz o que faz, por quê, o que substitui e o que não tem volta.

### 3. Aplique do zero e teste

Recrie o banco descartável: todas as migrations em ordem, os dados de exemplo, os testes de banco.
Gere de novo os tipos ou o cliente do banco e commite junto: `references/testes-e-volta.md` §1 a §3.
**Confira:** a migration nova também passa sobre um banco que já tem linhas (§5 da ficha).
**Pronto quando:** do zero e sobre dados dá verde, e o arquivo gerado sai sem diferença.

### 4. Responda as duas perguntas e preencha o roteiro

Copie `assets/moldes/roteiro-de-subida.md` e escreva a resposta de cada pergunta com a evidência.
Se o código antigo não funciona com o banco novo, volte ao passo 1: `references/producao.md` §1.
**Confira:** a ordem é banco, dados, código; em remoção, o código vai primeiro.
**Pronto quando:** o roteiro diz o que pode sobrar na simulação e em que linha parar.

### 5. Entregue o roteiro e espere o pedido

O dono lê a lista inteira. Um sim vale para aquela lista, e passo novo pede lista nova.
**Confira:** tudo o que vai subir está commitado, e o envio de código ainda não saiu.
**Pronto quando:** o dono pediu a aplicação com a lista na frente.

### 6. Suba na ordem: banco, dados, código

Banco: compare o histórico com os arquivos e aplique uma migration por vez. Dados: simule, leia
linha a linha e só então escreva. Código: envie e espere implantar: `references/producao.md` §2 a §5.
**Confira:** depois de cada passo, o sistema que está no ar continua respondendo.
**Pronto quando:** os três passos terminaram, ou a subida parou num deles com o motivo escrito.

### 7. Confira no banco e registre

Consulte se o objeto existe, as proteções da função e os privilégios. Compare o histórico com os
arquivos e registre o que está aplicado, onde e desde quando: `references/producao.md` §6.
**Confira:** como visitante, no endereço que o dono usa, a mudança aparece.
**Pronto quando:** o estado escrito bate com o banco, e a divergência que sobrou tem dono e data.

## Regras inegociáveis

1. **Migration que saiu da máquina não se edita.** A correção é um arquivo novo, que diz o que
   substitui. Se não, dois bancos diferentes ficam com o mesmo histórico.
2. **Uma migration por mudança, com a versão posta pela ferramenta.** Se não, o erro de uma parte
   derruba a outra, e duas pessoas criam a mesma versão.
3. **O valor novo de enum e o primeiro uso dele ficam em migrations separadas.** Se não, o arquivo
   falha inteiro: o valor só existe depois do commit.
4. **Coluna nova nasce opcional.** O código antigo continua no ar e grava sem ela. Se nascer
   obrigatória, toda gravação dele falha.
5. **Ao redefinir função, repita `security definer` e `search_path`.** `create or replace` guarda
   só o dono e os privilégios. Se não, ela passa a rodar com o privilégio de quem chama.
6. **Nada destrutivo sem o dono.** `drop`, `truncate` e `delete` sem `where` não têm simulação
   que devolva o dado.
7. **Nada é aplicado em produção sem pedido explícito.** Ler o ambiente remoto também é ação: só
   por comando que não tem como escrever.
8. **Depois de aplicar, confira e registre.** Se não, a próxima sessão parte de um estado suposto.

## Pare e pergunte ao dono

- **Só o dono decide:** aplicar migration em produção; remover coluna, tabela ou dado; aceitar o
  que não tem volta; a hora da subida; restaurar cópia de segurança; acertar o histórico remoto.
- **Pergunte antes:** quantas linhas têm as tabelas tocadas; se há cópia de segurança recente e
  quem a restaura; se outro sistema lê o mesmo banco; qual ref do git corresponde a produção.
- **Pare se:** a simulação mostra linha fora do previsto; o histórico remoto não bate com os
  arquivos; uma migration falhou no meio; o conferidor acusa como alterado um arquivo já aplicado.

## Armadilhas já vistas

- **"unsafe use of new value" ao aplicar.** O valor de enum foi criado e usado no mesmo arquivo:
  `references/expandir-e-usar.md` §1.
- **A função "perdeu a proteção" depois de uma mudança de uma linha.** Foi redefinida sem repetir
  os atributos: `references/escrever.md` §4.
- **A implantação do código novo falhou, ou as páginas saíram incompletas.** O código subiu antes
  do banco ou antes dos dados, e a montagem das páginas consulta o banco: `references/producao.md`
  §1 e §2.
- **A ferramenta quer reaplicar o que já está no banco.** A migration foi aplicada por outro
  canal, que gravou a hora no lugar da versão: `references/producao.md` §6.
- **A migration avisou e ninguém viu.** O aviso não aparece em todo canal: `references/producao.md` §3.
- **O teste de banco passa hoje e falha perto da meia-noite.** Datas relativas nos dados de exemplo
  e no teste: `references/testes-e-volta.md` §4.
- **Passou do zero e falhou com "contains null values".** O banco de teste estava vazio:
  `references/testes-e-volta.md` §5.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/escrever.md` | o arquivo, o cabeçalho, editar ou escrever outra, redefinir função, dado em migration | passo 2 |
| `references/expandir-e-usar.md` | receitas: enum, coluna obrigatória, renomear, trocar tipo, remover, tabela grande, outros bancos | passos 1 e 2 |
| `references/producao.md` | as duas perguntas, a ordem, aplicar, simular, conferir, histórico e estado | passos 4 a 7 |
| `references/testes-e-volta.md` | banco do zero, testes em transação, tipos no CI, datas relativas, o que tem volta | passo 3; algo quebrou |
| `assets/moldes/01-migration-com-cabecalho.sql` | tipo, tabela, privilégios e função com as proteções | passo 2 |
| `assets/moldes/02-enum-valor-novo.sql`, `assets/moldes/03-enum-usar-o-valor.sql` | o par de enum: uma cria, a seguinte usa | valor novo de enum |
| `assets/moldes/04-coluna-em-tres-passos.sql` | opcional, preencher, obrigar | coluna obrigatória |
| `assets/moldes/05-redefinir-funcao.sql` | a definição inteira, com o que se repete e a consulta de conferência | redefinir função |
| `assets/moldes/roteiro-de-subida.md` | a lista que o dono autoriza, para preencher | passo 4 |
| `scripts/conferir.py` | cinco conferências na pasta de migrations e no git; `--help` | antes de escrever e antes de subir |
