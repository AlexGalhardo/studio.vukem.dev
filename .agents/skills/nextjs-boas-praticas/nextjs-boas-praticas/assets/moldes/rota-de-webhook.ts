// Molde: webhook em duas partes. Este arquivo junta as duas para caber no molde; no projeto,
// separe: a função `POST` vai para app/api/webhooks/<serviço>/route.ts e o resto para o módulo
// do domínio (features/<área>/webhook.ts). Motivo: a regra fica testável sem subir servidor, e
// o arquivo de rota fica só com o método HTTP.
//
// A conferência abaixo é HMAC-SHA256 do corpo cru, em hexadecimal. Cada serviço tem o seu
// formato de assinatura (cabeçalho, prefixo, carimbo de tempo): confira na documentação dele e,
// se existir pacote oficial, use a função de conferência do pacote.

import { createHmac, timingSafeEqual } from "node:crypto";
// Troque pelos módulos do seu projeto: quem grava o efeito do evento e o segredo.
import { applyOrderEvent } from "@/features/orders/events";
import { serverEnv } from "@/lib/env.server";

export interface WebhookResult {
  status: 200 | 400 | 500;
  body: { received: boolean; error?: string };
}

export interface WebhookDeps {
  /** Segredo do endpoint, lido no módulo de ambiente do servidor. */
  secret: string;
  /** Grava o efeito do evento. Lança em falha, para o serviço reenviar. */
  apply: (event: { id: string; type: string; data: unknown }) => Promise<void>;
}

const HANDLED_TYPES = new Set(["order.paid", "order.refunded"]);

function signatureMatches(rawBody: string, signature: string, secret: string): boolean {
  const expected = Buffer.from(createHmac("sha256", secret).update(rawBody).digest("hex"));
  const sent = Buffer.from(signature);
  return sent.length === expected.length && timingSafeEqual(sent, expected);
}

function parseEvent(rawBody: string): { id: string; type: string; data: unknown } | null {
  try {
    const parsed: unknown = JSON.parse(rawBody);
    if (typeof parsed !== "object" || parsed === null) return null;
    const { id, type, data } = parsed as { id?: unknown; type?: unknown; data?: unknown };
    return typeof id === "string" && typeof type === "string" ? { id, type, data } : null;
  } catch {
    return null;
  }
}

/** A ordem importa: assinatura sobre o texto cru, depois o JSON, depois o tipo, depois gravar. */
export async function handleWebhook(
  rawBody: string,
  signature: string | null,
  deps: WebhookDeps,
): Promise<WebhookResult> {
  if (!signature || !signatureMatches(rawBody, signature, deps.secret)) {
    return { status: 400, body: { received: false, error: "Assinatura inválida." } };
  }
  const event = parseEvent(rawBody);
  if (!event) return { status: 400, body: { received: false, error: "Corpo inválido." } };
  // Tipo que não interessa responde 200: se responder erro, o serviço reenvia para sempre
  if (!HANDLED_TYPES.has(event.type)) return { status: 200, body: { received: true } };

  try {
    await deps.apply(event);
  } catch (error) {
    console.error(`webhook: falha ao aplicar ${event.type} (${event.id})`, error);
    // 500 faz o serviço reenviar. `apply` precisa aguentar o mesmo evento duas vezes
    return { status: 500, body: { received: false, error: "Falha ao gravar." } };
  }
  return { status: 200, body: { received: true } };
}

/**
 * A rota só lê o corpo CRU e repassa. Um `request.json()` antes da conferência muda o texto
 * (espaços, ordem das chaves) e a assinatura deixa de bater: toda entrega passa a responder 400.
 * Deixe /api/webhooks fora do matcher do proxy: a chamada vem sem sessão.
 */
export async function POST(request: Request) {
  const rawBody = await request.text();
  const result = await handleWebhook(rawBody, request.headers.get("x-signature"), {
    secret: serverEnv().WEBHOOK_SECRET,
    apply: applyOrderEvent,
  });
  return Response.json(result.body, { status: result.status });
}
