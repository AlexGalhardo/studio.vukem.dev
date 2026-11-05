# Dado dinâmico e Suspense: o que só existe na hora da requisição e onde ele pode ficar?

Leia quando: o build falhar pedindo Suspense, uma página ficar toda dinâmica por causa de um
cookie, ou for criar página com parâmetro, filtro ou sessão (passo 5 do fluxo).
Não é aqui: o que pode ser guardado em cache (`references/cache.md`); os arquivos de
carregamento, vazio e erro (`references/navegacao.md`).

## O mínimo

- `cookies()`, `headers()`, `params` e `searchParams` são assíncronos: sempre `await`.
- Quem lê um deles fica dentro de `<Suspense>` com fallback. O que está fora entra pronto na
  casca estática da página.
- A página não precisa ser `async`: ela passa as promessas para baixo, e só o componente que
  precisa do valor espera.
- Componente de cliente que lê o caminho ou a busca num layout também fica dentro de `<Suspense>`.

Conferido na documentação da versão 16.4.0, com `cacheComponents: true`. Em outra versão,
confira: antes da 15, `cookies()`, `headers()`, `params` e `searchParams` eram síncronos.

Conteúdo: 1. O que é dado de requisição 2. A página em três fronteiras 3. Parâmetro de rota
4. Componente de cliente no layout 5. Valor que muda a cada requisição 6. Sintomas

## 1. O que é dado de requisição

| Fonte | Como ler | Observação |
| --- | --- | --- |
| Cookies | `(await cookies()).get("nome")` | gravar cookie só em ação ou rota de servidor, nunca durante a renderização |
| Cabeçalhos | `(await headers()).get("nome")` | |
| Parâmetro de rota | `(await params).slug` | é dado de requisição quando o valor não está em `generateStaticParams` |
| Parâmetros de busca | `(await searchParams).q` | sempre dado de requisição |
| Sessão | pela função de sessão do projeto | ela lê cookies: tudo o que a chama é dinâmico |
| Hora atual, número aleatório | depois de `await connection()` | §5 |

Com Cache Components, o Next monta no build uma casca estática de cada rota e transmite o resto
quando fica pronto. Uma leitura de dado de requisição fora de `<Suspense>` não tem para onde ir:
o build falha, em vez de transformar a página inteira em dinâmica sem avisar.

## 2. A página em três fronteiras

Molde: `assets/moldes/pagina-com-suspense.tsx`.

```tsx
export default function Page({ params, searchParams }: PageProps<"/produtos/[categoria]">) {
  return (
    <Suspense fallback={<ListingSkeleton />}>
      <Listing params={params} searchParams={searchParams} />
    </Suspense>
  );
}
```

1. **A página** não espera nada. Recebe as promessas e repassa.
2. **A listagem** espera `params` e a leitura em cache. Para os valores de
   `generateStaticParams`, sai pronta no HTML: título, descrição e filtros aparecem na hora.
3. **Os resultados** são o único componente que espera `searchParams`. Só a grade fica atrás do
   esqueleto.

A consequência: trocar o filtro refaz a grade, não a página. Se a página inteira esperasse
`searchParams`, o título piscaria a cada clique.

O fallback tem a forma do conteúdo que vem (mesma altura, mesma grade), para a troca não
empurrar o resto da tela.

Informação de quem está logado no cabeçalho (o botão de conta) segue a mesma regra: um
componente pequeno, dentro do próprio `<Suspense>`, com o estado de visitante no fallback. O
cabeçalho inteiro não espera a sessão.

## 3. Parâmetro de rota

| A rota tem `generateStaticParams`? | O que acontece | O que fazer |
| --- | --- | --- |
| Sim, com pelo menos 1 valor | o build executa a rota com cada valor e confere o uso de dado de requisição | devolva a lista fechada; `params` pode ser lido direto |
| Sim, com lista vazia | o build falha | tire a função enquanto não houver item, ou devolva pelo menos 1 valor |
| Não | todo `params` é dado de requisição | leia `params` dentro de `<Suspense>` |

A conferência do build só cobre os caminhos de código executados com os valores de exemplo. Um
ramo que lê cookie só para certos valores passa no build e falha na primeira visita.

`dynamicParams` não existe com Cache Components. Para recusar valor fora da lista, confira o
parâmetro e chame `notFound()`: `references/navegacao.md` §5.

## 4. Componente de cliente no layout

`usePathname()` num menu que marca o item ativo suspende quando a rota tem parâmetro fora de
`generateStaticParams`: o caminho só existe na requisição. Fora de `<Suspense>`, o build falha
(`blocking-prerender-client-hook`), e a falha aparece em rotas que nem usam o menu de forma
diferente: basta estarem abaixo do layout.

```tsx
export function Nav() {
  return (
    <Suspense fallback={<NavLinks pathname={null} />}>
      <NavCurrent />
    </Suspense>
  );
}
function NavCurrent() {
  return <NavLinks pathname={usePathname()} />;
}
```

O fallback é a mesma navegação sem item ativo: ela entra na casca estática, e o destaque chega
depois. O mesmo invólucro vale para `useSearchParams()` em barra de filtro ou campo de busca,
com o estado padrão no fallback.

## 5. Valor que muda a cada requisição

Hora atual e número aleatório não leem a requisição, mas mudam a cada uma. Chame
`await connection()` antes: a pré-renderização para ali e o resto roda na requisição.

O caso real: conferir uma sessão compara a validade do token com a hora atual. O cliente de
banco com sessão passou a chamar `await connection()` logo depois de `cookies()`, e tudo o que
passa por ele ficou marcado como dado de requisição.

Dentro de uma função em cache, a hora lida fica guardada com o resultado. Um selo "novo"
calculado ali só muda quando a entrada é refeita.

## 6. Sintomas

| Sintoma | Causa | Conserto |
| --- | --- | --- |
| Build falha citando dado não guardado ou de requisição fora de Suspense | leitura de cookie, sessão, `params` ou `searchParams` sem fronteira | envolva o componente que lê, não a página inteira |
| Build falha citando `usePathname` ou `useSearchParams` | componente de cliente de layout sem fronteira | o invólucro do §4 |
| Build parado, erro de tempo esgotado depois de 50 s | função em cache recebeu uma promessa de dado de requisição | espere o valor fora e passe o valor, não a promessa |
| Erro imediato de `cookies()` dentro de `"use cache"` | leitura de cookie no escopo em cache, direta ou por função auxiliar | leia fora e passe como argumento |
| Funciona em desenvolvimento e quebra no build | o servidor de desenvolvimento renderiza sob demanda; a documentação diz que `useSearchParams` não suspende nele | rode o build antes de enviar: `references/verificacao.md` §4 |
| A página inteira mostra o esqueleto a cada clique de filtro | a página espera `searchParams` no topo | desça a espera para o componente de resultados |
