// uso: node dbg.mjs <video ou prefixo> <t> "<expressão JS>"   — inspeciona o estado do vídeo num instante
import { chromium } from 'playwright';
import http from 'http'; import { readFileSync, readdirSync, existsSync, statSync } from 'fs'; import path from 'path';
import { fileURLToPath } from 'url';
import { fileURLToPath } from 'url';
const [name, t, expr] = process.argv.slice(2); const ROOT = process.cwd();
const MOTOR = path.dirname(fileURLToPath(import.meta.url));   // o motor e o node_modules ficam na skill
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
const s = http.createServer((q, r) => { const rel = decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, ''); let p = path.join(ROOT, rel); if (!existsSync(p)) { const z = path.join(MOTOR, rel); if (z.startsWith(MOTOR) && existsSync(z)) p = z; } if (!existsSync(p) || statSync(p).isDirectory()) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' }); r.end(readFileSync(p)); });
await new Promise(r => s.listen(0, r));
const b = await chromium.launch({ args: [...(process.platform === 'darwin' ? ['--use-angle=metal'] : []), '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } }); p.on('pageerror', e => console.log('ERRO:', e.message));
await p.addInitScript(() => { window.__render = true; });
const all = readdirSync('videos').filter(d => existsSync(`videos/${d}/index.html`)), dir = all.find(d => d === name) ?? all.find(d => d.startsWith(name));
if (!dir) { console.log('vídeo não encontrado:', name); process.exit(1); }   // aceita prefixo, como o render.mjs
await p.goto(`http://127.0.0.1:${s.address().port}/videos/${dir}/index.html`); await p.waitForFunction(() => window.__ready);
await p.evaluate(t => window.__seek(+t), t);
console.log(JSON.stringify(await p.evaluate(e => eval(e), expr), null, 1));
await b.close(); s.close();
