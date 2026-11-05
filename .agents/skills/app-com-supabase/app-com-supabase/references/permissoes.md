# Permissões: quem pode ler e escrever o quê, e como provar?

Leia quando: for criar tabela, policy ou função; ao revisar "quem vê o quê"; quando um visitante
ou um logado alcançar o que não devia (passo 3 do fluxo).
Não é aqui: a chave secreta (`references/clientes-e-chaves.md`); arquivos (`references/storage.md`).

## O mínimo

- Escreva a matriz por persona antes do SQL: ela é o contrato que os testes conferem.
- Barre em três lugares: privilégio de objeto, regra de linha (RLS) e guarda no aplicativo.
- Tabela nova nasce sem RLS e com tudo concedido a `anon` e `authenticated`: ligue a RLS e
  revogue antes de conceder, na migration que cria a tabela.
- Função com privilégio leva a guarda na primeira linha, `set search_path = ''` e a execução
  revogada de `public` e de `anon`.
- Prove no banco, com um teste por persona e um teste só de privilégios.

Conteúdo: 1. A matriz 2. Três barreiras 3. Privilégios 4. Policies 5. Funções 6. Conteúdo pago
7. Testes por persona 8. Teste de privilégios 9. Guarda no aplicativo

## 1. A matriz por persona

No Supabase há três papéis do banco e mais personas do que papéis: logado, assinante e admin são
todos `authenticated`, e o que os separa são as funções da §5.

| Família de dado | Visitante (`anon`) | Logado | Assinante | Admin | Chave secreta (`service_role`) |
| --- | --- | --- | --- | --- | --- |
| Vitrine publicada | lê | lê | lê | lê e altera | tudo |
| Conteúdo pago | nada | só o grátis | lê | lê e altera | tudo |
| Da própria pessoa | nada | lê e altera o seu | lê e altera o seu | nada dos outros | tudo |
| Só serviço (assinatura, lista de admins) | nada | lê o seu | lê o seu | não escreve | escreve |

Valide com o dono em frases, com o que a persona não consegue: "quem não assinou vê o título e
o resumo, e não o texto. Sigo assim, salvo aviso."

## 2. Três barreiras, sempre as três

| Barreira | O que decide | O que não segura |
| --- | --- | --- |
| Privilégio de objeto (`grant`) | se o papel pode executar aquele comando naquela tabela | não distingue linhas |
| Regra de linha (policy) | quais linhas o papel alcança | não filtra `truncate` |
| Guarda no aplicativo | quem é a pessoa, antes de validar ou ler | não existe para quem chama a API do banco direto |

A chave pública vai no navegador: qualquer pessoa chama a API do banco com ela, por fora do
aplicativo. Por isso a regra mora no banco, e a guarda existe para responder cedo e bem.

## 3. Privilégios: revogar antes de conceder

Visto no Supabase local: tabela nova em `public` nasce com `truncate` concedido a `anon` e com a
RLS desligada. Quem só soma `grant` não tira o que veio de fábrica.

| Faça | Detalhe |
| --- | --- |
| Revogue primeiro | `revoke all privileges on <objetos novos> from anon, authenticated;` |
| Conceda o mínimo | `anon`: só `select` no que é público. `authenticated`: os comandos que as policies decidem; só `select` nas tabelas de serviço. `service_role`: tudo |
| Revogue objeto a objeto | não mexa nos privilégios padrão do banco inteiro: muda o comportamento de tudo |
| Visão (view) | revogue tudo e conceda só `select`: visão atualizável escreve por baixo das policies |

Sem privilégio o papel recebe o erro `42501`, e não zero linhas.

## 4. Policies

Nome: `<tabela>_<quem>_<comando>`. Uma por comando e por papel.

| Caso | Policy |
| --- | --- |
| Leitura pública do publicado | `for select to anon, authenticated using (status = 'published')` |
| Tabela filha segue o pai | `using (exists (select 1 from public.items i where i.id = item_id and i.status = 'published'))` |
| Admin faz tudo | `for all to authenticated using ((select public.is_admin())) with check ((select public.is_admin()))` |
| Da própria pessoa | `using (user_id = (select auth.uid()))`, e a mesma condição em `with check` |
| Onde não deve haver acesso | nenhuma policy: sem ela, com a RLS ligada, ninguém passa |
| Escrita que cita outro registro | acrescente `exists (...)` do item citado: ele tem de ser visível para quem grava, ou o erro revela que existe |

- Embrulhe função em subconsulta, `(select public.is_admin())`: é avaliada uma vez por comando.
- Sempre diga `to <papéis>`: sem isso a policy vale para todo papel.
- Em `update`, `using` decide a linha alcançada e `with check` a linha gravada. Escreva os dois:
  omitido, o `with check` repete o `using`, e a regra de escrita deixa de estar à vista.

## 5. Funções de autorização e função com privilégio

Molde das duas: `assets/moldes/funcao-com-guarda.sql`.

| | Função de autorização | Função com privilégio |
| --- | --- | --- |
| Para quê | responder sim ou não: `is_admin()`, `has_plan()` | operação que atravessa as policies: publicar em vários passos |
| Atributos | `language sql stable security definer set search_path = ''` | `security definer set search_path = ''`; a guarda é a primeira instrução |
| Identidade | não recebe por argumento: usa `auth.uid()` | a mesma regra: quem chama não escolhe quem é |
| Execução | todos os papéis; para o visitante responde falso | `revoke execute ... from public, anon`; `grant` a `authenticated` e `service_role` |
| Quantas | duas ou três; toda policy usa só elas | uma por operação |

- **Caminho de busca vazio** impede que um objeto de mesmo nome, em outro esquema, seja chamado
  dentro de função que roda com direitos elevados. Escreva todo objeto com o esquema.
- **Revogar só de `public` não basta.** Visto no Supabase local: função nova já nasce executável
  por `anon` e `authenticated`, e `anon` continua executando depois de `revoke ... from public`.
- **`service_role` executa e não tem identidade:** `auth.uid()` é nulo e a guarda recusa. É de
  propósito, para a chave secreta não virar atalho. Use a sessão de um admin.

## 6. Como o conteúdo pago é modelado

1. O texto pago mora em `item_bodies`, fora da vitrine. `anon` não tem nem `select` nela.
2. A policy de leitura pergunta ao item: publicado e (grátis ou `has_plan()`).
3. `has_plan()` lê o espelho da assinatura, que só a chave secreta escreve. A tabela completa e
   o webhook que a mantém estão na skill irmã `assinatura-com-stripe`.
4. No aplicativo, uma função só lê o texto pago, chamada depois da guarda. Para quem não pode
   ela devolve nulo: o texto não vai escondido na página, em propriedade de componente nem na
   carga de dados que o framework envia junto.

## 7. Testes por persona

Molde: `assets/moldes/teste-por-persona.sql`. Arquivos SQL com pgTAP em `supabase/tests/`,
numerados, um por persona, cada um dentro de `begin` e `rollback`.

| Peça | Como |
| --- | --- |
| Virar visitante | `set local role anon;` e `select set_config('request.jwt.claims', '', true);` |
| Virar uma pessoa | `set local role authenticated;` e as declarações com `"sub"` igual ao id dela |
| Voltar | `reset role;` devolve a quem abriu a transação, que ignora as policies |
| Dados do teste | os próprios, numa faixa de ids que não colide com a do seed; filtre por eles |

| O bloqueio vem de | O que acontece | Como afirmar |
| --- | --- | --- |
| Policy, em `select`, `update` e `delete` | nenhum erro: zero linhas | `is_empty`, ou contagem |
| Policy, em `insert` | erro `42501` | `throws_ok` com o código |
| Falta de privilégio; guarda de função | erro `42501` | `throws_ok` com o código |
| `check`, unicidade | `23514`, `23505` | `throws_ok` com o código |

Cubra, por persona: o que lê, o que não vê, o que grava, o que não grava e a autopromoção.

## 8. Teste só de privilégios

Molde: `assets/moldes/teste-de-privilegios.sql`. Quatro afirmações genéricas varrem `public`:
toda tabela com RLS, nenhum `truncate` para `anon` e `authenticated`, visitante sem escrita, toda
função `security definer` com caminho de busca. Pegam a tabela que alguém criar depois. As
outras fixam a lista exata por tabela e por papel, com `table_privs_are`.

## 9. Guarda no aplicativo

Molde: bloco de guardas de `assets/moldes/login-por-codigo.ts`.

- `requireUser()` ou `requireAdmin()` é a primeira instrução de toda ação de servidor e de toda
  leitura por pessoa. Se vier depois da validação, a mensagem de erro já conta algo a quem não
  devia saber.
- Em área de admin, a guarda vai na casca, em cada página e em cada função de leitura: a casca
  sozinha não protege página nem ação chamada direto.
- Logado que não é admin recebe "não encontrado", não "proibido": a área fica invisível.
- "É admin?" com erro do banco responde não. Erro não abre área restrita.

## O que evitar

- **"Funciona quando uso a chave secreta."** A policy está errada e a chave a ignora. Corrija a
  policy e teste com a sessão da pessoa.
- **Policy `using (true)` em tabela que ganhou coluna que nem todos podem ver.** Reveja.
- **Passar o id da pessoa por argumento a uma função com privilégio.** Quem chama escolhe quem é.
- **Afirmar bloqueio sem trocar de papel.** Quem abre a transação ignora as policies: o teste
  passa e não prova nada.

## Pronto quando

- [ ] Cada persona da matriz tem teste do que lê, do que grava e do que não consegue.
- [ ] Toda tabela e toda função nova está no teste só de privilégios.
- [ ] Os testes passam no banco local recriado do zero.
