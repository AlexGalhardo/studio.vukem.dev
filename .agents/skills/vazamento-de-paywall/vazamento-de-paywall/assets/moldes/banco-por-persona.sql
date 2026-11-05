-- Molde: o banco, por persona, não entrega conteúdo pago a quem não paga. Postgres puro, sem
-- extensão. Rode no banco LOCAL:
--   psql "$URL_DO_BANCO_LOCAL" -v ON_ERROR_STOP=1 -f banco-por-persona.sql
-- Cria os próprios dados numa faixa de identificadores (f…) que não colide com a dos dados de
-- exemplo e desfaz tudo no fim (rollback). Para na primeira falha: "VAZOU:" ou "NÃO CONFERIU:".
-- Rodou em Postgres 18 contra um esquema de brinquedo e reprovou em cinco vazamentos plantados:
-- leitura aberta, "basta estar logado", autopromoção, ex-assinante que se reativa e assinante que
-- lê rascunho. Virar persona aqui é à moda do Supabase (papel e declarações da sessão). Se a
-- permissão mora só no aplicativo, este arquivo não se aplica: a camada é o teste da função única
-- de leitura.
begin;

insert into app_usuarios (id, nome, papel) values
  ('f0000000-0000-4000-8000-000000000002', 'Teste: logado sem plano', 'membro'),
  ('f0000000-0000-4000-8000-000000000003', 'Teste: assinante',        'membro'),
  ('f0000000-0000-4000-8000-000000000005', 'Teste: ex-assinante',     'membro');
insert into app_assinaturas (usuario_id, status) values
  ('f0000000-0000-4000-8000-000000000003', 'ativa'),
  ('f0000000-0000-4000-8000-000000000005', 'cancelada');
insert into app_itens (id, slug, titulo, status, acesso) values
  ('f1000000-0000-4000-8000-000000000001', 'teste-pago',     'Pago',     'publicado', 'pago'),
  ('f1000000-0000-4000-8000-000000000002', 'teste-livre',    'Livre',    'publicado', 'livre'),
  ('f1000000-0000-4000-8000-000000000003', 'teste-rascunho', 'Rascunho', 'rascunho',  'pago');
insert into app_conteudos (item_id, corpo) values
  ('f1000000-0000-4000-8000-000000000001', E'PAGO-INICIO-FZ5P2F\ncorpo pago\nPAGO-FIM-ZPCQBD'),
  ('f1000000-0000-4000-8000-000000000002', E'LIVRE-INICIO-8M9DC9\ncorpo livre\nLIVRE-FIM-9P38TU'),
  ('f1000000-0000-4000-8000-000000000003', E'RASCUNHO-INICIO-94GEU3\nrascunho\nRASCUNHO-FIM-DC9GHU');

-- A varredura: nenhuma linha que a persona atual consegue ler, em tabela ou visão nenhuma do
-- esquema, traz marcador da classe proibida. Devolve quantas tabelas leu, para provar que
-- enxergou. Some no rollback. Função exposta como chamada remota não entra: teste pelo nome.
create function public.teste_varrer(proibido text) returns integer language plpgsql as $f$
declare t record; achadas bigint; lidas integer := 0;
begin
  for t in select c.oid::regclass as nome from pg_class c
           join pg_namespace n on n.oid = c.relnamespace
           where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm')
             and has_table_privilege(c.oid, 'select')
  loop
    execute format('select count(*) from %s linha where linha::text ~ %L', t.nome, proibido)
      into achadas;
    if achadas > 0 then
      raise exception 'VAZOU: % lê % linha(s) de % com %', current_user, achadas, t.nome, proibido;
    end if;
    lidas := lidas + 1;
  end loop;
  if lidas = 0 then raise exception 'NÃO CONFERIU: % não lê tabela nenhuma', current_user; end if;
  return lidas;
end $f$;
grant execute on function public.teste_varrer(text) to anon, authenticated;

-- Persona: visitante. O papel sem sessão, com as declarações vazias.
set local role anon;
select set_config('request.jwt.claims', '', true);
do $$ begin
  perform public.teste_varrer('(PAGO|RASCUNHO)-(INICIO|FIM)-');
  -- Controle positivo: o conteúdo livre chega. "Zero linhas" de tabela fechada não prova nada.
  if (select count(*) from app_conteudos where corpo like 'LIVRE-INICIO-8M9DC9%') <> 1 then
    raise exception 'NÃO CONFERIU: o visitante não leu o conteúdo livre';
  end if;
end $$;

-- Persona: logado sem plano. Ao trocar de persona, troque o papel E as declarações.
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"f0000000-0000-4000-8000-000000000002","role":"authenticated"}', true);
do $$ begin
  perform public.teste_varrer('(PAGO|RASCUNHO)-(INICIO|FIM)-');
  begin -- autopromoção: é a escrita que mais rende a quem quer ler sem pagar
    insert into app_assinaturas (usuario_id, status)
      values ('f0000000-0000-4000-8000-000000000002', 'ativa');
    raise exception 'VAZOU: o logado se deu o plano';
  exception when insufficient_privilege then null; -- esperado: código 42501
  end;
  perform public.teste_varrer('(PAGO|RASCUNHO)-(INICIO|FIM)-');
end $$;

-- Persona: ex-assinante. Cancelou e não pode continuar lendo, nem reativar a própria linha.
select set_config('request.jwt.claims',
  '{"sub":"f0000000-0000-4000-8000-000000000005","role":"authenticated"}', true);
do $$ begin
  perform public.teste_varrer('(PAGO|RASCUNHO)-(INICIO|FIM)-');
  begin -- alterar barrado por política não dá erro: afeta zero linhas. A prova final confere.
    update app_assinaturas set status = 'ativa'
      where usuario_id = 'f0000000-0000-4000-8000-000000000005';
  exception when insufficient_privilege then null;
  end;
  perform public.teste_varrer('(PAGO|RASCUNHO)-(INICIO|FIM)-');
end $$;

-- Persona: assinante. Controle positivo: quem paga lê as duas pontas, e não lê rascunho.
select set_config('request.jwt.claims',
  '{"sub":"f0000000-0000-4000-8000-000000000003","role":"authenticated"}', true);
do $$ begin
  if (select count(*) from app_conteudos
      where corpo like 'PAGO-INICIO-FZ5P2F%' and corpo like '%PAGO-FIM-ZPCQBD') <> 1 then
    raise exception 'NÃO CONFERIU: a assinante não leu o conteúdo pago';
  end if;
  perform public.teste_varrer('RASCUNHO-(INICIO|FIM)-');
end $$;

-- Prova final, de volta ao papel que abriu a transação: nada do que foi tentado ficou gravado.
reset role;
select set_config('request.jwt.claims', '', true);
do $$ begin
  if exists (select 1 from app_assinaturas
             where usuario_id = 'f0000000-0000-4000-8000-000000000002') then
    raise exception 'VAZOU: a autopromoção do logado ficou gravada';
  end if;
  if (select status from app_assinaturas
      where usuario_id = 'f0000000-0000-4000-8000-000000000005') <> 'cancelada' then
    raise exception 'VAZOU: o ex-assinante reativou a própria assinatura';
  end if;
end $$;
select 'banco por persona: nada pago chegou a quem não paga' as resultado;
rollback;

-- O que adaptar:
-- - Tabelas, colunas e os valores de status; os dois comandos que viram a persona.
-- - Controle positivo do visitante: se ele não lê a tabela de conteúdo nem do item livre, troque
--   por uma leitura que ele tem de conseguir (a lista de itens publicados).
-- - Afirme bloqueio só depois de trocar de papel: como dono do banco, a política é ignorada.
