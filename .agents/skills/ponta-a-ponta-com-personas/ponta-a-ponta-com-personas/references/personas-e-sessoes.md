# Personas e sessões: como o teste vira cada tipo de usuário sem passar pelo login?

Leia quando: for criar as personas nos dados de exemplo, gerar as sessões, pôr as travas ou decidir
o que um teste pode gravar (passos 1 a 3 do fluxo).
Não é aqui: o que afirmar em cada persona (`references/o-que-testar.md`); onde e como rodar
(`references/rodar-e-diagnosticar.md`).

## O mínimo

- Uma conta por papel nos dados de exemplo, com identificador fixo, só no ambiente local.
- Um projeto de preparo grava um arquivo de sessão por persona antes dos testes. Cada bloco escolhe
  a persona numa linha; sem escolher, é visitante.
- A sessão nasce da biblioteca de sessão do próprio aplicativo: sem rota de teste, sem cookie
  montado à mão.
- A configuração recusa banco, endereço e caixa de e-mail que não sejam desta máquina.
- Tudo o que o teste cria leva o prefixo, e quem grava usa conta própria.

Conteúdo: 1. Personas 2. Sessão sem tela 3. O projeto de preparo 4. Travas 5. Dados que o teste
cria 6. Outro provedor de login

## 1. Personas nos dados de exemplo

| Persona | O que faz dela essa persona | No teste |
| --- | --- | --- |
| Visitante | nenhuma conta | `VISITANTE`, a sessão vazia |
| Logado | conta, sem linha de assinatura | `ESTADO.logado` |
| Assinante | conta e linha de assinatura ativa | `ESTADO.assinante` |
| Admin | conta e linha de papel de admin | `ESTADO.admin` |

- **Identificador fixo.** O teste e os outros dados apontam para a conta sem consultar o banco, e
  a mesma persona é a mesma linha depois de recriar o banco.
- **O assinante é assinante por uma linha.** Em produção quem grava a assinatura é o aviso do
  provedor de pagamento. Nos dados de exemplo, o próprio arquivo faz esse papel.
- **Todas já cumpriram os passos obrigatórios** (perfil respondido, termos aceitos). Se não, todo
  teste delas cai no formulário de boas-vindas.
- **Uma persona para cada estado que as regras distinguem.** Se existe plano pausado ou conta
  bloqueada, existe a persona. Quatro é o ponto de partida, não o teto.
- **Só local.** O arquivo de dados de exemplo abre com o aviso e nunca roda no banco remoto.

Molde: `assets/moldes/personas.sql`, com a lista de personas no cabeçalho.

## 2. Sessão sem tela

| Caminho | Por que não |
| --- | --- |
| Logar pela tela em todo teste | lento; o serviço de login limita pedidos; uma mudança na tela de login derruba a suíte inteira |
| Rota de teste que loga quem pedir | é uma porta dos fundos, e um dia ela vai a produção |
| Cookie montado à mão | quebra quando a biblioteca muda o nome, a codificação ou o fatiamento |

O caminho usado, em `cookiesDeSessao` de `assets/moldes/personas.ts`:

1. Com a chave de serviço do banco local, peça uma credencial de uso único para o e-mail da
   persona à API de administração do login. Nenhum e-mail é enviado.
2. Troque a credencial por sessão com a mesma biblioteca de sessão que o aplicativo usa no
   servidor, com um gravador de cookies no lugar do navegador.
3. O mesmo cookie pode chegar duas vezes (remoção e depois gravação): vale o último, e o vazio é
   descartado. Zero cookies no fim é erro, com o e-mail da persona na mensagem.
4. Grave `{ cookies, origins: [] }` em `<pasta de sessões>/<persona>.json`. Esse é o formato que
   `storageState` lê.

A chave de serviço fica no processo do teste, nunca no navegador nem no aplicativo. O arquivo de
sessão é uma credencial: a pasta entra no `.gitignore` antes do primeiro preparo.

## 3. O projeto de preparo

Crie `<testes>/preparo.setup.ts`. São 12 linhas; o projeto `preparo` da configuração aponta para
ele, e `desktop` e `celular` dependem dele.

```ts
import { test as preparo } from "@playwright/test";
import { apagarContasDeTeste, apagarPorPrefixo, gravarSessoes } from "./personas";

// Projeto "preparo": roda uma vez, antes do desktop e do celular, que dependem dele.
preparo("sessões das personas e limpeza das sobras", async ({ baseURL }) => {
  if (!baseURL) throw new Error("Ponta a ponta: baseURL não configurada.");
  await gravarSessoes(baseURL);
  // Sobras de execução que parou no meio: o que leva o prefixo de teste, tabela por tabela.
  await apagarPorPrefixo("itens", "slug");
  // Lista vazia: só as contas de teste com mais de 10 minutos.
  await apagarContasDeTeste([]);
});
```

- **O apoio não é um teste, e o preparo é um arquivo à parte.** O Playwright recusa um arquivo de
  teste que importa outro (`should not import test file`). O que é compartilhado mora em
  `personas.ts`, que não chama `test()`; a configuração e os testes importam dele.
- **A sessão gravada vence e não sobrevive a recriar o banco.** No sistema de origem ela valia 1
  hora. O preparo roda a cada execução, então só `--no-deps` usa sessão velha: se tudo falhar com
  cara de visitante, rode sem essa opção.
- **Um teste escolhe a persona assim:** `test.use({ storageState: ESTADO.assinante })` dentro do
  `test.describe`. A requisição direta (`request`) usa a mesma sessão do bloco.

## 4. Travas

| Trava | Onde | Recusa |
| --- | --- | --- |
| Endereço do aplicativo | `exigirLocal`, ao carregar a configuração | `baseURL` fora de `127.0.0.1`, `localhost` e `[::1]` |
| Banco | `lerAmbienteDeTeste`, ao carregar a configuração e em toda função que usa a chave de serviço | endereço de banco que não é local, ou variável faltando |
| Caixa de e-mail | `exigirLocal`, no topo do teste de login | caixa que não é local |

A mensagem diz o porquê ("os testes criam sessões e dados") e nunca traz o valor de uma chave.

O que a trava não prova: que o servidor sob teste lê o mesmo arquivo de ambiente que a
configuração. Confira uma vez: o comando que sobe o servidor e a configuração do Playwright leem a
mesma variável de endereço do banco. No CI as duas vêm do ambiente do job.

## 5. Dados que o teste cria

- **Prefixo em tudo.** O molde usa `zzteste-`; combine o do projeto com o dono. Sem `_` nem `%`,
  que são coringas na busca da limpeza. Nenhum dado de exemplo começa com ele.
- **Quem grava usa conta própria.** O teste que só olha a tela usa a persona dos dados de exemplo.
  O que grava (resposta de formulário, perfil, item) cria uma conta por projeto e por processo,
  porque desktop e celular rodam ao mesmo tempo e escreveriam na mesma linha.
- **Limpeza em três momentos.** No preparo (sobra de execução que parou no meio), no `afterAll` do
  grupo (o que este processo criou) e a varredura das contas com mais de 10 minutos, pelo carimbo
  de tempo no e-mail: uma requisição lenta pode criar a conta depois de a limpeza ter passado.
- **O teste deixa o banco como achou.** O fluxo que cria e publica também arquiva e apaga.
- **Estado que em produção vem de fora** (assinatura gravada pelo aviso do provedor de pagamento) o
  teste grava com o cliente de serviço, fazendo o papel do aviso, na conta própria dele.
- **A suíte passa com e sem as chaves do serviço externo.** O CI roda sem elas: o fluxo termina num
  aviso tratado, e é isso que o teste afirma.

## 6. Outro provedor de login

Só o caminho do Supabase foi usado de verdade. Os outros seguem a mesma ordem de decisões e não
foram executados: confira os nomes na documentação do provedor.

| Login | O preparo gera a sessão assim |
| --- | --- |
| Supabase | o molde: `generateLink`, `verifyOtp` e o gravador de cookies de `createServerClient` |
| Próprio, com sessão no banco | insira a linha de sessão com o cliente de serviço e grave o cookie pela função do aplicativo que o assina, importada no teste |
| Token no cabeçalho | emita o token com a chave do ambiente local e mande-o por `extraHTTPHeaders`; se o aplicativo o lê do armazenamento do navegador, grave-o em `origins` |
| Página hospedada pelo provedor | procure o modo de teste ou a API de administração do provedor. Se só houver a tela, o preparo loga uma vez por persona e salva com `page.context().storageState({ path })` |

O que não muda: contas fixas por persona, sessão gerada antes dos testes, travas, e o login de
verdade coberto uma vez, no teste dele.

## Pronto quando

- Recriar o banco local e rodar a suíte duas vezes seguidas dá o mesmo resultado.
- Apontar a variável do banco para um endereço remoto faz a execução parar antes do primeiro teste.
- `git status` não mostra arquivo de sessão, e depois da suíte não sobra linha com o prefixo.
