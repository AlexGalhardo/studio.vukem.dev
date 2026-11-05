// Molde: o módulo de segredos e os cinco clientes do Supabase, num arquivo só para ler de uma vez.
// Ao copiar, separe: cada bloco diz o arquivo de destino e leva os imports que usa.
// Passou pelo verificador de tipos com @supabase/ssr 0.12, @supabase/supabase-js 2.117 e Next 16.
// Não foi executado contra um projeto remoto: rode os testes do projeto antes de confiar.
import { createBrowserClient, createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";
import type { Database } from "./database.types"; // gerado pelo comando de tipos, nunca à mão

// Públicas: vão para o navegador. Nenhuma chave secreta mora neste bloco.
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";

// --- lib/env.server.ts ------------------------------------------------------------------------
// Primeira linha do arquivo: import "server-only";  (o build falha se o navegador importar)
// O único módulo que lê a chave secreta. É este caminho que vai em --modulo do conferidor.
export function secretKey(): string {
  const value = process.env.SUPABASE_SECRET_KEY?.trim();
  if (!value) throw new Error("SUPABASE_SECRET_KEY ausente. Confira o arquivo de exemplo.");
  return value;
}

// --- lib/supabase/server.ts: sessão da pessoa, pelos cookies -------------------------------------
// Primeira linha: import "server-only". Um cliente novo a cada chamada, nunca guardado no módulo:
// a sessão é a dos cookies desta requisição.
export async function createServerSupabase() {
  const cookieStore = await cookies();
  return createServerClient<Database>(SUPABASE_URL, PUBLISHABLE_KEY, {
    cookies: {
      getAll: () => cookieStore.getAll(),
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) cookieStore.set(name, value, options);
        } catch {
          // Componente de servidor não grava cookie. Quem renova a sessão é o proxy, abaixo.
        }
      },
    },
  });
}

// --- lib/supabase/client.ts: navegador ----------------------------------------------------------
// Sem "server-only". No navegador há uma pessoa só: a instância fica guardada.
let browserClient: ReturnType<typeof createBrowserClient<Database>> | undefined;
export function createBrowserSupabase() {
  if (typeof window === "undefined") return createBrowserClient<Database>(SUPABASE_URL, PUBLISHABLE_KEY);
  browserClient ??= createBrowserClient<Database>(SUPABASE_URL, PUBLISHABLE_KEY);
  return browserClient;
}

// --- lib/supabase/public.ts: visitante, sem cookies -----------------------------------------------
// Primeira linha: import "server-only". Para leitura em cache compartilhado: papel anon, e a RLS
// já entrega só o que é público. Nada que dependa de quem pede passa por aqui.
export function createPublicSupabase() {
  return createClient<Database>(SUPABASE_URL, PUBLISHABLE_KEY, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
}

// --- lib/supabase/admin.ts: chave secreta, ignora a RLS -------------------------------------------
// Primeira linha: import "server-only". Use em poucos pontos, listados no documento de dados:
// webhook, link assinado, ferramenta de carga. Nunca para ler "em nome" de uma pessoa.
export function createAdminSupabase() {
  return createClient<Database>(SUPABASE_URL, secretKey(), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

// --- lib/supabase/proxy.ts: renova a sessão a cada requisição ------------------------------------
// Chamado pelo proxy.ts da raiz (middleware.ts antes do Next 16). Só mantém os cookies vivos:
// a proteção de rota fica nas páginas e nas ações, onde o dado é lido.
export async function updateSession(request: NextRequest): Promise<NextResponse> {
  let response = NextResponse.next({ request });

  const supabase = createServerClient<Database>(SUPABASE_URL, PUBLISHABLE_KEY, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(cookiesToSet, headers) {
        for (const { name, value } of cookiesToSet) request.cookies.set(name, value);
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options);
        }
        // Resposta que grava cookie de sessão não pode ficar em cache de CDN: a biblioteca manda
        // os cabeçalhos que impedem isso, e eles só valem se forem copiados para a resposta.
        for (const [key, value] of Object.entries(headers)) response.headers.set(key, value);
      },
    },
  });

  // Nada entre criar o cliente e esta chamada: é ela que confere o token e, perto de vencer,
  // troca por um novo (o setAll acima grava os cookies).
  await supabase.auth.getClaims();
  return response;
}

// O que adaptar:
// - Os nomes das variáveis. A chave antiga (anon, service_role) entra por um nome alternativo.
// - O matcher do proxy: deixe de fora arquivos estáticos e a rota do webhook, que chega sem sessão.
// - Com cacheComponents no Next 16, chame `await connection()` (de "next/server") depois de
//   `cookies()` em createServerSupabase(): visto em um projeto, confira no seu.
// - Fora do Next: o desenho é o mesmo (getAll e setAll sobre os cookies da requisição).
