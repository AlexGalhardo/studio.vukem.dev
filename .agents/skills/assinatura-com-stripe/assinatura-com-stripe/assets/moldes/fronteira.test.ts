// Molde: três regras de arquitetura da cobrança que viram teste. Lê o código-fonte como texto,
// sem subir banco nem Stripe: roda em segundos, junto dos testes de unidade.
// Ajuste as constantes ao projeto. Escrito para Vitest; em Jest, tire a linha do import.
// Limite: não segue imports nem entende a ordem de execução. Enxerga texto.

import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = process.cwd();
/** Onde mora o código do aplicativo (sem testes, sem dependências). */
const SOURCE_DIRS = ["app", "features", "lib"];
const SUBSCRIPTIONS_TABLE = "subscriptions";
/** O único arquivo que escreve na tabela de assinatura. */
const WEBHOOK_MODULE = "features/billing/webhook.ts";
/** O único arquivo que cria o cliente do Stripe e lê as chaves dele. */
const STRIPE_MODULE = "features/billing/stripe.ts";
/** Arquivos em que TODA função exportada é uma ação de cobrança chamada pelo navegador. */
const ACTION_FILES = ["features/billing/actions.ts", "features/billing/cancel-actions.ts"];
/** A guarda que devolve o usuário logado ou interrompe a ação. */
const GUARD = "requireUser";

interface Source {
  file: string;
  text: string;
}

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === "node_modules" ? [] : walk(path);
    return /\.(ts|tsx|js|jsx|mjs)$/.test(entry.name) && !/\.(test|spec)\./.test(entry.name)
      ? [path]
      : [];
  });
}

const sources: Source[] = SOURCE_DIRS.flatMap((dir) => walk(join(ROOT, dir))).map((path) => ({
  file: relative(ROOT, path).split(sep).join("/"),
  text: readFileSync(path, "utf8"),
}));

const sourceOf = (file: string) => sources.find((source) => source.file === file)?.text;
const offenders = (test: (source: Source) => boolean) => sources.filter(test).map((s) => s.file);

// Escrita pelo construtor de consultas e por SQL escrito à mão. Acrescente a forma do seu ORM.
const WRITE_PATTERNS = [
  new RegExp(
    `from\\(\\s*["'\`]${SUBSCRIPTIONS_TABLE}["'\`]\\s*\\)[\\s\\S]{0,200}?\\.(insert|update|upsert|delete)\\(`,
  ),
  new RegExp(`\\binsert\\s+into\\s+(\\w+\\.)?"?${SUBSCRIPTIONS_TABLE}"?\\b`, "i"),
  new RegExp(`\\bupdate\\s+(\\w+\\.)?"?${SUBSCRIPTIONS_TABLE}"?\\s+set\\b`, "i"),
  new RegExp(`\\bdelete\\s+from\\s+(\\w+\\.)?"?${SUBSCRIPTIONS_TABLE}"?\\b`, "i"),
];
const writesSubscriptions = (text: string) => WRITE_PATTERNS.some((pattern) => pattern.test(text));

/** A primeira instrução do corpo da função cujo parêntese de abertura está em `openParen`. */
function firstStatement(text: string, openParen: number): string {
  let index = openParen;
  // Fecha a lista de parâmetros
  for (let depth = 0; index < text.length; index += 1) {
    if (text[index] === "(") depth += 1;
    if (text[index] === ")" && (depth -= 1) === 0) break;
  }
  // Pula o tipo de retorno (Promise<{ ... }>) até a chave que abre o corpo
  for (let angle = 0; index < text.length; index += 1) {
    if (text[index] === "<") angle += 1;
    if (text[index] === ">") angle -= 1;
    if (text[index] === "{" && angle === 0) break;
  }
  const body = text
    .slice(index + 1)
    .replace(/^(\s|\/\/[^\n]*\n|\/\*[\s\S]*?\*\/)*/, "");
  return body.slice(0, body.search(/[;\n]/));
}

describe("fronteiras da cobrança", () => {
  it("só o módulo do webhook escreve na tabela de assinatura", () => {
    expect(
      offenders(({ file, text }) => file !== WEBHOOK_MODULE && writesSubscriptions(text)),
    ).toEqual([]);
    // Controle: com um nome errado nas constantes, a regra passaria sem olhar nada
    expect(writesSubscriptions(sourceOf(WEBHOOK_MODULE) ?? "")).toBe(true);
  });

  it("toda ação de cobrança começa pela guarda de usuário", () => {
    const startsWithGuard = new RegExp(`^(const \\w+ = )?await ${GUARD}\\(`);
    for (const file of ACTION_FILES) {
      const text = sourceOf(file);
      expect(text, file).toBeDefined();
      if (text === undefined) continue;
      const actions = [...text.matchAll(/^export async function (\w+)\s*\(/gm)];
      // Controle: o arquivo tem ações, e todo export dele é uma ação
      expect(actions.length, file).toBeGreaterThan(0);
      expect(text.split("\n").filter((line) => /^export\b/.test(line)), file).toHaveLength(
        actions.length,
      );
      for (const match of actions) {
        const first = firstStatement(text, (match.index ?? 0) + match[0].length - 1);
        expect(first, `${match[1] ?? ""} em ${file}`).toMatch(startsWithGuard);
      }
    }
  });

  it("o cliente do Stripe é criado em um módulo só", () => {
    const createsClient = /\bnew Stripe\(/;
    expect(
      offenders(({ file, text }) => file !== STRIPE_MODULE && createsClient.test(text)),
    ).toEqual([]);
    expect(sourceOf(STRIPE_MODULE) ?? "").toMatch(createsClient);
  });
});
