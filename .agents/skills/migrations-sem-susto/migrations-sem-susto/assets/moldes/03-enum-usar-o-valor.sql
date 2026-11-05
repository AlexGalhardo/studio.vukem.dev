-- Molde 3 de 5: o par de enum, arquivo 2 de 2. O primeiro uso do valor.
--
-- O que faz: prepara items para áudio: a coluna opcional duration_seconds e o índice da listagem
--   de áudios, que cita o valor audio.
-- Por quê é outra migration: usa o valor criado em <versão do arquivo 1>, que precisa estar
--   confirmado antes. No mesmo arquivo, o Postgres recusa com "unsafe use of new value".
-- Fica de fora, de propósito: a regra "áudio só publica com duração" (migration da função).
-- Substitui: nada. Só acrescenta: as linhas antigas continuam válidas, nenhuma é audio.
-- Roda de novo sem erro? Não: é aplicada uma vez.
-- Volta: migration nova que remove o índice; a coluna fica, sem uso, até o dono decidir.

alter table public.items add column duration_seconds integer;
alter table public.items
  add constraint items_duration_check check (duration_seconds > 0);   -- nulo passa: é opcional
comment on column public.items.duration_seconds is 'Duração em segundos. Só áudio preenche.';

create index items_audio_created_at_idx
  on public.items (created_at desc)
  where kind = 'audio';

-- O que adaptar:
-- - O uso de verdade: uma função, uma regra, um índice ou um dado que cita o valor.
-- - Tabela com muitas linhas: "add constraint" lê a tabela inteira com ela travada, e
--   "create index" trava a escrita. As saídas estão em references/expandir-e-usar.md §6.
-- - O código que grava audio sobe depois desta migration, nunca antes.
