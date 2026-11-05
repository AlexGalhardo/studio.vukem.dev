# Resposta crua: como escrever o teste que vê o que a tela esconde?

Leia quando: for escrever ou revisar o teste de vazamento (passos 3 e 5 do fluxo), ou quando o
teste passar e o texto pago estiver no código-fonte da página.
Não é aqui: os marcadores e as sessões (`references/marcadores-e-personas.md`).

## O mínimo

- O teste pede a rota por requisição direta, sem navegador, e lê o corpo como texto.
- De cada rota ele pede todas as formas em que o servidor responde: a página e o payload de dados.
- Antes de afirmar "não contém", prova a resposta: código 200, caminho final, tipo e tamanho.
- Cada bloco sem acesso prova a persona; quem paga recebe os marcadores (controle positivo).
- A lista de marcadores do teste é conferida contra o arquivo de dados de exemplo.

Conteúdo: 1. O que é resposta crua 2. As quatro provas 3. A matriz 4. Rascunho e nomes internos
5. Cache 6. Como rodar 7. A sonda

## 1. O que é resposta crua

É o texto que o servidor mandou, antes de o navegador executar qualquer coisa. O conteúdo pago
pode estar ali sem aparecer na tela: num bloco de dados para o navegador montar a página, num
elemento escondido por estilo, num texto que o JavaScript corta depois.

Quase todo framework manda os dados duas vezes: embutidos na página e, na navegação interna, por
um pedido à parte. O teste precisa das duas formas.

| Onde | Embutido na página | Pedido à parte |
| --- | --- | --- |
| Next.js, roteador de aplicativo | blocos de `<script>` dentro do HTML | a mesma rota com o cabeçalho `RSC: 1`; tipo `text/x-component` |
| Outros frameworks com renderização no servidor | um `<script>` com o estado inicial | um endereço de dados por rota: a conferir na documentação do framework |
| Página montada no navegador sobre uma API | nada | o JSON de cada endereço da API que a página chama |
| Aplicativo móvel | nada | as respostas da API que o aplicativo consome |

Só a primeira linha foi praticada (Next.js 16). Nela, o pedido com o cabeçalho é redirecionado
para o mesmo caminho com um parâmetro a mais: por isso o molde segue o redirecionamento e confere
que o caminho final é o pedido. Para achar o pedido à parte de outro framework, abra a aba de
rede do navegador, navegue de uma página a outra por um link interno e copie a requisição.

## 2. As quatro provas

Um teste que procura uma coisa e não acha passa por muitos motivos errados. Cada prova fecha um.

| Prova | Como | Sem ela, o teste passa quando |
| --- | --- | --- |
| Da resposta | código 200, caminho final igual ao pedido, tipo de conteúdo esperado, mais de 1.000 caracteres, o elemento de bloqueio presente e o de conteúdo ausente | a rota deu erro, mandou ao login ou devolveu uma casca vazia |
| Da persona | um elemento que só ela recebe está na resposta, e o da outra não está | a sessão venceu e todo mundo virou visitante |
| Controle positivo | a assinante e o admin recebem as duas pontas, em toda forma; o visitante recebe as do item livre | a busca está cega: rota errada, marcador que não existe nos dados |
| Lista conferida | um teste extrai os marcadores do arquivo de dados de exemplo e exige o mesmo conjunto que o teste conhece | alguém acrescentou um item pago e não o classificou |

## 3. A matriz

Personas sem acesso × rotas públicas × formas de resposta. No molde
(`assets/moldes/vazamento.spec.ts`), 2 personas × 5 rotas × 2 formas dão 20 testes, mais os
controles.

- **Rotas:** toda rota pública que pode mostrar um item. A inicial, cada listagem, a busca, o
  feed, a página do item pago e as páginas dos **outros** itens: "relacionados" e "veja também"
  carregam o registro do vizinho.
- **O que não pode aparecer:** cada marcador pago conhecido e a classe inteira (`PAGO-INICIO-`,
  `PAGO-FIM-`, `RASCUNHO-INICIO-`, `RASCUNHO-FIM-`). A classe pega o item que a lista ainda não
  conhece.
- **Mensagem de falha:** marcador, rota, forma e persona. É o que diz onde consertar.
- **Rota nova:** entra na lista na mesma mudança. Um teste que conta os arquivos de página da
  pasta pública e compara com o tamanho da lista evita o esquecimento (não está no molde).

A busca por requisição direta, usada no molde:

```ts
const r = await request.get(rota, { headers: cabecalhos }); // `request` já leva a sessão do bloco
const corpo = await r.text();                                // texto cru: nada foi executado
const caminho = new URL(r.url()).pathname;                   // depois de redirecionar, onde parou
```

## 4. Rascunho e nomes internos

Para **todas** as personas, inclusive quem paga:

- Nenhum marcador de rascunho em rota pública. Rascunho é do painel de admin.
- Nenhum nome interno em resposta nenhuma: a coluna que guarda o caminho do arquivo pago e o nome
  do repositório privado de arquivos. Com os dois, quem tem um link antigo monta o endereço.

## 5. Cache

**Base:** adaptação. No sistema de origem a garantia é a regra de fronteira do cache
(`references/camadas.md` §3); o teste abaixo foi escrito para esta skill e não rodou lá.

O vazamento por cache só aparece depois que alguém com acesso pediu a página: a resposta montada
para a assinante é guardada e servida ao visitante. O último teste do molde pede como assinante,
confere que o cabeçalho `Cache-Control` da resposta não tem `public` nem `s-maxage`, e pede de
novo como visitante. Rode contra o build de produção: o servidor de desenvolvimento não guarda
cache do mesmo jeito.

## 6. Como rodar

| Regra | Por quê |
| --- | --- |
| Contra o build de produção, em porta própria | é o que vai ao ar, com cache e payload de verdade |
| Em um tamanho de tela só | a resposta crua não muda com a tela |
| Depois do passo de preparo das sessões | sessão gravada vence e não sobrevive a recriar o banco |
| A cada mudança que toca rota pública, leitura ou cache | vazamento novo nasce numa página vizinha, não na do item |

## 7. A sonda

`scripts/sonda.py` faz a mesma busca sem executor de teste: serve para a primeira leitura, para
reproduzir um vazamento e para a conferência por fora.

```bash
grep -oE '(PAGO|RASCUNHO)-(INICIO|FIM)-[A-Z0-9]{6}' banco/dados-de-exemplo.sql | sort -u > marcadores.txt
python3 <skill>/scripts/sonda.py --base http://localhost:3000 --rotas-de rotas.txt \
  --marcadores-de marcadores.txt --controle LIVRE-INICIO-AXWPYX
# de novo, pedindo o payload; e como logado sem plano, com a sessão que o preparo gravou
python3 <skill>/scripts/sonda.py ... --cabecalho "RSC: 1"
SONDA_COOKIE="$(python3 -c "import json,sys; print('; '.join(c['name']+'='+c['value'] \
  for c in json.load(open(sys.argv[1]))['cookies']))" ponta-a-ponta/.sessoes/logado.json)" \
  python3 <skill>/scripts/sonda.py ...
```

| Linha da saída | Quer dizer |
| --- | --- |
| `vazou: <rota> contém <marcador> (...)` | o texto está na resposta; a pista diz se é dado embutido, atributo ou texto |
| `limpo: <rota>` | 200, tamanho mínimo e nenhum marcador procurado |
| `não conferi: <rota> ...` | erro, redirecionamento, resposta curta ou compactação desconhecida: não é "limpo" |
| `controle: ... apareceu` | a busca enxerga |

Saída 0 nada vazou; 1 vazou; 2 uso errado; 3 nada vazou, mas algo não foi conferido. A sonda faz
uma requisição por rota (mais uma, se a rota redireciona para ela mesma com um parâmetro), não
segue outro redirecionamento e também varre o corpo de respostas de erro.

## O que evitar

- **Abrir o navegador e procurar o texto na tela.** A tela é o que sobrou depois de esconder.
- **Pedir só a página.** O payload é uma segunda cópia dos dados, com outra chance de vazar.
- **Afirmar "não contém" sem provar a resposta.** A tela de login também não contém.
- **Testar só a página do item pago.** Em listagem e em relacionados o registro vem inteiro.
- **Baixar o tamanho mínimo até passar.** Resposta pequena é sinal de que não é a página.
