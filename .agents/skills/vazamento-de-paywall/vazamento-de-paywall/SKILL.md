---
name: vazamento-de-paywall
description: Prova, por tipo de usuário, que conteúdo pago não sai do servidor para quem não pagou, em qualquer aplicativo web com área paga. Planta marcadores únicos no começo e no fim de cada conteúdo pago dos dados de exemplo e os procura na resposta crua (HTML e payload de dados do framework) de cada rota, como visitante, logado sem plano, assinante e admin. Prende as outras três camadas (banco por persona, teste de fronteira no código-fonte, arquivo pago só por link assinado curto) e confere por fora depois de publicar, com moldes em Playwright, TypeScript e Postgres e uma sonda em Python que só faz GET. Use sempre que houver paywall, área de assinante ou conteúdo premium e o usuário disser "dá para ler o conteúdo pago sem pagar?", "testa meu paywall", "o texto aparece no código-fonte da página", "vazou conteúdo de assinante" ou "posso abrir a área paga?", mesmo sem dizer vazamento. Não use para montar a cobrança, criar as permissões do banco do zero, testar site de terceiros ou impedir cópia por quem pagou.
---

# Vazamento de paywall

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do projeto do dono.

- **O dado pago de teste se anuncia sozinho.** Cada conteúdo pago dos dados de exemplo leva um
  marcador único no começo e outro no fim. O teste procura por eles; não adivinha.
- **Resposta crua, não tela.** O que vaza está no HTML e no payload de dados que o framework manda
  junto, antes de o navegador esconder qualquer coisa.
- **Por persona.** Visitante, logado sem plano, assinante e admin pedem as mesmas rotas. Quem não
  paga recebe zero marcador pago; quem paga recebe todos.
- **Teste que nunca acha nada não prova nada.** Prova da resposta, prova da persona, controle
  positivo e lista conferida, em todo teste.
- **Quatro camadas.** Resposta, banco, código-fonte e armazenamento. Cada uma falha de um jeito.

Funciona porque esconder é trabalho do navegador, e o navegador é de quem visita: o que chegou
até ele já saiu. O teste antes de agir: sei qual função lê o conteúdo pago, quais rotas podem
mostrá-lo e que marcador prova que ele saiu?

Os moldes de `assets/moldes/` saíram de um sistema em produção (Next.js 16 e Postgres com
segurança por linha), com os nomes trocados. Rodaram: a sonda, contra um servidor de brinquedo
local (16 casos); os dois SQL, em Postgres 18, reprovando em 5 vazamentos plantados; o teste de
fronteira, em Vitest 5, contra um projeto de brinquedo. O teste de vazamento e as personas
passaram no verificador de tipos (TypeScript 5.9, Playwright 1.64) e não foram executados nesta
forma. O que as fichas marcam "adaptação" não foi praticado na origem. **O teste prova o que
procura:** marcador que não está nos dados de exemplo, que chega codificado ou cuja rota ficou
fora da lista não é encontrado. "Limpo" é "não achei o que procurei", para aquela persona.

## Preparar

1. Leia o que o projeto já tem: onde mora o conteúdo pago (tabela, campo, arquivo), a função que
   decide o acesso, os dados de exemplo, o executor de ponta a ponta e como se cria uma sessão.
2. Entregue ao dono as perguntas da seção "Pare e pergunte ao dono".

- **Requisitos:** Python 3.8 ou mais novo, só para a sonda (rodou em macOS com Python 3.14).
- **Só local.** Dados de exemplo, sessões e testes rodam contra banco e servidor locais.

## Onde o projeto está

| Situação | Sinal | Comece por | Leia |
| --- | --- | --- | --- |
| Sem teste de vazamento | não há marcador nos dados de exemplo | passo 1 | `references/marcadores-e-personas.md` |
| Suspeita de vazamento | "o texto aparece no código-fonte da página" | passos 2 e 3 | `references/onde-vaza.md` §2 |
| Teste só de tela | o teste abre o navegador e procura o texto visível | passo 5 | `references/resposta-crua.md` |
| Passa na ponta, e só | não há teste de banco nem de fronteira | passo 6 | `references/camadas.md` |
| Vai publicar ou publicou | "posso abrir a área paga?" | passo 7 | `references/onde-vaza.md` §3 |

## Fluxo

### 1. Liste o que é pago, quem pede e por onde sai

Escreva três listas: os conteúdos pagos (texto, arquivo, vídeo), as personas e toda rota pública
que pode mostrar um item (inicial, listagens, busca, feed, a página do item e as dos outros).
**Confira:** cada linha da tabela de `references/onde-vaza.md` §1 virou rota ou foi descartada.
**Pronto quando:** o dono confirmou o que cada persona pode ler.

### 2. Plante os marcadores

Parta de `assets/moldes/dados-de-exemplo.sql`: 2 itens pagos, 1 livre e 1 rascunho, cada corpo
com `PAGO-INICIO-<6 caracteres>` na primeira linha e `PAGO-FIM-<6 caracteres>` na última.
Formato e sorteio: `references/marcadores-e-personas.md` §1 e §2.
**Confira:** cada marcador ocorre 1 vez no corpo e 1 vez no cabeçalho do arquivo, e em mais nada.
**Pronto quando:** o banco local recriado mostra o item pago bloqueado e o livre aberto.

### 3. Faça a primeira leitura com a sonda

Com o servidor local no ar, rode como visitante (só GET, uma requisição por rota):

```bash
python3 <skill>/scripts/sonda.py --base http://localhost:3000 --rotas-de rotas.txt \
  --marcadores-de marcadores.txt --controle <ponta INICIO do item livre>
# → "vazou:", "limpo:", "não conferi:". Saída 0 nada vazou, 1 vazou, 2 uso, 3 não conferiu
```

Repita pedindo o payload (`--cabecalho`): `references/resposta-crua.md` §7.
**Confira:** a linha `controle:` apareceu. Sem ela a sonda pode estar cega.
**Pronto quando:** todo `vazou:` e todo `não conferi` têm causa (`references/onde-vaza.md` §2).

### 4. Prepare as personas

Parta de `assets/moldes/personas.ts`: uma conta fixa por persona, sessão gerada sem tela com a
biblioteca de sessão do produto, trava que recusa banco que não é local.
**Confira:** apague a pasta de sessões e rode o preparo: os três arquivos voltam.
**Pronto quando:** cada arquivo de sessão abre a página como a persona certa.

### 5. Escreva o teste de vazamento

Parta de `assets/moldes/vazamento.spec.ts`. Para cada persona sem acesso, cada rota e cada forma
de resposta: as quatro provas de `references/resposta-crua.md` §2 e nenhum marcador pago.
**Confira:** entregue o corpo pago à tela de bloqueio de propósito: o teste reprova. Desfaça.
**Pronto quando:** o teste passa contra o build de produção e entra no CI.

### 6. Prenda as outras três camadas

Banco: `assets/moldes/banco-por-persona.sql`. Código: `assets/moldes/fronteira.test.ts`.
Armazenamento: as cinco regras de `references/camadas.md` §4.
**Confira:** cada teste reprova com um vazamento plantado (política aberta, segundo leitor).
**Pronto quando:** os dois testes rodam antes de todo envio e as cinco regras estão conferidas.

### 7. Confira por fora depois de publicar

Com o aval do dono e o endereço exato (`references/onde-vaza.md` §3): como visitante, com
trechos-isca do conteúdo de verdade, duas vezes, e com a chave pública direto no banco.
**Confira:** saída 0 e a linha `controle:`. Saída 3 não é aprovação.
**Pronto quando:** data, endereço, rotas e saídas estão registrados onde o dono lê.

## Regras inegociáveis

1. **O conteúdo pago mora separado do registro público, e uma função só o lê.** Se não, a
   listagem que pede "todas as colunas" leva o texto junto.
2. **A função decide o acesso antes de consultar, e erro nunca libera.** Se a decisão fica no
   navegador, o texto já saiu.
3. **Leitura por pessoa fica fora de cache compartilhado.** Se não, a resposta montada para a
   assinante é servida ao visitante.
4. **O teste lê a resposta crua, em toda forma, e prova que é a página pedida.** Se não, tela de
   login, erro e resposta vazia contam como "não vazou".
5. **Todo bloco sem acesso prova a persona, e todo teste tem controle positivo.** Se não, sessão
   vencida vira visitante e tudo passa.
6. **A lista de marcadores do teste é a dos dados de exemplo, conferida por teste.** Se não, o
   item pago novo fica de fora sem ninguém notar.
7. **Arquivo pago: repositório privado e link assinado de até 60 segundos, gerado no servidor
   depois da função de acesso.** Se não, o link circula e o arquivo é de todos.
8. **Fora do local, a sonda só roda no site do próprio dono, com `--site-proprio` e o aval dele.**
   Varrer site de terceiros não é teste: é sondagem sem permissão.

## Pare e pergunte ao dono

- **Só o dono faz:** exportar no próprio terminal o cookie de uma conta de produção (o valor não
  passa pela conversa); abrir o item como assinante para a conferência do cache; decidir o que
  fazer com conteúdo que já vazou.
- **Pergunte antes:** o que conta como pago (o texto inteiro, parte dele, o arquivo); se existe
  prévia grátis de propósito, e de quantos caracteres; se robô de busca recebe o texto completo;
  qualquer requisição a endereço que não seja local; chamar o banco remoto com a chave pública.

## Armadilhas

- **"O teste passa, e o texto está no código-fonte da página."** O teste olhou a tela ou pulou o
  payload: `references/resposta-crua.md` §1.
- **Tudo verde depois de recriar o banco.** As sessões venceram e todos viraram visitante. Prova
  da persona, e o preparo rodado de novo: `references/marcadores-e-personas.md` §4.
- **O visitante vai ao login e o teste passa.** O teste seguiu o redirecionamento e examinou a
  tela de login. Confira o caminho final: `references/resposta-crua.md` §2.
- **Vazou só depois que uma assinante abriu a página.** Cache: `references/resposta-crua.md` §5.
- **A listagem não mostra o texto, e a resposta traz.** A consulta seleciona o registro inteiro:
  `references/onde-vaza.md` §1.
- **O teste acusa vazamento que não existe.** Marcador repetido no título ou no resumo, ou termo
  de busca ecoado na página: `references/marcadores-e-personas.md` §2.
- **O arquivo pago abre por um link de ontem.** Endereço público, ou link assinado longo:
  `references/camadas.md` §4.

## Skills irmãs

`ponta-a-ponta-com-personas` (ainda por sair) monta as personas em detalhe; `app-com-supabase`
cuida das permissões no banco; `nextjs-boas-praticas`, do que pode entrar em cache.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/marcadores-e-personas.md` | formato do marcador, o que plantar, personas, sessão sem tela | passos 2 e 4 |
| `references/resposta-crua.md` | formas de resposta, as quatro provas, a matriz, cache, uso da sonda | passos 3 e 5 |
| `references/camadas.md` | banco por persona, a função única, cinco regras de fronteira, arquivo pago | passo 6 |
| `references/onde-vaza.md` | nove lugares, da pista à causa, conferência por fora, vazou em produção | passos 1 e 7; todo `vazou:` |
| `assets/moldes/dados-de-exemplo.sql` | personas, itens e corpos com marcadores | passo 2 |
| `assets/moldes/personas.ts` | contas, sessões por persona, trava de ambiente | passo 4 |
| `assets/moldes/vazamento.spec.ts` | o teste de vazamento em Playwright | passo 5 |
| `assets/moldes/banco-por-persona.sql` | varredura do banco por persona e autopromoção | passo 6 |
| `assets/moldes/fronteira.test.ts` | cinco regras lidas do código-fonte, em Vitest | passo 6 |
| `scripts/sonda.py` | busca marcadores na resposta crua de cada rota; só GET; `--help` | passos 3 e 7 |
