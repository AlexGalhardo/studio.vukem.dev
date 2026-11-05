<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Levantamento · {{fase ou projeto}} ({{AAAA-MM-DD}})

<!-- Só leitura: nada é criado, alterado nem commitado além deste arquivo. Grave em docs/planos/.
     Fato e sugestão não se misturam: proposta de quem pesquisa começa por "Sugestão:". Fato que
     sustenta decisão leva a etiqueta de origem: [medido], [documentação da versão instalada] ou
     [memória]. Levantamento de plataforma abre com "As conclusões que mais mudam a arquitetura".
     Na adoção de um projeto que já existe, separe em cada seção "Rodei e vi" de "Inferi". Apague
     os comentários ao preencher. -->

- **Commit de base:** {{abreviado}}, {{árvore limpa, ou o que estava alterado}}. No ar: {{o quê}}.
- **Li:** {{arquivos, pastas, documentos, banco do ambiente local, documentação instalada}}.
- **Não li:** {{o que ficou de fora, e por quê}}.
- **Não pude medir:** {{o quê, e onde repetir a medição}}.
- **Precedência:** {{o que vale quando os documentos divergem}}.
- **Regras desta rodada:** {{lista}}.

## A. Requisitos

- **R-01 · {{requisito}}.** {{Detalhe.}} Fonte: {{onde está escrito}}. Pronto quando: {{critério
  que se observa}}.

## B. Restrições

| Decisão ou regra | O que obriga | Onde bate nesta fase |
| --- | --- | --- |
| {{registro ou regra inegociável}} | {{o que obriga}} | {{arquivo ou fluxo}} |

## C. Inventário do que existe e padrões a seguir

- {{O que já existe e serve}}, em {{caminho}}. {{O padrão a seguir.}} {{"Não refazer", se já foi
  feito.}}

## D. Dados

{{O que cada persona lê hoje. Como estão os dados de exemplo. O que precisa mudar.}}

## E. Testes e CI

{{Como as sessões de teste nascem. As personas. O que um teste novo precisa respeitar. O que os
testes atuais esperam e esta fase muda.}}

## F. Riscos e lacunas

- **F-01 · {{problema}}.** {{Por que importa.}} **Sugestão:** {{a decisão proposta e a
  alternativa}}.
- **F-02 · Contradições entre documentos e de processo.** {{O que diverge, e a saída de cada uma.}}

**Os riscos que mais pesam:** {{até dez, pelo identificador}}.
