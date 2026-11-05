---
name: revisor-de-codigo
description: Revisa uma mudança de código antes de ela ir para produção, de forma adversarial, em qualquer linguagem. Revisores com lentes diferentes (banco e implantação, segurança e fronteiras, comportamento, qualidade dos testes) procuram defeito real, e cada achado passa por uma segunda leitura que tenta refutá-lo. Delimita o que mudou por zona com um script que só lê o git, exige cenário concreto de falha em todo achado, rebaixa a severidade às claras, corrige o mínimo, confere cada correção e entrega um relatório que separa o confirmado, o refutado e o que foi só lido. Funciona com um agente só ou com vários. Use quando o usuário disser "revisa essa mudança", "revisa meu PR", "faz um code review", "posso subir isso?", "confere antes do deploy", "acha os bugs do que eu fiz" ou "revisa o que o outro agente escreveu", mesmo sem dizer revisão. Não use para auditar o sistema inteiro sem uma mudança delimitada, para opinar sobre estilo ou arquitetura, nem no lugar de teste automatizado.
---

# Revisor de código

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).


`<skill>` é a pasta deste arquivo; `<projeto>`, a raiz do repositório do dono.

- **A revisão parte da diferença do git.** Quem escreveu relê a intenção; o git mostra o que mudou.
- **Uma lente por leitura.** Banco e implantação, segurança e fronteiras, comportamento, testes.
  Duas ao mesmo tempo viram uma olhada geral.
- **Sem cenário não é achado.** Todo achado diz a entrada ou o estado que leva ao resultado
  errado. Estilo, preferência e "poderia ser melhor" não entram.
- **Todo achado é atacado antes de ser aceito.** Uma segunda leitura tenta refutá-lo seguindo o
  caminho de código de verdade. Só fica o que tem caminho até a falha.
- **Relatório de agente é alegação.** O ponto que importa é conferido de novo por quem coordena.

Funciona porque quem procura o defeito e quem decide se ele existe são leituras diferentes: o
revisor tende a inflar, o verificador existe para derrubar, e o que sobra dos dois é o que vale
corrigir. O teste antes de agir: sei qual é a base, que lentes a mudança pede e quem vai tentar
refutar cada achado?

O método saiu de uma revisão real, de uma mudança com migration, tela pública e ferramenta de
carga: 9 leituras entre revisões e verificações, nenhum achado crítico ou grave, 2 médios
confirmados (um título por baixo de um botão no celular; um filtro ativo invisível para quem
chegava por um link), vários rebaixados de médio para baixo e um erro na ordem de subida que só
a lente de banco viu. Revisão por leitura não prova ausência de defeito: não pega o que só
aparece rodando (corrida, desempenho, memória), nem o que está fora da diferença.

## Preparar

1. Rode o script, que só lê o git:

   ```bash
   python3 <skill>/scripts/escopo.py <projeto> [--base <ramo, tag ou commit>]
   # → a base, os arquivos por zona com +linhas e -linhas, "lentes pedidas:", "aviso:", "nota:"
   # Saída 0 sem aviso, 1 com aviso, 2 uso errado ou git falhou, 3 nada mudou
   ```

2. Leia o arquivo de instruções do projeto e ache os comandos de verificação (lint, tipos,
   testes) e as regras escritas: é contra elas que a lente de segurança confere.
3. Pergunte a quem escreveu, pessoa ou agente, o que considera frágil.

- **Requisitos:** git e Python 3.8 ou mais novo, só para o script, que rodou em macOS com
  Python 3.14 e git 2.50. Sem Python: `git status --short` e `git diff --stat <base>`, com as
  zonas de `references/escopo.md` §3 aplicadas à mão.
- **O script não abre arquivo de ambiente** (`.env` e parecidos), e você também não.

## Qual revisão cabe

| Situação | Sinal | O que fazer | Leia |
| --- | --- | --- | --- |
| Só documentação | "lentes pedidas: nenhuma" | leia a diferença uma vez; sem verificação | nenhuma ficha |
| Mudança fora de zona sensível | só `interface`, `outros` e `testes`, sem aviso | um agente em passes, pelas lentes pedidas | `references/relato.md` §3 |
| Zona sensível | `banco`, `pagamento`, `acesso` ou `segredo` na saída | todas as lentes pedidas; proponha vários agentes | `references/relato.md` §4 |
| Mudança grande | aviso de mais de 800 linhas ou 40 arquivos | divida por zona, uma revisão por parte | `references/escopo.md` §5 |
| Código de outro agente | um relatório dizendo que tudo passou | a mesma revisão; o relatório é alegação | `references/relato.md` §5 |

## Fluxo

### 1. Delimite

Confirme a base na primeira linha da saída do script e responda a cada aviso. Escreva o contexto
comum: o que a mudança faz em até 5 itens, o que o autor relatou como frágil, o que pode rodar e
o que é proibido. Detalhes: `references/escopo.md`.
**Confira:** arquivo de `outros` que lê dado restrito ganhou a lente de segurança à mão.
**Pronto quando:** a lista de lentes está escrita, com o motivo de cada uma.

### 2. Revise, uma lente por leitura

Para cada lente, adapte de 4 a 6 perguntas de `references/lentes.md` aos arquivos da mudança e
leia a diferença e o código em volta. Arquivo novo se lê inteiro. Nesta etapa nada é corrigido.
**Confira:** cada lente devolveu a cobertura: o que leu e o que não conseguiu conferir.
**Pronto quando:** todos os achados estão escritos no formato de `assets/modelos/achado.md`.

### 3. Verifique cada achado

Para todo achado acima de baixo, até 4 por lente, uma segunda leitura tenta refutar: abre a
linha, sobe até quem chama, desce até o efeito. Detalhes: `references/verificacao.md` §2 e §3.
**Confira:** cada veredito cita arquivo e linha do caminho até a falha, ou do trecho que a impede.
**Pronto quando:** cada achado está confirmado, confirmado em parte, refutado ou não verificado.

### 4. Corrija o mínimo

Só o confirmado, do mais grave ao mais leve, pela menor mudança que fecha o cenário, com o teste
que passa a prová-lo. Sem commit. O que contraria decisão registrada ou pede migration nova vai
ao dono: `references/verificacao.md` §4.
**Confira:** a diferença das correções toca só o que os achados pedem.
**Pronto quando:** cada correção está descrita em uma ou duas frases, numerada.

### 5. Reverifique e valide

Uma leitura cética confere cada correção contra o achado original, procurando a entrada que
ainda quebra, e aponta regressão fora dos itens. Depois, a verificação do projeto roda, um
comando pesado por vez: `references/verificacao.md` §5 a §7.
**Confira:** teste que falhou rodou de novo isolado, uma vez, e as duas saídas foram guardadas.
**Pronto quando:** cada item está resolvido ou não resolvido, com evidência, em até 2 rodadas.

### 6. Relate ao dono

Preencha `assets/modelos/relatorio.md`; há um preenchido em
`assets/modelos/exemplo-preenchido.md`. Antes de enviar, confira você mesmo os pontos de
`references/relato.md` §5.
**Confira:** confirmados + refutados + não verificados = achados.
**Pronto quando:** o relato separa rodado, lido e não conferido, e responde "posso subir?".

## Regras inegociáveis

1. **Todo achado tem cenário concreto de falha.** Se não, a lista enche de opinião e o defeito
   real se perde no meio.
2. **Todos os achados são escritos antes de qualquer correção.** Se não, a correção apaga a
   evidência e o achado seguinte nunca é escrito.
3. **Nenhum achado é corrigido sem veredito.** Se não, corrige-se o que não existe, e a
   correção vira a regressão.
4. **Rebaixamento diz de quanto para quanto e por quê.** Sem motivo, ele esconde o achado.
5. **Achado refutado sai da lista e fica no relato, com o motivo.** Se sumir, a próxima revisão
   gasta a mesma leitura.
6. **Revisor e verificador só leem,** e rodam no máximo um arquivo de teste isolado. Se não,
   dois agentes mexem na mesma árvore e ninguém sabe o que foi revisado.
7. **A correção faz só o que o achado pede.** Melhoria feita no caminho não passou por revisão.
8. **O relato separa o que rodou do que foi lido.** Se não, o dono sobe confiando num teste que
   ninguém executou.
9. **Nenhum papel abre arquivo de ambiente nem repete segredo.** O relato é copiado adiante.

## Pare e pergunte ao dono

- **Só o dono decide:** enviar o código, aplicar migration no banco remoto, subir com achado
  confirmado em aberto e desfazer uma decisão registrada do projeto.
- **Pergunte antes:** a base, se a escolhida sozinha não for o que está em produção; quantas
  leituras a revisão com vários agentes vai gastar; correção que pede migration, dependência
  nova ou muda regra do produto; rodar a suíte pesada numa máquina que ele está usando.
- **Arquivo de ambiente no diff:** pare e avise. Não abra para conferir.

## Armadilhas já vistas

- **Dez achados, todos "poderia ser melhor".** Faltou no texto do revisor a frase que proíbe
  estilo e exige cenário: `assets/modelos/papeis.md`.
- **O achado mais grave era falso.** O revisor leu o trecho e não quem o chama; o tratamento
  estava um nível acima: `references/verificacao.md` §2.
- **O código estava certo e a subida quebraria.** O código novo dependia de um valor que o banco
  ainda não tinha. Só a lente de banco pergunta a ordem nos dois sentidos:
  `references/lentes.md` §2.
- **Passava em todo teste e estava quebrado no celular.** Um título ficava por baixo de um botão
  em 375 px, e nenhum teste perguntava isso: `references/lentes.md` §4.
- **A correção fechou o caso do achado e deixou o vizinho aberto.** O reverificador não recebeu
  as entradas a tentar: `references/verificacao.md` §5.
- **O teste novo oscilava e ganhou uma espera longa.** A espera esconde a corrida:
  `references/lentes.md` §5.
- **"Tudo verde" sem número.** O resumo do agente não era a saída do comando; e revisão cortada
  por orçamento se diz no topo do relato: `references/relato.md` §5 e §6.

Irmãs, se instaladas: `migrations-sem-susto` escreve a migration e a subida que a lente de banco
revisa; `vazamento-de-paywall` prova que conteúdo pago não sai do servidor;
`ponta-a-ponta-com-personas` percorre os fluxos rodando, o que esta skill só lê. Auditar a
segurança do sistema inteiro é trabalho de uma skill de auditoria, não desta.

## Arquivos

| Arquivo | O que traz | Abra quando |
| --- | --- | --- |
| `references/escopo.md` | a base, as zonas, das zonas às lentes, mudança grande, os avisos | passo 1 |
| `references/lentes.md` | as perguntas de cada lente e o que não é achado | passo 2 |
| `references/verificacao.md` | o achado, refutar, veredito e severidade, corrigir, reverificar, validar | passos 3 a 5 |
| `references/relato.md` | o relatório, um agente ou vários, o que conferir de novo | antes do passo 2; passo 6 |
| `assets/modelos/papeis.md` | contexto comum e o texto de revisor, verificador, corretor, reverificador e validador | ao entregar um papel |
| `assets/modelos/achado.md` | o achado, o veredito e a tabela de correções, em branco | passo 2 |
| `assets/modelos/relatorio.md` | o relatório ao dono, em branco | passo 6 |
| `assets/modelos/exemplo-preenchido.md` | um achado e um relatório fictícios, preenchidos | na primeira revisão |
| `assets/modelos/zonas.ini` | modelo de `.revisor.ini`: zonas e lentes do projeto | as pastas fogem do padrão |
| `scripts/escopo.py` | base, arquivos por zona, lentes pedidas e avisos; `--help` | antes de toda revisão |
