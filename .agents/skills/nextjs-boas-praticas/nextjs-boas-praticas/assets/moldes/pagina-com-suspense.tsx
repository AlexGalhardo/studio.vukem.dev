// Molde: página de listagem com segmento dinâmico, filtro na URL e os estados de carregamento e
// vazio. O estado de erro é o error.tsx do segmento (references/navegacao.md §3).
// Destino sugerido: app/produtos/[categoria]/page.tsx. Troque o literal de PageProps pela sua
// rota: o tipo é global e é gerado por `next dev`, `next build` ou `next typegen`.
//
// Três fronteiras, de fora para dentro:
// 1. a página não é async e não espera nada: `params` e `searchParams` descem como promessas;
// 2. `CategoryListing` espera `params` e a lista em cache: para as categorias de
//    generateStaticParams, entra pronta no HTML estático;
// 3. `Results` é o único que espera `searchParams`: só a grade fica para a hora da requisição.

import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import {
  CATEGORIES,
  listPublishedByCategory,
  parseCategory,
  type ProductCard,
} from "./leitura-em-cache";

type Props = PageProps<"/produtos/[categoria]">;

// Com Cache Components, a lista não pode ser vazia: o build falha
export function generateStaticParams() {
  return CATEGORIES.map((categoria) => ({ categoria }));
}

export default function CategoryPage({ params, searchParams }: Props) {
  return (
    <Suspense fallback={<ListingSkeleton />}>
      <CategoryListing params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function CategoryListing({ params, searchParams }: Props) {
  // O segmento aceita qualquer texto: confira contra a lista ANTES de ler dado
  const category = parseCategory((await params).categoria);
  if (!category) notFound();

  const products = await listPublishedByCategory(category);

  // Vazio de verdade: não há nada publicado. Diga isso e dê uma saída
  if (products.length === 0) {
    return (
      <main>
        <h1>{category}</h1>
        <p>Ainda não há nada publicado aqui.</p>
        <Link href="/produtos">Ver todas as categorias</Link>
      </main>
    );
  }

  return (
    <main>
      <h1>{category}</h1>
      <Suspense fallback={<GridSkeleton />}>
        <Results category={category} products={products} searchParams={searchParams} />
      </Suspense>
    </main>
  );
}

/** Valor inválido na URL cai no padrão: endereço colado errado não pode virar tela de erro. */
function parseQuery(value: string | string[] | undefined): string {
  return typeof value === "string" ? value.trim().slice(0, 80).toLowerCase() : "";
}

async function Results({
  category,
  products,
  searchParams,
}: {
  category: string;
  products: readonly ProductCard[];
  searchParams: Props["searchParams"];
}) {
  const query = parseQuery((await searchParams).q);
  const visible = query
    ? products.filter((product) => product.title.toLowerCase().includes(query))
    : products;

  // Vazio do filtro: há produtos, mas nenhum com esta busca. A saída é limpar o filtro
  if (visible.length === 0) {
    return (
      <p>
        Nada encontrado para “{query}”. <Link href={`/produtos/${category}`}>Limpar a busca</Link>
      </p>
    );
  }

  return (
    <ul>
      {visible.map((product) => (
        <li key={product.id}>{product.title}</li>
      ))}
    </ul>
  );
}

function GridSkeleton() {
  return (
    <div aria-busy="true">
      <p className="sr-only">Carregando…</p>
      <ul aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => (
          <li key={index} className="skeleton" />
        ))}
      </ul>
    </div>
  );
}

/** Mova para um arquivo próprio e use também como `export default` do loading.tsx do segmento. */
function ListingSkeleton() {
  return (
    <main>
      <div className="skeleton" />
      <GridSkeleton />
    </main>
  );
}
