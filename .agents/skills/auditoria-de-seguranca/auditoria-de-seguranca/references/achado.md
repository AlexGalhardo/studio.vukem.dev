# Achado: campos, gravidade e redação

**Leia quando:** passo 5 do fluxo, antes de escrever o primeiro achado.
**Não é aqui:** como comprovar (`references/comprovacao.md`), como gerar o PDF
(`references/relatorio.md`).

## O mínimo

Um achado por problema, em `<auditoria>/achados.json`. Todo achado responde a duas perguntas, e a
gravidade sai delas: o que alguém **consegue**, e o que essa pessoa **precisa** ter para conseguir.
Achado sem as duas respostas não entra no relatório.

## 1. Os campos

| Campo | O que escrever |
| --- | --- |
| `id` | `SEG-001`, em ordem de registro; não muda depois |
| `titulo` | o problema em uma frase que o dono entende |
| `gravidade` | `critico`, `alto`, `medio`, `baixo` ou `informativo` (seção 2) |
| `area` | o nome da área, como em `references/areas.md` §1 |
| `onde` | lista de arquivo e linha, ou de rotas |
| `consegue` | o que a pessoa obtém ou faz, em termos do negócio |
| `precisa` | o que ela precisa ter: nada, uma conta, uma conta paga, acesso interno |
| `cenario` | como o problema aparece, em palavras, sem código de ataque |
| `evidencia` | o que foi visto, e em que ambiente e data |
| `estado` | `comprovado com teste` ou `encontrado na leitura` |
| `correcao` | o que mudar, e em que ordem se houver mais de um passo |
| `esforco` | `pequeno` (até 2 horas), `medio` (até 1 dia) ou `grande` |
| `situacao` | `aberto`, `corrigido` (exige `reconferencia`) ou `aceito` (risco aceito pelo dono) |

`estado` diz como o achado foi encontrado e não muda. `situacao` diz em que pé ele está e muda a
cada reemissão. `python3 <skill>/scripts/relatorio.py <auditoria>/achados.json --so-validar` lista
cada campo que falta.

## 2. A tabela de gravidade

| Gravidade | Consegue | Precisa |
| --- | --- | --- |
| `critico` | ler, alterar ou apagar dado de todos, ou assumir a conta de qualquer pessoa | nada, ou só o que já é público |
| `alto` | o mesmo, sobre dado de outras pessoas | uma conta comum |
| `medio` | acesso indevido limitado, ou algo que depende de condição pouco provável | uma conta e mais uma condição |
| `baixo` | informação que ajuda outro ataque, sem dano direto | qualquer coisa |
| `informativo` | nada hoje; é prática que deixa o sistema mais frágil | não se aplica |

Na dúvida entre duas, escreva o "consegue" e o "precisa" de novo, com mais precisão, e a dúvida
costuma sumir. Gravidade dada pelo susto vira "tudo crítico", e o dono perde a ordem do que
corrigir.

## 3. A redação

- **Título em linguagem de dono.** "Qualquer pessoa logada lê o pedido de outra", e não o nome
  técnico da categoria. A categoria do OWASP vai no cenário, se ajudar.
- **Cenário sem receita.** Descreva a situação e o efeito. O relatório circula: ele não leva
  passo a passo que sirva a quem queira repetir.
- **Segredo nunca aparece.** Escreva o tipo da chave, o arquivo e a linha. O valor, nunca.
- **Correção que o dono confere.** Diga o que muda e como ele vê que mudou.

## 4. Descartados

Candidato que não se sustentou fica em `<auditoria>/descartados.md`, com o trecho do código que
impede a falha. Serve a duas coisas: o dono vê o que foi olhado, e a próxima auditoria não repete
a dúvida.

## 5. Risco aceito

Só o dono aceita um risco. Registre em `reconferencia` a frase dele e a data, e mude `situacao`
para `aceito`. O achado continua no relatório, com esse estado, a cada reemissão.

## O que evitar

- **Juntar dois problemas num achado.** Cada um tem a sua correção e a sua reconferência.
- **Rebaixar para agradar.** A gravidade segue a tabela; o que muda a prioridade é o esforço.
- **Escrever "pode permitir".** Diga quem consegue o quê, ou marque `encontrado na leitura`.

Volte ao `SKILL.md`, passo 6.
