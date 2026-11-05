<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# {{Produto}}

{{O que é, em um parágrafo, para quem chega agora. Sem contagem que muda.}}

<!-- Fala com quem chega e com quem opera. Regra do agente e estado moram em outros arquivos. -->
## Requisitos

| Você precisa de | Versão | Por quê |
| --- | --- | --- |
| {{ferramenta}} | {{versão mínima}} | {{o que deixa de funcionar sem ela}} |

## Começando

```bash
{{comando 1}}     # {{o que faz}}
{{comando 2}}     # {{o que faz; o que precisa estar no ar}}
# depois, abra {{endereço local}}: você deve ver {{o quê}}
```

## Comandos

| Comando | O que faz | Precisa de |
| --- | --- | --- |
| `{{comando}}` | {{o que faz}} | {{o que tem de estar no ar}} |

## CI

- {{Estágio}}: {{o que roda e por que é assim}}.

## Banco

- **Fluxo local:** {{como subir, aplicar as migrações e carregar os dados de exemplo (seed)}}.
- **Contas de teste, só no ambiente local:** {{conta}} é {{persona}}.
- **Produção:** o que está aplicado e o que falta está em `docs/ESTADO.md`, em "Ambientes".

## Passos do dono: {{serviço externo}}

1. **{{Painel, menu}}:** {{valor exato do campo}}. {{O porquê, em uma frase.}} Sem isso,
   {{o que o produto faz: por exemplo, abre e mostra um aviso}}.

## Testes

{{Como subir o que os testes precisam.}} {{O que cada pasta de teste prova, uma linha cada.}} O
resultado da última rodada, com a data, está em `docs/ESTADO.md`.

## Documentação

- `ESPECIFICACAO.md`: o que o produto é para ser.
- `{{arquivo de instruções}}`: regras e mapa do código, para o agente.
- `docs/decisoes.md`: o porquê de cada decisão.
- `docs/ROTEIRO.md`: as fases e o que conta como pronto.
- `docs/ESTADO.md`: onde o projeto está hoje e o que depende de você.

## Fases

A lista e a fase atual estão em `docs/ROTEIRO.md`.
