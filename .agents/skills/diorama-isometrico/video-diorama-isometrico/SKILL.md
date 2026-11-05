---
name: video-diorama-isometrico
description: Cria vídeos curtos (reels/shorts 9:16) no estilo "diorama isométrico" — um bloco de terreno recortado (faces cortadas mostrando solo e água) sobre base técnica verde-água, câmera ortográfica totalmente parada, acabamento de história em quadrinhos (cel-shading em faixas, contorno a nanquim, hachura nas sombras roxas duras) e um relevo que se metamorfoseia sem cortes: montanhas sobem, afundam, viram mar, a mata brota. Feito em three.js (lib/diorama.js) com Playwright + ffmpeg e som sintetizado. Use quando pedirem diorama, diorama isométrico, maquete 3D, terreno isométrico, "mapa em bloco", corte de terreno, paisagem que se transforma, timelapse de relevo, vídeo de geografia/geologia/história de um lugar, ou mandarem uma referência nesse visual (bloco 3D com cara de HQ/Moebius) pedindo "nesse estilo". Difere das irmãs: video-floresta-luminosa é diorama NOTURNO hachurado a lápis; video-lowpoly-explicativo é maquete de massinha com HUD de capítulos; video-mapa-documental é mapa de satélite.
---

# Vídeo em diorama isométrico

## Instalação (automática, uma vez por máquina)

> **No Windows:** onde estiver `python3`, use **`py -3`** (`python3` não existe no Windows e abre a Microsoft
> Store). Na primeira vez, o caminho mais simples é o `instalar.bat` na raiz do zip. As barras `/` dos caminhos
> podem ficar como estão: o Python aceita barra normal no Windows.

1. Rode `python3 <pasta desta skill>/scripts/preparar.py`. Ele confere tudo e lista o que falta (código 0 = pronto, 3 = falta algo).
2. Se faltar algo, mostre a lista ao usuário e, com o ok dele, rode o mesmo comando com `--instalar`: ele copia a skill para `~/.claude/skills/`, instala os programas pelo gerenciador do sistema e as bibliotecas Python num ambiente próprio (`~/.criabr/venv`).
3. Rode os scripts com o Python que ele imprimir na linha `PYTHON=` (também gravado em `~/.criabr/ambiente.json`).

As 3 marcas do estilo: **(1)** um bloco de terreno recortado sobre uma base técnica verde-água, câmera ortográfica quase isométrica e totalmente parada; **(2)** acabamento de HQ — faixas chapadas de luz, contorno a nanquim, hachura de gravura e salpicos nas sombras roxas duras; **(3)** o relevo se transforma continuamente, numa onda que atravessa o bloco, sem nenhum corte. Juntas, elas fazem o espectador ler o vídeo como uma maquete viva: a câmera não se mexe, então todo o movimento é a paisagem mudando, e as faces cortadas do bloco mostram o "por dentro" (solo, água) como num livro de ciências.

Veja `assets/exemplo.mp4` (8 s, "Pão de Açúcar — como a rocha virou cartão-postal"). O código está em `assets/projeto/videos/exemplo-pao-de-acucar/index.html` e é o ponto de partida de todo vídeo novo.

## Preparar a pasta de trabalho (uma vez por projeto)

```
python3 <pasta desta skill>/scripts/projeto.py <pasta-do-projeto>
cd <pasta-do-projeto>
python3 tools/renderizar.py exemplo --preview=6     # confere → previews/exemplo-pao-de-acucar.jpg
```

O `projeto.py` copia `lib/`, `videos/` e `audio/` para a sua pasta e deixa as ferramentas em `tools/`. O motor
(`render.mjs`) e as bibliotecas Node ficam dentro da skill: cada projeto fica leve e o `node_modules` é instalado
uma vez só, pelo `preparar.py`. Requisitos: Node ≥ 20, ffmpeg, Python com numpy+scipy e WebGL2 no Chromium do
Playwright (no Mac usa Metal). O `renderizar.py` passa o render pela trava de memória quando ela existe.
Funciona igual em Mac, Linux e Windows — não há script `.sh` no caminho obrigatório.

## Fluxo

1. **Roteiro em estados.** Um vídeo do estilo é uma sequência de 2–4 *paisagens* do mesmo lugar (ex.: planície → maciço → domos com mar). Escreva a tabela `T` com a janela de cada transformação e dos eventos (água subindo, mata brotando, objetos aparecendo). Ritmo: uma paisagem nova a cada ~2 s, sempre algo se mexendo. Ver `references/movimento.md`.
2. **Relevos como funções.** Cada paisagem é uma função `(x, z) → altura` montada com `DI.domo`, `DI.cristas`, `DI.fbm`, `DI.smax`. Ver `references/receitas.md`.
3. **Montar.** `cp -R videos/exemplo-pao-de-acucar videos/<nn-nome>` e troque: relevos, `DI.metamorfose` (estados + passos), água, mata, adereços (`casinha`, `cabo`, `cabine`, `barco`) e o HUD (título, etiquetas com fio de nanquim).
4. **Preview.** `python3 tools/renderizar.py <nn> --at=0.5,1.5,3,5,7` → `previews/<nn-nome>.jpg`. Olhe: o relevo lê bem? a sombra roxa cai à direita? as etiquetas apontam para o lugar certo?
5. **Som e render.** `python3 tools/renderizar.py <nn> --at=1` (grava `cues.json`) → `<PYTHON> audio/synth.py <nn>` → `python3 tools/renderizar.py <nn>` → `out/<nn-nome>.mp4`. Ver `references/audio.md`.
6. **Conferir.** `ffprobe` (1080×1920, duração, faixa de áudio) e uma folha de quadros: `ffmpeg -i out/<v>.mp4 -vf "fps=4,scale=180:-1,tile=8x4" -frames:v 1 folha.jpg`.

Para recriar o estilo a partir de outra referência, compare lado a lado: `<PYTHON> tools/analisar.py comparar <ref.mp4> out/<v>.mp4 previews/comparar.jpg`.

## Regras do motor

- **Tudo é função de `t`.** O 3D muda em `S.update = t => {…}`; o HUD em `onTick(t => …)` ou na timeline `TL` (GSAP). Nada de animação CSS, `setTimeout`, `requestAnimationFrame` ou `Math.random()` — use `DI.rng(semente)`.
- **Página = módulo.** A página carrega `boot.js` (GSAP + núcleo + importmap do three) e depois `<script type="module">import * as DI from '../../lib/diorama.js'</script>`. Defina `window.SETUP` de forma síncrona no módulo (sem `await` no topo).
- **Paisagens são calculadas uma vez.** `DI.metamorfose` guarda cada estado num array; por quadro só mistura. Não chame `fbm`/`cristas` dentro do `S.update` para a malha inteira.
- **Câmera parada.** Não anime a câmera: o estilo vive do terreno mudando. Para enquadrar, mude `meia` (zoom) e `alvo` (sobe/desce o bloco na tela) no `DI.palco`.
- **Cores em hex sRGB direto.** A lib desliga gestão de cor e tone mapping: o hex da rampa é o hex do vídeo. Para mudar a paleta, edite `DI.RAMPAS` ou passe `rampa: {c:[5 tons], cs, hc}`.
- **Elemento HTML escondido** entra com `TL.fromTo(..., {immediateRender: true})`.
- **Fonte:** só Chakra Petch (300–700) vem na skill. Outra fonte: ponha o woff2 em `lib/fonts/` e o `@font-face` em `lib/fonts.css`.

## Armadilhas conhecidas

- **`domo` fora do raio é negativo de propósito**: assim `smax(chão, domo)` não levanta o chão em volta. Não troque por `Math.max(0, …)`.
- **A frente "acima" da tela é o canto −x −z** (câmera em +x +z). O que fica atrás dos morros não aparece: ponha terra/mata na frente e à esquerda, mar à direita.
- **Laço de medida de texto**: meça um `<span>` interno (`DI.titulo` já faz isso); `scrollWidth` de um bloco `left:0;right:0` nunca diminui.
- **Fosso escuro na erosão**: se o fundo do mar for cavado antes da água chegar, aparece um buraco preto. Comece a subir a água junto com a erosão.
- **Contorno demais**: se o nanquim pegar ruído no relevo, suba `kNormal` (padrão .32) ou `kDepth` (.05) no `DI.palco`.

## Arquivos

- `assets/projeto/lib/diorama.js` — a biblioteca do estilo (API em `references/receitas.md`).
- `assets/projeto/audio/synth.py` — trilha e efeitos sintetizados, com os sons do estilo (`ronco`, `cascalho`, `mar`, `folhas`, `bonde`).
- `references/estilo.md` (paleta, materiais, composição) · `movimento.md` (tempos e transformações) · `receitas.md` (API e receitas) · `audio.md` (trilha e cues).
- `scripts/projeto.py` (monta a pasta de trabalho) · `scripts/renderizar.py` (chama o motor com o Node certo e pela trava) · `scripts/analisar.py` (ler/comparar referências) · `scripts/comum.py` · `scripts/preparar.py`.
