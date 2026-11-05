// Molde: manipulador do webhook do Stripe. É o ÚNICO módulo que escreve na tabela de assinatura.
// Adapte: implemente SubscriptionStore NESTE arquivo, com o cliente do banco que usa a chave de
// serviço (o SQL de cada método está em references/webhook.md §8), e chame handleStripeWebhook da
// rota com o corpo CRU (texto) e o cabeçalho stripe-signature. Nunca lança: devolve a resposta.

import Stripe from "stripe";
import { hasPlan, isSubscriptionStatus, storedStatus, type SubscriptionStatus } from "./acesso";

export interface WebhookResponse {
  status: 200 | 400 | 500;
  body: Record<string, string | boolean>;
}

export interface SubscriptionRow {
  userId: string;
  stripeCustomerId: string;
  stripeSubscriptionId: string;
  status: SubscriptionStatus;
  /** ISO 8601, ou null se o Stripe não informar. */
  currentPeriodEnd: string | null;
  cancelAtPeriodEnd: boolean;
}

/** A camada de banco. Erro de banco LANÇA: o manipulador responde 500 e o Stripe reenvia. */
export interface SubscriptionStore {
  wasProcessed(eventId: string): Promise<boolean>;
  /** Id repetido (duas entregas ao mesmo tempo) não é erro. */
  markProcessed(eventId: string, type: string): Promise<void>;
  findUserIdByCustomer(customerId: string): Promise<string | null>;
  readCurrent(userId: string): Promise<{ stripeSubscriptionId: string; status: SubscriptionStatus } | null>;
  /** Grava por userId. "unknown_user": a pessoa não existe. "conflict": violação de unicidade. */
  upsert(row: SubscriptionRow): Promise<"ok" | "unknown_user" | "conflict">;
}

export interface WebhookDeps {
  /** null quando falta a chave secreta: o evento responde 500 e volta no reenvio. */
  stripe: Stripe | null;
  webhookSecret: string | undefined;
  store: SubscriptionStore;
  /** O valor tem o formato do id de usuário do seu sistema (uuid, número)? */
  isUserId(value: unknown): value is string;
}

/** Só `synced` e `kept` contam como processados e gravam o id do evento. */
type Outcome =
  | ("synced" | "kept")
  | ("ignored_not_subscription" | "ignored_missing_subscription" | "ignored_unknown_customer")
  | ("ignored_unknown_user" | "ignored_customer_conflict");

type SubscriptionEvent =
  | Stripe.CheckoutSessionCompletedEvent
  | Stripe.CustomerSubscriptionCreatedEvent
  | Stripe.CustomerSubscriptionUpdatedEvent
  | Stripe.CustomerSubscriptionDeletedEvent;

function isHandled(event: Stripe.Event): event is SubscriptionEvent {
  return (
    event.type === "checkout.session.completed" ||
    event.type === "customer.subscription.created" ||
    event.type === "customer.subscription.updated" ||
    event.type === "customer.subscription.deleted"
  );
}

/** Status de assinatura que terminou de vez. */
const ENDED_STATUSES: readonly string[] = ["canceled", "incomplete_expired"];

/** Campo expansível do Stripe: vem como id ou como o objeto. */
function idOf(value: string | { id: string } | null | undefined): string | null {
  if (!value) return null;
  return typeof value === "string" ? value : value.id;
}

/**
 * Fim do período atual. Nas versões novas da API o campo fica em cada item da assinatura (vale
 * o que vence primeiro); nas antigas, na própria assinatura. Sem nenhum dos dois: null.
 */
export function currentPeriodEnd(subscription: Stripe.Subscription): string | null {
  const legacy: unknown = (subscription as { current_period_end?: unknown }).current_period_end;
  const fromItems = (subscription.items?.data ?? [])
    .map((item): unknown => item.current_period_end)
    .filter((value): value is number => typeof value === "number");
  const seconds =
    typeof legacy === "number" ? legacy : fromItems.length > 0 ? Math.min(...fromItems) : null;
  return seconds === null ? null : new Date(seconds * 1000).toISOString();
}

/** Vai terminar sem renovar? Vale a marca de fim de período ou uma data de cancelamento. */
function willCancel(subscription: Stripe.Subscription): boolean {
  return subscription.cancel_at_period_end === true || typeof subscription.cancel_at === "number";
}

/** Tipo e código do erro, sem os dados da requisição: é o que vai para o log. */
function describeError(error: unknown): string {
  if (error instanceof Stripe.errors.StripeError) {
    return `${error.type}${error.code ? ` (${error.code})` : ""}: ${error.message}`;
  }
  return error instanceof Error ? error.message : String(error);
}

/**
 * O estado ATUAL da assinatura, lido no Stripe. Se ela não existe mais lá, só o retrato de um
 * evento de fim serve: qualquer outro estado poderia estar velho.
 */
async function fetchSubscription(
  stripe: Stripe,
  subscriptionId: string,
  snapshot: Stripe.Subscription | null,
): Promise<Stripe.Subscription | null> {
  try {
    return await stripe.subscriptions.retrieve(subscriptionId);
  } catch (error) {
    const missing =
      error instanceof Stripe.errors.StripeInvalidRequestError && error.code === "resource_missing";
    if (!missing) throw error;
    return snapshot !== null && ENDED_STATUSES.includes(snapshot.status) ? snapshot : null;
  }
}

async function syncSubscription(
  deps: WebhookDeps,
  subscriptionId: string,
  fallbackUserId: string | null,
  snapshot: Stripe.Subscription | null,
): Promise<Outcome> {
  if (!deps.stripe) throw new Error("chave secreta do Stripe ausente");
  const subscription = await fetchSubscription(deps.stripe, subscriptionId, snapshot);
  if (!subscription) return "ignored_missing_subscription";

  // Status que o sistema não conhece: falhar (e receber o reenvio) é melhor que gravar um palpite
  if (!isSubscriptionStatus(subscription.status)) {
    throw new Error(`status de assinatura desconhecido: ${subscription.status}`);
  }
  const status = storedStatus(subscription.pause_collection, subscription.status);

  const customerId = idOf(subscription.customer);
  if (!customerId) return "ignored_unknown_customer";

  // De quem é: o id que o checkout gravou; se faltar, a linha que já tem esse cliente do Stripe
  const userId =
    [subscription.metadata?.user_id, fallbackUserId].find(deps.isUserId) ??
    (await deps.store.findUserIdByCustomer(customerId));
  if (!userId) return "ignored_unknown_customer";

  // Evento de uma assinatura antiga, que não dá o plano, não passa por cima de outra que dá
  const current = await deps.store.readCurrent(userId);
  if (
    current &&
    current.stripeSubscriptionId !== subscription.id &&
    hasPlan(current.status) &&
    !hasPlan(status)
  ) {
    return "kept";
  }

  const row: SubscriptionRow = {
    userId,
    stripeCustomerId: customerId,
    stripeSubscriptionId: subscription.id,
    status,
    currentPeriodEnd: currentPeriodEnd(subscription),
    cancelAtPeriodEnd: willCancel(subscription),
  };
  let result = await deps.store.upsert(row);
  // As duas primeiras entregas de uma assinatura nova chegam juntas e uma perde a corrida da
  // inserção. Na segunda tentativa a linha já existe e a gravação vira atualização.
  if (result === "conflict") result = await deps.store.upsert(row);

  // Reenviar não resolve nenhum dos dois: pessoa que não existe, ou cliente que é de outra pessoa
  if (result === "unknown_user") return "ignored_unknown_user";
  if (result === "conflict") return "ignored_customer_conflict";
  return "synced";
}

function processEvent(deps: WebhookDeps, event: SubscriptionEvent): Promise<Outcome> {
  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const subscriptionId = idOf(session.subscription);
    if (session.mode !== "subscription" || !subscriptionId) {
      return Promise.resolve("ignored_not_subscription");
    }
    return syncSubscription(deps, subscriptionId, session.client_reference_id, null);
  }
  return syncSubscription(deps, event.data.object.id, null, event.data.object);
}

export async function handleStripeWebhook(
  rawBody: string,
  signature: string | null,
  deps: WebhookDeps,
): Promise<WebhookResponse> {
  // Sem assinatura válida sobre o corpo cru, nada é lido nem gravado
  if (!deps.webhookSecret) return { status: 500, body: { error: "webhook_not_configured" } };
  if (!signature) return { status: 400, body: { error: "invalid_signature" } };
  let event: Stripe.Event;
  try {
    event = Stripe.webhooks.constructEvent(rawBody, signature, deps.webhookSecret);
  } catch {
    return { status: 400, body: { error: "invalid_signature" } };
  }
  if (!isHandled(event)) return { status: 200, body: { received: true, ignored: "event_type" } };

  try {
    if (await deps.store.wasProcessed(event.id)) {
      return { status: 200, body: { received: true, duplicate: true } };
    }
    const outcome = await processEvent(deps, event);
    if (outcome === "synced" || outcome === "kept") {
      // A marca vem DEPOIS de gravar. Se só ela falhar, o pior caso é reprocessar: log e 200
      await deps.store.markProcessed(event.id, event.type).catch((error: unknown) => {
        console.error(`webhook: não marquei ${event.id}:`, describeError(error));
      });
    } else {
      console.warn(`webhook: ${event.type} (${event.id}) sem efeito: ${outcome}`);
    }
    return { status: 200, body: { received: true, result: outcome } };
  } catch (error) {
    console.error(`webhook: falha em ${event.type} (${event.id}):`, describeError(error));
    return { status: 500, body: { error: "processing_failed" } };
  }
}
