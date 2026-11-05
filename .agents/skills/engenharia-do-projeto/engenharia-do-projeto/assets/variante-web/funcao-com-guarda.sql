-- Molde da variante web. Generalizado de uso real, com nomes genéricos.
-- Não foi executado nesta forma: rode antes de confiar.

-- 1. Função de autorização: responde sim ou não, só lê e não recebe a identidade por argumento.
--    Quem decide é a sessão de quem chama. Para o visitante, responde falso.
create function public.app_is_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.app_admins a where a.user_id = auth.uid());
$$;

-- 2. Função com privilégio: roda com os direitos de quem a criou e atravessa as políticas.
--    A guarda é a primeira instrução. Caminho de busca vazio: todo objeto vai com o esquema.
create function public.app_publicar(item_id uuid) returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  faltando text[] := '{}';
begin
  if not public.app_is_admin() then
    raise exception 'Só administrador publica' using errcode = '42501';
  end if;

  perform 1 from public.app_itens i where i.id = app_publicar.item_id for update;
  if not found then
    raise exception 'Item não encontrado' using errcode = 'P0002';
  end if;

  -- Monte aqui, em "faltando", a lista do que falta. Com a lista vazia, grave tudo nesta transação.
  if cardinality(faltando) > 0 then
    raise exception 'Não dá para publicar: falta %', array_to_string(faltando, ', ')
      using errcode = 'P0001';
  end if;
end;
$$;

-- Toda função nasce executável por qualquer papel: sem isto, a única barreira seria a guarda.
revoke execute on function public.app_publicar(uuid) from public, anon;
grant execute on function public.app_publicar(uuid) to authenticated, service_role;

-- O que adaptar:
-- - O corpo: o que a operação confere e grava. A guarda continua sendo a primeira instrução.
-- - Os três códigos de erro combinados: sem privilégio, não encontrado, falta isto.
-- - O papel de serviço tem execução e não tem identidade: a guarda o recusa, de propósito.
-- - O teste: visitante falha por privilégio; logado falha pela guarda, e o dado fica como estava.
