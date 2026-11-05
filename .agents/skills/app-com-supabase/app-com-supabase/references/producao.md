# Ambientes e produção: como levar o banco ao ar sem surpresa, e publicar conteúdo por pasta?

Leia quando: for arrumar os arquivos de ambiente, responder "posso aplicar em produção?", conferir
o que está no ar ou montar a ferramenta que publica conteúdo (passo 7 do fluxo).
Não é aqui: escrever a migration (`references/dados-e-migrations.md`); o painel do login (`references/login.md` §10).

## O mínimo

- O banco local é o padrão: o arquivo que as ferramentas carregam sozinhas aponta para ele.
- O projeto remoto é só leitura até o dono pedir. Aplicar migration, painel e chaves são dele.
- A ordem de ida é banco, dados, código. Código novo num banco antigo quebra o build ou a tela.
- Depois de aplicar, o histórico remoto tem as mesmas versões dos arquivos locais.
- A conferência final é como visitante, com a chave pública, no endereço que o dono usa.

Conteúdo: 1. Local 2. Do dono 3. A ordem 4. Histórico 5. Visitante 6. Conteúdo por pasta 7. Conferidor

## 1. Local como padrão

| Arquivo de ambiente | Aponta para | Quem carrega | No git |
| --- | --- | --- | --- |
| Local, o padrão das ferramentas | o Supabase local | as ferramentas, sozinhas | não |
| Remoto | o projeto remoto | só o comando que o cita pelo nome | não |
| Exemplo | nada: só os nomes das variáveis | ninguém | sim |

- `supabase start` sobe o banco local e `supabase status` mostra o endereço e as chaves locais.
  O dono copia para o arquivo local: não peça que cole na conversa.
- Dê ao arquivo remoto um nome que nenhuma ferramenta carrega sozinha: o descuido cai no local.
  A chave secreta de produção mora no painel da hospedagem.
- **Um comando rodou contra o remoto por engano:** pare, diga ao dono qual foi e o que pode ter
  escrito, confira o efeito só com leitura e corrija a arrumação antes de seguir.

## 2. O que é do dono

| Só o dono faz | O agente entrega |
| --- | --- |
| Criar o projeto no Supabase e guardar as chaves | a lista de variáveis, só com os nomes |
| Colar as chaves no painel da hospedagem; trocar chave exposta | o aviso de que ficou exposta, sem repetir o valor |
| Mexer no painel: SMTP, modelos de e-mail, tamanho do código, limites, endereço do site | a lista de `references/login.md` §10 |
| Autorizar cada migration no remoto, pela lista de arquivos | os arquivos, a ordem e o que cada um muda |
| Inserir a própria linha de admin, depois do primeiro login | o comando pronto, para ele rodar |

Antes da primeira escrita fora do local, pergunte que projetos a conta alcança, inclusive os
antigos, e diga o alvo pelo nome em todo comando contra o remoto.

## 3. A ordem: banco, dados, código

1. **Banco.** As migrations que faltam, na ordem dos arquivos. O que o código novo exige vai num
   passo anterior e compatível com o código antigo, que ignora o que não conhece.
2. **Dados.** O que o produto precisa para funcionar (vocabulário, a linha do admin, conteúdo).
3. **Código.** A implantação. Se o build lê o banco para montar páginas, ele falha num banco sem
   a estrutura: banco migrado e variáveis presentes antes do primeiro build.

```bash
supabase link --project-ref <REF_DO_PROJETO>   # o dono confirma o alvo
supabase migration list                        # local e remoto, lado a lado
supabase db push --dry-run                     # o que seria aplicado, sem aplicar
supabase db push                               # só com o "pode" do dono para essa lista
```

- Mostre ao dono a saída do `--dry-run` e espere a autorização para aquela lista. Um "pode"
  antigo não vale para migration nova.
- Não use `--include-seed`. Não rode `supabase db reset --linked`: recria o banco remoto.
- Aviso de migration (`raise warning`) pode não aparecer: confira o efeito com uma leitura.
- Escreva no arquivo de instruções do projeto o que está aplicado no remoto e desde quando.

## 4. Histórico de migrations alinhado

O `db push` decide o que falta pela versão gravada no histórico remoto. No projeto de origem,
migrations aplicadas por outra ferramenta ficaram registradas com a hora da aplicação, e não com
o carimbo do arquivo: o `db push` seguinte tentaria aplicar tudo de novo.

1. Depois de aplicar, rode `supabase migration list` e compare as duas colunas, versão a versão.
2. Versão remota sem arquivo local, e arquivo local "pendente" que já foi aplicado, é histórico
   desalinhado. Pare e avise o dono.
3. O conserto é `supabase migration repair --status reverted <versão errada>` e
   `--status applied <versão do arquivo>`. Ele escreve no remoto: é passo autorizado pelo dono, e
   o efeito exato é a conferir na documentação do Supabase antes de rodar. Aplicar sempre pelo
   mesmo caminho evita o problema.

## 5. Conferir como visitante, com a chave pública

Depois da implantação, sem sessão. O comando não imprime a chave.

```bash
node --env-file=<arquivo de ambiente do alvo> -e '
const { createClient } = require("@supabase/supabase-js");
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const db = createClient(url, process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, { auth: { persistSession: false } });
(async () => {
  console.log("alvo:", new URL(url).host);
  const vitrine = await db.from("items").select("id", { count: "exact", head: true });
  console.log("vitrine visível:", vitrine.count, vitrine.error?.code ?? "sem erro");
  const pago = await db.from("item_bodies").select("item_id").limit(1);
  console.log("texto pago:", pago.data?.length ?? 0, "linhas,", pago.error?.code ?? "sem erro");
})();'
# → alvo: <host>   vitrine visível: <o número de publicados>   texto pago: 0 linhas, 42501
```

- Conte o que deveria estar lá e confira o que não deve aparecer: rascunho, texto pago, tabela
  de serviço.
- Abra também o site, no endereço que o dono usa. Cada endereço guarda a própria cópia em
  cache, e a primeira visita depois da mudança pode vir antiga: recarregue antes de concluir.
- Rode com Node 22 ou mais novo: o `supabase-js` 2.117 recusou o Node 20 ao criar o cliente.
  No Supabase local o comando mostrou 12 publicados de 13 itens, e `42501` na tabela de serviço.

## 6. Conteúdo por pasta

Uma ferramenta de linha de comando que publica um item a partir de uma pasta, sem passar pela
tela de admin: `conteudo/<slug>/` com o manifesto (`item.json`: tipo, slug, título, resumo,
acesso e os caminhos dos arquivos), o texto pago e a mídia. Usa a chave secreta: é um segundo
leitor dela, declarado ao conferidor.

| Trava | Como | Sem ela |
| --- | --- | --- |
| Manifesto validado inteiro antes de escrever | uma lista de erros, com o campo de cada um | meio item gravado |
| Idempotente pela chave do item (o slug) | rodar de novo atualiza o mesmo item; arquivo igual não sobe de novo | item duplicado a cada execução |
| Simulação (`--dry-run`) | faz tudo menos escrever, pelo mesmo caminho de código, e imprime o plano | a primeira execução é em produção |
| Remoto só com opção explícita (`--allow-remote`) | endereço local passa; qualquer outro exige a opção. O atalho de comando do projeto não escolhe o ambiente: quem roda passa o arquivo pelo nome | carga de teste em produção |
| Endereço exato | com a opção, só o host de produção, escrito inteiro numa constante, em `https` | padrão largo aceita o projeto errado |
| Alvo impresso antes de agir; chave nunca impressa | `Alvo: <host> (PRODUÇÃO)` | ninguém vê para onde foi |
| Publicar é opção (`--publish`); nunca despublica | sem ela, fica em rascunho | item pela metade no ar |

```ts
const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost"]);
const PRODUCTION_HOST = "<host exato do projeto de produção>"; // constante: não vem do ambiente

export function resolveTarget(raw: string | undefined, allowRemote: boolean) {
  if (!raw || !URL.canParse(raw)) return { ok: false as const, error: "URL do Supabase ausente ou inválida." };
  const url = new URL(raw);
  if (LOCAL_HOSTS.has(url.hostname)) return { ok: true as const, host: url.host, local: true };
  if (!allowRemote) return { ok: false as const, error: `"${url.host}" não é local. Use --allow-remote.` };
  if (url.protocol !== "https:" || url.hostname !== PRODUCTION_HOST) {
    return { ok: false as const, error: `Recusado: "${url.host}". Só ${PRODUCTION_HOST} é aceito.` };
  }
  return { ok: true as const, host: url.host, local: false };
}
```

- Escrita por fora do aplicativo não expira o cache: diga em quanto tempo o item aparece.
- A pasta de conteúdo fica fora do git, menos o leia-me dela: é o que se vende.

## 7. O conferidor

```bash
python3 <skill>/scripts/conferir.py <projeto> --modulo lib/env.server.ts --modulo <ferramenta de carga>
# → linhas "acusa:", "aviso:", "ok:" e "não conferi:", um resumo e os limites
```

Saída 0: limpo. Saída 1: há "acusa:"; corrija numa migration nova, ou mova a leitura da chave.
Saída 2: uso errado. Saída 3: nada acusado, mas algo não foi conferido; passe `--modulo` ou
`--migrations`, ou confira à mão e diga isso no relato. Ele lê as migrations como texto, na
ordem dos arquivos, e não consulta o banco: tabela criada pelo painel não aparece, e é o teste
só de privilégios que a pega.

## Pronto quando

- [ ] O arquivo carregado por padrão aponta para o local, e só o exemplo está no git.
- [ ] O dono autorizou a lista de migrations que foi aplicada, e `migration list` bate.
- [ ] A conferência como visitante mostrou o que devia, e o arquivo de instruções diz o que
      está aplicado no remoto.
