// catalogo.mjs — imprime, em JSON, o `meta` de cada cena da biblioteca (sem abrir browser, sem DA).
// Uso: node catalogo.mjs [pasta das cenas]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const pasta = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(aqui, '..', 'cenas');
/** Regra de um parâmetro, por dentro: lista com `itens` e objeto com `campos` descem junto. */
function regra(v) {
  const r = {
    tipo: v.tipo || 'texto', obrigatorio: !!v.obrigatorio,
    padrao: v.padrao === undefined ? null : v.padrao,
    descricao: v.descricao || '',
  };
  if (v.opcoes) r.opcoes = v.opcoes;
  if (v.min !== undefined) r.min = v.min;
  if (v.max !== undefined) r.max = v.max;
  if (v.itens) r.itens = regra(v.itens);
  if (v.campos) r.campos = Object.fromEntries(Object.entries(v.campos).map(([k, c]) => [k, regra(c)]));
  return r;
}

const saida = [];
const falhas = [];

for (const arq of fs.readdirSync(pasta).filter((f) => f.endsWith('.js') && !f.startsWith('_')).sort()) {
  const caminho = path.join(pasta, arq);
  try {
    const mod = await import(pathToFileURL(caminho).href);
    const m = mod.meta || {};
    saida.push({
      nome: m.nome || arq.replace(/\.js$/, ''),
      arquivo: arq,
      descricao: m.descricao || '',
      dur_padrao: m.dur_padrao ?? null,
      alfa_padrao: !!m.alfa_padrao,
      formatos: m.formatos || null,
      params: Object.fromEntries(Object.entries(m.params || {}).map(([k, v]) => [k, regra(v)])),
    });
  } catch (e) {
    falhas.push({ arquivo: arq, erro: e && e.message ? e.message : String(e) });
  }
}

console.log(JSON.stringify({ pasta, cenas: saida, falhas }, null, 1));
if (falhas.length) process.exit(1);
