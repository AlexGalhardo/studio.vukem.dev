// Molde da variante web. Generalizado de uso real, com nomes genéricos.
// Não foi executado nesta forma: rode antes de confiar.
// Sessões por persona, geradas sem tela, para a ponta a ponta. Chame gravarSessoes() no passo de
// preparo do executor, do qual os outros dependem. O login pela tela tem um teste próprio.
import { mkdir, writeFile } from "node:fs/promises";

const SERVIDORES_LOCAIS = new Set(["127.0.0.1", "localhost"]);

/** Trava de ambiente. Toda função de apoio que usa a chave do papel service_role passa por aqui. */
export function lerAmbienteDeTeste() {
  const url = process.env.URL_DO_BANCO ?? "";
  const chaveDeServico = process.env.CHAVE_DE_SERVICO ?? "";
  if (!url || !chaveDeServico) {
    throw new Error("Ponta a ponta: faltam variáveis. Confira o arquivo de ambiente local.");
  }
  const { hostname } = new URL(url);
  if (!SERVIDORES_LOCAIS.has(hostname)) {
    throw new Error(`Ponta a ponta: banco em "${hostname}". Só local: os testes criam dados.`);
  }
  return { url, chaveDeServico };
}

/** Uma conta de identificador fixo por persona, como no cabeçalho dos dados de exemplo. */
export const CONTAS = {
  logado: "logado@example.com",
  pagante: "pagante@example.com",
  administrador: "admin@example.com",
} as const;
export type Persona = keyof typeof CONTAS;

export const PASTA = "<pasta ignorada pelo git>/sessoes";
export const ESTADO: Record<Persona, string> = {
  logado: `${PASTA}/logado.json`,
  pagante: `${PASTA}/pagante.json`,
  administrador: `${PASTA}/administrador.json`,
};
/** Visitante é a sessão vazia. */
export const VISITANTE = { cookies: [], origins: [] };

export interface Cookie {
  name: string; value: string; domain: string; path: string;
  expires: number; httpOnly: boolean; secure: boolean; sameSite: "Strict" | "Lax" | "None";
}

/**
 * Adaptador. Gera a credencial de uso único pela API de administração do login e a troca por
 * sessão com a mesma biblioteca de sessão que o produto usa, com um gravador que só captura o que
 * seria gravado. Cookie montado à mão quebra no dia em que a biblioteca muda o formato.
 */
export type GerarCookies = (email: string, baseURL: string) => Promise<Cookie[]>;

export async function gravarSessoes(baseURL: string, gerar: GerarCookies): Promise<void> {
  lerAmbienteDeTeste();
  await mkdir(PASTA, { recursive: true });
  for (const [persona, email] of Object.entries(CONTAS) as [Persona, string][]) {
    // O mesmo cookie pode chegar duas vezes (remoção e gravação): vale o último; vazio se descarta.
    const ultimos = new Map((await gerar(email, baseURL)).map((c) => [c.name, c]));
    const cookies = [...ultimos.values()].filter((c) => c.value !== "");
    if (cookies.length === 0) throw new Error(`Ponta a ponta: nenhuma sessão para ${persona}.`);
    await writeFile(ESTADO[persona], JSON.stringify({ cookies, origins: [] }, null, 2));
  }
}

// O que adaptar:
// - URL_DO_BANCO e CHAVE_DE_SERVICO: os nomes das variáveis do projeto.
// - CONTAS: as personas e as contas dos dados de exemplo; PASTA: uma pasta que o git ignora.
// - gerar: a troca da credencial de uso único por sessão, com a biblioteca do produto.
// - A sessão gravada vence e não sobrevive a recriar o banco: rode o preparo de novo.
