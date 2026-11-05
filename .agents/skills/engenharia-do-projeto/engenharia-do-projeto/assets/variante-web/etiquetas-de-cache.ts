// Molde da variante web. Generalizado de uso real, com nomes genéricos.
// Não foi executado nesta forma: rode antes de confiar.
//
// Módulo único de etiquetas de cache: nenhum texto de etiqueta é escrito fora daqui. Puro, com
// teste ao lado. As duas tabelas abaixo mudam na mesma mudança que o código.
//
// Quem lê (só leitura compartilhada leva etiqueta, declarada nas primeiras linhas da função):
//   | Função        | Etiquetas          | Usada em           |
//   | listarItens   | tipo, tudo         | vitrine, listagem  |
//   | lerItem       | item, tipo, tudo   | página do item     |
// Quem expira (toda escrita que muda o que é público):
//   | Ação          | Quando                    | Etiquetas         |
//   | publicarItem  | sempre                    | etiquetasDoItem   |
//   | editarItem    | só com o item publicado   | etiquetasDoItem   |
// Não expiram nada, porque só tocam rascunho: criarRascunho, editarRascunho.
// Fora do cache: dado restrito, o que depende de quem pede, lê cookie ou cabeçalho, área restrita.

export const ETIQUETAS = {
  tudo: "app",
  tipo: (tipo: string) => `app:tipo:${tipo}`,
  item: (slug: string) => `app:item:${slug}`,
} as const;

/** O conjunto que uma mudança num item afeta: o item, as listagens do tipo e o geral. */
export function etiquetasDoItem(slug: string, tipo: string): string[] {
  return [ETIQUETAS.item(slug), ETIQUETAS.tipo(tipo), ETIQUETAS.tudo];
}

// Adaptadores: as funções de cache do framework entram por parâmetro, com nome genérico.
export type Marcar = (etiqueta: string) => void; // "esta leitura usa esta etiqueta"
export type Expirar = (etiqueta: string) => void; // "o que usa esta etiqueta venceu"

export function marcarLeituraDoItem(marcar: Marcar, slug: string, tipo: string) {
  for (const etiqueta of etiquetasDoItem(slug, tipo)) marcar(etiqueta);
}

/** Chame nas ações de escrita. Mexer em rascunho não expira nada. */
export function expirarItem(expirar: Expirar, slug: string, tipo: string, publicado: boolean) {
  if (!publicado) return;
  for (const etiqueta of etiquetasDoItem(slug, tipo)) expirar(etiqueta);
}

// O que adaptar:
// - A hierarquia de etiquetas e as linhas das duas tabelas.
// - Os adaptadores: passe as funções de marcar e de expirar do framework do projeto.
// - "tipo" é o endereço público do tipo, não o valor guardado no banco: converta num lugar só.
