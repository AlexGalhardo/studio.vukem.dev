<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido. -->
# Achados · {{a mudança revisada}}

<!-- Escreva todos os achados antes de corrigir qualquer um. Identifique cada um pela lente e por
     um número: B-01 banco e implantação, S-01 segurança e fronteiras, C-01 comportamento, T-01
     testes. Severidades e vereditos: references/verificacao.md §1 e §3. Sem cenário de falha não
     é achado: apague. Apague os comentários ao preencher. -->

Revisado em {{AAAA-MM-DD}}, sobre {{a base}} até {{o commit, ou "a árvore de trabalho"}}:
{{n}} arquivos, +{{n}} -{{n}} linhas. Lentes: {{quais}}.
Quem revisou: {{um agente em passes: independência limitada | <n> agentes, 1 por lente}}.

## Cobertura por lente

- **{{lente}}:** li {{o quê}}; conferi {{o quê}}; não consegui conferir {{o quê, e por quê}}.

## Achados

### {{C-01}} · {{crítico | grave | médio | baixo}} · {{o comportamento errado, em uma frase}}

- **Onde:** `{{arquivo}}:{{linha}}`
- **Descrição:** {{o que o código faz e o que devia fazer}}
- **Cenário de falha:** {{a entrada ou o estado concreto}} → {{o resultado errado}}
- **Correção sugerida:** {{o que mudar, e o teste que passa a provar}}

## Veredito por achado

| Achado | Veredito | Severidade | Evidência (arquivo e linha do caminho, ou do trecho que impede) |
| --- | --- | --- | --- |
| {{C-01}} | {{confirmado, confirmado em parte, refutado ou não verificado}} | {{mantida, ou "de médio para baixo, porque …"}} | {{...}} |

## Correções, rodada {{1}}

<!-- A rodada 2 é a última e trata só do que ficou "não resolvido" ou virou regressão. -->

| Achado | O que mudou | Entradas tentadas na reverificação | Resultado |
| --- | --- | --- | --- |
| {{C-01}} | {{arquivos, e o teste que passou a provar}} | {{o vizinho, o inverso, o vazio}} | {{resolvido, não resolvido (com a evidência) ou com o dono}} |

Regressões fora dos itens: {{arquivo e cenário, ou "nenhuma"}}.
Validação depois das correções: {{comando → números}}.
