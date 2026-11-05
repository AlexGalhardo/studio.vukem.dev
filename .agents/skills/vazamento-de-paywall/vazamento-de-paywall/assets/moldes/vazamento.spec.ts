// Molde: teste de vazamento de conteúdo pago, em Playwright. Procura os marcadores dos dados de
// exemplo na resposta crua de cada rota, por persona, sem abrir navegador. Saiu de um teste em
// uso (Next.js com payload de componentes de servidor), com os nomes trocados. Passou no
// verificador de tipos; não foi executado nesta forma: ajuste as constantes e rode.
// O teste de cache, no fim, é adaptação: não existia no sistema de origem.
import { readFileSync } from "node:fs";
import { type APIRequestContext, expect, test } from "@playwright/test";
import { ESTADO, VISITANTE } from "./personas";

const DADOS_DE_EXEMPLO = "banco/dados-de-exemplo.sql";
const MARCADOR = /\b(?:PAGO|LIVRE|RASCUNHO)-(?:INICIO|FIM)-[A-Z0-9]{6}\b/g;
const ROTA_PAGA = "/itens/item-pago-a";
const DA_ROTA_PAGA = ["PAGO-INICIO-R3NM3R", "PAGO-FIM-DTVAV3"]; // primeira e última linha
/** Rota de cada item pago e os dois marcadores do corpo dele. */
const PAGOS: Record<string, string[]> = {
  [ROTA_PAGA]: DA_ROTA_PAGA,
  "/itens/item-pago-b": ["PAGO-INICIO-HK8HAB", "PAGO-FIM-EBR9NW"],
};
const LIVRE = { rota: "/itens/item-livre", marcadores: ["LIVRE-INICIO-AXWPYX", "LIVRE-FIM-P97H5R"] };
const RASCUNHO = {
  rota: "/itens/item-rascunho",
  marcadores: ["RASCUNHO-INICIO-JWUNNM", "RASCUNHO-FIM-GPGMG6"],
};
const TODOS_PAGOS = Object.values(PAGOS).flat();
/** Toda rota pública que pode mostrar um item: inicial, listagens, busca, feed e cada item. */
const ROTAS = ["/", "/itens", ...Object.keys(PAGOS), LIVRE.rota];
/** A classe inteira: pega o marcador pago ou de rascunho que a lista ainda não conhece. */
const CLASSES_PROIBIDAS = ["PAGO-INICIO-", "PAGO-FIM-", "RASCUNHO-INICIO-", "RASCUNHO-FIM-"];
/** Nomes que nunca chegam a ninguém: a coluna do caminho do arquivo pago, o repositório privado. */
const NOMES_INTERNOS = ["caminho_do_arquivo", "arquivos-privados"];
/** Formas em que o servidor responde a mesma rota. Sem payload à parte, deixe só a página. */
const FORMAS: { nome: string; cabecalhos: Record<string, string>; tipo: string }[] = [
  { nome: "página", cabecalhos: {}, tipo: "text/html" },
  { nome: "payload", cabecalhos: { RSC: "1" }, tipo: "text/x-component" },
];
const TAMANHO_MINIMO = 1000;
const SEM_ACESSO = [
  { persona: "visitante", estado: VISITANTE, proprio: "botao-entrar", alheio: "botao-sair" },
  { persona: "logado sem plano", estado: ESTADO.logado, proprio: "botao-sair", alheio: "botao-entrar" },
];
const COM_ACESSO = [["assinante", ESTADO.assinante], ["admin", ESTADO.admin]] as const;
const TODAS = [["visitante", VISITANTE], ["logado sem plano", ESTADO.logado], ...COM_ACESSO] as const;

/** GET cru. Segue redirecionamento, e por isso devolve o caminho final para ser conferido. */
async function cru(request: APIRequestContext, rota: string, cabecalhos: Record<string, string>) {
  const r = await request.get(rota, { headers: cabecalhos });
  return {
    status: r.status(),
    caminho: new URL(r.url()).pathname,
    tipo: r.headers()["content-type"] ?? "",
    cache: r.headers()["cache-control"] ?? "",
    corpo: await r.text(),
  };
}

function semNenhum(corpo: string, proibidos: readonly string[], onde: string) {
  for (const m of proibidos) expect(corpo, `"${m}" vazou em ${onde}`).not.toContain(m);
}

test("lista conferida: os marcadores do teste são os dos dados de exemplo", () => {
  const achados = new Set(readFileSync(DADOS_DE_EXEMPLO, "utf8").match(MARCADOR) ?? []);
  const conhecidos = new Set([...TODOS_PAGOS, ...LIVRE.marcadores, ...RASCUNHO.marcadores]);
  expect([...achados].sort(), "marcador novo: classifique no teste").toEqual([...conhecidos].sort());
});

for (const { persona, estado, proprio, alheio } of SEM_ACESSO) {
  test.describe(`sem acesso: ${persona}`, () => {
    test.use({ storageState: estado });

    test("a persona é quem diz ser", async ({ request }) => {
      const { corpo } = await cru(request, ROTA_PAGA, {});
      expect(corpo, "sessão vencida? rode o preparo").toContain(`data-testid="${proprio}"`);
      expect(corpo).not.toContain(`data-testid="${alheio}"`);
    });

    for (const rota of ROTAS) {
      for (const forma of FORMAS) {
        test(`${rota} (${forma.nome}): resposta provada e nada pago`, async ({ request }) => {
          const r = await cru(request, rota, forma.cabecalhos);
          // Prova da resposta: erro, redirecionamento e resposta vazia também "não contêm".
          expect(r.status).toBe(200);
          expect(r.caminho, "foi parar em outra página").toBe(rota);
          expect(r.tipo).toContain(forma.tipo);
          expect(r.corpo.length).toBeGreaterThan(TAMANHO_MINIMO);
          if (rota in PAGOS && forma.nome === "página") {
            expect(r.corpo).toContain('data-testid="bloqueio"');
            expect(r.corpo).not.toContain('data-testid="conteudo-pago"');
          }
          const onde = `${rota} (${forma.nome}), como ${persona}`;
          semNenhum(r.corpo, [...TODOS_PAGOS, ...CLASSES_PROIBIDAS, ...NOMES_INTERNOS], onde);
          // Controle positivo: o item livre chega. Sem isso, um teste cego estaria verde.
          if (rota === LIVRE.rota) for (const m of LIVRE.marcadores) expect(r.corpo).toContain(m);
        });
      }
    }
  });
}

for (const [persona, estado] of COM_ACESSO) {
  test.describe(`controle positivo: ${persona}`, () => {
    test.use({ storageState: estado });
    for (const forma of FORMAS) {
      test(`recebe as duas pontas do item pago (${forma.nome})`, async ({ request }) => {
        const r = await cru(request, ROTA_PAGA, forma.cabecalhos);
        expect(r.status).toBe(200);
        for (const m of DA_ROTA_PAGA) expect(r.corpo, `${m} não chegou a quem paga`).toContain(m);
      });
    }
  });
}

for (const [persona, estado] of TODAS) {
  test.describe(`rascunho: ${persona}`, () => {
    test.use({ storageState: estado });
    test("rota pública não entrega rascunho nem nome interno a ninguém", async ({ request }) => {
      for (const rota of [...ROTAS, RASCUNHO.rota]) {
        const { corpo } = await cru(request, rota, {});
        semNenhum(corpo, [...RASCUNHO.marcadores, ...NOMES_INTERNOS], `${rota}, como ${persona}`);
      }
    });
  });
}

test("cache: o assinante pede antes e o visitante continua sem", async ({ playwright, baseURL }) => {
  const assinante = await playwright.request.newContext({ baseURL, storageState: ESTADO.assinante });
  const visitante = await playwright.request.newContext({ baseURL, storageState: VISITANTE });
  for (const forma of FORMAS) {
    const antes = await cru(assinante, ROTA_PAGA, forma.cabecalhos);
    for (const m of DA_ROTA_PAGA) expect(antes.corpo).toContain(m);
    expect(antes.cache, "resposta com conteúdo pago liberada para cache compartilhado").not.toMatch(
      /\bpublic\b|s-maxage/,
    );
    const depois = await cru(visitante, ROTA_PAGA, forma.cabecalhos);
    semNenhum(depois.corpo, CLASSES_PROIBIDAS, `${ROTA_PAGA} (${forma.nome}), depois do assinante`);
  }
  await Promise.all([assinante.dispose(), visitante.dispose()]);
});

// O que adaptar:
// - DADOS_DE_EXEMPLO, as rotas e os marcadores (os mesmos do arquivo de dados de exemplo).
// - FORMAS: o cabeçalho e o tipo do payload são os do seu framework (aqui, os do Next.js).
// - Os `data-testid` da persona, do bloqueio e do conteúdo; NOMES_INTERNOS; TAMANHO_MINIMO.
// - Rode num tamanho de tela só: a resposta crua não muda com a tela.
