<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Roteiro · {{produto}}

<!-- Como preencher. Troque cada lacuna e apague os comentários. Não mude a forma dos títulos de
     fase nem dos itens de "Pronto quando": o diagnóstico lê os dois. Situações válidas no título:
     a fazer, em andamento, pronta; só uma fase fica em andamento. Marque um item só com a prova
     na mão: o comando rodado ou a conferência do dono. Entregas vão separadas por ponto e vírgula;
     cada uma diz o que fazer e onde e, se houver, a decisão já tomada e a armadilha prevista. -->

## Como usar este roteiro

Uma sessão nova lê este arquivo depois do arquivo de instruções e de `docs/ESTADO.md`, e segue a
fase em andamento. Antes de começar: {{o que precisa estar no ar no ambiente local}}. Pare no fim
de cada fase, com o relato, para o dono conferir.

## Onde estamos

O que está pronto, o que está em curso e a última rodada das verificações moram em `docs/ESTADO.md`.

## Leia antes de escrever código

- O arquivo de instruções e `ESPECIFICACAO.md`, nas seções {{que a fase em andamento cita}}.
- Os títulos de `docs/decisoes.md`. Não desfaça decisão registrada sem perguntar ao dono.
- {{Os documentos por assunto da fase, quando existirem.}}
- A documentação da versão instalada de {{dependência central}}, em {{caminho}}: não confie na
  memória. {{O que mudou nesta versão e já causou erro.}}

## Regras de trabalho

<!-- Só as regras desta rodada, cada uma com a consequência. As de toda sessão moram no arquivo de
     instruções: não repita. -->

- **Fim de fase:** pare; suba a escada inteira e mostre o resultado; revise a diferença da fase;
  atualize `docs/ESTADO.md`; entregue o relato com o roteiro de validação.
- **Fases 0 e 1 são de fundação:** mostre o plano ao dono e espere o ok antes de implementar.
- **Não rode {{comando}}:** {{o que ele causaria}}.
- **Não derrube {{o que o dono deixa aberto}}:** use {{outra porta}} para os testes.
- **Já liberado:** {{as dependências previstas na especificação, pelo nome}}.

## Com o dono, uma vez só

<!-- Bloco opcional: apague o título e o bloco se não houver nada. É o que só se faz uma vez e com
     o dono ao lado: criar contas, criar o repositório remoto, ligar o primeiro ambiente remoto. -->

1. {{Passo, com a resposta já decidida para cada pergunta que a ferramenta fizer.}}
2. **Não rode {{comando}}:** {{o que ele causaria}}.

Se aparecer {{sintoma provável}}: {{o que ajustar, e o que não ajustar}}. Se o dono adiar, siga sem
este bloco e lembre antes da Fase {{número}}: {{por quê}}.

## Pendências com fase-alvo

<!-- A única lista do roteiro: corte de escopo com fase de destino. Adiado por prazo, passo do dono
     e decisão pendente moram em docs/ESTADO.md. Sem itens, escreva "Nenhuma." -->

1. **{{Título}}** ({{registro que a originou, se houver}}): {{como está hoje}}. {{O que fazer}} na
   Fase {{número}}. Atenção: {{armadilha}}.

## Fase 0 · Base (a fazer)

**Objetivo:** o projeto abre no ambiente local, com a escada montada até o degrau 2.
**Entregas:** projeto criado com {{stack}}, que abre no ambiente local com um comando; arquivos de
ambiente, um por alvo, e só o de exemplo no git; degraus 0 a 2 com comando em `metodo.ini`, e
`[zonas]` com os caminhos reais; primeiro estágio do CI, quando o dono criar a conta e o repositório
remoto; {{a casca da interface, ou o comando de entrada, ainda sem funcionalidade}}.
**Pronto quando:**
- [ ] Abro `{{endereço local}}` e vejo {{o quê}}.
- [ ] {{O caminho de erro: o que aparece quando algo falta ou não existe.}}
- [ ] Os degraus 0 a 2 passam com um comando, e o teste {{nome}} roda neles.

## Fase 1 · Dados e permissões (a fazer)

**Objetivo:** os dados e a matriz de permissões existem e estão provados, antes das telas.
**Entregas:** migrações das tabelas da seção 5 da especificação, só de acréscimo; a matriz de
permissões imposta em {{onde todos os caminhos passam}}; dados de exemplo só no ambiente local, com
uma conta por persona e, em cada dado restrito, o marcador ou o valor sentinela que o teste de
vazamento procura; teste de permissão por persona, e o degrau 3 com comando; {{uma tela mínima, sem
acabamento, para o dono entrar com cada conta de teste}}.
**Pronto quando:**
- [ ] Entro como {{persona}} e não consigo ver {{dado restrito}}.
- [ ] Entro como {{persona que pode}} e vejo {{o dado}}.
- [ ] O teste {{nome}} prova as duas coisas para cada persona, com o banco recriado do zero.

## Fase 2 · {{nome}} (a fazer)

**Objetivo:** {{uma frase: o que o dono passa a conseguir fazer}}.
**Entregas:** {{o que fazer, e onde}}; {{a decisão já tomada}}; {{a armadilha prevista}}.
**Pronto quando:**
- [ ] {{Uma ação do dono, na voz dele.}}
- [ ] {{O caminho de erro, ou o que não pode acontecer}}, com o teste {{nome}}.
- [ ] {{Até que degrau a escada sobe nesta fase.}}

<!-- Uma seção por fase, nesta mesma forma. A última costuma ser a de ir a produção. -->

## Quando tiver dúvida

Decida e registre em `docs/decisoes.md`. O que pede pergunta e o que só o dono faz estão no arquivo
de instruções, em "Como trabalhamos". Nesta fase, pergunte também antes de {{o que é próprio dela}}.
