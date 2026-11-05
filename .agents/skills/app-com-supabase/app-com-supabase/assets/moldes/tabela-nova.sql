-- Molde: migration de tabela nova no Supabase, com RLS, policies e privilégios.
-- Rodou no Supabase local (Postgres 17) depois de funcao-com-guarda.sql. Troque os nomes e rode
-- os testes do projeto antes de confiar.
--
-- <Funcionalidade>: <o que esta migration cria, em uma frase>. Só acrescenta.
-- A vitrine (items) é pública quando publicada. O texto pago mora em tabela à parte
-- (item_bodies): uma consulta que pede tudo da vitrine não leva o que é pago.

create table public.items (
  id uuid primary key default gen_random_uuid(),
  slug text not null,
  title text not null,
  status text not null default 'draft',
  access text not null default 'paid',
  file_path text,                                -- caminho no bucket privado, ou nulo
  published_at timestamptz,
  created_at timestamptz not null default now(),
  constraint items_slug_key unique (slug),
  constraint items_slug_check
    check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and char_length(slug) between 2 and 80),
  constraint items_title_check check (char_length(title) between 2 and 80),
  constraint items_status_check check (status in ('draft', 'published')),
  constraint items_access_check check (access in ('free', 'paid'))
);

create table public.item_bodies (
  item_id uuid primary key references public.items (id) on delete cascade,
  body text not null,
  constraint item_bodies_body_check check (char_length(body) between 1 and 20000)
);

comment on table public.items is 'Vitrine: o que o visitante vê quando o item está publicado.';
comment on table public.item_bodies is 'Texto pago de cada item. Lido por quem tem direito.';

-- Tabela nova nasce sem RLS: ligue em toda tabela, na mesma migration que a cria.
alter table public.items enable row level security;
alter table public.item_bodies enable row level security;

-- Nome: <tabela>_<quem>_<comando>. Função dentro de policy vai em subconsulta: é avaliada uma
-- vez por comando, e não uma vez por linha.
create policy items_public_select on public.items
  for select to anon, authenticated using (status = 'published');
create policy items_admin_all on public.items
  for all to authenticated
  using ((select public.is_admin())) with check ((select public.is_admin()));

create policy item_bodies_reader_select on public.item_bodies
  for select to authenticated
  using (exists (
    select 1 from public.items i
    where i.id = item_bodies.item_id
      and i.status = 'published'
      and (i.access = 'free' or (select public.has_plan()))
  ));
create policy item_bodies_admin_all on public.item_bodies
  for all to authenticated
  using ((select public.is_admin())) with check ((select public.is_admin()));

-- Privilégios: tabela nova nasce com tudo concedido a anon e authenticated, inclusive truncate.
-- Revogue o que veio de fábrica e só então conceda o mínimo.
revoke all privileges on public.items, public.item_bodies from anon, authenticated;
grant select on public.items to anon;                                  -- item_bodies: nada
grant select, insert, update, delete on public.items, public.item_bodies to authenticated;
grant all on public.items, public.item_bodies to service_role;

-- O que adaptar:
-- - Nomes, colunas e tetos. O destino de cada filho quando o pai é apagado.
-- - As policies: uma por comando e por papel, e nenhuma onde não deve haver acesso.
-- - Quem escreve: aqui só o admin passa pela policy de escrita, e por isso authenticated tem os
--   quatro comandos. Em tabela "da própria pessoa", troque por user_id = (select auth.uid()).
-- - Depois: gere de novo os tipos e inclua as tabelas no teste só de privilégios.
