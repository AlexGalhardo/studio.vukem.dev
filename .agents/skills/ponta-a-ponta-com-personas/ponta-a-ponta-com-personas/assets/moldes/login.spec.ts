// Molde: o login de verdade, pela tela, com o código lido na caixa de e-mail local.
// Copie para <testes>/login.spec.ts. Saiu de um teste em uso, com os nomes trocados; passou pelo
// verificador de tipos com @playwright/test 1.64 e não foi executado nesta forma. A leitura da
// caixa usa a API do Mailpit, como ele vem no Supabase local; outra caixa: troque `lerEmail`.
import { type APIRequestContext, expect, type Page, test, type TestInfo } from "@playwright/test";
import { apagarContasDeTeste, emailDeTeste, exigirLocal, VISITANTE } from "./personas";

const CAIXA = exigirLocal(process.env.URL_DA_CAIXA ?? "http://127.0.0.1:54324", "URL_DA_CAIXA");
const DIA = 24 * 60 * 60;
/** Requisito do produto: a sessão dura pelo menos isto. Menos é regressão. */
const DIAS_MINIMOS_DE_SESSAO = 30;
/** O cookie da sessão, inteiro ou fatiado (.0, .1…), com o nome que a biblioteca grava. */
const COOKIE_DE_SESSAO = /^sb-.+-auth-token(\.\d+)?$/;

test.use({ storageState: VISITANTE });

// Em fila dentro do arquivo: todos pedem código ao mesmo serviço de login, que limita pedidos
// por origem. Desktop e celular seguem em paralelo entre si.
test.describe.configure({ mode: "default" });

// Uma lista por processo: o afterAll apaga só as contas que este processo criou.
const criadas: string[] = [];

function novaConta(info: TestInfo): string {
  const email = emailDeTeste(`login-${info.project.name}-${info.workerIndex}-${criadas.length}`);
  criadas.push(email);
  return email;
}

test.afterAll(() => apagarContasDeTeste(criadas));

type Mensagem = { Subject: string; HTML: string };

/** O e-mail mais recente para o endereço. Espera ativa com limite: o envio é assíncrono. */
async function lerEmail(request: APIRequestContext, email: string): Promise<Mensagem> {
  const achado: { mensagem?: Mensagem } = {};
  await expect
    .poll(
      async () => {
        const busca = await request.get(`${CAIXA}/api/v1/search`, {
          params: { query: `to:"${email}"` },
        });
        const { messages } = (await busca.json()) as { messages?: { ID: string }[] };
        const ultima = messages?.[0];
        if (!ultima) return false;
        const detalhe = await request.get(`${CAIXA}/api/v1/message/${ultima.ID}`);
        achado.mensagem = (await detalhe.json()) as Mensagem;
        return true;
      },
      { message: `o e-mail do código não chegou para ${email}`, timeout: 30_000 },
    )
    .toBe(true);
  if (!achado.mensagem) throw new Error("Ponta a ponta: e-mail sem corpo.");
  return achado.mensagem;
}

/** O código do corpo. Sem as tags, não sobra cor em hexadecimal para confundir com ele. */
function codigoDe(mensagem: Mensagem): string {
  const texto = mensagem.HTML.replace(/<[^>]*>/g, " ");
  const codigo = /(?<!\d)\d{6,10}(?!\d)/.exec(texto)?.[0];
  if (!codigo) throw new Error("Ponta a ponta: o e-mail não trouxe um código.");
  return codigo;
}

async function entrar(page: Page, request: APIRequestContext, email: string) {
  await page.getByLabel("Seu e-mail").fill(email);
  await page.getByRole("button", { name: "Enviar código" }).click();
  await expect(page.getByLabel("Código do e-mail")).toBeVisible();
  await page.getByLabel("Código do e-mail").fill(codigoDe(await lerEmail(request, email)));
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
}

/** O que só aparece para quem está logado. */
function sinalDeLogado(page: Page) {
  return page.getByRole("banner").getByRole("link", { name: "Minha conta" });
}

test("entra com o código do e-mail, chega ao destino e a sessão dura", async ({
  page,
  request,
}, info) => {
  const email = novaConta(info);
  await page.goto("/entrar?next=%2Fconta");
  await entrar(page, request, email);
  await expect(page).toHaveURL(/\/conta$/);
  await expect(sinalDeLogado(page)).toBeVisible();

  const cookies = (await page.context().cookies()).filter((c) => COOKIE_DE_SESSAO.test(c.name));
  expect(cookies.length, "nenhum cookie de sessão foi gravado").toBeGreaterThan(0);
  const minimo = Date.now() / 1000 + DIAS_MINIMOS_DE_SESSAO * DIA;
  for (const cookie of cookies) {
    expect(cookie.expires, `${cookie.name} vence antes do prometido`).toBeGreaterThan(minimo);
  }
});

for (const fora of ["https://fora.example.test/", "//fora.example.test/"]) {
  test(`caminho de volta externo (${fora}) é ignorado`, async ({ page, request, baseURL }, info) => {
    await page.goto(`/entrar?next=${encodeURIComponent(fora)}`);
    await entrar(page, request, novaConta(info));
    await expect(sinalDeLogado(page)).toBeVisible();
    expect(new URL(page.url()).origin).toBe(new URL(baseURL ?? "").origin);
  });
}

test("sair encerra a sessão", async ({ page, request }, info) => {
  await page.goto("/entrar");
  await entrar(page, request, novaConta(info));
  await expect(sinalDeLogado(page)).toBeVisible();
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(sinalDeLogado(page)).toHaveCount(0);
  await page.goto("/conta");
  await expect(page).toHaveURL(/\/entrar\?next=%2Fconta$/);
});

// O que adaptar:
// - Os rótulos ("Seu e-mail", "Enviar código", "Código do e-mail", "Entrar", "Sair", "Minha
//   conta") e as rotas ("/entrar", "/conta", "?next="): os do produto.
// - COOKIE_DE_SESSAO e DIAS_MINIMOS_DE_SESSAO: o nome que a biblioteca grava e o que o dono pediu.
// - Login por link em vez de código: `codigoDe` vira "o primeiro href do corpo", e o teste navega
//   até ele. Login por senha: a conta nasce pela tela de cadastro, com o mesmo e-mail de teste.
// - Produto com passo obrigatório depois do primeiro login (boas-vindas): a conta nova cai nele.
//   Responda o passo dentro de `entrar`, ou confira aqui que não dá para sair dele sem responder.
