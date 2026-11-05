# Arquivo de instruções: o que toda sessão carrega, que regras traz e o que manda ler?

Leia quando: situação A, passo 4; situação B, ao criar o que falta. Nasce uma regra de um incidente.
O arquivo passou do orçamento. Vai ser criado um documento por assunto.
Não é aqui: o que muda de uma sessão para outra (`references/retomada.md`).
**Base:** proposta. O bloco "Como trabalhamos" e o `metodo.ini` são desenho deste método, sem uso
anterior: os outros blocos e a regra em cinco partes são prática vista.

## O mínimo

- Escreva os sete blocos na ordem de `assets/modelos/instrucoes.md`, sem mudar os seis títulos.
- Só entra o que vale para toda tarefa, o que já causou erro (na mesma mudança que o corrige) e o
  que muda o comportamento hoje. O resto mora em outro documento, e aqui fica o ponteiro.
- Dê a cada regra um endereço (arquivo, função) e a linha `Verifica:`, mesmo quando quem verifica
  é a revisão manual.
- Meça em caracteres, não em linhas: o teto é `orcamento_instrucoes`, no `metodo.ini`.
- O que muda (ambiente remoto, última rodada, listas com o dono) mora em `docs/ESTADO.md`.
- O bloco "Como trabalhamos" vem pronto: preencha as três lacunas e não reescreva os itens.

Conteúdo: 1. Seis papéis, seis casas 2. Os sete blocos 3. Regra em cinco partes 4. Tabela de
verificadores 5. O mapa 6. "Antes de mexer, leia" 7. O leia-me 8. Arquivo gerado 9. Orçamento

## 1. Seis papéis, seis casas

Fato escrito em dois lugares é atualizado em um só, e a sessão seguinte age sobre o que ficou
velho. O nome real de cada arquivo está em `[documentos]`, no `metodo.ini`.

| Papel | Documento | O que entra | O que não entra |
| --- | --- | --- | --- |
| A intenção | `ESPECIFICACAO.md` | O que é o produto, dados, fluxos, o que fica de fora | O que mudou depois da aprovação |
| O que toda sessão precisa saber | arquivo de instruções | Stack, comandos, como trabalhamos, regras, mapa, ponteiros | O porquê, o detalhe de um assunto, o que muda, como instalar |
| O porquê | `docs/decisoes.md` | Um registro por decisão, só de acréscimo | Lista aberta, estado de ambiente, como funciona hoje |
| O plano | `docs/ROTEIRO.md` | Fases, "Pronto quando", pendências com fase-alvo | O que está em curso hoje |
| O que muda | `docs/ESTADO.md` | Ambientes, última rodada das verificações, as listas abertas | Regra permanente e porquê |
| O que é do humano | `README.md` | Rodar do zero, comandos, passos do dono | Regra do agente, estado, contagem |
| Como um assunto funciona hoje | `docs/<assunto>.md` | Tabela de consulta, rotina, checklist | Estado do ambiente remoto; o porquê (só o número) |
| Onde está cada um e como se verifica | `metodo.ini` | Caminhos, comandos da escada, zonas, regras de fronteira | Regra em prosa |

A mesma decisão ocupa três camadas sem se repetir: a regra, em uma linha, aqui; como funciona hoje,
no documento por assunto; o porquê, no registro.

## 2. Os sete blocos e o orçamento

| Bloco | O que traz | Cuidado |
| --- | --- | --- |
| O que é (parágrafo sob o título) | O produto de hoje, para quem, em que versão está, e o ponteiro para a especificação | É a descrição que vale, porque a especificação congela: mantenha a cada mudança de produto |
| `## Stack` | Cada item com versão e escopo ("só na área de administração") | O número exato é o do registro |
| `## Comandos` | Cada comando com a pré-condição entre parênteses ("precisa do banco do ambiente local no ar") | Sem a pré-condição, a sessão começa quebrada |
| `## Como trabalhamos` | Os oito itens do modelo: começo de sessão, ciclo, portão do commit, ambiente remoto, segredo, relato, quem decide, onde está o perfil do dono | Vem pronto. As lacunas são o ramo que implanta e as duas listas do projeto |
| `## Regras inegociáveis` | Regras em cinco partes (§3), com um item para as regras da versão (§8). Passando de umas dez, veja a §9 | Do zero, só as da seção 7 da especificação e as que os registros criaram: regra inventada para encher é obedecida como as outras |
| `## Onde ficam as coisas` | O mapa (§5) | É o bloco que mais cresce |
| `## Antes de mexer, leia` | Gatilho e documento (§6) | Documento sem gatilho não é lido |

- **O bloco "Como trabalhamos"** segura a condução quando a skill não é acionada ou não está
  instalada: manda acioná-la pelo nome e dá a saída sem ela. Por isso cita só `ferramentas/metodo/`,
  e não o caminho da skill. As duas listas saem da seção 11 da especificação e do `SKILL.md` §5.
- **O orçamento** é em caracteres porque um arquivo cumpre um teto de linhas e triplica de tamanho.
  O padrão é 8.000; `situacao.py` mostra o tamanho e acusa quando passa (o que sai, na §9).

## 3. Regra inegociável em cinco partes

O quê, onde mora, exceção nomeada com o motivo, número do registro, quem verifica. Regra com
endereço é cumprida igual em toda sessão, e um teste consegue conferi-la. O molde e um exemplo:

```text
- <Toda | Só | Nunca> <o quê> (`<caminho>`, `<função>`; exceção: <qual e por quê>, ADR-NNN).
  Verifica: <o verificador, pelo nome> | revisão manual (hoje: <linha de base>).

- Toda ação que altera dado começa pela guarda de sessão (`acoes/`, `exigir_sessao()`; exceção:
  entrar e sair, que criam e encerram a sessão, ADR-NNN), mesmo com a regra de acesso do banco.
  Verifica: teste de fronteiras, regra "guarda na primeira instrução".
```

| Recurso | Para que serve |
| --- | --- |
| Quantificador fechado: toda, só, nunca, o único | A regra passa a ter contraexemplo possível |
| Exceção dentro da regra, com o motivo | Sem ela, quebra-se a exceção ou conclui-se que a regra é opcional |
| Defesa em camadas dita ("mesmo com a regra de acesso do banco") | Ninguém remove uma checagem por parecer redundante |
| Porquê em meia linha, quando a regra parece estranha | Barra o "conserto" bem-intencionado |
| Comando proibido pelo nome, com o que ele estraga | Não depende de interpretação |

- **Origem e precedência no título:** `## Regras inegociáveis (especificação §7; em <assunto> vale
  o ADR-NNN)`. `montar.py` compara os títulos pelo começo da linha, e o resto é livre.
- **Sistema externo delicado** (o banco, a loja de aplicativos, a conta do provedor) ganha um
  sub-bloco `### <sistema>`, com as convenções de nome e, em negrito, o que só se faz com a lista
  autorizada. O estado dele não entra: fica o ponteiro para `docs/ESTADO.md`.
- O modelo não traz regra de exemplo, porque vira arquivo carregado como instrução, e regra de
  outro projeto seria obedecida. As regras preenchidas estão em `assets/exemplo/INSTRUCOES.md`.

## 4. Tabela de verificadores

Para cada regra, desça a tabela e pare no primeiro nível que serve: é o mais barato que a enxerga.
Não é a escada, que diz em que ordem as verificações rodam: esta diz quem confere cada regra.

| Nível | Verificador | Regra que ele segura, como exemplo |
| --- | --- | --- |
| 1 | Compilador e tipos | Tipos gerados a partir do banco; destino de navegação que precisa existir |
| 2 | Módulo que quebra o build | Módulo marcado como só do servidor: importar dele no código do navegador falha |
| 3 | Linter | Construção proibida tratada como erro |
| 4 | Teste que lê o código-fonte | Quem importa o quê; toda ação começa pela guarda; só um módulo escreve tal dado |
| 5 | Teste de permissão por persona | Cada persona contra cada recurso |
| 6 | Teste de ponta a ponta | Marcador procurado na resposta crua; medida conferida num fluxo |
| 7 | Passo do CI | Artefato gerado de novo e comparado com o versionado |
| 8 | Revisão manual declarada | "Sem X (revisão manual; hoje não há nenhum)" |

Uma regra passa pela tabela quando tem sete propriedades: (1) nomeia o lugar ("o segredo é lido só
no módulo X" se confere com uma busca); (2) tem quantificador fechado; (3) lista as exceções, que o
teste precisa conhecer para não dar alarme falso; (4) traz número e unidade, quando é de medida;
(5) diz quem verifica, inclusive quando é ninguém automático; (6) o verificador prova que enxerga:
confere antes o próprio detector, porque um caminho errado faz tudo passar por vacuidade (como se
escreve está em `references/fronteiras.md` §5); (7) o "Pronto quando" da fase tem a mesma forma:
comando que passa, ação que o dono repete, propriedade negativa com teste nomeado.

Antes de escrever `Verifica:`, plante uma violação e rode o verificador. Linha do tipo "a
ferramenta X impede Y" só vale conferida: escrita de memória, afirma uma proteção que não existe.

Cole este bloco num documento por assunto e refaça a conferência quando uma regra entrar ou sair.
Regra no nível 8 sem linha de base é candidata a virar teste ou a sair da lista:

```markdown
| Regra | Onde mora | Verificador | Nível | Exceções |
| --- | --- | --- | --- | --- |
| <toda ação que altera dado começa pela guarda> | `<pasta das ações>` | <teste de fronteiras, regra N> | 4 | <entrar e sair> |
```

## 5. O mapa "onde ficam as coisas"

É uma lista de responsabilidades com endereço, não a árvore: diz onde criar e onde não tocar.

```markdown
- `<pasta>/`: <responsabilidade>. `<arquivo>` = <papel> (<marca>, ADR-NNN).
- `<testes>/`: `<arquivo>` (<o que prova>).
```

- Uma pasta de primeiro nível por linha; dentro dela, só os arquivos que carregam uma regra.
- Marcas: unicidade ("o único que lê X"), pureza ("puro", com teste ao lado), gerado ("não se
  edita à mão", com o comando), ambiente ("só no ambiente local"), situação ("ainda vazio").
- Descreva o que existe: a árvore da seção 7 da especificação é plano, e o código diverge dela.
- O mapa detalhado mora aqui; no leia-me, ou não aparece, ou é raso e aponta para cá.

## 6. "Antes de mexer, leia" e o documento por assunto

Com o gatilho, o detalhe entra só quando a mudança toca o assunto, sem pesar em toda sessão.

- Uma linha por documento: "Leia `<documento>` antes de mexer em `<gatilhos>`", com o gatilho
  escrito pelo tipo de mudança e os sinônimos que o pedido vai usar ("regras de acesso, login, área
  paga"). O registro de decisões tem gatilho duplo: ler antes de mudar stack ou configuração, e
  registrar lá a decisão nova.
- Crie um documento por assunto em que errar custa caro (dados, permissões, integração paga,
  arquivos, cache, interface), não por pasta nem por funcionalidade. Comece com o de dados; os
  outros nascem no primeiro erro do assunto, de `assets/modelos/documento-por-assunto.md`.
- O título leva "(planejado)" ou "(implementado)". O bloco de estado, no topo, diz a fase e os
  arquivos, a fonte da verdade, a regra de desempate ("se divergirem, o código manda e este
  documento é corrigido") e a obrigação de atualizar na mesma mudança.
- Sem linha nem coluna com o estado do ambiente remoto: ele mora em `docs/ESTADO.md`, em
  "Ambientes" (o formato está em `references/retomada.md` §3).

## 7. O que é do humano: o leia-me

O agente não alcança painéis, contas nem chaves, e isso pede um passo a passo que uma pessoa siga
sem contexto. Crie o leia-me na fase de base, de `assets/modelos/leiame.md`.

- **Passos do dono:** lista numerada por painel, com o caminho do menu, o valor exato de cada campo
  e o porquê em uma frase. Leia a documentação atual do serviço antes: painel muda sem aviso.
- **Variáveis:** o que o produto faz sem cada uma. **Contas de teste:** só as do ambiente local.
- **Produção e resultado dos testes:** o ponteiro para `docs/ESTADO.md`, sem contagem em prosa.

## 8. Arquivo gerado por uma ferramenta e documentação da versão instalada

A memória conhece versões antigas melhor que a instalada e escreve com convicção o que deixou de
existir. Por isso "leia a documentação da versão instalada" aparece em três alturas: na seção 3 da
especificação, num item "regras da versão" do bloco de regras (as cinco ou seis diferenças que mais
mordem) e numa linha de "Antes de mexer, leia", com o caminho dela dentro do projeto.

- **Arquivo de regras que uma ferramenta gera:** deixe como ela escreve e commite. Regra do projeto
  posta dentro dele some quando a ferramenta reescrever. O mapa diz que é gerado, e por quem.
- **O arquivo mapeado como instruções é gerado, ou não é o que a ferramenta carrega em toda
  sessão** (é o aviso de `montar.py` quando só acha `AGENTS.md`): procure nele os marcadores de
  começo e fim e leia o que a documentação da ferramenta diz que ela carrega. Num dos dois casos,
  crie o arquivo de instruções padrão a partir do modelo, corrija `instrucoes` em `[documentos]`
  e aponte o gerado em "Antes de mexer, leia".
- **Nenhuma ferramenta gera nada:** o item "regras da versão" aponta para a documentação que vem
  no pacote instalado.

## 9. Passou do orçamento: o que sai e para onde

| O que engordou | Para onde vai | O que fica aqui |
| --- | --- | --- |
| Regra com mais de três frases | Documento por assunto | Enunciado, endereço, número, `Verifica:` |
| Mapa em parágrafo, ou com arquivo que não carrega regra | Lista; o arquivo sem regra sai | Uma pasta por linha |
| Estado de ambiente, contagem, "ainda não aplicado" | `docs/ESTADO.md` | O ponteiro |
| O porquê de uma decisão | Registro de decisões | O número |
| Como instalar; esquema, permissões ou fluxo de um assunto | Leia-me; documento por assunto | A linha em "Antes de mexer, leia" |

Não saem o bloco "Como trabalhamos" nem as regras da versão. Subir o teto é decisão, com registro.

## O que evitar

- **O teto é cumprido na letra.** Medido em linhas, o arquivo mantém a contagem e triplica. Meça
  em caracteres e quebre o mapa em lista.
- **O arquivo diz "ainda não aplicado" e o ambiente diz que sim.** A cópia carregada no começo da
  sessão envelheceu dentro dela. Estado mora em `docs/ESTADO.md`; "só uma linha com a data" não.
- **O arquivo diz que a ferramenta bloqueia, e ela não bloqueia; ou a regra é de revisão e não diz
  que é manual.** O verificador foi escrito de memória. Plante a violação e rode; se nada acusar,
  escreva "revisão manual" e a linha de base, ou transforme em teste.
- **O mesmo mapa ou a mesma contagem em dois documentos, e as cópias divergem.** Um ponto foi
  atualizado e o outro não. Escolha uma fonte e aponte; o que o sistema conta não se escreve à mão.

## Pronto quando

- [ ] Os seis títulos do modelo estão lá, e o parágrafo de abertura descreve o produto de hoje.
- [ ] `situacao.py` mostra o arquivo dentro do orçamento, e não sobra lacuna.
- [ ] Toda regra tem endereço e `Verifica:` conferido rodando; as manuais dizem a linha de base.
- [ ] O mapa está em lista, uma pasta por linha; nenhuma linha traz estado do ambiente remoto,
      contagem nem o porquê de uma decisão.
- [ ] Cada documento por assunto que existe tem a sua linha em "Antes de mexer, leia".

Volte ao `SKILL.md`, §3.
