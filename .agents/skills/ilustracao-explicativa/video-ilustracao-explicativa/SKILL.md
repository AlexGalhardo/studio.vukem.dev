---
name: video-ilustracao-explicativa
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "ilustração explicativa" — explainer de ilustração PLANA com contorno preto fino e personagens sem rosto (cabeça-círculo com bico triangular, jaleco, braços-tubo) sobre fundos rosa-chiclete e creme com grão; fotos reais P&B em cantoneiras ciano que se reorganizam em grade; plano contínuo com câmera que sobe e desce; e banco de nuvens pretas com rótulo químico ("CO₂", "H₂O") varrido por uma mão com rede, revelando um título larguíssimo. Páginas HTML animadas quadro a quadro (GSAP + Playwright + ffmpeg), globo com continentes reais e som sintetizado. Use quando pedirem "explainer animado", "estilo Kurzgesagt/flat", "ilustração plana", "infográfico animado com personagens", vídeo sobre clima, meio ambiente, ciência, saúde ou "como funciona X", ou mandarem referência nesse visual pedindo "nesse estilo". Difere das irmãs: video-colagem-explicativa monta a cena com recortes de foto; video-traco-simples é forma chapada de papel recortado, sem foto.
---

# Vídeo em ilustração explicativa

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

Três marcas, juntas, fazem o estilo:

1. **Ilustração plana de explainer com contorno preto fino.** Personagens sem rosto (cabeça-círculo azul, um bico triangular rosa ou amarelo como nariz, cabelo em blob preto, tronco-pílula estampado, calça em Π preta, braços-tubo com contorno, luvas arredondadas), objetos chapados (globo preto com continentes em linha, labareda amarela de contorno rosa, regadores cinza sem contorno com selo rosa). Fundos chapados rosa-chiclete `#f06aa6` e creme `#f3ece0` com grão fino. É o "sotaque" visual: amigável, sério sem ser frio.
2. **Fotos P&B em cantoneiras ciano sobre o rosa**, que deslizam de fora em 5–7 quadros e empurram as outras para formar uma grade 2×2, enquanto rachaduras/rios pretos crescem em degraus e duas coroas amarelas fervem nos cantos de baixo. A foto real ancora o assunto no mundo; o resto é desenho.
3. **Banco de nuvens pretas com rótulo químico + título larguíssimo.** Bolhas pretas cheias de "H₂O"/"CO₂" em creme cobrem o alto; uma mão com rede de borboleta (ou guarda-chuva) varre o miolo em arco, as bolhas encolhem e caem como bolinhas, e aparece o título em Archivo expandida 900: 1ª linha preta, 2ª creme.

Entre as fotos e o título, a cena do meio é **um plano contínuo com câmera que passeia** (tilt para cima e para baixo): os personagens saem pela borda e a próxima ação entra no mesmo mundo. Cortes secos só entre fundos diferentes (rosa → creme → rosa).

Veja `assets/exemplo.mp4` (8 s, "Rios voadores — como a Amazônia faz chover no Sudeste"). O código está em `assets/projeto/videos/exemplo-rios-voadores/index.html` e é o ponto de partida de todo vídeo novo.

## Preparar a pasta de trabalho (uma vez por projeto)

```
python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>
cd <pasta-do-projeto>
python3 tools/renderizar.py exemplo --preview=6     # confere → previews/exemplo-rios-voadores.jpg
```

O `projeto.py` copia `lib/`, `videos/` e `audio/` para a sua pasta e deixa as ferramentas em `tools/`. O motor
(`render.mjs`) e as bibliotecas Node ficam dentro da skill: cada projeto fica leve e o `node_modules` é instalado
uma vez só, pelo `preparar.py`. Requisitos: Node ≥ 20, ffmpeg, Python com numpy+scipy+Pillow e o Chromium do
Playwright. O `renderizar.py` passa o render pela trava de memória quando ela existe. Funciona igual em Mac,
Linux e Windows — não há script `.sh` no caminho obrigatório. Não há recorte automático de foto: as fotos entram
inteiras, em cantoneiras (é assim o estilo).

## Fluxo

1. **Tema e roteiro.** Um assunto que se explica em 3 tempos: *o problema/assunto no mundo real* (fotos) → *o mecanismo* (personagens e objetos, metáfora visual) → *o nome da coisa* (título). Escreva a tabela `T` antes de desenhar, na proporção 26% / 54% / 20% (ver `references/movimento.md`). Sem narração: o título final e, se precisar, uma linha de subtítulo carregam a explicação. Não invente números; prefira frases seguras.
2. **Fotos** (4 de licença livre, ver `references/receitas.md`, "Fotos"):
   - `<PYTHON> -I tools/commons.py buscar "termo em inglês" --n 16 --folha previews/c.jpg` → olhe a folha e baixe com `baixar <n> videos/<nn>/img/x.jpg --largura 1400`.
   - `<PYTHON> -I tools/ilustra.py foto img/x.jpg img/x_pb.jpg --foco .5,.5` → P&B sépia de contraste baixo, 900×600.
3. **Metáfora do meio.** Escolha 3 ações com objetos (regar, pescar com rede, pôr no freezer, apontar com lupa, encher um copo) que contem o mecanismo. O globo (`IL.globo`) com um caminho em cima (`IL.fluxo`) é o "mapa" do explainer.
4. **Montar:** `cp -R videos/exemplo-rios-voadores videos/<nn-nome>` e troque fotos, ações e textos mantendo a gramática (`references/estilo.md`) e a API (`references/receitas.md`).
5. **Preview:** `python3 tools/renderizar.py <nn> --at=0.5,2.5,4.2,5.8,7.5` (ou `--preview=12`) → `previews/<nn-nome>*` e corrija.
6. **Som e render:** `python3 tools/renderizar.py <nn> --at=1` (grava `cues.json`), `<PYTHON> audio/synth.py <nn>`, `python3 tools/renderizar.py <nn>` → `out/<nn-nome>.mp4` (ver `references/audio.md`).
7. **Conferir:** `ffprobe` (1080×1920, duração, uma faixa de áudio), folha a 8 qps do mp4, texto legível no celular, crédito das fotos (e "Mapa: Natural Earth" se usar o globo) no rodapé da última cena.

## Regras do motor

- Tudo é função do tempo (`onTick(t => …)` ou `TL`); nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()` (use `K.rng`).
- Gestos de personagem, balanço de fotos e fervura vão "em dois": `IL.q(t, 12)` e `IL.quadro(t, 8)`. Câmera, deslizes e varridas são lisos.
- Medições de texto (`IL.cabe`) só dentro de `window.SETUP` (as fontes já carregaram). Meça o `<span>` interno: o bloco `.titulo` tem `left/right: 0` e sempre mede a largura do palco.
- Fonte: só **Archivo** (`lib/fonts.css`), variável: `font-stretch:125%; font-weight:900` para título e rótulos, `112%/800` para subtítulo, `100%/500` para crédito.
- Cenas fora da janela ficam `display:none`; o `onTick` de cada cena sai cedo (`if (cenaEm(t) !== 2) return;`).

## Armadilhas do estilo

- **Personagem que vira poste.** Em 9:16 os bonecos ficam altos demais se aparecem inteiros. Use escala ~1,5 e deixe o quadro cortar na coxa (6–7 raios de cabeça de calça visível), como na referência.
- **Dois personagens embolados no meio.** O braço que aponta sobe para o objeto (cotovelo para fora, pulso acima do ombro); a lupa fica à altura da cabeça. Confira num quadro grande.
- **Cientistas que reaparecem.** Num plano contínuo, quem sai pela borda e não volta precisa sair de verdade (afunde-o com `power2.in` e esconda) antes da câmera passar de novo por ali.
- **Regador que não derrama.** O bico aponta ~30° para cima em repouso; incline ≥ 55° para a água cair. As gotas saem da ponta calculada (gire o vetor do bico pelo mesmo ângulo).
- **Nuvem com frestas.** O miolo precisa cobrir a janela inteira no corte; aumente `escalaMiolo` ou acrescente bolhas nas laterais. Rótulos do miolo ficam numa camada por cima (já é assim em `IL.nuvens`).
- **Bolinhas sobre o título.** As bolhas varridas caem com gravidade forte (2600 px/s²) para sumir em ~0,4 s.
- **Música por cima de tudo.** A trilha `explicador` fica em `gain:-8`; os efeitos contam a história.

## Arquivos

- `assets/projeto/lib/ilustra.js` — biblioteca do estilo, global `IL` (API em `references/receitas.md`).
- `assets/projeto/lib/terra.js` — contornos de continentes e do Brasil (Natural Earth 110m, domínio público) para `IL.globo`. Para destacar outro país: `tools/ilustra.py terra land.geojson lib/terra.js --paises countries.geojson --destaque ARG`.
- `assets/projeto/audio/synth.py` — som sintetizado; trilha `explicador` e efeitos `agua`, `chuva`, `sizzle` foram feitos para este estilo.
- `scripts/ilustra.py` — foto P&B sépia em proporção e geração do `terra.js`.
- `references/estilo.md` (paleta, traço, personagens, composição) · `movimento.md` (tempos e eases medidos) · `receitas.md` (API e passo a passo) · `audio.md` (trilha e efeitos).
- `scripts/projeto.py` (monta a pasta de trabalho) · `scripts/renderizar.py` (chama o motor com o Node certo e pela trava) · `scripts/commons.py` (fotos de licença livre + crédito) · `scripts/analisar.py` (ler uma referência nova e comparar lado a lado) · `scripts/comum.py` · `scripts/preparar.py`.
