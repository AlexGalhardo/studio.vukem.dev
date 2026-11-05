// Molde: quem tem o plano, em funções puras. Sem banco, sem Stripe, sem rede.
// Espelha a função has_plan() de tabelas.sql: os casos de teste de uma ponta são repetidos na
// outra. Tela, ação e webhook perguntam aqui; ninguém compara status por conta própria.

/** Os oito status de assinatura do Stripe, iguais ao tipo enumerado do banco. */
export const SUBSCRIPTION_STATUSES = [
  "trialing",
  "active",
  "past_due",
  "canceled",
  "unpaid",
  "incomplete",
  "incomplete_expired",
  "paused",
] as const;

export type SubscriptionStatus = (typeof SUBSCRIPTION_STATUSES)[number];

/** O Stripe pode criar um status novo: quem recebe um valor de fora confere antes de usar. */
export function isSubscriptionStatus(value: string): value is SubscriptionStatus {
  return (SUBSCRIPTION_STATUSES as readonly string[]).includes(value);
}

/** Status que dão o plano. `trialing` conta: o período de avaliação já é assinatura. */
const PLAN_STATUSES: readonly SubscriptionStatus[] = ["active", "trialing"];

/** Espelha has_plan(): sem linha de assinatura (null ou undefined), sem plano. */
export function hasPlan(status: SubscriptionStatus | null | undefined): boolean {
  return status != null && PLAN_STATUSES.includes(status);
}

/** Viva no Stripe, sem dar o plano, com cobrança pendente ou pausada. */
const RETRYING_STATUSES: readonly SubscriptionStatus[] = ["past_due", "unpaid", "paused"];

/**
 * Quem já tem o plano, ou tem cobrança pendente, resolve na página da conta: um checkout novo
 * por cima criaria duas assinaturas. `incomplete` fica de fora: é o primeiro pagamento que não
 * fechou e expira sozinho, então a pessoa pode tentar de novo.
 */
export function blocksNewCheckout(status: SubscriptionStatus): boolean {
  return hasPlan(status) || RETRYING_STATUSES.includes(status);
}

const CANCELABLE_STATUSES: readonly SubscriptionStatus[] = ["trialing", "active", "past_due"];

/** Dá para pedir o cancelamento? Assinatura viva e ainda não marcada para terminar. */
export function isCancelable(
  subscription: { status: SubscriptionStatus; cancelAtPeriodEnd: boolean } | null,
): boolean {
  return (
    subscription !== null &&
    CANCELABLE_STATUSES.includes(subscription.status) &&
    !subscription.cancelAtPeriodEnd
  );
}

const PAUSABLE_STATUSES: readonly SubscriptionStatus[] = ["trialing", "active", "past_due", "unpaid"];

/**
 * O status que vai para o banco. Com a cobrança pausada (`pause_collection`), o Stripe mantém o
 * status da assinatura; aqui a assinatura viva é gravada como `paused`, que não dá o plano.
 * Assinatura que terminou, ou que nem fechou o primeiro pagamento, fica com o status do Stripe.
 * Se no seu produto a pausa mantém o acesso, apague esta função e grave o status como veio.
 */
export function storedStatus(
  pauseCollection: object | null | undefined,
  status: SubscriptionStatus,
): SubscriptionStatus {
  return pauseCollection && PAUSABLE_STATUSES.includes(status) ? "paused" : status;
}
