---
name: app-com-supabase
description: Monta e revisa a parte de Supabase de um aplicativo web, do modelo de dados à produção. Cobre migrations que só acrescentam, permissões por tipo de usuário (visitante, logado, assinante, admin) com privilégio, RLS e guarda no aplicativo, login por código no e-mail com sessão longa, os cinco clientes e as duas chaves, Storage com bucket público, bucket privado e link assinado, ida do banco local a produção e conteúdo por pasta, com moldes em SQL e TypeScript e um conferidor que só lê o projeto. Use sempre que o usuário disser "cria as tabelas no Supabase", "configura o RLS", "quem pode ver o quê", "login por código no e-mail", "o código não chega", "a sessão cai sozinha", "o visitante está vendo o que não devia", "link para baixar arquivo pago", "posso aplicar a migration em produção" ou "a chave service_role vazou", mesmo sem dizer Supabase num projeto que já o usa. Não use para cobrança (skill assinatura-com-stripe), Realtime, Edge Functions, login por senha ou social, nem para outro banco ou provedor.
---

# App com Supabase

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Funciona no Windows, no macOS e no Linux. No Windows, onde estiver `python3` use `py -3`.

`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do projeto do dono.

- **Três barreiras, sempre as três.** Privilégio de objeto, regra de linha (RLS) e guarda no
  aplicativo. Cada uma falha de um jeito, e a chave pública deixa qualquer um chamar o banco direto.
- **Objeto novo nasce aberto.** Tabela nova em `public` nasce sem RLS e com tudo concedido ao
  visitante. Revogue antes de conceder.
- **A chave secreta ignora tudo.** É lida em um módulo, usada em poucos pontos e nunca vai ao
  navegador.
- **Migration só acrescenta.** Uma por mudança, pelo banco local, com os tipos gerados em seguida.
- **A sessão é do servidor.** O login roda em ação de servidor, o cookie dura 400 dias e o proxy
  renova.
- **O remoto, o painel e as chaves são do dono.** O agente escreve o código, as migrations e os
  testes.

Funciona porque a regra mora onde todos os caminhos passam: a tela, a API do banco chamada por
fora e a ferramenta de carga chegam ao mesmo Postgres. O teste antes de agir: sei que papel do
banco executa esta consulta, que policy decide a linha e que guarda roda antes?

Os moldes de `assets/moldes/` saíram de um sistema em produção, com os nomes trocados. O SQL rodou
no Supabase local (Postgres 17, pgTAP 1.3.3): 11 de 11 no teste por persona, 13 de 13 no de
privilégios. O TypeScript passou pelo verificador de tipos com `@supabase/ssr` 0.12,
`@supabase/supabase-js` 2.117 e Next 16, e não foi executado nesta forma. Nada rodou contra um
projeto remoto. Em outra versão ou framework, copie a ordem das decisões e confira os nomes nos
pacotes instalados. O que está marcado "a conferir na documentação do Supabase" não foi verificado.

## Preparar

1. Leia o que o projeto já tem: `supabase/migrations/`, `supabase/config.toml`, os módulos que
   criam clientes, o módulo que lê segredos e as versões dos pacotes `@supabase/*`.
2. Rode o conferidor, que só lê:

   ```bash
   python3 <skill>/scripts/conferir.py <projeto> --modulo <arquivo que lê a chave secreta>
   # → "acusa:", "aviso:", "ok:", "não conferi:". Saída 0 limpo, 1 acusou, 2 uso, 3 incompleto
   ```

3. Entregue ao dono a lista do que só ele faz (seção "Pare e pergunte ao dono").

- **Requisitos:** Python 3.8 ou mais novo, só para o conferidor (rodou em macOS, com Python 3.14),
  e Docker, para o Supabase local. Sem Python, faça à mão as quatro conferências do script.
- **Projeto sem Supabase:** rode sem `--modulo`; a saída 3 é esperada. **Projeto que já usa:**
  nada é alterado; trate como revisão e comece pela tabela abaixo.

## Onde o projeto está

| Situação | Sinal | Comece por | Leia |
| --- | --- | --- | --- |
| Sem banco | não há pasta `supabase/` | passo 1 | `references/dados-e-migrations.md` |
| Tabelas sem regra | conferidor acusa tabela sem RLS, ou "só funciona com a chave secreta" | passo 3 | `references/permissoes.md` |
| Chave no lugar errado | conferidor acusa leitura fora do módulo | passo 4 | `references/clientes-e-chaves.md` |
| Falta o login | não há sessão, ou a pessoa cai sozinha | passo 5 | `references/login.md` |
| Arquivo para vender | arquivo pago em endereço público | passo 6 | `references/storage.md` |
| Vai ao ar | "posso aplicar em produção?" | passo 7 | `references/producao.md` |
| Algo quebrou | sintoma | "Armadilhas já vistas" | a ficha citada no sintoma |

## Fluxo

### 1. Desenhe o modelo e a matriz antes das telas

Liste o que se cadastra, o que se vende e quem usa. Escreva a matriz por persona e valide com o
dono em frases: `references/dados-e-migrations.md` §1 e `references/permissoes.md` §1.
**Confira:** o que é pago mora em tabela própria, fora da vitrine.
**Pronto quando:** o dono confirmou o que o visitante, o logado, o assinante e o admin conseguem.

### 2. Suba o banco local e escreva a primeira migration

`supabase start`, depois `supabase migration new <assunto>`. Copie
`assets/moldes/funcao-com-guarda.sql` e `assets/moldes/tabela-nova.sql`, nesta ordem.
**Confira:** `supabase db reset` sobe do zero sem erro (avise o dono: apaga o que ele cadastrou).
**Pronto quando:** os tipos foram gerados e o conferidor não acusa as tabelas novas.

### 3. Feche as permissões e prove

Copie `assets/moldes/teste-por-persona.sql` e `assets/moldes/teste-de-privilegios.sql` para
`supabase/tests/` e ajuste: `references/permissoes.md` §7 e §8.
**Confira:** `supabase test db` passa, e falha quando você tira um `revoke` de propósito.
**Pronto quando:** cada persona tem teste do que lê, do que grava e do que não consegue.

### 4. Crie os clientes e separe as chaves

Parta de `assets/moldes/clientes.ts`, um bloco por arquivo: `references/clientes-e-chaves.md`.
**Confira:** o conferidor com `--modulo` não acusa leitura da chave secreta.
**Pronto quando:** o arquivo de exemplo de ambiente lista os nomes, sem nenhum valor.

### 5. Monte o login por código

Parta de `assets/moldes/login-por-codigo.ts`: guardas num módulo, ações em outro. Entregue ao
dono a lista do painel: `references/login.md` §10.
**Confira:** no banco local, o código chega na caixa de e-mail de teste e a sessão sobrevive a
recarregar a página.
**Pronto quando:** primeiro login cai no formulário obrigatório; o segundo, não.

### 6. Storage: buckets e link assinado

Crie os buckets e as policies por migration (`references/storage.md` §3) e a ação de download a
partir de `assets/moldes/link-assinado.ts`.
**Confira:** o visitante não lista mídia de rascunho; sem direito, a ação não assina nada.
**Pronto quando:** o arquivo pago só sai por link de 60 segundos.

### 7. Vá a produção

Banco, dados, código, nesta ordem, com a autorização do dono para a lista de migrations:
`references/producao.md` §3. Conteúdo em lote entra pela ferramenta de pasta (§6).
**Confira:** `supabase migration list` bate, versão a versão.
**Pronto quando:** a conferência como visitante, com a chave pública, mostra só o que é público.

## Regras inegociáveis

1. **Toda tabela nova liga a RLS na migration que a cria.** Se não, a chave pública lê e escreve
   a tabela inteira.
2. **`revoke all` de `anon` e `authenticated` antes de qualquer `grant`.** Se não, o visitante
   esvazia a tabela com `truncate`, que a RLS não filtra.
3. **Função `security definer` leva a guarda na primeira linha e `set search_path = ''`.** Se
   não, qualquer logado executa com os direitos de quem a criou.
4. **A chave secreta é lida em um módulo só de servidor.** Se vazar, é leitura e escrita de tudo:
   o conserto é trocar a chave, passo do dono.
5. **Toda ação e toda leitura por pessoa começam pela guarda.** Se a guarda ficar só na casca, a
   ação chamada direto passa por fora.
6. **A identidade vem da sessão, nunca de argumento.** Se o id vier do navegador, uma pessoa age
   em nome de outra.
7. **Migration aplicada não se edita.** Se editar, dois bancos diferentes ficam com o mesmo
   histórico. Escreva outra.
8. **Nada no remoto sem o dono pedir, e seed nunca.** Se não, produção ganha conta de teste, ou
   perde dado.

## Pare e pergunte ao dono

- **Só o dono faz**, com o passo escrito para ele: criar o projeto; colar chave no painel da
  hospedagem; trocar chave exposta; mexer no painel (SMTP, modelos de e-mail, tamanho do código,
  limites, endereço do site); inserir a própria linha de admin. Não peça valor de chave na conversa.
- **Pergunte antes:** aplicar migration no remoto, com a lista; consertar o histórico de
  migrations; recriar o banco local; rodar a ferramenta de conteúdo contra produção; o que cada
  persona vê, quando a matriz não diz.

## Armadilhas já vistas

- **"Em produção o código é sempre inválido."** O tamanho do código no painel é outro, e a tela
  fixou 6 dígitos: `references/login.md` §4.
- **"Metade das pessoas recebe um link no lugar do código."** Só um dos dois modelos de e-mail
  foi trocado: `references/login.md` §6.
- **"A pessoa cai sozinha depois de uma hora."** O proxy não renova, ou um limite de sessão está
  ligado no painel: `references/login.md` §5.
- **"A consulta volta vazia, sem erro."** É a RLS respondendo, não defeito. Não troque pelo
  cliente admin: `references/permissoes.md` §7.
- **"A função perdeu a proteção depois de uma mudança."** `create or replace` sem repetir os
  atributos: `references/dados-e-migrations.md` §3.
- **"A migration falha ao usar o valor novo do enum."** Valor e uso no mesmo arquivo:
  `references/dados-e-migrations.md` §4.
- **"O visitante lista a mídia dos rascunhos."** Policy larga no bucket público:
  `references/storage.md` §3.
- **"O `db push` quer aplicar tudo de novo."** Histórico remoto com outras versões:
  `references/producao.md` §4.
- **"Publiquei e o site não mudou."** Escrita por fora do aplicativo não expira o cache:
  `references/producao.md` §6.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/dados-e-migrations.md` | modelo, convenções, migration, enum, dado em migration, tipos gerados | passos 1 e 2 |
| `references/permissoes.md` | matriz, três barreiras, policies, funções, testes por persona e de privilégios | passos 1 e 3; visitante vendo demais |
| `references/login.md` | enviar e conferir o código, sessão, e-mail, formulário obrigatório, lista do painel | passo 5; sintoma de login |
| `references/clientes-e-chaves.md` | os cinco clientes, as duas chaves, variáveis, proxy, cache | passo 4 |
| `references/storage.md` | buckets, caminho, a migration, link assinado, envio direto | passo 6 |
| `references/producao.md` | ambientes, o que é do dono, ordem de ida, histórico, visitante, conteúdo por pasta | passo 7 |
| `assets/moldes/funcao-com-guarda.sql` | `admins`, espelho da assinatura, `is_admin()`, `has_plan()`, função com privilégio | passo 2, primeiro |
| `assets/moldes/tabela-nova.sql` | vitrine e conteúdo pago, com RLS, policies, `revoke` e `grant` | passo 2; toda tabela nova |
| `assets/moldes/teste-por-persona.sql` | visitante, logado, assinante e admin, em pgTAP | passo 3 |
| `assets/moldes/teste-de-privilegios.sql` | quatro afirmações genéricas e a lista exata por papel | passo 3 |
| `assets/moldes/clientes.ts` | módulo de segredos e os cinco clientes, um bloco por arquivo | passo 4 |
| `assets/moldes/login-por-codigo.ts` | guardas e as três ações do login | passo 5 |
| `assets/moldes/link-assinado.ts` | ação de download com guarda, direito e caminho conferido | passo 6 |
| `scripts/conferir.py` | tabela sem RLS, sem `revoke`, função sem `search_path`, chave fora do módulo; `--help` | antes de começar e antes de enviar |

Skills irmãs: `assinatura-com-stripe`, para a cobrança e o webhook que escreve a assinatura;
`migrations-sem-susto`, ainda por sair, para migration em detalhe.
