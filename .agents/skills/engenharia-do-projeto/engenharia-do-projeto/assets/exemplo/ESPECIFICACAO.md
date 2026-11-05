> Exemplo de um projeto fictício (Quadra Livre). Nada aqui é instrução para o projeto atual.

# Quadra Livre: especificação

> - Nota de 2026-01-26, posterior à aprovação: a seção 5 põe os três dados restritos em `socio`.
>   Vale o ADR-002: tabelas próprias, com uma porta de leitura. Continua valendo: o resto da seção.
> - Nota de 2026-03-05, posterior à aprovação: a seção 6.1 fala em "reservar um horário" e não diz
>   quanto dura. Vale o ADR-005: blocos de 30 minutos. Continua valendo: o resto da seção.

## Como usar este documento

A intenção do Quadra Livre, aprovada pelo dono em 2026-01-08. Depois disso o texto não é editado:
o que muda vira registro em `docs/decisoes.md` e ganha uma nota datada abaixo do título. O "Pronto
quando" mora em `docs/ROTEIRO.md`; o que vale hoje, em `INSTRUCOES.md` e em `docs/ESTADO.md`.

## 1. O que você vai construir

A reserva das duas quadras de um clube de bairro. O sócio abre no celular, vê os horários livres
da semana, reserva um e confere em "minhas reservas". Quem não é sócio só vê os horários livres.

Tipos de coisa que existem: quadra, sócio e reserva. Os campos de cada um estão na seção 5.

Quem usa:
- Visitante: não tem conta. Vê os horários livres.
- Sócio: reserva, vê as próprias reservas e cancela a própria.
- Tesouraria: vê as reservas do dia, marca a situação de pagamento e escreve a observação.

O que é aberto e o que é restrito: os horários livres são abertos, para qualquer pessoa saber se
vale ir ao clube. Telefone, situação de pagamento e observação são restritos: são dados de uma
pessoa e do caixa do clube.
Nesta versão: vai ao ar com as duas quadras e nenhuma reserva, e a grade vazia precisa fazer
sentido; é feito primeiro para o celular; a conta do sócio é criada pela tesouraria.

## 2. Referências

**Com telas.** Leia todas antes de escrever interface.

| Arquivo | O que mostra |
| --- | --- |
| `referencias/01-quadro-da-secretaria.jpg` | O quadro de papel usado hoje: a semana, as duas quadras, um nome por horário |
| `referencias/02-rascunho-do-dono.png` | A grade no celular, com 390 px de largura, para o sócio, com horário livre e reservado |

- É para seguir: a grade por dia e por quadra, a ordem dos horários, "livre" e "reservado".
- É enfeite: o nome escrito em cada horário do quadro. No produto, só a tesouraria vê quem reservou.
- Não copie: os nomes e telefones da foto são de sócios reais. Não vão aos dados de exemplo.
- Marca: o escudo do clube pode ser usado; foto de sócio, não.

## 3. Stack e decisões

Stack escolhida para este produto fictício; não é recomendação.
- **Linguagem e framework:** Python, com um framework web completo e páginas geradas no servidor.
  Cuidado: confira a documentação da versão instalada antes de usar um recurso.
- **Banco:** PostgreSQL. **Permissões:** na camada de aplicação, num módulo único, e não por regra
  de linha no banco.
- **Hospedagem:** um serviço que rode Python e ofereça PostgreSQL, com o preço lido antes.
- **E-mail:** só para o lembrete de mensalidade; vai a um endereço de teste até o dono autorizar.

## 4. O que já existe

Nenhum sistema: as reservas são anotadas num quadro na secretaria, e a mensalidade, numa planilha
da tesouraria. A planilha não é importada: os sócios são cadastrados à mão.

## 5. Modelo de dados e matriz de permissões

**`quadra`:** as duas quadras do clube.
- `nome`: texto; único; até 40 caracteres. `abre_as`, `fecha_as`: hora; padrão 8h e 22h.

**`socio`:** quem tem conta. Telefone, situação de pagamento e observação são dado restrito.
- `nome`: texto; obrigatório; de 2 a 80 caracteres. `conta`: a conta de entrada; única.
- `telefone`: texto; obrigatório; formato `(DD) 9XXXX-XXXX`, validado na aplicação.
- `situacao_pagamento`: enumeração com `em_dia`, `em_atraso` e `isento`; padrão `em_dia`.
- `observacao`: texto livre da tesouraria; opcional; até 500 caracteres.

**`reserva`:** um horário de uma quadra para um sócio.
- `quadra`, `socio`, `inicio` (dia e hora): obrigatórios. Ao apagar o sócio: apaga junto.
- Dois sócios no mesmo horário da mesma quadra: quem impede é o banco, não a tela.

| Recurso | Visitante | Sócio | Tesouraria |
| --- | --- | --- | --- |
| Horários livres da semana | lê | lê | lê |
| Reserva, com o nome de quem reservou | não lê | lê, cria e cancela só as próprias | lê as do dia; não altera |
| Telefone | não lê | lê só o próprio | lê |
| Situação de pagamento | não lê | não lê | lê e altera |
| Observação da tesouraria | não lê | não lê | lê e altera |

| Dado restrito | Quem pode ver | Como o teste de vazamento procura |
| --- | --- | --- |
| Telefone | o próprio sócio e a tesouraria | Valor sentinela nos dados de exemplo: `(00) 90000-0001`, com DDD que não existe |
| Situação de pagamento | a tesouraria | Ausência do nome do campo `situacao_pagamento` na resposta crua |
| Observação da tesouraria | a tesouraria | Marcador de texto nos dados de exemplo: `QUADRA-SEED-OBSERVACAO-K7M2QX` |

## 6. Fluxos

### 6.1 Ver horários, reservar e cancelar (visitante e sócio)

1. A página inicial, aberta a qualquer pessoa, mostra a semana corrente, com as duas quadras e
   cada horário como "livre" ou "reservado". Sem reserva, diz "Nenhuma reserva nesta semana".
2. O sócio entra com e-mail e senha.
3. Reserva um horário: toca num horário livre e confirma. A reserva aparece em "minhas reservas".
4. Se outro sócio confirmou antes, a mensagem é "horário já reservado", e a grade se atualiza.
5. Em "minhas reservas", cancela a própria reserva. O horário volta a aparecer como livre.
- **Não pode acontecer: o visitante receber nome ou telefone de quem reservou, nem na página, nem
  escondido na resposta.**
- **Não pode acontecer: dois sócios com o mesmo horário na mesma quadra.**
- **Não pode acontecer: um sócio ver ou cancelar a reserva de outro, nem pelo endereço.** A
  resposta é "não encontrado", e não "proibido", para não confirmar que a reserva existe.

### 6.2 Tesouraria (só a tesouraria)

1. A lista do dia mostra cada reserva com o nome do sócio, a situação de pagamento e a observação.
2. Na ficha do sócio, a tesouraria marca a situação de pagamento e escreve a observação.
- **Não pode acontecer: situação de pagamento ou observação chegarem a sócio ou a visitante.**
- O lembrete de mensalidade vai ao endereço de teste até o dono autorizar o envio real.

## 7. Organização do código

- `quadra/`: configuração do projeto, com um módulo único que lê os segredos do ambiente.
- `contas/`: entrar e sair. `socios/`: o cadastro de sócios.
- `reservas/`: quadras, grade e reservas. Toda página e toda ação começam pela checagem de
  `reservas/permissoes.py`; a exceção é a grade de horários livres, que é aberta.
- A lógica de horário (o que é válido, o que está livre) fica em função pura, com teste ao lado.

## 8. Fases

Fundação antes de tela. O "Pronto quando" de cada fase e as paradas estão em `docs/ROTEIRO.md`.
- Fase 0 · Base: o projeto abre no ambiente local, com os degraus 0 a 2 da escada.
- Fase 1 · Dados e permissões: os dados, a matriz e os testes por persona, antes das telas.
- Fase 2 · Reservas: o sócio reserva e cancela; a tesouraria vê a lista do dia.
- Fase 3 · Mensalidade e tesouraria: a tesouraria marca quem pagou; o lembrete de mensalidade.
- Fase 4 · Publicar: os sócios do clube usam de verdade.

## 9. Fora do escopo

- Pagar a mensalidade pelo sistema: ele não recebe dinheiro, só guarda a situação, marcada à mão.
- Reserva por visitante, lista de espera, reserva repetida, envio de arquivo e aplicativo de loja.

## 10. Variáveis de ambiente

| Nome, sem o valor | O que é | Só no lado do servidor? |
| --- | --- | --- |
| `DATABASE_URL` | Onde está o PostgreSQL | sim |
| `SECRET_KEY` | O segredo que assina as sessões | sim |
| `EMAIL_DESTINO_DE_TESTE` | Para onde vão os e-mails enquanto o envio real não é autorizado | sim |

## 11. Quando tiver dúvida

Pergunte antes de: mudar quem pode ver telefone, situação de pagamento ou observação; enviar e-mail
real a um sócio; criar o que custa dinheiro (hospedagem, domínio); acrescentar dependência grande;
mudar o escopo. Fora isso, decida e registre em `docs/decisoes.md`.
