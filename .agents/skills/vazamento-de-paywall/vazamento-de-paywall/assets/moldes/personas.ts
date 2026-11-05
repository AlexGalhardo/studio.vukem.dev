// Molde: as personas do teste de vazamento e a sessão de cada uma, gerada sem passar pela tela.
// Chame gravarSessoes() no passo de preparo do executor de ponta a ponta, do qual os outros
// dependem (o trecho está no fim do arquivo). O login pela tela merece um teste próprio.
// Saiu de um preparo em uso, com os nomes trocados. Passou no verificador de tipos; o adaptador
// `gerar` é do seu sistema de login e não vem pronto.
import { mkdir, writeFile } from "node:fs/promises";

const SERVIDORES_LOCAIS = new Set(["127.0.0.1", "localhost"]);

/** Trava de ambiente: quem cria sessão e dados de teste só fala com banco local. */
export function lerAmbienteDeTeste(): { url: string; chaveDeServico: string } {
  const url = process.env.URL_DO_BANCO ?? "";
  const chaveDeServico = process.env.CHAVE_DE_SERVICO ?? "";
  if (!url || !chaveDeServico) {
    throw new Error("Ponta a ponta: faltam variáveis. Confira o arquivo de ambiente local.");
  }
  const { hostname } = new URL(url);
  if (!SERVIDORES_LOCAIS.has(hostname)) {
    throw new Error(`Ponta a ponta: banco em "${hostname}". Só local: o preparo cria sessões.`);
  }
  return { url, chaveDeServico };
}

/** Uma conta de identificador fixo por persona, as mesmas dos dados de exemplo. */
export const CONTAS = {
  logado: "00000000-0000-4000-8000-000000000002",
  assinante: "00000000-0000-4000-8000-000000000003",
  admin: "00000000-0000-4000-8000-000000000004",
} as const;
export type Persona = keyof typeof CONTAS;

/** Pasta que o git ignora: arquivo de sessão é credencial. */
export const PASTA = "ponta-a-ponta/.sessoes";
export const ESTADO: Record<Persona, string> = {
  logado: `${PASTA}/logado.json`,
  assinante: `${PASTA}/assinante.json`,
  admin: `${PASTA}/admin.json`,
};
/** O visitante é a sessão vazia. */
export const VISITANTE: { cookies: []; origins: [] } = { cookies: [], origins: [] };

export interface Cookie {
  name: string;
  value: string;
  domain: string;
  path: string;
  expires: number;
  httpOnly: boolean;
  secure: boolean;
  sameSite: "Strict" | "Lax" | "None";
}

/**
 * Adaptador do seu login. Gera uma credencial de uso único para a conta, pela interface de
 * administração do login, e a troca por sessão com a MESMA biblioteca de sessão que o produto
 * usa, capturando os cookies que ela gravaria. Cookie montado à mão quebra no dia em que a
 * biblioteca muda o formato, e o teste passa a rodar como visitante sem avisar.
 */
export type GerarCookies = (idDaConta: string, baseURL: string) => Promise<Cookie[]>;

export async function gravarSessoes(baseURL: string, gerar: GerarCookies): Promise<void> {
  lerAmbienteDeTeste();
  await mkdir(PASTA, { recursive: true });
  for (const [persona, idDaConta] of Object.entries(CONTAS) as [Persona, string][]) {
    // O mesmo cookie pode vir duas vezes (remoção e gravação): vale o último; vazio se descarta.
    const ultimos = new Map((await gerar(idDaConta, baseURL)).map((c) => [c.name, c]));
    const cookies = [...ultimos.values()].filter((c) => c.value !== "");
    if (cookies.length === 0) throw new Error(`Ponta a ponta: nenhuma sessão para ${persona}.`);
    await writeFile(ESTADO[persona], JSON.stringify({ cookies, origins: [] }, null, 2));
  }
}

// O passo de preparo, em um arquivo só dele (por exemplo `sessoes.setup.ts`):
//
//   import { test as preparo } from "@playwright/test";
//   import { gravarSessoes } from "./personas";
//   import { gerarCookies } from "./meu-login"; // o seu adaptador
//   preparo("sessões das personas", async ({ baseURL }) => {
//     await gravarSessoes(baseURL ?? "", gerarCookies);
//   });
//
// O que adaptar:
// - URL_DO_BANCO e CHAVE_DE_SERVICO: os nomes das variáveis do projeto.
// - CONTAS: os identificadores dos dados de exemplo. Persona a mais (ex-assinante): uma linha.
// - A sessão gravada vence e não sobrevive a recriar o banco: rode o preparo de novo.
