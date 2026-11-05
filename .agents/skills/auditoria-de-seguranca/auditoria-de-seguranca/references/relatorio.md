# Relatório: montar, conferir, entregar e reemitir

**Leia quando:** passos 6 e 7 do fluxo.
**Não é aqui:** os campos do achado (`references/achado.md`).

## O mínimo

O relatório sai de `<auditoria>/achados.json` por `scripts/relatorio.py`, em PDF e em Markdown. O
script valida antes de gerar e recusa se faltar campo. O relatório fica fora do repositório: ele é
o mapa das falhas ainda abertas.

## 1. As seções, na ordem

1. **Capa:** sistema, data, versão, quem pediu, quem auditou e a confirmação do escopo.
2. **Resumo executivo**, em uma página: a contagem por gravidade, o parecer e até três riscos
   principais, em linguagem de dono.
3. **Escopo e método:** o que entrou, o que ficou de fora, os ambientes, o que foi testado e o que
   NÃO foi testado.
4. **Achados por gravidade:** do crítico ao informativo, cada um com todos os campos.
5. **Plano de correção:** os abertos em ordem, pela gravidade e depois pelo esforço.
6. **O que esta auditoria não cobre.**

Sem Python, escreva o Markdown à mão nessa mesma ordem.

## 2. O bloco `relatorio` do arquivo

Além da lista `achados`, o arquivo tem um bloco `relatorio` com: `sistema`, `data`, `versao`,
`pedido_por`, `auditado_por`, `confirmacao_de_escopo`, `escopo` (`dentro`, `fora`, `ambientes`),
`metodo` (`testado`, `nao_testado`), `resumo` (`parecer`, `riscos_principais`) e `nao_cobre`.
Parta de `assets/modelos/achados-em-branco.json`; `assets/modelos/achados.json` mostra tudo
preenchido, com um sistema fictício.

## 3. O resumo executivo

- **Parecer:** duas ou três frases. Diga o estado geral e o que resolver primeiro.
- **Riscos principais:** no máximo três, cada um como consequência para o negócio ("um visitante
  apaga os pedidos"), e não como nome de falha. Havendo achado aberto, a lista não pode vir vazia.
- Os textos têm teto de caracteres para o resumo caber em uma página; o script avisa se passar.

## 4. Gerar

```bash
python3 <skill>/scripts/relatorio.py <auditoria>/achados.json --so-validar
# → sai 0 se o arquivo está completo; 1 lista cada campo que falta
python3 <skill>/scripts/relatorio.py <auditoria>/achados.json
# → relatorio-de-seguranca-v<versão>.pdf e .md, na pasta do arquivo de achados
```

Saída 3 é "gerado com aviso": campo desconhecido, ou caractere que o PDF não tem (emoji, alfabeto
não latino) trocado por "?". O Markdown guarda o texto original.

## 5. Conferir antes de entregar

Abra o PDF e olhe: a capa traz o sistema e a data certos; o resumo cabe em uma página e a contagem
bate com o número de achados; os acentos saíram; nenhuma página traz valor de chave, senha ou dado
de pessoa de verdade. Entregue o caminho do arquivo e, na conversa, a contagem por gravidade e os
três riscos.

## 6. Reemitir depois da correção

Para cada achado que o dono corrigiu: repita a mesma prova (`references/comprovacao.md` §2),
escreva em `reconferencia` o que foi visto e a data, e mude `situacao` para `corrigido`. Some 1 em
`versao`, troque `data` e gere de novo. A versão anterior fica guardada: a diferença entre as duas
é o registro do que foi resolvido.

## O que evitar

- **Editar o PDF à mão.** A fonte é o arquivo de achados; o que não está nele some na reemissão.
- **Mandar o relatório por canal aberto.** Combine com o dono para onde ele vai.
- **Prometer que está seguro.** O relatório diz o que foi olhado e o que ficou de fora. Ele não
  substitui um teste de invasão profissional.

Volte ao `SKILL.md`, passo 7.
