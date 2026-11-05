-- Molde: tabela de assinatura, tabela de eventos do Stripe, função de acesso e respostas do
-- formulário de cancelamento. Postgres. Só adiciona: rode como uma migração nova.
--
-- Adapte antes de rodar:
--   1. Os nomes, se o projeto usa prefixo. O teste de fronteira e o conferidor recebem o nome.
--   2. auth.users e auth.uid() são do Supabase. Em outro backend, troque pela sua tabela de
--      usuários e pela função que devolve o usuário da sessão.
--   3. Os papéis anon, authenticated e service_role. Sem segurança por linha (RLS), a regra "só o
--      servidor com a chave de serviço escreve" vira permissão de tabela do usuário do aplicativo.

-- Os oito status são os do Stripe. Status novo deve FALHAR no webhook, não virar palpite.
create type public.subscription_status as enum (
  'trialing', 'active', 'past_due', 'canceled', 'unpaid', 'incomplete', 'incomplete_expired', 'paused'
);

-- Eventos já processados: é o que torna o webhook idempotente.
create table public.stripe_events (
  id text primary key,
  type text not null,
  received_at timestamptz not null default now()
);

-- Uma linha por pessoa, espelho do Stripe. Sem linha = nunca assinou.
-- Só o webhook escreve; a pessoa lê a própria linha; has_plan() decide o acesso.
create table public.subscriptions (
  user_id uuid primary key references auth.users (id) on delete cascade,
  stripe_customer_id text not null,
  stripe_subscription_id text not null,
  status public.subscription_status not null,
  current_period_end timestamptz,
  cancel_at_period_end boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint subscriptions_stripe_customer_id_key unique (stripe_customer_id),
  constraint subscriptions_stripe_subscription_id_key unique (stripe_subscription_id)
);

-- Quem tem o plano: a ÚNICA regra de acesso do banco, espelhada em acesso.ts (hasPlan).
-- trialing conta; past_due, unpaid, paused, canceled e os demais não dão acesso.
create function public.has_plan() returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.subscriptions s
    where s.user_id = auth.uid()
      and s.status in ('active', 'trialing')
  );
$$;

alter table public.stripe_events enable row level security;
alter table public.subscriptions enable row level security;

-- A pessoa lê a própria assinatura. Não há policy de escrita em nenhuma das duas tabelas, e
-- stripe_events não tem policy de leitura: só o papel de serviço, que ignora a RLS, alcança.
create policy subscriptions_owner_select on public.subscriptions
  for select to authenticated
  using (user_id = (select auth.uid()));

-- Primeiro tira tudo, depois concede só o necessário. Assim nem um erro de policy deixa o
-- usuário logado escrever a própria assinatura.
revoke all privileges on public.stripe_events, public.subscriptions from anon, authenticated;
grant select on public.subscriptions to authenticated;
grant all on public.stripe_events, public.subscriptions to service_role;
grant execute on function public.has_plan() to anon, authenticated, service_role;

-- Uso numa policy de conteúdo pago:
--   using (is_free or (select public.has_plan()))

-- ---------------------------------------------------------------------------------------------
-- Opcional: respostas do formulário obrigatório de cancelamento (references/cancelamento.md).
-- Uma linha por envio. As perguntas e os valores aceitos ficam no código, validados por esquema:
-- trocar uma pergunta não pede migração. A resposta sobrevive à exclusão da conta.
create table public.cancel_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  answers jsonb not null,
  outcome text not null default 'pending',
  subscription_status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cancel_feedback_answers_check check (jsonb_typeof(answers) = 'object'),
  constraint cancel_feedback_answers_size_check check (octet_length(answers::text) <= 16384),
  constraint cancel_feedback_outcome_check
    check (outcome in ('pending', 'discount', 'paused', 'cancel'))
);

create index cancel_feedback_user_id_created_at_idx
  on public.cancel_feedback (user_id, created_at desc);

alter table public.cancel_feedback enable row level security;

-- A pessoa cria, lê e atualiza (o desfecho) só as próprias respostas. Sem policy de delete.
-- Para o painel de motivos, acrescente uma policy de leitura com a função de admin do projeto.
create policy cancel_feedback_owner_insert on public.cancel_feedback
  for insert to authenticated
  with check (user_id = (select auth.uid()));

create policy cancel_feedback_owner_select on public.cancel_feedback
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy cancel_feedback_owner_update on public.cancel_feedback
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

revoke all privileges on public.cancel_feedback from anon, authenticated;
grant select, insert, update on public.cancel_feedback to authenticated;
grant all on public.cancel_feedback to service_role;
