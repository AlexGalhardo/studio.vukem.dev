# Clientes e chaves: qual cliente do Supabase usar em cada lugar?

Leia quando: for criar ou revisar os módulos que falam com o Supabase, as variáveis de ambiente
ou o proxy; quando uma leitura devolver vazio "sem motivo" ou a chave secreta aparecer onde não
devia (passo 4 do fluxo).
Não é aqui: as ações de login (`references/login.md`); o link assinado (`references/storage.md`).

## O mínimo

- São cinco clientes, um por situação. Trocar um pelo outro é a origem de quase todo vazamento.
- A chave pública vai no navegador e vale pouco: quem protege o dado é o banco.
- A chave secreta ignora a RLS. É lida em um módulo só de servidor e usada em poucos pontos.
- Cliente de servidor é criado a cada requisição, nunca guardado no módulo.
- Leitura em cache compartilhado usa o cliente sem cookies, no papel de visitante.

Conteúdo: 1. Os cinco clientes 2. As duas chaves 3. Variáveis 4. O que nunca vai ao navegador
5. O proxy 6. Cache 7. O teste de fronteira

## 1. Os cinco clientes

Molde: `assets/moldes/clientes.ts`, com um bloco por arquivo de destino.

| Cliente | Feito com | Chave | Sessão | Use para |
| --- | --- | --- | --- | --- |
| Servidor | `createServerClient` (`@supabase/ssr`) e os cookies da requisição | pública | a da pessoa | página, ação e rota que dependem de quem pede |
| Navegador | `createBrowserClient` (`@supabase/ssr`) | pública | a da pessoa | componente de cliente que precisa falar direto com o Supabase |
| Público | `createClient` (`@supabase/supabase-js`), sem guardar sessão | pública | nenhuma: `anon` | leitura em cache compartilhado: vitrine, listagem |
| Admin | `createClient`, sem guardar sessão | secreta | nenhuma: `service_role` | webhook, link assinado, ferramenta de carga |
| Proxy | `createServerClient` sobre a requisição e a resposta | pública | a da pessoa | só renovar a sessão |

- **Um cliente de servidor novo a cada chamada.** Guardado no módulo, a sessão de uma pessoa
  serve a requisição de outra. O pacote também só entrega os cabeçalhos que impedem cache na
  primeira gravação de cookie de cada cliente.
- **No navegador há uma pessoa só:** a instância pode ficar guardada.
- **O cliente público e o admin desligam a sessão:** `persistSession: false` e
  `autoRefreshToken: false`. Não há cookie para ler nem token para renovar.
- **Se o login roda em ação de servidor, o navegador quase não precisa de cliente.** No projeto
  de origem ele existia e não era usado para dados.

## 2. As duas chaves

| | Chave pública | Chave secreta |
| --- | --- | --- |
| Nome antigo | `anon` | `service_role` |
| Papel no banco | `anon`, ou `authenticated` quando há sessão | `service_role`, que ignora a RLS |
| Onde pode estar | no navegador, no código público | só no servidor, lida em um módulo |
| Se vazar | nada além do que a RLS já permite | leitura e escrita de tudo: troque na hora |

O Supabase tem chaves no formato novo (publicável e secreta) e no antigo (`anon` e
`service_role`). Aceite as duas pelo nome da variável; o que muda no painel e quando o formato
antigo deixa de valer é a conferir na documentação do Supabase.

## 3. Variáveis de ambiente

| Variável | Quem lê | Vai ao navegador |
| --- | --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | módulo de variáveis públicas | sim |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | módulo de variáveis públicas | sim |
| `SUPABASE_SECRET_KEY` | um módulo só de servidor | nunca |

- **Dois módulos de ambiente.** O público é compartilhado com o navegador e nunca lê segredo. O
  de servidor abre com `import "server-only"`: o build falha se um componente de cliente o
  importar.
- **Variável em branco conta como ausente.** `CHAVE=` copiado do arquivo de exemplo não pode
  passar por valor.
- **O arquivo de exemplo vai ao git só com os nomes.** Valor de exemplo é `<SUA_CHAVE>`.
- **Não abra o arquivo de ambiente para conferir:** o valor entra na conversa. Confira pelos nomes.
- **Chave colada na conversa:** não repita, nem em parte. Diga que ficou exposta e peça a troca
  no painel. Trocar é passo do dono.

## 4. O que nunca vai ao navegador

| Não vai | Como garantir |
| --- | --- |
| A chave secreta | lida em um módulo com `server-only`; nenhuma variável com prefixo público e nome de segredo |
| O cliente admin | módulo com `server-only`; nunca passado como propriedade de componente |
| O dado restrito | lido por uma função só, depois da guarda; para quem não pode, ela devolve nulo |
| O link assinado em página que fica em cache | gerado em ação, por pedido |

O conferidor acusa dois desses casos:

```bash
python3 <skill>/scripts/conferir.py <projeto> --modulo lib/env.server.ts
# → "acusa: app/page.tsx:3 lê SUPABASE_SECRET_KEY do ambiente fora de lib/env.server.ts"
```

Repita `--modulo` para cada leitor legítimo, como a ferramenta de carga
(`references/producao.md` §5). Cada leitor a mais é um ponto a revisar.

## 5. O proxy: renovar a sessão

O bloco do proxy em `assets/moldes/clientes.ts` segue a ordem que o pacote pede:

1. Criar a resposta e o cliente sobre os cookies da requisição.
2. Em `setAll`: gravar os cookies na requisição, recriar a resposta, gravar nela, e copiar os
   cabeçalhos do segundo argumento. São os que impedem cache: resposta com cookie de sessão
   guardada por uma CDN entrega a sessão de uma pessoa a outra.
3. Chamar `getClaims()` logo depois de criar o cliente, sem nada no meio.
4. Devolver a resposta que recebeu os cookies.

- **Padrão de rotas:** deixe de fora arquivos estáticos e a rota do webhook, que chega sem sessão
  e não pode ter cookie mexido.
- **Não redirecione no proxy.** A proteção fica onde o dado é lido.
- No Next 16 o arquivo é `proxy.ts`; antes, `middleware.ts`. O desenho é o mesmo.

## 6. Leitura em cache e leitura por pessoa

| | Leitura compartilhada | Leitura por pessoa |
| --- | --- | --- |
| Exemplo | vitrine, listagem, página pública | o que é da pessoa, conteúdo pago, área de admin |
| Cliente | público, sem cookies | servidor, com a sessão |
| Cache | compartilhado, com prazo | nenhum |
| Quando o banco falha | lança erro | conforme o caso: "é admin?" nega |

- É a permissão de `anon` no banco que torna o cache seguro: ele só recebe o que é público.
- Leitura compartilhada que devolve lista vazia num erro guarda o vazio em cache e esconde tudo
  até o prazo. Lance.
- Escrita por fora do aplicativo (ferramenta de carga, painel) não expira o cache: diga ao dono
  em quanto tempo o dado aparece.

## 7. O teste de fronteira

Um teste que lê o código-fonte prende o que a revisão esquece. Três regras bastam:

1. Só o módulo de segredos lê a variável da chave secreta, e só o módulo admin o importa.
2. Arquivo com leitura em cache não importa o cliente de servidor, a sessão nem o cliente admin.
3. Toda ação de servidor começa pela guarda, menos as de login.

Rode junto dos testes do projeto. O conferidor desta skill cobre só a primeira metade da regra 1.

## O que evitar

- **Usar o cliente admin porque a consulta "voltava vazia".** Vazio com a sessão da pessoa é a
  RLS respondendo. Corrija a policy.
- **Ler a sessão com `getSession()` no servidor para decidir acesso.** O usuário vem do cookie
  sem conferência. Use `getClaims()`.
- **Dar prefixo público à chave secreta para "funcionar no cliente".** Ela vai inteira no pacote
  do navegador.

## Pronto quando

- [ ] Os cinco clientes existem, e os módulos de segredos, servidor, público e admin abrem com
      `server-only`.
- [ ] `scripts/conferir.py` com `--modulo` sai sem acusar leitura da chave secreta.
- [ ] O arquivo de exemplo de ambiente lista os nomes, sem nenhum valor.
