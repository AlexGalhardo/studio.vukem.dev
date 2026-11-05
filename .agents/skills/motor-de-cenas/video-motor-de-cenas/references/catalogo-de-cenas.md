# Catálogo de cenas do motor

Gerado por `scripts/catalogo.py --md`. Todas aceitam, além do que está aqui: `palco`
(cartao·cheia·abre·fecha), `camera` (parada·aproxima·afasta), `chapeu`, `fonte`, `plataforma`
e `reservar_legenda`.

## cartela

Cartela de troca de assunto: sobretítulo, título, filete e contador de capítulo.

- duração padrão: 4 s · alfa: não

  - titulo (texto, obrigatório) — o assunto que começa agora
  - sobretitulo (texto, padrão null) — texto curto acima (ex.: "Parte 2")
  - subtitulo (texto, padrão null) — linha de apoio
  - capitulo (inteiro (1…), padrão null) — número deste capítulo (acende no contador)
  - de (inteiro (1…), padrão null) — total de capítulos (desenha o contador inteiro)
  - alinhar (opcao, padrão "esquerda") [esquerda, centro]

## citacao

Citação na DA (aspas, autor, fonte) com carimbo de estado — "confirmado", "negou", "sem resposta".

- duração padrão: 6 s · alfa: não

  - texto (texto, obrigatório) — a frase citada, sem aspas (o kit põe)
  - autor (texto, padrão null) — quem disse
  - cargo (texto, padrão null) — cargo ou contexto
  - foto (arquivo, padrão null) — foto do autor
  - carimbo (texto, padrão null) — texto do carimbo (curto, em caixa alta)
  - cor_carimbo (cor, padrão "negativo") — token do carimbo
  - carimbo_em (numero (0…), padrão null) — segundos em que o carimbo bate; padrão: 62% da cena

## documento

Página de documento: cabeçalho, linhas em monoespaçada, trecho grifado e carimbo.

- duração padrão: 6 s · alfa: não

  - linhas (lista (1…12), obrigatório) — as linhas do documento, na ordem
      - cada item (texto, padrão null)
  - titulo (texto, padrão null) — cabeçalho do documento
  - sub (texto, padrão null) — linha de identificação (processo, data, origem)
  - grifo (lista, padrão []) — trechos a marcar (procurados em todas as linhas)
      - cada item (texto, padrão null)
  - carimbo (texto, padrão null) — texto do carimbo
  - cor_carimbo (cor, padrão "negativo")

## foto

Foto na moldura da DA (rótulo + crédito), em cartão ou em tela cheia.

- duração padrão: 4 s · alfa: não

  - arquivo (arquivo, obrigatório) — imagem (jpg/png); nada de GIF — o auditor reprova imagem animada
  - rotulo (texto, padrão null) — rótulo da moldura (quem é, de quando é)
  - sub (texto, padrão null) — segunda linha do rótulo (ex.: "Reprodução")
  - encaixe (opcao, padrão "cobrir") [cobrir, inteira] — cobrir recorta para preencher a janela; inteira mostra a foto toda
  - estilo (opcao, padrão null) [nenhuma, borda, cantoneiras, janela, polaroid] — estilo da moldura; padrão: tratamento.moldura da DA
  - area (lista (4…4), padrão null) — [x, y, l, a] em frações do quadro; padrão: a área livre inteira
      - cada item (numero, padrão null)

## infografico

Infográfico simples: blocos lado a lado ou etapas numeradas ligadas, com valor e nota.

- duração padrão: 6 s · alfa: não

  - itens (lista (2…6), obrigatório)
      - rotulo (texto, obrigatório)
      - valor (numero, padrão null)
      - nota (texto, padrão null)
  - modo (opcao, padrão "blocos") [blocos, etapas]
  - titulo (texto, padrão null)
  - prefixo (texto, padrão "")
  - sufixo (texto, padrão "")
  - casas (inteiro (0…4), padrão 0)
  - destaque (inteiro (0…), padrão null) — índice do item em destaque
  - cores (opcao, padrão "serie") [serie, primaria] — série de cor.dados ou tudo na primária

## insert

Moldura de insert com a janela transparente: o vídeo é encaixado pelo ffmpeg depois.

- duração padrão: 4 s · alfa: sim

  - rotulo (texto, padrão null) — rótulo da moldura (o que é o vídeo, de quando é)
  - sub (texto, padrão null) — segunda linha do rótulo (ex.: "Reprodução")
  - area (lista (4…4), padrão null) — [x, y, l, a] em frações do quadro; padrão: a área livre inteira
      - cada item (numero, padrão null)
  - estilo (opcao, padrão null) [nenhuma, borda, cantoneiras, janela, polaroid] — padrão: tratamento.moldura da DA
  - inclinacao (numero (-15…15), padrão null) — graus (só em polaroid)

## linha_do_tempo

Linha do tempo: trilho que cresce e marcos datados que acendem em ordem.

- duração padrão: 7 s · alfa: não

  - marcos (lista (2…7), obrigatório)
      - data (texto, obrigatório) — como a data deve aparecer
      - texto (texto, padrão null) — o que aconteceu (curto)
      - destaque (booleano, padrão false)
  - titulo (texto, padrão null)
  - sentido (opcao, padrão "auto") [auto, deitado, empe] — auto segue a orientação do quadro

## manchete

Recorte de notícia: veículo, data, manchete grande e linha fina, com grifo opcional.

- duração padrão: 4.5 s · alfa: não

  - manchete (texto, obrigatório) — o título da notícia
  - veiculo (texto, padrão null) — nome do veículo (vai na tarja)
  - data (texto, padrão null) — data como ela deve aparecer (ex.: "12 de março de 2024")
  - linha_fina (texto, padrão null) — subtítulo da notícia
  - grifo (lista, padrão []) — trechos da manchete a marcar
      - cada item (texto, padrão null)

## mapa

Mapa esquemático com malha, contorno, pontos marcados e rotas — sem nenhum dado baixado.

- duração padrão: 6 s · alfa: não

  - pontos (lista (1…8), obrigatório)
      - nome (texto, obrigatório)
      - x (numero (0…1), obrigatório) — fração da largura do mapa
      - y (numero (0…1), obrigatório) — fração da altura do mapa
      - destaque (booleano, padrão false)
  - rotas (lista (…8), padrão []) — rotas entre pontos, por índice
      - de (inteiro (0…), obrigatório)
      - para (inteiro (0…), obrigatório)
  - contorno (lista (6…), padrão null) — polígono [[x, y], …] em frações; padrão: a forma genérica do kit
      - cada item (lista (2…2), padrão null)
          - cada item (numero, padrão null)
  - titulo (texto, padrão null)

## numero

Um número grande que conta até o valor, com rótulo, apoio e crédito da fonte.

- duração padrão: 4 s · alfa: não

  - valor (numero, obrigatório) — o valor final
  - rotulo (texto, obrigatório) — o que o número é (uma linha)
  - apoio (texto, padrão null) — linha curta de contexto abaixo do rótulo
  - prefixo (texto, padrão "") — ex.: "R$ "
  - sufixo (texto, padrão "") — ex.: "%" ou " mil"
  - casas (inteiro (0…4), padrão 0) — casas decimais
  - de (numero, padrão 0) — valor inicial da contagem
  - cor (cor, padrão "primaria") — token do número
  - alinhar (opcao, padrão "centro") [esquerda, centro]

## painel

Painel de pessoas ou entidades ligadas por fios, com rótulo nas ligações.

- duração padrão: 6 s · alfa: não

  - pessoas (lista (2…6), obrigatório) — de 2 a 6 nós do painel
      - nome (texto, obrigatório)
      - cargo (texto, padrão null)
      - foto (arquivo, padrão null)
      - destaque (booleano, padrão false)
  - ligacoes (lista (…10), padrão []) — fios entre os nós, por índice (0 = o primeiro)
      - de (inteiro (0…), obrigatório)
      - para (inteiro (0…), obrigatório)
      - rotulo (texto, padrão null)
  - titulo (texto, padrão null) — título acima do painel

## selo

Selo de estado no canto da zona segura, que troca de texto e de cor no tempo da fala.

- duração padrão: 5 s · alfa: sim

  - estados (lista (1…4), obrigatório)
      - texto (texto, obrigatório) — curto, 1 a 3 palavras
      - cor (cor, padrão "primaria")
      - em (numero (0…), padrão null) — segundos da peça em que este estado entra; padrão: distribuído
  - canto (opcao, padrão "superior_direita") [superior_esquerda, superior_direita, inferior_esquerda, inferior_direita]
  - inclinacao (numero (-15…15), padrão -7)

## texto

Frase datilografada na tipografia da DA, com um trecho grifado a marca-texto no fim.

- duração padrão: 5 s · alfa: não

  - texto (texto, obrigatório) — a frase (até ~30 palavras; encolhe para caber)
  - grifo (lista, padrão []) — trechos exatos da frase a marcar (acento e caixa não importam)
      - cada item (texto, padrão null)
  - papel (opcao, padrão "corpo") [titulo, subtitulo, corpo] — papel tipográfico da frase
  - escala (opcao, padrão "h2") [h1, h2, h3, corpo] — degrau da escala da DA
  - alinhar (opcao, padrão "esquerda") [esquerda, centro]

