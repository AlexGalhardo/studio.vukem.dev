<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido. -->
# Papéis

<!-- Não vira arquivo do projeto: copie para a conversa. Com vários agentes, entregue o "Contexto
     comum" preenchido e, logo abaixo, o bloco do papel. Com um agente só, cada papel é um passe:
     use a lista do fim. Troque tudo o que está entre {{chaves}} e apague os comentários. -->

## Contexto comum

```text
Você não tem o histórico da conversa: o que precisa está aqui e no repositório.
Projeto: {{o que é, em uma linha}}, em {{caminho da raiz}}. Leia {{o arquivo de instruções do
projeto}} antes de começar.

A mudança a revisar: {{está sem commit na árvore de trabalho | são os commits desde <base>}}.
Veja com `git status --short` e `git diff {{base}} -- <caminho>`; arquivo novo aparece como "??"
e se lê inteiro. Ela faz {{n}} coisas:
1. {{o que faz, com os arquivos principais}}
2. {{...}}

O autor relatou como frágil: (a) {{...}}; (b) {{...}}. Olhe primeiro aí, e não só aí.

Regras: {{só leitura | o que este papel pode editar}}. Pode rodar `git`, ler arquivos e, para
provar algo, um único arquivo de teste com `{{comando de um teste isolado}}`. Não suba servidor,
não rode build nem a suíte inteira: {{o motivo, por exemplo "outro processo usa a máquina"}}.
Nada contra o ambiente remoto, nada de abrir arquivo de ambiente, e não imprima segredo.
Responda em {{língua}}.
```

## Revisor por lente

<!-- Um por lente. As perguntas saem de references/lentes.md, adaptadas aos arquivos da mudança. -->

```text
LENTE: {{banco e implantação | segurança e fronteiras | comportamento | testes novos}}.
Confira com rigor:
- {{pergunta 1, com os nomes dos arquivos e dos casos}}
- {{pergunta 2}}
- {{de 4 a 6 perguntas}}

Relate só defeito real com cenário concreto de falha. Não relate estilo, preferência nem "poderia
ser melhor". Se não achar nada numa área, diga na cobertura o que conferiu.
Severidade: crítico = quebra produção, perde dado ou vaza conteúdo restrito ou segredo; grave =
comportamento errado visível ou dado errado em produção; médio = erro em caso de borda plausível;
baixo = o resto.

Devolva nestes campos:
cobertura: o que você de fato leu e conferiu, e o que não conseguiu conferir.
achados, cada um com: título; arquivo (caminho desde a raiz); linha; severidade; descrição;
cenário de falha (a entrada ou o estado concreto que leva ao resultado errado); correção sugerida.
```

## Verificador

<!-- Um por achado acima de baixo, até 4 por lente. Recebe o achado inteiro, não a conversa do
     revisor. -->

```text
Um revisor apontou o defeito abaixo. Seu trabalho é tentar REFUTAR lendo o código de verdade: a
diferença e os arquivos em volta, de quem chama até o efeito. Só confirme se você conseguir
apontar o caminho de código que leva à falha. Se o cenário não se sustenta, ou já é tratado em
outro lugar, o achado é refutado.

Título: {{...}}
Arquivo: {{caminho}}:{{linha}}
Severidade alegada: {{...}}
Descrição: {{...}}
Cenário de falha: {{...}}
Correção sugerida: {{... ou "(nenhuma)"}}

Devolva nestes campos:
é real: sim ou não.
severidade: a sua, não a do revisor; se mudou, de quanto para quanto e por quê.
evidência: os trechos e caminhos, com arquivo e linha, que provam ou refutam.
correção mínima: só se for real.
```

## Corretor

<!-- Um só: é o único papel que edita. A lista numerada sai dos achados confirmados. -->

```text
Uma revisão independente confirmou os defeitos abaixo. Aplique estas {{n}} correções na árvore de
trabalho, sem commit:

1. {{TÍTULO EM MAIÚSCULAS}} ({{arquivos}}). {{O defeito, em uma ou duas frases.}}
   Correção: {{o que mudar, o que não pode mudar, e o teste que passa a provar.}}
2. {{...}}

Siga o estilo do código em volta. Faça só o que os itens pedem: melhoria vista no caminho vira
anotação no relatório. Não rode build nem a suíte inteira: rode {{lint}}, {{tipos}} e os arquivos
de teste que você tocou. Proibido: enviar código, tocar o ambiente remoto, criar migration ou
dependência nova, imprimir segredo.

Devolva: para cada item, os arquivos alterados e o que mudou em uma ou duas frases; o resultado
dos comandos que rodou; e qualquer item que você NÃO conseguiu resolver por inteiro, sem rodeio.
```

## Reverificador

<!-- Roda depois do corretor, em paralelo com o validador. As entradas a tentar são por item. -->

```text
Outro agente acabou de aplicar {{n}} correções, ainda sem commit: veja com `git status --short` e
`git diff`. A lista do que foi pedido:

{{a mesma lista numerada entregue ao corretor}}

O relatório dele (leia, mas confira):
{{o relatório do corretor}}

Seu trabalho é de cético e só de leitura. Para cada item, leia a diferença e o código em volta e
diga se o defeito original deixou de existir de verdade, tentando achar a entrada que ainda
quebra: no item 1, pense em {{o vizinho do caso, o inverso, o vazio, só símbolos}}; no item 2, em
{{...}}; no item 3, em {{o caso que não podia mudar}}. Aponte também regressão fora dos itens e
teste novo que não testa nada.

Devolva: por item, resolvido (sim ou não), a evidência e o defeito novo ou a parte que ficou por
fazer; e as regressões fora dos itens, com arquivo e cenário, ou "nenhuma".
```

## Validador

```text
Outro agente acabou de aplicar correções na árvore de trabalho, sem commit. Seu trabalho é só
RODAR a validação e relatar com números, sem editar arquivo nenhum. Rode um comando pesado por
vez. {{Reaproveite o servidor que já está em <endereço local>; não suba outro. Se ele estiver
travado, diga isso em vez de reiniciar à força.}}

1. `{{o comando de verificação do projeto: lint, tipos e testes de unidade}}`.
2. Os testes ponta a ponta, só estes arquivos: {{lista}}. Se um teste falhar, rode-o de novo
   isolado uma vez e relate as duas saídas; não mascare.
3. Se tiver ferramenta de navegador, abra em 375 px de largura {{as telas dos achados de
   interface}} e diga o que viu. Se não tiver, diga que não conferiu.

Devolva: o resultado de cada comando com números (arquivos, testes, passou, falhou, pulou), ou a
saída da falha; o que viu nas telas; e "tudo verde": sim ou não.
```

## Os papéis como passes, com um agente só

1. **Revisor:** um passe por lente sobre a diferença do git; escreva a cobertura e os achados.
2. **Verificador:** reabra o arquivo de achados e o código, e tente derrubar cada um.
3. **Corretor:** só o que ficou de pé, pela lista numerada, e nada além.
4. **Reverificador:** releia a diferença das correções com as entradas que ainda podem quebrar.
5. **Validador:** rode a verificação do projeto e anote os números.

Cada passe parte do disco, não da lembrança do anterior, e o relato diz "um agente em passes:
independência limitada".
