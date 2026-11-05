// Molde: ação de servidor que entrega um arquivo pago por link assinado de vida curta.
// Arquivo "use server" (a diretiva vai na primeira linha). O bucket é privado e a pessoa comum
// não tem policy de leitura nele: o link sai daqui, depois da guarda e da conferência de direito.
// Passou pelo verificador de tipos com @supabase/supabase-js 2.117 (storage-js 2.117).
// Não foi executado contra um bucket: confira no Supabase local antes de confiar.
import { createAdminSupabase, createServerSupabase } from "./clientes";
import { requireUser } from "./login-por-codigo";

const FILES_BUCKET = "files";
const LINK_TTL_SECONDS = 60; // dá para o navegador começar o download, e não para repassar o link

type DownloadResult = { ok: true; url: string } | { ok: false; error: string };

export async function requestDownload(input: { itemId: unknown }): Promise<DownloadResult> {
  // 1. Guarda: a primeira instrução, antes de validar ou ler qualquer coisa.
  await requireUser();
  const itemId = typeof input.itemId === "string" ? input.itemId : "";
  if (!/^[0-9a-f-]{36}$/i.test(itemId)) return { ok: false, error: "Item inválido." };

  // 2. Leitura com a sessão da pessoa: a RLS só entrega item publicado.
  const supabase = await createServerSupabase();
  const { data: item, error } = await supabase
    .from("items")
    .select("id, slug, access, file_path")
    .eq("id", itemId)
    .maybeSingle();
  if (error) return { ok: false, error: "Não deu para consultar agora. Tente de novo." };
  if (!item) return { ok: false, error: "Item não encontrado." };

  // 3. Direito: a mesma função que as policies usam. Erro nega.
  if (item.access !== "free") {
    const plan = await supabase.rpc("has_plan");
    if (plan.error || plan.data !== true) return { ok: false, error: "Disponível no plano pago." };
  }

  // 4. O caminho vem do banco, nunca do navegador, e tem de ser da pasta deste item: a chave
  //    secreta assinaria qualquer objeto do bucket.
  const path = item.file_path;
  if (!path || !path.startsWith(`items/${item.id}/`)) {
    return { ok: false, error: "Este item não tem arquivo para baixar." };
  }

  // 5. Só aqui entra a chave secreta, e só para assinar.
  const { data: signed, error: signError } = await createAdminSupabase()
    .storage.from(FILES_BUCKET)
    .createSignedUrl(path, LINK_TTL_SECONDS, { download: `${item.slug}.zip` });
  if (signError || !signed?.signedUrl) {
    console.error("Download: não consegui assinar o link", signError?.message);
    return { ok: false, error: "Não deu para preparar o download agora. Tente de novo." };
  }
  return { ok: true, url: signed.signedUrl };
}

// O que adaptar:
// - A regra de direito do passo 3 (aqui: item grátis, ou has_plan()). Admin, se baixa sem plano.
// - De onde vem o caminho: aqui, a coluna file_path do item; com versões, a da versão atual.
// - O nome do arquivo baixado e o prazo. O link vale para quem o tiver: não o grave em banco
//   nem em log, e não o ponha em página que fica em cache.
// - O teste da ação: sem sessão redireciona; sem plano devolve erro e não chama createSignedUrl;
//   caminho de outra pasta é recusado.
