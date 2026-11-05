# Cancelamento: como saber por que a pessoa sai e ainda oferecer um motivo para ficar?

Leia quando: o dono pedir formulário antes de cancelar, oferta de desconto, pausa como alternativa
ou um painel de motivos (passo 6 do fluxo).
Não é aqui: as duas configurações do portal e a mecânica da pausa (`references/portal.md`).

## O mínimo

- Avise o dono do risco antes de escrever uma linha. A decisão é dele, e fica registrada.
- A ordem é: formulário, oferta de desconto, oferta de pausa, tela de cancelamento do Stripe.
- A obrigatoriedade vale no servidor. As três ações que vêm depois só andam com uma resposta
  completa, pendente e recente.
- O desconto e o texto dele são lidos do Stripe. O código não conhece o valor.
- Nenhuma dessas ações escreve na tabela de assinatura.

Conteúdo: 1. O aviso ao dono 2. O portão no servidor 3. O formulário 4. A oferta de retenção
5. A pausa como alternativa 6. Seguir para cancelar 7. O painel de motivos

## 1. O aviso ao dono

Barreira para cancelar tem custo: atrito, reclamação pública, estorno pedido direto ao cartão e,
em vários lugares, regra de consumo que pede que cancelar seja tão fácil quanto assinar. Diga isso
uma vez, com a alternativa (formulário curto, com opção de pular). Se o dono mantiver o
obrigatório, cumpra e registre quem decidiu. A regra de cada país é assunto para o advogado dele:
esta skill não avalia a legalidade.

Deixe o formulário em um arquivo só. Se virar reclamação, encurtar é a primeira correção.

## 2. O portão no servidor

A tela pode ser pulada com uma chamada direta. Por isso a regra mora nas ações:

```ts
// Abre toda ação que vem DEPOIS do formulário: aceitar o desconto, pausar, seguir para cancelar
const user = await requireUser(caminhoDoCancelamento);
const contexto = await carregarContextoDoCancelamento(user.id);
if (typeof contexto === "string") return fail(contexto);   // nada tocou o Stripe
```

O contexto só existe com as duas coisas:

1. A assinatura da pessoa é cancelável: `trialing`, `active` ou `past_due`, sem cancelamento
   marcado.
2. Há uma resposta dela que seja, ao mesmo tempo, das últimas 24 horas, ainda `pending` e completa.

- **Completa se confere de novo.** A pessoa pode gravar a própria linha pela API do banco, sem
  passar pela tela. A prova do formulário é a validação das respostas gravadas contra o esquema, e
  não a existência da linha.
- **Resposta usada não vale de novo.** Depois de mudar o Stripe, a ação grava o desfecho na
  resposta (`discount`, `paused` ou `cancel`), com a condição "só se ainda está `pending`". Quem
  volta do Stripe sem cancelar responde outra vez.
- **Gravar o desfecho nunca lança.** Quando essa linha roda, o Stripe já mudou. Uma falha ali vai
  para o log e não desfaz nem esconde o que aconteceu.
- O teste de fronteira confere que o portão vem antes de qualquer chamada ao Stripe em cada uma
  das três ações: procure o índice de cada chamada no texto da função e compare.

## 3. O formulário

- As perguntas ficam em um arquivo de código, e um esquema de validação é gerado delas. A coluna
  de respostas é um objeto JSON, com teto de tamanho (16 KB no molde): trocar uma pergunta não pede
  migração. A tabela está no fim de `assets/moldes/tabelas.sql`.
- Guarde o rascunho no navegador, por sessão, para a pessoa não perder as respostas ao recarregar.
- Poucas perguntas rendem mais respostas boas. Peça ao menos: motivo principal (lista fechada),
  quando decidiu, com que frequência usava, o que acha do preço, para onde vai, nota de 0 a 10 e
  um campo aberto.
- Grave junto o status da assinatura na hora da resposta: separa quem saiu no teste de quem saiu
  pagando.

## 4. A oferta de retenção

O dono cria o desconto no painel, nos dois modos, e põe o id numa variável opcional. Sem a
variável, a etapa não existe e o fluxo pula para a pausa.

| | Cupom | Código promocional |
| --- | --- | --- |
| O que é | a regra do desconto | um código que aponta para um cupom |
| Quem desconta de verdade | ele: percentual ou valor fixo, e por quanto tempo | o cupom por trás |
| Como reconhecer o id | qualquer outro valor | prefixo `promo_` |
| Parâmetro na assinatura | `discounts: [{ coupon: id }]` | `discounts: [{ promotion_code: id }]` |
| Antes de oferecer, confira | `valid` | `active`, e o cupom por trás |

O que o desconto faz depende de três campos do cupom, lidos na API:

| Campo | Valores | O texto da oferta diz |
| --- | --- | --- |
| `duration` | `once` | "na próxima cobrança", e que depois volta ao preço normal |
| | `repeating`, com `duration_in_months` | "pelos próximos N meses", e que depois volta |
| | `forever` | "enquanto você continuar assinando" |
| `percent_off` | maior que 0 e menor que 100 | preço menos o percentual, arredondado na menor unidade |
| `amount_off` | inteiro, na mesma moeda do preço | preço menos o valor |

A oferta **não aparece** quando: o cupom está inválido; o código promocional está inativo; a moeda
do valor fixo é outra; o resultado não fica acima de zero e abaixo do preço cheio; a duração é um
valor que o código não sabe descrever. É melhor não oferecer do que prometer errado.

- Calcule o valor com desconto numa função pura, com teste. Nunca escreva o valor no texto.
- A oferta vale uma vez por pessoa: antes de aplicar, procure uma resposta dela com o desfecho
  `discount`.
- O desconto entra na assinatura que já existe e aparece a partir da próxima cobrança: o período
  atual já foi pago.
- A conferir na documentação do Stripe: onde o cupom fica dentro do código promocional na sua
  versão da API (na 23 do pacote, em `promotion.coupon`, pedido com `expand`); e o que acontece
  com um desconto que a assinatura já tinha quando `discounts` é enviado.

## 5. A pausa como alternativa

Ofereça depois do desconto, com o prazo dito em dias (30 é o ponto de partida; o dono decide) e o
que acontece com o acesso nesse período. A ação é a de `references/portal.md` §3, atrás do portão da §2, e grava o
desfecho `paused`.

## 6. Seguir para cancelar

A última ação abre a tela de cancelamento do Stripe, direto na assinatura da pessoa:

```ts
flow_data: {
  type: "subscription_cancel",
  subscription_cancel: { subscription: idDaAssinatura },
  after_completion: { type: "redirect", redirect: { return_url: urlDaConta } },
}
```

A sessão usa a configuração `cancel` do portal. O cancelamento vale no fim do período pago: a
pessoa mantém o acesso até lá, e o webhook grava a marca de "vai terminar". Grave o desfecho
`cancel` ao redirecionar: ele significa "seguiu para a tela", e não "cancelou". Quem cancelou de
fato é o que a tabela de assinatura diz depois.

## 7. O painel de motivos

Só o administrador lê as respostas de todos. Mostre, nesta ordem:

1. Contagem por desfecho: ficou com desconto, pausou, seguiu para cancelar, não concluiu
   (`pending` com mais de 24 horas).
2. Contagem de cada pergunta fechada, da mais votada para a menos.
3. Média das notas e, se houver a pergunta de 0 a 10, o NPS: percentual de 9 e 10 menos o
   percentual de 0 a 6.
4. As 50 respostas mais recentes, com os campos abertos.

A resposta guarda o usuário com "ao apagar a conta, vira nulo": o motivo continua valendo depois
que a pessoa vai embora.

## O que evitar

- **Travar a tela e deixar a ação aberta.** Uma chamada direta cancela sem responder.
- **Aceitar a existência da linha como prova.** Qualquer pessoa logada grava a própria linha.
- **Texto de oferta fixo.** O dono troca o cupom no painel e a tela passa a prometer outra coisa.
- **Oferecer desconto de 100%.** Não é "continuar por um preço". A conta recusa.
- **Esconder o caminho de cancelar.** O link fica na página da conta, com esse nome.

Volte ao `SKILL.md`, passo 7.
