# Portal e pausa: como deixar a pessoa cuidar da assinatura sem furar as regras?

Leia quando: for montar a página da conta (passo 5 do fluxo): trocar o cartão, ver as faturas,
pausar e retomar.
Não é aqui: o formulário e as ofertas antes de cancelar (`references/cancelamento.md`).

## O mínimo

- O portal do cliente é a tela do Stripe para cartão, faturas e dados. O aplicativo só abre uma
  sessão dele e redireciona.
- Se cancelar tem formulário, o portal de "gerenciar" não pode ter o botão de cancelar. Use duas
  configurações, criadas pelo próprio aplicativo.
- Pausar e retomar mudam a assinatura no Stripe. Quem grava o estado novo é o webhook.
- No Stripe, pausar a cobrança não muda o status da assinatura. A tradução para "pausada" é sua.

Conteúdo: 1. Duas configurações 2. Qual abrir 3. Pausa e retomada 4. O que a página da conta
mostra

## 1. Duas configurações

| Papel | Quem abre | Cartão, faturas, dados | Cancelar |
| --- | --- | --- | --- |
| `manage` | o botão "Gerenciar assinatura" | ligado | desligado |
| `cancel` | só a última etapa do cancelamento | ligado | ligado, no fim do período pago, sem acerto proporcional |

O código está em `assets/moldes/portal.ts`. Como ele mantém as duas:

1. **Achar ou criar.** Cada configuração leva uma chave de metadata com o papel. O código lista as
   ativas, procura a do papel e só cria se não achar. Vale igual nos dois modos: a primeira
   abertura do portal em cada modo cria a configuração daquele modo.
2. **Consertar antes de usar.** Alguém pode ter mexido no painel. Se a configuração achada tem a
   função de cancelar diferente do que o papel exige, o código corrige e só então usa. A de
   gerenciar nunca sai dali oferecendo cancelamento.
3. **Guardar o id em memória**, por cliente do Stripe, para não listar a cada clique.
4. **Refazer uma vez** se o id guardado deixou de servir (configuração apagada ou desativada): o
   erro vem com o parâmetro `configuration`; esqueça o id, procure de novo e tente só mais uma vez.

Com isso, o dono não configura o portal à mão. Diga a ele para não apagar nem editar as duas. Se a
conta exige algum passo no painel para o portal funcionar (ativação, dados do negócio): a
conferir na documentação do Stripe, e é passo do dono.

Se o produto não tem formulário de cancelamento, uma configuração basta: a `cancel`, aberta pelo
botão de gerenciar.

## 2. Qual abrir

| Situação da pessoa | Configuração | Por quê |
| --- | --- | --- |
| Assinatura viva, sem cancelamento marcado | `manage` | cancelar passa pelo formulário |
| Cancelamento já marcado | `cancel` | foi nela que se viu a opção de desfazer o cancelamento, e a pessoa já respondeu o formulário |
| Sem linha de assinatura | nenhuma | devolva "você ainda não tem assinatura para gerenciar" |

A ação que abre o portal começa pela guarda de usuário e usa o id de cliente da linha da própria
pessoa. Se o id viesse do navegador, uma pessoa abriria o portal de outra.

## 3. Pausa e retomada

```ts
// Pausar por 30 dias: as faturas do período são anuladas e a cobrança volta sozinha na data
await stripe.subscriptions.update(subscriptionId, {
  pause_collection: { behavior: "void", resumes_at: agoraEmSegundos + 30 * 24 * 60 * 60 },
});

// Retomar agora: valor vazio tira a pausa
await stripe.subscriptions.update(subscriptionId, { pause_collection: "" });
```

- **O status não muda no Stripe.** Com `pause_collection` preenchido, a assinatura continua com o
  status que tinha. Se a pausa tira o acesso no seu produto, o webhook grava `paused` quando a
  assinatura viva tem `pause_collection`, e volta ao status do Stripe quando ele some (função
  `storedStatus`, em `assets/moldes/acesso.ts`). Se a pausa mantém o acesso, grave o status como
  veio. A escolha é do dono: pergunte.
- **Só assinatura viva vira `paused`.** Uma que já terminou, ou que nem fechou o primeiro
  pagamento, fica com o status do Stripe, mesmo com a pausa preenchida.
- **A data da volta fica no Stripe.** A tabela guarda só o status. Para mostrar "pausada até
  dd/mm", leia `pause_collection.resumes_at` da assinatura. Se a leitura falhar, mostre "assinatura
  pausada" sem a data, e não um erro.
- **Depois de pausar ou retomar, a página espera o webhook**, com a mesma marca no endereço e a
  mesma espera da volta do checkout (`references/checkout.md` §4).
- **Retomar não pede formulário.** Voltar a pagar tem de ser um clique.
- A conferir na documentação do Stripe: que a mudança de `pause_collection` chega como
  `customer.subscription.updated` (o evento `customer.subscription.paused` é de outro mecanismo);
  o que cada `behavior` faz com as faturas; e se a pausa desloca ou não a data do ciclo. Decida o
  texto mostrado à pessoa depois de conferir: "sem cobrança por 30 dias" só vale se for verdade.

## 4. O que a página da conta mostra

Uma função pura recebe a linha da assinatura e devolve o título, a frase e o que oferecer. Quem
decide o acesso continua sendo a função de acesso: aqui é só texto.

| Estado | Título | Oferece |
| --- | --- | --- |
| Sem linha | sem assinatura | assinar |
| `trialing` | em teste até a data | gerenciar, cancelar |
| `active` | ativa; próxima cobrança na data | gerenciar, cancelar |
| `active` ou `trialing`, marcada para terminar | cancelada, com acesso até a data | portal `cancel`, para desfazer |
| `paused` | pausada até a data | retomar agora |
| `past_due`, `unpaid`, `incomplete` | pagamento pendente | atualizar a forma de pagamento |
| `canceled`, `incomplete_expired` | sem assinatura ativa | assinar de novo |

Formate a data no fuso do público, e não no do servidor. Data ausente ou inválida: o título sai
sem data.

## O que evitar

- **Deixar o portal padrão do painel aberto com cancelamento** quando há formulário obrigatório.
  A pessoa cancela por ali em dois cliques e o formulário não vale nada.
- **Gravar "pausada" na ação de pausar.** É a segunda escrita na tabela. Se a chamada ao Stripe
  falhar depois, o banco mente.
- **Mostrar a pausa lendo `pause_collection` em toda página.** É uma chamada à API por pedido.
  Leia só na página da conta, e só para quem está com o status `paused`.
- **Oferecer pausa a quem já está marcado para terminar.** Cancelável é: `trialing`, `active` ou
  `past_due`, sem cancelamento marcado.

## Pronto quando

- [ ] O teste das configurações cobre: achar, criar, consertar a que foi mexida e refazer com o id
      velho.
- [ ] "Gerenciar" abre o portal sem a opção de cancelar, se há formulário.
- [ ] Pausar leva a `paused` gravado pelo webhook, e a função de acesso passa a dizer não.
- [ ] Retomar devolve o status do Stripe, e a página mostra o estado novo sem recarregar à mão.

Volte ao `SKILL.md`, passo 6.
