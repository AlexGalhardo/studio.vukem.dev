# Relato: o que dizer ao dono, e como dividir o trabalho entre agentes?

Leia quando: for escolher entre um agente e vários (antes do passo 2) e ao fechar a revisão
(passo 6).
Não é aqui: o texto de cada papel, pronto para colar (`assets/modelos/papeis.md`).

## O mínimo

- O relato conta, não adjetiva: quantos achados, quantos confirmados, refutados e não
  verificados, por severidade.
- Separe três coisas: o que foi verificado rodando, o que foi só lido e o que não foi conferido.
- Achado refutado e achado deixado de fora aparecem, com o motivo. Lista que só tem confirmados
  não mostra o que foi olhado.
- Relatório de agente é alegação. Antes de repassar, quem coordena confere de novo os pontos que
  importam.
- Revisão por leitura não prova ausência de defeito. Diga isso, e diga o que ficou sem olhar.

Conteúdo: 1. O relatório 2. Rodado, lido e não conferido 3. Com um agente só 4. Com vários
agentes 5. O que quem coordena confere de novo 6. Quando algo falha no meio

## 1. O relatório

O formato em branco é `assets/modelos/relatorio.md`; um preenchido,
`assets/modelos/exemplo-preenchido.md`. A ordem:

1. **O que foi revisado e como:** a base, o tamanho, as lentes, quantos agentes ou "um agente em
   passes".
2. **A contagem:** achados, confirmados por severidade, refutados, não verificados, rebaixados.
3. **Confirmados e corrigidos:** título, arquivo e linha, o cenário em uma frase, a correção em
   uma frase, o resultado da reverificação.
4. **Confirmados e não corrigidos:** o que espera decisão do dono, com as opções.
5. **Refutados:** título e o trecho que impede a falha.
6. **Não verificados e deixados de fora de propósito:** os baixos, os além do limite, o defeito
   antigo fora da diferença, o que contraria decisão registrada.
7. **Validação:** rodado, lido, não conferido (§2).
8. **Para subir:** a ordem de subida, se houver banco, e o que o dono precisa fazer.

Escreva para quem não leu a revisão: o cenário em palavras do produto ("quem chega pelo link do
filtro não vê que há filtro ativo"), o arquivo e a linha para quem for conferir. Sem identificador
interno no meio da frase.

## 2. Rodado, lido e não conferido

| Diga | Quando | Exemplo |
| --- | --- | --- |
| **Verifiquei rodando** | um comando rodou nesta revisão e a saída foi lida | "testes de unidade: 212 de 212 em 41 arquivos" |
| **Só li** | a conclusão sai da leitura do código | "a guarda é a primeira linha das 3 ações novas" |
| **Não conferi** | não houve como, ou não houve orçamento | "as telas em 375 px: sem ferramenta de navegador" |

Um achado confirmado por leitura continua "só li". Uma correção vale como verificada quando o
teste que a prova rodou. Falha se relata com a saída, e a segunda execução também.

## 3. Com um agente só

Os papéis viram passes em sequência. A separação possível é de momento e de fonte: cada passe
parte do disco, não da lembrança do anterior.

1. **Delimitar:** rode o script e escreva o contexto comum.
2. **Revisar:** um passe por lente, relendo a diferença em cada um.
3. **Escrever todos os achados** num arquivo, antes de corrigir qualquer um.
4. **Verificar:** reabra o arquivo de achados e o código, e tente refutar cada um pelos cinco
   passos de `references/verificacao.md` §2.
5. **Corrigir, reverificar e validar.**

Diga no relato: "um agente em passes: independência limitada". Este formato é desenho do método:
na revisão de origem cada lente e cada verificação foi um agente separado. Em zona sensível
(`banco`, `pagamento`, `acesso`, `segredo`), proponha ao dono a revisão em outra conversa ou com
vários agentes, e diga quantas leituras ela custa (§4).

## 4. Com vários agentes

| Papel | Quantos | Lê ou escreve | Roda |
| --- | --- | --- | --- |
| Revisor por lente | 1 por lente, em paralelo | só lê | no máximo um arquivo de teste isolado |
| Verificador | 1 por achado acima de baixo, até 4 por lente, em paralelo | só lê | idem |
| Corretor | 1 | o único que edita | lint, tipos e os testes que tocou |
| Reverificador | 1 | só lê | idem ao revisor |
| Validador | 1, junto do reverificador | não edita | o único que roda comando pesado |

- **A conta antes de começar:** lentes + verificações + 3. Com 3 lentes e 6 achados a verificar,
  são 12 leituras. Diga o número ao dono antes; é ele quem paga.
- **Cada agente começa sem o histórico.** Recebe o contexto comum e o papel. É a falta do
  histórico que dá a independência: quem não viu a intenção lê o que está escrito.
- **Não entregue a sua hipótese ao revisor.** Um agente que recebe "acho que o problema é X"
  devolve X confirmado. Entregue a mudança, a lente e as perguntas.
- **O verificador recebe o achado, não o revisor.** Um verificador por achado: com todos juntos,
  ele gasta a atenção no primeiro e concorda com o resto.
- **Um só escreve, um só roda.** Dois corretores na mesma árvore se sobrescrevem; dois comandos
  pesados juntos falham por memória.
- **Peça a resposta em campos fixos** (os de `assets/modelos/achado.md`). Juntar três lentes em
  texto livre é onde o achado se perde ou conta duas vezes.

## 5. O que quem coordena confere de novo

O agente relata no mesmo tom o que fez e o que supôs. Antes de escrever o relato ao dono:

1. **Todo achado confirmado como crítico ou grave:** abra o arquivo na linha e refaça o caminho.
2. **Todo "resolvido":** leia a diferença daquele item. São poucas linhas.
3. **Os números da validação:** leia a saída do comando, não o resumo. Se o resumo diz "tudo
   verde" sem número, rode você o comando mais barato.
4. **`git status --short`:** só os arquivos das correções mudaram, e nenhum revisor editou nada.
5. **O que saiu refutado com severidade alta alegada:** leia o motivo. Refutar errado deixa o
   defeito subir; confirmar errado custa só uma correção à toa.

O que você não conferiu de novo vai ao relato como "relatado pelo agente, não conferido".

## 6. Quando algo falha no meio

| Aconteceu | O que vale |
| --- | --- |
| Um revisor não devolveu resultado | a lente conta como "não revisada", nunca como "sem achados"; refaça ou diga |
| O verificador não respondeu | o achado fica "não verificado" e não é corrigido às cegas |
| A revisão foi cortada por orçamento | diga quais lentes e verificações faltaram, no topo do relato |
| A validação não rodou | o relato diz "correções não validadas rodando", e a subida espera |
| O ambiente travou | relate o estado; não reinicie à força o que é do dono |

## O que evitar

- **"Revisão feita, tudo certo."** Não diz quantas lentes, o que foi refutado nem o que rodou.
  O dono não tem como saber se pode subir.
- **Esconder o refutado para a lista parecer limpa.** O refutado mostra o que foi atacado e
  evita que a próxima revisão gaste a mesma leitura.
- **Repetir segredo, ou trecho de arquivo de ambiente, no relato.** O relato é copiado para
  outros lugares.

## Pronto quando

- [ ] A contagem fecha: confirmados + refutados + não verificados = achados.
- [ ] Rodado, lido e não conferido estão separados, com números no que rodou.
- [ ] O refutado e o deixado de fora têm motivo.
- [ ] Os pontos da §5 foram conferidos por quem coordena, ou marcados como não conferidos.
- [ ] Com um agente só, o relato diz "independência limitada".

Volte ao `SKILL.md`.
