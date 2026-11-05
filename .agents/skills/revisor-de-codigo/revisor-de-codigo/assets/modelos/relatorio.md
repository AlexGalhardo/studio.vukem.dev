<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido. -->
# Revisão · {{a mudança, em palavras do produto}}

<!-- É o que o dono lê. Conte, não adjetive. Cenário em palavras do produto; arquivo e linha para
     quem for conferir. Seção vazia fica com "nenhum", não some. A ordem e o que cada parte quer
     dizer: references/relato.md §1 e §2. Apague os comentários ao preencher. -->

**Posso subir?** {{Sim | Sim, nesta ordem: … | Não ainda: falta …}}

## O que foi revisado, e como

- Da base {{base}} até {{commit ou "a árvore de trabalho"}}: {{n}} arquivos, +{{n}} -{{n}} linhas.
- Lentes: {{quais}}. {{Um agente em passes: independência limitada | <n> agentes: 1 por lente e
  1 verificador por achado, <n> leituras ao todo}}.
- Limite de verificação: {{4}} achados por lente, do mais grave ao menos.

## A contagem

{{n}} achados: {{n}} confirmados (crítico {{n}}, grave {{n}}, médio {{n}}, baixo {{n}}),
{{n}} refutados, {{n}} não verificados. Rebaixados na verificação: {{n}} ({{de → para}}).
Depois das correções: {{n}} resolvidos, {{n}} não resolvidos, {{n}} regressões.

## Confirmados e corrigidos

- **{{o defeito, em palavras do produto}}** ({{severidade}}; `{{arquivo}}:{{linha}}`).
  Cenário: {{...}}. Correção: {{...}}. Reverificado: {{resolvido; entradas tentadas: …}}.

## Confirmados e não corrigidos: para você decidir

- **{{o defeito}}** ({{severidade}}). Por que não corrigi: {{contraria a decisão X | pede
  migration nova | …}}. Opções: (a) {{...}}; (b) {{...}}. Enquanto você não decide: {{o que vale}}.

## Refutados

- {{título alegado}} ({{severidade alegada}}): {{o trecho que impede a falha, com arquivo e linha}}.

## Não verificados, e deixados de fora de propósito

- Não verificados: {{os baixos e os além do limite, um por linha}}.
- De fora: {{defeito antigo fora da diferença; o que é de etapa posterior; estilo}}.

## Validação

- **Verifiquei rodando:** {{comando → números: arquivos, testes, passou, falhou, pulou}}.
- **Só li:** {{o que foi concluído por leitura}}.
- **Não conferi:** {{o quê, e por quê}}.
- **Relatado por agente, não conferido por mim:** {{o quê, ou "nada"}}.

## Para subir

{{A ordem de subida, se há banco: 1. … 2. … 3. …, com o motivo. O que só você faz.}}

Revisão por leitura não prova ausência de defeito: ela cobriu as lentes e os arquivos acima.
