# Webhook: como gravar a assinatura sem dar o plano a quem não pagou?

Leia quando: for escrever ou revisar a rota que recebe os eventos do Stripe (passo 3 do fluxo), ou
quando o sintoma for "paguei e não liberou", evento com erro ou status que regride.
Não é aqui: criar a sessão de checkout (`references/checkout.md`).

## O mínimo

- A rota lê o corpo como texto e repassa: nenhuma regra mora nela.
- Sem assinatura válida sobre o corpo cru, nada é lido nem gravado.
- O evento só diz qual assinatura mudou. O que se grava é o estado atual, buscado no Stripe.
- O id do evento é marcado depois de gravar. Falha no meio responde 500, e o Stripe reenvia.
- Evento que não dá para ligar a uma pessoa responde 200 e vai para o log: reenviar não resolve.

Conteúdo: 1. A rota 2. Conferir a assinatura 3. Não processar duas vezes 4. Evento fora de ordem
5. Evento e status 6. De quem é a assinatura 7. Casos de teste 8. A camada de banco

## 1. A rota

```ts
// O corpo é lido CRU: a assinatura vale sobre o texto exato que o Stripe enviou.
// Um parser de JSON antes disso muda o texto e a conferência falha.
export async function POST(request: Request) {
  const rawBody = await request.text();
  const result = await handleStripeWebhook(rawBody, request.headers.get("stripe-signature"), deps);
  return Response.json(result.body, { status: result.status });
}
```

Tire a rota de qualquer camada que exija sessão ou cookie: quem chama é o Stripe, sem login. Em
outro framework, pegue o corpo antes do parser de JSON global (a forma de cada um: a conferir na
documentação dele). O manipulador completo está em `assets/moldes/webhook.ts`.

## 2. Conferir a assinatura

| Situação | Resposta | Por quê |
| --- | --- | --- |
| Falta o segredo do webhook no servidor | 500 | o Stripe reenvia depois de configurado |
| Falta o cabeçalho, não confere ou o corpo foi alterado | 400 | não veio do Stripe |
| Assinatura velha demais | 400 | o pacote recusa por padrão acima de 300 segundos, contra repetição |

Use `constructEvent` do pacote do Stripe, com o corpo cru, o cabeçalho e o segredo do endpoint.
Onde não há a biblioteca de criptografia do Node, existe `constructEventAsync`. Nunca use
`constructEventWithoutVerification` fora de teste: ele monta o evento sem conferir nada.

## 3. Não processar duas vezes

1. Consulte o id do evento na tabela de eventos. Já está lá: responda 200 e pare.
2. Processe.
3. Só então grave o id.

A ordem importa. Marcar antes de processar perde o evento se a gravação falhar: o reenvio chega,
acha o id e é descartado. Se só a marca falhar, registre no log e responda 200: a gravação já
aconteceu e repetir o mesmo evento dá no mesmo estado. Id repetido na inserção (duas entregas ao
mesmo tempo) não é erro.

## 4. Evento fora de ordem

O Stripe não garante a ordem de entrega, e reenvia eventos antigos. Por isso o retrato que vem
dentro do evento não é gravado. Três regras cobrem os casos:

- **Busque a assinatura atual** pelo id e grave o que a API devolver. Um `updated` antigo que
  chega depois do `deleted` grava "cancelada", porque é o que a assinatura é agora.
- **Assinatura que sumiu do Stripe** (erro `resource_missing`): só o retrato de um evento de fim
  (`canceled`, `incomplete_expired`) vale. Qualquer outro pode estar velho: ignore.
- **Outra assinatura da mesma pessoa:** evento de uma assinatura antiga, que não dá o plano, não
  sobrescreve a linha de outra que dá. O contrário sobrescreve: uma nova que dá o plano substitui
  a antiga. A mesma assinatura sempre se atualiza, inclusive para tirar o plano.

## 5. Evento e status

| Evento | O que o manipulador faz |
| --- | --- |
| `checkout.session.completed` | se a sessão é de assinatura, sincroniza a assinatura dela; `client_reference_id` é a reserva para achar a pessoa |
| `customer.subscription.created` e `updated` | sincroniza com o estado atual |
| `customer.subscription.deleted` | sincroniza; é o caso em que o retrato do evento pode valer (§4) |
| qualquer outro | 200, sem tocar no banco |

| Status gravado | Dá o plano | O que a tela oferece |
| --- | --- | --- |
| `trialing`, `active` | sim | gerenciar; se marcada para terminar, "acesso até a data" |
| `paused` | não | retomar agora |
| `past_due`, `unpaid` | não | atualizar a forma de pagamento; não abre checkout novo |
| `incomplete` | não | tentar o checkout de novo |
| `canceled`, `incomplete_expired` | não | assinar de novo |

- Copie o status do Stripe. A única tradução é a pausa: assinatura viva com `pause_collection`
  preenchido é gravada como `paused` (`references/portal.md` §3).
- Status que o seu tipo enumerado não conhece: lance erro e responda 500. Gravar um palpite dá
  ou tira acesso sem ninguém ver.
- Marcada para terminar: trate `cancel_at_period_end` verdadeiro ou `cancel_at` com data como a
  mesma coisa. No pacote conferido os dois campos existem; qual deles o portal preenche em cada
  versão da API: a conferir na documentação do Stripe.
- Fim do período: nas versões novas fica em cada item da assinatura, nas antigas na própria
  assinatura. Leia dos dois lugares e, com vários itens, use o que vence primeiro.

## 6. De quem é a assinatura

Procure nesta ordem e pare no primeiro que tiver o formato do id de usuário do sistema:

1. `metadata.user_id` da assinatura, gravado pelo checkout.
2. `client_reference_id` da sessão (só no evento da sessão concluída).
3. A linha que já tem esse cliente do Stripe.

| Não deu para ligar | Resposta | Marca o id? |
| --- | --- | --- |
| nenhum dos três achou alguém | 200, com aviso no log | não |
| a pessoa não existe (chave estrangeira) | 200, com aviso no log | não |
| o cliente do Stripe já está na linha de outra pessoa | 200, com aviso no log | não |

O segundo caso aparece quando o endpoint de um ambiente recebe evento criado em outro. O terceiro
pede uma pessoa olhando: não tente resolver no código.

## 7. Casos de teste

Gere a assinatura de teste com `generateTestHeaderString` do próprio pacote e simule o banco e a
busca no Stripe. O mínimo que precisa existir:

- Assinatura feita com outro segredo, cabeçalho ausente, corpo alterado e assinatura velha: 400,
  sem ler nem gravar. Sem o segredo configurado: 500.
- Evento já visto: 200, sem buscar no Stripe nem escrever.
- Falha ao gravar a assinatura: 500, e o id do evento não é gravado.
- O que vai para o banco é o estado buscado, e não o do evento.
- Os oito status, um a um; status desconhecido: 500, sem gravar.
- Pausa: viva com `pause_collection` vira `paused`; ao retomar, volta o status do Stripe.
- Assinatura antiga sem plano não sobrescreve outra com plano; a mesma, cancelada, tira o plano.
- Assinatura sumida: o evento de fim vale, os outros são ignorados.
- Sem dono, dono inexistente e cliente de outra pessoa: 200, sem gravar o id.
- Duas entregas da primeira assinatura ao mesmo tempo: a segunda tentativa sincroniza.

## 8. A camada de banco

O molde isola o banco na interface `SubscriptionStore`. Implemente no mesmo arquivo do
manipulador, para a escrita ter um endereço só. Em SQL, com os nomes de `assets/moldes/tabelas.sql`:

| Método | SQL |
| --- | --- |
| `wasProcessed` | `select 1 from stripe_events where id = $1` |
| `markProcessed` | `insert into stripe_events (id, type) values ($1, $2) on conflict (id) do nothing` |
| `findUserIdByCustomer` | `select user_id from subscriptions where stripe_customer_id = $1` |
| `readCurrent` | `select stripe_subscription_id, status from subscriptions where user_id = $1` |
| `upsert` | `insert into subscriptions (...) values (...) on conflict (user_id) do update set ...` |

No `upsert`, o erro `23503` (chave estrangeira) vira `"unknown_user"` e o `23505` (unicidade) vira
`"conflict"`; qualquer outro erro lança. Este SQL acompanha o molde e não foi executado: teste a
sua implementação.

## O que evitar

- **Liberar o acesso na tela de volta do checkout.** O endereço pode ser aberto por quem não
  pagou. A tela espera o webhook (`references/checkout.md` §4).
- **Responder 500 para evento que nunca vai dar certo.** O Stripe reenvia o mesmo evento várias
  vezes (por quanto tempo: a conferir na documentação do Stripe) e o painel enche de falha. Sem
  dono, sem pessoa, tipo que não interessa: 200.
- **Responder 200 quando a gravação falhou.** O evento não volta e a pessoa fica sem o plano.
- **Tratar todos os eventos da conta.** Assine no endpoint só os quatro que o manipulador usa.
- **Colocar regra de negócio na rota.** A rota não tem teste de unidade; o manipulador tem.
- **Gravar dado do evento no log.** Registre tipo, id e desfecho. O corpo tem dado pessoal.
