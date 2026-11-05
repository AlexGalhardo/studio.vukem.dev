# Lentes: o que cada revisor pergunta?

Leia quando: for revisar (passo 2 do fluxo) ou montar o texto de um revisor.
Não é aqui: quais lentes a mudança pede (`references/escopo.md` §4); o que fazer com o achado
(`references/verificacao.md`).

## O mínimo

- Uma lente por leitura. Com duas na cabeça, a leitura vira uma olhada geral e a pergunta
  específica não é feita.
- Leia a diferença e os arquivos em volta. O defeito costuma estar em quem chama o trecho mudado,
  não no trecho.
- Toda lente devolve a cobertura: o que leu, o que conferiu e o que não conseguiu conferir.
  "Nenhum achado" sem cobertura não diz se a lente olhou.
- Adapte as perguntas à mudança, com os nomes dos arquivos. Pergunta genérica recebe resposta
  genérica.

Conteúdo: 1. Como escrever as perguntas 2. Banco e implantação 3. Segurança e fronteiras
4. Comportamento 5. Testes novos 6. Outras lentes 7. O que não é achado

## 1. Como escrever as perguntas

As tabelas abaixo são o ponto de partida. Antes de usar, troque o genérico pelo que a mudança
tem. Em vez de "a entrada é validada?", escreva "a ação que cria a etiqueta: o que acontece com
rótulo que vira endereço vazio, rótulo igual com outra caixa, entrada enorme?". De 4 a 6
perguntas por lente bastam. Feche com: "Confira com rigor."

## 2. Banco e implantação

| Pergunta | O defeito que ela acha |
| --- | --- |
| A migration roda do zero e sobre o banco como está hoje? Rodar duas vezes quebra? | coluna obrigatória sem padrão em tabela com linhas; índice único sobre dado duplicado |
| Função, política ou visão redefinida é a anterior com só a troca pretendida? | a redefinição perdeu a guarda, o dono ou as permissões da versão antiga |
| O que mais no banco ramifica pelo tipo ou valor novo e ficou de fora? | uma função ou política que trata 3 valores e agora existem 4 |
| Código novo no ar antes da migration: que leitura ou escrita falha, e o que o visitante vê? | a página filtra por um valor que o banco ainda não aceita |
| Migration aplicada com o código antigo no ar: algo quebra? | o código antigo insere sem a coluna nova, ou lê uma que sumiu |
| O que acontece com as linhas que já existem? | linha antiga sem o campo novo some da listagem ou quebra a tela |
| O que desta mudança não tem volta? | coluna removida, tipo trocado, dado reescrito |
| Tipos gerados e dados de exemplo batem com a migration? O teste de banco cobre o que mudou? | tipo velho compila e falha rodando |
| A ferramenta de carga: reexecutar muda o quê? A simulação garante zero escrita? A trava de ambiente remoto continua? | reimportar um item publicado cria versão nova ou zera um campo |
| Variável de ambiente nova existe em todo ambiente antes do código subir? | o build passa no local e cai em produção |

A saída desta lente inclui a **ordem de subida**, escrita: banco, depois dados, depois código, ou
o motivo de outra ordem. Na revisão de origem, o erro na ordem de subida planejada só apareceu
aqui: as outras duas lentes leram a mesma mudança e não o apontaram. Para escrever a migration e
a subida, a irmã é `migrations-sem-susto`, se estiver instalada.

## 3. Segurança e fronteiras

| Pergunta | O defeito que ela acha |
| --- | --- |
| Toda ação ou rota nova começa pela guarda, na primeira linha da própria função? | a guarda está só na moldura da área, e a ação responde a quem chama direto |
| A entrada é validada no servidor: tamanho, caracteres, vazio, enorme, duplicada com outra caixa? | rótulo que normaliza para vazio; dois rótulos diferentes que viram a mesma chave |
| O identificador vem da sessão ou do navegador? | uma pessoa age sobre o registro de outra trocando um id |
| O que vai para o navegador: HTML, dados da página, código cliente, mensagem de erro? | o dado restrito sai inteiro e a tela só esconde |
| Leitura em cache compartilhado depende de quem pede? A escrita expira a entrada certa? | a resposta de uma pessoa servida a outra; item novo que não aparece |
| Parâmetro do visitante monta link, redirecionamento ou chave de cache sem conferência? | redirecionamento aberto; cache inflado por valor inventado |
| O segredo é lido em um módulo só, fora do código que vai ao navegador e dos registros? | chave no pacote do cliente ou no log |
| A permissão do banco diz o mesmo que a guarda do aplicativo? | a tela esconde o rascunho, e a interface pública de dados entrega |
| Que regra escrita do projeto esta mudança pode ter quebrado? | a regra sem verificador automático, que só a revisão confere |

Para provar por tipo de usuário que conteúdo pago não vaza, a irmã é `vazamento-de-paywall`.
Esta lente revisa uma mudança; auditar a segurança do sistema inteiro é outro trabalho, de uma
skill de auditoria de segurança, quando existir.

## 4. Comportamento

| Pergunta | O defeito que ela acha |
| --- | --- |
| O parâmetro novo: zero, um, vários valores, valor desconhecido, combinado com os outros filtros, a ordenação e a paginação? | filtro que zera a página 2; valor desconhecido que quebra a tela |
| Cada tela tocada tem carregando, vazio e erro? E quando a categoria nova não tem item nenhum? | produção no primeiro dia é o estado vazio |
| Em 375 px de largura algo se sobrepõe, some da tela ou fica sem alvo de toque de 44 px? | título por baixo de um botão; o item ativo fora da área visível |
| Quem chega por um link direto vê o estado que a URL carrega, e tem como desfazer? | filtro ativo invisível: a lista parece incompleta e não há "limpar" |
| O que mais usa a função, o tipo ou o componente alterado? A ordem ou o resultado de algo antigo mudou? | a regressão no que já existia |
| O caso novo herdou texto ou promessa do caso antigo que não vale para ele? | a página do tipo novo promete o que só o tipo antigo entrega |
| Toda lista paralela ganhou o valor novo: rotas, rótulos, navegação, rodapé, esqueleto de carregamento? | o tipo existe na rota e falta no menu |
| Clique durante a espera, segunda execução, voltar do navegador? | estado antigo preso numa função; a seleção feita na espera se perde |
| Botão e link são de verdade, com foco visível e rótulo? | controle que o teclado não alcança |

Esta lente lê; não abre o navegador. Para percorrer os fluxos rodando, como cada tipo de
usuário, a irmã é `ponta-a-ponta-com-personas`.

## 5. Testes novos

| Pergunta | O defeito que ela acha |
| --- | --- |
| O teste falha se a regra for invertida? | asserção sobre o próprio dublê; teste sem asserção; "não lançou erro" como prova |
| Há espera longa, repetição ou pausa fixa nova? O que oscilava antes dela? | defeito real de corrida escondido por um tempo limite maior |
| Algum teste foi removido, pulado ou restrito a um caso? | a regra perdeu a prova sem ninguém decidir |
| O teste depende da data, da ordem ou do dado deixado por outro teste? | passa hoje e falha amanhã |
| O caso de borda que o código novo trata tem teste? A pessoa barrada é testada? | só o caminho feliz é provado |

A prova custa pouco: inverta a condição no código, rode só aquele arquivo de teste e veja-o
falhar. Desfaça a inversão antes de seguir. Teste que oscilou é achado até a oscilação ter
explicação: "passou na segunda vez" não é explicação.

## 6. Outras lentes

Desempenho, custo, privacidade e fidelidade a uma referência visual também servem de lente. Não
têm prática vista neste método: escreva as perguntas do mesmo jeito (o que mudou, a entrada, o
resultado errado) e diga no relato que a lente é adaptação. Declare-a no script com `--lente`.

## 7. O que não é achado

- Estilo, nome, formatação, preferência e "poderia ser melhor". Sem entrada que leve a resultado
  errado, não entra.
- O que uma decisão registrada do projeto manda de propósito. Discordar da decisão é assunto para
  o dono, fora da lista.
- O que pertence a uma etapa posterior, já combinada.
- Defeito antigo, fora da diferença, que a mudança não piorou. Anote em "deixado de fora de
  propósito": some da lista, não do relato.

## O que evitar

- **Colar as quatro tabelas inteiras no texto do revisor.** Ele responde a todas pela metade.
  Escolha e adapte as que a mudança pede.
- **Aceitar "revisei e está tudo certo".** Sem cobertura, não se sabe se o arquivo novo foi lido.
- **Perguntar só pelo caminho feliz na tela grande.** Os dois defeitos médios confirmados na
  revisão de origem só apareciam no celular ou para quem chegava por um link.

## Pronto quando

- [ ] Cada lente pedida teve a sua leitura, com perguntas que citam os arquivos da mudança.
- [ ] Cada lente devolveu cobertura, com o que não conseguiu conferir.
- [ ] A lente de banco devolveu a ordem de subida, mesmo sem achado.

Volte ao `SKILL.md`, passo 3.
