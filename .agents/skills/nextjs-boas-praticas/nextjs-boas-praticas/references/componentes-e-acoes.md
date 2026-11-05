# Componentes e ações: onde mora cada coisa e como uma ação não vira um buraco?

Leia quando: for criar ou revisar um componente, uma leitura ou uma ação de servidor (passos 2 e
3 do fluxo).
Não é aqui: o que pode ir para o cache e como expirar (`references/cache.md`); login, sessão e
regras do banco (skill `app-com-supabase`).

## O mínimo

- Componente é de servidor até precisar de estado, evento ou API do navegador. Só então vira de
  cliente, e o mais fundo possível na árvore.
- Leitura mora em módulo só de servidor. Mutação mora em ação de servidor.
- Toda ação começa pela guarda, valida a entrada, confere o dono do recurso, escreve, expira o
  cache e devolve `{ ok, data }` ou `{ ok, error }`.
- No cliente, toda chamada de ação passa por uma função só.

Conteúdo: 1. Servidor por padrão 2. Onde mora cada coisa 3. A ordem dentro da ação 4. O retorno
5. Um ponto de chamada no cliente 6. O que não é trabalho de ação 7. Pacote pesado fora do
navegador

## 1. Servidor por padrão

Um arquivo com `"use client"` leva para o navegador tudo o que importa e tudo o que renderiza
direto. Marcar um layout inteiro como cliente por causa de um campo de busca manda o layout
inteiro como JavaScript.

- Ponha `"use client"` no arquivo do componente interativo (o campo, o botão com estado, o
  seletor), não no pai dele.
- O componente de cliente recebe dado por prop, vindo do servidor. Ele não busca: se buscasse, a
  consulta e a chave dela iriam junto.
- Provedor de contexto envolve só `{children}`, o mais fundo que der.
- Componente de servidor pode ser `async` e ler o banco direto. Componente de cliente não.

## 2. Onde mora cada coisa

| O quê | Arquivo | Marca | Por quê |
| --- | --- | --- | --- |
| Leitura | `features/<área>/queries.ts` | `import "server-only"` | importado por engano num componente de cliente, o build falha em vez de vazar a consulta |
| Mutação | `features/<área>/actions.ts` | `"use server"` no topo | toda função exportada vira endereço público; o arquivo exporta só ações |
| Regra pura | `features/<área>/<regra>.ts` | nenhuma | tela e ação dividem a mesma regra; o teste fica ao lado, em `<regra>.test.ts` |
| Schema de validação | `features/<área>/schemas.ts` | nenhuma | importado só por ações e leituras (§7) |
| Tela interativa | `features/<área>/<Componente>.tsx` | `"use client"` | folha da árvore |

Uma pasta por área do domínio (`features/products`, `features/billing`). A pasta `app/` fica só
com rotas: página, layout, carregamento, erro. Regra dentro de `page.tsx` não tem teste.

## 3. A ordem dentro da ação

O molde é `assets/moldes/acao-com-guarda.ts`. A documentação da 16.4 diz que uma função de
servidor é alcançável por POST direto, não só pela sua interface. Trate cada uma como rota
pública.

1. **Guarda, na primeira linha.** `await requireUser()` ou `await requireAdmin()`. A guarda
   devolve a pessoa ou interrompe (redireciona para o login, ou responde página não encontrada a
   quem não é admin, para a área ficar invisível). Proteger só o layout não protege a ação: ela
   é chamada sem passar pelo layout.
2. **Validação.** `schema.safeParse(input)`. O tipo do TypeScript descreve o que a sua tela
   manda, não o que chega.
3. **Dono do recurso.** O id veio do navegador. Leia a linha filtrando pelo id da pessoa logada.
   Sem isso, trocar o id na chamada altera o registro de outra pessoa.
4. **Escrita.** Com o cliente da sessão, para as regras do banco continuarem valendo como
   segunda barreira.
5. **Expiração do cache**, só se a mudança toca o que o público vê (`references/cache.md` §6).
6. **Retorno** no formato padrão.

As únicas ações sem guarda são as que criam e encerram a sessão (entrar, sair). Liste-as pelo
nome no teste de fronteira, para a exceção não crescer sozinha.

## 4. O retorno

`assets/moldes/resultado-de-acao.ts`: `{ ok: true, data }` ou `{ ok: false, error }`.

- `error` é uma frase pronta para a tela, na língua da interface. A tela não traduz código.
- Erro do banco vira uma frase genérica; o detalhe vai para `console.error` no servidor. Mensagem
  do banco na tela revela nome de tabela e de coluna.
- A ação não lança para o cliente. Lançar derruba a rota para o `error.tsx`.
- `data` leva só o que a tela usa: um id, um slug, um contador. Nunca a linha inteira, nunca
  conteúdo pago, nunca caminho de arquivo.

## 5. Um ponto de chamada no cliente

`runAction`, no mesmo molde. O caso real: a rede caiu durante um salvamento, a rejeição subiu
para o `error.tsx`, o formulário foi desmontado e o texto digitado se perdeu.

```tsx
const result = await runAction(() => renameProduct({ id, title }));
if (!result.ok) return setError(result.error);
```

`runAction` transforma a falha em `{ ok: false, error }` e mantém o formulário na tela. O
redirecionamento e a página não encontrada que a guarda lança continuam subindo, por
`unstable_rethrow`. Essa API é marcada como instável na 16.4: confira na sua versão.

Depois de criar um registro, zere o estado do formulário antes do `router.push`. Com Cache
Components o Next guarda a tela anterior escondida, com o estado dela: quem volta encontra o
formulário preenchido e cria o registro duas vezes.

## 6. O que não é trabalho de ação

- **Ler dado para montar a página.** Use componente de servidor. A documentação diz que as ações
  entram em fila, uma por vez: leitura por ação fica sequencial.
- **Receber chamada de outro sistema.** É rota de servidor (`references/apis-e-ambiente.md` §1).
- **Decidir acesso pela tela.** A tela esconde o botão; quem recusa é a ação.

## 7. Pacote pesado fora do navegador

O caso real: um componente de cliente público importava um módulo de regras, que importava o
validador de schema. O pacote inteiro foi para o bundle de todas as páginas públicas.

- Schemas ficam em arquivo próprio, importado só por ações e leituras.
- A regra que a tela e a ação dividem (limite de caracteres, formato de telefone) fica em módulo
  puro, sem o validador. A tela confere para dar retorno rápido; a ação confere de novo, com o
  schema, porque é ela que vale.
- Prenda com o teste de fronteira: `assets/moldes/fronteira.test.ts`, constante
  `CLIENT_FORBIDDEN_PACKAGES`.
