# APIs e ambiente: rota ou ação, o que o proxy faz e onde ficam os segredos?

Leia quando: for criar um endpoint, receber um webhook, mexer no `proxy.ts` (o antigo
`middleware.ts`) ou em variável de ambiente (passo 6 do fluxo).
Não é aqui: a ordem dentro de uma ação (`references/componentes-e-acoes.md` §3); o webhook de
pagamento completo (skill `assinatura-com-stripe`); sessão e chaves do banco (skill
`app-com-supabase`).

## O mínimo

- A sua tela chama ação de servidor. Outro sistema chama rota de servidor.
- A rota de webhook lê o corpo cru e repassa. A regra mora num módulo testável.
- O proxy só renova a sessão. Proteção fica em cada página e em cada ação.
- Variável pública num módulo, segredo em outro, só de servidor. Segredo é lido em um módulo e
  consumido em um lugar.

Conferido na documentação da versão 16.4.0. Em outra versão, confira: o arquivo `proxy.ts` se
chamava `middleware.ts` antes da 16.

Conteúdo: 1. Rota ou ação 2. Webhook 3. Rota de revalidação 4. Proxy 5. Variáveis de ambiente
6. Configuração do Next que entra nesta conta

## 1. Rota ou ação

| Quem chama | Use | Por quê |
| --- | --- | --- |
| A sua própria tela, para mudar dado | ação de servidor | tipo de ponta a ponta, sem montar requisição, e a tela atualiza na mesma ida ao servidor |
| A sua própria tela, para ler dado | componente de servidor | ação entra em fila, uma por vez; leitura por ação fica lenta |
| Outro sistema (webhook, script, aplicativo de celular) | rota de servidor | ele precisa de um endereço fixo, de método HTTP e de código de resposta |
| O navegador, para baixar arquivo ou receber algo que não é tela | rota de servidor, ou ação que devolve um endereço assinado de curta duração | resposta com outro tipo de conteúdo |

Regras da rota (`app/.../route.ts`):

- Não existe `route.ts` e `page.tsx` na mesma pasta.
- Rota não é guardada em cache por padrão. `"use cache"` não vai direto no corpo da rota: fica
  numa função auxiliar.
- Rota não passa pela guarda de página nenhuma. Ela confere quem chama por conta própria:
  assinatura, segredo em cabeçalho ou sessão.
- Valide o corpo como numa ação. O chamador é desconhecido.
- Deixe o arquivo de rota só com os métodos HTTP. A regra vai para um módulo do domínio, que
  recebe texto e devolve `{ status, body }`: o teste chama a função, sem servidor.

## 2. Webhook

Molde: `assets/moldes/rota-de-webhook.ts`.

```ts
export async function POST(request: Request) {
  const rawBody = await request.text();
  const result = await handleWebhook(rawBody, request.headers.get("x-signature"), deps);
  return Response.json(result.body, { status: result.status });
}
```

- **Corpo cru.** A assinatura é calculada sobre o texto exato que o serviço enviou. Um
  `request.json()` antes da conferência perde esse texto, e toda entrega passa a responder 400.
- **Ordem no manipulador:** conferir a assinatura, interpretar o JSON, filtrar o tipo, gravar.
- **Códigos:** assinatura errada, 400. Tipo que não interessa, 200 (com erro, o serviço reenvia
  sem parar). Falha ao gravar, 500, para o serviço reenviar.
- **O mesmo evento chega mais de uma vez.** Quem grava precisa aguentar a repetição. Prazo e
  número de reenvios dependem do serviço: a conferir na documentação dele.
- **Fora do proxy.** A chamada vem sem sessão; o proxy não deve tocar em cookies ali.
- O molde confere com HMAC-SHA256 em hexadecimal, comparado em tempo constante. O formato real
  (cabeçalho, prefixo, carimbo de tempo) é de cada serviço. Havendo pacote oficial, use a função
  de conferência dele.

## 3. Rota de revalidação

Para a escrita feita por fora do aplicativo (`references/cache.md` §7). Segunda parte de
`assets/moldes/expirar-cache.ts`.

- Segredo próprio, em cabeçalho, comparado em tempo constante. Sem segredo configurado, a rota
  responde 503 em vez de aceitar qualquer chamada.
- O corpo diz o que mudou (`slug` e `category`). As etiquetas são calculadas pela mesma função
  que as ações usam. A rota não aceita nome de etiqueta vindo de fora.
- `revalidateTag(tag, "max")`. `updateTag` não funciona em rota.
- O script chama a rota depois de gravar e trata resposta diferente de 200 como falha da
  importação. Assim o dado antigo não fica no ar sem ninguém saber.

## 4. Proxy

```ts
// proxy.ts, na raiz
export async function proxy(request: NextRequest) {
  return updateSession(request); // do seu provedor de login: só renova o cookie da sessão
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico|api/webhooks|.*\\.(?:svg|png|jpg|webp|woff2?)$).*)"],
};
```

- **Só renova a sessão.** Componente de servidor não grava cookie durante a renderização; o
  proxy é o lugar que consegue renovar o cookie antes de a página rodar.
- **Não é a guarda.** A documentação da 16.4 avisa: uma ação de servidor é um POST para a rota
  em que é usada, então um matcher que exclui um caminho também deixa de fora as ações dele.
  Mudar o matcher tira a proteção sem nenhum erro. A guarda fica dentro de cada ação e no
  começo de cada página protegida.
- **Sem matcher, roda em toda requisição**, incluindo arquivo estático e imagem. Exclua os
  estáticos e os webhooks. Os valores do matcher precisam ser constantes.
- Roda no runtime Node.js; a opção `runtime` não existe no arquivo.
- Vindo do `middleware.ts`: o arquivo e a função mudam de nome. O codemod oficial
  `middleware-to-proxy` está descrito em `proxy.md`, nos documentos do Next.

## 5. Variáveis de ambiente

Dois módulos, e nenhum outro arquivo lê `process.env`:

| Módulo | Lê | Marca | Quem importa |
| --- | --- | --- | --- |
| `lib/env.ts` | só `NEXT_PUBLIC_*` | nenhuma | servidor e navegador |
| `lib/env.server.ts` | segredos | `import "server-only"` | um módulo por segredo (o cliente do banco com a chave de serviço, o cliente do serviço de pagamento) |

- **Variável pública é escrita por extenso.** O Next troca `process.env.NEXT_PUBLIC_X` pelo
  valor durante o build. Acesso por nome montado (`process.env[nome]`) não é trocado e chega
  sem valor ao navegador.
- **Pública é pública.** O valor fica no JavaScript entregue a todo visitante. Chave de serviço,
  segredo de webhook e token nunca levam o prefixo.
- **Mudou a pública, refaça o build.** O valor foi fixado no build.
- **Segredo é lido sob demanda**, dentro de uma função (`serverEnv()`), com o resultado
  guardado. Lido e validado no topo do módulo, uma variável ausente derruba toda rota que
  importa o arquivo, mesmo as que não usam aquele segredo.
- **Valide com schema** e falhe com uma mensagem que lista os nomes que faltam, nunca os
  valores. `CHAVE=` em branco conta como ausente.
- **`.env.example` lista os nomes, sem valor**, e entra no git. Os arquivos `.env*` de verdade
  ficam fora. Chave de produção mora no painel da hospedagem, colada pelo dono.
- Na hospedagem, as variáveis precisam existir também no ambiente de prévia, senão o build de
  cada pull request falha.

## 6. Configuração do Next que entra nesta conta

| Opção | Valor | Motivo |
| --- | --- | --- |
| `cacheComponents` | `true` | liga `"use cache"` e a casca estática |
| `partialPrefetching` | `true` | pedido junto com a anterior na 16.4 |
| `typedRoutes` | `true` | link para rota inexistente falha nos tipos |
| `poweredByHeader` | `false` | não anuncia o framework em cada resposta |
| `images.remotePatterns` | só a pasta pública do seu armazenamento, nunca um curinga de domínio | com curinga, o otimizador de imagem atende arquivo de terceiros na sua conta |
| `allowedDevOrigins` | o endereço que o teste usa, se não for `localhost` | sem isso o servidor de desenvolvimento recusa os próprios recursos e a página não hidrata |
