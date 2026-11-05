-- Molde: funções de autorização e função com privilégio, no Supabase (Postgres).
-- Rodou no Supabase local (Postgres 17) junto dos outros moldes desta pasta. Troque os nomes e
-- rode os testes do projeto antes de confiar.
-- Ordem: este arquivo vem antes de tabela-nova.sql, porque as policies de lá chamam is_admin().

-- 1. Tabelas só de serviço: quem é admin e o espelho da assinatura. Quem escreve é a chave
--    secreta (papel service_role). A pessoa logada só lê a própria linha.
create table public.admins (
  user_id uuid primary key references auth.users (id) on delete cascade,
  created_at timestamptz not null default now()
);
create table public.subscriptions (
  user_id uuid primary key references auth.users (id) on delete cascade,
  status text not null,
  updated_at timestamptz not null default now(),
  constraint subscriptions_status_check
    check (status in ('trialing', 'active', 'past_due', 'paused', 'canceled'))
);
comment on table public.admins is 'Quem é admin. Escrita só pela chave secreta.';
comment on table public.subscriptions is 'Espelho da assinatura. Escrita só pelo webhook.';

alter table public.admins enable row level security;
alter table public.subscriptions enable row level security;

create policy admins_owner_select on public.admins
  for select to authenticated using (user_id = (select auth.uid()));
create policy subscriptions_owner_select on public.subscriptions
  for select to authenticated using (user_id = (select auth.uid()));

revoke all privileges on public.admins, public.subscriptions from anon, authenticated;
grant select on public.admins, public.subscriptions to authenticated;   -- sem escrita
grant all on public.admins, public.subscriptions to service_role;

-- 2. Funções de autorização: respondem sim ou não, só leem e não recebem a identidade por
--    argumento. Quem decide é a sessão de quem chama: para o visitante, auth.uid() é nulo e a
--    resposta é falso. Caminho de busca vazio: todo objeto vai escrito com o esquema.
create function public.is_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.admins a where a.user_id = (select auth.uid()));
$$;

create function public.has_plan() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.subscriptions s
    where s.user_id = (select auth.uid()) and s.status in ('trialing', 'active')
  );
$$;

-- 3. Função com privilégio: roda com os direitos de quem a criou e atravessa as policies.
--    A guarda é a primeira instrução. public.items nasce em tabela-nova.sql: plpgsql só resolve
--    o nome da tabela ao executar.
create function public.publish_item(p_item_id uuid) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if not public.is_admin() then
    raise exception 'Só admin publica' using errcode = '42501';
  end if;

  update public.items set status = 'published', published_at = now() where id = p_item_id;
  if not found then
    raise exception 'Item não encontrado' using errcode = 'P0002';
  end if;
end;
$$;

-- Toda função nasce executável por qualquer papel: sem isto, a única barreira seria a guarda.
revoke execute on function public.publish_item(uuid) from public, anon;
grant execute on function public.publish_item(uuid) to authenticated, service_role;

-- O que adaptar:
-- - A lista de status que dá o plano. A tabela completa da assinatura e o webhook que a escreve
--   estão na skill irmã assinatura-com-stripe.
-- - O corpo de publish_item: o que a operação confere e grava. A guarda continua na primeira linha.
-- - service_role executa e não tem identidade: auth.uid() é nulo e a guarda recusa, de propósito.
-- - O primeiro admin: uma linha em public.admins, inserida pelo dono depois do primeiro login dele.
