// Molde: início do checkout de assinatura, com teste pago e período de avaliação.
// Quem chama é a ação de servidor, que COMEÇA pela guarda de usuário, lê a linha de assinatura
// da própria pessoa e termina redirecionando. Nada aqui escreve na tabela de assinatura: quem
// grava é o webhook, depois que o Stripe confirma.

import type Stripe from "stripe";
import { blocksNewCheckout, type SubscriptionStatus } from "./acesso";

export interface CheckoutInput {
  stripe: Stripe;
  user: { id: string; email: string | null };
  /** A linha de assinatura da pessoa; null se nunca assinou. */
  subscription: { status: SubscriptionStatus; stripeCustomerId: string } | null;
  /** Preço recorrente do plano (variável de ambiente). */
  planPriceId: string;
  /** Preço avulso de entrada; ausente = checkout sem período de avaliação. */
  trialPriceId: string | undefined;
  /** Dias de avaliação antes da primeira cobrança do plano; no mínimo 1. */
  trialDays: number;
  /** Endereço de volta, já com a marca que faz a tela esperar o webhook (ex.: ?assinatura=ok). */
  successUrl: string;
  cancelUrl: string;
}

export type CheckoutResult =
  | { kind: "redirect"; url: string }
  /** Já tem o plano, ou tem cobrança pendente: mande para a página da conta. */
  | { kind: "account" }
  | { kind: "error" };

export async function createSubscriptionCheckout(input: CheckoutInput): Promise<CheckoutResult> {
  const { stripe, user, subscription } = input;
  if (subscription && blocksNewCheckout(subscription.status)) return { kind: "account" };

  // O teste pago vale uma vez: só para quem nunca teve linha de assinatura
  const withTrial = subscription === null && input.trialPriceId !== undefined;

  try {
    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      line_items: [
        { price: input.planPriceId, quantity: 1 },
        // Preço avulso num checkout de assinatura: entra só na primeira fatura
        ...(withTrial && input.trialPriceId ? [{ price: input.trialPriceId, quantity: 1 }] : []),
      ],
      subscription_data: {
        // É por aqui que o webhook acha a pessoa em todo evento da assinatura
        metadata: { user_id: user.id },
        ...(withTrial ? { trial_period_days: input.trialDays } : {}),
      },
      // Reserva para o primeiro evento, o da sessão concluída
      client_reference_id: user.id,
      // Quem volta reusa o mesmo cliente do Stripe: um cliente por pessoa
      ...(subscription
        ? { customer: subscription.stripeCustomerId }
        : user.email
          ? { customer_email: user.email }
          : {}),
      success_url: input.successUrl,
      cancel_url: input.cancelUrl,
    });
    return session.url ? { kind: "redirect", url: session.url } : { kind: "error" };
  } catch (error) {
    // Só o tipo e a mensagem: o objeto do erro carrega dados da requisição
    console.error("checkout: o Stripe não criou a sessão:", error instanceof Error ? error.message : error);
    return { kind: "error" };
  }
}
