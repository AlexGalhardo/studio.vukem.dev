// Locally, stop the Vite dev server and delete resources/public/hot first: a
// leftover hot file makes the app load its scripts from the dev server.
import { defineConfig } from "@playwright/test";

const server = (port: number, mode: string) => ({
  command: "go test ./tests -run ^TestE2EServer$ -count=1 -timeout 20m",
  cwd: "..",
  url: `http://127.0.0.1:${port}/up`,
  reuseExistingServer: !process.env.CI,
  timeout: 180_000,
  env: { STUDIO_E2E_ADDR: `127.0.0.1:${port}`, STUDIO_E2E_MODE: mode },
});

export default defineConfig({
  testDir: "./specs",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: { trace: "retain-on-failure" },
  projects: [
    { name: "ok", use: { baseURL: "http://127.0.0.1:3101" }, testMatch: /ok\.spec\.ts/ },
    { name: "model-failure", use: { baseURL: "http://127.0.0.1:3102" }, testMatch: /model\.spec\.ts/ },
    { name: "render-failure", use: { baseURL: "http://127.0.0.1:3103" }, testMatch: /render\.spec\.ts/ },
  ],
  webServer: [server(3101, "ok"), server(3102, "model"), server(3103, "render")],
});
