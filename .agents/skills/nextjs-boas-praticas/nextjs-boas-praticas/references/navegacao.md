# Navegação: como a rota aguenta link quebrado, filtro, espera, vazio, erro e endereço inválido?

Leia quando: for criar rota, link, filtro ou paginação, ou quando uma página mostrar tela de erro
para um endereço que só não existe (passo 5 do fluxo).
Não é aqui: Suspense e leitura de parâmetros (`references/dado-dinamico.md`).

## O mínimo

- Link para rota que não existe tem de falhar no verificador de tipos, não em produção.
- Filtro, busca, ordem e página moram na URL, e cada opção é um link de verdade.
- Toda rota tem três estados além do normal: carregando, vazio e erro. E o site tem uma página
  de "não encontrada".
- Segmento dinâmico confere o valor contra uma lista ou contra o banco antes de qualquer outra
  coisa, e responde "não encontrada" para o resto.

Conferido na documentação da versão 16.4.0. Em outra versão, confira os nomes das props.

Conteúdo: 1. Links tipados 2. Filtros na URL 3. Carregando, vazio e erro 4. Página não
encontrada 5. Segmento dinâmico que aceita qualquer valor 6. A tela anterior continua montada

## 1. Links tipados

```ts
// next.config.ts
const nextConfig: NextConfig = { typedRoutes: true };
```

- `<Link href="/produtos">` com texto literal é conferido contra as rotas que existem. Renomear
  uma pasta de `app/` quebra o verificador de tipos em todo link antigo.
- Os tipos são gerados por `next dev`, `next build` ou `next typegen`. No CI, sem build, rode
  `next typegen && tsc --noEmit`: sem o primeiro comando, o segundo confere contra rotas velhas.
- `as Route` só quando o endereço é dinâmico de verdade (montado com query, vindo de um
  parâmetro `next` já conferido). Cada `as Route` é um link que o verificador deixou de olhar.
- `PageProps<"/rota/[param]">` tipa `params` e `searchParams` da página a partir do literal da
  rota, sem importar nada.
- Use `<Link>` para navegar e `<button>` para agir. Um `<div>` com clique não abre em nova aba,
  não recebe foco e não é lido como link.
- Redirecionar para um caminho vindo da URL (o "volte para onde estava" do login) aceita só
  caminho interno: uma barra no começo, não duas, sem barra invertida, com tamanho máximo. Sem
  isso, o login vira um redirecionador para qualquer site.

## 2. Filtros na URL

Estado de filtro em `useState` some ao recarregar, não vai junto no link compartilhado e quebra
o botão de voltar. Na URL (`?categoria=x&ordem=recentes&pagina=2`) os três funcionam, e o
servidor já entrega a lista filtrada.

- **Uma função pura lê os parâmetros** e devolve o filtro, com teste ao lado. Valor
  desconhecido cai no padrão. Endereço colado errado não pode virar tela de erro.
- **Outra função pura monta o endereço** a partir do filtro. Parâmetro com valor padrão fica de
  fora, para a mesma lista ter um endereço só.
- **Cada opção é um `<Link>`** com o endereço já montado. Sem `router.push` em `onClick`: o link
  funciona sem JavaScript e com clique do meio.
- **Só o componente de resultados espera `searchParams`** (`references/dado-dinamico.md` §2).
- **Retorno do clique:** `useLinkStatus()`, de `next/link`, dentro do link, mostra um indicador
  enquanto a navegação está em andamento.
- O chip ativo da barra de filtros lê a URL no cliente com `useSearchParams()`, dentro de
  `<Suspense>` com o estado padrão no fallback.
- `generateMetadata` não lê `searchParams`: a página filtrada tem o mesmo título.

## 3. Carregando, vazio e erro

| Estado | Arquivo | Regra |
| --- | --- | --- |
| Carregando | `loading.tsx` do segmento, ou `<Suspense fallback>` na página | esqueleto com a forma do conteúdo, `aria-busy="true"` e um texto para leitor de tela |
| Vazio | dentro da página | ícone, uma frase que diz o que falta e uma saída (um link) |
| Erro | `error.tsx` do segmento ou de um acima | frase sem detalhe técnico e botão de tentar de novo |

`loading.tsx` envolve a página e os filhos numa fronteira de Suspense. Ele não envolve o layout
do mesmo segmento.

Há dois vazios, e a saída de cada um é diferente: "ainda não há nada aqui" (leva para outra
seção) e "nenhum resultado para este filtro" (leva para a mesma lista sem o filtro).

```tsx
"use client"; // error.tsx: fronteira de erro é sempre componente de cliente

import { useEffect } from "react";

export default function RouteError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main>
      <h1>Algo deu errado</h1>
      <p>Não conseguimos carregar esta página. Tente de novo.</p>
      <button type="button" onClick={() => retry()}>
        Tentar de novo
      </button>
    </main>
  );
}
```

- `retry` busca os dados de novo e refaz a renderização. É estável desde a 16.3; na 16.2 era
  `unstable_retry`, e antes só existia `reset`, que limpa o erro sem buscar de novo.
- Erro vindo de componente de servidor chega com mensagem genérica e um `digest` para achar no
  log. Não mostre `error.message` na tela.
- `error.tsx` não pega erro do layout do mesmo segmento. Para o layout raiz existe
  `app/global-error.tsx`, que monta os próprios `<html>` e `<body>`.
- Um `error.tsx` dentro de um grupo com layout mostra só o conteúdo, e o cabeçalho continua
  na tela. O da raiz fica acima do layout do grupo e precisa do próprio caminho de volta.

## 4. Página não encontrada

- `notFound()`, de `next/navigation`, interrompe a renderização e mostra o `not-found.tsx` mais
  próximo. O `app/not-found.tsx` da raiz também atende todo endereço sem rota.
- Dentro de `try/catch`, `notFound()` e `redirect()` são engolidos pelo `catch`. Chame
  `unstable_rethrow(error)` na primeira linha do `catch` (API instável: confira na sua versão).
- **O código de resposta depende do momento.** Antes de a transmissão começar, a resposta é 404.
  Depois que um fallback de Suspense já foi enviado, a resposta fica 200 e o Next inclui
  `<meta name="robots" content="noindex">`. Se o seu caso exige o código 404 (auditoria,
  monitoramento), a conferência do parâmetro tem de acontecer antes de qualquer fronteira.
- Página "não encontrada" de dentro de um grupo com layout não repete o cabeçalho: o layout já
  monta.

## 5. Segmento dinâmico que aceita qualquer valor

Uma pasta `app/[categoria]/` na raiz atende todo endereço de um nível só: `/cursos`, mas também
`/qualquer-coisa`, `/wp-login.php` e todo erro de digitação. No sistema de origem a conferência
existe desde a primeira versão; a tabela é o que ela evita:

| O que chega | O que quebra |
| --- | --- |
| Texto que não é categoria | a consulta vai ao banco com um valor que a coluna não aceita, e a pessoa vê a tela de erro no lugar da "não encontrada" |
| Texto qualquer, repetido por robôs | cada valor diferente vira uma entrada nova no cache, porque o argumento entra na chave |
| Qualquer texto | o título da aba e o `<h1>` mostram o que o visitante digitou |
| Endereço de arquivo que não existe | cai na página dinâmica em vez de responder direto |

O conserto, na ordem (está no molde `assets/moldes/pagina-com-suspense.tsx`):

1. Uma lista fechada num módulo só, e uma função `parse` que devolve o valor ou `null`.
2. `generateStaticParams` devolve a lista. O `generateMetadata` usa a mesma `parse` e devolve um
   título neutro para valor inválido.
3. Na página, `parse` é a primeira coisa depois de `await params`; `null` chama `notFound()`
   antes de qualquer leitura.
4. A leitura em cache recebe o tipo fechado, não `string`. O verificador de tipos impede a
   chamada com texto cru.

Para segmento que vem do banco (`[slug]`) não há lista fechada: a leitura devolve `null` e a
página chama `notFound()`. Limite o tamanho e os caracteres do slug antes de consultar.

## 6. A tela anterior continua montada

Com Cache Components, ao navegar o Next esconde a tela anterior em vez de desmontar, e mantém o
estado dela. Duas consequências vistas no sistema de origem e uma descrita na documentação:

- Formulário de criação volta preenchido: zere o estado antes do `router.push`.
- Teste ponta a ponta acha texto da tela escondida: use localizador por papel e nome
  (`references/verificacao.md` §4).
- Menu aberto continua aberto ao voltar (documentação, `preserving-ui-state.md`): feche no
  efeito de limpeza.
