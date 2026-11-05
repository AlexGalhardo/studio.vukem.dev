# Dados e migrations: o que se guarda e como o banco muda sem quebrar?

Leia quando: for desenhar tabelas, escrever ou revisar uma migration, acrescentar valor de enum ou
gerar os tipos (passos 1 e 2 do fluxo).
Não é aqui: quem pode ler e escrever (`references/permissoes.md`); aplicar no projeto remoto
(`references/producao.md` §3). Migration em detalhe (trocar tipo de coluna, coluna obrigatória em
tabela cheia, volta atrás) é assunto da skill irmã `migrations-sem-susto`, ainda por sair: aqui
fica só o que é do Supabase.

## O mínimo

- Desenhe o modelo e a matriz de permissões antes da primeira tela: tela muda barato, tabela com
  dado dentro muda caro, e regra de acesso que entra depois entra como remendo.
- Toda mudança de banco é um arquivo em `supabase/migrations/`. Nada é criado pelo painel.
- Migration só acrescenta, e é uma por mudança. Corrigir uma já aplicada é escrever outra.
- Valor novo de enum vai numa migration; o uso dele, na seguinte.
- Os tipos do aplicativo são gerados do banco, pelo mesmo comando na máquina e no CI.

Conteúdo: 1. O modelo 2. Convenções 3. A migration 4. Enum 5. Dado dentro de migration
6. Tipos gerados 7. Banco do zero

## 1. O modelo antes das telas

1. Liste os substantivos do produto: o que se cadastra, o que se vende, quem usa, o que se mede.
2. De cada um: campo, tipo, obrigatório, limite e para onde aponta cada chave.
3. Escreva a matriz de permissões na mesma página (`references/permissoes.md` §1) e confira que
   todo dado citado numa tela existe no modelo.

| Decisão | Faça | Porque |
| --- | --- | --- |
| O que é vendido ou restrito | tabela própria (`item_bodies`), separada da vitrine (`items`) | consulta que pede tudo da vitrine não leva o que é pago |
| Quem usa o produto | chave estrangeira para `auth.users (id)` com `on delete cascade`; dados da pessoa em `profiles`, com a mesma chave | o esquema `auth` é do Supabase: não crie coluna nem tabela nele |
| Estado decidido por terceiro (pagamento) | tabela-espelho, uma linha por pessoa, escrita só pela chave secreta | se a tela gravasse, um erro de regra daria o plano a quem não pagou |
| Quem é admin | tabela `admins`, escrita só pela chave secreta | cabe em teste por persona e é lida por uma função só |
| O nível de acesso | atributo do item (`access`), não da pessoa | a pergunta vira "esta pessoa pode ler este item?", respondida num lugar |

Com um banco que já tem gente: não altere nem apague o que existe, dê prefixo ao que é novo e pare
para perguntar ao dono antes de tocar em tabela antiga.

## 2. Convenções, decididas uma vez

| Convenção | Regra e motivo |
| --- | --- |
| Identificador e datas | `uuid` com `gen_random_uuid()`; `timestamptz` com `default now()`. "Hoje" no banco é UTC: escreva isso onde a data vira texto na tela |
| Teto no banco | `check` de tamanho em todo texto e em todo `jsonb`: sem teto, qualquer logado grava um registro enorme |
| Nome de restrição | previsível (`items_slug_key`, `items_title_check`): o aplicativo reconhece o erro pelo nome e responde com uma frase boa |
| Lista de valores | `check (col in (...))` troca de lista numa migration; enum não perde valor depois de criado (§4). Lista que muda toda semana fica no aplicativo |
| Apagar o pai | decida o destino de cada filho (`cascade`, `restrict`, `set null`) e escreva o motivo quando não é o óbvio |
| Comentário | `comment on table` em toda tabela: é o que aparece para quem abre o banco sem o repositório |

## 3. A migration

```bash
supabase migration new <assunto>   # cria supabase/migrations/<carimbo>_<assunto>.sql
```

- **Cabeçalho que explica.** O arquivo abre dizendo o que faz, por quê e o que deixa de fora de
  propósito. Quem aplica em produção lê isso, não o diff.
- **Só acrescenta.** Não apague nem altere estrutura que guarda dado; coluna nova aceita nulo ou
  tem padrão. Se não, o código que está no ar quebra entre a migration e a implantação.
- **Uma por mudança.** Arquivo que mistura dois assuntos não pode ser aplicado pela metade.
- **Tabela nova sai completa:** `enable row level security`, policies, `revoke` e `grant` na mesma
  migration que a cria. Parta de `assets/moldes/tabela-nova.sql`.
- **Regra pode ser trocada, em migration nova** que diz o que havia e o que passa a valer:
  `drop policy` e `create policy`, ou `create or replace function`.
- **`create or replace function` mantém dono e privilégios, e não mantém os atributos.** Repita
  `security definer` e `set search_path = ''` na definição nova: sem repetir, os dois somem (visto
  no banco local). O conferidor acusa esse caso.
- **Editar no lugar** só enquanto o arquivo não saiu do ambiente local. Depois de aplicado em
  outro banco, editar cria dois bancos diferentes com o mesmo histórico.

## 4. Enum: valor novo e uso em migrations separadas

Um valor recém-acrescentado a um enum não pode ser usado na transação que o cria; o Postgres
recusa com "unsafe use of new value". Valor e uso no mesmo arquivo falharam no projeto de origem.

1. Migration A: só `alter type public.<tipo> add value if not exists '<valor>';`. O cabeçalho diz
   por que é só isso e qual é a migration seguinte.
2. Migration B, com o carimbo seguinte: o que usa o valor (padrão de coluna, função, dado).
3. Registre: valor de enum não sai depois; voltar atrás pede recriar o tipo.

A mesma restrição dá a ordem de ida a produção: o aplicativo novo valida entradas contra os
valores gerados do banco e falha num banco sem o valor; o antigo ignora o que não conhece.

## 5. Dado dentro de migration

| Dado | Onde fica | Regra |
| --- | --- | --- |
| Vocabulário que o produto precisa para funcionar | migration própria | idempotente (`on conflict do nothing`) e com `raise warning` quando não pôde fazer o que devia: migration que falha em silêncio deixa produção sem o dado |
| Dados de exemplo e contas de teste | `supabase/seed.sql` | só no banco local. Só insere linhas: tabela criada no seed entraria nos tipos gerados |
| O primeiro admin | passo à parte, do dono | a conta dele só existe depois do primeiro login: a migration roda antes |

`supabase db push` tem a opção `--include-seed`. Não a use contra o projeto remoto: criaria em
produção contas de teste e dados falsos.

## 6. Tipos gerados

```bash
supabase gen types typescript --db-url <URL do banco local> --schema public > types/database.types.ts
```

- **O arquivo é gerado, nunca escrito.** Renomear uma coluna quebra a compilação nos pontos certos.
- **O aplicativo importa por um módulo só**, que reexporta os apelidos úteis (linha, linha para
  inserir, valores de enum). Trocar o gerador mexe em um arquivo.
- **No CI:** suba o banco, aplique as migrations, gere para um arquivo temporário, passe o mesmo
  formatador e compare com o arquivo commitado. Diferença falha, com a instrução do que rodar.
- **Mesmo comando, mesmos argumentos, na máquina e no CI.** No projeto de origem dois caminhos de
  geração davam saídas diferentes, e a primeira regeneração legítima quebraria o CI.
- O gerador marca coluna de visão como anulável, e `check` não vira tipo: valide no aplicativo.

## 7. Banco do zero a cada verificação

| Comando | O que faz | Cuidado |
| --- | --- | --- |
| `supabase start` | sobe o Supabase local (Postgres, Auth, Storage, caixa de e-mail) | pede Docker |
| `supabase db reset` | recria o banco local: todas as migrations em ordem e o seed | apaga o que o dono cadastrou à mão: avise antes |
| `supabase test db` | roda os arquivos pgTAP de `supabase/tests/` | passa só no banco local |

Aplicar por cima esconde dependência de ordem: a prova de que as migrations funcionam é subir do
zero. `supabase db reset --linked` recria o projeto remoto: não rode, é perda de dados.

## O que evitar

- **Criar tabela pelo painel "só para testar".** O banco local e o remoto deixam de bater, e a
  tabela nasce sem RLS e com tudo concedido.
- **Guardar o papel da pessoa numa coluna que ela mesma edita.** Vira autopromoção. Papel mora em
  tabela escrita só pela chave secreta.
- **Editar uma migration já aplicada no remoto.** Pare e escreva outra.
- **Rodar de novo o teste até passar.** Data relativa que colide com o seed falha um dia sim e
  outro não: recrie o banco e corrija a data.

## Pronto quando

- [ ] O modelo e a matriz estão escritos, e o dono confirmou o que cada persona vê.
- [ ] O banco local sobe do zero, com todas as migrations em ordem, sem erro.
- [ ] Os tipos gerados estão commitados, e o CI compara.
- [ ] `scripts/conferir.py` não acusa tabela sem RLS nem sem `revoke`.
