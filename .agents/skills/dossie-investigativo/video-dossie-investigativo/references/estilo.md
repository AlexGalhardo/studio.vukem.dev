# Estilo: dossiê investigativo

Leitura das referências (cinco imagens de arquivo e de ficha: fotocópias anotadas, ficha de agente com tarjas, capa com digital e bloco censurado, painel de fotos ligadas por linhas, ficha com retratos de olhos tarjados) e como elas viram vídeo 9:16.

## As 3 marcas

1. **Papel de xerox preto e branco, sujo**, que treme em degraus como registro de stop-motion.
2. **O que está escondido**: tarja que risca o texto, fita sobre os olhos da foto 3x4, digital carimbada.
3. **Painel de fios**: fotos, cartões e etiquetas presos por alfinetes, ligados por fios que se desenham, com a câmera de mesa percorrendo e abrindo no fim.

Toda cena tem de servir a pelo menos uma delas. Uma cena sem papel sujo, sem tarja e sem fio não é deste estilo.

## Paleta

| papel | hex | variável CSS (`lib/dossie.js`) |
|---|---|---|
| papel claro (fundo) | `#e0e0dc` em média, bandas entre `#d2` e `#ec` | `--ds-papel` (`#e4e3df`, cor do texto vazado) |
| tinta (texto, tarja, digital, carimbo) | `#111111` | `--ds-tinta` |
| cinza de apoio (subtítulos de cartão) | `#6e6d68` | `--ds-cinza` |
| fio | `#2c2c2a` | `--ds-fio` |
| caneta | `#15151a` | `--ds-caneta` |
| cartão de papel | `#efeeea` | — |
| papel escuro (negativo) | `#1a1a1a`, tinta `#eceae5` | `tom: 'escuro'` |
| mesa (atrás da folha) | `#0d0d0d` | `#stage{background}` |
| acento (opcional, um só) | no exemplo `#d8481e` | `--ds-acento` |

Preto, branco e cinzas. O acento é opcional, único e pequeno: fios que importam, uma etiqueta. O padrão de `--ds-acento` é preto; para usar cor, defina-o em `:root` na página e passe `cor: 'var(--ds-acento)'` na peça. Sem gradiente colorido, sem brilho, sem sombra projetada macia (a "sombra" de cartões é um degrau duro, de fotocópia).

## Tipografia

| papel | fonte | tamanho em 9:16 | onde |
|---|---|---|---|
| título e código do arquivo | **Inter Tight 800–900**, caixa alta, entrelinha 0,94 | código 150–160 px; título do mural 250 px no mundo (≈ 135 px na tela) | alto da ficha; base do mural |
| etiqueta de nome | Inter Tight 800 vazada em bloco preto, com linha de apoio 500 | 60 px no mural | colada acima da foto |
| ficha e rótulos | **Courier Prime** 400 (700 no valor forte) | 36 px (campo), 20–26 px (rótulo), 15–19 px (colunas de números) | corpo da folha |
| citação | **Lora** 500 itálica, aspas curvas | 58 px no mural | ao lado de uma peça |
| carimbo | Inter Tight 900 (ou Courier Prime 700) em caixa dupla | 62–110 px | girado −8° a −10° |

- Rótulos de ficha em caixa alta seguidos de dois-pontos (`NOME:`, `CODINOME:`, `SITUAÇÃO:`). Horas no formato `03H12`.
- No celular, o menor texto que precisa ser lido tem 30 px na tela. Colunas de números e rótulos miúdos são textura.

## Materiais

- **Papel** (`DS.papel`): cinza-claro com nuvens de toner esticadas na horizontal, bandas de scanner de alturas variadas, linhas finas, riscos verticais, arrastos de toner, vinco (linha clara entre duas sombras), grão por pixel, pontinhos pretos e a borda irregular escura da fotocópia. `verso: true` deixa vazar linhas-fantasma do verso; `furos: true` põe três furos de arquivo na margem. `tom: 'escuro'` é o negativo.
- **Tarja** (`DS.tarja`): `marcador` são duas ou três passadas desalinhadas, com pontas falhadas; `fita` é um retângulo quase reto. As duas têm a borda roída de fotocópia. Altura ≈ 1,08× o tamanho da letra.
- **Foto de ficha** (`DS.foto`): retrato frontal 3x4 em xerox (grão grosso, toner empelotado, riscos verticais claros), com duas cópias desbotadas ao lado vazando pelas laterais, quatro cruzes de registro, linha de medida tracejada e um pedaço de fita adesiva. No mural ganha moldura de papel de 10 px e alfinete.
- **Digital** (`DS.digital`): cristas geradas por um campo de fase com ruído (`laco`, `espiral` ou `arco`), contorno de ponta de dedo, falhas e empastamento de tinta; opcionalmente dentro de uma caixa com rótulo (`POLEGAR D.`).
- **Carimbo** (`DS.carimbo`): caixa dupla, texto em caixa alta, tinta falhada com pressão desigual (um lado mais apagado).
- **Caneta** (`DS.garrancho`, `circulo`, `seta`, `sublinhado`, `assinatura`): traço de 2,6 a 5 px com pontas redondas; o garrancho imita escrita cursiva sem formar palavras.
- **Cartão, etiqueta, alfinete, fio**: papel mais claro que o mural com degrau de sombra duro; bloco preto com texto vazado e número num quadrado claro; cabeça de alfinete preta com brilho; fio de 2,2 px quase reto.
- **Por cima de tudo**: `DS.grao` (grão que muda 12 vezes por segundo), `DS.vinheta` (bordas 30% mais escuras) e `DS.scanner` (faixa de luz).

## Composição 9:16

**Página 1, a ficha** (folha 1080×1920, margem esquerda de 84 px):

| faixa (y) | conteúdo |
|---|---|
| 56–110 | cabeçalho em mono (2 linhas) à esquerda; colunas de números à direita |
| 158–350 | rótulo `ID DO SUJEITO` + código do arquivo em 158 px; ao lado, um rótulo curto |
| 364 | régua graduada de margem a margem |
| 440–1135 | medida tracejada, cruzes e a foto 500×635 no centro, com as cópias a ±372 px vazando pelas laterais |
| 1195–1505 | ficha: 5 linhas de 36 px com entrelinha de 62 px (duas nascem tarjadas) |
| 1560–1855 | duas digitais em caixa à esquerda; carimbo girado à direita, por cima da segunda caixa |

A anotação à mão ocupa o vão à direita das linhas curtas da ficha, com uma seta para a foto e um círculo num valor.

**Página 2, o mural** (2000×3556; a tela vê 1080×1920 em zoom 1 e o mural inteiro em zoom 0,548):

- Três retratos em triângulo (alto à esquerda, meio à direita, baixo à esquerda), cada um com etiqueta de nome 130 px acima e, embaixo, um cartão de texto com tarjas.
- No meio, o cartão do lugar ou do fato central (o exemplo usa o cartão escuro, em negativo); perto dele, uma linha do tempo datilografada.
- Canto superior direito: código do mural, colunas de números e régua. Lado direito, embaixo: digital em caixa e citação serifada.
- Base: título de duas linhas em 250 px, rótulo do arquivo, carimbo girado sobre o canto do título e assinatura.
- Fios pretos entre as peças; os três fios de acento saem do alto do título e sobem até as etiquetas.
- Nada de texto abaixo de y = 3400: ali fica o rodapé fixo da tela.

## 16:9

O motor aceita `VIDEO={w:1920,h:1080,…}` sem outra mudança (a biblioteca lê `VIDEO.w/h` para câmera, scanner, grão e rodapé). Recomponha em vez de esticar:

- **Ficha:** folha deitada 1920×1080 com a foto à esquerda (cópias vazando para a esquerda) e código + ficha à direita; ou mantenha a folha em pé e deixe a câmera percorrê-la em zoom ≥ 1,78.
- **Mural:** deitado, por exemplo 3200×1800 (zoom final 0,6), com o título na base à esquerda e os retratos em fileira.
- Tamanhos de letra: os mesmos em px (a tela é mais baixa, então caiba menos coisa por quadro).

## Conteúdo responsável

O estilo faz qualquer frase parecer documento. Vale o que está no `SKILL.md`: dados só do roteiro do usuário, fonte ou aviso de ficção no rodapé, nenhuma marca de órgão real, foto de pessoa real só fornecida pelo usuário ou de licença livre.
