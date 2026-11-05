-- Molde: dados de exemplo com marcadores. SÓ PARA O BANCO LOCAL: nunca rode em produção.
-- Cada corpo leva um marcador na primeira linha e outro na última, e o marcador não aparece em
-- nenhum outro campo (título, resumo, slug, etiqueta). Marcador PAGO- ou RASCUNHO- na resposta de
-- quem não paga quer dizer que o texto saiu do servidor.
--
-- Marcadores (o teste de vazamento confere que a lista dele é igual a esta):
--   item-pago-a    pago, publicado    PAGO-INICIO-R3NM3R      PAGO-FIM-DTVAV3
--   item-pago-b    pago, publicado    PAGO-INICIO-HK8HAB      PAGO-FIM-EBR9NW
--   item-livre     livre, publicado   LIVRE-INICIO-AXWPYX     LIVRE-FIM-P97H5R       todos leem
--   item-rascunho  pago, rascunho     RASCUNHO-INICIO-JWUNNM  RASCUNHO-FIM-GPGMG6    ninguém lê
--
-- Formato: <CLASSE>-<PONTA>-<6 caracteres sorteados>. Só maiúsculas, dígitos e hífen, que passam
-- iguais por HTML, JSON e endereço. Sorteie; não invente à mão nem reaproveite de outro item:
--   python3 -c "import secrets; print(''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6)))"
--
-- Rodou em Postgres 18 contra um esquema de brinquedo com estas quatro tabelas. Os nomes são
-- genéricos: troque pelos do projeto e acrescente as colunas obrigatórias de cada tabela.
begin;

-- Uma conta de identificador fixo por persona. O visitante não tem conta: é a sessão vazia.
-- Na sua tabela de usuários, use endereço de um domínio reservado para teste, nunca o de alguém.
insert into app_usuarios (id, nome, papel) values
  ('00000000-0000-4000-8000-000000000002', 'Persona logada sem plano', 'membro'),
  ('00000000-0000-4000-8000-000000000003', 'Persona assinante',        'membro'),
  ('00000000-0000-4000-8000-000000000004', 'Persona admin',            'admin');

-- A assinante é assinante porque esta linha existe. Em produção quem grava é o aviso do provedor
-- de pagamento; aqui, os dados de exemplo fazem esse papel.
insert into app_assinaturas (usuario_id, status) values
  ('00000000-0000-4000-8000-000000000003', 'ativa');

-- Dois itens pagos (um é "a página de outro item" para o outro), um livre e um rascunho.
insert into app_itens (id, slug, titulo, resumo, status, acesso) values
  ('10000000-0000-4000-8000-000000000001', 'item-pago-a',   'Item pago A',
   'Resumo público do item pago A.', 'publicado', 'pago'),
  ('10000000-0000-4000-8000-000000000002', 'item-pago-b',   'Item pago B',
   'Resumo público do item pago B.', 'publicado', 'pago'),
  ('10000000-0000-4000-8000-000000000003', 'item-livre',    'Item livre',
   'Resumo público do item livre.',  'publicado', 'livre'),
  ('10000000-0000-4000-8000-000000000004', 'item-rascunho', 'Item em rascunho',
   'Resumo que ainda não saiu.',     'rascunho',  'pago');

-- O corpo mora em tabela própria: a leitura pública do item nunca o traz junto.
-- Dê ao texto o tamanho e o formato do conteúdo de verdade (títulos, listas, código): o marcador
-- tem de atravessar o mesmo caminho que ele, inclusive o corte de uma prévia.
insert into app_conteudos (item_id, corpo) values
  ('10000000-0000-4000-8000-000000000001', $corpo$PAGO-INICIO-R3NM3R
# Item pago A

Texto de exemplo do item pago A, com parágrafos, uma lista e um bloco de código.

- primeiro ponto
- segundo ponto
PAGO-FIM-DTVAV3$corpo$),
  ('10000000-0000-4000-8000-000000000002', $corpo$PAGO-INICIO-HK8HAB
Texto de exemplo do item pago B.
PAGO-FIM-EBR9NW$corpo$),
  ('10000000-0000-4000-8000-000000000003', $corpo$LIVRE-INICIO-AXWPYX
Texto de exemplo do item livre. O visitante tem de receber as duas pontas.
LIVRE-FIM-P97H5R$corpo$),
  ('10000000-0000-4000-8000-000000000004', $corpo$RASCUNHO-INICIO-JWUNNM
Texto de exemplo do rascunho. Não aparece em rota pública para ninguém.
RASCUNHO-FIM-GPGMG6$corpo$);

commit;

-- O que adaptar:
-- - Os nomes de tabela e coluna; um item pago de cada tipo que o produto vende (texto, arquivo).
-- - Se o item tem versões, plante um rascunho de versão nova num item publicado: classe RASCUNHO.
-- - Conteúdo pago novo nos dados de exemplo: par de marcadores novo, aqui e na lista do teste.
