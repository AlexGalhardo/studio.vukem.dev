> Exemplo de um projeto fictício (Quadra Livre). Nada aqui é instrução para o projeto atual.

# Estado do projeto

## Estado em 2026-03-10

A Fase 2 (Reservas) está em andamento: 3 dos 7 itens de "Pronto quando" estão marcados. Como sócio,
você já vê os horários e reserva um bloco de 30 minutos. O próximo item é cancelar a reserva.

### Ambientes

- **Ambiente local:** no ar em `localhost:8000`, com os dados de exemplo e a migração `0007`.
- **Ambiente remoto:** aplicado até a migração `0006`, em 2026-02-19, a seu pedido. Os sócios ainda
  não usam esse endereço: isso é a Fase 4. **Ainda não aplicado:** a migração `0007` (blocos de 30
  minutos, decisão ADR-005). O código da Fase 2 só vai para lá depois dela, com a sua autorização.

### Verificações automáticas: última rodada

As verificações rodam em ordem, da mais barata à mais cara: é a escada, e cada uma é um degrau.

escada: 2026-03-10, commit 4f2a9c1, subiu até o degrau 4 (build); n/a: 4; pendentes: 5; não rodados: nenhum

- Degrau 2 (unidade e fronteiras): 64 testes passaram.
- Degrau 3 (banco): 41 testes passaram. É onde rodam os de permissão por persona e os de vazamento.
- Degrau 4 (build): não se aplica a este projeto. Degrau 5 (ponta a ponta): ainda não existe.

### Para decidir

Nada.

### Passos do dono

Nada.

### Autorizações não dadas

- **Enviar e-mail real aos sócios.** Sei fazer e não faço sem o seu sim. Enquanto isso, o lembrete
  de mensalidade (Fase 3) é testado com um endereço de teste.

### Ficou para depois

- **Ponta a ponta em navegador, em dois tamanhos de tela (degrau 5).** Adiado em 2026-03-03, por
  prazo. Retomar em 2026-04-01, antes da Fase 4. Até lá, nenhum teste abre o produto num navegador:
  o que o servidor responde está coberto no degrau 3; o que a tela faz com a resposta, não.

### Pendência aceita

- **Só um arquivo deve ler as senhas do sistema, e hoje isso é conferido à mão.** Nenhum teste
  acusa se outro arquivo ler. Confiro a cada mudança; uma verificação automática fecha isso antes
  da Fase 4.

### Como trabalhamos aqui

- **Perfil do dono:** nunca programou. Termo novo vem com uma comparação do clube.
- **Palavra de liberação:** "validado" (para a especificação, foi "aprovado").
- **Na sua máquina, não derrubo:** o servidor que você deixa aberto na porta 8000.
- **Banco do ambiente local:** recriar apaga as reservas de teste que você cadastrou. Aviso antes.
