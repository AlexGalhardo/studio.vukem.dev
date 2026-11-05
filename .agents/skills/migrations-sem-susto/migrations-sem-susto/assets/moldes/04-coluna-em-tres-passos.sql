-- Molde 4 de 5: coluna obrigatória em três migrations.
-- Cada bloco abaixo é UM ARQUIVO, com o cabeçalho completo do molde 1, e entre eles há envio de
-- código. Estão juntos só para caber num molde: separe ao copiar.
-- Exemplo: toda linha de items passa a dizer de onde veio (source).

-- ===== Arquivo 1 de 3: <versão>_items_source.sql =================================================
-- O que faz: cria items.source, opcional. Só acrescenta.
-- Por quê opcional: o código que está no ar não conhece a coluna e continua gravando sem ela.
-- Fica de fora, de propósito: o preenchimento e a obrigatoriedade (arquivos 2 e 3).
alter table public.items add column source text;
comment on column public.items.source is 'De onde o item veio: manual, import ou api.';

-- >>> Entre o 1 e o 2: sobe o código que grava source em toda linha nova. Sem isso, o
-- >>> preenchimento nunca termina: linhas novas continuam chegando vazias.

-- ===== Arquivo 2 de 3: <versão>_items_source_backfill.sql ========================================
-- O que faz: preenche as linhas antigas com 'manual'.
-- Roda de novo sem erro? Sim: só toca linha em que source é nulo.
-- Volta: não tem como distinguir depois o 'manual' preenchido aqui do gravado pelo aplicativo.
-- Tabela grande: não faça num comando só dentro da migration. Rode em lotes, por faixa de chave,
--   com simulação antes (references/expandir-e-usar.md §2).
update public.items set source = 'manual' where source is null;

-- >>> Entre o 2 e o 3: confira no ambiente de destino, e só siga com zero:
-- >>>   select count(*) from public.items where source is null;

-- ===== Arquivo 3 de 3: <versão>_items_source_required.sql ========================================
-- O que faz: torna items.source obrigatória.
-- Por quê por último: com uma linha nula, o comando falha inteiro ("contains null values").
-- Volta: migration nova com "alter column source drop not null".
alter table public.items alter column source set not null;

-- O que adaptar:
-- - O valor do preenchimento: é decisão de produto. Pergunte ao dono o que as linhas antigas valem.
-- - Com valor padrão constante ("add column source text not null default 'manual'") os três
--   passos viram um. Só serve quando o padrão é a resposta certa também para as linhas futuras.
-- - Tabela com muitas linhas: "set not null" lê a tabela inteira com ela travada. A saída, com
--   restrição validada antes, está em references/expandir-e-usar.md §2.
