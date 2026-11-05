<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Decisões (ADR)

Registro das decisões de stack, arquitetura, configuração e produto. Uma decisão por registro.

- **Só se acrescenta.** Registro novo entra acima do molde do fim; registro antigo não se reescreve.
- **O título é a própria decisão**, em forma de afirmação. O número ordena; a data informa.
- **Rever é escrever um registro novo**, que diz o que faz ao antigo com um dos sete verbos:
  substitui, atualiza, corrige, revê, fecha, complementa ou fica.
- **Pergunte ao dono antes de desfazer** uma decisão registrada. No resto, decida e registre aqui.

## ADR-XXX · <título que é a própria decisão>

**Data:** <AAAA-MM-DD>
**Decidiu:** <agente | dono | dono, contra a recomendação>
**Contexto:** <a tensão: o que puxava para cada lado>
**Decisão:** <o que se faz, dito de modo que se ache no código>
**Consequências:** <o que fica mais caro; o que quebra se alguém desfizer; para que lado falha>

<!--
O bloco ADR-XXX acima é o molde. Fica sempre por último: registro novo entra logo acima dele, com
o próximo número, em três dígitos, sem reaproveitar nenhum. Este comentário fica junto do molde.

Nas Consequências, duas linhas não podem faltar: a regra para o próximo arquivo ou o custo; e
"rever quando", como condição que se observa (ou "não há gatilho previsto").

Rever um registro antigo: escreva um registro novo e, no antigo, faça só isto.
  - Revisto em parte: logo abaixo da linha "Decidiu", acrescente  **Revisto por:** ADR-NNN
  - Substituído por inteiro: essa mesma linha, e o título ganha o sufixo  (substituída pelo ADR-NNN)
O texto original fica intacto nos dois casos.

Blocos opcionais: só estes dois, porque são permanentes.
  - Ordem de produção, em bloco próprio depois das Consequências: os passos numerados, cada um
    com o porquê (o que quebra se a ordem inverter).
  - Limite aceito, como linha dentro das Consequências: o que esta decisão não resolve.

Não entra em registro: "Ficou para depois", "Para decidir", "Passos do dono", pendência conhecida
e o que está aplicado em cada ambiente. São listas abertas e estado: moram em docs/ESTADO.md, e o
item de lá cita o número do registro.
-->
