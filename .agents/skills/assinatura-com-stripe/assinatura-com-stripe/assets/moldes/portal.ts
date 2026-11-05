// Molde: portal do cliente com duas configurações, pausa, retomada e desconto de retenção.
// Tudo aqui muda o Stripe e nada escreve no banco: o estado novo chega pelo webhook.
// Quem chama são ações de servidor que começam pela guarda de usuário e passam o id do cliente e
// da assinatura lidos da linha da PRÓPRIA pessoa, nunca recebidos do navegador.

import Stripe from "stripe";

/** `manage`: cartão, faturas e dados, sem cancelar. `cancel`: só a tela de cancelamento. */
export type PortalRole = "manage" | "cancel";

/** Chave de metadata que marca as configurações criadas pelo aplicativo. Troque pelo seu nome. */
export const PORTAL_ROLE_KEY = "app_portal_role";

type PortalFeatures = Stripe.BillingPortal.ConfigurationCreateParams.Features;

/** A função de cancelar é a única diferença entre as duas configurações. */
export function portalFeatures(role: PortalRole): PortalFeatures {
  return {
    customer_update: { enabled: true, allowed_updates: ["name", "email", "address", "phone"] },
    invoice_history: { enabled: true },
    payment_method_update: { enabled: true },
    subscription_update: { enabled: false },
    subscription_cancel:
      role === "cancel"
        ? { enabled: true, mode: "at_period_end", proration_behavior: "none" }
        : { enabled: false },
  };
}

// O id fica em memória do processo, por cliente do Stripe: trocou a chave, a busca refaz
const cachedIds = new WeakMap<Stripe, Partial<Record<PortalRole, string>>>();

async function findConfiguration(
  stripe: Stripe,
  role: PortalRole,
): Promise<Stripe.BillingPortal.Configuration | null> {
  let startingAfter: string | undefined;
  for (;;) {
    const page = await stripe.billingPortal.configurations.list({
      active: true,
      limit: 100,
      ...(startingAfter ? { starting_after: startingAfter } : {}),
    });
    const found = page.data.find((candidate) => candidate.metadata?.[PORTAL_ROLE_KEY] === role);
    if (found) return found;
    const last = page.data.at(-1);
    if (!page.has_more || !last) return null;
    startingAfter = last.id;
  }
}

/** Achar ou criar. Uma configuração que alguém mexeu no painel é consertada antes de ser usada. */
export async function ensurePortalConfiguration(stripe: Stripe, role: PortalRole): Promise<string> {
  const cached = cachedIds.get(stripe)?.[role];
  if (cached) return cached;

  let id: string;
  const existing = await findConfiguration(stripe, role);
  if (existing) {
    const cancel = existing.features.subscription_cancel;
    const matches =
      role === "manage" ? cancel.enabled === false : cancel.enabled && cancel.mode === "at_period_end";
    if (!matches) {
      await stripe.billingPortal.configurations.update(existing.id, {
        features: { subscription_cancel: portalFeatures(role).subscription_cancel },
      });
    }
    id = existing.id;
  } else {
    const created = await stripe.billingPortal.configurations.create({
      name: role === "manage" ? "Gerenciar assinatura (sem cancelar)" : "Cancelar assinatura",
      features: portalFeatures(role),
      metadata: { [PORTAL_ROLE_KEY]: role },
    });
    id = created.id;
  }
  cachedIds.set(stripe, { ...cachedIds.get(stripe), [role]: id });
  return id;
}

/** Abre o portal com a configuração do papel. Id guardado que não serve mais: refaz uma vez. */
export async function createPortalSession(
  stripe: Stripe,
  role: PortalRole,
  params: Omit<Stripe.BillingPortal.SessionCreateParams, "configuration">,
): Promise<Stripe.BillingPortal.Session> {
  const hadCached = cachedIds.get(stripe)?.[role] !== undefined;
  const configuration = await ensurePortalConfiguration(stripe, role);
  try {
    return await stripe.billingPortal.sessions.create({ ...params, configuration });
  } catch (error) {
    const stale =
      hadCached &&
      error instanceof Stripe.errors.StripeInvalidRequestError &&
      error.param === "configuration";
    if (!stale) throw error;
    cachedIds.set(stripe, { ...cachedIds.get(stripe), [role]: undefined });
    const fresh = await ensurePortalConfiguration(stripe, role);
    return stripe.billingPortal.sessions.create({ ...params, configuration: fresh });
  }
}

/** A tela de cancelamento do Stripe para UMA assinatura, voltando ao aplicativo no fim. */
export function openCancelScreen(
  stripe: Stripe,
  customerId: string,
  subscriptionId: string,
  returnUrl: string,
): Promise<Stripe.BillingPortal.Session> {
  return createPortalSession(stripe, "cancel", {
    customer: customerId,
    return_url: returnUrl,
    flow_data: {
      type: "subscription_cancel",
      subscription_cancel: { subscription: subscriptionId },
      after_completion: { type: "redirect", redirect: { return_url: returnUrl } },
    },
  });
}

/** Pausa a cobrança por `days` dias; as faturas do período são anuladas e a volta é sozinha. */
export async function pauseCollection(stripe: Stripe, subscriptionId: string, days: number) {
  await stripe.subscriptions.update(subscriptionId, {
    pause_collection: {
      behavior: "void",
      resumes_at: Math.floor(Date.now() / 1000) + days * 24 * 60 * 60,
    },
  });
}

/** Retoma agora: valor vazio tira a pausa. */
export async function resumeCollection(stripe: Stripe, subscriptionId: string) {
  await stripe.subscriptions.update(subscriptionId, { pause_collection: "" });
}

export interface RetentionRef {
  kind: "promotion_code" | "coupon";
  id: string;
}

/** Lê a variável do desconto: prefixo `promo_` é código promocional; o resto é id de cupom. */
export function parseRetentionRef(value: string | undefined): RetentionRef | undefined {
  const id = value?.trim();
  if (!id) return undefined;
  return { kind: id.startsWith("promo_") ? "promotion_code" : "coupon", id };
}

/** Aplica o desconto na assinatura que já existe. Cada tipo entra por um parâmetro diferente. */
export async function applyRetention(stripe: Stripe, subscriptionId: string, ref: RetentionRef) {
  await stripe.subscriptions.update(subscriptionId, {
    discounts: [ref.kind === "promotion_code" ? { promotion_code: ref.id } : { coupon: ref.id }],
  });
}
