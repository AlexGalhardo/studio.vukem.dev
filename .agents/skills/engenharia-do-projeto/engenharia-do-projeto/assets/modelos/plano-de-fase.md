<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Plano · {{fase ou mudança}}

<!-- Uma página, para o peso médio. Grave em docs/planos/. Se não couber em uma página, a fase pede
     o plano-contrato ou são duas fases. Apague os comentários ao preencher. -->

Escrito em {{AAAA-MM-DD}}, sobre o commit {{abreviado}}. Regras desta rodada: {{as proibições, cada
uma com a consequência; o que já está liberado}}.

## Objetivo e "Pronto quando"

{{Uma frase: o que o dono passa a conseguir fazer.}}

{{Os itens de "Pronto quando": aponte a fase do roteiro; fora de uma fase, escreva-os aqui.}}

## Decisões

<!-- Decisão que alguém desfaria por engano vira registro ao fechar; até lá, cite por A-01. -->

| # | Decisão | Motivo | Plano B, e o que o aciona |
| --- | --- | --- | --- |
| A-01 | {{o que se faz, dito de modo que se ache no código}} | {{por quê}} | {{o gatilho, e o que fazer se ele acontecer}} |

## Mapa de arquivos por pacote

<!-- De dois a quatro pacotes, em ordem, um por vez. Marca: N novo, A alterado, X apagado. Cada
     arquivo tem um dono só. -->

| Pacote | Arquivo | Marca | Papel |
| --- | --- | --- | --- |
| P1 · {{nome}} | {{caminho}} | N | {{para que serve}} |

## Aceite por comando

<!-- Um bloco por pacote, rodado como escrito. Todo pacote termina com os degraus 0 a 2 verdes. -->

```bash
{{comando do P1}}     # → {{saída esperada}}
```

## O que não muda

- {{Área ou arquivo que fica como está, e o teste que precisa continuar passando.}}

## Perguntas com decisão padrão

| Ponto, como o dono vê | Padrão adotado | Se o dono quiser diferente |
| --- | --- | --- |
| {{o que a pessoa vê}} | {{o que será feito}} | {{o que muda, e onde}} |
