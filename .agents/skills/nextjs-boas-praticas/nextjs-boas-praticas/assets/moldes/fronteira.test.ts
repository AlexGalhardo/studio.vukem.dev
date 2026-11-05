// Molde: quatro regras de arquitetura que viram teste. Lê o código-fonte como texto, sem subir
// servidor nem banco: roda em segundos, junto dos testes de unidade.
// Ajuste as constantes ao projeto. Escrito para Vitest; em Jest, tire a linha do import.
// Limite: olha só o import direto de cada arquivo (não segue a cadeia) e não entende a ordem de
// execução. Enxerga texto.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";

/** A raiz do projeto: rode os testes a partir dela. */
const ROOT = process.cwd();
/** Onde mora o código do aplicativo (sem testes, sem dependências). */
const SOURCE_DIRS = ["app", "components", "features", "lib"];
/** O apelido de import que aponta para a raiz. */
const ALIAS = "@/";
/** Arquivos em que TODA função exportada é uma ação chamada pelo navegador. */
const ACTION_FILES = ["features/products/actions.ts"];
/** As guardas aceitas como primeira instrução de uma ação. */
const GUARDS = ["requireUser", "requireAdmin"];
/** O que um arquivo com a diretiva de cache não importa: cookies, cabeçalhos, sessão. */
const CACHE_FORBIDDEN = ["next/headers", "features/auth/session"];
/** Pacotes que um componente de cliente não carrega (o validador de schema, por exemplo). */
const CLIENT_FORBIDDEN_PACKAGES = ["zod"];
/** Os únicos arquivos que leem variável de ambiente. */
const ENV_MODULES = ["lib/env.ts", "lib/env.server.ts"];
/** Variáveis que não são configuração do projeto e podem ser lidas em qualquer lugar. */
const ENV_ALLOWED = ["NODE_ENV"];

interface Source {
  file: string;
  text: string;
}

function walk(dir: string): string[] {
  if (!existsSync(dir)) return [];
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

/** A diretiva como instrução ("use client" no topo, "use cache" no topo ou dentro da função). */
const hasDirective = (text: string, name: string) =>
  new RegExp(`^\\s*["']${name}["'];?\\s*$`, "m").test(text);

/** Imports de runtime (sem `import type`), com o apelido e o caminho relativo já resolvidos. */
function runtimeImports({ file, text }: Source): string[] {
  const found = [
    ...text.matchAll(/^import\s+(?!type\b)[^;"']*?\bfrom\s+["']([^"']+)["']/gm),
    ...text.matchAll(/^import\s+["']([^"']+)["']/gm),
    ...text.matchAll(/\bimport\(\s*["']([^"']+)["']\s*\)/g),
  ];
  return found.map((match) => {
    const spec = match[1] ?? "";
    if (spec.startsWith(ALIAS)) return spec.slice(ALIAS.length);
    return spec.startsWith(".") ? join(dirname(file), spec).split(sep).join("/") : spec;
  });
}

/** O arquivo do projeto que um import resolvido alcança, se houver. */
const targetOf = (target: string) =>
  [".ts", ".tsx", "/index.ts", "/index.tsx"].map((end) => sourceOf(target + end)).find(Boolean);

/** A primeira instrução do corpo da função cujo parêntese de abertura está em `openParen`. */
function firstStatement(text: string, openParen: number): string {
  let index = openParen;
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
  const body = text.slice(index + 1).replace(/^(\s|\/\/[^\n]*\n|\/\*[\s\S]*?\*\/)*/, "");
  return body.slice(0, body.search(/[;\n]/));
}

describe("fronteiras do aplicativo", () => {
  it("componente de cliente não importa módulo só de servidor nem pacote pesado", () => {
    const clients = sources.filter(({ text }) => hasDirective(text, "use client"));
    // Controle: com uma pasta errada nas constantes, a regra passaria sem olhar nada
    expect(clients.length).toBeGreaterThan(0);
    const breaks = (source: Source) =>
      runtimeImports(source).some(
        (target) =>
          target === "server-only" ||
          target === "next/headers" ||
          CLIENT_FORBIDDEN_PACKAGES.includes(target) ||
          // O alvo é um arquivo do projeto marcado como só de servidor
          /^import\s+["']server-only["']/m.test(targetOf(target) ?? ""),
      );
    expect(clients.filter(breaks).map((source) => source.file)).toEqual([]);
  });

  it("toda ação de servidor começa pela guarda", () => {
    const startsWithGuard = new RegExp(`^(const \\w+ = )?await (${GUARDS.join("|")})\\(`);
    for (const file of ACTION_FILES) {
      const text = sourceOf(file);
      expect(text, file).toBeDefined();
      if (text === undefined) continue;
      expect(hasDirective(text, "use server"), file).toBe(true);
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

  it("arquivo com a diretiva de cache não importa cookies, cabeçalhos nem sessão", () => {
    const cached = sources.filter(({ text }) => hasDirective(text, "use cache"));
    expect(cached.length).toBeGreaterThan(0);
    const breaks = (source: Source) =>
      runtimeImports(source).some((target) => CACHE_FORBIDDEN.includes(target));
    expect(cached.filter(breaks).map((source) => source.file)).toEqual([]);
  });

  it("variável de ambiente só é lida nos módulos de ambiente", () => {
    const reads = (text: string) =>
      [...text.matchAll(/\bprocess\.env\.([A-Z0-9_]+)/g)].some(
        (match) => !ENV_ALLOWED.includes(match[1] ?? ""),
      );
    expect(offenders(({ file, text }) => !ENV_MODULES.includes(file) && reads(text))).toEqual([]);
    for (const file of ENV_MODULES) expect(reads(sourceOf(file) ?? ""), file).toBe(true);
  });
});
