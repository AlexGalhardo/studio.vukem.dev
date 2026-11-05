# Fase grande: como conduzir uma fase no peso pesado, do levantamento ao relatório?

Leia quando: só se o peso escolhido for o pesado (`references/pesos.md` §5).
Não é aqui: fase de peso médio (`references/fases.md` §3).
**Base:** proposta. Duas partes são desenho deste método, sem uso anterior: guardar o planejamento
em `docs/planos/`, versionado, e executar em passes com um agente só (§5). Na prática vista, cada
papel era um agente.

## O mínimo

- Se a fase não é pesada, feche esta ficha e use o plano de uma página.
- Comece pelo levantamento só de leitura: plano feito de memória erra no que já existe e no que a
  plataforma faz nesta versão.
- Escreva o plano-contrato, com a tabela "o que não pode acontecer, e o teste que prova".
- Revise o plano antes de implementar: erro de plano custa uma linha no documento e um pacote
  inteiro no código.
- Rode os pacotes em sequência, um por vez, na mesma árvore.
- Quem implementa não é quem confere, nem que seja em passes separados.

Conteúdo: 1. Levantamento só de leitura 2. O plano-contrato 3. Revisar o plano antes de implementar
4. Pacotes 5. Executar com um agente 6. Com vários agentes 7. Onde guardar o planejamento

## 1. Levantamento só de leitura

É a casa deste fato. Antes de decidir a arquitetura da fase, leia e escreva o que achou, sem criar,
alterar nem commitar nada além do próprio relatório. O modelo é `assets/modelos/levantamento.md`.

- **Cabeçalho:** data, commit de base, o que estava no ar, as fontes lidas e **o que não foi
  lido**. Sem essa segunda lista, quem planeja toma silêncio por ausência de problema.
- **Assuntos**, cada um numa seção (ou num relatório, com vários agentes): a plataforma na versão
  instalada, com as conclusões que mais mudam a arquitetura no topo; o contrato com o que já
  existe (API, esquema, configuração) ou as referências visuais medidas; e os requisitos e
  restrições, nas seis partes do modelo.
- **Fato separado de sugestão:** proposta de quem pesquisa começa por "Sugestão:". Fato técnico
  que sustenta decisão leva etiqueta de origem (medir em vez de supor: `references/stack.md` §2).
- **Contradições listadas**, com a saída de cada uma: o roteiro manda e a regra da rodada proíbe;
  item que já foi feito ("não refazer"); documento que cita solução substituída.
- **Limite declarado:** o que não pôde ser medido, e onde repetir a medição.
- Requisito sem "Pronto quando" não vira teste: escreva o critério ao lado de cada um.

## 2. O plano-contrato

Decide tudo o que os pacotes não devem decidir sozinhos. Pacotes feitos em sequência, sem o
histórico uns dos outros, só encaixam se nomes, tipos e fronteiras forem combinados antes. O modelo
é `assets/modelos/plano-contrato.md`: cabeçalho, espaço da errata e onze partes, de 0 a 10.

| Parte | O que não pode faltar |
| --- | --- |
| Cabeçalho | Commit de base, fontes e a frase dos **nomes definitivos**: quem precisar mudar um nome muda no plano primeiro |
| 0. O que foi medido | Medições numeradas (M1, M2), com o script e o resultado, e a validade: "medido na sonda; repetir no build real" |
| 1. Decisões de arquitetura | `A-01`, `A-02`: a decisão em parágrafo concreto, motivo e fonte. Nas difíceis: o que não resolve, custos aceitos, como validar e **plano B com o gatilho** |
| 2. Mapa de arquivos | Um dono por arquivo |
| 3. Contratos | Tipos, assinaturas e as marcações que os testes usam para achar cada elemento |
| 4. Dados | O que cada leitura seleciona; chaves de cache e quem usa; o que muda nos dados de exemplo |
| 5. Segurança | O caminho do dado restrito até a resposta; a tabela **"o que não pode acontecer, e o teste que prova"**, com a franqueza de dizer o que o teste não prova; as regras do teste de fronteiras |
| 6. Pacotes | Os cinco blocos de cada um (§4) |
| 7. Plano de testes | Camadas com o pacote dono; a rodada final em passos ordenados |
| 8. Registros novos | Pelo identificador do plano e pelo título, **sem número** |
| 9. Rastreabilidade | Requisito, pacote e arquivos, prova. Nenhum requisito sem dono; o destino de cada pendência com fase-alvo |
| 10. Perguntas em aberto | Cada ponto com decisão padrão, na língua do dono. Nenhuma bloqueia |

- **Sem número de registro.** Decisão nova se cita por `A-01` até o registro existir: o número
  nasce com `scripts/decisoes.py novo`, e um número escrito antes faz `scripts/decisoes.py
  conferir` acusar o plano.
- **Padrão que afrouxa regra inegociável não pode ser padrão.** Vira pergunta ao dono, e o plano
  segue a regra ao pé da letra.
- **Tamanho.** Ninguém lê um plano longo inteiro: diga a cada pacote quais seções ler até o fim.

## 3. Revisar o plano antes de implementar

Lentes, formato do achado e decisão por achado são os de `references/revisao.md` §2 a §4. Aqui
fica só o que muda quando o que se revisa é um plano.

- **O que se procura num plano e não num código:** requisito sem dono; trechos que mandam pacotes
  diferentes fazerem coisas incompatíveis; afirmação sobre a plataforma sem medição; aceite que
  passa com a coisa ainda vazia; motivo escrito errado, porque o registro herdaria o erro.
- **Lentes de plano:** completude, segurança, a plataforma na versão instalada e, havendo
  interface, a experiência. Cada lente mede o que puder, em vez de opinar.
- **Um árbitro** confere cada achado na fonte (código, banco do ambiente local como visitante,
  build, documentação da versão instalada, o próprio plano) e decide: aceito, aceito em parte ou
  refutado. Para cada um, escreve o que mudou no plano, seção por seção. "Em parte" diz que parte
  ficou de fora e por quê; senão parece aceito inteiro.
- **Achado que pede mudança fora do escopo** não entra no plano: vai para "Perguntas em aberto",
  com as opções.
- **A revisão também erra.** Leia a decisão do árbitro com o mesmo ceticismo, sobretudo quando ela
  abre exceção a uma regra.
- **Com um agente só,** cada lente e o árbitro são passes separados, e cada passe parte do disco.
- Grave a revisão a partir de `assets/modelos/achados.md`. O plano revisto substitui o anterior no
  mesmo caminho, e o cabeçalho ganha a linha da revisão.

## 4. Pacotes

O corte por camada e a regra de um dono por arquivo, a errata e o fim de fase estão em
`references/fases.md` (§3, §8 e §9). Aqui, só o que o peso pesado acrescenta. Cada pacote tem cinco
blocos:

| Bloco | O que traz |
| --- | --- |
| Objetivo | O que fica pronto e o estado ao fim: "as telas atuais continuam de pé com os tipos novos" |
| Arquivos | Aponta a parte 2 do plano |
| Passos, em ordem | O que fazer, numerado |
| Aceite | Comandos com a saída esperada no comentário |
| Entrega ao próximo | O que o pacote seguinte recebe e o que o relatório precisa dizer |

- **Regra de fronteira entra no pacote que cria o arquivo que ela protege**, nunca antes. Regra
  sem arquivo é `VAZIA` em `scripts/fronteiras.py`, sai com código 3 e derruba o degrau 2.
- **Encostar em arquivo de outro pacote:** o plano autoriza o mínimo ("só a troca de um nome por
  outro") e diz quem reescreve depois.
- **Vale para todos**, numa lista só: como obter a sessão de cada persona para uma requisição à
  mão; como contar elementos na resposta crua; o que não é divergência das referências.
- **O banco do ambiente local tem dono.** Pacote de testes que recria o banco apaga o que o dono
  cadastrou à mão: avise em "Perguntas em aberto" antes do primeiro.

## 5. Executar com um agente

Sete passes por pacote. A separação que um agente só consegue é de momento e de fonte: em cada
passe, parta do disco (o plano, o relatório, a diferença do git), e não da lembrança do passe
anterior.

1. **Implementar.** Leia a errata, a parte geral e as seções do pacote até o fim; leia os arquivos
   que vai alterar e os vizinhos que servem de exemplo. Faça os passos na ordem, testando enquanto
   escreve. Desvio do plano: o mínimo que resolve, anotado (o quê, por quê, evidência).
2. **Escrever o relatório do pacote**, em cinco partes: arquivos criados e alterados; cada comando
   de aceite com a saída real; desvios; o que não foi feito ou ficou frágil; o que o pacote
   seguinte precisa saber.
3. **Verificar o aceite.** Sem alterar arquivo, rode um a um os comandos de aceite, exatamente
   como escritos, e os degraus 0 a 2. Confira se o que o relatório diz ter rodado é verdade.
4. **Revisar por lente.** Só leitura; escreva todos os achados antes de corrigir qualquer um.
5. **Conferir cada achado**, tentando refutar: abra o arquivo, rode o comando. O que não se
   sustenta sai, com uma linha de motivo.
6. **Corrigir** o que ficou de pé, inclusive o teste que não provava, e nada além disso. Rode de
   novo o aceite e os degraus 0 a 2. Só o que está acima de baixa abre a segunda rodada, que é a
   última: o que sobrar vai para o relatório.
7. **Commitar** pelo portão do commit, e só então abrir o pacote seguinte.

## 6. Com vários agentes

Os passes do §5 viram cinco papéis: implementador, verificador de aceite, revisor por lente,
conferente e corretor. O texto de cada um está em `assets/modelos/papeis.md`. O que muda:

- Todos recebem o mesmo contexto comum, que começa dizendo que o papel não tem o histórico da
  conversa, e o aviso: "o relatório do implementador está em tal caminho; leia, mas confira".
- **Um só roda comando pesado:** o verificador de aceite, em sequência. Vários subindo a escada ao
  mesmo tempo, na mesma árvore, se atrapalham e travam máquina de pouca memória.
- **Ninguém commita, guarda alteração de lado, desfaz nem envia.** Quem coordena commita, depois
  de conferir cada pacote: relatório de agente é alegação, não fato.
- Revisores só leem; podem rodar um arquivo de teste isolado, requisições ao servidor do ambiente
  local e consultas de leitura.
- Levantamento e revisão do plano podem rodar em paralelo, um agente por assunto ou por lente. A
  implementação continua em sequência.

## 7. Onde guardar o planejamento

Em `docs/planos/` (o caminho de `planos`, em `[documentos]` de `metodo.ini`), versionado:

```text
docs/planos/<fase>-levantamento.md
docs/planos/<fase>-plano.md
docs/planos/<fase>-revisao-do-plano.md
docs/planos/<fase>-pacote-<n>.md
```

Editar um plano não vence a evidência da escada, porque esses caminhos ficam fora da impressão
digital da árvore. Capturas de tela, saídas longas e sondas ficam fora do repositório; o plano
guarda o resultado e, quando é curto, o script da sonda. Antes do último commit da fase, `git
status` confere que nada disso ficou na árvore. Dentro do plano, escreva caminho relativo à raiz do
projeto: caminho de pasta temporária quebra na sessão seguinte.

## O que evitar

- **Um comentário do código cita número de registro que não existe.** O plano reservou números, e
  a fase terminou com menos registros. Cite por `A-01` até `scripts/decisoes.py novo` dar o número.
- **Três trechos do plano mandam pacotes diferentes fazerem coisas incompatíveis.** Quem escreveu
  não vê; a revisão do plano vê. Não serve: pular a revisão porque o plano "parece pronto".
- **O plano afirma um comportamento da plataforma, e a medição mostra o contrário.** Era inferência
  escrita como fato. Etiquete a origem e meça o que sustenta decisão.
- **A revisão aceitou abrir exceção a uma regra inegociável.** Plano e revisão não afrouxam regra:
  no máximo propõem. A exceção vira pergunta ao dono.
- **"Rodei e passou" no relatório, sem a saída.** Comando que não pôde rodar e não foi declarado
  parece verde. O passe de verificação roda de novo e confere o relatório.
- **O plano aponta para uma pasta temporária que sumiu.** O planejamento morava fora do
  repositório. Guarde em `docs/planos/`.

## Pronto quando

- [ ] O levantamento diz o que foi lido e o que não foi, e separa fato de "Sugestão:".
- [ ] A tabela "o que não pode acontecer, e o teste que prova" não tem linha sem teste.
- [ ] A revisão do plano terminou, com decisão por achado, antes do primeiro pacote.
- [ ] Nenhum requisito ficou sem dono na rastreabilidade.
- [ ] `scripts/decisoes.py conferir` não acusa número de registro citado sem registro.
- [ ] Cada pacote tem relatório com a saída real do aceite, conferida num passe à parte.
- [ ] Levantamento, plano, revisão e relatórios estão em `docs/planos/`.

Volte ao `SKILL.md`, §4.
