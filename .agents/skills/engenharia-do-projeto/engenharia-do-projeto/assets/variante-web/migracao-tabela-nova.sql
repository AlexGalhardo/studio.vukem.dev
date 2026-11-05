-- Molde da variante web. Generalizado de uso real, com nomes genéricos.
-- Não foi executado nesta forma: rode antes de confiar.
--
-- <Funcionalidade>: <o que esta migração cria, em uma frase>.
-- Só acrescenta. Quem cria, lê e altera; quem só lê; quem não apaga.
-- O que é validado no aplicativo e não aqui, e por quê.

create table public.app_coisas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  titulo text not null,
  dados jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint app_coisas_titulo_check check (char_length(titulo) between 2 and 80),
  constraint app_coisas_dados_check check (jsonb_typeof(dados) = 'object'),
  constraint app_coisas_dados_size_check check (octet_length(dados::text) <= 4096)
);

create index app_coisas_user_id_created_at_idx on public.app_coisas (user_id, created_at desc);

create trigger app_coisas_set_updated_at
  before update on public.app_coisas
  for each row execute function public.app_set_updated_at();

comment on table public.app_coisas is '<para que serve, em uma frase>';
comment on column public.app_coisas.dados is '<o que guarda; objeto de até 4096 bytes>';

alter table public.app_coisas enable row level security;

-- Função dentro de política vai em subconsulta: é avaliada uma vez por comando, não por linha.
create policy app_coisas_owner_select on public.app_coisas
  for select to authenticated using (user_id = (select auth.uid()));
create policy app_coisas_owner_insert on public.app_coisas
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy app_coisas_owner_update on public.app_coisas
  for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy app_coisas_admin_select on public.app_coisas
  for select to authenticated using ((select public.app_is_admin()));

-- Privilégios: revogue o que veio de fábrica e só então conceda o mínimo.
revoke all privileges on public.app_coisas from anon, authenticated;
grant select, insert, update on public.app_coisas to authenticated;   -- sem delete
grant all on public.app_coisas to service_role;

-- O que adaptar:
-- - Nomes, colunas e tetos; o destino de cada filho quando o pai é apagado.
-- - As políticas: uma por comando e por papel, e nenhuma onde não deve haver acesso.
-- - app_set_updated_at() e app_is_admin() vêm de migrações anteriores: sem elas, o arquivo falha.
-- - Depois: gere de novo o artefato do banco e inclua a tabela no teste só de privilégios.
