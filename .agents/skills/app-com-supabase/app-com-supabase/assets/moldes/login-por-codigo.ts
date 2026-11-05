// Molde: as guardas e as ações do login por código no e-mail (Supabase Auth), em dois blocos.
// Ao copiar, separe: as guardas num módulo só de servidor, as ações num arquivo "use server".
// Passou pelo verificador de tipos com @supabase/ssr 0.12, @supabase/supabase-js 2.117 e Next 16.
// Não foi executado nesta forma: confira no banco local, lendo o código na caixa de e-mail local.
import { notFound, redirect } from "next/navigation";
import { createServerSupabase } from "./clientes";

export type ActionResult = { ok: true } | { ok: false; error: string };
const LOGIN_PATH = "/entrar";
const WELCOME_PATH = "/boas-vindas";

/** Só caminho interno: começa com uma barra, sem segunda barra, sem barra invertida nem controle. */
export function safeNextPath(value: unknown): string | null {
  if (typeof value !== "string" || value.length === 0 || value.length > 512) return null;
  if (!/^\/(?!\/)/.test(value)) return null;
  for (const char of value) {
    const code = char.charCodeAt(0);
    if (code < 0x20 || code === 0x7f || char === "\\") return null;
  }
  return value;
}

// --- features/auth/session.ts: as guardas (import "server-only") ----------------------------------

/** Pessoa da sessão, ou null para visitante. getClaims() confere o token; o cookie cru não vale. */
export async function getUser(): Promise<{ id: string } | null> {
  const supabase = await createServerSupabase();
  const { data, error } = await supabase.auth.getClaims();
  return error || !data ? null : { id: data.claims.sub };
}

/** Primeira instrução de toda ação e de toda leitura por pessoa. */
export async function requireUser(nextPath?: string): Promise<{ id: string }> {
  const user = await getUser();
  if (user) return user;
  const next = safeNextPath(nextPath);
  redirect(next ? `${LOGIN_PATH}?next=${encodeURIComponent(next)}` : LOGIN_PATH);
}

/** Logado que não é admin recebe "não encontrado": a área fica invisível. Erro do banco nega. */
export async function requireAdmin(nextPath?: string): Promise<{ id: string }> {
  const user = await requireUser(nextPath);
  const supabase = await createServerSupabase();
  const { data, error } = await supabase.rpc("is_admin");
  if (error || data !== true) notFound();
  return user;
}

// --- features/auth/actions.ts: as ações ("use server" na primeira linha) ---------------------------
// São a exceção à guarda: criam e encerram a sessão. Nada aqui lê ou grava dado do produto.

/** O tamanho do código é do painel do projeto: aceite a faixa, não um número fixo. */
const CODE = /^\d{6,10}$/;

function readEmail(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const email = value.trim().toLowerCase();
  return email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : null;
}

/** Envia o código. A resposta é a mesma para conta nova e antiga: não revela quem tem conta. */
export async function sendLoginCode(input: { email: unknown }): Promise<ActionResult> {
  const email = readEmail(input.email);
  if (!email) return { ok: false, error: "E-mail inválido." };

  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { shouldCreateUser: true },
  });
  if (error) {
    console.error("Login: falha ao enviar o código", error.status, error.code); // sem o e-mail
    return { ok: false, error: "Não deu para enviar o código agora. Tente de novo em instantes." };
  }
  return { ok: true };
}

/** Confere o código, abre a sessão e redireciona. Só devolve valor quando falha. */
export async function verifyLoginCode(input: {
  email: unknown;
  code: unknown;
  next?: unknown;
}): Promise<ActionResult> {
  const email = readEmail(input.email);
  const code = typeof input.code === "string" ? input.code.replace(/[\s-]/g, "") : "";
  if (!email || !CODE.test(code)) {
    return { ok: false, error: "Digite o código completo que chegou no seu e-mail." };
  }

  // No cliente de servidor: é ele que grava os cookies da sessão na resposta desta ação.
  const supabase = await createServerSupabase();
  const { data, error } = await supabase.auth.verifyOtp({ email, token: code, type: "email" });
  if (error || !data.user) {
    console.error("Login: falha ao conferir o código", error?.status, error?.code);
    return { ok: false, error: "Código inválido ou vencido. Peça um novo." };
  }

  // Formulário obrigatório depois do primeiro login. Com o mesmo cliente: só ele conhece a sessão
  // nova. Se a leitura falhar, libere: banco fora do ar não pode prender ninguém.
  const profile = await supabase
    .from("profiles")
    .select("user_id")
    .eq("user_id", data.user.id)
    .maybeSingle();
  const answered = profile.error ? true : profile.data !== null;

  const next = safeNextPath(input.next);
  const welcome = next ? `${WELCOME_PATH}?next=${encodeURIComponent(next)}` : WELCOME_PATH;
  redirect(answered ? (next ?? "/") : welcome); // fora de try/catch: o redirect funciona lançando
}

/** Encerra a sessão deste aparelho; os outros continuam logados. */
export async function signOut(): Promise<void> {
  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signOut({ scope: "local" });
  if (error) console.error("Login: falha ao sair", error.status, error.code);
  redirect("/");
}

// O que adaptar:
// - As rotas, as mensagens e a tabela do formulário (aqui, profiles com user_id).
// - O validador: com uma biblioteca de esquemas, mantenha a faixa do código e o corte de espaços.
// - A página que tem o formulário também confere a linha: a ação de gravar valida o conteúdo de
//   novo, porque quem grava a própria linha pode gravar direto, sem passar pela tela.
