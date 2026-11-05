// Molde: guarda da área de admin. Quem não é admin não entra e não descobre o que há lá.
// Copie para <testes>/guarda-admin.spec.ts. Saiu de um teste em uso, com os nomes trocados; passou
// pelo verificador de tipos com @playwright/test 1.64 e não foi executado nesta forma.
import { readdirSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { ESTADO, VISITANTE } from "./personas";

/** Pasta das páginas restritas e o nome do arquivo de página do framework. */
const PASTA_DO_ADMIN = "app/admin";
const ARQUIVO_DE_PAGINA = "page.tsx";
const ROTA_DE_LOGIN = "/entrar";

/** Toda rota restrita. Nas dinâmicas, um identificador que existe nos dados de exemplo. */
const ROTAS = [
  "/admin",
  "/admin/itens",
  "/admin/itens/novo",
  "/admin/itens/10000000-0000-4000-8000-000000000001",
];
const ROTA_DE_AMOSTRA = "/admin/itens";

/** Textos que só as telas do admin têm: identificador de teste, rótulo de botão, campo interno. */
const MARCADORES = ["admin-itens", "Novo item", "rascunho-interno", "Ver o site"];

const SEM_ACESSO = [
  { persona: "visitante", estado: VISITANTE },
  { persona: "logado", estado: ESTADO.logado },
  { persona: "assinante", estado: ESTADO.assinante },
];

test("toda página restrita está na lista conferida", () => {
  const paginas = readdirSync(PASTA_DO_ADMIN, { recursive: true, encoding: "utf8" }).filter(
    (arquivo) => arquivo.endsWith(ARQUIVO_DE_PAGINA),
  );
  expect(paginas.length, "página nova no admin: acrescente a rota a ROTAS").toBe(ROTAS.length);
});

test.describe("admin", () => {
  test.use({ storageState: ESTADO.admin });

  // Controle positivo: sem ele, um marcador que mudou de nome faz o teste de baixo passar à toa.
  test("os marcadores aparecem nas respostas do admin", async ({ request }) => {
    const corpos = await Promise.all(ROTAS.map(async (rota) => (await request.get(rota)).text()));
    const tudo = corpos.join("\n");
    for (const marcador of MARCADORES) {
      expect(tudo, `"${marcador}" não aparece para o admin: o marcador ficou velho`).toContain(
        marcador,
      );
    }
  });

  test("entra e vê a tela", async ({ page }) => {
    await page.goto(ROTA_DE_AMOSTRA);
    await expect(page.getByRole("heading", { level: 1, name: "Itens" })).toBeVisible();
  });
});

test.describe("visitante", () => {
  test.use({ storageState: VISITANTE });

  test("vai para o login com o caminho de volta da página pedida, não um fixo", async ({
    page,
  }) => {
    for (const rota of ROTAS) {
      await page.goto(rota);
      const esperado = `${ROTA_DE_LOGIN}?next=${encodeURIComponent(rota)}`;
      await expect(page).toHaveURL((url) => url.pathname + url.search === esperado);
    }
  });
});

test.describe("logado sem papel de admin", () => {
  test.use({ storageState: ESTADO.logado });

  test("vê o mesmo 'não encontrado' de uma rota que não existe", async ({ page }) => {
    await page.goto("/rota-que-nao-existe");
    const titulo = await page.getByRole("heading", { level: 1 }).innerText();
    await page.goto(ROTA_DE_AMOSTRA);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(titulo);
  });
});

// A guarda não pode ser só visual. A resposta crua de cada rota, sem seguir o redirecionamento,
// não pode trazer nada da tela para quem não é admin: nem a lista, nem os dados do formulário.
for (const { persona, estado } of SEM_ACESSO) {
  test.describe(`resposta crua para ${persona}`, () => {
    test.use({ storageState: estado });

    for (const rota of ROTAS) {
      test(`${rota} não traz nada do admin`, async ({ request }) => {
        const resposta = await request.get(rota, { maxRedirects: 0 });
        const corpo = await resposta.text();
        for (const marcador of MARCADORES) {
          expect(corpo, `"${marcador}" vazou em ${rota}`).not.toContain(marcador);
        }
      });
    }
  });
}

// O que adaptar:
// - PASTA_DO_ADMIN e ARQUIVO_DE_PAGINA: onde o framework guarda as páginas restritas. Sem pasta de
//   rotas, troque o primeiro teste pela lista de rotas que o próprio framework imprime.
// - ROTAS, MARCADORES e o título "Itens": os do produto. Marcador bom não aparece em tela pública.
// - A página de "não encontrado" sem título de nível 1: compare outro elemento fixo dela.
// - "?next=": o nome do parâmetro de volta. Guarda que responde 404 para o visitante também serve:
//   troque o teste do visitante pelo de "não encontrado".
// - Em framework que envia a página em pedaços, o código de status pode ser 200 mesmo com a guarda
//   funcionando: por isso o molde confere o corpo e a tela, não o status.
