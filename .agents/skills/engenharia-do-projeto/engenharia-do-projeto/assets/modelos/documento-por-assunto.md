<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# {{Assunto}} ({{planejado ou implementado}})

> **Estado:** {{implementado na Fase N, em `arquivos`; ou planejado para a Fase N}}.
> **Fonte da verdade:** `{{código, esquema ou migrações}}`. Este documento descreve o que está lá:
> se divergirem, o código manda e este documento é corrigido. Mudou o código: atualize aqui na
> mesma mudança.
> **Vizinhos:** {{outro assunto}} em `docs/{{outro}}.md`.

<!-- Um documento por assunto em que errar custa caro, não por pasta nem por funcionalidade. Não
tem linha nem coluna de estado do ambiente remoto: esse dado mora em docs/ESTADO.md. Número que o
sistema sabe contar não se escreve aqui. Apague este comentário ao preencher. -->

## {{Tabela de consulta: matriz, limites ou nomes}}

| {{O quê}} | {{Valor}} | {{Observação}} |
| --- | --- | --- |
| {{item}} | {{valor}} | {{observação}} |

## Regras

- {{Regra do assunto}}, porque {{o porquê}} ({{ADR-NNN}}).

## Como {{fazer a tarefa recorrente}}

1. {{O que escrever, com as regras do assunto.}}
2. {{O comando de verificação e o que deve sair.}}
3. {{Gerar o que é gerado e versionar.}}
4. {{Testes a escrever ou ajustar.}}
5. Atualize este documento e, se for decisão, o registro em `docs/decisoes.md`.
6. Ambiente remoto: só com a lista que o dono autorizou.

## O que os testes cobrem

- `{{arquivo de teste}}`: {{o que prova}}

## Checklist

- [ ] {{item verificável do assunto}}
