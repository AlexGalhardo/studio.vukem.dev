# Interface: como transformar gosto em critério medido antes de uma mudança visual grande?

Variante. Só vale para projeto com interface.

Leia quando: antes de uma fase de telas ou de um redesenho. O dono diz "deixa bonito" ou "parecido
com o site X".
Não é aqui: referência com regras de uso: o que é lei, o que é enfeite, o que não copiar
(`references/especificacao.md` §4).
**Base:** proposta. O briefing vem de uso real, mas o resultado de executá-lo não foi visto, e a §6
(como perguntar gosto) é desenho deste método, sem uso anterior: confira com capturas de tela
antes de dar por pronto.

## O mínimo

- Gosto vira critério medido: "bonito" não se confere; "uma cor de ação, título de N pontos" sim.
- A referência entra pelo que foi medido nela, com data: o site muda, a medida fica.
- Toda tela tem três estados escritos: carregando, vazio e erro.
- Escreva o que não muda: as áreas intocadas e os testes que continuam verdes.
- Preencha `assets/modelos/briefing-visual.md` antes do código e grave em
  `docs/planos/briefing-<área>.md`: sem ele, cada sessão decide pelo próprio gosto.

Conteúdo: 1. Medir 2. As seis partes 3. Proibido e desejado 4. O que não muda 5. Estados 6. Gosto

## 1. Medir a referência

Anote o valor lido na referência, não a impressão; o que foi estimado por captura leva "estimado".

| Meça | O que anotar |
| --- | --- |
| Fonte | Família, tamanhos de título e de texto, pesos, altura de linha, espaço entre letras |
| Cores | Os valores; qual é a de ação; quantas de destaque aparecem na mesma tela |
| Espaçamento e forma | Raios, bordas, espaço entre seções, largura máxima da linha de texto |
| Densidade | Blocos por tela, espaço vazio, a ordem dos blocos de cada página, de cima a baixo |

Date a medição no título da parte 0 ("medido em AAAA-MM-DD"). Sem site de referência, a parte 0
vira "o que o produto atual faz, medido".

## 2. O briefing em seis partes

É o contrato da mudança visual. Abre com o pedido do dono, literal e numerado, e com um princípio
de desempate em três palavras, que decide onde o texto for omisso.

| Parte | O que entra |
| --- | --- |
| 0. O que a referência faz | As medidas da §1, com a data |
| 1. Sistema visual | Variáveis de estilo, uma coluna por tema. Uso de cada cor (uma é de ação; a de destaque, só em lugares nomeados). Escala de fonte. Forma e ritmo. Proibido e desejado (§3). Texto: tom, palavras banidas, o texto de cada bloco e a variação para quando um dado falta |
| 2. Marca | O que pode usar e o que não pode |
| 3. Componentes e páginas | A ordem dos blocos de cada página, os estados (§5) e os componentes compartilhados, com as propriedades e quem cria primeiro |
| 4. O que não muda | §4 |
| 5. O que não copiar | O que a referência tem e o produto não terá |

## 3. Proibido e desejado

Duas listas na parte 1, escritas pelo que se vê na tela, não por adjetivo: cada item se confere
numa captura. Os exemplos mostram a forma; o conteúdo sai da medição e das respostas do dono.

- **Proibido**, como exemplo: fundo em gradiente colorido, vidro fosco, emoji, três cores de
  destaque na mesma tela, título com exclamação, texto longo centralizado.
- **Desejado**, como exemplo: imagem real do produto, espaço vazio, uma cor de destaque por bloco,
  bordas finas, alinhamento à esquerda.

## 4. O que não muda

- **Áreas intocadas**, pelo nome, e os testes que precisam continuar verdes.
- **Nomes das variáveis de estilo:** ficam, e passam a apontar para valores que trocam com o tema.
  É o que impede a mudança de quebrar o que existe.
- **Regra do projeto em que a mudança esbarra:** lembre-a no briefing e dê a saída. Se o preço tem
  de vir do serviço de cobrança, o texto traz a frase para quando ele falta, e não um preço fixo.
- **Teste que quebra por texto que o briefing manda mudar:** ajuste o localizador, não a regra.

## 5. Estados de toda tela e regra com número

Para cada página, escreva na parte 3 o que aparece em cada estado. **Carregando:** o que ocupa o
lugar do conteúdo. **Vazio:** a mensagem e o próximo passo; pesa mais quando o produto vai ao ar
sem nada cadastrado. **Erro:** a mensagem e a saída (tentar de novo, voltar).

Regra visual leva número e unidade. Estes são exemplos de forma, não regra geral: "alvo de toque
de pelo menos N pontos"; "celular primeiro, conferido em duas larguras"; "linha de texto com até N
caracteres". Cada uma entra no bloco de regras do arquivo de instruções com quem a verifica (os
níveis estão em `references/instrucoes.md` §4). "Toda tela tem os três estados" costuma ser
revisão manual: diga isso na regra.

## 6. Como perguntar gosto a quem não é designer, e conferir por captura

1. Peça de uma a três referências de que o dono gosta, o que ele gosta em cada uma, e uma de que
   não gosta. "Que estilo prefere?" não tem resposta em abstrato.
2. Pergunte por pares, pelo efeito, cada par com o padrão que será adotado (a forma está em
   `references/dono.md` §2): mais espaço vazio ou mais informação por tela; uma cor de destaque ou
   várias; texto sério ou descontraído.
3. Transforme cada resposta em uma linha do briefing, com número. O que o dono não disse entra em
   "Decidi sem perguntar": qual cor é a de ação, por exemplo.
4. Faça primeiro a tela mais representativa e mostre-a por captura, em duas larguras e em cada
   tema, antes das outras.
5. Antes de dar por pronto, capture cada página em cada estado e compare com os números do
   briefing. Sem como capturar na sessão, diga isso em "Não rodei" e entregue ao dono o roteiro de
   validação com o que abrir.

## O que evitar

- **"Deixa bonito" rende um estilo por sessão.** Faltou o contrato. Escreva o briefing antes do
  código, com as medidas.
- **A cor da marca usada como texto passa no contraste num tema e falha no outro.** Dê a ela uma
  variável própria para texto e confira nos dois temas.
- **A tela pisca ao abrir, porque o tema é aplicado depois de a página aparecer.** Leia a
  preferência antes do primeiro quadro.

## Pronto quando

- [ ] O briefing está gravado, com a referência medida e datada e com "O que não muda" preenchido.
- [ ] Toda regra visual tem número e unidade, e diz quem a verifica.
- [ ] Cada página traz o que aparece em carregando, vazio e erro.
- [ ] O dono viu a primeira tela por captura, em duas larguras, e deu a palavra de liberação.

Volte ao `SKILL.md`, §4.
