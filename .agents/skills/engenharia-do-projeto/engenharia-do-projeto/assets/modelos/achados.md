<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Achados · {{o que foi revisado: a mudança, a fase ou o plano}}

<!-- Grave em docs/planos/. Escreva todos os achados antes de corrigir qualquer um. Identifique cada
     um pela lente e por um número (S-01 segurança, B-01 banco, C-01 comportamento). As severidades
     e as decisões são as de references/revisao.md, §3 e §4. Ao revisar um plano, "Onde" é a seção
     dele, e "O que mudou" é a seção alterada. Apague os comentários ao preencher. -->

Revisado em {{AAAA-MM-DD}}, sobre {{o commit, ou "a mudança em curso"}}. Lentes: {{quais}}.
Quem revisou: {{em passes por quem escreveu: independência limitada | um agente por lente}}.

## Achados

### {{S-01}} · {{bloqueante | alta | média | baixa}} · {{o comportamento errado, em uma frase}}

- **Onde:** `{{arquivo}}:{{linha}}`, ou {{o comando}}.
- **Evidência:** {{o trecho ou a saída, conferida antes de escrever}}.
- **Correção proposta:** {{o que mudar, e o teste que passa a provar}}.

## Decisão por achado, rodada {{1}}

| Achado | Severidade | Decisão | Motivo | Conferido como |
| --- | --- | --- | --- | --- |
| {{S-01}} | {{mantida, ou "rebaixada de alta para média"}} | {{aceito, aceito em parte ou refutado}} | {{em uma linha; em "aceito em parte", o que ficou de fora}} | {{o arquivo aberto ou o comando rodado, e o que saiu}} |

## Correções, rodada {{1}}

<!-- A rodada 2 olha só a diferença das correções e é a última: repita para ela as duas tabelas. -->

| Achado | O que mudou | Depois da correção |
| --- | --- | --- |
| {{S-01}} | {{o arquivo, e o teste que passou a provar}} | {{resolvido, não resolvido, com o dono ("Para decidir") ou origem de outro achado, e qual}} |

Escada depois das correções: {{a linha `escada:`, colada}}

## Contagem final

{{n}} achados em {{n}} lentes: {{n}} aceitos ({{n}} em parte), {{n}} refutados, {{n}} com o dono.
Por severidade: {{n}} bloqueantes, {{n}} altas, {{n}} médias, {{n}} baixas. Rodada 2: {{n}}
achados, {{n}} deles regressão da correção. Ficou aberto: {{o achado, e onde está anotado no
estado; ou "nada"}}.
