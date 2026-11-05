---
name: ponta-a-ponta-com-personas
description: Monta e revisa testes de ponta a ponta com Playwright que navegam o aplicativo web como cada tipo de usuário, visitante, logado sem plano, assinante e admin. Entrega personas fixas nos dados de exemplo, a sessão de cada uma gerada antes dos testes, sem tela de login nem rota de teste, travas que recusam banco ou endereço não local, a guarda do admin provada pela resposta crua, o login de verdade com o código lido no e-mail local, desktop e celular, execução contra o build de produção, diagnóstico de teste instável e o job de CI, com moldes em TypeScript e um conferidor. Use quando o usuário disser "testa o app como cada tipo de usuário", "quero teste e2e", "configura o Playwright", "o admin está protegido?", "testa o login", "testa no celular também", "o teste falha às vezes", "passa na minha máquina e falha no CI" ou "põe os testes no CI". Não use para teste de unidade ou de banco, teste de carga, comparação visual de telas, nem para provar que conteúdo pago não vaza (skill vazamento-de-paywall).
---

# Ponta a ponta com personas

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do projeto do dono; `<testes>`, a pasta dos
testes de ponta a ponta.

- **Todo teste diz quem é**, numa linha por bloco: visitante, logado sem plano, assinante ou admin.
- **A sessão fica pronta antes do primeiro teste.** O login pela tela tem um teste só dele.
- **Só local.** A configuração recusa banco e endereço que não sejam desta máquina.
- **O teste deixa o banco como achou.** O que ele cria leva um prefixo, e a limpeza apaga por ele.
- **O resultado que vale é contra o build de produção.**

Funciona porque quase todo defeito grave de aplicativo com contas é de papel: alguém vê ou faz o
que não podia. Quando trocar de persona custa uma linha, o teste do "não pode" é escrito. Antes de
agir: sei qual persona este bloco usa, de onde veio a sessão e contra qual servidor estou rodando?

Os moldes de `assets/moldes/` são Playwright com TypeScript, saídos de uma suíte em uso, de 86
testes em desktop e celular, com os nomes trocados. Passaram pelo verificador de tipos com
`@playwright/test` 1.64 e TypeScript 5.9, e o SQL rodou em Postgres 18. Nenhum foi executado nesta
forma contra um aplicativo: adapte e rode. A geração de sessão é a do Supabase; outro provedor:
`references/personas-e-sessoes.md` §6. O que diz "a conferir" não foi verificado.

## Preparar

1. Leia o que o projeto já tem: os dados de exemplo, a guarda de usuário e a de admin, a biblioteca
   de sessão, a pasta de testes, a configuração do Playwright e o comando que sobe o banco local.
2. Rode o conferidor, que só lê:

   ```bash
   python3 <skill>/scripts/conferir.py <projeto> --prefixo <prefixo> --sessoes <pasta de sessões>
   # → "acusa:", "aviso:", "ok:", "não conferi:". Saída 0 limpo, 1 acusou, 2 uso, 3 incompleto
   ```

3. Combine com o dono as personas e o prefixo (seção "Pare e pergunte ao dono").

- **Requisitos:** Node 20.12 ou mais novo, `@playwright/test` no projeto e um banco local que sobe
  por comando. Python 3.8 ou mais novo, só para o conferidor; ele rodou em macOS com Python 3.14.
- **Projeto sem ponta a ponta:** a saída 3 é esperada. **Projeto que já tem:** trate como revisão.

## Onde o projeto está

| Situação | Sinal | Comece por | Leia |
| --- | --- | --- | --- |
| Sem ponta a ponta | não há configuração do Playwright | passo 1 | `references/personas-e-sessoes.md` |
| Todo teste loga pela tela | cada arquivo preenche o formulário de login | passo 2 | `references/personas-e-sessoes.md` §2 |
| Só testa como um papel | nenhum `storageState` por bloco | passo 4 | `references/o-que-testar.md` §1 |
| Admin "protegido" sem prova | o teste só confere o redirecionamento | passo 4 | `references/o-que-testar.md` §2 |
| Teste falha às vezes | "roda de novo que passa" | passo 7 | `references/rodar-e-diagnosticar.md` §4 |
| Vai para o CI | "põe os testes no CI" | passo 8 | `references/ci.md` |

## Fluxo

### 1. Ponha as personas nos dados de exemplo

Parta de `assets/moldes/personas.sql`: uma conta por papel, com identificador fixo; o assinante com
a linha de assinatura ativa; todas com os passos obrigatórios já cumpridos. Só no ambiente local.
**Confira:** recriar o banco local traz as contas com os mesmos identificadores.
**Pronto quando:** o cabeçalho do arquivo lista cada persona, o papel e o identificador.

### 2. Copie o apoio e as travas

Copie `assets/moldes/personas.ts` para `<testes>/`, ajuste os nomes das variáveis e ponha a pasta
de sessões no `.gitignore` antes de gerar a primeira. Outro provedor de login: troque só a parte 4.
**Confira:** com a variável do banco num endereço remoto de mentira, a execução para na trava.
**Pronto quando:** `git check-ignore <pasta de sessões>/admin.json` devolve o caminho.

### 3. Configure o preparo, o desktop e o celular

Copie `assets/moldes/playwright.config.ts` para a raiz e crie `<testes>/preparo.setup.ts` com as 12
linhas de `references/personas-e-sessoes.md` §3.
**Confira:** `npx playwright test --project=preparo` grava um arquivo de sessão por persona.
**Pronto quando:** um teste de uma linha por persona abre a conta e vê o e-mail certo.

### 4. Prove a guarda do admin

Parta de `assets/moldes/guarda-admin.spec.ts`: lista conferida de rotas, controle positivo como
admin e resposta crua, sem seguir o redirecionamento, para as três personas sem acesso.
**Confira:** tire a guarda de uma página de propósito; a resposta crua tem de ficar vermelha.
**Pronto quando:** nenhuma persona sem acesso recebe marcador, e o admin recebe todos.

### 5. Cubra o que cada papel vê, o login e as regras de fluxo

Monte a matriz de tela por persona com o dono: `references/o-que-testar.md` §1. O login pela tela
parte de `assets/moldes/login.spec.ts`; formulário obrigatório e rascunho, das §5 e §6 da ficha.
**Confira:** depois da suíte, nenhuma linha com o prefixo sobra no banco.
**Pronto quando:** cada célula da matriz tem um teste, com a persona no título.

### 6. Separe o que é só do celular

Os dois projetos rodam os mesmos arquivos. O que é de um tamanho só pula dentro do teste, com o
motivo; o que confere resposta crua sai do celular: `references/rodar-e-diagnosticar.md` §3.
**Confira:** os dois projetos rodam juntos sem um escrever na linha do outro.
**Pronto quando:** todo `test.skip` tem o motivo escrito.

### 7. Rode contra o build de produção e trate o instável

O molde da configuração faz o build e sobe o servidor numa porta própria. Teste que falha às vezes:
rode isolado, sem repetição, e leia a falha (`references/rodar-e-diagnosticar.md` §4).
**Confira:** a suíte passa duas vezes seguidas, sem repetição automática.
**Pronto quando:** `conferir.py` sai com 0.

### 8. Ponha no CI

Parta de `assets/moldes/ci-ponta-a-ponta.yml`: banco local com migrations e dados de exemplo,
variáveis lidas da stack, navegador, build, suíte e relatório guardado quando falha.
**Confira:** um teste quebrado de propósito deixa o relatório para baixar.
**Pronto quando:** o job passa sem nenhum segredo do repositório.

## Regras inegociáveis

1. **A suíte só roda contra banco e endereço locais.** A trava roda ao carregar a configuração. Se
   não, um arquivo de ambiente trocado cria contas e apaga dados em produção.
2. **Nenhuma rota de teste no aplicativo; chave de serviço só no processo do teste; arquivo de
   sessão fora do git.** Se não, a porta dos fundos e a credencial vão juntas para produção.
3. **Todo dado criado por teste leva o prefixo, e quem grava usa conta própria.** Se não, desktop
   e celular escrevem na mesma linha, e a sobra de uma execução quebra a seguinte.
4. **A guarda do admin se prova pela resposta crua, com controle positivo.** Se não, uma guarda só
   visual passa no teste de redirecionamento.
5. **Persona declarada em cada bloco.** Com o admin de padrão, um teste sem persona passa com um
   poder que a pessoa de verdade não tem.
6. **O resultado que vale é contra o build de produção.** Medido em 8 GB de memória, com 86 testes:
   10,9 min e 2 falhas no servidor de desenvolvimento com horas de uso; 22,6 s e nenhuma no build.
7. **Sem espera fixa, sem `.only` enviado, repetição automática só no CI.** Se não, o defeito real
   some atrás da segunda tentativa.

## Pare e pergunte ao dono

- **Só o dono faz:** apontar um teste para ambiente que não seja local; pôr segredo no repositório
  ou no CI; encerrar um servidor que ele deixou aberto.
- **Pergunte antes:** os papéis e o que cada um não pode ver; o prefixo; quantos dias a sessão
  dura; recriar o banco local, que apaga os cadastros dele; pular ou apagar um teste; corrigir o
  produto quando o teste achou um defeito.

## Armadilhas já vistas

- **Tudo falha com cara de visitante.** A sessão venceu ou o banco foi recriado: rode o preparo.
- **O preparo não acha as variáveis.** O Playwright não lê o arquivo de ambiente sozinho: a
  configuração o carrega.
- **O teste de guarda passa e a página vaza.** Ele seguiu o redirecionamento e examinou a tela de
  login: `references/o-que-testar.md` §2.
- **Falha só quando roda tudo junto.** Desktop e celular gravam na mesma conta, ou ficou sobra de
  execução anterior ("já existe"): `references/rodar-e-diagnosticar.md` §5.
- **"Achou 2 elementos".** A tela anterior segue escondida no documento: localize por papel.
- **O código de login não chega para todos.** O serviço limita pedidos: os testes daquele arquivo
  rodam em fila (`references/o-que-testar.md` §4).
- **Falhas ao acaso depois de horas.** É o servidor de desenvolvimento: rode contra o build.

Skills irmãs: `vazamento-de-paywall` prova que conteúdo pago não sai do servidor;
`app-com-supabase` cuida de login, sessão e permissões; `nextjs-boas-praticas`, do build.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/personas-e-sessoes.md` | personas, sessão sem tela, preparo, travas, dados de teste, outro provedor | passos 1 a 3 |
| `references/o-que-testar.md` | matriz por persona, guarda, login, formulário obrigatório, rascunho | passos 4 e 5 |
| `references/rodar-e-diagnosticar.md` | build de produção, comandos, celular, teste instável | passos 6 e 7 |
| `references/ci.md` | os passos do job, segredos, o que muda no CI, vermelho | passo 8 |
| `assets/moldes/personas.sql` | as contas e os dados mínimos de cada papel | passo 1 |
| `assets/moldes/personas.ts` | travas, contas, prefixo, geração de sessão e limpeza | passo 2 |
| `assets/moldes/playwright.config.ts` | preparo, desktop, celular, travas e servidor de produção | passo 3 |
| `assets/moldes/guarda-admin.spec.ts` | a guarda provada de cinco jeitos | passo 4 |
| `assets/moldes/login.spec.ts` | login pela tela com o código lido no e-mail local | passo 5 |
| `assets/moldes/ci-ponta-a-ponta.yml` | o job para o GitHub Actions | passo 8 |
| `scripts/conferir.py` | `.only`, espera fixa, endereço remoto, sessão no git, gravação sem prefixo; `--help` | antes de começar e antes de enviar |
