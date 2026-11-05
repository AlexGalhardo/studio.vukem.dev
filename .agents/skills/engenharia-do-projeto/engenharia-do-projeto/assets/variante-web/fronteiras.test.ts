// Molde da variante web. Generalizado de uso real, com nomes genéricos.
// Não foi executado nesta forma: rode antes de confiar.
// Teste de fronteiras: lê os fontes como texto, sem executar o produto, e falha com o caminho do
// arquivo infrator. Diretiva é a linha que é só a string. Regra de texto vale no arquivo inteiro,
// comentário incluído. Caminho de import montado em tempo de execução não se lê: fica de fora.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import ts from "typescript";

const RAIZ = process.cwd();
const PASTAS = ["app", "componentes", "recursos", "lib"];
const MINIMO_DE_ARQUIVOS = 50, ARQUIVO_CONHECIDO = "lib/banco/servico.ts";
const APELIDO = "@/"; // o apelido de import que aponta para a raiz
const DIRETIVA = "use client"; // a linha que marca código de navegador

interface Fonte { arquivo: string; texto: string }
const andar = (dir: string): string[] =>
  readdirSync(path.join(RAIZ, dir), { withFileTypes: true }).flatMap((e) => {
    if (e.isDirectory()) return andar(`${dir}/${e.name}`);
    return /\.tsx?$/.test(e.name) && !/\.test\./.test(e.name) ? [`${dir}/${e.name}`] : [];
  });

const FONTES: Fonte[] = PASTAS.flatMap(andar).sort()
  .map((arquivo) => ({ arquivo, texto: readFileSync(path.join(RAIZ, arquivo), "utf8") }));
const fonteDe = (arquivo: string) => FONTES.find((f) => f.arquivo === arquivo);
const infratores = (regra: (f: Fonte) => boolean) => FONTES.filter(regra).map((f) => f.arquivo);

/** Diretiva é a linha que é só a string: a mesma frase num comentário não conta. */
function temDiretiva(texto: string, diretiva: string): boolean {
  return new RegExp(`^\\s*(["'])${diretiva}\\1\\s*;?\\s*(?://.*)?$`, "m").test(texto);
}
interface Import { destino: string; soTipo: boolean }

/** Apelido e caminho relativo viram o mesmo caminho, a partir da raiz e sem extensão. */
function resolver(deArquivo: string, alvo: string): string {
  const semExt = (v: string) => v.replace(/\.(tsx?|js)$/, "");
  if (alvo.startsWith(APELIDO)) return semExt(alvo.slice(APELIDO.length));
  if (!alvo.startsWith(".")) return alvo; // nome de pacote
  return semExt(path.posix.normalize(path.posix.join(path.posix.dirname(deArquivo), alvo)));
}

/** Pelo analisador sintático: comentário, crase e quebra de linha não escondem um import. */
function importsDe({ arquivo, texto }: Fonte): Import[] {
  const arvore = ts.createSourceFile(arquivo, texto, ts.ScriptTarget.Latest);
  const refs: Import[] = [];
  const somar = (alvo: ts.Node | undefined, soTipo: boolean) => {
    if (!alvo || !ts.isStringLiteralLike(alvo)) return;
    refs.push({ destino: resolver(arquivo, alvo.text), soTipo });
  };
  const visitar = (no: ts.Node): void => {
    if (ts.isImportDeclaration(no)) {
      // Somem na compilação: `import type` e `{ type A, type B }`. O campo que marca o primeiro
      // muda de nome entre versões do compilador: confira na versão instalada.
      const c = no.importClause, b = c?.namedBindings;
      const nomes = b && ts.isNamedImports(b) ? [...b.elements] : [];
      const soTipos = !c?.name && nomes.length > 0 && nomes.every((n) => n.isTypeOnly);
      somar(no.moduleSpecifier, (c?.isTypeOnly ?? false) || soTipos);
    } else if (ts.isExportDeclaration(no)) {
      somar(no.moduleSpecifier, no.isTypeOnly);
    } else if (ts.isCallExpression(no) && no.expression.kind === ts.SyntaxKind.ImportKeyword) {
      somar(no.arguments[0], false); // dinâmico: traz o módulo inteiro
    }
    ts.forEachChild(no, visitar);
  };
  visitar(arvore);
  return refs;
}
const importsQueRodam = (f: Fonte) => importsDe(f).filter((i) => !i.soTipo).map((i) => i.destino);

// Regras como predicados: a sanidade planta um violador em cada um.
const SO_SERVIDOR = ["lib/banco/servidor", "lib/banco/servico"];
const eDeNavegador = (f: Fonte) => temDiretiva(f.texto, DIRETIVA);
const navegadorImportaServidor = (f: Fonte) =>
  eDeNavegador(f) && importsQueRodam(f).some((d) => SO_SERVIDOR.includes(d));
const TABELA_RESTRITA = "app_conteudos";
const PODEM_CITAR = ["recursos/itens/leitura-restrita.ts"];
const citaTabelaRestrita = (f: Fonte) =>
  f.texto.includes(TABELA_RESTRITA) && !PODEM_CITAR.includes(f.arquivo);
const ESCRITOR = "recursos/cobranca/receptor.ts";
const ESCREVE_NO_ESPELHO =
  /from\(\s*["']app_assinaturas["']\s*\)[\s\S]{0,200}?\.(insert|update|upsert|delete)\(/;
const escreveForaDoEscritor = (f: Fonte) =>
  ESCREVE_NO_ESPELHO.test(f.texto) && f.arquivo !== ESCRITOR;
const ARQUIVO_DE_ACOES = "recursos/itens/acoes.ts";
const ACOES = ["salvarItem", "registrarUso"]; // ação nova obriga a editar esta lista
const GUARDA = /^(?:const \w+ = )?await exigirSessao\(/;

describe("sanidade: o verificador prova que enxerga", () => {
  it("acha os fontes: caminho errado faria toda regra passar por vacuidade", () => {
    assert.ok(FONTES.length >= MINIMO_DE_ARQUIVOS, `só ${FONTES.length} arquivos lidos`);
    assert.ok(fonteDe(ARQUIVO_CONHECIDO), `${ARQUIVO_CONHECIDO} ficou fora da varredura`);
    for (const p of PASTAS) assert.ok(FONTES.some((f) => f.arquivo.startsWith(`${p}/`)), p);
    assert.equal(FONTES.some((f) => f.arquivo.includes(".test.")), false);
  });

  it("o detector de diretiva ignora a frase em comentário", () => {
    assert.equal(temDiretiva(`"${DIRETIVA}";\n`, DIRETIVA), true);
    assert.equal(temDiretiva(`// "${DIRETIVA}" só nas folhas\n`, DIRETIVA), false);
  });

  it("cada regra acusa o violador plantado e poupa o inocente", () => {
    const plantar = (...linhas: string[]): Fonte =>
      ({ arquivo: "recursos/x/Exemplo.tsx", texto: linhas.join("\n") });
    const d = `"${DIRETIVA}";`;
    const alvo = `${APELIDO}${SO_SERVIDOR[1]}`;
    const casos: [(f: Fonte) => boolean, Fonte, boolean][] = [
      [navegadorImportaServidor, plantar(d, `import { c } from "${alvo}";`), true],
      [navegadorImportaServidor, plantar(d, `const m = await import(\`${alvo}\`);`), true],
      [navegadorImportaServidor, plantar(d, `import type { C } from "${alvo}";`), false],
      [navegadorImportaServidor, plantar(d, `import { type C } from "${alvo}";`), false],
      [navegadorImportaServidor, plantar(`import { c } from "${alvo}";`), false], // sem diretiva
      [citaTabelaRestrita, plantar(`banco.from("${TABELA_RESTRITA}")`), true],
      [escreveForaDoEscritor, plantar('banco.from("app_assinaturas")', "  .update({})"), true],
      [escreveForaDoEscritor, plantar('banco.from("app_assinaturas").select("id")'), false],
    ];
    for (const [regra, fonte, esperado] of casos) assert.equal(regra(fonte), esperado, fonte.texto);
  });

  it("a primeira instrução é achada depois de parâmetros, tipo de retorno e comentários", () => {
    const t = "export async function f(a: { b: string }): Promise<{ ok: boolean }> {\n" +
      "  // nota\n  await exigirSessao();\n  return { ok: true };\n}";
    assert.equal(primeiraInstrucao(t, t.indexOf("(")), "await exigirSessao();");
  });
});

describe("fronteiras", () => {
  it("1. a tabela do dado restrito só é citada no módulo de leitura por pessoa", () => {
    assert.deepEqual(infratores(citaTabelaRestrita), []);
    // Controle positivo: quem pode citar, cita. Arquivo renomeado não passa em silêncio.
    for (const a of PODEM_CITAR) assert.ok(fonteDe(a)?.texto.includes(TABELA_RESTRITA), a);
  });

  it("2. código de navegador não importa os clientes de servidor", () => {
    assert.ok(FONTES.some(eDeNavegador), "nenhum arquivo de navegador: a regra não olha nada");
    for (const m of SO_SERVIDOR) assert.ok(fonteDe(`${m}.ts`), `${m} não existe mais`);
    assert.deepEqual(infratores(navegadorImportaServidor), []);
  });

  it("3. só o receptor de notificação escreve na tabela de assinaturas", () => {
    assert.deepEqual(infratores(escreveForaDoEscritor), []);
    assert.ok(ESCREVE_NO_ESPELHO.test(fonteDe(ESCRITOR)?.texto ?? ""), "o escritor não escreve");
  });

  it("4. toda ação exportada começa com a guarda", () => {
    const texto = fonteDe(ARQUIVO_DE_ACOES)?.texto ?? "";
    const funcoes = [...texto.matchAll(/^export async function (\w+)\s*\(/gm)];
    assert.deepEqual(funcoes.map((m) => m[1]), ACOES);
    // Nenhum export por outra forma (constante, reexportação) escapa da regra.
    assert.equal(texto.split("\n").filter((l) => /^export\b/.test(l)).length, funcoes.length);
    for (const m of funcoes) {
      assert.match(primeiraInstrucao(texto, (m.index ?? 0) + m[0].length - 1), GUARDA, m[1]);
    }
    // A forma fraca (ler a sessão e devolver erro) não existe no arquivo.
    assert.equal(/\blerSessao\(/.test(texto), false);
  });
});

/** Primeira instrução do corpo, dado o índice do "(" dos parâmetros. */
function primeiraInstrucao(texto: string, abre: number): string {
  let i = abre, parens = 0;
  do { if (texto[i] === "(") parens++; if (texto[i] === ")") parens--; i++; }
  while (parens > 0 && i < texto.length);
  let angulos = 0; // o tipo de retorno pode ter chaves dentro de <…>
  for (; i < texto.length; i++) {
    const c = texto[i];
    if (c === "<") angulos++; else if (c === ">") angulos--;
    else if (c === "{" && angulos === 0) break;
  }
  let corpo = texto.slice(i + 1);
  for (;;) {
    const t = corpo.trimStart();
    if (t.startsWith("//")) corpo = t.slice(t.indexOf("\n") + 1);
    else if (t.startsWith("/*")) corpo = t.slice(t.indexOf("*/") + 2);
    else return t.slice(0, t.indexOf(";") + 1);
  }
}

// O que adaptar:
// - PASTAS, MINIMO_DE_ARQUIVOS, ARQUIVO_CONHECIDO, APELIDO e a diretiva do framework do projeto.
// - As listas de cada regra (quem pode citar, quem escreve, as ações) e o nome da guarda.
// - `describe` e `it` são do executor embutido do Node.js: troque pelos do executor do projeto.
// - Regra nova: predicado, violador plantado na sanidade e controle positivo, na mesma mudança.
