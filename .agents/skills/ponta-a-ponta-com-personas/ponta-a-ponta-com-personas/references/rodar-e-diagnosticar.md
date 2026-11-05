# Rodar e diagnosticar: contra o que rodar, em quais telas, e o que fazer com o teste que falha às vezes?

Leia quando: for rodar a suíte, acrescentar o celular ou investigar um teste instável (passos 6 e
7 do fluxo).
Não é aqui: o job de CI (`references/ci.md`); o que afirmar em cada teste
(`references/o-que-testar.md`).

## O mínimo

- O resultado que vale é contra o build de produção, numa porta própria.
- Desktop e celular são dois projetos que rodam os mesmos arquivos. O que é de um só pula com o
  motivo escrito.
- Teste instável: rode isolado e sem repetição, e leia a falha antes de mexer em qualquer coisa.
- Repetição automática só no CI. Espera fixa por tempo, nunca.

Conteúdo: 1. Build de produção 2. Comandos 3. Desktop e celular 4. Teste instável 5. Causa e
conserto

## 1. Contra o build de produção

Medido no sistema de origem, numa máquina de 8 GB de memória, com a mesma suíte de 86 testes:

| Alvo | Resultado | Tempo |
| --- | --- | --- |
| Servidor de desenvolvimento com horas de uso | 2 testes falhando, por conexão derrubada e tempo estourado | 10,9 min |
| Build de produção | os 86 passando | 22,6 s |

O servidor de desenvolvimento compila cada rota na primeira visita, cresce em memória com o uso e
não é o que vai a produção. As regras, já no molde `assets/moldes/playwright.config.ts`:

- **O comando local faz o build e sobe o servidor.** Subir à mão um servidor de produção antigo
  testa o código do último build, não o de agora.
- **Porta própria (3100 no molde).** Não disputa com o servidor de desenvolvimento que o dono
  deixou aberto, e ninguém precisa derrubá-lo.
- **`reuseExistingServer: false`.** Com algo já na porta, o Playwright para com "is already used".
  Se o processo que sobrou não foi você que subiu, pergunte ao dono antes de encerrá-lo.
- **Um processo pesado por vez** em máquina com pouca memória: build, suíte e servidor de
  desenvolvimento compilando ao mesmo tempo produzem as falhas da primeira linha da tabela.
- **Build que consulta o banco** precisa do banco local no ar e migrado antes. Detalhes do build:
  skill `nextjs-boas-praticas`.

## 2. Comandos

Opções conferidas no pacote `@playwright/test` 1.64.

| Para | Comando |
| --- | --- |
| A suíte inteira, nos dois projetos | `npx playwright test` |
| Um arquivo num projeto | `npx playwright test login.spec.ts --project=desktop` |
| Um teste pelo título | `npx playwright test -g "trecho do título"` |
| Ver a falha de verdade | `npx playwright test <arquivo> --project=desktop --retries=0 --workers=1 --trace on` |
| Medir a frequência | acrescente `--repeat-each 10` ao comando de cima |
| Só os que falharam na última execução | `npx playwright test --last-failed` |
| Parar na primeira falha | acrescente `-x` |
| Pular o preparo | acrescente `--no-deps`; usa a sessão já gravada, que vence |
| Abrir o relatório ou um rastro | `npx playwright show-report` e `npx playwright show-trace <trace.zip>` |

## 3. Desktop e celular

- **Dois projetos, os mesmos arquivos.** `desktop` usa o Chromium de mesa em 1440 × 900; `celular`
  usa `devices["Pixel 7"]`, em 412 × 839 e com tela de toque. Defeito de tela pequena não aparece
  na larga.
- **O que é de um tamanho só pula dentro do teste, com o motivo:**

  ```ts
  test("a barra fixa leva a cada seção", async ({ page }, info) => {
    test.skip(info.project.name !== "celular", "A barra fixa só existe no celular");
    // …
  });
  ```

- **O que não depende de tela roda num projeto só.** A resposta crua é igual nos dois: o molde
  tira o teste de guarda do celular com `testIgnore`.
- **Localidade e fuso fixos na configuração.** O resultado não pode mudar com a máquina.
- **Quem grava usa uma conta por projeto.** Os dois rodam ao mesmo tempo: ponha
  `info.project.name` e `info.workerIndex` no rótulo de `emailDeTeste`.

| Costuma ser só do celular | Costuma ser só do desktop |
| --- | --- |
| menu que vira gaveta, barra fixa de navegação, alvo de toque de 44 px ou mais, página sem rolagem horizontal | atalho de teclado, tabela larga, painel lateral, resposta crua |

O projeto `celular` é emulação no Chromium (tamanho, toque e identificação do navegador). Não é o
navegador de um aparelho de verdade: motor diferente pede outro projeto e outro navegador
instalado no CI.

## 4. Teste instável: o procedimento

1. **Leia a saída e o rastro.** Relate a falha com a saída, não com "falhou um teste".
2. **Rode isolado e sem repetição** (linha "Ver a falha de verdade"). Depois rode junto dos outros.
3. **Separe o tipo de falha:**

   | A saída mostra | É | Olhe |
   | --- | --- | --- |
   | `expect` com esperado e recebido | falha de asserção: o aplicativo respondeu, e respondeu outra coisa | o produto ou o teste |
   | erro de rede do navegador (`net::ERR_…`), conexão recusada ou derrubada | o servidor caiu ou não aguentou | o alvo: é o servidor de desenvolvimento? falta memória? |
   | `Timeout … exceeded` | pode ser qualquer um dos dois | o rastro: a requisição ficou sem resposta (ambiente) ou o elemento nunca apareceu (asserção)? |

4. **Compare as execuções.** Falha só junto dos outros: estado compartilhado. Só no servidor de
   desenvolvimento: ambiente. Só em certo dia ou hora: data.
5. **Classifique na tabela do item 5 e aplique o conserto.** Se a causa é defeito do produto (o
   clique perdido acontece com uma pessoa de verdade?), é correção, não ajuste de teste.
6. **Não servem:** espera fixa, limite global maior, repetição automática local, teste pulado ou
   apagado em silêncio, CI vermelho "conhecido".

## 5. Causa e conserto

| Causa | Sintoma | Conserto |
| --- | --- | --- |
| Clique antes de a página ficar interativa | o botão existe e o clique não faz nada | repita a ação e a conferência juntas até passar (bloco abaixo) |
| Cache que serve a versão anterior | o item publicado não aparece na primeira carga | recarregue até aparecer, com limite de 30 s; registre o comportamento e cite no teste |
| Dado que depende da data | selo "novo", ordem por uso | não afirme o que depende do dia; localidade e fuso fixos |
| Serviço com limite de pedidos | vários testes pedem código de login juntos | os testes daquele arquivo rodam em fila |
| Um teste depende do anterior | o segundo passo falha isolado | grupo em série, com o porquê no comentário e conta própria |
| Desktop e celular gravam na mesma linha | falha só quando roda tudo junto | uma conta por projeto, criada e apagada no grupo |
| Sobra de execução anterior | "já existe" na criação | prefixo, limpeza antes e depois, varredura das contas antigas |
| Mensagem assíncrona | o e-mail ainda não chegou | `expect.poll` com limite e mensagem própria |
| Elemento duplicado no documento | "achou 2 elementos" | localize por papel, ou só os visíveis |
| Passo longo de verdade | o envio de um arquivo estoura o limite | limite maior só naquele teste, com o motivo |
| Servidor de desenvolvimento degradado | falhas ao acaso depois de horas | rode contra o build de produção |

```ts
// O critério é o efeito observável, não o tempo.
await expect(async () => {
  await botao.click();
  await expect(painel).toBeVisible({ timeout: 1_000 });
}).toPass({ timeout: 15_000 });
```

A rede de proteção: nenhuma repetição na máquina, para a instabilidade aparecer a quem escreve; no
CI, até 2, com o rastro gravado na primeira. Teste que só passa na repetição continua na lista de
consertos: a repetição evita travar o envio, não resolve a causa.

## Pronto quando

- A suíte passa duas vezes seguidas contra o build de produção, sem repetição, nos dois projetos.
- `conferir.py` não acusa espera fixa nem `.only`, e todo teste pulado tem o motivo escrito.
- Cada teste que já foi instável tem, no comentário, a causa achada.
