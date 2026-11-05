// Molde: cinco regras de fronteira do conteúdo pago, lidas do código-fonte como texto. Não sobe
// banco nem servidor: roda em segundos, junto dos testes de unidade. Escrito para Vitest.
// Diretiva é a linha que é só a string; import se lê com o analisador do TypeScript (comentário,
// crase e quebra de linha não escondem um import). Limites: regra de texto vale para o arquivo
// inteiro, comentário incluído, e caminho de import montado em tempo de execução não se lê.
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const RAIZ = process.cwd();
const PASTAS = ["app", "recursos", "lib"];
const MINIMO_DE_ARQUIVOS = 20;
const APELIDO = "@/"; // o apelido de import que aponta para a raiz
/** O nome que só o leitor cita: a tabela (ou o campo) do conteúdo pago. */
const TABELA_PAGA = "app_conteudos";
/** O único módulo que lê o conteúdo pago, e a função dele. */
const LEITOR = "recursos/itens/leitura-paga";
const FUNCAO = "lerConteudoPago";
/** Quem mais pode citar a tabela: a área de admin, que grava. */
const tambemCita = (arquivo: string) => arquivo.startsWith("recursos/admin/");
/** O único arquivo que chama o leitor: o componente de servidor (ou a rota) que mostra o texto. */
const QUEM_CHAMA = "recursos/itens/ConteudoPago.tsx";
const DE_NAVEGADOR = "use client"; // diretiva de código que vai para o navegador
const DE_CACHE = "use cache"; // diretiva de função guardada em cache compartilhado
/** O que código em cache compartilhado não importa, nem como tipo: leitura por pessoa e sessão. */
const SO_POR_PESSOA = [LEITOR, "lib/sessao", "lib/banco/servidor"];
/** O que código de navegador não importa em execução. */
const SO_DE_SERVIDOR = [LEITOR, "lib/banco/servidor", "lib/banco/servico"];
/** Como o código seleciona a coluna do conteúdo. Ajuste ao seu cliente de banco. */
const SELECIONA_O_CORPO = /\.select\(\s*(["'`])[^"'`]*\bcorpo\b[^"'`]*\1/g;

interface Fonte { arquivo: string; texto: string }
interface Import { destino: string; soTipo: boolean; nomes: string[] | "*" }

const andar = (dir: string): string[] =>
  readdirSync(path.join(RAIZ, dir), { withFileTypes: true }).flatMap((e) => {
    if (e.isDirectory()) return andar(`${dir}/${e.name}`);
    return /\.tsx?$/.test(e.name) && !/\.(test|spec)\./.test(e.name) ? [`${dir}/${e.name}`] : [];
  });
const FONTES: Fonte[] = PASTAS.flatMap(andar).sort()
  .map((arquivo) => ({ arquivo, texto: readFileSync(path.join(RAIZ, arquivo), "utf8") }));
const fonteDe = (arquivo: string) => FONTES.find((f) => f.arquivo === arquivo);
const infratores = (regra: (f: Fonte) => boolean) => FONTES.filter(regra).map((f) => f.arquivo);
const temDiretiva = (texto: string, diretiva: string) =>
  new RegExp(`^\\s*(["'])${diretiva}\\1\\s*;?\\s*(?://.*)?$`, "m").test(texto);

/** Apelido e caminho relativo viram o mesmo caminho, a partir da raiz e sem extensão. */
function resolver(deArquivo: string, alvo: string): string {
  const semExt = (v: string) => v.replace(/\.(tsx?|js)$/, "");
  if (alvo.startsWith(APELIDO)) return semExt(alvo.slice(APELIDO.length));
  if (!alvo.startsWith(".")) return alvo; // nome de pacote
  return semExt(path.posix.normalize(path.posix.join(path.posix.dirname(deArquivo), alvo)));
}

function importsDe({ arquivo, texto }: Fonte): Import[] {
  const refs: Import[] = [];
  const somar = (alvo: ts.Node | undefined, soTipo: boolean, nomes: string[] | "*") => {
    if (!alvo || !ts.isStringLiteralLike(alvo)) return;
    refs.push({ destino: resolver(arquivo, alvo.text), soTipo, nomes });
  };
  const visitar = (no: ts.Node): void => {
    if (ts.isImportDeclaration(no)) {
      // O campo que marca `import type` muda de nome entre versões do compilador: confira.
      const c = no.importClause, b = c?.namedBindings;
      const el = b && ts.isNamedImports(b) ? [...b.elements] : [];
      const inteiro = !c || Boolean(c.name) || Boolean(b && ts.isNamespaceImport(b));
      const soTipo = Boolean(c?.isTypeOnly) || (!inteiro && el.every((e) => e.isTypeOnly));
      somar(no.moduleSpecifier, soTipo, inteiro ? "*" : el.map((e) => (e.propertyName ?? e.name).text));
    } else if (ts.isExportDeclaration(no)) {
      const c = no.exportClause;
      const el = c && ts.isNamedExports(c) ? c.elements.map((e) => (e.propertyName ?? e.name).text) : "*";
      somar(no.moduleSpecifier, no.isTypeOnly, el);
    } else if (ts.isCallExpression(no) && no.expression.kind === ts.SyntaxKind.ImportKeyword) {
      somar(no.arguments[0], false, "*"); // import dinâmico: traz o módulo inteiro
    }
    ts.forEachChild(no, visitar);
  };
  visitar(ts.createSourceFile(arquivo, texto, ts.ScriptTarget.Latest));
  return refs;
}

// As regras como predicados: a sanidade planta um violador em cada uma.
const citaATabela = (f: Fonte) =>
  f.texto.includes(TABELA_PAGA) && f.arquivo !== `${LEITOR}.ts` && !tambemCita(f.arquivo);
const chamaOLeitor = (f: Fonte) =>
  importsDe(f).some((i) => i.destino === LEITOR && (i.nomes === "*" || i.nomes.includes(FUNCAO)));
const cacheLePorPessoa = (f: Fonte) =>
  temDiretiva(f.texto, DE_CACHE) && importsDe(f).some((i) => SO_POR_PESSOA.includes(i.destino));
const navegadorLeServidor = (f: Fonte) =>
  temDiretiva(f.texto, DE_NAVEGADOR) &&
  importsDe(f).some((i) => !i.soTipo && SO_DE_SERVIDOR.includes(i.destino));
const selecoesDoCorpo = (f: Fonte) => [...f.texto.matchAll(SELECIONA_O_CORPO)].length;

describe("sanidade: o verificador prova que enxerga", () => {
  it("acha os fontes: caminho errado faria toda regra passar por vacuidade", () => {
    expect(FONTES.length, `só ${FONTES.length} arquivos lidos`).toBeGreaterThanOrEqual(MINIMO_DE_ARQUIVOS);
    for (const p of PASTAS) expect(FONTES.some((f) => f.arquivo.startsWith(`${p}/`)), p).toBe(true);
    expect(FONTES.some((f) => /\.(test|spec)\./.test(f.arquivo))).toBe(false);
  });

  it("cada regra acusa o violador plantado e poupa o inocente", () => {
    const plantar = (...linhas: string[]): Fonte =>
      ({ arquivo: "recursos/x/Exemplo.tsx", texto: linhas.join("\n") });
    const leitor = `${APELIDO}${LEITOR}`;
    const [nav, cache] = [`"${DE_NAVEGADOR}";`, `"${DE_CACHE}";`];
    const casos: [(f: Fonte) => boolean, Fonte, boolean][] = [
      [citaATabela, plantar(`banco.from("${TABELA_PAGA}")`), true],
      [citaATabela, plantar('banco.from("app_itens")'), false],
      [chamaOLeitor, plantar(`import { ${FUNCAO} } from "${leitor}";`), true],
      [chamaOLeitor, plantar(`import * as leitura from "${leitor}";`), true],
      [chamaOLeitor, plantar(`const m = await import(\`${leitor}\`);`), true],
      [chamaOLeitor, plantar(`import { type Resultado } from "${leitor}";`), false],
      [chamaOLeitor, plantar(`// import { ${FUNCAO} } from "${leitor}";`), false],
      [cacheLePorPessoa, plantar(cache, `import type { R } from "${leitor}";`), true],
      [cacheLePorPessoa, plantar(`// ${cache}`, `import { x } from "${leitor}";`), false],
      [navegadorLeServidor, plantar(nav, `import { ${FUNCAO} } from "${leitor}";`), true],
      [navegadorLeServidor, plantar(nav, `import type { R } from "${leitor}";`), false],
      [navegadorLeServidor, plantar(`import { ${FUNCAO} } from "${leitor}";`), false],
    ];
    for (const [regra, fonte, esperado] of casos) expect(regra(fonte), fonte.texto).toBe(esperado);
    expect(selecoesDoCorpo(plantar('.select("id, corpo")', ".select('titulo')"))).toBe(1);
  });
});

describe("fronteiras do conteúdo pago", () => {
  it("1. a tabela do conteúdo pago só é citada no leitor e na área de admin", () => {
    expect(infratores(citaATabela)).toEqual([]);
    // Controle positivo: o leitor existe e cita a tabela. Arquivo renomeado não passa em silêncio.
    expect(fonteDe(`${LEITOR}.ts`)?.texto ?? "", `${LEITOR}.ts sumiu`).toContain(TABELA_PAGA);
  });

  it("2. a função que lê o conteúdo pago só é importada por um arquivo", () => {
    expect(infratores(chamaOLeitor)).toEqual([QUEM_CHAMA]);
  });

  it("3. código em cache compartilhado não importa leitura por pessoa nem sessão", () => {
    // Sem cache compartilhado no projeto, apague esta regra: do contrário ela não olha nada.
    expect(FONTES.some((f) => temDiretiva(f.texto, DE_CACHE)), "nenhum arquivo com cache").toBe(true);
    expect(infratores(cacheLePorPessoa)).toEqual([]);
  });

  it("4. código de navegador não importa o leitor nem os clientes de servidor", () => {
    expect(FONTES.some((f) => temDiretiva(f.texto, DE_NAVEGADOR)), "nenhum de navegador").toBe(true);
    for (const m of SO_DE_SERVIDOR) expect(fonteDe(`${m}.ts`), `${m} não existe mais`).toBeDefined();
    expect(infratores(navegadorLeServidor)).toEqual([]);
  });

  it("5. o corpo é selecionado uma vez, no leitor, e em nenhum outro lugar fora do admin", () => {
    const fora = FONTES.filter((f) => f.arquivo !== `${LEITOR}.ts` && !tambemCita(f.arquivo));
    expect(fora.filter((f) => selecoesDoCorpo(f) > 0).map((f) => f.arquivo)).toEqual([]);
    expect(selecoesDoCorpo(fonteDe(`${LEITOR}.ts`) ?? { arquivo: "", texto: "" })).toBe(1);
  });
});

// O que adaptar:
// - PASTAS, MINIMO_DE_ARQUIVOS, APELIDO e as duas diretivas (as do molde são as do React e do Next.js).
// - TABELA_PAGA, LEITOR, FUNCAO, QUEM_CHAMA, as duas listas de módulos e SELECIONA_O_CORPO.
// - Em Jest, tire a linha do import do Vitest. Em outra linguagem, copie as regras e leia os
//   imports com o analisador sintático que ela traz.
// - Regra nova: predicado, violador plantado na sanidade e controle positivo, na mesma mudança.
