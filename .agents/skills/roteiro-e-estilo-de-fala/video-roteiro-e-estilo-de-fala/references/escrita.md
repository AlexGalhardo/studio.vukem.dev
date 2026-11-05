# Padrão de escrita: soar como gente, não como IA

Vale para toda narração escrita por esta skill. O roteiro é feito para ser **dito em voz alta**, não lido.

## Antes de escrever

1. **Uma tese por vídeo**, e ela cabe numa frase. Se não cabe, tem ideia demais: corte ou vira dois vídeos.
2. **Uma tese por parte.** Cada agente roteirista escreve a frase da parte dele antes do primeiro parágrafo.
3. **Orçamento de palavras.** O número vem da ficha de estilo (palavras ÷ ppm). Escrever "umas 3 páginas" não é medida.

## Ritmo

- Alterne o tamanho das frases: duas ou três na média da ficha e uma curta. Frase curta é onde a ideia bate.
- Deixe a muleta onde ela cai na fala real — na virada, não no meio da informação. A ficha diz quantas por mil palavras.
- Um bordão por parte, no máximo. Dois seguidos viram paródia.
- Pergunta é a virada mais barata e a mais gasta: use na proporção que a ficha mostra, não mais.

## Proibido

- **Fechar com "não é X, é Y".** É a assinatura mais reconhecível de texto de IA. Negar a causa óbvia numa frase e
  expandir a causa nova na seguinte, com detalhe, continua valendo — o que está banido é a fórmula seca de encerramento.
- **Marcador de seção dentro da fala**: `[0-3s]`, `HOOK`, `CTA`, `B-ROLL:`, nome de arquivo. Quem grava lê em voz alta
  o que estiver ali. Tudo isso é do arquivo de edição.
- **Número por extenso.** `6 etapas`, `40 minutos`, `3 fontes` — sempre em algarismo.
- **Vocabulário genérico**: clareza, barulho, propósito, "real" como adjetivo, "isso muda tudo", "nesse sentido",
  "em suma", "vale ressaltar", "é importante destacar", "mergulhe", "desvendar".
- **Frase com sujeito oculto quando há um referente claro.** Diga o nome, o pronome ou a profissão.
- **Reapresentar o vídeo no meio dele.** "Como eu disse", "neste vídeo eu vou mostrar" só na parte 01.
- **Adjetivo no lugar de dado.** "Enorme" não sobrevive a uma conferência; "4 vezes maior" sobrevive, se estiver na pesquisa.

## Especificidade

Termo concreto vence termo vago, sempre. `3 meses sem resposta` carrega mais do que `muito tempo parado`. Todo número
e toda data saem da pesquisa, com `fato_id`; número sem fonte é opinião com cara de dado — e quem publica paga por ele.

## Abertura e fecho

- A abertura cria dissonância nos primeiros segundos: ela não apresenta o tema de forma neutra. Olhe as aberturas
  reais da ficha de estilo: elas mostram como **essa pessoa** entra no assunto.
- O fecho não resume o vídeo inteiro. Ele entrega a consequência da tese e chama uma ação compatível com o formato.
- Quando o vídeo depende da abertura, escreva 5 opções e deixe o usuário escolher: 3 que atacam uma crença do público
  e 2 de curiosidade ou autoridade. Cada uma precisa funcionar sozinha, e nenhuma repete frase já usada no corpo.

## Checklist antes de mandar gravar

- [ ] A tese cabe numa frase, e cada parte tem a dela?
- [ ] O total de palavras bate com a duração combinada (±15 %)?
- [ ] Nenhum parágrafo fecha com "não é X, é Y"?
- [ ] Todos os números estão em algarismo e todos têm `fato_id`?
- [ ] Nenhuma palavra da lista banida?
- [ ] Nenhuma marcação de tela dentro da narração?
- [ ] As muletas estão na proporção da ficha, e nenhum bordão aparece duas vezes seguidas?
- [ ] Nenhuma frase se repete entre duas partes (`juntar.py` reprova)?
- [ ] Toda subseção tem pelo menos um bloco de edição, e todo bloco tem um `fala` literal?
- [ ] Lido em voz alta, sem tropeço — e no tempo previsto?
