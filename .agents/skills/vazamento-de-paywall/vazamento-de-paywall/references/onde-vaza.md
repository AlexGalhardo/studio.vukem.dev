# Onde vaza, e como conferir por fora depois de publicar?

Leia quando: a sonda ou o teste acusou um marcador e é preciso achar a causa; for montar a lista
de rotas (passo 1 do fluxo); ou o site acabou de ser publicado (passo 7).
Não é aqui: escrever o teste (`references/resposta-crua.md`).

## O mínimo

- O texto pago quase nunca vaza na página do item: vaza numa cópia dos dados que ninguém olha.
- Cada lugar da tabela abaixo vira uma rota na lista do teste ou uma regra de fronteira.
- Em produção não há marcador: a conferência por fora usa trechos do conteúdo de verdade.
- Fora do endereço local, a sonda só roda no site do próprio dono, com o aval dele.
- O que já saiu não volta: conserte, expire o cache e avise o dono com a data e a rota.

Conteúdo: 1. Os nove lugares 2. Da pista à causa 3. Conferência por fora 4. Se vazou em produção

## 1. Os nove lugares

**Base:** os quatro primeiros foram praticados no sistema de origem. Os outros cinco são
adaptação: confira no seu produto antes de confiar.

| Lugar | Como vaza | Como o teste pega | Conserto |
| --- | --- | --- | --- |
| Escondido na tela | o texto vai inteiro e um estilo o borra, ou o JavaScript corta em 200 caracteres | resposta crua da página | cortar no servidor; a prévia é um campo público à parte |
| Payload de hidratação | o servidor passa o registro inteiro a um componente de navegador, que mostra só o título | resposta crua, na forma página e na forma payload | o componente de navegador recebe só os campos que mostra |
| Cache compartilhado | a resposta montada para a assinante é guardada e servida a todos | assinante pede antes, visitante depois; regra de fronteira 3 | leitura por pessoa fora de toda função com cache |
| Registro inteiro na resposta | a listagem ou a API seleciona todas as colunas, e o corpo vem junto | listagens, relacionados e cada endereço de API na lista de rotas | corpo em tabela própria; lista de colunas escrita |
| Mensagem de erro | o erro devolve a linha que falhou, ou o rastro com os dados | a sonda varre o corpo de respostas 4xx e 5xx; peça a rota com parâmetro inválido | erro genérico para fora, detalhe só no registro do servidor |
| Mapa de código-fonte | o conteúdo pago mora em arquivo do repositório e entra no pacote JavaScript | acrescente às rotas os arquivos `.js` e `.js.map` que a página carrega | conteúdo pago fora do pacote; lido no servidor, por pessoa |
| Pré-visualização de link | a descrição da página, a imagem de compartilhamento ou o dado estruturado saem do corpo | resposta crua; a pista da sonda diz "em atributo de <meta>" | descrição escrita à parte, nunca os primeiros caracteres do corpo |
| Feed e mapa do site | o feed publica o texto completo de cada item | o endereço do feed na lista de rotas | feed só com título, resumo e endereço |
| Busca | o índice inclui o corpo, e o resultado mostra um trecho | busque pela ponta `INICIO` e procure a ponta `FIM` na resposta | índice só com campos públicos |

Dois cuidados com a tabela:

- **Página para robô de busca.** Se o site entrega o texto completo a robôs para ser indexado,
  qualquer pessoa que se apresente como robô o recebe. Teste com
  `--cabecalho "User-Agent: <o do robô>"`. Manter ou não é decisão do dono.
- **Busca ecoa o termo.** A página de resultados repete o que foi buscado. Por isso se busca por
  uma ponta e se procura a outra: achar a própria ponta buscada não prova nada.

## 2. Da pista à causa

| A sonda disse | Olhe primeiro |
| --- | --- |
| `dentro de <script>` | o que o componente de servidor passa ao componente de navegador naquela página |
| `em atributo de <meta>` | a função que monta título, descrição e dados de compartilhamento |
| `no texto da resposta`, tipo de página | um elemento escondido por estilo: procure o marcador no HTML e suba até o elemento |
| `no texto da resposta`, tipo JSON ou payload | a consulta por trás daquele endereço: quais colunas ela seleciona |
| vazou só na segunda execução | cache: alguém com acesso pediu a página entre uma e outra |
| vazou em listagem e não na página do item | a consulta da listagem traz o registro inteiro |
| só uma das pontas apareceu | prévia cortada (`INICIO`) ou trecho citado (`FIM`): o corte está no lugar errado |

Depois de consertar, rode o teste inteiro, não só a rota que acusou: o mesmo registro costuma
sair por mais de uma porta.

## 3. Conferência por fora

Os dados de exemplo não vão a produção, então lá não há marcador. O que se confere é o site
publicado, como visitante, com o que qualquer pessoa tem: o endereço e a chave pública.

1. **Peça o aval do dono**, com o endereço exato. A sonda recusa host que não é local sem
   `--site-proprio <host>`, só faz GET e espera pelo menos 1 segundo entre requisições.
2. **Monte os trechos-isca.** De 2 ou 3 itens pagos de verdade, uma frase de 20 caracteres ou
   mais que só exista no corpo: nem no título, nem no resumo. Uma frase do começo e uma do fim,
   sem aspas, apóstrofo, `&` nem `<`: o HTML e o JSON trocam esses caracteres, e a busca é por
   texto exato. Ponha em um arquivo fora do repositório, uma por linha. O controle é uma frase de
   um item livre.
3. **Rode como visitante:**

   ```bash
   python3 <skill>/scripts/sonda.py --base https://<host> --site-proprio <host> \
     --rotas-de rotas.txt --marcadores-de trechos.txt --controle "<frase do item livre>"
   ```

   Repita com o cabeçalho do payload. Saída 3 não é aprovação: veja cada `não conferi`.
4. **Confira o cache.** O dono abre um item pago como assinante, no navegador dele. Rode a sonda
   de novo como visitante.
5. **Chame o banco com a chave pública.** Se o produto usa um banco com interface na web, peça a
   tabela do conteúdo pago direto, sem sessão. O esperado é lista vazia ou erro de permissão.
   Numa interface no estilo PostgREST, por exemplo:

   ```bash
   curl -s "https://<projeto>/rest/v1/<tabela do conteúdo>?select=*&limit=5" -H "apikey: <chave pública>"
   # esperado: []  ou um erro de permissão. Linha com corpo pago: pare e avise o dono.
   ```

   Só a chave pública, a que já vai no JavaScript do site. A chave de serviço nunca entra aqui.
6. **Peça um arquivo pago pelo endereço público** do repositório de arquivos: 4xx.
7. **Registre** a data, o endereço, as rotas e a saída de cada passo.

Como outra persona, em produção: o dono exporta `SONDA_COOKIE` no terminal dele, com o cookie de
uma conta de teste sem plano. O valor não passa pela conversa, e a sonda recusa cookie fora do
local por `http`.

## 4. Se vazou em produção

1. Diga ao dono na hora: qual item, qual rota, qual persona, desde quando se sabe.
2. Conserte a causa e publique. Esconder o sintoma na tela não é conserto.
3. Expire o cache da rota e confira de novo por fora, duas vezes.
4. Transforme o caso em teste: a rota entra na lista, e a regra de fronteira que faltava entra
   no teste de fronteira, na mesma mudança.
5. O que foi exposto continua exposto em cópias e em caches de terceiros. Trocar ou não o
   conteúdo é decisão do dono.

## O que evitar

- **Rodar a sonda no site de outra pessoa.** A trava existe para lembrar: é para o próprio site.
- **Usar a frase do título como trecho-isca.** Aparece para todos, e a sonda acusa o que é público.
- **Tratar saída 3 como "passou".** Rota que redirecionou ou deu erro não foi conferida.
- **Conferir uma vez só.** Vazamento por cache depende de quem pediu a página antes.
- **Colar cookie ou chave na conversa.** Variável de ambiente, no terminal do dono.
