---
name: video-maquete-3d
description: Cria vídeos curtos (reels/shorts 9:16 e 16:9) no estilo "maquete 3D semi-realista" — um bloco de diorama flutuando num estúdio creme, visto de cima em 3/4, laterais cortadas mostrando os estratos do chão (terra, canos, rocha) e, em cima, um lugar inteiro em miniatura limpa, telhado removido e paredes em corte, com bonecos de maquete sem rosto trabalhando em ações em loop, mais um HUD editorial claro (versalete, serifa itálica, selo, painel). A câmera só orbita devagar. Feito em three.js, renderizado quadro a quadro com Playwright + ffmpeg. Use quando o usuário pedir maquete 3D, diorama, miniatura, casa de bonecas em corte, tilt-shift, vista de cima de um lugar com gente trabalhando (restaurante, oficina, obra, escritório, loja, escola), bloco de terra com camadas, "material study", ou mandar referência nesse visual pedindo "nesse estilo". Difere das irmãs: video-lowpoly-explicativo explica processos em massinha low-poly, video-pixel-art-hd2d é pixel art; aqui o protagonista é o LUGAR em miniatura.
---

# Vídeo maquete 3D semi-realista

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## As 3 marcas do estilo

1. Um **bloco de diorama** flutuando num estúdio creme infinito (#ECEAE4, sombra de contato macia), visto de cima em 3/4 com lente longa, e as **laterais cortadas mostrando os estratos** do chão (concreto, terra vermelha com raízes e canos, argila, areia, brita, rocha).
2. Em cima, um **lugar inteiro em miniatura semi-realista** — telhado removido, paredes de perto cortadas baixas (topo escuro de "corte"), materiais PBR com textura procedural (ladrilho hidráulico, azulejo, pedra portuguesa, asfalto, madeira, toalha xadrez), inox, vidro, água, luz de estúdio com IBL, oclusão de ambiente (GTAO) e sombras macias — com **gente trabalhando ao mesmo tempo**, cada boneco (proporção de arquitetura, sem rosto, tons de pele diversos, uniformes) numa ação em loop, mais vapor e fumaça.
3. O **HUD editorial claro**: rótulo em versalete espaçado ("ESTUDOS DE MAQUETE · Nº 01"), título grande em serifa itálica com o ponto na cor de acento, subtítulo itálico, selo "AO VIVO", painel branco com botões, chips e sliders, dados em mono no rodapé.

A câmera só orbita devagar (~15–20° em 5 s) com leve aproximação. Nada de cortes, legendas grandes ou capítulos: é um "estudo de material" contemplativo. Detalhe em `references/estilo.md`.

Veja `assets/exemplo.mp4` (5 s, 9:16): restaurante de esquina fictício "Sabor de Casa" — cozinheira de touca mexendo o feijão (vapor), chapeiro virando bife, lavador de luva amarela, garçom com bandeja, atendente no caixa, varredor na calçada de pedra portuguesa, clientes comendo, TV, ventilador, quadro de giz, toldo listrado, vira-lata. Código: `assets/projeto/videos/01-restaurante/index.html` (ponto de partida de todo vídeo novo).

## Preparar a pasta de trabalho (uma vez por projeto)

```
python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>
cd <pasta-do-projeto>
python3 tools/renderizar.py 01 --at=0.2,2.5,4.8      # -> previews/01-restaurante-9x16.jpg
```

O `projeto.py` copia `lib/`, `videos/` e `audio/` para a sua pasta e deixa as ferramentas em `tools/`. O motor
(`render.mjs`) e as bibliotecas Node ficam dentro da skill: cada projeto fica leve e o `node_modules` é instalado
uma vez só, pelo `preparar.py`. Requisitos: Node ≥ 20, ffmpeg, Python com numpy+scipy e WebGL2 no Chromium do
Playwright (no Mac usa Metal). O `renderizar.py` passa o render pela trava de memória quando ela existe.

## Fluxo

1. **Planta baixa no papel.** Bloco ~10 × 9 m (1 unid. = 1 m). Defina: o que fica na calçada/rua (frente e um lado = as duas faces que a câmera vê), a fachada (letreiro + toldo numa lateral vista de viés), as zonas internas (ex.: cozinha no fundo, salão na frente) e **onde cada trabalhador fica e o que faz**. Paredes do fundo e da esquerda inteiras (2,8 m, com azulejo/pintura/quadros); paredes de perto cortadas a ~0,95 m.
2. **Copiar e montar.** `cp -R videos/01-restaurante videos/02-<nome>` e troque: estratos (`M.bloco`), pisos (`M.piso` + `tex.*`), paredes (`M.parede`), móveis/objetos, pessoas (`M.pessoa` + `ACAO.*`), câmera (`M.orbita`) e HUD (`cabecalho`, `selo`, `painel`, `rodape`). API e receitas em `references/receitas.md`.
3. **Preview** com poucos quadros: `python3 tools/renderizar.py 02 --at=0.2,2.5,4.8`. Para conferir poses e objetos, aproxime a câmera temporariamente (`raio` ~16, `alvo` no ponto de interesse) e olhe os quadros cheios em `previews/<v>-9x16/NN.jpg`.
4. **Som e render.** `python3 tools/renderizar.py 02 --at=1` (grava `cues.json`) → `<PYTHON> audio/synth.py 02` → `python3 tools/renderizar.py 02` → `out/02-<nome>-9x16.mp4` e `-16x9.mp4` (≈30 s cada para 5 s a 30 fps num Mac M).
5. **Conferir.** `ffprobe` (1080×1920, yuv420p, 5 s, áudio) e folha: `ffmpeg -i out/X.mp4 -vf "fps=3,scale=270:-1,tile=5x3" -frames:v 1 folha.jpg`.

### Checklist de cada preview

- O bloco inteiro cabe na largura (9:16: `fov` 26 e `raio` ~55 para um bloco de 10 × 9 m) e fica entre o subtítulo (~y 480) e o painel (~y 1400)? Sobra creme em volta e a sombra cai para trás/direita.
- As duas faces de estrato visíveis (frente e lateral) aparecem inteiras? Os canos cortados aparecem na terra?
- Todo trabalhador está visível o tempo todo? **Nada importante a menos de ~1,5 m atrás de uma parede alta virada para a câmera** (a fachada esconde o que está colado nela).
- Cada boneco tem ação clara na silhueta (braço na panela, vassoura no chão, bandeja na mão)? Vapor visível (cinza-azulado, não branco sobre azulejo branco)?
- O HUD não cobre o bloco (o painel pode encostar num canto, como na referência)?

## Regras do motor

- **Tudo é função de `t`.** Peças animadas se registram com `S.cada(fn)`; o resto vai em `S.update = t => {…}`. Nada de `Math.random`, `setTimeout`, rAF ou animação CSS — use `M.rng(semente)`.
- **Loop de rede social:** toda ação usa período que divide a duração (5 s → 5, 2,5, 1,25, 1, 0,625, 0,5). O garçom anda num laço fechado (`M.caminho` com `T = dur`). Só a câmera não fecha o laço.
- **Construa a cena dentro de `window.SETUP = async () => {…}`**: as texturas com texto (quadro de giz, letreiro, TV) usam as fontes, que só estão carregadas ali.
- **Fundo exato:** o creme é calculado com a inversa do tone mapping (sai igual ao hex). Não pinte o fundo por CSS nem ponha plano de chão colorido — o chão é `ShadowMaterial` (só sombra).
- **AO:** sprites, vidro e água ficam fora do GTAO (senão viram quadrados escuros). Para pôr um transparente no AO: `obj.userData.ao = true`.
- **Fontes:** Geist (rótulos), JetBrains Mono (dados) e uma serifa itálica para os títulos. Outra fonte: woff2 em `lib/fonts/` + `@font-face` em `lib/fonts.css`. Se a serifa faltar, o HUD cai para Georgia.
- **Marcas sempre fictícias**; preços e números de HUD são decorativos — não apresente como dado real.
- **Estilo fechado.** O creme do estúdio, os estratos e o HUD editorial são a identidade do formato: não troque por tokens de `da/da.json`. A direção de arte do projeto entra no uso do clipe (moldura, carimbo, conferência final).

## Armadilhas conhecidas

- `grupo.add(x).rotation.x = …` gira o GRUPO (o `add` devolve o pai). Crie, posicione e depois adicione.
- Fachada alta virada para a câmera esconde o balcão atrás dela: mova o que importa para o meio do salão ou corte a parede.
- Vapor branco some sobre parede branca: use `cor: '#aab6bf'`, `opac` .7–.85, `tam` .3–.36.
- Ferramenta na mão (`M.segurar`) aponta ao longo do antebraço; ajuste a rotação local. Objetos grandes (vassoura, bandeja) ficam melhor presos ao `p.tronco`.
- Codificador de hardware com entrada MJPEG sai `yuvj420p`: o `render.mjs` daqui já converte para `yuv420p` (faixa TV).

## Arquivos

- `assets/projeto/lib/maquete.js` — a biblioteca do estilo (API em `references/receitas.md`).
- `assets/projeto/videos/01-restaurante/` — a demo (9:16 e 16:9 via `<meta name="formats">`).
- `assets/projeto/audio/synth.py` — trilha em loop: bossa (violão Karplus-Strong + baixo), murmúrio de salão, chapa, panela, louça.
- `references/estilo.md` (marcas, paleta, materiais, luz, câmera, composição, HUD) · `references/receitas.md` (API + receitas de outros lugares).
- `scripts/projeto.py` (monta a pasta de trabalho) · `scripts/renderizar.py` (render pelo Node, com trava) · `scripts/comum.py`.
