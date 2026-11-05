// Molde: leitura pública em cache compartilhado, com as etiquetas num só lugar.
// Destino sugerido: features/<área>/queries.ts. Aqui está tudo num arquivo para caber no molde;
// no projeto são três: a lista fechada (puro), as etiquetas (puro, com teste ao lado) e as
// leituras (só de servidor). Separe quando um componente de cliente precisar da lista.
//
// O que entra aqui é igual para todo mundo. Nunca: nada que leia cookie ou cabeçalho, nada que
// dependa de quem está logado, nenhum conteúdo pago.

import "server-only";

import { cacheLife, cacheTag } from "next/cache";
// Troque pelo cliente do seu banco SEM sessão: papel anônimo, sem cookies.
import { publicDb } from "@/lib/db";

/** Os valores que o segmento dinâmico aceita. Lista fechada: o resto é página não encontrada. */
export const CATEGORIES = ["cursos", "modelos", "guias"] as const;
export type Category = (typeof CATEGORIES)[number];

export function parseCategory(value: string): Category | null {
  return CATEGORIES.find((category) => category === value) ?? null;
}

/** Nenhuma etiqueta é escrita fora deste objeto: quem lê e quem expira usam os mesmos nomes. */
export const CACHE_TAGS = {
  products: "products",
  category: (category: Category): string => `products:category:${category}`,
  product: (slug: string): string => `products:item:${slug}`,
} as const;

export interface ProductCard {
  id: string;
  slug: string;
  title: string;
  category: Category;
}

/** Publicados de uma categoria. O argumento entra na chave do cache: uma entrada por categoria. */
export async function listPublishedByCategory(category: Category): Promise<ProductCard[]> {
  "use cache";
  cacheTag(CACHE_TAGS.products, CACHE_TAGS.category(category));
  // Perfil "hours": o servidor refaz em segundo plano depois de 1 h e descarta depois de 1 dia
  cacheLife("hours");

  const { data, error } = await publicDb.listPublished(category);
  // Erro LANÇA: uma lista vazia guardada em cache esconderia tudo até a entrada expirar
  if (error) throw new Error(`Não consegui ler os produtos (${category}): ${error.message}`);
  return data;
}

/** Um produto publicado; null quando não existe. Quem chama decide o notFound(). */
export async function getPublishedProduct(slug: string): Promise<ProductCard | null> {
  "use cache";
  cacheTag(CACHE_TAGS.products, CACHE_TAGS.product(slug));
  cacheLife("hours");

  const { data, error } = await publicDb.findPublished(slug);
  if (error) throw new Error(`Não consegui ler o produto ${slug}: ${error.message}`);
  return data;
}
