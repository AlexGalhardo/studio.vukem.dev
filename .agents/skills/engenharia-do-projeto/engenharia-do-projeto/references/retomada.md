# Retomada: como chegar numa sessão nova e deixar a próxima pronta para fazer o mesmo?

Leia quando: situação E; início de sessão em projeto que já usa o método; fim de sessão com
mudança; o dono deu uma regra de trabalho.
Não é aqui: projeto com código e sem os documentos (`references/adocao.md`).
**Base:** proposta. A casa única do estado e a pasta `docs/notas/` são desenho deste método, sem
uso anterior: na prática vista, o estado ficava no arquivo de instruções e as notas na memória da
ferramenta. Confira se o estado continua sendo a única casa do que muda.

## O mínimo

- Leia do disco, não da lembrança: arquivo de instruções, estado, roteiro, nessa ordem.
- Reconfira na fonte o que tem data, antes de agir sobre ele.
- Diga onde o projeto está antes da primeira ação.
- "Quanto falta" é contagem que diz o que contou; para prazo não há base.
- Ao sair, substitua o estado; não empilhe.
- Regra de trabalho que o dono deu vai para o arquivo de instruções no mesmo dia.

Conteúdo: 1. Ao chegar 2. "Em que pé estamos, quanto falta" 3. O estado 4. O que guardar para a
sessão seguinte 5. A nota de memória 6. Números com data

## 1. Ao chegar

1. Rode o diagnóstico (`SKILL.md` §1). Ele dá a data do estado, quantos commits de código vieram
   depois dela, a fase atual, a evidência da escada e o que há a enviar.
2. Leia do disco, nesta ordem: o arquivo de instruções, `docs/ESTADO.md`, a fase em andamento no
   roteiro, os títulos do registro de decisões e, se existir, `docs/notas/INDICE.md`. A cópia do
   arquivo de instruções carregada no começo da sessão pode ser anterior ao último commit.
3. Reconfira o que tem data, pela tabela abaixo.
4. Diga ao dono onde o projeto está e o que divergiu, antes de agir (§2).

| O estado diz | Reconfira em | Se divergir |
| --- | --- | --- |
| Ambiente remoto: aplicado até, ainda não aplicado | A lista do que está aplicado, lida do próprio ambiente, só quando a próxima ação depende disso (ler o remoto também tem regra: `references/producao.md`) | Corrija o estado antes de agir, e não aplique nada |
| A linha `escada:` | `escada.py --evidencia`: vale para a árvore atual ou venceu | Vencida: suba de novo antes de dizer que passa |
| Fase em andamento e itens marcados | O roteiro e o `git log` desde a data do estado | Marque item só depois de rodar o que ele pede, ou de o dono conferir |
| O que há a enviar | `git status` e a linha `a enviar:` do diagnóstico | Diga ao dono o que está commitado e não foi enviado |
| Autorizações e passos do dono | A conversa de hoje: pergunte se algo mudou | Atualize a lista; autorização antiga não se presume |

Se outra sessão escreve no mesmo ramo (branch), rode `git fetch` e compare antes de numerar um
registro ou de enviar: dois lados criam o mesmo número sem saber.

## 2. "Em que pé estamos, quanto falta"

Responda em tópicos, com contagem; o texto da mensagem está em
`assets/modelos/mensagens-ao-dono.md` §3. `situacao.py --completo` dá os itens marcados sobre o
total de cada fase e a contagem de cada lista do estado.

- **Conte fases e itens de "Pronto quando", e diga o que contou:** "2 fases prontas de 5; na fase
  atual, 3 de 7 itens". Fase que ainda não tem itens escritos é dita como não contada.
- **Porcentagem só junto da conta que a produziu:** "3 de 7 itens, 43%". Solta, ela parece medida
  de trabalho, e os itens não têm o mesmo tamanho.
- **Sem estimativa de prazo.** O método conta o que está provado, não mede velocidade, e parte do
  que falta depende de decisão e de passo do dono. Se ele pedir uma data, diga isso e mostre a
  contagem e a lista do que depende dele.
- **Separe o que foi reconferido hoje do que foi só lido do estado**, com "Rodei e vi" e "Inferi".

## 3. O estado

`docs/ESTADO.md` é a casa única do que muda. O arquivo de instruções traz só a regra e o ponteiro;
o leia-me e os documentos por assunto apontam. Quem lê é o dono: linguagem comum, falando com ele.

| Seção | O que mora ali |
| --- | --- |
| `## Estado em AAAA-MM-DD` | A data, que o diagnóstico lê, e uma frase: onde o projeto está e o que vem a seguir |
| Ambientes | O ambiente local e o ambiente remoto, este com "aplicado até" e "**Ainda não aplicado:**" |
| Verificações automáticas: última rodada | A linha `escada:`, colada inteira, e a contagem por degrau copiada da saída |
| As cinco listas | Para decidir, Passos do dono, Autorizações não dadas, Ficou para depois, Pendência aceita (o que entra em cada uma: `references/dono.md` §6) |
| Como trabalhamos aqui | O perfil do dono, a palavra de liberação, o que não derrubar na máquina, o aviso de que recriar o banco apaga o que ele cadastrou |

Não mora ali: a regra (arquivo de instruções), o porquê (registro de decisões), o plano (roteiro)
e segredo nenhum. O modelo é `assets/modelos/estado.md`; os títulos não mudam.

Como atualizar:

1. **Quando:** no passo 6 de toda mudança que altera o que ele descreve, e logo depois de cada ação
   no ambiente remoto, porque o remoto muda fora do git.
2. **Substitua o bloco inteiro e troque a data.** Parágrafo datado empilhado obriga a sessão
   seguinte a ler pela data. O histórico mora no git e no registro de decisões.
3. **Depois de ação no ambiente remoto,** três coisas: o que foi feito, a pedido de quem e quando;
   o que não saiu como previsto; o que conferir antes da próxima ação.
4. **Enquanto algo só existe no ambiente local,** "Ainda não aplicado" funciona como trava: diz o
   que falta e que o código que depende disso só vai a produção depois.
5. **Cole a linha `escada:` e a contagem por degrau.** É por ela que a sessão seguinte percebe se o
   número de testes caiu. Colar não vence a evidência: o estado fica fora da impressão digital.
6. **Item resolvido sai da lista.** Lista sem item diz "Nada.", para constar que foi olhada.

## 4. O que guardar para a sessão seguinte

O que não está no código nem no git é redescoberto com custo ou adivinhado. São três destinos:

| O que se aprendeu | Vai para | Como |
| --- | --- | --- |
| Regra de trabalho: a que o dono deu e a que nasceu de um erro | Arquivo de instruções, no mesmo dia | A frase do dono entre aspas, com a data. A exceção que o agente deduziu vai rotulada: "Minha leitura: …" |
| O que muda: aplicado, pendente, autorizado, não autorizado, ação barrada, última rodada | `docs/ESTADO.md` | §3 |
| Referência e mania da máquina: onde ficam as coisas, o endereço que o dono usa e o que não é do projeto, o comando que funcionou, o erro de busca já cometido | Nota de memória | §5 |

Decisão não é nenhum dos três: vai ao registro, e os outros citam o número. Segredo não vai a
lugar nenhum.

## 5. A nota de memória

Uma nota por fato, em `docs/notas/<assunto>.md`, a partir de `assets/modelos/nota-de-memoria.md`.

- **Três partes:** o fato, com data inteira e quem disse; o porquê, de preferência o incidente que
  gerou a nota; como aplicar, com o que fazer, o que não fazer e o comando.
- **O índice:** `docs/notas/INDICE.md`, uma linha por nota, com o gancho que diz quando abrir. Ao
  chegar, leia o índice; a nota inteira, só quando o gancho importa para o pedido.
- **Curta:** nota de até 30 linhas é lida inteira. A que cresce virou diário: parta por assunto.
- **Adendo datado** quando o fato muda, e releia o topo: se ficou falso, reescreva a nota.
- **O que foi conferido rodando** leva "(conferido)"; o resto é expectativa, e a nota diz.
- **Em repositório compartilhado,** identificador, endereço interno e dado pessoal se escrevem pelo
  papel ("o endereço que o dono usa", "o ambiente remoto antigo"), não pelo valor. O arquivo é
  versionado e pode ser copiado ou virar público.
- **A memória da ferramenta é complemento.** Onde ela existe, guarda o identificador e o endereço
  que não devem ir ao repositório, e as preferências do dono; segredo, nem lá. O que outra sessão
  precisa para retomar mora no repositório, porque nem toda sessão tem a mesma memória.

## 6. Números com data

- **Número que o sistema conta não se escreve à mão em documento permanente.** "São cinco tabelas",
  no leia-me, fica falso na sexta. Escreva o comando que conta.
- **Onde o número entra:** no relato e no estado, copiado da saída, com a data da rodada.
- **Data inteira,** `AAAA-MM-DD`. "Ontem" e "na quinta" não sobrevivem à sessão.
- **Contagem que caiu** de uma rodada para a outra é achado: diga antes de seguir.

## O que evitar

- **O estado virou diário.** Parágrafos de três datas, e o de cima diz que falta o que o de baixo
  já fez. Substitua o bloco a cada atualização. Não serve: acrescentar mais um parágrafo datado.
- **Agir sobre a cópia carregada no começo da sessão.** Ela dizia "ainda não aplicado", e o disco
  já dizia o contrário. Releia do disco e reconfira na fonte antes de qualquer ação que dependa.
- **O mesmo estado em três documentos.** Instruções, leia-me e documento de dados envelhecem em
  ritmos diferentes e passam a se contradizer. Uma casa; os outros apontam.
- **Identificador real ou e-mail numa nota versionada.** Não é segredo, mas chega perto. Escreva o
  papel, e diga onde o valor mora.

## Pronto quando

- [ ] Ao chegar: instruções, estado e roteiro foram lidos do disco, e o que tem data foi
      reconferido ou dito como não reconferido.
- [ ] O dono ouviu onde o projeto está antes da primeira ação.
- [ ] "Quanto falta" saiu como contagem, dizendo o que contou.
- [ ] Ao sair: o estado tem a data de hoje, o bloco foi substituído e a linha `escada:` é a da
      última rodada.
- [ ] Regra de trabalho nova está no arquivo de instruções; referência nova tem nota e linha no
      índice.

Volte ao `SKILL.md`, §1.
