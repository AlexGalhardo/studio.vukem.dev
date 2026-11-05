// Molde: configuração do Playwright com o projeto de preparo, desktop, celular e as travas.
// Copie para a raiz do projeto. Passou pelo verificador de tipos com @playwright/test 1.64; não
// foi executado nesta forma. O projeto "preparo" aponta para <testes>/preparo.setup.ts, um arquivo
// de 12 linhas que está em references/personas-e-sessoes.md §3.
import { existsSync } from "node:fs";
import { defineConfig, devices } from "@playwright/test";
import { exigirLocal, lerAmbienteDeTeste } from "./tests/e2e/personas";

// O Playwright não lê o arquivo de ambiente do framework: carregue-o aqui (Node 20.12 ou mais novo).
if (existsSync(".env.local")) process.loadEnvFile(".env.local");

const noCI = Boolean(process.env.CI);
// Porta própria: não disputa com o servidor de desenvolvimento que o dono deixou aberto.
const porta = Number(process.env.PORTA_E2E ?? 3100);

// Travas. Rodam ao carregar a configuração: nenhum comando do executor passa sem elas.
const baseURL = exigirLocal(
  process.env.E2E_BASE_URL ?? `http://127.0.0.1:${porta}`,
  "E2E_BASE_URL",
);
lerAmbienteDeTeste();

// Teste que confere a resposta crua não muda com o tamanho da tela: roda só no desktop.
const SO_NO_DESKTOP = /guarda-admin\.spec\.ts/;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  // Um `.only` esquecido derruba o CI, em vez de pular o resto da suíte em silêncio.
  forbidOnly: noCI,
  // Local: nenhuma repetição, para a instabilidade aparecer a quem escreve. CI: até 2.
  retries: noCI ? 2 : 0,
  // CI: anotações no pedido de merge e relatório em HTML, que o job guarda quando falha.
  reporter: noCI ? [["github"], ["html", { open: "never" }]] : "list",
  // Os limites ficam no padrão (30 s por teste, 5 s por conferência). Passo longo de verdade
  // ganha limite maior só naquele teste, com o motivo no comentário.
  use: {
    baseURL,
    // O rastro é gravado na primeira repetição: no CI, toda falha repetida deixa o que olhar.
    trace: "on-first-retry",
    // Fixos: o resultado não pode mudar com a máquina que roda.
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
  },
  projects: [
    // Gera a sessão de cada persona uma vez; os outros dois dependem dele.
    { name: "preparo", testMatch: /preparo\.setup\.ts/ },
    // Nenhum projeto tem persona padrão: sem `test.use({ storageState })`, o bloco é visitante.
    {
      name: "desktop",
      dependencies: ["preparo"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "celular",
      dependencies: ["preparo"],
      testIgnore: SO_NO_DESKTOP,
      use: { ...devices["Pixel 7"] },
    },
  ],
  webServer: {
    // Sempre o build de produção. No CI o build é um passo à parte, para o vermelho dizer onde foi.
    command: noCI ? "npm run start" : "npm run build && npm run start",
    // Soma ao ambiente do processo (conferido no pacote 1.64).
    env: { PORT: String(porta) },
    url: baseURL,
    // Nunca reaproveita: se já há algo na porta, o Playwright para com "is already used".
    reuseExistingServer: false,
    timeout: 300_000,
  },
});

// O que adaptar:
// - ".env.local": o arquivo de ambiente local do projeto. O servidor sob teste tem de ler o mesmo.
// - testDir e o caminho do import de personas: a pasta dos testes.
// - "npm run build" e "npm run start": os comandos do projeto. Se o servidor não lê PORT do
//   ambiente, passe a porta no comando.
// - locale e timezoneId: os do público do produto.
// - devices["Pixel 7"] usa o Chromium. Aparelho com outro motor pede instalar esse navegador no CI.
// - Projeto que precisa de mais um navegador: um projeto a mais, com as mesmas dependências.
