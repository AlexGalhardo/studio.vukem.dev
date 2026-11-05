# Verificação: como separar o defeito real do achado que só parece?

Leia quando: houver achados escritos (passos 3, 4 e 5 do fluxo).
Não é aqui: as perguntas (`references/lentes.md`) e o relato ao dono (`references/relato.md`).

## O mínimo

- Achado é alegação até uma segunda leitura tentar derrubá-lo. Quem verifica não escreveu o
  achado e, com vários agentes, não leu a conversa do revisor.
- Refutar é seguir o caminho de código de verdade: da entrada do cenário até a falha. Sem caminho,
  não fica.
- Rebaixe a severidade dizendo de quanto para quanto e o que a leitura mostrou.
- Corrija o mínimo, só o confirmado; confira a correção contra o achado original, procurando a
  entrada que ainda quebra; e rode a verificação do projeto: correção também quebra.

Conteúdo: 1. O achado 2. Refutar 3. O veredito e a severidade 4. Corrigir 5. Reverificar
6. Validar rodando 7. Quantas rodadas

## 1. O achado

Seis campos, no formato de `assets/modelos/achado.md`: **título** (o comportamento errado em uma
frase), **arquivo e linha**, **severidade**, **descrição**, **cenário de falha** e **correção
sugerida**. O cenário é a entrada ou o estado concreto que leva ao resultado errado: "rótulo
`C++` depois de `C#`: os dois viram o endereço `c` e o segundo reaproveita o primeiro em
silêncio". "Pode dar problema com caracteres especiais" não é cenário.

| Severidade | Quer dizer |
| --- | --- |
| **crítico** | quebra produção, perde dado ou vaza conteúdo restrito ou segredo |
| **grave** | comportamento errado visível, ou dado errado em produção, no caminho comum |
| **médio** | erro em caso de borda plausível |
| **baixo** | o resto que ainda tem cenário: borda improvável ou efeito pequeno |

Identifique pela lente e por um número: `B-01` banco, `S-01` segurança, `C-01` comportamento,
`T-01` testes. O mesmo defeito visto por duas lentes conta uma vez, com as duas letras.

## 2. Refutar

Verifique todo achado acima de baixo, do mais grave ao menos, até 4 por lente. O que passar do
limite e os baixos seguem como "não verificado", nunca como confirmado. O limite de 4 é o da
revisão de origem; mude-o se o orçamento permitir e diga o número no relato.

O verificador recebe o achado inteiro e faz, nesta ordem:

1. **Abre o arquivo na linha citada.** O trecho existe e diz o que o achado diz? Achado escrito
   de lembrança cai aqui.
2. **Sobe até quem chama.** O cenário chega a esse trecho? Uma validação, uma guarda ou um valor
   padrão no caminho pode impedir a entrada do cenário.
3. **Desce até o efeito.** O resultado errado acontece, ou é tratado adiante: um erro capturado,
   um estado vazio, uma restrição do banco?
4. **Procura a mesma regra em outro lugar.** Um teste, uma política do banco ou uma camada
   anterior que já cobre o caso.
5. **Prova barata, se existir:** um arquivo de teste isolado ou uma consulta de leitura no
   ambiente local. Nunca a suíte inteira, nunca o ambiente remoto.

Só confirma quem aponta o caminho, com arquivo e linha de cada passo. "Parece plausível" é
refutado por falta de caminho.

## 3. O veredito e a severidade

| Veredito | Quando | Escreva |
| --- | --- | --- |
| **confirmado** | o caminho até a falha foi apontado | o caminho, e a correção mínima |
| **confirmado em parte** | só uma parte do cenário se sustenta | a parte que caiu e por quê |
| **refutado** | o cenário não chega à falha, ou já é tratado | o trecho que impede, com arquivo e linha |
| **não verificado** | baixo, ou além do limite | "segue sem verificação", no relato |

A severidade do veredito é a do verificador, não a do revisor:

- **Rebaixe** quando o caminho existe e o alcance é menor: entrada improvável, efeito só visual,
  há como desfazer. Escreva "de médio para baixo: só com dois rótulos que diferem por símbolo".
- **Não rebaixe para encerrar a revisão.** Sem motivo que caiba em uma frase, a severidade fica.
- **Suba** quando a leitura mostrar alcance maior que o escrito. A verificação não tem lado.

Na revisão de origem, nenhum achado ficou crítico ou grave, 2 médios foram confirmados e vários
alegados como médios terminaram baixos. A lista só vale depois da segunda leitura.

## 4. Corrigir

1. **Só o confirmado**, do mais grave ao mais leve. O confirmado como baixo entra por último, e
   vai ao relato se a correção passar de 10 linhas. O não verificado não é corrigido às cegas.
2. **A menor mudança que fecha o cenário**, com o teste que passa a prová-lo ao lado. Melhoria
   vista no caminho vira anotação, não mudança: ela não foi revisada.
3. **Numere as correções** e escreva cada uma como instrução: o defeito, os arquivos, a correção
   e o que não pode mudar ("os outros tipos ficam como estão"). É essa lista que o reverificador
   recebe.
4. **Sem commit e sem envio.** A correção fica na árvore de trabalho até a validação passar; o
   commit e a subida são do dono, ou do que ele combinou.
5. **O que não se corrige aqui:** o que contraria decisão registrada ou regra do projeto, e o que
   pede migration nova, dependência nova ou mudança de regra do produto. Vira pergunta ao dono,
   com as opções. Às vezes a correção certa é de documentação: uma ordem de subida escrita.

O corretor devolve, por item: os arquivos alterados, o que mudou em uma ou duas frases, o
resultado dos comandos que rodou e o que **não** conseguiu resolver por inteiro, sem rodeio.

## 5. Reverificar

Uma leitura cética, só de leitura, recebe a lista numerada e o relatório do corretor (que é
alegação) e lê a diferença das correções. Para cada item, três perguntas:

| Pergunta | Como procurar |
| --- | --- |
| O defeito original deixou de existir? | refaça o caminho do cenário original no código novo |
| Que entrada ainda quebra? | o vizinho do caso original, o inverso, o vazio, só símbolos, o mesmo valor com outra caixa, a ordem trocada |
| O que a correção mudou fora do alvo? | o caso que não devia mudar: a tela larga quando o conserto foi no celular, o tipo antigo quando o conserto foi no novo |

Escreva as entradas a tentar no texto do reverificador, por item: sem elas a leitura devolve
"parece certo". Ela aponta também **regressão fora dos itens**, com arquivo e cenário, e **teste
novo que não testa nada**. Cada item sai como resolvido ou não resolvido, com evidência.

## 6. Validar rodando

Um papel só roda os comandos, sem editar arquivo, e relata com números:

1. A verificação do projeto: formatação e lint, tipos, testes de unidade. O que o arquivo de
   instruções do projeto manda rodar antes de enviar.
2. Os testes ponta a ponta só dos arquivos que a mudança e as correções tocam.
3. Se houver ferramenta de navegador, as telas dos achados de interface em 375 px de largura.
   Se não houver, "não conferi".

- **Um comando pesado por vez.** Dois juntos numa máquina pequena falham por falta de memória e
  parecem defeito.
- **Encadeie com `&&`, nunca com `;`.** Com `;`, o passo seguinte roda mesmo com o teste falhando.
- **Teste que falhou roda de novo isolado, uma vez,** e as duas saídas vão para o relato:
  "passou na segunda" é um dado, não um verde.
- **Números:** quantos arquivos e testes; quantos passaram, falharam e foram pulados.
- **O que travou se relata.** Não reinicie à força o servidor de desenvolvimento do dono.

## 7. Quantas rodadas

Até 2. A rodada 2 corrige só o que a reverificação deixou como não resolvido ou apontou como
regressão, e passa de novo por reverificar e validar. O que sobrar vai ao relato como aberto,
com a evidência: sem teto, o laço não termina.

## O que evitar

- **Corrigir enquanto revisa.** A correção apaga a evidência, e o achado seguinte, no mesmo
  arquivo, não chega a ser escrito.
- **O mesmo agente conferir o próprio achado ou a própria correção sem dizer.** Com um agente só
  é o que há: diga "independência limitada" no relato.

## Pronto quando

- [ ] Cada achado acima de baixo tem veredito, com arquivo e linha, até o limite por lente.
- [ ] Todo rebaixamento diz de quanto para quanto e por quê.
- [ ] A diferença das correções toca só o que os achados confirmados pedem.
- [ ] Cada correção foi conferida contra o achado original, com as entradas tentadas escritas.
- [ ] A verificação do projeto rodou depois da última correção, com números.

Volte ao `SKILL.md`, passo 6.
