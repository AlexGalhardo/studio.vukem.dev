-- Molde 1 de 5: a migration com cabeçalho. Nomes genéricos; os cinco moldes rodam nesta ordem.
-- Copie para <migrations>/<versão>_<assunto>.sql, com o arquivo criado pela ferramenta do projeto.
--
-- ---- O cabeçalho que toda migration leva: troque o texto, mantenha as seis respostas ----------
-- O que faz: cria o catálogo de itens: o tipo item_kind, a tabela items e a função publish_item.
-- Por quê: <a funcionalidade ou a decisão que pede isto, com o número do registro de decisão>.
-- Fica de fora, de propósito: <o que alguém esperaria achar aqui, e onde está>.
-- Substitui: nada. (Ao redefinir: "igual à da <versão>, mudando só <o quê>".)
-- Roda de novo sem erro? Não: é aplicada uma vez. (Se rodar, diga por quê: "if not exists".)
-- Volta: remover pede migration nova, depois de o código parar de usar; o dado gravado se perde.
-- -----------------------------------------------------------------------------------------------

create type public.item_kind as enum ('video', 'text');
comment on type public.item_kind is 'Tipo do item: video ou text.';

create table public.items (
  id uuid primary key default gen_random_uuid(),
  kind public.item_kind not null,
  title text not null,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  constraint items_title_check check (char_length(title) between 2 and 120)
);
comment on table public.items is 'Itens do catálogo. Publicado quando published_at não é nulo.';

-- Privilégios na mesma migration que cria: revogue o que veio de fábrica e conceda o mínimo.
revoke all on public.items from public;
grant select, insert on public.items to app_user;   -- sem update nem delete: publicar é pela função

-- Função que roda com o privilégio do dono. As três proteções andam juntas: security definer,
-- caminho de busca fixo (todo objeto com o esquema escrito) e execute só para quem pode chamar.
create function public.publish_item(p_item_id uuid) returns void
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
  update public.items set published_at = now() where id = p_item_id;
end;
$$;
comment on function public.publish_item(uuid) is 'Publica um item. Só app_user executa.';

revoke execute on function public.publish_item(uuid) from public;
grant execute on function public.publish_item(uuid) to app_user;

-- O que adaptar:
-- - app_user é o papel com que o aplicativo conecta: troque pelo do projeto. Se a plataforma
--   concede privilégios de fábrica a outros papéis, revogue deles também.
-- - Quem pode chamar a função, dentro dela: se a regra depende de quem é a pessoa, a guarda vai
--   na primeira linha do corpo. No Supabase, veja a skill irmã app-com-supabase.
-- - Depois de aplicar do zero: gere de novo os tipos ou o cliente do banco e commite junto.
