-- Molde da variante web. Generalizado de uso real, com nomes genéricos.
-- Não foi executado nesta forma: rode antes de confiar.
-- Regras como <persona>: <o que lê, o que grava, o que não faz>, em uma frase.
begin;
select plan(6);

-- Dados próprios, numa faixa (f0…, f1…) que não colide com a dos dados de exemplo.
insert into auth.users (id, email) values
  ('f0000000-0000-0000-0000-000000000002', 'teste-logado@example.com');
insert into public.app_itens (id, slug, titulo, status, acesso) values
  ('f1000000-0000-0000-0000-000000000001', 'teste-restrito', 'Restrito', 'publicado', 'restrito'),
  ('f1000000-0000-0000-0000-000000000002', 'teste-livre',    'Livre',    'publicado', 'livre'),
  ('f1000000-0000-0000-0000-000000000003', 'teste-rascunho', 'Rascunho', 'rascunho',  'restrito');
insert into public.app_conteudos (item_id, corpo) values
  ('f1000000-0000-0000-0000-000000000001', 'corpo restrito do teste');

-- Visitante: o papel sem sessão, com as declarações vazias.
set local role anon;
select set_config('request.jwt.claims', '', true);
select is((select count(*) from public.app_itens where slug like 'teste-%'), 2::bigint,
  'visitante vê os 2 publicados e não vê o rascunho');
select is_empty($$select 1 from public.app_conteudos$$, 'visitante não lê o dado restrito');
select throws_ok($$select 1 from public.app_assinaturas$$, '42501', null,
  'visitante não tem nem leitura no espelho de assinaturas');

-- Logado sem acesso pago: ao trocar de persona, troque o papel e as declarações.
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"f0000000-0000-0000-0000-000000000002","role":"authenticated"}', true);
-- Bloqueio por política se prova pelo efeito (zero linhas); por privilégio, pelo código do erro.
select is_empty(
  $$with u as (update public.app_itens set titulo = 'x' where slug = 'teste-restrito' returning 1)
    select * from u$$,
  'logado não altera item (0 linhas)');
select throws_ok(
  $$insert into public.app_assinaturas (user_id, status)
    values ('f0000000-0000-0000-0000-000000000002', 'ativa')$$,
  '42501', null, 'autopromoção: logado não se dá acesso pago');

-- Prova final, de volta ao papel que abriu a transação: nada do que foi tentado ficou gravado.
reset role;
select set_config('request.jwt.claims', '', true);
select is((select titulo from public.app_itens where slug = 'teste-restrito'), 'Restrito',
  'título intacto');
select * from finish();
rollback;

-- O que adaptar:
-- - Um arquivo por persona da matriz; o plano (plan) acompanha o número de afirmações.
-- - Para cada persona: o que lê, o que não vê, o que grava, o que não grava e a autopromoção.
-- - Afirme bloqueio só depois de trocar de papel: sem a troca, quem roda ignora as políticas.
