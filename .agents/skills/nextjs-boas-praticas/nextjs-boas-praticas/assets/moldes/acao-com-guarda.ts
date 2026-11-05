// Molde: ação de servidor na ordem que não deixa buraco.
// Destino sugerido: features/<área>/actions.ts. Num arquivo com "use server" no topo, toda
// função exportada roda no servidor e é um endereço que qualquer pessoa pode chamar com um POST
// direto, sem passar pela sua tela. Por isso a guarda é a PRIMEIRA linha de cada função, e o
// arquivo não exporta mais nada.

"use server";

import { z } from "zod";
import { expireProduct } from "./expirar-cache";
import { fail, ok, SAVE_ERROR, type ActionResult } from "./resultado-de-acao";
// Troque pelos módulos do seu projeto: a guarda de sessão e o acesso ao banco.
import { requireUser } from "@/features/auth/session";
import { db } from "@/lib/db";

// O schema fica no servidor: o validador é um pacote grande e não entra no bundle público
const renameSchema = z.object({
  id: z.uuid("Produto inválido."),
  title: z.string().trim().min(1, "Dê um título ao produto.").max(120, "Título longo demais."),
});

type RenameProductInput = z.input<typeof renameSchema>;

export async function renameProduct(
  input: RenameProductInput,
): Promise<ActionResult<{ slug: string }>> {
  // 1. Guarda: devolve a pessoa logada ou interrompe (redirect para o login)
  const user = await requireUser();

  // 2. Validação: o tipo do TypeScript não vale nada aqui, o corpo vem do navegador
  const parsed = renameSchema.safeParse(input);
  if (!parsed.success) return fail(parsed.error.issues[0]?.message ?? "Dados inválidos.");

  // 3. Autorização do recurso: o id veio do navegador. Sem conferir o dono, uma pessoa
  //    renomeia o produto de outra só trocando o id
  const product = await db.products.findOwned(parsed.data.id, user.id);
  if (!product) return fail("Produto não encontrado.");

  // 4. Escrita. O detalhe do erro vai para o log; para a tela, uma frase genérica
  try {
    await db.products.rename(product.id, parsed.data.title);
  } catch (error) {
    console.error("renameProduct: falha ao gravar", error);
    return fail(SAVE_ERROR);
  }

  // 5. Expira o cache, e só se a mudança aparece para o público (rascunho não expira nada)
  if (product.published) expireProduct(product.slug, product.category);

  // 6. Devolve só o que a tela usa: nunca a linha inteira, nunca conteúdo pago
  return ok({ slug: product.slug });
}
