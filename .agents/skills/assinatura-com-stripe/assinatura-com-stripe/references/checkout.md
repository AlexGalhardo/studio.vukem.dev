# Checkout: como vender a assinatura com teste pago e período de avaliação?

Leia quando: for combinar o plano com o dono (passo 1 do fluxo) ou escrever a ação que abre o
checkout (passo 4).
Não é aqui: o que acontece depois do pagamento (`references/webhook.md`).

## O mínimo

- Dois preços criados pelo dono: o recorrente do plano e um avulso de entrada. Os ids vêm de
  variável de ambiente.
- Quem nunca assinou paga o avulso e ganha os dias de avaliação. Quem já assinou assina direto.
- Quem já tem o plano, ou tem cobrança pendente, vai para a página da conta, e não para outro
  checkout.
- A pessoa é identificada em dois lugares da sessão, para o webhook achá-la em todo evento.
- A tela de volta não libera nada: ela espera o webhook.

Conteúdo: 1. O que o dono cria 2. Como o teste pago funciona 3. A ação, passo a passo 4. A volta
do checkout 5. O preço na tela

## 1. O que o dono cria

O painel do Stripe é do dono. Entregue a ele esta lista e peça só os ids de preço, que não são
segredo. Chave secreta não vem para a conversa (`references/producao.md` §2).

| O quê | Onde | Vira a variável |
| --- | --- | --- |
| Produto do plano, com um preço recorrente | painel, nos dois modos | `STRIPE_PRICE_PLAN` |
| Preço avulso de entrada, se houver teste pago | painel, nos dois modos | `STRIPE_PRICE_TRIAL` |
| Dias de avaliação | decisão do dono | constante no código, com teste |

"Nos dois modos" é literal: o modo de teste e o de produção têm objetos separados, com ids
diferentes. Um id de um modo não existe no outro.

## 2. Como o teste pago funciona

| Peça | Parâmetro | Efeito |
| --- | --- | --- |
| Preço recorrente | `line_items[0]` | é a assinatura |
| Preço avulso | `line_items[1]` | entra só na primeira fatura |
| Avaliação | `subscription_data.trial_period_days` | adia a primeira cobrança do recorrente; no mínimo 1 dia |

Resultado: a pessoa paga o valor de entrada na hora, a assinatura nasce `trialing` e, ao fim dos
dias, o Stripe cobra o preço recorrente sozinho. `trialing` dá o plano: é por isso que a função de
acesso aceita os dois status.

- Sem o preço avulso configurado, o checkout abre sem avaliação, com cobrança cheia na hora. O
  código trata a variável ausente como "sem teste", e não como erro.
- O teste vale uma vez por pessoa. A regra mais simples que funciona: só recebe quem não tem linha
  na tabela de assinatura. Quem cancelou e volta assina direto.
- O que a primeira fatura cobra nesse arranjo foi visto em uso com a versão 23 do pacote. Antes de
  anunciar o valor ao público, faça uma compra no modo de teste e leia a fatura.
- O texto da página de vendas tem de dizer o valor de entrada, os dias e o valor que vem depois.
  Esse texto é do dono.

## 3. A ação, passo a passo

O molde está em `assets/moldes/checkout.ts`. A ação de servidor que o chama faz, nesta ordem:

1. **Guarda de usuário**, na primeira linha. Visitante vai para o login e volta.
2. **Lê a linha de assinatura da própria pessoa**, com o cliente da sessão. Erro de leitura
   devolve uma frase de erro: sem saber o estado, não se abre checkout.
3. **Bloqueia o segundo checkout.** Com `active`, `trialing`, `past_due`, `unpaid` ou `paused`,
   redireciona para a conta. `incomplete` pode tentar de novo: é o primeiro pagamento que não
   fechou, e expira sozinho.
4. **Confere a configuração.** Sem chave ou sem o preço do plano, devolve "a assinatura ainda não
   está disponível". Nenhuma página pública cai por falta de variável do Stripe.
5. **Cria a sessão** e redireciona para o endereço que o Stripe devolveu.

Os parâmetros que ligam a sessão à pessoa:

```ts
subscription_data: { metadata: { user_id: user.id } },  // segue a assinatura em todo evento
client_reference_id: user.id,                            // reserva, só no evento da sessão
customer: linha.stripe_customer_id,                      // quem volta reusa o mesmo cliente
customer_email: user.email,                              // quem nunca assinou; nunca os dois
```

- O id de usuário vem da sessão do servidor. Nunca do formulário, da URL ou do navegador.
- O endereço de sucesso e o de cancelamento são montados no servidor, com o endereço público do
  site. Um caminho de volta recebido do navegador passa por validação: só caminho interno.
- A ação não escreve na tabela de assinatura, nem "para adiantar".

## 4. A volta do checkout

A pessoa pode voltar do Stripe antes de o webhook chegar. Sem tratar isso, ela paga e vê a tela
de quem não pagou.

1. Ponha uma marca no endereço de sucesso, por exemplo `?assinatura=ok`.
2. Com a marca, a página mostra "liberando seu acesso" e pede o estado ao servidor de novo a cada
   2 segundos, por até 30.
3. Quando a função de acesso passa a dizer sim, a página mostra o conteúdo e tira a marca.
4. Passados os 30 segundos, diga que o pagamento foi recebido e que o acesso chega em instantes,
   com o caminho para o suporte. Não libere por conta própria.

A mesma marca serve para a pausa e para a retomada, que também esperam o webhook
(`references/portal.md` §3).

## 5. O preço na tela

- Leia o valor do preço recorrente na API e formate. O valor não fica escrito no código nem em
  texto fixo: quando o dono mudar o preço no painel, a tela acompanha.
- Guarde em cache de horas, compartilhado: não depende de quem está logado.
- Erro do Stripe não entra no cache. Se entrar, "sem preço" fica guardado por horas.
- Sem chave, ou com o Stripe fora do ar, a linha do preço some e a página continua de pé.

## O que evitar

- **Criar o cliente do Stripe em vários arquivos.** A chave se espalha. Um módulo lê a chave e
  cria o cliente; o teste de fronteira prende isso (`assets/moldes/fronteira.test.ts`).
- **Abrir checkout de quem volta sem o `customer` da linha.** O Stripe cria um segundo cliente
  para a mesma pessoa, e as faturas dela se dividem em dois. Passe `customer` ou `customer_email`,
  nunca os dois.
- **Dar o teste a quem já assinou.** A pessoa cancela e volta a cada ciclo pelo valor de entrada.
- **Confiar no id de preço como prova de modo.** O modo é o da chave. Preço de um modo com chave
  do outro dá erro de "objeto não existe".
- **Registrar o objeto de erro inteiro no log.** Ele carrega dados da requisição. Registre o tipo
  e o código.

## Pronto quando

- [ ] O teste da ação cobre os três casos: nunca assinou, já assinou, bloqueado.
- [ ] A ação começa pela guarda e não importa o cliente do banco com a chave de serviço.
- [ ] No modo de teste, a compra termina em `trialing` gravado pelo webhook, e a tela libera
      sozinha.
- [ ] O dono leu a primeira fatura no modo de teste e confirmou o valor.

Volte ao `SKILL.md`, passo 5.
