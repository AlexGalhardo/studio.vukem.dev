// Molde da variante web. Generalizado de uso real, com nomes genéricos.
// Não foi executado nesta forma: rode antes de confiar.
// Para ferramenta que grava por fora do aplicativo: todo o cuidado com o alvo mora aqui.

const SERVIDORES_LOCAIS = new Set(["127.0.0.1", "localhost"]);
const SERVIDOR_DE_PRODUCAO = "<servidor exato de produção>"; // constante: não vem do ambiente

export type Alvo = { servidor: string; local: boolean };
export type ResultadoDoAlvo = { ok: true; alvo: Alvo } | { ok: false; erro: string };

/** Três degraus: local passa; remoto exige a opção; com a opção, só o servidor exato, em https. */
export function resolverAlvo(texto: string | undefined, permitirRemoto: boolean): ResultadoDoAlvo {
  if (!texto) return { ok: false, erro: "A URL do banco não está no ambiente." };
  let url: URL;
  try {
    url = new URL(texto);
  } catch {
    return { ok: false, erro: "A URL do banco não é válida." };
  }
  const local = SERVIDORES_LOCAIS.has(url.hostname);
  if (local) return { ok: true, alvo: { servidor: url.host, local } };
  if (!permitirRemoto) {
    return { ok: false, erro: `O alvo "${url.host}" não é local. Use --permitir-remoto.` };
  }
  if (url.protocol !== "https:" || url.hostname !== SERVIDOR_DE_PRODUCAO) {
    return { ok: false, erro: `Recusado: "${url.host}". Só ${SERVIDOR_DE_PRODUCAO} é aceito.` };
  }
  return { ok: true, alvo: { servidor: url.host, local } };
}

/** Imprima antes de agir. A chave não entra em linha nenhuma. */
export function rotuloDoAlvo(alvo: Alvo): string {
  return `Alvo: ${alvo.servidor} (${alvo.local ? "local" : "PRODUÇÃO"})`;
}

export type Contexto = { simular: boolean; dizer: (linha: string) => void };

/** Toda escrita passa por aqui. Em simulação, anuncia e devolve o valor combinado, sem executar. */
export async function escrever<T>(
  ctx: Contexto, oQue: string, acao: () => PromiseLike<T>, seSimulado: T,
): Promise<T> {
  if (ctx.simular) {
    ctx.dizer(`faria  ${oQue}`);
    return seSimulado;
  }
  const valor = await acao();
  ctx.dizer(`ok     ${oQue}`);
  return valor;
}
// O que já está igual não chama escrever(): ctx.dizer(`=      ${oQue} já está igual`).

// O que adaptar:
// - SERVIDOR_DE_PRODUCAO: o nome inteiro, sem curinga. Padrão largo deixa passar o projeto errado.
// - Os nomes das opções (--permitir-remoto, --simular) e da variável que traz a URL.
// - Teste resolverAlvo(): local passa com e sem a opção; remoto sem a opção é recusado, mesmo o de
//   produção; com a opção, só o servidor exato em https; URL ausente ou inválida é recusada.
// - O resumo final repete o alvo, diz "nada foi escrito" na simulação e, no remoto, avisa do cache.
