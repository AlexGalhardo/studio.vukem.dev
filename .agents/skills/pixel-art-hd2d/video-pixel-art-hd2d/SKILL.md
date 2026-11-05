---
name: video-pixel-art-hd2d
description: Cria vídeos curtos (reels/shorts/TikTok 9:16, também 16:9) no estilo "pixel art HD-2D" (Octopath Traveler) — um cenário 3D de verdade (casas, muros, rua, postes com fios) vestido com texturas de pixel art e filtro nearest, personagens como sprites 2D pixelados em billboard dentro do 3D, câmera alta em 3/4 com FOV estreito em travelling lento, tilt-shift forte de miniatura, bloom quente, névoa dourada de fim de tarde, placa de local pixelada e balões de fala em fonte bitmap. Feito em three.js, renderizado quadro a quadro com Playwright + ffmpeg. Use quando o usuário pedir pixel art, HD-2D, "estilo Octopath", "RPG/SNES em 3D", jogo retrô em perspectiva, cena de vila ou rua de joguinho, sprite andando num cenário 3D, 2.5D pixelado, diorama pixelado com tilt-shift, ou mandar uma referência nesse visual pedindo "nesse estilo". Difere das irmãs: video-maquete-3d (diorama semi-realista, sem pixel), video-lowpoly-explicativo (massinha low-poly que explica processos), video-jelly, video-pelucia.
---

# Vídeo pixel art HD-2D

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

## As 4 marcas do estilo

(detalhe em `references/estilo.md`)

1. **O cenário é 3D de verdade** — blocos, telhados, muros, chão com relevo — mas TODA superfície é pixel art: textura de baixa resolução, filtro nearest, rampas de cor com matiz deslocado, pontilhado Bayer, normal map pixelado.
2. **As pessoas são sprites 2D em billboard**, cabeçudos como nos RPGs, com contorno escuro e animação por quadros (andar, acenar, varrer, moto com a roda girando).
3. **Câmera alta em 3/4** (~31–38° para baixo, levemente de lado, FOV 22–30) em travelling lento.
4. **Pós de "miniatura"**: tilt-shift forte em cima e embaixo, bloom quente em lampiões/janelas/letreiros, névoa dourada, raios de luz, poeira e pétalas em pixels, poça d'água animada, vinheta e gradação de fim de tarde (sombras azuladas, luzes douradas).

Veja `assets/exemplo.mp4` (5 s, 9:16): um motoboy atravessa a Rua das Palmeiras às 18h40 — padaria com toldo listrado, banca, orelhão, gari varrendo, pipa enroscada no fio, poça que respinga — e para na casa 47: "BI-BI!", o vira-lata late e a cliente sai no portão acenando. O código está em `assets/projeto/videos/motoboy-entrega/index.html` e é o ponto de partida de todo vídeo novo.

## Preparar a pasta de trabalho (uma vez por projeto)

```
python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>
cd <pasta-do-projeto>
python3 tools/renderizar.py motoboy --preview=6     # confere -> previews/motoboy-entrega-9x16.jpg
```

O `projeto.py` copia `lib/`, `videos/` e `audio/` para a sua pasta e deixa as ferramentas em `tools/`. O motor
(`render.mjs`) e as bibliotecas Node ficam dentro da skill: cada projeto fica leve e o `node_modules` é instalado
uma vez só, pelo `preparar.py`. Requisitos: Node ≥ 20, ffmpeg, Python com numpy+scipy e WebGL2 no Chromium do
Playwright (no Mac usa Metal). O `renderizar.py` passa o render pela trava de memória quando ela existe.

## Fluxo

1. **Roteiro de 5–10 s em beats.** Um herói (sprite) com um percurso claro, 3–5 figurantes fazendo algo em loop, 1–2 "pontos de virada" (buzina, balão, porta que abre) e a placa de local. Escreva a tabela `T` de tempos antes de modelar.
2. **Cenário com a biblioteca.** `HD.rua`, `HD.casa` (janelas, portas, loja, portão, toldo, letreiro, sacada, muro, telhado colonial/platibanda/laje), `HD.poste` + `HD.emaranhado`, `HD.banca`, `HD.orelhao`, `HD.arvore`, `HD.palmeira`, `HD.carro`, `HD.vaso`, `HD.engradado`, `HD.canteiro`, `HD.bairroFundo`. Algo novo: pinte uma textura com `new HD.Pixels(w,h)` + rampas e use `HD.caixa/plano/cilindro/bolha` com UV em texels. API em `references/receitas.md`.
3. **Sprites.** `HD.folhaPessoa({...})`, `HD.folhaMotoboy()`, `HD.folhaCachorro()`, `HD.folhaBalao('TEXTO')` ou `HD.folhaSprite(w,h,n, desenhar)` → `HD.sprite(S, folha, {pos})`; no `S.update`, mova `spr.g.position` e troque `spr.quadro(i)`.
4. **Luz e pós.** `HD.palco({...})` já traz sol com sombra macia, céu/hemisfério, tilt-shift, névoa, bloom e gradação. Acrescente `HD.poeira`, `HD.petalas`, `HD.fumaca`, `HD.respingos`, `HD.vagalumes`, `HD.raios`, `HD.poca` e `HD.placaLocal`.
5. **Câmera.** `HD.travelling(S, {de, ate, dist, pitch, yaw, fov})` — alvo nas fachadas (z ≈ calçada de lá, y ≈ 2), não no chão.
6. **Preview.** `python3 tools/renderizar.py <nome> --at=0.2,1.5,2.5,3.5,4.8` → `previews/<nome>-9x16.jpg`. Confira a checklist. 16:9: `--fmt=16x9`.
7. **Som e render.** `python3 tools/renderizar.py <nome> --at=1` (grava `cues.json`) → `<PYTHON> audio/synth.py <nome>` → `python3 tools/renderizar.py <nome> --fmt=9x16` → `out/<nome>-9x16.mp4` (150 quadros ≈ 15–20 s num Mac M).
8. **Conferir.** `ffprobe` (1080×1920, yuv420p, duração, áudio) e folha: `ffmpeg -i out/X.mp4 -vf "fps=3,scale=270:-1,tile=5x3" -frames:v 1 folha.jpg`.

### Checklist de cada preview

- Em 9:16: 0–25% telhados e morro desfocados · 25–55% fachadas nítidas · 55–85% rua com o herói · 85–100% primeiro plano desfocado (canteiros, calçada).
- Os pixels estão grandes e nítidos na faixa de foco? (sprite a 20 px/m, cenário a 24 texels/m). Nada de textura lisa "de 3D".
- Todo mundo está fazendo algo (câmera + herói + figurantes + partículas)? Nenhum balão ou placa cortado na borda?
- Brilhos: só lâmpadas, janelas, vitrines e letreiros passam do limiar do bloom; o resto não estoura.
- Texto de tela em pt-BR com acentos (a fonte bitmap tem Á À Â Ã É Ê Í Ó Ô Õ Ú Ç e o "h" de 18h40); marcas sempre fictícias.

## Regras do motor

- **Tudo é função de `t`.** Nada de `Math.random`, `setTimeout`, rAF ou CSS animado: use `HD.rng(semente)`, `HD.hash`, `HD.fase(t, t0, t1, ease)`.
- **Página = módulo.** `boot.js` e depois `<script type="module">import * as HD from '../../lib/hd2d.js'</script>`; defina `window.SETUP` síncrono. `<meta name="formats" content="9x16,16x9">` + `?fmt=16x9` troca `VIDEO.w/h`.
- **UV em texels.** As peças da biblioteca põem UV em texels e as texturas usam `repeat = 1/largura`: qualquer textura de `HD.tex` serve em qualquer peça com a mesma densidade de pixel. Peça própria: use `HD.caixa/plano/cilindro/bolha/chao` (não `BoxGeometry` cru).
- **Sprites:** quadros de mesmo tamanho lado a lado; contorno escuro automático; `spr.flip = true` espelha; `inclina` (0–1) deita o sprite para a câmera. Sprites em `MeshBasicMaterial` não recebem luz — pinte a luz de cima-esquerda no próprio sprite.
- **Sombra:** caixa fixa do sol (`sombraCaixa: [cx, cz, raio]`) cobrindo todo o percurso — mover a caixa por quadro faz a sombra tremer.
- **Estilo fechado.** A paleta, a fonte bitmap e o tilt-shift são a identidade do formato: não troque por tokens de `da/da.json`. A direção de arte do projeto entra no uso do clipe (moldura, carimbo, conferência final), não nas cores da cena.

## Armadilhas conhecidas

- **Câmera mirando o chão:** sobra rua e somem as fachadas. Mire na calçada de lá a ~2 m de altura, pitch ~31°, dist ~40, fov 28 (9:16).
- **Árvore perto da câmera:** com sol baixo a sombra dela atravessa a rua inteira; mantenha copas grandes longe do percurso do herói.
- **Fumaça parada acumula** e embranquece o sprite: reduza `forca` quando o veículo para e jogue a `deriva` para trás (z negativo).
- **Bloom estourado:** sol forte (> 2,8) ou letreiro com `brilho` > 1,5 passa do limiar; o `limiar` do bloom está em luz linear (~1,5).
- **Cabelo/acessório cobrindo o rosto:** volumes atrás da cabeça (black power, coque) são desenhados ANTES do rosto.
- **Postes e fios na frente do letreiro:** confira se o nome da loja fica legível no primeiro quadro em que aparece.

## Arquivos

- `assets/projeto/lib/hd2d.js` — a biblioteca do estilo (API em `references/receitas.md`).
- `assets/projeto/videos/motoboy-entrega/` — o exemplo completo (9:16 e 16:9).
- `assets/projeto/audio/synth.py` — música curta (violão Karplus-Strong em bossa + pad) e ambiente/efeitos de rua.
- `references/estilo.md` (o que define o HD-2D, paleta, luz, câmera, composição) · `references/receitas.md` (API + receitas).
- `scripts/projeto.py` (monta a pasta de trabalho) · `scripts/renderizar.py` (render pelo Node, com trava) · `scripts/comum.py`.
