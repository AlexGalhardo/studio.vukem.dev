# Verificação: como uma regra de arquitetura deixa de depender de quem lembra dela?

Leia quando: for fechar uma entrega, montar o CI, ou quando uma regra "que todo mundo sabe" for
quebrada pela segunda vez (passo 7 do fluxo).
Não é aqui: testes do banco e das regras de acesso por linha (skill `app-com-supabase`).

## O mínimo

- Regra de arquitetura que importa vira teste que lê o código-fonte. Roda em segundos, junto dos
  testes de unidade.
- Todo teste desse tipo tem um controle que prova que ele olhou alguma coisa.
- O teste ponta a ponta que vale roda contra o build de produção.
- `conferir.py` é a primeira passada num projeto que você ainda não conhece. O teste de
  fronteira é o que fica no projeto.

Conteúdo: 1. Três camadas 2. Regras que viram teste 3. O controle contra passar por nada
4. Ponta a ponta contra o build 5. O conferidor 6. Antes de enviar

## 1. Três camadas

| Camada | O que pega | Tempo | Precisa de |
| --- | --- | --- | --- |
| Unidade, ao lado do arquivo (`regra.test.ts`) | regra pura errada: filtro, endereço, validação, etiqueta | segundos | nada |
| Fronteira, lendo o código-fonte | arquitetura quebrada: import proibido, ação sem guarda, segredo fora do lugar | segundos | nada |
| Ponta a ponta, no navegador | o que só existe montado: cache, Suspense, guarda de verdade, vazamento no HTML | minutos | build, banco local com dados de teste |

Verificador de tipos e lint rodam antes das três. Com rotas tipadas, o comando é
`next typegen && tsc --noEmit`.

## 2. Regras que viram teste

Molde: `assets/moldes/fronteira.test.ts`. Ele lê os arquivos como texto, sem subir nada.

| Regra | Como o teste enxerga | Se quebrar em produção |
| --- | --- | --- |
| Componente de cliente não importa módulo só de servidor | arquivo com `"use client"` e import de runtime de arquivo com `import "server-only"`, ou de `next/headers` | o build falha, ou a consulta vai parar no navegador |
| Pacote pesado fora do bundle público | arquivo com `"use client"` e import de runtime do pacote | todas as páginas públicas carregam o pacote |
| Toda ação começa pela guarda | a primeira instrução de cada `export async function` dos arquivos de ação | qualquer pessoa chama a ação por POST |
| Escopo em cache não lê sessão | arquivo com `"use cache"` que importa `next/headers` ou o módulo de sessão | dado de uma pessoa servido a outra |
| Segredo lido num módulo só | `process.env.X` fora dos módulos de ambiente | chave espalhada, sem validação, com risco de ir para o cliente |
| Conteúdo pago lido por uma função só | o nome da tabela ou da função aparece só nos arquivos permitidos | o texto pago sai no HTML de quem não pagou |

A última regra depende de nomes do seu projeto: acrescente-a ao molde com a tabela e os
arquivos permitidos. `import type` não conta como import de runtime: tipo não vai para o bundle.

Escolha regra cujo descumprimento custa caro e passa calado. Não transforme em teste o que o
verificador de tipos ou o lint já recusam.

## 3. O controle contra passar por nada

Um teste que procura violações numa lista vazia passa sempre. Basta uma pasta mudar de nome:
a regra continua verde e não olha mais nenhum arquivo. O sistema de origem tem um teste só para
isso, que planta um arquivo errado em quatro das regras e exige a falha.

- Confira que a varredura achou arquivos (`expect(clients.length).toBeGreaterThan(0)`).
- Confira que o arquivo citado nas constantes existe e contém o padrão esperado (o módulo de
  ambiente lê `process.env`, o arquivo de ações tem pelo menos uma ação).
- Ao criar a regra, quebre-a de propósito uma vez e veja o teste falhar. Só então confie nele.
- Num arquivo de ações, exija que todo `export` seja uma ação. Uma função auxiliar exportada ali
  vira endereço público sem ninguém notar.

## 4. Ponta a ponta contra o build

O servidor de desenvolvimento e o build diferem justamente no que esta skill cuida:

| Diferença | De onde vem |
| --- | --- |
| No servidor de desenvolvimento a rota é renderizada sob demanda: `useSearchParams` não suspende e a falta de `<Suspense>` não aparece. No build, ela quebra | documentação da 16.4 (`use-search-params.md`) |
| Cada rota compila na primeira visita: o primeiro teste de cada rota espera a compilação e pode estourar o prazo | documentação da 16.4 (`local-development.md`) |
| O servidor de desenvolvimento recusa os próprios recursos quando o teste usa outro endereço (`127.0.0.1` no lugar de `localhost`), e a página não hidrata até configurar `allowedDevOrigins` | visto no sistema de origem |
| Casca estática, expiração do cache e a primeira visita antiga | medidos só contra `next start`; no servidor de desenvolvimento não foram medidos |

A documentação do Next recomenda rodar os testes de navegador contra o código de produção
(`testing/playwright.md`).

- No CI: `next build`, depois `next start`, depois os testes. Deixe o executor de testes subir o
  `next start` e esperar o endereço responder.
- Na máquina de trabalho, o servidor de desenvolvimento serve para escrever o teste. O resultado
  que vale é o do build.
- O build consulta o banco (`references/cache.md` §9): suba o banco e carregue os dados de teste
  antes.
- **Teste de cache:** publique pelo painel, depois recarregue a página pública até o item
  aparecer, com prazo de 30 s. Não exija a primeira resposta (`references/cache.md` §8).
- **Teste de vazamento:** como visitante e como usuário sem plano, baixe o HTML da página paga e
  procure um marcador que só existe no conteúdo pago. Procure também nas respostas de
  navegação, não só no HTML inicial.
- **Localize por papel e nome**, não por texto solto: a tela anterior continua no documento,
  escondida, e uma busca por texto a encontra.
- **Teste de guarda:** visitante é levado ao login; logado sem permissão recebe página não
  encontrada; a ação chamada direto, sem a tela, é recusada.

## 5. O conferidor

```bash
python3 <skill>/scripts/conferir.py <projeto> --segredos lib/env.server.ts
# → linhas "acusa:", "aviso:", "ok:", "não conferi:" e um resumo
# saída 0 limpo; 1 acusou; 2 uso errado; 3 alguma conferência não rodou
```

| Confere | Acusa quando | Não enxerga |
| --- | --- | --- |
| Cliente e servidor | arquivo com `"use client"` importa `next/headers`, `server-only` ou arquivo marcado só de servidor | import indireto, por um arquivo no meio |
| Guarda | função exportada de arquivo com `"use server"` no topo não começa por `await <guarda>(` | ação definida dentro de componente; `export const` (sai como "não conferi") |
| Cache | o corpo de uma função com `"use cache"` chama `cookies()` ou `headers()` | leitura feita por função auxiliar de outro arquivo |
| Estados da rota | página sem `loading.*` acima nem `<Suspense` nela, ou sem `error.*` acima | `<Suspense>` dentro de um componente filho (falso alarme possível) |
| Ambiente | `process.env.X` não pública fora de `--segredos`, em arquivo de cliente, ou pública com nome de segredo | acesso por nome montado; arquivos da raiz e de `scripts/` ficam de fora |

Opções: `--guarda NOME` troca os nomes das guardas; `--sem-guarda ARQUIVO` isenta o arquivo das
ações de login; `--alias PREFIXO` troca o apelido de import. Ele lê texto: não segue imports,
não executa nada, não abre arquivos `.env`. Não achar não prova que não há.

## 6. Antes de enviar

1. `next typegen && tsc --noEmit`, lint e testes de unidade passam.
2. O teste de fronteira passa, e falhou quando você quebrou a regra de propósito.
3. `conferir.py` sai com 0, ou cada "acusa" tem explicação escrita.
4. O build passa com o banco no ar.
5. Os testes ponta a ponta passam contra `next start`.
6. Se houve escrita por fora do aplicativo, a rota de revalidação foi chamada e a página foi
   conferida no endereço que o público usa.
