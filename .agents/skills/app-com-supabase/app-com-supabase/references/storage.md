# Storage: onde ficam os arquivos e quem consegue abrir cada um?

Leia quando: o produto tiver imagem, vídeo ou arquivo para baixar; ao criar bucket, policy de
arquivo, envio ou download (passo 6 do fluxo).
Não é aqui: as funções `is_admin()` e `has_plan()` (`references/permissoes.md` §5).

## O mínimo

- Dois buckets: um público para a vitrine, um privado para o que é pago.
- Em bucket público a policy só governa a listagem: quem sabe o endereço abre o arquivo.
- Arquivo pago sai por link assinado de 60 segundos, gerado no servidor depois da guarda.
- O caminho leva o id do item e vem do banco, nunca do navegador.
- Bucket e policy são criados por migration, com limite de tamanho e lista de tipos.

Conteúdo: 1. Os dois buckets 2. Caminho por item 3. A migration 4. Download pago 5. Envio direto
6. Apagar 7. Teste

## 1. Os dois buckets

| | Bucket público (`previews`) | Bucket privado (`files`) |
| --- | --- | --- |
| Guarda | capas e vídeos da vitrine | o arquivo que se vende |
| Quem abre | qualquer um com o endereço público | só quem recebe um link assinado |
| Policy de leitura | decide o que a API lista | só admin; a pessoa comum não tem nenhuma |
| Quem escreve | admin | admin |
| Endereço | fixo, serve em cache | assinado, vence |

Nada vai ao bucket público se não puder ser aberto por quem souber o endereço. Mídia de
rascunho fica acessível a quem adivinhar o caminho: por isso ele leva um `uuid` (§2).

## 2. Caminho por item

```text
previews:  items/<id do item>/<papel>-<uuid>.<ext>
files:     items/<id do item>/v<versão>/<nome>-<uuid>.<ext>
```

- **O id do item é a segunda pasta.** A policy e a ação conferem a pasta, e apagar o item vira
  apagar uma pasta.
- **Um `uuid` novo a cada envio.** Trocar a capa não esbarra em cache do endereço antigo, e o
  caminho não se adivinha.
- **Um módulo só monta e confere caminhos**, puro e com teste. Uma ação não registra caminho que
  ela mesma não poderia ter montado.

## 3. A migration

Rodou no Supabase local com os moldes de `assets/moldes/`, em transação desfeita, com cinco
afirmações de teste. Troque os nomes, os limites e os tipos.

```sql
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('previews', 'previews', true, 8388608, array['image/jpeg', 'image/webp', 'video/mp4']),
  ('files', 'files', false, 52428800, array['application/zip'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- previews: a listagem só mostra mídia de item publicado. O admin vê tudo e é o único que escreve.
create policy previews_published_select on storage.objects
  for select to anon, authenticated
  using (
    bucket_id = 'previews'
    and (
      (select public.is_admin())
      or exists (
        select 1 from public.items i
        where i.status = 'published'
          and i.id::text = (storage.foldername(storage.objects.name))[2]
      )
    )
  );
create policy previews_admin_insert on storage.objects
  for insert to authenticated
  with check (bucket_id = 'previews' and (select public.is_admin()));
create policy previews_admin_update on storage.objects
  for update to authenticated
  using (bucket_id = 'previews' and (select public.is_admin()))
  with check (bucket_id = 'previews' and (select public.is_admin()));
create policy previews_admin_delete on storage.objects
  for delete to authenticated
  using (bucket_id = 'previews' and (select public.is_admin()));

-- files: privado. Pela sessão, só o admin alcança. Quem tem direito baixa por link assinado.
create policy files_admin_all on storage.objects
  for all to authenticated
  using (bucket_id = 'files' and (select public.is_admin()))
  with check (bucket_id = 'files' and (select public.is_admin()));
```

- **A policy larga (`using (bucket_id = 'previews')`) deixa qualquer visitante listar o bucket
  inteiro**, com a mídia dos rascunhos. No projeto de origem ela existiu e foi trocada por esta.
- **O admin precisa ver tudo no bucket público:** o arquivo nasce antes da linha no banco, e o
  registro falha se ele não enxergar o que acabou de enviar.
- **O limite e os tipos ficam no bucket**, e o Storage recusa o que passar. Limite mais fino, por
  papel do arquivo, é do aplicativo.
- O esquema `storage` é do Supabase: insira o bucket, crie policy em `storage.objects` e não
  altere mais nada nele.

## 4. Download pago: link assinado

Molde: `assets/moldes/link-assinado.ts`. A ordem dentro da ação:

1. Guarda de usuário, antes de validar ou ler.
2. Ler o item com a sessão da pessoa: a RLS só entrega o publicado.
3. Conferir o direito com a mesma função que as policies usam. Erro nega.
4. Ler o caminho do banco e conferir que começa por `items/<id do item>/`.
5. Só então assinar, com o cliente admin: `createSignedUrl(caminho, 60, { download: nome })`.

- **A chave secreta assina qualquer objeto do bucket.** A conferência do passo 4 é o que impede
  uma coluna com o caminho errado de entregar o arquivo de outro item.
- **60 segundos** dão para o navegador começar o download e não para repassar o link. O link vale
  para quem o tiver: não vai para registro, banco nem página em cache.
- **Registre o download depois de assinar**, numa tabela só de inserção. É o que o dono consulta.

## 5. Envio direto ao bucket

Função de servidor tem limite de tamanho de corpo: arquivo grande não passa por ela.

| Passo | Quem | O que faz |
| --- | --- | --- |
| 1 | navegador | valida tipo e tamanho e mostra o erro cedo |
| 2 | ação de servidor | exige admin, valida de novo, confere que o item existe, monta o caminho com um `uuid` novo e devolve `createSignedUploadUrl(caminho)` |
| 3 | navegador | envia direto ao bucket, com o endereço e o token recebidos |
| 4 | ação de registro | exige admin, confere que o caminho é do item, lê `info(caminho)` e usa o tamanho e o tipo que o Storage informa; grava a linha; apaga o arquivo antigo |

- O endereço de envio assinado vale 2 horas (comentário do pacote `storage-js`, versão 2.117).
- Limites e mensagens moram num módulo puro, usado no navegador, no servidor e nos testes.

## 6. Apagar

- Apague pela API do Storage (`remove`), não por `delete` em `storage.objects`: no projeto de
  origem um gatilho do Storage recusava o `delete` direto com `42501`, antes da policy.
- Falha ao apagar arquivo é registrada e a ação segue: limpeza que falha não derruba a operação.
- Arquivo compartilhado entre versões só sai quando nenhuma outra o usa: conte antes.

## 7. Teste

No banco, com pgTAP, por persona: o visitante lista só a mídia de item publicado; visitante e
logado não veem nada no bucket privado; logado não escreve no público; o admin vê tudo. Insira as
linhas de `storage.objects` como quem abre a transação, e afirme depois de trocar de papel.

O teste de `delete` em `storage.objects` precisa ligar, só na transação, a configuração que o
gatilho do Storage consulta. No projeto de origem foi
`select set_config('storage.allow_delete_query', 'true', true);`: confira o nome na sua versão.

## O que evitar

- **Guardar o arquivo pago no bucket público "com nome difícil".** Endereço público não passa
  por regra nenhuma, e vaza no primeiro link compartilhado.
- **Receber o caminho do navegador na ação de download.** A pessoa pede o arquivo de outro item.
- **Gerar o link assinado ao montar a página.** Vai para o cache junto com a página.
- **Confiar no tipo que o navegador declara.** Vale o que o Storage informa depois do envio.

## Pronto quando

- [ ] Os dois buckets nascem por migration, com limite e tipos.
- [ ] O visitante não lista mídia de rascunho, e ninguém além do admin lê o bucket privado.
- [ ] O teste da ação de download cobre: sem sessão, sem direito e caminho de outra pasta.
