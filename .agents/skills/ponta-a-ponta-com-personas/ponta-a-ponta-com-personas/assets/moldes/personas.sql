-- Molde: as personas nos dados de exemplo. Cole no arquivo de dados de exemplo do projeto.
-- Generalizado de uso real, com tabelas de nomes genéricos. Rodou nesta forma em Postgres 18,
-- duas vezes seguidas, sobre cinco tabelas mínimas criadas só para o teste.
-- =============================================================================================
--  DADOS DE EXEMPLO · SÓ NO AMBIENTE LOCAL E NO CI. NÃO RODE NO BANCO REMOTO.
-- =============================================================================================
-- Só insere linhas: não cria tabela, função nem tipo.
--
-- Personas (conta, papel, identificador fixo):
--   admin@example.test       admin                    a0000000-0000-4000-8000-000000000001
--   logado@example.test      logado, sem plano        a0000000-0000-4000-8000-000000000002
--   assinante@example.test   assinante, plano ativo   a0000000-0000-4000-8000-000000000003
-- Visitante não tem linha: é a sessão vazia.
--
-- Itens (identificador 10000000-0000-4000-8000-0000000000NN):
--   01 item-publicado     publicado · todos veem
--   02 rascunho-interno   RASCUNHO  · só o admin vê (é marcador do teste de guarda)

-- 1. As contas. Identificador fixo: o teste e os outros dados apontam para ele sem consultar.
insert into usuarios (id, email) values
  ('a0000000-0000-4000-8000-000000000001', 'admin@example.test'),
  ('a0000000-0000-4000-8000-000000000002', 'logado@example.test'),
  ('a0000000-0000-4000-8000-000000000003', 'assinante@example.test')
on conflict (id) do nothing;

-- 2. O papel de admin é uma linha, não um e-mail escrito no código.
insert into administradores (usuario_id) values
  ('a0000000-0000-4000-8000-000000000001')
on conflict (usuario_id) do nothing;

-- 3. O assinante é assinante porque esta linha existe. Em produção quem a grava é o aviso do
--    provedor de pagamento; aqui o arquivo de dados de exemplo faz esse papel. Data relativa:
--    o teste não pode depender do dia em que roda.
insert into assinaturas (usuario_id, status, periodo_ate) values
  ('a0000000-0000-4000-8000-000000000003', 'active', now() + interval '30 days')
on conflict (usuario_id) do nothing;

-- 4. As três já cumpriram os passos obrigatórios do produto (perfil respondido). Sem isto, todo
--    teste delas cai no formulário de boas-vindas em vez da tela que queria ver.
insert into perfis (usuario_id, respondido_em) values
  ('a0000000-0000-4000-8000-000000000001', now() - interval '8 days'),
  ('a0000000-0000-4000-8000-000000000002', now() - interval '8 days'),
  ('a0000000-0000-4000-8000-000000000003', now() - interval '8 days')
on conflict (usuario_id) do nothing;

-- 5. Um dado de cada estado que os papéis distinguem.
insert into itens (id, slug, titulo, status) values
  ('10000000-0000-4000-8000-000000000001', 'item-publicado', 'Item publicado', 'published'),
  ('10000000-0000-4000-8000-000000000002', 'rascunho-interno', 'Rascunho interno', 'draft')
on conflict (id) do nothing;

-- O que adaptar:
-- - As tabelas e colunas: as do projeto. O cabeçalho com a lista de personas fica.
-- - Uma persona a mais para cada papel que as regras distinguem (plano pausado, conta bloqueada).
-- - Provedor de login que guarda a conta em tabela dele (no Supabase, o schema `auth`): a linha
--   da conta leva as colunas que o serviço exige. Confira na skill `app-com-supabase`, ou crie as
--   contas pela API de administração num script de dados de exemplo, passando o identificador.
-- - Nenhum dado daqui começa com o prefixo de teste: a limpeza por prefixo apagaria a persona.
