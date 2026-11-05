// Molde da variante web. Generalizado de uso real, com nomes genéricos.
// Não foi executado nesta forma: rode antes de confiar.
// Teste de vazamento: procura os marcadores dos dados de exemplo na resposta crua, por persona.
// Sem navegador e sem seguir redirecionamento. Um tamanho de tela só: a resposta crua não muda.
import { readdirSync, readFileSync } from "node:fs";
import { type APIRequestContext, expect, test } from "@playwright/test";
import { ESTADO, VISITANTE } from "./sessoes-de-teste";

const PREFIXO = "APP-SEED-"; // procurado inteiro: pega o marcador que a lista ainda não conhece
const RESTRITOS = ["APP-SEED-RESTRITO-3T8V2L", "APP-SEED-RESTRITO-7F3K9Q"]; // primeira e última
const LIVRE = "APP-SEED-LIVRE-2M8XZD"; // o visitante deve receber: prova que a busca enxerga
const RASCUNHOS = ["APP-SEED-RASCUNHO-9B4T1W", "APP-SEED-VERSAONOVA-K4P7QD"]; // ninguém recebe
const [ROTA_RESTRITA, ROTA_LIVRE] = ["/itens/<slug restrito>", "/itens/<slug livre>"];
const ROTAS_PUBLICAS = ["/", "/itens", ROTA_RESTRITA, ROTA_LIVRE];
const PAGINAS_PUBLICAS = 3; // arquivos de página por trás das rotas acima
const PEDE_PAYLOAD = { "<cabeçalho que pede o payload>": "1" }; // não aparece na tela e vaza
const TIPO_DO_PAYLOAD = "<tipo de conteúdo do payload>";
const SEM_ACESSO = [
  { persona: "visitante", estado: VISITANTE, proprio: "botao-entrar", alheio: "botao-sair" },
  { persona: "logado", estado: ESTADO.logado, proprio: "botao-sair", alheio: "botao-entrar" },
];

async function cru(request: APIRequestContext, rota: string, payload = false) {
  const r = await request.get(rota, { headers: payload ? PEDE_PAYLOAD : {}, maxRedirects: 0 });
  return { status: r.status(), tipo: r.headers()["content-type"] ?? "", corpo: await r.text() };
}

test("as listas cobrem os dados de exemplo e as páginas públicas", () => {
  const dados = readFileSync("<arquivo dos dados de exemplo>", "utf8");
  const achados = [...new Set(dados.match(/APP-SEED-[A-Z]+-[A-Z0-9]{6}\b/g) ?? [])].sort();
  expect(achados, "marcador novo: classifique").toEqual([...RESTRITOS, LIVRE, ...RASCUNHOS].sort());
  const paginas = readdirSync("<pasta das rotas públicas>", { recursive: true })
    .filter((arquivo) => String(arquivo).endsWith("<nome do arquivo de página>"));
  expect(paginas.length, "página nova: acrescente a rota a ROTAS_PUBLICAS").toBe(PAGINAS_PUBLICAS);
});

for (const { persona, estado, proprio, alheio } of SEM_ACESSO) {
  test.describe(`sem acesso: ${persona}`, () => {
    test.use({ storageState: estado });
    test("a persona é quem diz ser", async ({ request }) => {
      const { corpo } = await cru(request, ROTA_RESTRITA);
      expect(corpo).toContain(`data-testid="${proprio}"`);
      expect(corpo).not.toContain(`data-testid="${alheio}"`);
    });
    for (const rota of ROTAS_PUBLICAS) {
      for (const payload of [false, true]) {
        test(`${rota}, payload ${payload}: nada restrito`, async ({ request }) => {
          const { status, tipo, corpo } = await cru(request, rota, payload);
          expect(status).toBe(200); // redirecionamento e resposta vazia também "não contêm"
          expect(tipo).toContain(payload ? TIPO_DO_PAYLOAD : "text/html");
          expect(corpo.length).toBeGreaterThan(1000);
          if (rota === ROTA_RESTRITA && !payload) expect(corpo).toContain('data-testid="bloqueio"');
          if (rota === ROTA_RESTRITA) expect(corpo).not.toContain('data-testid="dado-restrito"');
          const proibidos = rota === ROTA_LIVRE ? [...RESTRITOS, ...RASCUNHOS] : [PREFIXO];
          for (const m of proibidos) expect(corpo).not.toContain(m);
          if (rota === ROTA_LIVRE) expect(corpo).toContain(LIVRE); // controle positivo
        });
      }
    }
  });
}

for (const persona of ["pagante", "administrador"] as const) {
  test.describe(`controle positivo: ${persona}`, () => {
    test.use({ storageState: ESTADO[persona] });
    test("recebe os marcadores, na página e no payload, e nenhum rascunho", async ({ request }) => {
      for (const payload of [false, true]) {
        const { corpo } = await cru(request, ROTA_RESTRITA, payload);
        for (const m of RESTRITOS) expect(corpo).toContain(m);
        for (const m of RASCUNHOS) expect(corpo).not.toContain(m);
      }
    });
  });
}

// O que adaptar:
// - Os marcadores, as rotas e PAGINAS_PUBLICAS; os `data-testid` da persona, do bloqueio e do dado.
// - PEDE_PAYLOAD e TIPO_DO_PAYLOAD: os do framework. Sem payload à parte, tire esse laço.
// - Os três textos entre <> do primeiro teste: arquivo, pasta e nome do arquivo de página.
// - Dado que não aceita texto: procure o valor sentinela, ou afirme a ausência do nome do campo.
