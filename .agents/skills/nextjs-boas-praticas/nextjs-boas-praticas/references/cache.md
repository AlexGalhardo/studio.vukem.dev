# Cache: o que pode ser compartilhado, quanto tempo fica velho e quem expira?

Leia quando: for criar uma leitura pública, uma ação que muda dado publicado, ou quando o site
mostrar dado antigo (passo 4 do fluxo).
Não é aqui: Suspense e dado de requisição (`references/dado-dinamico.md`).

## O mínimo

- Cache compartilhado é igual para todo mundo. Só entra o que qualquer visitante pode ver.
- Toda leitura em cache tem etiqueta, e os nomes das etiquetas moram num lugar só.
- Quem escreve expira. Escrita feita por fora do aplicativo não expira nada.
- Erro de leitura lança. Lista vazia em cache esconde tudo.

Conferido na documentação da versão 16.4.0 (`node_modules/next/dist/docs`), com
`cacheComponents: true`. Em outra versão, confira os nomes antes de copiar: esta API mudou a cada
versão maior. Sem Cache Components, o modelo é outro (`caching-without-cache-components.md`).

Conteúdo: 1. Ligar 2. O que entra e o que nunca entra 3. A leitura 4. Etiquetas 5. Quanto tempo
fica velho 6. Expirar 7. Escrita por fora do aplicativo 8. A primeira visita pode vir antiga
9. O build consulta o banco

## 1. Ligar

```ts
// next.config.ts
const nextConfig: NextConfig = { cacheComponents: true, partialPrefetching: true };
```

Declare `partialPrefetching` de forma explícita: sem ele a 16.4 avisa no log. Cache Components
exige o runtime Node.js.

## 2. O que entra e o que nunca entra

| Dado | Cache compartilhado? | Por quê |
| --- | --- | --- |
| Listagem e página de item publicado | sim | igual para todo visitante |
| Preço e textos de oferta lidos de outro serviço | sim, com prazo curto | muda pouco, e cada leitura custa uma chamada |
| Qualquer coisa que leia `cookies()` ou `headers()` | não | o escopo em cache não pode lê-los: a chamada falha, mesmo dentro de uma função auxiliar |
| O que depende de quem está logado (salvos, plano, sessão) | não | a resposta de uma pessoa seria servida a outra |
| Conteúdo pago | nunca | o escopo é compartilhado: o texto sairia para quem não pagou |
| Leituras do painel de admin | não | sempre com a sessão, sempre atrás da guarda |

O conteúdo pago é lido por uma função só, fora de qualquer `"use cache"`, chamada por um
componente só, depois de conferir o acesso. Prenda com teste: arquivo com a diretiva de cache não
importa o módulo de sessão nem `next/headers`.

Para usar um valor de cookie numa leitura em cache, leia o cookie fora e passe o valor como
argumento: ele entra na chave do cache.

## 3. A leitura

Molde: `assets/moldes/leitura-em-cache.ts`.

- A função é `async` e começa por `"use cache"`, depois `cacheTag(...)` e `cacheLife(...)`.
- Use um cliente do banco **sem cookies**, com o papel de visitante. Um cliente que lê cookie
  falha dentro do escopo em cache.
- **Erro lança.** Devolver `[]` em erro guarda uma lista vazia: a vitrine some até a entrada
  expirar.
- Registro que não existe devolve `null`, e a página chama `notFound()`.
- Os argumentos entram na chave: uma entrada por combinação. Não passe texto livre do visitante
  como argumento (`references/navegacao.md` §5).

## 4. Etiquetas

Nenhuma etiqueta é escrita como texto solto fora do objeto de nomes. Uma letra diferente entre
quem lê e quem expira não dá erro: só não expira.

| Etiqueta | Cobre | Quem leva |
| --- | --- | --- |
| `products` | tudo o que é listagem pública | toda leitura |
| `products:category:<categoria>` | a listagem de uma categoria | a leitura da categoria |
| `products:item:<slug>` | a página de um item | a leitura do item |

Limites da 16.4: etiqueta com até 256 caracteres, e maiúscula é diferente de minúscula.

## 5. Quanto tempo fica velho

Três prazos por perfil. `stale`: por quanto tempo o navegador reaproveita sem perguntar ao
servidor. `revalidate`: depois dele, a próxima visita recebe o antigo e o servidor refaz em
segundo plano. `expire`: depois dele sem visita, a próxima espera o dado novo.

| Perfil | `stale` | `revalidate` | `expire` |
| --- | --- | --- | --- |
| `seconds` | 30 s | 1 s | 1 min |
| `minutes` | 5 min | 1 min | 1 h |
| `hours` | 5 min | 1 h | 1 dia |
| `days` | 5 min | 1 dia | 1 semana |
| `max` | 5 min | 30 dias | 1 ano |

Sem `cacheLife`, vale o perfil `default`: 5 min, 15 min, nunca expira. Declare sempre. Escolha
pelo pior caso aceitável: "se ninguém expirar, quanto tempo o dono aceita ver o dado antigo?".

## 6. Expirar

Molde: `assets/moldes/expirar-cache.ts`.

| Função | Onde pode | Efeito | Use para |
| --- | --- | --- | --- |
| `updateTag(tag)` | só ação de servidor | expira na hora; a próxima leitura espera o dado novo | quem escreveu ver o que escreveu |
| `revalidateTag(tag, "max")` | ação e rota de servidor | marca como velho; serve o antigo enquanto refaz | webhook, script, outro sistema |
| `revalidateTag(tag, { expire: 0 })` | ação e rota de servidor | o antigo não é mais servido | rota que precisa do efeito imediato |
| `revalidatePath(caminho)` | ação e rota de servidor | invalida uma página, não o dado nas outras | raro; prefira etiqueta |
| `refresh()` | só ação de servidor | atualiza a tela de quem chamou | dado sem cache (um contador da pessoa) |

`revalidateTag` com um argumento só está obsoleto na 16.4 e não passa no verificador de tipos.
`updateTag` fora de ação de servidor lança erro.

Expire só quando a escrita muda o que o público vê. Faça a tabela do projeto: ação, quando
expira, quais etiquetas. Salvar rascunho não expira nada; publicar, despublicar e apagar expiram
o item, a categoria e o geral; editar expira só se o item está publicado.

## 7. Escrita por fora do aplicativo

O caso real: um script de importação gravou itens direto no banco, e nenhuma etiqueta foi
expirada. O site continuou com a lista antiga até o prazo do perfil passar (1 h) ou até um novo
deploy. No mesmo dia, um endereço do site já mostrava 8 itens e o outro ainda mostrava 4.

- **Por que o deploy resolve:** a chave de cada entrada inclui o id do build. Todo deploy começa
  com o cache vazio.
- **Por que esperar nem sempre resolve:** o prazo só conta quando chega visita, e a primeira
  visita depois do prazo ainda recebe o antigo.
- **O conserto:** uma rota de revalidação com segredo, chamada pelo script depois de gravar
  (segunda parte do molde). O mesmo vale para edição no painel do banco: ou passa pela rota, ou
  alguém refaz o deploy. No sistema de origem a saída usada foi refazer o deploy: a rota do
  molde passou no verificador de tipos e não rodou em produção.
- **Confira no endereço que o público usa.** Os dois domínios do mesmo site mostraram
  quantidades diferentes ao mesmo tempo: cada endereço servia a própria cópia. A causa exata é
  da hospedagem: a conferir na documentação dela.
- **Vários servidores:** por padrão a revalidação vale só na instância que recebeu a chamada. Em
  hospedagem própria com mais de uma instância, leia `how-revalidation-works.md` nos documentos
  do Next.

## 8. A primeira visita pode vir antiga

Medido com `next start` na 16.4: depois de `updateTag`, uma página pré-renderizada ainda foi
entregue uma vez na versão anterior e a visita seguinte já veio nova. A documentação diz que a
próxima requisição espera o dado novo; o motivo da diferença fica a conferir na documentação do
Next. Na prática: o teste ponta a ponta recarrega até o item aparecer, com prazo de 30 s, e não
exige a primeira resposta.

## 9. O build consulta o banco

Com Cache Components o `next build` executa as leituras em cache para pré-renderizar. O build
precisa das variáveis de ambiente e de um banco no ar, já com as tabelas. No CI, suba o banco
antes do build. Se o build ficar parado e acusar tempo esgotado depois de 50 s, uma função em
cache está esperando dado de requisição: `references/dado-dinamico.md` §6.

Em hospedagem sem servidor, o cache em memória pode não sobreviver entre requisições; o que foi
pré-renderizado no build continua valendo. Existe `"use cache: remote"` para um cache
compartilhado: não foi usado no sistema de origem, a conferir na documentação do Next.
