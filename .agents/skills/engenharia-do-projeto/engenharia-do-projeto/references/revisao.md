# Revisão: como achar o que nenhum teste pergunta, sem inventar achado?

Leia quando: passo 5 do ciclo; fim de fase.
Não é aqui: o que muda ao revisar o plano de uma fase pesada (`references/fase-grande.md` §3).
**Base:** proposta. A revisão em passes por um agente só (§6) é desenho deste método, sem uso
anterior: na prática vista, cada lente e a conferência eram agentes separados, e com um agente só
a revisão era cortada. Diga "independência limitada" no relato.

## O mínimo

- Parta da diferença do git, não da lembrança do que se quis fazer: quem escreveu relê a intenção.
- Faça uma lente por passada. Duas ao mesmo tempo viram uma olhada geral.
- Escreva todos os achados antes de corrigir qualquer um: corrigir no caminho apaga o que havia.
- Tente refutar cada achado rodando, não lembrando. O que não se sustenta sai, com o motivo.
- Corrija só o que os achados pedem, em até duas rodadas. O que sobrar vai para o relato.
- Depois de corrigir, suba a escada de novo: correção também quebra.

Conteúdo: 1. O que a revisão procura 2. Lentes 3. O achado 4. Conferir antes de corrigir 5. Corrigir
6. Com um agente só 7. Com vários agentes ou outra conversa 8. O que ela não pode fazer, e o relato

## 1. O que a revisão procura que nenhum teste pergunta

Teste responde só ao que alguém pensou em perguntar. A revisão lê a mudança atrás do resto:

| Procure | Como aparece |
| --- | --- |
| Teste que não prova | Passa com a regra trocada, com a página vazia ou para toda persona, inclusive a que devia ser barrada |
| Garantia escrita que o código não cumpre | O documento diz que só um módulo lê a chave, e outro também lê; a guarda está na moldura da área restrita, e cada página responde a quem pede direto |
| Regra inegociável sem verificador automático | A regra cujo nível, na tabela de verificadores, é a revisão manual: é aqui que ela é conferida |
| Caminho que ninguém percorreu | A persona sem permissão, a entrada vazia, o erro do serviço externo, a segunda execução |

Não é achado: gosto pessoal; o que o plano ou um registro de decisões (ADR) manda de propósito; o
que pertence a um pacote ou a uma fase posterior.

## 2. Escolher as lentes, por tipo de mudança

| Lente | A pergunta | Use quando a mudança toca |
| --- | --- | --- |
| Segurança e fronteiras | Quem não devia consegue ler, escrever ou entrar? A guarda é a primeira instrução? O dado restrito sai por outro caminho: cache, resposta crua, arquivo? | acesso, dado restrito, segredos, cobrança |
| Banco e implantação | A migração só acrescenta e roda do zero? O que acontece entre o banco novo e o código novo? O que não tem volta? | dados; tudo o que vai a produção com banco ou carga |
| Comportamento público | O que o visitante anônimo e cada persona recebem? Há carregando, vazio e erro? O caminho de erro foi percorrido? | rota, tela, leitura compartilhada |
| Fidelidade à referência | A tela bate com o briefing visual, nos dois tamanhos de tela? | fase de telas ou redesenho |

Quantas lentes cada peso pede está em `references/pesos.md` §4. No fim de fase, a prática vista
usou duas: segurança e a comparação das telas com as referências. Custo, desempenho, privacidade e
operação também servem de lente (adaptação, a conferir: não há prática vista com elas).

## 3. O achado

Cinco campos, sempre os mesmos: **severidade**; **arquivo e linha** (ou o comando, quando o achado
é de execução); **título**, que é o comportamento errado em uma frase; **evidência**, o trecho ou a
saída, conferida antes de escrever; **correção proposta**, com o teste que passa a provar.

| Severidade | Quer dizer | Abre a segunda rodada |
| --- | --- | --- |
| **bloqueante** | quebra ou vaza | sim |
| **alta** | comportamento errado ou contrato violado | sim |
| **média** | frágil; teste que não prova; regra do projeto violada | sim |
| **baixa** | limpeza | não |

Identifique cada achado pela lente e por um número (`S-01`, `B-01`): o mesmo problema visto por
duas lentes conta uma vez. O formato em branco é o de `assets/modelos/achados.md`.

## 4. Conferir antes de corrigir

Achado é alegação até ser conferido na fonte: o arquivo aberto agora, o comando rodado, a resposta
crua do ambiente local como a persona, a documentação da versão instalada. Tente derrubar cada um.

| Decisão | Quando | Escreva |
| --- | --- | --- |
| **aceito** | a conferência reproduziu o problema | como foi conferido |
| **aceito em parte** | só uma parte se sustenta | a parte que ficou de fora e por quê; sem isso, parece aceito inteiro |
| **refutado** | não se reproduz, ou é escolha de plano, de especificação ou de registro | o motivo, em uma linha |

Rebaixe a severidade só quando a conferência mostrar alcance menor que o escrito, e diga de quanto
para quanto: rebaixar para escapar da segunda rodada esconde o achado. Decisão por achado:

```text
<id> · <severidade> · <arquivo>:<linha> · <título>
Conferi: <o que abri ou rodei, e o que saiu>. Decisão: <aceito | em parte | refutado>, <motivo>.
Severidade: <mantida | rebaixada de <a> para <b>, porque <o que a conferência mostrou>>.
```

## 5. Corrigir em até duas rodadas

1. Corrija cada achado aceito, do mais grave ao mais leve, inclusive o teste que não provava, e
   nada além disso: melhoria vista no caminho vira achado de severidade baixa. As correções saem
   num commit próprio, que lista os achados (`references/fechar.md` §2).
2. Suba a escada de novo (`python3 <skill>/scripts/escada.py --exigido`).
3. Rodada 2, só com achado acima de baixa: reveja a diferença das correções e diga de cada achado
   se foi resolvido, não foi ou originou achado novo. É a última: sem teto, o laço não termina.
4. O que sobrar vai para o relato e, com data, para o estado. Achado novo causado pela correção
   entra no relato como regressão: contar só os resolvidos esconde que a revisão quebrou algo.

## 6. Com um agente só

Quem revisa é quem escreveu. A separação possível é de momento e de fonte: cada passe parte do
disco, e não da lembrança do passe anterior.

1. **Ler por lente,** um passe para cada uma, sobre a diferença: `git status --short` e `git diff
   HEAD` na mudança em curso; `git diff <commit de base>...HEAD` no fim de fase. Arquivo novo só
   aparece no primeiro comando, e se lê inteiro.
2. **Escrever todos os achados,** no formato da §3. No peso leve, cabem no relato. No médio, no
   pesado e no fim de fase, grave a partir de `assets/modelos/achados.md`, em `docs/planos/`.
3. **Conferir,** tentando refutar (§4), a partir do arquivo de achados e do código no disco.
4. **Corrigir, subir a escada e conferir as correções** (§5).

No relato, escreva "revisão em passes por quem escreveu: independência limitada". Em zona
sensível, se o orçamento permitir, proponha ao dono a revisão em outra conversa (§7).

## 7. Com vários agentes ou outra conversa

O contexto comum e o texto de cada papel estão em `assets/modelos/papeis.md`. O que muda:

- **Cada lente é um agente,** ou uma conversa nova, que recebe o contexto comum e o papel de
  revisor por lente, sem o histórico. É a falta do histórico que dá a independência.
- **O conferente não escreveu o código nem o achado,** e o corretor não confere a própria correção.
  Só assim "independência limitada" sai do relato, que passa a dizer quantos agentes e que lentes.
- **Revisores só leem.** Podem rodar um arquivo de teste isolado, requisições ao ambiente local e
  consultas de leitura. A escada, só um papel sobe, em sequência.
- **Relatório de agente é alegação.** Todo papel recebe "leia, mas confira", e quem coordena confere
  de novo os pontos que importam. A revisão também erra.

## 8. O que a revisão não pode fazer, e o relato

A revisão propõe: não afrouxa regra inegociável nem desfaz decisão registrada (`SKILL.md` §6).

- **A correção contraria um registro ou uma regra:** o achado é aceito e não é corrigido. Abra o
  item em "Para decidir" (as quatro partes dele estão em `references/dono.md` §5) e conte o achado
  como "com o dono". A regra vale até o dono responder.
- **A correção pede mudança fora do combinado** (uma migração a mais, uma dependência nova): vira
  pergunta ao dono, com as opções, e não entra na rodada.

O relato traz contagem, não adjetivo (ao dono: `assets/modelos/mensagens-ao-dono.md` §4):

```text
Revisão: <n> lentes (<quais>); <em passes por quem escreveu: independência limitada | <n> agentes>.
Achados: <n>. Aceitos <n> (<n> em parte), refutados <n>, com o dono <n>. Por severidade: <…>.
Rodada 2: <n> achados, <n> deles regressão da correção. Ficou aberto: <achado, e onde está anotado>.
```

## O que evitar

- **Cada passada devolve os achados num formato.** Sem os cinco campos fixos, juntar as lentes vira
  trabalho, e achado repetido conta duas vezes. Use o modelo desde a primeira passada.
- **Achado escrito de lembrança, sem arquivo e linha.** Não dá para conferir nem para refutar. Abra
  o arquivo ou rode o comando antes de escrever: sem evidência, não é achado.
- **A revisão foi cortada, e o relato não disse.** A mudança seguiu como se tivesse sido revista.
  Diga em "Não rodei", abra item datado em "Ficou para depois" e, em zona sensível, diga o corte
  na lista antes de ir a produção.

## Pronto quando

- [ ] A revisão partiu da diferença do git, e cada lente teve a sua passada.
- [ ] Todo achado tem os cinco campos e uma decisão, com a parte recusada ou o motivo.
- [ ] Nenhuma correção contrariou registro ou regra: o que contrariava está em "Para decidir".
- [ ] Depois da última correção, a escada subiu de novo até o degrau exigido.
- [ ] O relato traz a contagem, as regressões e, com um agente só, "independência limitada".

Volte ao `SKILL.md`, §4.
