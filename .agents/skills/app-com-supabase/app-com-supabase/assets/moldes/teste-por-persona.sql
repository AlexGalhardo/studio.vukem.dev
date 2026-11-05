-- Molde: teste de permissão dentro do banco (pgTAP), uma persona por bloco.
-- Rodou no Supabase local (Postgres 17, pgTAP 1.3.3) sobre funcao-com-guarda.sql e
-- tabela-nova.sql: 11 de 11. No projeto, um arquivo por persona; rode com `supabase test db`.
begin;
select plan(11);

-- Dados próprios, numa faixa de ids (f0…, f1…) que não colide com a dos dados de exemplo.
-- Quem abre a transação ignora as policies: é o equivalente da chave secreta.
insert into auth.users (id) values
  ('f0000000-0000-4000-8000-000000000001'),   -- admin
  ('f0000000-0000-4000-8000-000000000002'),   -- logado, sem plano
  ('f0000000-0000-4000-8000-000000000003');   -- assinante
insert into public.admins (user_id) values ('f0000000-0000-4000-8000-000000000001');
insert into public.subscriptions (user_id, status)
  values ('f0000000-0000-4000-8000-000000000003', 'active');
insert into public.items (id, slug, title, status, access) values
  ('f1000000-0000-4000-8000-000000000001', 'teste-pago', 'Pago', 'published', 'paid'),
  ('f1000000-0000-4000-8000-000000000002', 'teste-rascunho', 'Rascunho', 'draft', 'paid');
insert into public.item_bodies (item_id, body) values
  ('f1000000-0000-4000-8000-000000000001', 'corpo pago do teste'),
  ('f1000000-0000-4000-8000-000000000002', 'corpo do rascunho');

-- Visitante: o papel sem sessão, com as declarações do token vazias.
set local role anon;
select set_config('request.jwt.claims', '', true);
select is((select count(*) from public.items where slug like 'teste-%'), 1::bigint,
  'visitante vê o publicado e não vê o rascunho');
select throws_ok($$select 1 from public.item_bodies$$, '42501', null,
  'visitante não tem nem leitura no texto pago (privilégio)');
select throws_ok(
  $$select public.publish_item('f1000000-0000-4000-8000-000000000002')$$, '42501', null,
  'visitante não executa a função com privilégio');

-- Logado sem plano: ao trocar de persona, troque o papel e as declarações.
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"f0000000-0000-4000-8000-000000000002","role":"authenticated"}', true);
-- Bloqueio por policy se prova pelo efeito (zero linhas); por privilégio ou guarda, pelo erro.
select is_empty($$select 1 from public.item_bodies where item_id::text like 'f1%'$$,
  'logado sem plano não lê o texto pago (0 linhas, sem erro)');
select is_empty(
  $$with u as (update public.items set title = 'x' where slug = 'teste-pago' returning 1)
    select * from u$$,
  'logado não altera item (0 linhas, sem erro)');
select throws_ok(
  $$insert into public.subscriptions (user_id, status)
    values ('f0000000-0000-4000-8000-000000000002', 'active')$$,
  '42501', null, 'autopromoção: logado não se dá o plano');
select throws_ok(
  $$select public.publish_item('f1000000-0000-4000-8000-000000000002')$$, '42501',
  'Só admin publica', 'logado é barrado pela guarda da função');

-- Assinante: mesmo papel do banco, outra pessoa.
select set_config('request.jwt.claims',
  '{"sub":"f0000000-0000-4000-8000-000000000003","role":"authenticated"}', true);
select is((select count(*) from public.item_bodies where item_id::text like 'f1%'), 1::bigint,
  'assinante lê o texto do publicado, e não o do rascunho');

-- Admin.
select set_config('request.jwt.claims',
  '{"sub":"f0000000-0000-4000-8000-000000000001","role":"authenticated"}', true);
select is((select count(*) from public.items where slug like 'teste-%'), 2::bigint,
  'admin vê o rascunho');
select lives_ok(
  $$select public.publish_item('f1000000-0000-4000-8000-000000000002')$$, 'admin publica');

-- Prova final, de volta a quem abriu a transação: nada do que foi tentado ficou gravado.
reset role;
select set_config('request.jwt.claims', '', true);
select is((select title from public.items where slug = 'teste-pago'), 'Pago', 'título intacto');

select * from finish();
rollback;

-- O que adaptar:
-- - plan(N) acompanha o número de afirmações: plano desatualizado faz o arquivo falhar.
-- - Para cada persona: o que lê, o que não vê, o que grava, o que não grava e a autopromoção.
-- - Filtre pelos ids do teste: os dados de exemplo do projeto estão no mesmo banco.
-- - Afirme bloqueio só depois de trocar de papel: sem a troca, quem roda ignora as policies.
