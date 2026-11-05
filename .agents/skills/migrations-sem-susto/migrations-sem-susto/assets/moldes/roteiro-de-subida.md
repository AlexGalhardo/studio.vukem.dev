# Roteiro de subida: <a mudança, em uma frase> (<AAAA-MM-DD>)

Molde para preencher. É a lista que o dono lê e autoriza: um sim vale para ela inteira, e passo
novo pede lista nova. Apague o que não se aplica e diga que apagou.

## O que muda

- Para quem usa o sistema: <o que aparece de diferente, ou "nada visível">.
- No banco: <as migrations, pelo nome do arquivo, na ordem>.
- Nos dados: <a carga ou o preenchimento, ou "nenhum">.
- No código: <os commits que sobem>.
- Não tem volta: <valor de enum, dado convertido, o que for; ou "tudo tem volta, e a volta é X">.

## As duas perguntas

| Pergunta | Resposta | O que foi rodado para saber |
| --- | --- | --- |
| O código novo funciona com o banco antigo? | <sim ou não> | <o comando e o resultado> |
| O código antigo funciona com o banco novo? | <sim; se não, a mudança não está pronta> | <o comando e o resultado> |

A ordem que sai daí: <banco, dados, código; ou código primeiro, por ser remoção>.

## Portões, todos antes de tocar em produção

- [ ] Validado pelo dono no ambiente local, em <data>.
- [ ] Migrations aplicadas do zero no banco descartável, e sobre um banco com linhas.
- [ ] Testes de banco verdes, e o arquivo gerado do banco sem diferença.
- [ ] `conferir.py <migrations> --base <ref de produção>` com saída 0, ou cada acusação respondida.
- [ ] Estado de produção relido do disco agora: aplicado até <versão>.
- [ ] Tudo commitado, e o envio de código ainda não saiu.
- [ ] Pedido do dono para esta lista, em <data e hora>.

## 1. Banco

- [ ] Histórico do ambiente listado e igual aos arquivos até <versão>.
- [ ] <versão>_<assunto>.sql aplicada pelo canal de migrations. Conferência: <a consulta> deu <o esperado>.
- [ ] <a seguinte, uma por linha>.
- [ ] Histórico listado de novo: as versões são as dos nomes dos arquivos.

Pare se: uma migration falhar, o histórico divergir ou a conferência der outro resultado.

## 2. Dados

- Comando da simulação: <o comando, com o alvo dito pelo nome>.
- Só pode sobrar: <as linhas esperadas, com a contagem>.
- Pare se aparecer: <a linha que não pode aparecer, e o que ela causaria>.

- [ ] Simulação rodada contra o destino e lida linha a linha: sobrou só o previsto.
- [ ] Escrita rodada. Resumo: <alvo e contagem>.

## 3. Código

- [ ] Envio de <os commits> para <o ramo que implanta>.
- [ ] Implantação terminada sem erro.

## Depois

- [ ] No banco: o objeto existe, a função tem as proteções, os privilégios são os previstos.
- [ ] Como visitante, em <o endereço que o dono usa>: <o que contar e o que não pode aparecer>.
- [ ] Estado escrito em <o arquivo>: aplicado até <versão>, em <data>, a pedido de <quem>.

## Não feito, ou com o dono

- <o que ficou de fora, com o motivo>.
- <o que só o dono faz, com o passo escrito para ele>.
- <divergência conhecida, com o que conferir antes da próxima subida>.
