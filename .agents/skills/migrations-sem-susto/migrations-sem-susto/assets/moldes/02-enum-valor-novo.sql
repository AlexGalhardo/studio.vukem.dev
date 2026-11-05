-- Molde 2 de 5: o par de enum, arquivo 1 de 2. Só o valor novo, sozinho no arquivo.
--
-- O que faz: acrescenta o valor audio ao tipo item_kind.
-- Por quê é só isto: em Postgres o valor novo não pode ser usado na transação em que nasce, e
--   cada arquivo de migration roda numa transação. O primeiro uso está na migration seguinte:
--   <versão>_<assunto>.sql.
-- Fica de fora, de propósito: coluna, regra, índice ou dado que cite o valor.
-- Substitui: nada.
-- Roda de novo sem erro? Sim: "if not exists".
-- Volta: não tem. Valor de enum não sai do tipo; desfazer é recriar o tipo e todas as colunas
--   que o usam. Diga isso ao dono antes de aplicar.

alter type public.item_kind add value if not exists 'audio';
comment on type public.item_kind is 'Tipo do item: video, text ou audio.';

-- O que adaptar:
-- - O nome do tipo e o valor. A posição ("before", "after") só importa se o código ordena por ela.
-- - Coluna de texto com "check" no lugar de enum: a ordem é a mesma. Primeiro uma migration troca
--   o check para aceitar o valor; só depois alguém grava.
-- - O código que está no ar não conhece o valor. Enquanto nenhuma linha o usa, nada muda para ele.
