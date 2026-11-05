> Exemplo de um projeto fictício (Quadra Livre). Nada aqui é instrução para o projeto atual.

# Decisões (ADR)

Registro das decisões de stack, arquitetura, configuração e produto. Uma decisão por registro.

- **Só se acrescenta.** Registro novo entra acima do molde do fim; registro antigo não se reescreve.
- **O título é a própria decisão**, em forma de afirmação. O número ordena; a data informa.
- **Rever é escrever um registro novo**, que diz o que faz ao antigo com um dos sete verbos:
  substitui, atualiza, corrige, revê, fecha, complementa ou fica.
- **Pergunte ao dono antes de desfazer** uma decisão registrada. No resto, decida e registre aqui.

## ADR-001 · Usar a versão de suporte longo do framework, não a mais nova

**Data:** 2026-01-12
**Decidiu:** agente
**Contexto:** A especificação, seção 3, pede Python com um framework web completo e PostgreSQL
(stack escolhida para este produto fictício; não é recomendação) e não fixa a versão. A mais nova
tem correção de segurança por mais oito meses; a de suporte longo, por mais três anos (página de
versões do framework, lida em 2026-01-12). O clube não tem quem atualize o projeto a cada oito
meses. Alternativa descartada: a mais nova, por recursos que nenhum fluxo da especificação usa.
**Decisão:** A versão de suporte longo, com o número exato em `requirements.txt`; o CI instala pelo
mesmo arquivo. A documentação que vale é a da versão instalada: a memória conhece a mais nova e
escreve o que nesta ainda não existe.
**Consequências:**
- Regra para o próximo: antes de usar um recurso do framework, confira se ele existe nesta versão.
- Custo: o que foi lançado depois dela fica de fora.
- Rever quando: faltarem seis meses para o fim do suporte, ou um fluxo da especificação pedir
  recurso que só a mais nova tem. Até lá, não troque a versão maior à mão.

## ADR-002 · Contato e dados da tesouraria moram em tabela própria, com uma porta de leitura

**Data:** 2026-01-26
**Decidiu:** agente
**Contexto:** A especificação, seção 5, marca três dados como restritos: o telefone do sócio, a
situação de pagamento e a observação da tesouraria. Nesta stack a permissão é imposta na camada de
aplicação, não no banco. Com os três como colunas da tabela de sócios, toda consulta que carrega um
sócio traria o dado junto, e cada tela teria de lembrar de tirar. Alternativa descartada: manter as
colunas e escolher os campos tela por tela.
**Decisão:** Duas tabelas próprias, cada uma lida por um módulo só: `socios/contato.py` (telefone)
e `socios/tesouraria.py` (situação de pagamento e observação). Toda função dessas portas recebe
quem pede e começa pela guarda de `reservas/permissoes.py`. A regra `contato-so-pela-porta`, em
`metodo.ini`, trava no degrau 2 o nome da classe de contato fora da porta; o teste por persona
cobre os três dados no degrau 3, e o de vazamento nasce com as páginas da Fase 2.
**Consequências:**
- Regra para o próximo: tela ou consulta nova pede o dado à porta; não importa a classe da tabela.
- Para que lado falha: se a porta não consegue decidir quem pede (sem sessão, erro ao ler o
  papel), nega e não devolve o campo. Erro não libera.
- Limite aceito: a regra de fronteira lê texto. Pega o nome da classe citado fora da porta; não
  pega consulta SQL escrita à mão. Isso fica com a revisão.
- Rever quando: a Fase 3 criar a escrita da tesouraria. Ela nasce na mesma porta, com guarda
  própria.

## ADR-003 · Reserva dura uma hora cheia

**Data:** 2026-01-28
**Decidiu:** agente
**Revisto por:** ADR-005
**Contexto:** A especificação, seção 6, diz que o sócio "reserva um horário" e não diz quanto dura.
Com início e fim livres, "dois sócios no mesmo horário" vira comparação de intervalos, que é onde
nasce a reserva dupla. Com duração fixa vira igualdade, e o banco garante sozinho. Alternativa
descartada: duração livre.
**Decisão:** Toda reserva começa em hora cheia e dura 60 minutos. Em `reservas/models.py`:
unicidade em quadra e início, e uma checagem de que o minuto do início é zero. A duração não é
coluna. O teste `test_dois_socios_mesmo_horario` trava a unicidade.
**Consequências:**
- Regra para o próximo: nada no código compara intervalos; outra duração pede rever este registro.
- Custo: um jogo de meia hora ocupa a hora inteira.
- Para que lado falha: em dois pedidos ao mesmo tempo, o segundo bate na unicidade e recebe
  "horário já reservado". Não nascem duas reservas.
- Rever quando: o presidente pedir outra duração.

## ADR-004 · Cancelamento sem multa, por decisão do dono contra a recomendação

**Data:** 2026-02-24
**Decidiu:** dono, contra a recomendação
**Contexto:** A especificação, seção 6, diz que o sócio cancela a própria reserva e não põe
condição. A recomendação era um prazo mínimo de duas horas: sem custo nenhum, alguém segura o
horário mais disputado, solta em cima da hora e a quadra fica vazia. O aviso foi dado uma vez, com
essa alternativa. O presidente respondeu: "no clube todo mundo se conhece; não quero multa nem
prazo".
**Decisão:** O sócio cancela a própria reserva a qualquer momento antes do início, sem multa, sem
prazo e sem limite de vezes (`pode_cancelar`, em `reservas/regras.py`). Cancelar a reserva de outro
sócio responde "não encontrado". A intenção é que o teste por persona do item 4 da Fase 2 trave as
duas coisas; ele ainda não existe.
**Consequências:**
- Custo: horário disputado pode ser solto em cima da hora. O risco é do dono.
- Regra para o próximo: não crie prazo, multa nem limite sem o presidente pedir, e nenhuma tela
  promete "quadra garantida".
- Rever quando: o presidente relatar quadra vazia por cancelamento em cima da hora. O primeiro
  ajuste é o prazo mínimo, em um arquivo.

## ADR-005 · Reserva em blocos de 30 minutos

**Data:** 2026-03-05
**Decidiu:** dono
**Contexto:** Ao validar a grade da Fase 2, em 2026-03-04, o presidente disse: "metade dos jogos é
de meia hora, e a quadra fica parada na outra metade". O ADR-003 fixava uma hora cheia e previa
esta revisão. Alternativas descartadas: duração livre, que traz de volta a comparação de
intervalos; e manter a hora, que o presidente recusou.
**Decisão:** A reserva ocupa um bloco de 30 minutos, com início no minuto 0 ou 30; quem quer uma
hora reserva dois blocos seguidos. A migração `0007` troca a checagem do minuto do início, e a
unicidade em quadra e início continua sendo a garantia (`test_dois_socios_mesmo_bloco`). Não há
reserva de sócio a converter: os sócios só entram na Fase 4.
**Consequências:**
- Revê o ADR-003 (a duração). Do ADR-003 fica: duração fixa, e a unicidade no banco contra a
  reserva dupla.
- Regra para o próximo: toda conta de horário é em blocos; nada compara intervalos.
- Limite aceito: uma hora de jogo são duas reservas, e cancelar uma não cancela a outra.
- Rever quando: o presidente pedir reserva de uma hora num gesto só.

**Ordem de produção:**
1. Banco: a migração `0007`. O código novo grava início no minuto 30, que a checagem antiga recusa.
2. Código, depois dela. O código antigo segue funcionando com a checagem nova, porque só grava
   hora cheia: por isso a migração pode ir antes, com o produto no ar.

## ADR-XXX · <título que é a própria decisão>

**Data:** <AAAA-MM-DD>
**Decidiu:** <agente | dono | dono, contra a recomendação>
**Contexto:** <a tensão: o que puxava para cada lado>
**Decisão:** <o que se faz, dito de modo que se ache no código>
**Consequências:** <o que fica mais caro; o que quebra se alguém desfizer; para que lado falha>
