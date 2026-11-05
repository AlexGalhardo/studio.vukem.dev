-- Molde 5 de 5: redefinir função repetindo as proteções.
--
-- O que faz: publish_item passa a recusar áudio sem duração.
-- Por quê: <a decisão que pede a regra nova>.
-- Substitui: a definição da <versão do molde 1>. Igual a ela, mudando só o bloco marcado NOVO.
-- O que "create or replace function" guarda e o que não guarda (medido em Postgres 17):
--   guarda o dono e os privilégios (quem tem execute);
--   NÃO guarda security definer, "set search_path", nem a volatilidade (stable, immutable).
--   Sem repetir, a função passa a rodar com o privilégio de quem chama e com o caminho de busca
--   da sessão. Por isso os dois estão repetidos abaixo.
-- Não muda: nome, tipos dos argumentos e retorno. Com tipo de argumento diferente nasce OUTRA
--   função, sem proteção nenhuma, e a antiga continua existindo.
-- Roda de novo sem erro? Sim: "create or replace".
-- Volta: migration nova com a definição anterior inteira.

create or replace function public.publish_item(p_item_id uuid) returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_item public.items;
begin
  select * into v_item from public.items where id = p_item_id for update;
  if not found or v_item.published_at is not null then
    raise exception 'Item não encontrado ou já publicado' using errcode = 'P0002';
  end if;
  -- NOVO: áudio só publica com duração.
  if v_item.kind = 'audio' and v_item.duration_seconds is null then
    raise exception 'Áudio sem duração não pode ser publicado' using errcode = '23514';
  end if;
  update public.items set published_at = now() where id = p_item_id;
end;
$$;

-- Confira depois de aplicar, em cada ambiente. Tem de dar: t | {search_path=""} | dono e app_user.
--   select prosecdef, proconfig, proacl from pg_proc
--   where oid = 'public.publish_item(uuid)'::regprocedure;

-- O que adaptar:
-- - Copie a definição em vigor da última migration que a define, ou do banco:
--     select pg_get_functiondef('public.publish_item(uuid)'::regprocedure);
-- - Política: "drop policy" e "create policy" na mesma migration, com a regra inteira.
-- - Visão: "create or replace view" também perde as opções ("security_invoker") se não repetir.
