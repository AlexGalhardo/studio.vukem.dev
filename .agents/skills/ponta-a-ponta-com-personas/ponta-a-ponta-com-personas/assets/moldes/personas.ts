// Molde: apoio dos testes de ponta a ponta. Copie para <testes>/personas.ts.
// Saiu de uma suíte em uso, com os nomes trocados. Passou pelo verificador de tipos com
// @playwright/test 1.64, @supabase/ssr 0.12 e @supabase/supabase-js 2.117; não foi executado
// nesta forma: adapte e rode. As partes 1 a 3 valem para qualquer provedor de login; a parte 4 é
// o adaptador do Supabase (outro provedor: references/personas-e-sessoes.md §6).
import { mkdir, writeFile } from "node:fs/promises";
import { createServerClient } from "@supabase/ssr";
import { createClient } from "@supabase/supabase-js";

// ---------- 1. Travas ----------

const SERVIDORES_LOCAIS = new Set(["127.0.0.1", "localhost", "[::1]"]);

/** Recusa endereço que não seja desta máquina. `nome` é o da variável, para a mensagem. */
export function exigirLocal(endereco: string, nome: string): string {
  let servidor = "(endereço inválido)";
  try {
    servidor = new URL(endereco).hostname;
  } catch {
    // fica "(endereço inválido)" e cai na recusa abaixo
  }
  if (!SERVIDORES_LOCAIS.has(servidor)) {
    throw new Error(
      `Ponta a ponta: ${nome} aponta para "${servidor}". Os testes criam sessões e dados: só rodam contra endereço local.`,
    );
  }
  return endereco;
}

export type AmbienteDeTeste = { urlDoBanco: string; chavePublica: string; chaveDeServico: string };

/** Toda função que usa a chave de serviço passa por aqui. A mensagem nunca traz o valor. */
export function lerAmbienteDeTeste(): AmbienteDeTeste {
  const urlDoBanco = process.env.URL_DO_BANCO ?? "";
  const chavePublica = process.env.CHAVE_PUBLICA ?? "";
  const chaveDeServico = process.env.CHAVE_DE_SERVICO ?? "";
  if (!urlDoBanco || !chavePublica || !chaveDeServico) {
    throw new Error(
      "Ponta a ponta: faltam URL_DO_BANCO, CHAVE_PUBLICA ou CHAVE_DE_SERVICO. Confira o arquivo de ambiente local.",
    );
  }
  exigirLocal(urlDoBanco, "URL_DO_BANCO");
  return { urlDoBanco, chavePublica, chaveDeServico };
}

// ---------- 2. Personas ----------

/** As contas dos dados de exemplo (assets/moldes/personas.sql). Visitante não tem conta. */
export const CONTAS = {
  logado: "logado@example.test",
  assinante: "assinante@example.test",
  admin: "admin@example.test",
} as const;
export type Persona = keyof typeof CONTAS;

/** Pasta que o git ignora: um arquivo de sessão é uma credencial. */
export const PASTA_DE_SESSOES = "playwright/.auth";
export const ESTADO: Record<Persona, string> = {
  logado: `${PASTA_DE_SESSOES}/logado.json`,
  assinante: `${PASTA_DE_SESSOES}/assinante.json`,
  admin: `${PASTA_DE_SESSOES}/admin.json`,
};
/** Visitante é a sessão vazia. */
export const VISITANTE: { cookies: []; origins: [] } = { cookies: [], origins: [] };

// ---------- 3. Dados que o teste cria ----------

/** Tudo o que um teste cria começa assim. Sem "_" nem "%": são coringas na busca da limpeza. */
export const PREFIXO = "zzteste-";
const DEZ_MINUTOS = 10 * 60 * 1000;

/** Conta nova. O carimbo de tempo serve à varredura; o rótulo leva o projeto e o processo. */
export function emailDeTeste(rotulo: string): string {
  return `${PREFIXO}${Date.now()}-${rotulo}@example.test`;
}

/**
 * Sobra de execução antiga: se o envio demora e o teste falha antes, a conta nasce depois da
 * limpeza. Só as de mais de 10 minutos, para não apagar a de um processo em andamento.
 */
export function eSobraAntiga(email: string, agora: number = Date.now()): boolean {
  if (!email.startsWith(PREFIXO)) return false;
  const criada = Number(/^(\d+)-/.exec(email.slice(PREFIXO.length))?.[1]);
  return Number.isFinite(criada) && agora - criada > DEZ_MINUTOS;
}

// ---------- 4. ADAPTADOR DO PROVEDOR (Supabase): troque só esta parte ----------

export function clienteDeServico(ambiente: AmbienteDeTeste = lerAmbienteDeTeste()) {
  return createClient(ambiente.urlDoBanco, ambiente.chaveDeServico, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export interface CookieDeSessao {
  name: string; value: string; domain: string; path: string;
  expires: number; httpOnly: boolean; secure: boolean; sameSite: "Strict" | "Lax" | "None";
}

function paraSameSite(valor: unknown): CookieDeSessao["sameSite"] {
  if (valor === "strict" || valor === true) return "Strict";
  if (valor === "none") return "None";
  return "Lax";
}

/**
 * Sessão de uma conta sem passar pela tela e sem rota de teste no aplicativo. A credencial de uso
 * único sai da API de administração e é trocada por sessão com a mesma biblioteca de sessão que o
 * aplicativo usa, com um gravador que só captura os cookies: eles saem com o nome, a codificação
 * e o fatiamento que o aplicativo espera. Cookie montado à mão quebra quando o formato muda.
 */
export async function cookiesDeSessao(
  email: string,
  baseURL: string,
  ambiente: AmbienteDeTeste = lerAmbienteDeTeste(),
): Promise<CookieDeSessao[]> {
  const servico = clienteDeServico(ambiente);
  const { data, error } = await servico.auth.admin.generateLink({ type: "magiclink", email });
  const codigo = data?.properties?.email_otp;
  if (error || !codigo) {
    throw new Error(`Ponta a ponta: sem código para ${email}: ${error?.message ?? "veio vazio"}`);
  }

  const capturados: { name: string; value: string; options: Record<string, unknown> }[] = [];
  const cliente = createServerClient(ambiente.urlDoBanco, ambiente.chavePublica, {
    cookies: {
      getAll: () => [],
      setAll: (cookies) => {
        for (const c of cookies) capturados.push({ ...c, options: { ...c.options } });
      },
    },
  });
  const troca = await cliente.auth.verifyOtp({ email, token: codigo, type: "email" });
  if (troca.error) {
    throw new Error(`Ponta a ponta: a troca falhou para ${email}: ${troca.error.message}`);
  }

  const agora = Math.floor(Date.now() / 1000);
  // O mesmo cookie pode chegar duas vezes (remoção e gravação): vale o último; vazio se descarta.
  const ultimos = new Map(capturados.map((c) => [c.name, c]));
  const cookies = [...ultimos.values()]
    .filter((c) => c.value !== "")
    .map((c) => ({
      name: c.name,
      value: c.value,
      domain: new URL(baseURL).hostname,
      path: typeof c.options.path === "string" ? c.options.path : "/",
      expires: agora + (typeof c.options.maxAge === "number" ? c.options.maxAge : 3600),
      httpOnly: c.options.httpOnly === true,
      secure: false, // o endereço local é http
      sameSite: paraSameSite(c.options.sameSite),
    }));
  if (cookies.length === 0) throw new Error(`Ponta a ponta: nenhuma sessão para ${email}.`);
  return cookies;
}

/** Grava o arquivo de sessão de cada persona. Quem chama é o projeto de preparo. */
export async function gravarSessoes(baseURL: string): Promise<void> {
  await mkdir(PASTA_DE_SESSOES, { recursive: true });
  for (const [persona, email] of Object.entries(CONTAS) as [Persona, string][]) {
    const cookies = await cookiesDeSessao(email, baseURL);
    await writeFile(ESTADO[persona], JSON.stringify({ cookies, origins: [] }, null, 2));
  }
}

/** Apaga, pelo prefixo, as linhas que os testes criaram numa tabela. */
export async function apagarPorPrefixo(tabela: string, coluna: string): Promise<void> {
  const { error } = await clienteDeServico().from(tabela).delete().like(coluna, `${PREFIXO}%`);
  if (error) throw new Error(`Ponta a ponta: não limpei ${tabela}: ${error.message}`);
}

/** Apaga as contas de teste: as que este processo criou e as sobras antigas. */
export async function apagarContasDeTeste(criadas: readonly string[]): Promise<void> {
  const servico = clienteDeServico();
  const { data, error } = await servico.auth.admin.listUsers({ perPage: 1000 });
  if (error) throw new Error(`Ponta a ponta: não listei as contas: ${error.message}`);
  for (const conta of data.users) {
    if (!conta.email) continue;
    if (!criadas.includes(conta.email) && !eSobraAntiga(conta.email)) continue;
    const apagada = await servico.auth.admin.deleteUser(conta.id);
    if (apagada.error) throw new Error(`Ponta a ponta: não apaguei ${conta.email}.`);
  }
}

// O que adaptar:
// - URL_DO_BANCO, CHAVE_PUBLICA e CHAVE_DE_SERVICO: os nomes das variáveis do projeto.
// - CONTAS: as personas do produto, iguais às dos dados de exemplo.
// - PASTA_DE_SESSOES: tem de estar no .gitignore antes do primeiro preparo.
// - PREFIXO: combine com o dono um que não comece nenhum dado de verdade.
// - Parte 4: a troca da credencial por sessão e as duas limpezas, com a biblioteca do provedor.
