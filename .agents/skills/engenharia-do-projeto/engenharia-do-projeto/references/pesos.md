# Pesos: quanto processo cabe nesta mudança?

Leia quando: a classificação está em dúvida; a mudança toca zona sensível; o dono pede para ir mais
rápido ou gastar menos; ao preencher `[zonas]` em `metodo.ini`.
Não é aqui: o que cada degrau prova (`references/testes.md` §1).
**Base:** proposta. As zonas sensíveis com degrau mínimo são desenho deste método, sem uso
anterior: confira os caminhos de `[zonas]` contra o que a mudança toca. Os três pesos e o modo
enxuto são prática vista.

## O mínimo

- Zona sensível tocada: peso médio, no mínimo, e escada até o degrau da zona.
- A zona se decide pelo que a mudança toca, não só pelo caminho: os caminhos de `[zonas]` são a
  rede, e um arquivo fora dela também pode mexer em quem vê o quê.
- Rebaixar pede uma frase de justificativa no relato.
- O piso não entra em corte nenhum (a lista está no `SKILL.md` §4).
- Cortar de propósito é modo enxuto, e fica escrito no estado, com data.

Conteúdo: 1. Treze casos classificados 2. Zonas sensíveis 3. Agravar e rebaixar 4. O que cada peso
pede em cada passo 5. Quando o peso é o pesado 6. Modo enxuto 7. Pouco orçamento de uso

## 1. Treze casos classificados

A definição dos três pesos está no `SKILL.md` §4. Ache aqui o caso mais parecido com o pedido.

| Pedido | Peso | Por quê |
| --- | --- | --- |
| Corrigir uma palavra num texto de tela, em arquivo fora de zona | fora do método | Cabe em um arquivo, não toca zona e não decide nada: sem ficha, só o portão do commit (`SKILL.md` §1) |
| A mesma correção, mais o teste que afirma o texto, em outro arquivo | leve | Já são dois arquivos: "O mínimo" da ficha do passo e a escada até o degrau 2 |
| Ordenar por data uma listagem que já é pública | leve | Lógica nova fora de zona: o teste nasce ao lado dela, na mesma mudança |
| Acrescentar uma coluna a uma tabela | médio | Zona de dados: é migração, e a escada sobe até o degrau 3 |
| Incluir mais uma persona na condição de quem executa uma ação, em uma linha | médio | Zona de acesso: o tamanho não mede o risco. Teste por persona com o caminho negativo; degrau 5 |
| Exportar em arquivo um dado que só uma persona vê | médio | Zonas de acesso e de dado restrito: guarda antes da leitura e teste de vazamento; degrau 5 |
| Ler a chave de um serviço que o projeto ainda não usa | médio | Zona de segredos: a leitura mora no módulo dos segredos, e a regra de fronteira entra junto; degrau 2 |
| Guardar em cache compartilhado uma leitura | médio | Zona de cache: o que é de uma pessoa não pode entrar na cópia de todos; degrau 4 |
| Mudar plano, preço ou a regra de quem conta como pagante | médio | Zona de cobrança, e preço é decisão do dono (`SKILL.md` §5); degrau 5 |
| Apagar coluna, tabela ou registros "que ninguém usa" | médio | Apagar dado não tem volta: pede pergunta ao dono e a conferência prévia do que some |
| Uma semana de telas numa área só, sem dado restrito | médio | Não toca zona, mas não cabe em horas: plano de fase de uma página, em pacotes |
| A primeira página pública de um produto que tem área restrita | pesado | Abre ao público um caminho que passa perto do dado restrito (§5) |
| Corrigir já um defeito que está em produção, a pedido do dono | o que a zona tocada pedir | **Leitura do método, não regra vista do dono.** Cai só a espera pelo roteiro de validação; o piso fica inteiro (`references/producao.md` §1) |

## 2. Zonas sensíveis

| Zona | A mudança toca quando | Degrau mínimo padrão | Chave em `[zonas]` |
| --- | --- | --- | --- |
| Dados | muda esquema, migração ou dados de exemplo | 3 | `dados` |
| Acesso | muda quem pode ver ou fazer: login, sessão, guarda, regra de permissão | 5 | `acesso` |
| Segredos | lê, cria ou move um segredo | 2 | `segredos` |
| Dado restrito | lê, mostra, copia ou exporta dado restrito | 5 | `restrito` |
| Cache compartilhado | cria ou altera leitura guardada para mais de uma pessoa | 4 | `cache` |
| Cobrança | muda preço, plano, estado de pagamento ou quem escreve esse estado | 5 | `cobranca` |
| Escrita fora do ambiente local | grava em qualquer ambiente remoto | o do que está a enviar | não tem |
| Apagar dado | remove coluna, tabela, registro ou arquivo guardado | o da zona de dados, se é migração | não tem |

As duas últimas não se detectam por caminho: ficam por conta do agente, e as duas pedem pergunta ao
dono (`SKILL.md` §5). Nas outras seis, `scripts/situacao.py` casa os arquivos da mudança em curso
com os caminhos e imprime `zonas: …; peso mínimo: médio; degrau mínimo: <n>`, e
`scripts/escada.py --exigido` sobe até esse degrau. Com duas zonas tocadas vale o maior degrau; sem
nenhuma, o 2. O script classifica só por caminho e diz isso na última linha: o efeito da mudança
quem julga é o agente.

- **Padrões de `<zona>.caminhos`:** separados por vírgula, relativos à raiz do projeto. `*` não
  atravessa `/`; `**` atravessa; padrão sem `/` casa com o nome do arquivo em qualquer pasta;
  maiúsculas contam. Exemplo: `<pasta das migrações>/**, <arquivo dos dados de exemplo>`.
- **Zona sem caminhos** não casa com nada: a mudança nela passa por leve, e o diagnóstico avisa
  que a classificação por caminho está desligada. Preencha com os caminhos reais, inclusive os do
  código que a mudança vai criar, antes do primeiro commit de código.
- **Zona que o projeto não tem:** apague as duas linhas e deixe um comentário com o motivo. Zona
  nova é mais um par `<nome>.degrau`, `<nome>.caminhos`.
- **`<zona>.degrau`** nasce com o padrão da tabela. Troque só quando, na stack do projeto, o teste
  que protege a zona roda em outro degrau, e escreva o motivo num comentário.
- **`segredos.caminhos`** é o módulo que lê os segredos, não os arquivos de ambiente: estes o git
  ignora, e por isso nunca aparecem numa mudança.
- **Arquivo novo de zona** entra em `[zonas]` na mesma mudança que o cria. Se não entrar, a
  próxima mudança nele é classificada como se não tocasse nada.

## 3. Agravar e rebaixar

**Agravar** não pede licença. Suba o peso quando um arquivo fora de `[zonas]` mexe no que a zona
protege (uma tela que passa a mostrar um campo restrito, um utilitário que a guarda chama), quando
a mudança cresceu além do combinado ou quando apareceu algo sem volta. Diga o peso novo e
acrescente o caminho a `[zonas]`.

**Rebaixar** cabe quando o caminho casou e a mudança não toca o que a zona protege: um comentário,
um texto de tela num arquivo da zona de acesso. Suba com `scripts/escada.py --ate <n>` e escreva no
relato a frase:
`Rebaixei: <arquivo> está na zona <zona>, mas a mudança só altera <o quê>. Subi até o degrau <n>.`

Não se rebaixa: migração, regra de acesso, leitura de segredo e escrita fora do ambiente local.
Nesses quatro o tamanho da mudança não entra na conta. O script não conhece rebaixamento: antes do
envio, `scripts/escada.py --evidencia` compara a evidência com o degrau das zonas do que está a
enviar e cobra o degrau poupado. Rebaixar adia o degrau caro; não o dispensa antes de ir a produção.

## 4. O que cada peso pede em cada passo

É a casa deste fato. Os passos são os do ciclo (`SKILL.md` §4); o piso vale nas três colunas.

| Passo | Leve | Médio | Pesado |
| --- | --- | --- | --- |
| 1. Mapear | Busca pelo que a mudança toca; títulos do registro de decisões | O mesmo, mais o documento por assunto da área | Levantamento só de leitura, escrito (`assets/modelos/levantamento.md`) |
| 2. Combinar | Objetivo, "Pronto quando" e proibições numa mensagem | Plano de fase de uma página (`assets/modelos/plano-de-fase.md`), de dois a quatro pacotes | Plano-contrato (`assets/modelos/plano-contrato.md`), revisto antes de implementar |
| 3. Implementar | Código e teste na mesma mudança | Um pacote por vez, com o teste da camada que a zona pede | Um pacote por vez; quem implementa não é quem confere |
| 4. Subir a escada | Até o degrau 2 | Até o degrau da zona; a escada inteira no fim de fase | O aceite de cada pacote, rodado como escrito; a escada inteira no fim |
| 5. Revisar | Releitura da diferença antes do commit | Uma lente, escolhida pelo que a mudança toca, com os achados escritos antes de corrigir | Duas lentes ou mais, cada achado conferido, até duas rodadas |
| 6. Fechar | Commit pelo portão e relato curto, com os três rótulos | Estado e documento por assunto na mesma mudança; registro, se houve decisão; roteiro de validação | Relatório por pacote, relato de fim de fase, registros e estado |

## 5. Quando o peso é o pesado

Basta um dos três critérios. Tamanho sozinho não torna pesado: fase longa sem nenhum deles se parte
em fases de peso médio.

| Critério | Como reconhecer | O que o peso pesado compra |
| --- | --- | --- |
| Dado restrito exposto ao público | A fase cria um caminho pelo qual quem não pode ver chega perto do dado: página pública de item com parte restrita, cache compartilhado ao lado de dado por pessoa | A tabela "o que não pode acontecer, e o teste que prova", revista por uma lente de segurança antes do código |
| Plataforma que o agente não conhece | Versão nova, serviço nunca usado no projeto, comportamento que a documentação da versão instalada não fecha | Fatos com etiqueta de origem, sonda e plano B com gatilho |
| Vários contratos entre partes | Mais pacotes do que cabem no plano de uma página, com nomes e tipos que precisam encaixar entre eles | Nomes definitivos e um dono por arquivo, combinados antes |

## 6. Modo enxuto

É escolher um peso menor que o risco pede, quando prazo ou orçamento apertam. O critério do corte:
sai o que mede ou enfeita; fica o que protege e o que é caro de desfazer.

- **Costuma sair:** a conferência por papel separado e as rodadas de correção; teste de interface
  (ficam os de lógica pura); ponta a ponta além do teste de vazamento e de um de fumaça; medição de
  desempenho e fidelidade visual fina (fica uma captura por tela); documentação detalhada.
- **Não sai:** o piso, as regras inegociáveis do projeto e os estados de carregando, vazio e erro.
  "Faz só o necessário" é pedido de economia, não licença para pular a escada.
- **Onde se declara:** no plano, como item de errata, se há plano (`references/fases.md` §8); no
  estado, em "Ficou para depois"; num registro, só se a dívida é permanente.
- **O item de "Ficou para depois"** traz a data do corte e quem pediu, o que saiu, os fluxos sem
  teste pelo nome e a data ou o gatilho de retomada.

## 7. Pouco orçamento de uso

Use um agente por tarefa e o modelo de linguagem mais barato no que é mecânico: renomear, mover,
formatar, preencher documento. Vários agentes com papéis separados são para quando o orçamento
permite. Anote o limite que o dono deu em "Como trabalhamos aqui", no estado, para a sessão seguinte
não gastar o que ele pediu para poupar (máquina com pouca memória: `references/ambientes.md` §4).

## O que evitar

- **Mudança de uma linha tratada como pequena.** O tamanho não mede o risco: uma condição de
  acesso cabe em uma linha. Classifique pelo que a mudança toca. Não serve: "é rapidinho".
- **"Ficou para depois: mais testes."** Sem o nome do fluxo e sem data, o depois não chega.
  Escreva cada fluxo sem teste pelo nome, com a data ou o gatilho de retomada.
- **Corte que ficou só na conversa.** O que é adiado sem registro vira esquecimento na sessão
  seguinte. Escreva no estado na mesma mudança.
- **Peso pesado por hábito.** Levantamento, plano-contrato e conferência separada são o que mais
  consome orçamento. Sem um dos três critérios, use o médio e parta a fase.

## Pronto quando

- [ ] O peso foi decidido antes de implementar, com o motivo em uma frase.
- [ ] Toda zona tocada está nomeada, e a escada subiu até o degrau dela ou ele está em "Não rodei".
- [ ] O rebaixamento, se houve, tem a frase no relato.
- [ ] O que foi cortado está no estado, com data, e os fluxos sem teste estão lá pelo nome.
- [ ] Toda zona que o projeto tem está em `[zonas]` com caminhos; a que ele não tem foi apagada.

Volte ao `SKILL.md`, §4.
