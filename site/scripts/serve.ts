// Serves the static build in dist/ for the docs container (node scripts/serve.ts).
// /docs/introduction and /docs/introduction/ both answer 200: the build writes
// <path>/index.html and this server accepts either spelling. "/" is a 307.
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, resolve } from "node:path";
import { posix } from "node:path";

const root = resolve(import.meta.dirname, "..", "dist");
const port = Number(process.env.PORT ?? 3000);

const types: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

async function isFile(path: string): Promise<boolean> {
  try {
    return (await stat(path)).isFile();
  } catch {
    return false;
  }
}

createServer(async (req, res) => {
  const pathname = decodeURIComponent(new URL(req.url ?? "/", "http://localhost").pathname);
  const clean = posix.normalize(pathname);

  if (clean === "/" || clean === "/docs" || clean === "/docs/") {
    res.writeHead(307, { Location: "/docs/introduction" }).end();
    return;
  }

  for (const candidate of [clean, posix.join(clean, "index.html"), `${clean}.html`]) {
    const file = join(root, candidate);
    if (!file.startsWith(root) || !(await isFile(file))) continue;

    const immutable = candidate.startsWith("/_astro/") || candidate.startsWith("\\_astro\\");
    res.writeHead(200, {
      "Content-Type": types[extname(file)] ?? "application/octet-stream",
      "Cache-Control": immutable ? "public, max-age=31536000, immutable" : "public, max-age=300",
      "X-Content-Type-Options": "nosniff",
    });
    createReadStream(file).pipe(res);
    return;
  }

  res.writeHead(404, { "Content-Type": "text/html; charset=utf-8" });
  const notFound = join(root, "404.html");
  if (await isFile(notFound)) createReadStream(notFound).pipe(res);
  else res.end("Not found");
}).listen(port, process.env.HOST ?? "0.0.0.0", () => console.log(`docs listening on :${port}`));
