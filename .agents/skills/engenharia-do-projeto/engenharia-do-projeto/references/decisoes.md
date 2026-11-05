# Registro de decisões (ADR): o que registrar, como escrever e como rever sem apagar

Leia quando: passo 1 do ciclo (só "O mínimo") e passo 6 (registrar); antes de mudar stack ou
configuração; antes de "corrigir" algo que parece erro; uma decisão mudou; documento e código
divergem (só a §5).
Não é aqui: as perguntas de uma decisão de stack (`references/stack.md` §3).
**Base:** proposta. Os campos `**Decidiu:**` e `**Revisto por:**` e a conferência de citação sem
registro são desenho deste método, sem uso anterior: o resto é prática vista.

## O mínimo

- Antes de mexer, rode `python3 <skill>/scripts/decisoes.py titulos` e abra os registros do
  assunto. Os títulos, lidos em lista, são o índice do que já foi decidido.
- Antes de "corrigir" uma construção estranha, procure o número no comentário ao lado: o que
  parece erro pode ser escolha.
- Registre quando a resposta a "alguém desfaria isto por engano?" for sim.
- O título é a própria decisão, em forma de afirmação. O Contexto traz a tensão: o que puxava
  para cada lado e a alternativa descartada.
- As Consequências dizem o que quebra se alguém desfizer e para que lado a decisão falha.
- Não edite registro antigo: escreva um novo e ligue os dois (§5).

Conteúdo: 1. O que merece registro 2. O registro 3. Contexto com tensão 4. Decisão e
Consequências 5. Rever sem apagar, e quem manda 6. Amarrar as pontas 7. Numeração 8. Adaptar

## 1. O que merece registro

O teste é uma pergunta: quem chegar depois, olhando só o código, vai achar que isto é erro,
descuido ou escolha sem motivo, e desfazer? Se sim, registre. É o registro que deixa o agente
decidir sem perguntar e o dono conferir depois, com o motivo e com o que foi descartado.

| Gatilho | Registre quando |
| --- | --- |
| Versão contra a mais nova | existe versão mais nova e ela não foi usada |
| Desvio da especificação | a especificação diz A e o código faz B |
| Lacuna da especificação | ela não diz, e alguém precisou escolher |
| Regra ambígua | há duas leituras, ou a leitura literal quebra outra regra |
| Conflito entre documentos | dois documentos do projeto pedem coisas incompatíveis |
| Adiamento | algo previsto fica para uma fase posterior |
| Valor provisório | um valor foi preenchido sem confirmação do dono |
| Convenção | uma regra que todo arquivo novo precisa seguir |
| Fonte única | o mesmo número ou a mesma regra seria escrito em mais de um lugar |
| Limitação aceita | um comportamento ruim é conhecido e fica |
| Aviso de ferramenta aceito | o lint ou o painel de um serviço vai reclamar, e está certo que reclame |
| Diferença entre ambientes | ambiente local, CI e produção não são iguais |
| Registro errado | um registro anterior afirmava o que não era verdade |
| Resultado de revisão | a revisão achou problema e o desenho mudou |
| Mudança de premissa | um fato de base mudou e derruba várias decisões |
| Fim de fase com corte | a fase fecha em modo enxuto e parte do corte é para ficar: o que saiu de propósito, e por quê |
| Decisão de produto do dono | o dono mudou o que o produto faz |
| Dono contra a recomendação | o agente avisou do risco e o dono manteve |
| Ferramenta que escreve em produção | um script passa a gravar por fora do aplicativo |
| Ordem de ida a produção | a mudança só funciona se for aplicada numa ordem |

Não merece registro: correção de defeito, que é assunto de commit; ajuste da mesma decisão no
mesmo ciclo, que se faz no registro recém-criado (§5); o que a especificação já diz, sem
alternativa descartada; como o sistema funciona hoje, que mora no documento por assunto; estado de
ambiente e lista aberta, que moram em `docs/ESTADO.md` (§4).

## 2. O registro

Crie pelo script, que numera, data e insere o registro acima do molde, com três campos vazios:

```bash
python3 <skill>/scripts/decisoes.py novo "<título>" --decidiu agente   # → o registro, numerado
```

| Linha | O que entra |
| --- | --- |
| `## ADR-NNN · <título>` | A decisão, em forma de afirmação: "Linguagem na versão anterior, não na mais nova"; "Dados de exemplo só no ambiente local". "Sobre o cache" é assunto, não decisão |
| `**Data:**` | O dia do registro, `AAAA-MM-DD`. O número ordena; a data informa |
| `**Decidiu:**` | `agente`, `dono` ou `dono, contra a recomendação` (no script: `agente`, `dono`, `dono-contra`). O último, quando o risco foi dito uma vez, com a alternativa, e ele manteve; o Contexto guarda o aviso dado |
| `**Contexto:**` | A tensão (§3) |
| `**Decisão:**` | O que se faz, dito de modo que se ache no código (§4) |
| `**Consequências:**` | O que passa a custar ou a obrigar (§4) |

- Cada campo começa a linha pelo rótulo em negrito, como acima: `decisoes.py conferir` o procura.
- Uma decisão por registro. O normal fica entre 9 e 20 linhas; acima de 60, quase sempre são
  várias decisões juntas, e ninguém consegue citar uma delas sozinha.
- Registre na mesma mudança, no passo 6, e anote a alternativa descartada na hora em que decidir:
  é o que some primeiro. Se a sessão cai antes, a decisão fica no código sem o porquê.

## 3. Contexto com tensão

O Contexto útil mostra duas forças que não cabem juntas. Seis padrões servem de régua:

1. **Comece pelo que a especificação pede**, com a seção, e mostre por que não dá ao pé da letra.
2. **Nomeie a alternativa descartada.** Sem isso, a sessão seguinte propõe a mesma de novo.
3. **Traga a evidência crua:** o erro literal, o número medido, o trecho da documentação lida.
4. **Diga como se descobriu:** a revisão mostrou, o teste pegou, só apareceu no ambiente remoto.
5. **Registre a palavra do dono** quando ela autoriza ou muda o rumo, e o aviso que ele recebeu.
6. **Amarre para trás:** que registro este fecha, complementa ou revê.

O Contexto não conta a história do projeto, não justifica a tecnologia em abstrato ("é moderna")
e não repete a decisão. Uma frase basta; vazio, não: sem ele não se sabe o que foi descartado.

## 4. Decisão e Consequências

**Decisão**, escrita para alguém abrir o arquivo e conferir:

- Cite arquivo, função, opção de configuração, nome da migração, valor exato.
- Cole o motivo, entre parênteses, na escolha que parece estranha.
- Diga onde a regra é imposta (servidor, banco, build, lint): isso separa conveniência de garantia.
- Diga qual teste trava. Sem teste citado é intenção: escreva "a intenção é", não "garante".
- Decisão composta vira lista. Se contraria uma regra geral, diga que contraria e por que pode.

**Consequências.** Duas linhas não podem faltar:

1. **Regra para o próximo** ou **custo**, pelo menos uma: o que todo arquivo novo deste tipo
   passa a ter de fazer; o que ficou mais caro, mais lento ou mais difícil.
2. **Rever quando**, como condição observável, e o que não fazer até lá. "Rever no futuro" não é
   condição. Sem gatilho, escreva "não há gatilho previsto".

Em decisão de acesso, de dado restrito ou de serviço externo, acrescente **para que lado falha**:
o que acontece quando alguém erra ou a dependência cai. "Se a consulta falhar, nega" é decisão
pensada; o silêncio descreve só o caminho em que tudo dá certo. Entram também o que muda junto
(arquivos que se alteram em par) e a surpresa que vai pegar alguém.

**Mora no registro para sempre**, porque não muda com o tempo:

- **Ordem de produção** de uma decisão, em bloco próprio depois das Consequências: os passos
  numerados e o porquê de cada um, isto é, o que quebra se a ordem inverter.
- **Limite aceito**, como linha dentro de Consequências: o que a decisão não resolve ("fecha a
  listagem, não o acesso de quem conhece o endereço exato").

**Não mora no registro**, porque muda: o que está aplicado em cada ambiente, "Ficou para depois",
"Para decidir", "Passos do dono" e pendência conhecida. Vão para `docs/ESTADO.md`, e o item de lá
cita o número do registro (o que entra em cada lista está em `references/dono.md` §6). O registro
diz "depende do dono para ir ao ambiente remoto"; "foi aplicado em tal data" é do estado.

## 5. Rever sem apagar, e quem manda

Dentro do mesmo ciclo, edite o registro recém-criado: a revisão achou algo, ou o dono pediu mais
um pedaço que não contradiz o resto. Depois que o ciclo fechou (commit feito, dono validou), só
registro novo. O novo diz, nas Consequências, o que faz ao antigo, com um destes sete verbos:

| Verbo | Quer dizer |
| --- | --- |
| **Substitui** | a parte citada deixa de valer |
| **Atualiza** | a premissa mudou; o resto fica |
| **Corrige** | o registro anterior afirmava algo errado, e o novo diz que estava errado |
| **Revê** | muda um ponto de uma decisão composta |
| **Fecha** | resolve um adiamento ou uma pendência |
| **Complementa** | acrescenta sem mudar |
| **Fica** | confirma que o antigo continua valendo depois de uma mudança grande |

Diga qual parte: "Revê o ADR-NNN (a duração)". Quando uma premissa de base cai, diga de cada
registro afetado se foi substituído, atualizado ou se fica, com o motivo: quem lê não precisa
adivinhar o que sobrou de pé. No registro antigo cabem duas edições, e só:

- **Revisto em parte:** uma linha logo abaixo de `**Decidiu:**`, na forma `**Revisto por:**
  ADR-NNN`. Sem ela, quem abre só o antigo lê uma decisão já corrigida e não tem como saber.
- **Substituído por inteiro:** além dessa linha, o título ganha o sufixo ` (substituída pelo
  ADR-NNN)`. O texto original fica intacto, e o registro novo diz o que dele ainda é verdade.

**Quem manda quando dois textos discordam.** Entre documentos que mandam, vale nesta ordem: o
registro mais novo, o arquivo de instruções, a especificação. Ela não é reescrita para acompanhar:
o registro diz qual seção ficou velha, e o título do bloco afetado, no arquivo de instruções, diz
qual registro vale. Sem isso, a sessão seguinte segue a especificação e desfaz a decisão.

Entre documento e código, depende do que o documento faz:

| O documento | Exemplos | A divergência é | O que fazer |
| --- | --- | --- | --- |
| descreve | documento por assunto, leia-me, mapa "onde ficam as coisas" | documento velho | O código manda: corrija o documento na mesma mudança |
| manda | regra inegociável, registro, especificação | achado | Não mexa em nenhum dos dois sem o dono: pode ser defeito, pode ser decisão que ninguém registrou. Leve em "Para decidir" (`references/dono.md` §5) |

## 6. Amarrar as pontas

1. Escreva o registro (§2 a §4).
2. Se ele cria regra para todo arquivo novo: uma linha no arquivo de instruções, com o número (o
   molde da regra está em `references/instrucoes.md` §3).
3. Se muda como algo funciona: atualize o documento por assunto.
4. No código: comentário curto com o número, só onde a construção parece erro.
5. Se há teste que trava: cite o teste no registro e o número na descrição do teste.
6. Se uma seção da especificação ficou velha: diga qual, no registro e no arquivo de instruções.
7. Rode `python3 <skill>/scripts/decisoes.py conferir`: número citado não fica sem registro.

A citação tem uma forma só, `(ADR-NNN)` no fim da frase: no comentário, no cabeçalho da migração,
na descrição do teste e na mensagem do commit.

## 7. Numeração

Três dígitos, em sequência, sem reaproveitar número. A parte mecânica é de `scripts/decisoes.py`:
`proximo` dá o próximo número livre e avisa se um ramo (branch) já buscado tem número maior;
`conferir` aponta, com arquivo e linha, número repetido, número citado sem registro, registro sem
campo e ligação para registro que não existe. Ele não busca no remoto nem altera registro existente.

- **Dois ramos com o mesmo número.** Havendo outra sessão, rode `git fetch` antes de numerar. Se
  colidiu na integração, renumere à mão o registro que chegou, sem mudar o texto, diga no Contexto
  dele com que número foi escrito e reaponte as citações.
- **Número citado antes de existir.** Primeiro o registro, depois a citação. Num plano, decisão
  nova se cita pelo identificador do plano e pelo título até o registro nascer. Número reservado
  acaba usado para outro assunto, e os comentários passam a apontar para o registro errado.

## 8. Adaptar

- **Dono que nunca programou.** O arquivo é o mesmo. Ao mostrar um registro, diga em três frases:
  "estava em dúvida entre A e B porque…; escolhi A; daqui para a frente isso significa…".
- **Time ou projeto longo.** Um arquivo por registro: aponte `decisoes`, em `metodo.ini`, para uma
  pasta, e o script passa a criar `<NNN>-<título em minúsculas com hífens>.md`, no mesmo formato.
  Numere só na integração dos ramos e ponha `conferir` no CI, pela cópia do projeto
  (`ferramentas/metodo/decisoes.py`). O arquivo único serve até algumas dezenas de registros.
- **Fora do que este método cobre:** revisão por pessoas, pedido de merge e estratégia de ramos
  (a prática vista é de um ramo com um dono); registro rejeitado; decisão revertida em produção.

## O que evitar

- **O registro promete o que o código não entrega.** A frase de garantia foi escrita antes de
  existir o teste. Cite o teste ao lado da garantia; sem teste, escreva "a intenção é". O registro
  que conserta diz que o anterior estava errado. Apagar a frase do antigo não serve.
- **Um registro com seis decisões.** O registro de fase ou de revisão juntou tudo, e os seguintes
  passam a dizer "revê a parte tal". Cada decisão que vira regra ganha número próprio.
- **"Foi aplicado em produção" dentro do registro.** A frase envelhece a cada ida a produção. O
  registro guarda a ordem e de quem depende; a data mora no estado.
- **"Decidir depois" que passa de registro em registro.** Adiamento sem dono e sem condição vira
  ruído. Diga quem decide e o que dispara; na terceira vez, vira item de "Para decidir".
- **E-mail de uma pessoa ou identificador real no registro.** O arquivo é versionado e pode virar
  público. Escreva o papel ("o e-mail do dono", "o banco de produção"), não o valor.

## Pronto quando

- [ ] `decisoes.py conferir` não acusa achado.
- [ ] O título, lido sozinho, diz a decisão, e o Contexto nomeia a alternativa descartada.
- [ ] As Consequências têm regra para o próximo ou custo, e "rever quando".
- [ ] Nenhum registro antigo foi reescrito; o revisto ganhou a linha `**Revisto por:**`.
- [ ] As pontas da §6 estão amarradas, e o dono leu o número e o título de cada decisão nova.

Volte ao `SKILL.md`, §4.
