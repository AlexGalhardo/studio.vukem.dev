import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

const root = path.dirname(fileURLToPath(import.meta.url));

// Static HTML served by scripts/serve.ts. "/" and "/docs" open the introduction.
export default defineConfig({
  site: "https://studio.vukem.dev",
  output: "static",
  outDir: "dist",
  trailingSlash: "always",
  build: { format: "directory" },
  server: { port: 3000 },
  integrations: [react()],
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: { "@": root },
    },
  },
  redirects: {
    "/": "/docs/introduction/",
    "/docs": "/docs/introduction/",
  },
});
