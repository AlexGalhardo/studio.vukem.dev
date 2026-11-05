# Variantes salvas do estilo

Variações do dossiê investigativo guardadas a pedido do usuário. Cada uma muda a paleta e alguns tratamentos; o motor, as peças e as regras de conteúdo do SKILL.md continuam valendo. Quando o pedido citar o nome de uma variante, leia a seção dela antes de montar o vídeo.

## iceberg-pt — preto, branco e vermelho (vídeo longo, 16:9)

Guardada em 16/10/2026 para um projeto de vídeo longo de jornalismo no YouTube. As duas imagens de referência ficam na pasta do projeto do usuário (`referencias-visuais/`), não na skill.

**Paleta.** Papel creme de xerox, preto profundo e um único acento: vermelho vivo de impressão (perto de `#D7262B`, com leve retícula). O vermelho entra em blocos chapados grandes, não em detalhes miúdos.

**O que muda em relação ao dossiê padrão:**
- **Censura em vermelho:** rosto coberto por uma máscara vermelha chapada, recortada no formato da cabeça (silhueta), no lugar da tarja preta nos olhos. É o tratamento para preservar a identidade de terceiros, e obrigatório para crianças.
- **Grifo vermelho:** marca-texto vermelho translúcido, com retícula, correndo atrás de trechos do texto datilografado (ficha, currículo, documento).
- **Blocos vermelhos:** faixas largas nas bordas de cima e de baixo e retângulos atrás e entre os recortes de foto, como na colagem impressa.
- **Diagonais vermelhas:** barras finas cruzando o quadro de ponta a ponta, no papel que os fios fazem no painel investigativo.
- **Fotos:** recortes de jornal em meio-tom de alto contraste, com borda branca de tesoura e sombra curta; o retrato principal recortado em silhueta, sem fundo, por cima do documento; fotos de arquivo em xerox de grão forte, sobrepostas em camadas.
- **Texto:** documento datilografado em mono (seções sublinhadas, datas em coluna), citação curta numa caixa branca com aspas em grotesca negrito, número circulado à mão, rabiscos e setas em preto, carimbo circular genérico (nunca de órgão real).

**Composição e movimento.** Colagem em camadas que sangra nas bordas, com profundidade entre recortes. Câmera lenta de vídeo longo com parallax entre as camadas; recortes entram como papel colado; o bloco vermelho varre; o grifo corre no tempo da fala; a máscara vermelha bate sobre o rosto como carimbo.

**Formato.** 16:9 (1920x1080). Ainda não implementado na biblioteca: a lib tem as peças do dossiê em 9:16, sem tema vermelho, sem máscara por silhueta e sem composição própria em 16:9. Na primeira produção com esta variante, acrescente à `lib/dossie.js` um tema (acento vermelho, grifo, blocos, diagonais) e a máscara de rosto por silhueta (o recorte de pessoa das skills irmãs, `cutout.swift`, serve para gerar o contorno), e componha em 16:9.
