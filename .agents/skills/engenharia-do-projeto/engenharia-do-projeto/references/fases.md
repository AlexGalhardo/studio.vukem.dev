# Fases: como cortar o trabalho em entregas e dizer o que é pronto?

Leia quando: situação A, passo 5; passo 2 do ciclo; começo e fim de fase; o plano mudou no meio; o
roteiro vai servir a outra sessão.
Não é aqui: a fase no peso pesado (`references/fase-grande.md`).

## O mínimo

- Uma fase termina em algo que o dono abre e confere, inclusive as de fundação. Fase que só
  termina em código não dá a ele onde parar para corrigir o rumo.
- Escreva o "Pronto quando" na voz do dono, com o caminho de erro e um teste nomeado.
- Fundação (base, dados) vem antes de tela, e o plano dela é mostrado antes de implementar.
- Corte de escopo só com fase de destino; sem destino, é item do estado.
- Uma fase em andamento por vez, com o título na forma que o diagnóstico lê (§7).
- Fim de fase: escada inteira, revisão, estado, relato, e parar (§9).

Conteúdo: 1. Cortar e ordenar 2. "Pronto quando" 3. Plano de uma página e pacotes 4. Regras de
trabalho 5. Autonomia graduada 6. Pendências com fase-alvo 7. O roteiro como passagem de bastão
8. Nota datada e errata 9. Fim de fase e portão entre fases

## 1. Cortar e ordenar

1. Liste o que a primeira versão precisa fazer e, à parte, o que fica fora do escopo.
2. Ordene pela dependência. A ordem que generaliza: (0) base: projeto que abre, degraus 0 a 2, CI
   e casca; (1) dados e permissões, com os testes de permissão; (2) o lado que põe conteúdo para
   dentro; (3) o lado que lê; (4) conta e cobrança; (5) qualidade e ida a produção.
3. Escreva cada fase em uma frase e um "Pronto quando" (§2).
4. Se o lançamento for "no ar, ainda sem conteúdo", estado vazio e build com banco vazio são
   requisito desde a primeira fase que tem tela.

Projeto pequeno pode ter três fases: base, o fluxo principal de ponta a ponta, publicar (adaptação,
a conferir: o corte em três não foi praticado). Havendo dado restrito, dados e permissões continuam
sendo fase própria, antes do fluxo.

Quando o pronto de uma fase depende de outra, resolva de propósito e escreva no roteiro:

| Saída | Quando | O que o roteiro diz |
| --- | --- | --- |
| Fatia mínima | O "Pronto quando" da fase N pede algo que só fica completo na N+1 | A fase N entrega a versão mínima, e a N+1 completa |
| Lógica antes da tela | Uma regra será ligada a outra parte na fase seguinte | A regra nasce como módulo puro, com testes; a fase seguinte só liga |
| Andaime de teste | O teste ponta a ponta precisa de sessão, e a tela de login só chega depois | A sessão vem da preparação do teste, e isso não vira rota do aplicativo |

O que o dono abre nas fases de fundação. **Na fase de base:** o projeto no ambiente local, com uma
tela ou um comando que responde. **Na fase de dados:** uma tela mínima, sem acabamento, em que ele
entra com cada conta de teste e confere a matriz de permissões: o que aparece e o que não aparece.
Sem tela nenhuma, leia com ele a saída do teste por persona, uma linha por persona.

## 2. "Pronto quando"

É a casa deste fato. Seis qualidades; um bom "Pronto quando" tem as três primeiras:

1. **Na voz do dono, como ação:** "cadastro um item, publico e o vejo na lista".
2. **Com o caminho de erro:** "um arquivo inválido mostra o erro certo".
3. **Com o que não pode acontecer e o teste nomeado:** "o visitante não recebe o dado restrito, e
   o teste de vazamento prova".
4. **Com número e condição:** "nota N ou mais na medição X, com a lista vazia e com dez itens".
5. **Com o que não pode ter mudado:** "nada do que já existia foi alterado".
6. **No pacote, como comando com a saída esperada ao lado** (§3).

Cinco vícios, e a troca de cada um:

| Vício | Como aparece | Troque por |
| --- | --- | --- |
| Critério vácuo | "A página tem tamanho maior que zero" passa com a página ainda vazia | Checagem de conteúdo: um texto que só existe na página pronta, e a ausência do texto do estado de carregamento |
| Prova por busca de texto | "O erro de leitura lança" provado por uma busca no código | Teste que força o erro em cada leitura |
| Comando que só acerta na primeira vez | "200, depois 404" depende de o endereço nunca ter sido pedido | Identificador aleatório no comando |
| Medido no lugar errado | Número tirado do servidor de desenvolvimento, que só vale no build de produção | Medir no build de produção, e dizer onde mediu |
| Critério preso à data | Marca de "novo" que expira em dias: o teste quebra sem recriar os dados de exemplo | Critério que não depende do dia em que roda |

No roteiro, cada item é uma linha `- [ ]`. Marque `- [x]` só com a prova na mão: o comando rodado
ou a conferência do dono.

## 3. Plano de uma página e pacotes

É a casa do corte em pacotes. No peso médio, copie `assets/modelos/plano-de-fase.md` para
`docs/planos/` e preencha as seis partes: objetivo e "Pronto quando"; decisões, com motivo e plano
B; mapa de arquivos por pacote; aceite por comando; o que não muda; perguntas com decisão padrão
(como redigir: `references/dono.md` §2). Se não couber em uma página, a fase é pesada ou são duas.

- **Pacotes:** de dois a quatro, em ordem fixa, um por vez, na mesma árvore. Em paralelo na mesma
  árvore eles se atropelam; a fase inteira de uma vez não cabe no contexto.
- **Corte por camada de dependência:** dados e domínio (tipos, leituras, regras puras, ações,
  dados de exemplo); peças de base e a primeira tela; as outras telas; provas (ponta a ponta,
  medições); documentos e registros. Sem interface (adaptação, a conferir): esquema e contratos;
  casos de uso; adaptadores e rotas; testes de integração; documentação.
- **Um dono por arquivo:** o mapa lista arquivo, marca (N novo, A alterado, X apagado) e papel.
  Quando outro pacote precisa encostar, a linha diz o mínimo autorizado e quem reescreve depois.
- **Aceite:** o "Pronto quando" é da fase; o aceite é o bloco de comandos do pacote que o prova,
  cada linha com a saída esperada no comentário (`# → 6 passaram, 0 falharam`). Todo pacote
  termina com os degraus 0 a 2 passando.
- **Pacote de provas:** defeito de produto que o teste achar se corrige no arquivo onde mora, e o
  relato diz qual foi. **Pacote de documentos:** nenhum arquivo de código muda, e nenhum documento
  continua dizendo que algo "ainda não existe".

## 4. Regras de trabalho

Cada sessão lê só o artefato que recebeu: regra que mora num lugar só é regra que alguém não leu.
Por isso o bloco de regras da rodada se repete no topo do roteiro, do plano e do contexto de cada
papel. E proibição sem motivo é desobedecida na primeira vez em que parece atrapalhar.

- Liste as proibições da rodada, com os comandos nomeados um a um: nada contra o ambiente remoto;
  sem envio; sem dependência nova; não derrubar o que o dono deixou aberto (use outra porta); não
  desfazer decisão registrada; não mexer em arquivo de outro pacote.
- Escreva a consequência junto: "Não rode o comando de reparo: ele marcaria as migrações como
  aplicadas no ambiente remoto sem que existam, e a ida a produção pularia todas."
- Declare o que já está liberado (as dependências da especificação), para ninguém perguntar à toa.
- Separe regra da rodada de fato do projeto. "Sem envio" vale para esta rodada; nenhum documento
  do repositório diz que "a fase ficou sem envio".

## 5. Autonomia graduada

Nas fases de fundação, mostre um plano curto e espere o ok; nas seguintes, execute e pare no fim
(a lista do que sempre pede pergunta está no `SKILL.md` §5). Fundação é o que mais custa desfazer.

- **Perfil dev:** o plano lista arquivos e decisões.
- **Quem nunca programou:** o plano não lista arquivo. Responde a "o que você vai conseguir abrir,
  que contas vai precisar criar, quanto custa". Custo é o que é de graça, o que é pago e a partir
  de quando; prazo e valor estimado não entram, porque o método não tem base para estimar.
- **A parada no ponto exato:** além da lista geral, escreva a instrução onde ela vale. "Se precisar
  mexer no que já existe, pare e pergunte." "Peça os identificadores ao dono; não crie."

## 6. Pendências com fase-alvo

É a única lista do roteiro, e só guarda corte de escopo com fase de destino. Adiado por prazo, passo
do dono e decisão pendente moram no estado (o que entra em cada lista: `references/dono.md` §6).

- Cada item traz o título, o registro que a originou, como está hoje, o que fazer e em que fase, e
  a armadilha. A forma, com as lacunas, está em `assets/modelos/roteiro.md`.
- Tipos que aparecem: comportamento provisório aceito, a decidir de vez na fase certa; ponta solta
  que outra fase liga (um indicador fixo em "não" até existir a cobrança); o que a referência visual
  mostra e não entra nesta versão ("não faça o botão; escreva o texto sem depender dele").
- Cite o registro, que é estável, e não o nome de um arquivo, que muda de lugar.
- Ao fechar a fase-alvo, o item sai: resolvido, ou movido com outra fase de destino.

## 7. O roteiro como passagem de bastão

A sessão seguinte não tem o histórico. O roteiro (`assets/modelos/roteiro.md`) tem oito partes:

| Parte | O que traz |
| --- | --- |
| Como usar este roteiro | O que precisa estar no ar e onde parar |
| Onde estamos | Uma linha: aponta `docs/ESTADO.md`, a casa do que muda |
| Leia antes de escrever código | Instruções, seções da especificação, títulos do registro, documentação da versão instalada |
| Regras de trabalho | As da rodada (§4) e o fim de fase (§9) |
| Com o dono, uma vez só | Opcional. Contas, repositório remoto, primeiro ambiente remoto: passos numerados, a resposta de cada pergunta da ferramenta já decidida, o que não rodar, e "se o dono adiar, lembre antes da Fase N" |
| Pendências com fase-alvo | A lista do §6 |
| Uma seção por fase | `**Objetivo:**`, `**Entregas:**`, `**Pronto quando:**`. Cada entrega diz o que fazer, onde, a decisão já tomada e a armadilha prevista |
| Quando tiver dúvida | O que é próprio da fase, além das listas do arquivo de instruções |

O diagnóstico lê duas formas: o título `## Fase <n> · <nome> (<situação>)`, com situação `a
fazer`, `em andamento` ou `pronta`, e os itens `- [ ]` e `- [x]` abaixo dele. Fora dessa forma, ele
responde "não reconheci o formato das fases"; com duas fases em andamento, abre item de atenção.

## 8. Nota datada e errata

Quando a decisão chega depois do documento pronto, não reescreva: corrija no topo. Reescrever um
plano longo no meio da execução custa caro e introduz erro. No roteiro, uma nota datada: o que
mudou, o que deixa de valer, o que continua. No plano, a errata. É a casa do bloco:

```markdown
## Errata (prevalece sobre qualquer trecho abaixo)

Onde este bloco e o resto do documento divergirem, vale este bloco.

**E-1 · <a regra nova, em uma frase>.** <Por quê, e de quem é a decisão.> Portanto:
- Em <arquivo ou seção>: <o que passa a valer>.
- No teste <nome>: <o que passa a provar>.
- Consequência aceita: <qual>. A alternativa vai para "Para decidir", no estado.

**E-2 · O pacote <P> está pronto e commitado (<AAAA-MM-DD>): o código dele é a fonte, onde
divergirem.** Divergências conhecidas: <lista>. Não conserte o teste de volta para a seção <x>.
```

Liste cada lugar atingido, inclusive o caso de teste descrito mais abaixo. Quem pega o plano lê a
errata primeiro. A errata corrige o plano; não afrouxa regra inegociável nem desfaz registro.

## 9. Fim de fase e portão entre fases

1. Pare de implementar.
2. Suba a escada inteira (`scripts/escada.py`, sem opção) e mostre o resultado e o que não rodou.
3. Revise a diferença da fase (`references/revisao.md`). Se corrigiu algo, suba a escada de novo.
4. Marque os itens que têm prova e troque a situação no título para `pronta`. Item sem prova: a
   fase não está pronta, ou o item vira pendência com fase-alvo, com o dono sabendo.
5. Atualize `docs/ESTADO.md`: a data, a linha `escada:` e as listas.
6. Entregue o relato de fim de fase, com o roteiro de validação
   (`assets/modelos/mensagens-ao-dono.md` §4), e espere a palavra de liberação. Commit não é envio.

**Portão entre fases:** antes de começar uma fase, confira no estado que o dono validou a anterior.
Se ele dispensar a parada e mandar emendar, anote no estado a dispensa, com a data, e o que deixou
de ser conferido por causa dela.

## O que evitar

- **Um documento diz que o módulo "é da Fase 4" depois de o roteiro puxá-lo para a 3.** A ordem
  mudou num lugar só. Ao mover uma entrega, busque o nome da fase nos documentos, na mesma mudança.
- **A sessão nova refaz o que já estava pronto.** O item foi feito numa fase anterior e continuou
  no roteiro. Marque `- [x]` e escreva "não refazer" na entrega.
- **Errata que não aponta os trechos atingidos.** Quem lê escolhe qual versão seguir. Liste cada
  lugar. Não serve: "onde houver conflito, vale o bom senso".
- **O roteiro manda enviar no fim da fase, e a regra da rodada proíbe envio.** Diga quem faz cada
  coisa, e deixe o envio fora do roteiro: enviar ao ramo que implanta é ir a produção.
- **Nome de tabela e de função no roteiro.** É o que envelhece primeiro. O roteiro diz o quê, o
  porquê e a armadilha; nome de arquivo e de tipo ficam para o plano.

## Pronto quando

- [ ] Toda fase tem título na forma lida pelo diagnóstico, objetivo, entregas e "Pronto quando".
- [ ] Cada "Pronto quando" tem uma ação do dono, um caminho de erro e um teste nomeado.
- [ ] As fases de fundação vêm antes das telas, e o plano delas foi mostrado ao dono.
- [ ] Todo corte de escopo está em "Pendências com fase-alvo", com fase de destino.
- [ ] Só uma fase está `em andamento`.
- [ ] No fim de fase: a linha `escada:` está no estado, a revisão foi feita e o relato, entregue.

Volte ao `SKILL.md`, §4.
