// Molde da variante web. Generalizado de uso real, com nomes genéricos.
// Não foi executado nesta forma: rode antes de confiar.
// Ação de servidor testada sem banco. O cliente falso registra cada chamada, e o teste afirma
// ordem e ausência. Troque só as bordas (guarda, cliente do banco): a regra roda de verdade.
import assert from "node:assert/strict";
import { it } from "node:test";
import { type Bordas, salvarItem } from "./acoes";

type Resultado = { data: unknown; error: unknown };
type Chamada = { tabela: string; operacao: string; metodo: string; args: unknown[] };
const OK: Resultado = { data: null, error: null };
/** Cliente encadeável: registra as chamadas; `await` resolve com o de "tabela.operação". */
export function clienteFalso(resultados: Record<string, Resultado> = {}) {
  const chamadas: Chamada[] = [];
  const from = (tabela: string) => {
    let operacao = "";
    const construtor: Record<string, unknown> = {};
    for (const metodo of ["select", "insert", "update", "delete", "eq", "single"]) {
      construtor[metodo] = (...args: unknown[]) => {
        if (operacao === "") operacao = metodo; // a primeira chamada dá nome à operação
        chamadas.push({ tabela, operacao, metodo, args });
        return construtor;
      };
    }
    construtor.then = (ok: (v: Resultado) => unknown, erro: (r: unknown) => unknown) =>
      Promise.resolve(resultados[`${tabela}.${operacao}`] ?? OK).then(ok, erro);
    return construtor;
  };
  return { from, chamadas };
}

const SEM_SESSAO = new Error("sem sessão"); // o que a guarda lança para quem não entrou
const ACOES: [string, (bordas: Bordas) => Promise<unknown>][] = [ // todas; ação nova entra aqui
  ["salvarItem", (bordas) => salvarItem(bordas, { titulo: "" })], // com entrada inválida
];

for (const [nome, executar] of ACOES) {
  it(`${nome}: sem sessão, o erro da guarda sobe e nada toca o banco`, async () => {
    const banco = clienteFalso();
    const exigirSessao = async () => { throw SEM_SESSAO; };
    // Entrada inválida e sem sessão: quem barra é a guarda, antes da validação.
    await assert.rejects(executar({ exigirSessao, banco }), (erro) => erro === SEM_SESSAO);
    assert.deepEqual(banco.chamadas, []); // ausência de chamada é a prova
  });
}

// O que adaptar:
// - `./acoes`, ACOES (todas as ações do arquivo) e os métodos que o cliente do banco encadeia.
// - As bordas entram aqui por parâmetro. Se as ações importam a guarda e o cliente, troque os
//   módulos pelo mecanismo do executor de unidade do projeto e zere as peças antes de cada teste.
// - `it` é do executor embutido do Node.js: troque pelo do executor de unidade do projeto.
