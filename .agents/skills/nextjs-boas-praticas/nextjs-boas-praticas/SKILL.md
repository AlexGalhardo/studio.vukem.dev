---
name: nextjs-boas-praticas
description: Monta e revisa aplicativo Next.js com App Router sem vazar dado, sem ação desprotegida e sem página velha no ar. Entrega componentes de servidor por padrão, ações de servidor com guarda, validação e retorno padronizado, cache público com etiquetas e expiração, Suspense para o que depende da requisição, links tipados, filtros na URL e os estados de carregamento, vazio e erro, rota de webhook, proxy e variáveis de ambiente, com moldes em TypeScript, teste de fronteira e um conferidor que só lê o projeto. Use sempre que o usuário for criar página, ação, rota ou cache em Next.js, ou disser "revisa meu projeto Next", "o site mostra dado antigo", "publiquei e não apareceu", "o build quebrou pedindo Suspense", "onde ponho o use client", "server action ou rota de API", "como invalido o cache" ou "migrar o middleware para proxy", mesmo sem dizer boas práticas. Não use para Pages Router, React sem Next, estilo e design, banco e login (app-com-supabase) nem pagamento (assinatura-com-stripe).
---

# Next.js: boas práticas

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do projeto do dono.

- **Servidor por padrão.** Um componente só vira de cliente quando precisa de estado, evento ou
  API do navegador, e o mais fundo possível na árvore.
- **Toda ação é um endereço público.** Ela começa pela guarda e desconfia de tudo o que recebe.
- **Cache compartilhado é igual para todos.** Nada de cookie, nada de sessão, nada de conteúdo
  pago. Quem escreve expira, pelas mesmas etiquetas que a leitura usou.
- **Dado de requisição fica atrás de Suspense.** O resto da página sai pronto do servidor.
- **Regra que importa vira teste.** O teste lê o código-fonte e roda em segundos.

Funciona porque cada regra tira uma decisão da memória de quem programa e põe num lugar que
falha sozinho: o build, o verificador de tipos ou um teste. O teste antes de agir: sei onde este
código roda, quem pode chamá-lo e quem vai ver a resposta?

Saiu de um sistema em produção com Next.js 16.4, App Router e `cacheComponents: true`. Cada
fato sobre a API foi conferido na documentação instalada daquela versão
(`node_modules/next/dist/docs`). **Confira na versão do projeto antes de copiar:** cache, proxy e
as props do `error.tsx` mudaram entre as versões 14, 15 e 16. O que está marcado "a conferir"
não foi verificado. Os moldes de `assets/moldes/` passaram no verificador de tipos contra o Next
16.4, com a guarda e o banco trocados por substitutos, e o teste de fronteira rodou em Vitest.
Nenhum foi executado num build nem num servidor: adapte e rode os testes do projeto.

## Preparar

1. Leia a versão do Next em `package.json` e o arquivo de configuração. Sem `cacheComponents`,
   os passos 2, 3, 6 e 7 valem iguais; o cache e a exigência de Suspense seguem outro modelo:
   leia `caching-without-cache-components.md` nos documentos do Next antes dos passos 4 e 5.
2. Abra o documento da versão instalada antes de usar uma API de cache, de rota ou de erro:
   `<projeto>/node_modules/next/dist/docs/01-app/03-api-reference/`.
3. Rode o conferidor, que só lê:

   ```bash
   python3 <skill>/scripts/conferir.py <projeto> --segredos <módulo que lê os segredos>
   # → "acusa:", "aviso:", "ok:", "não conferi:". Saída 0 limpo, 1 acusou, 2 uso, 3 incompleto
   ```

Requisitos: Python 3.8 ou mais novo, só para o conferidor (rodou em macOS com Python 3.14). Sem
Python, faça à mão as cinco conferências do cabeçalho do script. Em projeto que já existe, nada é
alterado: trate como revisão e comece pela tabela abaixo.

## Onde o projeto está

| Situação | Sinal | Comece por | Leia |
| --- | --- | --- | --- |
| Projeto novo | ainda não há `features/` nem ações | passo 1 | `references/componentes-e-acoes.md` |
| Tudo é cliente | `"use client"` em layout ou página; busca de dado em efeito | passo 2 | `references/componentes-e-acoes.md` §1 |
| Ação sem guarda | o conferidor acusa; a proteção está só no layout ou no proxy | passo 3 | `references/componentes-e-acoes.md` §3 |
| Dado antigo no ar | "publiquei e não apareceu"; só o deploy atualiza | passo 4 | `references/cache.md` §6 e §7 |
| Build pede Suspense | erro citando dado de requisição, `usePathname` ou `useSearchParams` | passo 5 | `references/dado-dinamico.md` §6 |
| Rota frágil | tela de erro para endereço que não existe; filtro que some ao recarregar | passo 5 | `references/navegacao.md` |
| Endpoint novo | webhook, script que precisa avisar o site, variável nova | passo 6 | `references/apis-e-ambiente.md` |
| Vai enviar | "posso subir?" | passo 7 | `references/verificacao.md` §6 |

## Fluxo

### 1. Leia a versão e combine o que é público

Liste com o dono: o que qualquer visitante vê, o que é só de quem está logado e o que é pago.
Essa lista decide o que entra no cache e o que nunca entra.
**Confira:** cada tipo de dado está numa das três colunas.
**Pronto quando:** a lista está escrita no documento do projeto, com a versão do Next ao lado.

### 2. Ponha cada coisa no lugar

Leitura em `features/<área>/queries.ts` com `import "server-only"`; mutação em
`features/<área>/actions.ts`; regra pura em módulo próprio com teste ao lado; `"use client"` só
no componente interativo.
**Confira:** `conferir.py` não acusa componente de cliente importando módulo só de servidor.
**Pronto quando:** nenhuma página, layout ou seção inteira é de cliente.

### 3. Escreva as ações

Parta de `assets/moldes/resultado-de-acao.ts` e `assets/moldes/acao-com-guarda.ts`. A ordem:
guarda, validação, dono do recurso, escrita, expiração, retorno. No cliente, toda chamada passa
por `runAction`.
**Confira:** o teste da ação cobre visitante, entrada inválida e recurso de outra pessoa.
**Pronto quando:** a ação chamada direto, sem a tela, recusa os três casos.

### 4. Ligue o cache público

Parta de `assets/moldes/leitura-em-cache.ts` e `assets/moldes/expirar-cache.ts`. Escreva a
tabela do projeto: cada ação, quando expira, quais etiquetas. Se existe escrita por fora do
aplicativo, crie a rota de revalidação: `references/cache.md` §7.
**Confira:** nenhum arquivo com `"use cache"` importa sessão, cookies ou a leitura do conteúdo
pago.
**Pronto quando:** publicar pelo painel faz o item aparecer na página pública sem novo deploy.

### 5. Monte as rotas

Parta de `assets/moldes/pagina-com-suspense.tsx`. Em cada rota: parâmetro conferido antes de
ler dado, `<Suspense>` em volta de quem lê a requisição, filtro na URL, e os estados de
carregamento, vazio e erro.
**Confira:** `next typegen && tsc --noEmit` passa, e um link para rota inexistente o faz falhar.
**Pronto quando:** um endereço inventado mostra "não encontrada", e não a tela de erro.

### 6. Feche as APIs e o ambiente

Webhook a partir de `assets/moldes/rota-de-webhook.ts`; proxy só renovando a sessão; variáveis
públicas e segredos em dois módulos: `references/apis-e-ambiente.md`.
**Confira:** `conferir.py --segredos <módulo>` não acusa segredo fora do módulo.
**Pronto quando:** o arquivo de exemplo de ambiente lista os nomes, sem nenhum valor.

### 7. Prenda as regras e rode contra o build

Copie `assets/moldes/fronteira.test.ts`, ajuste as constantes e ligue aos testes do projeto.
Rode os testes ponta a ponta contra `next start`: `references/verificacao.md` §4.
**Confira:** o teste de fronteira falha quando você quebra uma regra de propósito.
**Pronto quando:** a lista de `references/verificacao.md` §6 está cumprida.

## Regras inegociáveis

1. **Toda ação de servidor começa pela guarda.** Ela é alcançável por POST direto: com a
   proteção só no layout ou no proxy, qualquer pessoa a executa sem abrir a tela.
2. **Entrada validada no servidor, e o dono do recurso conferido.** Se não, trocar um id na
   chamada altera o registro de outra pessoa.
3. **Nada que leia cookie, sessão ou conteúdo pago entra em `"use cache"`.** Se entrar, a
   resposta de uma pessoa é servida a todas.
4. **Etiqueta de cache só nasce num módulo.** Com o nome escrito à mão em dois lugares, uma
   letra diferente não dá erro: só não expira.
5. **Leitura em cache lança em erro.** Se devolver lista vazia, a vitrine some até a entrada
   expirar.
6. **Quem lê a requisição fica dentro de `<Suspense>` com fallback.** Fora, o build falha; e, se
   a página inteira esperar, a tela toda pisca a cada filtro.
7. **Segmento dinâmico confere o valor antes de ler dado.** Se não, endereço inventado vira
   tela de erro e entrada nova no cache.
8. **Segredo é lido num módulo só de servidor; variável pública nunca guarda segredo.** O valor
   de `NEXT_PUBLIC_*` vai dentro do JavaScript de todo visitante.
9. **O proxy não é a guarda.** Um matcher que exclui um caminho exclui também as ações dele, sem
   nenhum erro.

## Pare e pergunte ao dono

- **Só o dono faz:** colar segredo no painel da hospedagem; refazer o deploy de produção;
  apontar domínio. Não peça o valor de chave na conversa.
- **Pergunte antes:** o que é público, o que é de quem está logado e o que é pago; quanto tempo
  um dado público pode ficar velho; se a resposta 404 de verdade é exigida; ligar
  `cacheComponents` num projeto que não usa; rodar o build numa máquina com pouca memória.

## Armadilhas já vistas

- **"Publiquei e o site não mudou", ou um endereço mostra o novo e o outro, o antigo.** A
  escrita foi por fora do aplicativo (script, painel do banco) e nada expirou; cada domínio
  serviu a própria cópia. Confira no endereço que o público usa: `references/cache.md` §7.
- **Acabei de salvar e a página ainda veio antiga, uma vez.** Página pré-renderizada, primeira
  visita depois da expiração: `references/cache.md` §8.
- **O build falha pedindo Suspense numa rota que não mudou.** Um componente de cliente do
  layout lê o caminho ou a busca: `references/dado-dinamico.md` §4.
- **O build falha com lista vazia.** `generateStaticParams` sem nenhum valor, com Cache
  Components: `references/dado-dinamico.md` §3.
- **Funciona em desenvolvimento e quebra no build.** O servidor de desenvolvimento renderiza sob
  demanda: `references/verificacao.md` §4.
- **Endereço que não existe mostra "algo deu errado".** O segmento dinâmico aceitou o valor e a
  consulta falhou: `references/navegacao.md` §5.
- **A rede caiu e o formulário perdeu o que foi digitado.** A ação foi chamada sem `runAction`:
  `references/componentes-e-acoes.md` §5.
- **Todo webhook responde 400.** O corpo passou por `request.json()` antes da conferência:
  `references/apis-e-ambiente.md` §2.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/componentes-e-acoes.md` | servidor e cliente, onde mora cada coisa, ordem da ação, retorno, `runAction`, pacote pesado | passos 2 e 3 |
| `references/cache.md` | o que entra, etiquetas, prazos por perfil, as funções de expirar, escrita por fora, build | passo 4; "dado antigo" |
| `references/dado-dinamico.md` | o que é dado de requisição, três fronteiras, parâmetro de rota, layout, sintomas | passo 5; build pedindo Suspense |
| `references/navegacao.md` | links tipados, filtros na URL, três estados, não encontrada, segmento dinâmico | passo 5 |
| `references/apis-e-ambiente.md` | rota ou ação, webhook, rota de revalidação, proxy, variáveis, configuração | passo 6 |
| `references/verificacao.md` | camadas de teste, regras que viram teste, ponta a ponta contra o build, conferidor | passo 7 |
| `assets/moldes/resultado-de-acao.ts` | o tipo de retorno, `ok`, `fail` e `runAction` | passo 3 |
| `assets/moldes/acao-com-guarda.ts` | uma ação completa, nos seis passos | passo 3 |
| `assets/moldes/leitura-em-cache.ts` | lista fechada, etiquetas e duas leituras em cache | passo 4 |
| `assets/moldes/expirar-cache.ts` | expiração em ação e revalidação por rota com segredo | passo 4 |
| `assets/moldes/pagina-com-suspense.tsx` | página com três fronteiras, filtro na URL, vazio e carregamento | passo 5 |
| `assets/moldes/rota-de-webhook.ts` | a rota que só repassa e o manipulador com os códigos de resposta | passo 6 |
| `assets/moldes/fronteira.test.ts` | quatro regras de arquitetura lidas do código-fonte | passo 7 |
| `scripts/conferir.py` | cinco conferências por leitura de texto; `--help` | antes de começar e antes de enviar |
