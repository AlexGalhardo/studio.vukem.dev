# Fronteiras: que testes seguram o que não pode acontecer?

Leia quando: passo 3 do ciclo, se existe dado restrito, área restrita, segredo ou regra do tipo
"só X pode Y"; uma funcionalidade cria uma fronteira nova.
Não é aqui: a matriz de permissões e a forma dos marcadores (`references/dados.md`).
**Base:** proposta. `scripts/fronteiras.py` é desenho deste método, sem uso anterior: na prática
vista, o teste de fronteiras era escrito na linguagem do projeto. Plante um violador em cada regra
antes de confiar no verde.

## O mínimo

- Regra de fronteira nova entra no teste na mesma mudança que cria a fronteira. Depois disso
  ninguém lembra que ela existia, e o caminho mais curto a atravessa.
- Antes das regras, prove que a varredura enxerga: verde com zero arquivos lidos é vermelho.
- Todo teste de vazamento tem controle positivo: quem pode recebe o marcador. Sem ele, um teste
  que nunca acha nada fica verde.
- Olhe a resposta crua, não a tela: o dado restrito vaza no que a tela não mostra.
- Confira a área restrita pela resposta crua, sem seguir redirecionamento.

Conteúdo: 1. Quando são obrigatórios 2. Famílias de regra 3. Qual ferramenta 4. Teste que lê o
código 5. Provar que enxerga 6. Teste de vazamento 7. Guarda de área restrita 8. Outras stacks

## 1. Quando são obrigatórios

O **teste de fronteiras** lê o código-fonte e falha com o caminho do arquivo que quebrou a regra,
sem executar o produto: degrau 2. O **teste de vazamento** procura os marcadores na resposta crua,
por persona: degrau 5, ou mais baixo se a stack tem cliente de teste que a devolve sem navegador.

| O produto tem | Entra | Na mudança que cria |
| --- | --- | --- |
| Segredo | regra "o segredo só é lido no módulo dele" | o módulo dos segredos |
| Ação que exige sessão | regra "toda ação começa com a guarda" | o primeiro arquivo de ações |
| Dado restrito | teste de vazamento (§6); regras "só a porta lê" e "nada dele em leitura compartilhada" | o primeiro dado restrito |
| Área restrita | guarda pela resposta crua (§7) | a primeira tela restrita |
| Estado com um escritor só | regra de escritor único | a tabela ou o módulo que escreve |

Havendo dado restrito ou área restrita, o teste de vazamento e a guarda pela resposta crua são do
piso (`SKILL.md` §4): o que eles protegem não aparece em teste de comportamento até vazar. Regra
do arquivo de instruções presa aqui leva o nome do teste em `Verifica:`
(`references/instrucoes.md` §3).

## 2. Onze famílias de regra de fronteira

| Família | Forma geral | Exemplo | Lê como |
| --- | --- | --- | --- |
| Nome restrito | O identificador X só aparece nos arquivos da lista | A tabela do dado restrito só é citada no módulo de leitura por pessoa e na área de administração | texto |
| Import proibido por diretiva | Arquivo marcado com a diretiva D não importa os módulos da lista | Arquivo de leitura compartilhada não importa leitura por pessoa, sessão nem o módulo dos segredos, nem como tipo | sintaxe |
| Import proibido por lado | Código de navegador não importa módulo de servidor | Componente de navegador não importa consultas nem clientes do banco | sintaxe |
| Porta única | A função F só é importada pelo arquivo A | A leitura do dado restrito só é importada por um componente | sintaxe; texto, se o nome é único |
| Seleção única | O campo restrito é selecionado uma vez, num arquivo | O campo é selecionado uma vez e nunca nas ações | texto |
| Primeira instrução | Toda função exportada do arquivo de ações começa com a guarda | A chamada da guarda é a primeira instrução de cada ação | sintaxe |
| Ordem dentro da função | A conferência P vem antes de qualquer chamada ao serviço externo | A conferência de quem pede vem antes da chamada ao serviço de pagamento | sintaxe |
| Escritor único | Só o arquivo W escreve na tabela T | Só o receptor de notificação escreve no espelho da cobrança | sintaxe; texto, se a escrita tem nome próprio |
| Pacote confinado | O pacote K só entra no módulo M | O pacote do serviço de pagamento só é importado num módulo | texto |
| Texto proibido | O texto S não aparece na interface | Preço escrito à mão | texto |
| Peso do que vai ao navegador | Código público de navegador não importa o módulo que carrega a biblioteca pesada | O validador de entrada fica fora do código público | sintaxe |

"Texto": basta procurar o padrão no arquivo. "Sintaxe": depende de import resolvido, de import só
de tipo, da primeira instrução ou da ordem, e pede o analisador sintático da linguagem.

## 3. Qual ferramenta

| | `scripts/fronteiras.py` | Teste na linguagem do projeto |
| --- | --- | --- |
| Lê | o texto de cada arquivo | a árvore sintática de cada arquivo |
| Cobre | nome restrito e texto proibido: o que cabe em "este texto só aparece nestes arquivos" ou "este texto não aparece" | as onze famílias |
| Não entende | import resolvido, import só de tipo, primeira instrução, ordem de chamadas; comentário e texto contam como ocorrência | caminho de import montado em tempo de execução |
| Contra a vacuidade | sanidade antes das regras, `VAZIA` e código 3, já embutidos | quem escreve é o agente (§5) |

Comece por `fronteiras.py` quando a regra é de texto: preencha `[fronteiras]` em `metodo.ini` e
declare a regra. Cada chave está explicada nos comentários de `assets/modelos/metodo.ini`.

```ini
[fronteira.segredo-so-no-modulo-dele]
tipo = nome-restrito
padrao = <o nome da variável do segredo>
permitidos = <o módulo que lê os segredos>
motivo = Lido fora do módulo dele, o segredo chega ao navegador ou à saída de um comando.

[escada]
2.comando = <o comando de testes do projeto> && python3 ferramentas/metodo/fronteiras.py
```

```bash
python3 <skill>/scripts/montar.py <projeto> --com-ferramentas   # → `criado:` por script copiado
python3 ferramentas/metodo/fronteiras.py                    # → `sanidade:` e uma linha por regra
```

- **De onde se chama.** Regra declarada põe `fronteiras.py` no degrau 2, e por isso a cópia vem
  antes. Comando de `[escada]`, passo de CI e o bloco "Como trabalhamos" do arquivo de instruções
  só citam script por `ferramentas/metodo/`: o caminho da skill não existe em outra máquina.
- **`difere:`** na saída de `montar.py --com-ferramentas`: a cópia do projeto é de outra versão
  da skill. Mostre a diferença ao dono, apague a cópia antiga num commit próprio e rode de novo.
  Cópia editada à mão deixa de ser o script que estas fichas descrevem.
- **`VIOLOU regra <nome>: <caminho>:<linha>`** (código 1): corrija o código. Acrescentar o arquivo
  a `permitidos` abre a fronteira: é decisão, e exceção a regra inegociável passa pelo dono.
- **`VAZIA`** (código 3): a regra não protege nada. A pasta está errada, o arquivo permitido mudou
  de nome ou o `exemplo` não casa. Corrija a configuração; baixar `minimo_de_arquivos` não serve.
- **Quando migrar** para o teste na linguagem do projeto: a regra depende de import, de primeira
  instrução ou de ordem, ou um comentário legítimo que cita o nome passa a violar. Apague a seção
  `[fronteira.<nome>]` na mesma mudança, porque regra em dois verificadores diverge. Molde da
  variante web: `assets/variante-web/fronteiras.test.ts`.

## 4. Como escrever o teste que lê o código

1. **Varra uma vez**, num arquivo do executor de unidade. Ande pelas pastas de código, pule os
   arquivos de teste e guarde caminho e texto de cada arquivo em memória.
2. **Prove a varredura antes das regras**, num bloco de sanidade (§5).
3. **Leia imports com o analisador sintático**, não com expressão regular: comentário, quebra de
   linha e import dinâmico escondem um import. Guarde o destino resolvido a partir da raiz e se é
   só de tipo. Import dinâmico e reexportação contam como o módulo inteiro.
4. **Detecte diretiva como linha inteira.** A mesma frase num comentário não conta.
5. **Escreva cada regra como predicado** sobre um arquivo, e a afirmação como "a lista de
   infratores é vazia". A mensagem de falha é a lista de caminhos.
6. **Plante um violador em cada predicado** (§5).
7. **Ponha um controle positivo em cada regra de lista** (§5).
8. **Para "toda ação começa com a guarda":** compare as funções exportadas com a lista de nomes
   escrita no teste (ação nova obriga a editá-lo); exija tantas linhas de exportação quantas
   funções; extraia a primeira instrução pulando parâmetros, tipo de retorno e comentários. Afirme
   que a forma fraca (ler a sessão e devolver erro) não existe no arquivo.
9. **Numere as regras**, cada uma com um nome que é a própria regra. O cabeçalho diz o que conta
   como diretiva e como import e o que fica de fora: caminho de import montado em tempo de
   execução não se lê, e regra de texto vale para o arquivo inteiro, comentário incluído.
10. **Regra nova entra na mudança que cria a fronteira**; no peso pesado, no pacote do arquivo.

## 5. O verificador prova que enxerga

Verificador que lê texto passa por vacuidade quando um caminho muda. São quatro defesas:

| Defesa | Sem ela | No teste que lê o código | No vazamento e na guarda |
| --- | --- | --- | --- |
| Varredura conferida | Pasta errada: zero arquivos lidos, tudo verde | Achou pelo menos N arquivos; um arquivo conhecido está lá; cada pasta contribuiu; nenhum arquivo de teste entrou | Código de resposta, tipo de conteúdo e tamanho mínimo: resposta vazia ou redirecionamento também "não contém" |
| Violador plantado | Não se sabe se a regra pega alguma coisa | Fonte de mentira, em memória, que quebra a regra de cada forma conhecida, e uma parecida que não quebra | O marcador do dado livre, que o visitante tem de receber |
| Controle positivo | Arquivo permitido renomeado ou sessão vencida: verde sem proteger nada | "Só W escreve em T" vem com "e W de fato escreve em T"; cada módulo da lista existe | Quem pode recebe os marcadores; a persona é quem diz ser |
| Lista conferida | Item novo fica fora da regra sem ninguém notar | As funções exportadas são as da lista do teste | Os marcadores dos dados de exemplo são os do teste; as páginas da pasta são tantas quantas as rotas da lista |

`fronteiras.py` traz as quatro: `minimo_de_arquivos` e `arquivo_conhecido`; `exemplo`, obrigatório
com `regex = sim`; `VAZIA` quando nenhum arquivo permitido contém o padrão ou quando um padrão de
`permitidos` não casa com arquivo nenhum. No teste escrito à mão, quem as escreve é o agente.

## 6. Teste de vazamento por marcadores

O dado restrito de exemplo se anuncia sozinho: leva um marcador que não existe em nenhum outro
campo (a forma e onde plantar estão em `references/dados.md` §9), e o teste o procura na resposta
crua de cada rota, como cada persona.

1. **Resposta crua.** Requisição direta, sem navegador. De cada rota, peça todas as formas em que
   o servidor responde: a página e o payload de dados que o framework manda junto, se houver.
2. **Prova da resposta.** Código 200, o tipo de conteúdo esperado, tamanho mínimo, a presença do
   elemento de bloqueio e a ausência do elemento de conteúdo.
3. **Prova da persona.** Um elemento que só aquela persona recebe: o botão de sair para quem tem
   sessão, o de entrar para o visitante.
4. **Matriz.** Cada persona sem acesso, por todas as rotas públicas que podem mostrar um item (a
   inicial, as listagens, a página do item e as de outros itens), por cada forma de resposta.
   Afirme que nenhum marcador restrito aparece e, onde nenhum deveria aparecer, que o **prefixo
   inteiro** não aparece: é o que pega o marcador que a lista ainda não conhece.
5. **Controles positivos.** Quem tem acesso recebe os marcadores, em todas as formas de resposta;
   o visitante recebe o marcador do dado livre.
6. **Cobertura da lista.** Um teste extrai todos os marcadores do arquivo de dados de exemplo e
   exige que sejam os que o teste conhece; outro compara as páginas que existem com a lista de
   rotas. Marcador ou página sem classificar quebra.
7. **Higiene, para todas as personas.** Marcador de rascunho não aparece em rota pública, e nome
   interno (o campo com o caminho de um arquivo privado) não aparece em resposta nenhuma.
8. Rode num tamanho de tela só: a resposta crua não muda com a tela.

**Base:** adaptação. O método foi praticado numa aplicação web com banco relacional; o que está
aqui (dado restrito que não aceita texto) ainda não foi praticado. Confira antes de confiar.

- **Campo com formato** (telefone, documento): procure o valor sentinela, com o mesmo controle
  positivo, e também a forma sem pontuação, se o produto guarda ou devolve o valor assim.
- **Enumeração, ou sim e não:** não há valor único. Afirme que o nome do campo não aparece na
  resposta crua de quem não pode e aparece na de quem pode. Limite: isso prova que o campo não
  saiu com esse nome, não que o valor não foi derivado para outro campo, como um selo.

Para a variante web há o molde `assets/variante-web/vazamento.spec.ts`, com as sessões por
persona de `assets/variante-web/sessoes-de-teste.ts`.

## 7. Guarda de área restrita pela resposta crua

Guarda só na casca visual não impede a página de ser montada: quem não pode recebe código 200 com
a tela inteira na resposta, e o teste que olha a tela ("fui mandado ao login") passa. A técnica é
a do §6, com sinais da tela no lugar dos marcadores.

1. Liste as rotas restritas e os sinais das telas: identificadores de teste, rótulos, títulos.
2. Peça cada rota **sem seguir redirecionamento**, como visitante e como logado sem o papel.
   Nenhum sinal no corpo.
3. Controle positivo: como quem pode, todo sinal aparece em alguma resposta ("sinal ficou velho").
4. Lista conferida: conte os arquivos de página da pasta restrita e exija o tamanho da lista. A
   mensagem diz o conserto: "página nova: acrescente a rota à lista".
5. Comportamento: o visitante vai ao login com o caminho de volta da página que pediu, e não um
   fixo; o logado sem o papel recebe "não encontrado".

## 8. Em outras stacks

| Onde | O que muda |
| --- | --- |
| API sem interface | Os marcadores são procurados no corpo de cada rota, por persona ou por credencial; a guarda se confere pelo código de resposta e pelo corpo |
| Aplicativo móvel | Procure nas respostas da API que o aplicativo consome, não na tela do aparelho |
| Vários clientes no mesmo sistema | Um marcador por cliente nos dados de exemplo, e a matriz "a sessão do cliente A não recebe marcador do cliente B", com o controle positivo de cada um |
| Dado pessoal | Valor sentinela por pessoa, procurado nas respostas das outras pessoas |
| Outra linguagem | Os passos do §4 não mudam; os imports se leem com o analisador sintático que a linguagem traz |
| Regra de lint de import restrito | Cobre as famílias de import proibido. Não cobre primeira instrução, escritor único nem ordem |
| Biblioteca pronta que confere dependência entre módulos | Não foi praticada: confira o que ela lê; os passos 5 a 7 do §4 continuam valendo |

## O que evitar

- **Todas as regras ficam verdes depois de uma reorganização de pastas.** A varredura leu zero
  arquivos, ou o arquivo permitido mudou de nome. Sanidade antes das regras e controle positivo em
  cada lista. Não serve baixar o mínimo de arquivos até passar.
- **O teste de vazamento passa, e o dado restrito está na resposta.** O teste olhou a tela, pulou
  o payload de dados ou as páginas vizinhas (relacionados, listagens, busca), ou recebeu um
  redirecionamento. Resposta crua, todas as formas, todas as rotas públicas, e a prova da resposta.
- **Todo mundo virou visitante, e tudo passa.** A sessão gravada venceu ou o banco foi recriado.
  Prova da persona em cada bloco, e o preparo das sessões rodado de novo.
- **O visitante é mandado ao login, e a página restrita veio inteira na resposta.** A guarda está
  só na casca, e o teste seguiu o redirecionamento e examinou a tela de login. Não siga; ponha a
  guarda em cada página, em cada leitura e em cada ação.

## Pronto quando

- [ ] Cada fronteira criada pela mudança tem regra no teste, na mesma mudança.
- [ ] A sanidade roda antes das regras, e foi vista reprovando com um caminho errado de propósito.
- [ ] Cada regra acusou um violador plantado e tem controle positivo.
- [ ] O teste de vazamento pede a resposta crua de todas as rotas públicas, por persona sem
      acesso, com prova da resposta, prova da persona, controle positivo e lista conferida.
- [ ] Nenhuma rota restrita devolve sinal da tela a quem não pode, sem seguir redirecionamento.
- [ ] Se `fronteiras.py` faz parte de um degrau, o comando aponta para `ferramentas/metodo/`.

Volte ao `SKILL.md`, §4.
