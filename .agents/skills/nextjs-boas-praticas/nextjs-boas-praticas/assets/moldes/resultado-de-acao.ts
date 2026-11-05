// Molde: o retorno padrão de toda ação de servidor e o único ponto de chamada no cliente.
// Destino sugerido: lib/action-result.ts. É importado pelas ações (servidor) e pelos componentes
// de cliente, então não importe aqui validador de schema nem módulo só de servidor: o que este
// arquivo importa vai junto para o navegador.

import { unstable_rethrow } from "next/navigation";

/** Sucesso com dado, ou erro com uma frase pronta para a tela. A ação nunca lança para o cliente. */
export type ActionResult<T = null> = { ok: true; data: T } | { ok: false; error: string };

export function ok<T>(data: T): ActionResult<T> {
  return { ok: true, data };
}

export function fail<T = null>(error: string): ActionResult<T> {
  return { ok: false, error };
}

/** Erro de banco: mensagem genérica. O detalhe vai para o log do servidor, nunca para a tela. */
export const SAVE_ERROR = "Não deu para salvar agora. Tente de novo.";

export const CONNECTION_ERROR =
  "Não deu para falar com o servidor. Nada do que você digitou foi perdido: tente de novo.";

/**
 * Toda chamada de ação no cliente passa por aqui. Sem isto, uma falha de rede sobe para o
 * error.tsx, que desmonta o formulário e leva junto o que a pessoa digitou.
 * `unstable_rethrow` deixa passar o redirect e o notFound que a guarda lança; qualquer outra
 * rejeição vira `{ ok: false, error }`. A API é marcada como instável: confira na sua versão.
 */
export async function runAction<T>(
  action: () => Promise<ActionResult<T>>,
): Promise<ActionResult<T>> {
  try {
    return await action();
  } catch (error) {
    unstable_rethrow(error);
    return fail<T>(CONNECTION_ERROR);
  }
}

// Uso num componente de cliente:
//
//   async function handleSubmit() {
//     const result = await runAction(() => renameProduct({ id, title }));
//     if (!result.ok) return setError(result.error);
//     setSaved(result.data.slug);
//   }
