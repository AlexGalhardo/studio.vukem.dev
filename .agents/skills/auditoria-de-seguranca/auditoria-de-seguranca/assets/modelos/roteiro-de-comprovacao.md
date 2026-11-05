# Roteiro de comprovação

> Uma linha por prova. Só em ambiente local ou de homologação, com usuário e dado de teste.
> Regras em `references/comprovacao.md`. O arquivo preenchido fica em `<auditoria>`, fora do
> repositório.

**Ambiente:** {{local | homologação em <endereço>}} · **Data:** {{dd/mm/aaaa}}

| # | Candidato | Quem pede | O que pede, e de quem é | Esperado | Obtido | Controle (o dono legítimo consegue?) | Resultado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | {{área e arquivo:linha}} | {{usuário de teste}} | {{recurso de outro usuário de teste}} | recusa | {{…}} | {{sim / não}} | {{comprovado / não reproduzido / descartado}} |

## O que guardar de cada prova

Data, ambiente, usuário de teste, o pedido em palavras e a resposta resumida (código de resposta,
contagem de linhas, nome do campo que apareceu). Nunca o conteúdo do registro, valor de chave ou
de sessão, senha ou dado pessoal.

## Provas que não foram feitas

| Candidato | Motivo | Estado no relatório |
| --- | --- | --- |
| {{…}} | {{sem ambiente de teste / exigiria dado real / seria destrutiva}} | encontrado na leitura |
