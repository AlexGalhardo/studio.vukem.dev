// Molde: os dois jeitos de tirar dado velho do cache, com as etiquetas vindas de um lugar só.
// Destino sugerido: features/<área>/revalidate.ts.
//
// 1. `expireProduct`: dentro de ação de servidor. `updateTag` expira na hora (quem escreveu vê o
//    próprio dado) e só pode ser chamado de ação de servidor.
// 2. `handleRevalidateRequest`: para escrita feita POR FORA do aplicativo (script de importação,
//    painel do banco, outro sistema). Sem isto nada expira, e o site mostra o dado antigo até o
//    prazo do perfil passar ou até um novo deploy.

import "server-only";

import { timingSafeEqual } from "node:crypto";
import { revalidateTag, updateTag } from "next/cache";
import { CACHE_TAGS, parseCategory, type Category } from "./leitura-em-cache";

/** O que uma mudança num produto invalida: a página dele, a listagem da categoria e o geral. */
export function productTags(slug: string, category: Category): string[] {
  return [CACHE_TAGS.product(slug), CACHE_TAGS.category(category), CACHE_TAGS.products];
}

/** Chame depois de escrever, e só quando a mudança toca o que está publicado. */
export function expireProduct(slug: string, category: Category): void {
  for (const tag of productTags(slug, category)) updateTag(tag);
}

function sameSecret(sent: string, expected: string): boolean {
  const a = Buffer.from(sent);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

/** Aceita { slug, category } e devolve as etiquetas; qualquer outra coisa invalida tudo. */
function tagsFromBody(body: unknown): string[] {
  if (typeof body !== "object" || body === null) return [CACHE_TAGS.products];
  const { slug, category } = body as { slug?: unknown; category?: unknown };
  const parsed = typeof category === "string" ? parseCategory(category) : null;
  if (typeof slug !== "string" || slug.length === 0 || !parsed) return [CACHE_TAGS.products];
  return productTags(slug, parsed);
}

/**
 * Quem chama é a rota (que só repassa) e quem dispara é o script, depois de gravar:
 *   POST /api/revalidate  com o cabeçalho x-revalidate-secret e o corpo {"slug":"…","category":"…"}
 * O segredo vem do módulo de ambiente do servidor. As etiquetas saem do corpo conferido, nunca
 * do texto cru: uma etiqueta inventada por quem chama não invalida nada e esconde o erro.
 */
export async function handleRevalidateRequest(
  request: Request,
  secret: string | undefined,
): Promise<Response> {
  if (!secret) return Response.json({ error: "Revalidação desligada." }, { status: 503 });
  const sent = request.headers.get("x-revalidate-secret") ?? "";
  if (!sameSecret(sent, secret)) {
    return Response.json({ error: "Não autorizado." }, { status: 401 });
  }

  const body: unknown = await request.json().catch(() => null);
  const tags = tagsFromBody(body);
  // "max": a próxima visita ainda recebe o antigo enquanto o novo é refeito em segundo plano.
  // Para o antigo nunca mais ser servido, troque por { expire: 0 }.
  for (const tag of tags) revalidateTag(tag, "max");
  return Response.json({ revalidated: tags });
}

// A rota, em app/api/revalidate/route.ts (fora do matcher do proxy, como todo endpoint sem sessão):
//
//   import { handleRevalidateRequest } from "@/features/products/revalidate";
//   import { serverEnv } from "@/lib/env.server";
//
//   export async function POST(request: Request) {
//     return handleRevalidateRequest(request, serverEnv().REVALIDATE_SECRET);
//   }
