# Expandir e usar: em quantas etapas esta mudança entra sem derrubar o que está no ar?

Leia quando: a mudança é valor de enum, coluna obrigatória, renomear, trocar tipo ou remover; a
tabela tem muitas linhas; o banco não é Postgres (passos 1 e 2 do fluxo).
Não é aqui: o que vai dentro de cada arquivo (`references/escrever.md`); a subida
(`references/producao.md`).

## O mínimo

- Entre dois passos, o código antigo e o banco novo convivem. Toda etapa precisa valer para os dois.
- Acrescentar: o banco vai primeiro, o código depois. Remover: o código primeiro, o banco depois.
- Valor de enum: uma migration cria, a seguinte usa.
- Coluna obrigatória: nasce opcional, é preenchida, e só então é obrigada.
- Renomear e trocar tipo são "criar a nova, copiar, trocar a leitura, remover a antiga".

Conteúdo: 1. Enum 2. Coluna obrigatória 3. Renomear 4. Trocar tipo 5. Remover 6. Tabela grande
7. Em outros bancos

O que está "visto" aconteceu no sistema de origem. "Medido" rodou em Postgres 17.11. O resto é
receita corrente, marcada "a conferir": ensaie no banco descartável com dados parecidos.

## 1. Valor novo de enum (visto e medido)

| Passo | Banco | Código que está no ar |
| --- | --- | --- |
| 1 | Migration A: só `alter type ... add value if not exists` | o antigo: não conhece o valor, e nenhuma linha o usa |
| 2 | Migration B: o primeiro uso (regra, índice, função, dado) | o antigo |
| 3 | nada | o novo: passa a gravar e a ler o valor |

- **Por quê dois arquivos.** O valor só pode ser usado depois do commit da transação que o criou,
  e cada arquivo roda numa transação. No mesmo arquivo: `unsafe use of new value "audio" of enum
  type item_kind`. Os moldes são `assets/moldes/02-enum-valor-novo.sql` e
  `assets/moldes/03-enum-usar-o-valor.sql`.
- **O que falha e o que passa na mesma transação** (medido): `insert`, conversão, restrição,
  índice parcial e função em SQL falham; função em PL/pgSQL que cita o valor é criada, porque o
  corpo só é lido quando ela roda. Não aposte em qual uso passa: separe sempre.
- **Não tem volta.** `alter type ... drop value` responde "dropping an enum value is not
  implemented". Desfazer é recriar o tipo e reescrever cada coluna que o usa.
- **Renomear valor** (`rename value`) funciona (medido) e quebra o código antigo, que ainda grava
  o nome velho. Trate como renomear coluna (§3).
- **Texto com `check` no lugar de enum:** a mesma ordem. Uma migration troca o `check` para
  aceitar o valor; só depois alguém grava.
- **Antes do Postgres 12,** `add value` nem roda dentro de transação (pela documentação; não medido).

## 2. Coluna obrigatória (opcional vista; o resto medido em tabela pequena)

| Passo | Banco | Código |
| --- | --- | --- |
| 1 | Migration: a coluna nasce opcional | o antigo grava sem ela, e continua funcionando |
| 2 | nada | sobe o novo, que grava a coluna em toda linha nova |
| 3 | Migration ou carga: preenche as linhas antigas | o novo |
| 4 | Conferência no destino: `count(*) where coluna is null` dá 0 | o novo |
| 5 | Migration: `set not null` | o novo |

- **Direto como obrigatória, sem padrão:** em tabela com linhas falha com `column "source" of
  relation "items" contains null values` (medido). Em tabela vazia passa, e é por isso que o
  banco de teste não avisa. O molde é `assets/moldes/04-coluna-em-tres-passos.sql`.
- **Com valor padrão constante** os passos viram um, e o código antigo continua gravando. Só
  serve quando o padrão é a resposta certa também para as linhas futuras.
- **O passo 5 é opcional.** O sistema de origem parou no 1: a obrigatoriedade ficou no
  aplicativo, e uma linha criada pela metade continuou válida. Decida com o dono se o banco
  precisa garantir.
- **Preencher tabela grande** (a conferir): em lotes de tamanho fixo, por faixa de chave, cada
  lote na sua transação, fora da migration, com simulação antes (`references/producao.md` §5). Um
  `update` só segura as linhas travadas até o fim.
- **Obrigar em tabela grande.** `set not null` lê a tabela inteira com ela travada. A saída:
  `add constraint ... check (coluna is not null) not valid`; em outra transação, `validate
  constraint`; depois `set not null` e `drop constraint`. Medido: com a restrição validada, o
  Postgres 17 registra, em nível de depuração, que ela basta para provar que não há nulos, e não
  lê a tabela. Não medido em tabela grande.

## 3. Renomear coluna ou tabela (a conferir: o sistema de origem não renomeou)

Antes de tudo: o nome novo vale de 3 a 4 migrations e de 2 a 3 envios de código? Renomear só no
código, mantendo o nome no banco, quase sempre resolve.

| Passo | Banco | Código |
| --- | --- | --- |
| 1 | Cria a coluna nova, opcional | antigo |
| 2 | nada | grava nas duas, lê a antiga |
| 3 | Copia a antiga para a nova onde está vazia | o mesmo |
| 4 | nada | lê a nova, ainda grava nas duas |
| 5 | Se a antiga era obrigatória, deixa de ser | o mesmo |
| 6 | nada | para de gravar a antiga |
| 7 | Remove a antiga, com o dono (§5) | o mesmo |

`alter table ... rename column` num passo só derruba o código antigo no instante em que roda, e
o novo falha até ela rodar: não existe ordem que sirva aos dois.

## 4. Trocar o tipo de uma coluna (a conferir)

É renomear: coluna nova com o tipo novo, copiar convertendo, trocar a leitura, remover a antiga.
`alter column ... type` em um passo reescreve a tabela com ela travada na maioria das trocas, e
falha inteiro se uma linha não converte. Antes de copiar, conte as linhas que não convertem e
leve o número ao dono.

## 5. Remover coluna, tabela ou dado (a conferir)

| Passo | Quem | O quê |
| --- | --- | --- |
| 1 | Código | para de ler e de gravar; procure também consulta que lista todas as colunas |
| 2 | Espera | ao menos uma implantação inteira no ar, e a confirmação de que nenhum outro sistema lê |
| 3 | Dono | decide o destino do dado: cópia guardada ou perda aceita, por escrito |
| 4 | Banco | a migration que remove, com `destrutivo-de-proposito:` no cabeçalho |

- **A ordem inverte** porque o código antigo lê o que vai sumir. Banco primeiro derruba o que
  está no ar.
- **O conferidor acusa** `drop table`, `drop column`, `truncate` e `delete` sem `where`. A marca
  `destrutivo-de-proposito: <quem autorizou e por quê>` no cabeçalho troca a acusação por aviso.
- **Coluna sem uso pode ficar.** No sistema de origem ficou, anotada no documento do modelo.

## 6. Tabela grande: a trava (a conferir: o banco de origem era pequeno)

- **Migration que espera uma trava segura a fila atrás dela.** Ponha teto: `set local
  lock_timeout = '5s'` no começo. Estourou, ela falha sem ter mudado nada, e roda de novo depois.
- **Índice:** `create index concurrently` não trava a escrita e não roda dentro de transação
  (medido: "cannot run inside a transaction block"). Vai num arquivo só dele, com a transação da
  ferramenta desligada para ele (a conferir como se faz na sua).
- **Chave estrangeira e `check` novos:** `not valid` numa migration, `validate constraint` na
  seguinte. Na mesma transação, a trava do primeiro comando dura até o fim.

## 7. Em outros bancos (a conferir: nada disto rodou aqui)

| Assunto | Postgres | O que conferir fora dele |
| --- | --- | --- |
| Estrutura dentro de transação | sim: o arquivo que falha é desfeito inteiro | MySQL e Oracle confirmam a cada comando de estrutura: um arquivo pode parar pela metade. Um comando por migration |
| Enum | tipo próprio; valor só entra, não sai | MySQL: enum é da coluna e muda com `alter table`. SQLite e SQL Server: texto com `check` |
| Alterar tabela | quase tudo por `alter table` | SQLite: fora acrescentar, renomear e remover coluna, é criar a tabela nova, copiar e trocar |
| Função que roda como o dono | `security definer`, some ao redefinir | MySQL: `sql security`, com padrão diferente. Leia a definição depois de redefinir |
| Trava ao alterar | curta na maioria; longa ao reescrever | cada banco e versão tem a sua lista do que é feito sem travar |

A ordem das decisões não muda: expandir antes de usar, código antes de remover, um passo por vez.
