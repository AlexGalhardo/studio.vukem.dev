-- Molde: teste só de privilégios (pgTAP). A barreira antes da RLS: o que cada papel pode em
-- cada objeto. Rodou no Supabase local (Postgres 17, pgTAP 1.3.3): 13 de 13.
-- As quatro primeiras afirmações são genéricas: pegam a tabela ou a função que alguém criar
-- depois e esquecer de fechar. As outras fixam a lista exata por tabela e por papel.
begin;
select plan(13);

-- 1. Genéricas, sobre o esquema public inteiro.
select is_empty($$
  select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind in ('r', 'p') and not c.relrowsecurity
$$, 'toda tabela de public tem RLS ligada');

select is_empty($$
  select c.relname, r.papel
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  cross join (values ('anon'), ('authenticated')) as r (papel)
  where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm')
    and (has_table_privilege(r.papel, c.oid, 'TRUNCATE')
      or has_table_privilege(r.papel, c.oid, 'REFERENCES')
      or has_table_privilege(r.papel, c.oid, 'TRIGGER'))
$$, 'anon e authenticated não têm truncate, references nem trigger em nada de public');

select is_empty($$
  select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm')
    and has_table_privilege('anon', c.oid, 'INSERT, UPDATE, DELETE')
$$, 'visitante não escreve em nada de public');

select is_empty($$
  select p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.prosecdef
    and not exists (
      select 1 from unnest(coalesce(p.proconfig, '{}'::text[])) as c (item)
      where c.item like 'search_path=%')
$$, 'toda função security definer de public define o caminho de busca');

-- 2. A lista exata, por tabela e por papel. Tabela nova entra aqui na mesma mudança.
select table_privs_are('public', 'items', 'anon', array['SELECT'], 'anon: só select em items');
select table_privs_are('public', 'item_bodies', 'anon', '{}'::text[],
  'anon: nada em item_bodies');
select table_privs_are('public', 'subscriptions', 'anon', '{}'::text[],
  'anon: nada em subscriptions');
select table_privs_are('public', 'items', 'authenticated',
  array['SELECT', 'INSERT', 'UPDATE', 'DELETE'], 'authenticated: os quatro comandos em items');
select table_privs_are('public', 'subscriptions', 'authenticated', array['SELECT'],
  'authenticated: só select em subscriptions (quem escreve é o webhook)');
select table_privs_are('public', 'admins', 'authenticated', array['SELECT'],
  'authenticated: só select em admins');

-- 3. Função com privilégio: o visitante não executa.
select ok(not has_function_privilege('anon', 'public.publish_item(uuid)', 'EXECUTE'),
  'anon não executa publish_item');

-- 4. Provas por efeito: a RLS não filtra truncate, quem segura é o privilégio.
set local role anon;
select throws_ok($$truncate public.items$$, '42501', null, 'visitante não esvazia items');
set local role authenticated;
select throws_ok($$truncate public.items cascade$$, '42501', null, 'logado não esvazia items');

reset role;
select * from finish();
rollback;

-- O que adaptar:
-- - As listas do bloco 2: uma linha por tabela e por papel, com a lista exata.
-- - Se o visitante grava em alguma tabela (formulário de contato), tire-a pelo nome da terceira
--   afirmação genérica e fixe a lista dela no bloco 2.
-- - Visão (view) entra no bloco 2 com só SELECT, e ganha uma prova de que escrever por ela falha.
-- - service_role: confira pelo essencial (has_table_privilege), porque a lista exata muda entre
--   versões do Postgres.
