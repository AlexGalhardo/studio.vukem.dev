# Entrevista: o que perguntar ao dono antes de escrever a especificação?

Leia quando: situação A, antes de qualquer código (para a primeira resposta bastam "O mínimo" e as
seções 1 e 2). Funcionalidade grande pedida por quem nunca programou (só a §7).
Não é aqui: como escrever a especificação e a mensagem de aprovação
(`references/especificacao.md`).
**Base:** proposta. O roteiro de perguntas é desenho deste método, sem uso anterior: ajuste ao que
o dono responder.

## O mínimo

- Não escreva código, não crie arquivo e não escolha ferramenta: a escolha depende do que o produto
  precisa, e isso ainda não está escrito.
- Leia o que há na pasta e o que o dono anexou antes de perguntar.
- Faça até cinco perguntas por rodada, em linguagem comum, cada uma com o padrão que será adotado.
- Pare na segunda rodada. O que faltar entra na especificação como "Decidi sem perguntar", para o
  dono corrigir ao aprovar.
- Não abra parada só para "confirmar o que entendi": ela é a mesma do resumo da especificação, e
  duas paradas seguidas cansam quem ainda não viu nada pronto.

Conteúdo: 1. Antes de perguntar 2. Rodada 1: o produto 3. Rodada 2: condições e sinais de alerta
4. Quando parar 5. Da resposta à especificação 6. Perfil dev 7. Funcionalidade nova

## 1. Antes de perguntar

1. **Leia a pasta e o material:** anotação, planilha, captura de tela, conversa colada. Fora de uma
   pasta de projeto, leia só o que o dono anexou: a pasta pessoal dele não é material. O que já
   está respondido não vira pergunta. Nada se roda nem se cria nesta resposta (`SKILL.md` §1).
2. **Não pergunte o que é escolha do agente:** linguagem, framework, banco, hospedagem, aplicativo
   de loja ou navegador. Quem nunca programou responde com um chute, e o projeto herda o chute.
   Essas escolhas vêm depois da especificação aprovada, cada uma com registro.
3. **Abra a primeira resposta com até quatro linhas sobre como o trabalho anda:** perguntas agora;
   um documento curto que o dono aprova; fases que ele abre e confere. Diga o que fica com ele
   (criar contas, o que custa dinheiro, a ida a produção) e que as escolhas técnicas serão do
   agente, declaradas depois. A régua de tom é o trecho 1 de `assets/exemplo/conversa.md`.
4. **Não peça chave, senha nem conta:** nada disso é preciso antes da fase de base.

## 2. Rodada 1: o produto

Escreva cada pergunta com as palavras do negócio do dono e troque o padrão pelo caso dele (a forma
está em `references/dono.md` §2). A quarta leva um caso concreto ("o entregador vê o endereço de
todos os clientes ou só o da entrega dele?"): em abstrato, "quem pode ver o quê" não tem resposta.

| Pergunta | Por que importa | Padrão se o dono não souber |
| --- | --- | --- |
| Quem usa, e o que cada tipo de pessoa leva embora ao terminar? | Vira as personas e o parágrafo que abre a especificação | As pessoas que a ideia já cita, mais o visitante sem conta e alguém que administra |
| Qual é o caminho principal, do começo ao fim? | Vira o primeiro fluxo e a primeira fase que o dono abre | O caminho mais curto que entrega o que a pessoa veio buscar |
| O que é de graça e o que é pago? | A regra de negócio vira regra de segurança: o que é pago é dado restrito | Nada é cobrado na primeira versão; a cobrança entra em fase própria |
| O que cada tipo de pessoa pode ver e fazer? | Vira a matriz de permissões, que vem antes de qualquer tela | O mais fechado que ainda deixa o trabalho andar: cada um vê e altera só o que é seu |
| O que não pode acontecer de jeito nenhum? | Vira propriedade negativa, com teste, no "Pronto quando" | O que as duas respostas anteriores implicam: ninguém vê o que é de outro nem usa o pago sem pagar |

Persona de borda que aparecer (em teste, cancelou, deixou de pagar) ganha linha própria na matriz.

## 3. Rodada 2: as condições e os sinais de alerta

Até cinco perguntas, tiradas desta lista e do que a rodada 1 deixou em aberto:

| Pergunta | Padrão se o dono não souber |
| --- | --- |
| Há data marcada? Quanto dá para gastar por mês com serviços? | Sem data; custo zero para começar, e todo custo é perguntado antes |
| O que já existe: contas, domínio, sistema anterior, planilha, lista de clientes? | Nada; o que existir é lido antes de qualquer proposta |
| Já usa ou conhece algo pronto que quase resolve? O que falta nele? | Não conhece |
| Onde as pessoas vão usar: celular, computador, os dois? | Celular primeiro |
| O que fica de fora da primeira versão? | Tudo o que não está no caminho principal, em lista para ele cortar ou devolver |

Se uma ferramenta pronta resolve, diga isso antes de construir: construir mesmo assim é decisão do
dono, e ele só decide se souber. Cada sinal de alerta presente nas respostas ganha a pergunta e o
aviso do que muda, dito pelo efeito ("pagamento pede mais verificação a cada mudança"):

| Sinal | A pergunta | O que muda |
| --- | --- | --- |
| Dinheiro | O sistema recebe ou repassa pagamento? De quem? | Pagamento vira zona sensível, e a conta no serviço de pagamento só o dono cria |
| Dado pessoal | Que dado de pessoa fica guardado, e quem precisa ver? | É dado restrito na matriz desde o primeiro desenho |
| Menores | Há criança ou adolescente entre quem usa ou nos dados? | Dado de criança é dado restrito na matriz e pede orientação de especialista, que este método não dá |
| Saúde | Fica guardada alguma informação de saúde? | O mesmo: dado restrito na matriz, e especialista |
| Conteúdo enviado por quem usa o produto | As pessoas enviam foto, texto ou arquivo? Quem vê o que foi enviado? | Cada tipo de envio ganha linha na matriz e limite com número |
| Vários clientes no mesmo sistema | Cada cliente tem os próprios dados, sem ver os de outro? | "Um cliente nunca vê o de outro" entra no que não pode acontecer, com teste |

## 4. Quando parar de perguntar

- **A segunda rodada é a última.** Uma terceira adia o primeiro documento que o dono consegue ler,
  e ele julga melhor pelo que lê pronto do que por pergunta.
- **"Não sei" não é pendência.** Adote o padrão da tabela e diga, na mesma resposta, qual adotou.
- **Resposta que contradiz outra** se resolve pelo lado mais fechado e abre "Decidi sem perguntar".
- **Vira "Decidi sem perguntar":** cada padrão adotado e cada detalhe que o dono não citou e a
  especificação exige (limites, textos, estados), com a decisão, o motivo e como desfazer.
- **Não vira padrão:** o que custa dinheiro, conta em serviço, preço e texto legal. Vai para
  "Preciso de você", porque é das caixas do dono (`SKILL.md` §5).
- **A devolução do que se entendeu** é o resumo da especificação (`references/especificacao.md` §6).

## 5. Da resposta à especificação

| Resposta | Seção da especificação que ela preenche |
| --- | --- |
| Quem usa e o que leva embora | 1, e as personas da matriz, na 5 |
| Caminho principal | 6, e a primeira fase com tela, na 8 |
| De graça e pago | 1 (o que é pago e por quê, em uma frase) e a matriz, na 5 |
| Quem pode ver e fazer o quê | 5 (matriz de permissões) |
| O que não pode acontecer | 6, no ponto do fluxo em que a regra morde |
| Data e dinheiro; onde as pessoas usam | 1 (as condições desta versão) |
| O que já existe | 4 |
| Algo pronto que quase resolve; material de que o dono gosta | 2 |
| O que fica de fora | 9 |
| Sinais de alerta | 5 (o que é dado restrito) e 11 (o que pede pergunta) |

As seções 3, 7 e 10, e o desenho dos dados na 5, são proposta do agente: não viram pergunta.

## 6. O que encurta no perfil dev

- A explicação de como o trabalho anda vira uma linha.
- As duas rodadas podem ser uma, se o pedido já respondeu metade, e a pergunta pode pedir o
  artefato direto (esquema, contrato da API, documento que ele já tenha).
- Stack que ele já escolheu entra como restrição, com o dono como quem decidiu no registro.
- Não encurta: quem pode ver e fazer o quê, o que não pode acontecer, os sinais de alerta e o que
  fica com ele. O perfil muda a explicação, não o método.

## 7. Entrevista curta para funcionalidade nova

Uma rodada, três perguntas, cada uma com o padrão. Sinal de alerta novo traz a pergunta dele, da
§3, como quarta. Com as respostas, siga para o passo 2 do ciclo (`SKILL.md` §4).

1. **Quem usa isto, e o que consegue fazer ao terminar?** Vira o "Pronto quando" na voz do dono.
   Padrão: a persona que hoje faz a ação mais próxima.
2. **Quem não pode ver nem fazer isto?** Vira linha nova na matriz e a propriedade negativa.
   Padrão: todos os outros.
3. **O que não pode mudar no que já existe?** Padrão: nada do que hoje funciona muda.

## O que evitar

- **Pergunta em jargão.** O dono não lê, ou responde "pode ser". Diga o que a pessoa vai ver ou
  conseguir fazer. Explicar o jargão num parágrafo não resolve: troque a pergunta.
- **Padrão que afrouxa o que não pode acontecer.** Na dúvida sobre quem vê o quê, o padrão é o mais
  fechado: abrir depois é uma linha na matriz, e fechar depois de vazar não desfaz o vazamento.
- **Persona de borda esquecida.** Quem cancelou ou está em teste acaba tratado como pagante, ou
  como ninguém. Liste-as na rodada 1 e dê a cada uma a sua linha.
- **Detalhar cedo o que depois é cortado.** O desenho de uma funcionalidade que não entra deixa
  sobras nos dados. Pergunte o que fica de fora antes de detalhar, e registre a sobra se ela ficar.

## Pronto quando

- [ ] Nenhum código, nenhum arquivo e nenhuma ferramenta escolhida antes da especificação.
- [ ] No máximo duas rodadas, cada uma com até cinco perguntas, todas com padrão.
- [ ] Há resposta ou padrão declarado para as cinco perguntas da rodada 1 e para o que fica de fora.
- [ ] Cada sinal de alerta presente foi dito ao dono, com o que muda.
- [ ] O dono sabe o que fica com ele: contas, o que custa dinheiro, a ida a produção.

Volte ao `SKILL.md`, §3.
