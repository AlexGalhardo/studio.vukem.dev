> Exemplo de um projeto fictício (Quadra Livre). Nada aqui é instrução para o projeto atual.

# Roteiro · Quadra Livre

## Como usar este roteiro

Uma sessão nova lê este arquivo depois de `INSTRUCOES.md` e de `docs/ESTADO.md`, e segue a fase em
andamento, com o PostgreSQL do ambiente local no ar. Pare no fim de cada fase, com o relato.

## Onde estamos

O que está pronto, o que está em curso e a última rodada das verificações moram em `docs/ESTADO.md`.

## Leia antes de escrever código

- `ESPECIFICACAO.md`, seções 5 (dados e permissões) e 6 (fluxos); os títulos de `docs/decisoes.md`.
- A documentação da versão instalada do framework web, a de suporte longo (ADR-001), não a memória.

## Regras de trabalho

- **Fim de fase:** pare; suba a escada inteira e mostre o resultado; revise a diferença da fase;
  atualize `docs/ESTADO.md`; entregue o relato com o roteiro de validação.
- **Na Fase 2 a tesouraria só lê:** marcar pagamento é da Fase 3, que traz o teste de permissão.

## Pendências com fase-alvo

1. **Lembrete de mensalidade por mensagem.** Hoje o sócio em atraso não recebe aviso. Entra na
   Fase 3. Atenção: enviar e-mail real aos sócios é autorização que o presidente ainda não deu.

## Fase 0 · Base (pronta)

**Objetivo:** o projeto abre no ambiente local, com a escada montada até o degrau 2.
**Entregas:** projeto em Python, com um framework web completo e PostgreSQL (stack escolhida para
este produto fictício; não é recomendação), na versão de suporte longo (ADR-001); degraus 0 a 2.
**Pronto quando:**
- [x] Abro `localhost:8000` e vejo a página "Quadra Livre", com as duas quadras e nenhum horário.
- [x] Um endereço que não existe mostra "não encontrado", não um erro cru; os degraus 0 a 2 passam.

## Fase 1 · Dados e permissões (pronta)

**Objetivo:** os dados e a matriz de permissões existem e estão provados, antes das telas.
**Entregas:** telefone, situação de pagamento e observação em tabela própria, com uma porta de
leitura (ADR-002); permissão imposta na camada de aplicação; dados de exemplo só no ambiente local.
**Pronto quando:**
- [x] Entro como sócio e não consigo ver o telefone nem a situação de pagamento de outro sócio.
- [x] Entro como tesouraria e vejo os dois; o teste por persona prova a matriz inteira (degrau 3).

## Fase 2 · Reservas (em andamento)

**Objetivo:** o sócio reserva e cancela um horário, e ninguém vê o que não pode.
**Entregas:** grade da semana e reserva em blocos de 30 minutos (ADR-005, que revê o ADR-003);
cancelamento sem multa, só da própria reserva (ADR-004); lista do dia para a tesouraria, só de
leitura (fatia mínima: a Fase 3 completa); teste de vazamento no degrau 3, pelo cliente de teste.
**Pronto quando:**
- [x] O sócio vê os horários livres das duas quadras na semana corrente.
- [x] O sócio reserva um bloco de 30 minutos e a reserva aparece em "minhas reservas".
- [x] Dois sócios não reservam o mesmo bloco: o segundo recebe "horário já reservado" (teste
      nomeado).
- [ ] O sócio cancela a própria reserva; a de outro sócio responde "não encontrado" (teste por
      persona).
- [ ] O visitante vê os horários livres e não recebe nome nem telefone de quem reservou (teste de
      vazamento com o telefone sentinela `(00) 90000-0001`, pela resposta crua).
- [ ] A tesouraria vê as reservas do dia com a situação de pagamento e a observação; um sócio não
      recebe as de outro (teste de vazamento com `QUADRA-SEED-OBSERVACAO-K7M2QX` e pela ausência
      do campo `situacao_pagamento`).
- [ ] Degraus 0 a 3 verdes; o degrau 5 segue pendente e está em "Ficou para depois".

## Fase 3 · Mensalidade e tesouraria (a fazer)

**Objetivo:** a tesouraria marca quem pagou, e o sócio em atraso é lembrado.
**Entregas:** marcar pagamento e escrever observação, só para a tesouraria; lembrete (pendência 1).
**Pronto quando:**
- [ ] Entro como tesouraria, mudo a situação de pagamento de um sócio e a lista do dia mostra.
- [ ] Entro como sócio e não consigo mudar a situação de ninguém, nem a minha (teste por persona).

## Fase 4 · Publicar (a fazer)

**Objetivo:** os sócios do clube usam o produto de verdade.
**Entregas:** degrau 5 com comando, em dois tamanhos de tela; ida a produção com a lista autorizada.
**Pronto quando:**
- [ ] Abro o endereço do clube no celular, sem entrar, e vejo os horários livres da semana.
- [ ] Como visitante, no endereço que o clube usa, não recebo nome nem telefone de ninguém.

## Quando tiver dúvida

Decida e registre em `docs/decisoes.md`. Sobre bloco e cancelamento (ADR-005, ADR-004), pergunte.
